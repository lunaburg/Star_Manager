# 模组与资源文档索引

这里集中维护 zipmod、模组物品、角色卡依赖和 Unity3D 资源诊断相关的后端数据规则。页面布局请先看[前端 UI 专题索引](../frontend-ui/README.md)；HTTP 路由和任务 payload 只以[前后端接口](../backend-interface.md)为准。

- 上级索引：[文档总索引](../README.md)
- 开发总览：[项目总览](../project-overview.md)
- 缓存边界：[缓存与运行时文件登记](../runtime-cache-registry.md)

## 阅读路径

### 1. 先了解数据库和文件结构

| 文档 | 解决的问题 |
| --- | --- |
| [模组数据库设计](mod_database_design.md) | SQLite 表、字段、关系、扫描流程、状态和查询边界 |
| [模组数据库建库性能基准](mod_database_build_benchmark.md) | 现有数据库 100 个 zipmod 的建库耗时、ZIP 读取/解压与 Unity3D 缩略图阶段拆分和优化建议 |
| [游戏原版资源索引](builtin_resource_index.md) | `characustom/*.unity3d` 中的 ChaListData、原版物品表、缩略图和服装卡匹配 |
| [标准模组结构记录](standard_mod_structure_record.md) | `manifest.xml`、角色/Studio CSV（递归子目录、作者工具和日语原生表头兼容）、Unity3D 引用、缩略图来源和外部 `.zip` 归一化 |
| [Hooh ammunition_go.zipmod 结构解析](hooh_ammunition_go_zipmod_analysis.md) | 一个标准 Studio 自定义物品模组样本的目录、ItemCategory/ItemList、AssetBundle 对象和当前扫描边界 |
| [Studio 女性姿势转换](pose_zipmod_conversion.md) | Studio `.dat` 姿势到 `Kind=501` zipmod 的 CSV、Animator/AnimationClip、骨骼映射和验证边界 |
| [KK Animations ForMaker 注册补全](kk_animations_formaker_completion.md) | 完整 KK Animations 动画包与 ForMaker 姿势列表补丁的结构关系和全量注册结果 |

### 2. 再了解变更和异常

| 文档 | 解决的问题 |
| --- | --- |
| [数据库变动检测](mod_database_change_detection.md) | 新增、移除、修改、重复 GUID、manifest/物品建库线程数、stale 和依赖重连 |
| [模组异常分类](mod_exception_catalog.md) | 异常类型、触发条件、UI 标题和当前修复入口 |

### 3. 需要处理角色卡时阅读解析细节

| 文档 | 解决的问题 |
| --- | --- |
| [角色卡解析说明](character_card_parsing.md) | PNG 尾部、MessagePack、UniversalAutoResolver、类别映射和依赖记录 |
| [服装卡样本解析报告](clothes_card_sample_analysis.md) | AIS_Clothes 信封、Coordinate 部件、UAR 依赖和 KKEx 插件样本分析 |
| [Studio 场景卡解析说明](scene_card_parsing.md) | StudioNEOV2 场景数据、UAR 地图/物品/图案依赖、本地数据库匹配（含 Studio 物品）、远端补全和详情关联展示 |

## 按维护任务查找

| 维护任务 | 阅读顺序 |
| --- | --- |
| 修改全量/增量建库 | [模组数据库设计](mod_database_design.md) → [数据库变动检测](mod_database_change_detection.md) |
| 将 Studio 女性姿势转换为 zipmod | [Studio 女性姿势转换](pose_zipmod_conversion.md) → [标准模组结构记录](standard_mod_structure_record.md) |
| 补全 KK Animations 的 ForMaker 注册 | [KK Animations ForMaker 注册补全](kk_animations_formaker_completion.md) → [标准模组结构记录](standard_mod_structure_record.md) |
| 修改 zipmod 或 item 状态 | [标准模组结构记录](standard_mod_structure_record.md) → [模组数据库设计](mod_database_design.md) → [模组异常分类](mod_exception_catalog.md) |
| 解析 Studio 自定义物品模组 | [标准模组结构记录](standard_mod_structure_record.md) → [Hooh ammunition_go.zipmod 结构解析](hooh_ammunition_go_zipmod_analysis.md) |
| 修改重复 GUID 处理 | [模组数据库设计](mod_database_design.md) → [数据库变动检测](mod_database_change_detection.md) → [模组异常分类](mod_exception_catalog.md) |
| 修改角色卡依赖解析 | [角色卡解析说明](character_card_parsing.md) → [模组数据库设计](mod_database_design.md) |
| 修改角色卡页面关联展示 | [角色卡解析说明](character_card_parsing.md) → [前端 UI 专题索引](../frontend-ui/README.md) |
| 修改场景卡解析或关联展示 | [Studio 场景卡解析说明](scene_card_parsing.md) → [角色卡库布局](../frontend-ui/character-cards-layout.md) → [前端 UI 专题索引](../frontend-ui/README.md) |
| 修改原版物品扫描或服装卡原版关联 | [游戏原版资源索引](builtin_resource_index.md) → [服装卡样本解析报告](clothes_card_sample_analysis.md) → [角色卡库布局](../frontend-ui/character-cards-layout.md) |
| 修改缩略图或 Unity3D 修复 | [标准模组结构记录](standard_mod_structure_record.md) → [模组异常分类](mod_exception_catalog.md) → [Unity3D 解密与修复](../unity3d-decryption-notes.md)（含未知加密方式按 GUID→作者查询未加密参考模组、57 字节包裹、内嵌资源流、`wenchenyinger` profile、B002 三张流式纹理内嵌和 `.resS` 移除） |
| 诊断 Sims 4 FBX 灰黑块或黑三角 | [FBX 灰黑块修复记录](../sims4-fbx-gray-black-artifact-repair.md) → [Unity3D 解密与修复](../unity3d-decryption-notes.md) |
| 修改 API 或批量任务 | [前后端接口](../backend-interface.md) → 本目录对应数据文档 |

## 数据关系速览

```text
游戏目录 / zipmod / CSV / 角色卡 PNG
  -> 扫描与解析
  -> SQLite 本地索引
  -> 模组、物品、角色卡依赖和诊断
  -> 前端列表、详情、预览和维护任务
```

文件系统和原始资源仍是事实来源；SQLite、缩略图、卡片预览和模型预览属于可重建的运行时索引或缓存。修改缓存路径、失效条件或清理行为时，还要同步查看[缓存与运行时文件登记](../runtime-cache-registry.md)。

## 相关专题

- [前端 UI 专题索引](../frontend-ui/README.md)
- [前后端接口](../backend-interface.md)
- [Card metadata 插件](../card-metadata-plugin.md)
- [游戏物品运行时探针](../game-item-probe.md)
- [独立人物卡读取审计探针](../character-card-read-probe.md)
- [SB3UtilityScript](../sb3utility-script.md)
- [Unity3D 解密与修复](../unity3d-decryption-notes.md)
- [项目内 Unity3D 解密 skill](../../skills/mod-unity3d-decryption/SKILL.md)
