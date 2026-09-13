# 人物卡选择性读取到游戏

## 背景

人物卡浏览器需要把当前选中的 AIS 人物卡读取到 HS2 的角色制作器。该能力使用已有的 `StarManager.GameItemProbe` BepInEx 插件，不引用或加载 `GameBridge.dll`。HTTP 工作线程只接收并排队命令，Unity 对象只在插件 `Update()` 主线程访问。

## 当前实现

人物卡详情的“工具”页签新增“读取到游戏”。首次打开选择窗口时默认勾选以下六项，用户可以取消任意项；选择会作为所有人物卡共用的应用设置持久化，不会在切换人物卡或重新打开窗口时自动恢复为全选：

| 选项 | 写入的原生人物卡区块 |
| --- | --- |
| 脸部 | `ChaFile.custom.face`，包括脸型、眉眼和妆容 |
| 身体 | `ChaFile.custom.body`，包括体型、肌肤、细节和彩绘 |
| 头发 | `ChaFile.custom.hair` |
| 衣服 | `ChaFile.coordinate.clothes` |
| 装饰 | `ChaFile.coordinate.accessory` |
| 人物设定 | `ChaFile.parameter` 和 `parameter2` |

读取区块选择保存在 Electron 用户设置的 `characterCardLoadOptions` 字段中。用户每次勾选或取消选项后立即写入 `settings.json`；未存在该字段的旧设置按六项全选兼容处理。

### 2026-09-12 读取区块选择改为全局持久化

- **背景**：读取弹窗每次打开都会将六个区块重置为全选，用户为不同人物卡重复调整相同选择。
- **根因**：`openCardLoadPrompt()` 直接使用 `CARD_LOAD_OPTIONS` 覆盖当前选择，且选择状态未接入应用设置保存链路。
- **解决方案**：新增规范化设置字段 `characterCardLoadOptions`；应用启动时读取该字段，切换选项后立即保存，打开弹窗时保留当前全局选择。未保存过的旧设置继续默认六项全选。
- **验证结果**：通过前端生产构建、Electron 主进程语法检查和 `git diff --check` 验证；人物卡选择、读取请求构造和游戏侧读取逻辑未改变。
- **适用边界**：该设置对所有人物卡共用，不按人物卡、目录或性别区分；它只控制读取弹窗中的六个区块，不改变人物卡文件内容或后端读取接口。

后端接口为：

```http
POST /game-card-loader/load
Content-Type: application/json
```

请求示例：

```json
{
  "game_dir": "D:\\Games\\HoneySelect 2 DX",
  "path": "female/favorites/example.png",
  "face": true,
  "body": false,
  "hair": true,
  "parameter": false,
  "clothes": true,
  "accessory": false
}
```

后端会校验游戏目录、人物卡路径、性别目录和 `AIS_Chara` 标记，然后转换为插件请求：

```json
{
  "type": "card",
  "path": "UserData/chara/female/favorites/example.png",
  "face": true,
  "body": false,
  "hair": true,
  "parameter": false,
  "clothes": true,
  "accessory": false
}
```

插件收到命令后执行以下流程：

1. 限制路径在游戏根目录的 `UserData/chara/female` 或 `UserData/chara/male` 分支内，并根据目录确定性别。
2. 在当前角色已初始化的 `character.chaFile` 上调用 `ChaFileControl.LoadFileLimited`；该原生方法内部读取临时卡片并把请求中需要的区块写入当前对象。
3. 衣服和装饰共用原生 `coordinate` 读取开关，因此只选择其中一项时先备份并在加载后恢复另一项；脸、身体、头发和人物设定由原生方法按开关写入。
4. 先用 `ChaControl.ChangeNowCoordinate(false, true)` 将 coordinate 同步到当前角色，再复现原生人物卡窗口的 `Manager.Character.customLoadGCClear=false → ChaControl.Reload(...) → customLoadGCClear=true` 调用链。五参数 `Reload` 会按原生方式启动 `ReloadAsync(..., asyncFlags=false)`，在同一条链中调用 `ChangeClothes(true)` 和 `ChangeAccessory(true)`；不再自行拆分或重排服装、装饰协程，也不进入会隐藏角色的 `asyncFlags=true` 路径。命令在原生 `Reload` 调用返回后报告成功，后续贴图/模组资源仍由游戏自己的加载器处理。
5. 返回已有 `/game-item-probe/command?id=...` 可轮询的命令状态。

## 骨骼与覆盖贴图的选择边界（2026-08-29）

界面中看到的“身体骨骼”“面部骨骼”“身体纹理覆盖贴图”和“衣服覆盖贴图”，并不是当前选择性读取接口的四个原生参数。当前接口只接收 `face`、`body`、`hair`、`parameter`、`clothes` 和 `accessory` 六个选择项。它们先决定原生 `ChaFile` 区块，再由角色重载触发相关插件的回调。

实际调用为：

```csharp
target.LoadFileLimited(
    cardPath,
    cardSex,
    command.CardFace,
    command.CardBody,
    command.CardHair,
    command.CardParameter,
    command.CardClothes || command.CardAccessory
);

character.ChangeNowCoordinate(false, true);
Manager.Character.Instance.customLoadGCClear = false;
character.Reload(
    !(command.CardClothes || command.CardAccessory), // noChangeClothes
    !command.CardFace,                               // noChangeHead
    !command.CardHair,                               // noChangeHair
    !command.CardBody,                               // noChangeBody
    true                                             // forceChange
);
Manager.Character.Instance.customLoadGCClear = true;
```

当 `CardClothes` 与 `CardAccessory` 同时为 `true` 时，`noChangeClothes=false`，因此原生 `Reload` 会同时走服装和装饰更新；探针不再额外启动第二套服装/装饰协程。原生调用使用 `asyncFlags=false`，不会进入 HS2 的 `SetActiveTop(false)` 路径。

对应关系如下：

| 关注的数据 | 当前实际选择/处理依据 |
| --- | --- |
| 身体骨骼 | 原生 `body` 区块触发身体重建；如果卡片有 ABMX 扩展，则 `HS2ABMX` 的 `BoneController.OnReload` 读取 `KKABMPlugin.ABMData`，按每条记录的 `BoneName`、`BoneLocation` 和 `CoordinateModifiers` 定位并应用。ABMX 没有独立的 `Face` 骨骼区；`BodyTop` 包含身体和头部但不包含配饰。 |
| 面部骨骼 | 当前没有独立开关，最接近的原生选择是 `face=true`，写入 `ChaFile.custom.face` 并令 `ReloadAsync` 的 `noChangeHead=false`。面部形体数据不是一个独立的骨骼文件。 |
| 身体纹理覆盖贴图 | `HS2_OverlayMods.dll` 中 KSOX 的 `TexType` 区分 `BodyOver`、`BodyUnder`、`FaceOver`、`FaceUnder` 等类型；其 `OverlayStorage` 按 `CoordinateType -> TexType -> texture ID` 选择贴图。 |
| 衣服覆盖贴图 | 同一程序集中的 KCOX 按 `CoordinateType -> clothing ID -> ClothesTexData` 保存数据，通过当前服装部件和对应 Renderer 匹配后应用，不使用 KSOX 的身体 `TexType`。 |

因此，当前方法的选择链是：

```text
UI 六项选择
  -> LoadFileLimited 的原生区块参数
  -> ChangeNowCoordinate / Reload (内部启动 ReloadAsync)
  -> ABMX、KSOX/KCOX 各自按扩展数据键、骨骼名称、贴图类型或服装 ID 处理
```

`StarManager.CharacterCardReadProbe` 只记录这条链路，不负责选择或加载骨骼、覆盖贴图。它通过 `plugin_callback` 记录 ABMX/KSOX 的 `OnReload`，再通过 `scene_snapshot` 读取重载后的 Renderer、材质、贴图和蒙皮骨骼状态。

当前实现没有 `bodyBones`、`faceBones`、`bodyOverlay` 或 `clothesOverlay` 请求字段；截图中的四个名称不能直接当作现有 API 参数使用。

## 安全和适用边界

- 只允许读取单张位于人物卡库中的 AIS 人物卡，拒绝路径穿越、非 PNG、`navi` 分支和非 `AIS_Chara` 文件。
- 卡片性别必须和当前角色制作器角色一致；未进入角色制作器时返回 `not_in_editor`。
- 衣服和装饰在界面上可以独立选择。游戏的原生 `coordinate` 读取粒度是整体区块，但插件只把选中的 `clothes` 或 `accessory` 子对象写入目标，因此不会因选择衣服而覆盖装饰，反之亦然。
- “身体”包含原生身体比例和肌肤数据；当前没有把“皮肤/眼睛覆盖”或未知插件扩展数据伪装成独立字段。
- “身体骨骼”“面部骨骼”在当前程序集没有独立于 `shapeValueBody` / `shapeValueFace` 的原生人物卡区块，因此暂不提供会造成误解的独立开关；它们随对应的身体或脸部区块一起读取。
- 不复制 `status`、`gameinfo`、游戏进度或未知插件扩展数据，避免把角色编辑器之外的运行状态覆盖到当前角色。
- 命令成功表示原生 `Reload` 已被调用并接受资源重载请求；服装、发型和模组资源的后续内部加载仍由游戏处理，界面提示不会承诺所有贴图已经完成。
- 探针仍只监听 `127.0.0.1`。探针端口不携带游戏目录认证，用户需要确认运行中的 HS2 与 Star Manager 当前选择的是同一份游戏目录。

## 验证

- 使用当前 HS2 `Assembly-CSharp.dll` 构建 `StarManager.GameItemProbe`，验证 `LoadFileLimited(string, byte, bool, bool, bool, bool, bool)`、`ChangeNowCoordinate(bool, bool)` 和 `ReloadAsync(bool, bool, bool, bool, bool, bool)` 签名。
- 后端测试覆盖选择项转换、固定探针路径、空选择拒绝和错误返回。
- 前端执行 `npm run build`；插件使用项目文档中的 `dotnet build ... -p:GameDir=...` 命令构建。
- 安装新 DLL 并重启游戏后，仍需在角色制作器中分别验证脸、身体、头发、衣服、装饰和人物参数的实机表现；构建通过不等价于所有游戏资源异步加载完成。

### 2026-08-28 实机测试复盘

首次在 `E:\game\HoneySelect 2 DX - TSYMQ` 的角色制作器中调用旧版 `0.6.0` DLL：探针状态正常（`listControlFound=true`、`itemCount=33050`、当前角色 `sex=1`），但对多张有效女性 AIS 卡提交“仅人物设定”或“仅头发”均返回 `card_load_failed`。

根因是误用了 `ChaFileControl.LoadFileLimited`：HS2 的该方法是“将卡片选中区块加载到当前 `ChaFileControl`”的原地 API，方法内部自己创建临时 `ChaFileControl` 作为读取源；不能在全新的 `ChaFileControl` 上调用它再把结果取出。修复后改为直接在当前角色的已初始化 `character.chaFile` 上调用，并在只选衣服或只选装饰时备份、恢复另一个 coordinate 子区块；同时不再把该方法的返回值当作读取成功标志，因为游戏原生角色卡加载流程本身也忽略这个返回值。

修复版已使用当前游戏程序集构建通过（0 警告、0 错误），但 Windows 不允许在游戏运行时替换已映射的 DLL；必须先保存角色并关闭 HS2，再将新 DLL 放入 `BepInEx/Plugins/StarManager/`，重启后才能继续实机验证。当前尚未宣称修复版已在游戏内成功读取。

### 2026-08-28 卡顿诊断

实机读取成功后出现明显卡顿。当前插件没有在卡片应用后重新执行全量目录扫描：日志中的 `Captured 0 ...` 和 `Captured 33050 ...` 只出现在启动初始化阶段，应用卡片后没有新的 `Captured`；配置中的旧字段 `RefreshSeconds = 5` 也不再被 `0.6.0` 源码读取。

主要开销来自卡片读取后的原生重载链：`LoadFileLimited` 在 Unity 主线程读取并复制区块，随后 `ChaControl.Reload` 会同步执行脸/身体纹理重建、头发、衣服、配饰更新、形体更新和 `UpdateClothesStateAll`。HS2 的五参数 `Reload` 内部将 `asyncFlags` 固定为 `false`，因此这些步骤集中发生在一个主线程帧内；当六个区块全选时尤其明显。若游戏启用了角色加载后的资源清理，还会执行 `Resources.UnloadUnusedAssets` 和 `GC.Collect`，会进一步造成长帧和内存抖动。

本次运行日志还记录了多次完整卡片读取，以及 `AdvIKPlugin`、`EarWiggle`、`EyeControl` 在角色重载回调中的 `InvalidCastException`，并记录了两个 Sideloader 模组资源的 bundle 冲突/空引用错误。这些错误来自其他插件或模组，但会在 `Reload` 触发时放大卡顿；不能把它们归因于 Star Manager 自身。诊断期间进程约占用 4.8 GB 内存，空闲采样约 3.2 个 CPU 核心；该进程级指标包含整个游戏及所有 BepInEx 插件，不能单独作为探针 CPU 占用证明。

本次优化改为复现原生 `ChangeNowCoordinate(false, true) → Reload(...)` 调用链，并按原生方式临时关闭 `customLoadGCClear`。`Reload` 内部使用不隐藏角色的 `ReloadAsync(..., asyncFlags=false)`，再由游戏自己的流程协调服装和配饰；探针不再自行并行或顺序启动额外坐标协程。持续全量扫描不是本次卡顿原因，卡片应用触发的原生重载及其插件回调/资源加载仍可能造成资源切换期间的短暂负载。探针在加载前、调用后和异常路径都会尝试恢复角色顶层对象的显示状态，并在同步调用失败时回滚已选人物卡区块。

### 2026-08-28 服装与配饰读取复测

使用 `female/cloth/闪闪/HS2ChaF_20240222153946175.png` 复测“仅衣服”：探针命令返回 `succeeded`，但调用前后当前角色服装完全相同（`240/100008425`、`241/100008337`、`247/100008365` 等），配饰也保持原值。卡片详情本身包含可匹配的服装 `240/241/245/247` 和配饰 `351/352` 依赖，因此不是卡片没有 coordinate 数据。

根因是当前实现把数据写入 `character.chaFile.coordinate` 后直接调用 `Reload`，遗漏了 HS2 原生人物卡加载流程中的 `character.ChangeNowCoordinate(false, true)`。该调用会把 `chaFile.coordinate` 同步到 `nowCoordinate`；而 `Reload` 的服装/配饰更新读取的是当前 coordinate。修复时必须在恢复未选中的衣服或配饰子区块之后调用该同步方法，再执行重载；否则命令虽然被接受，服装和配饰不会真正切换。

### 0.7.0 修复

插件现在会在恢复未选中的 coordinate 子区块后调用 `ChangeNowCoordinate(false, true)`，随后启动 `ReloadAsync(..., true)`。命令状态会保持为 `executing`，直到游戏协程结束；这样前端不会在资源仍处于重载阶段时误报完成，也能降低人物卡完整读取导致的单帧卡顿。

### 0.7.1 修复角色消失

实机复盘发现，HS2 的 `ReloadAsync(..., asyncFlags=true)` 在第一步调用 `SetActiveTop(false)`，但该协程没有对应的恢复调用。若头发、衣服或配饰的第三方资源协程较慢或抛出异常，当前角色会长期保持隐藏，后续命令也会留在 `queued`。0.7.1 改用 `asyncFlags=false` 的非隐藏调用路径，并在加载前、启动后和异常/完成路径尝试 `SetActiveTop(true)`；如果重载抛出异常，还会恢复本次命令已选区块的旧数据。资源贴图最终可用时间仍取决于游戏和已安装模组。

### 2026-08-28 0.7.1 最终实测

在当前 HS2 角色编辑器中使用 `female/cloth/闪闪/HS2ChaF_20240222153946175.png` 完成接口测试。提交“仅衣服”后命令为 `succeeded`，当前服装切换为 `240/100001859`、`241/100001856`、`242/18`、`243/6`、`245/100001857`、`247/100001858`。随后提交“仅装饰”后命令为 `succeeded`，当前装饰出现于槽位 `0:351/100001855` 和 `1:352/100001854`，服装编号保持不变。用户确认游戏画面中人物、服装和装饰均显示正常；本次验证未保存异常角色状态。

### 2026-09-05 衣服与装饰同时读取修复

- **背景**：单独读取衣服或装饰可以生效，但同时勾选二者时，人物卡中的装饰没有正常出现在当前角色。第一次顺序化尝试直接使用 `asyncFlags=true`，又触发了 HS2 的角色隐藏路径，在第三方资源加载异常或延迟时造成读取后人物模型消失。
- **根因**：`ReloadAsync(..., asyncFlags=false)` 会并行启动 HS2 的服装和装饰资源协程；二者共享当前坐标与资源状态，服装流程可能在装饰流程完成前覆盖或打断装饰更新。另一方面，`asyncFlags=true` 会先调用 `SetActiveTop(false)`，不适合由探针接管的卡片读取流程。人物卡的 `coordinate` 数据和请求字段均已正确传递，问题发生在重载调度阶段。
- **解决方案**：不再使用会调用 `SetActiveTop(false)` 的 `asyncFlags=true` 路径，也不再绕过原生 `Reload` 自行调度服装和装饰。探针复现 `ChangeNowCoordinate(false, true) → customLoadGCClear=false → Reload(...) → customLoadGCClear=true`，由游戏自身以 `asyncFlags=false` 协调服装和装饰；同步调用异常时仍回滚已选区块并恢复角色显示。
- **验证结果**：原生人物卡窗口的 IL 已确认上述调用顺序，且 `Reload` 的第一个参数在衣服或装饰选择时为 `false`。本次代码改动后需重新完成后端人物卡测试和探针编译；安装新 DLL 并重启 HS2 后，再复测“衣服+装饰”组合，重点确认服装和配饰均切换且角色不会长期隐藏。
- **适用边界**：该修复只影响人物卡读取的重载调度，不改变人物卡解析、单独衣服/装饰读取、未选区块保留和卡片文件内容；命令成功仅表示原生重载已启动，最终资源可用时间仍受游戏及已安装模组影响。

### 2026-09-05 恢复原生人物卡重载链

探针在用户执行原生“读取人物卡”后确认，`CvsO_CharaLoad` 并不会由界面先单独调用 `ReloadAsync`，而是调用五参数 `ChaControl.Reload`；该方法内部再启动 `ReloadAsync(false, ...)`，并继续触发 `ChangeClothes(true)` 与 `ChangeAccessory(true)`。此前插件为了避免服装/装饰竞争而自行调用 `ReloadAsync`、`ChangeClothesAsync` 和 `ChangeAccessoryAsync`，导致与原生状态机不同步，也绕过了只补丁 `Reload` 的第三方插件。

本次修复改为：读取区块并恢复未选择的 coordinate 子区块后，调用 `ChangeNowCoordinate(false, true)`，临时设置 `Manager.Character.customLoadGCClear=false`，再按选择项调用原生 `Reload`，最后恢复该标志。`Reload` 的第一个参数只有在衣服或装饰被选择时才为 `false`，从而保持脸、身体、头发和坐标选择的原生语义。插件不再直接调用 `ReloadAsync` 或两个聚合坐标协程，也不使用会隐藏角色的 `asyncFlags=true`。

命令状态在 `Reload` 调用返回后结束，表示原生重载已启动；游戏及第三方插件的后续资源协程仍可能继续运行。需要安装新 DLL 并重启 HS2 后，用同一张同时包含衣服和装饰的卡片实测：服装完整切换、装饰完整切换、再次读取可覆盖当前服装，且角色模型保持可见。

### 2026-09-05 同时选择衣服和装饰的复测

使用 `female/cloth/闪闪/HS2ChaF_20240222153946175.png` 在运行中的 `0.8.0` 插件上复测，卡片原始 `Coordinate` 确认包含服装部件 `888830`、`888831`、`888833`、`888832` 和配饰槽 `0:351/888834`、`1:352/888835`。命令返回 `succeeded`，服装已切换；探针同时记录了原生 `Reload(false, true, true, true, true)`、`ChangeClothes(true)` 和 `ChangeAccessory(true)`，说明重载调用链及请求字段均正确，但 `/api/current` 中配饰仍全部为空。

根因是插件在 `LoadFileLimited` 后恢复未选择的 coordinate 子区块时只判断 `CardClothes`：当衣服和装饰同时选择时，它错误地把读取前的旧 `coordinate.accessory` 恢复回去，覆盖了卡片刚写入的装饰数据。现已改为仅在 `CardClothes=true` 且 `CardAccessory=false` 时恢复旧装饰；仅在 `CardAccessory=true` 且 `CardClothes=false` 时恢复旧服装；两者同时选择时保留卡片的两个区块。

修复版已重新编译通过；由于 HS2 当前仍在运行，尚未替换游戏目录中的 DLL，需关闭并重启游戏后再验证装饰出现、再次读取可覆盖以及人物模型保持可见。
