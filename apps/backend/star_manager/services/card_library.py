from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from star_manager.core.card_parser import (
    AIS_CARD_MARKERS,
    extract_auto_resolver_records_from_card,
    extract_character_profile_from_card,
    extract_character_profile_from_card_data,
    is_ais_card,
    read_card_marker,
)
from star_manager.core.card_metadata import (
    CardMetadataError,
    normalize_card_tags,
    read_card_metadata,
    read_card_metadata_bytes,
    read_card_tags,
    set_card_favorite_file,
    set_card_rating_file,
    set_card_tags_file,
)
from star_manager.core.coordinate_card import (
    CoordinateExtractionError,
    convert_character_card,
    make_card_data,
)
from star_manager.core.character_profile import (
    CharacterProfileUpdateError,
    replace_character_card_cover_file,
    update_character_profile_file,
)
from star_manager.core.runtime_paths import runtime_root
from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    get_database_metadata,
    init_db,
    set_database_metadata,
    timestamp_to_utc,
    utc_now,
)
from star_manager.services.mod_database_queries import export_zipmods


CARD_ROOT_PARTS = ("UserData", "chara")
DEFAULT_CARD_PREVIEW_DIR = runtime_root() / "card_previews"
STANDARD_CARD_SIZE = (252, 352)
IGNORED_ROOT_CARD_DIRS = {"navi"}
MANAGED_CARD_GENDER_DIRS = {"female", "male"}
INVALID_WINDOWS_FILENAME_CHARS = '<>:"/\\|?*'
WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
PORTABLE_DEPENDENCY_TYPES = ("face", "hair", "body", "clothes", "accessory")
PORTABLE_DEPENDENCY_CATEGORY_TYPES = {
    "8": "body",
    "110": "face",
    "111": "face",
    "112": "face",
    "121": "face",
    "131": "body",
    "132": "body",
    "133": "body",
    "140": "clothes",
    "141": "clothes",
    "144": "clothes",
    "147": "clothes",
    "210": "face",
    "211": "face",
    "212": "face",
    "231": "body",
    "232": "body",
    "233": "body",
    "240": "clothes",
    "241": "clothes",
    "242": "clothes",
    "243": "clothes",
    "244": "clothes",
    "245": "clothes",
    "246": "clothes",
    "247": "clothes",
    "300": "hair",
    "301": "hair",
    "302": "hair",
    "303": "hair",
    "313": "body",
    "314": "face",
    "315": "face",
    "316": "face",
    "317": "face",
    "318": "face",
    "319": "face",
    "320": "face",
    "322": "face",
    "323": "face",
    "334": "body",
    "335": "body",
    "351": "accessory",
    "352": "accessory",
    "353": "accessory",
    "354": "accessory",
    "355": "accessory",
    "356": "accessory",
    "357": "accessory",
    "358": "accessory",
    "359": "accessory",
    "360": "accessory",
    "361": "accessory",
    "362": "accessory",
    "363": "accessory",
}
PORTABLE_DEPENDENCY_PROPERTY_TYPES = (
    (re.compile(r"chafileface\.(?:headid|skinid|detailid|eyebrowid|eyelashesid|beardid|eyeblack[12]|hlid|moleid)$", re.I), "face"),
    (re.compile(r"makeupinfo\.(?:eyeshadowid|cheekid|lipid)$", re.I), "face"),
    (re.compile(r"chafilehair\.(?:hairback|hairfront|hairside|hairoption|hairextension)$", re.I), "hair"),
    (re.compile(r"chafilebody\.(?:skinid|detailid|sunburnid|paintlayoutid[12]|nipid|underhairid|pubichairid)$", re.I), "body"),
    (re.compile(r"chafileclothes\.(?:clothestop|clothesbot|clothesbra|clothesshorts|clothesgloves|clothespantyhose|clothessocks|clothesshoes)$", re.I), "clothes"),
)


def get_card_root(game_dir: str) -> Path:
    game_path = Path(game_dir)
    userdata = find_child_dir_case_insensitive(game_path, "UserData") or game_path / "UserData"
    return find_child_dir_case_insensitive(userdata, "chara") or userdata / "chara"


def find_child_dir_case_insensitive(parent: Path, name: str) -> Path | None:
    if not parent.is_dir():
        return None

    direct = parent / name
    if direct.is_dir():
        return direct

    target = name.casefold()
    for child in parent.iterdir():
        if child.is_dir() and child.name.casefold() == target:
            return child
    return None


def validate_card_root(game_dir: str) -> tuple[bool, Path, str]:
    if not is_hs2_game_dir(game_dir):
        return False, get_card_root(game_dir), "请选择有效的游戏目录"

    root = get_card_root(game_dir)
    if not root.is_dir():
        return False, root, "请选择有效的游戏目录"

    return True, root, ""


def resolve_card_directory(root: Path, relative_path: str = "") -> Path:
    if normalize_relative_path(relative_path).casefold() in IGNORED_ROOT_CARD_DIRS:
        raise ValueError("Card directory not found.")
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError("Invalid card directory.")
    if not candidate.is_dir():
        raise ValueError("Card directory not found.")
    return candidate


def resolve_card_file(root: Path, relative_path: str) -> Path:
    normalized_relative = normalize_relative_path(relative_path)
    parts = normalized_relative.split("/") if normalized_relative else []
    if parts and parts[0].casefold() in IGNORED_ROOT_CARD_DIRS:
        raise ValueError("Card image not found.")
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if resolved_root not in candidate.parents or not candidate.is_file():
        raise ValueError("Card image not found.")
    return candidate


def resolve_managed_card_directory(root: Path, relative_path: str) -> Path:
    """Resolve a directory inside the managed female/male character-card branches."""
    normalized_relative = normalize_relative_path(relative_path)
    parts = normalized_relative.split("/") if normalized_relative else []
    if not parts or parts[0].casefold() not in MANAGED_CARD_GENDER_DIRS:
        raise ValueError("目标目录必须位于 female 或 male 人物卡目录内。")
    candidate = (root / normalized_relative).resolve()
    resolved_root = root.resolve()
    if resolved_root not in candidate.parents or not candidate.is_dir():
        raise ValueError("人物卡目录不存在。")
    return candidate


def validate_card_folder_name(name: str) -> str:
    folder_name = str(name or "").strip()
    if not folder_name or folder_name in {".", ".."}:
        raise ValueError("请输入目录名称。")
    if folder_name[-1:] in {".", " "}:
        raise ValueError("目录名称不能以空格或句点结尾。")
    if any(character in INVALID_WINDOWS_FILENAME_CHARS for character in folder_name):
        raise ValueError("目录名称包含 Windows 不允许使用的字符。")
    if folder_name.upper() in WINDOWS_RESERVED_FILENAMES:
        raise ValueError("该目录名称为 Windows 保留名称。")
    return folder_name


def create_character_card_directory(game_dir: str, parent_path: str, name: str) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "请选择有效的游戏目录"}
    try:
        parent = resolve_managed_card_directory(root, parent_path)
        folder_name = validate_card_folder_name(name)
        target = parent / folder_name
        if target.exists():
            return {"ok": False, "error": "同名目录已存在。"}
        target.mkdir()
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"新建目录失败：{exc}"}
    return {
        "ok": True,
        "relative_path": normalize_relative(target, root),
        "name": target.name,
    }


def rename_character_card_directory(
    game_dir: str,
    relative_path: str,
    name: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "请选择有效的游戏目录"}
    try:
        source = resolve_managed_card_directory(root, relative_path)
        source_relative = normalize_relative(source, root)
        if len(Path(source_relative).parts) == 1:
            return {"ok": False, "error": "female 和 male 根目录不能重命名。"}
        folder_name = validate_card_folder_name(name)
        target = source.with_name(folder_name)
        if target == source:
            return {"ok": True, "relative_path": source_relative, "name": source.name}
        if target.exists():
            return {"ok": False, "error": "同名目录已存在。"}
        source.rename(target)
        update_character_card_index_directory(source, target, root, db_path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"目录重命名失败：{exc}"}
    return {
        "ok": True,
        "old_relative_path": source_relative,
        "relative_path": normalize_relative(target, root),
        "name": target.name,
    }


def move_character_card(
    game_dir: str,
    relative_path: str,
    target_directory: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    """Move one validated AIS card between managed female/male folders without overwriting."""
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "请选择有效的游戏目录"}
    normalized_relative = normalize_relative_path(relative_path)
    try:
        source = resolve_card_file(root, normalized_relative)
        source_parts = Path(normalized_relative).parts
        if not source_parts or source_parts[0].casefold() not in MANAGED_CARD_GENDER_DIRS:
            return {"ok": False, "error": "人物卡必须位于 female 或 male 目录内。"}
        target_dir = resolve_managed_card_directory(root, target_directory)
        target_parts = Path(normalize_relative(target_dir, root)).parts
        if not target_parts or target_parts[0].casefold() != source_parts[0].casefold():
            return {"ok": False, "error": "人物卡不能移动到另一性别的目录。"}
        if source.suffix.lower() != ".png" or not is_ais_card(str(source)):
            return {"ok": False, "error": "目标文件不是有效的 AIS 人物卡。"}
        target = target_dir / source.name
        if target == source:
            return {"ok": True, "skipped": True, "relative_path": normalized_relative}
        if target.exists():
            return {"ok": False, "error": f"目标目录已存在同名人物卡：{source.name}"}
        shutil.move(str(source), str(target))
        update_character_card_index_file(source, target, root, db_path)
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"人物卡移动失败：{exc}"}
    return {
        "ok": True,
        "old_relative_path": normalized_relative,
        "relative_path": normalize_relative(target, root),
        "file_name": target.name,
    }


def update_character_card_index_file(source: Path, target: Path, root: Path, db_path: Path) -> None:
    resolved_db_path = Path(db_path).resolve()
    if not resolved_db_path.is_file():
        return
    conn = sqlite3.connect(resolved_db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        with conn:
            conn.execute(
                """
                UPDATE character_cards
                SET file_path = ?, relative_path = ?, file_name = ?
                WHERE file_path = ?
                """,
                (
                    str(target.resolve()),
                    normalize_relative(target, root),
                    target.name,
                    str(source.resolve()),
                ),
            )
    finally:
        conn.close()


def update_character_card_index_directory(source: Path, target: Path, root: Path, db_path: Path) -> None:
    resolved_db_path = Path(db_path).resolve()
    if not resolved_db_path.is_file():
        return
    conn = sqlite3.connect(resolved_db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        rows = conn.execute("SELECT id, file_path FROM character_cards").fetchall()
        updates = []
        for row in rows:
            indexed_path = Path(row["file_path"]).resolve()
            try:
                suffix = indexed_path.relative_to(source.resolve())
            except ValueError:
                continue
            moved_path = (target / suffix).resolve()
            updates.append(
                (str(moved_path), normalize_relative(moved_path, root), moved_path.name, int(row["id"]))
            )
        with conn:
            conn.executemany(
                "UPDATE character_cards SET file_path = ?, relative_path = ?, file_name = ? WHERE id = ?",
                updates,
            )
    finally:
        conn.close()


def normalized_card_preview_path(
    card_path: Path,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
    size: tuple[int, int] = STANDARD_CARD_SIZE,
) -> Path:
    stat = card_path.stat()
    key = "|".join(
        [
            str(card_path.resolve()),
            str(stat.st_size),
            str(stat.st_mtime_ns),
            f"{size[0]}x{size[1]}",
        ]
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return preview_dir / digest[:2] / digest[2:4] / f"{digest}.png"


def normalize_card_preview(
    card_path: Path,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
    size: tuple[int, int] = STANDARD_CARD_SIZE,
) -> Path:
    output_path = normalized_card_preview_path(card_path, preview_dir, size)
    if output_path.is_file():
        return output_path

    try:
        from PIL import Image, ImageOps
    except ImportError:
        return card_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(card_path) as image:
        source = image.convert("RGBA")
        fitted = ImageOps.contain(source, size, method=Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", size, (255, 255, 255, 0))
        left = (size[0] - fitted.width) // 2
        top = (size[1] - fitted.height) // 2
        canvas.alpha_composite(fitted, (left, top))
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG", optimize=True)
        output_path.write_bytes(buffer.getvalue())

    return output_path


def delete_character_card(
    game_dir: str,
    relative_path: str,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    """Delete one validated AIS card and its disposable index/cache records."""
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "请选择有效的游戏目录"}

    normalized_relative = normalize_relative_path(relative_path)
    if not normalized_relative:
        return {"ok": False, "error": "未指定要删除的人物卡。"}

    try:
        card_path = resolve_card_file(root, normalized_relative)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if card_path.suffix.lower() != ".png" or not is_ais_card(str(card_path)):
        return {"ok": False, "error": "目标文件不是有效的 AIS 人物卡。"}

    cached_paths: set[Path] = {normalized_card_preview_path(card_path, preview_dir).resolve()}
    resolved_db_path = Path(db_path).resolve()
    if resolved_db_path.is_file():
        conn = sqlite3.connect(resolved_db_path)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            row = conn.execute(
                "SELECT preview_cache_path FROM character_cards WHERE file_path = ?",
                (str(card_path.resolve()),),
            ).fetchone()
            if row and row["preview_cache_path"]:
                cached_paths.add(Path(row["preview_cache_path"]).resolve())
        finally:
            conn.close()

    try:
        card_path.unlink()
    except OSError as exc:
        return {"ok": False, "error": f"人物卡删除失败：{exc}"}

    if resolved_db_path.is_file():
        conn = sqlite3.connect(resolved_db_path)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            with conn:
                conn.execute(
                    "DELETE FROM character_cards WHERE file_path = ?",
                    (str(card_path.resolve()),),
                )
        finally:
            conn.close()

    resolved_preview_dir = Path(preview_dir).resolve()
    for cached_path in cached_paths:
        if resolved_preview_dir in cached_path.parents:
            cached_path.unlink(missing_ok=True)

    return {
        "ok": True,
        "relative_path": normalized_relative,
        "file_name": card_path.name,
    }


def list_character_cards(
    game_dir: str,
    relative_path: str = "",
    db_path: Path = DEFAULT_DB_PATH,
    *,
    recursive: bool = False,
    tag: str = "",
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return invalid_payload(error)

    folder = root if recursive else resolve_card_directory(root, relative_path)
    normalized_tag = str(tag or "").strip().casefold()
    cards = []
    indexed_cards = indexed_card_metadata(db_path)
    metadata_updates: list[tuple[str, str, int, int, int, int, str]] = []
    if recursive:
        card_files = sorted(
            (
                file_path
                for file_path in root.rglob("*.png")
                if not (
                    (relative_parts := Path(normalize_relative(file_path, root)).parts)
                    and relative_parts[0].casefold() in IGNORED_ROOT_CARD_DIRS
                )
            ),
            key=lambda item: normalize_relative(item, root).casefold(),
        )
    else:
        card_files = sorted(folder.iterdir(), key=lambda item: item.name.lower())

    for file_path in card_files:
        if not file_path.is_file() or file_path.suffix.lower() != ".png":
            continue
        resolved_file_path = str(file_path.resolve())
        indexed_card = indexed_cards.get(resolved_file_path.casefold())
        stat = file_path.stat()
        metadata_is_current = bool(
            indexed_card
            and int(indexed_card.get("metadata_file_size") or 0) == stat.st_size
            and int(indexed_card.get("metadata_modified_ns") or 0) == stat.st_mtime_ns
        )
        if metadata_is_current:
            if indexed_card.get("parse_status") != "ok":
                continue
            listing_data = {
                "name": str(indexed_card.get("name") or "").strip() or file_path.stem,
                "favorite": bool(indexed_card.get("favorite")),
                "rating": int(indexed_card.get("rating") or 0),
                "tags": list(indexed_card.get("tags") or []),
            }
        else:
            listing_data = read_character_card_listing_data(file_path)
            if listing_data is None:
                continue
            if indexed_card is not None:
                metadata_updates.append(
                    (
                        str(listing_data["name"]),
                        json.dumps(listing_data["tags"], ensure_ascii=False),
                        int(bool(listing_data["favorite"])),
                        int(listing_data["rating"]),
                        stat.st_size,
                        stat.st_mtime_ns,
                        resolved_file_path,
                    )
                )

        if normalized_tag and not any(
            str(card_tag).strip().casefold() == normalized_tag
            for card_tag in listing_data["tags"]
        ):
            continue

        card_relative_path = normalize_relative(file_path, root)
        indexed_name = str(indexed_card.get("name") or "").strip() if indexed_card else ""
        if metadata_is_current and indexed_name:
            display_name = indexed_name
        else:
            display_name = str(listing_data["name"] or "").strip() or file_path.stem
        image_version = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
        image_url = (
            "/library/cards/image?"
            + f"game_dir={quote(str(Path(game_dir).resolve()))}&path={quote(card_relative_path)}"
            + f"&v={quote(image_version)}"
        )
        cards.append(
            {
                "id": card_relative_path,
                "filename": file_path.name,
                "name": display_name,
                "relative_path": card_relative_path,
                "directory": normalize_relative(file_path.parent, root),
                "absolute_path": str(file_path),
                "thumbnail_url": image_url,
                "cover_url": image_url + "&original=1",
                "modified_at": int(stat.st_mtime),
                "dependency_count": (
                    indexed_card["dependency_count"] if indexed_card is not None else None
                ),
                "missing_count": (
                    indexed_card["missing_count"] if indexed_card is not None else None
                ),
                "favorite": bool(listing_data["favorite"]),
                "rating": int(listing_data["rating"]),
                "tags": list(listing_data["tags"]),
            }
        )

    update_indexed_card_listing_metadata(db_path, metadata_updates)

    return {
        "ok": True,
        "is_valid_game_dir": True,
        "root": str(root),
        "relative_path": normalize_relative(folder, root),
        "cards": cards,
        "total": len(cards),
        "recursive": recursive,
        "tag": str(tag or "").strip(),
    }


def list_character_card_tags(game_dir: str, db_path: Path = DEFAULT_DB_PATH) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error, "tags": []}

    resolved_db_path = Path(db_path).resolve()
    cache_root = str(root.resolve())
    if resolved_db_path.is_file():
        conn = sqlite3.connect(resolved_db_path)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            if get_database_metadata(conn, "character_card_tags_cache_root") == cache_root:
                tags_by_key: dict[str, str] = {}
                for row in conn.execute(
                    """
                    SELECT tags_json
                    FROM character_cards
                    WHERE parse_status != 'stale' AND tags_json != '[]'
                    """
                ):
                    try:
                        cached_tags = json.loads(str(row["tags_json"] or "[]"))
                    except (TypeError, ValueError):
                        continue
                    for tag in cached_tags if isinstance(cached_tags, list) else []:
                        if isinstance(tag, str) and tag.strip():
                            tags_by_key.setdefault(tag.casefold(), tag)
                return {
                    "ok": True,
                    "tags": sorted(tags_by_key.values(), key=str.casefold),
                    "cached": True,
                }
        finally:
            conn.close()

    tags_by_key: dict[str, str] = {}
    cached_by_path: dict[str, str] = {}
    try:
        for card_path in root.rglob("*.png"):
            relative_parts = Path(normalize_relative(card_path, root)).parts
            if relative_parts and relative_parts[0].casefold() in IGNORED_ROOT_CARD_DIRS:
                continue
            if not card_path.is_file() or not is_ais_card(str(card_path)):
                continue
            card_tags = read_card_tags(card_path)
            cached_by_path[str(card_path.resolve())] = json.dumps(card_tags, ensure_ascii=False)
            for tag in card_tags:
                tags_by_key.setdefault(tag.casefold(), tag)
    except OSError as exc:
        return {"ok": False, "error": f"人物卡标签读取失败：{exc}", "tags": []}
    if resolved_db_path.is_file():
        conn = sqlite3.connect(resolved_db_path)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            with conn:
                conn.executemany(
                    "UPDATE character_cards SET tags_json = ? WHERE file_path = ?",
                    [(tags_json, file_path) for file_path, tags_json in cached_by_path.items()],
                )
                set_database_metadata(conn, "character_card_tags_cache_root", cache_root)
        finally:
            conn.close()
    return {
        "ok": True,
        "tags": sorted(tags_by_key.values(), key=str.casefold),
        "cached": False,
    }


def indexed_card_metadata(
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, dict[str, object]]:
    resolved_db_path = db_path.resolve()
    if not resolved_db_path.is_file():
        return {}

    conn = sqlite3.connect(resolved_db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        rows = conn.execute(
            """
            SELECT file_path, chara_name, tags_json, favorite, rating,
                   metadata_file_size, metadata_modified_ns, parse_status,
                   dependency_count, missing_count
            FROM character_cards
            WHERE parse_status != 'stale'
            """
        ).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        conn.close()

    indexed: dict[str, dict[str, object]] = {}
    for row in rows:
        try:
            tags = json.loads(str(row["tags_json"] or "[]"))
        except (TypeError, ValueError):
            tags = []
        indexed[str(row["file_path"]).casefold()] = {
            "name": str(row["chara_name"] or ""),
            "tags": tags if isinstance(tags, list) else [],
            "favorite": bool(row["favorite"]),
            "rating": int(row["rating"] or 0),
            "metadata_file_size": int(row["metadata_file_size"] or 0),
            "metadata_modified_ns": int(row["metadata_modified_ns"] or 0),
            "parse_status": str(row["parse_status"] or ""),
            "dependency_count": int(row["dependency_count"] or 0),
            "missing_count": int(row["missing_count"] or 0),
        }
    return indexed


def read_character_card_listing_data(card_path: Path) -> dict[str, object] | None:
    """Read card validity, display name, and UI metadata in one filesystem pass."""
    try:
        file_data = card_path.read_bytes()
        card_data, _ = make_card_data(file_data)
        if read_card_marker(card_data) not in AIS_CARD_MARKERS:
            return None
        profile = extract_character_profile_from_card_data(card_data)
        metadata = read_card_metadata_bytes(file_data)
    except (OSError, TypeError, ValueError, CoordinateExtractionError):
        return None
    return {
        "name": str(profile.get("fullname") or "").strip() or card_path.stem,
        "favorite": bool(metadata["favorite"]),
        "rating": int(metadata["rating"]),
        "tags": list(metadata["tags"]),
    }


def update_indexed_card_listing_metadata(
    db_path: Path,
    updates: list[tuple[str, str, int, int, int, int, str]],
) -> None:
    if not updates or not db_path.resolve().is_file():
        return
    try:
        conn = sqlite3.connect(db_path.resolve(), timeout=0.1)
        try:
            with conn:
                conn.executemany(
                    """
                    UPDATE character_cards
                    SET chara_name = ?, tags_json = ?, favorite = ?, rating = ?,
                        metadata_file_size = ?, metadata_modified_ns = ?
                    WHERE file_path = ?
                    """,
                    updates,
                )
        finally:
            conn.close()
    except sqlite3.Error:
        # Listing remains correct even if a concurrent database rebuild owns the write lock.
        return


def get_character_card_detail(game_dir: str, relative_path: str) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return invalid_payload(error)

    card_path = resolve_card_file(root, relative_path)
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "Card image not found."}

    profile = extract_character_profile_from_card(str(card_path))
    dependencies = resolve_card_dependencies(str(card_path))
    metadata = read_card_metadata(card_path)
    return {
        "ok": True,
        "is_valid_game_dir": True,
        "card": {
            "id": normalize_relative(card_path, root),
            "filename": card_path.name,
            "name": card_path.stem,
            "relative_path": normalize_relative(card_path, root),
            "absolute_path": str(card_path),
            "modified_at": int(card_path.stat().st_mtime),
            "profile": profile,
            "dependencies": dependencies,
            "favorite": bool(metadata["favorite"]),
            "rating": int(metadata["rating"]),
            "tags": list(metadata["tags"]),
        },
    }


def set_character_card_favorite(
    game_dir: str,
    relative_path: str,
    favorite: bool,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    try:
        set_card_favorite_file(card_path, bool(favorite))
    except (CardMetadataError, OSError) as exc:
        return {"ok": False, "error": f"人物卡收藏状态保存失败：{exc}"}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "收藏信息写入后人物卡校验失败。"}

    stat = card_path.stat()
    index_warning = ""
    try:
        preview = normalize_card_preview(card_path, preview_dir)
        resolved_db_path = Path(db_path).resolve()
        if resolved_db_path.is_file():
            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        UPDATE character_cards
                        SET favorite = ?, metadata_file_size = ?, metadata_modified_ns = ?,
                            preview_cache_path = ?, modified_at = ?, last_scanned_at = ?
                        WHERE file_path = ?
                        """,
                        (
                            int(bool(favorite)),
                            stat.st_size,
                            stat.st_mtime_ns,
                            str(preview) if preview != card_path else "",
                            timestamp_to_utc(stat.st_mtime),
                            utc_now(),
                            str(card_path.resolve()),
                        ),
                    )
            finally:
                conn.close()
    except (OSError, sqlite3.Error) as exc:
        index_warning = f"收藏状态已写入人物卡，但索引刷新失败：{exc}"

    return {
        "ok": True,
        "favorite": bool(favorite),
        "relative_path": normalize_relative(card_path, root),
        "modified_at": int(stat.st_mtime),
        "image_version": f"{stat.st_mtime_ns:x}-{stat.st_size:x}",
        "warning": index_warning,
    }


def set_character_card_rating(
    game_dir: str,
    relative_path: str,
    rating: int,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        return {"ok": False, "error": "人物卡评分必须是 1 到 5 的整数。"}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    try:
        set_card_rating_file(card_path, rating)
    except (CardMetadataError, OSError) as exc:
        return {"ok": False, "error": f"人物卡评分保存失败：{exc}"}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "评分写入后人物卡校验失败。"}

    stat = card_path.stat()
    index_warning = ""
    try:
        preview = normalize_card_preview(card_path, preview_dir)
        resolved_db_path = Path(db_path).resolve()
        if resolved_db_path.is_file():
            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        UPDATE character_cards
                        SET rating = ?, metadata_file_size = ?, metadata_modified_ns = ?,
                            preview_cache_path = ?, modified_at = ?, last_scanned_at = ?
                        WHERE file_path = ?
                        """,
                        (
                            rating,
                            stat.st_size,
                            stat.st_mtime_ns,
                            str(preview) if preview != card_path else "",
                            timestamp_to_utc(stat.st_mtime),
                            utc_now(),
                            str(card_path.resolve()),
                        ),
                    )
            finally:
                conn.close()
    except (OSError, sqlite3.Error) as exc:
        index_warning = f"评分已写入人物卡，但索引刷新失败：{exc}"

    return {
        "ok": True,
        "rating": rating,
        "relative_path": normalize_relative(card_path, root),
        "modified_at": int(stat.st_mtime),
        "image_version": f"{stat.st_mtime_ns:x}-{stat.st_size:x}",
        "warning": index_warning,
    }


def set_character_card_tags(
    game_dir: str,
    relative_path: str,
    tags: object,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    try:
        set_card_tags_file(card_path, tags)
    except (CardMetadataError, OSError) as exc:
        return {"ok": False, "error": f"人物卡标签保存失败：{exc}"}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "标签写入后人物卡校验失败。"}

    metadata = read_card_metadata(card_path)
    saved_tags = list(metadata["tags"])
    stat = card_path.stat()
    index_warning = ""
    try:
        preview = normalize_card_preview(card_path, preview_dir)
        resolved_db_path = Path(db_path).resolve()
        if resolved_db_path.is_file():
            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    cursor = conn.execute(
                        """
                        UPDATE character_cards
                        SET tags_json = ?, favorite = ?, rating = ?, metadata_file_size = ?,
                            metadata_modified_ns = ?, preview_cache_path = ?, modified_at = ?,
                            last_scanned_at = ?
                        WHERE file_path = ?
                        """,
                        (
                            json.dumps(saved_tags, ensure_ascii=False),
                            int(bool(metadata["favorite"])),
                            int(metadata["rating"]),
                            stat.st_size,
                            stat.st_mtime_ns,
                            str(preview) if preview != card_path else "",
                            timestamp_to_utc(stat.st_mtime),
                            utc_now(),
                            str(card_path.resolve()),
                        ),
                    )
                    if cursor.rowcount == 0:
                        set_database_metadata(conn, "character_card_tags_cache_root", "")
            finally:
                conn.close()
    except (OSError, sqlite3.Error) as exc:
        index_warning = f"标签已写入人物卡，但索引刷新失败：{exc}"

    return {
        "ok": True,
        "tags": saved_tags,
        "relative_path": normalize_relative(card_path, root),
        "modified_at": int(stat.st_mtime),
        "image_version": f"{stat.st_mtime_ns:x}-{stat.st_size:x}",
        "warning": index_warning,
    }


def add_character_card_tags(
    game_dir: str,
    relative_path: str,
    tags: object,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    try:
        additions = normalize_card_tags(tags)
    except CardMetadataError as exc:
        return {"ok": False, "error": str(exc)}
    if not additions:
        return {"ok": False, "error": "请至少选择一个要添加的标签。"}

    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    current = read_card_tags(card_path)
    try:
        merged = normalize_card_tags([*current, *additions])
    except CardMetadataError as exc:
        return {"ok": False, "error": str(exc)}
    return set_character_card_tags(
        game_dir,
        relative_path,
        merged,
        db_path=db_path,
        preview_dir=preview_dir,
    )


def update_character_card_profile(
    game_dir: str,
    relative_path: str,
    values: dict,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}

    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    try:
        profile = update_character_profile_file(card_path, values)
    except (CharacterProfileUpdateError, OSError, TypeError, OverflowError) as exc:
        return {"ok": False, "error": f"人物参数保存失败：{exc}"}

    stat = card_path.stat()
    index_warning = ""
    resolved_db_path = Path(db_path).resolve()
    try:
        preview = normalize_card_preview(card_path, preview_dir)
        if resolved_db_path.is_file():
            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        UPDATE character_cards
                        SET chara_name = ?, metadata_file_size = ?, metadata_modified_ns = ?,
                            preview_cache_path = ?, modified_at = ?, last_scanned_at = ?
                        WHERE file_path = ?
                        """,
                        (
                            str(profile.get("fullname") or card_path.stem),
                            stat.st_size,
                            stat.st_mtime_ns,
                            str(preview) if preview != card_path else "",
                            timestamp_to_utc(stat.st_mtime),
                            utc_now(),
                            str(card_path.resolve()),
                        ),
                    )
            finally:
                conn.close()
    except (OSError, sqlite3.Error) as exc:
        index_warning = f"人物卡已保存，但索引刷新失败：{exc}"

    return {
        "ok": True,
        "relative_path": normalize_relative(card_path, root),
        "modified_at": int(stat.st_mtime),
        "profile": profile,
        "warning": index_warning,
    }


def replace_character_card_cover(
    game_dir: str,
    relative_path: str,
    image_path: str,
    crop: dict | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    try:
        report = replace_character_card_cover_file(card_path, Path(image_path), crop)
    except (CharacterProfileUpdateError, OSError) as exc:
        return {"ok": False, "error": f"人物卡封面替换失败：{exc}"}

    stat = card_path.stat()
    index_warning = ""
    try:
        preview = normalize_card_preview(card_path, preview_dir)
        resolved_db_path = Path(db_path).resolve()
        if resolved_db_path.is_file():
            conn = sqlite3.connect(resolved_db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        UPDATE character_cards
                        SET metadata_file_size = ?, metadata_modified_ns = ?, preview_cache_path = ?,
                            modified_at = ?, last_scanned_at = ?
                        WHERE file_path = ?
                        """,
                        (
                            stat.st_size,
                            stat.st_mtime_ns,
                            str(preview) if preview != card_path else "",
                            timestamp_to_utc(stat.st_mtime),
                            utc_now(),
                            str(card_path.resolve()),
                        ),
                    )
            finally:
                conn.close()
    except (OSError, sqlite3.Error) as exc:
        index_warning = f"封面已替换，但索引刷新失败：{exc}"

    return {
        "ok": True,
        "relative_path": normalize_relative(card_path, root),
        "modified_at": int(stat.st_mtime),
        "image_version": f"{stat.st_mtime_ns:x}-{stat.st_size:x}",
        "warning": index_warning,
        **report,
    }


def set_character_card_as_navi(game_dir: str, relative_path: str, slot: str) -> dict:
    """Replace one of the game's two navigation character card slots."""
    normalized_slot = str(slot or "").strip().casefold()
    if normalized_slot not in {"navi", "sitri"}:
        return {"ok": False, "error": "看板娘槽位只能是 navi 或 sitri。"}

    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}

    source = resolve_card_file(root, relative_path)
    if not is_ais_card(str(source)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    target_dir = find_child_dir_case_insensitive(root, "navi") or root / "navi"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{normalized_slot}.png"
    shutil.copy2(source, target)
    return {
        "ok": True,
        "slot": normalized_slot,
        "source_path": str(source),
        "target_path": str(target),
    }


def export_character_card_coordinate(
    game_dir: str,
    relative_path: str,
    coordinate_name: str = "",
    custom_output_dir: str = "",
) -> dict:
    """Export one character card's current outfit to the configured directory."""
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}

    source = resolve_card_file(root, relative_path)
    if not is_ais_card(str(source)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    name = "".join(
        character for character in str(coordinate_name or source.stem).strip()
        if character >= " "
    )
    if not name:
        name = source.stem
    name = name[:120]

    source_relative = source.relative_to(root.resolve())
    sex_folder = source_relative.parts[0].casefold() if source_relative.parts else "female"
    if sex_folder not in {"female", "male"}:
        sex_folder = "female"

    configured_output = str(custom_output_dir or "").strip()
    if configured_output:
        output_dir = Path(configured_output).expanduser().resolve()
        if not output_dir.is_dir():
            return {"ok": False, "error": "配置的服装卡导出路径不存在或不是文件夹。"}
    else:
        userdata = root.parent
        coordinate_root = (
            find_child_dir_case_insensitive(userdata, "coordinate")
            or userdata / "coordinate"
        )
        output_dir = (
            find_child_dir_case_insensitive(coordinate_root, sex_folder)
            or coordinate_root / sex_folder
        )
        output_dir.mkdir(parents=True, exist_ok=True)
    output = unique_coordinate_output_path(output_dir, safe_coordinate_filename(name))

    try:
        report = convert_character_card(
            source,
            output,
            name=name,
            preview=source,
            overwrite=False,
        )
    except (CoordinateExtractionError, OSError, TypeError, OverflowError) as exc:
        return {"ok": False, "error": f"服装卡导出失败：{exc}"}

    return {
        "ok": True,
        "source_path": str(source),
        "target_path": str(output),
        "coordinate_name": name,
        "coordinate_dependencies": int(report.get("coordinate_dependencies") or 0),
        "copied_plugins": list(report.get("copied_plugins") or []),
        "skipped_plugins": list(report.get("skipped_plugins") or []),
        "output_size": int(report.get("output_size") or 0),
    }


def safe_coordinate_filename(name: str) -> str:
    translation = str.maketrans({character: "_" for character in INVALID_WINDOWS_FILENAME_CHARS})
    filename = name.translate(translation).strip(" .") or "coordinate"
    if filename.upper() in WINDOWS_RESERVED_FILENAMES:
        filename = f"_{filename}"
    return filename[:120]


def unique_coordinate_output_path(output_dir: Path, filename: str) -> Path:
    candidate = output_dir / f"{filename}.png"
    suffix = 2
    while candidate.exists():
        candidate = output_dir / f"{filename}_{suffix}.png"
        suffix += 1
    return candidate


def export_character_dependency_package(
    game_dir: str,
    relative_path: str,
    target_dir: str,
    compress: bool = True,
    dependency_types: object = None,
    db_path: Path = DEFAULT_DB_PATH,
    progress_callback=None,
) -> dict:
    """Copy one character card and all locally resolved dependencies into a portable bundle."""
    is_valid, card_root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error}

    source = resolve_card_file(card_root, relative_path)
    if not is_ais_card(str(source)):
        return {"ok": False, "error": "未找到有效的人物卡。"}

    export_root = Path(str(target_dir or "")).expanduser().resolve()
    if not str(target_dir or "").strip() or not export_root.is_dir():
        return {"ok": False, "error": "请选择有效的便携依赖包导出目录。"}

    try:
        selected_dependency_types = normalize_portable_dependency_types(dependency_types)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    all_dependencies = resolve_card_dependencies(str(source), db_path=db_path)
    dependency_type_counts = {dependency_type: 0 for dependency_type in PORTABLE_DEPENDENCY_TYPES}
    dependencies = []
    unclassified_dependency_count = 0
    for dependency in all_dependencies:
        dependency_type = portable_dependency_type(dependency)
        if dependency_type is None:
            unclassified_dependency_count += 1
            continue
        dependency_type_counts[dependency_type] += 1
        if dependency_type in selected_dependency_types:
            dependencies.append(dependency)
    zipmods_by_id: dict[int, dict] = {}
    missing_mod_ids: set[str] = set()
    for dependency in dependencies:
        zipmod = dependency.get("zipmod") or {}
        try:
            zipmod_id = int(zipmod.get("id") or 0)
        except (TypeError, ValueError):
            zipmod_id = 0
        if zipmod_id > 0:
            zipmods_by_id[zipmod_id] = zipmod
        elif dependency.get("mod_id"):
            missing_mod_ids.add(str(dependency["mod_id"]))

    package_name = f"{safe_coordinate_filename(source.stem)}_便携依赖包"
    staging_root = export_root / f".star_manager_{uuid4().hex}"
    output_path = unique_dependency_package_path(export_root, package_name, bool(compress))
    bundle_root = staging_root if compress else output_path

    try:
        bundle_root.mkdir(parents=True, exist_ok=False)
        card_relative = source.relative_to(card_root.resolve())
        card_target = bundle_root / "UserData" / "chara" / card_relative
        card_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, card_target)
        if progress_callback is not None:
            progress_callback(10, "人物卡已复制")

        export_result = {
            "ok": True,
            "exported_count": 0,
            "exported_unity3d_count": 0,
            "failure_count": 0,
            "failures": [],
        }
        if zipmods_by_id:
            def report_zipmod_progress(index: int, total: int, zipmod_id: int) -> None:
                if progress_callback is not None:
                    value = 10 + int((index / max(total, 1)) * 65)
                    progress_callback(value, f"正在复制依赖 {index}/{total}")

            export_result = export_zipmods(
                zipmods_by_id.keys(),
                str(bundle_root),
                "copy",
                "portable",
                db_path=db_path,
                progress_callback=report_zipmod_progress,
            )

        manifest = {
            "schema_version": 1,
            "package_name": package_name,
            "card": {
                "name": source.stem,
                "source_relative_path": str(card_relative).replace("\\", "/"),
                "package_path": str(card_target.relative_to(bundle_root)).replace("\\", "/"),
            },
            "selected_dependency_types": list(selected_dependency_types),
            "dependency_type_counts": dependency_type_counts,
            "dependency_record_count": len(dependencies),
            "total_dependency_record_count": len(all_dependencies),
            "excluded_dependency_record_count": len(all_dependencies) - len(dependencies),
            "unclassified_dependency_record_count": unclassified_dependency_count,
            "resolved_zipmod_count": int(export_result.get("exported_count") or 0),
            "external_unity3d_count": int(export_result.get("exported_unity3d_count") or 0),
            "missing_mod_ids": sorted(missing_mod_ids, key=str.casefold),
            "copy_failures": list(export_result.get("failures") or []),
            "zipmods": [
                {
                    "id": zipmod_id,
                    "guid": zipmod.get("guid") or "",
                    "name": zipmod.get("name") or "",
                    "author": zipmod.get("author") or "",
                    "version": zipmod.get("version") or "",
                }
                for zipmod_id, zipmod in sorted(zipmods_by_id.items())
            ],
        }
        manifest_path = bundle_root / "Star_Manager_依赖清单.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if progress_callback is not None:
            progress_callback(82, "依赖清单已生成")

        if compress:
            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                files = [path for path in bundle_root.rglob("*") if path.is_file()]
                for index, path in enumerate(files, start=1):
                    archive.write(path, path.relative_to(bundle_root))
                    if progress_callback is not None and (index == len(files) or index % 10 == 0):
                        progress_callback(82 + int((index / max(len(files), 1)) * 17), f"正在压缩 {index}/{len(files)}")
            shutil.rmtree(bundle_root)

        return {
            "ok": True,
            "compressed": bool(compress),
            "target_path": str(output_path),
            "card_path": str(card_target if not compress else Path("UserData") / "chara" / card_relative),
            "dependency_count": len(dependencies),
            "total_dependency_count": len(all_dependencies),
            "excluded_dependency_count": len(all_dependencies) - len(dependencies),
            "selected_dependency_types": list(selected_dependency_types),
            "dependency_type_counts": dependency_type_counts,
            "exported_zipmod_count": int(export_result.get("exported_count") or 0),
            "exported_unity3d_count": int(export_result.get("exported_unity3d_count") or 0),
            "missing_mod_ids": sorted(missing_mod_ids, key=str.casefold),
            "failure_count": int(export_result.get("failure_count") or 0),
            "failures": list(export_result.get("failures") or []),
        }
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        if bundle_root.exists():
            shutil.rmtree(bundle_root, ignore_errors=True)
        if compress and output_path.exists():
            output_path.unlink(missing_ok=True)
        return {"ok": False, "error": f"便携依赖包生成失败：{exc}"}


def normalize_portable_dependency_types(dependency_types: object) -> tuple[str, ...]:
    if dependency_types is None:
        return PORTABLE_DEPENDENCY_TYPES
    if not isinstance(dependency_types, (list, tuple, set)):
        raise ValueError("导出的模组类型配置无效。")

    requested = {str(value).strip() for value in dependency_types}
    unknown = sorted(requested.difference(PORTABLE_DEPENDENCY_TYPES))
    if unknown:
        raise ValueError(f"不支持的模组类型：{', '.join(unknown)}")
    return tuple(value for value in PORTABLE_DEPENDENCY_TYPES if value in requested)


def portable_dependency_type(dependency: dict) -> str | None:
    property_name = re.sub(r"^outfit\.", "", str(dependency.get("property") or ""), flags=re.I)
    category_type = PORTABLE_DEPENDENCY_CATEGORY_TYPES.get(str(dependency.get("category_no") or "").strip())
    if re.match(r"^accessory\d+\.", property_name, flags=re.I) and category_type:
        return category_type

    for pattern, dependency_type in PORTABLE_DEPENDENCY_PROPERTY_TYPES:
        if pattern.search(property_name):
            return dependency_type
    if category_type:
        return category_type

    kind = str((dependency.get("item") or {}).get("kind") or "")
    if "面部" in kind:
        return "face"
    if "头发" in kind:
        return "hair"
    if "身体" in kind:
        return "body"
    if "服饰" in kind:
        return "clothes"
    if "饰品" in kind:
        return "accessory"
    return None


def unique_dependency_package_path(output_dir: Path, package_name: str, compress: bool) -> Path:
    suffix = ".zip" if compress else ""
    candidate = output_dir / f"{package_name}{suffix}"
    index = 2
    while candidate.exists():
        candidate = output_dir / f"{package_name}_{index}{suffix}"
        index += 1
    return candidate


def resolve_card_dependencies(card_path: str, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    records = extract_auto_resolver_records_from_card(card_path)
    resolved = []
    db_exists = db_path.resolve().is_file()
    conn = None
    if db_exists:
        conn = sqlite3.connect(db_path.resolve())
        conn.row_factory = sqlite3.Row

    try:
        for index, record in enumerate(records):
            mod_id = str(record.get("ModID") or "").strip()
            category = dependency_record_value(record.get("CategoryNo"))
            slot = dependency_record_value(record.get("Slot"))
            local_slot = dependency_record_value(record.get("LocalSlot"))
            item = find_dependency_item(conn, mod_id, category, slot, local_slot) if conn and mod_id else None
            zipmod = find_dependency_zipmod(conn, mod_id) if conn and mod_id else None
            resolved.append(
                {
                    "id": f"{mod_id}:{category}:{slot}:{local_slot}:{index}",
                    "mod_id": mod_id,
                    "name": str(record.get("Name") or ""),
                    "author": str(record.get("Author") or ""),
                    "property": str(record.get("Property") or ""),
                    "category_no": category,
                    "slot": slot,
                    "local_slot": local_slot,
                    "matched": bool(item),
                    "zipmod": zipmod,
                    "item": item,
                }
            )
    finally:
        if conn is not None:
            conn.close()

    return resolved


def dependency_record_value(value: object) -> str:
    """Normalize resolver fields without discarding valid numeric zero values."""
    if value is None:
        return ""
    return str(value).strip()


def find_dependency_item(
    conn: sqlite3.Connection | None,
    mod_id: str,
    category: str,
    slot: str,
    local_slot: str,
) -> dict | None:
    if conn is None:
        return None
    for require_kind in (True, False):
        if require_kind and not category:
            continue
        kind_clause = "AND mod_items.kind = ?" if require_kind else ""
        for item_id in [slot, local_slot]:
            if not item_id:
                continue
            params = (
                (mod_id, category, item_id, item_id, item_id, item_id)
                if require_kind
                else (mod_id, item_id, item_id, item_id, item_id)
            )
            row = conn.execute(
                f"""
                SELECT mod_items.id, mod_items.zipmod_id, mod_items.zipmod_guid, mod_items.zipmod_author,
                       mod_items.item_id, mod_items.kind, mod_items.name, mod_items.thumbnail_cache_path,
                       mod_items.thumbnail_status, mod_items.parse_status,
                       zipmods.name AS zipmod_name, zipmods.file_name AS zipmod_file_name
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE zipmods.scan_status != 'stale'
                  AND trim(mod_items.zipmod_guid) = trim(?) COLLATE NOCASE
                  {kind_clause}
                  AND (
                      mod_items.item_id = ?
                      OR (
                          mod_items.item_id != '' AND mod_items.item_id NOT GLOB '*[^0-9]*'
                          AND ? != '' AND ? NOT GLOB '*[^0-9]*'
                          AND ltrim(mod_items.item_id, '0') = ltrim(?, '0')
                      )
                  )
                LIMIT 1
                """,
                params,
            ).fetchone()
            if row:
                return dependency_item_payload(row, category)
    return None


def find_dependency_zipmod(conn: sqlite3.Connection | None, mod_id: str) -> dict | None:
    if conn is None:
        return None
    row = conn.execute(
        """
        SELECT id, guid, name, author, version, file_name
        FROM zipmods
        WHERE scan_status != 'stale' AND trim(guid) = trim(?) COLLATE NOCASE
        LIMIT 1
        """,
        (mod_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "guid": row["guid"],
        "name": row["name"] or row["file_name"],
        "author": row["author"],
        "version": row["version"],
    }


def dependency_item_payload(row: sqlite3.Row, category: str) -> dict:
    return {
        "id": row["id"],
        "zipmod_id": row["zipmod_id"],
        "zipmod_guid": row["zipmod_guid"],
        "source_mod": row["zipmod_name"] or row["zipmod_file_name"],
        "author": row["zipmod_author"],
        "item_id": row["item_id"],
        "kind": row["kind"] or category,
        "name": row["name"],
        "thumbnail_status": row["thumbnail_status"],
        "thumbnail_url": f"/mods/thumbnails?path={quote(row['thumbnail_cache_path'])}"
        if row["thumbnail_cache_path"]
        else "",
        "status": row["parse_status"],
    }


def build_character_card_tree(game_dir: str) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return invalid_payload(error)

    resolved_root = root.resolve()
    node = build_tree_node(root, resolved_root)
    return {
        "ok": True,
        "is_valid_game_dir": True,
        "root": str(root),
        "tree": node,
        "total": count_tree_cards(node),
    }


def build_tree_node(folder: Path, root: Path) -> dict:
    entries = sorted(folder.iterdir(), key=lambda item: item.name.lower())
    children = [
        build_tree_node(child, root)
        for child in entries
        if child.is_dir() and not is_ignored_root_card_dir(child, root)
    ]
    relative_path = normalize_relative(folder, root)
    return {
        "id": relative_path or ".",
        "name": "人物卡" if folder.resolve() == root.resolve() else folder.name,
        "relative_path": relative_path,
        "count": count_direct_cards(entries),
        "children": children,
        "has_children": bool(children),
    }


def count_direct_cards(entries: list[Path]) -> int:
    count = 0
    for file_path in entries:
        if file_path.is_file() and file_path.suffix.lower() == ".png" and is_ais_card(str(file_path)):
            count += 1
    return count


def count_tree_cards(node: dict) -> int:
    return int(node["count"]) + sum(count_tree_cards(child) for child in node["children"])


def invalid_payload(error: str) -> dict:
    return {
        "ok": True,
        "is_valid_game_dir": False,
        "error": error,
        "tree": None,
        "cards": [],
        "total": 0,
    }


def normalize_relative(path: Path, root: Path) -> str:
    relative = os.path.relpath(path, root)
    if relative == ".":
        return ""
    return relative.replace(os.sep, "/")


def normalize_relative_path(relative_path: str) -> str:
    return str(relative_path or "").strip().replace("\\", "/").strip("/")


def is_ignored_root_card_dir(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return len(relative.parts) == 1 and relative.parts[0].casefold() in IGNORED_ROOT_CARD_DIRS
