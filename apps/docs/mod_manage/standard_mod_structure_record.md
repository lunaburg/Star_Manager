# 标准模组结构与缩略图提取

标准解包后的模组通常由清单文件、列表表格和实际资源组成。列表表格负责登记物品信息和资源引用，模型、材质、贴图、缩略图等实际内容则放在 `abdata` 下的资源目录中。

## 目录结构

```text
模组根目录/
|-- manifest.xml
`-- abdata/
    |-- list/
    |   `-- characustom/
    |       |-- 分类编号/
    |       |   `-- 列表文件.csv
    |       `-- 列表文件.csv
    `-- 作者或模组资源目录/
        |-- 主资源包.unity3d
        |-- 缩略图资源包.unity3d
        `-- 未打包缩略图.png
```

地图类 zipmod 可能不包含 `abdata/list/`。目前已识别的 kPlug 地图结构为：

```text
模组根目录/
|-- manifest.xml
`-- abdata/
    |-- studio/info/kPlug/Map_kPlug.csv
    `-- <地图资源目录>/data_scene_000.unity3d
```

`Map_kPlug.csv` 以 `MAPMOD` 作为标志行；每条有效注册记录依次包含地图槽位、内部名称、相对于 `abdata/` 的场景 `.unity3d` 路径、显示名称和根目录。数据库将其索引为只读的“地图 / 场景”条目，不把它误当作角色自定义 CSV。

游戏本体地图还会提供 `abdata/map/list/mapinfo/*.unity3d`。该路径下存在地图信息包时，表示地图可进入本体地图列表；如果它与 `Map_kPlug.csv` 同时存在，则识别为“地图 / 本体 + 工作室”。只有 `Map_kPlug.csv` 时识别为“地图 / 工作室”，只有 `mapinfo` 信息包时识别为“地图 / 游戏本体”。本体地图常额外携带场景缩略图和 `abdata/adv/eventcg/` 事件资源，但它们不是判定的必要条件。

当 `MapInfo.param` 中存在 `ThumbnailBundle_S` 与 `ThumbnailAsset_S` 时，索引会读取对应 Unity 贴图并缓存为地图缩略图；地图列表优先显示此缓存图，缺失时才显示地图占位图。

`characustom` 下的 CSV 可能直接放在该目录，也可能继续按分类编号分层。读取时应递归扫描 `abdata/list/**/*.csv`。

### Studio 自定义物品模组变体

Studio 自定义物品可以使用另一套列表目录，不应强行按角色服饰的 `characustom` CSV 解析：

```text
模组根目录/
|-- manifest.xml
`-- abdata/
    |-- <作者或模组资源目录>/*.unity3d
    `-- studio/info/<作者>/
        |-- ItemCategory_<分类>_<大类>.csv
        `-- ItemList_<列表>_<大类>_<分类>.csv
```

`ItemCategory_*.csv` 通常登记 Studio 分类 ID 和显示名称；`ItemList_*.csv` 通常使用 `BigCategory`、`MidCategory`、`Name`、`Manifest`、`Bundle`、`Object` 等字段，把每个 Studio 物品映射到 Unity3D AssetBundle 内的 prefab。它可能没有 `ThumbAB` / `ThumbTex`，因此资源包中的材质贴图不应被误当作列表缩略图。

当前 Star Manager 通过独立 Studio 适配器读取 `abdata/studio/info/<作者>/ItemGroup_*.csv`、`ItemCategory_*.csv` 和 `ItemList_*.csv`。适配器先汇总 Group，再按 `ItemCategory_<category>_<group>.csv` 建立 Group/Category 映射，最后读取 ItemList，并将 `Manifest + Bundle + Object` 写入物品资源字段。Studio 条目统一使用 `kind = __studio_item__` 与 `item_domain = studio`；`BigCategory + MidCategory` 仅回填 Group/Category 显示信息，不参与分类筛选。

Studio 条目不读取 `abdata/studio_thumbnails/`，不生成缩略图缓存，固定使用 `thumbnail_status = not_applicable`。因此 Studio 物品不会显示缩略图，也不会被归入缺失缩略图诊断。

已验证样本：[Hooh ammunition_go.zipmod 结构解析记录](hooh_ammunition_go_zipmod_analysis.md)。

## 外部导入的 `.zip` 归一化

“导入外部模组”任务除了扫描 `*.zipmod`，还会扫描 `*.zip`。对后者，后端先检查压缩包内部结构：

- 压缩包必须可读取；
- 根目录必须有合法的 `manifest.xml`，根元素为 `manifest`，且包含 `guid`；
- 压缩包内必须存在 `abdata/` 下的实际内容。

通过检查的 `.zip` 才会被当作 zipmod 参与复制、Unity3D 补入、数据库重建和重复 GUID 处理；复制到游戏 `mods/Imported/` 时，目标文件名会把后缀规范化为 `.zipmod`。外部目录中的原始 `.zip` 保留不变，这是导入任务的安全复制边界。没有 `manifest.xml`、没有 GUID、没有 `abdata` 内容或不是标准 ZIP 的文件会进入导入结果的无效列表，不会被复制。

该判定是外部导入的最小结构检查，不替代后续的 CSV 解析、Unity3D 引用检查和数据库完整性诊断。地图类模组仍可不含 `abdata/list/`，只要具备 manifest 和合法的 `abdata` 内容即可。

### 本次问题记录

- **背景与根因**：外部导入任务原先只枚举 `*.zipmod`，下载器或其他工具生成的同构 `*.zip` 因扩展名不同而完全没有进入检查和复制流程。
- **解决方案**：新增 ZIP 内部结构检查，并将通过检查的 `.zip` 纳入现有 manifest、Unity3D 补入、数据库重建和重复 GUID 流程；写入 `mods/Imported` 时仅规范化导入副本后缀，原文件保持不变。
- **验证结果**：新增外部导入回归测试覆盖有效/无效 ZIP、目标后缀和源文件保留；定向测试 8 项、模组资源测试 43 项、全量后端测试 181 项通过，前端生产构建通过。
- **适用边界**：只扫描外部目录下的 `.zip` / `.zipmod`；`.zip` 必须是根级 manifest、GUID 和 `abdata` 内容均满足要求的 ZIP。该检查不保证 CSV、Unity3D 或资源引用本身完整，后续数据库诊断仍负责这些问题。

## 文件说明

| 位置 | 作用 |
| --- | --- |
| `manifest.xml` | 模组清单，记录模组 ID、名称、版本、作者、描述等基础信息。 |
| `abdata/list/` | 游戏读取的列表数据目录，用 CSV 登记物品、分类和资源引用。 |
| `abdata/list/characustom/**/*.csv` | 角色自定义相关物品列表。 |
| `abdata/**/*.unity3d` | Unity AssetBundle，存放模型、材质、贴图、缩略图等资源。 |
| `abdata/**/*.png`、`abdata/**/*.jpg`、`abdata/**/*.tga` | 少数模组会直接放未打包图片，CSV 可直接引用这些文件。 |

## manifest.xml

```xml
<manifest schema-ver="1">
	<guid>模组唯一ID</guid>
	<name>模组名称</name>
	<version>版本号</version>
	<author>作者</author>
	<description>描述</description>
</manifest>
```

## CSV 列表文件

CSV 文件通常前几行为元信息，之后是字段表头和实际数据行。

```csv
元信息1,,,,,
元信息2,,,,,
元信息3,,,,,
ID,Kind,Possess,Name,MainManifest,MainAB,MainData,ThumbAB,ThumbTex
100001,0,1,物品名称,abdata,作者/主资源.unity3d,资源名,作者/缩略图资源.unity3d,thumb
```

部分作者工具导出的 CSV 使用 UTF-16 LE（带 BOM），并可能将类别编号和作者分别放在表头前的元信息行中，例如：

```csv
247
assetboye
ID,Kind,Possess,Name,...
298,0,1,[rz]Boots2,...
```

数据库构建会按 UTF-8、UTF-16 和常见旧编码自动选择能正确识别 CSV 表头的编码；前置元信息行不计入物品记录，第一行类别编号仍作为数据库 `kind`（此例为 `247`），数据行中的 `Kind` 列按游戏 CSV 语义保留为行内字段，不覆盖类别编号。

CSV 中每一条实际数据行表示一个物品。一个模组内可能包含多个 CSV 文件，一个 CSV 文件也可能包含多条实际数据行；统计模组内物品总数时，应递归读取该模组下所有列表 CSV，并将所有 CSV 的实际数据行数量相加。元信息行和字段表头行不计入物品总数。

常见字段含义：

| 字段 | 含义 |
| --- | --- |
| `ID` | 当前列表内的物品编号。 |
| `Kind` | 物品类型或分类。 |
| `Possess` | 是否拥有或是否默认可用。 |
| `Name` | 游戏内显示名称。 |
| `MainManifest` | 主资源所属清单，通常为 `abdata`。 |
| `MainAB` | 主资源包路径。 |
| `MainData` | 主资源包中的资源名或资源键。 |
| `TexAB` | 外部贴图资源包路径；部分发型模组通过它引用单独的 `.unity3d` 贴图包。 |
| `MainTex` | 主贴图或基础贴图引用。 |
| `ColorMaskTex` | 颜色遮罩贴图引用。 |
| `ThumbAB` | 缩略图所在路径，可以是 `.unity3d` 资源包，也可以是未打包图片目录或图片文件。 |
| `ThumbTex` | 缩略图资源名、资源键，或未打包图片文件名。 |

## 资源引用关系

CSV 不直接保存模型或图片内容，而是通过路径和资源名引用实际文件。

- `MainAB` + `MainData` 指向主要模型、服装或配件资源。
- `TexAB` 指向部分发型或材质使用的外部贴图 Unity3D 资源包。它用于兼容性和外部贴图提示：缺失时不单独判错；如果只存在于游戏目录且不在公共 `abdata/chara/00`–`60` 范围内，则作为可补入的外置资源警告。`MainAB` 也遵循同一公共目录豁免规则。
- `ThumbAB` + `ThumbTex` 指向物品缩略图。
- 各类 `Mask` 字段用于控制身体、内衣、裤袜等遮罩或覆盖关系。

路径通常相对于 `模组根目录/abdata/`。如果在当前模组根目录的 `abdata/` 下找不到对应资源，应继续到游戏目录下的 `abdata/` 中查找。CSV 中常使用 `/`，Windows 文件系统中读取时需要兼容 `/` 和 `\`。

## 缩略图来源

缩略图常见有两种形式。

### 1. 缩略图打包在 unity3d 中

CSV 示例：

```csv
ThumbAB,ThumbTex
chara/sjjpl/sjjpl_yz_top_213.unity3d,prev
```

含义：

```text
从 abdata/chara/sjjpl/sjjpl_yz_top_213.unity3d 中读取名为 prev 的缩略图资源。
```

注意：`ThumbTex` 不一定等于 AssetBundle 内部完整路径。实际容器路径可能是：

```text
assets/111sjjpl/124/prev.jpg
assets/作者/编号/prev.png
prev
prev.jpg
```

提取时不要依赖固定前缀。推荐匹配顺序：

1. 容器完整路径等于 `ThumbTex`。
2. 容器文件名等于 `ThumbTex`。
3. 容器文件名去扩展名后等于 `ThumbTex`。
4. `Texture2D` 或 `Sprite` 对象名等于 `ThumbTex`。

### 2. 缩略图是未打包图片文件

有些模组不会把缩略图放进 `.unity3d`，而是在 CSV 中直接引用 PNG/JPG/TGA 文件。

可能形式：

```csv
ThumbAB,ThumbTex
作者/缩略图目录,thumb.png
```

或：

```csv
ThumbAB,ThumbTex
作者/缩略图目录/thumb.png,
```

或：

```csv
ThumbAB,ThumbTex
作者/缩略图目录/thumb.png,thumb
```

处理规则：

- 如果 `ThumbAB` 指向图片文件，优先直接读取该图片。
- 如果 `ThumbAB` 指向目录，使用 `ThumbTex` 在该目录下查找同名图片。
- 如果 `ThumbTex` 没有扩展名，应尝试 `.png`、`.jpg`、`.jpeg`、`.tga` 等常见图片扩展名。
- 如果直接图片存在，直接复制或转换为缓存 PNG，不需要解析 Unity AssetBundle。
- 如果 `ThumbAB` 指向 `.unity3d`，再进入 AssetBundle 解析流程。

### Unity3D 缩略图的按目标解析

- **问题背景**：一个缩略图 Unity3D 包可能包含大量 `Texture2D` / `Sprite`。旧流程在加载包后对 `env.container` 中的所有对象以及所有纹理对象调用 `obj.read()`，即使当前物品只需要其中一张图，也会把整包图片逐张解码。
- **根因**：UnityPy 的 `obj.read()` 会执行对象解析和图像转换；对象路径和对象名称本身可以先作为索引使用，不需要提前读取图像。
- **解决方案**：现在加载包时只登记 container 路径和 `Texture2D` / `Sprite` 的 `peek_name()`；`ThumbTex` 匹配到目标对象后才调用 `obj.read()` 和 `.image`。同一个对象在当前包内的解码结果只保留一次，多个物品引用同一目标时复用该结果；找不到精确目标时仍按原有 `icon` / `thumb` / `preview` fallback 顺序尝试。
- **验证结果**：缩略图相关后端测试 51 项通过。当前真实模组样本中，Unity3D 包解析及目标图写出耗时的中位数约为 80ms；与旧版整包图像读取基准的中位数约 649ms 相比，约 8 倍加速。不同压缩格式、包大小和目标对象位置会造成明显差异。
- **适用边界**：该优化只减少不相关图片的对象读取和解码，不改变 UnityPy 对包头、SerializedFile、AssetBundle 容器元数据的加载成本；损坏包、特殊加密包、没有可读名称的对象仍沿用原有错误或 fallback 行为。官方参考：[UnityPy Object](https://github.com/K0lb3/UnityPy#object) 和 [Texture2D](https://github.com/K0lb3/UnityPy#texture2d)。

## 提取脚本

当前项目提供了测试用脚本：

```text
apps/scripts/extract_unity_thumbnail.py
```

基本用法：

```powershell
D:\desktop_app\anaconda\envs\mm_env\python.exe apps/scripts/extract_unity_thumbnail.py "D:\path\to\mod_root" --output-dir "D:\path\to\output"
```

脚本会递归扫描 `abdata/list/**/*.csv`，读取 `ThumbAB` 和 `ThumbTex`，从对应 `.unity3d` 中导出缩略图，并输出为 PNG。输出文件名包含 `ID`，避免同名物品互相覆盖。

后续集成到后端时，建议扩展为统一流程：

```text
扫描 CSV -> 读取 ThumbAB/ThumbTex -> 判断直接图片或 unity3d -> 导出/复制为缓存 PNG -> 前端显示缓存图
```

如果提取失败，前端应显示默认占位图，并在日志中记录失败的 CSV、`ThumbAB`、`ThumbTex` 和错误原因。
