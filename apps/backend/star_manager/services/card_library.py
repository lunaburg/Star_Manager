from __future__ import annotations

import hashlib
import io
import os
import sqlite3
from pathlib import Path
from urllib.parse import quote

from star_manager.core.card_parser import (
    extract_auto_resolver_records_from_card,
    extract_character_profile_from_card,
    is_ais_card,
)
from star_manager.core.runtime_paths import runtime_root
from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.mod_database_core import DEFAULT_DB_PATH, init_db


CARD_ROOT_PARTS = ("UserData", "chara")
DEFAULT_CARD_PREVIEW_DIR = runtime_root() / "card_previews"
STANDARD_CARD_SIZE = (252, 352)
IGNORED_ROOT_CARD_DIRS = {"navi"}


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


def list_character_cards(game_dir: str, relative_path: str = "") -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return invalid_payload(error)

    folder = resolve_card_directory(root, relative_path)
    cards = []
    for file_path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if not file_path.is_file() or file_path.suffix.lower() != ".png":
            continue
        if not is_ais_card(str(file_path)):
            continue

        card_relative_path = normalize_relative(file_path, root)
        stat = file_path.stat()
        image_version = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
        cards.append(
            {
                "id": card_relative_path,
                "filename": file_path.name,
                "name": file_path.stem,
                "relative_path": card_relative_path,
                "directory": normalize_relative(file_path.parent, root),
                "absolute_path": str(file_path),
                "thumbnail_url": "/library/cards/image?"
                + f"game_dir={quote(str(Path(game_dir).resolve()))}&path={quote(card_relative_path)}"
                + f"&v={quote(image_version)}",
                "modified_at": int(stat.st_mtime),
            }
        )

    return {
        "ok": True,
        "is_valid_game_dir": True,
        "root": str(root),
        "relative_path": normalize_relative(folder, root),
        "cards": cards,
        "total": len(cards),
        "recursive": False,
    }


def get_character_card_detail(game_dir: str, relative_path: str) -> dict:
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return invalid_payload(error)

    card_path = resolve_card_file(root, relative_path)
    if not is_ais_card(str(card_path)):
        return {"ok": False, "error": "Card image not found."}

    profile = extract_character_profile_from_card(str(card_path))
    dependencies = resolve_card_dependencies(str(card_path))
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
        },
    }


def resolve_card_dependencies(card_path: str, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    records = extract_auto_resolver_records_from_card(card_path)
    resolved = []
    db_exists = db_path.resolve().is_file()
    conn = None
    if db_exists:
        conn = sqlite3.connect(db_path.resolve())
        conn.row_factory = sqlite3.Row
        init_db(conn)

    try:
        for index, record in enumerate(records):
            mod_id = str(record.get("ModID") or "").strip()
            category = str(record.get("CategoryNo") or "").strip()
            slot = str(record.get("Slot") or "").strip()
            local_slot = str(record.get("LocalSlot") or "").strip()
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


def find_dependency_item(
    conn: sqlite3.Connection | None,
    mod_id: str,
    category: str,
    slot: str,
    local_slot: str,
) -> dict | None:
    if conn is None:
        return None
    for item_id in [slot, local_slot]:
        if not item_id:
            continue
        row = conn.execute(
            """
            SELECT mod_items.id, mod_items.zipmod_id, mod_items.zipmod_guid, mod_items.zipmod_author,
                   mod_items.item_id, mod_items.kind, mod_items.name, mod_items.thumbnail_cache_path,
                   mod_items.thumbnail_status, mod_items.parse_status,
                   zipmods.name AS zipmod_name, zipmods.file_name AS zipmod_file_name
            FROM mod_items
            INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
            WHERE zipmods.scan_status != 'stale'
              AND mod_items.zipmod_guid = ?
              AND mod_items.item_id = ?
            LIMIT 1
            """,
            (mod_id, item_id),
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
        WHERE scan_status != 'stale' AND guid = ?
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
