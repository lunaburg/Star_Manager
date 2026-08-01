from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import msgpack


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.core.card_parser import (  # noqa: E402
    AIS_CARD_MARKERS,
    MOD_ID_PATTERN,
    extract_mod_guids_from_card,
    extract_png_extra_data,
    read_card_marker,
)
from star_manager.services.mod_database_core import DEFAULT_DB_PATH  # noqa: E402


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_IEND_CHUNK = b"\x00\x00\x00\x00IEND\xaeB`\x82"
DEFAULT_GAME_DIR = Path("test/hs2")
CARD_ROOT_PARTS = ("UserData", "chara")
TEXT_KEYS = {
    "fullname",
    "lastname",
    "firstname",
    "nickname",
    "personality",
    "birthmonth",
    "birthday",
    "school",
    "club",
    "name",
    "coordinateName",
    "version",
    "language",
}
UNIVERSAL_AUTO_RESOLVER_ID = "com.bepis.sideloader.universalautoresolver"
PROFILE_FIELDS = {
    "version",
    "sex",
    "fullname",
    "personality",
    "birthMonth",
    "birthDay",
    "voiceRate",
    "hsWish",
    "futanari",
}


@dataclass(frozen=True)
class MsgpackString:
    offset: int
    value: str


def read_exact_png_iend_offset(data: bytes) -> int:
    """Return the byte offset just after the first complete PNG IEND chunk."""
    if not data.startswith(PNG_SIGNATURE):
        return -1
    found = data.find(PNG_IEND_CHUNK)
    if found >= 0:
        return found + len(PNG_IEND_CHUNK)
    chunk_type = b"IEND"
    type_pos = data.find(chunk_type)
    if type_pos < 4:
        return -1
    return type_pos + len(chunk_type) + 4


def read_7bit_int(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    cursor = offset
    while cursor < len(data):
        byte = data[cursor]
        cursor += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, cursor
        shift += 7
        if shift > 35:
            break
    raise ValueError("invalid 7-bit integer")


def try_read_dotnet_string(data: bytes, offset: int) -> tuple[str, int] | None:
    try:
        length, cursor = read_7bit_int(data, offset)
    except ValueError:
        return None
    if length <= 0 or cursor + length > len(data):
        return None
    raw = data[cursor : cursor + length]
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, cursor + length


def read_card_header(data: bytes) -> dict[str, Any]:
    offset = 8
    marker = try_read_dotnet_string(data, offset)
    if not marker:
        return {}
    marker_value, offset = marker
    version = try_read_dotnet_string(data, offset)
    if not version:
        return {"marker": marker_value}
    version_value, offset = version
    unknown_int32 = None
    if offset + 4 <= len(data):
        unknown_int32 = int.from_bytes(data[offset : offset + 4], "little")
        offset += 4
    card_id = try_read_dotnet_string(data, offset)
    card_id_value = ""
    if card_id:
        card_id_value, offset = card_id
    user_id = try_read_dotnet_string(data, offset)
    user_id_value = ""
    if user_id:
        user_id_value, offset = user_id
    info_size = None
    if offset + 4 <= len(data):
        info_size = int.from_bytes(data[offset : offset + 4], "little")
        offset += 4
    return {
        "marker": marker_value,
        "version": version_value,
        "unknown_int32": unknown_int32,
        "card_id": card_id_value,
        "user_id": user_id_value,
        "info_size": info_size,
        "info_offset": offset,
    }


def unpack_first(data: bytes, offset: int = 0) -> tuple[Any, int]:
    unpacker = msgpack.Unpacker(raw=False, strict_map_key=False, max_buffer_size=100 * 1024 * 1024)
    unpacker.feed(data[offset:])
    value = next(unpacker)
    return value, offset + unpacker.tell()


def try_unpack_first(data: bytes, offset: int = 0) -> tuple[Any, int] | None:
    try:
        return unpack_first(data, offset)
    except Exception:
        return None


def unpack_value(data: bytes) -> Any:
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


def simplify_value(value: Any, depth: int = 0, max_depth: int = 5) -> Any:
    if depth >= max_depth:
        if isinstance(value, dict):
            return {"type": "dict", "len": len(value), "keys": [str(k) for k in list(value)[:20]]}
        if isinstance(value, list):
            return {"type": "list", "len": len(value)}
        if isinstance(value, bytes):
            return {"type": "bytes", "len": len(value)}
        return value
    if isinstance(value, dict):
        return {str(k): simplify_value(v, depth + 1, max_depth) for k, v in value.items()}
    if isinstance(value, list):
        return [simplify_value(item, depth + 1, max_depth) for item in value]
    if isinstance(value, bytes):
        nested = try_unpack_msgpack_bytes(value)
        if nested is not None:
            return simplify_value(nested, depth + 1, max_depth)
        return {"type": "bytes", "len": len(value), "hex": value[:32].hex(" ")}
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, bytes):
        return {"type": "bytes", "len": len(value), "hex": value[:64].hex(" ")}
    return value


def try_unpack_msgpack_bytes(data: bytes) -> Any | None:
    try:
        return unpack_value(data)
    except Exception:
        return None


def analyze_card_structure(card_data: bytes) -> dict[str, Any]:
    header = read_card_header(card_data)
    info_offset = header.get("info_offset")
    if not isinstance(info_offset, int):
        return {"header": header, "error": "Missing card info offset."}
    try:
        info, table_end = unpack_first(card_data, info_offset)
    except Exception as exc:  # noqa: BLE001
        return {"header": header, "error": f"Failed to unpack block table: {exc}"}
    if table_end + 8 > len(card_data):
        return {"header": header, "error": "Missing character-card block-data size."}
    block_data_size = int.from_bytes(card_data[table_end : table_end + 8], "little")
    block_base = table_end + 8
    if block_base + block_data_size > len(card_data):
        return {"header": header, "error": "Character-card block data is truncated."}
    block_infos = info.get("lstInfo", []) if isinstance(info, dict) else []
    blocks = []
    for block_info in block_infos:
        if not isinstance(block_info, dict):
            continue
        name = str(block_info.get("name", ""))
        pos = int(block_info.get("pos", 0))
        size = int(block_info.get("size", 0))
        blob = card_data[block_base + pos : block_base + pos + size]
        objects = scan_msgpack_objects(blob)
        blocks.append(
            {
                "name": name,
                "version": str(block_info.get("version", "")),
                "pos": pos,
                "absolute_pos": block_base + pos,
                "size": size,
                "object_count": len(objects),
                "objects": objects,
            }
        )
    return {
        "header": header,
        "block_base": block_base,
        "block_data_size": block_data_size,
        "table": info,
        "blocks": blocks,
    }


def get_card_block(card_data: bytes, block_name: str) -> tuple[dict[str, Any], bytes] | None:
    header = read_card_header(card_data)
    info_offset = header.get("info_offset")
    if not isinstance(info_offset, int):
        return None
    try:
        info, table_end = unpack_first(card_data, info_offset)
    except Exception:
        return None
    if not isinstance(info, dict):
        return None
    if table_end + 8 > len(card_data):
        return None
    block_data_size = int.from_bytes(card_data[table_end : table_end + 8], "little")
    block_base = table_end + 8
    if block_base + block_data_size > len(card_data):
        return None
    for block_info in info.get("lstInfo", []):
        if not isinstance(block_info, dict) or block_info.get("name") != block_name:
            continue
        pos = int(block_info.get("pos", 0))
        size = int(block_info.get("size", 0))
        if pos < 0 or size < 0 or pos + size > block_data_size:
            return None
        return block_info, card_data[block_base + pos : block_base + pos + size]
    return None


def extract_character_profile(card_data: bytes) -> dict[str, Any]:
    block = get_card_block(card_data, "Parameter")
    if not block:
        return {}
    block_info, blob = block
    profile = parse_partial_profile_map(blob)
    if not profile:
        return {}
    profile["_block"] = {
        "name": block_info.get("name"),
        "version": block_info.get("version"),
        "pos": block_info.get("pos"),
        "size": block_info.get("size"),
    }
    return profile


def parse_partial_profile_map(blob: bytes) -> dict[str, Any]:
    for start in range(0, min(len(blob), 32)):
        if not (0x80 <= blob[start] <= 0x8F or blob[start] in {0xDE, 0xDF}):
            continue
        parsed = parse_partial_msgpack_map(blob, start)
        if PROFILE_FIELDS.intersection(parsed):
            return parsed
    return {}


def parse_partial_msgpack_map(blob: bytes, offset: int) -> dict[str, Any]:
    if offset >= len(blob):
        return {}
    prefix = blob[offset]
    cursor = offset + 1
    if 0x80 <= prefix <= 0x8F:
        item_count = prefix & 0x0F
    elif prefix == 0xDE and cursor + 2 <= len(blob):
        item_count = int.from_bytes(blob[cursor : cursor + 2], "big")
        cursor += 2
    elif prefix == 0xDF and cursor + 4 <= len(blob):
        item_count = int.from_bytes(blob[cursor : cursor + 4], "big")
        cursor += 4
    else:
        return {}

    result: dict[str, Any] = {}
    for _ in range(item_count):
        key_read = try_unpack_first(blob, cursor)
        if not key_read:
            break
        key, cursor = key_read
        value_read = try_unpack_first(blob, cursor)
        if not value_read:
            break
        value, cursor = value_read
        result[str(key)] = json_safe(value)
    return result


def scan_msgpack_objects(blob: bytes) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    position = 0
    while position < len(blob):
        found = None
        for skip in range(0, 20):
            start = position + skip
            if start >= len(blob):
                break
            try:
                value, end = unpack_first(blob, start)
            except Exception:
                continue
            consumed = end - start
            if isinstance(value, (dict, list)) or consumed > 8:
                found = (start, consumed, value)
                break
        if not found:
            position += 1
            continue
        start, consumed, value = found
        objects.append(
            {
                "offset": start,
                "size": consumed,
                "type": type(value).__name__,
                "summary": summarize_object(value),
            }
        )
        position = start + max(consumed, 1)
    return objects


def summarize_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "dict",
            "len": len(value),
            "keys": [str(key) for key in list(value)[:40]],
            "value": simplify_value(value, max_depth=2),
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "len": len(value),
            "sample": simplify_value(value[:5], max_depth=3),
        }
    if isinstance(value, bytes):
        return {"type": "bytes", "len": len(value), "hex": value[:32].hex(" ")}
    return {"type": type(value).__name__, "value": value}


def extract_auto_resolver_records(card_data: bytes) -> list[dict[str, Any]]:
    structure = analyze_card_structure(card_data)
    block_base = structure.get("block_base")
    if not isinstance(block_base, int):
        return []
    table = structure.get("table")
    if not isinstance(table, dict):
        return []
    block_infos = table.get("lstInfo", [])
    kkex_info = next(
        (
            block
            for block in block_infos
            if isinstance(block, dict) and block.get("name") == "KKEx"
        ),
        None,
    )
    if not kkex_info:
        return []

    kkex = card_data[
        block_base + int(kkex_info["pos"]) : block_base + int(kkex_info["pos"]) + int(kkex_info["size"])
    ]
    records: list[dict[str, Any]] = []
    position = 0
    while position < len(kkex):
        plugin_found = kkex.find(UNIVERSAL_AUTO_RESOLVER_ID.encode("utf-8"), position)
        if plugin_found < 0:
            break
        plugin_offset = plugin_found - 2 if plugin_found >= 2 and kkex[plugin_found - 2] == 0xD9 else plugin_found - 1
        if plugin_offset < 0:
            break
        try:
            plugin_id, plugin_end = unpack_first(kkex, plugin_offset)
        except Exception:
            position = plugin_found + len(UNIVERSAL_AUTO_RESOLVER_ID)
            continue
        if plugin_id != UNIVERSAL_AUTO_RESOLVER_ID:
            position = plugin_found + len(UNIVERSAL_AUTO_RESOLVER_ID)
            continue
        try:
            payload, payload_end = unpack_first(kkex, plugin_end)
        except Exception:
            position = plugin_end
            continue
        records.extend(parse_auto_resolver_payload(payload))
        position = payload_end
    return records


def parse_auto_resolver_payload(payload: Any) -> list[dict[str, Any]]:
    if not (
        isinstance(payload, list)
        and len(payload) >= 2
        and isinstance(payload[1], dict)
        and isinstance(payload[1].get("info"), list)
    ):
        return []
    records = []
    for raw_record in payload[1]["info"]:
        if not isinstance(raw_record, bytes):
            continue
        try:
            record = unpack_value(raw_record)
        except Exception:
            continue
        if isinstance(record, dict):
            records.append(json_safe(record))
    return records


def iter_msgpack_strings(data: bytes) -> list[MsgpackString]:
    strings: list[MsgpackString] = []
    cursor = 0
    while cursor < len(data):
        prefix = data[cursor]
        length = None
        start = cursor + 1
        if 0xA0 <= prefix <= 0xBF:
            length = prefix & 0x1F
        elif prefix == 0xD9 and cursor + 1 < len(data):
            length = data[cursor + 1]
            start = cursor + 2
        elif prefix == 0xDA and cursor + 2 < len(data):
            length = int.from_bytes(data[cursor + 1 : cursor + 3], "big")
            start = cursor + 3
        elif prefix == 0xDB and cursor + 4 < len(data):
            length = int.from_bytes(data[cursor + 1 : cursor + 5], "big")
            start = cursor + 5

        if length is None or length <= 0 or start + length > len(data):
            cursor += 1
            continue

        raw = data[start : start + length]
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            cursor += 1
            continue
        if is_interesting_text(value):
            strings.append(MsgpackString(cursor, value))
        cursor = start + length
    return strings


def is_interesting_text(value: str) -> bool:
    if not value:
        return False
    printable = sum(1 for char in value if char.isprintable())
    if printable / max(len(value), 1) < 0.85:
        return False
    return len(value) >= 2


def decode_msgpack_string_at(data: bytes, offset: int) -> tuple[str, int] | None:
    if offset >= len(data):
        return None
    prefix = data[offset]
    start = offset + 1
    length = None
    if 0xA0 <= prefix <= 0xBF:
        length = prefix & 0x1F
    elif prefix == 0xD9 and offset + 1 < len(data):
        length = data[offset + 1]
        start = offset + 2
    elif prefix == 0xDA and offset + 2 < len(data):
        length = int.from_bytes(data[offset + 1 : offset + 3], "big")
        start = offset + 3
    elif prefix == 0xDB and offset + 4 < len(data):
        length = int.from_bytes(data[offset + 1 : offset + 5], "big")
        start = offset + 5
    if length is None or length <= 0 or start + length > len(data):
        return None
    try:
        return data[start : start + length].decode("utf-8"), start + length
    except UnicodeDecodeError:
        return None


def extract_mod_id_pairs(data: bytes) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    cursor = 0
    while True:
        found = data.find(MOD_ID_PATTERN, cursor)
        if found < 0:
            break
        key_offset = found - 1 if found > 0 and 0xA0 <= data[found - 1] <= 0xBF else found
        key = decode_msgpack_string_at(data, key_offset)
        value = None
        if key and key[1] < len(data):
            value = decode_msgpack_string_at(data, key[1])
        if value:
            pairs.append(
                {
                    "key_offset": key_offset,
                    "value_offset": key[1],
                    "guid": value[0],
                }
            )
            cursor = value[1]
        else:
            cursor = found + len(MOD_ID_PATTERN)
    return pairs


def collect_card_paths(inputs: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in inputs:
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix.lower() == ".png":
            files.append(resolved)
            continue
        if resolved.is_dir():
            pattern = "**/*.png" if recursive else "*.png"
            files.extend(p.resolve() for p in resolved.glob(pattern) if p.is_file())
    return sorted(set(files))


def default_input_from_game_dir(game_dir: Path) -> Path:
    return game_dir / CARD_ROOT_PARTS[0] / CARD_ROOT_PARTS[1]


def summarize_strings(strings: list[MsgpackString]) -> dict[str, Any]:
    values = [item.value for item in strings]
    counter = Counter(values)
    key_hits = [
        {"offset": item.offset, "value": item.value}
        for item in strings
        if item.value in TEXT_KEYS or "Mod" in item.value or "Cha" in item.value
    ][:80]
    frequent = [
        {"value": value, "count": count}
        for value, count in counter.most_common(40)
        if count > 1 or value in TEXT_KEYS
    ]
    samples = [
        {"offset": item.offset, "value": item.value}
        for item in strings[:120]
        if len(item.value) <= 120
    ]
    return {"count": len(strings), "key_hits": key_hits, "frequent": frequent, "samples": samples}


def load_zipmod_map(db_path: Path) -> dict[str, dict[str, str]]:
    if not db_path.is_file():
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT guid, name, author, version, file_path FROM zipmods"
        ).fetchall()
    finally:
        conn.close()
    return {
        row["guid"]: {
            "name": row["name"],
            "author": row["author"],
            "version": row["version"],
            "file_path": row["file_path"],
        }
        for row in rows
    }


def analyze_card(path: Path, zipmods_by_guid: dict[str, dict[str, str]]) -> dict[str, Any]:
    raw = path.read_bytes()
    iend_after = read_exact_png_iend_offset(raw)
    extra = extract_png_extra_data(str(path))
    try:
        marker = read_card_marker(extra)
    except Exception as exc:  # noqa: BLE001
        marker = None
        marker_error = str(exc)
    else:
        marker_error = ""

    guid_set = sorted(extract_mod_guids_from_card(str(path))) if marker in AIS_CARD_MARKERS else []
    pairs = extract_mod_id_pairs(extra)
    character_profile = extract_character_profile(extra) if marker in AIS_CARD_MARKERS else {}
    auto_resolver_records = extract_auto_resolver_records(extra) if marker in AIS_CARD_MARKERS else []
    pair_guids = sorted({item["guid"] for item in pairs})
    auto_resolver_guids = sorted(
        {
            str(item.get("ModID", ""))
            for item in auto_resolver_records
            if item.get("ModID")
        }
    )
    all_guids = sorted(set(guid_set) | set(pair_guids) | set(auto_resolver_guids))
    strings = iter_msgpack_strings(extra)
    dotnet_header = []
    cursor = 8
    for _ in range(12):
        read = try_read_dotnet_string(extra, cursor)
        if not read:
            break
        value, cursor = read
        dotnet_header.append(value)

    dependencies = []
    for guid in all_guids:
        dependencies.append(
            {
                "guid": guid,
                "zipmod": zipmods_by_guid.get(guid),
                "matched_in_database": guid in zipmods_by_guid,
            }
        )

    return {
        "file": str(path),
        "file_size": len(raw),
        "png_iend_after": iend_after,
        "extra_data_size": len(extra),
        "marker": marker,
        "marker_error": marker_error,
        "is_ais_card": marker in AIS_CARD_MARKERS,
        "dotnet_header_strings": dotnet_header,
        "character_profile": character_profile,
        "dependency_count": len(all_guids),
        "dependencies": dependencies,
        "auto_resolver_record_count": len(auto_resolver_records),
        "auto_resolver_records": auto_resolver_records,
        "structure": analyze_card_structure(extra) if marker in AIS_CARD_MARKERS else {},
        "mod_id_pairs": pairs[:200],
        "string_summary": summarize_strings(strings),
    }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    cards = [item for item in results if item["is_ais_card"]]
    all_deps = sorted({dep["guid"] for card in cards for dep in card["dependencies"]})
    missing = sorted(
        {
            dep["guid"]
            for card in cards
            for dep in card["dependencies"]
            if not dep["matched_in_database"]
        }
    )
    return {
        "files_scanned": len(results),
        "ais_cards": len(cards),
        "non_cards": len(results) - len(cards),
        "unique_dependency_count": len(all_deps),
        "unique_dependencies": all_deps,
        "database_missing_dependency_count": len(missing),
        "database_missing_dependencies": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze HS2/AIS PNG character cards and their zipmod dependencies."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Card PNG files or folders. Defaults to <game-dir>/UserData/chara.",
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=DEFAULT_GAME_DIR,
        help="HS2 game directory used when no explicit path is provided.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Optional Star_Manager SQLite database used to resolve GUIDs to zipmods.",
    )
    parser.add_argument("--recursive", action="store_true", default=True, help="Scan folders recursively.")
    parser.add_argument("--no-recursive", dest="recursive", action="store_false")
    parser.add_argument("--limit", type=int, default=10, help="Maximum PNG files to analyze.")
    parser.add_argument("--json", type=Path, help="Write the full analysis JSON to this file.")
    args = parser.parse_args()

    inputs = args.paths or [default_input_from_game_dir(args.game_dir)]
    paths = collect_card_paths(inputs, args.recursive)
    if args.limit > 0:
        paths = paths[: args.limit]

    zipmods_by_guid = load_zipmod_map(args.db.resolve())
    results = [analyze_card(path, zipmods_by_guid) for path in paths]
    summary = build_summary(results)
    payload = {"summary": summary, "cards": results}

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for card in results:
        print()
        print(Path(card["file"]).name)
        print(f"  path: {card['file']}")
        print(f"  AIS: {card['is_ais_card']} marker={card['marker']!r} extra={card['extra_data_size']} bytes")
        if card.get("character_profile"):
            profile = card["character_profile"]
            print("  character profile:")
            for key in ("fullname", "sex", "personality", "birthMonth", "birthDay", "voiceRate", "hsWish", "futanari"):
                if key in profile:
                    print(f"    {key}: {profile[key]}")
        print(f"  dependencies: {card['dependency_count']}")
        if card.get("structure", {}).get("blocks"):
            block_labels = [
                f"{block['name']}({block['size']})"
                for block in card["structure"]["blocks"]
            ]
            print(f"  blocks: {', '.join(block_labels)}")
        for dep in card["dependencies"][:20]:
            zipmod = dep["zipmod"]
            label = f"{zipmod['author']} / {zipmod['name']}" if zipmod else "not found in database"
            print(f"    - {dep['guid']} ({label})")
        if card["dependency_count"] > 20:
            print(f"    ... {card['dependency_count'] - 20} more")
        if card.get("auto_resolver_records"):
            print(f"  resolved item records: {card['auto_resolver_record_count']}")
            for record in card["auto_resolver_records"][:20]:
                print(
                    "    - "
                    f"{record.get('Property', '')} "
                    f"cat={record.get('CategoryNo', '')} "
                    f"slot={record.get('Slot', '')} "
                    f"local={record.get('LocalSlot', '')} "
                    f"mod={record.get('ModID', '')} "
                    f"name={record.get('Name', '')}"
                )
        if card["string_summary"]["key_hits"]:
            print("  structural string hits:")
            for hit in card["string_summary"]["key_hits"][:12]:
                print(f"    @{hit['offset']}: {hit['value']}")

    if not paths:
        print()
        print("No PNG files found. Pass a card file/folder, or use --game-dir pointing at an HS2 install.")
    elif not summary["ais_cards"]:
        print()
        print("No AIS character-card payloads found in the scanned PNG files.")
    if args.json:
        print()
        print(f"Full JSON written to: {args.json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
