# 服装卡样本解析报告

## 样本信息

本报告针对用户提供的附件 `codex-clipboard-a2d7e67d-f46a-4cd0-8def-dd22df7f9b22.png`。附件不是普通截图，而是保留了 HS2/AIS 服装卡尾部数据的原始 PNG。

| 项目 | 结果 |
| --- | --- |
| 文件类型 | PNG + AIS 服装卡附加数据 |
| PNG 可见图像尺寸 | `504 x 704` |
| 文件总大小 | `334,677` bytes |
| PNG 主体大小（含 IEND） | `318,508` bytes |
| IEND 后附加数据 | `16,169` bytes |
| SHA-256 | `a472f5da86ee597458808ed5ff5001fe11edfbcbd086da5d23ba219c678435f0` |
| 卡片标记 | `【AIS_Clothes】` |
| 卡片版本 | `0.0.0` |
| 卡片名称 | `12` |
| 信封版本 | `100` |

视觉上，这是一张女性角色穿着黑色/深色礼服、长裙、手部装饰和腿部/头部配饰的服装预览图。性别和服装风格判断来自预览与部件结构；服装卡信封本身不保存完整人物 `Parameter` 性别字段，因此不能仅凭服装卡二进制断言角色性别。

## 文件结构

样本在 PNG `IEND` 之后符合服装卡信封：

```text
UInt32 100
.NET string 【AIS_Clothes】
.NET string 0.0.0
UInt32 0
.NET string 12
UInt32 14388
Coordinate（14388 bytes）
.NET string KKEx
UInt32 3
UInt32 1729
KKEx MessagePack map（1729 bytes）
```

结构校验结果：

- Coordinate 总长度为 `14,388` bytes。
- Coordinate 由两个小端长度前缀 MessagePack 对象组成。
- 第一个对象为 8 个服装部件。
- 第二个对象为 20 个配饰槽位。
- KKEx 为完整 MessagePack map，扩展版本为 `3`。

## 服装部件

HS2 Coordinate 的 8 个服装部件按标准顺序解释如下。`0` 通常表示该槽位没有有效模组物品；`1` 是一个有效的原始槽位值，但本样本中没有对应的 UniversalAutoResolver 记录，因此不能直接判断其来源。

| 顺序 | 部位 | Coordinate ID | UAR ModID | Slot | CategoryNo | 结论 |
| ---: | --- | ---: | --- | ---: | ---: | --- |
| 0 | 上衣 `ClothesTop` | `100000062` | `Andy.heiqunbai1` | `50100151` | `240` | 已记录服装模组依赖 |
| 1 | 下装 `ClothesBot` | `100000063` | `Andy.heiqunbai2` | `50100152` | `241` | 已记录服装模组依赖 |
| 2 | 胸衣 `ClothesBra` | `0` | — | — | — | 未使用/无模组记录 |
| 3 | 短裤 `ClothesShorts` | `1` | — | — | — | 有槽位值，但未发现 UAR 依赖记录 |
| 4 | 手套 `ClothesGloves` | `100000064` | `Andy.heiqunbai3` | `50100153` | `244` | 已记录服装模组依赖 |
| 5 | 连裤袜 `ClothesPanst` | `0` | — | — | — | 未使用/无模组记录 |
| 6 | 袜子 `ClothesSocks` | `0` | — | — | — | 未使用/无模组记录 |
| 7 | 鞋子 `ClothesShoes` | `100000065` | `Andy.heiqunbai4` | `501001059` | `247` | 已记录服装模组依赖 |

服装对象大小为 `4,022` bytes。每个部件还包含颜色、图案布局、旋转、光泽、金属度和隐藏选项等材质/显示参数；本报告只列出部件 ID 和依赖定位字段，未逐项展开全部浮点颜色参数。

### 服装依赖结论

样本至少包含以下 4 个服装模组依赖：

```text
Andy.heiqunbai1  -> ClothesTop    -> CategoryNo 240
Andy.heiqunbai2  -> ClothesBot    -> CategoryNo 241
Andy.heiqunbai3  -> ClothesGloves -> CategoryNo 244
Andy.heiqunbai4  -> ClothesShoes  -> CategoryNo 247
```

这些记录中的 `ModID`、`Slot`、`LocalSlot` 和 `CategoryNo` 可以与本地 zipmod 数据库进行二次匹配。当前附件本身不包含 zipmod 文件内容，因此无法仅凭这张卡确认模组文件是否存在、作者、版本或具体 zipmod 文件名。

## 配饰部件

配饰对象大小为 `10,358` bytes，共有 `20` 个槽位。其中前 5 个槽位有实际配饰，后 15 个槽位为 `type=350、id=0` 的空槽。

| 配饰槽位 | 类型 | 类型含义 | ID | 父节点 | UAR ModID | Slot | CategoryNo |
| ---: | ---: | --- | ---: | --- | --- | ---: | ---: |
| 0 | `361` | 手部配饰 | `100000291` | `N_Arm_R` | `heiqunbai10` | `500100141` | `361` |
| 1 | `361` | 手部配饰 | `100000292` | `N_Arm_L` | `heiqunbai10` | `500100142` | `361` |
| 2 | `358` | 腰部配饰 | `100000293` | `N_Waist` | `heiqunbai10` | `500100146` | `358` |
| 3 | `362` | 腿部配饰 | `100000294` | `N_Leg_L` | `heiqunbai10` | `500100147` | `362` |
| 4 | `351` | 头部配饰 | `100000295` | `N_Head` | `heiqunbai10` | `500100148` | `351` |
| 5–19 | `350` | 空/通用槽位 | `0` | 空 | — | — | — |

配饰的 `addMove`、颜色、光泽、金属度、隐藏时机和物理摇摆开关也被成功解码。样本中已使用的配饰全部来自 `heiqunbai10`，但该 ModID 可能对应同一套模组中的多个物品，仍需通过数据库用 `CategoryNo + Slot + LocalSlot` 精确匹配。

## UniversalAutoResolver 依赖记录

KKEx 中的 `com.bepis.sideloader.universalautoresolver` 有 `9` 条记录：4 条服装记录和 5 条配饰记录。

| Property | ModID | Slot | LocalSlot | CategoryNo |
| --- | --- | ---: | ---: | ---: |
| `ChaFileClothes.ClothesTop` | `Andy.heiqunbai1` | `50100151` | `100000062` | `240` |
| `ChaFileClothes.ClothesBot` | `Andy.heiqunbai2` | `50100152` | `100000063` | `241` |
| `ChaFileClothes.ClothesGloves` | `Andy.heiqunbai3` | `50100153` | `100000064` | `244` |
| `ChaFileClothes.ClothesShoes` | `Andy.heiqunbai4` | `501001059` | `100000065` | `247` |
| `accessory0.ChaFileAccessory.PartsInfo.id` | `heiqunbai10` | `500100141` | `100000291` | `361` |
| `accessory1.ChaFileAccessory.PartsInfo.id` | `heiqunbai10` | `500100142` | `100000292` | `361` |
| `accessory2.ChaFileAccessory.PartsInfo.id` | `heiqunbai10` | `500100146` | `100000293` | `358` |
| `accessory3.ChaFileAccessory.PartsInfo.id` | `heiqunbai10` | `500100147` | `100000294` | `362` |
| `accessory4.ChaFileAccessory.PartsInfo.id` | `heiqunbai10` | `500100148` | `100000295` | `351` |

这 9 条记录是当前最可靠的外部资源依赖清单。服装卡没有人物卡的 `Parameter`、`Parameter2`、`GameInfo` 等人物身份区块，因此不能像人物卡一样解析姓名、性格、生日或人物卡收藏信息。

## KKEx 插件扩展

样本包含 6 组插件数据：

| 插件 ID | 解析结果 |
| --- | --- |
| `com.bepis.sideloader.universalautoresolver` | 9 条依赖记录，见上文 |
| `moreAccessories` | `additionalAccessories` XML 为 `<additionalAccessories version="1.2.2" />`，未发现额外配饰条目 |
| `KCOX` | 值为 `null`，没有可展开的有效数据 |
| `com.deathweasel.bepinex.materialeditor` | 纹理字典、Renderer、材质浮点/颜色/纹理/Shader 列表均为 `null`，未发现 MaterialEditor 覆盖项 |
| `mikke.BeaverAI` | `K_PANTIES=false`、`K_PANTYHOSE=false`、`K_BOTTOM=false` |
| `mikke.pushUpAI` | 启用 PushUp；`FIRMNESS=0.9`、`LIFT=0.6`、`PUSH_TOGETHER=0.65`、`SQUEEZE=0.6`、`CENTER_NIPPLES=1.0`；`FLATTEN_NIPPLES=true`；隐藏配饰和隐藏乳头均为 `false` |

`mikke.pushUpAI` 的 `TOP_*` 覆盖字段均为默认值或关闭状态；本报告按字段名记录其值，没有对插件内部数值含义做超出字段名的推断。

## 可视预览与二进制的对应关系

预览图中可以观察到：

- 深色上衣/礼服主体，对应 UAR 中的 `ClothesTop`。
- 深色裙装或下装主体，对应 `ClothesBot`。
- 手臂附近的装饰，对应两个 `type=361` 手部配饰。
- 腰部装饰，对应 `type=358` 腰部配饰。
- 左腿附近的装饰，对应 `type=362` 腿部配饰。
- 头部/发饰区域的装饰，对应 `type=351` 头部配饰。
- 鞋子存在对应的 `ClothesShoes` 记录；预览底部较暗，无法仅凭图片判断鞋类细节。

图片本身只能证明最终渲染外观，不能替代 `ModID`、Slot 和 LocalSlot 依赖字段。

## 验证结果

使用项目现有 `apps/backend/star_manager/core/coordinate_card.py` 的服装卡校验逻辑验证通过：

- 标记校验：通过，识别为 `【AIS_Clothes】`。
- 信封版本校验：通过，版本 `100`。
- Coordinate 校验：通过，服装 `8` 部件、配饰 `20` 槽位。
- KKEx 校验：通过，MessagePack map 完整消费，版本 `3`，长度 `1,729` bytes。
- PNG IEND 定位：通过，IEND 后存在合法附加卡片数据。

## 解析边界

- 未提供对应的 `mods/*.zipmod` 文件，因此无法解析模组 manifest、作者、版本、文件名或验证依赖是否已安装。
- `Slot` 与 `LocalSlot` 只在卡片中被记录；最终匹配应使用本地模组数据库的 GUID、CategoryNo、Slot 和 LocalSlot 联合查询。
- 服装卡不包含完整人物卡 `Parameter` 区块，不能从本卡获得人物姓名、性格、生日、声线或人物卡元数据。
- 插件扩展中的未知字段没有被修改或重编码；本报告只做读取和摘要，没有写回样本文件。

## 结论

这是一张结构完整、可被 HS2/AIS 识别的服装卡，卡片名称为 `12`。其核心内容是：

1. 4 个服装模组部件：上衣、下装、手套、鞋子。
2. 5 个配饰模组部件：双手、腰部、左腿、头部。
3. 15 个空配饰槽位。
4. 9 条 UniversalAutoResolver 外部依赖记录。
5. 6 组 KKEx 插件扩展，其中包括 `moreAccessories`、MaterialEditor、BeaverAI 和 pushUpAI 状态。

在 Star_Manager 中实现服装卡浏览时，可以直接将本报告中的 `【AIS_Clothes】` 标记、卡片名称、Coordinate 部件、UAR 依赖和 KKEx 插件摘要作为列表与详情页的字段来源；依赖是否匹配则需要在选择 HS2 游戏目录后连接本地 zipmod 数据库进行解析。
