# 工作台

## 文档定位

工作台是一个独立的模组制作工作区。它把模组工程、`abdata/list/**/*.csv` 物品数据和 Unity3D 主资源组织在同一个本地工程中；当前页面的主流程是“创建工程 → 创建或选择物品 → 为物品选择 Unity3D 模板 → 确认 `MainData` → 写入 CSV”。

本文描述当前已经接入的工作台页面、工程格式、CSV 数据边界、Unity3D 模板流程和保留但未接入页面的 Sims 4 工具。实现以以下代码为准：

工作台不显示应用全局顶部栏，页面会回收顶部栏的布局高度；工程工具栏和资源编辑区仍由工作台页面自身提供。

物品工具栏仅显示中文“物品工具”标题，不再显示英文辅助小标题；当前选中物品后，工具栏显示在工作台顶部项目工具栏中，位于 `Package → FBX` 后方，工具按钮和操作范围保持不变。

工程物品列表标题仅显示“模组物品”和工程 GUID，不再显示 `ITEM BROWSER / 工程名` 辅助文字；工程名称仍通过项目工具栏和工程数据保留。

- 页面：`apps/src/components/views/WorkbenchView.vue`
- 共享状态和模组管理跳转：`apps/src/App.vue`
- Electron IPC 和工程文件操作：`apps/electron/preload.cjs`、`apps/electron/main.cjs`
- Unity3D 读取与副本预处理：`apps/backend/star_manager/services/model_preview.py`
- 模板物品查询：`apps/backend/star_manager/services/mod_database_queries.py`
- HTTP 路由：`apps/backend/app/server.py`

## 当前能力边界

| 能力 | 当前状态 | 说明 |
| --- | --- | --- |
| 作者和工作空间登记 | 已接入 | 保存到 Star_Manager 本地设置，不写入 HS2 游戏目录 |
| 模组工程管理 | 已接入 | 创建、扫描、切换和删除工作空间内的工程 |
| CSV 物品浏览 | 已接入 | 每条 CSV 数据行对应一个工作台物品 |
| 新建/删除物品 | 已接入 | 新建追加 CSV 行，删除只移除对应数据行 |
| Unity3D 数据库模板 | 已接入 | 从“模组管理 → 物品浏览 → 工具”选择可用物品作为模板 |
| `MainData` 读取 | 已接入 | 后端只读解析返回候选 GameObject，优先保留源物品的 `MainData` |
| Unity3D 对象复制与重命名 | 已接入 | 模板和工程内已有资源均可复制所选对象并按输入名称重命名；工程内已有资源会在临时副本验证后原子回写 |
| 工程内 Unity3D 资源选择 | 已接入 | `MainAB` 行会列出当前工程 `abdata/` 下已有的 Unity3D，资源编辑区直接确认文件和 `MainData` |
| Sims 4 Package → FBX | 已接入 | 位于模组工程区域的“Package → FBX”工具按钮，以弹窗选择源 `.package`、输出目录并查看导出结果；配置 Blender 时会自动检测并安全清理完全重合、方向相反的重复三角面 |
| FBX 应用旋转与缩放 | 已接入 | 位于工作台顶部的当前物品工具栏；按 Blender 默认方式导入当前项目内的 `.fbx`，只应用 Mesh 自带的旋转与缩放并保留 Armature 的坐标系/单位变换，不提供额外角度或倍率输入 |
| FBX 纯网格 | 已接入 | 位于工作台顶部的当前物品工具栏；选择当前项目目录内的 `.fbx`，删除骨骼、蒙皮 Modifier 与顶点组并在原目录生成新的静态 FBX |
| 绑定 HS2 骨架 | 已接入 | 位于工作台顶部的当前物品工具栏；选择 Mesh FBX 和外部 `body.fbx`，加入 HS2 骨架但不添加蒙皮 |
| 复制 FBX 权重 | 已接入 | 位于工作台顶部的当前物品工具栏；从带蒙皮的外部 FBX 按骨骼名称匹配，将目标顶点投影到来源网格最近表面并用三角形重心插值转移权重 |
| 贴图处理 | 已接入 | 位于工作台顶部的当前物品工具栏；可视化选择 1:1 裁剪区域、自定义输出分辨率、去除基础色并导出 SB3Utility 可读取的 PNG |

工作台不是模组数据库，也不把工程 CSV 写回游戏目录的 zipmod。工程文件由用户选择的工作空间管理；数据库模板选择会读取当前模组库，但最终资源复制和 CSV 写入发生在工作台工程内。

### 模组物品选择 Unity3D 模板后预处理区未显示（2026-09-06）

- 背景：从“模组管理 → 物品浏览 → 工具”点击“作为模板 / 选择”后，工作台没有出现 Unity3D `MainData` 预处理组件。
- 根因：页面导航使用 Vue `KeepAlive` 后，工作台组件从模组管理返回时处于重新激活状态，不会再次执行 `onMounted`；原有模板结果消费逻辑只写在 `onMounted` 中，因此共享状态里的模板结果没有被转成工作台的 `resourceEditor` 状态。
- 解决方案：在 `onActivated` 中消费待处理模板结果；首次挂载和从其它页面返回都能读取待处理模板，打开资源编辑器并显示 `MainData` 候选及“清除其他对象 / 复制当前对象 / 重命名当前对象”等预处理操作。
- 验证结果：`npm run build` 通过；`git diff --check` 通过；已核对模板选择结果在工作台激活生命周期中被消费。
- 适用边界：只修复当前应用运行期间通过物品浏览器选择工作台模板的页面衔接，不改变 Unity3D 解析、对象预处理或 CSV 写入规则；刷新或重启后不会保留未完成的临时模板选择。

## 1. 首次进入：作者与工作空间

首次进入工作台时，页面要求填写：

- **模组作者 ID**：作为新工程 `manifest.xml` 的 `<author>`，也用于生成工程 GUID 和资源目录名。
- **工具台工作空间**：专门存放多个 Star_Manager 模组工程的本地文件夹。

点击保存后，前端调用 `saveWorkbenchProfile(authorId, workspacePath)`，持久化以下上下文：

- `workbenchAuthorId`
- `workbenchWorkspacePath`
- `workbenchActiveProjectId`
- `workbenchProjects`

工作空间只用于工作台工程，不会被当作 HS2 游戏目录，也不会因为保存登记信息而修改游戏文件。进入工作台和保存工作空间时，Electron 会扫描工作空间的一级子目录，只有能通过工程标识和 `manifest.xml` 校验的目录才会显示为工程。

## 2. 工程生命周期

### 创建工程

创建工程只需要输入模组名称。Electron 会在工作空间下建立不冲突的目录，并生成：

```text
<工作空间>/
└─ <模组目录>/
   ├─ manifest.xml
   ├─ star-manager.project.json
   └─ abdata/
      └─ list/
```

如果同名目录已经存在，会追加 ` (2)`、` (3)` 等后缀。`manifest.xml` 的当前默认字段为：

```xml
<guid>com.<作者ID>.<模组名></guid>
<name>模组名</name>
<version>1.0.0</version>
<author>作者ID</author>
```

目录名会清理 Windows 不允许的字符，但 `manifest.xml` 的 `<name>` 保留用户输入的模组名称。工程 GUID 使用安全化后的作者和模组名称生成，格式必须满足 `com.<segment>.<segment>`。

### 工程标识文件

`star-manager.project.json` 用来确认一个目录确实是 Star_Manager 工作台工程：

```json
{
  "format": "star-manager.hs2-mod-project",
  "schemaVersion": 1,
  "projectId": "稳定的工程 UUID",
  "manifest": "manifest.xml",
  "createdAt": "ISO 时间",
  "generator": "Star_Manager"
}
```

工程扫描还会校验 `manifest.xml` 存在、字段完整且 GUID 格式有效。仅有一个普通文件夹或只有 `manifest.xml` 的目录不会自动显示为新工程；对旧设置缓存中的可识别工程，扫描过程可以补写缺失的工程标识文件。

### 切换和删除工程

- 工程列表是单选列表，当前工程 ID 会保存到 `workbenchActiveProjectId`。
- 工程列表标题栏提供“隐藏列表 / 显示列表”切换；隐藏时仅收起项目行，当前工程和下方工具区仍保持可用。
- 打开工程后，页面读取该工程 `abdata/list/` 下的所有 CSV 数据行。
- 删除工程必须经过确认；删除范围是工作空间下的该工程目录及其中全部文件，且不可恢复。
- Electron 会校验工程目录必须是当前工作空间的直接子目录，不能删除工作空间外或工作空间本身。

### 项目搜索栏布局维护记录

- **问题背景**：当前工程工具栏中的“搜索项目”输入框需要靠近右侧项目列表开关，同时避免占用过多横向空间。
- **根因**：桌面布局原先让搜索控件按剩余空间伸展，项目列表开关再通过自动外边距单独推到最右侧，导致搜索框过长且与右侧控件间距偏大。
- **解决方案**：搜索框在桌面宽度下固定为 `280px`，由搜索框承担自动外边距；同时清除列表开关继承到的自动外边距，让搜索框与列表开关紧靠右侧排列；窄屏仍恢复为整行宽度，避免工具按钮拥挤。
- **验证结果**：已执行 `apps` 目录下的 `npm run build`，Vite 生产构建成功；仅保留现有第三方 `eval` 和大 chunk 警告。
- **适用边界**：仅调整工作台当前工程工具栏的视觉布局，不改变项目名称、GUID、路径搜索逻辑或项目列表折叠行为。

### 工程列表数量截断排障记录

- **问题背景**：工作空间中的第 101 个有效工程（例如 `T054`）已经存在且工程文件完整，但项目搜索显示“未找到匹配的项目”。
- **根因**：前端合并工作空间扫描结果和 Electron 设置规范化时都使用 `slice(0, 100)`，导致第 101 个及之后的工程从内存列表和持久化设置中被丢弃。
- **解决方案**：移除前端 `mergeWorkbenchProjects` 与 Electron `normalizeSettings` 对工作台工程列表的 100 条截断；工程列表仍只接受当前工作空间一级目录下通过工程标识和 `manifest.xml` 校验的工程。
- **验证结果**：工作空间扫描确认 101 个有效工程，`T054` 位于第 101 个且工程标识有效；已通过 Electron 语法检查和前端生产构建。
- **适用边界**：取消的是工作台工程列表数量上限，不改变工程目录层级、工程文件格式、有效性校验或项目搜索的名称/GUID/路径匹配规则。

### 工具层级

- **模组工具**位于模组工程区域，作用对象是当前工程；“打包模组”属于这一层，会把当前工程生成正式的 zipmod 并替换游戏目录中的旧版本。打包成功后会自动提交一次单个模组索引任务，只读取当前生成的 zipmod，完成后新 GUID 可立即在模组库中定位；如果同步失败，仍保留已生成的 zipmod，并在页面提示原因。
- “Package → FBX”在配置 Blender 后会于 T-Pose 固化完成、导出纯网格之前检查反向重合三角面。自动清理只接受恰好两个三角面、顶点位置完全重合、几何法向相反且材质一致的组；优先按 FBX 分角法向选择保留面，无法据此判断时使用网格中心方向，仍有歧义或同位置超过两个面时保留原样。导出结果会分别显示检测、清理和歧义跳过数量。未配置 Blender 的静态 FBX 导出不会执行该几何清理。
- **物品工具**位于工作台顶部的当前物品工具栏，作用对象只能是当前 CSV 物品。“应用旋转与缩放”按 Blender 默认方式导入项目内 FBX，只选中 Mesh 执行 Apply Rotation & Scale 并保留 Armature 的坐标系和单位缩放；它不接收或叠加自定义角度与倍率。当前还提供“FBX 纯网格”：可从当前项目目录选择任意 `.fbx`，由设置中的 Blender 删除 Armature、蒙皮 Modifier 和 Vertex Groups，保留 Mesh、材质、UV 与网格数据；默认备份后输出 `_mesh-only` 文件，也可取消备份并直接覆盖原文件。
- “复制 FBX 权重”默认采用 Maya 风格的最近表面复制：目标顶点投影到来源网格最近三角形，按三角形重心坐标插值来源顶点权重，再按骨骼名称写入目标骨架。默认不强制截断到 4 个影响骨骼；脚本命令行可用 `--max-influences 4` 为特定运行时启用四权重限制。
- “贴图处理”读取 PNG、JPG 或 WebP，但不修改源文件。裁剪框固定为 1:1，可拖动、缩放并用方向键微调；输出支持 64–4096 像素的自定义正方形分辨率，常用的 256/512/1024/2048/4096 提供快捷档位。默认“纯纹理”模式会中和色相和局部光照，将底面还原为白色并保留纤维、凹凸等明暗细节；关闭后则保留原始颜色。最终通过系统保存窗口写出 RGBA 8-bit PNG，适合作为 SB3Utility 的 `AddTexture` / `ReplaceTexture` 输入。
- 已知裁剪坐标需要重复处理时，可使用 `apps/scripts/process_texture.py` 执行相同的居中/指定方形裁剪、分辨率缩放和纯纹理 PNG 处理；可视化选择仍以物品工具弹窗为主。
- 两类工具按作用范围分开显示，不能把模组级操作放入物品工作区。

## 3. 工程内物品与 CSV

### CSV 目录和类别

工作台递归读取工程下的 `abdata/list/**/*.csv`。新建类别 CSV 默认放在 `abdata/list/characustom/` 下；已有类别 CSV 会在整个 `abdata/list/` 范围内复用。每个类别 CSV 的第一行第一个单元格是类别标识，随后保留两行类别元信息，再写入包含 `ID` 和 `Name` 的表头。例如新建类别时使用的基础结构是：

```text
<类别>
0
ABCDEFG
ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,StateType,MainTex,ColorMaskTex,ThumbAB,ThumbTex
```

类别 CSV 文件名默认按 `<工程名>_<类别>.csv` 生成；已有同类别 CSV 会复用，不会重复创建。

Kind `361`（饰品/手部）使用游戏实际的饰品结构，而不是上面的通用结构。新建该类别时自动生成：

```text
361
0
Assets/in-house/assetbundle/list/characustom/00/ao_hand_00.bytes
ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,Parent,ThumbAB,ThumbTex
```

饰品创建行的 `Parent` 默认填写 `N_Hand_R`，其余主资源字段沿用工作台的初始值；创建后可继续通过物品工作区应用 Unity3D 资源。`Parent` 是饰品挂点字段，`ID`、`Name`、`MainManifest`、`MainAB`、`MainData` 和 `Parent` 是工作台处理饰品资源时的核心字段，`ThumbAB`/`ThumbTex` 用于缩略图。

### 标准字段

当前 Electron 创建物品时使用以下字段：

| 字段 | 新建默认值 | 工作台用途 |
| --- | --- | --- |
| `ID` | 当前 CSV 最大数字 ID + 1 | 物品在类别 CSV 中的标识 |
| `Kind` | `0` | 保留给游戏物品类别数据 |
| `Possess` | `1` | 物品拥有状态 |
| `Name` | 用户输入的物品名 | 工作台列表和工程资源命名的来源 |
| `EN_US` | `0` | 保留字段 |
| `MainManifest` | `abdata` | 主资源所在的游戏相对根目录 |
| `MainAB` | `0` | 主 Unity3D 相对路径；`0` 表示尚未配置 |
| `MainData` | `<物品名>_obj` | 主 Unity3D 中的模型根 GameObject 名称 |
| `StateType` | `0` | 资源状态字段 |
| `Parent`（Kind `361`） | `N_Hand_R` | 饰品挂点；饰品 CSV 的必要字段 |
| `MainTex` | `<物品名>_diffuse1` | 主贴图引用 |
| `ColorMaskTex` | `mc_1` | 颜色遮罩贴图引用 |
| `MainTex02` / `ColorMask02Tex` | `0` | 可选的第二组贴图引用，由工作台按需加入 |
| `MainTex03` / `ColorMask03Tex` | `0` | 可选的第三组贴图引用，由工作台按需加入 |
| `ThumbAB` | `0` | 缩略图资源路径，可以是 `.unity3d`、未打包图片或图片目录 |
| `ThumbTex` | `0` | 缩略图贴图引用 |

CSV 是当前工作台物品数据的唯一来源。工作台不创建或读取 `star-manager.item.json`，也不把每条物品复制到 SQLite 数据库。

### 物品操作

- **新建物品**：输入物品名和类别；如果类别 CSV 不存在则先创建，再追加一行基础记录，并立即进入物品工作区。
- **浏览物品**：当前工程的所有有效类别 CSV 会合并显示，列表展示 `Name`。
- **删除物品**：确认后只删除对应 CSV 的一行，保留 CSV 文件、同文件其它物品和工程资源文件。
- **打开 CSV 目录**：在物品工作区顶部打开当前 CSV 所在的本地目录。

物品 ID 使用 `<CSV 相对路径>#<CSV 数据行号>` 定位，因此删除或手工重排 CSV 后，页面需要重新扫描物品列表。

## 4. 物品工作区布局

选中物品后，页面进入物品级工作区：

1. 顶部显示返回物品列表、物品名称、CSV 来源标记和打开 CSV 目录操作。
2. **模型**卡片显示 `MainAB`、`MainData`；当前工程 `abdata/` 下存在 Unity3D 时，`MainAB` 行直接显示已有文件下拉列表，选择后在资源编辑区确认该文件中的 `MainData` 再写入 CSV。当主资源信息不完整时，右侧仍提供“+”数据库模板入口；`MainAB` 已填写时，旁侧打开按钮会调用已配置的 SB3Utility 打开对应 Unity3D。
3. **贴图**卡片最多显示三组 `MainTex` / `ColorMaskTex` 配对；点击“新增一组”会把下一组字段加入 CSV，删除中间组时后续组会前移。所有贴图字段均可直接编辑，输入框失焦或按 Enter 后写回当前 CSV。非空贴图字段检查为缺失时，字段右侧显示“导入”按钮，可选择外部图片并按当前资源名导入到 `MainAB`；资源已找到时则显示 SVG 替换图标按钮。贴图写入会使用当前 `MainData` 对应的 Animator 组件，而不是 Texture2D 自身的组件序号；替换前校验同名纹理，输出后重新读取临时 Unity3D，验证通过才原子覆盖工程文件。
4. 资源检查条下方显示当前物品的交互式 **3D 物品预览**。当 `MainAB` 和 `MainData` 都有效时自动生成带材质贴图的 GLB，可拖动旋转、滚轮缩放、切换灯光/背景和放大查看；替换贴图后自动刷新，也可通过右上角 SVG 刷新按钮重新生成。
5. 3D 预览右侧显示当前模组工程目录下递归扫描到的贴图文件和 `.fbx` 模型，展示工程相对路径与文件大小；点击贴图行会在左侧切换到贴图预览，资源行提供“使用 SB3Utility 打开”和定位文件按钮，FBX 行还保留 Blender 打开按钮，右上角按钮可重新扫描。
6. 打开资源编辑器后，在当前工作区下方显示模板信息、`MainData` 候选和对象处理操作；工程内已有资源也可直接使用复制和重命名工具。

当前“+”入口只在 `MainAB` 或 `MainData` 缺失时显示，避免覆盖已经完整的主资源记录；工程内 Unity3D 下拉列表在扫描到可用文件时始终显示，允许为已有记录改选主资源。

### Unity3D 资源自动检查

当物品的 `MainAB` 已填写时，工作区会自动检查工程 `abdata/` 下的对应 `.unity3d` 文件。文件可读取后继续检查同一资源中的：

- `MainData`：必须匹配 Unity3D 中的 `GameObject` 名称；
- 非空 `MainTex`、`ColorMaskTex`、`MainTex02`、`ColorMask02Tex`、`MainTex03`、`ColorMask03Tex`：必须匹配 Unity3D 中的 `Texture2D` 名称。

检查结果显示在模型和贴图卡片下方；快速切换物品或修改 CSV 数据时，旧的异步检查结果不会覆盖当前物品。空的贴图字段表示尚未配置，不会被当作缺失资源。

## 5. 数据库物品作为 Unity3D 模板

这是当前页面的主资源制作流程。

### 选择模板

点击物品工作区模型卡片中的“+”后，应用会暂存当前工程、CSV、物品 ID 和目标物品，跳转到“模组管理 → 物品浏览”的“工具”页。模板选择只允许使用：

- 非地图物品；
- `MainAB` 指向 `.unity3d` 的物品；
- 数据库状态为 `in_mod` 或 `in_game` 的可用 Unity3D 资源。

选择一个物品后，应用会：

1. 准备该物品的 Unity3D 文件；包内资源会使用运行时副本，游戏目录中的资源使用可读取的现有路径。
2. 调用 `/workbench/unity3d/assets` 读取可能的 `MainData` GameObject。
3. 优先匹配源物品 CSV 的 `MainData`，找不到时使用后端推荐候选或第一项候选。
4. 返回工作台，并恢复原目标物品，显示模板缩略图、物品名、GUID、Unity3D 路径和候选对象。

取消选择不会写入工程；模板选择流程中的准备副本也不等于已经写入工作台 CSV。

### `MainData` 和默认重命名值

`MainData` 必须对应当前模板 Unity3D 中的有效 GameObject。候选对象来自 UnityPy 解析结果，优先选择带 Renderer 的可能根对象。

预处理区的“新的对象名称”输入框默认填写当前工作台物品名加 `_obj`，例如物品名为 `ribbon` 时默认值为 `ribbon_obj`。这是实际输入值，不是 placeholder；用户可以直接修改后执行“重命名当前对象”。

## 6. Unity3D 副本预处理

所有预处理操作都先针对运行时临时副本执行，并重新扫描候选对象。模板资源只更新临时副本；工程内已有资源在脚本成功且输出可读后原子回写原工程 `.unity3d`，不会留下半成品。实际写入由 Electron 主进程生成临时 SB3UtilityScript 脚本并等待 `SB3UtilityScript.exe` 返回；Python 后端只负责候选对象读取和输出校验，不再用 UnityPy 序列化工作台修改结果。

| 操作 | 行为 |
| --- | --- |
| 清除其他对象 | 保留当前选中的 MainData 对象及其对象树，移除同一 Unity3D 中的其它对象 |
| 复制当前对象 | 复制当前选中的 GameObject 及其对象树，并为副本生成不冲突的对象名称 |
| 重命名当前对象 | 使用“新的对象名称”输入值重命名当前选中的对象，并同步后续 CSV 的 MainData |
| 复制所选对象并重命名 | 工程内已有 Unity3D 资源保留的兼容操作：复制选中对象及其对象树，并使用输入名称为副本命名 |

数据库物品模板和外部 Unity3D 的处理界面提供前三个独立操作；工程内已有资源仍保留“复制所选对象并重命名”。所有操作都会先在临时副本中执行，再重新读取候选对象；若无法定位所选对象、复制出的对象或输入名称无效，页面只显示错误，不继续写入工程 CSV。

### Unity3D 复制对象显示与换色问题记录

#### 问题背景

UnityPy 复制 Unity3D 对象后，复制出的对象可能已经出现在编辑器候选列表中，但进入游戏时只有原始对象（例如 `T007_base`）能正常显示；复制出的对象虽然存在，却无法显示模型。补齐显示所需的资源链后，还可能出现只有原始对象能正常换色、复制对象不响应游戏换色逻辑的问题。`B015` 文件还出现过资源入口名称与实际根对象错配，导致整组对象无法正常换色。

#### 根因

- AssetBundle 的 `m_Container` 只登记了原始对象，没有为复制对象建立入口；复制对象对应的 `m_PreloadTable` 也没有包含完整、唯一且可解析的对象依赖。
- 复制网格、材质和贴图时，依赖对象之间的本地 PPtr 没有全部重映射，导致运行时仍引用原对象或引用到不完整的资源链。
- `CmpClothes` 的部分字段是 UnityPy 动态序列化字段。旧的克隆逻辑只读取 `__attrs_attrs__`，没有复制 `vars(value)` 中的 `rendNormal01`、`rendCheckVisible`、`objTopDef`、`objTopHalf` 等字段，因此复制对象的换色脚本仍指向原始对象的渲染器（T007 中曾错误指向渲染器 `2741`）。
- B015 中 `B015_base_obj` 被错误登记为第二个 `b015_base_diffuse1` 容器入口，使同一个入口同时指向贴图和根 GameObject；根对象的预加载表因此只有 1 个贴图依赖，缺少完整依赖链。

#### 解决方案

- 在 `_append_asset_bundle_duplicate_entry()` 中为每个复制对象补充 AssetBundle `m_Container` 入口，并按复制对象的完整依赖图重建 `m_PreloadTable`。
- 深度复制对象树、网格、材质和贴图，对复制范围内的 PPtr 做统一的本地映射；不再复用原对象的资源引用。
- 在 `_clone_unity_value()` 中合并复制 UnityPy 类型声明字段和运行时动态字段（`__attrs_attrs__` 与 `vars(value)`），并递归重映射动态字段中的对象引用，使 `CmpClothes` 的渲染器列表、可见性列表和对象配置都属于复制对象。
- 依赖图扫描也必须合并 `__attrs_attrs__` 与 `vars(value)`；否则动态 `CmpClothes` 引用虽已写入副本，仍可能不会进入预加载表，保存后会出现可见但运行时换色链不完整的对象。
- 对已经生成的 B015 文件删除错误的根对象容器入口，新增正确的 `b015_base_obj` 入口，并重建完整预加载表。外部 Unity3D 修复均先写入临时副本，重新读取并完成结构校验后再原子替换，同时保留备份。

#### 修复与验证结果

- T007 文件 `D:\Workspace\Star_workspace\T007\abdata\chara\yukilat\yukilat_T007_1.unity3d`：AssetBundle 容器共 11 个入口；`t007_base_obj`、`t007_1_obj`、`t007_2_obj` 的预加载项分别为 390、388、388 个，全部唯一且可解析。两个复制对象的 `CmpClothes` 已分别指向渲染器 `3128` 和 `3514`，不再指向 `T007_base` 的渲染器。
- B015 文件 `D:\Workspace\Star_workspace\B015\abdata\chara\yukilat\yukilat_B015_1.unity3d`：已修正 `b015_base_obj` 容器入口，并重建 1014 个唯一且可解析的预加载依赖。修复前的文件备份为 `yukilat_B015_1.unity3d.star-manager-backup-color-20260816`。
- 自动化验证覆盖 AssetBundle 入口补齐和动态序列化字段重映射，结果为 `29 passed, 1 skipped`；同时完成 Electron 语法检查和前端构建验证。

#### 适用边界

- 该修复针对 UnityPy 复制或改写后出现的 AssetBundle 入口、依赖链和动态字段问题；普通原始 Unity3D 文件不需要重复处理。
- 已经生成但缺少入口、预加载依赖或动态字段的旧文件需要单独修复；新的复制流程会自动执行深度复制、PPtr 重映射和 AssetBundle 入口重建。
- 新增或遇到其它带动态序列化字段的 MonoBehaviour 时，不能只依据静态字段声明判断复制是否完整，必须检查运行时字段及其中的 PPtr 是否也被重映射。
- 修复游戏资源时应使用“临时副本验证 → 原子替换 → 保留备份”的顺序，避免 UnityPy 序列化失败或结构不完整时破坏原始 Unity3D。

#### 鞋类原始对象对照案例

`D:\Workspace\Star_workspace\shoes_1\abdata\chara\yukilat\yukilat_shoes_1_1.unity3d` 中，`shoe_333_3_obj` 可正常换色，而 `shoe_333_1_obj` 与 `shoe_333_2_obj` 不响应。对照同文件其它鞋对象后确认：鞋类没有上下衣变体，`CmpClothes.objTopDef`、`objTopHalf`、`objBotDef` 和 `objBotHalf` 应保持空引用；`rendNormal01` 与 `rendCheckVisible` 则必须分别指向本对象树中的 `n_shoes_00` 渲染器，不能把 `n_shoes_00` 填入 `objTopDef`。

此外，三个可作为主资源入口的鞋对象必须拥有一致的 AssetBundle 预加载结构。修复旧副本时应以可用鞋对象的段为模板，补齐内置依赖并保持材质、贴图、渲染器和 Mesh 的完整依赖链；只改 MonoBehaviour 字段而不修正预加载段，可能仍导致游戏运行时换色失败。该案例已在 UnityPy 中重新打开并校验对象表、容器段连续性和本地引用。

## 7. 将模板写入当前物品

点击“写入 CSV 并完成”后，Electron 通过 `applyWorkbenchMainResource` 将选中的模板写入工程：

1. 校验工程、CSV 路径、物品 ID 和 `MainData`。
2. 将准备好的 Unity3D 副本复制到工程的资源目录：

   ```text
   <工程>/abdata/chara/<作者ID>/<作者ID>_<工程名>_<序号>.unity3d
   ```

3. 为复制后的 Unity3D 中每个 serialized CAB 条目生成独立的 `CAB-<32 hex>` 标识，并重新打开文件验证写入结果；CAB 阶段只重建 UnityFS 外层目录和压缩块，serialized 子文件与 `.resS` 的负载字节、长度和 flags 必须保持不变。这一步防止多个由同一模板派生的模组在 Sideloader 中发生 `conflicting CAB string`，同时避免 UnityPy 重新序列化对象表后改变 Unity 2018 资源偏移。
4. 在当前物品 CSV 行中原子更新：

   ```text
   MainManifest = abdata
   MainAB       = <相对于工程 abdata 的路径>
   MainData     = <选中的 GameObject 名称>
   StateType    = 0
   ```

5. 重新读取 CSV 行并刷新物品工作区。

目标文件名采用递增序号并避开已有文件，不覆盖工程中已有的 Unity3D。导入、内置模板和数据库模板复制都会在写入 CSV 前重写唯一 CAB；预处理和贴图写回会先保存实际对象修改，再重新读取该输出并以不序列化 SerializedFile 的方式改 CAB。`.resS` 资源节点名和所有子文件负载不随 serialized CAB 改名，避免破坏现有流式资源引用，也保持 SB3Utility 与 Unity 2018 的读取兼容性。任一步骤失败时会删除本次刚复制的目标文件，避免留下孤立资源。

## 8. 资源来源分支

Electron 的 `applyWorkbenchMainResource` 仍实现了以下资源来源分支：

- `existing`：`MainAB` 行直接列出工程 `abdata/` 下已有的 `.unity3d`，选择后在资源编辑区确认 `MainData`，不复制源文件；
- `import`：保留为兼容性的内部分支，当前页面不显示外部文件导入切换入口；
- `database`：当前页面实际使用的数据库物品模板复制流程；
- `template`：Electron 内置 Unity3D 模板的兼容分支。

当前 `WorkbenchView.vue` 已接入 `existing` 与数据库物品模板入口；内置 `template` 分支和 `import` 分支保留兼容实现。

## 9. 接口与进程边界

### Electron preload IPC

Package → FBX 导出结果卡片的垃圾桶按钮会直接调用 `deleteSims4ResultDirectory`，只删除带有匹配 `extraction_manifest.json` 的当前导出结果目录。

工作台项目和文件操作通过 `window.desktopApi` 暴露：

- `createWorkbenchProject`
- `deleteSims4ResultDirectory`
- `deleteWorkbenchProject`
- `scanWorkbenchProjects`
- `scanWorkbenchItems`
- `scanWorkbenchAssetFiles`
- `loadWorkbenchAssetPreview`
- `loadWorkbenchThumbnail` / `saveWorkbenchThumbnail`
- `createWorkbenchItem`
- `deleteWorkbenchItem`
- `scanWorkbenchUnity3d`
- `validateWorkbenchMainResource`
- `previewWorkbenchItem`
- `openWorkbenchMainResourceInSb3Utility`
- `updateWorkbenchItemResourceFields`
- `importWorkbenchTexture`
- `exportWorkbenchProcessedTexture`
- `applyWorkbenchMainResource`
- `packageWorkbenchMod`：生成正式 zipmod，并等待单个模组索引任务完成；打包进度和数据库同步进度都通过 `onWorkbenchPackageProgress` 推送。

渲染进程不直接访问 Node 或文件系统。单个工程、物品和资源写入由 Electron 主进程执行，并进行路径边界校验。

### Python HTTP 后端

当前工作台直接使用的 Unity3D 路由为：

- `GET /workbench/template-items`：分页返回可用的数据库模板物品；
- `POST /workbench/unity3d/assets`：读取一个本地 Unity3D 的 `MainData` 候选和 `Texture2D` 名称；
- `POST /workbench/unity3d/model-preview`：按当前工程 Unity3D、`MainData` 和 `Kind` 生成可交互预览使用的缓存 GLB；
- `POST /workbench/unity3d/thumbnail`：只读解析工程内 Unity3D 缩略图资源，返回前端预览用 PNG 数据；
- `POST /workbench/unity3d/duplicate`：复制选中的 GameObject 子树，并深度复制网格、材质和贴图资源后返回派生 Unity3D；
- `POST /workbench/unity3d/preprocess`：执行跨 Animator 的“清除其他对象”，保留所选 GameObject 及其子树后返回派生 Unity3D；
- `POST /workbench/unity3d/import-texture`：使用 UnityPy 导入或替换贴图，避免重新解析 UnityPy 派生文件时触发 SB3Utility 的 Avatar 校验错误；
- `workbench:preprocessTemplate`：复制与清除对象使用后端 UnityPy，重命名、贴图及其他资源写入仍由 Electron 主进程调用 `SB3UtilityScript.exe`；
- `applyWorkbenchMainResource`：复制模板后通过同一脚本执行 `RenameCabinet`，再更新 CSV。

模板物品跳转流程还会调用模组管理的 `POST /mods/items/:id/open-unity3d` 准备 Unity3D 文件。以上都是单对象操作；当前工作台没有批量任务，也不应新增批量直连 HTTP 写入接口。

物品详情头部会显示 CSV 当前引用的缩略图。若 `ThumbAB` / `ThumbTex` 缺失或无法读取，页面显示“构建缩略图”按钮；按钮会截取当前工作台 3D 预览的 PNG，写入工程 `abdata/thumbnail/star_manager/`，并回写当前 CSV 的 `ThumbAB` 与 `ThumbTex`。

详细请求字段、响应结构和前后端 mutation 规则统一维护在[前后端接口](../backend-interface.md)。

## 10. Sims 4 Package → FBX 工具

模组工程区域的“Package → FBX”按钮会打开 Sims 4 模型转换弹窗。页面通过 `POST /tools/sims4/package-fbx` 调用 `apps/backend/star_manager/services/sims4_workbench.py`，不会把该工具混入当前物品工具栏。

弹窗支持选择源 `.package`、输出目录、开始转换、直接删除当前导出结果目录、定位 FBX 文件，以及使用设置中已配置的 Blender 打开模型。删除操作只允许删除带有匹配 `extraction_manifest.json` 的 Package→FBX 结果目录。输出目录默认使用当前选中模组工程的根目录；切换模组工程后会随工程切换，用户点击“更换”后仍可选择其它目录。

保留能力包括：

- 读取一个 Sims 4 `.package`，按模型族选择顶点数最高的 LOD0 GEOM；
- 解码支持的 RLE2/DXT5 色板为外部 PNG，并保留其它色板；
- 按透明度覆盖清理完全没有可见像素的三角面；
- 配置 Blender 时，使用内置 TS4 参考骨架和 GEOM 原始权重临时固化为 HS2 对齐 T-Pose；双臂保持水平和方向不变，左右整条手臂骨骼链分别向躯干水平平移上臂长度的 6%，减轻肩部外撑；
- T-Pose 固化后自动检测位置完全重合、几何法向相反的重复三角面；只自动删除材质一致且能由分角法向或网格中心方向安全判定的反向副本，歧义组和同位置超过两个面的组保持不变；
- 导出阶段移除 Armature、骨骼、顶点组和蒙皮，最终 FBX 是静态纯网格；
- Blender 未配置时仍可导出未固化姿势的静态 FBX。

导出结果总览显示反向重合面的检测与处理结果；单个 FBX 文件行只保留文件名和打开/定位操作。后端响应和 `extraction_manifest.json` 使用 `reverse_duplicate_groups_detected`、`reverse_duplicate_faces_removed`、`reverse_duplicate_ambiguous_groups` 字段记录数量；处理后的 `vertices` 和 `triangles` 仍是最终导出网格的实际数量。

相关入口和配置包括 `selectPackageFile`、`openFbxInBlender`、设置页的 Blender 路径，以及 `apps/build-resources/workbench-templates/` 中的打包资源。该工具的详细输入输出约束应继续与 `backend-interface.md` 和打包文档保持一致。

## 11. FBX 应用旋转与缩放

进入某个物品工作区后，物品工具栏中的“应用旋转与缩放”会打开固定流程弹窗。文件选择器和 Electron 都会校验源文件位于当前项目目录且扩展名为 `.fbx`。处理时调用当前设置中的 Blender 和 `apps/build-resources/workbench-templates/blender_transform_fbx.py`，依次执行默认 FBX 导入、只选中 Mesh、Apply Rotation & Scale、检查 Mesh 局部平移并默认 FBX 导出；Armature 的坐标系和单位缩放保持不变，界面不提供额外旋转角度或缩放倍率。

该流程会把 Mesh 的局部平移与 `1e-6` 阈值比较。检测到异常平移时，会将该局部变换烘焙进 Mesh 数据并把 Mesh 的位置、旋转和缩放归零，从而修复 Mesh 与 Armature 错开的情况；没有异常时不会改变 Mesh 的位置。FBX 导出关闭自动叶子骨骼，避免处理过程额外增加骨骼。

勾选“处理前备份原文件”时，源文件同目录会生成唯一的 `_backup.fbx` 副本，结果写入唯一的 `_transformed.fbx`；取消勾选时，脚本先生成临时输出，成功后原子替换源 FBX。处理保留网格、完整骨架（包括导入的末端骨）、蒙皮、材质、UV 和父子层级，结果返回应用前带有非单位旋转/缩放的 Mesh 数、Mesh 总数、Armature 数，以及局部平移异常数、自动修复数和修复的 Mesh 名称。该工具是单文件本地 Electron IPC 操作，发布版通过 `extraResources` 携带 Blender 脚本。

## 12. FBX 纯网格工具

进入某个物品工作区后，物品工具栏中的“FBX 纯网格”会打开处理弹窗。文件选择器默认定位到当前项目目录，Electron 会再次校验所选文件确实位于该目录内且扩展名为 `.fbx`。处理时调用当前设置中的 Blender 和 `apps/build-resources/workbench-templates/blender_remove_fbx_skin.py`：导入 FBX，移除所有 Armature 对象、Armature Modifier 和顶点组，仅导出 Mesh 对象。

勾选“处理前备份原文件”时，源文件同目录会生成唯一的 `原文件_backup.fbx` 副本，并将结果写入 `原文件_mesh-only.fbx`；若结果文件已存在则依次使用 `_mesh-only_1`、`_mesh-only_2` 等后缀。取消勾选时，结果会先写入临时文件，成功后原子替换原 FBX，直接更新原文件。弹窗会显示 Mesh 数量、移除的 Modifier/顶点组数量，并支持定位输出文件。该工具是单文件本地操作，不经过 Python HTTP 任务接口；发布版通过 Electron Builder 的 `extraResources` 携带 Blender 脚本。

## 13. FBX HS2 骨架绑定脚本

物品工具栏中的“绑定 HS2 骨架”会调用 `apps/build-resources/workbench-templates/blender_bind_hs2_skeleton.py`，把 `body.fbx` 中的 HS2 Armature 和骨骼层级加入上一步生成的无骨骼 FBX。弹窗允许选择当前项目内的 Mesh FBX 和项目外的骨架来源。脚本只建立 Mesh 对 Armature 的对象级父子关系，不添加 Armature Modifier，也不创建 Vertex Groups，因此不会改变网格形状或产生蒙皮。

命令行参数为 `--input <无骨骼 FBX> --skeleton <body.fbx> --output <输出 FBX>`。输出建议使用新的文件名，例如 `原文件_with-hs2-skeleton.fbx`；脚本会写入临时文件后再替换目标，输入和骨架文件不会被修改。处理结果会输出 Mesh 数量、骨骼数量、顶点组数量和蒙皮状态。

## 14. 复制 FBX 权重

物品工具栏中的“复制 FBX 权重”用于把已有蒙皮 FBX（例如 `meshes0.fbx`）的权重转移到当前项目内只有骨架的目标 FBX。脚本按骨骼名称匹配来源组与目标 Armature，并为目标每个顶点查找来源网格的最近顶点，使用距离加权合成权重；两个网格不要求顶点数或拓扑一致。

勾选备份时，目标会生成 `_backup.fbx`，结果另存为 `_weights-transferred.fbx`；取消备份时，处理成功后直接原子替换目标文件。导出会烘焙 Mesh 的 FBX 补偿变换为单位变换、把每个顶点限制为最多 4 个权重，并使用稳定的 `Mesh_0` 节点名以兼容 SB3Utility。输出会包含 Armature Modifier 和匹配到的 Vertex Groups，弹窗显示映射组数、写入顶点数和平均最近距离。来源 FBX 可以位于当前项目之外，目标 FBX 必须位于当前项目目录内。

## 15. 当前限制与维护注意

- 工作台工程是本地文件工程，不会在编辑过程中直接进入模组 SQLite 索引；修改工程 CSV 后需要重新打包，打包成功后的 zipmod 才会通过自动增量任务写入模组库数据库。
- 当前数据库模板选择依赖模组库可用状态；没有可读的 `MainAB` Unity3D 或当前物品为地图资源时不能选择。
- Unity3D 预处理使用运行时副本，缓存文件可重新生成，不应把缓存路径当作工程最终资源路径。
- 资源写入是单个物品操作，没有批量导入、批量预处理或批量 CSV 更新入口。
- 删除工程不可恢复；删除物品只删除 CSV 行，但手工删除工程资源可能导致 CSV 的 `MainAB` 失效。
- `MainData` 是 CSV 和 Unity3D 之间的关联键，修改 Unity3D 对象名后必须确认 CSV 最终写入的名称仍然指向有效对象。
- 修改工作台页面、资源流程或工程格式时，应同步检查 `apps/docs/backend-interface.md`、`apps/docs/project-introduction.md`、`apps/docs/project-overview.md` 和本文索引。

## 继续阅读

- [文档索引](../README.md)：按页面、功能和开发任务查找专题文档。
- [前端 UI 专题索引](README.md)：前端页面入口、共享外壳和视觉基线。
- [前后端接口](../backend-interface.md)：HTTP 路由、preload bridge、任务协议和单项/批量边界。
- [项目总览](../project-overview.md)：仓库结构、运行链路、数据模型和开发规则。
- [UI 风格规范](ui-style.md)：工作台继续沿用的资源管理器和像素硬边视觉规则。
