# AGENTS.md

## Project Layout

This repository now contains one desktop application:

```text
apps/
|-- electron/   # Electron main process and preload
|-- src/        # Vue renderer
|-- backend/    # Local Python HTTP backend and business logic
|-- scripts/    # Developer helper scripts
|-- dist/       # Vite build output
|-- package.json
|-- package-lock.json
`-- vite.config.js
```

The former `apps/pyside6` application line has been removed intentionally. Do not add new PySide6 application files unless the project is deliberately reintroducing that app.

The root directory is for repository-level files only. Keep application source, runtime files, and dependency files under `apps/`.

## Project Documentation

When gathering project context or learning how the app works, check the project documents under `apps/docs/` first. Useful entry points:

- `apps/docs/project-overview.md`: current project map, product scope, runtime architecture, directory responsibilities, backend/frontend modules, data model, main workflows, commands, and development rules. Start here when you need to understand the whole repo.
- `apps/README.md`: maintained Electron/Vue/Python app overview, commands, backend boundary, and current backend endpoint summary.
- `apps/docs/backend-interface.md`: frontend/backend interface contract, Electron preload bridge, direct HTTP routes, task protocol, task types, and the single-object-vs-batch mutation rule.
- `apps/docs/frontend-ui/frontend-ui-architecture.md`: frontend documentation index and high-level product assumptions.
- `apps/docs/frontend-ui/main-layout.md`: application shell, global navigation, top bar, workspace regions, backend context, and global rebuild-database behavior.
- `apps/docs/frontend-ui/zipmod-library-layout.md`: mod management UI, mod/item list behavior, detail drawer, pagination, thumbnails, Kind mapping, and file-location interactions.
- `apps/docs/frontend-ui/character-cards-layout.md`: character-card browser layout and expected card-library behavior.
- `apps/docs/frontend-ui/overview-layout.md`: overview dashboard structure and suggested actions.
- `apps/docs/frontend-ui/runtime-log-layout.md`: runtime log page behavior.
- `apps/docs/frontend-ui/start-layout.md`: start page and setup/game-launch workflows.
- `apps/docs/frontend-ui/ui-style.md`: visual style and interaction rules.
- `apps/docs/packaging-windows.md`: Windows Electron/Python packaging flow, output paths, verification commands, and packaging warnings. Consult when building or troubleshooting distributable exe output.
- `apps/docs/mod_manage/character_card_parsing.md`: AIS character-card PNG payload layout, MessagePack block table, UniversalAutoResolver dependency records, and item-level mapping notes. Consult when updating card parsing, dependency extraction, or card detail diagnostics.
- `apps/docs/mod_manage/mod_database_design.md`: SQLite mod database schema, indexing flow, build rules, and current mod database API.
- `apps/docs/mod_manage/mod_database_change_detection.md`: current implemented database change detection, incremental rebuild behavior, added/removed/modified zipmod handling, duplicate GUID handling, and character-card dependency relinking. Consult when updating rebuild detection, database association logic, or automatic startup rebuild behavior.
- `apps/docs/mod_manage/mod_exception_catalog.md`: current mod exception types, trigger conditions, UI titles, and repair actions. Consult when updating diagnostics or adding new repair flows.

When adding a new project document, update this `Project Documentation` section in the same change. Add the document path, a short content summary, and when an agent should consult it.

## Electron App

Location:

```text
apps
```

Important files:

- `package.json`, `package-lock.json`: Node dependency and script definitions.
- `node_modules/`: local installed Node dependencies. Keep this directory with the app when moving/copying it locally.
- `.npm-cache/`: local npm cache from this workspace.
- `electron/main.cjs`: Electron main process and Python backend launcher.
- `electron/preload.cjs`: renderer bridge.
- `src/`: Vue renderer.
- `backend/app/server.py`: local HTTP backend entry.
- `backend/app/bridge.py`: task bridge.
- `backend/star_manager/`: Electron-owned Python business package.

Mod database backend modules:

- `backend/star_manager/services/mod_database.py`: compatibility facade and database build orchestration.
- `backend/star_manager/services/mod_database_core.py`: shared constants, dataclasses, SQLite schema, migrations, and metadata helpers.
- `backend/star_manager/services/mod_database_queries.py`: database status, list/filter queries, GUID lookup, and zipmod export.
- `backend/star_manager/services/mod_database_assets.py`: zipmod scanning, manifest/CSV parsing, Unity3D/thumbnail handling, and repair/delete write-back helpers.

Common commands:

```powershell
cd apps
npm run check:python
npm run dev
npm run build
npm run electron
```

Python backend development:

```powershell
cd apps
npm run python:dev
```

By default, the Electron main process starts the backend with `PYTHON_EXECUTABLE` if set. Otherwise it tries the local `mm_env` conda environment path first, then falls back to:

```powershell
conda run -n mm_env python backend/app/server.py
```

To force a specific Python interpreter:

```powershell
cd apps
$env:PYTHON_EXECUTABLE="D:\path\to\python.exe"
npm run dev
```

## Backend Boundary

Electron calls `backend/app/server.py`, which imports local modules from `backend/star_manager/`.

Because `apps/pyside6` has been removed, the Electron app must not depend on any deleted PySide6 paths such as `apps/pyside6/script/app`. Shared or migrated behavior belongs inside `apps/backend/star_manager/`.

Frontend/backend mutation rule: single file or single object operations use direct HTTP API routes; batch operations use `/tasks` and report progress through the task bridge. Do not add new bulk direct-HTTP mutation endpoints.

## Windows Encoding Safety

This repository contains UTF-8 source files with Chinese UI text. On Windows, do not edit source files using PowerShell text pipelines such as:

- `Get-Content ... | Set-Content ...`
- `Set-Content` without explicit UTF-8 no-BOM handling
- `Out-File`
- PowerShell line filtering that rewrites whole files

These commands can corrupt non-ASCII text through the active console code page.

For source edits, use `apply_patch` only. If a mechanical rewrite is unavoidable, use a UTF-8-safe script that explicitly reads and writes `encoding="utf-8"` and first explains why `apply_patch` is insufficient. Never use PowerShell to rewrite whole `.vue`, `.js`, `.ts`, `.css`, `.py`, `.md`, `.json`, or `.html` files containing non-ASCII text.

When deleting or moving blocks in source files, prefer `apply_patch` with exact context. Do not perform line-number based rewrites through shell commands.

Before finishing any frontend/source edit on Windows, run:

```powershell
npm run build
```

If mojibake such as `????`, `锟`, `�`, or broken Chinese appears in edited UI text, stop and repair it before reporting completion.

## Maintenance Notes

- `Copy` is the safe default zipmod extraction mode.
- `Cut`/move modifies the game directory and should be treated as risky.
- Keep Electron, Vue, Python backend, dependency, and build files inside `apps/`.
- Do not add application source files directly to the repository root.
