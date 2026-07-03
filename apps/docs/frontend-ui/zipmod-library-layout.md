# Zipmod 库布局

## 目标

Zipmod 库通过本地索引浏览、诊断和整理所选 HS2 游戏目录中的 `mods/**/*.zipmod`。

这个页面不是普通文件列表，而是面向大资源库的本地模组管理工作台。默认体验应优先支持快速扫读、错误定位、重复 GUID 处理和安全整理。

真实数据仍然来自文件系统、`manifest.xml` 和 CSV。前端读取后端索引中的 `zipmods` 主表，并在选中模组时展示关联的 `mod_items`、解析诊断和文件位置。

## 信息来源

### `zipmods`

模组级主索引，来自 `manifest.xml` 和 zipmod 文件属性。

推荐用于列表和详情的字段：

- `id`：数据库 ID。
- `guid`：manifest GUID，业务定位优先使用它。
- `name`：mod 名称。
- `author`：作者。
- `version`：版本。
- `item_count`：该 zipmod 中解析出的物品总数。
- `scan_status`：`ok`、`missing_manifest`、`invalid_manifest`、`read_error`、`stale`。
- `scan_error`：扫描错误原因。
- `unity3d_status`：`in_mod`、`in_game`、`missing` 或空值。
- `unity3d_in_mod_count`、`unity3d_in_game_count`、`unity3d_missing_count`：资源状态汇总。
- `duplicate_zipmod_count`：同 GUID 重复文件数量。
- `file_name`：zipmod 文件名。
- `relative_path`：相对 `mods/` 的路径。
- `file_path`：完整路径。
- `last_scanned_at`：最近扫描时间。

### `mod_items`

物品级索引，来自 zipmod 或解包目录内的 `abdata/list/**/*.csv`。

选中 zipmod 后可展示：

- `item_id`：CSV 中的 `ID`。
- `name`：游戏内物品名。
- `kind`：物品类别数字，展示时映射为中文分类。
- `csv_path`：来源 CSV。
- `thumbnail_cache_path`：缩略图缓存路径。
- `thumbnail_status`：`ready`、`missing`、`error`。
- `unity3d_status`：物品引用的 `.unity3d` 是否在 zipmod 内、游戏目录中或缺失。
- `parse_status`：`ok`、`missing_header`、`short_row`、`parse_error`。

## 浏览模式

模组管理页必须支持两种浏览模式：

- 模组浏览：默认模式，以 `zipmods` 为主表，帮助用户按 zipmod 包处理状态、路径和诊断。
- 物品浏览：以 `mod_items` 为主表，帮助用户按游戏内物品查找来源模组。

浏览类型使用顶部 segmented control：

```text
[物品浏览] [模组浏览]
```

浏览类型 tab 与详情抽屉 tab 使用同一套经典页签样式：淡蓝和浅粉渐变、顶部圆角、细描边、底部基线；当前项像抬起的标签页，使用白底和深色细描边标识。

浏览类型行右侧放人物卡依赖筛选滚轮，用于按角色卡依赖关系筛选当前浏览模式，选项为 `已使用`、`未使用`、`全部`。该控件必须可横向滚动，避免挤压浏览类型 tab；不在这里放刷新列表按钮，避免和数据库重建、筛选变化触发的刷新行为重复。若后续确实需要导出清单等低频操作，可放置轻量图标按钮，并提供 `title` / `aria-label`，避免和下方筛选工具栏混在一起。

切换浏览类型时必须同步切换：

- 左侧筛选控件。
- 主表格列。
- 当前选中记录。
- 右侧详情抽屉的标题、状态 badge、内容结构，以及详情 tab 内的操作入口。

物品浏览选中的是 `mod_items` 记录，详情抽屉显示物品信息和来源模组。模组浏览选中的是 `zipmods` 记录，详情抽屉显示模组信息、关联物品和诊断信息。列表不会默认选中第一行；未选中对象时详情抽屉显示“请选择一个对象”。

文件定位类操作跟随对应记录展示。模组详情的“所在文件夹”信息栏本身是可点击控件，不显示路径文本；点击后通过 Electron `shell.showItemInFolder` 打开资源管理器并选中对应 `.zipmod` 文件。

## 总体布局

模组管理页使用“资源库表格 + 常驻同步详情抽屉”的双栏布局：

```text
+------------------------------------------------------+----------------------+
| 模组管理                                             | 同步详情抽屉          |
| 8,214 zipmod · 142,309 items · 17 errors · 6 dupes   | 当前选中记录          |
| [物品浏览] [模组浏览]                                | 物品详情或模组详情     |
| [按当前模式显示筛选项]              [排序] [扫描]     | 基础信息              |
|------------------------------------------------------| 文件位置              |
| 当前模式表格                                         | 解析诊断              |
| ...                                                  | 详情 tab 内操作        |
+------------------------------------------------------+----------------------+
```

左侧主区域服务于大批量扫读和筛选。右侧详情抽屉保持打开，随浏览模式和选中行更新，避免频繁弹窗打断浏览。

详情抽屉建议宽度为 `380-420px`。两种浏览模式都使用表格作为主视图，以适配超大资源库的精确扫读和排序。

## 模块标题栏

标题栏展示：

- 页面标题：`模组管理`。
- 页面说明：`在物品浏览和模组浏览之间切换，筛选项随浏览类型收窄。`
- 扫描摘要：
  - zipmod 数量。
  - 物品总数。
  - 解析错误数量。
  - 重复 GUID 数量。
  - 最近扫描时间。

示例：

```text
8,214 zipmod · 142,309 items · 17 errors · 6 dupes · last scan 20:52
```

错误数量、重复 GUID 数量可作为快捷筛选入口。

## 工具栏

工具栏分为模式切换、筛选区和通用操作区。

### 物品浏览筛选

物品浏览只显示四类检索入口：

- Kind：按 `mod_items.kind` 映射后的类别筛选。
- 作者：按 `mod_items.zipmod_author` 或来源 `zipmods.author` 筛选。
- 状态：当前支持 `ready`、`parse`、`thumb`，分别对应可展示、CSV 解析失败、缩略图缺失或错误。
- 搜索物品名字：按 `mod_items.name`、`item_id` 或 `zipmod_guid` 搜索。

物品浏览工具栏应使用稳定网格布局：搜索框占较大宽度，Kind、作者、状态三个下拉控件使用较窄且一致的宽度。所有控件必须设置 `min-width: 0` 或等效约束，避免下拉控件撑出父容器。

### 模组浏览筛选

模组浏览只显示两类检索入口：

- 作者：按 `zipmods.author` 筛选。
- 状态：当前支持 `normal` 和 `abnormal`。`abnormal` 包含非 `ok` 扫描状态、`.unity3d` 缺失或只存在于游戏目录、以及重复 GUID。

### 通用操作

两个模式都可以保留：

- 排序。
- 密度。

排序和密度控件应放在右侧紧凑操作组中，宽度受控，不应挤压或溢出主筛选组。

重建数据库入口放在全局顶部栏。刷新、导出等低频操作优先放到对应模块工具栏，不占用物品/模组检索工具栏；打开目录跟随详情抽屉中的文件位置展示。仅图标按钮必须提供 tooltip。

## 物品表格

物品浏览推荐表格列：

- 状态。
- 缩略图。
- 物品名。
- Kind。
- 作者。
- 来源模组。

展示规则：

- 缩略图列放在物品名之前，使用固定尺寸小图或稳定占位图；表格缩略图不使用黑色描边，避免和按钮/卡片控件混淆。
- 标准密度下物品列表行高建议不低于 `60px`，表格缩略图建议为 `46px` 固定尺寸，并保留至少 `6px` 上下内边距，确保图片不触碰行的上下边界。
- 物品名是主要扫读字段，列宽应优先保证。
- Kind 展示中文映射，同时保留原始数字可放 tooltip 或详情抽屉。
- 作者来自来源 zipmod。
- 来源模组可点击或双击切到模组浏览并选中对应 zipmod。
- `thumbnail_status` 和 `parse_status` 以 badge 显示。
- `thumbnail_status = ready` 时显示缓存缩略图；`missing` 或 `error` 时显示带文字的占位图，不让行高跳动。

当前加载策略：

- 进入物品浏览时先调用 `GET /mods/database`。
- 数据库不存在时不加载表格，提示创建数据库。
- 数据库存在时首批调用 `GET /mods/items?offset=0&limit=500`。
- 表格滚动接近底部后继续按 500 条加载。
- Kind 数字在前端映射为中文类别，例如 `351` 显示为 `饰品 mod / 头部`；未知 Kind 保留原始值。

物品详情抽屉展示：

- 物品名、Kind、作者、状态。
- 来源模组名称、完整 GUID、来源 CSV。
- 同模组物品预览。
- 可进入来源模组详情。

## Zipmod 表格

模组浏览推荐表格列：

- 状态。
- 名称。
- 作者。
- 版本。
- 物品数。
- 相对路径。
- GUID。
- 最近扫描。

展示规则：

- `scan_status = ok` 显示绿色或普通 `正常` badge。
- `missing_manifest`、`invalid_manifest`、`read_error` 显示琥珀或红色诊断 badge。
- `stale` 显示灰色 `已失效` badge。
- 重复 GUID 显示 `重复 GUID` badge，即使主记录本身可解析。
- GUID、路径和错误码使用等宽字体。
- GUID 在表格中可截断，详情抽屉显示完整值。
- 当前选中行使用浅粉或浅蓝背景，不增加额外粗边框。
- `item_count = 0` 不一定是错误，但应在详情诊断中说明可能原因。

表格交互：

- 单击行后选中该对象并更新右侧详情抽屉。
- 未选中对象时，右侧详情抽屉只显示“请选择一个对象”。
- 双击物品行可定位来源模组。
- 双击模组行可进入详情抽屉的 `物品` tab 或展开关联物品。
- 点击状态 badge 可筛选同类状态。
- 文件路径不在表格内展示。模组详情中的“所在文件夹”信息栏用于打开资源管理器并选中 zipmod 文件。

## 数据加载

模组管理页依赖本地 SQLite 索引，不直接扫描文件系统列表。

当前接口：

```text
GET /mods/database
GET /mods/zipmods?offset=0&limit=200&author=&status=&usage=
GET /mods/zipmods/authors
GET /mods/zipmods/<id>/manifest
GET /mods/zipmods/<id>/diagnostics
GET /mods/items?offset=0&limit=500&search=&kind=&author=&status=&usage=
GET /mods/items?zipmod_id=<zipmod_id>&offset=0&limit=1000
GET /mods/items/filters
GET /mods/thumbnails?path=<encoded_thumbnail_cache_path>
```

加载规则：

- 进入模组浏览或物品浏览前先检查数据库。
- 数据库不存在时不加载列表，提示创建数据库。
- 模组浏览首批 200 条，滚动到底部附近继续加载。
- 物品浏览首批 500 条，滚动到底部附近继续加载。
- 模组详情的物品 tab 按当前 `zipmods.id` 查询关联物品。
- 缩略图通过后端缩略图接口加载，前端不直接读取本地文件路径。
- 筛选项来自 `/mods/zipmods/authors` 和 `/mods/items/filters`；空作者在前端展示为 `未知作者`。

## 详情抽屉

详情抽屉随浏览模式同步切换。

物品浏览详情抽屉使用 tab：

```text
详情 | 工具
```

模组浏览详情抽屉使用 tab：

```text
详情 | 物品 | 诊断
```

详情抽屉内的 tab 使用轻量分段样式。当前 tab 可用浅底色、细边框或底部强调线区分，但不使用全局主按钮的粗描边、实体投影和按压位移。

### 物品详情

分组展示：

- 标题区：大缩略图、物品名、Kind、作者、状态 badge。
- 来源模组：mod 名称、完整 GUID、来源 CSV。
- 同模组物品：展示少量关联物品，方便横向浏览。
- 工具 tab：当前放置定位来源模组、导入/重建缩略图、删除物品等操作。导入缩略图会要求选择 PNG 文件。

### 模组详情

分组展示：

- 标题区：mod 名称、作者、版本、状态 badge。
- 基础信息：数据库 ID、完整 GUID、物品数、最近扫描时间。
- 文件位置：文件名，以及可点击的“所在文件夹”信息栏。
- 当前实现中详情信息栏使用紧凑布局，值紧跟标题显示，以便展示更多 GUID、文件名和时间信息。“所在文件夹”不显示路径，整条信息栏作为打开目录入口。

高风险整理操作不放在详情抽屉内。后续如重新加入移动、删除或在原目录整理，必须走独立高风险确认流程。

### 模组物品 tab

展示选中 zipmod 的 `mod_items` 摘要。当前实现使用：

```text
缩略图 | 物品名 | Kind 分类 | 状态
```

缩略图规则：

- `thumbnail_status = ready` 显示缓存图。
- `missing` 或 `error` 显示稳定占位图。
- 失败原因放到诊断 tab 或 tooltip，不阻塞物品列表。
- 模组物品 tab 只展示关联物品信息，不显示重新扫描、打开目录、复制 GUID、整理、删除等操作控件。
- 关联物品列表不显示 item ID，副信息只显示 Kind 中文分类，避免类别被截断。

### 诊断 tab

展示：

- `scan_status` 和 `scan_error`。
- CSV 解析状态摘要。
- 缩略图提取状态摘要。
- 重复 GUID 信息。
- stale 记录说明。
- 当前实现中诊断 tab 也承载对应的修复动作：补作者、选择缩略图、清理重复模组、补入 zipmod，以及在满足后端条件时删除模组。

如果存在重复 GUID，必须展示主记录和重复文件：

```text
主记录：mods/Sideloader/roy12/aiko.zipmod
重复文件：
- mods/_old/roy12/aiko.zipmod · 1.2.0 · 48 MB · 2025-12-09
- mods/downloads/aiko.zipmod · 1.3.0 · 51 MB · 2026-01-03
```

重复文件不应被静默忽略，也不应直接合并到主记录的 `mod_items`。
## 风险操作

安全默认模式为 `Copy`。任何会修改游戏目录的操作都必须进入高风险确认流程，包括：

- 移动 zipmod。
- 删除 zipmod 或重复文件。
- 在原目录整理文件。
- 批量改名。

高风险确认必须展示：

- 将要改变什么。
- 影响文件数。
- 源路径和目标路径。
- 是否可逆。
- 更安全的替代操作。
- 具体确认按钮文案。

按钮文案示例：

```text
确认移动 12 个 zipmod
确认删除 3 个重复 zipmod
确认整理游戏目录中的文件
```

不要使用 `OK`、`Yes`、`确定` 这类泛化确认文案。

## 空状态

空状态必须具体：

- 未选择 HS2 目录：展示目录选择入口和预期目录结构。
- 未建立索引：展示扫描 `mods/**/*.zipmod` 的操作。
- 搜索无结果：显示当前搜索词和清除筛选操作。
- 后端不可用：禁用后端操作，显示重试入口。
- 选中 zipmod 但无物品：说明可能是无 CSV、CSV 解析失败或该 zipmod 不是物品类模组。

## 数据需求

当前接口：

```text
GET  /mods/database
GET  /mods/zipmods?offset=&limit=&author=&status=&usage=
GET  /mods/zipmods/authors
GET  /mods/zipmods/:id/diagnostics
GET  /mods/items?offset=&limit=&search=&kind=&author=&status=&usage=
GET  /mods/items/filters
GET  /mods/items?zipmod_id=&offset=&limit=
GET  /mods/thumbnails?path=
POST /tasks { task_type: "build_mod_database" }
GET  /tasks/:task_id
POST /mods/zipmods/:id/repair-unity3d
POST /mods/zipmods/:id/update-author
POST /mods/zipmods/:id/manifest
POST /mods/zipmods/:id/cleanup-duplicates
POST /mods/zipmods/:id/delete
POST /mods/items/:id/import-thumbnail
POST /mods/items/:id/delete
```

