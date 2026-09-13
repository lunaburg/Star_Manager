# 游戏物品运行时探针

## 本次对话的关键结论与变更记录

本专题记录了“从 Star Manager 外部浏览物品并让 HS2 角色制作器或 H 场景角色换装”的调查、实现和验证结果。当前已完成 Star Manager 前端接入；结论如下：

1. zipmod 的 `guid`、`kind`、名称或 CSV `item_id` 不是可以直接传给游戏换装方法的唯一运行时 ID。
2. GameBridge 实际依赖游戏当前的 `CategoryNo + localId`，再通过 `ChaListControl` 和 UniversalAutoResolver 补齐原始槽位及模组信息。
3. 已新增独立的 `StarManager.GameItemProbe` 主线程换装接口，避免探针依赖 GameBridge DLL。
4. 已修复原先每 5 秒全量扫描导致的周期性卡顿：静态目录只在首次初始化成功或手动 `/api/refresh` 时扫描；当前角色状态单独轻量更新。
5. 已在当前 HS2 游戏中实际调用接口，将角色上衣切换到原生物品后又恢复为原来的模组服装，两个命令均返回 `succeeded`。
6. 已确认 HS2 `ChaControl.ChangeHair(Int32 kind, Int32 id, Boolean forceChange)` 的真实签名；头发类别与 `ChaFileHair.parts` 栏位一一对应，探针 `0.5.0` 支持固定栏位换装和面部/身体当前状态读取。
7. `0.8.0` 已增加面部物品换装：脸型、脸部肌肤/细节、胡子、眉毛、睫毛、眼影、美瞳、瞳孔、眼睛高光、腮红、口红和痣/雀斑均通过当前 HS2 原生面部更新路径提交；美瞳和瞳孔必须显式指定左眼或右眼。
8. `0.9.0` 已增加身体物品换装：身体肌肤、身体细节、身体晒痕、身体彩绘、乳头和阴毛均使用当前 HS2 原生身体更新路径；身体彩绘必须显式指定彩绘层。
9. `0.9.0` 已增加 H 场景单件物品目标：通过 `HScene.GetFemales()`/`GetMales()` 定位角色，支持服装、头发、面部、身体和配饰的单件换装，不执行整卡替换。
10. `0.9.0` 已增加 `GET /api/context`，用于枚举当前场景、角色制作器角色以及 H 场景中的女性/男性角色槽位，并返回每个角色的完整当前装配状态。

### 装配模式的产品约定

本次对话进一步明确了物品浏览器与运行时探针的交互边界：

- 装配模式右侧展示角色编辑器的实际服装、头发、面部、身体和配饰栏位；点击栏位后由 Star Manager 用该栏位的 `CategoryNo` 筛选左侧物品。
- 筛选结果的表格行和紧凑卡片支持左键直接换装，不需要先打开右键菜单；普通物品浏览仍使用右键菜单作为换装入口。
- 头发栏位不可跨槽位装配：前发物品不能改装到后发、侧发或扩展发，界面直接显示对应栏位名称，不提供跨槽位的禁用选项。
- 服装必须显示具体栏位名；配饰必须保留实际角色槽位映射。面部和身体栏位都可以读取、筛选和提交对应物品换装；身体彩绘需要额外选择彩绘层。
- 运行时请求仍必须经过类别、栏位和物品 ID 校验；模组物品还必须经过 GUID + CSV slot 映射，原版物品使用已索引的 `CategoryNo + localSlot`。配饰和头发仍分别校验 `slotNo`/`hairSlotNo`；左键入口只是交互方式变化，不降低探针的安全校验。

### 调查到的运行时映射

GameBridge/探针使用的可靠映射链为：

```text
ChaControl.nowCoordinate 中的当前 ID
  + CategoryNo
  -> ChaListControl.GetListInfo(category, localId)
  -> UniversalAutoResolver.LoadedResolutionInfo / TryGetResolutionInfo
  -> GUID + CSV 原始 Slot + LocalSlot + Property
```

其中：

- `localSlot`/`resolvedId` 是当前游戏实际使用的 ID，换装时应传这个值；
- `slot` 是 zipmod CSV 中的原始槽位，不能当作 `localSlot` 使用；
- `kind`、`listId` 和名称是列表或显示信息，不足以独立完成跨模组唯一映射；
- 同一个 `categoryNo + localSlot` 可能出现多个 UAR 记录，探针会保留全部候选；
- GUID + `categoryNo` + 原始 `slot` 若解析出多个不同 `localSlot`，接口拒绝执行并返回 `ambiguous_mapping`；
- 原版物品通常没有 UAR 记录，此时可以直接使用原生列表中的 `categoryNo + localSlot`。

头发的类别/栏位映射已经通过当前 HS2 的 `Assembly-CSharp.dll` 反射确认：

| CategoryNo | `ChaFileHair.parts` kind | 游戏栏位 | `ChangeHair` 调用含义 |
| --- | ---: | --- | --- |
| `300` (`so_hair_b`) | `0` | `HairBack` / 后发 | `ChangeHair(0, localSlot, false)` |
| `301` (`so_hair_f`) | `1` | `HairFront` / 前发 | `ChangeHair(1, localSlot, false)` |
| `302` (`so_hair_s`) | `2` | `HairSide` / 侧发 | `ChangeHair(2, localSlot, false)` |
| `303` (`so_hair_o`) | `3` | `HairOption` / 扩展发 | `ChangeHair(3, localSlot, false)` |

这里的 `categoryNo` 是物品所属的游戏分类，`hairSlotNo` 是明确的目标栏位索引；当前实现要求两者必须匹配，不能把类别 300 的物品提交到栏位 1。

服装当前状态读取使用 `ChaFileCoordinate.parts` 的通用栏位索引，而不是把返回数组压缩成连续类别：男性为 `0→140`、`1→141`、`4→144`、`7→147`，女性为 `0..7→240..247`。因此男性手套和鞋的当前状态仍能对应到正确的 `CategoryNo`。

已在运行中的游戏中观察到：完整目录约有 `33045` 个物品，UAR 记录约 `83241` 条，因此不应在每帧或短周期内重复生成全量快照。

### 换装命令实现

探针的 HTTP 服务绑定 `127.0.0.1:7880`。网络线程只解析 JSON 并将命令放入队列，Unity API 只在 `GameItemProbePlugin.Update()` 主线程调用：

```text
POST /api/apply
  -> 校验命令
  -> 入队
  -> Unity 主线程取出命令
   -> 按 target 查找角色制作器角色或 HScene 角色
   -> 校验性别、类别、localSlot、配饰 slotNo、头发 hairSlotNo、面部 facePartNo 和身体 bodyPartNo
   -> 调用 ChaControl 的服装、头发、面部、身体或配饰原生更新路径
   -> 返回命令状态
```

H 场景单件物品请求示例（以下为服装）：

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

`target` 缺省或为 `editor` 时保持原有角色制作器行为；设置为 `hscene` 后必须提供 `sex`（`0` 男性、`1` 女性）以及 `characterIndex` 或 `targetCharacterId`。女性索引对应 `HScene.GetFemales()`，男性索引对应 `HScene.GetMales()`；同时提供索引和 `targetCharacterId` 时必须指向同一个 `ChaControl`。H 场景支持 `type: "clothes"`、`"hair"`、`"face"`、`"body"` 和 `"accessory"` 的单件换装；仍不接受 `type: "card"` 的整卡替换。

H 场景目标的实际调用链是：

```text
Manager.HSceneManager.Instance.Hscene
  -> HScene.GetFemales()/GetMales()
  -> 选中的 ChaControl 原生单件更新方法
```

它不会调用 `LoadCharaFile`、`ChangeNowCoordinate` 或 `Reload`，因此保留当前 H 场景角色、动画状态以及 H 场景控制器引用。`succeeded` 仍只表示原生方法已接受调用，模组资源的异步加载应另行通过画面或当前状态确认。

场景和角色枚举使用只读接口：

```http
GET http://127.0.0.1:7880/api/context
```

返回内容包括 `scene`（`editor`、`hscene` 或 `none`）、角色制作器角色，以及 H 场景中非空的女性/男性角色。每个角色包含 `characterIndex`、`characterId`、`sex`、`characterName`、`characterFileName` 和 `current`；`current` 的结构与 `/api/current` 一致，包含 `hairs`、`clothes`、`faces`、`bodies`、`accessories` 五类当前装配栏位。`femaleCount`、`maleCount`、`totalCount` 是当前实际角色数。

示例：

```json
{
  "available": true,
  "scene": "hscene",
  "editor": {
    "available": false,
    "characterIndex": -1,
    "characterId": 0,
    "sex": -1
  },
  "hscene": {
    "available": true,
    "femaleCount": 1,
    "maleCount": 0,
    "totalCount": 1,
    "females": [
      {
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
      }
    ],
    "males": []
  }
}
```

服装调用对应 `ChaControl.ChangeClothes(kind, localSlot, false)`；配饰调用对应 `ChaControl.ChangeAccessory(slotNo, categoryNo, localSlot, parentKey, false)`；头发调用对应 `ChaControl.ChangeHair(hairSlotNo, localSlot, false)`；面部调用按类别使用 `ChangeHead`、面部贴图更新方法或 `CreateFaceTexture`；身体调用 `ChaFileBody` 的 ID 写入、`AddUpdateCMBodyTexFlags`/`AddUpdateCMBodyLayoutFlags` 和 `CreateBodyTexture`，乳头/阴毛分别使用 `ChangeNipKind`/`ChangeUnderHairKind`。这些路径对角色制作器角色和 H 场景角色共用，命令结果通过 `/api/command?id=...` 查询。

### 卡顿原因与修复

早期实现的 `Update()` 每隔 5 秒调用一次完整 `GameItemSnapshotBuilder.Build()`。该过程在 Unity 主线程上：

- 遍历约 83000 条 UAR 记录；
- 遍历约 33000 个原生列表项；
- 读取每项 `dictInfo`、资源路径和解析候选；
- 序列化完整 JSON；
- 同步写入约 78 MB 的快照文件。

这会造成主线程长时间占用、GC、磁盘 I/O 和周期性掉帧。0.3.0 将其改为：

- 首次检测到列表初始化完成时执行一次完整扫描；
- `/api/refresh` 显式请求时才再次完整扫描；
- 默认使用 `Server/CurrentPollSeconds=1` 轻量读取当前角色状态（低于 1 秒的配置会被限制为 1 秒）；
- 换装成功只刷新当前角色状态，不触发完整目录重建；
- 首次扫描或手动重扫仍可能造成一次短暂卡顿，这是全量构建本身的成本。

### 实际游戏验证

2026-08-27，在角色制作器中确认：

- 插件加载版本：`StarManager.GameItemProbe 0.3.0`；
- 角色：女性角色，`sex=1`；
- 测试前上衣：`categoryNo=240 / localSlot=100008284`，名称 `T043_base`；
- 第一次测试：切换到原生上衣 `categoryNo=240 / localSlot=1`，命令状态 `succeeded`，当前状态同步为“连衣裙”；
- 第二次测试：恢复 `categoryNo=240 / localSlot=100008284`，命令状态 `succeeded`，当前状态恢复为 `T043_base`；
- 日志确认全量 `Captured ...` 只发生在插件启动初始化阶段，换装测试没有触发再次全量扫描。

上述测试只验证了 `0.3.0` 的角色制作器服装接口；配饰接口已按相同主线程机制实现，但仍应在需要时使用明确的 `slotNo` 做单独验证。`0.4.0` 的头发接口已完成当前 HS2 程序集签名、栏位映射和构建确认；`0.5.0` 增加了面部/身体当前状态采集。H 场景五类单件物品路径已完成代码和程序集级编译验证，但尚未在目标 H 场景内逐类实测，因此不能把命令成功视为动画、碰撞、动态骨骼和模组资源均已验证。

## 问题背景

Star Manager 的 zipmod 物品记录使用 `zipmod_guid + kind + item_id/name` 等字段；这些字段来自 zipmod 的 manifest/CSV，不能直接当成游戏当前物品的唯一运行时 ID。HS2 Sideloader 会在加载时为冲突物品分配 resolved/local ID，因此同一个 CSV `item_id` 在游戏中可能对应 `LocalSlot`，而角色卡和游戏物品界面保存的是当前 ID。

GameBridge 的现有链路已经验证为：

1. 从角色制作器的 `ChaControl.nowCoordinate` 读取服装部件的当前 ID。
2. 按性别和部位把部件转换为 `ChaListDefine.CategoryNo`。
3. 使用 `Manager.Character.Instance.chaListCtrl.GetListInfo(category, localId)` 读取原生 `ListInfoBase` 的名称。
4. 使用 `UniversalAutoResolver.TryGetResolutionInfo(category, localId)` 把当前 ID 反查为 `GUID + Slot + LocalSlot`，并补齐 manifest 的作者、版本、网站和 zipmod 路径。

所以 GameBridge 的可靠识别链是：

```text
当前物品界面/角色坐标的 localId
  + CategoryNo
  -> ChaListControl.GetListInfo
  -> UniversalAutoResolver.TryGetResolutionInfo
  -> GUID + 原始 Slot + LocalSlot + Property
```

名称只用于显示，不参与唯一匹配。

## 探针实现

`apps/tools/star-manager-game-item-probe/` 提供 BepInEx 插件 `StarManager.GameItemProbe.dll`。插件在 Unity 主线程执行初始化/手动触发的目录扫描、轻量当前状态读取和排队的换装命令：

- `UniversalAutoResolver.LoadedResolutionInfo` 的全部 UAR 记录；
- `ChaListControl.GetCategoryInfo` 中男性/女性服装、头发和 13 个配饰类别的原生列表；
- `CharaCustom.CustomBase.chaCtrl.fileHair` 与 `nowCoordinate` 的当前头发、服装和配饰部件。

每个原生列表项会输出：

```text
categoryNo / categoryName / categoryEnumName
localSlot / resolvedId / listId / originalId
kind / name / listIndex / distribution
mainManifest / mainAB / mainData
thumbAB / thumbTex / texAB
dictInfo（包含原生列表所有字段）
resolverRecords（可能有多个候选）
```

`originalId` 只有在 UAR 候选唯一时才会填入；多个候选时为 `null`，完整候选保留在 `resolverRecords`，避免把冲突物品错误映射到某一条记录。没有 UAR 记录的原版物品将 `resolverRecords` 置为空，并把当前原生 ID 作为原始 ID。

## 接口和输出

插件只绑定回环地址 `127.0.0.1:7880`：

```text
GET /api/status
GET /api/items
GET /api/items?category=240&guid=hyman.cloth.jinqipao
GET /api/item?category=240&localSlot=100017053
GET /api/resolve?category=240&localSlot=100017053
GET /api/current
GET /api/refresh
POST /api/apply
GET /api/command?id=<commandId>
```

首次初始化成功时，插件会生成一次完整快照并默认写入：

```text
<HoneySelect2>/BepInEx/config/StarManager.GameItemProbe.items.json
```

路径可以通过 BepInEx 配置中的 `Output/SnapshotPath` 修改。完整目录不会按定时器反复扫描；`/api/refresh` 只排队一次手动重建请求，实际抓取仍在游戏主线程执行。当前角色的 `hairs`/`clothes`/`faces`/`bodies`/`accessories` 会独立轻量更新，不会重建完整物品目录。

## 主线程换装命令

`POST /api/apply` 的 HTTP 接收线程不会访问 Unity 对象，只会将命令放入有上限的队列；插件每帧最多执行有限数量的命令。每个命令默认 15 秒过期，并保留最近一段时间的结果供查询。换装成功后只请求当前角色状态更新，不会触发 33000+ 物品和 83000+ UAR 记录的完整扫描。

直接指定游戏当前 ID：

```json
{"type":"clothes","categoryNo":240,"localSlot":100016311}
```

使用 zipmod 的 GUID 和 CSV 原始槽位严格映射：

```json
{"type":"clothes","guid":"hyman.cloth.jinqipao","categoryNo":240,"slot":1}
```

配饰指定角色配饰槽位 `slotNo`：

```json
{"type":"accessory","slotNo":0,"categoryNo":361,"localSlot":100000291}
```

头发必须显式指定与类别匹配的 `hairSlotNo`（`0..3`）：

```json
{"type":"hair","hairSlotNo":0,"categoryNo":300,"guid":"hyman.hair","slot":1}
```

`hairSlotNo` 不是物品的 `localSlot`，也不能跨类别复用；插件会按上面的固定映射再次校验。

面部类别使用 `type: "face"`。脸型、脸部肌肤/细节、胡子、眉毛、睫毛、眼影、眼睛高光、腮红、口红和痣/雀斑不需要额外栏位；美瞳 `317` 和瞳孔 `318` 必须提供 `facePartNo`（`0` 为左眼，`1` 为右眼）：

```json
{"type":"face","facePartNo":1,"categoryNo":317,"guid":"mod.face","slot":4}
```

身体类别使用 `type: "body"`。男性身体类别为 `8`（身体彩绘布局）、`131`（肌肤）、`132`（细节）、`133`（晒痕）；女性身体类别为 `231`（肌肤）、`232`（细节）、`233`（晒痕）、`313`（身体彩绘类型）、`334`（乳头）和 `335`（阴毛）。男性 `8` 修改 `paintInfo[index].layoutId`，女性 `313` 修改 `paintInfo[index].id`；两者都必须提供 `bodyPartNo`（`0` 为彩绘层 1，`1` 为彩绘层 2）：

```json
{"type":"body","bodyPartNo":1,"categoryNo":313,"guid":"mod.body","slot":4}
```

身体肌肤和细节会重建身体纹理，晒痕只更新晒痕纹理；`334`/`335` 分别调用原生乳头/阴毛刷新方法。

服装请求在当前角色性别对应的类别中转换为 `ChaControl.ChangeClothes(kind, localSlot, false)`；配饰请求校验 `slotNo` 为 `0..19` 后调用 `ChaControl.ChangeAccessory(slotNo, categoryNo, localSlot, parentKey, false)`；头发请求校验 `hairSlotNo` 为 `0..3` 且与 `categoryNo 300..303` 匹配后调用 `ChaControl.ChangeHair(hairSlotNo, localSlot, false)`；面部和身体请求按类别校验 `facePartNo`/`bodyPartNo` 后调用相应原生更新路径。上述调用在 `target: "hscene"` 时作用于选中的 H 场景角色。执行成功后只请求一次轻量当前角色状态刷新，不触发完整物品目录扫描。

提交响应是 `202`：

```json
{"accepted":true,"commandId":"...","status":"queued"}
```

使用 `GET /api/command?id=...` 查询 `queued`、`executing`、`succeeded`、`failed` 或 `expired`。失败结果带有 `errorCode`，包括 `not_in_editor`、`not_in_hscene`、`invalid_target`、`invalid_target_sex`、`invalid_character_index`、`target_not_found`、`target_mismatch`、`invalid_category`、`item_not_found`、`ambiguous_mapping`、`invalid_accessory_slot`、`invalid_hair_slot`、`queue_full` 和 `execution_error`。

## 构建和验证

```powershell
cd apps
dotnet build tools/star-manager-game-item-probe/StarManager.GameItemProbe.csproj `
  --configuration Release `
  -p:GameDir="E:\game\HoneySelect 2 DX - TSYMQ"
```

2026-08-27 已使用当前 HS2 安装的 `BepInEx.dll`、`Assembly-CSharp.dll` 和 `HS2_Sideloader.dll` 构建通过，输出位于：

```text
apps/tools/star-manager-game-item-probe/bin/Release/net472/StarManager.GameItemProbe.dll
```

本次已在当前 HS2 安装的引用上构建通过；安装新 DLL 后需要重启游戏，让 BepInEx 加载新版本，再通过 `/api/apply` 和 `/api/command` 验证实际运行时换装。日志中的 `Captured ...` 应只在首次初始化或手动 `/api/refresh` 后出现。

## 与右键换装的适用边界

这个探针已经解决“数据库物品如何对应游戏实际 ID”的观测问题，并提供了右键换装所需的游戏侧写入入口。Star Manager 当前通过后端固定回环代理接入，右键流程使用：

```text
数据库 CSV item_id + CategoryNo + GUID
  -> 探针 / GameBridge 的 resolver 记录找到 LocalSlot
  -> POST /api/apply 入队
  -> 插件主线程调用 ChaControl 的换装流程
  -> 轮询 /api/command 和 /api/current
```

如果一个 GUID、CategoryNo、原始 Slot 仍对应多个候选，调用方必须显示候选或要求用户确认，不能用 `name` 自动选择。原版物品没有 GUID 时，应使用 `CategoryNo + Coordinate ID/localSlot`。

Star Manager 当前界面把服饰类别 `140`、`141`、`144`、`147`、`240`–`247`、头发类别 `300`–`303`、面部类别 `110`–`112`、`121`、`210`–`212`、`314`–`320`、`322`、`323`、身体类别 `8`、`131`–`133`、`231`–`233`、`313`、`334`、`335` 和饰品类别 `351`–`363` 放入换装入口。普通物品浏览通过右键菜单提交换装；装配模式下点击右侧角色栏位后，左侧筛选结果改为通过鼠标左键直接提交到该栏位。服饰提交到对应服装栏位，头发提交到类别匹配的 `hairSlotNo` `0`–`3`，面部提交到当前面部栏位，美瞳/瞳孔提交到当前栏位的 `facePartNo` `0` 或 `1`，身体提交到当前身体栏位，身体彩绘提交到当前栏位的 `bodyPartNo` `0` 或 `1`，饰品提交到当前栏位 `partIndex` 对应的角色 `slotNo` `0`–`19`。头发颜色预设 `305`、发网格/发型选项资源 `306`、姿势和地图等其它类别仍是只读浏览资源。

### Star Manager 集成边界

- 前端调用 `/game-item-probe/apply`，后端只代理到 `127.0.0.1:7880`（可用 `STAR_MANAGER_GAME_ITEM_PROBE_PORT` 覆盖），并通过 `/game-item-probe/command` 轮询结果。
- 默认换装只影响当前 `CharaCustom.CustomBase.chaCtrl`；若请求显式使用 `target: "hscene"`，则只影响所选的 H 场景 `ChaControl`。普通模式从右键菜单提交，装配模式从已筛选物品的左键提交；不会写入数据库、zipmod、CSV、角色卡或服装卡。原版物品使用 `CategoryNo + item_id/localSlot`，模组物品使用 GUID + CategoryNo + CSV slot。
- 探针端口不携带游戏目录认证；调用方必须确认当前运行并占用该端口的 HS2 与 Star Manager 选中的游戏目录一致，否则可能对另一份游戏进程中的角色执行操作。
- 命令 `succeeded` 只表示游戏原生换装方法已接受调用，不代表所有贴图已完成异步加载。
- 插件未运行、未进入角色制作器、类别无效、头发栏位与类别不匹配、物品缺失、映射冲突、队列满和命令超时都必须作为失败反馈；前端不得回退到名称匹配。
- 后端代理使用固定 allow-list，不接受来自前端的任意目标 URL 或任意探针路径。
- 装配模式读取 `/game-item-probe/current` 时，Star Manager 后端对模组物品按 `GUID + CategoryNo + CSV slot` 查询本地物品库，对原版物品按所选 `game_dir + CategoryNo + localSlot` 查询 `builtin_items`；只有唯一匹配且存在缩略图缓存时才附带 `thumbnailUrl`。冲突映射、索引未收录或缩略图缺失的状态保留占位图，不按名称猜测。
- 探针仍会返回 `characterName`（`ChaFile.parameter.fullname`）供接口数据使用；装配模式界面当前只显示“角色编辑器”，不显示人物姓名、角色文件名或坐标。姓名读取失败不影响当前装配栏位读取。

## 适用边界与安全

- HTTP 只监听 `127.0.0.1`；不应改为对外网卡监听。
- 不能在 HTTP 工作线程直接调用 Unity API；所有 `ChaControl` 调用都发生在 `GameItemProbePlugin.Update()`。
- `localSlot` 是当前游戏解析后的 ID；GUID + `slot` 是严格映射输入，若映射到多个不同的 `localSlot` 会拒绝执行。
- `hairSlotNo` 是 `ChaFileHair.parts` 的栏位索引，必须按 `300→0`、`301→1`、`302→2`、`303→3` 固定映射提交；不能用类别或 `localSlot` 以外的名称猜测目标栏位。
- `bodyPartNo` 只用于类别 `8`/`313` 的身体彩绘，接口限制为 `0..1`；男性 `8` 使用 `paintInfo[index].layoutId`，女性 `313` 使用 `paintInfo[index].id`。身体其它类别按角色性别映射，男性不能使用女性专属的 `334`/`335`。
- 当前实现调用游戏原生换装方法，不依赖 GameBridge DLL；这样探针可以独立安装，但不会自动复用 GameBridge 的额外通知/颜色同步逻辑。
- 资源加载是游戏侧异步行为；命令成功表示原生换装调用已接受，不代表所有贴图已经完成加载。
- `0.8.0` 已完成当前 HS2 程序集中的 `ChangeHair` 签名、类别映射、面部/身体状态读取和人物卡选择性读取优化；人物卡读取会先同步 `ChangeNowCoordinate`，再复现原生 `Reload` 调用链，并临时关闭 `customLoadGCClear`。不再直接调用 `ReloadAsync` 或额外的服装/装饰聚合协程。选择性读取的接口契约与边界见[人物卡选择性读取](game-card-loading.md)。
- `0.7.1` 已在当前 HS2 角色编辑器中完成“仅衣服”和“仅装饰”实测：两次命令均返回 `succeeded`，仅装饰不会覆盖已读取的服装，用户确认人物、服装和装饰在画面中均正常显示。
- `0.8.0` 增加面部栏位写入。脸型使用 `ChangeHead`，面部贴图类别使用游戏原生面部更新方法；眼睛类别 `317`/`318` 通过 `facePartNo` 严格绑定左右眼。当前完成程序集级编译验证和代理 payload 测试，仍需将新 DLL 安装到目标 HS2 并在角色制作器内逐类实机验证资源加载结果。
- `0.9.0` 增加身体栏位写入。身体类别已加入静态目录扫描和装配模式；普通身体项直接执行，身体彩绘通过 `bodyPartNo=0/1` 绑定彩绘层。当前完成代码接入和代理 payload 测试，仍需将新 DLL 安装到目标 HS2 并在角色制作器内逐类实机验证资源加载结果。
- `0.9.0` 增加 H 场景角色枚举、完整当前装配状态和单件物品目标。通过 `Manager.HSceneManager.Instance.Hscene` 获取活动场景，再按 `sex + characterIndex` 调用 `GetFemales()`/`GetMales()`；服装、头发、面部、身体和配饰均只执行对应的原生单件更新方法，不执行整卡替换或 H 场景重载。当前已完成程序集级编译验证，尚未在目标 H 场景中逐类实测女性、男性和模组物品的资源加载结果。
