# Star Manager Card Metadata plugin

This BepInEx plugin formally registers the ExtendedSave data id
`star.manager.cardmetadata` with HS2API and prevents game-side card operations
from changing Star Manager-owned metadata.

The verified rule is that the existing card at the final disk save path is the
only metadata authority. Imported cards and in-memory `ChaFile` state are never
allowed to change the target card's entry. See
`apps/docs/card-metadata-plugin.md` for the final behavior matrix, runtime flow,
and the round-trip evidence.

Version 1.4.2 treats the card already present at the final save path as the only
authoritative source. It patches the same writable `FileStream` constructors as
the Remove Cards To Recycle Bin plugin, with higher priority and an explicit
Harmony ordering constraint. Before `FileMode.Create` can move or overwrite an
existing character-card PNG, the complete metadata payload is read once,
restored during the matching save event, and then discarded. New paths and
saves without a matching disk target receive no metadata. Game-side
`ChaFile.CopyChaFile` operations are explicitly prevented from propagating this
entry.

HS2 constructs more than one writable `FileStream` for the same card save.
Only the first capture for a normalized path is accepted; later constructors
for that path are ignored until `CardBeingSaved` consumes and clears the
one-operation snapshot. This prevents the recycle-bin move between constructors
from turning an existing marked target into a false new-target result.

Save-target paths and `ChaFile.charaFileName` are both reduced to normalized
leaf file names before matching, so cards in nested directories such as
`female/cloth/古装/a/card.png` match both relative and filename-only game state.
Every `CardBeingSaved` event consumes and clears the pending snapshot whether
the names match or not, preventing a failed comparison from poisoning later
saves.

## Validate

From `apps/`:

```powershell
npm run test:card-plugin
```

The dependency-free validation executable covers nested card paths, repeated
`FileStream` construction, overwrite snapshot restoration, and cleanup after a
mismatched save.

## Build

From `apps/`:

```powershell
npm run build:card-plugin
```

The project uses `test/hs2` as its default reference game. To build against a
different installation:

```powershell
dotnet build tools/star-manager-card-metadata-plugin/StarManager.CardMetadata.csproj `
  --configuration Release `
  -p:GameDir="D:\path\to\HoneySelect2"
```

## Install

Copy the built `StarManager.CardMetadata.dll` to:

```text
<HoneySelect2>/BepInEx/Plugins/StarManager/StarManager.CardMetadata.dll
```

The game installation must also contain working HS2API and ExtendedSave
plugins. After launch, the BepInEx log should contain:

```text
Registered ExtendedSave data ID: star.manager.cardmetadata
```

The plugin has no UI. Star Manager owns the payload schema and writes the
`PluginData`; this plugin preserves the payload without interpreting it.
