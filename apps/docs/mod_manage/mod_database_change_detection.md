# 模组数据库变动检测与关联更新

本文记录当前代码中模组数据库的变动检测、增量建库、重复 GUID 处理，以及角色卡依赖关联更新逻辑。需要修改数据库扫描、重建、异常诊断、角色卡依赖解析或前端自动重建提示时，应先阅读本文。

## 相关代码

- `apps/backend/star_manager/services/mod_database.py`：变动检测、增量/全量建库主流程。
- `apps/backend/star_manager/services/mod_database_core.py`：SQLite schema、dataclass、基础元数据工具。
- `apps/backend/star_manager/services/mod_database_assets.py`：zipmod 扫描、manifest/CSV 解析、重复项、删除、修复和写回。
- `apps/backend/star_manager/services/mod_database_queries.py`：数据库状态、列表、筛选和导出查询。
- `apps/backend/star_manager/services/card_database.py`：角色卡索引和角色卡依赖到 zipmod/item 的关联解析。
- `apps/backend/app/server.py`：`GET /mods/database/changes` 等 HTTP 入口。
- `apps/backend/app/bridge.py`：`build_mod_database` 任务入口。
- `apps/src/App.vue`：启动时的数据库变动检测和自动增量重建触发。

## 数据表关系

`zipmods` 是模组级主索引。每个主 zipmod 一条记录，业务唯一键是 `guid`。表中同时记录文件位置、文件大小、修改时间、扫描状态、物品数量和 Unity3D 诊断汇总。

`mod_items` 是物品级明细索引。它通过 `zipmod_id` 关联到 `zipmods.id`，并冗余保存 `zipmod_guid` 和 `zipmod_author`，便于筛选和诊断。当前唯一约束是：

```text
UNIQUE(zipmod_guid, item_id)
```

`duplicate_zipmods` 记录同一 `guid` 下未被选为主记录的重复 zipmod 文件。重复文件不进入 `zipmods` 主索引，也不解析 `mod_items`。

`character_cards` 和 `character_card_dependencies` 用于角色卡索引。依赖表通过可空外键关联到 `zipmods.id` 和 `mod_items.id`：

```text
character_card_dependencies.zipmod_id -> zipmods.id ON DELETE SET NULL
character_card_dependencies.mod_item_id -> mod_items.id ON DELETE SET NULL
```

## 变动检测入口

前端启动后会调用：

```text
GET /mods/database/changes?game_dir=<game_dir>
```

后端由 `server.py` 转发到 `assess_database_changes()`。该函数同时检测 zipmod 和角色卡文件变化，并返回是否需要重建、建议动作和变化统计。

当前自动重建阈值：

```text
AUTO_REBUILD_MAX_CHANGES = 200
AUTO_REBUILD_MAX_RATIO = 0.05
```

如果总变化数不超过 200，且变化比例不超过 5%，前端会自动提交 `build_mod_database` 任务并使用 `mode = "incremental"`。否则只提示用户手动重建。

## zipmod 变动判定

检测时扫描当前游戏目录：

```text
<game_dir>/mods/**/*.zipmod
```

对每个文件记录：

```text
absolute file_path
file_size
modified_at
```

然后与数据库中 `scan_status != 'stale'` 的 `zipmods` 记录比较：

- 新增：当前文件系统存在该路径，数据库没有该路径。
- 移除：数据库有该路径，当前文件系统没有该路径。
- 修改：路径相同，但 `file_size` 或 `modified_at` 不同。

注意：变动检测阶段按文件路径比较；建库写入阶段按 `guid` upsert。因此同一个 zipmod 文件被移动时，检测结果可能表现为“一个新增 + 一个移除”，但建库时会更新同一条 `guid` 主记录的路径，而不是创建新的业务记录。

## 增量建库流程

`build_mod_database` 任务由 `bridge.py` 调用 `build_database()`。该任务先重建模组数据库，再重建角色卡数据库。

增量建库不是简单清空数据库后全量写入。当前流程会尽量复用未变化 zipmod 的旧数据：

1. 扫描 `mods/**/*.zipmod`。
2. 对每个 zipmod 比较 `file_size` 和 `modified_at`。
3. 如果文件未变且旧记录不是 `stale`，复用数据库中的 manifest 数据，不重新读取 manifest，也不重新解析 CSV。
4. 如果文件新增或修改，读取 `manifest.xml`，并加入变化集合。
5. 按 `guid` 分组有效候选，缺失或无效 `guid` 的文件进入 invalid 处理。
6. 每个 `guid` 选择一个主 zipmod。
7. 只对变化过的主 zipmod 重新解析 CSV、缩略图和 Unity3D 状态。
8. 将主记录 upsert 到 `zipmods`。
9. 对重新解析过的 zipmod，删除旧 `mod_items` 并插入新 `mod_items`。
10. 回填 `zipmods.item_count` 和 zipmod 级 Unity3D 汇总状态。
11. 删除本轮未见到的旧 zipmod 记录。
12. 更新 `database_metadata.last_built_at`。

## 新增文件处理

新增 zipmod 在数据库中没有可复用路径记录，因此会读取 `manifest.xml`。

如果 manifest 有有效 `guid`：

- 进入 `guid` 分组。
- 参与主记录选择。
- 主记录通过 `upsert_zipmod()` 写入 `zipmods`。
- 其 CSV 物品通过 `replace_mod_items()` 写入 `mod_items`。
- 物品数量和 Unity3D 汇总写回 `zipmods`。

如果 manifest 缺失、解析失败或没有 `guid`：

- 使用 `__invalid__:<path>` 作为内部 guid 写入 `zipmods`。
- `scan_status` 和 `scan_error` 记录具体错误。
- 不解析 `mod_items`。

## 移除文件处理

建库过程中会维护本轮扫描到的 `seen_guids`。写入结束后调用 `remove_unseen_zipmods()`：

```text
DELETE FROM zipmods WHERE guid NOT IN (...)
```

由于 `mod_items.zipmod_id` 使用 `ON DELETE CASCADE`，删除 zipmod 主记录时对应物品记录会自动删除。

批量导出选择 `move` 时是一个特殊路径：导出成功后不会立即删除数据库记录，而是把对应 `zipmods` 标记为：

```text
scan_status = 'stale'
scan_error = 'moved by export'
```

普通列表和统计默认过滤 `scan_status != 'stale'`，因此 stale 记录不会显示在常规模组列表中。

## 修改文件处理

如果路径相同，但 `file_size` 或 `modified_at` 变化，增量建库会将其视为修改。

修改后的处理方式：

1. 重新读取 manifest。
2. 按 `guid` 更新 `zipmods` 主记录。
3. 重新解析该 zipmod 内的 CSV。
4. 删除该 `zipmod_id` 下旧的 `mod_items`。
5. 插入新的 `mod_items`。
6. 重新提取或记录缩略图状态。
7. 重新检测 item 级 Unity3D 状态。
8. 重新汇总 zipmod 级 Unity3D 状态。

当前没有使用内容哈希。判断依据是文件大小和修改时间，速度较快，但依赖文件系统时间戳准确。

## 重复 GUID 处理

如果多个 zipmod 文件拥有相同 `guid`，只有一个文件进入 `zipmods` 主索引，其余文件写入 `duplicate_zipmods`。

主记录选择规则：

1. 如果数据库已有该 `guid` 的路径，并且本轮候选中仍存在该路径，继续选它作为主记录。
2. 否则选择 `modified_at` 最新的文件。
3. 如果修改时间相同，选择 `file_size` 更大的文件。
4. 如果仍无法区分，按路径字典序选择第一个，保证结果稳定。

重复文件不会解析 `mod_items`。列表状态判断中，只要某个主 zipmod 存在重复记录，就会被视为异常。

## item 替换与汇总

重新解析某个 zipmod 时，`replace_mod_items()` 会先执行：

```text
DELETE FROM mod_items WHERE zipmod_id = ?
```

然后插入本次解析出的物品行。插入完成后回填 `zipmods`：

- `item_count`
- `unity3d_status`
- `unity3d_in_mod_count`
- `unity3d_in_game_count`
- `unity3d_missing_count`
- `unity3d_error`

zipmod 级 Unity3D 状态优先级是：

```text
missing > in_game > in_mod > empty
```

因此只要有任意 item 缺失 Unity3D，整个 zipmod 就会标记为 `missing`；没有缺失但依赖游戏目录 `abdata` 时标记为 `in_game`；全部资源都在 zipmod 内时标记为 `in_mod`。

## 角色卡依赖关联更新

`build_mod_database` 任务会在模组数据库完成后继续调用 `build_card_database()`，因此角色卡依赖会基于最新的 `zipmods` 和 `mod_items` 重新解析。

角色卡依赖解析时：

1. 从卡片中读出 `mod_id`、`category_no`、`slot`、`local_slot`。
2. 用 `mod_id` 匹配非 stale 的 `zipmods.guid`。
3. 如果找到 zipmod，再尝试匹配 item。
4. item 匹配先使用 `zipmod_guid + kind + item_id`。
5. 如果精确匹配失败，再降级使用 `zipmod_guid + item_id`。

依赖状态含义：

- `resolved`：找到 zipmod 和对应 item。
- `missing_item`：找到 zipmod，但找不到对应 item。
- `missing_zipmod`：找不到对应 zipmod。

当 zipmod 或 item 记录被删除时，已有依赖表的外键会被置空。但正常建库流程会在后续角色卡重建阶段删除旧依赖并重新插入新依赖。

## 前端行为

前端启动或进入相关页面时会读取数据库状态和变动检测结果。

如果 `/mods/database/changes` 返回无需重建，前端只记录日志。

如果返回 `recommended_action = "auto_incremental"`，前端自动提交：

```text
POST /tasks
task_type = build_mod_database
payload.mode = incremental
```

如果返回 `manual_rebuild`，前端只提示用户手动重建数据库，避免大规模扫描或写库在启动时自动发生。

## 维护注意事项

- 修改变动检测字段时，需要同步考虑 `assess_zipmod_file_changes()`、`build_candidates_from_file_stats()` 和前端自动重建提示。
- 修改 `zipmods` 主键策略时，需要同步检查 `duplicate_zipmods`、`mod_items` 唯一约束和角色卡依赖解析。
- 修改 item 唯一性时，需要同步检查 `replace_mod_items()`、`find_mod_item_id()` 和 CSV 重复行处理。
- 修改删除策略时，需要确认 `mod_items` 级联删除、角色卡依赖外键置空和 stale 过滤是否仍符合预期。
- 如果未来引入内容哈希，应明确哈希计算成本，并决定是否只在大小/时间变化时计算。
