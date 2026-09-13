# Studio 女性姿势 `.dat` 转换为 zipmod

## 背景

HS2 Studio 保存的姿势文件位于 `UserData/Studio/pose`，扩展名为 `.dat`。这类文件不是可直接放入 `mods` 目录的 zipmod：它保存的是 Studio 姿势编辑器的 FK/IK 数据，而 zipmod 的“女姿势”列表通过 `Kind=501` 的 `characustom` CSV 项，去引用一个带有女性 AnimatorController 和 AnimationClip 的 Unity3D 资源。

本专题记录将单个女性 Studio 姿势转换为可被列表扫描的静态姿势 zipmod 的实现与限制。

## 根因与格式关系

- `.dat` 的标记为 `【pose】`，其中 `sex=1` 表示女性姿势；文件可以同时包含 FK、IK 和表情开关数据。
- 参考女性姿势资源使用 `AnimatorController=edit_F`，CSV 的 `Clip=mannequin` 对应状态名；该状态实际使用名为 `f_manekin` 的静态 `AnimationClip`。
- `f_manekin` 的 Transform 绑定按位置、旋转、缩放三组排列，共 352 个绑定；常量数组布局为 `352×3 + 352×4 + 352×3 + 7 = 3527` 个数值。
- AnimationClip 的绑定使用路径 CRC32。必须用目标女性骨架的完整 Transform 路径匹配 `.dat` 中前 52 个有效女性 FK 骨骼，不能只按骨骼名写入。

## 转换方案

脚本：[`apps/scripts/build_female_pose_zipmod.py`](../../scripts/build_female_pose_zipmod.py)

脚本会：

1. 解析 `.dat` 并确认它是启用 FK 的女性姿势；
2. 从现有女性静态姿势资源复制 `edit_F` / `mannequin` / `f_manekin` 模板；
3. 按目标女性骨架的路径映射 FK `0–51`；
4. 用 Unity `Quaternion.Euler` 的 Z-X-Y 顺序将 `.dat` 欧拉角转换为四元数；
5. 写入旋转、缩放和根骨位置，并同步 `m_ValueArrayDelta`；
6. 写出 `manifest.xml`、`Kind=501` CSV 和 Unity3D 资源。

生成的最小结构为：

```text
manifest.xml
abdata/list/characustom/00/custom_pose_f_<name>.csv
abdata/custom/<name>/anim_f_00.unity3d
abdata/custom/<name>/ik_f_00.unity3d
```

CSV 的关键字段是：

```text
Kind=1
MainManifest=abdata
MainData=edit_F
Clip=mannequin
IKAB=custom/<name>/ik_f_00
IKData=edit_F
```

这里 CSV 文件头部的 `501` 才是 Studio 姿势类型；行内的 `Kind=1` 与现有女性姿势资源保持一致。

## 本次产物与验证

输入姿势：`LD 33 CuteyNip.dat`

输出：[`apps/runtime/exports/LD_33_CuteyNip_ForMaker.zipmod`](../../runtime/exports/LD_33_CuteyNip_ForMaker.zipmod)

报告：[`LD_33_CuteyNip_ForMaker.zipmod.report.json`](../../runtime/exports/LD_33_CuteyNip_ForMaker.zipmod.report.json)

如果需要把姿势直接合并到已有的 ForMaker 包中，可使用[`apps/scripts/merge_ld33_into_kk_formaker_zipmod.py`](../../scripts/merge_ld33_into_kk_formaker_zipmod.py)。本次合并产物为 `KK_Animations_Free_Sample_ForMaker_Complete_LD33.zipmod`：它在原包的 `custom_pose_f_complete.csv` 中追加一行，并将 `abdata/custom/LD_33_CuteyNip/anim_f_00.unity3d` 放入同一个压缩包；CSV 的 `IKAB` 继续指向原包已有的 `custom/KK_Animations_-_Free_Sample_ForMaker/ik_f_00`。

静态验证结果：

- 输入为女性姿势，包含 69 条 FK、13 条 IK 记录；
- 52 个有效女性 FK 骨骼映射成功；
- ZIP CRC 检查通过；
- 包内包含 `manifest.xml`、ForMaker 风格 CSV、`anim_f_00.unity3d` 和专用 `ik_f_00.unity3d`；
- UnityPy 可重新读取生成资源；
- `edit_F` 控制器、`mannequin` 状态和 `f_manekin` 动画存在；
- 常量数组和 `m_ValueArrayDelta` 均为 3527 个值。

## 适用边界

- 这是女性 Studio 姿势转换器；男性姿势、场景姿势或非标准骨架需要单独模板和映射。
- 当前写入的是 `.dat` 中可映射的 FK `0–51`。额外 IK 记录、表情开关及未映射的 17 条记录不会被完整重建；专用 `ik_f_00.unity3d` 是女性 IK 兼容模板，尚未写入 `.dat` 的 13 条 IK 数值。
- 静态检查不能替代游戏内验证。使用时将 zipmod 复制到 HS2 的 `mods` 目录，重建/刷新模组索引后，在 Studio 的“女姿势”列表中查找 `LD 33 CuteyNip`。
- 本次转换不会覆盖游戏目录中的原始 `.dat` 或 Unity3D 文件。
