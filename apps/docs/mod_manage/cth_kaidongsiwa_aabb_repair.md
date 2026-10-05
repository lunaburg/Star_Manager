# `[cth]kaidongsiwa.zipmod` Unity3D AABB 修复记录

## 问题背景

输入文件为 `C:\Users\yukilat\Downloads\[cth]kaidongsiwa.zipmod`。ZIP 结构、CRC、`manifest.xml` 和角色服饰 CSV 均可正常解析：CSV 项目为 `ID=121388`、`Kind=245`，`MainAB=chara/[cth]kaidongsiwa.unity3d`，`MainData=[cth]kaidongsiwa`。

## 根因

UnityFS 资源可以由 UnityPy 读取，Unity 版本为 `2018.2.21f1`，对象数为 533。`SkinnedMeshRenderer` `PathID=4363` 的 `m_AABB` 不合法：

```text
m_Center = (0, 0.0011696788, 0.061416246)
m_Extent = (0.01671148, -0.013698563, 0.060281463)
```

其中 `m_Extent.y` 为负数，且整体范围与该渲染器引用的 `Mesh PathID=4364` 的 `m_LocalAABB` 不一致。这是一个资源缺陷，但不是游戏中完全没有模型的唯一原因。

游戏日志显示资源已经被 Sideloader 加载，随后出现：

```text
[Warning:Fix UpdateWet Exceptions] Found null renderers in the CmpHair or CmpClothes MBs.
NullReferenceException: AIChara.CmpBase.get_isVisible()
```

进一步对照正常的 `Kind=245` 裤装资源发现，`MonoBehaviour PathID=3229` 的槽位方向也写反了：CSV 的 `Kind=245` 是裤装，应使用 `objBotDef/objBotHalf`，而原资源把两个根对象写进了 `objTopDef/objTopHalf`。同时 `rendCheckVisible` 和 `rendNormal01` 各含 1 个有效 Renderer 与若干 `PathID=0` 空引用，正对应日志中的 null Renderer 警告。

## 修复方案

第一版旁置副本只修正了包围盒。根据游戏日志和正常裤装资源的结构对照，第二版旁置副本同时做以下三个确定性修复：

1. 将 `SkinnedMeshRenderer PathID=4363` 的 `m_AABB` 精确复制为同一资源内 `Mesh PathID=4364` 的 `m_LocalAABB`：

```text
m_Center = (0, 6.1416234970, -0.1169685125)
m_Extent = (1.6711479425, 6.0281453133, 1.3698554039)
```

未修改 CSV、清单、模型顶点/索引/骨骼、材质、贴图或其它对象。原始文件没有覆盖。

2. 将 `objTopDef/objTopHalf` 的原有根对象移动到 `objBotDef/objBotHalf`，并清空 top 槽位。
3. 从 `rendCheckVisible` 和 `rendNormal01` 中移除 `PathID=0` 空引用，只保留有效的 `SkinnedMeshRenderer PathID=4363`。

## 验证结果

第二版输出文件：`apps/tmp/cth_kaidongsiwa.repaired-v2.zipmod`

- ZIP CRC 检查通过，8 个目录项和原包顺序一致。
- UnityPy 可重新加载，UnityFS 对象数仍为 533。
- 修复后的渲染器 `m_AABB` 与 Mesh `m_LocalAABB` 完全一致，三个 extent 均为正数。
- 渲染器的 GameObject、Mesh、Bones、Materials、RootBone 等关键引用保持不变。
- Mesh 的子网格、绑定姿势、索引缓冲和顶点数据保持不变。
- 8 张 Texture2D 的名称、尺寸、格式保持不变。
- 1605 个本地 PPtr 引用均可解析，无悬空引用。
- `manifest.xml`、CSV 和 PNG 在修复包中保持原字节内容。
- 第二版的 top/bottom 槽位与正常 `Kind=245` 裤装资源一致，两个 Renderer 数组不再含空引用。

详细哈希与验证字段见 `apps/tmp/cth_kaidongsiwa.repair-report.json`。

## 适用边界

第二版保留 `GameObject A` 作为 `objBotHalf`，因为它是原资源已有的半脱变体根对象；AssetBundle 中两个同名 `zt1` 容器入口也未修改。最终是否在游戏内正常显示仍需移除第一版、安装第二版后重新加载角色验证。
