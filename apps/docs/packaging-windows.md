# Windows Packaging Guide

This document records the current Windows packaging flow for the maintained Electron/Vue/Python Star_Manager app.

## English build verification (2026-10-29)

The English/Chinese application was successfully packaged with `npm run package:win` on branch `English-translation`. Outputs:

- `apps/release/win-unpacked/Star_Manager.exe`, with its accompanying runtime/resources files.
- `apps/release/Star_Manager-English-win-x64.zip` (155,115,355 bytes), containing the entire `win-unpacked` directory. Extract the whole directory before launching; the executable is not standalone.

The checkout initially lacked a Python build environment, a complete Electron runtime, and the required remote index. A local `apps/.venv` was created with `uv venv --python 3.11 .venv`; backend requirements and PyInstaller were installed using `uv pip install --python .venv/Scripts/python.exe -r backend/requirements.txt pyinstaller`. Set `PYTHON_EXECUTABLE` to this environment's absolute `Scripts/python.exe` path when rebuilding.

Electron 35.7.5's official `electron-v35.7.5-win32-x64.zip` was verified against the SHA-256 in the installed Electron package's `checksums.json` and extracted into `apps/node_modules/electron/dist`; `path.txt` identifies `electron.exe`. This completed the distribution left incomplete by the npm install step.

The remote index was recovered from the project's [V0.0.3 release archive](https://github.com/lunaburg/Star_Manager/releases/download/V0.0.3/Star_Manager.rar), extracting only `Star_Manager/runtime/remote/remote_zipmod_index.sqlite` into the existing packaging input location. SQLite `integrity_check` returned `ok`; the index has 12,979 records, including 12,978 valid manifests and one pre-existing `read_error`. Its SHA-256 is `8b3305f1cb15bdbc194d693a4250ce93a835a0097f47a0975a605fc72b071e0f`. This reuses the upstream snapshot rather than fabricating an empty index or claiming a new complete remote scan.

Validation: Python syntax checks, strict translation coverage and all 9 localization tests passed. The ASAR contains the shared localization module, English catalog and built renderer. A smoke launch of the actual packaged executable reached `renderer-ready`, `first-screen-shown` and `did-finish-load`; its packaged backend returned `ok: true` from `/health` on isolated port 18765, with all reported resource modules available and `fmod_dll_exists: true`. The test processes were stopped, then `clean_packaged_runtime.cjs` reset only the release runtime directory before ZIP creation. Existing external user settings were preserved; no game directory was configured and no game/resource mutation was tested.

The dependency audit passes when Windows' system DLL directory is included:

```powershell
.venv/Scripts/python.exe scripts/check_package_deps.py --extra-search-path "$env:WINDIR/System32"
```

Without that explicit search path, the current audit reports the companion plugins' `mscoree.dll` dependency as missing; both Windows system copies were verified to exist. PyInstaller's `fmod.dll` ctypes warning did not represent a missing bundled file: the DLL was explicitly collected and the packaged health check verified it. Other reported missing modules were classified as optional/platform noise. Vite's existing Lottie `eval` and bundle-size warnings and Electron Builder's missing-author warning remain non-blocking.

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

This script runs four stages:

1. `npm run stage:plugins`

   Synchronizes newer Release outputs from
   `tools/star-manager-*/bin/Release/net472/` into `tools/StarManager/`, the
   directory consumed by Electron Builder. This is the step that prevents a
   newly compiled `GameItemProbe` from being left out of the package. A lower
   versioned build output never downgrades an existing bundled DLL.

2. `npm run build`

   Builds the Vue renderer with Vite into `apps/dist`.

3. `npm run build:backend`

   Runs PyInstaller through `apps/scripts/python.cjs` and creates `apps/build/backend/star_manager_backend.exe`.

4. `electron-builder --win dir --config.electronDist=node_modules/electron/dist`

   Packages the Electron app as an unpacked Windows directory in `apps/release/win-unpacked`.

The packaging configuration lives in the `build` field of `apps/package.json`. The packaged app includes:

- `dist/**/*`, including the Vite-bundled `dist/assets/wallpaper-default-<hash>.mp4` used as the default application wallpaper
- `electron/**/*`
- `build-resources/**/*`
- no `node_modules` or Python backend source/vendor files
- `package.json`
- `build/backend/star_manager_backend.exe` as `resources/backend/star_manager_backend.exe`
- `backend/runtime/remote/**/*` as `runtime/remote/**/*` (the read-only remote mod index)
- `tools/StarManager/*.dll` as `resources/StarManager/*.dll` (the three manager companion plugins)

The three bundled plugins are installed by the Electron main process into the selected
game directory's `BepInEx/Plugins/StarManager/` folder. Each check compares the bundled
DLL's Windows assembly file version with the installed DLL. A mismatched version is
replaced; when file-version metadata cannot be read, the SHA-256 file hash is used as
the fallback comparison. The same comparison applies to disabled `.dl_` and historical
`.dll.disabled` files, and replacement keeps the disabled filename so a user's disabled
state is preserved. Symbolic-link targets are rejected. The check runs when a game
directory is selected and when the saved directory is restored at application startup.
Missing `BepInEx` and `Plugins/StarManager` directories are created as needed. The
installation result reports separate counts for newly installed and updated plugins.

The bundled release inputs currently report these file versions:

| DLL | File version |
| --- | --- |
| `StarManager.CardMetadata.dll` | `1.4.2.0` |
| `StarManager.CharacterCardReadProbe.dll` | `0.2.0.0` |
| `StarManager.GameItemProbe.dll` | `0.9.6.0` |

## Verification

After packaging, confirm the expected files exist:

```powershell
Test-Path .\release\win-unpacked\Star_Manager.exe
Test-Path .\release\win-unpacked\resources\backend\star_manager_backend.exe
Test-Path .\release\win-unpacked\runtime\remote\remote_zipmod_index.sqlite
Test-Path .\release\win-unpacked\resources\StarManager\StarManager.CardMetadata.dll
Test-Path .\release\win-unpacked\resources\StarManager\StarManager.CharacterCardReadProbe.dll
Test-Path .\release\win-unpacked\resources\StarManager\StarManager.GameItemProbe.dll
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
