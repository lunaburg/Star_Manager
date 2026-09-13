# Unity3D 资源解密与修复记录

本文记录在 HS2/Sakuraba 资源中确认过的 UnityFS 资源异常、修复规则、验证方法和安全边界。它是排障记录，不包含任何解密密钥，也不建议把未知原生插件直接放进主游戏环境。

## 资源依赖关系

发型 CSV 通常通过以下字段关联资源：

```text
MainAB   -> 发型主 Mesh AssetBundle
MainData -> Mesh 包中的目标对象名
TexAB    -> 外部贴图 AssetBundle
TexD/C   -> 贴图对象名，常见值为 placeholder
ThumbAB  -> 缩略图 AssetBundle
```

`hair_tex.unity3d` 不一定是实际发型贴图。正常模组中的同类文件往往只有一个 8×8 的 `Texture2D`，名称为 `placeholder`，作用是满足外部依赖。较大的发型纹理通常位于 Mesh 包中。

## `yukilat_B002_1.unity3d` 的 `B002_base` 读取修复

### 案例背景

2026-08-29 检查了：

```text
D:\Workspace\Star_workspace\B002\abdata\chara\yukilat\yukilat_B002_1.unity3d
```

同一个包内的 `B002_1_obj` 可以在游戏中读取，而 `B002_base_obj` 不能读取。原文件 SHA-256 为 `BFA28AED5181C0747F9A37751178C455C0D29EDFBC338F23D16BE96AAAC96E81`。

### 静态检查结论

原包能够被 UnityPy 读取，包含 `2030` 个对象、`1006` 个 `GameObject`、`1006` 个 `Transform` 和 `2` 个 Mesh。`B002_base_obj` 与 `B002_1_obj` 的层级规模、骨骼数量、Renderer 启用状态、Mesh 引用和 Material 引用均完整；两个 Mesh 的二进制内容一致，因此不是模型几何体或骨骼损坏。

关键差异是主贴图存储方式：

| 对象 | 尺寸 / 格式 | mip | 数据位置 |
| --- | --- | --- | --- |
| `B002_1_diffuse1` | 2048×4096 / TextureFormat 12 | 1 | SerializedFile 内嵌 |
| `B002_base_diffuse1` | 2048×4096 / TextureFormat 12 | 13 | `StreamingInfo` 指向 `archive:/...resS`，大小 11,184,848 字节 |

目标目录中虽然没有旁车 `.resS` 文件，但 UnityFS 内部确实存在对应的资源节点，且三张流式纹理声明的字节都可以从该节点按偏移完整取出。也就是说，问题不是资源字节缺失，而是该包仍依赖 SB3U/游戏不稳定处理的流式纹理读取；这与同类正常文件 `D:\Workspace\Star_workspace\T065\abdata\chara\yukilat\yukilat_T065_1.unity3d` 的“无 `.resS`、纹理全内嵌”结构形成了明确差异。`CmpClothes.useColorN02/useColorN03` 的值也不同，但对应空 Renderer 数组，代码路径对空数组有保护，因此本次没有修改这些服装组件开关。

### 修复方案

将 `B002_base_diffuse1`、`detail_cloth_02`、`liquid_1_t` 的完整原始纹理数据从 UnityFS 资源流写入 SerializedFile，并清空这三张 Texture2D 的 `m_StreamData.path/offset/size`，使其全部改为内嵌纹理；随后移除已经没有引用的 `.resS` 节点。保留宽高、TextureFormat、mip 数、原始纹理字节、模型、材质、容器名称和其它资源对象。输出文件没有重新编码贴图，也没有用 `B002_1` 的纹理替换 base 纹理。

修复后的文件已写回原路径，SHA-256 为：

```text
CDAFDF47E2704C849DC439525DEAD520A2350184D35774531AD36B5E73BA7225
```

原文件备份为：

```text
D:\Workspace\Star_workspace\B002\abdata\chara\yukilat\yukilat_B002_1.unity3d.original-bfa28aed5181.bak
```

写回前的上一版修复文件也已备份为：

```text
D:\Workspace\Star_workspace\B002\abdata\chara\yukilat\yukilat_B002_1.unity3d.pre-inline-all-20260829.bak
```

### 验证结果与边界

- UnityPy 重新读取写回文件通过；对象数、Mesh 数、两个 MainData 根对象和 AssetBundle 容器索引保持不变。
- 写回文件为 UnityFS 6、Unity `2018.2.21f1`，包含 `2030` 个对象、`2` 个 Mesh 和 `5` 张 Texture2D；三张原流式纹理均已改为内嵌，`.resS` 节点数为 `0`。
- `B002_base_diffuse1`、`detail_cloth_02`、`liquid_1_t` 的内嵌字节分别为 `11,184,848`、`87,408`、`1,048,575` 字节，哈希与原 UnityFS 资源节点按偏移提取的数据一致。
- SB3UtilityGUI `20.6.3` 已实际打开写回前生成的同哈希候选文件，列出 `B002_1_obj`、`B002_base_obj`，并成功为 `B002_base_obj` 建立虚拟 Animator；纹理页列出全部 `5` 张纹理，Streamed 列为空。
- 当前环境没有可运行的 `HoneySelect2.exe`，因此尚未完成游戏进程内的实例化验证；该修复结论是基于 UnityFS 结构、UnityPy 读取和原始纹理字节校验。AssetStudio helper 的额外复核因本机无法访问 NuGet 源而未能重新编译。
- 若游戏仍无法读取，应优先检查实际加载日志和同一路径下的旧版缓存；不要删除两个 `.bak` 备份，直到完成游戏内验证。本次处理只针对已确认的外部 `.resS` 依赖，不代表所有 SB3U 读取失败都可用相同方式修复。

## 已确认的三种文件状态

### 1. 正常的 placeholder tex 包

常见特征：

- UnityFS，Unity 版本通常为 `2018.2.21f1`；
- 可以被 AssetStudio/UnityPy 读取；
- 包含 `Texture2D` 和 `AssetBundle` 对象；
- `Texture2D` 名称为 `placeholder`，尺寸为 8×8；
- 容器路径类似 `assets/sakuraba/<bundle>/placeholder.png`。

### 2. SerializedFile 偏移字段损坏

此前的 `24-2-S01_hair_tex` 属于这一类。UnityFS 外层和数据块完整，内部 SerializedFile 的 `data_offset` 被写成了 `0x0BE0`，正常值为 `0x1000`。

修复方式：

1. 定位 UnityFS 数据块中的 SerializedFile；
2. 确认 SerializedFile 头、版本和元数据大小符合预期；
3. 仅将 `data_offset` 从 `0x0BE0` 改为 `0x1000`；
4. 输出到新文件，不覆盖原文件；
5. 用 UnityPy/AssetStudio 验证对象表和容器。

这种修复只改变两个实际不同的字节，不能把它和内容缺失或真正加密混为一谈。

### 3. BepInEx/Bit 二次保护

`yu` 文件夹中的另一批资源属于更强的保护层：

- 原文件仍以 `UnityFS` 开头；
- 文件中出现固定 16 字节标记：

```text
45 5A 97 5A E1 CA B9 93 56 B2 10 FC 7C 4C 6C 59
```

- 标记通常位于文件偏移 `0x90`（十进制 144）；
- 标记附近连续 128 字节内容被加密或替换；
- 删除标记本身不足以恢复 LZMA/LZ4 数据；
- 对应文件大小通常比正常原件多 16 字节。

随资源提供的插件由两部分组成：

- `Bit.dll`：托管 BepInEx 桥接层，加载同目录的 `Bit.xml` 并调用 `Bit_A`；
- `Bit.xml`：经过混淆的 64 位原生 DLL，负责 Unity 运行时钩子。

离线直接调用 `Bit_B` 或把文件缓冲区传给它不能完成解密。`Bit_A` 需要 UnityPlayer 运行环境，说明这类资源通常是在游戏运行时被还原，而不是一个简单的命令行 XOR 操作。

### 4. XT 四字节标记与循环 XOR

XT 的一类资源不保留明文 `UnityFS` 文件头，常见特征为：

- 文件以 `01 03 03 01` 开头；
- 去掉这 4 字节后，剩余内容使用 20 字节密钥循环 XOR；
- 配套 `resourceKit-5.dll` 在 AssetBundle 加载钩子中读取整个文件、去掉 4 字节标记，再执行两层 XOR；
- 第一层密钥与机器标识有关，第二层再混入资源文件名。

这种保护可以通过已知明文恢复：标准 UnityFS 的前 20 字节包含固定签名、格式版本、`5.x.x` 和 Unity revision 的开头，恰好覆盖完整循环密钥。`apps/scripts/decrypt_xt_unity3d.py` 会从每个目标文件自身恢复文件级密钥，因此不需要执行配套插件，也不需要取得原机器标识。

脚本默认不覆盖任何文件：

```powershell
python apps/scripts/decrypt_xt_unity3d.py `
  "E:\protected\asset.unity3d" `
  "E:\recovered\asset.decrypted.unity3d"
```

也可以递归处理整个目录。输出目录必须位于输入目录之外，目录结构会被保留；标准 UnityFS 文件只记为跳过：

```powershell
python apps/scripts/decrypt_xt_unity3d.py `
  "E:\protected-assets" `
  "E:\recovered-assets" `
  --report "E:\recovered-assets\decrypt_report.json"
```

输出前必须同时验证 UnityFS 签名、格式版本、Unity 版本字符串和声明文件大小。之后仍应使用 UnityPy 或 AssetStudio 验证对象表。

### 5. wen 作者的 57 字节包裹与内嵌资源流

#### 案例背景

`E:\game\HoneySelect 2 DX - TSYMQ\abdata\wen\wenchenyinger5.unity3d` 的文件头为：

```text
41 55 30 38 33 32 31 39 73 61 39 32 69 73 61 31
```

它不是 UnityFS，也不符合 XT XOR 或 Bit 二次保护的特征。用户提供的同作者正常包
`wen叶夕水.zipmod` 中的 `abdata/wen/wenyexishui.unity3d` 使用 Unity `2018.2.21f1`，可作为 SerializedFile 元数据对照。

#### 根因和结构

目标文件可分成三部分：

```text
57 字节自定义前缀
  -> 15,395,724 字节 SerializedFile 主体
  -> 74,291,456 字节内嵌资源流（原 SerializedFile 的 m_StreamData 引用该流）
```

主体从文件偏移 `57` 开始。除头部及第一个 `classID=115` TypeTree 记录外，后续字节与标准 SerializedFile 结构一致；缺失/替换区域覆盖主体开头约 `1120` 字节。`m_StreamData` 的外部路径仍保留为 `archive:/.../*.resS`，但实际资源数据紧接在对象数据末尾，并不是目录中的独立 `.resS` 文件。

#### 恢复方案

1. 去掉 57 字节自定义前缀，不把后续资源流误判成 SerializedFile 对象数据。
2. 使用同作者、同 Unity revision 的正常文件恢复 SerializedFile 头和缺失的首个 TypeTree 记录。
3. 以对象表的最大 `byte_start + byte_size`（本例为 `15,395,724`）确定内嵌资源流边界。
4. 将 SerializedFile 的 `file_size` 改为主体长度，保留资源流原始字节，并把两者重新放入标准 UnityFS 的 SerializedFile / `.resS` 两个节点。
5. 重新打开封装结果，读取全部对象，再逐张解码 Texture2D。

本例恢复结果：`5260` 个对象、`20` 个 TypeTree 类型、`2538` 个 GameObject、`2538` 个 Transform、`23` 个 Texture2D；全部对象读取成功，`23/23` 张纹理解码成功。AssetStudio helper 重新读取封装结果也报告 `5260` 个对象。

恢复产物的 SHA-256：

```text
wenchenyinger5.decrypted.unity3d
BBE9BCC1DFBC960AE048A5E857C0B9D87F645FA34B04A54386FA5D4251DF95CA
```

#### 适用边界

- 该 profile 只适用于能够同时确认 57 字节前缀、Unity revision、TypeTree 指纹、对象范围和内嵌资源边界的同类文件；不能按文件名批量套用。
- 当前验证是 UnityPy 与 AssetStudio 的静态读取/纹理解码验证，尚未替代 HS2 游戏中的实际角色或物品实例化测试。
- 输出已经重新封装为标准 UnityFS，原始目标文件没有覆盖；替换进游戏前应先备份，并确保同一资源路径/GUID 下没有旧版副本。

#### `wenchenyinger.unity3d` 同 profile 实例

目标文件 `E:\game\HoneySelect 2 DX - TSYMQ\abdata\wen\wenchenyinger.unity3d` 使用相同的 57 字节前缀，但不能直接复制 `wenchenyinger5` 的完整对象表。逐字节对齐确认：目标主体相对偏移 `257` 对应已恢复 SerializedFile 的偏移 `172`；两者共享 20 个 TypeTree，目标对象表从对齐后的偏移 `73,440` 开始，包含 `5291` 个对象。目标 SerializedFile 的可验证字段为：Unity `2018.2.21f1`、`metadata_size=179,380`、`data_offset=179,408`、最大对象边界 `19,666,024` 字节。

目标文件尾部实际提供的内嵌 `.resS` 数据比最后一张 `cf_t_face_00_17_00` 的声明范围少 `688` 字节。该缺口没有在本地原版资源或已提供的两个同作者 zipmod 中找到可逐字节替换的副本；恢复输出仅在资源流末尾补入 `688` 个零字节，使全部 `30/30` 张 Texture2D 可解码。这个补齐不是原始字节的唯一恢复，最后贴图的尾部区域可能需要在游戏内继续确认。

本次恢复产物：

```text
wenchenyinger.decrypted.unity3d
SHA-256: 807984F444D6D01965ABCF45D4A0319B03DFA0ACCA084620889BC70A9B4B39C7
```

UnityPy 验证结果为 `5291` 个对象全部读取成功、`30/30` 张 Texture2D 解码成功；输出为标准 UnityFS，原始 `wenchenyinger.unity3d` 未覆盖。AssetStudio helper 的额外验证因本机无法访问 NuGet 源而未完成，不应把该工具失败误判为资源解析失败。

## 正确的恢复策略

优先级如下：

1. **未知加密方式先找参考模组**：优先查询本地 SQLite 模组数据库中的非 stale `zipmods`，按目标 GUID 精确查找；只有同 GUID 没有仍可读取的未加密参考时，才按 manifest 作者查找。候选必须回到磁盘检查实际字节、Unity revision、TypeTree、节点布局和对象可读性，不能只依据数据库状态字段。
2. **有完全对应的正常原件**：从正常游戏 `abdata` 或对应 zipmod 提取同名资源，逐个验证后作为恢复结果。此前 `lmpy`、`lmpy_back`、`tjxm` 及其部分发型资源就是这样恢复的。
3. **符合 XT 自恢复特征**：从每个文件自身的标准 UnityFS 已知明文恢复 20 字节循环 XOR 密钥，不执行配套插件。
4. **精确符合已分析的无原件 profile**：按该 profile 的 bootstrap、固定错位和结构约束重建，并显式报告无法唯一恢复的尾部字节；哈希不同或任一结构条件不符时重新分析。
5. **只有偏移或少数字段损坏**：只修复被格式或日志证据唯一确定的字段，例如 `0x0BE0 -> 0x1000` 或 Build Target 端序，不做大范围猜测。
6. **SerializedFile 元数据损坏但主体可识别**：仅使用 Unity revision 和 TypeTree 指纹均匹配的正常模板，修复后重新检查全部对象范围。
7. **属于 Bit 二次保护且没有正常原件**：不要用其他发型、generic placeholder 或 24-5 文件替换 Mesh/角色包。必须在隔离的 Unity 环境中让插件运行，或取得对应的正常原件。

### 未知加密方式的参考模组查询

模组数据库的 `zipmods` 表是参考模组发现的首选入口，`guid` 和 `author` 均有索引。查询顺序固定为：

1. `guid = 目标 GUID`，大小写不敏感；
2. 若没有可验证的未加密候选，`author = 目标作者`，大小写不敏感且忽略首尾空白。

两个阶段都要排除 `scan_status = 'stale'`、路径不存在、无法读取或明显仍受保护的文件；同一 GUID 的重复候选可参考 `duplicate_zipmods`，但仍须对实际文件做验证。`mod_items` 可用于从候选 zipmod 的 CSV 记录定位目标 Unity3D 文件，不能替代 zipmod 级参考判断。

参考模组的报告至少记录 GUID、作者、zipmod 路径、输入 SHA-256、Unity revision、TypeTree/节点特征、实际可读性和采用它的理由。若同 GUID 和同作者都没有合格候选，不能把“没有找到参考”当成已知 profile，应该停止离线猜测或转入隔离运行时分析。

批量操作应始终：

- 递归扫描；
- 不覆盖源文件；
- 保留相对目录结构；
- 使用 `.decrypted.unity3d` 或 `.reconstructed.unity3d` 后缀；
- 输出每个文件的状态、对象数量、SHA-256 和失败原因。

## `apps/scripts/decrypt_unity3d.py` 脚本功能

该脚本是项目内用于批量处理 Sakuraba 风格 UnityFS 保护的命令行工具。它不是通用的 Unity 加密破解器，而是针对已识别的资源结构执行安全修复。

### 输入与输出

基本用法：

```powershell
python apps/scripts/decrypt_unity3d.py `
  "E:\protected-assets" `
  --output-dir "E:\decrypted-assets" `
  --template-root "E:\game\hs2\abdata"
```

支持：

- 输入单个 `.unity3d` 文件或目录；
- 默认递归扫描目录；
- `--no-recursive` 关闭递归；
- `--output-dir` 指定输出目录，源文件永远不会被覆盖；
- `--template` 可重复指定一个或多个正常 Unity3D 模板；
- `--template-root` 递归搜索同 Unity 版本和 TypeTree 指纹的正常模板；
- `--overwrite` 允许覆盖已有的输出副本；
- `--json` 输出逐文件 JSON 结果。

输出会保留输入目录的相对结构，并将文件名后缀改为：

```text
原文件名.decrypted.unity3d
```

### 处理流程

脚本的主要步骤如下：

1. 解析 UnityFS 头、block-info、存储块和节点目录；
2. 识别已知的 16 字节保护标记，并在支持的位置移除；
3. 尝试从 AssetBundle 数据中的 `archive:/...resS` 引用修复损坏的资源节点名称；
4. 解压 UnityFS 存储块；
5. 对无法读取的 SerializedFile 节点，按 Unity 版本和 TypeTree 指纹寻找正常模板；
6. 使用模板修复 SerializedFile 元数据、版本、类型表计数、对象范围和数据偏移；
7. 重新编码 block-info 和存储块；
8. 再次解码并验证每个 SerializedFile，确认对象元数据可以读取；
9. 输出 SHA-256、修复层级、模板来源和错误原因。

### 模板匹配原则

脚本不会仅凭文件名套用模板。它要求：

- Unity revision 一致；
- SerializedFile 的 TypeTree 指纹一致；
- 模板能够提供稳定的元数据前缀；
- 修复后的对象范围不能越过 SerializedFile 边界。

找不到匹配模板时，脚本会报告失败，不会生成一个看似可打开但内容错误的文件。

### 适用边界

该脚本适合处理：

- block-info 中插入的已知保护标记；
- 可从 archive 引用恢复的资源节点名称；
- SerializedFile 头和 TypeTree 元数据被破坏、但主体结构仍可识别的文件。

它目前**不能直接处理** `yu` 文件夹中发现的第二层保护：标记位于压缩数据流附近，且后续连续 128 字节已被加密。删除标记后 LZMA/LZ4 仍然无法解压，必须有对应正常原件，或在隔离的 Unity/BepInEx 运行环境中触发原生插件的运行时钩子。

因此，脚本的“失败”不代表 UnityFS 文件一定无法恢复，而是表示当前没有足够的模板或运行时解密条件。脚本输出的 `error`、`skipped` 和 `ok` 状态应结合本节边界解释。

## 验证清单

### UnityPy/AssetStudio

- 能否打开 UnityFS；
- SerializedFile 是否能读取；
- 对象数量是否大于零；
- Build Target 是否为游戏平台预期值，且字节序正确；
- `Texture2D` 是否有名称、尺寸和格式；
- AssetBundle 容器是否存在；
- `placeholder` 是否出现在预期容器路径。

### 二进制完整性

- UnityFS 声明大小与文件结构是否一致；
- block-info、节点偏移和节点大小是否自洽；
- 偏移修复类文件是否只改变预期字段；
- 不要仅凭“AssetStudio 能打开”判断贴图内容完整，仍需检查 Texture2D 数据和容器。

### 对象关系和游戏运行时

- Transform 的 `m_Children`/`m_Father` 是否双向一致，且没有悬空 PathID；
- GameObject 与 Transform 是否一一对应；
- Renderer、SkinnedMeshRenderer、Mesh、骨骼、材质和 MonoBehaviour 的引用是否存在；
- CSV 的 `MainAB`/`MainData` 是否指向实际 bundle 和 prefab；
- 游戏日志是否完成 AssetBundle 加载，而不是只通过离线解析；
- 每个服装、头发和附件 prefab 是否能被 `Object.Instantiate`，不能只测试缩略图或列表显示。

## `recover_sakuraba_no_source.py` 无原件恢复

针对 `sakuraba_26-3-s01_加密.unity3d` 这一已完成对齐分析的样本，项目还提供只依赖加密输入的恢复脚本：

```powershell
conda run -n mm_env python apps/scripts/recover_sakuraba_no_source.py `
  "E:\sakuraba_26-3-s01_加密.unity3d" `
  --output "E:\recovered\sakuraba_26-3-s01.no-source-recovered.unity3d" `
  --report "E:\recovered\sakuraba_26-3-s01.no-source-recovery.json"
```

该脚本不读取正常 Unity3D 模板，也不会覆盖输入文件。它只适用于当前已确认的 Unity `2018.4.11f1`、单 SerializedFile、单 `.resS` 节点布局。SerializedFile 和 `.resS` 的末尾各有 16 字节无法从加密文件唯一推出，默认以零填充并在 JSON 报告中标记；如果层级关系可以唯一确定最后一个 `Transform.m_Father`，脚本会自动用反向 `m_Children` 引用补回该字段。

当前样本验证结果为：2303 个对象可读取，21 类 TypeTree，78 张纹理可解码；与正常原件比较时，2303 个对象原始数据一致，77/78 张纹理逐字节一致，剩余 1 张纹理只涉及末尾 16 字节压缩块。该结果不表示任意 Sakuraba 加密文件都能用此 profile 恢复。

### 已知明文对齐结论

对 `sakuraba_26-3-s01_加密.unity3d` 与正常原件逐字节对齐后，确认该样本不是对整个文件执行不可逆加密，而是在两个节点中制造固定的 16 字节错位：

- SerializedFile 的 `0x00..0x95` 需要用已确认的 Unity 2018/Sakuraba 元数据前缀重建；
- 加密节点从 `0xA6` 开始的内容对应正常节点从 `0x96` 开始的内容，即中间插入或替换了 16 字节；
- 正常 SerializedFile 的对象数据起点为 `0x1DF90`，加密节点中的对应起点为 `0x1DFA0`；
- `.resS` 满足 `protected[0x10:] == normal[:-0x10]`，因此去掉开头 16 字节即可恢复其余内容；
- 加密文件在 UnityFS 声明边界之后还有 16 个物理字节，它们不属于任何 block 或 node，重建时不能带入输出；
- 上述两个节点的正常末尾各有 16 字节没有留在加密输入中，单凭该文件无法唯一推出。

因此，“无原件恢复”准确地说是基于已知格式前缀、确定性位移和对象关系约束进行重建。这里的“无原件”表示脚本执行时不再读取外部正常文件；脚本内嵌的 `0x96` 字节 bootstrap 是此前通过成对样本分析确认的 profile 数据，并不表示可以在完全没有先验信息的情况下解出任意文件。末尾零填充只是显式占位，不代表恢复了原始字节。只有在对象结构能给出唯一答案时，才允许推导占位区域中的字段。

同类型判断必须同时检查 Unity revision、节点数量和类型、元数据大小、数据偏移、位移关系以及重建后的对象边界。只看到 `UnityFS`、相同作者或相同的 16 字节标记，不足以套用该 profile。尤其不能把 `BOOTSTRAP_PREFIX` 直接用于元数据布局不同的资源。

### 本次对话样本分类

| 样本 | 可复核特征 | 分类 | 无正常原件时的结论 |
| --- | --- | --- | --- |
| `sakuraba_26-3-s01_加密.unity3d` | Unity `2018.4.11f1`；不含 Bit 固定标记；SerializedFile 与 `.resS` 呈确定的 16 字节位移 | 已知明文对齐 profile | 可用 `recover_sakuraba_no_source.py` 重建，但必须报告两个节点各自未知的末尾 16 字节 |
| `sakuraba_wyly.unity3d` | Unity `2018.4.11f1`；固定标记位于文件偏移 `0x90`；文件长度与 UnityFS 声明长度不一致 | BepInEx/Bit 运行时二次保护 | 不是 `26-3-s01` profile；没有对应正常原件或隔离的 Unity/BepInEx 运行环境时，不能可靠离线恢复 |
| `sakuraba_25-6-s02.unity3d` | 已能离线解析且没有 Bit 固定标记，但 Build Target 字节序错误，SerializedFile 尾对象存在 Transform 断链 | 恢复后元数据/对象尾部缺陷 | 不能再次套用 Bit 去标记或 `26-3-s01` bootstrap；应修复已被证据唯一确定的字段并做完整 prefab 审计 |

`wyly` 样本的实测指纹如下：

```text
size:          7,311,826 bytes
declared size: 7,311,770 bytes
marker offset: 0x90
SHA-256:       c29b3cabc5ab990297a74d707ed5a2466042edb97d8db4651319e8f3ba1d28b6
```

该样本的物理长度比 UnityFS 声明长度多 56 字节，而不是简单的 16 字节。固定标记之后的压缩数据也不能按标准 LZMA/LZ4 解码，因此“删除 `0x90` 处的标记并修正文件长度”不是恢复方法。它与 `26-3-s01` 的节点内位移在证据上属于两种不同保护。

成对分析使用的 `26-3-s01` 输入指纹为：

```text
protected SHA-256: 14830d85d1d22a16a6b3a9e36c274895123f1c0c5562a4caad1b6f8e561d6d74
normal SHA-256:    7afa3ae81f0b8a1eb6aafb478ae22bd97d07df7792a8551817fd4615d0f7efe1
```

这些哈希用于避免把同名但内容不同的资源误套到当前 profile。若哈希不同，仍需重新验证全部结构特征，不能只凭文件名判定。

### `25-6-s02` 的恢复后故障案例

`[sakuraba]25_6_s02.zipmod` 说明“AssetStudio/UnityPy 可以解析”仍不是最终成功条件。该包中的 Unity3D 在恢复后先后发现两个独立问题。

第一处是 Build Target 字段端序错误。样本文件偏移 `0xAA` 的四字节为：

```text
00 00 00 13  -> 按 little-endian 读取为 318767104，游戏拒绝加载
13 00 00 00  -> 按 little-endian 读取为 19，即 StandaloneWindows64
```

游戏日志对应提示为：

```text
File's Build target is: 318767104
The AssetBundle 'Memory' can't be loaded because it was not built with the right version or build target.
```

该偏移是当前样本的物理位置，不应当作为所有 Unity3D 的固定偏移。修复时应解析 SerializedFile 元数据、确认目标值和端序，只改动实际错误的两个字节。

第二处位于 `25-6-s02_bot.prefab`。Build Target 修复后，游戏已能进入 `Object.Instantiate`，但加载下装时原生闪退。审计发现唯一的 Transform 双向关系断链：

```text
父 Transform PathID: -4704507276268317942  (cf_J_LegLowRoll_R)
子 Transform PathID:  9215128663154997056  (cf_J_Foot01_R)

父对象 m_Children 包含子对象
子对象 m_Father 却为 0
```

对应崩溃栈停在：

```text
UnityEngine.Object.Internal_CloneSingle
UnityEngine.Object.Instantiate
CommonLib.LoadAsset
ChaControl.LoadCharaFbxData
ChangeClothesBotAsync
```

崩溃前最后一个相关日志是 `BonesFramework: Found matching line for asset 25-6-s02_top`。这组证据把故障范围缩小到下装 prefab 实例化阶段，而不是 CSV 列表、缩略图或 AssetBundle 外层读取阶段。

子 Transform 恰好是 SerializedFile 的最后一个对象，`m_Father` 又位于对象末尾，说明无原件恢复时的 16 字节尾部占位覆盖了真实父引用。由于父对象的 `m_Children` 提供了唯一反向证据，可以把最后 8 字节恢复为父 PathID；若存在零个或多个候选父对象，则必须停止，不能猜测。

本次还排除了 UnityFS 外层损坏、CSV `MainAB`/`MainData` 不匹配、GUID/资源路径/CAB 重复、Mesh/Texture2D 解码失败、材质或骨骼空引用等原因。Sideloader 的 `conflicting CAB string` 提示不能替代 Unity 原生日志中的 Build Target 证据。`TopBAnim.CopyHairColor` 缺失脚本警告在正常对比模组中也出现同名脚本依赖，且启动日志已显示 `TopBAnim` 被加载，因此没有把它认定为此次下装原生闪退的直接原因；若后续只有发型异常，应再单独检查插件版本和脚本绑定。

该案例形成以下通用规则：

- Build Target、Unity revision、对象表和容器都应分别验证；
- 对每个 Transform 检查 `parent.m_Children` 与 `child.m_Father` 是否双向一致；
- 对 GameObject、Renderer、SkinnedMeshRenderer、骨骼、材质和 MonoBehaviour 的 PPtr 检查目标是否存在且类型合理；
- 尾部未知字节落在对象字段内时，不能把零填充视为可交付结果；
- 解析验证通过后仍需在游戏日志中确认 AssetBundle 加载，并分别实例化每个衣物/发型 prefab；
- 打包测试时只保留一个相同 GUID/资源路径的 zipmod，避免旧版和修复版互相覆盖。

本次第二版修复包的 SHA-256 为：

```text
zipmod:  c52983644d143de3ea42502e98defc418b1e45d21af026414753095636820549
Unity3D: c3f9b29c39b44f8ae0875f0ff7cc3401dca8f2ba55bf26f0152d697520c32f48
```

最终静态审计结果为 2786 个对象、1100 个 GameObject、1100 个 Transform、125 个 Mesh、164/164 张可解码 Texture2D、13 个 AssetBundle container 项和 10 个完整 prefab；已检查的对象与资源引用没有剩余错误。这里的哈希和数量只用于识别本次产物，不能作为其他文件的通用模板。

## 鞋类 `CmpClothes` 对照修复记录

### 问题背景

`D:\Workspace\Star_workspace\shoes_1\abdata\chara\yukilat\yukilat_shoes_1_1.unity3d` 中，`shoe_333_3_obj` 可以换色，但 `shoe_333_1_obj` 和 `shoe_333_2_obj` 不响应。该文件不是 UnityFS 解密失败，而是复制/改写后对象关系和 AssetBundle 预加载段不一致。

### 根因

- 鞋类 `CmpClothes` 没有上下衣变体对象。前两个对象的 `objTopDef` 被错误填成了自身层级的 `n_shoes_00`，而同文件可用的鞋对象及其它正常鞋资源都保持该组变体字段为空。
- `rendNormal01` 与 `rendCheckVisible` 是实际换色渲染器列表，前两个对象应分别指向自身的 `n_shoes_00` `SkinnedMeshRenderer`；这两个引用不能用 `objTopDef` 代替。
- `shoe_333_2_obj` 的 AssetBundle 预加载段比可用的 `shoe_333_3_obj` 少了两个内置依赖；三个鞋对象的入口段应保持完整、连续且可解析的依赖链。

### 解决方案

- 从当前文件重新生成隔离候选，不叠加上一次错误的 `objTopDef` 修复；将 `shoe_333_1_obj` 和 `shoe_333_2_obj` 的四个上下衣变体字段清为空引用。
- 以 `shoe_333_3_obj` 的预加载段结构为对照，为前两个入口补齐内置依赖，并按材质、贴图、渲染器、Mesh 的完整依赖顺序重建段索引。
- 输出通过验证后才替换外部资源，并在同目录保留原文件备份。

### 验证结果

- 当前输入哈希：`876FE1087BB9176DA88E951F7AE84BF114CF9C8139B3D03CCF4294A5F6BDD527`；修复候选哈希：`5F97B69357B40069CA49C819A1C72072938B0BD2262D3A7F9A475C02BDD2E030`。
- UnityPy 重新打开后对象数保持 `843`；10 个 AssetBundle 容器段连续覆盖完整预加载表，三个鞋对象入口均为 `280` 项，所有本地 PPtr 均能解析。
- 三个鞋对象的 `CmpClothes` 均保持自身 `m_GameObject` 和 `rendNormal01`，四个上下衣变体引用均为空；除预期的两个 `CmpClothes` 字段和 AssetBundle 预加载索引外，没有改动其它对象序列化数据。

### 2026-09-06 当前文件复核与旁置修复候选

本次重新收到同一路径文件后，读取期间外部文件曾发生更新；最终用于生成候选的源文件哈希为
`90471288EB26D2D99DCF3E90EE6C969D164CE79F2A9C531F0FF82A66B3F71BA4`，对象数为 `1939`，与上方旧案例的输入版本不同。源文件没有被覆盖。

对当前版本的静态检查确认：`shoe_333_1_obj`、`shoe_333_2_obj` 和 `shoe_333_3_obj` 的
`CmpClothes` 已经分别指向自身的 `m_GameObject`、`n_shoes_00` 的
`SkinnedMeshRenderer`，四个上下衣变体引用均为空；唯一仍与完整鞋入口不一致的是
`shoe_333_2_obj` 的 AssetBundle 预加载段只有 `278` 项，且缺少开头的两个外部依赖
`(fileID=1, pathID=6/7)`。

已生成旁置候选：

```text
D:\Workspace\code_workspace\Star_Manager\apps\tmp\yukilat_shoes_1_1.shoe-333-color-repaired.unity3d
```

修复只在预加载表索引 `292` 插入上述两个依赖，将 `shoe_333_2_obj` 段改为 `280` 项，并将其后的容器起始索引顺移 `2`；没有修改模型、材质、贴图或 `CmpClothes` 字段。候选哈希为
`69E9B8FEA4954C0A2BD496AC2A632F34D51A36849B91E2670238541B1FE39606`。

候选经 UnityPy 重新读取通过：对象数仍为 `1939`，预加载表为 `1976` 项，三个鞋入口均为
`280` 项，容器区间完整覆盖预加载表且不重叠，所有本地预加载 PPtr 均可解析，三组
`CmpClothes` 换色字段检查通过。该结果仍属于离线结构验证，需在实际游戏加载和换色流程中复测。

### 适用边界

- 本规则仅适用于鞋类或其它没有上下衣变体节点的 `CmpClothes` 对象；服装上衣/下装必须根据实际 `n_top_a`、`n_top_b` 或 `n_bot_a` 节点填写变体引用，不能一概清空。
- 仅看到 `rendNormal01` 正确并不代表资源可换色，还必须检查 AssetBundle 容器入口、预加载段、内置依赖和材质/贴图/渲染器/Mesh 链。
- 游戏运行时换色仍需在实际角色加载流程中复测；离线 UnityPy 验证只能确认序列化结构和引用完整性。

## Mesh 零切线修复

各向异性衣物/头发着色器会依赖 Mesh tangent 构建光照方向。若部分顶点的 tangent 为
`(0, 0, 0, w)`，贴图即使完整、不透明，也可能在这些顶点相邻的三角面上出现黑色缺口。
这类异常经常由 UV 面积为零的三角形触发切线生成失败。

`apps/scripts/repair_unity3d_zero_tangents.py` 会从相邻 UV 非退化三角面计算替代切线，只修改
原顶点缓冲中的无效 float32 tangent，不合并顶点、不删除面、不修改 UV、蒙皮或已有的有效切线。
脚本永远不会覆盖源文件，并在写出后重新载入结果验证非切线数据未变化：

```powershell
conda run -n mm_env python apps/scripts/repair_unity3d_zero_tangents.py `
  "D:\path\source.unity3d" `
  "D:\path\source.repaired.unity3d" `
  --report "D:\path\tangent-repair-report.json"
```

先只检查而不写出文件：

```powershell
conda run -n mm_env python apps/scripts/repair_unity3d_zero_tangents.py `
  "D:\path\source.unity3d" `
  --dry-run
```

当前脚本只处理 Unity 2018.1 及以上、顶点数据内嵌于 SerializedFile、tangent 通道为四分量
float32 且未使用压缩 tangent 的 Mesh。遇到外部 `resS`、压缩切线或无法从相邻有效 UV 面恢复的
顶点时会停止，不输出部分修复文件。

若问题仍处于 FBX 源模型阶段，可使用 `apps/scripts/blender_repair_fbx_tangents.py`。该脚本通过
Blender 为每个 UV 层计算 MikkTSpace，并在新 FBX 中明确写入 `LayerElementTangent` 和
`LayerElementBinormal`。它不会覆盖源 FBX，写出后会检查全部切线向量并重新导入核对顶点、面、
UV 层、材质槽、顶点组、形态键和骨架名称：

```powershell
& "D:\path\Blender\blender.exe" --background --factory-startup `
  --python apps/scripts/blender_repair_fbx_tangents.py -- `
  --input "D:\path\source.fbx" `
  --output "D:\path\source.tangent-repaired.fbx" `
  --report "D:\path\fbx-tangent-repair.json"
```

修复后的 FBX 在 Unity/资源导入器中应选择导入 FBX 自带切线，而不是再次丢弃并重新计算切线。

### B020 裙子黑色三角形案例

`D:\Workspace\Star_workspace\B020\SEOULSOUL_2024__40_Skirt_lod0_fbx\SEOULSOUL_2024__40_Skirt_model01_lod0_719E19E713EBDB09.fbx`
出现与服装缝线/口袋边缘相邻的黑色三角形。该文件不是贴图损坏，也不是位置重合的反向重复面：
重复面扫描提议删除面数为 `0`，几何退化面数为 `0`，相邻面绕序冲突为 `0`。

根因是 FBX 没有 `LayerElementTangent`/`LayerElementBinormal`，同时两个 UV 层分别存在
`868` 和 `875` 个 UV 面积为零的三角形。各向异性或依赖切线空间的着色器在这些区域可能得到不稳定
的切线，最终表现为黑色三角形。源文件的法线层本身是 `ByPolygonVertex`，只有少量边界/接缝角点
与几何面法线不完全同向；没有发现上一次 `fixed.fbx` 案例中那种大范围共享顶点法线错配，因此不能
通过合并顶点法线或删除面来修复。

修复方式是以源 FBX 为输入，保留原始分角法线、顶点、面和 UV，仅使用 Blender MikkTSpace 为两个
UV 层生成并写入 `21801` 个有效切线及副切线向量。修复结果保持 `3679` 个顶点和 `7267` 个三角面，
重新导入验证通过；输出文件为同目录的
`SEOULSOUL_2024__40_Skirt_model01_lod0_719E19E713EBDB09_repaired.fbx`，源文件未覆盖。

适用边界：该修复能处理 FBX 阶段缺失切线导致的黑三角形，但不会改变原始 UV 退化面，也不能保证
着色器自身在 `Cull Off` 背面绘制时正确翻转法线。若导入修复文件后仍有黑色面，应确认 Unity 的
Normals/Tangents 导入设置为使用 FBX 数据，并继续检查 Shader 是否使用 `VFACE` 处理背面法线。

### B017 短裤 `normals_repaired_v2` 黑色三角形案例

`D:\Workspace\Star_workspace\B017\SEOULSOUL_2024__53_Shorts_lod0_fbx\SEOULSOUL_2024__53_Shorts_model01_lod0_6BD987F0B6B169A2_normals_repaired_v2.fbx`
也出现类似黑色三角形。该文件的法线层已经是 `ByPolygonVertex`，不是 B016 `fixed.fbx` 那种共享
顶点法线被错误合并的问题；位置重合反向面扫描提议删除面数为 `0`，因此不删除面或重新合并顶点。

根因仍是 FBX 未写入 `LayerElementTangent`/`LayerElementBinormal`。目标文件两个 UV 层分别有
`2948` 和 `3221` 个退化 UV 面，缺少切线时会让依赖切线空间的服装着色器在局部三角面上产生黑色
光照结果。修复以用户指定的 `normals_repaired_v2.fbx` 为源，保留其法线结果、顶点、面和 UV，
仅补写两个 UV 层的 MikkTSpace 切线与副切线；源文件没有覆盖。

修复输出为同目录的
`SEOULSOUL_2024__53_Shorts_model01_lod0_6BD987F0B6B169A2_normals_repaired_v2_tangent_repaired.fbx`。
验证结果：`11182` 个顶点、`19679` 个三角面和 `59037` 个面角点保持不变；两个 UV 层均写入
`59037` 个有效切线向量，FBX 重新导入成功，分角法线状态保持一致。

适用边界：该结果保留原文件的 UV 退化面和少量服装内外层相邻面法线差异；它不等同于删除面或
重建 UV。若导入后仍有黑三角，应确认 Unity 使用 FBX 自带 Normals/Tangents，并检查 `Cull Off`
着色器是否通过 `VFACE` 对背面法线进行翻转。

### B042 长裤内侧两条黑色长条案例

`D:\Workspace\Star_workspace\B042\SEOULSOUL_2025__100_Pants_lod0_fbx\SEOULSOUL_2025__100_Pants_model01_lod0_464FDAB9062D9ABE.fbx`
在游戏内的裤腿内侧出现两条连续黑色长条。截图中的位置与 FBX 内两组对称的独立窄条几何相对应：
它们分别包含 `576` 和 `552` 个三角面，属于同一个 Mesh 的独立连通组件。组件局部法线均与几何
面法线同向，扫描没有发现重合反向面、几何退化面或面绕序冲突，因此不能通过删面或整体翻转法线
处理，否则会破坏原本的服装细节。

根因是源 FBX 完全没有 `LayerElementTangent`/`LayerElementBinormal`。同时 `UVChannel_1` 有
`1104` 个零面积三角形，细长组件本身虽然有非零 UV，但 UV 面积非常小。`Cull Off` 着色器仍会
绘制这些背面/窄条面；当切线空间缺失或不稳定时，法线贴图/光照方向在这两条面上会得到黑色结果，
所以表现为连续黑条，而不是贴图文件损坏。该文件的源法线层仍是 `ByPolygonVertex`，没有发现
B016 那种全局共享法线错误。

修复以源 FBX 为输入，保留顶点、三角面、五个连通组件、原法线、UV、材质槽和顶点组，仅使用
Blender MikkTSpace 为 `UVChannel_1` 与 `UVChannel_2` 写入切线/副切线。输出为同目录旁置文件：

`SEOULSOUL_2025__100_Pants_model01_lod0_464FDAB9062D9ABE_tangent-repaired.fbx`

验证结果：`10852` 个顶点、`21481` 个三角面、`64443` 个面角点和五个连通组件保持不变；输出含
两个 `LayerElementTangent` 和两个 `LayerElementBinormal`，每层均有 `64443` 个有效向量，并已
重新导入验证通过。源 FBX 未覆盖。

适用边界：导入 Unity/游戏资源时应选择使用 FBX 自带 Normals/Tangents，避免导入器再次丢弃切线。
本修复不删除独立窄条、不重建 UV，也不改变 Cull Off 着色器的背面法线策略；若导入副本后仍有黑条，
需检查 shader 是否用 `VFACE` 翻转背面法线，以及材质是否实际绑定了修复后的 Mesh。

### B042 裙子法线异常案例

`D:\Workspace\Star_workspace\B042\SEOULSOUL_2025__106_Skirt_lod0_fbx\SEOULSOUL_2025__106_Skirt_model01_lod0_C7D51983201E766C.fbx`
的源法线层为 `ByVertice + IndexToDirect`，每个顶点只有一个共享法线。拓扑扫描没有发现位置重合的
反向重复面、几何退化面或面绕序冲突，但有 `131` 个面角点的源法线与所属几何面法线点积小于 `0`，
最小点积约为 `-0.963`。这来自裙摆褶皱、内外层和锐利边界仍共享顶点平滑法线，进入 `Cull Off` 或
依赖切线空间的着色器后容易表现为黑色三角/黑色边。

该 FBX 同时没有 `LayerElementTangent`/`LayerElementBinormal`，`UVChannel_1` 和 `UVChannel_2`
分别有 `692`、`771` 个 UV 零面积三角形，因此仅修正法线仍可能留下切线空间异常。修复时保留原始
顶点、面、UV、材质和权重，按相邻面法线夹角 `0.5`（约 60°）重建平滑组，写入每个面角点的
`ByPolygonVertex` 法线；对剩余 `3` 个反向角点直接使用所属几何面法线，并为两个 UV 层补写有效
MikkTSpace tangent/binormal。

输出文件为：

`SEOULSOUL_2025__106_Skirt_model01_lod0_C7D51983201E766C_normals-repaired-final.fbx`

验证结果：`4484` 个顶点、`13204` 条边、`8713` 个三角面、`26139` 个面角点和 `12` 个顶点组保持
不变；输出法线层改为 `ByPolygonVertex`，法线与几何面法线反向的面角点降为 `0`，两个 UV 层均
生成 `26139` 个有效切线向量，FBX 重新导入通过。源文件未覆盖。

适用边界：该修复保留裙摆的平滑效果，只在约 60° 以上的几何折角处分组，并修正极少数反向角点；
导入 Unity/游戏时仍应选择使用 FBX 自带 Normals/Tangents。若游戏内仍有黑面，应继续检查材质是否
绑定了该副本以及 `Cull Off` shader 是否通过 `VFACE` 正确处理背面法线。

## 安全要求

`Bit.xml` 是未知来源的原生 DLL。其导入表包含网络和密码学相关系统库（例如 WinHTTP、DNSAPI、BCrypt、Crypt32），不能据此断定它恶意，但足以要求隔离运行。

建议使用：

- 关闭网络的 Windows 虚拟机；
- 只读挂载输入资源目录；
- 独立的可写输出目录；
- 临时 BepInEx 插件目录；
- 运行结束后销毁虚拟机或回滚快照。

当前机器为 Windows 10 Home，未检测到可用的 Windows Sandbox、VirtualBox、VMware 或 Sandboxie，因此不应在主机游戏目录中直接运行该插件。此前生成的恢复文件不需要插件即可使用；未恢复的 Bit 二次保护文件应在具备上述隔离条件后再处理。

## 当前记录的批处理结果

`E:\download\南海二次加密\yu` 共扫描到 19 个 Unity3D 文件。已有完全对应正常原件、或本身已能正常解析的 11 个文件已输出到：

```text
E:\download\南海二次加密\yu_decrypted
```

仍缺少可靠原件或隔离运行条件的文件包括 `scfy`、`wyly`、`yysy` 相关资源。详细清单保存在该输出目录的 `restore_report.json` 中。

## `wen` 恢复资源的 zipmod 打包结果

本次根据用户提供的两个原始 zipmod 的 CSV 引用，将恢复后的 Unity3D 写入新的副本，原始 zipmod 未覆盖：

| 输出包 | CSV 引用路径 | 写入的恢复资源 |
| --- | --- | --- |
| `apps/tmp/wen陈樱儿v5.recovered.zipmod` | `abdata/wen/wen3siwa.unity3d` | `wenchenyinger.decrypted.unity3d` |
| `apps/tmp/wen陈樱儿.recovered.zipmod` | `abdata/wen/wenxuanyi5.unity3d`、`abdata/wen/wenxuanyi.unity3d` | 分别写入 `wenchenyinger5.decrypted.unity3d`、`wenchenyinger.decrypted.unity3d` |

两个输出包均已确认包含 `manifest.xml`、全部原 CSV 和 CSV 引用的 Unity3D 路径，zip CRC 校验通过。恢复资源的静态验证结果分别为 `5260` 个对象/`23` 张纹理和 `5291` 个对象/`30` 张纹理。

静态验证还发现部分 CSV 的 `MainData` 在恢复资源的 AssetBundle 容器中没有同名入口：v5 包涉及 `madai`、`lianku`、`lianti2`，普通包涉及 `back`、`headq`、`headr`、`headl`、`leg`、`piaodai`。因此本次只按 CSV 路径完成打包，没有擅自改写 CSV 或猜测性重命名 Unity3D 容器；这些条目仍需在 HS2 游戏内实际加载确认，必要时再依据同作者正常资源决定映射。
