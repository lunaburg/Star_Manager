from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from star_manager.core.card_parser import (
    extract_auto_resolver_records_from_card,
    extract_character_profile_from_card,
    extract_png_extra_data,
    read_card_header,
    read_card_marker,
)
from star_manager.core.card_metadata import read_card_metadata
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
    get_database_metadata,
    set_database_metadata,
    timestamp_to_utc,
    utc_now,
)


CARD_DATABASE_MAX_WORKERS = 4
_CACHE_UNSET = object()


def choose_card_database_worker_count(card_count: int) -> int:
    """Choose a conservative worker count for filesystem/card parsing work."""
    if card_count <= 1:
        return 1
    return min(CARD_DATABASE_MAX_WORKERS, max(1, os.cpu_count() or 1))


def build_card_database(
    game_dir: Path | str,
    db_path: Path = DEFAULT_DB_PATH,
    preview_dir: Path = DEFAULT_CARD_PREVIEW_DIR,
    progress_callback: Callable[[int, str], None] | None = None,
    mode: str = "incremental",
    affected_mod_guids: Iterable[str] | None = None,
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
        "relinked_cards": 0,
        "untouched_cards": 0,
        "worker_count": choose_card_database_worker_count(len(card_paths)),
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        resolver = DependencyResolver.load(conn)
        cached_cards = load_cached_card_records(conn)
        cached_dependencies = load_cached_card_dependencies_by_card(conn)
        tag_cache_key = str(root.resolve())
        refresh_tag_cache = force_full or get_database_metadata(
            conn, "character_card_tags_cache_root"
        ) != tag_cache_key
        affected_card_ids = find_affected_card_ids(conn, affected_mod_guids)

        def prepare(card_path: Path) -> dict:
            cache_key = str(card_path.resolve())
            cached = cached_cards.get(cache_key)
            return prepare_card_record(
                card_path,
                root,
                preview_dir,
                None,
                now,
                force_full,
                resolver,
                affected_card_ids,
                refresh_tag_cache,
                cached_record=cached,
                cached_dependencies=(
                    cached_dependencies.get(int(cached["id"]), [])
                    if cached is not None
                    else []
                ),
            )

        prepared_by_path: dict[str, dict] = {}
        worker_count = int(stats["worker_count"])
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="character-card-db",
        ) as executor:
            future_to_path = {
                executor.submit(prepare, card_path): card_path for card_path in card_paths
            }
            for completed_count, future in enumerate(
                as_completed(future_to_path), start=1
            ):
                prepared = future.result()
                prepared_by_path[prepared["file_path"]] = prepared
                report(
                    5 + round(completed_count / total * 70),
                    f"Prepared {completed_count}/{len(card_paths)} character cards",
                )

        with conn:
            for index, card_path in enumerate(card_paths, start=1):
                prepared = prepared_by_path[str(card_path.resolve())]
                seen_paths.add(prepared["file_path"])
                card_id = upsert_character_card(conn, prepared)
                if prepared["replace_dependencies"]:
                    replace_card_dependencies(conn, card_id, prepared["dependencies"])
                    if prepared["reused"]:
                        stats["relinked_cards"] += 1
                elif prepared["reused"]:
                    stats["untouched_cards"] += 1
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
                        75 + round(index / total * 25),
                        f"Indexed {index}/{total} character cards",
                    )

            stats["stale_cards"] = mark_stale_cards(conn, seen_paths, now)
            set_database_metadata(conn, "last_card_built_at", now)
            set_database_metadata(conn, "character_card_tags_cache_root", tag_cache_key)
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
    resolver: "DependencyResolver | None" = None,
    affected_card_ids: set[int] | None = None,
    refresh_tag_cache: bool = False,
    cached_record: object = _CACHE_UNSET,
    cached_dependencies: object = _CACHE_UNSET,
) -> dict:
    stat = card_path.stat()
    card_uid = ""
    chara_name = card_path.stem
    tags_json = "[]"
    favorite = False
    rating = 0
    metadata_file_size = stat.st_size
    metadata_modified_ns = stat.st_mtime_ns
    preview_cache_path = ""
    dependency_count = 0
    missing_count = 0
    parse_status = "ok"
    dependencies: list[dict[str, str | int | None]] = []
    modified_at = timestamp_to_utc(stat.st_mtime)
    if force_full:
        cached = None
    elif cached_record is _CACHE_UNSET:
        cached = load_cached_card(conn, card_path, modified_at)
    else:
        cached = cached_record
    if cached is not None and (
        str(cached["modified_at"] or "") != modified_at
        or int(cached["metadata_file_size"] or 0) != stat.st_size
        or int(cached["metadata_modified_ns"] or 0) != stat.st_mtime_ns
    ):
        cached = None
    if cached is not None:
        if refresh_tag_cache:
            metadata = read_card_metadata(card_path)
            tags_json = json.dumps(metadata["tags"], ensure_ascii=False)
            favorite = bool(metadata["favorite"])
            rating = int(metadata["rating"])
        else:
            tags_json = str(cached["tags_json"] or "[]")
            favorite = bool(cached["favorite"])
            rating = int(cached["rating"] or 0)
            metadata_file_size = int(cached["metadata_file_size"] or 0)
            metadata_modified_ns = int(cached["metadata_modified_ns"] or 0)
        should_relink = affected_card_ids is None or int(cached["id"]) in affected_card_ids
        if should_relink:
            if cached_dependencies is _CACHE_UNSET:
                raw_dependencies = load_cached_card_dependencies(conn, int(cached["id"]))
            else:
                raw_dependencies = list(cached_dependencies or [])
            dependencies = resolve_cached_dependencies(None, raw_dependencies, resolver)
            dependency_count = len(dependencies)
            missing_count = sum(
                1 for item in dependencies if item["resolve_status"] != "resolved"
            )
        else:
            dependency_count = int(cached["dependency_count"] or 0)
            missing_count = int(cached["missing_count"] or 0)
        return {
            "file_path": str(card_path.resolve()),
            "relative_path": normalize_relative(card_path, root),
            "file_name": card_path.name,
            "card_uid": str(cached["card_uid"] or ""),
            "chara_name": str(cached["chara_name"] or card_path.stem),
            "tags_json": tags_json,
            "favorite": favorite,
            "rating": rating,
            "metadata_file_size": metadata_file_size,
            "metadata_modified_ns": metadata_modified_ns,
            "preview_cache_path": str(cached["preview_cache_path"] or ""),
            "modified_at": modified_at,
            "parse_status": str(cached["parse_status"] or "ok"),
            "dependency_count": dependency_count,
            "missing_count": missing_count,
            "last_scanned_at": now,
            "dependencies": dependencies,
            "reused": True,
            "replace_dependencies": should_relink,
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
            metadata = read_card_metadata(card_path)
            tags_json = json.dumps(metadata["tags"], ensure_ascii=False)
            favorite = bool(metadata["favorite"])
            rating = int(metadata["rating"])
            records = extract_auto_resolver_records_from_card(str(card_path))
            dependencies = resolve_dependency_records(None, records, resolver)
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
        "tags_json": tags_json,
        "favorite": favorite,
        "rating": rating,
        "metadata_file_size": metadata_file_size,
        "metadata_modified_ns": metadata_modified_ns,
        "preview_cache_path": preview_cache_path,
        "modified_at": modified_at,
        "parse_status": parse_status,
        "dependency_count": dependency_count,
        "missing_count": missing_count,
        "last_scanned_at": now,
        "dependencies": dependencies,
        "reused": False,
        "replace_dependencies": True,
    }


def normalize_dependency_guid(value: object) -> str:
    return str(value or "").strip().casefold()


def find_affected_card_ids(
    conn: sqlite3.Connection,
    affected_mod_guids: Iterable[str] | None,
) -> set[int] | None:
    if affected_mod_guids is None:
        return None
    affected = {
        normalized
        for value in affected_mod_guids
        if (normalized := normalize_dependency_guid(value))
    }
    if not affected:
        return set()
    return {
        int(row["card_id"])
        for row in conn.execute(
            "SELECT card_id, mod_id FROM character_card_dependencies"
        )
        if normalize_dependency_guid(row["mod_id"]) in affected
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


def load_cached_card_records(conn: sqlite3.Connection) -> dict[str, dict]:
    """Load reusable card rows once before worker threads start."""
    return {
        str(row["file_path"]): dict(row)
        for row in conn.execute(
            """
            SELECT *
            FROM character_cards
            WHERE parse_status != 'stale'
            """
        )
    }


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


def load_cached_card_dependencies_by_card(
    conn: sqlite3.Connection,
) -> dict[int, list[dict[str, str]]]:
    """Load dependency keys once so worker threads never touch SQLite."""
    dependencies_by_card: dict[int, list[dict[str, str]]] = {}
    for row in conn.execute(
        """
        SELECT ccd.card_id, ccd.mod_id, ccd.category_no, ccd.slot, ccd.local_slot
        FROM character_card_dependencies ccd
        INNER JOIN character_cards cc ON cc.id = ccd.card_id
        WHERE cc.parse_status != 'stale'
        ORDER BY ccd.id
        """
    ):
        dependencies_by_card.setdefault(int(row["card_id"]), []).append(
            {
                "mod_id": str(row["mod_id"] or ""),
                "category_no": str(row["category_no"] or ""),
                "slot": str(row["slot"] or ""),
                "local_slot": str(row["local_slot"] or ""),
            }
        )
    return dependencies_by_card


def normalized_item_keys(value: object) -> tuple[str, ...]:
    raw = str(value or "").strip()
    if not raw:
        return ()
    if raw.isdigit():
        numeric = str(int(raw))
        if numeric != raw:
            return raw, numeric
    return (raw,)


@dataclass(frozen=True)
class DependencyResolver:
    zipmod_ids: dict[str, int]
    items_by_kind: dict[tuple[str, str, str], int]
    items_by_id: dict[tuple[str, str], int]

    @classmethod
    def load(cls, conn: sqlite3.Connection) -> "DependencyResolver":
        zipmod_ids: dict[str, int] = {}
        for row in conn.execute(
            "SELECT id, guid FROM zipmods WHERE scan_status != 'stale' ORDER BY id"
        ):
            guid = normalize_dependency_guid(row["guid"])
            if guid:
                zipmod_ids.setdefault(guid, int(row["id"]))

        items_by_kind: dict[tuple[str, str, str], int] = {}
        items_by_id: dict[tuple[str, str], int] = {}
        for row in conn.execute(
            """
            SELECT mod_items.id, mod_items.zipmod_guid, mod_items.kind, mod_items.item_id
            FROM mod_items
            INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
            WHERE zipmods.scan_status != 'stale'
            ORDER BY mod_items.id
            """
        ):
            guid = normalize_dependency_guid(row["zipmod_guid"])
            kind = str(row["kind"] or "").strip()
            for item_key in normalized_item_keys(row["item_id"]):
                item_id = int(row["id"])
                items_by_kind.setdefault((guid, kind, item_key), item_id)
                items_by_id.setdefault((guid, item_key), item_id)
        return cls(zipmod_ids, items_by_kind, items_by_id)

    def resolve(
        self,
        mod_id: str,
        category_no: str,
        slot: str,
        local_slot: str,
    ) -> tuple[int | None, int | None, str]:
        guid = normalize_dependency_guid(mod_id)
        zipmod_id = self.zipmod_ids.get(guid)
        candidates = (slot, local_slot)
        mod_item_id = next(
            (
                self.items_by_kind[(guid, category_no, item_key)]
                for value in candidates
                for item_key in normalized_item_keys(value)
                if (guid, category_no, item_key) in self.items_by_kind
            ),
            None,
        )
        if mod_item_id is None:
            mod_item_id = next(
                (
                    self.items_by_id[(guid, item_key)]
                    for value in candidates
                    for item_key in normalized_item_keys(value)
                    if (guid, item_key) in self.items_by_id
                ),
                None,
            )
        if mod_item_id is not None:
            resolve_status = "resolved"
        elif zipmod_id is not None:
            resolve_status = "missing_item"
        else:
            resolve_status = "missing_zipmod"
        return zipmod_id, mod_item_id, resolve_status


def resolve_cached_dependencies(
    conn: sqlite3.Connection,
    dependencies: list[dict[str, str]],
    resolver: DependencyResolver | None = None,
) -> list[dict[str, str | int | None]]:
    resolver = resolver or DependencyResolver.load(conn)
    resolved: list[dict[str, str | int | None]] = []
    for dependency in dependencies:
        mod_id = dependency["mod_id"]
        category_no = dependency["category_no"]
        slot = dependency["slot"]
        local_slot = dependency["local_slot"]
        zipmod_id, mod_item_id, resolve_status = resolver.resolve(
            mod_id, category_no, slot, local_slot
        )
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
            tags_json, favorite, rating, metadata_file_size, metadata_modified_ns,
            preview_cache_path, modified_at, parse_status, dependency_count,
            missing_count, last_scanned_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            relative_path = excluded.relative_path,
            file_name = excluded.file_name,
            card_uid = excluded.card_uid,
            chara_name = excluded.chara_name,
            tags_json = excluded.tags_json,
            favorite = excluded.favorite,
            rating = excluded.rating,
            metadata_file_size = excluded.metadata_file_size,
            metadata_modified_ns = excluded.metadata_modified_ns,
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
            record["tags_json"],
            int(bool(record["favorite"])),
            int(record["rating"]),
            int(record["metadata_file_size"]),
            int(record["metadata_modified_ns"]),
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
    resolver: DependencyResolver | None = None,
) -> list[dict[str, str | int | None]]:
    resolver = resolver or DependencyResolver.load(conn)
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

        zipmod_id, mod_item_id, resolve_status = resolver.resolve(
            mod_id, category_no, slot, local_slot
        )

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
        WHERE scan_status != 'stale' AND trim(guid) = trim(?) COLLATE NOCASE
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
              AND trim(mod_items.zipmod_guid) = trim(?) COLLATE NOCASE
              AND mod_items.kind = ?
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
            (mod_id, category_no, item_id, item_id, item_id, item_id),
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
              AND trim(mod_items.zipmod_guid) = trim(?) COLLATE NOCASE
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
            (mod_id, item_id, item_id, item_id, item_id),
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
