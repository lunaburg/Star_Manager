# 人物卡服装依赖重复清理

## 功能

总览页“实用工具”中的“人物卡清理”读取人物卡数据库，按服装依赖查找重复或高度相似的人物卡。服装依赖默认包含上衣、下装、内衣、手套、裤袜、袜子和鞋子对应的 `category_no`；配饰可以在分析面板中手动加入。

## 重复度

每张卡先归一化为依赖集合。已匹配物品使用 `zipmod_guid + category_no + item_id`，未匹配物品使用 `mod_id + category_no + slot/local_slot`。同一张卡中的重复记录只保留一次，数字 ID 去除前导零。

两张卡使用：

```text
Jaccard = 交集 / 并集
覆盖率 = 交集 / 两张卡中较小集合
重复度 = 0.7 × Jaccard + 0.3 × 覆盖率
```

默认阈值为 85%，最少服装依赖数为 3，最少共同服装数为 3。完全相同的依赖集合归为“完全重复”组；其他达到阈值的组合归为“高度重复”。

## 清理边界

完全重复组按照收藏、评分、缺失依赖、修改时间和路径顺序给出建议保留项，其他卡片预选为清理对象。高度重复组合不自动预选。用户确认后调用现有 `bulk_delete_character_cards` 任务，卡片进入人物卡回收站，数据库记录和预览缓存同步移除。

分析结果会在清理前重新请求；删除任务仍通过既有路径校验和回收站保护执行。人物卡内容可能不同但共享服装时，只会列出相似度，不会自动删除。

结果卡显示人物卡原始 PNG 的可见封面，使用标准人物卡图片接口和 `LazyThumbnail` 懒加载。

## 接口

```text
GET /library/cards/duplicate-clothing
  game_dir
  threshold       0..1
  min_dependency_count
  min_shared_count
  include_accessories=0|1
```

该接口只读 `character_cards`、`character_card_dependencies` 和 `mod_items`，不重新解析 PNG。没有人物卡数据库时返回 `needs_database=true`，前端提示先重建数据库。

## 验证

- `python -m compileall -q backend/star_manager backend/app`
- `npm run build`
