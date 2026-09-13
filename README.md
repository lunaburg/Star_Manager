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
- Generates on-demand item GLB/static FBX previews, including a reusable mannequin and Three.js viewer.
- Manages character-card profiles, covers, favorites, ratings, tags, navi slots, coordinate-card exports, and portable dependency packages.
- Scans BepInEx plugin metadata without executing DLLs and caches results by file fingerprint.
- Runs batch workflows for database rebuilds, external resource import, zipmod export/organization, duplicate cleanup, author updates, shared thumbnail application, and filtered error-item deletion.
- Launches `HoneySelect2.exe`, `StudioNEOV2.exe`, and `HoneySelect2VR.exe` from the desktop shell.

## Main Screens

- **Start**: choose an HS2 directory, keep common paths, and launch the game or studio.
- **Overview**: check library health, database status, suggested actions, and recent tasks.
- **Characters**: browse `UserData/chara`, preview AIS cards, and inspect parsed dependency status.
- **Mods**: switch between item browsing and zipmod browsing, filter large libraries, review details, and run repairs.
- **Plugins**: inspect BepInEx plugin identity, version, dependencies, process restrictions, and diagnostics.
- **Workbench**: extract Sims 4 Package LOD0 meshes and RLE2 textures, optionally bake an HS2-aligned T-Pose with Blender.
- **Logs**: follow task progress and backend messages.
- **Settings**: configure startup checks, local achievements, export defaults, favorite-card themes, and Blender.

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
|-- tools/                    # Isolated C# helper and card metadata plugin
|-- package.json
`-- vite.config.js
```

The former `apps/pyside6` app has been removed. Current development should stay inside `apps/`.

## Documentation

文档按“仓库 → 应用 → 专题 → 具体文档”分级组织，建议从对应层级的索引进入：

1. [文档总索引](apps/docs/README.md)：按阅读目标、功能和开发任务查找全部维护文档。
2. [应用 README](apps/README.md)：从 `apps/` 目录运行、构建和排查应用时的快速说明。
3. [项目总览](apps/docs/project-overview.md)：开发前了解架构、数据模型、工作流和边界。
4. [前端 UI 专题索引](apps/docs/frontend-ui/README.md)：页面、应用外壳和视觉规范。
5. [模组与资源专题索引](apps/docs/mod_manage/README.md)：模组数据库、角色卡解析、扫描变更和异常诊断。

按具体场景继续阅读：

- 用户首次使用： [项目介绍](apps/docs/project-introduction.md)
- 修改接口或任务： [前后端接口](apps/docs/backend-interface.md)
- 修改缓存或运行时文件： [缓存与运行时文件登记](apps/docs/runtime-cache-registry.md)
- 修改 Unity3D / Workbench： [前端 UI 专题索引](apps/docs/frontend-ui/README.md) → [工作台](apps/docs/frontend-ui/workbench-layout.md)
- 处理集成或资源恢复： [集成与排障文档](apps/docs/README.md#集成和排障)
- 生成 Windows 发行目录： [Windows 打包指南](apps/docs/packaging-windows.md)

## Development Notes

- Keep application source, build scripts, runtime files, dependencies, and docs under `apps/`.
- Use direct HTTP routes for single-object changes and `/tasks` for batch operations.
- Treat `Copy` as the safe default for extraction and export workflows.
- Move/delete operations modify the game directory and should be handled deliberately.
- Runtime caches and build outputs are disposable.
