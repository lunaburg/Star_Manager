from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

from star_manager.core.card_parser import (
    get_card_block,
    read_card_header,
    read_card_marker,
    try_unpack_msgpack,
    unpack_msgpack,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
CHARACTER_MARKER = "【AIS_Chara】"
CLOTHES_MARKER = "【AIS_Clothes】"
CARD_ENVELOPE_VERSION = 100
KKEX_NAME = "KKEx"
KKEX_VERSION = 3
UAR_PLUGIN_ID = "com.bepis.sideloader.universalautoresolver"
DEFAULT_COORDINATE_PLUGINS = {
    "moreAccessories",
    "orange.spork.additionalaccessorycontrolsplugin",
    "orange.spork.outfitpainter",
}
ACCESSORY_CONTROLS_PLUGIN_ID = "orange.spork.additionalaccessorycontrolsplugin"
ACCESSORY_PROPERTY_PATTERN = re.compile(r"^accessory\d+\.")


class CoordinateExtractionError(ValueError):
    pass


def find_png_end(data: bytes) -> int:
    if not data.startswith(PNG_SIGNATURE):
        raise CoordinateExtractionError("Input is not a PNG file.")

    cursor = len(PNG_SIGNATURE)
    while cursor + 12 <= len(data):
        size = int.from_bytes(data[cursor : cursor + 4], "big")
        chunk_type = data[cursor + 4 : cursor + 8]
        chunk_end = cursor + 12 + size
        if chunk_end > len(data):
            raise CoordinateExtractionError("PNG chunk data is truncated.")
        cursor = chunk_end
        if chunk_type == b"IEND":
            return cursor
    raise CoordinateExtractionError("PNG IEND chunk was not found.")


def png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(PNG_SIGNATURE) or len(data) < 24 or data[12:16] != b"IHDR":
        raise CoordinateExtractionError("PNG IHDR chunk is missing.")
    return struct.unpack(">II", data[16:24])


def read_png_image(path: Path) -> tuple[bytes, tuple[int, int]]:
    data = path.read_bytes()
    png_end = find_png_end(data)
    image = data[:png_end]
    return image, png_dimensions(image)


def make_card_data(file_bytes: bytes) -> tuple[bytes, int]:
    png_end = find_png_end(file_bytes)
    if png_end < 4:
        raise CoordinateExtractionError("PNG IEND CRC is missing.")
    # card_parser expects the IEND CRC followed by the appended card payload.
    return file_bytes[png_end - 4 :], png_end


def read_character_blocks(card_data: bytes) -> tuple[dict[str, Any], int, int]:
    header = read_card_header(card_data)
    if header.get("marker") != CHARACTER_MARKER:
        marker = header.get("marker") or read_card_marker(card_data)
        raise CoordinateExtractionError(f"Expected {CHARACTER_MARKER}, found {marker!r}.")

    info_offset = header.get("info_offset")
    if not isinstance(info_offset, int):
        raise CoordinateExtractionError("Character-card block table offset is missing.")
    unpacked = try_unpack_msgpack(card_data, info_offset)
    if not unpacked or not isinstance(unpacked[0], dict):
        raise CoordinateExtractionError("Character-card block table cannot be decoded.")

    table, table_end = unpacked
    if table_end + 8 > len(card_data):
        raise CoordinateExtractionError("Character-card block-data length is missing.")
    block_data_size = int.from_bytes(card_data[table_end : table_end + 8], "little")
    block_base = table_end + 8
    if block_base + block_data_size > len(card_data):
        raise CoordinateExtractionError("Character-card block data is truncated.")

    block_infos = table.get("lstInfo")
    if not isinstance(block_infos, list):
        raise CoordinateExtractionError("Character-card block list is missing.")
    declared_size = sum(
        int(item.get("size", 0)) for item in block_infos if isinstance(item, dict)
    )
    if declared_size != block_data_size:
        raise CoordinateExtractionError(
            f"Block sizes total {declared_size}, but the card declares {block_data_size}."
        )
    return table, block_base, block_data_size


def validate_coordinate_payload(payload: bytes) -> dict[str, int]:
    cursor = 0
    part_counts: list[int] = []
    object_sizes: list[int] = []
    for label in ("clothes", "accessories"):
        if cursor + 4 > len(payload):
            raise CoordinateExtractionError(f"Coordinate {label} length is missing.")
        size = int.from_bytes(payload[cursor : cursor + 4], "little")
        start = cursor + 4
        end = start + size
        if size <= 0 or end > len(payload):
            raise CoordinateExtractionError(f"Coordinate {label} data is truncated.")
        decoded = try_unpack_msgpack(payload, start)
        if not decoded or decoded[1] != end or not isinstance(decoded[0], dict):
            raise CoordinateExtractionError(f"Coordinate {label} MessagePack is invalid.")
        parts = decoded[0].get("parts")
        if not isinstance(parts, list):
            raise CoordinateExtractionError(f"Coordinate {label} parts are missing.")
        part_counts.append(len(parts))
        object_sizes.append(size)
        cursor = end

    if cursor != len(payload):
        raise CoordinateExtractionError(
            f"Coordinate payload has {len(payload) - cursor} unexpected trailing bytes."
        )
    if part_counts[0] != 8:
        raise CoordinateExtractionError(
            f"Expected 8 clothes parts, found {part_counts[0]}."
        )
    if part_counts[1] < 20:
        raise CoordinateExtractionError(
            f"Expected at least 20 accessory parts, found {part_counts[1]}."
        )
    return {
        "clothes_object_size": object_sizes[0],
        "clothes_part_count": part_counts[0],
        "accessory_object_size": object_sizes[1],
        "accessory_part_count": part_counts[1],
    }


def parse_coordinate_payload_parts(payload: bytes) -> dict[str, list[dict[str, Any]]]:
    """Return the clothing and accessory IDs from a validated Coordinate block."""
    validate_coordinate_payload(payload)
    cursor = 0
    objects: list[dict[str, Any]] = []
    for _ in range(2):
        size = int.from_bytes(payload[cursor : cursor + 4], "little")
        start = cursor + 4
        end = start + size
        decoded = try_unpack_msgpack(payload, start)
        if not decoded or decoded[1] != end or not isinstance(decoded[0], dict):
            raise CoordinateExtractionError("Coordinate MessagePack is invalid.")
        objects.append(decoded[0])
        cursor = end

    clothes_parts = [
        {"slot": index, "id": part.get("id")}
        for index, part in enumerate(objects[0].get("parts", []))
        if isinstance(part, dict)
    ]
    accessory_parts = [
        {
            "slot": index,
            "type": part.get("type"),
            "id": part.get("id"),
        }
        for index, part in enumerate(objects[1].get("parts", []))
        if isinstance(part, dict)
    ]
    return {
        "clothes_parts": clothes_parts,
        "accessory_parts": accessory_parts,
    }


def normalize_coordinate_property(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if value.startswith("outfit."):
        value = value[len("outfit.") :]
    if value.startswith("ChaFileClothes.") or ACCESSORY_PROPERTY_PATTERN.match(value):
        return value
    return None


def filter_uar_payload(payload: Any) -> tuple[Any, int, int]:
    if not (
        isinstance(payload, list)
        and len(payload) >= 2
        and isinstance(payload[1], dict)
        and isinstance(payload[1].get("info"), list)
    ):
        raise CoordinateExtractionError("UniversalAutoResolver payload has an unknown shape.")

    kept_records: list[bytes] = []
    source_records = payload[1]["info"]
    for raw_record in source_records:
        if not isinstance(raw_record, bytes):
            continue
        try:
            record, end = unpack_msgpack(raw_record)
        except (IndexError, UnicodeDecodeError, ValueError):
            continue
        if end != len(raw_record) or not isinstance(record, dict):
            continue
        coordinate_property = normalize_coordinate_property(record.get("Property"))
        if not coordinate_property:
            continue
        converted = dict(record)
        converted["Property"] = coordinate_property
        kept_records.append(pack_msgpack(converted))

    converted_payload = list(payload)
    converted_metadata = dict(payload[1])
    converted_metadata["info"] = kept_records
    converted_payload[1] = converted_metadata
    return converted_payload, len(source_records), len(kept_records)


def adapt_coordinate_plugin(plugin_name: str, payload: Any) -> Any:
    if plugin_name != ACCESSORY_CONTROLS_PLUGIN_ID:
        return payload
    if not (
        isinstance(payload, list)
        and len(payload) >= 2
        and isinstance(payload[1], dict)
    ):
        raise CoordinateExtractionError(
            "AdditionalAccessoryControls payload has an unknown shape."
        )

    converted_payload = list(payload)
    converted_metadata = dict(payload[1])
    if "accessoryData" in converted_metadata:
        converted_metadata["coordinateAccessoryData"] = converted_metadata.pop(
            "accessoryData"
        )
    if "overrideData" in converted_metadata:
        converted_metadata["coordinateOverrideData"] = converted_metadata.pop(
            "overrideData"
        )
    converted_payload[1] = converted_metadata
    return converted_payload


def build_coordinate_kkex(
    kkex_blob: bytes,
    extra_plugin_ids: set[str] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    if not kkex_blob:
        return pack_msgpack({}), {
            "source_plugins": [],
            "copied_plugins": [],
            "skipped_plugins": [],
            "source_dependencies": 0,
            "coordinate_dependencies": 0,
        }

    try:
        plugins, end = unpack_msgpack(kkex_blob)
    except (IndexError, UnicodeDecodeError, ValueError) as exc:
        raise CoordinateExtractionError(f"KKEx data cannot be decoded: {exc}") from exc
    if end != len(kkex_blob) or not isinstance(plugins, dict):
        raise CoordinateExtractionError("KKEx data is not one complete MessagePack map.")

    allowed_plugins = DEFAULT_COORDINATE_PLUGINS | set(extra_plugin_ids or ())
    converted: dict[Any, Any] = {}
    copied_plugins: list[str] = []
    skipped_plugins: list[str] = []
    source_dependencies = 0
    coordinate_dependencies = 0

    for plugin_id, plugin_payload in plugins.items():
        plugin_name = str(plugin_id)
        if plugin_name == UAR_PLUGIN_ID:
            converted_payload, source_dependencies, coordinate_dependencies = filter_uar_payload(
                plugin_payload
            )
            converted[plugin_id] = converted_payload
            copied_plugins.append(plugin_name)
        elif plugin_name in allowed_plugins:
            converted[plugin_id] = adapt_coordinate_plugin(plugin_name, plugin_payload)
            copied_plugins.append(plugin_name)
        else:
            skipped_plugins.append(plugin_name)

    return pack_msgpack(converted), {
        "source_plugins": [str(item) for item in plugins],
        "copied_plugins": copied_plugins,
        "skipped_plugins": skipped_plugins,
        "source_dependencies": source_dependencies,
        "coordinate_dependencies": coordinate_dependencies,
    }


def extract_character_coordinate(
    character_card: Path,
    extra_plugin_ids: set[str] | None = None,
) -> tuple[bytes, bytes, dict[str, Any]]:
    source_bytes = character_card.read_bytes()
    card_data, png_end = make_card_data(source_bytes)
    table, _, _ = read_character_blocks(card_data)

    coordinate = get_card_block(card_data, "Coordinate")
    if not coordinate:
        raise CoordinateExtractionError("Character card has no Coordinate block.")
    _, coordinate_blob = coordinate
    coordinate_summary = validate_coordinate_payload(coordinate_blob)

    kkex = get_card_block(card_data, KKEX_NAME)
    kkex_blob = kkex[1] if kkex else b""
    converted_kkex, kkex_summary = build_coordinate_kkex(kkex_blob, extra_plugin_ids)
    block_names = [
        str(item.get("name", ""))
        for item in table.get("lstInfo", [])
        if isinstance(item, dict)
    ]
    return coordinate_blob, converted_kkex, {
        "source_file": str(character_card.resolve()),
        "source_png_size": png_end,
        "source_blocks": block_names,
        "coordinate_size": len(coordinate_blob),
        **coordinate_summary,
        **kkex_summary,
    }


def write_7bit_int(value: int) -> bytes:
    if value < 0:
        raise ValueError("7-bit integers cannot be negative.")
    output = bytearray()
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def pack_dotnet_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return write_7bit_int(len(encoded)) + encoded


def pack_msgpack(value: Any) -> bytes:
    if value is None:
        return b"\xc0"
    if value is False:
        return b"\xc2"
    if value is True:
        return b"\xc3"
    if isinstance(value, int):
        return pack_msgpack_int(value)
    if isinstance(value, float):
        return b"\xcb" + struct.pack(">d", value)
    if isinstance(value, str):
        return pack_msgpack_string(value)
    if isinstance(value, (bytes, bytearray)):
        return pack_msgpack_binary(bytes(value))
    if isinstance(value, (list, tuple)):
        items = b"".join(pack_msgpack(item) for item in value)
        return pack_msgpack_array_header(len(value)) + items
    if isinstance(value, dict):
        items = b"".join(
            pack_msgpack(key) + pack_msgpack(item) for key, item in value.items()
        )
        return pack_msgpack_map_header(len(value)) + items
    raise TypeError(f"Unsupported MessagePack value: {type(value).__name__}")


def pack_msgpack_int(value: int) -> bytes:
    if 0 <= value <= 0x7F:
        return bytes([value])
    if -32 <= value < 0:
        return bytes([value & 0xFF])
    if 0 <= value <= 0xFF:
        return b"\xcc" + struct.pack(">B", value)
    if 0 <= value <= 0xFFFF:
        return b"\xcd" + struct.pack(">H", value)
    if 0 <= value <= 0xFFFFFFFF:
        return b"\xce" + struct.pack(">I", value)
    if 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        return b"\xcf" + struct.pack(">Q", value)
    if -0x80 <= value < 0:
        return b"\xd0" + struct.pack(">b", value)
    if -0x8000 <= value < -0x80:
        return b"\xd1" + struct.pack(">h", value)
    if -0x80000000 <= value < -0x8000:
        return b"\xd2" + struct.pack(">i", value)
    if -0x8000000000000000 <= value < -0x80000000:
        return b"\xd3" + struct.pack(">q", value)
    raise OverflowError("Integer is outside the MessagePack 64-bit range.")


def pack_msgpack_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    size = len(encoded)
    if size <= 31:
        return bytes([0xA0 | size]) + encoded
    if size <= 0xFF:
        return b"\xd9" + struct.pack(">B", size) + encoded
    if size <= 0xFFFF:
        return b"\xda" + struct.pack(">H", size) + encoded
    if size <= 0xFFFFFFFF:
        return b"\xdb" + struct.pack(">I", size) + encoded
    raise OverflowError("String is too large for MessagePack.")


def pack_msgpack_binary(value: bytes) -> bytes:
    size = len(value)
    if size <= 0xFF:
        return b"\xc4" + struct.pack(">B", size) + value
    if size <= 0xFFFF:
        return b"\xc5" + struct.pack(">H", size) + value
    if size <= 0xFFFFFFFF:
        return b"\xc6" + struct.pack(">I", size) + value
    raise OverflowError("Binary value is too large for MessagePack.")


def pack_msgpack_array_header(size: int) -> bytes:
    if size <= 15:
        return bytes([0x90 | size])
    if size <= 0xFFFF:
        return b"\xdc" + struct.pack(">H", size)
    if size <= 0xFFFFFFFF:
        return b"\xdd" + struct.pack(">I", size)
    raise OverflowError("Array is too large for MessagePack.")


def pack_msgpack_map_header(size: int) -> bytes:
    if size <= 15:
        return bytes([0x80 | size])
    if size <= 0xFFFF:
        return b"\xde" + struct.pack(">H", size)
    if size <= 0xFFFFFFFF:
        return b"\xdf" + struct.pack(">I", size)
    raise OverflowError("Map is too large for MessagePack.")


def build_clothes_card_payload(name: str, coordinate: bytes, kkex: bytes) -> bytes:
    return b"".join(
        [
            struct.pack("<I", CARD_ENVELOPE_VERSION),
            pack_dotnet_string(CLOTHES_MARKER),
            pack_dotnet_string("0.0.0"),
            struct.pack("<I", 0),
            pack_dotnet_string(name),
            struct.pack("<I", len(coordinate)),
            coordinate,
            pack_dotnet_string(KKEX_NAME),
            struct.pack("<I", KKEX_VERSION),
            struct.pack("<I", len(kkex)),
            kkex,
        ]
    )


def read_dotnet_string(data: bytes, cursor: int) -> tuple[str, int]:
    size = 0
    shift = 0
    while cursor < len(data):
        byte = data[cursor]
        cursor += 1
        size |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 35:
            raise CoordinateExtractionError("Invalid .NET string length.")
    else:
        raise CoordinateExtractionError("Truncated .NET string length.")
    end = cursor + size
    if end > len(data):
        raise CoordinateExtractionError("Truncated .NET string.")
    try:
        return data[cursor:end].decode("utf-8"), end
    except UnicodeDecodeError as exc:
        raise CoordinateExtractionError("Invalid UTF-8 .NET string.") from exc


def inspect_clothes_card(file_bytes: bytes) -> dict[str, Any]:
    png_end = find_png_end(file_bytes)
    payload = file_bytes[png_end:]
    if len(payload) < 4 or int.from_bytes(payload[:4], "little") != CARD_ENVELOPE_VERSION:
        raise CoordinateExtractionError("Clothes-card envelope version is invalid.")
    marker, cursor = read_dotnet_string(payload, 4)
    version, cursor = read_dotnet_string(payload, cursor)
    if marker != CLOTHES_MARKER or version != "0.0.0":
        raise CoordinateExtractionError("Generated clothes-card header is invalid.")
    if cursor + 4 > len(payload):
        raise CoordinateExtractionError("Generated clothes-card header is truncated.")
    unknown = int.from_bytes(payload[cursor : cursor + 4], "little")
    name, cursor = read_dotnet_string(payload, cursor + 4)
    if cursor + 4 > len(payload):
        raise CoordinateExtractionError("Generated coordinate length is missing.")
    coordinate_size = int.from_bytes(payload[cursor : cursor + 4], "little")
    coordinate_start = cursor + 4
    coordinate_end = coordinate_start + coordinate_size
    if coordinate_end > len(payload):
        raise CoordinateExtractionError("Generated coordinate payload is truncated.")
    coordinate_summary = validate_coordinate_payload(payload[coordinate_start:coordinate_end])

    extension_name, cursor = read_dotnet_string(payload, coordinate_end)
    if extension_name != KKEX_NAME or cursor + 8 > len(payload):
        raise CoordinateExtractionError("Generated KKEx header is invalid.")
    extension_version = int.from_bytes(payload[cursor : cursor + 4], "little")
    extension_size = int.from_bytes(payload[cursor + 4 : cursor + 8], "little")
    extension_start = cursor + 8
    extension_end = extension_start + extension_size
    if extension_end != len(payload):
        raise CoordinateExtractionError("Generated KKEx length does not consume the file.")
    decoded = try_unpack_msgpack(payload, extension_start)
    if not decoded or decoded[1] != extension_end or not isinstance(decoded[0], dict):
        raise CoordinateExtractionError("Generated KKEx MessagePack is invalid.")
    return {
        "marker": marker,
        "version": version,
        "unknown": unknown,
        "name": name,
        "png_size": png_end,
        "coordinate_size": coordinate_size,
        "extension_name": extension_name,
        "extension_version": extension_version,
        "extension_size": extension_size,
        "plugins": [str(item) for item in decoded[0]],
        **coordinate_summary,
    }


def inspect_clothes_card_listing_payload(payload: bytes, png_size: int = 0) -> dict[str, Any]:
    """Validate a clothes-card payload when the PNG image was streamed separately."""
    if len(payload) < 4 or int.from_bytes(payload[:4], "little") != CARD_ENVELOPE_VERSION:
        raise CoordinateExtractionError("Clothes-card envelope version is invalid.")
    marker, cursor = read_dotnet_string(payload, 4)
    version, cursor = read_dotnet_string(payload, cursor)
    if marker != CLOTHES_MARKER or version != "0.0.0":
        raise CoordinateExtractionError("Generated clothes-card header is invalid.")
    if cursor + 4 > len(payload):
        raise CoordinateExtractionError("Generated clothes-card header is truncated.")
    cursor += 4  # envelope reserved field
    name, cursor = read_dotnet_string(payload, cursor)
    if cursor + 4 > len(payload):
        raise CoordinateExtractionError("Generated coordinate length is missing.")
    coordinate_size = int.from_bytes(payload[cursor : cursor + 4], "little")
    coordinate_start = cursor + 4
    coordinate_end = coordinate_start + coordinate_size
    if coordinate_end > len(payload):
        raise CoordinateExtractionError("Generated coordinate payload is truncated.")
    coordinate_summary = validate_coordinate_payload(payload[coordinate_start:coordinate_end])

    extension_name, cursor = read_dotnet_string(payload, coordinate_end)
    if extension_name != KKEX_NAME or cursor + 8 > len(payload):
        raise CoordinateExtractionError("Generated KKEx header is invalid.")
    extension_version = int.from_bytes(payload[cursor : cursor + 4], "little")
    extension_size = int.from_bytes(payload[cursor + 4 : cursor + 8], "little")
    extension_end = cursor + 8 + extension_size
    if extension_end != len(payload):
        raise CoordinateExtractionError("Generated KKEx length does not consume the file.")

    return {
        "marker": marker,
        "version": version,
        "name": name,
        "png_size": png_size,
        "coordinate_size": coordinate_size,
        "extension_name": extension_name,
        "extension_version": extension_version,
        "extension_size": extension_size,
        **coordinate_summary,
    }


def inspect_clothes_card_listing(file_bytes: bytes) -> dict[str, Any]:
    """Validate only the envelope and coordinate block needed by a card list.

    The KKEx payload can contain a large UniversalAutoResolver record set. The
    browser list only needs the card name and file identity; full KKEx/UAR
    decoding remains reserved for the single-card detail endpoint.
    """
    png_end = find_png_end(file_bytes)
    return inspect_clothes_card_listing_payload(file_bytes[png_end:], png_end)


def atomic_write(path: Path, data: bytes, overwrite: bool) -> None:
    path = path.resolve()
    if path.exists() and not overwrite:
        raise CoordinateExtractionError(
            f"Output already exists: {path}. Pass --overwrite to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent, delete=False
        ) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def convert_character_card(
    character_card: Path,
    output: Path,
    name: str | None = None,
    preview: Path | None = None,
    extra_plugin_ids: set[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    character_card = character_card.resolve()
    if not character_card.is_file():
        raise CoordinateExtractionError(f"Character card does not exist: {character_card}")
    if not name:
        name = character_card.stem

    coordinate, kkex, extraction = extract_character_coordinate(
        character_card, extra_plugin_ids=extra_plugin_ids
    )
    preview_path = preview.resolve() if preview else character_card
    preview_png, dimensions = read_png_image(preview_path)
    if dimensions != (252, 352):
        raise CoordinateExtractionError(
            f"Preview must be 252x352, found {dimensions[0]}x{dimensions[1]}."
        )

    card_bytes = preview_png + build_clothes_card_payload(name, coordinate, kkex)
    validation = inspect_clothes_card(card_bytes)
    atomic_write(output, card_bytes, overwrite=overwrite)
    return {
        **extraction,
        **validation,
        "output_file": str(output.resolve()),
        "output_size": len(card_bytes),
        "preview_file": str(preview_path),
        "preview_width": dimensions[0],
        "preview_height": dimensions[1],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract the current outfit from an HS2/AIS character card into a clothes card."
    )
    parser.add_argument("character_card", type=Path, help="Source 【AIS_Chara】 PNG file.")
    parser.add_argument("output", type=Path, help="Output 【AIS_Clothes】 PNG file.")
    parser.add_argument("--name", help="Coordinate name. Defaults to the source filename stem.")
    parser.add_argument(
        "--preview",
        type=Path,
        help="Optional 252x352 PNG preview. Defaults to the character-card preview.",
    )
    parser.add_argument(
        "--copy-plugin",
        action="append",
        default=[],
        metavar="PLUGIN_ID",
        help="Copy an additional KKEx plugin payload without transformation. Repeat as needed.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")
    parser.add_argument("--json", action="store_true", help="Print the conversion report as JSON.")
    args = parser.parse_args()

    try:
        report = convert_character_card(
            args.character_card,
            args.output,
            name=args.name,
            preview=args.preview,
            extra_plugin_ids=set(args.copy_plugin),
            overwrite=args.overwrite,
        )
    except (CoordinateExtractionError, OSError, TypeError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"output: {report['output_file']}")
        print(f"coordinate: {report['coordinate_size']} bytes")
        print(f"dependencies: {report['coordinate_dependencies']}")
        print(f"plugins: {', '.join(report['plugins']) or '(none)'}")
        if report["skipped_plugins"]:
            print(f"skipped plugins: {', '.join(report['skipped_plugins'])}")
        print(f"verified marker: {report['marker']}")
    return 0
