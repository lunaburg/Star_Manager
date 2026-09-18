# Studio 场景卡解析说明

本文记录 Star_Manager 对 HS2 Studio 场景卡 PNG 的读取边界、场景依赖提取和详情页展示规则。场景卡仍以 `UserData/studio/scene` 下的 PNG 文件为资源单位；列表阶段只读取文件和预览信息，完整解析仅在用户打开单张卡片详情时执行。

## 文件结构

Studio 场景卡是可见 PNG 与 `IEND` 后附加数据的组合。附加数据通常包含：

```text
PNG 图像
└── IEND
    └── Studio 场景数据
        ├── 【StudioNEOV2】场景标记
        ├── 场景对象与参数
        └── KKEx 插件块
```

场景级 `KKEx` 块使用小端版本号和 payload 长度包裹 MessagePack。`com.bepis.sideloader.universalautoresolver` 在场景卡中不是人物卡/服装卡的 `info` 数组，而是使用以下场景专用字段：

- `mapInfoGUID`：场景地图模组 GUID；
- `itemInfo`：场景物品记录列表。记录可能直接是字典，也可能是嵌套的 MessagePack bytes，包含 `ModID`、`Slot`、`LocalSlot`、`Category`/`CategoryNo` 等字段；
- `patternInfo`：场景图案记录列表。每条记录的 `ObjectPatternInfo` 字典包含图案 GUID、Slot 和 LocalSlot；图案记录继承外层的场景对象定位字段。

解析器会把它们分别规范化为 `DependencyType=scene`、`scene_item` 和 `scene_pattern`，并按依赖类型、GUID、Slot、LocalSlot 去重。这样同一物品在场景中多次摆放时不会重复显示，但同一模组的不同物品仍会保留。

## 当前解析结果

解析器位置：`apps/backend/star_manager/core/scene_card.py`。

当前提取字段包括：

- 场景标记 `【StudioNEOV2】`；
- 场景级 KKEx 数量；
- 场景卡保存的插件 ID；
- `mapInfoGUID` 作为 `DependencyType=scene` 的场景地图依赖；
- `itemInfo` 作为 `DependencyType=scene_item` 的场景物品依赖；
- `patternInfo.ObjectPatternInfo` 作为 `DependencyType=scene_pattern` 的场景图案依赖。

场景依赖随后复用 `card_library.resolve_dependency_records()` 与本地 zipmod 数据库匹配。场景地图通常没有 `mod_items` 物品行，因此“已匹配”表示地图 GUID 已找到 zipmod；不要求存在可点击的服装/物品 CSV 条目。场景物品和场景图案允许匹配 `item_domain=studio` 的 Studio 物品记录；人物卡和服装卡依赖仍排除 Studio 物品，避免跨资源域误匹配。

## 远端模组补全

场景卡详情中的未匹配依赖可以通过 `/library/scene/missing-mods` 查询只读远端索引。查询按场景依赖的 `ModID`（manifest GUID）归并，地图、物品和图案记录会保留在 `usages` 中，便于说明同一模组被哪些场景对象使用。结果分为“模组未安装 · 可补全”“模组未安装 不可补全”和特殊的“模组存在 / 物品缺失”状态，界面中两段文字分行居中显示。远端索引找到的是可下载的 zipmod manifest，不等于该 zipmod 一定包含场景所需的具体物品；如果本地已经有该 GUID 的 zipmod，只是缺少目标物品，即使远端有候选也不提供重复下载。模组已存在时，点击关联卡片会按 GUID 跳转到模组浏览器并选中对应模组。

场景卡关联页复用人物卡的远端候选、全部安装、单项安装、暂停、继续和取消交互。安装任务仍使用 `download_card_missing_mods`：文件先下载到临时 `.part`，通过大小、ZIP CRC 和 manifest GUID 校验后原子写入 `mods/Remote/`，再执行单 zipmod 索引。安装完成后重新读取场景详情，重新按地图 GUID 或物品/图案的 GUID + Slot/LocalSlot 判断是否补全。

## 前端行为

场景卡详情新增“详情 / 关联”页签。关联页显示：

- 场景依赖数量；
- 场景地图、场景物品和场景图案名称或 GUID；
- 来源 zipmod；
- 已匹配、物品未找到或模组未安装状态。

已匹配的场景地图可点击跳转到模组详情，并在关联页归入“其它”；已匹配的场景物品可点击跳转到物品详情，并归入“工作室物品”；已匹配的场景图案可点击跳转到物品详情，并归入“其它”；未匹配依赖按模组归并后统一进入“模组依赖缺失”。场景卡列表不会执行完整解析，也不写回或修改场景文件。

场景卡还有一条专用的展示归并规则：如果场景物品或图案没有在本地物品数据库中匹配到，则不按每条 Slot/LocalSlot 单独显示，而是按 `ModID` 合并成一个“模组”条目，并在来源信息中显示该模组下未匹配记录数量。已匹配的物品仍按具体物品名逐条显示；人物卡和服装卡不使用这条归并规则。

## 验证与边界

- `apps/backend/tests/test_scene_card.py` 覆盖场景级 UAR `mapInfoGUID`、嵌套 MessagePack `itemInfo` / `patternInfo` 和重复记录去重。
- `apps/backend/tests/test_scene_card_library.py` 覆盖详情接口返回解析结果和场景物品按 Slot/LocalSlot 匹配本地数据库物品。
- `apps/backend/tests/test_remote_mod_completion.py` 覆盖场景卡依赖按 GUID 查询远端候选、同一模组多条场景使用归并，以及本地已有 zipmod 但物品未索引的统计。
- 当前附件的 UAR 数据包含 34 条 `itemInfo`、2 条 `patternInfo`，去重后得到 18 条逻辑依赖；其中 `alex7997.patterns` 的 Slot 184 可以匹配本地物品记录。
- Studio 场景物品匹配回归覆盖 `[KKY] 4KSkyboxPack.zipmod` 的日语原生 CSV：场景 `Slot=2` 可匹配 Studio `item_id=2`；相同 GUID/Slot 不会被人物卡依赖路径匹配。
- 场景关联页对未匹配记录按 ModID 合并展示，避免同一模组的多个缺失物品重复占用条目；已匹配记录仍保留物品级展示。模组未安装时进一步区分可补全与不可补全；本地模组存在但物品缺失时使用特殊状态且不显示安装按钮。
- 嵌入场景的人物卡、服装或对象配置不自动合并为场景依赖；当前仅处理场景级 UAR 的地图、物品和图案记录。
- 如果 PNG 没有 `【StudioNEOV2】` 或场景级 KKEx，详情仍可正常显示文件信息，但关联页显示暂无关联模组；远端查询也会将其视为无效场景卡，不会凭文件名猜测模组。
- 远端候选按 manifest GUID 判断，无法保证远端 zipmod 中存在目标 `Slot`/`LocalSlot`；安装后仍以本地索引的精确匹配结果为准。远端索引文件缺失或没有有效 manifest 记录时，关联页显示不可补全。
