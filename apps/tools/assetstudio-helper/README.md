# Star Manager AssetStudio Helper

This isolated command-line helper reads Unity serialized files with AssetStudio and returns a stable JSON envelope on standard output. It does not automate or depend on AssetStudioGUI.

## Commands

```powershell
dotnet run --project apps/tools/assetstudio-helper -- list --input "sample.unity3d"
dotnet run --project apps/tools/assetstudio-helper -- list --input "sample.unity3d" --type Texture2D
dotnet run --project apps/tools/assetstudio-helper -- inspect --input "sample.unity3d" --path-id -123
dotnet run --project apps/tools/assetstudio-helper -- export-raw --input "sample.unity3d" --path-id -123 --output "asset.dat"
dotnet run --project apps/tools/assetstudio-helper -- export-text --input "sample.unity3d" --path-id -123 --output "asset.txt"
```

All responses have the form `{ "ok": true, "result": ... }` or `{ "ok": false, "error": ... }`. Diagnostics and progress must not be written to standard output because the Python backend will parse it as JSON.

The vendored AssetStudio source is from Perfare/AssetStudio at commit `d158e864b556b5970709c2a52e47944d53aa98a2` and remains under its MIT license. The first prototype intentionally supports metadata, raw export, and `TextAsset` export only. Texture, Sprite, audio, and Mesh conversion require AssetStudioUtility/native decoder packaging and are follow-up work.
