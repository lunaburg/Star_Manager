# Star_Manager 文档索引

本文档是 `apps/docs/` 的统一入口。先按“快速入口”建立项目全貌，再根据任务进入对应专题。接口和任务列表以当前代码为准；文档中明确标注“后续”或“未接入”的内容不代表当前可用功能。

## 快速入口

| 你想了解什么 | 先读 | 内容 |
| --- | --- | --- |
| 这个项目是什么、用户怎么开始用 | [项目介绍](project-introduction.md) | 产品定位、页面导览、首次使用流程、数据边界和当前限制 |
| 项目整体结构和当前边界 | [项目总览](project-overview.md) | 产品范围、运行链路、目录职责、数据模型、工作流和开发规则 |
| 前后端怎么通信 | [前后端接口](backend-interface.md) | Electron preload、HTTP 路由、任务协议、请求字段和单项/批量边界 |
| 前端页面怎么组织 | [前端 UI 架构](frontend-ui/frontend-ui-architecture.md) | 页面索引、应用外壳、实现基线和视觉假设 |
| 如何运行、构建和打包 | [Windows 打包指南](packaging-windows.md) | 开发命令、PyInstaller、electron-builder、产物检查和运行时后端选择 |

## 按功能查找

### 前端页面

| 页面/主题 | 文档 | 当前实现重点 |
| --- | --- | --- |
| 应用外壳 | [主布局](frontend-ui/main-layout.md) | 全局导航、顶部目录状态、数据库重建、共享上下文 |
| 开始游戏 | [开始页布局](frontend-ui/start-layout.md) | HS2 目录选择、三种启动入口、目录快捷入口；`setup.xml` 编辑目前仍是占位状态 |
| 总览 | [总览页布局](frontend-ui/overview-layout.md) | 人物卡/模组/物品摘要、建议操作、最近任务、本地成就 |
| 角色管理 | [角色卡库布局](frontend-ui/character-cards-layout.md) | 目录树、卡片、详情、依赖、标签、收藏、批量操作和导出 |
| 收藏视觉 | [人物卡收藏视觉状态](frontend-ui/character-card-favorite-effects.md) | 收藏主题、铭牌、边框、名字溢出和设置持久化 |
| 模组管理 | [Zipmod 库布局](frontend-ui/zipmod-library-layout.md) | 物品/模组浏览、筛选、分页、诊断、模型预览和安全维护 |
| 插件管理 | [插件管理布局](frontend-ui/plugins-layout.md) | BepInEx DLL 扫描、元数据、依赖、缓存和诊断 |
| 工作台 | [工作台布局](frontend-ui/workbench-layout.md) | Sims 4 Package → LOD0 FBX、RLE2 贴图和可选 Blender T-Pose 固化 |
| 运行日志 | [运行日志布局](frontend-ui/runtime-log-layout.md) | 本地日志数组、任务轮询消息、清空和复制占位操作 |
| 设置 | [设置页布局](frontend-ui/settings-layout.md) | 启动页面、启动检查、成就、导出目录、便携包和 Blender 路径 |
| 视觉规范 | [UI 风格规范](frontend-ui/ui-style.md) | 颜色、控件、卡片、风险状态和响应式原则 |

### 后端和数据

| 主题 | 文档 | 适用场景 |
| --- | --- | --- |
| 模组数据库 | [模组数据库设计](mod_manage/mod_database_design.md) | SQLite 表、字段、状态、扫描和查询边界 |
| 增量建库 | [数据库变动检测](mod_manage/mod_database_change_detection.md) | 新增/移除/修改、重复 GUID、stale 和角色卡依赖重连 |
| 角色卡二进制 | [角色卡解析说明](mod_manage/character_card_parsing.md) | PNG 尾部、MessagePack、UniversalAutoResolver、人物参数和坐标卡导出 |
| 模组异常 | [模组异常分类](mod_manage/mod_exception_catalog.md) | 诊断类型、触发条件和当前修复入口 |
| 标准模组结构 | [标准模组结构记录](mod_manage/standard_mod_structure_record.md) | manifest、CSV、Unity3D 引用和缩略图来源 |

### 集成和排障

| 主题 | 文档 | 适用场景 |
| --- | --- | --- |
| 人物卡元数据插件 | [Card metadata 插件](card-metadata-plugin.md) | `KKEx` 注册数据、游戏保存覆盖规则、编译和安装 |
| Unity3D 修复记录 | [Unity3D 解密与修复](unity3d-decryption-notes.md) | UnityFS 异常、二次保护、脚本边界和隔离验证 |
| AssetStudio helper | [AssetStudio helper](assetstudio-helper.md) | C# 子进程协议和未来 Unity 资源集成 |
| Windows 打包 | [Windows 打包指南](packaging-windows.md) | 发布目录、后端 exe、依赖检查和已知警告 |

## 按任务查找

| 任务 | 需要同时阅读 |
| --- | --- |
| 增加或修改 HTTP 路由/任务 | [前后端接口](backend-interface.md) + [项目总览](project-overview.md) |
| 修改模组扫描、状态或增量重建 | [模组数据库设计](mod_manage/mod_database_design.md) + [数据库变动检测](mod_manage/mod_database_change_detection.md) |
| 修改角色卡解析、依赖或导出 | [角色卡解析说明](mod_manage/character_card_parsing.md) + [角色卡库布局](frontend-ui/character-cards-layout.md) |
| 修改收藏、评分或标签 | [Card metadata 插件](card-metadata-plugin.md) + [人物卡收藏视觉状态](frontend-ui/character-card-favorite-effects.md) |
| 修改 Sims 4 / Unity3D 资源流程 | [工作台布局](frontend-ui/workbench-layout.md) + [Unity3D 解密与修复](unity3d-decryption-notes.md) |
| 修改页面结构或样式 | [前端 UI 架构](frontend-ui/frontend-ui-architecture.md) + 对应页面文档 + [UI 风格规范](frontend-ui/ui-style.md) |
| 生成 Windows 发行目录 | [Windows 打包指南](packaging-windows.md) |

## 文档维护规则

- 面向新用户的产品行为、页面职责和当前限制优先维护在[项目介绍](project-introduction.md)；面向开发者的架构、接口和数据细节维护在对应专题文档中。
- 新增文档时先更新本索引，再在根目录 `AGENTS.md` 的项目文档清单中补充入口。
- 文档描述“当前实现”时，应能在 `apps/backend/app/server.py`、`apps/backend/app/bridge.py`、`apps/src/` 或 `apps/electron/` 找到对应代码；规划内容单独标为“后续/未接入”。
- HTTP 路由、任务类型和 payload 的详细契约只维护在 [前后端接口](backend-interface.md)；其他专题只保留与页面或业务相关的摘要，避免出现多份互相矛盾的清单。
- `apps/backend/runtime/`、`apps/dist/`、`apps/build/`、`apps/release/` 和提取结果目录属于运行时或构建产物，不作为维护文档入口。

## 辅助 README

- [应用 README](../README.md)：从 `apps/` 目录运行项目时的快速说明。
- [Card metadata plugin README](../tools/star-manager-card-metadata-plugin/README.md)：插件验证、编译和安装命令。
- [AssetStudio helper README](../tools/assetstudio-helper/README.md)：C# helper 的命令行示例和 JSON 输出约定。
