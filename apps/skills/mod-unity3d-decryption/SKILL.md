---
name: mod-unity3d-decryption
description: Diagnose and recover protected HS2/Sakuraba Unity3D mod resources using the project's scripts and verified structural profiles. Use when a mod UnityFS file is unreadable, has damaged metadata or streamed textures, uses XT XOR protection, or needs static recovery validation; do not use as a generic decryption or key-extraction workflow.
metadata:
  short-description: Recover and validate protected Unity3D mod assets
---

# 模组 Unity3D 解密与修复

先阅读项目记录 [unity3d-decryption-notes.md](../../docs/unity3d-decryption-notes.md)。它是事实来源，包含已验证 profile、案例边界和验证结果。

## 工作原则

- 原文件永不覆盖；输出放在输入目录外，使用 `.decrypted.unity3d`、`.reconstructed.unity3d` 或 `.no-source-recovered.unity3d` 后缀。
- 先分类再处理：标准 UnityFS、XT 四字节标记、SerializedFile 偏移/元数据损坏、流式纹理/`.resS` 问题、已知无原件 profile、Bit/BepInEx 二次保护。
- 不按文件名、作者名或单个十六字节标记套用 profile。至少核对 Unity revision、节点数量/类型、元数据大小、数据偏移、对象边界和资源流布局。
- 每个结果保留 SHA-256、状态、修复层级、模板/profile 来源、对象数量和失败原因；不确定的字节必须显式记录，不能用猜测伪装成恢复。

## 推荐流程

1. 复制输入到隔离工作目录，计算输入哈希并检查文件头、UnityFS 声明大小和节点目录。
2. 如果判断为项目中尚未记录的加密方式，先寻找可作对照的未加密模组。优先通过本地 SQLite 模组数据库查找，而不是先递归扫描整个模组目录：
   - 先按目标 `guid` 精确匹配 `zipmods`（大小写不敏感），只考虑 `scan_status != 'stale'`、文件仍存在且能从 `file_path` 打开或解压的记录；必要时结合 `mod_items` 的 Unity3D 路径定位对应资源。
   - 对同一 GUID 的候选逐个检查实际字节和 UnityFS/SerializedFile 可读性，确认它确实是未加密或已知正常结构；数据库中的 `scan_status`、`unity3d_status` 只能用于缩小候选范围，不能单独证明未加密。
   - 同一 GUID 没有可用参考时，再按 manifest 的 `author` 在 `zipmods` 中查找未 stale 且文件存在的模组，并同样通过字节、Unity revision、TypeTree、节点布局和对象结构确认可比性。作者匹配应大小写不敏感并去除首尾空白；空作者、`Unknown author` 和内置资源不能作为作者参考。
   - 参考候选必须记录来源 zipmod 的 GUID、作者、路径、SHA-256、Unity revision、TypeTree/节点特征和选择理由。不能因为“同作者”就直接复制元数据；先用候选探索保护层、位移关系、密钥/明文关系或资源流布局，再为目标文件单独验证。
3. 若找到完全对应的正常原件，优先做逐资源对齐；否则使用参考模组探索出、且已被目标文件结构证据支持的修复方式；最后才评估已验证的无原件 profile。若 GUID 和作者两级都找不到可用参考，停止猜测并报告缺少对照样本。
4. 单文件或目录批处理使用 `apps/scripts/decrypt_unity3d.py`。它会递归扫描、匹配 Unity revision/TypeTree 模板、重建 UnityFS，并报告 `ok`、`skipped` 或 `error`。

```powershell
python apps/scripts/decrypt_unity3d.py `
  "E:\protected-assets" --output-dir "E:\recovered-assets" `
  --template-root "E:\game\abdata" --json
```

5. XT 文件（首四字节 `01 03 03 01`）使用 `apps/scripts/decrypt_xt_unity3d.py`。脚本从 UnityFS 已知明文恢复文件级 20 字节循环 XOR 密钥，不执行配套插件；输出后必须检查 UnityFS 头、版本、声明大小，并用 UnityPy 或 AssetStudio 读取对象表。

6. 只有同时符合 `sakuraba-26-3-s01-no-source` profile 时，才使用 `apps/scripts/recover_sakuraba_no_source.py`。该 profile 仅适用于 Unity `2018.4.11f1`、单 SerializedFile/单 `.resS`、确定的 16 字节位移关系；未知尾部默认零填充并写入报告，只有反向 Transform 引用唯一时才允许补回父 PathID。

## 验证门槛

静态验证至少包括：UnityPy/AssetStudio 能打开；SerializedFile 对象数大于零；Build Target、Unity revision、block/node 大小自洽；Texture2D 名称、尺寸、格式和数据可读；AssetBundle 容器和 CSV `MainAB`/`MainData` 引用一致；Transform 的 `m_Children`/`m_Father` 双向一致；Renderer、Mesh、骨骼、材质和 MonoBehaviour PPtr 无悬空引用。最终还要在游戏日志中确认 AssetBundle 加载并逐个实例化相关 prefab，离线解析通过不等于游戏可用。

## 不可处理或需升级

Bit/BepInEx 二次保护（例如固定标记后压缩数据仍无法解码）不能通过删除标记或修正文件长度解决。没有对应正常原件时，应停止离线猜测，改在关闭网络的隔离 Unity/BepInEx 环境中运行插件；未知 `Bit.xml` 是原生 DLL，不得直接放入主机游戏目录。

若只发现 Build Target 端序、尾部 Transform 断链、外部 `.resS` 依赖或 Mesh 零切线等单点缺陷，只修改被格式或日志证据唯一确定的字段，并使用对应项目脚本/专题记录；不要扩大为整包重建。

## 相关项目工具

- `apps/scripts/decrypt_unity3d.py`：模板辅助的 UnityFS/SerializedFile 修复。
- `apps/scripts/decrypt_xt_unity3d.py`：XT 循环 XOR 自恢复。
- `apps/scripts/recover_sakuraba_no_source.py`：仅限已验证 Sakuraba profile 的无原件恢复。
- `apps/tools/assetstudio-helper`：对象、原始数据和文本的 JSON 诊断边界。
- 详细案例、B002 内嵌流、wen 57 字节包裹、鞋类 CmpClothes、切线修复和安全要求见项目解密记录。
