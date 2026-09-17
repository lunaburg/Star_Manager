# 模组数据库变动检测与关联更新

本文记录当前代码中模组数据库的变动检测、增量建库、重复 GUID 处理，以及角色卡依赖关联更新逻辑。需要修改数据库扫描、重建、异常诊断、角色卡依赖解析或前端自动重建提示时，应先阅读本文。

## 相关代码

- `apps/backend/star_manager/services/mod_database.py`：变动检测、增量/全量建库主流程。
- `apps/backend/star_manager/services/mod_database_core.py`：SQLite schema、dataclass、基础元数据工具。
- `apps/backend/star_manager/services/mod_database_assets.py`：zipmod 扫描、manifest/CSV 解析、重复项、删除、修复和写回。
- `apps/backend/star_manager/services/mod_database_queries.py`：数据库状态、列表、筛选和导出查询。
- `apps/backend/star_manager/services/card_database.py`：角色卡索引和角色卡依赖到 zipmod/item 的关联解析。
- `apps/backend/app/server.py`：`GET /mods/database/changes` 等 HTTP 入口。
- `apps/backend/app/bridge.py`：`build_mod_database` 和工作台 `index_single_zipmod` 任务入口。
- `apps/src/App.vue`：启动时的数据库变动检测和自动增量重建触发。

## 数据表关系

`zipmods` 是模组级主索引。每个主 zipmod 一条记录，业务唯一键是 `guid`。表中同时记录文件位置、文件大小、修改时间、扫描状态、物品数量和 Unity3D 诊断汇总。

`mod_items` 是物品级明细索引。它通过 `zipmod_id` 关联到 `zipmods.id`，并冗余保存 `zipmod_guid` 和 `zipmod_author`，便于筛选和诊断。当前唯一约束是：

```text
UNIQUE(zipmod_guid, kind, csv_path, item_id)
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
9. 对重新解析过的 zipmod，按 `zipmod_guid + kind + csv_path + item_id` 更新现有 `mod_items`，尽量保留物品主键和角色卡依赖；本轮已不存在的物品才删除，新增物品才插入。该键同时允许同一个 Studio 模组的不同 ItemList 复用局部 ID。
10. 回填 `zipmods.item_count` 和 zipmod 级 Unity3D 汇总状态。
11. 删除本轮未见到的旧 zipmod 记录。
12. 更新 `database_metadata.last_built_at`。

### 缩略图失败不触发模组物品重解析

- **变更**：增量建库不再因为数据库中已有的缩略图失败或缺失状态，将对应 GUID 加入物品重解析集合。
- **保留行为**：模组文件本身发生变化、执行全量建库，或通过缩略图专用处理流程时，仍会按相应流程重新处理缩略图。
- **适用边界**：该调整只取消“历史缩略图失败 → 整个模组重新解析”的触发条件，不改变缩略图状态、错误信息或单独修复接口。

### CSV 解析器版本不触发模组物品重解析

- **变更背景**：增量建库原先会把 CSV 解析器版本变化视为所有 zipmod 的物品重解析条件。
- **调整**：移除 `mod_item_parser_version` 的比较和写入逻辑；解析器版本变化本身不再加入 `replaced_item_guids`。
- **适用边界**：模组文件发生变化、执行全量建库或 Unity3D 提供者索引变化时，仍按对应条件重新解析物品。

## 新增文件处理

新增 zipmod 在数据库中没有可复用路径记录，因此会读取 `manifest.xml`。

如果 manifest 有有效 `guid`：

- 进入 `guid` 分组。
- 参与主记录选择。
- 主记录通过 `upsert_zipmod()` 写入 `zipmods`。
- 其 CSV 物品通过 `replace_mod_items()` 写入 `mod_items`。
- 物品数量和 Unity3D 汇总写回 `zipmods`。

## 工作台单个模组索引

工作台打包完成后不使用全目录 `build_mod_database`。Electron 会提交 `index_single_zipmod`，payload 同时包含游戏目录和刚生成的 zipmod 路径。该任务只读取目标 zipmod 的 manifest、CSV、缩略图和 Unity3D 状态，然后按 GUID upsert 一个主记录并替换该 GUID 的物品行；不会遍历其它 `mods/**/*.zipmod`，不会删除其它数据库记录，但会把受该 GUID 影响的人物卡依赖记录增量重连，避免人物卡文件未变化导致“缺失数量”继续使用旧缓存。

### 工作台单模组索引边界修正记录

- **问题背景**：工作台已经生成目标 zipmod，但单模组数据库同步仍需要较长时间，进度长期停在 5% 或同步过程中与其它任务竞争 SQLite 写锁。
- **根因**：`index_single_zipmod()` 曾在处理目标 zipmod 前调用 `build_candidates(game_dir)` 和 `refresh_unity3d_provider_index()`。前者递归遍历整个 `mods/**/*.zipmod` 并读取 manifest，后者还会按缓存状态读取多个压缩包的 Unity3D 目录；这超出了单模组索引边界。
- **解决方案**：单模组任务现在只在 SQLite 的 `zipmods` 表按 `guid` 查询是否已有记录，然后解析目标 zipmod 必需的 manifest、CSV、缩略图和自身 Unity3D 引用，使用现有 GUID 记录执行 upsert。全目录候选扫描和 provider 索引刷新仅由完整数据库重建负责；单模组任务不再刷新其它模组的 provider 数据。
- **验证结果**：`conda run -n mm_env python -m unittest discover -s apps/backend/tests -p 'test_single_zipmod_index.py' -v` 通过；回归测试确认单模组索引不会调用全目录 zipmod 扫描。
- **适用边界**：单模组同步优先保证目标 zipmod 快速入库；其它模组提供的 Unity3D 关联状态沿用现有数据库结果，目标模组替换后如需刷新全库 provider 关系，仍应执行完整增量数据库重建。

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
zipmod_guid + kind + csv_path + item_id
```

匹配到的物品原地更新并保留 `mod_items.id`，不存在的旧物品才删除，新增物品才插入。这样角色卡依赖不会因为普通重解析而被外键置空。写入完成后回填 `zipmods`：

- `item_count`
- `unity3d_status`
- `unity3d_not_in_mod_count`
- `unity3d_in_mod_count`
- `unity3d_in_game_count`
- `unity3d_other_mod_count`
- `unity3d_missing_count`
- `unity3d_error`

Unity3D 提供者索引还记录每个实际 zipmod 的文件签名和其中的 Unity3D 文件/目录路径。增量建库只重新读取新增、修改或此前没有索引记录的 zipmod 压缩包目录；其它 zipmod 提供者变化时，会重新计算受影响的 Unity3D 状态。诊断页直接查询该索引，不在每次打开诊断时遍历所有 zipmod。

zipmod 级 Unity3D 状态优先级是：

```text
error > missing > not_in_mod > in_mod > empty
```

因此只要有任意 item 的 Unity3D 资源不可用，整个 zipmod 就会标记为 `error`；没有 error 但有缺失引用时标记为 `missing`；没有缺失但资源在当前 zipmod 外时标记为 `not_in_mod`。`game_abdata` 与 `other_zipmod` 两种来源都会让模组进入警告状态；`unity3d_in_game_count` 和 `unity3d_other_mod_count` 分别保留来源统计。

## 角色卡依赖关联更新

`build_mod_database` 任务会在模组数据库完成后继续调用 `build_card_database()`。增量模式不会再重新关联所有角色卡，而是由模组阶段返回本轮受影响的 GUID，再只更新引用这些 GUID 的缓存卡片。

受影响 GUID 包括：

- 新增或内容发生变化、需要替换 `mod_items` 的主 zipmod；
- 已删除的旧 GUID；
- 同一路径的 manifest GUID 发生变化时的旧 GUID 和新 GUID；
- 重复 GUID 的主文件发生切换；

角色卡增量处理规则：

1. 新增或修改的角色卡仍读取 PNG，并重新提取全部原始依赖。
2. 未变化、但引用了受影响 GUID 的卡片，从已有依赖行读取原始键并重新关联。
3. 未变化且不引用受影响 GUID 的卡片保留原依赖行，不执行删除和重新插入。
4. 独立调用 `build_card_database` 且没有提供 GUID 影响集合时，普通增量模式保留所有缓存卡的依赖行，不执行无差别重关联。
5. `mode = full` 时重新解析全部卡片。

### 增量重关联条件修正记录

- **问题背景**：普通增量建库没有模组 GUID 影响集合时，缓存人物卡仍会被逐张执行依赖重关联，导致未变化卡片重复进行内存解析和依赖状态计算。
- **根因**：旧条件使用 `affected_card_ids is None or ...`；而 `None` 表示“没有指定受影响集合”，并不表示“所有卡片受影响”，却因此让所有缓存卡的 `should_relink` 都为真。
- **解决方案**：`should_relink` 现在仅在全量模式，或卡片 ID 明确存在于 `affected_card_ids` 集合时为真。普通增量模式没有影响集合时直接沿用缓存的依赖计数和依赖行。
- **验证结果**：新增回归测试确认普通增量不会调用 `resolve_cached_dependencies()`，缓存卡计入 `untouched_cards`；受影响 GUID 的既有重关联测试仍通过。
- **适用边界**：该优化只影响缓存卡。新卡、文件签名发生变化的卡仍会重新读取和解析；模组建库阶段必须正确传递受影响 GUID，才能触发对应人物卡的依赖重连；`mode = full` 仍会完整重建。

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

### 模组建库线程数配置

- **问题背景**：模组物品与缩略图准备阶段原先在主模组数量不超过 1000 个时固定使用单线程，超过阈值后才按逻辑处理器数量选择最多 8 个 worker；同一台电脑会因为任务规模不同而使用不同并发度。
- **解决方案**：新增设置项“建库线程数”。`build_mod_database` 将设置值同时传给模组和人物卡准备阶段，两个阶段始终按该值创建 worker，不再根据本轮任务大小降级。后端按 `1..min(8, floor(可用逻辑处理器 / 2))` 进行最终校验；未提供设置值时使用当前机器上限。SQLite 写入仍由主线程串行完成。
- **前端行为**：设置页显示本机检测到的逻辑处理器数量和可选线程范围，应用级硬上限为 8；设置保存到 Electron 用户设置，自动增量建库和手动重建共用该值。
- **验证结果**：后端单元测试覆盖 32 逻辑处理器对应 8 worker 上限、单处理器退化为 1、请求值过大截断，以及任务桥传递配置值；前端构建和 Python 测试用于验证完整链路。
- **适用边界**：线程数上限适用于模组和人物卡解析/预览准备 worker，不代表 SQLite 写入线程数；大体积 Unity3D 模组或大型 PNG 会提高并发内存峰值，8 线程仍不是所有磁盘和内存配置下的最佳速度，用户可选择更低值。

#### Manifest 读取并发化（2026-09-17）

- **问题背景**：全量或首次建库时，`build_candidates_from_file_stats()` 会逐个打开 zipmod 并读取 `manifest.xml`；已有“建库线程数”设置仅影响后续 CSV、缩略图和 Unity3D 准备，无法缩短该阶段。
- **根因**：文件指纹、SQLite 缓存复用判断和 ZIP manifest 读取位于同一个主线程循环中。
- **解决方案**：主线程仍顺序读取文件属性、判断 `file_size`/`modified_at` 缓存命中并维护稳定候选顺序；对新增、变更或全量模式下需要实际读取的 archive，复用同一 `worker_count` 建立 `ThreadPoolExecutor` 并行读取 manifest。worker 不访问 SQLite，完成结果由主线程汇总。单 worker、单个待读取 archive 和缓存命中场景保持顺序读取。
- **验证结果**：`test_mod_database_workers.py` 新增两份变更 zipmod 的 barrier 并发测试，确认配置为 2 时 manifest 读取在两个 worker 中执行；既有 worker 上限测试仍覆盖配置截断。
- **适用边界**：并发只覆盖 manifest 文件读取，不改变 ZIP 中央目录解析、SQLite 串行写入或后续 Unity3D provider 扫描。NVMe 通常适合从 4 worker 开始实测，机械硬盘应从 2 worker 开始，避免随机读取竞争。

#### 模组准备进度日志节流（2026-09-17）

- **问题背景**：并行准备 CSV、缩略图与 Unity3D 状态时，每完成一个主 zipmod 都会发送一次 `Prepared N/total primary zipmods` 进度消息；大型库会在运行日志中产生数千条相邻记录。
- **解决方案**：多 worker 与单 worker 路径统一仅在完成数为 100 的倍数，以及最后一个主 zipmod 完成时发送准备阶段进度消息。
- **验证结果**：`test_mod_database_workers.py` 覆盖 250 个任务只报告 100、200、250，以及总数小于 100 时仍报告最终完成项。
- **适用边界**：节流只减少任务桥和前端运行日志的重复消息，不改变实际准备顺序、进度区间、worker 调度或 SQLite 写入。

#### 8 线程硬上限调整（2026-09-16）

- **背景**：实际建库测试中，12 线程的缩略图解析阶段明显慢于 8 线程；该阶段受磁盘、UnityPy 和内存并发影响，不会随线程数线性提速。
- **调整**：Electron 设置层、模组数据库后端和人物卡数据库后端统一将最大 worker 数限制为 8；保留“可用逻辑处理器一半”作为较低机器的进一步限制。历史设置中的 12 或更大值加载时会自动截断为 8。
- **验证**：更新 worker 上限单元测试，并执行 Python 测试、前端构建、Electron/Preload 语法检查和 `git diff --check`。
- **边界**：该限制只约束建库解析与预览准备的 worker 数，不改变 SQLite 串行写入，也不保证 8 线程在每台电脑上的绝对最优速度。

### 角色卡建库的并行解析

- **问题背景**：人物卡数据库重建原先按单一循环逐张读取 PNG、解析卡片内容、生成预览并写入 SQLite；人物卡数量较多或卡片体积较大时，解析阶段会成为主要耗时。
- **根因**：PNG 读取、MessagePack/UAR 解析和预览生成属于独立的文件/CPU 工作，但原流程把它们与 SQLite 写入放在同一条串行路径中。
- **解决方案**：`build_card_database()` 现在先在主线程加载可复用的卡片记录、依赖原始键和模组/item 解析器，然后使用应用“建库线程数”设置并行准备人物卡记录。worker 不访问 SQLite；SQLite 的 upsert、依赖替换、stale 标记和构建元数据更新仍由主线程在单事务中按稳定路径顺序完成。
- **验证结果**：`conda run -n mm_env python -m unittest discover -s apps/backend/tests -p 'test_card_database.py' -v` 通过，并包含多 worker 调度测试以及原有依赖重连、文件签名和 ID 匹配测试。
- **适用边界**：并行化覆盖人物卡扫描后的解析和预览准备，不会并行写 SQLite；线程数上限与模组建库相同，为可用逻辑处理器的一半。服装卡的独立 `clothes_card_index.sqlite` 不属于本次流程。

### 人物卡任务进度消息节流

- **问题背景**：人物卡建库的每张卡准备完成和写入完成都会通过任务桥发送一条进度消息。数千张卡会产生大量重复状态传输，并持续增加前端运行日志压力。
- **解决方案**：准备阶段和写入阶段都只在每 100 张卡以及当前阶段最后一张卡时调用进度回调；扫描开始和建库完成仍立即上报。进度百分比与文字消息使用同一批节流事件，保证任务状态与日志内容一致。
- **适用边界**：该节流只作用于 `build_card_database` 的人物卡阶段，不改变卡片解析、数据库写入或最终统计；少于 100 张的任务仍会在阶段结束时上报一次。

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
