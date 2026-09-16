# Star_Manager 文档索引

本文档是 `apps/docs/` 的统一入口。先按“快速入口”建立项目全貌，再根据任务进入对应专题。接口和任务列表以当前代码为准；文档中明确标注“后续”或“未接入”的内容不代表当前可用功能。

## 分级目录

`apps/docs/` 按以下层级组织。具体专题目录拥有自己的二级索引，专题文档不再需要记忆全部文件名：

1. [产品与项目总览](project-introduction.md) / [项目总览](project-overview.md)
2. [截图页面概览](page-overview-from-screenshots.md)：按截图顺序快速了解各个用户页面
3. [运行时架构图](runtime-architecture.html)（源规格：[runtime-architecture.json](runtime-architecture.json)）
4. [前端 UI 专题索引](frontend-ui/README.md)：应用外壳、页面布局和视觉规范
5. [模组与资源专题索引](mod_manage/README.md)：数据库、角色卡解析、变更检测和异常诊断
6. [接口与运行时](backend-interface.md) / [缓存与运行时文件登记](runtime-cache-registry.md)
7. [集成、排障与发布](#集成和排障)：插件、AssetStudio、SB3UtilityScript、Unity3D 修复和 Windows 打包

推荐阅读路径：

```text
首次了解项目
  -> 项目介绍
  -> 项目总览
  -> 对应专题索引
  -> 具体实现文档

准备修改代码
  -> 项目总览
  -> 前后端接口 / 缓存登记
  -> 前端 UI 或模组与资源专题索引
  -> 相关页面、服务或排障文档
```

## 快速入口

| 你想了解什么 | 先读 | 内容 |
| --- | --- | --- |
| 模组 Unity3D 解密与修复 | [项目内 skill](../skills/mod-unity3d-decryption/SKILL.md) | 按已验证 profile 诊断、恢复和验证受保护 Unity3D 资源 |
| 这个项目是什么、用户怎么开始用 | [项目介绍](project-introduction.md) | 产品定位、页面导览、首次使用流程、数据边界和当前限制 |
| 想按截图快速了解每个页面 | [截图页面概览](page-overview-from-screenshots.md) | 根据 9 张页面截图，按时间顺序说明页面外观、入口和粗略用途 |
| 项目整体结构和当前边界 | [项目总览](project-overview.md) | 产品范围、运行链路、目录职责、数据模型、工作流和开发规则 |
| 运行时组件、主路径和信任边界 | [运行时架构图](runtime-architecture.html) | Electron/Vue/Python/SQLite 主链路、HS2 与资源工具外部边界；源规格见 [runtime-architecture.json](runtime-architecture.json) |
| 前后端怎么通信 | [前后端接口](backend-interface.md) | Electron preload、HTTP 路由、任务协议、请求字段和单项/批量边界 |
| 前端页面怎么组织 | [前端 UI 专题索引](frontend-ui/README.md) | 页面索引、应用外壳、实现基线和视觉假设 |
| 应用缓存和运行时文件在哪里 | [缓存与运行时文件登记](runtime-cache-registry.md) | 后端缓存、SQLite 索引、前端缓存、回收站、临时与派生运行时文件、清理边界和开发缓存 |
| 删除的卡片和模组在哪里 | [回收站](trash-recycle-bin.md) | runtime/trash 目录结构、恢复、永久删除、测试残留隔离和索引恢复行为 |
| 如何运行、构建和打包 | [Windows 打包指南](packaging-windows.md) | 开发命令、PyInstaller、electron-builder、产物检查和运行时后端选择 |
| Electron 启动与后端退出 | [Electron 进程生命周期](electron-process-lifecycle.md) | 单实例锁、Windows 后端进程树清理、退出等待和异常退出边界 |
| Electron 启动与后端退出 | [Electron 进程生命周期](electron-process-lifecycle.md) | 单实例锁、Windows 后端进程树清理、退出等待和异常退出边界 |

## 按功能查找

### 前端页面

| 页面/主题 | 文档 | 当前实现重点 |
| --- | --- | --- |
| 前端架构 | [前端 UI 架构](frontend-ui/frontend-ui-architecture.md) | 页面清单、实现基线和整体产品假设 |
| 应用外壳 | [主布局](frontend-ui/main-layout.md) | 全局导航、顶部目录状态、按实测耗时加权的数据库任务进度、数据库重建和共享上下文 |
| 开始游戏 | [开始页布局](frontend-ui/start-layout.md) | 三个一级容器移除外部边框；HS2 目录选择、后端就绪竞态恢复、目录校验任务、三种启动入口、固定与自定义目录快捷入口、六个固定插件开关和两个特殊设置；读写 `UserData/setup.xml`、备份和启动框架检测 |
| 总览 | [总览页布局](frontend-ui/overview-layout.md) | 四个一级容器移除外部边框；人物卡/模组/物品摘要、建议操作、最近任务、本地成就 |
| 卡片管理 | [角色卡库布局](frontend-ui/character-cards-layout.md) | 卡片管理页隐藏全局顶部栏并回收其布局高度；通过互斥 SVG 按钮切换人物卡、服装卡、场景卡子界面，其中三类卡片按钮使用资源目录图标；人物卡浏览器标题栏刷新按钮和普通卡名称铭牌使用透明玻璃样式，收藏卡使用暖色不透明铭牌；外部导入的人物卡归档到 `female/imported`；人物卡、服装卡和场景卡浏览器均采用宽窗口最多五列、缩小窗口优先四列的响应式虚拟网格，服装卡不显示额外搜索工具栏并复用人物卡的底部名称条和“目录/详情”tab；场景卡复用服装卡的目录、分页、虚拟网格和详情链路，预览比例为 `320:180`，关联页支持远端模组候选查询和安全安装；人物卡、服装卡和场景卡详情及关联页签控件统一为连续玻璃样式，工具页签四个工具卡移除图标并保留文字与操作按钮，底部增加可恢复的单卡删除工具，包含目录树、详情、依赖、标签、收藏、批量操作和导出 |
| 收藏视觉 | [人物卡收藏视觉状态](frontend-ui/character-card-favorite-effects.md) | 收藏主题、铭牌、边框、名字溢出和设置持久化 |
| 模组管理 | [Zipmod 库布局](frontend-ui/zipmod-library-layout.md) | 物品/模组浏览、轻模糊玻璃化物品列表/预览图与详情面板、多选操作栏与批量按钮玻璃化、增强表头磨砂层、Kind 分类玻璃控件过渡、全部 Kind 与视图切换统一背景、全部 Kind 下方的等尺寸无图标物品视图切换、筛选图标、分页、装配模式顶部角色选择器、诊断、模型预览、详情文件名定位、右键服饰/头发/面部/身体/饰品换装和安全维护 |
| 插件管理 | [插件管理布局](frontend-ui/plugins-layout.md) | BepInEx DLL 扫描、元数据、依赖、缓存、诊断和 `.dl_` 启停 |
| 工作台 | [工作台](frontend-ui/workbench-layout.md) | 模组工程、CSV 物品、Unity3D 模板选择、MainData 预处理和资源写入；另记保留的 Sims 4 Package → FBX 能力 |
| 运行日志 | [运行日志布局](frontend-ui/runtime-log-layout.md) | 隐藏全局顶部栏；本地日志数组、任务轮询消息、Electron 首屏里程碑，以及 `did-finish-load`/`ready-to-show`/`renderer-ready` 的首屏显示门槛诊断 |
| 设置 | [设置页布局](frontend-ui/settings-layout.md) | 启动页面、启动检查、数据库建库线程数、应用壁纸（图片/MP4）、成就、导出目录、便携包和 Blender 路径 |
| 视觉规范 | [UI 风格规范](frontend-ui/ui-style.md) | 颜色、控件、卡片、界面文字极简原则、风险状态和响应式原则 |

### 后端和数据

| 主题 | 文档 | 适用场景 |
| --- | --- | --- |
| 模组数据库 | [模组数据库设计](mod_manage/mod_database_design.md) | SQLite 表、字段、状态、扫描和查询边界 |
| 建库性能基准 | [模组数据库建库性能基准](mod_manage/mod_database_build_benchmark.md) | 从现有数据库抽取 100 个 zipmod，拆分 ZIP 读取/解压、UnityPy 加载、缩略图写出和完整建库耗时 |
| 游戏原版资源索引 | [原版资源索引](mod_manage/builtin_resource_index.md) | 原版 `ChaListData` 列表、`builtin_items`、缩略图和 Coordinate 匹配 |
| 增量建库 | [数据库变动检测](mod_manage/mod_database_change_detection.md) | 新增/移除/修改、重复 GUID、stale 和角色卡依赖重连 |
| 角色卡二进制 | [角色卡解析说明](mod_manage/character_card_parsing.md) | PNG 尾部、MessagePack、UniversalAutoResolver、人物参数和坐标卡导出 |
| 服装卡样本解析 | [服装卡样本解析报告](mod_manage/clothes_card_sample_analysis.md) | 用户提供的 AIS_Clothes 样本结构、Coordinate 部件、UAR 依赖和 KKEx 插件摘要 |
| Studio 场景卡解析 | [Studio 场景卡解析说明](mod_manage/scene_card_parsing.md) | StudioNEOV2 场景数据、地图/物品/图案依赖、本地数据库匹配、远端候选查询和详情关联展示 |
| 模组异常 | [模组异常分类](mod_manage/mod_exception_catalog.md) | 诊断类型、触发条件和当前修复入口 |
| 标准模组结构 | [标准模组结构记录](mod_manage/standard_mod_structure_record.md) | manifest、CSV、Unity3D 引用、缩略图来源和外部 `.zip` 归一化 |
| Studio 模组样本解析 | [Hooh ammunition_go.zipmod 结构解析](mod_manage/hooh_ammunition_go_zipmod_analysis.md) | Studio `ItemCategory` / `ItemList`、AssetBundle prefab 映射和当前扫描边界 |
| Studio 姿势转 zipmod | [Studio 女性姿势转换](mod_manage/pose_zipmod_conversion.md) | `.dat` 女性姿势、Kind=501 CSV、Animator/AnimationClip 模板、骨骼路径映射和验证边界 |
| KK Animations ForMaker 补全 | [KK Animations ForMaker 注册补全](mod_manage/kk_animations_formaker_completion.md) | 从完整动画包读取全部 Studio 动画并注册到 Kind=501 姿势列表 |

### 集成和排障

| 主题 | 文档 | 适用场景 |
| --- | --- | --- |
| 人物卡元数据插件 | [Card metadata 插件](card-metadata-plugin.md) | `KKEx` 注册数据、游戏保存覆盖规则、编译和安装 |
| 游戏物品运行时探针 | [游戏物品运行时探针](game-item-probe.md) | `ChaListControl`、UniversalAutoResolver、localSlot、头发/面部/身体栏位与 zipmod/CSV 物品映射 |
| 人物卡读取到游戏 | [人物卡选择性读取](game-card-loading.md) | 使用现有 BepInEx 探针将人物卡的选定区块读取到当前角色制作器 |
| 独立人物卡读取审计探针 | [独立人物卡读取审计探针](character-card-read-probe.md) | 监听原生卡片读取、Harmony 插件介入、角色骨骼、Renderer、材质和贴图元数据 |
| SB3UtilityScript | [SB3UtilityScript 调用说明](sb3utility-script.md) | Unity3D 脚本调用、MainData/GameObject 修改、保存验证和 GUI 脚本兼容性 |
| Sims 4 FBX 灰黑块 | [FBX 灰黑块修复记录](sims4-fbx-gray-black-artifact-repair.md) | FBX 源模型切线/法线诊断、MikkTSpace 修复和验证边界 |
| Unity3D 修复记录 | [Unity3D 解密与修复](unity3d-decryption-notes.md) | UnityFS 异常、二次保护、已知明文/无原件恢复、57 字节包裹与内嵌资源流、wen 目标 profile、B002 三张流式纹理内嵌及 `.resS` 移除、对象关系和游戏运行时验证 |
| AssetStudio helper | [AssetStudio helper](assetstudio-helper.md) | C# 子进程协议和未来 Unity 资源集成 |
| Windows 打包 | [Windows 打包指南](packaging-windows.md) | 发布目录、后端 exe、依赖检查和已知警告 |

## 按任务查找

| 任务 | 需要同时阅读 |
| --- | --- |
| 增加或修改 HTTP 路由/任务 | [前后端接口](backend-interface.md) + [项目总览](project-overview.md) |
| 修改物品浏览筛选图标、右键换装、面部/身体栏位或装配模式 | [Zipmod 库布局](frontend-ui/zipmod-library-layout.md) + [游戏物品运行时探针](game-item-probe.md) + [前后端接口](backend-interface.md) |
| 修改模组扫描、状态或增量重建 | [模组数据库设计](mod_manage/mod_database_design.md) + [数据库变动检测](mod_manage/mod_database_change_detection.md) |
| 将 Studio 女性姿势转换为 zipmod | [Studio 女性姿势转换](mod_manage/pose_zipmod_conversion.md) + [标准模组结构记录](mod_manage/standard_mod_structure_record.md) |
| 补全 KK Animations 的 ForMaker 注册 | [KK Animations ForMaker 注册补全](mod_manage/kk_animations_formaker_completion.md) + [标准模组结构记录](mod_manage/standard_mod_structure_record.md) |
| 修改角色卡解析、依赖或导出 | [角色卡解析说明](mod_manage/character_card_parsing.md) + [角色卡库布局](frontend-ui/character-cards-layout.md) |
| 增加人物卡到游戏的选择性读取 | [人物卡选择性读取](game-card-loading.md) + [角色卡库布局](frontend-ui/character-cards-layout.md) + [前后端接口](backend-interface.md) |
| 调查游戏如何读取人物卡或哪个插件介入 | [独立人物卡读取审计探针](character-card-read-probe.md) + [角色卡解析说明](mod_manage/character_card_parsing.md) |
| 解析服装卡样本或扩展服装卡浏览 | [服装卡样本解析报告](mod_manage/clothes_card_sample_analysis.md) + [角色卡解析说明](mod_manage/character_card_parsing.md) |
| 修改收藏、评分或标签 | [Card metadata 插件](card-metadata-plugin.md) + [人物卡收藏视觉状态](frontend-ui/character-card-favorite-effects.md) |
| 修改工作台工程、CSV、Unity3D 模板或资源写入 | [工作台](frontend-ui/workbench-layout.md) + [前后端接口](backend-interface.md) |
| 编写或排查 SB3UtilityScript | [SB3UtilityScript 调用说明](sb3utility-script.md) + [工作台](frontend-ui/workbench-layout.md) |
| 诊断或修复 Sims 4 FBX 灰黑块/黑三角 | [FBX 灰黑块修复记录](sims4-fbx-gray-black-artifact-repair.md) + [Unity3D 解密与修复](unity3d-decryption-notes.md) |
| 修改 Sims 4 / Unity3D 资源提取或修复流程 | [工作台](frontend-ui/workbench-layout.md) + [Unity3D 解密与修复](unity3d-decryption-notes.md) |
| 对照修复 Unity3D 服装/鞋类对象换色 | [Unity3D 解密与修复](unity3d-decryption-notes.md) + [工作台](frontend-ui/workbench-layout.md) |
| 修改页面结构或样式 | [前端 UI 专题索引](frontend-ui/README.md) + 对应页面文档 + [UI 风格规范](frontend-ui/ui-style.md) |
| 修改缓存路径、失效条件或清理逻辑 | [缓存与运行时文件登记](runtime-cache-registry.md) + 对应功能文档 |
| 修改删除、恢复或永久删除行为 | [回收站](trash-recycle-bin.md) + [前后端接口](backend-interface.md) |
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
