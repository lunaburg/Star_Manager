# Character card parsing notes

This document records the current understanding of HS2/AIS character-card PNG parsing in Star_Manager. Consult it when changing card dependency extraction, card detail views, missing-mod diagnostics, or scripts that inspect `UserData/chara/**/*.png`.

## Scope

HS2/AIS character cards are PNG files with game data appended after the PNG `IEND` chunk. The appended payload can be inspected without modifying the card file.

Current implementation and probe script:

- `apps/backend/star_manager/core/card_parser.py`: lightweight AIS marker and `ModID` GUID extraction.
- `apps/scripts/analyze_character_card.py`: exploratory full decode script for card structure, MessagePack sections, and UniversalAutoResolver records.

Example:

```powershell
python apps\scripts\analyze_character_card.py test\hs2\UserData\chara\female\hhh2.png --limit 1 --json apps\backend\runtime\hhh2_card_full_decode.json
```

## Outer PNG layout

The parser should treat the visible PNG image and the appended card data separately.

```text
PNG bytes
`-- IEND chunk
    `-- appended AIS card payload
```

The current lightweight parser finds the `IEND` marker and returns bytes after it. The returned slice intentionally includes the IEND CRC bytes because the card reader skips an initial 8-byte block before reading the AIS marker.

For `hhh2.png`, the appended payload begins with:

```text
ae 42 60 82 64 00 00 00 ...
```

The first 4 bytes are the PNG IEND CRC. The next 4 bytes are skipped with it by the current reader.

## Card header

After the initial 8 bytes, the card uses .NET-style 7-bit length-prefixed UTF-8 strings.

Observed `hhh2.png` header:

```text
marker: 【AIS_Chara】
version: 1.0.0
unknown_int32: 0
card_id: 3adf5278-8db1-4b41-9647-20db5d13c069
user_id: bfd13730-a0e6-4ded-a903-3456208eb09a
info_size: 352
info_offset: 112
```

Known AIS card markers:

```text
【AIS_Chara】
【AIS_Clothes】
```

## Block table

At `info_offset`, a MessagePack object stores a block directory:

```text
{
  "lstInfo": [
    { "name": "...", "version": "...", "pos": 0, "size": 0 }
  ]
}
```

Important detail: `pos` is relative to the block-data base, not to the file or appended payload start. The block-data base is:

```text
info_offset + consumed_size_of_lstInfo_messagepack
```

Observed `hhh2.png` block table:

```text
KKEx        version 3      size 2018087
Custom      version 0.0.0  size 4591
Coordinate  version 0.0.0  size 16736
Parameter   version 0.0.1  size 125
GameInfo    version 0.0.0  size 553
Status      version 0.0.0  size 842
Parameter2  version 0.0.0  size 86
GameInfo2   version 0.0.0  size 560
```

## Block contents

Blocks are not always a single MessagePack object from byte zero. Several blocks contain small prefixes, length fields, or multiple MessagePack fragments. The analysis script currently scans each block for meaningful MessagePack objects and records offsets, sizes, keys, and compact samples.

Observed high-level contents:

```text
Custom
  Face/body custom data, including face IDs, skin IDs, makeup/color fields, hair custom entries.

Coordinate
  Outfit coordinate data. Includes clothing parts and accessory entries.

Parameter / Parameter2
  Character profile and personality-like fields.

GameInfo / GameInfo2
  Gameplay state fields.

Status
  Current status, clothing state, accessory visibility, eye/mouth/look state.

KKEx
  Plugin extension data. This is the most important block for sideloader dependency records.
```

`Coordinate` is especially relevant for card detail views because it includes clothing parts and accessory entries. `KKEx` is especially relevant for dependency extraction because it contains plugin-owned resolver metadata.

## Character profile fields

Basic character identity/profile fields are stored in the `Parameter` block. Offsets reported by `apps/scripts/analyze_character_card.py` are offsets within that block, not absolute file offsets. The block itself is located by the block table.

Observed `hhh2.png` `Parameter` block:

```json
{
  "name": "Parameter",
  "version": "0.0.1",
  "pos": 21327,
  "absolute_pos": 21791,
  "size": 125,
  "object_count": 7
}
```

Observed profile field keys in `hhh2.png`:

```text
fullname
  Character display/full name.
  Observed block offset: 28

personality
  Personality id.
  Observed block offset: 44

birthMonth
  Birthday month.
  Observed block offset: 57

birthDay
  Birthday day.
  Observed block offset: 69

voiceRate
  Voice pitch/rate value.
  Observed block offset: 79

hsWish
  A 3-item numeric list observed in `Parameter`.
  Observed block offset: 101
  Semantic meaning is not yet confirmed.

futanari
  Boolean-like character attribute flag.
  Observed block offset: 105
```

Observed decoded `hhh2.png` values:

```text
fullname: 111111
sex: 1
personality: 5
birthMonth: 1
birthDay: 1
voiceRate: 0.5
hsWish: [2, 5, 11]
futanari: false
```

HS2 may retain an older personality id in `Parameter.personality` while writing
the personality selected in-game to `Parameter2.personality`. Production card
detail parsing therefore treats `Parameter2.personality` as authoritative when
present and falls back to `Parameter.personality` for cards without that field.

Personality ids use the following game UI order (left-to-right, then
top-to-bottom):

```text
0 酷妹      1 标准
2 御姐      3 女友
4 辣妹      5 弱妹
6 人妻      7 女王
8 腐女      9 正妹
10 认真妹   11 软妹纸
12 正太     13 病娇
```

Do not expose `hsWish` in UI as a named business field until it is verified against additional cards or upstream HS2 field definitions.

Implementation note: the current exploratory scanner records individual MessagePack fragments. For production parsing, prefer decoding the complete `Parameter` map from the correct internal object offset so field names and values stay paired, instead of interpreting isolated key strings.

## UniversalAutoResolver dependency records

Concrete mod dependency records were found in `KKEx` under plugin id:

```text
com.bepis.sideloader.universalautoresolver
```

That plugin payload contains an `info` list. Each `info` entry is a nested MessagePack byte array. Decode each entry again to get one dependency record.

Observed record shape:

```json
{
  "ModID": "higeo.FaceMod",
  "Slot": 702,
  "LocalSlot": 100015713,
  "Property": "ChaFileFace.hlId",
  "CategoryNo": 319,
  "Author": "higeo",
  "Website": null,
  "Name": "higeo FaceMod"
}
```

Field meanings:

```text
ModID
  Sideloader/manifest-level mod identifier. Use this to find the owning zipmod.

CategoryNo
  HS2 list category number. Use together with Slot or LocalSlot when mapping to CSV item rows.

Slot
  Original item slot/id recorded for that category. This is the preferred field for matching back to zipmod CSV item ids when available.

LocalSlot
  Sideloader-assigned local runtime id. It avoids conflicts in the local game environment and often appears as the effective id saved in the card.

Property
  Card property that uses the item, such as hair, face, body, clothing, or outfit fields.

Author / Name / Website
  Metadata copied into the resolver record. Useful for display and fallback diagnostics, but database matches should prefer ModID and item ids.
```

For dependency mapping, prefer this matching order:

```text
1. ModID -> zipmods.guid
2. CategoryNo + Slot -> mod_items kind/item id mapping, if the CSV item id uses the original slot
3. CategoryNo + LocalSlot -> fallback for locally remapped ids
4. Author/Name -> display-only fallback, not a stable key
```

## CategoryNo mapping

`CategoryNo` is the HS2 list category number. It identifies the body region, clothing category, accessory category, or makeup category that a dependency record targets. It should be displayed as a category label, while `Slot` and `LocalSlot` identify the concrete item within that category.

Known mappings from the mod item Kind table:

```text
140 男 mod / 上衣
141 男 mod / 下衣
144 男 mod / 手套
147 男 mod / 鞋子
210 脸模
211 脸部肌肤
212 脸部皱纹 / 脸部细节
231 身体肌肤
232 肉感
240 女 mod / 上衣
241 女 mod / 下衣
242 女 mod / 内衣
243 女 mod / 内裤
244 女 mod / 手套
245 女 mod / 裤袜
246 女 mod / 袜子
247 女 mod / 鞋子
300 头发 / 后发
301 头发 / 前发
302 头发 / 鬓发
303 头发 / 侧发
313 人体彩绘
314 眉毛
315 睫毛
316 眼影
317 美瞳 / 眼睛种类
319 眼睛高光
322 口红
334 乳头
335 阴毛
348 图案
351 饰品 mod / 头部
352 饰品 mod / 耳朵
353 饰品 mod / 眼镜
354 饰品 mod / 脸部
355 饰品 mod / 脖子
356 饰品 mod / 肩部
357 饰品 mod / 胸部
358 饰品 mod / 腰部
359 饰品 mod / 后背
360 饰品 mod / 胳膊
361 饰品 mod / 手部
362 饰品 mod / 脚
363 饰品 mod / 腹部下
```

Additional mappings inferred from card resolver `Property` values and sample `ModID`/`Name` values:

```text
8   身体彩绘布局
110 男性脸模
111 男性脸部肌肤
112 男性脸部细节
121 胡子
131 男性身体肌肤
132 男性身体细节
133 男性身体晒痕
233 女性身体晒痕
318 瞳孔 / 黑眼
320 腮红
323 痣 / 雀斑
```

Inference basis:

```text
8
  Property: ChaFileBody.PaintLayoutID1, ChaFileBody.PaintLayoutID2
  Example: com.toshiaki.bodypaint_layout_abdomen / bodypaint_layout_abdomen

110
  Property: ChaFileFace.headId
  Examples: KKY.femaleface4male, Leon S. Kennedy, sjjpl.Headless

111
  Property: ChaFileFace.skinId
  Example: k1t0k1tn.baseface.MALE.smooth

112
  Property: ChaFileFace.detailId
  Example: k1t0k1tn.dimples.male

121
  Property: ChaFileFace.beardId
  Example: k1t0k1tn.bushy.beards

131
  Property: ChaFileBody.skinId
  Example: k1t0k1tn.MALE-hd-body-lighthairy

132
  Property: ChaFileBody.detailId
  Example: K1T0-K1TN UHD Body Hairy Male 2 Build

133
  Property: ChaFileBody.sunburnId
  Example: metaru.pfreckles.paint02 / natural freckles

233
  Property: ChaFileBody.sunburnId
  Female-body range counterpart to 133.

318
  Property: ChaFileFace.EyeBlack1, ChaFileFace.EyeBlack2
  Example: K1T0-K1TN Pupils 1

320
  Property: MakeupInfo.cheekId
  Examples: Joecheek, Darkruler.Lightning, com.chw.owmakeup

323
  Property: ChaFileFace.moleId
  Example: k1t0k1tn.softer-freckles
```

Observed numbering pattern:

```text
110-133  mostly male face/body categories
210-233  mostly female face/body categories
31x-32x  face makeup and eye-detail categories
35x-36x  accessory attachment categories
```

Validation script:

```powershell
python apps\scripts\summarize_card_category_parts.py test\hs2\UserData\chara --json apps\backend\runtime\card_category_parts_summary.json
```

## hhh2.png decoded dependency sample

The probe decoded 14 UniversalAutoResolver item records from `hhh2.png`.

```text
ChaFileFace.eyebrowId
  CategoryNo: 314
  Slot: 703
  LocalSlot: 100005246
  ModID: aquan.eyelesh
  Name: test

ChaFileFace.eyelashesId
  CategoryNo: 315
  Slot: 31536
  LocalSlot: 100013419
  ModID: eyelashe
  Name: eyelashes

ChaFileFace.hlId
  CategoryNo: 319
  Slot: 702
  LocalSlot: 100015713
  ModID: higeo.FaceMod
  Name: higeo FaceMod

ChaFileFace.detailId
  CategoryNo: 212
  Slot: 666107
  LocalSlot: 100017690
  ModID: k1t0k1tn.smiles.female
  Name: K1T0-K1TN Smiles female

ChaFileFace.skinId
  CategoryNo: 211
  Slot: 29
  LocalSlot: 100006302
  ModID: com.3dh9527.newmakeupskin
  Name: [3dh9527] NewMakeupSkin

ChaFileHair.HairBack
  CategoryNo: 300
  Slot: 2
  LocalSlot: 100002214
  ModID: [sakuraba]24-12-s02
  Name: [sakuraba]24-12-s02

MakeupInfo.lipId
  CategoryNo: 322
  Slot: 301
  LocalSlot: 100016503
  ModID: Joelips
  Name: Joelips

outfit.ChaFileClothes.ClothesTop
  CategoryNo: 240
  Slot: 13680
  LocalSlot: 100002216
  ModID: [sakuraba]24-12-s02
  Name: [sakuraba]24-12-s02

outfit.ChaFileClothes.ClothesShoes
  CategoryNo: 247
  Slot: 152133
  LocalSlot: 100002169
  ModID: [sakuraba]23-12-s01
  Name: [sakuraba]23-12-s01
```

## Current limitations

- The production parser currently extracts `ModID` GUIDs with a byte scan. It does not yet expose full block structures or UniversalAutoResolver item records through backend APIs.
- The analysis script is intentionally exploratory. It summarizes binary fields instead of preserving every byte in JSON.
- Some cards may not contain UniversalAutoResolver data, or may contain plugin records with different schemas.
- `Slot` and `LocalSlot` mapping to `mod_items` should be validated against real zipmod CSV rows before presenting item-level dependency status as authoritative.

## Implementation direction

When moving this from script to backend service:

```text
1. Keep read-only PNG parsing in backend/star_manager/core/card_parser.py or a nearby card-specific module.
2. Return both GUID-level dependencies and item-level UniversalAutoResolver records.
3. Resolve ModID through zipmods.guid.
4. Resolve item records through CategoryNo + Slot/LocalSlot against mod_items.
5. Surface missing zipmods separately from missing item rows.
6. Keep batch extraction under /tasks; use direct HTTP only for single-card detail reads.
```
