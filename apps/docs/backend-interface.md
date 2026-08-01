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
- `selectPackageFile(title)`: open a native file picker limited to Sims 4 `.package` files.
- `selectImageFile(title)`: open a native image picker.
- `selectImageForCrop(title)`: open a native image picker for character-card cover replacement.
- `selectBlenderExecutable(title)`: select a Windows `blender.exe` executable for persistent Workbench integration.
- `promptText(title, message, defaultValue)`: open a native text prompt.
- `showItemInFolder(filePath)`: reveal a file in the system file manager.
- `openDirectory(directoryPath)`: open an existing directory in the system file manager.
- `launchGameExecutable(launchType, gameDir)`: launch `HoneySelect2.exe`, `StudioNEOV2.exe`, or `HoneySelect2VR.exe`.
- `openFbxInBlender(blenderPath, fbxPath)`: validate the configured Blender executable and one `.fbx` file, then launch Blender with a Python FBX import expression and the FBX directory as its working directory.
- `loadSettings()`: load persisted app settings.
- `saveSettings(settings)`: save persisted app settings, including `blenderExecutablePath`.
- `backendRequest(route, options)`: call the Python HTTP backend.
- `backendBaseUrl`: backend base URL, defaulting to `http://127.0.0.1:8765`.

## Mutation routing rule

- Single file or single object operations use direct HTTP API routes.
- Batch operations use `/tasks` and report progress through the task bridge.
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
- `GET /mods/database`
  - Returns mod database status and summary counts.
  - Zipmod summary counts include `zipmod_error_count` for red error rows and `zipmod_warning_count` for yellow warning rows. Duplicate GUIDs are still counted in `duplicate_guid_count` for diagnostics, but the top mod-library summary displays warning/error separately rather than a standalone duplicate count.
- `GET /mods/database/changes?game_dir=`
  - Compares indexed database records with current zipmod and character-card files under the selected game directory.
  - Returns whether a rebuild is needed, change counts, and whether an automatic incremental rebuild is recommended.
- `GET /cards/database`
  - Returns character-card database status and summary counts.
- `GET /plugins?game_dir=&search=&category=&offset=&limit=`
  - Recursively scans `BepInEx/Plugins`, `BepInEx/patchers`, and `BepInEx/core` without loading or executing DLL files. It returns DLLs with a successfully parsed `BepInPlugin` attribute and non-empty plugin GUID; ordinary dependency assemblies without that GUID are excluded.
  - Returns assembly identity/version, BepInEx plugin GUID/name/version, functional description and its source/confidence/evidence, dependencies, process restrictions, incompatibilities, assembly references, file metadata, diagnostics, and summary counts. Descriptions prefer `AssemblyDescription`, then correlate matching `config/*.cfg` settings with `Translation/**/*.txt` labels; known-plugin and name-based descriptions are marked separately.
  - The plugin library contains only DLLs with a valid `BepInPlugin` GUID. The maximum page size is 1000.
  - Results are cached in the shared SQLite database. A fingerprint of plugin DLLs, config files, and translation files invalidates stale entries automatically. Pass `refresh=1` to force a complete rescan.
- `GET /mods/zipmods?offset=&limit=&author=&status=&usage=&zipmod_id=`
  - Returns paged zipmod rows. `status` may be `normal`, `abnormal`, `warning`, `error`, `manifest_author`, `read_error`, `unity3d_missing`, `unity3d_in_game`, `thumbnail`, `duplicate_zipmod`, or empty. `usage` may be `used`, `unused`, or empty, based on character-card dependencies.
  - `normal`: `scan_status = ok`, author is present, no duplicate GUID, no thumbnail issue items, and `unity3d_status` is not `missing`, `in_game`, or `error`.
  - `warning`: empty author, external main Unity3D resources in game `abdata`, duplicate GUID, or thumbnail issue items.
  - `error`: missing manifest, missing item main `MainAB` Unity3D resource, item main Unity3D error, or `unity3d_missing_count > 0`.
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
- `GET /mods/items?offset=&limit=&zipmod_id=&search=&kind=&author=&status=&usage=`
  - Returns paged mod item rows. `status` may be `ready`, `error`, `thumb`, or empty. `error` covers items with parse errors or missing Unity3D files. `usage` may be `used`, `unused`, or empty, based on character-card dependencies.
  - Item display status is derived in the renderer: `error` for parse errors or `unity3d_status` `missing/error`; `thumb` for parsed items whose main Unity3D resource is usable but whose `thumbnail_status` is not `ready` / `ok`; `ready` when both the item and thumbnail are usable.
  - Item `unity3d_status` is based on the main resource referenced by `MainAB`. `ThumbAB` only affects `unity3d_status` when it points to the same `.unity3d` as `MainAB` and thumbnail parsing proves that file is not a usable Unity resource.
- `GET /mods/items/filters`
  - Returns item filter options.
- `GET /mods/thumbnails?path=`
  - Serves a cached thumbnail file from the backend thumbnail cache.
- `GET /mods/models/:file.glb`
  - Serves a generated GLB from the runtime model-preview cache. Model files are generated on demand and are disposable runtime data.
- `GET /mods/mannequin/body.fbx`
  - Serves the bundled mannequin FBX used as the clothing preview reference model.
- `GET /library/cards/tree?game_dir=`
  - Returns the character-card folder tree.
- `GET /library/cards?game_dir=&path=&scope=&tag=`
  - Returns direct AIS card files under one card folder by default. `scope=library` together with a non-empty `tag` recursively returns every matching card under `UserData/chara`, excluding `navi`; tag comparison is case-insensitive. When the card database contains a current row for a returned file, each card also includes `dependency_count` and `missing_count`; unindexed cards return `null` for both fields.
- `GET /library/cards/detail?game_dir=&path=`
  - Returns one character-card profile plus parsed dependency information, resolved against indexed zipmods and mod items when available.
- `GET /library/cards/image?game_dir=&path=`
  - Serves the normalized `252 x 352` card preview used by the character grid.
  - Add `original=1` for the detail view to receive the card's visible PNG at its actual stored resolution. This response stops at the PNG `IEND` chunk and never transfers the appended character-card payload.

Direct mutation routes:

- `POST /tools/sims4/package-fbx`
  - Body: `{ "package_path": "E:\\Mods\\item.package", "target_dir": "D:\\Exports", "blender_executable_path": "D:\\Blender\\blender.exe" }`. `blender_executable_path` is optional; omitting it keeps static-FBX compatibility.
  - Reads one Sims 4 DBPF package, groups GEOM resources by instance ID, selects only the highest-vertex LOD0 resource in each group, and writes binary FBX 7.4 files into a new collision-safe output folder.
  - Scales source positions by `10.0` and declares the same Y-up, +Z-front, centimeter FBX convention used by the HS2 reference body. Blender consequently imports the mesh at the HS2 model's world scale and Z-up/-Y-front orientation.
  - Decodes every supported DXT5 RLE2 resource to an external PNG under `textures/`. Each FBX references the PNG whose resource index is nearest to its selected GEOM as the default diffuse swatch; all remaining swatches are retained for manual replacement.
  - Before FBX writing, combines matching diffuse-swatch alpha coverage and removes triangles whose primary UV is transparent in every matching swatch. Orphaned vertices, normals, and UV entries are compacted. Each export reports `removed_untextured_vertices`, `removed_untextured_triangles`, and `alpha_coverage_filter`; the response also includes `removed_untextured_triangle_count`.
  - Parses GEOM usage 4/5 vertex channels as four bone indices and four byte-normalized weights, reads the GEOM bone-hash palette, and compacts both channels together with vertices when alpha filtering removes faces.
  - When Blender is configured, launches it headlessly and imports only the bundled `ts4_reference_rig.fbx`. TS4 bone names are matched to GEOM hashes with lowercase FNV32 and used temporarily to bind the source weights. The `.blend` source and an HS2 skeleton template are not required at runtime.
  - The template starts in TS4 A-pose (measured shoulder-to-elbow drop about `44.9°`). Blender rotates both upper-arm chains and the evaluated mesh to the HS2 horizontal shoulder/elbow/wrist reference and bakes the deformed mesh into T-pose. It then removes the Armature, all vertex groups, and Armature modifiers before exporting only the mesh.
  - Returns `texture_count`, `t_pose_model_count`, `rigged_model_count: 0`, textures with absolute paths and dimensions, plus exported model paths and each model's `default_texture`. T-pose exports report `t_pose_baked: true`, `skin_data_removed: true`, `skeleton_bones: 0`, `weighted_bones: 0`, the source bone/group counts removed during processing, and source/target arm-drop angles.
  - The final FBX contains no skeleton, skin weights, blend shapes, or animation while retaining the existing HS2-aligned scale, position, axes, materials, UVs, and external PNG texture references. Without Blender it returns an unposed static FBX with `t_pose_baked: false`.
- `POST /mods/zipmods/:id/repair-unity3d`
  - Body: `{ "path": "optional unity3d reference path" }`
  - Repairs one zipmod by moving repairable item main Unity3D files from the game directory into the zipmod. Thumbnail-only `ThumbAB` issues are repaired through thumbnail import, not this endpoint.
- `POST /library/cards/export-coordinate`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "name": "optional name", "output_dir": "optional custom directory" }`.
  - Extracts the selected character card's current `Coordinate` and converts coordinate-scoped KKEx data. When `output_dir` is empty, it writes under `UserData/coordinate/female` or `male`; otherwise it writes directly to the configured existing directory.
  - This is a single-card direct mutation. Existing files are never overwritten; a numeric suffix is added on filename collisions.
- `POST /library/cards/set-navi`
  - Body: `{ "game_dir": "D:\\HS2", "path": "female/card.png", "slot": "navi | sitri" }`
  - Copies one validated character card to the selected navigation-card slot under `UserData/chara/navi`.
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
- `POST /mods/items/:id/export-fbx`
  - Body: `{ "target_dir": "D:\\Exports" }`. Exports the CSV `MainData`-selected static meshes as an ASCII FBX 7.4 file, with material colors, UVs, normals, and extracted texture PNGs in a sibling `textures` folder. The current exporter does not include bones, skin weights, blend shapes, or animation. A new collision-safe output folder is created for every export.
- `POST /mods/items/:id/delete`
  - Deletes one item row from its source zipmod; if it was the final item, deletes the zipmod.

## Task API

Implemented in `apps/backend/app/bridge.py`; exposed by `POST /tasks` and `GET /tasks/:task_id`.

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
  "status": "queued | running | completed | failed",
  "progress": 0,
  "title": "Task title",
  "messages": [],
  "error": "",
  "data": {},
  "created_at": 0,
  "updated_at": 0
}
```

The renderer submits a task, then polls `GET /tasks/:task_id` until `status` is `completed` or `failed`.

Current task types:

- `check_game_dir`
  - Payload: `{ "game_dir": "D:\\HS2" }`
  - Data: `{ "is_valid": true, "game_dir": "..." }`
- `search_cards`
  - Payload: `{ "input_dir": "D:\\HS2\\UserData\\chara" }`
  - Data: card path list and card count.
- `extract_mods`
  - Payload: `{ "game_dir": "...", "input_dir": "...", "output_dir": "...", "card_paths": [], "zipmod_extract_mode": "copy | move" }`
  - Extracts zipmods required by selected character cards.
- `sort_mods`
  - Payload: `{ "input_dir": "...", "output_dir": "...", "delete_empty": false }`
  - Sorts zipmods by manifest metadata.
- `build_mod_database`
  - Payload: `{ "game_dir": "D:\\HS2", "mode": "incremental | full" }`
  - Rebuilds the SQLite mod database, thumbnail cache, character-card database, and card preview cache. The frontend uses incremental mode for automatic small-change rebuilds.
- `import_external_zipmods`
  - Payload: `{ "game_dir": "D:\\HS2", "source_dir": "D:\\Downloads\\mods" }`
  - Scans all external `*.zipmod` files, copies valid candidates into `mods/Imported`, rebuilds the index, analyzes duplicate GUIDs, and keeps the best candidate by the existing duplicate-completeness policy. Existing game files are only replaced when duplicate analysis marks the imported candidate as safer/better.
  - Before indexing copied zipmods, recursively searches `abdata` directories under the import source folder. When a copied zipmod references a missing `abdata/**/*.unity3d`, the matching loose unity3d file is moved into the zipmod at that referenced path.
  - Also scans external `*.png` files. `【AIS_Chara】` character cards are copied into `UserData/chara/female`, while `【AIS_Clothes】` clothes cards are copied into `UserData/coordinate/female/imoprted`; ordinary PNG images are skipped. The task result reports them separately through `card_imported_count` / `imported_cards` and `coordinate_imported_count` / `imported_coordinates`.
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
  - Repairs repairable item main Unity3D issues for selected zipmods. The backend first groups repairable `MainAB` `.unity3d` references by game-directory source path; sources needed by multiple selected zipmods are copied into each zipmod and kept in game `abdata`, while sources needed by only one selected zipmod may be moved into that zipmod.
- `bulk_cleanup_duplicate_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Runs duplicate analysis for selected primary zipmods, deletes only duplicate files that are safe to remove, and skips candidates that appear newer, more complete, contain unique item records, or have newer CSV-referenced `.unity3d` members than the primary zipmod. Only `.unity3d` files referenced by parsed CSV item rows participate in this comparison; unreferenced `.unity3d` members are ignored. File size is displayed for review but does not block cleanup by itself.
- `bulk_delete_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Deletes selected zipmod files and removes related database records.
- `bulk_delete_character_cards`
  - Payload: `{ "game_dir": "D:\\HS2", "card_paths": ["female/card-a.png", "female/card-b.png"] }`
  - Permanently deletes selected AIS character-card PNG files after re-validating that every relative path remains inside `UserData/chara` and still points to an AIS card. Related character-card index rows, dependency rows, and preview caches are removed.
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
- Direct HTTP mutations should update their local busy state and then refresh affected lists or diagnostics.
- Task mutations should use `submitTask(...)`, let polling update logs/recent tasks, then refresh affected lists after completion.

## Local achievement routes

- `GET /achievements`: evaluates static library milestones and returns all local achievement progress plus preferences.
- `POST /achievements/preferences`: updates `enabled`, `notifications`, or `hide_locked` preferences.
- `POST /achievements/reset`: clears achievement progress and event history without changing indexed resources.

Successful duplicate-cleanup operations record released bytes. Successful thumbnail and Unity3D repairs record repaired-resource counts. Event keys are idempotent so a completed task cannot be counted twice.
