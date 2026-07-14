# AssetStudio Helper

`apps/tools/assetstudio-helper/` is an isolated C# command-line process for inspecting Unity serialized assets. It references the vendored AssetStudio parser core and emits a stable JSON response for later use by the Python backend.

The initial protocol supports resource listing, metadata inspection, raw export, and `TextAsset` export. It deliberately does not expose an HTTP server: Star Manager should launch it as a bounded child process, enforce timeouts, and parse standard output. Single-resource export can later use a direct HTTP route; batch export must use `/tasks`.

Consult this document when changing the C# parser, its JSON contract, packaging, or the future Python integration.
