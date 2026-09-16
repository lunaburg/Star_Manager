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

- `apps/docs/README.md`: canonical documentation index, task-oriented reading paths, and documentation maintenance rules. Start here when you do not yet know which document applies.
- `apps/docs/frontend-ui/README.md`: frontend UI sub-index covering the app shell, all pages, visual rules, and UI change paths.
- `apps/docs/mod_manage/README.md`: mod/resource sub-index covering database design, card parsing, change detection, and diagnostics.
- `apps/docs/project-introduction.md`: 面向用户的产品定位、页面导览、首次使用流程、数据边界和当前限制。需要介绍项目或核对页面行为时先查阅。
- `apps/docs/page-overview-from-screenshots.md`: 根据用户提供的页面截图，按截图顺序整理各页面的粗略介绍。需要快速向用户介绍界面时查阅。
- `apps/docs/project-overview.md`: current project map, product scope, runtime architecture, directory responsibilities, backend/frontend modules, data model, main workflows, commands, and development rules. Start here when you need to understand the whole repo.
- `apps/docs/runtime-architecture.html` / `apps/docs/runtime-architecture.json`: Archify-rendered high-level runtime architecture, primary request path, external dependencies, trust boundaries, and source-evidence pin. Consult when explaining or reviewing the desktop runtime topology.
- `apps/README.md`: maintained Electron/Vue/Python app overview, commands, backend boundary, and current backend endpoint summary.
- `apps/docs/backend-interface.md`: frontend/backend interface contract, Electron preload bridge, direct HTTP routes, task protocol, task types, and the single-object-vs-batch mutation rule.
- `apps/docs/runtime-cache-registry.md`: 当前应用的后端/前端/HTTP/进程内缓存、SQLite 索引、临时与派生运行时文件、开发缓存边界和清理规则。修改缓存路径、失效条件或清理行为时先查阅。
- `apps/docs/trash-recycle-bin.md`: 人物卡与 zipmod 的 runtime/trash 回收站目录、删除、恢复、永久删除、测试残留隔离和索引恢复边界。修改删除或恢复流程时先查阅。
- `apps/docs/frontend-ui/frontend-ui-architecture.md`: high-level frontend UI architecture, implementation baseline, and product assumptions.
- `apps/docs/frontend-ui/main-layout.md`: application shell, global navigation, page-specific top bar visibility including the card-management exception, workspace regions, backend context, weighted database-task progress, and global rebuild-database behavior.
- `apps/docs/frontend-ui/zipmod-library-layout.md`: mod management UI, light-blur glass-styled mod/item list, preview frames, detail drawer, multi-select action controls, enhanced header blur, unified backgrounds for the All Kind and item-view controls, the equal-size text-only item view switch below the All Kind control, Kind filter icons and mapping, pagination, thumbnails, and the merged filename file-location interaction.
- `apps/docs/frontend-ui/character-cards-layout.md`: character-card browser layout, the resource SVG icons for character/clothes/scene card type buttons, the transparent-glass refresh button, clothes-card browser behavior, shared card sizing rules, sidebar tree/detail tab interaction, the glass-styled controls within the character-card detail and related tabs, the icon-free tool cards in the detail tools tab, and the recoverable single-card delete tool.
- `apps/docs/frontend-ui/character-card-favorite-effects.md`: current configurable favorite-card themes, card/title styling, overflowing-name scrolling, and removal of legacy effect settings. Consult when changing character-card favorite visuals.
- `apps/docs/frontend-ui/overview-layout.md`: overview dashboard structure and suggested actions.
- `apps/docs/frontend-ui/runtime-log-layout.md`: runtime log page behavior, Electron first-screen milestones, and the non-blocking reveal-window startup rule.
- `apps/docs/frontend-ui/start-layout.md`: start page, persisted HS2 directory validation, backend-ready recovery, setup/game-launch workflows, and directory shortcuts.
- `apps/docs/frontend-ui/workbench-layout.md`: workbench project lifecycle, CSV item model, Unity3D template selection, MainData preprocessing, resource write-back, retained Sims 4 Package-to-FBX capability, and current limits. Consult when changing workbench tools, project files, CSV behavior, Unity3D resources, or Sims 4 extraction UI.
- `apps/docs/frontend-ui/plugins-layout.md`: BepInEx plugin scan scope, metadata display, cache behavior, and current read-only boundary. Consult when changing plugin inventory or plugin diagnostics.
- `apps/docs/frontend-ui/settings-layout.md`: manager settings, persistence fields, achievement preferences, export directories, and Blender integration. Consult when changing settings or startup behavior.
- `apps/docs/frontend-ui/ui-style.md`: visual style, interaction rules, and the minimal-text constraint for UI copy.
- `apps/docs/packaging-windows.md`: Windows Electron/Python packaging flow, output paths, verification commands, and packaging warnings. Consult when building or troubleshooting distributable exe output.
- `apps/docs/electron-process-lifecycle.md`: Electron single-instance behavior, Windows backend process-tree cleanup, exit waiting, and lifecycle boundaries. Consult when changing app startup, backend launch, or shutdown behavior.
- `apps/docs/electron-process-lifecycle.md`: Electron single-instance behavior, Windows backend process-tree cleanup, exit waiting, and lifecycle boundaries. Consult when changing app startup, backend launch, or shutdown behavior.
- `apps/docs/mod_manage/character_card_parsing.md`: AIS character-card PNG payload layout, MessagePack block table, UniversalAutoResolver dependency records, item-level mapping notes, and character-card database parsing performance/one-read reuse. Consult when updating card parsing, dependency extraction, card detail diagnostics, or database build performance.
- `apps/docs/mod_manage/clothes_card_sample_analysis.md`: one verified AIS_Clothes sample report covering the clothes-card envelope, Coordinate part layout, UniversalAutoResolver dependencies, KKEx plugins, and parsing limits. Consult when validating clothes-card parsing or designing the clothes-card browser.
- `apps/docs/mod_manage/scene_card_parsing.md`: StudioNEOV2 scene-card payload layout, scene-level UniversalAutoResolver map/item/pattern dependencies, local/remote zipmod and item matching, remote completion, and the detail-page related-tab display. Consult when changing scene-card parsing, scene dependency presentation, or remote completion.
- `apps/docs/mod_manage/builtin_resource_index.md`: game-original `ChaListData` Unity3D list scanning, `builtin_items`, thumbnail extraction, and Coordinate matching. Consult when changing original-resource indexing or original clothes-card associations.
- `apps/docs/mod_manage/mod_database_design.md`: SQLite mod database schema, indexing flow, build rules, and current mod database API.
- `apps/docs/mod_manage/mod_database_build_benchmark.md`: 100 个数据库真实 zipmod 的建库性能基准，ZIP 读取/解压、UnityPy 缩略图处理的时间占比、验证产物和优化边界；调查建库性能或压缩包/缩略图优化时先查阅。
- `apps/docs/mod_manage/mod_database_change_detection.md`: current implemented database change detection, incremental rebuild behavior, added/removed/modified zipmod handling, duplicate GUID handling, character-card dependency relinking, and throttled character-card task progress messages. Consult when updating rebuild detection, database association logic, automatic startup rebuild behavior, or task progress reporting.
- `apps/docs/mod_manage/standard_mod_structure_record.md`: standard zipmod archive layout, manifest/CSV relationships, Unity3D references, thumbnail sources, and external `.zip` normalization. Consult when changing scanners, imports, or write-back behavior.
- `apps/docs/mod_manage/hooh_ammunition_go_zipmod_analysis.md`: verified `[Hooh] ammunition_go.zipmod` Studio sample, `ItemCategory`/`ItemList` fields, AssetBundle prefab mapping, validation evidence, and the current scanner boundary. Consult when analyzing or adding support for general Studio custom-item zipmods.
- `apps/docs/mod_manage/pose_zipmod_conversion.md`: Studio female `.dat` pose conversion to a `Kind=501` zipmod, Animator/AnimationClip template, bone-path mapping, validation results, and limitations. Consult when converting or troubleshooting Studio pose zipmods.
- `apps/docs/mod_manage/kk_animations_formaker_completion.md`: relationship between the full KK Animations archive and its ForMaker `Kind=501` registration patch, complete registration output, and gender-label boundary. Consult when extending or troubleshooting KK Animations ForMaker registration.
- `apps/docs/mod_manage/mod_exception_catalog.md`: current mod exception types, trigger conditions, UI titles, and repair actions. Consult when updating diagnostics or adding new repair flows.
- `apps/docs/assetstudio-helper.md`: C# AssetStudio helper location, JSON process boundary, initial commands, and integration rules. Consult when changing Unity resource browsing/export or helper packaging.
- `apps/docs/sb3utility-script.md`: SB3UtilityScript command-line grammar, Unity3D/Animator/MonoBehaviour script APIs, MainData modification, save verification, and GUI-script compatibility. Consult when calling SB3UtilityScript, modifying Unity3D resources through its DLLs, or diagnosing script execution failures.
- `apps/docs/sims4-fbx-gray-black-artifact-repair.md`: Sims 4 FBX 灰黑光照块的切线/法线诊断、MikkTSpace 修复与验证边界。
- `apps/docs/card-metadata-plugin.md`: companion HS2 BepInEx/HS2API plugin, registered ExtendedSave data contract, build/install steps, and character-card metadata persistence rules. Consult when changing favorites or other persistent card metadata.
- `apps/docs/game-item-probe.md`: HS2 BepInEx runtime item probe, `ChaListControl`/UniversalAutoResolver mapping, local IDs, endpoints, and right-click outfit integration boundary. Consult when changing game-side item identification or outfit synchronization.
- `apps/docs/game-card-loading.md`: selective character-card loading through the existing BepInEx probe, native `ChaFile` copy boundaries, endpoint contract, and verification limits. Consult when changing the character-card browser's game-loading tool.
- `apps/docs/character-card-read-probe.md`: independent character-card read auditing probe, Harmony method ownership, bone/material/texture snapshots, build instructions, and verification limits. Consult when investigating how the game reads character cards or which plugins participate.
- `apps/docs/unity3d-decryption-notes.md`: UnityFS/Sakuraba resource repair findings, BepInEx second-layer protection characteristics, the 57-byte wen SerializedFile wrapper with embedded resource-stream profiles (including `wenchenyinger`), the B002 base streamed-texture inline repair case, validation checklist, batch output rules, and isolation requirements. Consult when diagnosing or restoring encrypted Unity3D assets.
- `apps/skills/mod-unity3d-decryption/SKILL.md`: reusable project skill for classifying, recovering, and validating protected Unity3D mod assets with the project scripts and verified profiles. Consult when performing or automating mod decryption/recovery work.
- `apps/tools/assetstudio-helper/README.md`: AssetStudio helper commands, JSON output boundary, and supported operations. Consult when changing or invoking the helper.
- `apps/tools/star-manager-card-metadata-plugin/README.md`: card metadata plugin validation, build, installation, and runtime contract. Consult when changing or packaging the companion plugin.

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
- 每次解决关键问题后，必须在 `apps/docs/` 中记录问题背景、根因、解决方案、验证结果和适用边界；如果已有专题文档，应更新对应文档，否则新增文档，并同步更新 `apps/docs/README.md`、相关专题索引和本文件的项目文档清单。
