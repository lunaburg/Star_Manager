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

## 正确的恢复策略

优先级如下：

1. **有完全对应的正常原件**：从正常游戏 `abdata` 或对应 zipmod 提取同名资源，逐个验证后作为恢复结果。此前 `lmpy`、`lmpy_back`、`tjxm` 及其部分发型资源就是这样恢复的。
2. **只有偏移字段损坏**：按 `0x0BE0 -> 0x1000` 规则生成 `.reconstructed.unity3d`。
3. **属于 Bit 二次保护且没有正常原件**：不要用其他发型、generic placeholder 或 24-5 文件替换 Mesh/角色包。必须在隔离的 Unity 环境中让插件运行，或取得对应的正常原件。

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
- `Texture2D` 是否有名称、尺寸和格式；
- AssetBundle 容器是否存在；
- `placeholder` 是否出现在预期容器路径。

### 二进制完整性

- UnityFS 声明大小与文件结构是否一致；
- block-info、节点偏移和节点大小是否自洽；
- 偏移修复类文件是否只改变预期字段；
- 不要仅凭“AssetStudio 能打开”判断贴图内容完整，仍需检查 Texture2D 数据和容器。

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
