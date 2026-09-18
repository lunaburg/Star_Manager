# Star_Manager 缓存与运行时文件登记

本文登记当前 Electron/Vue/Python 应用产生或依赖的缓存、索引、临时文件和派生运行时文件。审计基线为 2026-08-03；描述以当前代码为准。修改缓存路径、缓存键、失效条件或清理行为时，必须同步维护本文。

## 1. 统一路径和分类

应用运行时根目录由 `STAR_MANAGER_RUNTIME_DIR` 决定：

| 运行方式 | 默认位置 |
| --- | --- |
| 开发运行 | `apps/backend/runtime/` |
| Windows 打包运行 | `Star_Manager.exe` 同级的 `runtime/` |
| 外部显式配置 | `STAR_MANAGER_RUNTIME_DIR` 指定的目录 |

本文使用以下分类：

- **可重建缓存**：删除后可以从游戏目录、zipmod、人物卡或插件文件重新生成。
- **索引兼缓存**：主要是派生索引，但同一存储文件还包含用户状态；不能直接当作纯缓存删除。
- **进程内缓存**：只存在于当前 Python/Electron/Vue 进程，重启后自然消失。
- **临时/派生文件**：由外部工具或后续工作流继续使用，不能仅因为它位于 runtime 目录就直接删除。
- **开发工具缓存**：只服务于测试、依赖安装或构建，不随用户运行时产生。

源文件仍是数据源：HS2 游戏目录、`UserData/chara` 人物卡、`mods/**/*.zipmod`、zipmod 内的 `manifest.xml`/CSV/Unity3D，以及 BepInEx 文件。runtime 下的资源索引和生成文件都不是源文件。

### 2.0 `trash/`：可恢复删除文件

位置：`<runtime>/trash/cards/` 和 `<runtime>/trash/mods/`。

这是由用户删除动作产生的可恢复文件区，不属于可直接清理的普通缓存。人物卡和整包 zipmod 删除时先移动到这里，并在每个条目目录写入 `record.json`；回收站页面可以恢复、永久删除或清空。恢复模组后会重新索引单个 zipmod，恢复人物卡后由前端刷新卡片目录。只有用户明确执行永久删除/清空，或手动删除回收站目录时，文件才会真正消失。

### 2.0.1 `pending-deletes/`：被 Windows 文件占用而等待续行的删除请求

位置：`<runtime>/pending-deletes/<operation-id>.json`。

- 单个模组移动到回收站或单个物品写回 zipmod 时，如果 Windows 报告共享占用，应用会把删除意图和目标数据库/文件信息原子写入这里。
- 这是持久化的操作队列，不是回收站文件，也不是可重建缓存；队列存在时，原 zipmod 和 SQLite 记录仍保留，避免数据库提前丢失导致后续扫描重新出现模组。
- 后端启动一个 5 秒间隔的后台重试 worker；应用重启后会继续读取队列。回收站页面显示等待数量，也提供一次手动重试接口。
- 成功完成后，整包模组才进入 `trash/mods`，或物品删除才完成 zipmod 写回并刷新索引，随后移除对应 JSON。普通路径错误、坏压缩包和非占用权限错误不会无限排队。
- 排查时可查看 `last_error`、`attempts` 和 `payload`；确认游戏及外部 zip 工具已关闭后可使用页面“立即重试”。不要手动删除正在等待的源 zipmod；如需取消操作，应先移走/备份对应 JSON 并确认不会与当前重试并发。

`settings.json`、HS2 的 `UserData/setup.xml`、工作台工程目录和用户指定的导出目录属于持久化配置或明确的用户输出，不属于缓存；本文只在相关位置说明它们与缓存的边界。

## 2. 应用运行时磁盘缓存和索引

### 2.1 `star_manager.sqlite`：主索引兼缓存数据库

位置：`<runtime>/star_manager.sqlite`

这是一个 SQLite 文件，不应把整个文件简单视为“可随时删除的缓存”。其中既有可从源文件重建的索引，也有应用本地状态：

| 逻辑缓存/数据 | SQLite 内容 | 失效或刷新条件 |
| --- | --- | --- |
| zipmod/物品索引 | `zipmods`、`mod_items`、`duplicate_zipmods` | 增量建库比较 zipmod 路径、文件大小和修改时间；全量建库或受影响 GUID 处理时重新解析 |
| 人物卡浏览索引 | `character_cards`、`character_card_dependencies` | 人物卡新增、移动、删除或大小/修改时间变化；全量建库；受影响模组 GUID 变化时重连依赖 |
| 人物卡浏览字段缓存 | `character_cards.chara_name`、`tags_json`、`favorite`、`rating`、`metadata_file_size`、`metadata_modified_ns`、`preview_cache_path` | 文件签名变化时读取 PNG；收藏、评分、标签等单卡操作会同步索引 |
| 人物卡标签目录缓存 | `database_metadata.character_card_tags_cache_root` + `character_cards.tags_json` | 游戏目录根路径变化、全量建库或标签写入后回填；`/library/cards/tags` 会复用有效缓存 |
| 插件扫描缓存 | `bepinex_plugin_cache` | 以游戏目录为键，以 BepInEx DLL、`.dl_`（兼容读取历史 `.dll.disabled` 和临时 `.dll.dl_`）、配置和翻译文件的大小/修改时间指纹失效；`refresh=1` 强制重扫 |
| 建库元数据 | `database_metadata` 中的构建时间、解析器版本和缓存根路径 | 每次对应建库或迁移更新 |
| 本地成就状态 | `achievement_progress`、`achievement_events`、`achievement_preferences` | 由成就事件和设置操作更新；这是持久化用户状态，不是可无损删除的缓存 |

清理规则：

- 需要重建索引时优先使用应用内“重建数据库”或对应任务。
- 如必须删除 SQLite，先退出应用并备份文件；重建会恢复资源索引，但会影响本地成就历史/进度，并会清除尚未重新建立的索引状态。
- 收藏、评分和标签的主要内容会写回人物卡的 `KKEx`/Card metadata 数据块，SQLite 中的对应字段仍然是浏览缓存和查询索引；删除数据库后需要重新建库才能显示。
- 不要在后端运行时直接删除或覆盖 SQLite，避免连接、迁移或任务写入失败。

相关实现：[`mod_database_core.py`](../backend/star_manager/services/mod_database_core.py)、[`mod_database.py`](../backend/star_manager/services/mod_database.py)、[`card_database.py`](../backend/star_manager/services/card_database.py)、[`plugin_library.py`](../backend/star_manager/services/plugin_library.py)、[`achievements.py`](../backend/star_manager/services/achievements.py)。

### 2.2 `ais_card_cache.json`：AIS 人物卡类型判定缓存

位置：`<runtime>/ais_card_cache.json`

- 键为人物卡绝对路径。
- 值保存缓存版本、文件大小、`mtime_ns` 和 `is_ais` 判定结果。
- Python 进程会先把 JSON 加载到 `_AIS_CARD_CACHE`；发生新判定后标记 dirty，并在进程退出时写回。
- 缓存版本变化、路径签名变化或 JSON 损坏时自动重新判定。
- 可安全删除。删除后只会增加下一次人物卡识别的解析成本，不会修改人物卡。

实现：[`card_parser.py`](../backend/star_manager/core/card_parser.py)。

### 2.3 `thumbnails/`：zipmod 物品缩略图缓存

位置：`<runtime>/thumbnails/<sha1 前两位>/<sha1 接下来两位>/<sha1>.png`

- 缓存内容是从 zipmod 或游戏 `abdata` 提取、转换得到的 PNG。
- 键由 `zipmod_guid`、`item_id`、`thumb_ab`、`thumb_tex` 组成；数据库在 `mod_items.thumbnail_cache_path` 保存路径和状态。
- 单次建库内还有 `UnityThumbnailBundleCache` 和 `ThumbnailSourceCache`，分别复用已加载的 Unity3D 缩略图包/目标对象解码结果和同一来源的输出文件；Unity3D 包加载时不会预先解码所有图片，只有命中的 `ThumbTex` 或 fallback 对象才会执行 `obj.read()`。
- 物品资源解析成功后会复用已有输出文件；缺失、异常或相关 zipmod 重建时按数据库状态重试。
- 删除 PNG 是可重建操作，但 SQLite 可能暂时仍指向旧路径；删除后应执行相关模组/物品重建或重新提取缩略图。
- 当前没有面向用户的全局“清空缩略图缓存”按钮，也没有通用的孤儿文件回收任务。

实现：[`mod_database_assets.py`](../backend/star_manager/services/mod_database_assets.py)、[`mod_database_queries.py`](../backend/star_manager/services/mod_database_queries.py)。

### 2.4 `card_previews/`：人物卡、服装卡和场景卡标准化预览缓存

位置：`<runtime>/card_previews/<sha1 前两位>/<sha1 接下来两位>/<sha1>.png`

- 人物卡和服装卡默认生成标准 `252 x 352` 的 PNG；场景卡使用独立的 `320 x 180` 目标尺寸，供场景卡横向网格和详情预览使用，避免每次直接解码原始大图。
- 键包含人物卡绝对路径、源文件大小、`mtime_ns` 和目标尺寸；源文件变化或尺寸变化会得到新键。
- 服装卡复用同一目录，键同样包含服装卡绝对路径、源文件大小、`mtime_ns` 和目标尺寸；服装卡的附加信封不会被写入标准化预览。
- 键包含目标尺寸，因此同一个源文件的 `252 x 352` 与 `320 x 180` 预览不会相互覆盖；`character_cards.preview_cache_path` 保存人物卡当前索引使用的路径。
- 删除后会在下次人物卡列表/建库时重新生成；删除单张人物卡时，已知的对应预览缓存会一并删除。
- 旧版本或路径变化造成的孤儿预览文件不会被全局自动清理，可以在后端停止后清理整个目录，再重建人物卡数据库。

实现：[`card_library.py`](../backend/star_manager/services/card_library.py)、[`card_database.py`](../backend/star_manager/services/card_database.py)。

#### 卡片预览加载统一规则

所有卡片类型的列表预览都必须复用 `card_previews/`、`LazyThumbnail` 和可视区域虚拟渲染逻辑。列表接口只返回轻量元数据和带源文件签名的预览 URL；前端通过 `IntersectionObserver` 请求视口附近的图片，不能为渲染列表直接读取或解码原始卡片 PNG。完整卡片解析和原图请求仅允许发生在用户打开单卡详情后。新增卡片类型时，若无法遵循该规则，必须在对应页面文档和本文登记明确的性能与缓存边界。

### 2.5 `clothes_card_index.sqlite`：服装卡有效性索引

位置：`<runtime>/clothes_card_index.sqlite`

- 这是独立于 `star_manager.sqlite` 的可重建 SQLite 索引，只记录 `UserData/coordinate` 下 PNG 的文件签名、轻量 `AIS_Clothes` 有效性、卡片名称、解析器版本和封面结束位置。
- 索引键包含游戏目录根路径和服装卡相对路径；文件大小、`mtime_ns` 或解析器版本变化时重新校验。普通 PNG 和损坏文件会缓存为无效，列表接口不会返回它们。
- 进入大目录时只校验当前页面附近的未知文件，最多 96 个候选；有效性结果会保留到下次运行，完整 KKEx/UAR 详情不写入此索引。
- 打开服装卡目录树时，后端会在后台遍历 coordinate 子目录并复用该索引完成全量轻量校验；目录树首次显示 PNG 候选数，索引完成后改用 `is_valid=1` 的目录分组计数。前端在 `indexing=true` 期间轮询树接口，完成后自动替换数字。
- 删除该文件不会修改游戏目录；下次打开服装卡浏览器会按需重建。它不属于模组数据库重建流程，也不保存用户收藏等状态。

实现：[`card_library.py`](../backend/star_manager/services/card_library.py)。

### 2.6 `model_previews/`：物品模型 GLB 缓存

位置：`<runtime>/model_previews/<sha1 前两位>/<sha1>.glb`，有时同目录还有 `<sha1>-half.glb`。

- 由模组数据库物品或工作台工程物品的 MainAB/MainData 转换得到，供 Three.js 预览。
- 模组库预览键包含物品 ID、zipmod 修改时间、MainAB、MainData 和预览转换版本（当前为 `main-data-v17-png-no-optimize`）；工作台预览键包含工程 Unity3D 绝对路径、文件大小、修改时间、MainData、Kind 和转换版本（当前为 `workbench-main-data-v3-png-no-optimize`）。相同输入命中已有 GLB 时不重复转换；贴图编码器从 PNG `optimize=True` 改为 `optimize=False` 后会生成新键。工作台替换贴图或修改资源后也会生成新的缓存键。
- Electron 在正常 `before-quit` 阶段删除整个 `model_previews` 目录，因此它主要是跨请求、单次运行期间的缓存。
- 崩溃或强制终止可能留下旧文件；应用启动前或后端停止后可以删除。删除后重新打开模型预览即可生成。

实现：[`model_preview.py`](../backend/star_manager/services/model_preview.py)、[`main.cjs`](../electron/main.cjs)。

### 2.7 `unity3d_open/`：外部工具打开用的 Unity3D 派生副本

位置：`<runtime>/unity3d_open/<sha1 前两位>/<键>-<安全文件名>.unity3d`

- 当资源位于 zipmod 内时，应用会把 Unity3D 成员解压为临时副本，并把路径交给 AssetStudio/SB3Utility 等外部工具。
- 键包含 zipmod 绝对路径、zipmod 修改时间、大小和成员路径。
- 该目录没有应用退出时的自动清理；它不是普通预览缓存，外部工具仍可能正在读取。
- 确认外部工具关闭且不再需要导出文件后才可清理。删除不会修改原始 zipmod。

实现：[`model_preview.py`](../backend/star_manager/services/model_preview.py) 的 `prepare_item_unity3d_file()`。

### 2.8 `unity3d_preprocessed/`：Unity3D 预处理派生文件

位置：Electron 临时目录 `star-manager-sb3utility/preprocess-<uuid>.unity3d`；写入工程前会复制到项目资源目录。

- 保存 MainData 选择以及“复制并重命名”对象的预处理结果，供工作台继续检查或写回工程。
- 签名包含源文件信息、操作类型和选择参数；同一操作会生成稳定的派生路径。
- 每次实际生成派生内容时，Electron 都调用 `SB3UtilityScript.exe` 保存对象修改；模板写入工程时再调用 `RenameCabinet` 生成新的 CAB，防止多个源自同一模板的输出在 Sideloader 中冲突。Python 后端只负责重新读取候选对象。
- 当前没有自动清理。它属于可重新生成的派生文件，但在用户完成复制/写回前不得删除。

实现：[`main.cjs`](../electron/main.cjs) 的 `runWorkbenchSb3Mutation()` 和 `workbench:preprocessTemplate` IPC。

### 2.9 `remote/remote_zipmod_index.sqlite`：远端模组只读索引

位置：开发运行时的 `apps/backend/runtime/remote/remote_zipmod_index.sqlite`；Windows 发布版的 `Star_Manager.exe` 同级 `runtime/remote/remote_zipmod_index.sqlite`。

- 该 SQLite 文件由 `build_remote_zipmod_index.py` 生成，记录可供人物卡和场景卡缺失依赖查询、下载的远端 zipmod manifest 信息。
- 后端通过 `STAR_MANAGER_RUNTIME_DIR` 定位它，并以只读方式打开；它不是本地 `star_manager.sqlite`，也不参与本地模组建库。
- Windows 打包时由 `apps/package.json` 的 `extraFiles` 从 `apps/backend/runtime/remote` 复制到发布目录；`package:win` 会在 electron-builder 前检查该文件存在，缺失时直接终止打包。
- 发布版携带的是打包时的索引快照。更新远端索引后需要重新执行 Windows 打包；运行中的应用不会自动把它更新为最新版本。
- 这是发布资源而非普通用户缓存。若需要替换，应先退出应用，用新的完整 SQLite 文件替换，再重新启动；不要在后端查询期间覆盖文件。

实现：[`remote_mod_completion.py`](../backend/star_manager/services/remote_mod_completion.py)、[`build_remote_zipmod_index.py`](../scripts/build_remote_zipmod_index.py) 和 [`package.json`](../package.json)。

## 3. 前端和 HTTP 层缓存

### 3.1 工作台资料的 localStorage 回退缓存

存储键：`star-manager.workbench-profile`

- 位置是 Electron renderer 的 `localStorage`，由 Chromium 按应用用户数据目录保存，代码没有自定义文件路径。
- 内容只有 `authorId` 和 `workspacePath`，用于设置文件不可写或迁移期间的工作台资料回退。
- Electron 的 `settings.json` 是规范持久化来源，localStorage 不是工作台项目清单的主存储。
- 清除 renderer 的站点数据只会丢失这个回退值；重新选择作者/工作区即可恢复。不要把 `settings.json` 当缓存清理。

实现：[`App.vue`](../src/App.vue)、[`main.cjs`](../electron/main.cjs)。

### 3.2 卡片列表的前端状态

`App.vue` 只在当前 renderer 会话中保留当前目录已经返回的有效人物卡/服装卡/场景卡文件项、分页位置和目录树。切换目录或刷新会替换对应状态；服装卡有效性和轻量卡片名称由后端的 `clothes_card_index.sqlite` 持久化，前端本身不保存完整解析结果。三类卡片网格分别通过 `VirtualCharacterCardGrid` / `VirtualClothesCardGrid` 只创建视口附近的卡片 DOM，并通过 `LazyThumbnail` 的 IntersectionObserver 只请求视口附近图片；服装卡首批分页最多保留 96 条。

### 3.3 卡片浏览滚动位置

- 位置是 `App.vue` 的 renderer 进程内状态，按 `character`、`clothes` 和 `scene` 分别保存人物卡、服装卡、场景卡浏览器的垂直 `scrollTop`；没有存储键，也不写入 `localStorage`。对应列表数组、分页偏移和加载标记同样只保留在当前 renderer 会话中。
- 三个卡片浏览器的实际滚动容器由 `CharactersView.vue` 注册到应用壳层；切换到开始游戏或其它页面前同步捕获当前位置，返回卡片管理页或切换卡片类型后，在异步列表和虚拟网格完成更新时多次恢复。虚拟网格不会在重新挂载时无条件置顶，目录切换则由目录选择操作显式清零对应类型的位置。
- 这段状态只属于当前应用 renderer 进程，刷新页面、renderer 重载或重启应用后自然清空；人物卡/服装卡/场景卡的数据库索引、源文件和解析缓存不受影响。

实现：[`CharactersView.vue`](../src/components/views/CharactersView.vue)、[`VirtualCharacterCardGrid.vue`](../src/components/VirtualCharacterCardGrid.vue)、[`VirtualClothesCardGrid.vue`](../src/components/VirtualClothesCardGrid.vue)、[`App.vue`](../src/App.vue)。

### 3.4 模组管理列表滚动位置

- 位置是 `App.vue` 的 renderer 进程内状态，按 `mods` 和 `items` 分别保存模组浏览、物品浏览列表的垂直 `scrollTop`，没有存储键，也不写入 `localStorage`。两种浏览模式已加载的行数据、分页 `offset` / `hasMore` 和加载标记也属于同一份进程内状态。
- 页面切换期间由应用壳层的 `KeepAlive` 优先保留模组管理实例和实际滚动容器；`App.vue` 在切页前同步捕获已注册容器的 `scrollTop`。刷新页面或重启应用后，这段内存状态会自然清空。
- 列表异步加载、浏览模式切换和应用视图返回时由应用壳层再次尝试恢复；返回任一浏览模式时，如果首批或增量请求仍在进行，不会重复发起 reset 请求，已加载批次会继续保留。筛选重载或数据库内容变化时，浏览器会按新的内容高度自然限制滚动位置。
- 应用重启不会影响模组数据库、筛选条件来源或游戏目录，只会让列表滚动位置回到初始位置。

实现：[`ModsView.vue`](../src/components/views/ModsView.vue)、[`App.vue`](../src/App.vue)。

### 3.5 人物卡标签目录的 Vue 进程内缓存

前端 `App.vue` 的 `cardTagCatalog` 保存当前游戏目录的标签列表，打开标签弹窗或筛选器时复用，切换游戏目录后失效。它不落盘，刷新页面或重启 renderer 后消失。

### 3.6 mannequin FBX 模板 Promise 缓存

[`modelPreviewAssets.js`](../src/modelPreviewAssets.js) 的 `mannequinTemplatePromises` 按 URL 缓存 FBX 加载 Promise，使同一 renderer 内多个模型预览共享一次模板加载。加载失败会删除对应键；刷新页面或关闭应用后消失。

### 3.7 HTTP/Chromium 资源缓存

后端 `send_bytes()` 和 `send_file()` 对图片、GLB、FBX 等资源返回：

```text
Cache-Control: public, max-age=604800, immutable
ETag: 基于文件修改时间和大小
Last-Modified: 文件修改时间
```

适用资源包括：

- `/mods/thumbnails`
- `/library/cards/image` 的原图和标准预览
- `/mods/models/<file>.glb`
- `/mods/mannequin/body.fbx`

实际缓存由 Electron/Chromium renderer 管理，不在 `<runtime>` 下。人物卡封面修改后，前端会把 `image_version` 加到 URL 作为 cache-buster；其它资源主要依靠稳定生成键和 ETag。应用没有自定义的 HTTP 缓存清理接口。

Electron 还可能在默认 user data 目录维护 `Cache`、`Code Cache`、`GPUCache` 等平台目录；当前 `main.cjs` 没有自定义位置或主动清理逻辑。这些是 Electron 平台缓存，不应与后端 runtime 缓存混在一起登记。

当前 renderer 代码没有使用 `sessionStorage`、IndexedDB 或 Cache Storage 作为应用数据缓存。

## 4. Python 进程内缓存

以下缓存不写入磁盘，生命周期通常不超过一次任务或一次 HTTP 请求：

| 缓存 | 位置/用途 | 生命周期 |
| --- | --- | --- |
| `_AIS_CARD_CACHE` | `card_parser.py` 读取 `ais_card_cache.json` 后的进程内字典 | Python 后端进程生命周期；退出时 flush dirty 状态 |
| `UnityThumbnailBundleCache.bundles` | 同一建库任务内复用已解析的 Unity3D 缩略图包 | 一次建库调用 |
| `ThumbnailSourceCache.results` | 同一建库任务内复用同一来源生成的缩略图结果 | 一次建库调用 |
| `model_preview.py` 的 transform matrix cache | 复用同一 Unity3D 预览转换中的世界矩阵 | 一次模型预览转换 |
| `model_preview.py` 的 texture cache | 复用同一模型预览转换中已导出的纹理 PNG | 一次模型预览转换 |

这些对象不能通过删除文件清理；重启相关进程即可释放。

## 5. 临时文件和诊断输出：不是缓存，但容易被误认

### 5.0 游戏物品探针快照

位置：`<HoneySelect2>/BepInEx/config/StarManager.GameItemProbe.items.json`，也可由探针的 `Output/SnapshotPath` 配置修改。

- 这是 `StarManager.GameItemProbe` 生成的只读诊断快照，不属于 Star Manager 的 Python/Electron runtime 缓存。
- 内容来自游戏运行时的 `ChaListControl`、`UniversalAutoResolver` 和当前角色坐标；刷新请求在 Unity 主线程执行。
- 文件会在探针周期刷新时覆盖，删除不会修改游戏资源、zipmod 或角色卡；停止游戏后可安全删除。
- `/api/items` 等回环 HTTP 接口直接读取进程内快照，快照文件主要用于离线检查和故障反馈。

| 路径/模式 | 用途 | 当前行为和清理边界 |
| --- | --- | --- |
| `<runtime>/thumbnail_uploads/preview-*.png` | HTTP 图片上传的短暂落盘文件 | 请求结束后在 `finally` 中删除；进程异常退出可能遗留，确认没有上传任务后可清理 |
| `<runtime>/thumbnail_profile.log` | 当前缩略图建库的性能记录 | 诊断日志，不参与缓存命中；没有通用轮转策略 |
| `<runtime>/thumbnail_profile_<时间>_<run>.jsonl` | 每次缩略图建库的详细 profiling | 诊断日志，不是缩略图数据；可按日志保留策略清理 |
| `<runtime>` 下的手工分析/解密/测试目录 | 脚本或人工操作产生的分析结果 | 当前维护应用没有统一目录管理，不能仅凭目录名推断为应用缓存 |

代码内部还会创建系统临时目录、`.tmp` 文件和同目录替换文件，用于 Unity3D 解码、CSV/zipmod 原子写入和设置保存。这些是单次操作的安全写入中间物，不是长期缓存；不要把用户的 `.bak` 备份当作缓存自动删除。

## 6. 开发、测试和构建缓存边界

这些目录不属于用户运行时缓存，但在仓库开发环境中会出现：

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `__pycache__/`、`*.pyc` | Python 字节码缓存 | 可删除，运行测试或后端时会重新生成 |
| `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`.coverage`、`htmlcov/` | 测试/静态检查缓存或报告 | 可删除，不影响应用运行数据 |
| `.npm-cache/`、`apps/.npm-cache/` | npm 下载缓存 | 可删除，但下次安装依赖会重新下载 |
| `apps/.dotnet-home/` | .NET CLI/NuGet 工具缓存 | 服务于 Card metadata 插件测试/构建，不属于用户运行时 |
| `apps/dist/` | Vite 构建产物 | 生成物，不是运行时缓存；`npm run build` 会重建 |
| `apps/build/`、`apps/release/`、`apps/release-packaged/`、`apps/extracted/` | PyInstaller/electron-builder 或提取产物 | 生成物，不是用户 runtime 缓存 |

`node_modules/`、`backend/.vendor/`、依赖包和工作台导出目录也不是应用缓存：它们分别是依赖/运行资源或用户明确生成的输出，不能套用缓存清理规则。

## 7. 清理决策速查

| 目标 | 风险等级 | 建议 |
| --- | --- | --- |
| `ais_card_cache.json`、`card_previews/`、`clothes_card_index.sqlite`、`model_previews/` | 低 | 停止相关进程后可删除，再按需自动生成；模型预览正常退出通常已自动清理 |
| `thumbnails/` | 中 | 可重建，但删除后需重建/重新提取以恢复 SQLite 路径指向的文件 |
| `thumbnail_uploads/`、旧 profiling 日志 | 低 | 确认没有运行中的任务后清理 |
| `unity3d_open/`、`unity3d_preprocessed/` | 中 | 先确认外部工具和工作台写回流程结束；它们可能是用户下一步操作的输入 |
| `star_manager.sqlite` | 高 | 先备份，优先使用应用内重建；不要把成就等本地状态当作缓存丢弃 |
| Electron `Cache`/`Code Cache`/`GPUCache` 或 renderer storage | 中 | 只在排查页面缓存问题时清理；会清除 localStorage 回退值，应用没有自己的清理按钮 |

新增缓存时至少登记：名称、默认路径、是否持久化、缓存键、源数据、失效条件、是否自动清理、删除后的恢复方式，以及对应实现文件。
