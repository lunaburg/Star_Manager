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
UNIQUE(zipmod_guid, kind, item_id)
```

`duplicate_zipmods` 记录同一 `guid` 下未被选为主记录的重复 zipmod 文件。重复文件不进入 `zipmods` 主索引，也不解析 `mod_items`。

`character_cards` 和 `character_card_dependencies` 用于角色卡索引。依赖表通过可空外键关联到 `zipmods.id` 和 `mod_items.id`：

`character_cards` 同时缓存人物卡浏览器需要的姓名、收藏、评分和标签。`tags_json` 保存 `star.manager.cardmetadata.tags` 的 JSON 数组，`favorite` 与 `rating` 保存对应展示值；`metadata_file_size` 和 `metadata_modified_ns` 是这组浏览缓存的文件签名。目录切换时，签名未变化的人物卡直接使用 SQLite，不再打开 PNG；新增、外部修改或旧数据库中尚未补齐签名的卡只读取一次，并同步刷新浏览缓存。

浏览缓存签名与用于依赖变动检测的 `modified_at` 分开维护。目录浏览补齐姓名、收藏、评分和标签时不得覆盖 `modified_at`，否则外部修改过依赖数据的人物卡会被误判为无需重建。应用内明确知道只修改了收藏、评分、标签、人物参数或封面的单卡操作，可以同时同步两组签名，因为这些操作会保留依赖区块。

标签弹窗从 SQLite 汇总全库标签，不在每次打开时重新解析所有 PNG。旧数据库首次读取标签时执行一次性回填并写入 `character_card_tags_cache_root` 元数据；人物卡数据库重建和单卡标签修改都会同步该缓存。

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
9. 对重新解析过的 zipmod，按 `zipmod_guid + kind + item_id` 更新现有 `mod_items`，尽量保留物品主键和角色卡依赖；本轮已不存在的物品才删除，新增物品才插入。
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

重新解析某个 zipmod 时，`replace_mod_items()` 会按以下稳定键匹配已有物品：

```text
zipmod_guid + kind + item_id
```

匹配到的物品原地更新并保留 `mod_items.id`，不存在的旧物品才删除，新增物品才插入。这样角色卡依赖不会因为普通重解析而被外键置空。写入完成后回填 `zipmods`：

- `item_count`
- `unity3d_status`
- `unity3d_in_mod_count`
- `unity3d_in_game_count`
- `unity3d_missing_count`
- `unity3d_error`

zipmod 级 Unity3D 状态优先级是：

```text
error > missing > in_game > in_mod > empty
```

因此只要有任意 item 的 Unity3D 资源不可用，整个 zipmod 就会标记为 `error`；没有 error 但有缺失引用时标记为 `missing`；没有缺失但依赖游戏目录 `abdata` 时标记为 `in_game`；全部资源都在 zipmod 内时标记为 `in_mod`。

## 角色卡依赖关联更新

`build_mod_database` 任务会在模组数据库完成后继续调用 `build_card_database()`。增量模式不会再重新关联所有角色卡，而是由模组阶段返回本轮受影响的 GUID，再只更新引用这些 GUID 的缓存卡片。

受影响 GUID 包括：

- 新增或内容发生变化、需要替换 `mod_items` 的主 zipmod；
- 已删除的旧 GUID；
- 同一路径的 manifest GUID 发生变化时的旧 GUID 和新 GUID；
- 重复 GUID 的主文件发生切换；
- 因缩略图或 Unity3D 重试而重新生成物品记录的 GUID。

角色卡增量处理规则：

1. 新增或修改的角色卡仍读取 PNG，并重新提取全部原始依赖。
2. 未变化、但引用了受影响 GUID 的卡片，从已有依赖行读取原始键并重新关联。
3. 未变化且不引用受影响 GUID 的卡片保留原依赖行，不执行删除和重新插入。
4. 独立调用 `build_card_database` 且没有提供 GUID 影响集合时，为兼容旧调用仍重新关联所有缓存卡。
5. `mode = full` 时重新解析全部卡片。

关联阶段一次加载有效 `zipmods` 和 `mod_items`，建立大小写无关、去除首尾空白并兼容数字前导零的内存索引。所有卡片共享该索引，避免为每条依赖重复执行 SQLite 查询。

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

当 zipmod 或 item 记录被删除时，已有依赖表的外键会被置空。模组阶段必须把对应 GUID 放入影响集合，使后续角色卡阶段更新 `zipmod_id`、`mod_item_id`、`resolve_status` 和卡片缺失依赖统计。

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

如果用户在应用内只修改人物卡收藏、评分、标签、人物参数或封面，单卡接口会同步 SQLite 浏览缓存的文件签名，不需要再提交完整 `build_mod_database`；移动、删除和外部程序修改文件则仍通过下一次变动检测发现。插件页面使用独立的 BepInEx 文件指纹缓存，不参与 zipmod/角色卡自动重建阈值。

## 维护注意事项

- 修改变动检测字段时，需要同步考虑 `assess_zipmod_file_changes()`、`build_candidates_from_file_stats()` 和前端自动重建提示。
- 修改 `zipmods` 主键策略时，需要同步检查 `duplicate_zipmods`、`mod_items` 唯一约束和角色卡依赖解析。
- 修改 item 唯一性时，需要同步检查 `replace_mod_items()`、`find_mod_item_id()` 和 CSV 重复行处理。
- 修改删除策略时，需要确认 `mod_items` 级联删除、角色卡依赖外键置空和 stale 过滤是否仍符合预期。
- 如果未来引入内容哈希，应明确哈希计算成本，并决定是否只在大小/时间变化时计算。
