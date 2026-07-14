# 主布局

## 目标

主布局定义 Star_Manager 的通用应用外壳。界面应让用户首先感受到“资源库浏览器”，其次才是“任务运行器”。

用户的主要目标：

- 选择 HS2 游戏目录。
- 在开始页读取和修改 `UserData/setup.xml`。
- 启动游戏、打开工作室或打开常用游戏目录。
- 扫描并浏览资源。
- 查看角色卡、zipmod、模组物品、诊断和任务结果。
- 默认执行基于 `Copy` 的安全工作流。

## 应用外壳

采用三段式结构：

```text
+----------------------+-------------------------------------------------------------+
| 左侧导航栏           | 顶部全局栏                                                  |
| Star_Manager         | [选择 HS2 目录] [当前目录] [状态] [任务进度] [全局操作]     |
| HS2 resource desk    +-------------------------------------------------------------+
|                      | 工作区                                                      |
| - 开始游戏           | +----------------------------------------+----------------+ |
| - 总览               | | 浏览器 / 模块内容                      | 目录/详情区    | |
| - 角色管理           | | 工具栏 / 卡片 / 表格 / 日志             | 元数据         | |
| - 模组管理           | +----------------------------------------+----------------+ |
| - 运行日志           |                                                             |
|                      |                                                             |
|                      |                                                             |
|                      |                                                             |
+----------------------+-------------------------------------------------------------+
```

## 左侧导航栏

左侧栏是主导航，在所有模块中保持可见。

导航项：

- 开始游戏
- 总览
- 角色管理
- 模组管理
- 插件管理
- 运行日志

左侧栏行为：

- 当前预览宽度为 250 px，实际实现可在 240-280 px 内微调。
- 开始页固定为第一项，用于配置游戏和启动游戏。
- 当前模块使用柔和粉色到浅蓝的高亮背景、黑色描边和短投影。
- 每个导航项使用两字母图标加短文字：`ST`、`OV`、`CH`、`MD`、`LG`。
- 左侧栏不固定显示安全上下文，也不放“导出诊断信息”入口。

## 顶部全局栏

顶部栏展示全局状态和全局操作，不重复承担模块导航。

必需控件：

- 当前游戏目录选择器，文案为“选择 HS2 目录”。
- 当前游戏目录路径，使用等宽或稳定数字字体显示，例如 `D:\HoneySelect2`。
- 游戏目录校验徽标：未选择、有效、无效、扫描中；当前预览为“目录有效”。
- 当前任务迷你进度指示器，包含任务名、百分比、进度条和任务 ID，例如 `扫描 zipmod / 42% / scan_zipmods`。
- Python backend 状态徽标：checking、ready、error；当前预览在任务进度区显示 `Backend ready`。
- 全局操作：仅保留“重建数据库”，用于重新生成本地资源索引。点击前必须先确认游戏目录有效；目录无效时顶部任务提示显示“请选择有效目录后点击重建”，目录有效并开始执行时显示“正在创建数据库，请稍等”，完成后显示“数据库已创建”。

禁用状态：

- 后端不可用时，应用外壳仍保持可见。
- 禁用依赖后端的操作。
- 显示重试按钮和简短后端错误状态。

## 工作区

工作区随模块变化，但保持一致区域：

- 模块标题栏：标题和摘要状态。模块级操作优先放入工具栏，避免标题栏右侧堆叠小按钮。
- 工具栏：搜索、筛选、排序、视图模式、批量选择。
- 主浏览区：卡片、表格、目录树、日志窗口。
- 右侧辅助区：按模块显示详情抽屉或目录树。角色卡库默认显示卡片目录树，Zipmod 库默认显示详情抽屉。
- 运行日志入口：通过左侧导航或任务进度上下文进入。当前预览中运行日志作为完整工作区页面显示。

当前模块工作区：

- 开始游戏：启动操作条、游戏配置、启动器视觉卡、目录入口、底部外链占位。
- 总览：资源摘要、游戏目录状态、建议操作、最近任务，两列卡片布局。
- 角色管理：人物卡浏览器和右侧卡片目录双栏。
- 模组管理：zipmod 表格和右侧详情抽屉双栏。
- 插件管理：进入页面后读取当前游戏目录的 BepInEx 插件，提供程序集汇总、名称/GUID 搜索、core/patcher/plugin 分类筛选，以及包含版本、文件、依赖、进程限制和解析诊断的右侧详情栏。
  - 页面实例在导航切换时保持挂载，避免每次返回都重新解析 DLL；仅首次加载、游戏目录变化或用户点击“重新扫描”时请求扫描。
- 运行日志：日志标题、轻量工具栏和深色终端区域。

## 共享后端上下文

当前后端任务路由继续有效：

- `GET /health`
- `GET /tasks`
- `GET /tasks/:id`
- `POST /tasks`

当前 `POST /tasks` 支持：

- `check_game_dir`
- `search_cards`
- `extract_mods`
- `sort_mods`
- `build_mod_database`

当前模组资源库浏览接口：

- `GET /mods/database`：检查本地模组数据库是否存在，并返回 zipmod 与物品计数。
- `GET /mods/zipmods?offset=&limit=&author=&status=`：分页读取 zipmod 列表，当前前端首批 200 条。
- `GET /mods/zipmods/authors`：读取模组作者筛选项。
- `GET /mods/zipmods/:id/diagnostics`：读取当前 zipmod 的 manifest、Unity3D、缩略图和重复文件诊断。
- `GET /mods/items?offset=&limit=&zipmod_id=&search=&kind=&author=&status=`：分页读取物品列表，当前前端首批 500 条；带 `zipmod_id` 时用于模组详情的物品 tab。
- `GET /mods/items/filters`：读取物品作者和 Kind 筛选项。
- `GET /mods/thumbnails?path=`：读取运行时缩略图缓存，仅允许访问缩略图目录。
- `POST /tasks` with `build_mod_database`：重建模组数据库，后端会拒绝无效 HS2 游戏目录。
- `POST /mods/zipmods/:id/repair-unity3d`：将游戏目录中存在的 `.unity3d` 补入 zipmod。
- `POST /mods/zipmods/:id/update-author`：补写 `manifest.xml` 作者。
- `POST /mods/zipmods/:id/cleanup-duplicates`：删除重复 GUID 文件记录和对应重复文件。
- `POST /mods/zipmods/:id/delete`：删除满足条件的 zipmod 文件和数据库记录。
- `POST /mods/items/:id/import-thumbnail`：导入 PNG 缩略图并回写 CSV。
- `POST /mods/items/:id/delete`：从 zipmod 中移除物品 CSV 行和相关资源。

当前角色卡库接口：

- `GET /library/cards/tree?game_dir=`：读取 `UserData/chara` 目录树和 AIS PNG 计数。
- `GET /library/cards?game_dir=&path=`：读取当前目录直属 AIS 人物卡，不递归子目录。
- `GET /library/cards/image?game_dir=&path=`：读取人物卡图像或标准化预览缓存。

仍待补齐或深化的接口组：

- 游戏 `UserData/setup.xml` 读取、校验、保存和备份。
- 游戏、工作室、VR 模式启动。
- 角色卡详情和依赖结果。
- 运行日志读取、筛选、复制和清空。

## Electron IPC 边界

前端通过 `window.desktopApi` 访问桌面能力：

- `selectDirectory`、`selectImageFile`：选择目录和 PNG 缩略图。
- `showItemInFolder`：在资源管理器中定位选中文件。
- `launchGameExecutable`：启动游戏、工作室或 VR 可执行文件。
- `loadSettings`、`saveSettings`：保存 `gameDir`、`inputDir`、`outputDir`。
- `backendRequest`：访问本地 Python HTTP API。

## 高风险规则

所有会修改游戏目录的操作都必须使用统一的高风险确认流程。

高风险示例：

- `move/cut`。
- 删除文件或目录。
- 修改游戏目录结构。
- 在原游戏目录内批量整理。
- 删除空目录。

确认弹窗必须展示操作名称、影响数量、源路径、目标路径、是否可恢复，以及明确的确认按钮，例如 `确认移动 128 个 zipmod`。
