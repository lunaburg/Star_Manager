import atexit
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from star_manager.core.runtime_paths import runtime_root
from star_manager.utils.binary_reader import BinaryReader


AIS_CARD_MARKERS = {"\u3010AIS_Chara\u3011", "\u3010AIS_Clothes\u3011"}
MOD_ID_PATTERN = b"ModID"
PNG_IEND_MARKER = b"IEND"
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
AIS_CARD_CACHE_PATH = runtime_root() / "ais_card_cache.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
AIS_CARD_CACHE_VERSION = 2
_AIS_CARD_CACHE: dict[str, dict[str, Any]] | None = None
_AIS_CARD_CACHE_DIRTY = False


def load_ais_card_cache() -> dict[str, dict[str, Any]]:
    global _AIS_CARD_CACHE
    if _AIS_CARD_CACHE is not None:
        return _AIS_CARD_CACHE

    try:
        raw = json.loads(AIS_CARD_CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        raw = {}

    _AIS_CARD_CACHE = raw if isinstance(raw, dict) else {}
    return _AIS_CARD_CACHE


def mark_ais_card_cache_dirty() -> None:
    global _AIS_CARD_CACHE_DIRTY
    _AIS_CARD_CACHE_DIRTY = True


def flush_ais_card_cache() -> None:
    global _AIS_CARD_CACHE_DIRTY
    cache = load_ais_card_cache()
    if not _AIS_CARD_CACHE_DIRTY:
        return

    try:
        AIS_CARD_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        AIS_CARD_CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        _AIS_CARD_CACHE_DIRTY = False
    except OSError:
        return


atexit.register(flush_ais_card_cache)


def extract_png_extra_data(file_path):
    """Return the bytes stored after the PNG IEND chunk."""
    with open(file_path, "rb") as file:
        if file.read(len(PNG_SIGNATURE)) != PNG_SIGNATURE:
            return b""

        while True:
            chunk_length_raw = file.read(4)
            if len(chunk_length_raw) < 4:
                return b""
            chunk_type = file.read(4)
            if len(chunk_type) < 4:
                return b""

            chunk_length = int.from_bytes(chunk_length_raw, "big", signed=False)
            if chunk_type == b"IEND":
                crc = file.read(chunk_length + 4)
                return crc + file.read()
            file.seek(chunk_length + 4, 1)


def read_card_marker(card_data):
    if len(card_data) < 100:
        return None

    reader = BinaryReader(BytesIO(card_data))
    reader.read_bytes(8)
    return reader.read_string()


def is_ais_card(file_path):
    path = Path(file_path)
    try:
        stat = path.stat()
    except OSError:
        return False

    cache = load_ais_card_cache()
    cache_key = str(path.resolve())
    cached = cache.get(cache_key)
    if (
        isinstance(cached, dict)
        and cached.get("version") == AIS_CARD_CACHE_VERSION
        and cached.get("size") == stat.st_size
        and cached.get("mtime_ns") == stat.st_mtime_ns
    ):
        return bool(cached.get("is_ais"))

    try:
        marker = read_card_marker(extract_png_extra_data(file_path))
    except Exception:
        is_ais = False
    else:
        is_ais = marker in AIS_CARD_MARKERS

    cache[cache_key] = {
        "version": AIS_CARD_CACHE_VERSION,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "is_ais": is_ais,
    }
    mark_ais_card_cache_dirty()
    return is_ais


def extract_mod_guids_from_card(file_path):
    card_data = extract_png_extra_data(file_path)
    if read_card_marker(card_data) not in AIS_CARD_MARKERS:
        return set()
    return parse_mod_data(card_data)


def extract_character_profile_from_card(file_path: str) -> dict[str, Any]:
    card_data = extract_png_extra_data(file_path)
    if read_card_marker(card_data) not in AIS_CARD_MARKERS:
        return {}

    block = get_card_block(card_data, "Parameter")
    if not block:
        return {}

    block_info, blob = block
    profile = parse_partial_profile_map(blob)
    if not profile:
        return {}

    # HS2 keeps a second set of gameplay profile fields in Parameter2. Changes
    # made in the game can update this value without rewriting the legacy
    # Parameter.personality field, so Parameter2 is authoritative when present.
    parameter2_block = get_card_block(card_data, "Parameter2")
    if parameter2_block:
        _, parameter2_blob = parameter2_block
        parameter2_profile = parse_partial_profile_map(parameter2_blob)
        if "personality" in parameter2_profile:
            profile["personality"] = parameter2_profile["personality"]

    return {
        key: profile.get(key)
        for key in [
            "fullname",
            "sex",
            "personality",
            "birthMonth",
            "birthDay",
            "voiceRate",
            "hsWish",
            "futanari",
        ]
        if key in profile
    } | {
        "_block": {
            "name": block_info.get("name"),
            "version": block_info.get("version"),
            "pos": block_info.get("pos"),
            "size": block_info.get("size"),
        }
    }


def extract_auto_resolver_records_from_card(file_path: str) -> list[dict[str, Any]]:
    card_data = extract_png_extra_data(file_path)
    if read_card_marker(card_data) not in AIS_CARD_MARKERS:
        return []
    block = get_card_block(card_data, "KKEx")
    if not block:
        return []

    _, kkex = block
    records: list[dict[str, Any]] = []
    position = 0
    plugin_bytes = UNIVERSAL_AUTO_RESOLVER_ID.encode("utf-8")
    while position < len(kkex):
        plugin_found = kkex.find(plugin_bytes, position)
        if plugin_found < 0:
            break

        plugin_offset = plugin_found - 2 if plugin_found >= 2 and kkex[plugin_found - 2] == 0xD9 else plugin_found - 1
        if plugin_offset < 0:
            position = plugin_found + len(plugin_bytes)
            continue

        plugin_read = try_unpack_msgpack(kkex, plugin_offset)
        if not plugin_read:
            position = plugin_found + len(plugin_bytes)
            continue
        plugin_id, plugin_end = plugin_read
        if plugin_id != UNIVERSAL_AUTO_RESOLVER_ID:
            position = plugin_found + len(plugin_bytes)
            continue

        payload_read = try_unpack_msgpack(kkex, plugin_end)
        if not payload_read:
            position = plugin_end
            continue
        payload, payload_end = payload_read
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
        decoded = try_unpack_msgpack(raw_record)
        if not decoded:
            continue
        record, _ = decoded
        if isinstance(record, dict):
            records.append(json_safe_msgpack(record))
    return records


def parse_mod_data(card_bytes):
    """Parse HS2 mod identifiers from card binary data."""
    mod_guids = set()
    data = bytearray(card_bytes)
    position = 0

    while position <= len(data) - len(MOD_ID_PATTERN):
        found = data.find(MOD_ID_PATTERN, position)
        if found == -1:
            break

        cursor = found + len(MOD_ID_PATTERN)
        if cursor >= len(data):
            break

        length_prefix = data[cursor]
        cursor += 1

        if length_prefix < 0xC0:
            length = length_prefix - 0xA0
        else:
            if cursor >= len(data):
                break
            length = data[cursor]
            cursor += 1

        if length <= 0 or cursor + length > len(data):
            break

        try:
            mod_guids.add(bytes(data[cursor:cursor + length]).decode("utf-8"))
        except UnicodeDecodeError:
            pass

        position = cursor + length

    return mod_guids


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
    raise ValueError("Invalid 7-bit integer.")


def try_read_dotnet_string(data: bytes, offset: int) -> tuple[str, int] | None:
    try:
        length, cursor = read_7bit_int(data, offset)
    except ValueError:
        return None
    if length <= 0 or cursor + length > len(data):
        return None
    try:
        return data[cursor : cursor + length].decode("utf-8"), cursor + length
    except UnicodeDecodeError:
        return None


def read_card_header(card_data: bytes) -> dict[str, Any]:
    offset = 8
    marker = try_read_dotnet_string(card_data, offset)
    if not marker:
        return {}
    marker_value, offset = marker
    version = try_read_dotnet_string(card_data, offset)
    if not version:
        return {"marker": marker_value}
    version_value, offset = version

    if offset + 4 <= len(card_data):
        offset += 4

    card_id_value = ""
    card_id = try_read_dotnet_string(card_data, offset)
    if card_id:
        card_id_value, offset = card_id
    user_id = try_read_dotnet_string(card_data, offset)
    if user_id:
        _, offset = user_id

    info_size = None
    if offset + 4 <= len(card_data):
        info_size = int.from_bytes(card_data[offset : offset + 4], "little")
        offset += 4

    return {
        "marker": marker_value,
        "version": version_value,
        "card_id": card_id_value,
        "info_size": info_size,
        "info_offset": offset,
    }


def get_card_block(card_data: bytes, block_name: str) -> tuple[dict[str, Any], bytes] | None:
    header = read_card_header(card_data)
    info_offset = header.get("info_offset")
    if not isinstance(info_offset, int):
        return None
    unpacked = try_unpack_msgpack(card_data, info_offset)
    if not unpacked:
        return None
    info, block_base = unpacked
    if not isinstance(info, dict):
        return None

    for block_info in info.get("lstInfo", []):
        if not isinstance(block_info, dict) or block_info.get("name") != block_name:
            continue
        pos = int(block_info.get("pos", 0))
        size = int(block_info.get("size", 0))
        return block_info, card_data[block_base + pos : block_base + pos + size]
    return None


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
    marker = blob[offset]
    cursor = offset + 1
    if 0x80 <= marker <= 0x8F:
        item_count = marker & 0x0F
    elif marker == 0xDE and cursor + 2 <= len(blob):
        item_count = int.from_bytes(blob[cursor : cursor + 2], "big")
        cursor += 2
    elif marker == 0xDF and cursor + 4 <= len(blob):
        item_count = int.from_bytes(blob[cursor : cursor + 4], "big")
        cursor += 4
    else:
        return {}

    result: dict[str, Any] = {}
    for _ in range(item_count):
        key_read = try_unpack_msgpack(blob, cursor)
        if not key_read:
            break
        key, cursor = key_read
        value_read = try_unpack_msgpack(blob, cursor)
        if not value_read:
            break
        value, cursor = value_read
        result[str(key)] = json_safe_msgpack(value)
    return result


def try_unpack_msgpack(data: bytes, offset: int = 0) -> tuple[Any, int] | None:
    try:
        return unpack_msgpack(data, offset)
    except (IndexError, UnicodeDecodeError, ValueError):
        return None


def unpack_msgpack(data: bytes, offset: int = 0) -> tuple[Any, int]:
    if offset >= len(data):
        raise ValueError("Offset is outside MessagePack data.")
    marker = data[offset]
    cursor = offset + 1

    if marker <= 0x7F:
        return marker, cursor
    if marker >= 0xE0:
        return marker - 0x100, cursor
    if 0xA0 <= marker <= 0xBF:
        return unpack_msgpack_string(data, cursor, marker & 0x1F)
    if 0x90 <= marker <= 0x9F:
        return unpack_msgpack_array(data, cursor, marker & 0x0F)
    if 0x80 <= marker <= 0x8F:
        return unpack_msgpack_map(data, cursor, marker & 0x0F)

    if marker == 0xC0:
        return None, cursor
    if marker == 0xC2:
        return False, cursor
    if marker == 0xC3:
        return True, cursor
    if marker == 0xCC:
        return data[cursor], cursor + 1
    if marker == 0xCD:
        return int.from_bytes(data[cursor : cursor + 2], "big"), cursor + 2
    if marker == 0xCE:
        return int.from_bytes(data[cursor : cursor + 4], "big"), cursor + 4
    if marker == 0xCF:
        return int.from_bytes(data[cursor : cursor + 8], "big"), cursor + 8
    if marker == 0xD0:
        return int.from_bytes(data[cursor : cursor + 1], "big", signed=True), cursor + 1
    if marker == 0xD1:
        return int.from_bytes(data[cursor : cursor + 2], "big", signed=True), cursor + 2
    if marker == 0xD2:
        return int.from_bytes(data[cursor : cursor + 4], "big", signed=True), cursor + 4
    if marker == 0xD3:
        return int.from_bytes(data[cursor : cursor + 8], "big", signed=True), cursor + 8
    if marker == 0xCA:
        import struct

        return struct.unpack(">f", data[cursor : cursor + 4])[0], cursor + 4
    if marker == 0xCB:
        import struct

        return struct.unpack(">d", data[cursor : cursor + 8])[0], cursor + 8
    if marker in {0xC4, 0xD9}:
        size = data[cursor]
        cursor += 1
        return unpack_msgpack_bytes_or_string(data, cursor, size, marker == 0xD9)
    if marker in {0xC5, 0xDA}:
        size = int.from_bytes(data[cursor : cursor + 2], "big")
        cursor += 2
        return unpack_msgpack_bytes_or_string(data, cursor, size, marker == 0xDA)
    if marker in {0xC6, 0xDB}:
        size = int.from_bytes(data[cursor : cursor + 4], "big")
        cursor += 4
        return unpack_msgpack_bytes_or_string(data, cursor, size, marker == 0xDB)
    if marker == 0xDC:
        size = int.from_bytes(data[cursor : cursor + 2], "big")
        return unpack_msgpack_array(data, cursor + 2, size)
    if marker == 0xDD:
        size = int.from_bytes(data[cursor : cursor + 4], "big")
        return unpack_msgpack_array(data, cursor + 4, size)
    if marker == 0xDE:
        size = int.from_bytes(data[cursor : cursor + 2], "big")
        return unpack_msgpack_map(data, cursor + 2, size)
    if marker == 0xDF:
        size = int.from_bytes(data[cursor : cursor + 4], "big")
        return unpack_msgpack_map(data, cursor + 4, size)

    raise ValueError(f"Unsupported MessagePack marker: 0x{marker:02x}")


def unpack_msgpack_string(data: bytes, cursor: int, size: int) -> tuple[str, int]:
    end = cursor + size
    return data[cursor:end].decode("utf-8"), end


def unpack_msgpack_bytes_or_string(data: bytes, cursor: int, size: int, is_string: bool) -> tuple[Any, int]:
    end = cursor + size
    raw = data[cursor:end]
    return (raw.decode("utf-8") if is_string else raw), end


def unpack_msgpack_array(data: bytes, cursor: int, size: int) -> tuple[list[Any], int]:
    result = []
    for _ in range(size):
        value, cursor = unpack_msgpack(data, cursor)
        result.append(value)
    return result, cursor


def unpack_msgpack_map(data: bytes, cursor: int, size: int) -> tuple[dict[Any, Any], int]:
    result = {}
    for _ in range(size):
        key, cursor = unpack_msgpack(data, cursor)
        value, cursor = unpack_msgpack(data, cursor)
        result[key] = value
    return result, cursor


def json_safe_msgpack(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe_msgpack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe_msgpack(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe_msgpack(item) for item in value]
    if isinstance(value, bytes):
        return {"type": "bytes", "len": len(value)}
    return value
