# 开始页布局

## 当前职责

开始页是左侧导航第一项，当前已经接通：

- 选择并保存 HS2 游戏目录；
- 通过 Electron 启动 HS2、Studio 和 VR；
- 打开游戏主目录、`UserData`、工作室场景、截图和男女角色卡目录；
- 展示一个面向 `UserData/setup.xml` 的游戏配置面板。

其中 `setup.xml` 面板目前只是渲染器内的状态占位：初始值由 `App.vue` 的默认对象提供，修改只改变内存状态，保存按钮只清除 dirty 标记并写入一条“backup placeholder”日志。它不会读取、解析、备份或写回真实 XML。

## 参考布局

```text
+--------------------------------------------------------------------+
| [开始游戏] [开始工作室] [开始 VR] [ctx.setup.xml 已读取] [状态]       |
+----------------------+-----------------------------+---------------+
| 游戏配置（占位）     | 启动器视觉卡                | 目录入口       |
| - 语言               |                             | - 游戏主目录   |
| - 画质               |                             | - UserData     |
| - 显示器             |                             | - 工作室场景   |
| - 分辨率             |                             | - 截图         |
| - 全屏               |                             | - 人物卡女/男  |
| [保存配置]           |                             |                |
+----------------------+-----------------------------+---------------+
```

## 启动操作条

页面提供三个启动按钮：

- `开始游戏` → `HoneySelect2.exe`；
- `开始工作室` → `StudioNEOV2.exe`；
- `开始 VR` → `HoneySelect2VR.exe`。

未选择游戏目录时按钮禁用。启动动作通过 preload 的 `launchGameExecutable(launchType, gameDir)` 进入 Electron 主进程，由主进程校验目标文件存在后启动；失败写入运行日志。

当前顶部的 `ctx.setup.xml 已读取` 是固定文案，不代表已经读取 XML；第二个徽标只反映前端占位对象的 dirty 状态。

## 游戏配置区

当前控件为语言、画质、显示器、分辨率、全屏和保存按钮。字段名与默认值来自 `apps/src/App.vue`：

```text
language: 中文
quality: ?
display: Display 0
resolution: 1920 x 1080
fullscreen: false
dirty: false
```

`updateSetup()` 只更新上述响应式对象。当前没有后端 `/game/setup` 路由，也没有 XML 字段映射，因此不要根据这个面板实现“已保存到游戏”的行为。

## 启动器视觉卡和目录入口

中间视觉卡是品牌和启动状态展示区，不承载文件写入操作。右侧目录入口使用当前游戏根目录拼接相对路径：

| 文案 | 相对路径 |
| --- | --- |
| 游戏主目录 | `.` |
| UserData | `UserData` |
| 工作室场景 | `UserData\\Studio\\scene` |
| 截图 | `UserData\\cap` |
| 人物卡（女） | `UserData\\chara\\female` |
| 人物卡（男） | `UserData\\chara\\male` |

目录打开使用 `openDirectory()`。目标不存在或打开失败时只记录错误，不自动创建目录。

## 当前持久化边界

游戏目录和输入/输出目录等管理器设置通过 Electron `settings.json` 保存，详见[设置页布局](settings-layout.md)。开始页的配置对象不在其中；只有真正接入 `setup.xml` 读写后，才应增加独立的备份和原子写入规则。

## 当前接口

开始页实际使用：

```text
POST /tasks { task_type: "check_game_dir" }
GET  /health
```

桌面能力使用：

```text
selectDirectory("选择 HS2 目录")
openDirectory(path)
launchGameExecutable("game | studio | vr", gameDir)
```

下列能力仍是后续工作，不应写成当前接口：

```text
GET/POST /game/setup
POST /game/launch
POST /game/open-path
```

## 空状态和错误状态

- 未选择游戏目录：保留页面结构，禁用启动按钮和目录入口。
- 目录校验失败：顶部显示目录无效，依赖游戏目录的浏览和任务操作由主壳层禁用。
- 启动文件不存在或启动失败：保持页面可用，并在运行日志中显示错误。
- `setup.xml` 解析/保存错误：当前不会发生真实 XML 错误；接入后应保留用户编辑状态、显示错误摘要并阻止覆盖源文件。

## 相关代码

- `apps/src/components/views/StartView.vue`
- `apps/src/App.vue`：游戏目录、启动、占位 setup 状态和目录打开逻辑
- `apps/electron/preload.cjs`
- `apps/electron/main.cjs`
