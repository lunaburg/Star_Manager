# Star_Manager 前端 UI 架构

本文档记录前端 UI 的整体架构和实现基线；本目录的统一入口是[前端 UI 文档索引](README.md)。仓库不再维护独立的静态预览 HTML；当前实现以 `apps/src/` 的 Vue 组件和 `apps/src/styles.css` 为准。

UI 架构按业务职责拆分为：

- [项目内容总览](../project-overview.md)：当前产品范围、运行架构、目录职责、前后端模块、数据模型、主要工作流、命令和开发规则。
- [主布局](main-layout.md)：应用外壳、全局导航、顶部栏、工作区区域、通用交互规则。
- [开始页布局](start-layout.md)：启动游戏、路径入口、游戏配置、管理器配置、高风险操作策略。
- [工作台](workbench-layout.md)：模组工程、CSV 物品、Unity3D 模板选择、MainData 预处理、资源写入，以及保留的 Sims 4 工具边界。
- [插件管理布局](plugins-layout.md)：BepInEx 插件扫描、元数据、依赖、缓存和单插件启停。
- [设置页布局](settings-layout.md)：启动行为、自动检查、本地成就、导出偏好、收藏主题和外部工具配置。
- [角色卡库布局](character-cards-layout.md)：`UserData/chara` 目录树、人物卡网格、批量选择、依赖提取。
- [Zipmod 库布局](zipmod-library-layout.md)：本地 zipmod 索引浏览、筛选、表格、详情抽屉、诊断与修复。
- [总览页布局](overview-layout.md)：游戏目录概况、资源健康状态、最近任务、建议操作。
- [运行日志布局](runtime-log-layout.md)：运行日志面板、实时消息、筛选、复制与清空。
- [UI 风格规范](ui-style.md)：视觉方向、颜色、卡片、字体、控件、风险状态。
- [模组数据库设计](../mod_manage/mod_database_design.md)：`zipmods` 与 `mod_items` 两个本地索引库的来源、字段和扫描流程。
- [模组异常分类](../mod_manage/mod_exception_catalog.md)：模组诊断类型、触发条件和当前修复入口。

核心产品假设：

- Star_Manager 应从单页任务控制台演进为面向 HS2 游戏目录的资源库浏览器。
- 默认资源来源是用户选择并校验通过的 HS2 游戏目录。
- 角色卡按 `UserData/chara` 目录树分组；后端会兼容大小写目录名，并忽略根级 `navi` 目录。
- Zipmod 通过本地索引表管理。
- `Copy` 是安全默认值。任何会修改游戏目录的操作都必须显示高风险提示，并要求用户明确二次确认。

当前实现基线：

- Electron preload 暴露目录选择、PNG/Package 文件选择、设置读写、游戏启动、打开文件所在目录和 `backendRequest`。
- 后端是本地 HTTP 服务，默认端口 `8765`，支持 `/health` 返回当前 task type 和 API route 列表。
- 主布局使用 Vue `KeepAlive` 缓存页面实例，导航时只渲染当前页面；模组管理和人物卡浏览器返回时保留滚动位置及页面状态，插件、日志和设置不会误显示模组管理内容。
- 模组管理已经接入筛选、分页、缩略图、关联物品、诊断和部分修复动作。
- 角色管理已经接入目录树、当前目录卡片列表和标准化卡片预览。
- 开始页的游戏启动和 `setup.xml` 配置读写都走 Electron IPC；配置保存包含 `.bak` 备份、原子写回和 Unity 注册表同步。

当前预览基线：

- 应用外壳由左侧导航、顶部全局栏和主工作区组成。
- 左侧品牌为 `Star_Manager / HS2 resource desk`，导航顺序为开始游戏、总览、卡片管理、模组管理、插件管理、工作台、运行日志、回收站，设置固定在底部；卡片管理项右侧展示人物卡、服装卡、场景卡三个互斥 SVG 类型按钮，点击后切换对应子界面。
- 侧栏只保留品牌和主导航，不固定显示安全上下文，也不放“导出诊断信息”入口。
- 顶部全局栏包含 HS2 目录选择、当前目录路径、目录有效状态、后台任务进度、后端状态和单一“重建数据库”入口。
- 角色管理页使用“人物卡浏览器 + 卡片目录”双栏；人物卡浏览器标题栏提供当前目录刷新按钮，筛选、多选和批量操作仍属于下方工具栏，低频操作不堆叠到标题栏。
- 服装卡使用 `UserData/coordinate` 下的独立目录扫描和 `clothes_card_index.sqlite` 增量索引，场景卡目前仍只显示 `UserData/studio/scene` 的占位浏览工作区。
