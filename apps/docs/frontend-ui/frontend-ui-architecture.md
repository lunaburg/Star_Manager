# Star_Manager 前端 UI 架构

本文档是拆分后的前端 UI 架构文档入口。当前静态预览基线见 [frontend-ui-preview.html](frontend-ui-preview.html)。

UI 架构按业务职责拆分为：

- [项目内容总览](../project-overview.md)：当前产品范围、运行架构、目录职责、前后端模块、数据模型、主要工作流、命令和开发规则。
- [主布局](main-layout.md)：应用外壳、全局导航、顶部栏、工作区区域、通用交互规则。
- [开始页布局](start-layout.md)：启动游戏、路径入口、游戏配置、管理器配置、高风险操作策略。
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

- Electron preload 暴露目录选择、PNG 选择、设置读写、游戏启动、打开文件所在目录和 `backendRequest`。
- 后端是本地 HTTP 服务，默认端口 `8765`，支持 `/health` 返回当前 task type 和 API route 列表。
- 模组管理已经接入筛选、分页、缩略图、关联物品、诊断和部分修复动作。
- 角色管理已经接入目录树、当前目录卡片列表和标准化卡片预览。
- 开始页的游戏启动走 Electron IPC，`setup.xml` 编辑仍是界面状态和后续能力。

当前预览基线：

- 应用外壳由左侧导航、顶部全局栏和主工作区组成。
- 左侧品牌为 `Star_Manager / HS2 resource desk`，导航顺序为开始游戏、总览、角色管理、模组管理、运行日志。
- 侧栏只保留品牌和主导航，不固定显示安全上下文，也不放“导出诊断信息”入口。
- 顶部全局栏包含 HS2 目录选择、当前目录路径、目录有效状态、后台任务进度、后端状态和单一“重建数据库”入口。
- 角色管理页使用“人物卡浏览器 + 卡片目录”双栏，不在人物卡浏览器标题栏右侧放刷新、视图或更多按钮；这些操作属于下方工具栏或全局栏。
