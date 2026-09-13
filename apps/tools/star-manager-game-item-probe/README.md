# Star Manager Game Item Probe

## 本次实现摘要

本插件源于对 GameBridge 物品映射方式的调查：zipmod 的 GUID、CSV `slot`、`kind` 和名称与游戏运行时使用的 `localSlot` 并不等价。插件通过读取 `ChaListControl` 和 UniversalAutoResolver 输出精确映射，并提供主线程换装接口。

当前版本为 `0.9.0`。完整目录约包含 33000 个游戏物品和 83000 条 UAR 记录，因此目录只在首次初始化成功或手动刷新时扫描；角色状态独立轻量更新，避免周期性卡顿。角色编辑器和 H 场景角色都使用相同的状态读取模型。人物卡读取会先同步当前 coordinate，再触发游戏自身的分段资源加载；探针不会隐藏角色，也不会等待第三方资源协程，避免资源异常时角色长期消失或命令队列卡死。

这是一个 HS2 BepInEx 探针插件，用于回答“游戏原生物品界面当前这一项究竟对应什么”，并提供受控的主线程换装命令接口。它不依赖物品名称作为主键。

## 输出内容

插件在游戏主线程读取两类运行时数据：

- `ChaListControl.GetCategoryInfo(...)` 的原生列表项。这里的 `localSlot`/`resolvedId` 是游戏当前实际使用的 ID，`kind` 是列表/CSV 中的原始物品编号，并输出 `MainAB`、`MainData`、缩略图字段及完整 `dictInfo`。
- `UniversalAutoResolver.LoadedResolutionInfo`。这里输出 `guid`、原始 `slot`、当前 `localSlot`、`property`、`categoryNo`、模组作者、版本、网站和 zipmod 路径。

两者按 `categoryNo + localSlot` 合并。一个本地 ID 若对应多条 UAR 记录，JSON 会保留全部 `resolverRecords`，不会自动按名称猜测。

角色制作器和 H 场景中的角色都会输出其头发、服装、面部、身体和配饰部件的 `categoryNo + localSlot`，用于核对“当前装配”和物品列表。角色制作器状态位于 `/api/current` 的 `hairs`、`clothes`、`faces`、`bodies` 和 `accessories` 数组；H 场景角色的同结构状态位于 `/api/context` 返回的每个角色 `current` 对象中。面部/身体数组只扩展当前角色状态，不会把非服装资源加入 `/api/items` 的完整目录扫描。

### 头发栏位映射

HS2 的 `ChaControl.ChangeHair(Int32 kind, Int32 id, Boolean forceChange)` 使用 `ChaFileHair.parts` 的索引作为 `kind`。物品类别和目标栏位固定对应：

| CategoryNo | hairSlotNo / kind | 栏位 |
| --- | ---: | --- |
| `300` (`so_hair_b`) | `0` | `HairBack` / 后发 |
| `301` (`so_hair_f`) | `1` | `HairFront` / 前发 |
| `302` (`so_hair_s`) | `2` | `HairSide` / 侧发 |
| `303` (`so_hair_o`) | `3` | `HairOption` / 扩展发 |

插件和 Star Manager 都会拒绝类别与 `hairSlotNo` 不匹配的请求；头发栏位不是 `localSlot`，也不是可以按名称猜测的字段。

服装当前状态按 `ChaFileCoordinate.parts` 的通用栏位索引读取：男性为 `0→140`、`1→141`、`4→144`、`7→147`，女性为 `0..7→240..247`；男性手套和鞋不会按紧凑数组索引误判。

面部物品使用 `type: "face"`。脸型、脸部肌肤/细节、胡子、眉毛、睫毛、眼影、眼睛高光、腮红、口红和痣/雀斑按类别直接提交；美瞳 `317` 和瞳孔 `318` 需要 `facePartNo`（`0` 为左眼，`1` 为右眼）：

```json
{"type":"face","facePartNo":1,"categoryNo":317,"localSlot":100000291}
```

身体物品使用 `type: "body"`。男性支持 `8`（身体彩绘布局）、`131`（肌肤）、`132`（细节）、`133`（晒痕）；女性支持 `231`（肌肤）、`232`（细节）、`233`（晒痕）、`313`（身体彩绘类型）、`334`（乳头）和 `335`（阴毛）。`8`/`313` 必须提供 `bodyPartNo`（`0` 为彩绘层 1，`1` 为彩绘层 2）：

```json
{"type":"body","bodyPartNo":1,"categoryNo":313,"localSlot":100000291}
```

男性 `8` 写入 `paintInfo[index].layoutId`，女性 `313` 写入 `paintInfo[index].id`；肌肤、细节、晒痕、乳头和阴毛分别使用对应的原生身体刷新路径。

## 构建

从 `apps/` 的上级目录执行：

```powershell
dotnet build tools/star-manager-game-item-probe/StarManager.GameItemProbe.csproj `
  --configuration Release `
  -p:GameDir="E:\game\HoneySelect 2 DX - TSYMQ"
```

或在其他游戏目录上构建：

```powershell
dotnet build tools/star-manager-game-item-probe/StarManager.GameItemProbe.csproj `
  --configuration Release `
  -p:GameDir="D:\path\to\HoneySelect2"
```

产物：

```text
apps/tools/star-manager-game-item-probe/bin/Release/net472/StarManager.GameItemProbe.dll
```

## 安装和使用

将 DLL 放到：

```text
<HoneySelect2>/BepInEx/Plugins/StarManager/StarManager.GameItemProbe.dll
```

启动游戏并等待角色制作器/列表初始化，然后访问：

```text
http://127.0.0.1:7880/api/status
http://127.0.0.1:7880/api/items?category=240
http://127.0.0.1:7880/api/item?category=240&localSlot=100017053
http://127.0.0.1:7880/api/resolve?category=240&localSlot=100017053
http://127.0.0.1:7880/api/current
http://127.0.0.1:7880/api/context
```

插件首次检测到游戏列表初始化完成时，会在游戏主线程执行一次完整目录扫描。之后不会自动重复扫描；`/api/refresh` 才会请求下一帧手动重建完整目录：

```text
http://127.0.0.1:7880/api/refresh
```

当前角色的服装和配饰状态与静态目录分开处理，会以较轻量的轮询更新；这不会重新遍历全部物品和 UAR 记录。换装命令成功后也只刷新当前角色状态。

### 当前场景和 H 场景角色枚举

`GET /api/context` 是只读接口，由插件在 Unity 主线程定期刷新缓存。`scene` 的值为：

- `editor`：当前角色制作器中的角色可用；角色信息位于 `editor`。
- `hscene`：当前存在活动 H 场景；角色信息位于 `hscene.females` 和 `hscene.males`。
- `none`：当前无法识别角色制作器或活动 H 场景。

H 场景数组只返回非空角色槽位。每个角色包含 `characterIndex`（对应原始
`GetFemales()`/`GetMales()` 数组下标）、`characterId`（`ChaControl.chaID`）、
`sex`、`characterName`、`characterFileName` 和 `active`。`femaleCount`、`maleCount`
和 `totalCount` 是实际返回的角色数量，不是 H 场景内部预留槽位数：

```json
{
  "available": true,
  "scene": "hscene",
  "editor": { "available": false, "characterIndex": -1, "characterId": 0, "sex": -1 },
  "hscene": {
    "available": true,
    "femaleCount": 1,
    "maleCount": 1,
    "totalCount": 2,
    "females": [{
      "available": true,
      "active": true,
      "characterIndex": 0,
      "characterId": 12345,
       "sex": 1,
       "characterName": "女性角色",
       "characterFileName": "female.png",
       "current": {
         "available": true,
         "source": "hscene",
         "characterId": 12345,
         "sex": 1,
         "hairs": [],
         "clothes": [],
         "faces": [],
         "bodies": [],
         "accessories": []
       }
    }],
    "males": [{
      "available": true,
      "active": true,
      "characterIndex": 0,
      "characterId": 67890,
       "sex": 0,
       "characterName": "男性角色",
       "characterFileName": "male.png",
       "current": {
         "available": true,
         "source": "hscene",
         "characterId": 67890,
         "sex": 0,
         "hairs": [],
         "clothes": [],
         "faces": [],
         "bodies": [],
         "accessories": []
       }
    }]
  }
}
```

应用提交 H 场景服装时应使用该接口返回的 `sex`、`characterIndex`，并建议同时
带上 `targetCharacterId`。插件执行命令时会重新查找当前 H 场景并校验两种身份，
避免场景切换或角色槽位变化后换错角色。

每个 H 场景角色还包含 `current` 对象，其字段与 `/api/current` 相同：`source`、
`characterId`、`sex`、`characterName`、`characterFileName`、`coordinateName` 以及
`hairs`、`clothes`、`faces`、`bodies`、`accessories`。因此调用方可以先选择角色，
再直接复用角色编辑器的栏位展示、`CategoryNo + localSlot` 映射和缩略图逻辑。

### 主线程换装接口

HTTP 工作线程只负责解析请求并入队，真正的 Unity 调用在插件 `Update()` 中执行。提交接口只接受 POST：

```http
POST http://127.0.0.1:7880/api/apply
Content-Type: application/json

{"type":"clothes","categoryNo":240,"localSlot":100016311}
```

服装也可以使用 GUID、类别和 CSV 原始 `slot`，由游戏当前 UAR 表严格解析 `localSlot`：

```json
{"type":"clothes","guid":"hyman.cloth.jinqipao","categoryNo":240,"slot":1}
```

### H 场景单件物品替换

H 场景中的角色不由 `CharaCustom.CustomBase.chaCtrl` 管理，而是由活动的
`HScene` 持有。探针支持通过 `target: "hscene"` 明确指定 H 场景目标：

```json
{
  "type": "clothes",
  "target": "hscene",
  "sex": 1,
  "characterIndex": 0,
  "categoryNo": 240,
  "localSlot": 100008284
}
```

其中 `sex=1` 表示女性并从 `HScene.GetFemales()` 取角色，`sex=0` 表示男性并从
`HScene.GetMales()` 取角色；`characterIndex` 是对应数组下标，不是人物卡 ID。
也可以使用 `targetCharacterId` 按 `ChaControl.chaID` 定位；同时提供两者时，探针会
要求它们指向同一个角色。模组物品仍可使用 `guid + categoryNo + slot`，探针会先通过
UniversalAutoResolver 解析为当前游戏的 `localSlot`。

H 场景服装路径只执行这一条原生调用：

```csharp
targetCharacter.ChangeClothes(kind, localSlot, false);
```

不会调用整卡 `LoadCharaFile`、`ChangeNowCoordinate` 或 `Reload`，因此不会替换人物、
动作状态和 H 场景控制器引用。H 场景目标现在也接受 `hair`、`face`、`body` 和
`accessory`，分别复用角色编辑器的原生单件更新方法；人物卡 `type: "card"` 仍然
只允许角色编辑器目标。Star Manager 装配模式会在右侧角色选择器中列出 H 场景角色，
选中后复用同一组栏位和换装逻辑。

配饰需要额外提供角色配饰槽 `slotNo`（`0..19`）：

```json
{"type":"accessory","slotNo":0,"categoryNo":361,"localSlot":100000291}
```

头发需要额外提供与类别匹配的 `hairSlotNo`（`0..3`）：

```json
{"type":"hair","hairSlotNo":0,"categoryNo":300,"localSlot":100000291}
```

选择性读取人物卡也使用这个主线程命令队列，但不会把卡片整体覆盖到当前角色：

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

`path` 必须位于游戏根目录的 `UserData/chara/female` 或 `male` 下，且性别必须与当前角色制作器角色一致。插件在当前角色的 `ChaFileControl` 上调用原生 `LoadFileLimited`，服装/配饰区块随后通过 `ChangeNowCoordinate(false, true)` 同步到当前坐标，再复现原生的 `customLoadGCClear=false → Reload(...) → customLoadGCClear=true` 调用链。五参数 `Reload` 内部按游戏原生方式启动不隐藏角色的 `ReloadAsync(..., asyncFlags=false)`，并负责服装、装饰及其它已选区块的资源重载；插件不再直接调用 `ReloadAsync`、`ChangeClothesAsync` 或 `ChangeAccessoryAsync`。未勾选的区块不会写入当前角色；服装和配饰在插件内可以独立选择，即使游戏原生 `coordinate` 区块需要一起读取，也不会把未选择的另一部分复制过去。命令在原生重载调用返回、资源加载请求已启动后结束。

提交成功返回 `202` 和 `commandId`；再查询：

```text
GET /api/command?id=<commandId>
```

命令状态为 `queued`、`executing`、`succeeded`、`failed` 或 `expired`。换装成功后会自动请求下一帧轻量刷新当前角色状态，不会重建完整物品快照。错误会通过 `errorCode` 区分，例如 `not_in_editor`、`invalid_category`、`item_not_found`、`ambiguous_mapping`、`invalid_accessory_slot`、`invalid_hair_slot`、`invalid_body_slot` 和 `execution_error`。

端口可以在 BepInEx 配置文件中修改。服务只绑定 `127.0.0.1`，换装仅接受 POST，不提供 GET 写操作。

## 与 GameBridge 的关系

GameBridge 当前使用的 `zipInfo` 适合查询某个已知 resolved ID，但它没有把完整的原生 `ListInfoBase` 和 UAR 记录全部暴露出来。本探针提供的是调试/集成用的补充接口；Star Manager 后续可以用 `categoryNo + localSlot` 从游戏侧取精确记录，再把浏览器中的数据库物品映射到游戏实际 ID。

## 边界

- 探针默认覆盖男性/女性服装、头发、面部、身体和 13 个配饰类别；身体类别已加入 `/api/items` 的完整目录扫描，当前角色身体状态通过 `/api/current.bodies` 返回。面部和身体换装使用当前角色的 `ChaFileFace`/`ChaFileBody` 和原生更新方法。
- 原版物品可能没有 UAR 记录，此时 `resolverRecords` 为空，但原生列表字段仍然有效。
- 角色制作器未初始化时，`/api/current` 会返回 `available=false`；列表初始化后插件会自动执行一次完整扫描，也可以调用 `/api/refresh` 手动重扫。
- 默认换装目标是角色制作器当前的 `CharaCustom.CustomBase.chaCtrl`；传入 `target: "hscene"` 时改为活动 H 场景的 `GetFemales()`/`GetMales()` 角色数组。H 场景角色的服装、头发、面部、身体和配饰状态通过 `/api/context` 中每个角色的 `current` 返回。
- `localSlot` 必须存在于当前 `ChaListControl`；GUID 方式必须同时提供原始 CSV `slot`，且只能解析出一个 `localSlot`，否则返回 `ambiguous_mapping`。
- 配饰的 `slotNo` 是角色身上的配饰槽位，不是物品的 `localSlot`；接口限制为 `0..19`。
- 头发的 `hairSlotNo` 是 `ChaFileHair.parts` 的目标索引，不是物品的 `localSlot`；接口限制为 `0..3`，并且必须与 `categoryNo 300..303` 的固定映射一致。
- 身体的 `bodyPartNo` 只用于 `8`/`313` 身体彩绘，接口限制为 `0..1`；男性 `8` 使用布局 ID，女性 `313` 使用纹理 ID，身体类别仍必须与当前角色性别匹配。
- 当前调用的是游戏原生 `ChaControl.ChangeClothes(..., false)` / `ChangeAccessory(..., false)` / `ChangeHair(..., false)` 以及面部的 `ChangeHead`、面部类别刷新和 `CreateFaceTexture`。换装后资源加载仍受游戏和模组异步加载状态影响，调用方应轮询命令状态和 `/api/current`。
- `type: "card"` 使用当前探针已有的 `ChaFileControl.LoadFileLimited`、`ChangeNowCoordinate` 和 `ChaControl.Reload`（内部启动原生 `ReloadAsync`），不依赖 `GameBridge.dll`；读取接口只接受位于游戏 `UserData/chara/female` 或 `male` 分支中的 PNG。
- 人物卡读取的 `face`、`body`、`hair`、`parameter`、`clothes`、`accessory` 是独立选择项；插件不复制 `status`、游戏进度或未知插件扩展数据。
- 这些选择项不是“身体骨骼”“面部骨骼”“身体纹理覆盖贴图”或“衣服覆盖贴图”的独立开关。身体/面部分别通过原生 `custom.body` / `custom.face` 及重载参数处理；ABMX 依据 `KKABMPlugin.ABMData` 中的骨骼名称和 `BoneLocation` 应用骨骼修改；KSOX 依据 `TexType` 应用身体/面部覆盖贴图；KCOX 依据服装 ID 和 Renderer 应用衣服覆盖贴图。详细边界见 `apps/docs/game-card-loading.md`。
- `0.8.0` 根据人物卡读取审计探针恢复原生 `ChangeNowCoordinate(false, true) → Reload(...)` 调用链；`Reload` 的第一个参数按衣服/装饰是否选择设置，并在调用前后同步 `Manager.Character.customLoadGCClear`。人物卡读取不再直接调用 `ReloadAsync` 或额外的服装/装饰协程，避免与原生状态机及 `Reload` 的第三方补丁脱节；异常路径仍会回滚已选区块并尝试恢复角色显示。
- 2026-09-05 复测发现，衣服和装饰同时选择时，coordinate 子区块保护逻辑错误地恢复了旧装饰，导致原生 `ChangeAccessory(true)` 虽被调用但卡片装饰不在当前角色中。现已改为仅在单独读取衣服时恢复旧装饰、单独读取装饰时恢复旧服装；同时选择两者时保留卡片的完整 coordinate 数据。修复版已编译，需重启游戏后实测。
 - `0.9.0` 增加 H 场景角色枚举、完整当前装配读取和目标换装。通过 `Manager.HSceneManager.Instance.Hscene` 获取活动场景，再按 `sex + characterIndex` 调用 `GetFemales()`/`GetMales()`；服装、头发、面部、身体和配饰分别复用对应的原生单件更新路径，不执行整卡替换或 H 场景重载。程序集级编译已验证；需要重启游戏后在目标 H 场景中实测女性、男性及模组资源加载结果。
