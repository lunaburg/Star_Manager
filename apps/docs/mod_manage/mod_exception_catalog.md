# 模组异常分类说明

## 目标

本文档说明当前模组管理页中已实现的异常类型、触发条件、界面标题和对应解决方案，供维护和后续扩展时参考。

## 异常总览

当前异常详情主要来自 `GET /mods/zipmods/<id>/diagnostics` 返回的 `issues` 列表。每个异常项都包含：

- `type`：异常分类。
- `status`：异常状态。
- `path`：关联路径或诊断锚点。
- `affected_count`：影响数量。
- `affected_items`：受影响物品或文件。
- `solution`：界面展示的解决方案说明。
- `repair_action`：可执行修复动作标识。

## 异常分类

### `manifest_author`

触发条件：

- `manifest.xml` 中 `author` 为空。

界面标题：

- `缺少模组作者`

解决方案：

- 输入作者名并写回 `manifest.xml`。

操作入口：

- 异常详情中的 `补作者`。

后端动作：

- `POST /mods/zipmods/<id>/update-author`

说明：

- 该异常在模组列表中也会影响作者显示，空值会显示为 `未知作者`。

### `unity3d`

触发条件：

- `MainAB` 关联的主 `.unity3d` 文件在 zipmod 内和游戏目录中都找不到。
- 或者 `MainAB` 主 `.unity3d` 文件只存在于游戏目录 `abdata` 中。
- 或者 `MainAB` 主 `.unity3d` 文件存在但无法作为有效 Unity 资源使用。当前实现中，这类 `error` 主要由 `ThumbAB` 与 `MainAB` 指向同一个 `.unity3d`，且缩略图解析发现 UnityPy 无法读取可用资源时触发。

界面标题：

- `Unity3D 文件无法找到`

解决方案：

- `in_game`：将对应 `.unity3d` 文件补入 zipmod。
- `missing`：重新安装来源模组，或手动找回对应 `.unity3d` 文件后重建数据库。

操作入口：

- `补入 zipmod`

后端动作：

- `POST /mods/zipmods/<id>/repair-unity3d`

说明：

- `ThumbAB` 缺失、缩略图 Unity3D 缺失、缩略图 Unity3D 解析失败，如果该 `ThumbAB` 不是同一个物品的 `MainAB`，只归入 `thumbnail` 异常，不归入 `unity3d` 异常。

### `thumbnail`

触发条件：

- 该 zipmod 下存在 `parse_status = ok` 但 `thumbnail_status` 不是 `ready` / `ok` 的物品。
- 包括 `ThumbAB` 为空、`ThumbTex` 为空、缩略图源文件找不到、缩略图 Unity3D 存在但找不到贴图资源、缩略图 Unity3D 无法解析等情况。

界面标题：

- `缩略图缺失`

解决方案：

- 为单个物品选择一张图片，自动导入 zipmod，并回写该物品 CSV 的 `ThumbAB` / `ThumbTex`。

操作入口：

- `选择图片`

后端动作：

- `POST /mods/items/<id>/import-thumbnail`
- `POST /mods/items/<id>/delete`

说明：

- 导入后的图片会写入 zipmod 内的 `abdata/thumbnail/star_manager/`。
- 如果缩略图问题来自 `ThumbAB`，但该 `ThumbAB` 同时也是物品 `MainAB`，并且 UnityPy 无法解析可用资源，则物品和 zipmod 会被归入 `unity3d` `error`，因为这说明主资源本身不可用。
- 删除物品会从 zipmod 中移除对应 CSV 行，并尝试移除相关 `.unity3d` 引用文件；该操作会修改 zipmod，必须走明确确认。

### `duplicate_zipmod`

触发条件：

- 多个 zipmod 具有相同 `guid`。

界面表现：

- 进入重复模组诊断或标题栏 `dupes` 统计。

解决方案：

- 以主记录为准，保留主 zipmod，重复文件单独记录并提示用户处理。
- 点击 `清理重复模组` 可删除重复文件并清空该 GUID 的重复记录。

说明：

- 当前 UI 主要展示重复 GUID 数量，不提供高风险自动合并。
- 该异常会把主 zipmod 本身也标记为 `异常`。
- 清理动作会删除 `duplicate_zipmods` 中记录的重复文件，并尝试从磁盘移除对应 `.zipmod`。

### `delete_zipmod`

触发条件：

- 诊断结果返回 `can_delete = true`。
- 当前实现中仅当该 zipmod 有缺失 `.unity3d`，且没有 `in_mod` 或 `in_game` 物品引用时允许删除。

界面入口：

- 诊断 tab 底部的 `删除模组`。

后端动作：

- `POST /mods/zipmods/<id>/delete`

说明：

- 删除动作会从磁盘删除对应 `.zipmod` 文件，并删除数据库主记录。
- 这是高风险操作，调用侧必须让用户知道将删除的具体模组。

### `invalid_manifest`

触发条件：

- `manifest.xml` 解析失败。
- 或 `guid` 缺失。
- 或 `author` 缺失。

界面表现：

- 模组列表状态显示为 `异常`。

解决方案：

- 根据具体错误修复 manifest 内容，再重建数据库。

## 与列表状态的关系

- `正常`：`scan_status = ok`，作者不为空，没有重复 GUID，没有主资源 `unity3d` 问题，也没有缩略图问题。
- `错误`：包括 `invalid_manifest`、`missing_manifest`、主资源 `MainAB` 缺失、主资源 Unity3D 损坏等会影响物品本体可用性的情况。
- `警告`：包括作者为空、主资源只在游戏目录中、重复 GUID、缩略图缺失或缩略图解析失败等需要人工整理但不一定影响物品本体可用性的情况。
- `已失效`：`scan_status = stale`。

## 备注

- 这份分类以当前已实现的诊断和修复入口为准。
- 新增异常时，应同步更新后端 `zipmod_unity3d_diagnostics` / 相关修复接口、前端标题映射和本文档。
