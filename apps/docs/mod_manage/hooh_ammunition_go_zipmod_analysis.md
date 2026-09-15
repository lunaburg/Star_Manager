# `[Hooh] ammunition_go.zipmod` 结构解析记录

本文档记录对用户提供的 `[Hooh] ammunition_go.zipmod` 的只读解析结果。它是一个标准的 Studio 自定义物品模组样本，不是角色服饰类 `characustom` 模组，也不是地图类 `kPlug` 模组。

## 样本与结论

| 项目 | 结果 |
| --- | --- |
| 原始文件 | `C:\Users\yukilat\Downloads\[Hooh] ammunition_go.zipmod` |
| 文件大小 | 25,745,390 bytes |
| SHA-256 | `665CD0C67CFCC75BAD778874B086929A6A4F8993F6A854EC22ACFFD8FA57B0E6` |
| ZIP 条目 | 9 个，其中 4 个文件、5 个目录条目 |
| 清单 | 根级 `manifest.xml`，XML 合法且 GUID 存在 |
| CSV | 1 个 Studio 分类表，1 个 Studio 物品表 |
| Unity3D | 1 个 UnityFS AssetBundle，25,740,709 bytes |
| 物品数 | 31 个，ID `0`–`30` |
| 缩略图 | 没有独立图片，也没有 `ThumbAB` / `ThumbTex` 字段 |
| 资源引用 | 31 条 `Bundle + Object` 引用全部闭合到同一个 Unity3D |

结论：该压缩包结构完整，属于“Studio 分类登记表 + Studio 物品登记表 + 单 UnityFS 资源包”的标准闭环。当前 Star Manager 的通用 CSV 扫描器不会读取它，不代表模组损坏，而是因为 Studio 表位于 `abdata/studio/info/`，不在当前扫描范围 `abdata/list/**/*.csv` 内。

## 压缩包目录

```text
[Hooh] ammunition_go.zipmod/
|-- manifest.xml
`-- abdata/
    |-- hooh/
    |   `-- modern_weapons_ammunition_000.unity3d
    `-- studio/
        `-- info/
            `-- hooh/
                |-- ItemCategory_0058_1095.csv
                `-- ItemList_0001_1095_0058.csv
```

压缩包内没有以下内容：

- `abdata/list/` 角色自定义列表目录；
- `ThumbAB` / `ThumbTex` 指向的独立缩略图包；
- PNG、JPG、TGA 等未打包图片；
- `TexAB`、外部 Unity3D 或其他外部文件。

## `manifest.xml`

文件使用 UTF-8 编码，根元素为 `manifest`，属性为 `schema-ver="1"`：

```xml
<manifest schema-ver="1">
    <guid>hooh.props.ammunition01</guid>
    <name>Ammunition</name>
    <version>1.0.0</version>
    <author>hooh</author>
    <description>hackeries</description>
</manifest>
```

解析字段：

| 字段 | 值 | 作用 |
| --- | --- | --- |
| `guid` | `hooh.props.ammunition01` | 模组稳定标识，作为数据库归属键 |
| `name` | `Ammunition` | 模组显示名 |
| `version` | `1.0.0` | 模组版本 |
| `author` | `hooh` | 作者 |
| `description` | `hackeries` | 描述 |

## Studio CSV 结构

### 分类表：`ItemCategory_0058_1095.csv`

```csv
ID,Name
58,Modern Weapons
```

该表把中类/自定义分类 ID `58` 注册为 `Modern Weapons`。文件名中的 `0058_1095` 与内容中的 `ID=58`、物品表中的 `MidCategory=58` 相互印证；`1095` 是该 Studio 列表使用的 `BigCategory`。

### 物品表：`ItemList_0001_1095_0058.csv`

该表有 32 行：1 行表头和 31 行物品数据，没有前置元信息行。表头为：

```text
ID, BigCategory, MidCategory, Name, Manifest, Bundle, Object, Child,
IsAnime, IsColor, 柄, IsColor2, 柄, IsColor3, 柄, 拡縮判定, Emission
```

字段含义按本样本确认如下：

| 字段 | 本样本值/形式 | 解析含义 |
| --- | --- | --- |
| `ID` | `0`–`30` | Studio 物品在该列表中的局部编号 |
| `BigCategory` | `1095` | Studio 大类编号 |
| `MidCategory` | `58` | 对应 `ItemCategory` 的分类编号 |
| `Name` | `Ammo 25mm` 等 | Studio 内显示名称 |
| `Manifest` | `abdata` | 资源引用根，表示后续 `Bundle` 相对 `abdata/` |
| `Bundle` | `hooh/modern_weapons_ammunition_000.unity3d` | Unity3D 资源包路径 |
| `Object` | `Ammo_25mm` 等 | 资源包内对应的 prefab/物品逻辑名 |
| `Child` | 空 | 子节点/子资源字段，本样本未使用 |
| `IsAnime` | 空 | 动画标记，本样本未使用 |
| `IsColor`、`IsColor2`、`IsColor3` | 空 | 颜色变体标记，本样本未使用 |
| `柄` | 空 | 纹理/图案相关字段，本样本未使用 |
| `拡縮判定` | 空 | 缩放判定字段，本样本未使用 |
| `Emission` | 空 | 发光字段，本样本未使用 |

表头中出现了 3 个同名的 `柄` 列。该样本中三列均为空，因此没有信息丢失；通用解析器不能把表头简单转换为普通字典，否则会发生同名列覆盖，若以后遇到非空值应保留列序号或使用重复列名规范化。

## 31 个物品登记

| ID | 显示名 | `Object` | 类型分组 |
| ---: | --- | --- | --- |
| 0 | Ammo 25mm | `Ammo_25mm` | Ammo |
| 1 | Ammo 40mm | `Ammo_40mm` | Ammo |
| 2 | Ammo 762X39mm | `Ammo_762X39mm` | Ammo |
| 3 | Ammo 9X19mm | `Ammo_9X19mm` | Ammo |
| 4 | Ammo ACP45 | `Ammo_ACP45` | Ammo |
| 5 | Ammo Caliber 50BMG | `Ammo_Caliber_50BMG` | Ammo |
| 6 | Ammo Creedmoor65 | `Ammo_Creedmoor65` | Ammo |
| 7 | Ammo FN57X28mm | `Ammo_FN57X28mm` | Ammo |
| 8 | Ammo Gauge20 | `Ammo_Gauge20` | Ammo |
| 9 | Ammo Gauge410 | `Ammo_Gauge410` | Ammo |
| 10 | Ammo Long Rifle22 | `Ammo_LongRifle22` | Ammo |
| 11 | Ammo Magnum357 | `Ammo_Magnum357` | Ammo |
| 12 | Ammo NATO556X45mm | `Ammo_NATO556X45mm` | Ammo |
| 13 | Ammo SW40 | `Ammo_SW40` | Ammo |
| 14 | Ammo Winchester300 | `Ammo_Winchester300` | Ammo |
| 15 | Ammo Winchester308 | `Ammo_Winchester308` | Ammo |
| 16 | Shell 40mm | `Shell_40mm` | Shell |
| 17 | Shell 762X39mm | `Shell_762X39mm` | Shell |
| 18 | Shell 9X19mm | `Shell_9X19mm` | Shell |
| 19 | Shell ACP45 | `Shell_ACP45` | Shell |
| 20 | Shell Caliber 50BMG | `Shell_Caliber_50BMG` | Shell |
| 21 | Shell Creedmoor65 | `Shell_Creedmoor65` | Shell |
| 22 | Shell FN57X28mm | `Shell_FN57X28mm` | Shell |
| 23 | Shell Gauge20 | `Shell_Gauge20` | Shell |
| 24 | Shell Gauge410 | `Shell_Gauge410` | Shell |
| 25 | Shell Long Rifle22 | `Shell_LongRifle22` | Shell |
| 26 | Shell Magnum357 | `Shell_Magnum357` | Shell |
| 27 | Shell NATO556X45mm | `Shell_NATO556X45mm` | Shell |
| 28 | Shell SW40 | `Shell_SW40` | Shell |
| 29 | Shell Winchester300 | `Shell_Winchester300` | Shell |
| 30 | Shell Winchester308 | `Shell_Winchester308` | Shell |

数量上是 16 个 Ammo 和 15 个 Shell。`Shell` 没有 `Shell_25mm` 条目，这是列表本身的内容，不是解析遗漏。

## Unity3D 资源包

### 容器信息

```text
路径:     abdata/hooh/modern_weapons_ammunition_000.unity3d
大小:     25,740,709 bytes
签名:     UnityFS
格式版本: 6
Unity:    2018.2.21f1
```

AssetStudio Helper 成功读取该包。所有 364 个对象来自一个 serialized file：`CAB-b2e8c90853409346b415b4e62fad9939`。

| Unity 对象类型 | 数量 |
| --- | ---: |
| `AssetBundle` | 1 |
| `GameObject` | 62 |
| `Transform` | 62 |
| `MeshFilter` | 31 |
| `MeshRenderer` | 31 |
| `Animator` | 31 |
| `Avatar` | 31 |
| `Mesh` | 31 |
| `Material` | 16 |
| `Texture2D` | 67 |
| `Shader` | 1 |
| **合计** | **364** |

AssetBundle 的容器表包含 31 个 prefab 路径，例如：

```text
assets/@studio_assets/ammunition_pack/output/ammo_25mm.prefab
assets/@studio_assets/ammunition_pack/output/shell_40mm.prefab
assets/@studio_assets/ammunition_pack/output/shell_winchester308.prefab
```

31 个 CSV `Object` 名称在大小写归一化后全部能找到对应的 prefab 容器。每个容器记录 1 个顶层 `GameObject`；其余 `Transform`、`MeshFilter`、`MeshRenderer`、`Animator`、`Avatar` 和网格/材质/贴图对象组成实际资源层。

命名规则也与物品表相互对应：

- 物品 `Ammo_25mm` 对应容器路径中的 `ammo_25mm.prefab`；
- 物品 `Shell_Caliber_50BMG` 对应 `shell_caliber_50bmg.prefab`；
- 网格名使用 `SM_CT_<口径>`，材质名使用 `M_CT_<口径>`；
- 贴图名使用 `T_CT_<口径>_<用途>`，本样本可见 `_A`、`_AO`、`_N`、`_R` 等后缀；
- 多数口径同时存在 Ammo/Shell 两个 prefab，所以同名网格在包内出现两次；`SM_CT_25mm` 是本样本中唯一只出现一次的网格名。

### 资源引用闭环

```text
manifest.xml
  guid = hooh.props.ammunition01
        |
        v
ItemCategory_0058_1095.csv
  ID 58 -> Modern Weapons
        |
        v
ItemList_0001_1095_0058.csv
  ID + BigCategory + MidCategory + Name
  Manifest=abdata
  Bundle=hooh/modern_weapons_ammunition_000.unity3d
  Object=Ammo_25mm / Shell_40mm / ...
        |
        v
abdata/hooh/modern_weapons_ammunition_000.unity3d
  31 prefab containers -> 31 个 Studio 物品
  prefab -> GameObject/Transform/Renderer/Mesh/Material/Texture
```

该包没有 `ThumbAB` / `ThumbTex`，所以不能按角色服饰模组的缩略图提取流程生成物品预览。资源包中虽然存在 67 个 `Texture2D`，但它们是模型材质贴图，不是 CSV 声明的列表缩略图。

## 与 Star Manager 当前扫描器的关系

### 可以直接识别的部分

当前实现可以识别该文件是可读取的 zipmod：

- 根级 `manifest.xml` 存在；
- 根元素为 `manifest`；
- `guid` 非空；
- 存在 `abdata/` 内容。

因此它不会触发缺少清单、无 GUID 或缺少 `abdata` 的压缩包结构错误。

### 当前不会索引的部分

`apps/backend/star_manager/services/mod_database_assets.py` 中的通用 ZIP CSV 迭代器当前只处理：

- `abdata/list/**/*.csv`；
- 特殊的 `abdata/studio/info/kPlug/Map_kPlug.csv`；
- 游戏地图 `mapinfo` Unity3D。

本样本的两个 CSV 位于 `abdata/studio/info/hooh/`，既不是 `Map_kPlug.csv`，也不属于 `abdata/list/`，所以当前数据库建库时会出现以下行为边界：

```text
manifest: 可识别
zipmod:   可作为合法文件保留
mod_items: 0 条（当前扫描范围不会读取 Studio ItemCategory/ItemList）
```

如果未来支持这类模组，应增加独立的 Studio ItemList 解析器，不应直接把它当作 `characustom` CSV：

1. 以 `ItemCategory` 解析 Studio 分类名称和分类 ID；
2. 以 `ItemList` 的 `BigCategory + MidCategory` 建立列表归属；
3. 将 `Manifest + Bundle` 归一化为 `abdata/` 下的资源包路径；
4. 将 `Object` 与 AssetBundle 容器中的 prefab 路径匹配；
5. 为没有 `ThumbAB` / `ThumbTex` 的 Studio 物品保留“无列表缩略图”状态；
6. 对重复表头（本样本的 `柄`）使用位置化字段，而不是普通字典覆盖。

这类物品的数据库 `kind` 不能从通用 `characustom` 规则中的首行类别编号直接推导。`1095` / `58` 是本样本的 Studio 分类字段，应在数据模型中作为 Studio 大类/中类保留，待更多 Studio 模组或游戏原始列表对照后再建立稳定的统一 Kind 映射。

## 验证方法与边界

本次只读验证包括：

1. ZIP 条目枚举、文件大小和 SHA-256 计算；
2. `manifest.xml` XML 解析与字段读取；
3. 两个 CSV 的编码、表头、数据行和字段关系检查；
4. UnityFS 签名和 Unity 版本头检查；
5. 使用项目内 `apps/tools/assetstudio-helper/bin/Release/net8.0/StarManager.AssetStudioHelper.exe` 列出 Unity serialized objects；
6. 31 条 CSV `Object` 与 AssetBundle 31 个 prefab container 的逐项归一化匹配。

验证未做以下事情：

- 未修改原始 `.zipmod`；
- 未把资源写入游戏目录；
- 未在游戏内实际加载 Studio 物品；
- 未将模型导出为 FBX/OBJ；
- 未确认每个模型在目标 HS2/AIS 安装环境中的插件或游戏版本兼容性。

因此本文能确认“压缩包结构完整、列表引用闭合、Unity 资源可被 AssetStudio 读取”，但不能单凭离线结构分析保证游戏内显示、物理碰撞、脚本联动或特定 Studio 插件行为。

## 维护记录

- **背景**：用户提供的标准 Studio 模组采用 `abdata/studio/info/<author>/ItemCategory_*.csv` 与 `ItemList_*.csv`，而不是角色服饰模组常见的 `abdata/list/characustom/**/*.csv`。
- **根因/边界**：当前 ZIP CSV 扫描器的范围没有覆盖一般 Studio `ItemCategory` / `ItemList`，因此合法模组会被识别为 zipmod，但不会产生物品索引。
- **本次处理**：新增本样本的结构解析文档，并在标准模组结构文档中补充 Studio 表结构、字段和解析边界；本次未改动扫描代码。
- **适用边界**：本文结论只适用于该文件的离线结构和当前代码边界；Studio 其他类别可能使用不同表头、附加字段、多个 Bundle、缩略图或插件专属格式，需逐包验证。
