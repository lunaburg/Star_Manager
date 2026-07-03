# Star_Manager Desktop App

This directory contains the maintained Star_Manager desktop application: an Electron shell, a Vue renderer, and a local Python HTTP backend.

Star_Manager is an HS2 / AIS resource manager. It indexes a selected game directory, then presents the data as a local resource library for character cards, zipmods, mod items, thumbnails, diagnostics, and maintenance workflows.

## Product Scope

Main managed resources:

- `zipmod` archives under `mods/**/*.zipmod`, usually containing `manifest.xml`, `abdata/list/**/*.csv`, thumbnails, and `.unity3d` resources.
- AIS/HS2 character-card PNG files under `UserData/chara`.
- `.unity3d` resources, either inside zipmods or as fallback files in the game `abdata` tree.

Current app views:

- Start: game directory setup and launch actions for HS2, Studio, and VR executables.
- Overview: selected-directory status, library health, suggested actions, and recent tasks.
- Characters: card-folder tree, AIS card previews, card detail, and parsed dependency information.
- Mods: item browsing, zipmod browsing, filters, detail drawer, diagnostics, and direct/batch maintenance actions.
- Logs: task progress and runtime messages.

## Structure

```text
apps/
|-- electron/                 # Electron main process and preload bridge
|-- src/                      # Vue renderer and view components
|-- backend/app/              # Local Python HTTP service entry and task bridge
|-- backend/star_manager/     # Python business package
|-- backend/tests/            # Python backend tests
|-- backend/runtime/          # Development runtime cache, generated locally
|-- scripts/                  # Developer and packaging helper scripts
|-- docs/                     # Project documentation
|-- dist/                     # Vite build output
|-- build/                    # Backend packaging output
|-- release/                  # Electron-builder output
|-- package.json
|-- package-lock.json
`-- vite.config.js
```

The former `apps/pyside6` app has been removed. This app should remain self-contained in `apps/`.

The repository-level `test/hs2` directory is the local HS2 test environment. In the expected HS2 layout, `mods` stores `zipmod` files, `abdata` stores `.unity3d` files, and `UserData/chara` stores character-card PNG files.

## Commands

Run from `apps/`:

```powershell
npm run check:python
npm run python:dev
npm run dev
npm run build
npm run electron
npm run build:backend
npm run package:win
npm run check:package-deps
```

By default the Electron main process starts the backend with `PYTHON_EXECUTABLE` if set, then tries the configured local `mm_env` Python path, then falls back to `conda run -n mm_env python backend/app/server.py`.

```powershell
$env:PYTHON_EXECUTABLE="D:\path\to\python.exe"
npm run dev
```

## Runtime Architecture

```text
Vue renderer
  -> window.desktopApi from electron/preload.cjs
  -> Electron IPC handlers in electron/main.cjs
  -> Python HTTP backend at http://127.0.0.1:8765
  -> backend/star_manager services
  -> local filesystem, zipmod archives, SQLite runtime database
```

Development runtime data is normally written under `backend/runtime/`. Packaged builds use a runtime folder beside `Star_Manager.exe`. Runtime SQLite files, card previews, and thumbnail caches are rebuildable indexes, not source files.

## Backend Boundary

Electron calls `backend/app/server.py`, which imports local modules from `backend/star_manager/`. It should not import from removed PySide6 paths. Shared behavior belongs inside this backend package.

Renderer code should use `window.desktopApi` and `backendRequest`; it should not call Node, Electron, or filesystem APIs directly.

Backend connection rule:

- Single file or single object operations use direct HTTP API routes.
- Batch operations use `/tasks` and must report task progress.
- Do not add new bulk direct-HTTP mutation endpoints. Add a task type in `backend/app/bridge.py` instead.

Examples of direct operations:

- repair one zipmod Unity3D issue;
- update one zipmod author or editable manifest fields;
- inspect, cleanup, promote, merge, or delete one duplicate/zipmod target;
- import/export one item thumbnail;
- delete one item.

Examples of task operations:

- rebuild the mod/card database;
- export or organize selected zipmods;
- bulk repair Unity3D issues;
- smart cleanup duplicate zipmods;
- bulk delete zipmods;
- bulk update manifest authors;
- apply one thumbnail to many target items;
- delete filtered error items.

## Important Backend Files

- `backend/app/server.py`: HTTP routes, file serving, JSON responses, parent-process watchdog.
- `backend/app/bridge.py`: in-memory task store and task type dispatch.
- `backend/star_manager/services/mod_database.py`: compatibility facade and database build orchestration.
- `backend/star_manager/services/mod_database_core.py`: dataclasses, SQLite schema, migrations, and metadata.
- `backend/star_manager/services/mod_database_queries.py`: database status, list/filter queries, GUID lookup, export, and duplicate analysis queries.
- `backend/star_manager/services/mod_database_assets.py`: zipmod scanning, manifest/CSV parsing, thumbnail handling, Unity3D diagnostics, and repair/delete write-back helpers.
- `backend/star_manager/services/card_library.py`: card folder tree, card listing, normalized preview images, and card detail.
- `backend/star_manager/services/card_database.py`: character-card indexing and dependency association with zipmods/items.
- `backend/star_manager/core/card_parser.py`: AIS card PNG payload parsing and dependency extraction.
- `backend/star_manager/core/runtime_paths.py`: runtime path helpers.
- `backend/star_manager/core/zipmod_utils.py`: HS2 directory checks and zipmod helper logic.
- `backend/star_manager/services/mod_workflow.py`: legacy card search, dependency extraction, and zipmod sorting workflows.

## Data and Workflows

The local database is normally `backend/runtime/star_manager.sqlite`.

Core indexed data:

- `zipmods`: one primary row per manifest GUID, file metadata, scan status, Unity3D summary, and diagnostics.
- `duplicate_zipmods`: duplicate files for GUIDs already represented by a primary zipmod.
- `mod_items`: item rows parsed from `abdata/list/**/*.csv`, linked to source zipmods.
- `character_cards`: indexed card PNG files under `UserData/chara`.
- `character_card_dependencies`: card dependencies parsed from UniversalAutoResolver records and linked to zipmods/items when possible.

Database rebuild flow:

```text
validate HS2 directory
-> scan mods/**/*.zipmod
-> parse manifest.xml and choose primary zipmod per GUID
-> parse abdata/list/**/*.csv
-> extract/cache thumbnails and diagnose MainAB/ThumbAB resources
-> build character-card index and dependency links
-> update SQLite metadata
```

The renderer checks database existence before loading lists. Zipmods load in pages of 200, items load in pages of 500, and thumbnails are served through the backend instead of direct filesystem URLs. Character cards are read from `UserData/chara`; the service intentionally ignores the root-level `navi` card folder.

## API Summary

Read and file routes:

- `GET /health`
- `GET /tasks`
- `GET /tasks/:task_id`
- `GET /mods/database`
- `GET /mods/database/changes?game_dir=`
- `GET /cards/database`
- `GET /mods/zipmods?offset=&limit=&author=&status=&usage=`
- `GET /mods/zipmods/authors`
- `GET /mods/zipmods/:id/diagnostics`
- `GET /mods/zipmods/:id/duplicate-analysis`
- `GET /mods/zipmods/:id/manifest`
- `GET /mods/items?offset=&limit=&zipmod_id=&search=&kind=&author=&status=&usage=`
- `GET /mods/items/filters`
- `GET /mods/thumbnails?path=`
- `GET /library/cards/tree?game_dir=`
- `GET /library/cards?game_dir=&path=`
- `GET /library/cards/detail?game_dir=&path=`
- `GET /library/cards/image?game_dir=&path=`

Mutation and task routes:

- `POST /tasks`
- `POST /mods/zipmods/:id/repair-unity3d`
- `POST /mods/zipmods/:id/update-author`
- `POST /mods/zipmods/:id/manifest`
- `POST /mods/zipmods/:id/cleanup-duplicates`
- `POST /mods/zipmods/:id/promote-duplicate`
- `POST /mods/zipmods/:id/merge-duplicate`
- `POST /mods/zipmods/:id/delete`
- `POST /mods/items/:id/import-thumbnail`
- `POST /mods/items/:id/export-thumbnail`
- `POST /mods/items/:id/delete`

Current task types:

- `check_game_dir`
- `search_cards`
- `extract_mods`
- `sort_mods`
- `build_card_database`
- `build_mod_database`
- `bulk_export_zipmods`
- `bulk_organize_zipmods`
- `bulk_cleanup_duplicate_zipmods`
- `bulk_delete_zipmods`
- `bulk_repair_zipmods_unity3d`
- `bulk_update_zipmod_authors`
- `bulk_apply_item_thumbnail`
- `bulk_delete_error_items`

For exact payloads and response shapes, see `docs/backend-interface.md`.

## Electron Bridge

The preload bridge exposes:

- directory and PNG file pickers;
- a native text prompt;
- `showItemInFolder` for file-location actions;
- game launch helpers for `HoneySelect2.exe`, `StudioNEOV2.exe`, and `HoneySelect2VR.exe`;
- persisted settings for `gameDir`, `inputDir`, and `outputDir`;
- `backendRequest` for local HTTP API calls.

Packaged builds can use a PyInstaller backend executable from `build/backend/star_manager_backend.exe`; otherwise Electron starts the Python backend script.

## Documentation

- `docs/project-overview.md`: product map, runtime architecture, directory responsibilities, data model, workflows, commands, tests, and development rules.
- `docs/backend-interface.md`: frontend/backend contract, direct routes, task protocol, and mutation boundaries.
- `docs/frontend-ui/frontend-ui-architecture.md`: UI documentation index and high-level layout assumptions.
- `docs/mod_manage/mod_database_design.md`: SQLite schema and mod database build rules.
- `docs/mod_manage/mod_database_change_detection.md`: incremental rebuild behavior and dependency relinking.
- `docs/mod_manage/character_card_parsing.md`: AIS card PNG payload and dependency parsing notes.
- `docs/packaging-windows.md`: Windows packaging flow and verification commands.

## Development Notes

- Keep new application source, runtime files, dependencies, build scripts, and docs under `apps/`.
- Do not import or recreate removed `apps/pyside6` paths.
- Treat `Copy` as the safe default. Move/delete operations require clear confirmation.
- Frontend/source edits should be followed by `npm run build` before completion.
