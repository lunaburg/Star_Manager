# 插件管理布局

## 目标

插件管理用于只读浏览所选 HS2 游戏目录中的 BepInEx 插件程序集，帮助用户确认插件身份、版本、依赖和解析异常。它不执行 DLL，也不修改游戏目录。

## 当前页面

页面入口是左侧“插件管理”，使用“插件列表 + 右侧详情”双栏结构：

- 工具栏提供名称/GUID/DLL 搜索和“打开 BepInEx 目录”。
- 首次进入页面或游戏目录变化时自动扫描；当前界面没有独立的强制重扫按钮。
- 列表显示插件名、版本、类型和状态；前端会保留当前选中项。
- 详情显示相对路径、功能说明、插件 GUID/版本、BepInEx 依赖、适用进程和解析诊断。
- 空状态区分未选择游戏目录、准备扫描、没有匹配结果和扫描失败。

类型标签来自扫描区域：`plugin`、`patcher`、`core`。当前扫描结果只把成功解析出非空 `BepInPlugin` GUID 的 DLL 纳入插件库；普通依赖程序集不会出现在列表中。

## 后端扫描规则

`GET /plugins?game_dir=&search=&category=&offset=&limit=` 扫描 `BepInEx/Plugins`、`BepInEx/patchers` 和 `BepInEx/core` 下的 DLL，但只读取 .NET 元数据，不加载或执行程序集。

返回内容包括：

- assembly 名称和版本；
- BepInEx 插件 GUID、名称和版本；
- 功能描述、描述来源、置信度和证据；
- BepInEx 依赖、适用进程、不兼容项和程序集引用；
- 文件路径、大小、修改时间和元数据错误；
- 总数、各类别数量、解析失败数、重复 GUID 数和带描述/依赖的数量。

插件描述优先使用程序集自带描述，其次使用已知插件目录；必要时结合 `config/*.cfg` 和 `Translation/**/*.txt` 进行补充。重复 GUID 显示为诊断状态，不自动合并。

## 缓存

扫描结果复用主 SQLite 文件中的 `bepinex_plugin_cache` 表。缓存指纹包含插件 DLL、配置和翻译文件；文件大小或修改时间发生变化时自动失效。后端支持 `refresh=1` 强制重扫，供后续 UI 或排障使用。

## 当前边界

- 页面当前只读，不提供启用、禁用、删除或编辑插件的操作。
- 插件描述不是插件运行时行为分析，不能替代 BepInEx 日志。
- 所选目录无效或没有 `BepInEx` 文件夹时，后端返回错误并由页面显示重试入口。

## 相关代码和接口

- `apps/src/components/views/PluginsView.vue`
- `apps/backend/star_manager/services/plugin_library.py`
- `apps/backend/app/server.py`：`GET /plugins`
- `apps/backend/star_manager/services/mod_database_core.py`：`bepinex_plugin_cache` schema
