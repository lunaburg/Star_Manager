# SB3UtilityScript 调用说明

## 文档定位

本文记录当前 `D:\desktop_app\SB3UGS` 版本中，通过 `SB3UtilityScript.exe` 调用 SB3Utility DLL 的脚本方式。内容适用于 Unity3D 资源检查、GameObject/MainData 处理、MonoBehaviour 字段修改以及保存结果验证。

本文记录的是 SB3Utility 自带脚本语言，不是任意 C#、Python 或 Unity Editor 脚本。具体参数以当前目录中的 DLL 和 GUI 自动生成脚本为准。

## 1. 运行环境和文件关系

当前工具目录的关键文件为：

```text
D:\desktop_app\SB3UGS\
|-- SB3UtilityScript.exe       # 执行文本脚本
|-- SB3UtilityGUI.exe          # 图形界面打开 Unity3D
|-- SB3Utility.dll             # 脚本引擎
`-- plugins/
    |-- UnityBase.dll
    |-- UnityPlugin.dll
    |-- SB3UtilityPlugins.dll
    `-- 其他依赖 DLL
```

`SB3UtilityScript.exe` 使用 .NET Framework 4.5 和当前版本的插件目录。它是 32 位程序，不能直接由 64 位 Python/Electron 进程加载这些 DLL；应用集成时应启动 `SB3UtilityScript.exe`，或者使用独立的 x86 .NET Framework 子进程。

从其他目录调用时建议仍然将工作目录设为 `D:\desktop_app\SB3UGS`，避免插件或原生依赖加载失败。

## 2. 命令行调用

脚本执行器的命令格式为：

```powershell
cd D:\desktop_app\SB3UGS
.\SB3UtilityScript.exe "D:\test\script.txt"
$LASTEXITCODE
```

也可以一次传入多个脚本：

```powershell
.\SB3UtilityScript.exe "D:\test\inspect.txt" "D:\test\modify.txt"
```

返回码约定：

| 返回码 | 含义 |
| --- | --- |
| `0` | 所有脚本执行成功 |
| `-1` | 脚本语法、DLL、资源解析或保存过程发生错误 |

脚本文件使用一行一条调用语句。分号 `;` 表示注释，变量通过赋值保存返回对象，参数可以使用命名参数：

```text
; comment
unityParser0 = OpenUnity3d(path="D:\test\source.unity3d")
unityEditor0 = Unity3dEditor(parser=unityParser0)
```

路径、字符串需要使用双引号；`null`、布尔值、整数和数组索引可以直接使用。

## 3. Unity3D 文件级接口

### 打开、读取和保存

常用接口：

```text
OpenUnity3d
Unity3dEditor
GetAssetNames
SaveUnity3d
WriteUnity3d
ExportUnity3d
ExtractFiles
```

最小读取脚本：

```text
unityParser0 = OpenUnity3d(path="D:\test\source.unity3d")
unityEditor0 = Unity3dEditor(parser=unityParser0)
unityEditor0.GetAssetNames(filter=True)
```

推荐保存到新文件，并等待保存完成：

```text
unityEditor0.SaveUnity3d(path="D:\test\modified.unity3d", keepBackup=False, backupExtension=".unit-y3d", background=False, clearMainAsset=True, pathIDsMode=-1, compressionLevel=3, compressionBufferSize=262144)
```

`path` 省略时通常会写回当前文件；测试阶段不要省略 `path`。`background=False` 适合命令行，避免脚本进程退出时后台保存尚未完成。若 Unity3D 产生 `.resS` 或其他旁车文件，应保留它们并与输出文件放在同一目录。

### 资源名称和资源删除

```text
unityEditor0.SetAssetName(componentIndex=389, name="NewAssetName")
unityEditor0.RemoveAsset(asset=unityParser0.Cabinet.Components[389])
```

`Components[389]` 是当前文件的组件序号，只能使用经过当前文件确认的编号。不能把一个 Unity3D 文件的组件序号直接套用到另一个文件。

还可以使用 `MarkAsset`、`UnmarkAsset`、`PasteAllMarked`、`CopyInPlace`、`ViewAssetData`、`RenameCabinet` 和 AssetBundle 主资源相关接口。

### 资源类型接口

`Unity3dEditor` 支持打开或导出以下资源类型：

- Animator、Animation、AudioClip、MonoBehaviour、Shader、TextAsset；
- Texture2D、Texture3D、Cubemap；
- AssetBundle、外部引用和类型定义；
- MonoBehaviour、Shader、TextAsset 的复制、粘贴、替换和导出。

文件级 `Plugins` 接口还包括 `ReplaceTexture`、`ReplaceAudioClip`、`ReplaceShader`、`ReplaceTextAsset`、`ExportTexture`、`ExportAudioClip`、`ExportShader`、`ExportTextAsset`、`MergeTexture` 和 `MergeTextures`。

## 4. Animator、GameObject 和 MainData

### 打开 Animator

```text
virtualAnimator0 = unityEditor0.OpenVirtualAnimator(componentIndex=1)
animatorEditor0 = AnimatorEditor(parser=virtualAnimator0)
```

`componentIndex` 必须是当前 Unity3D 文件中的 Animator 组件序号。

### 修改 MainData 对应的 GameObject 名称

工作台 CSV 中的 `MainData` 是 Unity3D 中 GameObject 的名称。命令行脚本修改根 GameObject 名称时使用 `SetAssetName`：

```text
unityEditor0.SetAssetName(componentIndex=1, name="New_MainData")
```

`componentIndex` 必须是当前 Unity3D 文件中目标 GameObject 的组件序号。GUI 自动脚本中的 `SetFrameName(id=0, ...)` 依赖 GUI 创建的根帧，在 `SB3UtilityScript.exe` 中对根帧调用可能触发空引用；工作台因此对根对象使用 `SetAssetName`。`AnimatorEditor` 的帧查询仍适用于非根节点操作。

`id=0` 只是示例。应先确认目标 GameObject 的 frame ID 或路径，再执行修改。可用的查找接口包括：

```text
animatorEditor0.GetFrameId(name="Old_MainData")
animatorEditor0.GetFrameIdByPath(path="Root/Old_MainData")
animatorEditor0.GetTransformPath(id=0)
```

修改后必须把 CSV 的 `MainData` 同步为新名称，否则模型预览和游戏资源索引可能找不到对象。

### GameObject、Mesh、Renderer 和材质

`AnimatorEditor` 主要支持：

- `SetGameObjectAttributes`、`SetGameObjectIsActive`、`SetGameObjectLayer`、`SetGameObjectTag`；
- `SetFrameSRT`、`SetFrameMatrix`、`CreateFrame`、`RemoveFrame`、`MoveFrame`；
- `SetMeshAttributes`、`SetMeshName`、`SetMeshBoneHash`；
- `SetRendererAttributes`、`SetSkinnedMeshRendererAttributes`、`RemoveMeshRenderer`；
- `SetMaterialName`、`SetMaterialColour`、`SetMaterialShader`、`SetMaterialTexture`；
- `SetTextureName`、`SetTextureAttributes`、`AddTexture`、`RemoveTexture`；
- 骨骼、Avatar、Morph、Skin、SubMesh、法线和切线相关操作。

复制当前编辑器中的对象树时，必须调用脚本公开的五参数重载：

```text
animatorEditor0.AddFrame(srcFrame=animatorEditor0.Frames[frameId0], srcMaterials=animatorEditor0.Materials, srcTextures=animatorEditor0.Textures, appendIfMissing=true, destParentId=-1)
```

`UnityPlugin.dll` 内部还存在接收 `newFrame` 和 `destParentId` 的两参数重载，但它没有注册为脚本插件方法；`SB3UtilityScript.exe` 调用该重载会报告 `Couldn't match args for AddFrame()`。

例如，GUI 自动脚本中常见的材质和节点调用形式为：

```text
animatorEditor0.SetFrameName(id=0, name="Item_base_obj")
animatorEditor0.SetTextureName(id=0, name="Item_diffuse")
animatorEditor0.SetMaterialTexture(id=0, index=7, editor=null, texIndex=-1)
animatorEditor0.RemoveMeshRenderer(id=0)
```

## 5. MonoBehaviour 和序列化字段

打开 MonoBehaviour：

```text
monoBehaviour0 = unityEditor0.OpenMonoBehaviour(componentIndex=13)
monoBehaviourEditor0 = MonoBehaviourEditor(parser=monoBehaviour0)
```

`CmpAccessory`、`CmpClothes` 等自定义 MonoBehaviour 在 SB3Utility 20.6.3 中可以正常匹配字段；出现“给定关键字不在字典中”时，应先区分是 MonoBehaviour 解析失败，还是 Animator 根帧命令在脚本模式下初始化不完整。

执行资源修改后，保存前应再次调用 `unityEditor0.GetAssetNames(filter=True)` 刷新资源缓存；否则自定义 MonoBehaviour 可能在保存阶段才被延迟加载并出现 `UnityPlugin.NotLoaded`。

常用修改接口：

```text
monoBehaviourEditor0.SetAttributes(line=2, value="1")
monoBehaviourEditor0.SetExtendedAttributes(line=12, value="0")
monoBehaviourEditor0.SetReference(line=8, value=animatorEditor0.Meshes[0])
monoBehaviourEditor0.ArrayInsertBelow(line=8)
monoBehaviourEditor0.ArrayDelete(line=8)
```

`componentIndex` 和 `line` 都是当前文件专属信息。`line` 是序列化字段行号，不是字段名称；应从当前文件的 MonoBehaviour 编辑结果或 GUI 自动脚本中确认。

## 6. 动画控制器和其他编辑器

当前 Unity 插件还提供以下脚本编辑器：

- `AnimationEditor`：动画剪辑名称、属性、插入、删除、移动和替换；
- `AnimatorControllerEditor`：状态、状态名称、动画槽、过渡和 AnimationClip；
- `AnimatorOverrideControllerEditor`：覆盖控制器和替换剪辑；
- `AssetBundleManifestEditor`：AssetBundle 属性和资源删除；
- `AudioClipEditor`：音频属性；
- `LoadedByTypeDefinitionEditor`：类型定义加载资源的数组、属性和引用；
- `UVNormalBlendMonoBehaviourEditor`、`NmlMonoBehaviourEditor`：特定 MonoBehaviour 的 UV、法线和对象数据。

此外，`SB3UtilityPlugins.dll` 保留了 `.xx`、`.xa`、`.pp` 和导入资源编辑器的脚本接口；`SB3UtilityFBX.dll` 主要用于 FBX 导入导出，不是 Unity3D MainData 修改的核心接口。

## 7. 一个完整的修改和验证流程

`D:\test\modify.txt`：

```text
unityParser0 = OpenUnity3d(path="D:\test\source.unity3d")
unityEditor0 = Unity3dEditor(parser=unityParser0)
virtualAnimator0 = unityEditor0.OpenVirtualAnimator(componentIndex=1)
animatorEditor0 = AnimatorEditor(parser=virtualAnimator0)
unityEditor0.SetAssetName(componentIndex=1, name="New_MainData")
unityEditor0.SaveUnity3d(path="D:\test\modified.unity3d", keepBackup=False, backupExtension=".unit-y3d", background=False, clearMainAsset=True, pathIDsMode=-1, compressionLevel=3, compressionBufferSize=262144)
```

执行并检查返回码：

```powershell
cd D:\desktop_app\SB3UGS
& .\SB3UtilityScript.exe D:\test\modify.txt
$LASTEXITCODE
```

`D:\test\verify.txt`：

```text
unityParser1 = OpenUnity3d(path="D:\test\modified.unity3d")
unityEditor1 = Unity3dEditor(parser=unityParser1)
unityEditor1.GetAssetNames(filter=True)
```

重新解析验证：

```powershell
& .\SB3UtilityScript.exe D:\test\verify.txt
$LASTEXITCODE
```

最后用 GUI 工具检查文件：

```powershell
& .\SB3UtilityGUI.exe D:\test\modified.unity3d
```

## 8. GUI 自动脚本的兼容边界

不要把 `SB3UtilityGUI.autosavescript.txt` 整个文件直接交给 `SB3UtilityScript.exe`。GUI 自动脚本可能包含多个会话、重复变量和仅用于打开窗口的语句，例如：

```text
FormUnity3d(...)
WorkspaceFbx(...)
OpenImageFile(...)
```

命令行脚本通常只保留资源对象和编辑器 API：

```text
OpenUnity3d
Unity3dEditor
OpenVirtualAnimator
AnimatorEditor
OpenMonoBehaviour
MonoBehaviourEditor
SaveUnity3d
```

跨文件编辑、外部资源引用和复杂 AnimatorEditor 操作应逐个文件验证。GUI 中能运行的脚本不保证不经整理就能在 `SB3UtilityScript.exe` 中运行。

## 9. 与 Star_Manager 的关系

Star_Manager 中用于点击打开 Unity3D 的外部程序应配置为：

```text
D:\desktop_app\SB3UGS\SB3UtilityGUI.exe
```

调用方式是把 Unity3D 路径作为参数传给 GUI 程序。`SB3UtilityScript.exe` 的参数是脚本路径，不能用来替代 Star_Manager 的图形化打开程序。

工作台的 Unity3D 写入现在统一由 Electron 主进程生成临时脚本并调用 `SB3UtilityScript.exe`：对象“复制并重命名”先使用 `OpenVirtualAnimator`/`AnimatorEditor.AddFrame` 复制对象树，再重新读取复制出的 GameObject 并用 `SetAssetName(componentIndex=..., name=...)` 修改名称；贴图导入使用 `AddTexture` 或 `ReplaceTexture`，资源复制后的 CAB 标识使用 `RenameCabinet`。`OpenVirtualAnimator(componentIndex=...)` 必须使用当前 `MainData` GameObject/Animator 的组件序号，不能使用目标 Texture2D 自身的组件序号；替换前必须确认同名纹理存在。所有操作先输出到运行时副本，确认脚本成功且后端能够重新读取结果后，才写回工程资源；工程内已有资源的复制并重命名会在验证后原子覆盖原文件；Python 后端不再负责工作台 Unity3D 的写入序列化。

## 继续阅读

- [文档索引](README.md)：按功能和任务查找项目文档。
- [工作台](frontend-ui/workbench-layout.md)：MainData、Unity3D 模板和工程资源写回流程。
- [Unity3D 解密与修复](unity3d-decryption-notes.md)：UnityFS、二次保护和隔离验证规则。
- [AssetStudio helper](assetstudio-helper.md)：另一条 Unity 资源读取子进程协议。
