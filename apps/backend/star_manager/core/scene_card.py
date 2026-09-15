from __future__ import annotations

from pathlib import Path
from typing import Any

from star_manager.core.card_parser import (
    UNIVERSAL_AUTO_RESOLVER_ID,
    json_safe_msgpack,
    try_unpack_msgpack,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STUDIO_SCENE_MARKER = "【StudioNEOV2】"
KKEX_MARKER = b"KKEx"
SCENE_MAP_GUID_FIELD = "mapInfoGUID"
SCENE_ITEM_INFO_FIELD = "itemInfo"
SCENE_PATTERN_INFO_FIELD = "patternInfo"


def find_png_end(data: bytes) -> int:
    """Return the byte offset immediately after the visible PNG image."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Input is not a PNG file.")

    cursor = len(PNG_SIGNATURE)
    while cursor + 12 <= len(data):
        chunk_size = int.from_bytes(data[cursor : cursor + 4], "big")
        chunk_type = data[cursor + 4 : cursor + 8]
        chunk_end = cursor + 12 + chunk_size
        if chunk_end > len(data):
            raise ValueError("PNG chunk data is truncated.")
        cursor = chunk_end
        if chunk_type == b"IEND":
            return cursor
    raise ValueError("PNG IEND chunk was not found.")


def extract_scene_data(file_bytes: bytes) -> bytes:
    """Return IEND CRC plus the Studio scene payload, if present."""
    png_end = find_png_end(file_bytes)
    if png_end + 1 >= len(file_bytes):
        return b""
    return file_bytes[png_end - 4 :]


def _iter_kkex_payloads(scene_data: bytes) -> list[dict[str, Any]]:
    """Decode length-prefixed Studio KKEx blocks.

    Studio scene files use a small binary envelope for plugin blocks:
    ``KKEx`` + little-endian version + little-endian payload size + MessagePack.
    The embedded character cards have a MessagePack block-table entry named
    ``KKEx`` too, so only envelopes whose version and payload size line up with
    a complete MessagePack value are accepted here.
    """
    payloads: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(scene_data):
        marker_offset = scene_data.find(KKEX_MARKER, cursor)
        if marker_offset < 0:
            break
        header_end = marker_offset + len(KKEX_MARKER) + 8
        if header_end > len(scene_data):
            break

        version_offset = marker_offset + len(KKEX_MARKER)
        version = int.from_bytes(scene_data[version_offset : version_offset + 4], "little")
        size_offset = version_offset + 4
        payload_size = int.from_bytes(scene_data[size_offset : size_offset + 4], "little")
        payload_start = size_offset + 4
        payload_end = payload_start + payload_size
        if version < 0 or payload_size <= 0 or payload_end > len(scene_data):
            cursor = marker_offset + len(KKEX_MARKER)
            continue

        decoded = try_unpack_msgpack(scene_data, payload_start)
        if not decoded or decoded[1] != payload_end or not isinstance(decoded[0], dict):
            cursor = marker_offset + len(KKEX_MARKER)
            continue

        payloads.append(
            {
                "offset": marker_offset,
                "version": version,
                "size": payload_size,
                "payload": decoded[0],
            }
        )
        cursor = payload_end
    return payloads


def _scene_dependency_record(guid: object, *, index: int) -> dict[str, Any] | None:
    mod_id = str(guid or "").strip()
    if not mod_id:
        return None
    return {
        "id": f"scene:{mod_id}:{index}",
        "ModID": mod_id,
        "Name": mod_id,
        "Property": "StudioScene.Map",
        "DependencyType": "scene",
        "mapInfoGUID": mod_id,
    }


def _decode_scene_uar_record(value: object) -> dict[str, Any] | None:
    """Decode one scene UAR record, including its nested MessagePack form."""
    if isinstance(value, bytes):
        decoded = try_unpack_msgpack(value)
        value = decoded[0] if decoded else None
    if not isinstance(value, dict):
        return None
    return value


def _scene_item_dependency_record(
    record: dict[str, Any],
    *,
    dependency_type: str,
    property_name: str,
    index: int,
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Normalize scene item/pattern records into the card dependency shape."""
    mod_id = str(record.get("ModID") or record.get("GUID") or "").strip()
    if not mod_id:
        return None
    context = context or {}
    dependency: dict[str, Any] = {
        "id": f"{dependency_type}:{mod_id}:{record.get('Slot', '')}:{record.get('LocalSlot', '')}:{index}",
        "ModID": mod_id,
        "Name": mod_id,
        "Property": property_name,
        "DependencyType": dependency_type,
    }
    for field in ("CategoryNo", "Slot", "LocalSlot", "SceneDicKey", "SceneObjectOrder"):
        value = record.get(field)
        if value is None and field == "CategoryNo":
            value = record.get("Category")
        if value is None:
            value = context.get(field)
        if value is not None:
            dependency[field] = value
    return dependency


def _scene_uar_dependencies(metadata: dict[str, Any], start_index: int) -> list[dict[str, Any]]:
    """Extract scene item and pattern dependencies from the current UAR format."""
    dependencies: list[dict[str, Any]] = []
    index = start_index

    item_info = metadata.get(SCENE_ITEM_INFO_FIELD)
    if isinstance(item_info, list):
        for raw_record in item_info:
            record = _decode_scene_uar_record(raw_record)
            if not record:
                continue
            dependency = _scene_item_dependency_record(
                record,
                dependency_type="scene_item",
                property_name="StudioScene.Item",
                index=index,
            )
            if dependency:
                dependencies.append(dependency)
                index += 1

    pattern_info = metadata.get(SCENE_PATTERN_INFO_FIELD)
    if isinstance(pattern_info, list):
        for raw_pattern in pattern_info:
            pattern = _decode_scene_uar_record(raw_pattern)
            if not pattern:
                continue
            object_pattern_info = pattern.get("ObjectPatternInfo")
            if not isinstance(object_pattern_info, dict):
                continue
            for raw_record in object_pattern_info.values():
                record = _decode_scene_uar_record(raw_record)
                if not record:
                    continue
                dependency = _scene_item_dependency_record(
                    record,
                    dependency_type="scene_pattern",
                    property_name="StudioScene.Pattern",
                    index=index,
                    context=pattern,
                )
                if dependency:
                    dependencies.append(dependency)
                    index += 1
    return dependencies


def inspect_scene_card_bytes(file_bytes: bytes) -> dict[str, Any] | None:
    """Inspect a Studio scene PNG without modifying it.

    Scene map dependencies are stored in the scene-level UAR plugin payload as
    ``mapInfoGUID``. Newer scene cards additionally store object dependencies
    in ``itemInfo`` and ``patternInfo`` rather than the item-oriented ``info``
    records used by character and clothes cards.
    """
    try:
        scene_data = extract_scene_data(file_bytes)
    except (TypeError, ValueError):
        return None
    marker_bytes = STUDIO_SCENE_MARKER.encode("utf-8")
    marker_offset = scene_data.find(marker_bytes)
    if marker_offset < 0:
        return None

    kkex_blocks = _iter_kkex_payloads(scene_data)
    dependencies: list[dict[str, Any]] = []
    plugin_ids: set[str] = set()
    for block in kkex_blocks:
        payload = block["payload"]
        for plugin_id, plugin_payload in payload.items():
            plugin_name = str(plugin_id)
            plugin_ids.add(plugin_name)
            if plugin_name != UNIVERSAL_AUTO_RESOLVER_ID:
                continue
            if not isinstance(plugin_payload, list) or len(plugin_payload) < 2:
                continue
            metadata = plugin_payload[1]
            if not isinstance(metadata, dict):
                continue
            dependency = _scene_dependency_record(
                metadata.get(SCENE_MAP_GUID_FIELD), index=len(dependencies)
            )
            if dependency:
                dependencies.append(dependency)
            dependencies.extend(_scene_uar_dependencies(metadata, len(dependencies)))

    unique_dependencies: list[dict[str, Any]] = []
    seen_dependencies: set[tuple[str, str, str, str]] = set()
    for dependency in dependencies:
        dependency_type = str(dependency.get("DependencyType") or "scene")
        mod_id = str(dependency.get("ModID") or "")
        slot = str(dependency.get("Slot") or "")
        local_slot = str(dependency.get("LocalSlot") or "")
        key = (dependency_type, mod_id, slot, local_slot)
        if key in seen_dependencies:
            continue
        seen_dependencies.add(key)
        unique_dependencies.append(dependency)

    return {
        "is_scene_card": True,
        "scene_marker": STUDIO_SCENE_MARKER,
        "scene_marker_offset": marker_offset,
        "kkex_count": len(kkex_blocks),
        "plugin_ids": sorted(plugin_ids),
        "dependencies": [json_safe_msgpack(item) for item in unique_dependencies],
        "dependency_count": len(unique_dependencies),
    }


def inspect_scene_card_file(card_path: Path) -> dict[str, Any] | None:
    try:
        return inspect_scene_card_bytes(card_path.read_bytes())
    except OSError:
        return None
