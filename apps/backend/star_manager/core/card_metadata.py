from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from star_manager.core.card_parser import read_card_header, try_unpack_msgpack, unpack_msgpack
from star_manager.core.coordinate_card import (
    CHARACTER_MARKER,
    atomic_write,
    make_card_data,
    pack_msgpack,
    read_character_blocks,
)


CARD_METADATA_PLUGIN_ID = "star.manager.cardmetadata"
CARD_METADATA_SCHEMA_VERSION = 1
KKEX_BLOCK_NAME = "KKEx"
KKEX_BLOCK_VERSION = "3"
MAX_CARD_TAGS = 12
MAX_CARD_TAG_LENGTH = 24
_MISSING = object()


class CardMetadataError(ValueError):
    pass


def _read_extended_metadata(file_data: bytes) -> object:
    try:
        card_data, _ = make_card_data(file_data)
        table, block_base, block_data_size = read_character_blocks(card_data)
        block_info = next(
            (
                item
                for item in table.get("lstInfo", [])
                if isinstance(item, dict) and item.get("name") == KKEX_BLOCK_NAME
            ),
            None,
        )
        if block_info is None:
            return _MISSING
        position = int(block_info.get("pos", 0))
        size = int(block_info.get("size", 0))
        if position < 0 or size < 0 or position + size > block_data_size:
            return _MISSING
        plugins, end = unpack_msgpack(card_data[block_base + position : block_base + position + size])
        if end != size or not isinstance(plugins, dict):
            return _MISSING
        return plugins.get(CARD_METADATA_PLUGIN_ID, _MISSING)
    except (OSError, TypeError, ValueError):
        return _MISSING


def _favorite_from_plugin_payload(payload: object) -> bool:
    return bool(
        isinstance(payload, list)
        and len(payload) == 2
        and isinstance(payload[1], dict)
        and payload[1].get("favorite") is True
    )


def read_card_metadata_bytes(file_data: bytes) -> dict[str, object]:
    """Read all Star Manager metadata fields from one in-memory card image."""
    payload = _read_extended_metadata(file_data)
    if payload is _MISSING:
        return {"favorite": False, "rating": 0, "tags": []}
    return {
        "favorite": _favorite_from_plugin_payload(payload),
        "rating": _rating_from_plugin_payload(payload),
        "tags": _tags_from_plugin_payload(payload),
    }


def read_card_metadata(path: Path | str) -> dict[str, object]:
    """Read favorite, rating, and tags with a single filesystem read."""
    try:
        return read_card_metadata_bytes(Path(path).read_bytes())
    except OSError:
        return {"favorite": False, "rating": 0, "tags": []}


def read_card_favorite(path: Path | str) -> bool:
    return bool(read_card_metadata(path)["favorite"])


def _rating_from_plugin_payload(payload: object) -> int:
    if not (
        isinstance(payload, list)
        and len(payload) == 2
        and isinstance(payload[1], dict)
    ):
        return 0
    rating = payload[1].get("rating")
    return rating if isinstance(rating, int) and not isinstance(rating, bool) and 1 <= rating <= 5 else 0


def read_card_rating(path: Path | str) -> int:
    return int(read_card_metadata(path)["rating"])


def normalize_card_tags(tags: object) -> list[str]:
    if not isinstance(tags, (list, tuple)):
        raise CardMetadataError("人物卡标签必须是字符串列表。")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in tags:
        if not isinstance(value, str):
            raise CardMetadataError("人物卡标签必须是字符串。")
        tag = value.strip()
        if not tag:
            raise CardMetadataError("人物卡标签不能为空。")
        if len(tag) > MAX_CARD_TAG_LENGTH:
            raise CardMetadataError(f"单个标签不能超过 {MAX_CARD_TAG_LENGTH} 个字符。")
        if any(ord(character) < 32 for character in tag):
            raise CardMetadataError("人物卡标签不能包含控制字符。")
        key = tag.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(tag)
        if len(normalized) > MAX_CARD_TAGS:
            raise CardMetadataError(f"每张人物卡最多添加 {MAX_CARD_TAGS} 个标签。")
    return normalized


def _tags_from_plugin_payload(payload: object) -> list[str]:
    if not (
        isinstance(payload, list)
        and len(payload) == 2
        and isinstance(payload[1], dict)
        and isinstance(payload[1].get("tags"), list)
    ):
        return []
    try:
        return normalize_card_tags(payload[1]["tags"])
    except CardMetadataError:
        return []


def read_card_tags(path: Path | str) -> list[str]:
    return list(read_card_metadata(path)["tags"])


def _updated_plugin_payload(existing: object, field: str, value: object) -> object:
    if existing is _MISSING:
        return (
            [CARD_METADATA_SCHEMA_VERSION, {field: value}]
            if value is not _MISSING
            else _MISSING
        )
    if not (
        isinstance(existing, list)
        and len(existing) == 2
        and isinstance(existing[0], int)
        and isinstance(existing[1], dict)
    ):
        raise CardMetadataError("人物卡中的 Star Manager 元数据格式无效，未修改原文件。")

    payload = [existing[0], dict(existing[1])]
    if value is not _MISSING:
        payload[1][field] = value
        return payload
    payload[1].pop(field, None)
    return payload if payload[1] else _MISSING


def _replace_kkex_metadata(card_data: bytes, field: str, value: object) -> bytes:
    header = read_card_header(card_data)
    info_offset = header.get("info_offset")
    if header.get("marker") != CHARACTER_MARKER or not isinstance(info_offset, int):
        raise CardMetadataError("不是有效的 AIS 人物卡。")

    unpacked = try_unpack_msgpack(card_data, info_offset)
    if not unpacked or not isinstance(unpacked[0], dict):
        raise CardMetadataError("人物卡区块表无法解码。")
    table = unpacked[0]
    _, block_base, block_data_size = read_character_blocks(card_data)
    block_infos = table.get("lstInfo")
    if not isinstance(block_infos, list):
        raise CardMetadataError("人物卡区块列表无效。")
    block_data = card_data[block_base : block_base + block_data_size]
    target = next(
        (
            item
            for item in block_infos
            if isinstance(item, dict) and item.get("name") == KKEX_BLOCK_NAME
        ),
        None,
    )

    if target is None:
        if value is _MISSING:
            return card_data
        plugins: dict[Any, Any] = {}
        position = len(block_data)
        old_size = 0
    else:
        position = int(target.get("pos", 0))
        old_size = int(target.get("size", 0))
        if position < 0 or old_size < 0 or position + old_size > block_data_size:
            raise CardMetadataError("人物卡 KKEx 区块范围无效。")
        try:
            plugins, end = unpack_msgpack(block_data[position : position + old_size])
        except (IndexError, TypeError, UnicodeDecodeError, ValueError) as exc:
            raise CardMetadataError("人物卡 KKEx 区块无法完整解码，未修改原文件。") from exc
        if end != old_size or not isinstance(plugins, dict):
            raise CardMetadataError("人物卡 KKEx 区块格式无效，未修改原文件。")

    existing = plugins.get(CARD_METADATA_PLUGIN_ID, _MISSING)
    updated_payload = _updated_plugin_payload(existing, field, value)
    if updated_payload is _MISSING:
        plugins.pop(CARD_METADATA_PLUGIN_ID, None)
    else:
        plugins[CARD_METADATA_PLUGIN_ID] = updated_payload
    new_blob = pack_msgpack(plugins)

    if target is None:
        target = {
            "name": KKEX_BLOCK_NAME,
            "version": KKEX_BLOCK_VERSION,
            "pos": position,
            "size": len(new_blob),
        }
        block_infos.append(target)
    else:
        delta = len(new_blob) - old_size
        target["size"] = len(new_blob)
        if delta:
            for item in block_infos:
                if isinstance(item, dict) and item is not target and int(item.get("pos", 0)) > position:
                    item["pos"] = int(item.get("pos", 0)) + delta

    new_block_data = block_data[:position] + new_blob + block_data[position + old_size :]
    new_table = pack_msgpack(table)
    header_prefix = bytearray(card_data[:info_offset])
    if len(header_prefix) < 4:
        raise CardMetadataError("人物卡头部长度无效。")
    header_prefix[-4:] = struct.pack("<I", len(new_table))
    suffix = card_data[block_base + block_data_size :]
    return b"".join(
        (
            bytes(header_prefix),
            new_table,
            struct.pack("<Q", len(new_block_data)),
            new_block_data,
            suffix,
        )
    )


def set_card_favorite_file(path: Path | str, favorite: bool) -> None:
    card_path = Path(path).resolve()
    source = card_path.read_bytes()
    card_data, png_end = make_card_data(source)
    updated_card_data = _replace_kkex_metadata(
        card_data,
        "favorite",
        True if favorite else _MISSING,
    )
    updated = source[: png_end - 4] + updated_card_data
    atomic_write(card_path, updated, overwrite=True)


def set_card_rating_file(path: Path | str, rating: int) -> None:
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        raise CardMetadataError("人物卡评分必须是 1 到 5 的整数。")
    card_path = Path(path).resolve()
    source = card_path.read_bytes()
    card_data, png_end = make_card_data(source)
    updated_card_data = _replace_kkex_metadata(card_data, "rating", rating)
    updated = source[: png_end - 4] + updated_card_data
    atomic_write(card_path, updated, overwrite=True)


def set_card_tags_file(path: Path | str, tags: object) -> None:
    normalized = normalize_card_tags(tags)
    card_path = Path(path).resolve()
    source = card_path.read_bytes()
    card_data, png_end = make_card_data(source)
    updated_card_data = _replace_kkex_metadata(
        card_data,
        "tags",
        normalized if normalized else _MISSING,
    )
    updated = source[: png_end - 4] + updated_card_data
    atomic_write(card_path, updated, overwrite=True)
