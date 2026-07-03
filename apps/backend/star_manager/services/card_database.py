from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

from star_manager.core.card_parser import (
    extract_auto_resolver_records_from_card,
    extract_character_profile_from_card,
    extract_png_extra_data,
    read_card_header,
    read_card_marker,
)
from star_manager.services.card_library import (
    DEFAULT_CARD_PREVIEW_DIR,
    IGNORED_ROOT_CARD_DIRS,
    get_card_root,
    normalize_card_preview,
    normalize_relative,
    validate_card_root,
)
from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    init_db,
    set_database_metadata,
    timestamp_to_utc,
    utc_now,
)


def build_card_database(
    game_dir: Path | str,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
    progress_callback: Callable[[int, str], None] | None = None,
    mode: str = "incremental",
) -> dict[str, int]:
    def report(value: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(value, message)

    is_valid, root, error = validate_card_root(str(game_dir))
    if not is_valid:
        raise ValueError(error or "Invalid character-card directory.")

    db_path = db_path.resolve()
    preview_dir = preview_dir.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    report(5, "Scanning UserData/chara/**/*.png")
    card_paths = list(iter_card_pngs(root))
    total = max(len(card_paths), 1)
    now = utc_now()
    seen_paths: set[str] = set()
    force_full = str(mode or "incremental").lower() == "full"
    stats = {
        "card_files": len(card_paths),
        "cards": 0,
        "parse_errors": 0,
        "dependencies": 0,
        "missing_dependencies": 0,
        "stale_cards": 0,
        "reused_cards": 0,
        "changed_cards": 0,
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        with conn:
            for index, card_path in enumerate(card_paths, start=1):
                prepared = prepare_card_record(card_path, root, preview_dir, conn, now, force_full)
                seen_paths.add(prepared["file_path"])
                card_id = upsert_character_card(conn, prepared)
                replace_card_dependencies(conn, card_id, prepared["dependencies"])
                stats["cards"] += 1
                if prepared["reused"]:
                    stats["reused_cards"] += 1
                else:
                    stats["changed_cards"] += 1
                if prepared["parse_status"] != "ok":
                    stats["parse_errors"] += 1
                stats["dependencies"] += int(prepared["dependency_count"])
                stats["missing_dependencies"] += int(prepared["missing_count"])
                if index == total or index % 25 == 0:
                    report(
                        5 + round(index / total * 90),
                        f"Indexed {index}/{total} character cards",
                    )

            stats["stale_cards"] = mark_stale_cards(conn, seen_paths, now)
            set_database_metadata(conn, "last_card_built_at", now)
        report(100, "Character card database rebuild completed")
        return stats
    finally:
        conn.close()


def iter_card_pngs(root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*.png"):
        if not path.is_file():
            continue
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        if relative.parts and relative.parts[0].casefold() in IGNORED_ROOT_CARD_DIRS:
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: normalize_relative(item, root).casefold())


def prepare_card_record(
    card_path: Path,
    root: Path,
    preview_dir: Path,
    conn: sqlite3.Connection,
    now: str,
    force_full: bool,
) -> dict:
    stat = card_path.stat()
    card_uid = ""
    chara_name = card_path.stem
    preview_cache_path = ""
    dependency_count = 0
    missing_count = 0
    parse_status = "ok"
    dependencies: list[dict[str, str | int | None]] = []
    modified_at = timestamp_to_utc(stat.st_mtime)
    cached = None if force_full else load_cached_card(conn, card_path, modified_at)
    if cached is not None:
        raw_dependencies = load_cached_card_dependencies(conn, int(cached["id"]))
        dependencies = resolve_cached_dependencies(conn, raw_dependencies)
        return {
            "file_path": str(card_path.resolve()),
            "relative_path": normalize_relative(card_path, root),
            "file_name": card_path.name,
            "card_uid": str(cached["card_uid"] or ""),
            "chara_name": str(cached["chara_name"] or card_path.stem),
            "preview_cache_path": str(cached["preview_cache_path"] or ""),
            "modified_at": modified_at,
            "parse_status": str(cached["parse_status"] or "ok"),
            "dependency_count": len(dependencies),
            "missing_count": sum(
                1 for item in dependencies if item["resolve_status"] != "resolved"
            ),
            "last_scanned_at": now,
            "dependencies": dependencies,
            "reused": True,
        }

    try:
        card_data = extract_png_extra_data(card_path)
        marker = read_card_marker(card_data)
        if not marker:
            parse_status = "not_ais"
        else:
            header = read_card_header(card_data)
            card_uid = str(header.get("card_id") or "")
            profile = extract_character_profile_from_card(str(card_path))
            chara_name = str(profile.get("fullname") or "").strip() or card_path.stem
            records = extract_auto_resolver_records_from_card(str(card_path))
            dependencies = resolve_dependency_records(conn, records)
            dependency_count = len(dependencies)
            missing_count = sum(
                1 for item in dependencies if item["resolve_status"] != "resolved"
            )
            preview = normalize_card_preview(card_path, preview_dir)
            preview_cache_path = str(preview) if preview != card_path else ""
    except Exception:
        parse_status = "parse_error"

    return {
        "file_path": str(card_path.resolve()),
        "relative_path": normalize_relative(card_path, root),
        "file_name": card_path.name,
        "card_uid": card_uid,
        "chara_name": chara_name,
        "preview_cache_path": preview_cache_path,
        "modified_at": modified_at,
        "parse_status": parse_status,
        "dependency_count": dependency_count,
        "missing_count": missing_count,
        "last_scanned_at": now,
        "dependencies": dependencies,
        "reused": False,
    }


def load_cached_card(
    conn: sqlite3.Connection,
    card_path: Path,
    modified_at: str,
) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM character_cards
        WHERE file_path = ?
          AND modified_at = ?
          AND parse_status != 'stale'
        LIMIT 1
        """,
        (str(card_path.resolve()), modified_at),
    ).fetchone()


def load_cached_card_dependencies(
    conn: sqlite3.Connection,
    card_id: int,
) -> list[dict[str, str]]:
    return [
        {
            "mod_id": str(row["mod_id"] or ""),
            "category_no": str(row["category_no"] or ""),
            "slot": str(row["slot"] or ""),
            "local_slot": str(row["local_slot"] or ""),
        }
        for row in conn.execute(
            """
            SELECT mod_id, category_no, slot, local_slot
            FROM character_card_dependencies
            WHERE card_id = ?
            """,
            (card_id,),
        )
    ]


def resolve_cached_dependencies(
    conn: sqlite3.Connection,
    dependencies: list[dict[str, str]],
) -> list[dict[str, str | int | None]]:
    resolved: list[dict[str, str | int | None]] = []
    for dependency in dependencies:
        mod_id = dependency["mod_id"]
        category_no = dependency["category_no"]
        slot = dependency["slot"]
        local_slot = dependency["local_slot"]
        zipmod_id = find_zipmod_id(conn, mod_id)
        mod_item_id = find_mod_item_id(conn, mod_id, category_no, slot, local_slot)
        if mod_item_id is not None:
            resolve_status = "resolved"
        elif zipmod_id is not None:
            resolve_status = "missing_item"
        else:
            resolve_status = "missing_zipmod"
        resolved.append(
            {
                "mod_id": mod_id,
                "category_no": category_no,
                "slot": slot,
                "local_slot": local_slot,
                "zipmod_id": zipmod_id,
                "mod_item_id": mod_item_id,
                "resolve_status": resolve_status,
            }
        )
    return resolved


def upsert_character_card(conn: sqlite3.Connection, record: dict) -> int:
    cursor = conn.execute(
        """
        INSERT INTO character_cards (
            file_path, relative_path, file_name, card_uid, chara_name,
            preview_cache_path, modified_at, parse_status, dependency_count,
            missing_count, last_scanned_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            relative_path = excluded.relative_path,
            file_name = excluded.file_name,
            card_uid = excluded.card_uid,
            chara_name = excluded.chara_name,
            preview_cache_path = excluded.preview_cache_path,
            modified_at = excluded.modified_at,
            parse_status = excluded.parse_status,
            dependency_count = excluded.dependency_count,
            missing_count = excluded.missing_count,
            last_scanned_at = excluded.last_scanned_at
        """,
        (
            record["file_path"],
            record["relative_path"],
            record["file_name"],
            record["card_uid"],
            record["chara_name"],
            record["preview_cache_path"],
            record["modified_at"],
            record["parse_status"],
            record["dependency_count"],
            record["missing_count"],
            record["last_scanned_at"],
        ),
    )
    row = conn.execute(
        "SELECT id FROM character_cards WHERE file_path = ?",
        (record["file_path"],),
    ).fetchone()
    if row:
        return int(row["id"])
    return int(cursor.lastrowid)


def resolve_dependency_records(
    conn: sqlite3.Connection,
    records: list[dict],
) -> list[dict[str, str | int | None]]:
    dependencies: list[dict[str, str | int | None]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for record in records:
        mod_id = record_value_to_str(record.get("ModID"))
        category_no = record_value_to_str(record.get("CategoryNo"))
        slot = record_value_to_str(record.get("Slot"))
        local_slot = record_value_to_str(record.get("LocalSlot"))
        if not mod_id:
            continue
        key = (mod_id, category_no, slot, local_slot)
        if key in seen:
            continue
        seen.add(key)

        zipmod_id = find_zipmod_id(conn, mod_id)
        mod_item_id = find_mod_item_id(conn, mod_id, category_no, slot, local_slot)
        if mod_item_id is not None:
            resolve_status = "resolved"
        elif zipmod_id is not None:
            resolve_status = "missing_item"
        else:
            resolve_status = "missing_zipmod"

        dependencies.append(
            {
                "mod_id": mod_id,
                "category_no": category_no,
                "slot": slot,
                "local_slot": local_slot,
                "zipmod_id": zipmod_id,
                "mod_item_id": mod_item_id,
                "resolve_status": resolve_status,
            }
        )
    return dependencies


def record_value_to_str(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def find_zipmod_id(conn: sqlite3.Connection, mod_id: str) -> int | None:
    row = conn.execute(
        """
        SELECT id
        FROM zipmods
        WHERE scan_status != 'stale' AND guid = ?
        LIMIT 1
        """,
        (mod_id,),
    ).fetchone()
    return int(row["id"]) if row else None


def find_mod_item_id(
    conn: sqlite3.Connection,
    mod_id: str,
    category_no: str,
    slot: str,
    local_slot: str,
) -> int | None:
    for item_id in [slot, local_slot]:
        if not item_id:
            continue
        row = conn.execute(
            """
            SELECT mod_items.id
            FROM mod_items
            INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
            WHERE zipmods.scan_status != 'stale'
              AND mod_items.zipmod_guid = ?
              AND mod_items.kind = ?
              AND mod_items.item_id = ?
            LIMIT 1
            """,
            (mod_id, category_no, item_id),
        ).fetchone()
        if row:
            return int(row["id"])

    for item_id in [slot, local_slot]:
        if not item_id:
            continue
        row = conn.execute(
            """
            SELECT mod_items.id
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
            return int(row["id"])
    return None


def replace_card_dependencies(
    conn: sqlite3.Connection,
    card_id: int,
    dependencies: list[dict[str, str | int | None]],
) -> None:
    conn.execute("DELETE FROM character_card_dependencies WHERE card_id = ?", (card_id,))
    for dependency in dependencies:
        conn.execute(
            """
            INSERT INTO character_card_dependencies (
                card_id, mod_id, category_no, slot, local_slot,
                zipmod_id, mod_item_id, resolve_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                dependency["mod_id"],
                dependency["category_no"],
                dependency["slot"],
                dependency["local_slot"],
                dependency["zipmod_id"],
                dependency["mod_item_id"],
                dependency["resolve_status"],
            ),
        )


def mark_stale_cards(conn: sqlite3.Connection, seen_paths: set[str], now: str) -> int:
    rows = conn.execute("SELECT file_path FROM character_cards").fetchall()
    stale_paths = [str(row["file_path"]) for row in rows if str(row["file_path"]) not in seen_paths]
    if not stale_paths:
        return 0
    for start in range(0, len(stale_paths), 900):
        batch = stale_paths[start : start + 900]
        placeholders = ",".join("?" for _ in batch)
        conn.execute(
            f"""
            UPDATE character_cards
            SET parse_status = 'stale',
                last_scanned_at = ?
            WHERE file_path IN ({placeholders})
            """,
            [now, *batch],
        )
    return len(stale_paths)


def card_database_status(db_path: Path = DEFAULT_DB_PATH) -> dict:
    resolved = db_path.resolve()
    exists = resolved.exists() and resolved.is_file()
    result = {
        "exists": exists,
        "database_path": str(resolved),
        "card_count": 0,
        "card_error_count": 0,
        "missing_dependency_count": 0,
        "last_card_built_at": "",
    }
    if not exists:
        return result

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        result["card_count"] = int(
            conn.execute(
                "SELECT COUNT(*) FROM character_cards WHERE parse_status != 'stale'"
            ).fetchone()[0]
        )
        result["card_error_count"] = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM character_cards
                WHERE parse_status != 'stale'
                  AND parse_status != 'ok'
                """
            ).fetchone()[0]
        )
        result["missing_dependency_count"] = int(
            conn.execute(
                """
                SELECT COALESCE(SUM(missing_count), 0)
                FROM character_cards
                WHERE parse_status != 'stale'
                """
            ).fetchone()[0]
        )
        row = conn.execute(
            "SELECT value FROM database_metadata WHERE key = 'last_card_built_at'"
        ).fetchone()
        result["last_card_built_at"] = str(row["value"]) if row else ""
    finally:
        conn.close()
    return result
