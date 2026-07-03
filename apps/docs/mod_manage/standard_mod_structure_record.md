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

`characustom` 下的 CSV 可能直接放在该目录，也可能继续按分类编号分层。读取时应递归扫描 `abdata/list/**/*.csv`。

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
| `MainTex` | 主贴图或基础贴图引用。 |
| `ColorMaskTex` | 颜色遮罩贴图引用。 |
| `ThumbAB` | 缩略图所在路径，可以是 `.unity3d` 资源包，也可以是未打包图片目录或图片文件。 |
| `ThumbTex` | 缩略图资源名、资源键，或未打包图片文件名。 |

## 资源引用关系

CSV 不直接保存模型或图片内容，而是通过路径和资源名引用实际文件。

- `MainAB` + `MainData` 指向主要模型、服装或配件资源。
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
