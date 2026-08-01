# 工作台布局

## 目标

工作台用于承载不依赖当前 HS2 游戏目录的模组制作辅助工具。页面采用“工具目录 + 当前工序”的双栏布局，新工具应作为独立工序卡继续扩展，不把制作能力堆入模组管理详情抽屉。

## 当前工具

### Sims 4 Package → FBX

- 通过 Electron 原生文件选择器选择一个 `.package` 文件。
- 自动读取设置中的“通用导出目录”；用户在工作台更换目录后会立即持久化为新的默认值，切换页面或重启应用时无需重新选择。
- 后端读取 DBPF 2.x 索引，以及其中的 GEOM 和 RLE2 资源。
- 按 GEOM instance ID 对不同模型族分组，每组只选择顶点数最多的资源作为 LOD0。
- 输出 FBX 7.4，保留顶点、三角面、法线和所有 UV 集；配置 Blender 时会临时读取 GEOM 原始四骨骼蒙皮权重以完成姿势固化，但最终 FBX 不保留这些权重。
- 应用内置从 Sims 4 Studio 工程清理得到的 `ts4_reference_rig.fbx`，包含 165 根 TS4 骨骼且不包含参考网格或动画。配置 Blender 后，导出阶段按小写 FNV32 骨骼哈希临时还原 GEOM 原始蒙皮；不读取或依赖 `.blend` 工程，也不再加载或映射 HS2 骨架。
- 内置模板的源静止姿势是 A-Pose，肩到肘相对水平线平均向下约 `44.9°`。完成临时绑定后，导出器将左右上臂连同后代骨骼和网格旋转到 HS2 的肩—肘—手腕水平参考线，并把变形后的网格固化为 T-Pose。随后删除 Armature、全部顶点组和蒙皮修改器，最终 FBX 只包含 T-Pose 模型网格。
- 参照 HS2 `body.fbx` 使用 Y-up、+Z front 和厘米单位：TS4 GEOM 顶点统一放大 10 倍，并将 FBX `UnitScaleFactor` 设为 `1.0`。Blender 导入后模型会自动转换为 Z-up、-Y front，世界尺寸与 HS2 模特一致。
- 将所有支持的 DXT5 RLE2 色板解码为 `textures/*.png`，不丢弃非默认色板。
- 每个 FBX 根据资源索引距离选择一张默认色板，通过外部 Material / Texture / Video 引用加载 PNG；建模软件中可以换用同目录内的其他色板。
- 导出前按模型族归属收集漫反射色板，将 Alpha 覆盖布局一致的色板合并为覆盖蒙版；第一套 UV 在所有这些色板中都没有非透明像素的三角面会被删除，随后同步清理未引用的顶点、法线和全部 UV 数据。若判断会删除整个模型，则保留原网格并在 manifest 中记录原因。
- 每次操作在目标目录中创建新的防冲突结果文件夹，不覆盖旧导出。
- T-Pose 固化不会改变既有的 HS2 尺寸与坐标换算；删除骨骼和蒙皮后，服装仍与 HS2 参考模特保持相同的世界比例、朝向和位置基准。
- 结果区显示导出模型、已固化 T-Pose 的纯网格、PNG 贴图数量、GEOM 和跳过低模的数量，并明确标记最终 FBX 无骨骼、无蒙皮；工作台不提供应用内 3D 预览。
- 每个 FBX 结果同时提供“Blender 打开”和“定位”操作。未配置 Blender 时，前一操作引导到设置页；配置完成后，Electron 启动 Blender、清空启动场景并导入对应 FBX。该会话明确启用简体中文界面，且不通过恢复出厂设置破坏用户已有的 Blender 偏好。
- Blender 导入完成后自动选中首个网格、第一套 UV 和连接到 Principled BSDF `Base Color` 的贴图节点，并将该图片分配给所有 UV/Image Editor 工作区，进入“UV 编辑”时直接显示默认色板。

## 限制

- 配置 Blender 时，最终 FBX 为已固化 T-Pose 的纯网格，不包含任何 TS4/HS2 骨骼、顶点组、蒙皮、blend shape 或动画。
- 未在设置页配置 Blender 时仍允许导出保持 HS2 尺寸与坐标的静态 FBX，但不会执行从 A-Pose 到 T-Pose 的姿势固化，并会在结果中明确标记。
- GEOM 使用的骨骼哈希如果不在内置 165 骨骼模板中，绑定阶段会停止并报告缺少的哈希，避免静默丢失权重。
- 贴图作为外部 PNG 文件保存，不嵌入 FBX；默认色板通过资源索引接近度推断，复杂 Package 中可能需要在建模软件里手动换用其他已导出的色板。
- 支持 TS4 DBPF 2.x 完整索引和共享 TGI 字段索引，以及未压缩或 zlib 压缩资源。
- 单个 package 属于单文件操作，使用直接 HTTP 路由；未来对目录批量提取时必须使用 `/tasks`。

## 桌面与后端边界

- `selectPackageFile(title)`：选择 Sims 4 `.package` 文件。
- `selectDirectory(title)`：选择结果输出目录。
- `POST /tools/sims4/package-fbx`：执行单 package 的 LOD0 FBX、GEOM 蒙皮与 RLE2 PNG 提取；配置 Blender 时用内置 TS4 骨架临时完成 T-Pose 固化，随后清除骨骼与蒙皮并导出纯网格。
- `openDirectory(path)` / `showItemInFolder(path)`：打开结果目录，或定位单个 FBX / PNG。
- `openFbxInBlender(blenderPath, fbxPath)`：使用设置页持久化的 `blender.exe` 路径导入一个 FBX；启动工作目录固定为 FBX 所在目录，以保留 `textures/*.png` 相对引用。
