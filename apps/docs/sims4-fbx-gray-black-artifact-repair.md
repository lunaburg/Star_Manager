# Sims 4 FBX 灰黑块修复记录

## 问题背景

`SEOULSOUL_2025__106_Skirt_model01_lod0_C7D51983201E766C_normals-repaired-final.fbx` 经 SB3Utility 打包为 Unity3D 后，裙面出现局部灰黑高光块。原文件由 Blender FBX IO 导出，包含两个 UV 通道及对应的 tangent/binormal 层。

## 根因与处理

仅修复法线不能保证 Unity/SB3Utility 使用的切线空间一致。对原 FBX 重新导入并按每个 UV 通道使用 Blender MikkTSpace 重算 tangent/binormal，再导出为独立副本。修复脚本同时验证了 FBX 版本、切线层数量、向量有限性和重新导入结果。

## 验证结果

- 原始与修复文件均为 FBX 7400。
- 两个 UV 通道各有 26,139 个 tangent 向量；重算后 invalid tangent 数为 0。
- 修复副本已写入用户工程目录，未覆盖原始 FBX。

## 适用边界

该处理只修复法线/切线空间导致的光照伪影，不改变网格、材质或贴图。若仍存在黑块，应在 SB3Utility 中确认材质 shader、贴图绑定到正确的 UV 通道，并检查 Unity 贴图导入的 Alpha/Cutout 设置。

## 2026-08-29 口袋区域双面黑三角案例

### 问题背景

`SEOULSOUL_Chic_Mood_N1_Slacks_lod0_fbx/meshes0.fbx` 在游戏材质启用双面显示时，臀部口袋附近出现黑色三角形。用户提供的截图和 FBX 均用于本次诊断；原始 `meshes0.fbx` 未被覆盖。

### 根因

该 FBX 为 7400 二进制格式，包含 5,000 个顶点、9,593 个三角面、2 套 UV、Skin/Cluster 蒙皮数据和 1 个材质。法线向量长度均正常，没有零值或非有限值；但有 6 个局部三角面的几何面法线与导入的角点法线平均方向相反，合计 10 个异常角点。文件没有显式 tangent/binormal 层，Unity 因此会按 UV 和法线重建切线。双面材质使原本会被背面剔除的错误面可见，错误光照将其显示为黑三角。相关 UV 同时落在贴图的实黑、不透明区域，因此贴图会放大该现象，但不是透明度孔洞根因。未发现完全重合的反向重复三角面。

### 解决方案

使用 `apps/scripts/blender_repair_fbx_normals.py` 导入源 FBX，按几何面法线与角点法线的方向冲突定位并翻转 6 个局部面，清除旧的自定义分割法线，再导出新的 FBX；随后使用 `apps/scripts/blender_repair_fbx_tangents.py` 按两套 UV 以 Blender MikkTSpace 重算 tangent/binormal。修复过程保留网格拓扑、骨架、权重、UV 和材质，不覆盖源文件。

### 验证结果

- 输出文件：`meshes0.normals-repaired.tangent-repaired.fbx`。
- 原文件与输出文件均为 FBX 7400。
- 修复后仍为 5,000 个顶点、9,593 个三角面、28,779 个面角、2 套 UV，骨架和顶点组结构重新导入一致。
- 输出包含 2 个 tangent 层和 2 个 binormal 层，每层 28,779 个向量，无无效 tangent。
- 原文件 SHA-256：`5f55206c57496efd40a3459b5d2be3225ff52d5e09b5999cc2478af95fd7ce2c`；修复输出另存，未改变原文件。

### 适用边界

该修复针对“局部面绕序与自定义法线冲突、双面显示出现黑三角”的情况。如果修复后仍出现同形状黑块，应使用纯白无贴图材质复测；若黑块消失，则继续检查主 UV 是否落到贴图内的黑色细节区域或是否绑定了错误的纹理/UV 通道。

## 2026-08-29 B006 裤绳视角相关黑色三角形案例

### 问题背景

`D:\Workspace\Star_workspace\B006\SEOULSOUL_2024__42_Bottoms_ONLY_lod0_fbx\SEOULSOUL_2024__42_Bottoms_ONLY_model01_lod0_DFAF493291C4C20D.fbx` 在游戏中观察裤绳时，部分视角会出现局部黑色三角形。原始 FBX 未覆盖，修复结果另存于同目录。

### 根因

源文件为 FBX 7400，包含 5386 个顶点、10567 个三角面、31701 个面角点、2 套 UV 和 1 个材质，但没有 `LayerElementTangent`/`LayerElementBinormal`。两套 UV 分别有 838 和 1688 个零面积三角形；Blender MikkTSpace 仍能为全部面角计算出有限切线，但在游戏着色器自行重建切线时，这些退化 UV 会使裤绳附近的切线空间不稳定。

此外，几何面法线与导入角点法线扫描发现 11 个方向冲突面，其中 10 个集中在裤绳附近（最小点积约 `-0.947`），另 1 个位于模型其它位置；未发现位置重合且方向相反的重复面。因此黑色伪影同时受到缺失切线和局部法线/面绕序冲突影响，不是贴图透明孔洞或重复面导致。

### 解决方案

先使用 `apps/scripts/blender_repair_fbx_normals.py` 翻转这 11 个局部冲突面、清除旧的自定义分割法线，再使用 `apps/scripts/blender_repair_fbx_tangents.py` 按两套 UV 以 Blender MikkTSpace 写入显式 tangent/binormal。处理不删除面、不重建 UV、不修改材质、骨架、权重或顶点组。

### 验证结果

- 输出文件：`SEOULSOUL_2024__42_Bottoms_ONLY_model01_lod0_DFAF493291C4C20D_normals-tangent-repaired.fbx`。
- 源文件 SHA-256：`97338acb41de8eb08cf55c1a0ee3a116e5dfeb47bf30ed4406cb01b0885f660f`；修复文件 SHA-256：`453e15701a20a81615a0cd699cef43af3172e4c73b20724e40ac1cd7ff40efdb`。
- 重新导入后网格仍为 5386 个顶点、10567 个三角面、31701 个面角点和 2 套 UV；FBX 版本仍为 7400。
- 输出包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 31701 个向量，全部有效；法线冲突均已降至脚本阈值 `-0.05` 以上。

### 适用边界

该修复针对 FBX 源阶段的缺失切线和局部法线方向冲突。导入 Unity/SB3Utility 时应选择使用 FBX 自带 Normals/Tangents，避免导入器丢弃已写入的切线；若游戏中仍有黑色，应确认材质实际绑定了修复副本，并继续检查 `Cull Off` shader 是否用 `VFACE` 正确处理背面法线。`UV` 零面积面仍被保留，未进行 UV 重建。

## 2026-08-30 B019 裤脚内侧黑色三角形案例

### 问题背景

`D:\Workspace\Star_workspace\B019\SEOULSOUL_2024__36_Shorts_lod0_fbx\SEOULSOUL_2024__36_Shorts_model01_lod0_5725857E5FEECC53_transformed.fbx` 在裤脚内侧出现多处黑色三角形。原始 FBX 未覆盖，修复结果另存于同目录。

### 根因

该 FBX 为 7400 二进制格式，包含 8,937 个顶点、17,090 个三角面、51,270 个面角点、2 套 UV 和 1 个材质，但没有显式 `LayerElementTangent`/`LayerElementBinormal`。两套 UV 存在零面积三角形：`UVChannel_1` 为 1,156 个，`UVChannel_2` 为 188 个。Blender 仍可计算有限切线，但游戏或导入器自行重建切线时，退化 UV 会使裤脚内侧的切线空间不稳定，从而被光照显示为黑色三角形。

法线方向扫描未发现需要翻转的局部面（0 个冲突面，最小几何法线与导入角点法线点积约 0.459），位置重合的反向重复面扫描也未发现候选。因此本案例不是面绕序、反向重复面或透明贴图孔洞导致。

### 解决方案

使用 `apps/scripts/blender_repair_fbx_tangents.py` 导入源 FBX，按两套 UV 以 Blender MikkTSpace 计算并写入显式 tangent/binormal；不翻转面、不删除面、不重建 UV，不修改材质、骨架、权重或顶点组。输出文件为：

`SEOULSOUL_2024__36_Shorts_model01_lod0_5725857E5FEECC53_transformed.normals-tangent-repaired.fbx`

### 验证结果

- 源文件 SHA-256：`4568705641606B86D36E3E09BDB41449A9C64635999ADE05ECC9DA64E140A803`。
- 修复文件 SHA-256：`BF56987BF2B9E3814A31F225EE77D14FEB29EE37A5C45C63B1AFA5B90748BD9E`。
- 输出包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 51,270 个向量，导出后无无效 tangent。
- FBX 重新导入验证通过；网格仍为 8,937 个顶点、17,090 个三角面、51,270 个面角点和 2 套 UV，结构元数据一致。
- 原始文件修改时间和哈希未改变。

### 适用边界

该修复针对本文件确认的“缺失显式切线 + 局部退化 UV”光照伪影。`UV` 零面积面仍被保留，因为直接重建会改变贴图映射；如果游戏中仍出现同样黑三角，应确认实际使用的是修复副本、Unity/SB3Utility 没有丢弃自带 Normals/Tangents，并检查 shader 的 UV 通道和双面处理。

## 2026-08-30 B020 口袋处黑色三角形案例

### 问题背景

`D:\Workspace\Star_workspace\B020\SEOULSOUL_2024__40_Skirt_lod0_fbx\SEOULSOUL_2024__40_Skirt_model01_lod0_719E19E713EBDB09_repaired.fbx` 在口袋缝线附近出现黑色三角形。用户提供的截图和 FBX 均用于本次诊断；原始 `*_repaired.fbx` 未被覆盖，修复结果另存于同目录。

### 根因

该 FBX 为 7400 二进制格式，包含 3,679 个顶点、7,267 个三角面、21,801 个面角点、2 套 UV、1 个材质和骨架，但没有显式 `LayerElementTangent`/`LayerElementBinormal`。`UVChannel_1` 和 `UVChannel_2` 分别检测到 868 和 875 个零面积 UV 三角形。Blender 可以为全部面角计算出有限切线，但游戏或导入器自行重建切线时，口袋缝线附近的退化 UV 会使切线空间不稳定，局部光照遂显示为黑三角。法线方向冲突扫描和位置重合反向重复面扫描均未发现候选，因此本案例不需要翻转面或删除几何；纹理中的深色口袋区域可能放大可见度，但不是几何孔洞。

### 解决方案

使用 `apps/scripts/blender_repair_fbx_tangents.py` 导入源 FBX，按两套 UV 以 Blender MikkTSpace 计算并写入显式 tangent/binormal；不翻转面、不删除面、不重建 UV，不修改材质、骨架、权重或顶点组。输出文件为：

`SEOULSOUL_2024__40_Skirt_model01_lod0_719E19E713EBDB09_repaired.tangent-repaired.fbx`

### 验证结果

- 源文件 SHA-256：`e71f7c926945d4cce212fa4d77d2566affa14e43f4f71c580a4f6a6f6e927556`。
- 修复文件 SHA-256：`afb9232e63c669da774f19970635cda94d4daf063a722f0de20e29ae6cd36d0a`。
- 输出包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 21,801 个向量，导出后无无效 tangent。
- FBX 重新导入验证通过；网格仍为 3,679 个顶点、7,267 个三角面、21,801 个面角点和 2 套 UV，材质、骨架和顶点组元数据一致。
- 修复副本再次扫描未发现位置重合反向重复面；源文件哈希和修改时间未改变。

### 适用边界

该修复针对本文件确认的“缺失显式切线 + 局部退化 UV”光照伪影。`UV` 零面积面仍被保留，因为直接重建会改变贴图映射；导入 Unity/SB3Utility 时应选择使用 FBX 自带 Normals/Tangents，确认实际绑定修复副本且导入器没有丢弃切线。如果游戏中仍出现同形状黑三角，应使用纯白无贴图材质复测，并继续检查 shader 的 UV 通道、Alpha/Cutout 和双面 `VFACE` 处理。

## 2026-09-05 B040 牛仔裤局部灰黑/三角伪影案例

### 问题背景

`D:\Workspace\Star_workspace\B040\SEOULSOUL_2026__155_Jeans_lod0_fbx\SEOULSOUL_2026__155_Jeans_model01_lod0_4EFDA4DF2E0D40DB.fbx` 在模型局部出现灰黑三角形高光块。原始 FBX 未覆盖，修复结果另存为同目录的 `*.tangent-repaired.fbx`。

### 根因

该 FBX 为 7400 二进制格式，包含 30,660 个面角、10,220 个三角面、2 套 UV、1 个材质和骨骼，但源文件没有 `LayerElementTangent`/`LayerElementBinormal`。`UVChannel_1` 和 `UVChannel_2` 分别检测到 664 和 757 个零面积 UV 三角形。几何三角面均有效，导入法线长度正常且未发现法线方向冲突或位置重合的反向重复面，因此本案例符合“缺失显式切线 + 退化 UV 导致切线空间不稳定”的光照伪影，而不是几何破面或透明贴图孔洞。

### 解决方案

使用 `D:\desktop_app\blender\blender-launcher.exe` 运行 `apps/scripts/blender_repair_fbx_tangents.py`，按 `UVChannel_1` 和 `UVChannel_2` 通过 Blender MikkTSpace 写入显式 tangent/binormal。修复不翻转面、不删除面、不重建 UV，不覆盖源 FBX。输出文件为：

`D:\Workspace\Star_workspace\B040\SEOULSOUL_2026__155_Jeans_lod0_fbx\SEOULSOUL_2026__155_Jeans_model01_lod0_4EFDA4DF2E0D40DB.tangent-repaired.fbx`

### 验证结果

- 源文件 SHA-256：`884927FA627D50A8DAFE31669B116762B91585EC49CA0BCC9317D1E0030BC388`。
- 修复文件 SHA-256：`A80E0E900E7F8D339448AFDE824D67BB0E3797DF1C4D753C7DDCCE8954E3593A`。
- 修复后包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 30,660 个向量，`invalid_count=0`。
- Blender 脚本重新导入验证通过；网格仍为 10,220 个三角面、30,660 个面角和 2 套 UV。独立 Three.js 复核确认输出仍无零面积几何面、无异常法线方向，法线长度范围为约 `1.0`。
- 源文件哈希和修改时间未改变。

### 适用边界

该处理修复的是 FBX 源阶段的切线空间问题；UV 零面积面仍被保留，以避免改变贴图映射。导入 Unity/SB3Utility 时应选择使用 FBX 自带 Normals/Tangents，并确认材质实际绑定修复副本。如果游戏中仍有同形状黑块，应使用纯白无贴图材质复测，再检查导入器是否丢弃切线、shader 的 UV 通道、Alpha/Cutout 和双面 `VFACE` 处理。

### 后续复核：闪烁残影与 z-fighting

用户反馈仅写入 tangent 后仍有灰色残影并随视角闪烁。对上一版 `*.tangent-repaired.fbx` 使用位置容差 `0.001`、法线点积阈值 `-0.995` 复查，发现 2 组近乎重合且法线相反的三角面，共 2 个朝内重复面待删除；这类小间距反向面会在渲染深度测试中产生 z-fighting。此前的 `1e-6` 精确位置扫描无法捕获它们。

先使用 `apps/scripts/blender_cleanup_reversed_faces.py` 删除这 2 个朝内重复面，再使用 `apps/scripts/blender_repair_fbx_tangents.py` 重新写入切线。最终输出为：

`D:\Workspace\Star_workspace\B040\SEOULSOUL_2026__155_Jeans_lod0_fbx\SEOULSOUL_2026__155_Jeans_model01_lod0_4EFDA4DF2E0D40DB.fixed.fbx`

最终验证结果：

- 网格从 10,220 个三角面减少为 10,218 个，保留 6,071 个顶点、30,654 个面角和 2 套 UV。
- 输出包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 30,654 个向量，`invalid_count=0`。
- 以相同容差复查后，近重合反向面为 0 组；独立复核无零面积几何面，法线长度范围约为 `0.99999996` 至 `1.00000005`。
- 最终文件 SHA-256：`EACE037AE0DB2ECC625602102D6F8529400EAA5C3652038F5CEA9C8506C9E766`。

如果最终副本仍出现闪烁，应优先确认游戏/Unity 实际加载的是 `*.fixed.fbx`，并检查材质 Alpha/Cutout、双面 shader 的 `VFACE` 处理以及是否还有其它身体/服装网格与它相交；本次已确认的两组近重合反向面已经清除。

## 2026-09-06 B051 裤脚黑色三角形案例

### 问题背景

`D:\Workspace\Star_workspace\B051\SEOULSOUL_2026__146_Shorts_lod0_fbx\SEOULSOUL_2026__146_Shorts_model01_lod0_37E0069F3E831243.fbx` 在裤脚位置出现截图所示的黑色三角形。原始 FBX 未覆盖，修复结果另存为同目录的 `*.tangent-repaired.fbx`。

### 根因

该 FBX 为 7400 二进制格式，包含 1,585 个顶点、2,335 个三角面、7,005 个面角点、2 套 UV 和 1 个材质，但没有显式 `LayerElementTangent`/`LayerElementBinormal`。两套 UV 分别检测到 384 和 552 个零面积三角形；这会使游戏或导入器自行重建切线时，裤脚局部的切线空间不稳定，从而在光照下显示为黑色三角形。

法线方向扫描未发现冲突面（0 个），以位置容差 `0.001`、法线点积阈值 `-0.995` 扫描也未发现近重合反向面（0 组）。因此本案例不是面绕序、z-fighting 或透明贴图孔洞导致。

### 解决方案

使用 `apps/scripts/blender_repair_fbx_tangents.py` 导入源 FBX，按 `UVChannel_1` 和 `UVChannel_2` 通过 Blender MikkTSpace 写入显式 tangent/binormal。修复不翻转面、不删除面、不重建 UV，不修改材质、骨架、权重或顶点组。输出文件为：

`D:\Workspace\Star_workspace\B051\SEOULSOUL_2026__146_Shorts_lod0_fbx\SEOULSOUL_2026__146_Shorts_model01_lod0_37E0069F3E831243.tangent-repaired.fbx`

### 验证结果

- 源文件 SHA-256：`c68ab2415f556ea86aaaca1103401fcf6fceb52ae4558128215edf2e898659b6`。
- 修复文件 SHA-256：`ee27aacf5bf1d297e2257bba90242eef9c1feaa11795c97efe2eeb1424ee16ba`。
- 输出仍为 FBX 7400，包含 2 个 `LayerElementTangent` 和 2 个 `LayerElementBinormal`，每层 7,005 个向量，`invalid_count=0`。
- Blender 重新导入验证通过；网格仍为 1,585 个顶点、2,335 个三角面、7,005 个面角点和 2 套 UV。
- 源文件未覆盖；UV 零面积面仍保留，以避免改变原有贴图映射。

### 适用边界

该修复针对本文件确认的“缺失显式切线 + 退化 UV”光照伪影。导入 Unity/SB3Utility 时应选择使用 FBX 自带 Normals/Tangents，并确认实际绑定的是 `*.tangent-repaired.fbx`。如果黑三角仍存在，应使用纯白无贴图材质复测，再检查导入器是否丢弃切线、shader 的 UV 通道、Alpha/Cutout 和双面 `VFACE` 处理。

### 后续复核：自定义法线重建

用户随后反馈裤脚局部仍有疑似法向异常。对现存的 `*.tangent-repaired.fbx` 进行邻接面法线一致性扫描，未发现反向三角面（0 个候选）；原有的自定义法线方向冲突扫描也为 0 个。为清除可能由导入器保留的错误自定义分割法线，使用 `apps/scripts/blender_repair_fbx_normals.py` 清除旧的 split normals 并重新导出：

`D:\Workspace\Star_workspace\B051\SEOULSOUL_2026__146_Shorts_lod0_fbx\SEOULSOUL_2026__146_Shorts_model01_lod0_37E0069F3E831243.normals-repaired.fbx`

该副本基于已存在的 `*.tangent-repaired.fbx` 生成，不覆盖现有文件。验证结果：FBX 仍为 7400，网格仍为 1,585 个顶点、2,335 个三角面、7,005 个面角点和 2 套 UV；2 个 tangent 层和 2 个 binormal 层均保留，每层 7,005 个向量且 `invalid_count=0`。修复文件 SHA-256 为 `6a79fbed97126163886cfc0338fb3826ca3df405cd18f56699c96c59ed5688d4`。

### 再次复核：Face Orientation 反向面

用户反馈在 Blender 的 Face Orientation 视图中，裤脚区域仍显示红色三角面。此前的法线扫描无法识别“整个断开小面片一起反向”的情况，因为该面片内部的自定义法线仍与其自身几何法线一致。进一步使用 Blender `Recalculate Outside` 对网格连通面片重建外侧方向，发现并翻转 49 个面，其中包含裤脚区域的反向面（面索引 58、193、210、377、440、441、1238、1370、1549、1611、1612）。

随后重新计算两套 UV 的 MikkTSpace tangent/binormal，最终输出为：

`D:\Workspace\Star_workspace\B051\SEOULSOUL_2026__146_Shorts_lod0_fbx\SEOULSOUL_2026__146_Shorts_model01_lod0_37E0069F3E831243.outside-tangent-repaired.fbx`

最终副本 SHA-256 为 `6e1c3af3b273569706729d32d5095200c89166f2ef8e4537608177e8ad6602ee`。验证通过：FBX 仍为 7400，网格仍为 1,585 个顶点、2,335 个三角面、7,005 个面角点和 2 套 UV；两套 tangent/binormal 各 7,005 个向量，`invalid_count=0`。后续导入或查看时应使用此 `outside-tangent-repaired.fbx`，不要继续使用只清除自定义法线的旧副本。
