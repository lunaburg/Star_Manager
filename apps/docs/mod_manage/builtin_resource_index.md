# 游戏原版资源索引

## 背景

服装卡和人物卡中的原版服装、配饰通常没有 `UniversalAutoResolver` 的 `ModID`。因此只读取 UAR 依赖会把“卡片没有模组依赖”误判成“卡片没有服装物品”。原版物品必须从当前选定的 HS2 游戏目录中单独建立索引。

## 实际资源格式

原版列表位于：

```text
游戏目录/abdata/list/characustom/*.unity3d
```

这些文件不是直接存在的 CSV，而是 Unity3D 包中的 `TextAsset`。`TextAsset.m_Script` 保存的是 `ChaListData` MessagePack，结构包含：

```text
mark
categoryNo
filePath
lstKey
dictList
```

`lstKey` 提供字段名，`dictList` 提供物品行。物品行中可读取 `ID`、各语言名称、`MainAB`、`MainData`、`ThumbAB` 和 `ThumbTex`。UnityPy 读取这类二进制 TextAsset 时可能将非 UTF-8 字节映射为 surrogate，扫描器需要用 `surrogateescape` 恢复原始 MessagePack 字节后再解析。

## 索引表

主数据库中的 `builtin_items` 保存当前游戏目录的原版资源：

```text
game_dir_key + category_no + item_id  唯一定位
```

索引同时保存：

- 原版名称和可用的中英文名称字段；
- 原始列表包、TextAsset 路径；
- 模型资源 `MainAB` / `MainData`；
- 缩略图资源 `ThumbAB` / `ThumbTex`；
- 缩略图缓存路径、资源状态和解析器版本；
- 列表包、模型包和缩略图包的文件签名。

索引随现有“重建模组数据库”任务刷新。原版列表扫描失败时保留旧记录，避免单个损坏 Unity3D 包造成整套原版索引消失。

## 服装卡和人物卡匹配

两种卡片的 `Coordinate` 区块都包含同样的服装部件和配饰部件结构。服装卡详情和人物卡详情读取 `Coordinate` 后，使用同一个解析器按 `CategoryNo + ID` 查询 `builtin_items`。

Coordinate 中的服装部件使用以下映射：

| Coordinate 部位 | CategoryNo |
| --- | ---: |
| `ClothesTop` | 240 |
| `ClothesBot` | 241 |
| `ClothesBra` | 242 |
| `ClothesShorts` | 243 |
| `ClothesGloves` | 244 |
| `ClothesPanst` | 245 |
| `ClothesSocks` | 246 |
| `ClothesShoes` | 247 |

配饰使用 Coordinate 中的 `type` 作为 `CategoryNo`，支持 `351`–`363`。匹配键始终是：

```text
CategoryNo + Coordinate ID
```

`id=0` 作为空槽位跳过。只有索引中实际存在的原版记录才会加入关联结果，因此带有大数模组 ID 的部件不会被误显示成原版物品。如果同一服装部位已经存在 UAR 模组记录，则以 UAR 为准，跳过该部位的 Coordinate 原版候选，避免同一张卡出现两个“上衣”或其他重复部位。

原版关联记录使用 `source_type=builtin`，前端显示“游戏本体”。原版物品不参与模组缺失下载流程；人物卡详情写回依赖缓存时会排除这些原版记录，避免下次被当成缺失模组。物品浏览可通过 `source=all` 与当前游戏目录筛选原版记录，但它们仍不属于 zipmod 物品，详情页只提供基本信息，不提供模组工具。

## 缩略图

缩略图从 `ThumbAB` / `ThumbTex` 指向的原版 Unity3D 包中提取，写入 Star Manager 运行时缩略图目录，不修改游戏本体。若专用缩略图包不存在，扫描器会尝试使用 `MainAB`；仍无法提取时保留物品索引并标记缩略图缺失。

装配模式读取当前角色状态时，后端使用所选游戏目录、`CategoryNo` 和游戏侧 `localSlot` 查询 `builtin_items`，将已建立的原版缩略图缓存 URL 补充到装配栏位。模组物品仍使用 UAR 的 GUID/CSV slot 匹配；切换游戏目录后必须使用对应目录重新建库，才能得到原版缩略图。

## 验证结果

使用 `E:\game\HoneySelect 2 DX - TSYMQ` 实际游戏目录验证：

- 扫描 `33` 个 `characustom/*.unity3d` 列表包；
- 建立 `1,676` 条原版物品记录；
- `1,514` 条成功提取缩略图；
- `162` 条保留索引但没有可用缩略图；
- `(240, 1)` 匹配原版上衣“ワンピース”；
- `(243, 1)` 匹配原版内裤“ノーマル”；
- 用户提供的 `00667` 服装卡最终得到这两条原版关联，UAR 为空不会再显示“暂无关联模组”。
- 人物卡 Coordinate 使用相同的 `CategoryNo + ID` 解析路径，原版服装和配饰会在人物卡详情的“关联”页签显示为“游戏本体”。

## 适用边界

- 索引以当前游戏安装目录和当前资源文件为准；切换游戏目录后必须重新建库。
- 不同游戏版本、DLC 或资源替换可能改变 `categoryNo`、ID、名称和资源路径，文件签名变化后会重新扫描。
- 原版列表存在记录不等于模型资源和缩略图一定完整，详情中仍需区分资源状态和缩略图状态。
- 原版物品可在模组管理的物品浏览中与模组物品混合浏览，也可通过来源筛选单独查看；点击原版记录不会跳转到 zipmod 物品浏览器，也不会触发模组工具。

### UAR 模组服装与原版服装重复记录（2026-08-22）

- 背景：人物卡关联页出现两个“上衣”，其中一条是 UAR 识别出的模组上衣，另一条来自 Coordinate 的原版索引匹配；人物模型实际只穿着一件上衣。
- 根因：详情接口先解析 UAR 依赖，随后无条件把 Coordinate 命中的原版记录追加到结果，没有判断该服装部位是否已被模组记录占用。
- 方案：原版匹配接收已解析的 UAR 记录；服装部位按 `CategoryNo` 占用，配饰按 `CategoryNo + accessory slot property` 占用。已被 UAR 覆盖的部位不再追加原版记录，未被覆盖的原版部件继续显示。
- 验证：人物卡、服装卡和原版索引专项测试通过；前端仍使用同一套“游戏本体”展示和远程补全过滤逻辑。
- 适用边界：该规则只处理同一逻辑部位的重复候选，不会删除其他未被 UAR 覆盖的原版内衣、内裤、袜子、鞋子或配饰。

### 物品浏览支持游戏本体记录（2026-08-28）

- 背景：`builtin_items` 已随模组数据库建立，但物品浏览原先只查询 `mod_items`，用户无法按缩略图和类别浏览游戏原版物品。
- 根因：列表接口没有统一来源查询契约，且原版记录没有 zipmod ID，直接复用模组详情工具会产生错误操作入口。
- 方案：`GET /mods/items` 新增 `source=mod|builtin|all` 和 `game_dir` 参数；物品浏览默认请求 `all`，只合并当前选定游戏目录的 `builtin_items`，并显示来源筛选和“本体”标识。原版详情只显示名称、分类、ID、原版列表、模型资源和资源状态，隐藏工具页签与模组写回操作。
- 验证：原版/模组物品查询专项单元测试通过，既有物品查询测试通过，`npm run build` 通过。
- 适用边界：原版记录的“已使用/未使用”筛选暂不纳入，因为卡片依赖缓存会排除原版记录；切换游戏目录后需重新建库，缩略图缺失时仍只保留索引并显示缺失状态。

### 原版物品浏览只显示已知 Kind（2026-08-28）

- 背景：`builtin_items` 还可能索引到当前 Kind 分类表未收录的游戏类别，例如 `504`；这些记录用于资源匹配，但不应出现在原版物品浏览中。
- 方案：原版 `/mods/items` 的 `builtin` 和 `all` 分支统一限制为前端 Kind 分类表中的数字类别；`/mods/items/filters` 的原版 Kind 和“游戏本体”来源选项也使用同一限制。模组物品查询仍保留未知 Kind。
- 验证：查询测试确认 `504` 不出现在原版列表、混合列表或 Kind 筛选项中，已知 `240` 继续显示。
- 适用边界：该规则只影响物品浏览展示，不删除 `builtin_items` 中的原始索引记录，也不影响角色卡 Coordinate/UAR 的原版资源匹配。
