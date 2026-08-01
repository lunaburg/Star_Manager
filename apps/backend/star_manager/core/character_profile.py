from __future__ import annotations

import calendar
import io
import math
import struct
from pathlib import Path
from typing import Any

from star_manager.core.card_parser import (
    PROFILE_FIELDS,
    extract_character_profile_from_card_data,
    get_card_block,
    read_card_marker,
    read_card_header,
    try_unpack_msgpack,
)
from star_manager.core.coordinate_card import (
    CHARACTER_MARKER,
    atomic_write,
    find_png_end,
    make_card_data,
    pack_msgpack,
    read_character_blocks,
)


EDITABLE_PROFILE_FIELDS = {
    "fullname",
    "personality",
    "birthMonth",
    "birthDay",
    "voiceRate",
    "futanari",
}


class CharacterProfileUpdateError(ValueError):
    pass


CARD_COVER_ASPECT_RATIO = 63 / 88


def _cover_crop_box(image_size: tuple[int, int], crop: dict[str, Any] | None) -> tuple[int, int, int, int]:
    image_width, image_height = image_size
    if image_width <= 0 or image_height <= 0:
        raise CharacterProfileUpdateError("封面图片尺寸无效。")

    if crop is None:
        left = 0.0
        top = 0.0
        width = 1.0
        height = 1.0
    else:
        try:
            left = float(crop.get("left"))
            top = float(crop.get("top"))
            width = float(crop.get("width"))
            height = float(crop.get("height"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise CharacterProfileUpdateError("封面裁剪区域格式无效。") from exc
        if not all(math.isfinite(value) for value in (left, top, width, height)):
            raise CharacterProfileUpdateError("封面裁剪区域包含无效数值。")
        if left < 0 or top < 0 or width <= 0 or height <= 0 or left + width > 1.000001 or top + height > 1.000001:
            raise CharacterProfileUpdateError("封面裁剪区域超出图片范围。")

    region_left = max(0.0, left * image_width)
    region_top = max(0.0, top * image_height)
    region_width = min(image_width - region_left, width * image_width)
    region_height = min(image_height - region_top, height * image_height)
    if region_width / region_height > CARD_COVER_ASPECT_RATIO:
        region_width = region_height * CARD_COVER_ASPECT_RATIO
    else:
        region_height = region_width / CARD_COVER_ASPECT_RATIO

    crop_width = max(1, int(round(region_width)))
    crop_height = max(1, int(round(crop_width / CARD_COVER_ASPECT_RATIO)))
    if crop_height > int(math.floor(region_height)) and region_height >= 1:
        crop_height = max(1, int(math.floor(region_height)))
        crop_width = max(1, int(round(crop_height * CARD_COVER_ASPECT_RATIO)))

    center_x = region_left + region_width / 2
    center_y = region_top + region_height / 2
    crop_left = max(0, min(image_width - crop_width, int(round(center_x - crop_width / 2))))
    crop_top = max(0, min(image_height - crop_height, int(round(center_y - crop_height / 2))))
    return crop_left, crop_top, crop_left + crop_width, crop_top + crop_height


def replace_character_card_cover_file(
    card_path: Path,
    image_path: Path,
    crop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    card_path = card_path.resolve()
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise CharacterProfileUpdateError("未找到选择的封面图片。")
    if image_path.stat().st_size > 50 * 1024 * 1024:
        raise CharacterProfileUpdateError("封面图片不能超过 50 MB。")

    source = card_path.read_bytes()
    png_end = find_png_end(source)
    card_payload = source[png_end:]
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise CharacterProfileUpdateError("当前环境缺少图片处理组件 Pillow。") from exc
    try:
        with Image.open(image_path) as image:
            image.load()
            converted = ImageOps.exif_transpose(image).convert("RGBA")
            crop_box = _cover_crop_box(converted.size, crop)
            fitted = converted.crop(crop_box)
            buffer = io.BytesIO()
            fitted.save(buffer, format="PNG", optimize=True)
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise CharacterProfileUpdateError(f"封面图片无法读取：{exc}") from exc

    replacement_png = buffer.getvalue()
    complete_file = replacement_png + card_payload
    updated_data, _ = make_card_data(complete_file)
    if read_card_marker(updated_data) != CHARACTER_MARKER:
        raise CharacterProfileUpdateError("替换封面后的人物卡校验失败，未修改原文件。")
    atomic_write(card_path, complete_file, overwrite=True)
    return {
        "width": fitted.width,
        "height": fitted.height,
        "source_image": str(image_path),
        "output_size": len(complete_file),
    }


def validate_profile_updates(values: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise CharacterProfileUpdateError("人物参数格式无效。")
    unknown = set(values) - EDITABLE_PROFILE_FIELDS
    if unknown:
        raise CharacterProfileUpdateError(f"不支持修改人物参数：{', '.join(sorted(unknown))}")

    fullname = str(values.get("fullname") or "").strip()
    if not fullname:
        raise CharacterProfileUpdateError("人物姓名不能为空。")
    if len(fullname) > 80:
        raise CharacterProfileUpdateError("人物姓名不能超过 80 个字符。")

    try:
        personality = int(values.get("personality"))
        birth_month = int(values.get("birthMonth"))
        birth_day = int(values.get("birthDay"))
        voice_rate = float(values.get("voiceRate"))
    except (TypeError, ValueError) as exc:
        raise CharacterProfileUpdateError("人物参数中包含无效数值。") from exc
    if not 0 <= personality <= 255:
        raise CharacterProfileUpdateError("性格编号必须在 0 到 255 之间。")
    if not 1 <= birth_month <= 12:
        raise CharacterProfileUpdateError("生日月份必须在 1 到 12 之间。")
    if not 1 <= birth_day <= calendar.monthrange(2000, birth_month)[1]:
        raise CharacterProfileUpdateError("生日日期与所选月份不匹配。")
    if not 0 <= voice_rate <= 1:
        raise CharacterProfileUpdateError("声线数值必须在 0 到 1 之间。")

    futanari_value = values.get("futanari")
    if not isinstance(futanari_value, bool):
        raise CharacterProfileUpdateError("扶她参数必须为布尔值。")
    return {
        "fullname": fullname,
        "personality": personality,
        "birthMonth": birth_month,
        "birthDay": birth_day,
        "voiceRate": voice_rate,
        "futanari": futanari_value,
    }


def find_profile_map(blob: bytes) -> tuple[int, int, dict[Any, Any]]:
    for start in range(0, min(len(blob), 32)):
        if not (0x80 <= blob[start] <= 0x8F or blob[start] in {0xDE, 0xDF}):
            continue
        unpacked = try_unpack_msgpack(blob, start)
        if not unpacked:
            continue
        value, end = unpacked
        if isinstance(value, dict) and PROFILE_FIELDS.intersection(str(key) for key in value):
            return start, end, value
    raise CharacterProfileUpdateError("人物参数区块无法完整解码，未修改原文件。")


def profile_value_spans(blob: bytes, offset: int) -> dict[str, tuple[int, int]]:
    marker = blob[offset]
    cursor = offset + 1
    if 0x80 <= marker <= 0x8F:
        item_count = marker & 0x0F
    elif marker == 0xDE:
        item_count = int.from_bytes(blob[cursor : cursor + 2], "big")
        cursor += 2
    elif marker == 0xDF:
        item_count = int.from_bytes(blob[cursor : cursor + 4], "big")
        cursor += 4
    else:
        raise CharacterProfileUpdateError("人物参数映射格式无效。")

    spans: dict[str, tuple[int, int]] = {}
    for _ in range(item_count):
        key_read = try_unpack_msgpack(blob, cursor)
        if not key_read:
            raise CharacterProfileUpdateError("人物参数键无法解码。")
        key, value_start = key_read
        value_read = try_unpack_msgpack(blob, value_start)
        if not value_read:
            raise CharacterProfileUpdateError(f"人物参数 {key} 无法解码。")
        _, value_end = value_read
        spans[str(key)] = (value_start, value_end)
        cursor = value_end
    return spans


def pack_profile_value(value: Any, original_marker: int) -> bytes:
    if isinstance(value, float) and original_marker == 0xCA:
        return b"\xca" + struct.pack(">f", value)
    if isinstance(value, float) and original_marker == 0xCB:
        return b"\xcb" + struct.pack(">d", value)
    if isinstance(value, int) and not isinstance(value, bool):
        integer_formats = {
            0xCC: (b"\xcc", ">B"),
            0xCD: (b"\xcd", ">H"),
            0xCE: (b"\xce", ">I"),
            0xCF: (b"\xcf", ">Q"),
            0xD0: (b"\xd0", ">b"),
            0xD1: (b"\xd1", ">h"),
            0xD2: (b"\xd2", ">i"),
            0xD3: (b"\xd3", ">q"),
        }
        if original_marker in integer_formats:
            marker, value_format = integer_formats[original_marker]
            try:
                return marker + struct.pack(value_format, value)
            except struct.error:
                pass
    return pack_msgpack(value)


def replace_profile_block(card_data: bytes, block_name: str, updates: dict[str, Any]) -> bytes:
    header = read_card_header(card_data)
    info_offset = header.get("info_offset")
    if header.get("marker") != CHARACTER_MARKER or not isinstance(info_offset, int):
        raise CharacterProfileUpdateError("不是有效的 AIS 人物卡。")

    unpacked = try_unpack_msgpack(card_data, info_offset)
    if not unpacked or not isinstance(unpacked[0], dict):
        raise CharacterProfileUpdateError("人物卡区块表无法解码。")
    table, _ = unpacked
    _, block_base, block_data_size = read_character_blocks(card_data)
    block_infos = table.get("lstInfo")
    target = next(
        (
            item
            for item in block_infos or []
            if isinstance(item, dict) and item.get("name") == block_name
        ),
        None,
    )
    if target is None:
        raise CharacterProfileUpdateError(f"人物卡缺少 {block_name} 参数区块。")

    position = int(target.get("pos", 0))
    size = int(target.get("size", 0))
    if position < 0 or size <= 0 or position + size > block_data_size:
        raise CharacterProfileUpdateError(f"{block_name} 参数区块范围无效。")
    block_data = card_data[block_base : block_base + block_data_size]
    old_blob = block_data[position : position + size]
    map_start, _, profile = find_profile_map(old_blob)
    missing_fields = set(updates) - {str(key) for key in profile}
    if missing_fields:
        raise CharacterProfileUpdateError(
            f"人物卡缺少可写参数：{', '.join(sorted(missing_fields))}"
        )
    spans = profile_value_spans(old_blob, map_start)
    new_blob = old_blob
    for key, value in sorted(updates.items(), key=lambda item: spans[item[0]][0], reverse=True):
        value_start, value_end = spans[key]
        replacement = pack_profile_value(value, old_blob[value_start])
        new_blob = new_blob[:value_start] + replacement + new_blob[value_end:]
    delta = len(new_blob) - size
    new_block_data = block_data[:position] + new_blob + block_data[position + size :]

    target["size"] = len(new_blob)
    if delta:
        for item in block_infos or []:
            if isinstance(item, dict) and item is not target and int(item.get("pos", 0)) > position:
                item["pos"] = int(item.get("pos", 0)) + delta

    new_table = pack_msgpack(table)
    header_prefix = bytearray(card_data[:info_offset])
    if len(header_prefix) < 4:
        raise CharacterProfileUpdateError("人物卡头部长度无效。")
    header_prefix[-4:] = struct.pack("<I", len(new_table))
    suffix = card_data[block_base + block_data_size :]
    return b"".join(
        [
            bytes(header_prefix),
            new_table,
            struct.pack("<Q", len(new_block_data)),
            new_block_data,
            suffix,
        ]
    )


def update_character_profile_file(path: Path, values: dict[str, Any]) -> dict[str, Any]:
    updates = validate_profile_updates(values)
    path = path.resolve()
    source = path.read_bytes()
    card_data, png_end = make_card_data(source)
    updated_data = replace_profile_block(card_data, "Parameter", updates)

    parameter2 = get_card_block(updated_data, "Parameter2")
    if parameter2 and "personality" in find_profile_map(parameter2[1])[2]:
        updated_data = replace_profile_block(
            updated_data,
            "Parameter2",
            {"personality": updates["personality"]},
        )

    profile = extract_character_profile_from_card_data(updated_data)
    for key, expected in updates.items():
        actual = profile.get(key)
        if key == "voiceRate":
            if abs(float(actual) - float(expected)) > 1e-6:
                raise CharacterProfileUpdateError("写回后的声线参数校验失败，未修改原文件。")
        elif actual != expected:
            raise CharacterProfileUpdateError(f"写回后的 {key} 参数校验失败，未修改原文件。")

    complete_file = source[: png_end - 4] + updated_data
    atomic_write(path, complete_file, overwrite=True)
    return profile
