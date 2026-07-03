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
- `selectImageFile(title)`: open a native image picker.
- `promptText(title, message, defaultValue)`: open a native text prompt.
- `showItemInFolder(filePath)`: reveal a file in the system file manager.
- `launchGameExecutable(launchType, gameDir)`: launch `HoneySelect2.exe`, `StudioNEOV2.exe`, or `HoneySelect2VR.exe`.
- `loadSettings()`: load persisted app settings.
- `saveSettings(settings)`: save persisted app settings.
- `backendRequest(route, options)`: call the Python HTTP backend.
- `backendBaseUrl`: backend base URL, defaulting to `http://127.0.0.1:8765`.

## Mutation routing rule

- Single file or single object operations use direct HTTP API routes.
- Batch operations use `/tasks` and report progress through the task bridge.
- Do not add new bulk direct-HTTP mutation endpoints. Add a task type in `apps/backend/app/bridge.py`.

Examples:

- Direct HTTP: repair one zipmod, update one zipmod author, delete one zipmod, import one item thumbnail, delete one item.
- Task: export selected zipmods, organize selected zipmods, bulk repair unity3d, bulk update zipmod authors, rebuild the mod database, character-card dependency extraction.

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
- `GET /mods/zipmods?offset=&limit=&author=&status=&usage=`
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
- `GET /library/cards/tree?game_dir=`
  - Returns the character-card folder tree.
- `GET /library/cards?game_dir=&path=`
  - Returns direct AIS card files under one card folder.
- `GET /library/cards/detail?game_dir=&path=`
  - Returns one character-card profile plus parsed dependency information, resolved against indexed zipmods and mod items when available.
- `GET /library/cards/image?game_dir=&path=`
  - Serves a normalized card preview or original card PNG.

Direct mutation routes:

- `POST /mods/zipmods/:id/repair-unity3d`
  - Body: `{ "path": "optional unity3d reference path" }`
  - Repairs one zipmod by moving repairable item main Unity3D files from the game directory into the zipmod. Thumbnail-only `ThumbAB` issues are repaired through thumbnail import, not this endpoint.
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
  - Body: `{ "image_path": "D:\\path\\image.png" }`
  - Imports one thumbnail into the source zipmod and updates the item CSV fields.
- `POST /mods/items/:id/export-thumbnail`
  - Body: `{ "target_dir": "D:\\thumbs" }`
  - Exports the selected item's cached thumbnail PNG to a chosen directory.
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
- `build_card_database`
  - Payload: `{ "game_dir": "D:\\HS2", "mode": "incremental | full" }`
  - Rebuilds only the character-card database and card preview cache.
- `bulk_export_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2], "target_dir": "...", "mode": "copy | move" }`
  - Exports selected zipmods preserving the original mods tree, and also exports repairable external item main `.unity3d` files from game `abdata` under their original `abdata/...` paths.
- `bulk_organize_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2], "target_dir": "..." }`
  - Copies selected zipmods into author-named folders.
- `bulk_repair_zipmods_unity3d`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Repairs repairable item main Unity3D issues for selected zipmods. The backend first groups repairable `MainAB` `.unity3d` references by game-directory source path; sources needed by multiple selected zipmods are copied into each zipmod and kept in game `abdata`, while sources needed by only one selected zipmod may be moved into that zipmod.
- `bulk_cleanup_duplicate_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Runs duplicate analysis for selected primary zipmods, deletes only duplicate files that are safe to remove, and skips candidates that appear newer, more complete, contain unique item records, or have newer CSV-referenced `.unity3d` members than the primary zipmod. Only `.unity3d` files referenced by parsed CSV item rows participate in this comparison; unreferenced `.unity3d` members are ignored. File size is displayed for review but does not block cleanup by itself.
- `bulk_delete_zipmods`
  - Payload: `{ "zipmod_ids": [1, 2] }`
  - Deletes selected zipmod files and removes related database records.
- `bulk_update_zipmod_authors`
  - Payload: `{ "zipmod_ids": [1, 2], "author": "Author name" }`
  - Updates `manifest.xml` author for selected zipmods.
- `bulk_apply_item_thumbnail`
  - Payload: `{ "source_item_id": 1, "source_image_path": "D:\\cache\\thumb.png", "target_item_ids": [2, 3] }`
  - Applies the selected source item's cached thumbnail PNG to specifically selected target items missing thumbnails. This reuses the single-item thumbnail import path and updates each target source zipmod/CSV.
- `bulk_delete_error_items`
  - Payload: `{ "search": "", "kind": "", "author": "", "usage": "" }`
  - Deletes every item matching the current item-browser filters with `status=error`. The task caps one run at 1000 items, re-resolves each item before deletion, and uses the same write-back behavior as single-item deletion.

## Frontend display expectations

- The top global progress bar is reserved for `build_mod_database`.
- The overview page recent-task list displays every task, including batch mod operations.
- Direct HTTP mutations should update their local busy state and then refresh affected lists or diagnostics.
- Task mutations should use `submitTask(...)`, let polling update logs/recent tasks, then refresh affected lists after completion.
