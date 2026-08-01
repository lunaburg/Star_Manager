# Card metadata BepInEx plugin

`apps/tools/star-manager-card-metadata-plugin/` contains the companion HS2
BepInEx plugin that formally registers the ExtendedSave data id
`star.manager.cardmetadata` with HS2API.

Consult this document when changing persistent character-card metadata, the
favorite storage format, the HS2API controller, plugin build references, or the
installation workflow.

## Current persistence design

Plugin version `1.4.2` implements the persistence design. Its governing rule
is:

> The character card already present at the final disk save path is the only
> authority for `star.manager.cardmetadata`. Game memory and cards used as
> appearance, hair, clothing, or coordinate sources are never authorities.

The final behavior is:

| Operation | Existing disk target | Saved metadata |
| --- | --- | --- |
| Overwrite a marked card | Entry exists | Preserve the complete original entry |
| Overwrite an unmarked card | Entry absent | Keep the entry absent |
| Import content from another card | Either | Ignore the source card's entry |
| Save to a new path | No target | Write no entry |
| `ChaFile.CopyChaFile` | Any | Block propagation; the disk snapshot is restored later if this is an overwrite |

The implementation intercepts writable `FileStream` construction because this
is the last common path used by all observed HS2 maker save flows. It runs
before `marco.RemoveToRecycleBin`, reads the old card while it still exists,
and holds only one operation-scoped snapshot. HS2 opens the same output path
multiple times; therefore the first normalized path capture is locked and all
later captures for that path are ignored until `CardBeingSaved` consumes it.
There is no cross-save or editing-session cache.

Version `1.4.2` normalizes both the captured disk target and
`ChaFile.charaFileName` to a leaf filename before comparison. This supports
cards stored in nested directories even when HS2 alternates between values such
as `cloth/古装/a/card.png` and `card.png`. `CardBeingSaved` consumes and clears
the pending snapshot before writing ExtendedSave data, so matching failure or a
later write exception cannot leave stale state that blocks subsequent captures.

The successful in-game round-trip validation of the original `1.4.1` root-card
flow on 2026-07-22 produced:

```text
Loading [Star Manager Card Metadata 1.4.1]
Card load metadata: star_manager_cardmetadata_favorite_test.png, present=True
Save target metadata: ...star_manager_cardmetadata_favorite_test.png, target=existing, present=True
Save target metadata: repeated path ignored: ...star_manager_cardmetadata_favorite_test.png
Save target metadata: repeated path ignored: ...star_manager_cardmetadata_favorite_test.png
Card save metadata: star_manager_cardmetadata_favorite_test.png, present=True, source=disk-target
```

The resulting card contained 14 fully decoded `KKEx` plugin entries and the
exact payload:

```text
star.manager.cardmetadata = [1, {"favorite": true}]
```

## Why the plugin is required

An unregistered entry can be inserted into the character-card `KKEx` map and
ExtendedSave can deserialize it. However, the HS2 character maker may save
through `ChaFile.CopyChaFile`. HS2API copies extended data through registered
controller handlers in that path, so an unknown entry is dropped while data
owned by installed plugins is recreated.

The companion plugin calls:

```csharp
CharacterApi.RegisterExtraBehaviour<CardMetadataController>(
    "star.manager.cardmetadata"
);
```

This formally establishes ownership of the id in HS2API. The controller itself
does not decide what to save; the disk-target handler is authoritative and
writes a fresh deep-cloned `PluginData` object during `CardBeingSaved`.

Version 1.4.2 treats the card already present at the final save path as the only
authoritative source. It patches every `FileStream` constructor containing both
`FileMode` and `FileAccess`, matching the interception point used by Remove
Cards To Recycle Bin. Only `FileMode.Create` writes to PNG files below
`UserData/chara/` are handled. `HarmonyPriority(Priority.First)` and
`HarmonyBefore("marco.RemoveToRecycleBin")` ensure the disk card is read before
the recycle-bin plugin can move it. The complete original payload,
including `cardId`, `favorite`, notes, tags, and future fields, is restored
during the matching save and the one-operation value is immediately cleared.
There is no cross-operation card or editing-session metadata cache.

If the disk target has no entry, the saved card has no entry. If the target
path is new, missing, unreadable, or does not match the `ChaFile` being saved,
the plugin removes untrusted incoming metadata. `ChaFile.CopyChaFile` is also
patched to clear this entry instead of propagating it. Star Manager is
therefore the only component that creates or changes the protected metadata.

HS2 may construct multiple writable `FileStream` instances for one save. The
first capture for a normalized target path is locked until `CardBeingSaved`
consumes it. Repeated constructors for the same path are logged as
`repeated path ignored`; they cannot replace an existing-card snapshot after
the recycle-bin plugin has moved the old file.

## Data contract

ExtendedSave stores one `PluginData` value as a two-element MessagePack array:

```text
[
  version,
  data
]
```

Favorite and rating metadata currently use schema version `1`:

```json
{
  "star.manager.cardmetadata": [
    1,
    {
      "favorite": true,
      "rating": 4,
      "tags": ["粉发", "礼服"]
    }
  ]
}
```

`rating` is an integer from `1` to `5`. Cards without a valid `rating` key are
treated as unrated. `tags` is an ordered array containing at most 12 distinct,
non-empty strings of at most 24 characters each. Cards without a valid `tags`
array are treated as untagged. Updating `favorite`, `rating`, or `tags`
preserves the other keys and every unknown/future field in the same dictionary.

The game plugin deliberately treats `data` as opaque. It clones the dictionary
without interpreting or removing keys, allowing Star Manager to add compatible
fields without requiring a plugin update. Keep values within the primitive,
string, byte-array, array, and map types supported by ExtendedSave's
MessagePack serializer.

## Runtime flow

```text
Card load
-> ExtendedSave decodes the complete KKEx map
-> the registered controller exposes the data without treating it as writable
-> direct CardBeingLoaded handler logs presence for diagnostics only

ChaFile.CopyChaFile
-> HS2API's registered basic copier transfers the PluginData entry
-> Harmony postfix removes the copied entry from the destination

Card save
-> game opens a character-card PNG with `FileMode.Create`
-> high-priority FileStream prefix reads metadata from the existing disk target
-> recycle-bin plugin may now move the old file
-> repeated FileStream constructors for the same path keep the first snapshot
-> direct CardBeingSaved handler normalizes both identities to leaf file names
-> consuming the snapshot immediately clears the operation state
-> matching disk-target metadata is restored without merging
-> missing, new, or mismatched targets remove untrusted incoming metadata
-> creates a fresh deep-cloned PluginData object
-> SetExtendedData writes it under the registered id
-> ExtendedSave serializes the complete KKEx map
-> the one-operation disk value is cleared

New save
-> FileStream target does not yet exist
-> record a known empty disk target
-> save the new card without `star.manager.cardmetadata`
```

Passing `null` to `SetExtendedData` removes the entry. A card without the entry
therefore remains unmarked.

## Build

From `apps/`:

```powershell
npm run test:card-plugin
npm run build:card-plugin
```

`test:card-plugin` runs four dependency-free plugin-state validations: nested
card directories, repeated `FileStream` captures, overwrite snapshot
restoration, and unconditional cleanup after a mismatched save. The build
command runs this validation before compiling the plugin.

The default references come from the repository's `test/hs2` installation. To
build against another HS2 installation:

```powershell
dotnet build tools/star-manager-card-metadata-plugin/StarManager.CardMetadata.csproj `
  --configuration Release `
  -p:GameDir="D:\path\to\HoneySelect2"
```

Output:

```text
apps/tools/star-manager-card-metadata-plugin/bin/Release/net472/StarManager.CardMetadata.dll
```

## Install and verify

Copy the DLL to:

```text
<HoneySelect2>/BepInEx/Plugins/StarManager/StarManager.CardMetadata.dll
```

HS2API and `HS2_ExtensibleSaveFormat.dll` are hard dependencies. On game
startup, `BepInEx/LogOutput.log` should contain:

```text
Registered ExtendedSave data ID: star.manager.cardmetadata
```

The installed DLL version must report `1.4.2.0`. The actual HS2 runtime log can
also be found at:

```text
%USERPROFILE%\AppData\LocalLow\illusion__HoneySelect2\HoneySelect2\output_log.txt
```

Round-trip verification should cover both character-maker overwrite and save
as a new card:

1. Write `favorite=true` into a card while the game is closed.
2. Load the card in the character maker and overwrite it.
3. Confirm the entry remains in `KKEx`.
4. Partially load appearance or clothing from a differently marked card.
5. Confirm the target card retains its own complete metadata unchanged.
6. Repeat with an originally unmarked target and confirm it remains unmarked.
7. Save to a new path and confirm the new card has no metadata until Star
   Manager explicitly marks it.

The disk target is read immediately before its write stream is created. This
keeps the interval between Star Manager's disk state and the game save as short
as possible.

## Manager integration

Star Manager reads and writes favorites and ratings exclusively through the
registered `star.manager.cardmetadata` entry in `KKEx`. Cards without that
entry are unfavorited and unrated. Cover replacement copies the appended card
payload byte-for-byte, so the metadata survives without being recreated.
