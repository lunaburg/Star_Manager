# Star Manager Character Card Read Probe

这是一个独立的 HS2 BepInEx 只读审计插件。它不依赖、也不修改
`StarManager.GameItemProbe`，不提供换装接口，不写入人物卡，不保存任何角色卡原始字节。
插件同时提供只绑定 `127.0.0.1` 的 HTTP 诊断接口，默认端口为 `7881`。
JSON 输出使用插件内置序列化器，不要求游戏目录额外提供 `System.Web.Extensions.dll`。

## 用途

插件用于确认“游戏通过哪些方法读取人物卡，以及哪些插件参与了后续资源重载”：

- Harmony 监听 `ChaFile` / `ChaFileControl` 的 `LoadFile`、`LoadFileLimited`、
  `LoadCharaFile`、`LoadFromBytes`；
- 监听 `ChaControl.Reload`、`ReloadAsync`、`ChangeNowCoordinate`、服装/头发/饰品更新方法；
- 记录每次卡片读取方法的参数、调用耗时、前后 `ChaFile` 区块指纹和发生变化的区块；
- 记录当前方法已有的 Harmony 补丁 owner，可用来判断哪个插件介入了该方法；
- 运行时反射观察 ABMX 的 `BoneController.OnReload` 和 KSOX 的
  `KoiSkinOverlayController` 加载/重载回调，记录 `plugin_callback` 的开始、完成或异常；
- 在重载后的第 1、10、30 帧扫描当前角色的蒙皮骨骼、骨骼局部变换、Mesh、Renderer、材质和贴图元数据；
- 可选追踪 `AssetBundle.LoadAsset*` 调用，但该选项默认关闭，避免日志过大；
- 如果运行环境暴露 `ExtendedSave.GetAllExtendedData`，会记录可读取到的扩展数据摘要。

输出是 UTF-8 JSON Lines，默认位置：

```text
<HoneySelect2>/BepInEx/config/StarManager.CharacterCardReadProbe.jsonl
```

按 `F8` 可手动记录当前角色的场景资源快照。贴图只记录名称、实例 ID、尺寸、材质属性等元数据，
不读取或导出贴图像素；这样可以判断贴图何时、由哪个材质属性加载，而不会制造大量内存和磁盘开销。

## HTTP API

默认基地址：

```text
http://127.0.0.1:7881
```

接口只用于读取诊断状态或请求一次只读场景快照：

```text
GET  /api/status
GET  /api/records?limit=50
GET  /api/logs?recordType=method_call&limit=50
POST /api/snapshot
```

`/api/records` 和 `/api/logs` 返回当前进程最近保留的记录，默认按最新在前，最多 128 条；完整历史仍在 JSONL 文件中。
`POST /api/snapshot` 只把请求排入 Unity 主线程，实际快照会在下一帧写入 JSONL，并可通过 `/api/records?recordType=scene_snapshot` 查询。
HTTP 服务只监听回环地址，不接受局域网或公网连接。

## 构建

从 `apps/` 目录执行，并指定实际 HS2 游戏目录：

```powershell
dotnet build tools/star-manager-character-card-read-probe/StarManager.CharacterCardReadProbe.csproj `
  --configuration Release `
  -p:GameDir="E:\game\Honey Select 2 DX - TSYMQ"
```

产物：

```text
apps/tools/star-manager-character-card-read-probe/bin/Release/net472/StarManager.CharacterCardReadProbe.dll
```

安装到：

```text
<HoneySelect2>/BepInEx/Plugins/StarManager/StarManager.CharacterCardReadProbe.dll
```

重启游戏后，先加载一张基准卡，再加载只改变一个内容的测试卡。重点查看：

1. `method_call` 中 `LoadFileLimited` 的参数和 `changedSections`；
2. 随后的 `Reload` / `ReloadAsync` 调用及 Harmony owner；
3. `scene_snapshot` 中 `boneSha256`、骨骼列表、Renderer、材质和纹理属性的变化；
4. `extendedSave` 是否可用，以及扩展数据中是否出现 ABMX、KSOX、MaterialEditor 等插件键。
5. `plugin_callback` 是否出现 `ABMX`/`KSOX` 的 `started` 与 `completed` 记录，以及关联的扩展数据 ID。

也可以直接查询回调记录：

```text
GET /api/logs?recordType=plugin_callback&limit=50
```

## 配置

配置文件为：

```text
<HoneySelect2>/BepInEx/config/star.manager.charactercardreadprobe.cfg
```

- `CaptureSceneAfterLoad=true`：人物卡/重载方法后记录三次角色资源快照；
- `CaptureMethodState=true`：记录原生 `ChaFile` 区块前后指纹与有限结构摘要；
- `TraceAssetBundleLoads=false`：需要追踪 AssetBundle 资源调用时再打开；
- `SnapshotHotkey=F8`：手动快照快捷键；
- `JsonlPath`：修改输出文件位置。
- `Server/Port=7881`：修改本地 HTTP API 端口；如果与其他程序冲突可改为未占用端口。

## 边界

- 插件只观察游戏运行时对象，不对人物卡、当前角色或模组资源执行写操作；
- 贴图像素、AssetBundle 全量内容和插件私有数据不会默认导出；扩展数据能否枚举取决于已安装的
  ExtendedSave 版本是否提供 `GetAllExtendedData`；
- 骨骼快照主要来自 `SkinnedMeshRenderer.bones`，动态骨骼插件自己的运行时粒子状态不一定属于该列表；
- `ReloadAsync` 返回的是协程，插件通过第 1、10、30 帧快照观察后续资源状态，不能把某一帧快照当作最终加载完成证明；
- Harmony owner 只能说明某插件给方法打过补丁，不能单凭 owner 证明该插件改变了人物卡数据；仍需结合单变量卡片和前后指纹判断。
- `plugin_callback` 只在目标插件程序集已加载且目标方法成功挂接时产生；没有记录时应先查看
  `session_started.pluginCallbackTargets`，确认目标方法是否发现/挂接，再检查插件是否实际参与本次重载。
