# Frontend/backend interface

This document records how the Vue renderer, Electron shell, and Python backend connect.

## Layers

```text
Vue renderer
  -> window.desktopApi in electron/preload.cjs
  -> Electron IPC handlers in electron/main.cjs
  -> Python HTTP backend at http://127.0.0.1:8765
  -> backend/star_manager business services
```

The renderer should not call Node, Electron, or filesystem APIs directly. Use `window.desktopApi`.

## Electron preload API

Defined in `apps/electron/preload.cjs`.

- `selectDirectory(title)`: open a native directory picker.
- `onStartupLog(callback)`: subscribe to startup milestone log events forwarded from the Electron main process, including `ready-to-show`, `renderer-ready`, and `first-screen-shown`; events received before the renderer registers are buffered by preload and replayed; returns an unsubscribe function.
- `selectPackageFile(title)`: open a native file picker limited to Sims 4 `.package` files.
- `selectUnity3dFile(title)`: open a native file picker limited to `.unity3d` files for Workbench resource import.
- `selectUnity3dExportPath(title, defaultName)`: open a native save picker for one exported `.unity3d` file.
- `selectImageFile(title, defaultPath)`: open a native image picker, optionally rooted at a default path.
- `selectWallpaperFile(title, defaultPath)`: open an image/MP4 picker for the application wallpaper.
- `readWallpaperImage(filePath)`: read one validated local wallpaper image and return a data URL for the renderer.
- `selectImageForCrop(title)`: open a native image picker for character-card cover replacement.
- `selectBlenderExecutable(title)`: select a Windows `blender.exe` executable for persistent Workbench integration.
- `selectSb3UtilityExecutable(title)`: select a Windows `SB3Utility.exe` executable for the external tool.
- `promptText(title, message, defaultValue)`: open a native text prompt.
- `showItemInFolder(filePath)`: reveal a file in the system file manager.
- `openUnity3dInSb3Utility(filePath)`: validate one `.unity3d` file and launch it through the configured SB3Utility executable.
- `openDirectory(directoryPath)`: open an existing directory in the system file manager.
- `deleteSims4ResultDirectory(directoryPath)`: delete one validated Sims 4 Package→FBX export result directory after the renderer confirmation step.
- `createWorkbenchProject(payload)`: create one validated Workbench project and its manifest/CSV directory structure.
- `deleteWorkbenchProject(payload)`: delete one validated Workbench project after the renderer confirmation step.
- `scanWorkbenchProjects(payload)`: list projects below the configured Workbench workspace.
- `scanWorkbenchItems(payload)`: read the CSV-backed items of one validated Workbench project.
- `scanWorkbenchUnity3d(payload)`: scan one Workbench project for `.unity3d` files under `abdata/` and report the built-in template.
- `scanWorkbenchAssetFiles(payload)`: recursively scan one Workbench project for external texture files and `.fbx` models, returning project-relative paths and file sizes.
- `loadWorkbenchAssetPreview(payload)`: read one validated PNG, JPEG, WebP, or BMP texture under the Workbench project and return a data URL for the renderer preview.
- `loadWorkbenchThumbnail(payload)`: read one project-local Workbench item thumbnail as a data URL.
- `saveWorkbenchThumbnail(payload)`: write one validated Workbench item thumbnail beneath the project.
- `createWorkbenchItem(payload)`: append one validated item row to a Workbench CSV.
- `deleteWorkbenchItem(payload)`: remove one validated item row from a Workbench CSV.
- `validateWorkbenchMainResource(payload)`: validate one Workbench item's `MainAB`, `MainData`, `MainTex`, and `ColorMaskTex` against the Unity3D resource under the project `abdata/` directory.
- `previewWorkbenchItem(payload)`: resolve one Workbench item's project-relative `MainAB`, validate the project boundary, and generate a cached GLB preview for its `MainData` through the Python backend.
- `openWorkbenchMainResourceInSb3Utility(payload)`: resolve one Workbench item's project-relative `MainAB` under `abdata/`, validate the file, and launch it through the configured SB3Utility executable.
- `openWorkbenchAssetInSb3Utility(payload)`: validate one project-contained texture or `.fbx` asset and launch it through the configured SB3Utility executable.
- `updateWorkbenchItemResourceFields(payload)`: update only one Workbench CSV row's `MainData`, `MainTex`, or `ColorMaskTex` fields after validating the project and CSV boundaries.
- `importWorkbenchTexture(payload)`: validate an external image and a project-relative `MainAB`, resolve the current `MainData` GameObject/Animator component, then import it as a renamed `Texture2D` or replace the pixels of an existing named texture when `replaceExisting` is true. Existing-texture replacement rejects a missing target and reopens the temporary Unity3D to verify the texture before atomically replacing the project file.
- `exportWorkbenchProcessedTexture(payload)`: validate the current Workbench project and renderer-generated PNG data, open a native save dialog rooted at that project, verify the PNG signature and size limit, and write one user-selected output file for later SB3Utility import.
- `applyWorkbenchMainResource(payload)`: select an existing project resource, import an external Unity3D, copy the built-in template, or copy a database item Unity3D template; every newly copied resource receives a verified unique CAB before one Workbench CSV row is updated with `MainManifest`, `MainAB`, `MainData`, and `StateType`.
- `preprocessWorkbenchTemplate(payload)`: create a disposable Workbench Unity3D copy containing only the selected GameObject hierarchy before resource write-back.
- `packageWorkbenchMod(payload)`: package one validated Workbench project into a formal zipmod under the configured game's `mods` directory; include only `manifest.xml`, Workbench CSV files, Unity3D files referenced by `MainAB`/Unity3D `ThumbAB`, and directly referenced thumbnail files, replacing older archives with the same manifest GUID. After the archive is written, Electron waits for `index_single_zipmod`, which indexes only that generated archive.
- `onWorkbenchPackageProgress(callback)`: subscribe to Workbench packaging progress events and receive an unsubscribe function.
- `launchGameExecutable(launchType, gameDir)`: launch `HoneySelect2.exe`, `StudioNEOV2.exe`, or `HoneySelect2VR.exe`.
- `openFbxInBlender(blenderPath, fbxPath)`: validate the configured Blender executable and one `.fbx` file, then launch Blender with a Python FBX import expression and the FBX directory as its working directory.
- `selectWorkbenchFbxFile(payload)`: open a `.fbx` picker rooted at the current Workbench project and return only a validated project-relative file.
- `selectFbxReferenceFile(payload)`: open a native `.fbx` picker for an external reference such as the HS2 `body.fbx` skeleton source.
- `transformWorkbenchFbx(payload)`: validate one project-contained `.fbx` and Blender, apply the imported rotation and scale to Mesh objects only while preserving Armature coordinate/unit transforms, detect Mesh local translation beyond the `1e-6` tolerance and bake that translation into the mesh data before resetting the Mesh transform, then export a unique `_transformed.fbx` or atomically replace the source. The response includes `alignmentIssueDetected`, `alignmentRepairApplied`, `translationIssueCount`, `translationRepairedCount`, and `translationRepairedMeshNames`. FBX export disables automatic leaf-bone creation. The fixed workflow does not accept custom angle or scale fields.
- `removeWorkbenchFbxSkin(payload)`: validate one project-contained `.fbx` and the configured Blender executable. When `backupOriginal` is true, copy the source to a unique `_backup.fbx` sibling and write a unique mesh-only output; when false, atomically replace the source after successful processing. This is a single-file local IPC operation, not a batch task or Python HTTP route.
- `bindWorkbenchHs2Skeleton(payload)`: validate one project-contained Mesh FBX, one external skeleton FBX, and Blender; optionally create a backup, then run the bundled non-skinned HS2 skeleton binding script and return output statistics.
- `transferWorkbenchFbxWeights(payload)`: validate one external skinned source FBX and one project-contained target FBX, optionally back up the target, then run the bundled nearest-vertex weight transfer script and return mapping statistics.
- `apps/build-resources/workbench-templates/blender_bind_hs2_skeleton.py`: standalone Blender script for adding the Armature from a reference `body.fbx` to an unskinned mesh as an object parent only; it deliberately creates no Armature Modifier or Vertex Groups.
- `loadSettings()`: load persisted app settings.
- `saveSettings(settings)`: save persisted app settings, including `blenderExecutablePath` and `sb3utilityExecutablePath`.
- `loadGameSetup(gameDir)`: read the game's `UserData/setup.xml` through the Electron main process.
- `saveGameSetup(gameDir, setup)`: validate and atomically write the game's `UserData/setup.xml`, retaining its `.bak` backup and synchronizing supported Unity display registry values.
- `backendRequest(route, options)`: call the Python HTTP backend.
- `backendBaseUrl`: backend base URL, defaulting to `http://127.0.0.1:8765`.

## Recycle bin API

- `GET /trash`: list recoverable entries under `<runtime>/trash/`.
- `POST /trash/{cards|mods}/{entry_id}/restore`: move one entry back to its recorded source path. Restored mods are re-indexed through the single-zipmod indexing flow.
- `POST /trash/{cards|mods}/{entry_id}/delete`: permanently delete one entry from the runtime recycle bin.
- `POST /trash/empty`: permanently delete all valid recycle-bin entries.

## Mutation routing rule

- Single file or single object operations use direct HTTP API routes.
- Batch operations use `/tasks` and report progress through the task bridge.
- The Workbench packaging completion path is an exception: it uses the task bridge for `index_single_zipmod` so the generated archive is indexed only after the file is finalized and its progress can be shown in the Workbench.
- Do not add new bulk direct-HTTP mutation endpoints. Add a task type in `apps/backend/app/bridge.py`.

Examples:

- Direct HTTP: preview/export one item model, repair one zipmod, update one zipmod author, update one character card, import one item thumbnail, or delete one item.
- Task: import external resources, export selected zipmods, organize selected zipmods, bulk repair Unity3D, bulk update zipmod authors, rebuild the mod database, generate one portable card package, or run character-card batch maintenance.

## HTTP API

Implemented in `apps/backend/app/server.py`.

All JSON responses include at least `ok` unless the route serves a file. Errors return `{"ok": false, "error": "..."}` with an appropriate HTTP status.

Read and file routes:

- `GET /health`
  - Returns backend readiness, supported task types, supported API routes, and backend source path.
- `GET /tasks`
  - Returns all in-memory task states.
- `GET /tasks/:task_id`
  - Returns one task state.
- `POST /tasks/:task_id/control`
  - Body: `{ "action": "pause" | "resume" | "cancel" }`. Pauses or resumes a remote character-card mod download task; the current `.part` file and task progress are retained while paused. `cancel` requests cancellation and removes any incomplete `.part` file before the task reaches terminal status.
- `GET /mods/database?game_dir=`
  - Returns mod database status and summary counts. When `game_dir` is supplied, `builtin_item_count` is counted only for that selected game directory; without it, the builtin count remains `0` so records from another installation are not presented as current.
  - Zipmod summary counts include `zipmod_error_count` for red error rows and `zipmod_warning_count` for yellow warning rows. Duplicate GUIDs are still counted in `duplicate_guid_count` for diagnostics, but the top mod-library summary displays warning/error separately rather than a standalone duplicate count.
- `GET /mods/database/changes?game_dir=`
  - Compares indexed database records with current zipmod and character-card files under the selected game directory.
  - Returns whether a rebuild is needed, change counts, and whether an automatic incremental rebuild is recommended.
- `GET /cards/database`
  - Returns character-card database status and summary counts.
- `GET /plugins?game_dir=&search=&category=&offset=&limit=`
  - Recursively scans `BepInEx/Plugins`, `BepInEx/patchers`, and `BepInEx/core` without loading or executing DLL files. It returns DLLs with a successfully parsed `BepInPlugin` attribute and non-empty plugin GUID; ordinary dependency assemblies without that GUID are excluded.
  - Returns assembly identity/version, BepInEx plugin GUID/name/version, functional description and its source/confidence/evidence, dependencies, process restrictions, incompatibilities, assembly references, file metadata, `enabled` state, diagnostics, and summary counts. Disabled plugins are discovered from the same scan area with the `.dl_` suffix (for example `Example.dl_`) and keep the same stable `id` as their enabled DLL. Historical `.dll.disabled` files remain readable, but new disable operations never create that suffix. Descriptions prefer `AssemblyDescription`, then correlate matching `config/*.cfg` settings with `Translation/**/*.txt` labels; known-plugin and name-based descriptions are marked separately.
  - `GET /plugins/status?game_dir=` returns the fixed-file status used by the start page plugin switches, including patchers and core DLLs even when their metadata cannot be parsed.
  - The plugin library contains only DLLs with a valid `BepInPlugin` GUID. The maximum page size is 1000.
  - Results are cached in the shared SQLite database. A fingerprint of plugin DLLs, config files, and translation files invalidates stale entries automatically. Pass `refresh=1` to force a complete rescan.
- `GET /mods/zipmods?offset=&limit=&author=&status=&usage=&guid=&zipmod_id=`
  - Returns paged zipmod rows. `author` uses case-insensitive substring matching; `status` may be `normal`, `abnormal`, `warning`, `error`, `manifest_author`, `read_error`, `unity3d_missing`, `unity3d_in_game`, `unity3d_not_in_mod`, `thumbnail`, `duplicate_zipmod`, or empty. `usage` may be `used`, `unused`, or empty, based on character-card dependencies.
  - `guid` performs an exact case-insensitive manifest GUID lookup and is used by Workbench after packaging to locate the corresponding mod row.
  - `normal`: `scan_status = ok`, author is present, no duplicate GUID, no thumbnail issue items, no missing/error Unity3D, and no `in_game`/`not_in_mod` Unity3D references. A resource supplied by another zipmod is usable, but remains a warning because it is outside the current zipmod.
  - `warning`: empty author, external `MainAB`/non-public `TexAB` resources in game `abdata` or another zipmod (`unity3d_not_in_mod_count > 0`), duplicate GUID, or thumbnail issue items. `TexAB` and `MainAB` under `abdata/chara/00`–`60` are treated as shared game resources and do not create this warning.
  - `error`: missing manifest, missing required item `MainAB` Unity3D resource, item main Unity3D error, or `unity3d_missing_count > 0`. A missing `TexAB` alone is ignored.
  - `read_error`: the zipmod scan cannot read a manifest GUID, including missing `manifest.xml`, invalid manifest XML, missing/empty `<guid>`, or unreadable/bad zip files.
  - `thumbnail`: at least one parsed item has `thumbnail_status` empty or not `ready` / `ok`. Missing or unreadable thumbnail-only `ThumbAB` resources are represented here, not as Unity3D errors.
- `GET /mods/zipmods/authors`
  - Returns distinct zipmod authors.
- `GET /mods/zipmods/:id/diagnostics`
  - Returns diagnostics for one zipmod.
- `GET /mods/zipmods/:id/duplicate-analysis`
  - Re-parses the primary and duplicate zipmod files for one GUID and returns version, file size, modified time, item completeness, Unity3D status, thumbnail issues, and item-set differences to help decide which duplicate to keep.
- `GET /mods/zipmods/:id/manifest`
  - Returns editable `manifest.xml` fields for one zipmod.
- `GET /mods/items?offset=&limit=&zipmod_id=&search=&kind=&author=&status=&usage=&source=&game_dir=&include_total=`
  - Returns paged item rows. The existing default `source=mod` returns only `mod_items`; `source=builtin` returns `builtin_items` for the supplied selected `game_dir`; `source=all` merges both sources with stable source metadata. `status` may be `ready`, `error`, `thumb`, or empty. `error` covers items with parse errors, missing required `MainAB` Unity3D files, or missing original-game resources; missing `TexAB` alone does not create item error status. `usage` may be `used`, `unused`, or empty, based on character-card dependencies; builtin rows are excluded from usage-filtered results because their card association is resolved on demand rather than stored as `mod_item_id`.
  - `include_total` defaults to `1`; when set to `0`, the response omits the full count (`total: null`) and fetches one extra row to report `has_more`, which is the preferred mode for incremental scrolling after the first page.
  - Builtin rows include `source_type: "builtin"`, `source_label: "游戏本体"`, `game_dir`, `category_no`, `source_path`, original resource references, and the cached thumbnail URL. They never expose a zipmod GUID or zipmod ID.
  - Item display status is derived in the renderer: `error` for parse errors or `unity3d_status` `missing/error`; `thumb` for parsed items whose main Unity3D resource is usable but whose `thumbnail_status` is not `ready` / `ok`; `ready` when both the item and thumbnail are usable.
  - Item `unity3d_status` checks the current zipmod first, then game `abdata`, then the indexed contents of other zipmods. Missing `TexAB` is tolerated. A resource outside the current zipmod uses `not_in_mod`; `unity3d_source` is `game_abdata` or `other_zipmod`. Public `abdata/chara/00`–`60` resources are treated as shared. `ThumbAB` only affects `unity3d_status` when it points to the same `.unity3d` as `MainAB` and thumbnail parsing proves that file is not a usable Unity resource; a thumbnail-only `ThumbAB` problem remains a thumbnail issue.
- `GET /mods/items/filters?game_dir=`
  - Returns item filter options across the indexed mod and builtin item sources. When `game_dir` is supplied, builtin Kind options and the `游戏本体` author option are limited to that selected game directory; without it, builtin options are aggregated across indexed game directories.
- `GET /mods/thumbnails?path=`
  - Serves a cached thumbnail file from the backend thumbnail cache.
- `GET /mods/items/:id/thumbnail`
  - Serves one item's thumbnail and lazily rebuilds the runtime cache from its source zipmod when the indexed cache path is empty or unavailable. Failed extraction updates the item's thumbnail status and returns an error.
- `GET /mods/models/:file.glb`
  - Serves a generated GLB from the runtime model-preview cache. Model files are generated on demand and are disposable runtime data.
- `GET /mods/mannequin/body.fbx`
  - Serves the bundled mannequin FBX used as the clothing preview reference model.
- `GET /library/cards/tree?game_dir=`
  - Returns the character-card folder tree.
- `GET /library/cards/changes?game_dir=&path=`
  - Compares the direct AIS cards in the selected folder with the indexed file-size and nanosecond-modification-time signatures. Returns added, removed, and modified counts; it does not rebuild the card database.
- `GET /library/cards?game_dir=&path=&scope=&tag=`
  - Returns direct AIS card files under one card folder by default. `scope=library` together with a non-empty `tag` recursively returns every matching card under `UserData/chara`, excluding `navi`; tag comparison is case-insensitive. When the card database contains a current row for a returned file, each card also includes `dependency_count` and `missing_count`; unindexed cards return `null` for both fields.
- `GET /library/cards/detail?game_dir=&path=`
  - Returns one character-card profile plus parsed dependency information, resolved against indexed zipmods and mod items when available.
- `GET /library/cards/missing-mods?game_dir=&path=`
  - Compares one AIS character card's unresolved GUID dependencies—including missing local zipmods and local zipmods whose specific item is not indexed—with the read-only remote index at `backend/runtime/remote/remote_zipmod_index.sqlite`.
  - Returns GUID groups split into `available` and `unavailable`. Each available group includes one or more remote candidates; an unavailable group includes the reason it cannot be completed.
- `GET /library/cards/image?game_dir=&path=`
  - Serves the normalized `252 x 352` card preview used by the character grid.
  - Add `original=1` for the detail view to receive the card's visible PNG at its actual stored resolution. This response stops at the PNG `IEND` chunk and never transfers the appended character-card payload.
- `GET /library/clothes/tree?game_dir=`
  - Returns the independent `UserData/coordinate` clothes-card tree. The first response uses fast PNG candidate counts while a backend background job validates all coordinate PNG envelopes; the frontend refreshes this tree while `indexing=true`, then the `count` values become exact `is_valid=1` clothes-card counts. The candidate phase is intentionally not marked in the tree UI. These files are never inserted into the character-card SQLite index. Clothes-card validity is stored separately in the disposable runtime SQLite index `clothes_card_index.sqlite`.
- `GET /library/clothes?game_dir=&path=&offset=&limit=`
  - Returns a page of indexed-valid clothes cards in one coordinate folder. `offset` defaults to `0`; `limit` is optional and is capped at `240`. When the current page still has unknown or changed PNG candidates, `indexing=true`, `total=null`, `candidate_total` contains the PNG candidate count, and `has_more=true`; after the current directory is indexed, `total` becomes the exact valid clothes-card count and `total_is_candidate=false`.
  - List rows include only files whose size, `mtime_ns`, and parser version match an index row with `is_valid=1`. Unknown or changed files are checked in a bounded current-page window using lightweight envelope validation; invalid PNGs are stored as `is_valid=0` and are never returned. Once the directory is stable, ordering and pagination are executed by the SQLite index instead of rebuilding the complete page in Python. Full card metadata parsing remains deferred to `/library/clothes/detail`.
- `GET /library/clothes/detail?game_dir=&path=`
  - Returns one clothes-card envelope summary, clothing/accessory part summaries, UAR records, and KKEx plugin identifiers.
- `GET /library/clothes/image?game_dir=&path=`
  - Serves the normalized clothes-card preview without parsing the card payload first. Add `original=1` to return only the visible PNG before the appended clothes-card envelope. Standardized previews use the runtime `card_previews` cache and HTTP immutable caching.
- `GET /library/scene/tree?game_dir=`
  - Returns the `UserData/studio/scene` scene-card directory tree and direct PNG counts. The tree and files are kept separate from both the character-card database and the clothes-card index.
- `GET /library/scene?game_dir=&path=&offset=&limit=`
  - Returns a paginated list of PNG scene cards in one scene directory. The endpoint only enumerates files and returns lightweight metadata; it does not parse scene-card payloads. `limit` is capped at `240`.
- `GET /library/scene/detail?game_dir=&path=`
  - Returns one scene-card file's metadata after validating that the path remains inside `UserData/studio/scene`. On demand, parses the `StudioNEOV2` scene payload and scene-level `KKEx`/UniversalAutoResolver `mapInfoGUID`, `itemInfo`, and `patternInfo`, then resolves scene-map records against zipmods and scene-item/pattern records against indexed mod items. The response includes `scene_marker`, `plugin_ids`, `dependencies`, and `dependency_count`; embedded character-card data and unrelated scene object settings are not merged into this dependency list.
- `GET /library/scene/missing-mods?game_dir=&path=`
  - Compares one scene card's unresolved map/item/pattern GUID dependencies with the read-only remote index at `backend/runtime/remote/remote_zipmod_index.sqlite`. It returns GUID groups split into `available` and `unavailable`, including usage counts and scene dependency locations. A remote candidate means the manifest GUID is available; after installation, the scene detail endpoint rechecks the exact item/pattern `Slot` and `LocalSlot` against the local index.
- `GET /library/scene/image?game_dir=&path=`
  - Serves the normalized scene-card preview using the runtime `card_previews` cache at `320 x 180`. Add `original=1` to return only the visible PNG before any appended file data.

Direct mutation routes:

- `POST /plugins/toggle`
  - Body: `{ "game_dir": "D:\\HS2", "relative_path": "BepInEx/Plugins/Pack/Example.dll", "enabled": false }`
  - Enables or disables one plugin by renaming only its DLL: disabling replaces the `.dll` ending with `.dl_`, enabling restores `.dll`. Historical `.dll.disabled` and interim `.dll.dl_` files may be read and are migrated to `.dl_` when a disable operation is requested. The backend accepts only files inside a configured BepInEx plugin scan area, never overwrites an existing target, and returns the new `enabled` state and relative path. The game must be restarted for the change to take effect.
- `GET /game/special-settings?game_dir=`
  - Returns the start-page states for the BepInEx console and experimental Bleeding Edge Modpack mode.
- `POST /game/special-settings/toggle`
  - Body: `{ "game_dir": "D:\\HS2", "key": "console" | "experimental", "enabled": true }`.
  - `console` changes only `[Logging.Console] Enabled` in `BepInEx/config/BepInEx.cfg`. `experimental` creates/removes `BepInEx/LauncherEN/ilikebleeding.txt` and reversibly moves `Sideloader Modpack - Bleeding Edge` between `mods` and `mods.experimental`; existing destinations are never overwritten.
- `POST /tools/sims4/package-fbx`
  - Body: `{ "package_path": "E:\\Mods\\item.package", "target_dir": "D:\\Exports", "blender_executable_path": "D:\\Blender\\blender.exe" }`. `blender_executable_path` is optional; omitting it keeps static-FBX compatibility.
  - Reads one Sims 4 DBPF package, groups GEOM resources by instance ID, selects only the highest-vertex LOD0 resource in each group, and writes binary FBX 7.4 files into a new collision-safe output folder.
  - Scales source positions by `10.0` and declares the same Y-up, +Z-front, centimeter FBX convention used by the HS2 reference body. Blender consequently imports the mesh at the HS2 model's world scale and Z-up/-Y-front orientation.
  - Decodes every supported DXT5 RLE2 resource to an external PNG under `textures/`. Each FBX references the PNG whose resource index is nearest to its selected GEOM as the default diffuse swatch; all remaining swatches are retained for manual replacement.
  - Before FBX writing, combines matching diffuse-swatch alpha coverage and removes triangles whose primary UV is transparent in every matching swatch. Orphaned vertices, normals, and UV entries are compacted. Each export reports `removed_untextured_vertices`, `removed_untextured_triangles`, and `alpha_coverage_filter`; the response also includes `removed_untextured_triangle_count`.
  - Supports GEOM versions `0x05`, `0x0C`, `0x0D`, `0x0E`, and `0x0F`. It parses usage 4/5 vertex channels as four bone indices and four byte-normalized weights, accounts for the additional four-byte pre-TGI field in `0x0F`, reads the bone-hash palette, and compacts both channels together with vertices when alpha filtering removes faces.
  - When Blender is configured, launches it headlessly and imports only the bundled `ts4_reference_rig.fbx`. TS4 bone names are matched to GEOM hashes with lowercase FNV32 and used temporarily to bind the source weights. The `.blend` source and an HS2 skeleton template are not required at runtime.
  - The template starts in TS4 A-pose (measured shoulder-to-elbow drop about `44.9°`). Blender rotates both upper-arm chains and the evaluated mesh to the HS2 horizontal shoulder/elbow/wrist reference, then translates each complete arm chain horizontally toward the torso by `6%` of its upper-arm length. This preserves level arms without introducing an inward angle. It then removes the Armature, all vertex groups, and Armature modifiers before exporting only the mesh.
  - Returns `texture_count`, `t_pose_model_count`, `rigged_model_count: 0`, textures with absolute paths and dimensions, plus exported model paths and each model's `default_texture`. T-pose exports report `t_pose_baked: true`, `skin_data_removed: true`, `skeleton_bones: 0`, `weighted_bones: 0`, the source bone/group counts removed during processing, source/target arm-drop angles, and the proportional/actual arm-chain inward offset.
  - The final FBX contains no skeleton, skin weights, blend shapes, or animation while retaining the existing HS2-aligned scale, position, axes, materials, UVs, and external PNG texture references. Without Blender it returns an unposed static FBX with `t_pose_baked: false`.
- `POST /workbench/unity3d/assets`
  - Body: `{ "path": "D:\\path\\to\\resource.unity3d" }`.
  - Reads one local Unity3D with UnityPy and returns likely `MainData` GameObject candidates (preferring renderable roots) when the GameObject has an `Animator` component. For older files where the native Animator component cannot be exposed, it falls back to renderer hierarchy roots only; it never returns every bone GameObject. `game_object_candidates` follows the same rule, while `game_object_names` remains the complete name list for validation and `texture_candidates` contains `Texture2D` names. This is a read-only inspection route used before the Electron-owned CSV/resource write.
- `POST /workbench/unity3d/duplicate`
  - Body: `{ "path": "D:\\path\\to\\resource.unity3d", "selected_path_id": 123, "selected_asset_file": "CAB-...", "selected_name": "source_obj", "new_name": "copy_obj" }`.
  - Creates a derived Unity3D with the selected GameObject subtree duplicated and its local Mesh, Material, Texture2D, Texture3D, and Cubemap references cloned and remapped. Shared bones and shaders remain shared. The response returns the derived path, the new object identity, candidate lists, and duplicated object/resource counts; Electron performs the final project write-back.
- `POST /workbench/unity3d/preprocess`
  - Body: `{ "path": "D:\\path\\to\\resource.unity3d", "operation": "keep_selected", "selected_path_id": 123, "selected_asset_file": "CAB-...", "selected_name": "source_obj" }`.
  - For `keep_selected`, removes every GameObject outside the selected object's hierarchy, including independent Animator roots, and returns a disposable derived Unity3D. Electron uses this route because `AnimatorEditor` can only edit the currently opened Animator and cannot remove sibling Animator roots.
- `POST /workbench/unity3d/model-preview`
  - Body: `{ "unity3d_path": "D:\\path\\to\\resource.unity3d", "main_data": "item_obj", "kind": "1" }`.
  - Generates a disposable cached GLB for the named `MainData`, embedding referenced material textures and returning the same URL/half-model/mannequin shape used by the mod-library preview. The Electron IPC caller resolves `unity3d_path` inside the validated Workbench project before calling this route. The cache key includes the source path, size, modification time, `MainData`, and `Kind`, so resource or texture replacement produces a fresh preview.
- `POST /workbench/unity3d/thumbnail`
  - Body: `{ "path": "D:\\path\\to\\resource.unity3d", "texture": "preview" }`.
  - Reads a project-local Unity3D thumbnail without modifying the project and returns a PNG data URL. The Electron IPC caller validates the source path inside the Workbench project's `abdata` directory before calling this route.
- The legacy `/workbench/unity3d/unique-cab` route is not exposed. `/workbench/unity3d/duplicate`, `/workbench/unity3d/preprocess` and `/workbench/unity3d/import-texture` are backend-owned UnityPy mutations; other Workbench Unity3D writes still go through Electron IPC and the configured `SB3UtilityScript.exe`.
- `GET /workbench/template-items`
  - Query: `offset`, `limit`, optional `search`, `author`, and `kind`. The normal `author` filter is case-insensitive and matches author-name fragments; `未知作者` continues to mean items whose author is empty.
  - Returns paginated non-map database items whose `MainAB` points to a Unity3D with database status `in_mod` or `not_in_mod`. The response includes the source item name, mod, Unity3D reference, source `MainData`, and thumbnail URL when available. This is a read-only picker source for the workbench template editor.
- `POST /mods/zipmods/:id/repair-unity3d`
  - Body: `{ "path": "optional unity3d reference path" }`
  - Repairs one zipmod by moving a repairable item `MainAB` or external non-public `TexAB` Unity3D file from the game directory into the zipmod. Missing `TexAB` and `TexAB` under shared `abdata/chara/00`–`60` do not enter this repair flow. Thumbnail-only `ThumbAB` issues are repaired through thumbnail import, not this endpoint.
- `POST /library/cards/export-coordinate`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "name": "optional name", "output_dir": "optional custom directory" }`.
  - Extracts the selected character card's current `Coordinate` and converts coordinate-scoped KKEx data. When `output_dir` is empty, it writes under `UserData/coordinate/female` or `male`; otherwise it writes directly to the configured existing directory.
  - This is a single-card direct mutation. Existing files are never overwritten; a numeric suffix is added on filename collisions.
- `POST /library/cards/set-navi`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "slot": "navi | sitri" }`
  - Copies one validated character card to the selected navigation-card slot under `UserData/chara/navi`.
- `POST /library/cards/delete`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png" }`.
  - Validates one AIS character card, moves the PNG into `runtime/trash/cards`, removes its character-card index row and disposable preview cache, and returns the trash entry ID. The source file is not permanently deleted; restoration and permanent deletion are handled by the trash routes.
- `POST /mods/zipmods/:id/update-author`
  - Body: `{ "author": "Author name" }`
  - Updates one zipmod `manifest.xml` author.
- `POST /mods/zipmods/:id/manifest`
  - Body: `{ "fields": { "name": "...", "version": "...", "author": "..." } }`
  - Updates editable `manifest.xml` core fields. GUID is read-only.
- `POST /mods/zipmods/:id/cleanup-duplicates`
  - Body: optional `{ "duplicate_ids": [1, 2] }`
  - Cleans duplicate zipmod files for one primary zipmod GUID. When `duplicate_ids` is provided, cleanup is limited to those duplicate records.
- `POST /mods/zipmods/:id/promote-duplicate`
  - Body: `{ "duplicate_id": 1 }`
  - Deletes the current primary zipmod and promotes the selected duplicate file to the primary record when backend safety checks pass.
- `POST /mods/zipmods/:id/merge-duplicate`
  - Body: `{ "duplicate_id": 1 }`
  - Merges a selected duplicate into the current primary zipmod when backend comparison rules allow it.
- `POST /mods/zipmods/:id/delete`
  - Deletes one zipmod file and related database records.
- `POST /mods/items/:id/import-thumbnail`
  - Body: `{ "image_path": "D:\\path\\image.png" }` for an external PNG, or `{ "image_data": "data:image/png;base64,..." }` for a screenshot captured from the 3D preview. Screenshot payloads are validated as PNG, capped at 2 MB decoded size, and passed through a short-lived runtime file before using the same single-item import path.
  - Imports one thumbnail into the source zipmod and updates the item CSV fields.
- `POST /mods/items/:id/export-thumbnail`
  - Body: `{ "target_dir": "D:\\thumbs" }`
  - Exports the selected item's cached thumbnail PNG to a chosen directory.
- `POST /mods/items/:id/model-preview`
  - Reads the selected item's `MainAB` Unity3D resource with UnityPy, locates the GameObject named by CSV `MainData`, and converts only Renderer meshes below that object to a cached GLB. If `MainData` is empty or cannot be found, the converter explicitly falls back to the meshes in the complete MainAB; a matched MainData tree with no renderable mesh returns an error instead of showing unrelated objects. Standard color, base-color texture, normal texture, metallic, roughness, and basic transparency properties are mapped to glTF PBR; proprietary game shaders use this standard-material fallback. A textured proprietary material whose color alpha is zero is treated as texture-driven rather than fully invisible, while transparency present in the texture itself is preserved. This is a read-only, single-item operation; it does not modify the source zipmod.
- `POST /mods/items/:id/open-unity3d`
  - Prepares the selected item's `MainAB` Unity3D file for opening. If the file is inside the zipmod, the backend extracts a cache copy under the runtime directory; if it is only in the game `abdata`, the existing file is used. The renderer then passes the resulting path to Electron, which launches the configured SB3Utility executable with that path as its argument. This operation does not export or add skeleton/skin data.
- `POST /mods/items/:id/export-unity3d`
  - Body: `{ "target_path": "D:\\Exports\\item.unity3d" }`
  - Copies the selected item's `MainAB` Unity3D resource to the user-selected target file. Resources inside a zipmod are read from the archive; resources only in the game `abdata` are copied from the existing file. The source zipmod, CSV, game `abdata`, and database record are never modified. This is a single-object direct HTTP mutation with copy semantics, not a batch task.
- `POST /mods/items/:id/delete`
  - Deletes one item row from its source zipmod; if it was the final item, moves the now-empty zipmod into `runtime/trash/mods` before removing the zipmod database records.

## Game item probe bridge

The item browser uses the existing `StarManager.GameItemProbe` BepInEx plugin through a fixed backend proxy. The proxy only forwards these allow-listed loopback calls to `127.0.0.1:${STAR_MANAGER_GAME_ITEM_PROBE_PORT:-7880}`; it is not a general HTTP forwarder:

- `GET /game-item-probe/status`
  - Returns the plugin catalog status in `data`. When the plugin is not reachable, returns `ok: false` with `error_code: "probe_unavailable"`.
- `GET /game-item-probe/current`
  - Optional query: `game_dir=<selected HS2 directory>`; the renderer passes the current game directory so original-item thumbnails are resolved against the correct installation.
  - Returns the current character-maker identity and hair/clothing/face/body/accessory state in `data`; `data.characterName` is the name from `ChaFile.parameter.fullname`, while `data.characterFileName` remains the loaded character-card file name. Entries are exposed in `data.hairs`, `data.clothes`, `data.faces`, `data.bodies`, and `data.accessories`.
  - The backend enriches modded entries with `thumbnailUrl` when their resolver record uniquely matches one non-stale `mod_items` row by `GUID + CategoryNo + CSV slot`; native entries use `game_dir + CategoryNo + localSlot` to match `builtin_items`. Ambiguous mappings and missing thumbnail caches omit the image URL.
- `GET /game-item-probe/context`
  - Returns the current game context from the probe: `scene` is `editor`, `hscene`, or `none`; `editor` describes the current character-maker character; `hscene.females` and `hscene.males` list non-empty H-scene slots with `characterIndex`, `characterId`, `sex`, `characterName`, and `characterFileName`. Each character also contains a `current` object with the same `source`, identity, `coordinateName`, `hairs`, `clothes`, `faces`, `bodies`, and `accessories` fields as `/game-item-probe/current`. Counts are returned as `femaleCount`, `maleCount`, and `totalCount`. The backend enriches all nested current items with the same unique mod/builtin `thumbnailUrl` lookup used by `/game-item-probe/current`.
- `GET /game-item-probe/command?id=<command_id>`
  - Returns one queued command state in `data`; the plugin states are `queued`, `executing`, `succeeded`, `failed`, and `expired`.
- `POST /game-item-probe/apply`
  - Body for clothing: `{ "type": "clothes", "guid": "mod.guid", "categoryNo": 240, "slot": 1 }`. To target a character in an active H scene instead of the character maker, add `target: "hscene"`, `sex` (`0` male or `1` female), and `characterIndex` (the index in `HScene.GetMales()`/`GetFemales()`), for example `{ "type": "clothes", "target": "hscene", "sex": 1, "characterIndex": 0, "categoryNo": 240, "localSlot": 100008284 }`. `targetCharacterId` may be used instead of `characterIndex`; if both are supplied they must identify the same character. H-scene targets accept the same single-item `clothes`, `hair`, `face`, `body`, and `accessory` types as the editor target and call the corresponding native `ChaControl` update method without card/coordinate reload. `type: "card"` remains editor-only.
  - Body for hair: `{ "type": "hair", "guid": "mod.guid", "categoryNo": 300, "slot": 1, "hairSlotNo": 0 }`; the only valid mappings are `300→0` (HairBack), `301→1` (HairFront), `302→2` (HairSide), and `303→3` (HairOption).
  - Body for a face item: `{ "type": "face", "guid": "mod.face", "categoryNo": 317, "slot": 4, "facePartNo": 1 }`; face categories include `110`–`112`, `121`, `210`–`212`, `314`–`320`, `322`, and `323`. Only eye-specific categories `317` (pupil) and `318` (black pupil) require `facePartNo` (`0` left, `1` right).
  - Body for a body item: `{ "type": "body", "guid": "mod.body", "categoryNo": 313, "slot": 4, "bodyPartNo": 1 }`; male body categories are `8`, `131`–`133`, female body categories are `231`–`233`, `313`, `334`, and `335`. Only body-paint categories `8` and `313` require `bodyPartNo` (`0` paint layer 1, `1` paint layer 2); category `8` updates the male paint layout and `313` updates the female paint texture ID.
  - Body for an accessory: `{ "type": "accessory", "guid": "mod.guid", "categoryNo": 351, "slot": 1, "slotNo": 0 }`.
  - Native game items omit `guid` and use their indexed list ID as `localSlot`, for example `{ "type": "clothes", "categoryNo": 240, "localSlot": 1 }`; the plugin verifies that this `CategoryNo + localSlot` exists in the current `ChaListControl` before calling the game API. Native hair still requires the matching `hairSlotNo`, and native accessories still require `slotNo`.
  - The backend returns the plugin submission payload under `data`, for example `{ "accepted": true, "commandId": "...", "status": "queued" }`; the renderer polls the command route until it reaches a terminal state.

The renderer must only construct these payloads from a validated item row. For mod rows, `kind` is the `categoryNo` and `item_id` is the original CSV `slot`; neither is treated as a `localSlot`. For native rows, `item_id` is the indexed native list ID and is sent as `localSlot`. Hair rows require an explicit `hairSlotNo`, eye-specific face rows require an explicit `facePartNo`, and body-paint rows require an explicit `bodyPartNo`; the plugin rejects category/slot mismatches before resolving the item. The plugin resolves mod runtime local IDs and rejects ambiguous GUID/category/slot mappings. The normal item browser submits from its right-click action; assembly mode submits the same validated payload from a left click after a character slot has selected the matching `CategoryNo`. This is a single current-character mutation, not a task, batch endpoint, library write, or character-card save operation.

The probe port does not authenticate a game directory. The user must ensure that the HS2 process currently owning the probe port is the same installation selected in Star Manager; the backend cannot safely infer or enforce that association.

## Character card loading bridge

The character-card detail tool uses the existing `StarManager.GameItemProbe` plugin to load selected native card sections into the current HS2 character-maker character. `POST /game-card-loader/load` is a single-card direct mutation route, not a batch task:

```json
{
  "game_dir": "D:\\Games\\HoneySelect 2 DX",
  "path": "female/favorites/example.png",
  "face": true,
  "body": false,
  "hair": true,
  "parameter": false,
  "clothes": true,
  "accessory": false
}
```

The backend validates the selected game directory, the `female`/`male` card branch, the PNG and `AIS_Chara` marker, then forwards an allow-listed `type: "card"` request to the probe with `UserData/chara/...` path. The plugin calls `LoadFileLimited` on the initialized current `ChaFileControl`, preserves unselected coordinate children, synchronizes `nowCoordinate`, and submits the refresh through the native `ChaControl.Reload(...)` path while temporarily disabling `customLoadGCClear`; `Reload` internally starts the non-hiding `ReloadAsync(..., asyncFlags=false)` flow. The renderer polls the existing `/game-item-probe/command?id=...` route.

The route never forwards an arbitrary URL or path. It does not copy `status`, `gameinfo`, unknown plugin extensions, or game progress. Clothing and accessory are separate UI selections even though the native card coordinate envelope is read as one block; the plugin copies only the selected coordinate child. The card sex must match the current character-maker character, and the probe must be connected to the same game directory selected in Star Manager.

## Task API

Implemented in `apps/backend/app/bridge.py`; exposed by `POST /tasks`, `GET /tasks/:task_id`, and the remote-download control route `POST /tasks/:task_id/control`.

Submit shape:

```json
{
  "task_type": "build_mod_database",
  "payload": {}
}
```

Task state shape:

```json
{
  "id": "task id",
  "task_type": "build_mod_database",
  "status": "queued | running | paused | completed | failed | cancelled",
  "paused": false,
  "progress": 0,
  "title": "Task title",
  "messages": [],
  "error": "",
  "data": {},
  "phase": "preparing | download | install | completed | failed | cancelled",
  "phase_progress": 0,
  "download_speed_bps": 0,
  "downloaded_bytes": 0,
  "total_bytes": 0,
  "current_file": "",
  "phase_message": "",
  "cancel_requested": false,
  "created_at": 0,
  "updated_at": 0,
  "finished_at": 0
}
```

The renderer submits a task, then polls `GET /tasks/:task_id` until `status` is `completed`, `failed`, or `cancelled`. Remote character-card downloads may also be `paused`; the renderer uses the control route to pause, resume, or cancel them. A cancellation request remains visible as an active task until the worker has stopped and cleaned up its temporary download file.

Current task types:

- `check_game_dir`
  - Payload: `{ "game_dir": "D:\\HS2" }`
  - Data: `{ "is_valid": true, "game_dir": "..." }`
- `extract_mods`
  - Payload: `{ "game_dir": "...", "input_dir": "...", "output_dir": "...", "card_paths": [], "zipmod_extract_mode": "copy | move" }`
  - Extracts zipmods required by selected character cards.
- `sort_mods`
  - Payload: `{ "input_dir": "...", "output_dir": "...", "delete_empty": false }`
  - Sorts zipmods by manifest metadata.
- `build_mod_database`
  - Payload: `{ "game_dir": "D:\\HS2", "mode": "incremental | full" }`
  - Rebuilds the SQLite mod database, thumbnail cache, character-card database, and card preview cache. The frontend uses incremental mode for automatic small-change rebuilds.
  - On success, `data.timings` reports milliseconds for `builtin_resource_index_ms`, `zipmod_scan_ms`, `item_parse_ms`, `database_write_ms`, `character_card_database_ms`, and `total_ms`. The task messages also include one human-readable seconds summary.
- `index_single_zipmod`
  - Payload: `{ "game_dir": "D:\\HS2", "zipmod_path": "D:\\HS2\\mods\\Author\\mod.zipmod" }`
  - Indexes only the specified zipmod and its item rows. It does not scan, add, remove, or reparse any other zipmod. After indexing, it incrementally relinks only character cards that depend on the affected GUIDs; the workbench uses this task immediately after packaging. The task result includes `card_stats` when a card relink was performed.
- `download_card_missing_mods`
  - Payload: `{ "game_dir": "D:\\HS2", "remote_ids": [123, 456] }`. The list may contain at most 100 candidates and must contain no more than one candidate for each GUID.
  - Downloads selected files from the indexed `https://sideload.betterrepack.com/download/AISHS2/` tree into `mods/Remote/`, writing a temporary `.part` file first. Each file is checked for size, ZIP CRC, and manifest GUID before being atomically installed. Existing valid files are also passed through single-zipmod indexing so a missing local database row can be repaired without a full rebuild.
  - Up to 3 selected files are downloaded concurrently. The task then enters a separate installation phase, which runs single-zipmod indexing in order and finally relinks character cards depending on the affected GUIDs when they are indexed. Scene cards do not need a persistent dependency-table relink: their next detail request resolves against the refreshed local mod database. During the download phase, task state exposes `phase_progress`, `downloaded_bytes`, `total_bytes`, and `download_speed_bps` (bytes per second; the frontend displays MB/s). During installation, `phase_progress` reports installation progress and download speed is zero. The task result exposes the GUIDs in `affected_mod_guids` and, when applicable, the relink result in `card_stats`. DLLs and scripts inside the archive are never executed. Failed downloads are reported in task `data.failures` and their temporary files are removed. A user cancellation stops the task with status `cancelled` and removes incomplete `.part` files; files already atomically installed before cancellation are not rolled back.
- `import_external_zipmods`
  - Payload: `{ "game_dir": "D:\\HS2", "source_dir": "D:\\Downloads\\mods" }`
  - Scans external `*.zipmod` and `*.zip` files. A `.zip` is accepted only when it is a readable archive with a root `manifest.xml` containing a GUID and actual `abdata/` content; accepted files are copied into `mods/Imported` with the target suffix normalized to `.zipmod`. The original external `.zip` is not renamed or deleted.
  - Valid candidates rebuild the index, undergo duplicate GUID analysis, and keep the best candidate by the existing duplicate-completeness policy. Existing game files are only replaced when duplicate analysis marks the imported candidate as safer/better. Invalid `.zip` files are reported in `data.invalid` with `status: "invalid_zipmod_structure"` and are not copied.
  - Result counters include `zip_scanned_count`, `zip_recognized_count`, `zip_renamed_count`, and the existing `scanned_count` (recognized zipmod candidates only). `zip_renamed_count` counts accepted `.zip` files whose imported copy was written with a `.zipmod` suffix.
  - Before indexing copied zipmods, recursively searches `abdata` directories under the import source folder. When a copied zipmod references a missing `abdata/**/*.unity3d`, the matching loose unity3d file is moved into the zipmod at that referenced path.
  - Also scans external `*.png` files. `【AIS_Chara】` character cards are copied into `UserData/chara/female/imported`, while `【AIS_Clothes】` clothes cards are copied into `UserData/coordinate/female/imoprted`; ordinary PNG images are skipped. The task result reports them separately through `card_imported_count` / `imported_cards` and `coordinate_imported_count` / `imported_coordinates`.
- `build_card_database`
  - Payload: `{ "game_dir": "D:\\HS2", "mode": "incremental | full" }`
  - Rebuilds only the character-card database and card preview cache.
- `bulk_export_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2], "target_dir": "...", "mode": "copy | move" }`
  - Exports selected zipmods preserving the original mods tree, and also exports repairable external item main `.unity3d` files from game `abdata` under their original `abdata/...` paths.
- `export_character_dependency_package`
  - Payload: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "target_dir": "...", "compress": true, "dependency_types": ["face", "hair", "body", "clothes", "accessory"] }`
  - Generates one portable dependency package for a character card. `dependency_types` independently selects any combination of face/features, hair, body/skin, clothes, and accessories; an empty array exports only the card and manifest, while omitting the field keeps all five types for backward compatibility. Dependencies are classified from resolver `Property`, then `CategoryNo`, then matched item Kind. The package mirrors game-root paths under `UserData/chara`, `mods`, and `abdata`, includes a UTF-8 JSON dependency manifest with selection/count metadata, deduplicates selected zipmods by database id, and reports missing GUIDs and copy failures only for selected types. `compress=true` produces a ZIP; otherwise it produces a folder. Source files are always copied.
- `bulk_organize_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2], "target_dir": "..." }`
  - Copies selected zipmods into author-named folders.
- `organize_all_zipmods_by_author`
  - Payload: `{ "game_dir": "D:\\HS2" }`
  - Moves every `*.zipmod` below the current game `mods` directory into `mods/<author>/`. Missing authors use `未知作者`, invalid Windows path characters are replaced, and filename collisions receive a numeric suffix instead of overwriting files. After moving files, empty directories below `mods` are deleted without deleting the `mods` root, then the task refreshes the mod database.
- `bulk_repair_zipmods_unity3d`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Repairs repairable item Unity3D issues for selected zipmods. The task processes `.unity3d` references from both `MainAB` and `TexAB` when the referenced file is present only in the game `abdata`. The backend groups references by game-directory source path; sources needed by multiple selected zipmods are copied into each zipmod and kept in game `abdata`, while sources needed by only one selected zipmod may be moved into that zipmod.
- `bulk_cleanup_duplicate_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Runs duplicate analysis for selected primary zipmods, deletes only duplicate files that are safe to remove, and skips candidates that appear newer, more complete, contain unique item records, or have newer CSV-referenced `.unity3d` members than the primary zipmod. Only `.unity3d` files referenced by parsed CSV item rows participate in this comparison; unreferenced `.unity3d` members are ignored. File size is displayed for review but does not block cleanup by itself.
- `bulk_delete_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Moves selected zipmod files into `runtime/trash/mods` and removes related database records; the files remain recoverable until permanently deleted from the trash.
- `bulk_delete_character_cards`
  - Payload: `{ "game_dir": "D:\\HS2", "card_paths": ["female/card-a.png", "female/card-b.png"] }`
  - Moves selected AIS character-card PNG files into `runtime/trash/cards` after re-validating that every relative path remains inside `UserData/chara` and still points to an AIS card. Related character-card index rows, dependency rows, and preview caches are removed; the files remain restorable from the trash.
- `bulk_add_character_card_tags`
  - Payload: `{ "game_dir": "D:\\HS2", "card_paths": ["female/card-a.png", "female/card-b.png"], "tags": ["礼服", "粉发"] }`
  - Appends the selected tags to every validated card without replacing existing tags. Each successful write updates the card's `star.manager.cardmetadata.tags` plus its SQLite tag cache; per-card validation failures are reported in task data.
- `bulk_move_character_cards`
  - Payload: `{ "game_dir": "D:\\HS2", "card_paths": ["female/Old/card-a.png"], "target_directory": "female/New" }`
  - Moves selected AIS character cards without overwriting existing files. Every source and target is revalidated under `UserData/chara/female` or `UserData/chara/male`, and the source and target gender branches must match. Successful moves update character-card index paths while retaining dependency rows.

- `bulk_update_zipmod_authors`
  - Payload: `{ "zipmod_ids": [1, 2], "author": "Author name" }`
  - Updates `manifest.xml` author for selected zipmods.
- `bulk_apply_item_thumbnail`
  - Payload: `{ "source_item_id": 1, "source_image_path": "D:\\cache\\thumb.png", "target_item_ids": [2, 3] }`
  - Applies the selected source item's cached thumbnail PNG to specifically selected target items missing thumbnails. This reuses the single-item thumbnail import path and updates each target source zipmod/CSV.
- `bulk_delete_error_items`
  - Payload: `{ "search": "", "kind": "", "author": "", "usage": "" }`
  - Deletes every item matching the current item-browser filters with `status=error`. The task caps one run at 1000 items, re-resolves each item before deletion, and uses the same write-back behavior as single-item deletion.

### Removed task type: `search_cards`

- Background: `search_cards` was a legacy wrapper around the AIS-card scanning helper. The current renderer loads the card library through `/library/cards/tree` and passes selected card paths directly to `extract_mods`, so it had no internal submission path.
- Root cause: the task remained registered in the task bridge and documentation after the renderer flow moved to direct card-library routes and explicit selections.
- Change: removed the task from `SUPPORTED_TASK_TYPES`, removed its dispatch branch and renderer-only result handling, and removed it from the task documentation. The shared `search_ais_cards()` helper remains because `extract_mods` still uses it as a fallback when no card paths are supplied.
- Verification: runtime source search contains no `search_cards` task reference; the frontend still submits `extract_mods`, and its backend fallback still resolves through `search_ais_cards()`.
- Scope: callers that manually submit `POST /tasks` with `task_type: "search_cards"` now receive the normal unsupported-task response. No current renderer flow is affected.

Single-card profile mutation:

- `POST /library/cards/update-profile`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "profile": { "fullname": "Name", "personality": 1, "birthMonth": 4, "birthDay": 10, "voiceRate": 0.5, "futanari": false } }`
  - Rewrites the card's `Parameter` block and mirrors `personality` into `Parameter2` when present. The PNG preview and all unrelated card blocks are preserved. `sex` is intentionally read-only because changing it without converting all sex-specific blocks would produce an internally inconsistent card.

Single-card cover mutation:

- `POST /library/cards/replace-cover`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "image_path": "D:\\Pictures\\cover.png", "crop": { "left": 0.1, "top": 0.0, "width": 0.7159, "height": 1.0 } }`. Crop coordinates are normalized to the source image.
  - Crops the selected local image to the fixed `63:88` cover ratio while retaining the selected region's native pixel resolution; it does not force `252 x 352`. When `crop` is omitted, the backend uses a centered native-resolution crop. It atomically replaces only the visible PNG portion and preserves the appended character-card payload byte-for-byte.

Single-card favorite mutation:

- `POST /library/cards/set-favorite`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "favorite": true }`
  - Stores the favorite state in the registered `star.manager.cardmetadata` entry of the card's `KKEx` block. Removing a favorite deletes only the `favorite` key and preserves ratings plus unknown/future Star Manager fields.

Single-card rating mutation:

- `POST /library/cards/set-rating`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "rating": 4 }`
  - Stores an integer from `1` to `5` as `rating` in the registered `star.manager.cardmetadata` entry. The mutation preserves the favorite state, other plugin entries, and unknown/future Star Manager fields.

Single-card tag routes:

- `GET /library/cards/tags?game_dir=`
  - Returns the distinct Star Manager tags for reuse in the tag picker. The normal path reads `character_cards.tags_json` from SQLite; an upgraded database performs one recursive PNG backfill only when the cache marker is absent.
- `POST /library/cards/set-tags`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "tags": ["粉发", "礼服"] }`
  - Replaces one card's `star.manager.cardmetadata.tags` string array. Tags are trimmed and case-insensitively deduplicated; one card accepts at most 12 tags and each tag accepts at most 24 characters. An empty array removes only the `tags` key.

Single-directory mutations:

- `POST /library/cards/folders/create`
  - Body: `{ "game_dir": "D:\\HS2", "parent_path": "female/Collection", "name": "New folder" }`
  - Creates one empty child directory. The parent must be inside the `female` or `male` character-card branch, and Windows-invalid or reserved names are rejected.
- `POST /library/cards/folders/rename`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/Collection", "name": "Favorites" }`
  - Renames one directory without moving it to a different parent. The `female` and `male` roots cannot be renamed; indexed card paths below the renamed directory are updated.

## Frontend display expectations

- The top global progress bar is reserved for `build_mod_database`.
- The overview page recent-task list displays every task, including batch mod operations.
- Recent-task rows are clickable. The renderer keeps the latest task snapshot in memory and opens a detail drawer showing status, result metrics, timing summary, timestamps, and task messages; this does not add a persistent task-history endpoint.
- Direct HTTP mutations should update their local busy state and then refresh affected lists or diagnostics.
- Task mutations should use `submitTask(...)`, let polling update logs/recent tasks, then refresh affected lists after completion.

## Local achievement routes

- `GET /achievements`: evaluates static library milestones and returns all local achievement progress plus preferences.
- `POST /achievements/preferences`: updates `enabled`, `notifications`, or `hide_locked` preferences.
- `POST /achievements/reset`: clears achievement progress and event history without changing indexed resources.

Successful duplicate-cleanup operations record released bytes. Successful thumbnail and Unity3D repairs record repaired-resource counts. Event keys are idempotent so a completed task cannot be counted twice.
