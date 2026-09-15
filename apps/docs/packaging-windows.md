# Windows Packaging Guide

This document records the current Windows packaging flow for the maintained Electron/Vue/Python Star_Manager app.

## Output

The standard packaging command creates an unpacked Windows application directory:

```text
apps/release/win-unpacked/
|-- Star_Manager.exe
|-- resources/
|   |-- app.asar
|   `-- backend/
|       `-- star_manager_backend.exe
`-- Electron runtime files...
```

Run `apps/release/win-unpacked/Star_Manager.exe` to start the packaged app.

The Python backend executable is also built separately at:

```text
apps/build/backend/star_manager_backend.exe
```

Runtime cache files created by the packaged app are stored next to `Star_Manager.exe`:

```text
apps/release/win-unpacked/runtime/
|-- remote/
|   `-- remote_zipmod_index.sqlite  # bundled read-only remote mod index
|-- star_manager.sqlite
|-- ais_card_cache.json
|-- thumbnails/
|-- card_previews/
|-- model_previews/          # normal app exit clears this preview cache
|-- unity3d_open/            # extracted copies for external tools
`-- unity3d_preprocessed/    # workbench-derived Unity3D outputs
```

The complete cache, temporary-file, and cleanup registry is maintained in [缓存与运行时文件登记](runtime-cache-registry.md). In particular, `star_manager.sqlite` also contains local achievement state and must not be treated as a disposable image cache.

The packaged output includes only the remote mod index at `runtime/remote/remote_zipmod_index.sqlite`. The source file is `apps/backend/runtime/remote/remote_zipmod_index.sqlite`; `package:win` checks that it exists, packages the app, then resets the release `runtime/` directory and stages the remote index. Local databases, settings, caches, previews, thumbnails, and trash from a previous launch are therefore cleared from every new package. Other runtime files are created by the application on first use.

The release package intentionally excludes the Python backend source/vendor tree and Node modules. The packaged Electron main process starts `resources/backend/star_manager_backend.exe`, while Vite has already bundled the Vue, Three.js and Lottie renderer code into `dist`. Only `en-US` and `zh-CN` Electron locale files are included.

## Prerequisites

- Windows.
- Node dependencies installed under `apps/node_modules`.
- A Python environment with the backend dependencies and PyInstaller installed. Install backend dependencies with:

```powershell
cd apps
D:\desktop_app\anaconda\envs\mm_env\python.exe -m pip install -r backend\requirements.txt
```
- By default, `apps/scripts/python.cjs` uses:

```text
D:\desktop_app\anaconda\envs\mm_env\python.exe
```

To use another interpreter for the packaging step, set `PYTHON_EXECUTABLE` before running the build:

```powershell
cd apps
$env:PYTHON_EXECUTABLE="D:\path\to\python.exe"
npm run package:win
```

## Standard Packaging Command

From the repository root:

```powershell
cd apps
npm run package:win
```

This script runs three stages:

1. `npm run build`

   Builds the Vue renderer with Vite into `apps/dist`.

2. `npm run build:backend`

   Runs PyInstaller through `apps/scripts/python.cjs` and creates `apps/build/backend/star_manager_backend.exe`.

3. `electron-builder --win dir --config.electronDist=node_modules/electron/dist`

   Packages the Electron app as an unpacked Windows directory in `apps/release/win-unpacked`.

The packaging configuration lives in the `build` field of `apps/package.json`. The packaged app includes:

- `dist/**/*`
- `electron/**/*`
- `build-resources/**/*`
- no `node_modules` or Python backend source/vendor files
- `package.json`
- `build/backend/star_manager_backend.exe` as `resources/backend/star_manager_backend.exe`
- `backend/runtime/remote/**/*` as `runtime/remote/**/*` (the read-only remote mod index)

## Verification

After packaging, confirm the expected files exist:

```powershell
Test-Path .\release\win-unpacked\Star_Manager.exe
Test-Path .\release\win-unpacked\resources\backend\star_manager_backend.exe
Test-Path .\release\win-unpacked\runtime\remote\remote_zipmod_index.sqlite
Test-Path .\release\win-unpacked\resources\app.asar.unpacked\node_modules
Get-ChildItem .\release\win-unpacked\runtime -Recurse -File | Select-Object -ExpandProperty FullName
```

The second command should return `False`; it confirms that Node modules were not copied into the release app. The final command should list only `runtime\remote\remote_zipmod_index.sqlite` immediately after packaging.

The package does not include or reset the user's external Electron settings under `%APPDATA%\star-manager\settings.json`; those settings are outside the release directory and must not be deleted during packaging.

Then perform a smoke launch:

```powershell
$exe = Resolve-Path ".\release\win-unpacked\Star_Manager.exe"
$p = Start-Process -FilePath $exe -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 6
if ($p.HasExited) { throw "Packaged app exited early with code $($p.ExitCode)" }
Stop-Process -Id $p.Id -Force
```

If the command reaches `Stop-Process`, the packaged Electron main process started successfully.

To audit packaged dependencies, run:

```powershell
npm run check:package-deps
```

This checks three dependency classes:

- PE dynamic imports from packaged `.exe`, `.dll`, and `.pyd` files. Windows system DLLs and files already present under `release/win-unpacked` are treated as resolved.
- PyInstaller missing-module warnings from `build/pyinstaller/star_manager_backend/warn-star_manager_backend.txt`, with common platform and optional-package noise filtered out.
- Static libraries (`.lib` and `.a`) accidentally present in the packaged app. Static libraries are build-time inputs and normally should not ship with the unpacked app.

The backend package explicitly collects Pillow, UnityPy, `texture2ddecoder`, `etcpak`, `astc_encoder`, `fmod_toolkit`, `archspec`, XML/expat support, and required Conda runtime DLLs. Runtime Python package requirements are recorded in `backend/requirements.txt`. `archspec` is required at runtime by texture decoder CPU-dispatch code; missing `archspec/json/cpu/microarchitectures.json` causes packaged thumbnail extraction to fail even though the Python modules import correctly.

## Runtime Backend Resolution

In a packaged app, `electron/main.cjs` prefers:

```text
resources/backend/star_manager_backend.exe
```

If `STAR_MANAGER_BACKEND_EXE` is set, that executable path takes priority. In development, or if no backend executable is present, the app falls back to a Python interpreter and starts `backend/app/server.py`.

Electron also passes `STAR_MANAGER_RUNTIME_DIR` to the backend. Packaged builds set it to the `runtime` folder beside `Star_Manager.exe`; development builds set it to `apps/backend/runtime`.

## Notes and Known Warnings

- The current `package:win` target is `dir`, so it creates an unpacked app folder rather than a single installer.
- `electron-builder` may warn that `author` is missing in `apps/package.json`; this does not block the unpacked build.
- `apps/scripts/python.cjs` explicitly includes `pyexpat`, `xml.parsers.expat`, `PIL`, `UnityPy`, the Sims 4 `ts4_reference_rig.fbx` plus its Blender T-pose baking helper, `fmod_toolkit`'s `fmod.dll`, and available Conda runtime DLLs needed by XML parsing, compressed standard-library modules, Unity3D thumbnail extraction, and Package FBX export. This avoids packaged-backend failures such as `No module named expat; use SimpleXMLTreeBuilder instead` while reading `manifest.xml`, `UnityPy is not available`, missing TS4 pose resources, and frozen-runtime `fmod.dll` errors while extracting thumbnails.
- PyInstaller may still report optional platform modules as missing in `apps/build/pyinstaller/star_manager_backend/warn-star_manager_backend.txt`. Treat these as packaging warnings unless the backend executable fails to launch or backend features fail at runtime.
- The default Electron icon is used unless an application icon is added to the `build.win` configuration.
