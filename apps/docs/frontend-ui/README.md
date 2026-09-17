# 前端 UI 文档索引

这里集中维护 Star_Manager Vue 渲染器的应用外壳、页面布局、交互边界和视觉规范。文档以当前 `apps/src/` 实现为准；接口字段、任务类型和文件写回规则以[前后端接口](../backend-interface.md)为准。

- 上级索引：[文档总索引](../README.md)
- 开发总览：[项目总览](../project-overview.md)
- 视觉实现：[UI 风格规范](ui-style.md)

## 阅读路径

### 1. 先了解应用骨架

| 顺序 | 文档 | 解决的问题 |
| --- | --- | --- |
| 1 | [前端 UI 架构](frontend-ui-architecture.md) | 页面清单、实现基线和整体产品假设 |
| 2 | [主布局](main-layout.md) | Electron/Vue 应用外壳、全局导航选中态、顶部栏、按实测耗时加权的数据库任务进度和共享后端上下文 |
| 3 | [UI 风格规范](ui-style.md) | 颜色、控件、卡片、界面文字极简原则、风险状态、空状态和响应式原则 |

### 2. 再进入具体页面

页面顺序与应用主导航保持一致：

| 页面 | 文档 | 重点 |
| --- | --- | --- |
| 开始游戏 | [开始页布局](start-layout.md) | 三个一级容器移除外部边框；HS2 目录、后端就绪竞态恢复、目录校验任务、固定与自定义目录入口、GitHub 仓库入口、六个固定插件开关和两个特殊设置、`setup.xml`、启动入口和高风险配置写回 |
| 总览 | [总览页布局](overview-layout.md) | 四个一级容器移除外部边框；资源摘要、使用工具、最近任务和本地成就 |
| 卡片管理 | [角色卡库布局](character-cards-layout.md) | 卡片管理页隐藏全局顶部栏并回收其布局高度；通过互斥 SVG 按钮切换人物卡、服装卡、场景卡子界面，其中三类卡片按钮使用资源目录图标；人物卡与服装卡浏览器标题栏刷新按钮和普通卡名称铭牌使用透明玻璃样式，收藏卡使用暖色不透明铭牌；人物卡、服装卡和场景卡浏览器均采用宽窗口最多五列、缩小窗口优先四列的响应式虚拟网格，服装卡不显示额外搜索工具栏并复用人物卡的底部名称条和“目录/详情”tab；场景卡复用服装卡的目录、分页、虚拟网格和详情链路，预览比例为 `320:180`；人物卡、服装卡和场景卡详情及关联页签控件统一为连续玻璃样式，工具页签四个工具卡移除图标并保留文字与操作按钮，底部提供可恢复的单卡删除工具，人物卡、服装卡和场景卡均支持浏览与文件详情 |
| 角色卡视觉 | [人物卡收藏视觉状态](character-card-favorite-effects.md) | 收藏主题、卡框、铭牌和名字溢出显示 |
| 模组管理 | [Zipmod 库布局](zipmod-library-layout.md) | 模组/物品浏览、轻模糊玻璃化物品列表/预览图与详情面板、多选操作栏与批量按钮玻璃化、增强表头磨砂层、Kind 分类玻璃控件过渡、全部 Kind 与视图切换统一背景、全部 Kind 下方的等尺寸无图标物品视图切换、筛选图标、分页、列表滚动位置保持、装配模式顶部角色选择器、详情文件名定位、右键服饰/头发/饰品换装和诊断入口 |
| 插件管理 | [插件管理布局](plugins-layout.md) | BepInEx 扫描、元数据、缓存和 `.dl_` 单插件启停 |
| 工作台 | [工作台](workbench-layout.md) | 工程生命周期、CSV、Unity3D 模板、资源写回和 Sims 4 工具 |
| 运行日志 | [运行日志布局](runtime-log-layout.md) | 隐藏全局顶部栏；任务进度、运行消息、Electron 首屏里程碑、首屏显示门槛诊断、筛选和导出占位行为 |
| 设置 | [设置页布局](settings-layout.md) | 启动偏好、数据库建库线程数、成就、导出目录、收藏主题和 Blender 配置 |
| 回收站 | [回收站](../trash-recycle-bin.md) | runtime/trash 下的人物卡与模组恢复、永久删除、筛选、测试残留隔离和独立可滚动工作区 |

### 3. 按修改任务查找

| 修改任务 | 先读 | 然后读 |
| --- | --- | --- |
| 修改应用壳、导航或顶部状态 | [前端 UI 架构](frontend-ui-architecture.md) | [主布局](main-layout.md) + [UI 风格规范](ui-style.md) |
| 修改某个页面 | [主布局](main-layout.md) | 对应页面布局文档 + [前后端接口](../backend-interface.md) |
| 修改角色卡收藏、标签或详情 | [角色卡库布局](character-cards-layout.md) | [人物卡收藏视觉状态](character-card-favorite-effects.md) + [Card metadata 插件](../card-metadata-plugin.md) |
| 修改角色卡删除、恢复或永久删除 | [角色卡库布局](character-cards-layout.md) | [回收站](../trash-recycle-bin.md) + [前后端接口](../backend-interface.md) |
| 修改模组列表、状态或诊断入口 | [Zipmod 库布局](zipmod-library-layout.md) | [模组与资源专题索引](../mod_manage/README.md) |
| 修改物品浏览筛选图标、右键换装或头发栏位 | [Zipmod 库布局](zipmod-library-layout.md) | [前后端接口](../backend-interface.md) + [游戏物品运行时探针](../game-item-probe.md) |
| 修改工作台工程、CSV 或 Unity3D | [工作台](workbench-layout.md) | [前后端接口](../backend-interface.md) + [SB3UtilityScript](../sb3utility-script.md) |
| 对照排查 Unity3D 服装/鞋类对象换色 | [工作台](workbench-layout.md) | [Unity3D 解密与修复](../unity3d-decryption-notes.md) |
| 修改缓存、预览或临时文件 | [工作台](workbench-layout.md) | [缓存与运行时文件登记](../runtime-cache-registry.md) |

## 前端实现边界

- `apps/src/App.vue` 维护应用壳、共享目录状态、任务轮询和跨页面操作。
- `apps/src/components/views/*.vue` 负责页面级展示和交互。
- `apps/src/styles.css` 维护全局布局、颜色、控件和风险状态样式。
- 桌面能力通过 `window.desktopApi` 调用；后端数据和任务通过 `backendRequest` 调用。
- 单文件或单对象操作走直接 HTTP/IPC；批量操作走 `/tasks` 并显示进度。
- 文档中的规划内容必须明确标记为“后续”或“未接入”，不能与当前页面能力混写。

## 相关专题

- [模组与资源专题索引](../mod_manage/README.md)
- [前后端接口](../backend-interface.md)
- [缓存与运行时文件登记](../runtime-cache-registry.md)
- [项目总览](../project-overview.md)
