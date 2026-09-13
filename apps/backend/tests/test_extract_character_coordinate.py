from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from star_manager.core import coordinate_card as converter
from star_manager.core.card_parser import unpack_msgpack


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def make_preview_png() -> bytes:
    width, height = 252, 352
    rows = b"".join(b"\x00" + b"\x00" * (width * 3) for _ in range(height))
    return b"".join(
        [
            converter.PNG_SIGNATURE,
            png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            png_chunk(b"IDAT", zlib.compress(rows)),
            png_chunk(b"IEND", b""),
        ]
    )


def make_coordinate_payload() -> bytes:
    clothes = {
        "version": "0.0.0",
        "parts": [{"id": index} for index in range(8)],
        "ExtendedSaveData": None,
    }
    accessories = {
        "version": "0.0.0",
        "parts": [
            {"type": 350, "id": 0, "parentKey": ""} for _ in range(20)
        ],
        "ExtendedSaveData": None,
    }
    clothes_blob = converter.pack_msgpack(clothes)
    accessories_blob = converter.pack_msgpack(accessories)
    return (
        struct.pack("<I", len(clothes_blob))
        + clothes_blob
        + struct.pack("<I", len(accessories_blob))
        + accessories_blob
    )


def make_character_card() -> bytes:
    coordinate = make_coordinate_payload()
    clothes_record = converter.pack_msgpack(
        {
            "ModID": "example.clothes",
            "Slot": 1,
            "LocalSlot": 100000001,
            "Property": "outfit.ChaFileClothes.ClothesTop",
            "CategoryNo": 240,
        }
    )
    face_record = converter.pack_msgpack(
        {
            "ModID": "example.face",
            "Slot": 2,
            "LocalSlot": 100000002,
            "Property": "ChaFileFace.headId",
            "CategoryNo": 210,
        }
    )
    kkex = converter.pack_msgpack(
        {
            converter.UAR_PLUGIN_ID: [0, {"info": [clothes_record, face_record]}],
            converter.ACCESSORY_CONTROLS_PLUGIN_ID: [
                0,
                {
                    "accessoryData": converter.pack_msgpack([[False, 0]]),
                    "overrideData": converter.pack_msgpack([[], []]),
                },
            ],
            "orange.spork.outfitpainter": [0, {"OutfitPainterData": b"\x90"}],
            "example.character.only": [0, {"value": True}],
        }
    )
    block_data = coordinate + kkex
    table = converter.pack_msgpack(
        {
            "lstInfo": [
                {
                    "name": "Coordinate",
                    "version": "0.0.0",
                    "pos": 0,
                    "size": len(coordinate),
                },
                {
                    "name": "KKEx",
                    "version": "3",
                    "pos": len(coordinate),
                    "size": len(kkex),
                },
            ]
        }
    )
    appended = b"".join(
        [
            struct.pack("<I", converter.CARD_ENVELOPE_VERSION),
            converter.pack_dotnet_string(converter.CHARACTER_MARKER),
            converter.pack_dotnet_string("1.0.0"),
            struct.pack("<I", 0),
            converter.pack_dotnet_string("card-id"),
            converter.pack_dotnet_string("user-id"),
            struct.pack("<I", len(table)),
            table,
            struct.pack("<Q", len(block_data)),
            block_data,
        ]
    )
    return make_preview_png() + appended


def test_parse_coordinate_payload_parts_keeps_category_source_fields():
    parsed = converter.parse_coordinate_payload_parts(make_coordinate_payload())

    assert parsed["clothes_parts"][0] == {"slot": 0, "id": 0}
    assert parsed["clothes_parts"][7] == {"slot": 7, "id": 7}
    assert parsed["accessory_parts"][0] == {"slot": 0, "type": 350, "id": 0}


def read_generated_plugins(card_bytes: bytes) -> dict:
    payload = card_bytes[converter.find_png_end(card_bytes) :]
    _, cursor = converter.read_dotnet_string(payload, 4)
    _, cursor = converter.read_dotnet_string(payload, cursor)
    _, cursor = converter.read_dotnet_string(payload, cursor + 4)
    coordinate_size = int.from_bytes(payload[cursor : cursor + 4], "little")
    cursor += 4 + coordinate_size
    _, cursor = converter.read_dotnet_string(payload, cursor)
    extension_size = int.from_bytes(payload[cursor + 4 : cursor + 8], "little")
    plugins, end = unpack_msgpack(payload, cursor + 8)
    assert end == cursor + 8 + extension_size
    return plugins


def test_convert_character_card_filters_dependencies_and_adapts_plugins(tmp_path: Path):
    source = tmp_path / "character.png"
    output = tmp_path / "coordinate.png"
    source.write_bytes(make_character_card())

    report = converter.convert_character_card(
        source,
        output,
        name="Test outfit",
    )

    assert report["marker"] == converter.CLOTHES_MARKER
    assert report["name"] == "Test outfit"
    assert report["source_dependencies"] == 2
    assert report["coordinate_dependencies"] == 1
    assert report["clothes_part_count"] == 8
    assert report["accessory_part_count"] == 20
    assert report["skipped_plugins"] == ["example.character.only"]

    plugins = read_generated_plugins(output.read_bytes())
    uar = plugins[converter.UAR_PLUGIN_ID]
    assert len(uar[1]["info"]) == 1
    dependency, dependency_end = unpack_msgpack(uar[1]["info"][0])
    assert dependency_end == len(uar[1]["info"][0])
    assert dependency["Property"] == "ChaFileClothes.ClothesTop"

    accessory_controls = plugins[converter.ACCESSORY_CONTROLS_PLUGIN_ID][1]
    assert "coordinateAccessoryData" in accessory_controls
    assert "coordinateOverrideData" in accessory_controls
    assert "accessoryData" not in accessory_controls
    assert "overrideData" not in accessory_controls


def test_convert_character_card_does_not_overwrite_by_default(tmp_path: Path):
    source = tmp_path / "character.png"
    output = tmp_path / "coordinate.png"
    source.write_bytes(make_character_card())
    output.write_bytes(b"existing")

    with pytest.raises(converter.CoordinateExtractionError, match="already exists"):
        converter.convert_character_card(source, output)

    assert output.read_bytes() == b"existing"
