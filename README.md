# Star_Manager

Star_Manager is a Windows desktop resource manager for local HS2 / AIS game directories. It helps players and modpack maintainers browse character cards, inspect zipmods, find missing resources, clean duplicate packages, and organize large local mod libraries.

The app is built with Electron, Vue, and a local Python backend. It never treats its SQLite database as the source of truth: your game directory, zipmod archives, `manifest.xml`, CSV files, `.unity3d` resources, and character-card PNG files remain the real data.

## What It Does

- Builds a local searchable index for `mods/**/*.zipmod` and `UserData/chara`.
- Browses zipmods by author, status, usage, path, GUID, version, scan result, and item count.
- Browses parsed mod items by name, Kind, author, thumbnail state, source zipmod, and character-card usage.
- Shows AIS/HS2 character-card folders and card previews.
- Parses UniversalAutoResolver dependency records from character-card PNG payloads.
- Links card dependencies back to indexed zipmods and mod items when possible.
- Diagnoses missing or external `.unity3d` files, thumbnail issues, manifest errors, read failures, stale records, and duplicate GUIDs.
- Repairs selected zipmod Unity3D issues, edits manifest metadata, imports/exports item thumbnails, and removes selected broken items or packages.
- Runs batch workflows for database rebuilds, zipmod export/organization, duplicate cleanup, author updates, shared thumbnail application, and filtered error-item deletion.
- Launches `HoneySelect2.exe`, `StudioNEOV2.exe`, and `HoneySelect2VR.exe` from the desktop shell.

## Main Screens

- **Start**: choose an HS2 directory, keep common paths, and launch the game or studio.
- **Overview**: check library health, database status, suggested actions, and recent tasks.
- **Characters**: browse `UserData/chara`, preview AIS cards, and inspect parsed dependency status.
- **Mods**: switch between item browsing and zipmod browsing, filter large libraries, review details, and run repairs.
- **Logs**: follow task progress and backend messages.

## How It Works

```text
Vue renderer
  -> Electron preload bridge
  -> local Python HTTP backend
  -> zipmod/card scanners
  -> SQLite runtime index and thumbnail/card-preview caches
```

The runtime database and generated previews are rebuildable caches. If the index gets out of date, rebuild it from the selected game directory.

## Requirements

- Windows
- Node.js / npm for development
- Python environment with the backend requirements installed
- An HS2 / AIS-style local game directory

The Electron main process starts the backend with `PYTHON_EXECUTABLE` if set. Otherwise it tries the local `mm_env` conda environment path, then falls back to `conda run -n mm_env python backend/app/server.py`.

## Quick Start

```powershell
cd apps
npm install
npm run check:python
npm run dev
```

To force a specific Python interpreter:

```powershell
cd apps
$env:PYTHON_EXECUTABLE="D:\path\to\python.exe"
npm run dev
```

Useful development commands:

```powershell
cd apps
npm run python:dev
npm run build
npm run electron
npm run build:backend
npm run package:win
```

## Project Layout

```text
apps/
|-- electron/                 # Electron main process and preload bridge
|-- src/                      # Vue renderer
|-- backend/app/              # Local Python HTTP service
|-- backend/star_manager/     # Python business logic
|-- backend/tests/            # Backend tests
|-- scripts/                  # Developer and packaging helpers
|-- docs/                     # Project documentation
|-- package.json
`-- vite.config.js
```

The former `apps/pyside6` app has been removed. Current development should stay inside `apps/`.

## Documentation

- [apps/README.md](apps/README.md): application-level developer notes.
- [apps/docs/project-overview.md](apps/docs/project-overview.md): full project map, runtime architecture, data model, workflows, tests, and development rules.
- [apps/docs/backend-interface.md](apps/docs/backend-interface.md): frontend/backend API contract and task protocol.
- [apps/docs/mod_manage/mod_database_design.md](apps/docs/mod_manage/mod_database_design.md): mod database schema and scanning rules.
- [apps/docs/mod_manage/character_card_parsing.md](apps/docs/mod_manage/character_card_parsing.md): AIS card payload and dependency parsing notes.
- [apps/docs/packaging-windows.md](apps/docs/packaging-windows.md): Windows packaging flow.

## Development Notes

- Keep application source, build scripts, runtime files, dependencies, and docs under `apps/`.
- Use direct HTTP routes for single-object changes and `/tasks` for batch operations.
- Treat `Copy` as the safe default for extraction and export workflows.
- Move/delete operations modify the game directory and should be handled deliberately.
- Runtime caches and build outputs are disposable.

