# Project Overview

本文档用于快速梳理 Star_Manager 当前项目内容。新成员或自动化代理在动手改代码前，应先读本文，再按具体任务进入对应专题文档。

## 当前产品

Star_Manager 是面向 HS2 / AIS 本地游戏目录的桌面资源管理器。当前维护线只有一个 Electron + Vue + Python 应用，旧的 `apps/pyside6` 应用线已移除，不应再作为依赖或新增入口。

核心管理对象：

- `zipmod`：HS2 模组压缩包，通常包含 `manifest.xml`、`abdata/list/**/*.csv` 和 `.unity3d` 资源。
- `png` 角色卡：位于 `UserData/chara`，包含 AIS/HS2 角色数据和 UniversalAutoResolver 依赖记录。
- `.unity3d`：作为 zipmod 内部资源或游戏目录 `abdata` 回退资源参与诊断、修复和导出。

当前应用定位已经从“单页任务控制台”转向“资源库浏览器”：用户选择 HS2 游戏目录后，应用建立本地 SQLite 索引，前端围绕角色卡、zipmod、物品、诊断和批量维护工作流浏览数据。

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

The backend uses `STAR_MANAGER_RUNTIME_DIR` for runtime cache location. Development defaults to `apps/backend/runtime`; packaged builds use a `runtime` folder beside `Star_Manager.exe`.

## Frontend Shape

The renderer is a Vue app with a persistent shell and five main views:

- Start: game launch, path setup, setup/configuration surfaces.
- Overview: game directory summary, health cards, suggested actions, recent tasks.
- Characters: `UserData/chara` directory tree, card grid, card detail, dependency views.
- Mods: item/zipmod browsing modes, filters, detail drawer, diagnostics, direct and batch maintenance actions.
- Logs: task and runtime message review.

Important frontend files:

- `apps/src/App.vue`: main shell, shared state, task polling, API calls, filters and bulk actions.
- `apps/src/components/views/*.vue`: view-level presentation components.
- `apps/src/components/LazyThumbnail.vue`: thumbnail display helper.
- `apps/src/styles.css`: global visual system and layout styles.

## Backend Modules

Important backend entry points:

- `apps/backend/app/server.py`: HTTP routes, file serving, JSON responses, parent-process watchdog.
- `apps/backend/app/bridge.py`: in-memory task store and task type dispatch.

Business modules:

- `star_manager/core/card_parser.py`: AIS card PNG payload parsing and dependency extraction.
- `star_manager/core/runtime_paths.py`: runtime path helpers.
- `star_manager/core/zipmod_utils.py`: HS2 directory checks and zipmod helper logic.
- `star_manager/services/card_library.py`: card folder tree, card listing, normalized preview images, card detail.
- `star_manager/services/card_database.py`: character-card indexing and dependency association with zipmods/items.
- `star_manager/services/mod_database.py`: compatibility facade plus database build orchestration.
- `star_manager/services/mod_database_core.py`: dataclasses, SQLite schema, migrations, metadata.
- `star_manager/services/mod_database_queries.py`: database status, lists, filters, exports, duplicate analysis queries.
- `star_manager/services/mod_database_assets.py`: zipmod scanning, manifest/CSV parsing, thumbnails, Unity3D diagnostics, write-back repair/delete operations.
- `star_manager/services/mod_workflow.py`: legacy card search, dependency extraction, zipmod sorting workflows.
- `star_manager/tools/mod_sorter.py`: mod sorting helper.
- `star_manager/utils/binary_reader.py`: binary parsing utility.

## Data Model

Runtime data is stored in SQLite, normally at `apps/backend/runtime/star_manager.sqlite` during development.

Core tables:

- `zipmods`: one primary row per manifest GUID, plus file metadata, scan status, item count, Unity3D summary and diagnostics.
- `duplicate_zipmods`: duplicate files for GUIDs whose primary zipmod is already represented in `zipmods`.
- `mod_items`: item rows parsed from `abdata/list/**/*.csv`, linked to `zipmods`.
- `character_cards`: indexed character cards under `UserData/chara`.
- `character_card_dependencies`: dependencies parsed from cards and linked to `zipmods` / `mod_items` when possible.
- `database_metadata`: build metadata such as last build time.

Important design rule: the file system, zipmod archive contents, `manifest.xml`, CSV rows, and card PNG payloads are the source of truth. SQLite is a local index and cache that can be rebuilt.

## API Boundary

Direct HTTP routes are used for single object mutations and reads. Batch operations use `/tasks` and task polling.

Examples of direct mutations:

- repair one zipmod Unity3D issue;
- update one zipmod manifest author or editable manifest fields;
- cleanup, promote, merge, or delete one duplicate/zipmod target;
- import/export one item thumbnail;
- delete one item.

Examples of task mutations:

- rebuild mod/card database;
- export or organize selected zipmods;
- bulk repair Unity3D issues;
- smart cleanup duplicate zipmods;
- bulk delete zipmods;
- bulk update manifest authors;
- apply one thumbnail to many target items;
- delete filtered error items.

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

## Commands

Run from `apps/` unless noted otherwise:

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

Python dependency requirements are in `apps/backend/requirements.txt`. Packaging details and verification commands are in `apps/docs/packaging-windows.md`.

## Tests

Backend tests live under `apps/backend/tests/`. Current coverage focuses on:

- mod database queries and filters;
- zipmod asset scanning and write-back helpers;
- duplicate cleanup policy and bridge task behavior;
- item thumbnail batch task behavior;
- character-card database behavior.

Use the existing tests as the first safety net when changing backend database, parser, or task behavior. Frontend changes should still run `npm run build` before completion.

## Development Rules

- Keep new application files under `apps/`.
- Do not import or recreate removed `apps/pyside6` paths.
- Keep single-object direct routes and batch task routes separate.
- Treat `Copy` as the safe default. Move/delete operations require clear confirmation.
- On Windows, use `apply_patch` for source/document edits containing Chinese text. Avoid PowerShell rewrite pipelines that can corrupt UTF-8.
- Runtime cache and build outputs are disposable and should not be used as maintained documentation.

## Where To Read Next

- Frontend/backend contract: `apps/docs/backend-interface.md`.
- Frontend layout and visual rules: `apps/docs/frontend-ui/frontend-ui-architecture.md`.
- Mod database schema and scanning: `apps/docs/mod_manage/mod_database_design.md`.
- Incremental rebuild and dependency relinking: `apps/docs/mod_manage/mod_database_change_detection.md`.
- Card parsing details: `apps/docs/mod_manage/character_card_parsing.md`.
- Packaging: `apps/docs/packaging-windows.md`.
