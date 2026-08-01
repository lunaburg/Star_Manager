# 模组数据库设计

## 目标

模组数据库用于把本地游戏目录中的 zipmod 和模组物品整理为可查询的本地索引。

当前阶段按两个核心索引库组织：

- `zipmods`：通过读取 zipmod 内的 `manifest.xml` 构建，记录模组级信息。
- `mod_items`：通过读取 zipmod 或解包目录中的 CSV 构建，记录物品级信息。

真实数据来源仍然是文件系统、zipmod、`manifest.xml` 和 CSV。数据库只保存扫描后的索引、解析状态和必要的定位信息，方便前端列表、搜索、筛选和详情展示。

## 存储建议

插件管理复用同一个 SQLite 文件，并使用 `bepinex_plugin_cache` 保存只读扫描缓存。每个游戏目录对应一条记录，包括 DLL/config/translation 文件指纹、完整插件 JSON 和扫描时间。路径、大小或修改时间变化时缓存自动失效；用户点击“重新扫描”时强制覆盖缓存。缓存只记录带有效 `BepInPlugin` GUID 的插件，不记录普通依赖程序集、core 或 patchers。

实现上建议使用 SQLite。

初版可以把 `zipmods` 和 `mod_items` 放在同一个 SQLite 文件中的两张核心表，便于事务、关联查询和迁移管理；业务文档和代码模块仍按两个索引库划分职责。

推荐运行时位置：

```text
用户数据目录/
`-- Star_Manager/
    `-- star_manager.sqlite
```

开发期可临时使用：

```text
apps/backend/runtime/star_manager.sqlite
```

数据库文件不应提交到仓库。

## zipmods 索引库

### 数据来源

`zipmods` 只从 `manifest.xml` 和 zipmod 文件自身属性构建。

扫描范围：

```text
游戏目录/mods/**/*.zipmod
```

读取内容：

```xml
<manifest schema-ver="1">
	<guid>模组唯一ID</guid>
	<name>模组名称</name>
	<version>版本号</version>
	<author>作者</author>
	<description>描述</description>
</manifest>
```

### 建议字段

```text
id                  本地数据库 ID，自增
guid                manifest.xml 中的 guid
name                manifest.xml 中的 name
version             manifest.xml 中的 version
author              manifest.xml 中的 author
file_path           zipmod 绝对路径
relative_path       相对 mods 目录的路径
file_name           zipmod 文件名
item_count          该 zipmod 下解析出的物品总数，可由 mod_items 汇总回填
file_size           zipmod 文件大小
modified_at         zipmod 文件最后修改时间
unity3d_status      missing / in_game / in_mod / ''
unity3d_in_mod_count    物品引用资源均在 zipmod 内的数量
unity3d_in_game_count   物品引用资源只在游戏目录 abdata 中的数量
unity3d_missing_count   缺失 unity3d 引用的数量
unity3d_error       unity3d 诊断摘要
scan_status         ok / missing_manifest / invalid_manifest / read_error / stale
scan_error          扫描失败原因
last_scanned_at     最近扫描时间
created_at          首次入库时间
updated_at          最近更新时间
```

### 唯一性

推荐以 `guid` 作为 zipmod 的业务唯一定位。zipmod 可能因为整理、分类或用户手动移动而改变所在文件夹，但 `manifest.xml` 中的 `guid` 不应改变；扫描到相同 `guid` 时，应更新该记录的当前位置、文件名、大小、修改时间和扫描状态，而不是创建新的 zipmod 记录。

`file_path` 表示当前文件位置，只用于打开文件、重扫和诊断，不作为 zipmod 的业务唯一键。

可建立索引：

```text
unique(guid) 

index(file_path)
index(guid)

可用下拉列表选择：
index(author)

待选考虑：
index(scan_status)
```

如果扫描时发现多个文件拥有相同 `guid`，应记录为重复模组状态或诊断项，由前端提示用户处理。后续如果需要识别“同一模组的多个版本”，可基于 `guid + version + file_size/content_hash` 增加版本视图或重复项明细表。

### 重复模组处理

建库时如果发现多个 zipmod 拥有相同 `guid`，应只让其中一个进入 `zipmods` 主索引并参与 `mod_items` 解析，其余文件记录为重复模组诊断项。

推荐处理规则：

```text
1. 按 guid 分组收集扫描到的 zipmod。
2. 每个 guid 选择一个主记录写入 zipmods。
3. 同 guid 的其它文件不写入 zipmods 主记录，不解析 mod_items。
4. 将重复文件路径、文件名、版本、大小、修改时间记录到重复诊断中。
5. 前端在模组管理或运行日志中提示用户处理重复模组。
```

主记录选择优先级：

```text
1. 优先选择 file_path 与数据库中已有记录一致的文件，避免每次扫描来回切换主记录。
2. 如果没有已有记录，优先选择 modified_at 最新的文件。
3. 如果 modified_at 相同，优先选择 file_size 更大的文件。
4. 如果仍无法区分，按 file_path 字典序选择第一个，保证结果稳定。
```

重复模组不应直接覆盖主记录，也不应合并它们的 `mod_items`。否则同一 `guid + item_id` 会出现来源冲突，物品数量和缩略图缓存也会变得不稳定。

如果后续需要保留重复项详情，可增加轻量诊断表：

```text
duplicate_zipmods
```

建议字段：

```text
id                  本地数据库 ID，自增
guid                重复的 manifest guid
primary_zipmod_id   当前进入 zipmods 主索引的记录 ID
file_path           重复 zipmod 绝对路径
relative_path       相对 mods 目录的路径
file_name           zipmod 文件名
version             manifest.xml 中的 version
author              manifest.xml 中的 author
file_size           文件大小
modified_at         文件最后修改时间
reason              duplicate_guid
created_at          首次发现时间
updated_at          最近更新时间
```

初版也可以先不建 `duplicate_zipmods` 表，而是把重复项写入扫描结果和运行日志；但不要把重复文件静默忽略，必须能让用户看到哪些文件重复。

## mod_items 索引库

### 数据来源

`mod_items` 只从 CSV 的实际数据行构建。

扫描范围：

```text
zipmod 内的 abdata/list/**/*.csv
解包模组目录下的 abdata/list/**/*.csv
```

CSV 通常结构：

```csv
元信息1,,,,,
元信息2,,,,,
元信息3,,,,,
ID,Kind,Possess,Name,MainManifest,MainAB,MainData,ThumbAB,ThumbTex
100001,0,1,物品名称,abdata,作者/主资源.unity3d,资源名,作者/缩略图资源.unity3d,thumb
```

每一条实际数据行表示一个物品。一个模组内可能有多个 CSV，一个 CSV 可能有多条实际数据行。一个模组的物品总数等于该模组下所有 CSV 实际数据行数量之和。

元信息行和字段表头行不计入物品总数。

### 建议字段

```text
id                  本地数据库 ID，自增
zipmod_id           关联的 zipmods.id
zipmod_guid         冗余保存 zipmods guid，便于诊断和跨库查询
zipmod_author       模组作者，辅助索引
csv_path            记录当前物品信息保存在模组文件夹的哪个csv中
item_id             CSV 的 ID 字段 
kind                CSV 元信息第一行的列表类别值，只记录白名单类别
name                CSV 的 Name 字段 （物品在游戏中的名字）
main_manifest       CSV 的 MainManifest 字段 （unity3d文件根路径）
main_ab             CSV 的 MainAB 字段 （unity3d文件路径）
main_data           CSV 的 MainData 字段 （unity3d中该物品模型的名字，用以索引）
thumb_ab            CSV 的 ThumbAB 字段 （缩略根路径）
thumb_tex           CSV 的 ThumbTex 字段 （缩略图路径或资源索引）
thumbnail_cache_path 提取后的缩略图缓存路径
thumbnail_status    ready / missing / error，表示缩略图缓存状态
thumbnail_error     缩略图提取失败或缺失原因
unity3d_status      in_mod / in_game / missing
unity3d_error       unity3d 文件定位失败或回退说明
parse_status        ok / missing_header / short_row / parse_error
parse_error         解析失败原因
created_at          首次入库时间
updated_at          最近更新时间
```

### Kind 类别映射

`kind` 字段来自 CSV 表头前的元信息第一行，表示该 CSV 列表的物品类别。注意：CSV 表头中的 `Kind` 字段可能只是行内标记，不作为本项目的物品类别。构建 `mod_items` 时不做类别白名单过滤，凡是 CSV 的实际物品行都写入 `mod_items`；以下列表只用于已知类别的展示映射。

| 分组 | 类别 | Kind |
| --- | --- | --- |
| 男 mod | 上衣 | `140` |
| 男 mod | 下衣 | `141` |
| 男 mod | 手套 | `144` |
| 男 mod | 鞋子 | `147` |
| 角色 | 脸模 | `210` |
| 角色 | 脸部肌肤 | `211` |
| 角色 | 脸部皱纹 | `212` |
| 角色 | 肌肤 | `231` |
| 角色 | 肉感 | `232` |
| 女 mod | 上衣 | `240` |
| 女 mod | 下衣 | `241` |
| 女 mod | 内衣 | `242` |
| 女 mod | 内裤 | `243` |
| 女 mod | 手套 | `244` |
| 女 mod | 裤袜 | `245` |
| 女 mod | 袜子 | `246` |
| 女 mod | 鞋子 | `247` |
| 头发 | 后发 | `300` |
| 头发 | 前发 | `301` |
| 头发 | 鬓发 | `302` |
| 头发 | O | `303` |
| 角色 | 人体彩绘 | `313` |
| 角色 | 眉毛 | `314` |
| 角色 | 睫毛 | `315` |
| 角色 | 眼影 | `316` |
| 角色 | 美瞳种类 | `317` |
| 角色 | 眼睛高光 | `319` |
| 角色 | 口红 | `322` |
| 角色 | 乳头 | `334` |
| 角色 | 阴毛 | `335` |
| 角色 | 图案 | `348` |
| 饰品 mod | 头部 | `351` |
| 饰品 mod | 耳朵 | `352` |
| 饰品 mod | 眼镜 | `353` |
| 饰品 mod | 脸部 | `354` |
| 饰品 mod | 脖子 | `355` |
| 饰品 mod | 肩部 | `356` |
| 饰品 mod | 胸部 | `357` |
| 饰品 mod | 腰部 | `358` |
| 饰品 mod | 后背 | `359` |
| 饰品 mod | 胳膊 | `360` |
| 饰品 mod | 手部 | `361` |
| 饰品 mod | 脚 | `362` |
| 饰品 mod | 腹部下 | `363` |
| 姿势 | 男姿势 | `500` |
| 姿势 | 女姿势 | `501` |

实现时保留原始 `kind` 数字，并在查询或前端展示时映射为类别名称。未知 `kind` 不丢弃，应以原始数字显示；即使数据行里的 `Kind` 字段是已知数字，也不能覆盖元信息第一行的列表类别。

### 唯一性

推荐用 `zipmods.guid + item_id` 定义唯一物品。`zipmods.guid` 标识物品所属模组，`item_id` 对应 CSV 的 `ID` 字段；同一个模组内，同一个 `item_id` 应视为同一个物品。

```text
unique(zipmod_guid, item_id)
```

`csv_path` 用于记录该物品来自哪个 CSV，作为来源定位和诊断信息，不参与物品业务唯一性。若扫描时发现同一 `zipmod_guid + item_id` 出现在多个 CSV 或多行中，应记录为重复物品状态或诊断项，由后续规则决定保留哪一条。

缩略图缓存是 `mod_items` 的派生字段，不单独建立缩略图数据库。构建数据库时根据 `thumb_ab` 和 `thumb_tex` 提取缩略图，缓存到运行时缩略图目录，并把缓存地址写入 `thumbnail_cache_path`。如果提取失败，不应阻断 `mod_items` 入库，而是写入 `thumbnail_status` 和 `thumbnail_error`。

可建立索引：

```text
unique(zipmod_guid, item_id) 唯一索引
-----------------------------------
选中zipmod时，列出，或者查看关联物品：
index(zipmod_id) 同一mod下的所有物品
-----------------------------------
可以用下拉列表选择
index(zipmod_author) 同一个作者的所有物品
index(kind) 同类物品索引
-----------------------------------
可以用搜索栏搜索
index(name) 物品在游戏内的名字
-----------------------------------
index(parse_status) 待考察是否纳入索引
```

## 两个索引库的关系

`zipmods` 是模组级主索引，`mod_items` 是物品级明细索引。

关系：

```text
zipmods.id 1 ---- N mod_items.zipmod_id
```

前端展示模组列表时，主要查询 `zipmods`。

前端展示某个模组包含的物品时，查询：

```sql
select *
from mod_items
where zipmod_id = ?
order by csv_path, csv_row_number;
```

刷新模组物品总数时，使用：

```sql
select count(*)
from mod_items
where zipmod_id = ? and parse_status = 'ok';
```

然后回填到：

```text
zipmods.item_count
```

## 扫描流程

### 全量扫描

```text
选择游戏目录
-> 扫描 mods/**/*.zipmod
-> 对每个 zipmod 读取 manifest.xml
-> 按 guid 分组，识别重复模组
-> 为每个 guid 选择一个主记录
-> 将重复模组写入诊断项或运行日志
-> 写入或更新 zipmods
-> 只扫描主记录 zipmod 内的 abdata/list/**/*.csv
-> 找到 CSV 表头
-> 逐行写入 mod_items
-> 汇总 mod_items 数量回填 zipmods.item_count
-> 标记不存在于本次扫描结果中的旧记录为 stale
```

### 单个 zipmod 重扫

```text
定位 zipmods.id
-> 重新读取 manifest.xml
-> 更新 zipmods
-> 删除该 zipmod_id 下旧的 mod_items
-> 重新解析 CSV 并写入 mod_items
-> 回填 item_count
```

单个 zipmod 重扫建议放在一个事务中。若重扫失败，保留旧数据并把 `scan_status` 或 `parse_status` 更新为错误状态。

### 增量判断

初版可通过以下字段判断是否需要重扫：

```text
guid
file_path
file_size
modified_at
```

如果 `guid` 已存在但 `file_path` 改变，视为同一 zipmod 被移动，更新路径并根据 `file_size` 和 `modified_at` 判断是否需要重新解析 CSV。如果 `file_path`、`file_size` 和 `modified_at` 都未变化，可以跳过 manifest 和 CSV 解析。

后续如果需要更稳，可以增加 `content_hash`，但哈希大文件会增加扫描时间。

## CSV 表头识别

CSV 前几行可能是元信息，不能假设第一行就是表头。

推荐识别方式：

```text
从上到下读取 CSV
找到同时包含 ID 和 Name 的行
将该行视为字段表头
表头之后的非空行视为实际数据行
```

如果表头中存在 `ThumbAB`、`ThumbTex`、`MainAB`、`MainData`，则按字段名读取；如果字段缺失，对应值为空，并记录 `parse_status` 或诊断信息。

## 当前 API

数据库状态：

```text
GET /mods/database
```

返回数据库是否存在、数据库路径、`zipmods` 总数和 `mod_items` 总数。前端进入模组管理或刷新列表时必须先调用该接口：

- 数据库不存在时，不加载列表，提示用户创建数据库。
- 数据库存在但对应表计数为 0 时，提示数据库为空，要求选择有效 HS2 目录后重建。

Zipmod 列表：

```text
GET /mods/zipmods?offset=0&limit=200&author=&status=
```

当前前端首批加载 200 条 zipmod；滚动接近底部时按相同 limit 继续加载。返回结构包含 `rows`、`offset`、`limit`、`total`、`has_more` 和当前筛选条件。`status=normal` 表示扫描正常、无重复 GUID、没有缺失或外置 `.unity3d`；`status=abnormal` 表示存在任一异常。

筛选项：

```text
GET /mods/zipmods/authors
```

物品列表：

```text
GET /mods/items?offset=0&limit=500&search=&kind=&author=&status=
GET /mods/items?zipmod_id=<zipmod_id>&offset=0&limit=1000
```

物品浏览首批加载 500 条 `mod_items`，滚动接近底部后继续分页加载。模组详情的“物品” tab 使用 `zipmod_id` 查询当前模组的关联物品，并展示缩略图、物品名、Kind 映射和状态。`search` 同时匹配 `name`、`item_id` 和 `zipmod_guid`；`status` 当前支持 `ready`、`error` 和 `thumb`。

筛选项：

```text
GET /mods/items/filters
```

缩略图：

```text
GET /mods/thumbnails?path=<encoded_thumbnail_cache_path>
```

该接口只允许读取运行时缩略图缓存目录下的文件。`thumbnail_status = ready` 时前端显示缓存图；缺失或错误时显示稳定占位。

扫描任务：

```text
POST /tasks  { task_type: "build_mod_database", payload: { game_dir } }
GET  /tasks/:task_id
```

创建数据库前后端都会校验游戏目录。后端会拒绝无效 HS2 目录，避免生成空数据库。前端顶部进度条下方显示建库提示：

- `请选择有效目录后点击重建`
- `正在创建数据库，请稍等`
- `数据库已创建`

诊断与修复：

```text
GET  /mods/zipmods/<id>/diagnostics
POST /mods/zipmods/<id>/repair-unity3d
POST /mods/zipmods/<id>/update-author
POST /mods/zipmods/<id>/cleanup-duplicates
POST /mods/zipmods/<id>/delete
POST /mods/items/<id>/import-thumbnail
POST /mods/items/<id>/delete
```

这些接口会直接改写 zipmod 或删除文件，调用侧必须走高风险确认或清晰的单项确认流程。

当前实现还提供：

```text
GET  /plugins?game_dir=&search=&category=&offset=&limit=&refresh=
POST /mods/items/<id>/model-preview
POST /mods/items/<id>/export-fbx
POST /mods/items/<id>/export-thumbnail
GET  /mods/models/<file.glb>
GET  /mods/mannequin/body.fbx
```

这些资源预览和导出接口不改变数据库源记录；模型缓存、缩略图缓存和插件扫描缓存都属于可重建运行时数据。完整 HTTP/task payload 以 `apps/docs/backend-interface.md` 为准。

## 当前后端模块

```text
apps/backend/star_manager/
|-- core/
|   |-- card_metadata.py
|   |-- card_parser.py
|   |-- character_profile.py
|   |-- coordinate_card.py
|   `-- zipmod_utils.py
|-- services/
|   |-- achievements.py
|   |-- card_database.py
|   |-- card_library.py
|   |-- model_preview.py
|   |-- mod_database.py
|   |-- mod_database_assets.py
|   |-- mod_database_core.py
|   |-- mod_database_queries.py
|   |-- plugin_library.py
|   |-- sims4_workbench.py
|   `-- mod_workflow.py
|-- tools/
|   `-- mod_sorter.py
`-- utils/
    `-- binary_reader.py
```

职责划分：

- `mod_database.py`：模组数据库兼容门面，继续导出既有 public API，并保留 `build_database` / `replace_mod_items` 主流程，避免破坏 `server.py`、`bridge.py` 和开发脚本的旧导入路径。
- `mod_database_core.py`：共享常量、数据模型、SQLite schema、迁移辅助、时间戳和 metadata 工具。
- `mod_database_queries.py`：数据库状态、zipmod/物品列表、筛选项、GUID 查找和 zipmod 导出等读写边界较轻的查询/导出接口。
- `mod_database_assets.py`：zipmod 扫描、manifest/CSV 解析、Unity3D 引用诊断、缩略图提取、CSV/zip 写回、模组修复和删除类操作。
- `card_library.py`：读取 `UserData/chara` 目录树、过滤 AIS PNG、生成标准化人物卡预览。
- `plugin_library.py`：扫描 BepInEx DLL 元数据，并将带有效 GUID 的结果缓存到同一个 SQLite 文件。
- `model_preview.py`：读取 item 的 MainAB，生成运行时 GLB 或静态 FBX。
- `achievements.py`：维护本地成就表，不参与资源索引。
- `sims4_workbench.py`：调度 Sims 4 Package 的 LOD0 FBX/PNG 导出和可选 Blender T-Pose 固化。
- `mod_workflow.py`：执行人物卡依赖搜索、模组提取和整理任务。
- `bridge.py`：管理异步任务状态，把 HTTP `POST /tasks` 映射到业务服务。

## 当前实现边界

当前已经实现：

- 从 `manifest.xml` 建立 zipmod 主索引，并把重复 GUID 放入 `duplicate_zipmods`。
- 从 CSV 实际数据行建立 `mod_items`，记录解析、缩略图和 MainAB Unity3D 状态。
- 统计 zipmod 物品数、Unity3D 汇总、缩略图问题和角色卡依赖使用关系。
- 支持 GUID、名称、作者、物品名称、Kind、状态和使用关系查询。
- 单个坏 zipmod、坏 CSV 或不可读资源只记录错误，不中断整个扫描。
- 角色卡数据库、BepInEx 插件缓存和本地成就复用同一 SQLite 文件。

当前仍未实现或不作为数据库保证的能力：

- 通用内容哈希去重；变动检测仍以路径、文件大小和修改时间为主。
- AssetStudio helper 尚未成为主扫描路径；Unity3D 读取主要使用 UnityPy/内置诊断流程。
- 数据库不是源文件备份，也不保存完整 zipmod/PNG 二进制内容。

## Unity3D resource status

`mod_items` stores the resolved state of item main `.unity3d` resources:

```text
unity3d_status      in_mod / in_game / missing / error
unity3d_error       diagnostic details, such as the missing main resource path or game abdata fallback path
```

Status meanings:

- `in_mod`: the item main resource referenced by `MainAB` can be found inside the current zipmod under `abdata/`, or the item uses a direct resource-image fallback inside the zipmod.
- `in_game`: the item main resource referenced by `MainAB` is absent from the zipmod but found under the selected game directory's `abdata/`, and the main resource is not missing.
- `missing`: the item main resource referenced by `MainAB` cannot be found in either the zipmod or the selected game directory's `abdata/`.
- `error`: the item main resource exists but is not a usable Unity resource. The current implemented trigger is thumbnail extraction proving that the same `.unity3d` path is both `ThumbAB` and `MainAB`, and UnityPy cannot load usable resources from that file.

The item error/missing check uses `.unity3d` references from `MainAB` only. `MainManifest` is treated as the root for `MainAB`; if empty or `abdata`, the path resolves under `abdata/`. A missing or unreadable `ThumbAB` that is not also the `MainAB` path is a thumbnail issue only and must not set `unity3d_status = missing/error`.

### Item display status

The renderer maps each item row to one of these display states:

- `error`: `unity3d_status` is `missing` or `error`, or the CSV row parse status is not `ok`.
- `thumb`: the item is parsed and its main Unity3D resource is not missing/error, but `thumbnail_status` is empty or not `ready` / `ok`.
- `ready`: the item is parsed, its main Unity3D resource is usable, and `thumbnail_status` is `ready` / `ok`.

This means a missing `ThumbAB` bundle, missing `ThumbTex` asset, or unreadable thumbnail-only Unity3D bundle marks the item as `thumb`. It marks the item as `error` only when that bad thumbnail Unity3D path is also the item's `MainAB` path.

### Zipmod-level Unity3D summary

The same status is also summarized onto `zipmods` so the mod library can filter or apply actions without querying every item row:

```text
zipmods.unity3d_status          error / missing / in_game / in_mod / ''
zipmods.unity3d_in_mod_count    number of item rows whose unity3d_status is in_mod
zipmods.unity3d_in_game_count   number of item rows whose unity3d_status is in_game
zipmods.unity3d_missing_count   number of item rows whose unity3d_status is missing
zipmods.unity3d_error           first missing-resource diagnostics, joined for display
```

Summary priority is `error` > `missing` > `in_game` > `in_mod` > empty. This means a zipmod with any item main Unity3D error is marked `error`; otherwise, any missing `MainAB` resource marks it `missing`; otherwise, if any item depends on a main resource in game-directory `abdata`, it is marked `in_game`; otherwise it is `in_mod` when all item main resources are inside the zipmod.

`unity3d_missing_count` counts item rows whose main `MainAB` resource is missing. It does not count missing thumbnail-only `ThumbAB` resources; those are represented by thumbnail issue counts.

### Zipmod display and filter status

The renderer maps each zipmod row to a display state:

- `错误`: `scan_status` is `missing_manifest`, `invalid`, or `invalid_manifest`; or `unity3d_status` is `missing` / `error`; or `unity3d_missing_count > 0`.
- `警告`: author is empty; or `unity3d_status` is `in_game`; or `unity3d_in_game_count > 0`; or there are duplicate zipmods for the same GUID; or `thumbnail_issue_count > 0`.
- `正常`: `scan_status = ok` and no earlier error/warning condition matched.
- `读取失败`: `scan_status = error`.
- `已失效`: `scan_status = stale`.

Backend zipmod list filters use similar but not identical query groups:

- `status=normal`: `scan_status = ok`, author is present, no duplicate GUID, no thumbnail issue items, and `unity3d_status` is not `missing` / `in_game` / `error`.
- `status=abnormal`: any non-`ok` scan status, empty author, `unity3d_status` in `missing` / `in_game` / `error`, duplicate GUID, or thumbnail issue item.
- `status=warning`: empty author, `unity3d_status = in_game`, `unity3d_in_game_count > 0`, duplicate GUID, or thumbnail issue item.
- `status=error`: `scan_status = missing_manifest`, `unity3d_status = missing/error`, or `unity3d_missing_count > 0`.
- `status=read_error`: the zipmod scan cannot read a manifest GUID, including missing `manifest.xml`, invalid manifest XML, missing/empty `<guid>`, or unreadable/bad zip files. This replaces the older separate `missing_manifest` and `read_error` filter entries in the UI.
