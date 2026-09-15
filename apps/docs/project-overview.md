# Project Overview

面向新用户的产品定位和页面使用流程见[项目介绍](project-introduction.md)；本文保留开发者需要的架构、数据模型、接口和维护规则。

本文档用于快速梳理 Star_Manager 当前项目内容。新成员或自动化代理在动手改代码前，应先读本文，再按具体任务进入对应专题文档。

## 当前产品

Star_Manager 是面向 HS2 / AIS 本地游戏目录的桌面资源管理器。当前维护线只有一个 Electron + Vue + Python 应用，旧的 `apps/pyside6` 应用线已移除，不应再作为依赖或新增入口。

核心管理对象：

- `zipmod`：HS2 模组压缩包，通常包含 `manifest.xml`、`abdata/list/**/*.csv` 和 `.unity3d` 资源。
- `png` 角色卡：位于 `UserData/chara`，包含 AIS/HS2 角色数据和 UniversalAutoResolver 依赖记录。
- `png` 服装卡：位于 `UserData/coordinate`，使用独立的服装卡有效性索引和按需详情解析。
- 游戏原版物品：从 `abdata/list/characustom/*.unity3d` 的 `ChaListData` 建立 `builtin_items`，用于物品浏览和 Coordinate 依赖匹配。
- `.unity3d`：作为 zipmod 内部资源或游戏目录 `abdata` 回退资源参与诊断、修复和导出。

当前应用定位已经从“单页任务控制台”转向“资源库浏览器”：用户选择 HS2 游戏目录后，应用建立本地 SQLite 索引，前端围绕角色卡、服装卡、zipmod、原版/模组物品、诊断、装配和批量维护工作流浏览数据。

## 目录分工

```text
apps/
|-- electron/                 # Electron main process and preload bridge
|-- src/                      # Vue renderer and view components
|-- backend/app/              # Local Python HTTP service entry and task bridge
|-- backend/star_manager/     # Python business package
|-- backend/tests/            # Python backend tests
|-- backend/runtime/          # Development runtime cache, generated locally
|-- scripts/                  # Developer and packaging helper scripts
|-- tools/                    # Isolated C# helpers and companion game plugins
|-- docs/                     # Project documentation
|-- dist/                     # Vite build output
|-- build/                    # Backend packaging output
|-- release/                  # Electron-builder output
|-- package.json
|-- package-lock.json
`-- vite.config.js
```

Repository root is reserved for repository-level files such as `README.md`, `AGENTS.md`, `.gitignore`, and local test fixtures. Application source, runtime files, dependency files, build scripts, and documentation belong under `apps/`.

`apps/backend/runtime/`, `apps/dist/`, `apps/build/`, and `apps/release/` are generated or environment-specific outputs. Do not treat runtime thumbnails, card previews, or SQLite files as source of truth.

## Runtime Architecture

```text
Vue renderer
  -> window.desktopApi from electron/preload.cjs
  -> Electron IPC handlers in electron/main.cjs
  -> Python HTTP backend at http://127.0.0.1:8765
  -> backend/star_manager services
  -> local filesystem, zipmod archives, SQLite runtime database
```

Renderer code should not call Node, Electron, or filesystem APIs directly. It should use `window.desktopApi` for desktop capabilities and `backendRequest` for backend HTTP calls.

Electron starts the backend with this priority:

1. Packaged backend executable from `resources/backend/star_manager_backend.exe`, or `STAR_MANAGER_BACKEND_EXE` when set.
2. `PYTHON_EXECUTABLE` when set.
3. The configured local `mm_env` Python path.
4. `conda run -n mm_env python backend/app/server.py`.

The Electron main process uses `app.requestSingleInstanceLock()` so a second Star_Manager launch focuses the existing window instead of creating another app/backend pair. On shutdown, the `before-quit` handler waits for backend cleanup; Windows uses `taskkill.exe /PID <pid> /T /F` so wrapper and child processes are removed together. See [Electron 进程生命周期](electron-process-lifecycle.md) for the lifecycle contract and verification boundaries.

The backend uses `STAR_MANAGER_RUNTIME_DIR` for runtime cache location. Development defaults to `apps/backend/runtime`; packaged builds use a `runtime` folder beside `Star_Manager.exe`.

Electron hardware acceleration is enabled by default so the Three.js model preview remains responsive at large sizes. Set `STAR_MANAGER_DISABLE_GPU=1` only as a compatibility fallback for systems where GPU acceleration prevents the app from starting or rendering correctly.

## Frontend Shape

The renderer is a Vue app with a persistent shell. It has eight main navigation items plus a settings page fixed at the bottom of the sidebar:

- Start: game launch, path setup, setup/configuration surfaces.
- Overview: game directory summary, health cards, suggested actions, recent tasks.
- Characters: `UserData/chara` directory tree, card grid, card detail, dependency views.
- Mods: item/zipmod browsing modes, filters, detail drawer, diagnostics, direct and batch maintenance actions.
- Plugins: BepInEx plugin inventory, metadata, dependencies, and diagnostics.
- Workbench: standalone mod-making workspace with local project/manifest files, CSV-backed items, Unity3D database-template selection, MainData preprocessing, resource write-back, and a modal Sims 4 Package → FBX tool in the project-level toolbar.
- Logs: task and runtime message review.
- Trash: recoverable character-card and zipmod entries, with restore and permanent-delete actions.
- Settings: manager startup behavior, local achievement preferences, persistent default export locations, and Blender executable integration for Workbench FBX imports.

The Start page reads and writes the game's UTF-16 `UserData/setup.xml` through Electron IPC. Saving creates a `.bak` copy, atomically replaces the XML, and synchronizes the Unity display values in the Windows registry. Launching checks for IPA/BepInEx conflicts and uses `IPA.exe --launch` when IPA is present.

Important frontend files:

- `apps/src/App.vue`: main shell, shared state, task polling, API calls, filters and bulk actions.
- `apps/src/components/views/*.vue`: view-level presentation components.
- `apps/src/components/ModelPreview.vue`: Three.js GLB viewer, mannequin overlay, camera/light/background controls, and screenshot capture.
- `apps/src/components/CardCoverCropper.vue`: native-resolution `63:88` cover crop UI.
- `apps/src/components/LazyThumbnail.vue`: thumbnail display helper.
- `apps/src/components/VirtualItemTable.vue` / `VirtualItemGrid.vue`: virtualized item table and compact item grid.
- `apps/src/styles.css`: global visual system and layout styles.

## Backend Modules

Important backend entry points:

- `apps/backend/app/server.py`: HTTP routes, file serving, JSON responses, parent-process watchdog.
- `apps/backend/app/bridge.py`: in-memory task store and task type dispatch.

Business modules:

- `star_manager/core/card_parser.py`: AIS card PNG payload parsing and dependency extraction.
- `star_manager/core/runtime_paths.py`: runtime path helpers.
- `star_manager/core/zipmod_utils.py`: HS2 directory checks and zipmod helper logic.
- `star_manager/services/card_library.py`: card folder tree, card listing, normalized preview images, card detail, coordinate export, and portable dependency package generation.
- `star_manager/services/card_database.py`: character-card indexing and dependency association with zipmods/items.
- `star_manager/services/builtin_database.py`: scans game-original `ChaListData` resources into the `builtin_items` index and prepares original-item thumbnails.
- `star_manager/services/game_item_probe.py`: communicates with the optional BepInEx game-side item probe and resolves current-character/H-scene item state.
- `star_manager/services/plugin_library.py`: BepInEx plugin metadata scan/cache and safe single-plugin enable/disable.
- `star_manager/services/achievements.py`: local achievement milestones, event deduplication, preferences, and reset.
- `star_manager/services/mod_database.py`: compatibility facade plus database build orchestration.
- `star_manager/services/mod_database_core.py`: dataclasses, SQLite schema, migrations, metadata.
- `star_manager/services/mod_database_queries.py`: database status, lists, filters, exports, duplicate analysis queries.
- `star_manager/services/mod_database_assets.py`: zipmod scanning, manifest/CSV parsing, thumbnails, Unity3D diagnostics, write-back repair/delete operations.
- `star_manager/services/model_preview.py`: selected item MainAB mesh/material conversion to runtime GLB and preparation of the source Unity3D file for external tools.
- `star_manager/services/mod_workflow.py`: legacy card search, dependency extraction, zipmod sorting workflows.
- `star_manager/services/remote_mod_completion.py`: reads the remote missing-mod index for character and scene cards, downloads, validates, installs, and indexes selected zipmods.
- `star_manager/services/trash.py`: validates runtime recycle-bin entries and handles recover/erase operations.
- `star_manager/services/sims4_workbench.py`: Sims 4 Package export request handler for collision-safe LOD0 FBX plus RLE2 PNG texture extraction, exposed from the Workbench project-level Package → FBX modal.
- `star_manager/core/card_metadata.py`: read/write of registered Star Manager favorite, rating, and tag metadata.
- `star_manager/core/character_profile.py`: atomic character parameter and cover replacement logic.
- `star_manager/core/coordinate_card.py`: coordinate block extraction and coordinate-scoped plugin conversion.
- `star_manager/tools/mod_sorter.py`: mod sorting helper.
- `star_manager/utils/binary_reader.py`: binary parsing utility.

## Data Model

Runtime data is stored in SQLite, normally at `apps/backend/runtime/star_manager.sqlite` during development.

Core tables:

- `zipmods`: one primary row per manifest GUID, plus file metadata, scan status, item count, Unity3D summary and diagnostics.
- `duplicate_zipmods`: duplicate files for GUIDs whose primary zipmod is already represented in `zipmods`.
- `mod_items`: item rows parsed from `abdata/list/**/*.csv`, linked to `zipmods`.
- `builtin_items`: game-original clothing and accessory rows indexed by game directory, `CategoryNo`, and local item ID, including thumbnail and resource status.
- `character_cards`: indexed character cards under `UserData/chara`, including signature-validated browser caches for name, favorite, rating, and tags.
- `character_card_dependencies`: dependencies parsed from cards and linked to `zipmods` / `mod_items` when possible.
- `database_metadata`: build metadata such as last build time.
- `bepinex_plugin_cache`: per-game-directory plugin scan payload and source fingerprint.
- `achievement_progress`, `achievement_events`, `achievement_preferences`: local achievement state; these tables do not replace resource indexes.

The clothes-card browser has a separate `apps/backend/runtime/clothes_card_index.sqlite` index. It stores file signatures, parser version, lightweight `AIS_Clothes` validity, and display names; full card parsing remains on demand.

Important design rule: the file system, zipmod archive contents, `manifest.xml`, CSV rows, and card PNG payloads are the source of truth. SQLite is a local index and cache that can be rebuilt.

## API Boundary

Direct HTTP routes are used for single object mutations and reads. Batch operations use `/tasks` and task polling.

Examples of direct mutations:

- repair one zipmod Unity3D issue;
- update one zipmod manifest author or editable manifest fields;
- cleanup, promote, merge, or delete one duplicate/zipmod target;
- import/export one item thumbnail;
- generate one item model preview or prepare its source Unity3D file for an external tool;
- update one character-card profile, cover, favorite, rating, tags, navi slot, or coordinate card;
- send one validated item to the connected game character or load one selected character-card section;
- delete one item.

Examples of task mutations:

- rebuild mod/card database;
- index one newly packaged zipmod;
- query and download selected remote missing-mod candidates for character or scene cards;
- import external zipmods and related loose cards/resources;
- export or organize selected zipmods;
- organize all zipmods by author;
- generate one card's portable dependency package, including its resolved files;
- bulk repair Unity3D issues;
- smart cleanup duplicate zipmods;
- bulk delete zipmods;
- bulk update manifest authors;
- apply one thumbnail to many target items;
- delete filtered error items.

Recycle-bin restore and permanent deletion are direct routes; deleted character cards and zipmods are first moved into the runtime trash area, so the original source is not immediately removed.

Do not add new bulk direct-HTTP mutation endpoints. Add or extend a task in `apps/backend/app/bridge.py`.

For the exact route and payload contract, see `apps/docs/backend-interface.md`.

## Main Workflows

Database build:

```text
Validate HS2 directory
-> scan mods/**/*.zipmod
-> parse manifest.xml and choose primary zipmod per GUID
-> parse abdata/list/**/*.csv from primary zipmods
-> extract/cache thumbnails and diagnose MainAB/ThumbAB resources
-> scan game-original ChaListData into builtin_items
-> build character-card index and dependency links
-> update SQLite metadata
```

Change detection:

```text
GET /mods/database/changes?game_dir=...
-> compare current zipmod/card file metadata against indexed records
-> return added/removed/modified counts and rebuild recommendation
-> frontend may auto-submit incremental build_mod_database for small changes
```

Character-card dependency flow:

```text
Read AIS PNG payload
-> parse MessagePack block table
-> extract UniversalAutoResolver records
-> match GUID/item references against zipmods and mod_items
-> expose card detail and dependency status in UI
```

Original-resource and game-state flow:

```text
Scan game abdata/list/characustom/*.unity3d
-> index builtin_items and cache thumbnails
-> match character/coordinate dependencies by CategoryNo + item ID
-> optionally read current editor or H-scene state from the game-side probe
-> display original items or apply a validated item to the connected game
```

Plugin inventory flow:

```text
Scan BepInEx Plugins/patchers/core DLL metadata without executing DLLs
-> correlate assembly/config/translation descriptions
-> cache by file fingerprint in SQLite
-> display plugin, dependency, process, and diagnostic data
-> allow safe single-plugin enable/disable by reversible DLL rename
```

Workbench project flow:

```text
Register author ID and workspace
-> create or select a Star_Manager mod project
-> scan abdata/list/**/*.csv as the item source
-> select one item and choose a usable database Unity3D template
-> inspect MainData candidates and preprocess a runtime copy
-> copy the prepared Unity3D into the project and atomically update the item CSV
-> package the project into a strict-content zipmod and replace older archives with the same manifest GUID
```

The retained Sims 4 extraction flow is separate from the current page flow:

```text
Select one Sims 4 Package
-> select highest-vertex LOD0 GEOM per model family
-> decode RLE2 textures and remove fully transparent triangles
-> optionally use Blender plus the bundled 165-bone TS4 template to bake HS2-aligned T-Pose and translate both level arm chains slightly toward the torso
-> remove skeleton/weights and export collision-safe static FBX + textures
```

## Commands

Run from `apps/` unless noted otherwise:

```powershell
npm run check:python
npm run python:dev
npm run dev
npm run build
npm run build:card-plugin
npm run electron
npm run build:backend
npm run package:win
npm run check:package-deps
```

Python dependency requirements are in `apps/backend/requirements.txt`. Packaging details and verification commands are in `apps/docs/packaging-windows.md`.

## Tests

Backend tests live under `apps/backend/tests/`. Current coverage focuses on:

- mod database queries and filters;
- zipmod asset scanning and write-back helpers;
- duplicate cleanup policy and bridge task behavior;
- item thumbnail batch task behavior;
- character-card database behavior.
- character-card folders, metadata, profile updates, cover replacement, coordinate extraction, dependency packages, and deletion.
- model preview, Sims 4 workbench extraction, plugin cache, and metadata plugin validation.

Use the existing tests as the first safety net when changing backend database, parser, or task behavior. Frontend changes should still run `npm run build` before completion.

## Development Rules

- Keep new application files under `apps/`.
- Do not import or recreate removed `apps/pyside6` paths.
- Keep single-object direct routes and batch task routes separate.
- Treat `Copy` as the safe default. Move/delete operations require clear confirmation.
- On Windows, use `apply_patch` for source/document edits containing Chinese text. Avoid PowerShell rewrite pipelines that can corrupt UTF-8.
- Runtime cache and build outputs are disposable and should not be used as maintained documentation.

## Where To Read Next

- Documentation index and task-oriented map: `apps/docs/README.md`.
- Frontend/backend contract: `apps/docs/backend-interface.md`.
- Frontend layout and visual rules: `apps/docs/frontend-ui/README.md`.
- Plugin inventory page: `apps/docs/frontend-ui/plugins-layout.md`.
- Manager settings and persistence: `apps/docs/frontend-ui/settings-layout.md`.
- Mod database schema and scanning: `apps/docs/mod_manage/mod_database_design.md`.
- Incremental rebuild and dependency relinking: `apps/docs/mod_manage/mod_database_change_detection.md`.
- Card parsing details: `apps/docs/mod_manage/character_card_parsing.md`.
- Persistent card metadata plugin: `apps/docs/card-metadata-plugin.md`.
- Unity3D resource recovery notes: `apps/docs/unity3d-decryption-notes.md`.
- Packaging: `apps/docs/packaging-windows.md`.
