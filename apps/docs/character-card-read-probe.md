# 独立人物卡读取审计探针

## 背景

插件库页面只能读取 BepInEx DLL 的元数据，不能证明某个插件实际参与了人物卡读取、角色重载、骨骼构建或贴图加载。现有 `StarManager.GameItemProbe` 负责物品映射、换装和人物卡选择性读取，不应承担与其目标不同的运行时审计职责。

因此新增完全独立的 `StarManager.CharacterCardReadProbe`。它不引用、不调用、不修改 `StarManager.GameItemProbe`，也不依赖 Sideloader、HS2API 或 ExtendedSave；ExtendedSave 只在运行时存在可枚举 API 时做反射式观察。

## 当前实现

插件使用 Harmony 监听以下两组方法：

| 观察对象 | 方法 |
| --- | --- |
| 原生卡片数据 | `ChaFile.LoadFile`、`ChaFileControl.LoadFileLimited`、`LoadCharaFile`、`LoadFromBytes` |
| 角色重载/资源切换 | `ChaControl.Reload`、`ReloadAsync`、`ChangeNowCoordinate`、`ChangeClothes`、`ChangeAccessory`、`ChangeHair` |
| 可选资源调用 | `AssetBundle.LoadAsset*`、`LoadAllAssets*`，默认关闭 |
| 目标插件回调 | 运行时反射挂接 `HS2ABMX` 的 `KKABMX.Core.BoneController.OnReload`；挂接 `HS2_OverlayMods` 的 `KoiSkinOverlayX.KoiSkinOverlayController.OnChaFileLoaded`、`OnCoordinateBeingLoaded`、`OnReload` |

每次人物卡方法调用会记录：

- 实际方法签名、参数摘要、线程和耗时；
- 调用前后的 `ChaFile` 原生区块指纹，包括 `custom`、`coordinate`、`parameter`、`parameter2`、`status` 和原始 `pngData` 摘要；
- 发生变化的区块；
- 该方法现有 Harmony 补丁的 owner，用于定位可能介入的插件；
- 若加载失败，记录异常类型和消息。

目标插件回调写入 `recordType=plugin_callback`，分别记录 `started` 和
`completed`/`threw` 两条记录。记录包含目标插件、扩展数据 ID、实际类型/方法、参数、
耗时、Harmony owner，以及通过反射找到的关联角色和 `ExtendedSave` 扩展数据摘要：

```text
GET /api/logs?recordType=plugin_callback&limit=50
```

探针只按程序集名、类型名和回调方法名进行运行时发现，不引用 ABMX 或 KSOX 的 DLL，
因此仍保持独立。当前对应关系为：

```text
ABMX -> HS2ABMX -> KKABMPlugin.ABMData
KSOX -> HS2_OverlayMods -> KSOX
```

### 骨骼与两类覆盖贴图的选择依据

当前人物卡选择性读取接口的选择项仍只有 `face`、`body`、`hair`、`parameter`、`clothes` 和 `accessory`。探针不会把“身体骨骼”“面部骨骼”“身体纹理覆盖贴图”“衣服覆盖贴图”伪装成四个独立的原生读取参数。

- **身体骨骼**：ABMX 从 `KKEx -> KKABMPlugin.ABMData` 取得骨骼修改记录，依据每条记录的目标骨骼名称 `BoneName`、位置分类 `BoneLocation` 和对应坐标的修改值应用。ABMX 的 `BoneLocation.BodyTop` 覆盖身体和头部但排除配饰，并不存在独立的 `Face` 分类。
- **面部骨骼/面部形体**：原生读取只区分 `ChaFile.custom.face` 和 `ChaFile.custom.body`。当前 loader 的 `face=true` 会触发面部区块写入和头部重建，但没有独立的面部骨骼 payload 开关。
- **身体纹理覆盖贴图**：KSOX 使用 `KoiSkinOverlayX.TexType` 选择 `BodyOver`、`BodyUnder`、`FaceOver`、`FaceUnder` 等类型，并在 `OverlayStorage` 中按 `CoordinateType -> TexType -> texture ID` 找到实际贴图。
- **衣服覆盖贴图**：KCOX 使用服装部件标识选择 `ClothesTexData`，再通过当前 Coordinate、服装 ID 和适用 Renderer 应用覆盖贴图。这与 KSOX 的身体/面部 `TexType` 是两套数据结构。

探针观察到的 ABMX/KSOX `OnReload` 是角色重载后的插件处理回调，不表示探针为它们传入了分类选择。是否执行这些处理，取决于对应插件已加载、人物卡或当前 `ChaFile` 存在相应扩展数据，以及原生重载是否触发了插件回调。

人物重载后在第 1、10、30 帧采集当前角色：

- `SkinnedMeshRenderer.bones` 的骨骼名称、层级路径、局部位置、旋转和缩放；
- Mesh 顶点数、绑定姿势数量和蒙皮骨骼数量；
- Renderer、材质、Shader 和常见贴图属性；
- 贴图名称、实例 ID、尺寸和材质属性；
- 角色对象中名称包含 Bone、IK、Pose、ABMX 或 Dynamic 的组件类型统计；
- 如果存在 `ExtendedSave.GetAllExtendedData`，记录扩展数据的安全摘要。

输出为 UTF-8 JSON Lines，默认写入：

```text
<HoneySelect2>/BepInEx/config/StarManager.CharacterCardReadProbe.jsonl
```

插件还提供独立的本地只读 HTTP API，默认绑定 `127.0.0.1:7881`，与 `StarManager.GameItemProbe` 的 `7880` 端口分离：

```text
GET  /api/status
GET  /api/records?limit=50
GET  /api/logs?recordType=method_call&limit=50
POST /api/snapshot
```

`/api/status` 返回插件版本、输出路径、记录序号和 API 信息；`/api/records`/`/api/logs` 返回当前进程最近的诊断记录，完整历史仍以 JSONL 为准；`POST /api/snapshot` 只排队一次主线程场景快照，不执行换装、写卡或资源修改。

## 推荐验证流程

1. 关闭 HS2 中的 Star Manager 物品探针相关测试操作，只保留本审计插件和正常游戏插件。
2. 加载一张基准人物卡，按 `F8` 保存一次当前角色场景快照。
3. 分别制作只改变脸、身体滑块、ABMX 参数、KSOX 纹理、服装或 MaterialEditor 设置的测试卡。
4. 每次只加载一张测试卡，比较 `method_call.changedSections`、Harmony owner 和后续 `scene_snapshot` 的骨骼/材质/贴图指纹。
5. 只有当某个插件 owner、扩展数据变化和运行时资源变化能够对应起来时，才认定该插件实际参与了该数据链路。

## 验证结果和当前边界

首次实机检查发现：插件能被 BepInEx 加载并生成配置文件，但没有生成 JSONL。根因是卡片补丁类的动态目标枚举方法误命名为 `GetTargetMethods`；Harmony 自动识别的约定名称是 `TargetMethods`，导致 `PatchAll` 阶段未完成，人物卡调用和 `F8` 快照都不会被记录。现已修正为 `TargetMethods`，并使用用户提供的 HS2 目录完成实际编译验证：0 个警告、0 个错误。

替换游戏目录中的 DLL 后，需要重新启动游戏；旧的 JSONL 不存在时，插件启动成功后应先写入 `session_started` 记录。启动流程会把 API 启动和 Harmony 方法发现/补丁分开处理，即使某个游戏方法签名不匹配，也应能通过 `/api/status` 查看状态和补丁错误。首次 API 实机测试发现 HS2 运行时不提供 `System.Web.Extensions.dll`，导致服务虽启动但 JSON 响应失败；现已移除该引用并改用插件内置 JSON 序列化器。若仍未生成文件，先查看 BepInEx 日志中是否出现 `Started independent character-card read probe`，再检查配置中的 `JsonlPath`。HTTP API 正常启动时，日志还应包含 `API: http://127.0.0.1:7881/api/status`。

本次实机 API 验证中，新读取人物卡产生了以下调用链：

```text
ChangeNowCoordinate(ChaFileCoordinate, Boolean, Boolean)
ChangeNowCoordinate(Boolean, Boolean)
ReloadAsync(Boolean, Boolean, Boolean, Boolean, Boolean, Boolean)
ChangeClothes(Boolean)
ChangeAccessory(Boolean)
Reload(Boolean, Boolean, Boolean, Boolean, Boolean)
```

调用均完成，没有异常。新增卡片读取前后的场景快照从 `840` 个 Transform、`68` 个 Renderer、`28` 个贴图对象变为最终 `908` 个 Transform、`66` 个 Renderer、`32` 个贴图对象；`boneSha256` 从 `447804a5...a5019cb` 变为 `9f21d666...679dc0`，`textureSha256` 从 `0b0980e2...a0a9e0b1` 变为 `247cfc48...bf198148`，说明运行时骨骼和贴图引用均发生了变化。

这次方法记录中没有直接出现 `ChaFile.LoadFile` 或 `LoadFileLimited`，因此当前实机证据表明角色卡进入场景后的关键资源重建链是 `ChangeNowCoordinate -> ReloadAsync/Reload -> ChangeClothes/ChangeAccessory`；卡片 PNG 的最初文件解析入口可能在探针启动前完成，或由尚未覆盖的方法完成，不能仅凭本次记录断定 PNG 读取入口。

本次记录的 Harmony owner 包括探针自身、`harmony-auto-9f9c339d-7c07-47ec-9699-fd83cf84c970`、`com.joan6694.illusionplugins.moreaccessories` 和 `com.bepis.bepinex.sliderunlocker`。通过当前游戏目录的 `HS2API.dll` XML 可将 `harmony-auto-...` 的 `ChaControl_ChangeNowCoordinatePreHook`、`CharaData_InitializePost` 和 `ReloadAsyncPostHook` 映射到 BepInEx 的 `Modding API`（GUID `marco.kkapi`）；它负责扩展数据/角色事件钩子，不是骨骼或贴图元数据读取器。`MoreAccessories` 只出现在 `ChangeAccessory` 的补丁 owner 中，`Slider Unlocker` 只出现在 `Reload` 的补丁 owner 中。owner 只表示这些插件给相关方法打过补丁，仍需结合单变量人物卡和指纹变化判断实际影响。

新增的目标插件回调观察已通过真实游戏目录编译并安装到
`E:\game\HoneySelect 2 DX - TSYMQ\BepInEx\Plugins\StarManager\`；编译结果为 0 个警告、0 个错误。
重启游戏后，`session_started.pluginCallbackTargets` 应列出实际成功挂接的 ABMX/KSOX 方法；
重新加载人物卡后，`/api/logs?recordType=plugin_callback` 或 JSONL 中应出现对应回调的
`started` 与 `completed` 记录。

本次 DLL 更新后的实机验证已经完成：`/api/status` 返回探针版本 `0.2.0`，当前序号为 `65`；
`session_started.pluginCallbackTargets` 成功列出以下两个目标，没有挂接错误：

```text
KSOX  -> KoiSkinOverlayX.KoiSkinOverlayController.OnReload
ABMX  -> KKABMX.Core.BoneController.OnReload
```

用户本次读取人物卡后的最近一轮重载中，API 返回了 16 条 `plugin_callback` 记录，即 ABMX/KSOX
各出现一次 `started` 和 `completed`。最近的完成记录为：

```text
KSOX  OnReload  completed  35.660 ms  gameObject=chaF_001  exception=none
ABMX  OnReload  completed   8.954 ms  gameObject=chaF_001  exception=none
```

ABMX 完成回调的状态摘要包含 `ModifierDict.count=1`（`BodyTop`）和
`Modifiers._items.length=18`，说明该次回调中已存在这张卡对应的 18 个骨骼修改器；KSOX
完成回调包含 `OverlayStorage` 状态。当前安装版本中 `OnChaFileLoaded` 和
`OnCoordinateBeingLoaded` 没有发现可挂接的方法，因此本次以两个插件的 `OnReload` 回调作为
实际执行证据。BepInEx `LogOutput.log` 同时记录了探针启动时成功观察 2 个插件回调目标。

骨骼和贴图元数据是 `StarManager.CharacterCardReadProbe` 自己通过 Unity 的 `SkinnedMeshRenderer.bones`、`Renderer.materials` 和材质纹理属性读取的；HS2 原生 `Assembly-CSharp.dll` 中的 `ChaControl` 方法负责实际角色资源重建。由于 `TraceAssetBundleLoads=false`，当前证据确认的是贴图对象已经进入材质后的状态，不等同于确认某个插件执行了贴图文件读取。

构建时必须使用真实游戏目录：

```powershell
cd apps
dotnet build tools/star-manager-character-card-read-probe/StarManager.CharacterCardReadProbe.csproj `
  --configuration Release `
  -p:GameDir="E:\game\HoneySelect 2 DX - TSYMQ"
```

插件只读取元数据和运行时对象，不导出贴图像素，不复制人物卡字节，不修改角色或模组资源。`ReloadAsync` 是协程，三次延迟快照只能说明不同时间点的资源状态，不能单独证明最终加载已完成。动态骨骼插件的私有粒子状态也不一定等于 `SkinnedMeshRenderer.bones`，仍需结合目标插件自身的扩展数据或补丁逻辑判断。
