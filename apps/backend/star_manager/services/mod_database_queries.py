from __future__ import annotations

import re
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote

from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    UNKNOWN_AUTHOR,
    get_database_metadata,
    init_db,
    utc_now,
)

MAP_SCENE_FILTER_KIND = "__map_filter__"
MAP_SCENE_KINDS = (
    "__map_scene__",
    "__game_map_scene__",
    "__game_studio_map_scene__",
)
BUILTIN_SOURCE_LABEL = "游戏本体"
# Keep the builtin browser aligned with the renderer's ITEM_KIND_LABELS table.
# Unknown game category numbers are indexed for card/resource matching, but do
# not belong in the user-facing original-item browser.
BUILTIN_VISIBLE_KINDS = (
    "8",
    "110", "111", "112", "121",
    "131", "132", "133",
    "140", "141", "144", "147",
    "210", "211", "212",
    "231", "232", "233",
    "240", "241", "242", "243", "244", "245", "246", "247",
    "300", "301", "302", "303",
    "313", "314", "315", "316", "317", "318", "319", "320",
    "322", "323",
    "334", "335", "348",
    "351", "352", "353", "354", "355", "356", "357", "358",
    "359", "360", "361", "362", "363",
    "500", "501",
)

_CURRENT_THUMBNAIL_CACHE_LOCK = threading.Lock()
_CURRENT_THUMBNAIL_CACHE_KEY = None
_CURRENT_THUMBNAIL_CACHE_ROWS = {}
_CURRENT_BUILTIN_THUMBNAIL_CACHE_KEY = None
_CURRENT_BUILTIN_THUMBNAIL_CACHE_ROWS = {}


def normalize_zip_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").lstrip("/")


def normalize_abdata_path(root: str, path: str) -> str:
    path = normalize_zip_path(path)
    if not path:
        return ""
    if path.lower().startswith("abdata/"):
        return path
    return f"abdata/{path}"


def is_unity3d_path(path: str) -> bool:
    return Path(str(path or "").lower()).suffix == ".unity3d"


def resolve_game_dir_from_zipmod(file_path: str, relative_path: str) -> Path:
    zipmod_path = Path(file_path).resolve()
    relative_parent = Path(str(relative_path or "")).parent
    mods_dir = zipmod_path.parent
    if str(relative_parent) not in {"", "."}:
        for _part in relative_parent.parts:
            mods_dir = mods_dir.parent
    return mods_dir.parent


def resolve_game_abdata_path(game_dir: Path, abdata_path: str) -> Path:
    normalized = normalize_zip_path(abdata_path)
    if normalized.lower().startswith("abdata/"):
        normalized = normalized[len("abdata/") :]
    return game_dir / "abdata" / normalized


def zipmod_unity3d_reference_paths(item: sqlite3.Row) -> list[str]:
    references: list[str] = []
    main_path = normalize_abdata_path(str(item["main_manifest"] or ""), str(item["main_ab"] or ""))
    if main_path and is_unity3d_path(main_path):
        references.append(main_path)
    tex_path = normalize_abdata_path("abdata", str(item["tex_ab"] or ""))
    if tex_path and is_unity3d_path(tex_path):
        references.append(tex_path)
    return list(dict.fromkeys(references))


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def resolve_thumbnail_cache_path(cache_path: str, thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR) -> Path | None:
    raw_path = str(cache_path or "").strip()
    if not raw_path:
        return None

    root = thumbnail_dir.resolve()
    resolved = Path(raw_path).resolve()
    if root in resolved.parents and resolved.is_file():
        return resolved

    # Older databases may contain absolute cache paths from a different runtime
    # directory.  The cache file name is a stable SHA1 key, so remap it into the
    # current runtime thumbnail tree before deciding the thumbnail is missing.
    if resolved.suffix.lower() == ".png":
        stem = resolved.stem
        candidates = []
        if len(stem) >= 4:
            candidates.append(root / stem[:2] / stem[2:4] / resolved.name)
        candidates.append(root / resolved.name)
        for candidate in candidates:
            candidate = candidate.resolve()
            if root in candidate.parents and candidate.is_file():
                return candidate

        if re.fullmatch(r"[0-9a-fA-F]{40}", stem) and resolved.is_file() and len(stem) >= 4:
            migrated = (root / stem[:2] / stem[2:4] / resolved.name).resolve()
            if root in migrated.parents:
                migrated.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(resolved, migrated)
                return migrated

    return None


def thumbnail_url_for_cache_path(cache_path: str, thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR) -> str:
    resolved = resolve_thumbnail_cache_path(cache_path, thumbnail_dir)
    if not resolved:
        return ""
    return f"/mods/thumbnails?path={quote(str(resolved))}"


def thumbnail_recovery_url_for_item(
    item_id: int,
    parse_status: str,
    thumbnail_status: str,
    kind: str,
    thumb_tex: str,
) -> str:
    """Return a lazy extraction endpoint for ready items whose cache is absent."""
    if str(parse_status or "") != "ok":
        return ""
    if str(thumbnail_status or "") not in {"ready", "ok"}:
        return ""
    if str(kind or "").strip() in MAP_SCENE_KINDS or not str(thumb_tex or "").strip():
        return ""
    return f"/mods/items/{int(item_id)}/thumbnail"


def _normalize_current_item_slot(value: object) -> str:
    """Normalize runtime resolver slots and CSV item IDs for one lookup."""

    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+", text):
        try:
            return str(int(text))
        except (TypeError, ValueError, OverflowError):
            pass
    return text.casefold()


def _current_item_thumbnail_candidates(item: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    category = _normalize_current_item_slot(item.get("categoryNo"))
    if not category:
        return []

    candidates: list[tuple[str, str, str]] = []
    resolver_records = item.get("resolverRecords")
    if not isinstance(resolver_records, list):
        return candidates

    for record in resolver_records:
        if not isinstance(record, Mapping):
            continue
        guid = str(record.get("guid") or "").strip().casefold()
        slot = _normalize_current_item_slot(record.get("slot"))
        if guid and slot:
            candidate = (guid, category, slot)
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def hydrate_current_game_state_thumbnails(
    current_state: Mapping[str, Any] | None,
    db_path: Path = DEFAULT_DB_PATH,
    game_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Attach library thumbnail URLs to current game items.

    Modded items use the original ``GUID + kind + item_id`` resolver key.
    Vanilla items use the selected game directory plus ``CategoryNo`` and
    ``localSlot`` to find their ``builtin_items`` thumbnail cache.
    """

    if not isinstance(current_state, Mapping):
        return {}

    group_names = ("hairs", "clothes", "faces", "bodies", "accessories")
    hydrated = dict(current_state)
    item_candidates: dict[tuple[str, int], list[tuple[str, str, str]]] = {}
    lookup_keys: set[tuple[str, str, str]] = set()
    builtin_item_candidates: dict[tuple[str, int], tuple[str, str]] = {}
    builtin_lookup_keys: set[tuple[str, str]] = set()

    for group_name in group_names:
        source_items = current_state.get(group_name)
        if not isinstance(source_items, list):
            continue

        hydrated_items: list[Any] = []
        for index, source_item in enumerate(source_items):
            if not isinstance(source_item, Mapping):
                hydrated_items.append(source_item)
                continue
            item = dict(source_item)
            item["thumbnailUrl"] = ""
            candidates = _current_item_thumbnail_candidates(item)
            item_candidates[(group_name, index)] = candidates
            lookup_keys.update(candidates)
            if not candidates:
                category = _normalize_current_item_slot(item.get("categoryNo"))
                local_slot = _normalize_current_item_slot(item.get("localSlot"))
                if category and local_slot and local_slot != "0":
                    builtin_candidate = (category, local_slot)
                    builtin_item_candidates[(group_name, index)] = builtin_candidate
                    builtin_lookup_keys.add(builtin_candidate)
            hydrated_items.append(item)
        hydrated[group_name] = hydrated_items

    game_dir_key = ""
    if game_dir is not None and str(game_dir).strip():
        game_dir_key = str(Path(game_dir).resolve()).casefold()

    if not lookup_keys and not (game_dir_key and builtin_lookup_keys):
        return hydrated

    resolved = Path(db_path).resolve()
    if not resolved.exists() or not resolved.is_file():
        return hydrated

    try:
        database_version = resolved.stat().st_mtime_ns
    except OSError:
        return hydrated
    cache_key = (str(resolved), database_version, tuple(sorted(lookup_keys)))
    builtin_cache_key = (
        str(resolved),
        database_version,
        game_dir_key,
        tuple(sorted(builtin_lookup_keys)),
    )

    global _CURRENT_THUMBNAIL_CACHE_KEY, _CURRENT_THUMBNAIL_CACHE_ROWS
    global _CURRENT_BUILTIN_THUMBNAIL_CACHE_KEY, _CURRENT_BUILTIN_THUMBNAIL_CACHE_ROWS
    with _CURRENT_THUMBNAIL_CACHE_LOCK:
        if cache_key == _CURRENT_THUMBNAIL_CACHE_KEY:
            rows_by_key = {
                key: list(rows)
                for key, rows in _CURRENT_THUMBNAIL_CACHE_ROWS.items()
            }
        else:
            rows_by_key = None
        if builtin_cache_key == _CURRENT_BUILTIN_THUMBNAIL_CACHE_KEY:
            builtin_rows_by_key = {
                key: list(rows)
                for key, rows in _CURRENT_BUILTIN_THUMBNAIL_CACHE_ROWS.items()
            }
        else:
            builtin_rows_by_key = None

    if rows_by_key is None or builtin_rows_by_key is None:
        rows_by_key = rows_by_key or {}
        builtin_rows_by_key = builtin_rows_by_key or {}
        conn = sqlite3.connect(resolved)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            if rows_by_key == {} and lookup_keys:
                clauses: list[str] = []
                params: list[str] = []
                for guid, category, slot in sorted(lookup_keys):
                    clauses.append(
                        """
                        (
                            LOWER(TRIM(mod_items.zipmod_guid)) = ?
                            AND TRIM(mod_items.kind) = ?
                            AND (
                                TRIM(mod_items.item_id) = ?
                                OR (
                                    TRIM(mod_items.item_id) != ''
                                    AND TRIM(mod_items.item_id) NOT GLOB '*[^0-9]*'
                                    AND CAST(TRIM(mod_items.item_id) AS INTEGER) = ?
                                )
                            )
                        )
                        """
                    )
                    params.extend([guid, category, slot, slot])

                rows = conn.execute(
                    f"""
                    SELECT mod_items.id, mod_items.zipmod_guid, mod_items.kind, mod_items.item_id,
                           mod_items.parse_status, mod_items.thumbnail_status,
                           mod_items.thumbnail_cache_path, mod_items.thumb_tex
                    FROM mod_items
                    INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                    WHERE zipmods.scan_status != 'stale'
                      AND ({' OR '.join(clauses)})
                    """,
                    params,
                ).fetchall()
                for row in rows:
                    key = (
                        str(row["zipmod_guid"] or "").strip().casefold(),
                        _normalize_current_item_slot(row["kind"]),
                        _normalize_current_item_slot(row["item_id"]),
                    )
                    rows_by_key.setdefault(key, []).append(
                        {
                            "id": int(row["id"]),
                            "thumbnail_url": (
                                thumbnail_url_for_cache_path(row["thumbnail_cache_path"])
                                or thumbnail_recovery_url_for_item(
                                    row["id"],
                                    row["parse_status"],
                                    row["thumbnail_status"],
                                    row["kind"],
                                    row["thumb_tex"],
                                )
                            ),
                        }
                    )

            if game_dir_key and builtin_lookup_keys:
                clauses = []
                params = [game_dir_key]
                for category, item_id in sorted(builtin_lookup_keys):
                    clauses.append(
                        """
                        (
                            TRIM(builtin_items.category_no) = ?
                            AND (
                                TRIM(builtin_items.item_id) = ?
                                OR (
                                    TRIM(builtin_items.item_id) != ''
                                    AND TRIM(builtin_items.item_id) NOT GLOB '*[^0-9]*'
                                    AND CAST(TRIM(builtin_items.item_id) AS INTEGER) = ?
                                )
                            )
                        )
                        """
                    )
                    params.extend([category, item_id, item_id])

                rows = conn.execute(
                    f"""
                    SELECT builtin_items.category_no, builtin_items.item_id,
                           builtin_items.thumbnail_cache_path
                    FROM builtin_items
                    WHERE builtin_items.game_dir_key = ?
                      AND ({' OR '.join(clauses)})
                    """,
                    params,
                ).fetchall()
                for row in rows:
                    key = (
                        _normalize_current_item_slot(row["category_no"]),
                        _normalize_current_item_slot(row["item_id"]),
                    )
                    builtin_rows_by_key.setdefault(key, []).append(
                        {
                            "thumbnail_url": thumbnail_url_for_cache_path(
                                row["thumbnail_cache_path"]
                            ),
                        }
                    )
        except sqlite3.Error:
            return hydrated
        finally:
            conn.close()

        with _CURRENT_THUMBNAIL_CACHE_LOCK:
            _CURRENT_THUMBNAIL_CACHE_KEY = cache_key
            _CURRENT_THUMBNAIL_CACHE_ROWS = {
                key: tuple(rows)
                for key, rows in rows_by_key.items()
            }
            _CURRENT_BUILTIN_THUMBNAIL_CACHE_KEY = builtin_cache_key
            _CURRENT_BUILTIN_THUMBNAIL_CACHE_ROWS = {
                key: tuple(rows)
                for key, rows in builtin_rows_by_key.items()
            }

    for group_name in group_names:
        items = hydrated.get(group_name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            candidates = item_candidates.get((group_name, index), [])
            if not isinstance(item, dict):
                continue

            if candidates:
                matched_rows: dict[int, dict[str, Any]] = {}
                for candidate in candidates:
                    for row in rows_by_key.get(candidate, []):
                        matched_rows[int(row["id"])] = row
                if len(matched_rows) != 1:
                    continue

                row = next(iter(matched_rows.values()))
                item["thumbnailUrl"] = str(row.get("thumbnail_url") or "")
                continue

            builtin_key = builtin_item_candidates.get((group_name, index))
            if not builtin_key:
                continue
            builtin_rows = builtin_rows_by_key.get(builtin_key, [])
            if len(builtin_rows) == 1:
                item["thumbnailUrl"] = str(
                    builtin_rows[0].get("thumbnail_url") or ""
                )

    return hydrated


def database_status(
    db_path: Path = DEFAULT_DB_PATH,
    game_dir: Path | str | None = None,
) -> dict:
    resolved = db_path.resolve()
    exists = resolved.exists() and resolved.is_file()
    result = {
        "exists": exists,
        "database_path": str(resolved),
        "zipmod_count": 0,
        "item_count": 0,
        "zipmod_error_count": 0,
        "zipmod_warning_count": 0,
        "duplicate_guid_count": 0,
        "builtin_item_count": 0,
        "card_count": 0,
        "card_error_count": 0,
        "card_missing_dependency_count": 0,
        "last_card_built_at": "",
        "last_built_at": "",
    }
    if not exists:
        return result

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        result["zipmod_count"] = int(
            conn.execute("SELECT COUNT(*) FROM zipmods WHERE scan_status != 'stale'").fetchone()[0]
        )
        result["item_count"] = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE zipmods.scan_status != 'stale'
                """
            ).fetchone()[0]
        )
        if game_dir:
            game_dir_key = str(Path(game_dir).resolve()).casefold()
            try:
                result["builtin_item_count"] = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM builtin_items WHERE game_dir_key = ?",
                        (game_dir_key,),
                    ).fetchone()[0]
                )
            except sqlite3.OperationalError:
                # Older databases are upgraded lazily by the next rebuild.
                result["builtin_item_count"] = 0
        result["zipmod_error_count"] = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM zipmods
                WHERE scan_status != 'stale'
                  AND (
                      scan_status IN ('missing_manifest', 'invalid', 'invalid_manifest', 'read_error')
                      OR COALESCE(unity3d_status, '') IN ('missing', 'error')
                      OR COALESCE(unity3d_missing_count, 0) > 0
                  )
                """
            ).fetchone()[0]
        )
        result["zipmod_warning_count"] = int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM zipmods
                WHERE scan_status != 'stale'
                  AND NOT (
                      scan_status IN ('missing_manifest', 'invalid', 'invalid_manifest', 'read_error')
                      OR COALESCE(unity3d_status, '') IN ('missing', 'error')
                      OR COALESCE(unity3d_missing_count, 0) > 0
                  )
                  AND (
                      TRIM(COALESCE(author, '')) = ''
                      OR COALESCE(unity3d_status, '') IN ('in_game', 'not_in_mod')
                      OR COALESCE(unity3d_not_in_mod_count, 0) > 0
                      OR COALESCE(unity3d_in_game_count, 0) > 0
                      OR COALESCE(unity3d_other_mod_count, 0) > 0
                      OR EXISTS (
                          SELECT 1
                          FROM duplicate_zipmods d
                          WHERE d.guid = zipmods.guid
                      )
                      OR EXISTS (
                          SELECT 1
                          FROM mod_items mi
                          WHERE mi.zipmod_id = zipmods.id
                            AND mi.parse_status = 'ok'
                            AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                            AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                      )
                  )
                """
            ).fetchone()[0]
        )
        result["duplicate_guid_count"] = int(
            conn.execute(
                """
                SELECT COUNT(DISTINCT d.guid)
                FROM duplicate_zipmods d
                INNER JOIN zipmods z ON z.guid = d.guid
                WHERE z.scan_status != 'stale'
                """
            ).fetchone()[0]
        )
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
        result["card_missing_dependency_count"] = int(
            conn.execute(
                """
                SELECT COALESCE(SUM(missing_count), 0)
                FROM character_cards
                WHERE parse_status != 'stale'
                """
            ).fetchone()[0]
        )
        result["last_built_at"] = get_database_metadata(conn, "last_built_at")
        result["last_card_built_at"] = get_database_metadata(conn, "last_card_built_at")
        if not result["last_built_at"]:
            result["last_built_at"] = str(
                conn.execute(
                    """
                    SELECT COALESCE(MAX(last_scanned_at), '')
                    FROM zipmods
                    WHERE scan_status != 'stale' AND last_scanned_at != ''
                    """
                ).fetchone()[0]
            )
    finally:
        conn.close()
    return result


def find_zipmod_paths_by_guid(
    required_guids: Iterable[str],
    mods_dir: Path | str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[set[str], set[str]]:
    guids = {str(guid) for guid in required_guids if str(guid)}
    if not guids:
        return set(), set()

    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return set(), guids

    resolved_mods_dir = Path(mods_dir).resolve() if mods_dir else None
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        matched_paths: set[str] = set()
        matched_guids: set[str] = set()
        ordered_guids = sorted(guids)
        batch_size = 900

        for start in range(0, len(ordered_guids), batch_size):
            batch = ordered_guids[start : start + batch_size]
            placeholders = ",".join("?" for _ in batch)
            rows = conn.execute(
                f"""
                SELECT guid, file_path
                FROM zipmods
                WHERE scan_status != 'stale'
                  AND guid IN ({placeholders})
                """,
                batch,
            ).fetchall()
            for row in rows:
                zipmod_path = Path(str(row["file_path"])).resolve()
                if not zipmod_path.is_file():
                    continue
                if resolved_mods_dir and resolved_mods_dir not in zipmod_path.parents:
                    continue
                matched_paths.add(str(zipmod_path))
                matched_guids.add(str(row["guid"]))

        return matched_paths, guids - matched_guids
    finally:
        conn.close()


def list_zipmod_authors(db_path: Path = DEFAULT_DB_PATH) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found", "authors": []}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        authors = [
            row["author"]
            for row in conn.execute(
                """
                SELECT DISTINCT TRIM(author) AS author
                FROM zipmods
                WHERE scan_status != 'stale'
                  AND TRIM(author) != ''
                ORDER BY author COLLATE NOCASE
                """
            )
            if row["author"]
        ]
        return {"ok": True, "authors": authors}
    finally:
        conn.close()


def list_mod_item_filters(
    db_path: Path = DEFAULT_DB_PATH,
    game_dir: Path | str | None = None,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found", "authors": [], "kinds": []}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        game_dir_key = str(Path(game_dir).resolve()).casefold() if game_dir else ""
        authors = [
            row["author"]
            for row in conn.execute(
                """
                SELECT DISTINCT TRIM(zipmod_author) AS author
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE zipmods.scan_status != 'stale'
                  AND TRIM(zipmod_author) != ''
                ORDER BY author COLLATE NOCASE
                """
            )
            if row["author"]
        ]
        builtin_scope = "game_dir_key = ? AND " if game_dir_key else ""
        builtin_scope_params = (game_dir_key,) if game_dir_key else ()
        builtin_kind_placeholders = ", ".join("?" for _ in BUILTIN_VISIBLE_KINDS)
        builtin_kind_scope = (
            builtin_scope
            + f"TRIM(category_no) IN ({builtin_kind_placeholders})"
        )
        builtin_kind_params = [*builtin_scope_params, *BUILTIN_VISIBLE_KINDS]
        if conn.execute(
            f"SELECT 1 FROM builtin_items WHERE {builtin_kind_scope} LIMIT 1",
            builtin_kind_params,
        ).fetchone():
            authors.append(BUILTIN_SOURCE_LABEL)
        authors = sorted(set(authors), key=str.casefold)
        kinds = [
            row["kind"]
            for row in conn.execute(
                f"""
                SELECT DISTINCT kind
                FROM (
                    SELECT TRIM(mod_items.kind) AS kind
                    FROM mod_items
                    INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                    WHERE zipmods.scan_status != 'stale'
                      AND TRIM(mod_items.kind) != ''
                    UNION ALL
                    SELECT TRIM(category_no) AS kind
                    FROM builtin_items
                    WHERE {builtin_kind_scope}
                )
                ORDER BY CAST(kind AS INTEGER), kind COLLATE NOCASE
                """,
                builtin_kind_params,
            )
            if row["kind"]
        ]
        return {"ok": True, "authors": authors, "kinds": kinds}
    finally:
        conn.close()


def list_zipmods(
    db_path: Path = DEFAULT_DB_PATH,
    offset: int = 0,
    limit: int = 200,
    author: str = "",
    status: str = "",
    usage: str = "",
    guid: str = "",
    zipmod_id: int = 0,
) -> dict:
    resolved = db_path.resolve()
    offset = max(0, int(offset))
    limit = min(500, max(1, int(limit)))
    author = str(author or "").strip()
    status = str(status or "").strip()
    usage = str(usage or "").strip()
    guid = str(guid or "").strip()
    zipmod_id = max(0, int(zipmod_id or 0))
    if not resolved.exists() or not resolved.is_file():
        return {
            "exists": False,
            "database_path": str(resolved),
            "rows": [],
            "offset": offset,
            "limit": limit,
            "total": 0,
            "has_more": False,
            "filters": {"author": author, "status": status, "usage": usage, "guid": guid, "zipmod_id": zipmod_id},
        }

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        where_sql = ""
        params: list[object] = []
        where_clauses: list[str] = ["scan_status != 'stale'"]
        if zipmod_id:
            where_clauses.append("id = ?")
            params.append(zipmod_id)
        if guid:
            where_clauses.append("guid COLLATE NOCASE = ?")
            params.append(guid)
        if author:
            if author == UNKNOWN_AUTHOR:
                where_clauses.append("TRIM(COALESCE(author, '')) = ''")
            else:
                where_clauses.append("TRIM(author) LIKE ? ESCAPE '\\' COLLATE NOCASE")
                params.append(f"%{escape_like(author)}%")
        if status == "normal":
            where_clauses.append(
                """
                scan_status = 'ok'
                AND TRIM(COALESCE(author, '')) != ''
                AND COALESCE(unity3d_status, '') NOT IN ('missing', 'error')
                AND COALESCE(unity3d_status, '') NOT IN ('in_game', 'not_in_mod')
                AND COALESCE(unity3d_not_in_mod_count, 0) = 0
                AND COALESCE(unity3d_in_game_count, 0) = 0
                AND COALESCE(unity3d_other_mod_count, 0) = 0
                AND NOT EXISTS (
                    SELECT 1
                    FROM duplicate_zipmods d
                    WHERE d.guid = zipmods.guid
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM mod_items mi
                    WHERE mi.zipmod_id = zipmods.id
                      AND mi.parse_status = 'ok'
                      AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                      AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                )
                """
            )
        elif status == "abnormal":
            where_clauses.append(
                """
                (
                    scan_status != 'ok'
                    OR TRIM(COALESCE(author, '')) = ''
                    OR COALESCE(unity3d_status, '') IN ('missing', 'error')
                    OR COALESCE(unity3d_status, '') IN ('in_game', 'not_in_mod')
                    OR COALESCE(unity3d_not_in_mod_count, 0) > 0
                    OR COALESCE(unity3d_in_game_count, 0) > 0
                    OR COALESCE(unity3d_other_mod_count, 0) > 0
                    OR EXISTS (
                        SELECT 1
                        FROM duplicate_zipmods d
                        WHERE d.guid = zipmods.guid
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM mod_items mi
                        WHERE mi.zipmod_id = zipmods.id
                          AND mi.parse_status = 'ok'
                          AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                          AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                    )
                )
                """
            )
        elif status == "warning":
            where_clauses.append(
                """
                (
                    TRIM(COALESCE(author, '')) = ''
                    OR COALESCE(unity3d_status, '') IN ('in_game', 'not_in_mod')
                    OR COALESCE(unity3d_not_in_mod_count, 0) > 0
                    OR COALESCE(unity3d_in_game_count, 0) > 0
                    OR COALESCE(unity3d_other_mod_count, 0) > 0
                    OR EXISTS (
                        SELECT 1
                        FROM duplicate_zipmods d
                        WHERE d.guid = zipmods.guid
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM mod_items mi
                        WHERE mi.zipmod_id = zipmods.id
                          AND mi.parse_status = 'ok'
                          AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                          AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                    )
                )
                """
            )
        elif status == "error":
            where_clauses.append(
                """
                (
                    scan_status IN ('missing_manifest', 'invalid_manifest', 'read_error')
                    OR COALESCE(unity3d_status, '') = 'missing'
                    OR COALESCE(unity3d_status, '') = 'error'
                    OR COALESCE(unity3d_missing_count, 0) > 0
                )
                """
            )
        elif status == "manifest_author":
            where_clauses.append("TRIM(COALESCE(author, '')) = ''")
        elif status == "missing_manifest":
            where_clauses.append("scan_status IN ('missing_manifest', 'invalid_manifest', 'read_error')")
        elif status == "read_error":
            where_clauses.append("scan_status IN ('missing_manifest', 'invalid_manifest', 'read_error')")
        elif status == "unity3d_missing":
            where_clauses.append(
                "COALESCE(unity3d_status, '') = 'missing' OR COALESCE(unity3d_missing_count, 0) > 0"
            )
        elif status == "unity3d_in_game":
            where_clauses.append(
                "COALESCE(unity3d_status, '') = 'in_game' OR COALESCE(unity3d_in_game_count, 0) > 0"
            )
        elif status == "unity3d_not_in_mod":
            where_clauses.append(
                """
                COALESCE(unity3d_status, '') IN ('in_game', 'not_in_mod')
                OR COALESCE(unity3d_not_in_mod_count, 0) > 0
                OR COALESCE(unity3d_in_game_count, 0) > 0
                OR COALESCE(unity3d_other_mod_count, 0) > 0
                """
            )
        elif status == "unity3d_error":
            where_clauses.append("COALESCE(unity3d_status, '') = 'error'")
        elif status == "duplicate_zipmod":
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM duplicate_zipmods d
                    WHERE d.guid = zipmods.guid
                )
                """
            )
        elif status == "thumbnail":
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM mod_items mi
                    WHERE mi.zipmod_id = zipmods.id
                      AND mi.parse_status = 'ok'
                      AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                      AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                )
                """
            )
        if usage == "used":
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM character_card_dependencies ccd
                    INNER JOIN character_cards cc ON cc.id = ccd.card_id
                    WHERE cc.parse_status != 'stale'
                      AND ccd.zipmod_id = zipmods.id
                )
                """
            )
        elif usage == "unused":
            where_clauses.append(
                """
                NOT EXISTS (
                    SELECT 1
                    FROM character_card_dependencies ccd
                    INNER JOIN character_cards cc ON cc.id = ccd.card_id
                    WHERE cc.parse_status != 'stale'
                      AND ccd.zipmod_id = zipmods.id
                )
                """
            )
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(f"({clause})" for clause in where_clauses)

        total = int(conn.execute(f"SELECT COUNT(*) FROM zipmods {where_sql}", params).fetchone()[0])
        rows = [
            {
                "id": row["id"],
                "status": row["scan_status"],
                "name": row["name"] or row["file_name"],
                "author": row["author"] or UNKNOWN_AUTHOR,
                "version": row["version"],
                "item_count": row["item_count"],
                "duplicate_zipmod_count": row["duplicate_zipmod_count"],
                "thumbnail_issue_count": row["thumbnail_issue_count"],
                "unity3d_status": row["unity3d_status"],
                "unity3d_not_in_mod_count": row["unity3d_not_in_mod_count"],
                "unity3d_in_mod_count": row["unity3d_in_mod_count"],
                "unity3d_in_game_count": row["unity3d_in_game_count"],
                "unity3d_other_mod_count": row["unity3d_other_mod_count"],
                "unity3d_missing_count": row["unity3d_missing_count"],
                "unity3d_error": row["unity3d_error"],
                "guid": row["guid"],
                "file_name": row["file_name"],
                "relative_path": row["relative_path"],
                "file_path": row["file_path"],
                "last_scanned_at": row["last_scanned_at"],
                "scan_error": row["scan_error"],
            }
            for row in conn.execute(
                f"""
                SELECT id, scan_status, name, author, version, item_count,
                       unity3d_status, unity3d_not_in_mod_count, unity3d_in_mod_count,
                       unity3d_in_game_count, unity3d_other_mod_count,
                       unity3d_missing_count, unity3d_error, guid,
                       file_name, relative_path, file_path, last_scanned_at, scan_error
                       , (
                           SELECT COUNT(*)
                           FROM duplicate_zipmods d
                           WHERE d.guid = zipmods.guid
                       ) AS duplicate_zipmod_count
                       , (
                           SELECT COUNT(*)
                           FROM mod_items mi
                             WHERE mi.zipmod_id = zipmods.id
                               AND mi.parse_status = 'ok'
                               AND TRIM(COALESCE(mi.kind, '')) NOT IN ('500', '501')
                               AND (mi.thumbnail_status = '' OR mi.thumbnail_status NOT IN ('ready', 'ok'))
                       ) AS thumbnail_issue_count
                FROM zipmods
                {where_sql}
                ORDER BY guid COLLATE NOCASE
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
        ]
        return {
            "exists": True,
            "database_path": str(resolved),
            "rows": rows,
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + len(rows) < total,
            "filters": {"author": author, "status": status, "usage": usage, "zipmod_id": zipmod_id},
        }
    finally:
        conn.close()


def export_zipmods(
    zipmod_ids: Iterable[int],
    target_dir: str,
    mode: str = "copy",
    layout: str = "tree",
    db_path: Path = DEFAULT_DB_PATH,
    progress_callback=None,
) -> dict:
    ids_set: set[int] = set()
    for zipmod_id in zipmod_ids:
        try:
            parsed_id = int(zipmod_id)
        except (TypeError, ValueError):
            continue
        if parsed_id > 0:
            ids_set.add(parsed_id)
    ids = sorted(ids_set)
    if not ids:
        return {"ok": False, "error": "No zipmods selected"}

    export_mode = str(mode or "copy").lower()
    if export_mode not in {"copy", "move"}:
        return {"ok": False, "error": "Invalid export mode"}

    export_layout = str(layout or "tree").lower()
    if export_layout not in {"tree", "by_author", "portable"}:
        return {"ok": False, "error": "Invalid export layout"}

    target_root = Path(target_dir).expanduser().resolve()
    if not str(target_dir or "").strip():
        return {"ok": False, "error": "No target directory selected"}
    target_root.mkdir(parents=True, exist_ok=True)
    if not target_root.is_dir():
        return {"ok": False, "error": "Target directory is not a directory"}

    resolved = db_path.resolve()
    if not resolved.exists():
        return {"ok": False, "error": "Mod database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    exported: list[dict] = []
    exported_unity3d: list[dict] = []
    failures: list[dict] = []
    try:
        init_db(conn)
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT id, file_path, relative_path, file_name, author
            FROM zipmods
            WHERE id IN ({placeholders}) AND scan_status != 'stale'
            """,
            ids,
        ).fetchall()
        rows_by_id = {int(row["id"]): row for row in rows}

        total = max(len(ids), 1)
        for index, zipmod_id in enumerate(ids, start=1):
            row = rows_by_id.get(zipmod_id)
            if row is None:
                failures.append({"id": zipmod_id, "error": "Zipmod not found in database"})
                if progress_callback is not None:
                    progress_callback(index, total, zipmod_id)
                continue

            source = Path(str(row["file_path"])).resolve()
            if not source.is_file():
                failures.append({"id": zipmod_id, "error": "Source zipmod file not found"})
                if progress_callback is not None:
                    progress_callback(index, total, zipmod_id)
                continue

            if export_layout == "by_author":
                author_dir = re.sub(r'[<>:"/\\|?*]', "_", str(row["author"] or "Unknown author")).strip()
                relative = Path(author_dir or "Unknown author") / str(row["file_name"] or source.name)
            else:
                relative = Path(str(row["relative_path"] or row["file_name"] or source.name))
                if relative.is_absolute() or ".." in relative.parts:
                    relative = Path(source.name)

            zipmod_root = target_root / "mods" if export_layout == "portable" else target_root
            target = (zipmod_root / relative).resolve()
            if target != target_root and target_root not in target.parents:
                failures.append({"id": zipmod_id, "error": "Unsafe target path"})
                if progress_callback is not None:
                    progress_callback(index, total, zipmod_id)
                continue

            if export_layout == "by_author":
                candidate = target
                counter = 1
                while candidate.exists():
                    candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
                    counter += 1
                target = candidate

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if export_mode == "move":
                    shutil.move(str(source), str(target))
                else:
                    shutil.copy2(source, target)
                exported.append({"id": zipmod_id, "source": str(source), "target": str(target)})
            except OSError as exc:
                failures.append({"id": zipmod_id, "error": str(exc)})
            finally:
                if progress_callback is not None:
                    progress_callback(index, total, zipmod_id)

        if exported:
            exported_ids = [item["id"] for item in exported]
            item_placeholders = ",".join("?" for _ in exported_ids)
            unity_rows = conn.execute(
                f"""
                SELECT zipmods.id AS zipmod_id, zipmods.file_path, zipmods.relative_path,
                       mod_items.main_manifest, mod_items.main_ab, mod_items.tex_ab, mod_items.thumb_ab
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE mod_items.zipmod_id IN ({item_placeholders})
                  AND mod_items.unity3d_status IN ('in_game', 'not_in_mod')
                """,
                exported_ids,
            ).fetchall()
            seen_unity_paths: set[str] = set()
            for unity_row in unity_rows:
                game_dir = resolve_game_dir_from_zipmod(
                    str(unity_row["file_path"] or ""),
                    str(unity_row["relative_path"] or ""),
                )
                for reference in zipmod_unity3d_reference_paths(unity_row):
                    key = normalize_zip_path(reference).lower()
                    if key in seen_unity_paths:
                        continue
                    seen_unity_paths.add(key)

                    source = resolve_game_abdata_path(game_dir, reference)
                    if not source.is_file():
                        failures.append(
                            {
                                "id": int(unity_row["zipmod_id"]),
                                "error": f"Unity3D source file not found: {reference}",
                            }
                        )
                        continue

                    target = (target_root / normalize_zip_path(reference)).resolve()
                    if target != target_root and target_root not in target.parents:
                        failures.append(
                            {
                                "id": int(unity_row["zipmod_id"]),
                                "error": f"Unsafe Unity3D target path: {reference}",
                            }
                        )
                        continue

                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if export_mode == "move":
                            shutil.move(str(source), str(target))
                        else:
                            shutil.copy2(source, target)
                        exported_unity3d.append(
                            {
                                "zipmod_id": int(unity_row["zipmod_id"]),
                                "path": normalize_zip_path(reference),
                                "source": str(source),
                                "target": str(target),
                            }
                        )
                    except OSError as exc:
                        failures.append(
                            {
                                "id": int(unity_row["zipmod_id"]),
                                "error": f"Unity3D export failed for {reference}: {exc}",
                            }
                        )

        if export_mode == "move" and exported:
            moved_ids = [item["id"] for item in exported]
            moved_placeholders = ",".join("?" for _ in moved_ids)
            conn.execute(
                f"""
                UPDATE zipmods
                SET scan_status = 'stale',
                    scan_error = 'moved by export',
                    updated_at = ?
                WHERE id IN ({moved_placeholders})
                """,
                [utc_now(), *moved_ids],
            )
            conn.commit()

        return {
            "ok": len(exported) > 0 or len(failures) == 0,
            "mode": export_mode,
            "layout": export_layout,
            "target_dir": str(target_root),
            "exported_count": len(exported),
            "exported_unity3d_count": len(exported_unity3d),
            "failure_count": len(failures),
            "exported": exported,
            "exported_unity3d": exported_unity3d,
            "failures": failures,
            "message": (
                f"{export_mode} exported {len(exported)} zipmod(s) "
                f"and {len(exported_unity3d)} external unity3d file(s)"
            ),
        }
    finally:
        conn.close()


def _normalized_usage_item_keys(value: object) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    keys = [raw]
    if raw.isdigit():
        normalized = raw.lstrip("0") or "0"
        if normalized not in keys:
            keys.append(normalized)
    return keys


def _orphaned_usage_item_ids(conn: sqlite3.Connection) -> set[int]:
    """Resolve legacy dependencies whose item FK was cleared during reindexing."""
    items_by_kind: dict[tuple[int, str, str], int] = {}
    items_by_id: dict[tuple[int, str], int] = {}
    for row in conn.execute(
        """
        SELECT mod_items.id, mod_items.zipmod_id, mod_items.kind, mod_items.item_id
        FROM mod_items
        INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
        WHERE zipmods.scan_status != 'stale'
        ORDER BY mod_items.id
        """
    ):
        zipmod_id = int(row["zipmod_id"])
        kind = str(row["kind"] or "").strip()
        item_db_id = int(row["id"])
        for item_key in _normalized_usage_item_keys(row["item_id"]):
            items_by_kind.setdefault((zipmod_id, kind, item_key), item_db_id)
            items_by_id.setdefault((zipmod_id, item_key), item_db_id)

    fallback_ids: set[int] = set()
    for row in conn.execute(
        """
        SELECT ccd.zipmod_id, ccd.category_no, ccd.slot, ccd.local_slot
        FROM character_card_dependencies ccd
        INNER JOIN character_cards cc ON cc.id = ccd.card_id
        WHERE cc.parse_status != 'stale'
          AND ccd.mod_item_id IS NULL
          AND ccd.zipmod_id IS NOT NULL
        """
    ):
        zipmod_id = int(row["zipmod_id"])
        kind = str(row["category_no"] or "").strip()
        candidates = [row["slot"], row["local_slot"]]
        item_db_id = next(
            (
                items_by_kind.get((zipmod_id, kind, item_key))
                for value in candidates
                for item_key in _normalized_usage_item_keys(value)
                if items_by_kind.get((zipmod_id, kind, item_key)) is not None
            ),
            None,
        )
        if item_db_id is None:
            item_db_id = next(
                (
                    items_by_id.get((zipmod_id, item_key))
                    for value in candidates
                    for item_key in _normalized_usage_item_keys(value)
                    if items_by_id.get((zipmod_id, item_key)) is not None
                ),
                None,
            )
        if item_db_id is not None:
            fallback_ids.add(int(item_db_id))
    return fallback_ids


def list_mod_items(
    db_path: Path = DEFAULT_DB_PATH,
    offset: int = 0,
    limit: int = 500,
    zipmod_id: int | None = None,
    search: str = "",
    kind: str = "",
    author: str = "",
    status: str = "",
    usage: str = "",
    source: str = "mod",
    game_dir: Path | str | None = None,
    include_total: bool = True,
) -> dict:
    resolved = db_path.resolve()
    offset = max(0, int(offset))
    limit = min(1000, max(1, int(limit)))
    search = str(search or "").strip()
    kind = str(kind or "").strip()
    author = str(author or "").strip()
    status = str(status or "").strip()
    usage = str(usage or "").strip()
    source = {
        "mod": "mod",
        "mods": "mod",
        "zipmod": "mod",
        "zipmods": "mod",
        "builtin": "builtin",
        "all": "all",
    }.get(str(source or "mod").strip().casefold(), "mod")
    game_dir_key = str(Path(game_dir).resolve()).casefold() if game_dir else ""
    if not resolved.exists() or not resolved.is_file():
        return {
            "exists": False,
            "database_path": str(resolved),
            "rows": [],
            "offset": offset,
            "limit": limit,
            "total": 0,
            "has_more": False,
            "filters": {
                "search": search,
                "kind": kind,
                "author": author,
                "status": status,
                "usage": usage,
                "source": source,
            },
        }

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        if usage in {"used", "unused"}:
            conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS star_manager_usage_fallback (id INTEGER PRIMARY KEY)"
            )
            conn.execute("DELETE FROM star_manager_usage_fallback")
            fallback_ids = _orphaned_usage_item_ids(conn)
            if fallback_ids:
                conn.executemany(
                    "INSERT INTO star_manager_usage_fallback (id) VALUES (?)",
                    ((item_id,) for item_id in fallback_ids),
                )
        def append_mod_query() -> tuple[str, list[int | str]]:
            clauses: list[str] = ["zipmods.scan_status != 'stale'"]
            query_params: list[int | str] = []
            if zipmod_id is not None:
                clauses.append("mod_items.zipmod_id = ?")
                query_params.append(int(zipmod_id))
            if search:
                clauses.append(
                    """
                    (
                        mod_items.name LIKE ? ESCAPE '\\'
                        OR mod_items.item_id LIKE ? ESCAPE '\\'
                        OR mod_items.zipmod_guid LIKE ? ESCAPE '\\'
                    )
                    """
                )
                search_pattern = f"%{escape_like(search)}%"
                query_params.extend([search_pattern, search_pattern, search_pattern])
            if kind:
                if kind == MAP_SCENE_FILTER_KIND:
                    placeholders = ", ".join("?" for _ in MAP_SCENE_KINDS)
                    clauses.append(f"TRIM(mod_items.kind) IN ({placeholders})")
                    query_params.extend(MAP_SCENE_KINDS)
                else:
                    clauses.append("TRIM(mod_items.kind) = ?")
                    query_params.append(kind)
            if author:
                if author == UNKNOWN_AUTHOR:
                    clauses.append("TRIM(COALESCE(mod_items.zipmod_author, '')) = ''")
                elif author == BUILTIN_SOURCE_LABEL:
                    clauses.append("1 = 0")
                else:
                    clauses.append("TRIM(mod_items.zipmod_author) = ?")
                    query_params.append(author)
            if status == "ready":
                clauses.append(
                    """
                    mod_items.parse_status = 'ok'
                    AND COALESCE(mod_items.unity3d_status, '') NOT IN ('missing', 'error')
                    AND (
                        mod_items.thumbnail_status IN ('ready', 'ok')
                        OR TRIM(COALESCE(mod_items.kind, '')) IN ('500', '501')
                    )
                    """
                )
            elif status == "error":
                clauses.append(
                    "mod_items.parse_status != 'ok' OR COALESCE(mod_items.unity3d_status, '') IN ('missing', 'error')"
                )
            elif status == "thumb":
                clauses.append(
                    """
                    mod_items.parse_status = 'ok'
                    AND COALESCE(mod_items.unity3d_status, '') NOT IN ('missing', 'error')
                    AND TRIM(COALESCE(mod_items.kind, '')) NOT IN ('500', '501')
                    AND (mod_items.thumbnail_status = '' OR mod_items.thumbnail_status NOT IN ('ready', 'ok'))
                    """
                )
            if usage == "used":
                clauses.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM character_card_dependencies ccd
                        INNER JOIN character_cards cc ON cc.id = ccd.card_id
                        WHERE cc.parse_status != 'stale'
                          AND ccd.mod_item_id = mod_items.id
                    )
                    OR mod_items.id IN (SELECT id FROM star_manager_usage_fallback)
                    """
                )
            elif usage == "unused":
                clauses.append(
                    """
                    NOT EXISTS (
                        SELECT 1
                        FROM character_card_dependencies ccd
                        INNER JOIN character_cards cc ON cc.id = ccd.card_id
                        WHERE cc.parse_status != 'stale'
                          AND ccd.mod_item_id = mod_items.id
                    )
                    AND mod_items.id NOT IN (SELECT id FROM star_manager_usage_fallback)
                    """
                )
            where_clause = " AND ".join(f"({clause})" for clause in clauses)
            return (
                f"""
                SELECT 'mod' AS source_type,
                       mod_items.id AS id, mod_items.zipmod_id AS zipmod_id,
                       mod_items.parse_status AS status, mod_items.thumbnail_status,
                       mod_items.thumbnail_cache_path, mod_items.unity3d_status,
                       mod_items.unity3d_source, mod_items.unity3d_error,
                       mod_items.name, mod_items.kind, mod_items.zipmod_author AS author,
                       mod_items.zipmod_guid, mod_items.item_id, mod_items.csv_path,
                       mod_items.main_ab, mod_items.main_data, mod_items.thumb_tex,
                       zipmods.name AS source_mod, zipmods.file_name AS source_file_name,
                       '' AS game_dir, '' AS source_path, '' AS source_asset,
                       '' AS main_manifest, '' AS thumb_ab, mod_items.thumbnail_error,
                       '' AS resource_status, '' AS resource_error
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE {where_clause}
                """,
                query_params,
            )

        def append_builtin_query() -> tuple[str, list[int | str]]:
            visible_kind_placeholders = ", ".join("?" for _ in BUILTIN_VISIBLE_KINDS)
            clauses: list[str] = [
                "builtin_items.game_dir_key = ?" if game_dir_key else "1 = 0",
                f"TRIM(builtin_items.category_no) IN ({visible_kind_placeholders})",
            ]
            query_params: list[int | str] = (
                ([game_dir_key] if game_dir_key else [])
                + list(BUILTIN_VISIBLE_KINDS)
            )
            if zipmod_id is not None or usage in {"used", "unused"}:
                clauses.append("1 = 0")
            if search:
                clauses.append(
                    """
                    (
                        builtin_items.name LIKE ? ESCAPE '\\'
                        OR builtin_items.item_id LIKE ? ESCAPE '\\'
                        OR builtin_items.category_no LIKE ? ESCAPE '\\'
                        OR builtin_items.source_path LIKE ? ESCAPE '\\'
                    )
                    """
                )
                search_pattern = f"%{escape_like(search)}%"
                query_params.extend([search_pattern] * 4)
            if kind:
                if kind == MAP_SCENE_FILTER_KIND:
                    clauses.append("1 = 0")
                else:
                    clauses.append("TRIM(builtin_items.category_no) = ?")
                    query_params.append(kind)
            if author and author != BUILTIN_SOURCE_LABEL:
                clauses.append("1 = 0")
            if status == "ready":
                clauses.append(
                    """
                    builtin_items.resource_status IN ('in_game', 'not_applicable')
                    AND builtin_items.thumbnail_status IN ('ready', 'ok')
                    """
                )
            elif status == "error":
                clauses.append("builtin_items.resource_status NOT IN ('in_game', 'not_applicable')")
            elif status == "thumb":
                clauses.append(
                    """
                    builtin_items.resource_status IN ('in_game', 'not_applicable')
                    AND (builtin_items.thumbnail_status = '' OR builtin_items.thumbnail_status NOT IN ('ready', 'ok'))
                    """
                )
            where_clause = " AND ".join(f"({clause})" for clause in clauses)
            return (
                f"""
                SELECT 'builtin' AS source_type,
                       builtin_items.id AS id, NULL AS zipmod_id,
                       'ok' AS status, builtin_items.thumbnail_status,
                       builtin_items.thumbnail_cache_path,
                       CASE
                           WHEN builtin_items.resource_status IN ('in_game', 'not_applicable') THEN 'in_game'
                           ELSE 'missing'
                       END AS unity3d_status,
                       'game_abdata' AS unity3d_source,
                       builtin_items.resource_error AS unity3d_error,
                       builtin_items.name, builtin_items.category_no AS kind,
                       ? AS author, '' AS zipmod_guid, builtin_items.item_id,
                       builtin_items.source_path AS csv_path,
                       builtin_items.main_ab, builtin_items.main_data, builtin_items.thumb_tex,
                       ? AS source_mod, '' AS source_file_name,
                       builtin_items.game_dir, builtin_items.source_path, builtin_items.source_asset,
                       builtin_items.main_manifest, builtin_items.thumb_ab,
                       builtin_items.thumbnail_error, builtin_items.resource_status,
                       builtin_items.resource_error
                FROM builtin_items
                WHERE {where_clause}
                """,
                [BUILTIN_SOURCE_LABEL, BUILTIN_SOURCE_LABEL, *query_params],
            )

        queries: list[tuple[str, list[int | str]]] = []
        if source in {"mod", "all"}:
            queries.append(append_mod_query())
        if source in {"builtin", "all"}:
            queries.append(append_builtin_query())
        union_sql = " UNION ALL ".join(query for query, _ in queries)
        params = [param for _, query_params in queries for param in query_params]
        total = None
        if include_total:
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) FROM ({union_sql}) AS item_sources",
                    params,
                ).fetchone()[0]
            )
        page_limit = limit + 1 if total is None else limit
        raw_rows = conn.execute(
            f"""
            SELECT *
            FROM ({union_sql}) AS item_sources
            ORDER BY name COLLATE NOCASE, source_type, id
            LIMIT ? OFFSET ?
            """,
            (*params, page_limit, offset),
        ).fetchall()
        has_more = len(raw_rows) > limit if total is None else offset + len(raw_rows) < total
        if len(raw_rows) > limit:
            raw_rows = raw_rows[:limit]
        rows = []
        for row in raw_rows:
            if row["source_type"] == "builtin":
                rows.append(
                    {
                        "id": row["id"],
                        "source_type": "builtin",
                        "source_label": BUILTIN_SOURCE_LABEL,
                        "game_dir": row["game_dir"],
                        "status": row["status"],
                        "thumbnail_status": row["thumbnail_status"],
                        "thumbnail_cache_path": row["thumbnail_cache_path"],
                        "thumbnail_url": thumbnail_url_for_cache_path(row["thumbnail_cache_path"]),
                        "unity3d_status": row["unity3d_status"],
                        "unity3d_source": row["unity3d_source"],
                        "unity3d_error": row["unity3d_error"],
                        "resource_status": row["resource_status"],
                        "resource_error": row["resource_error"],
                        "name": row["name"],
                        "kind": row["kind"],
                        "category_no": row["kind"],
                        "author": BUILTIN_SOURCE_LABEL,
                        "source_mod": BUILTIN_SOURCE_LABEL,
                        "zipmod_guid": "",
                        "item_id": row["item_id"],
                        "csv_path": row["csv_path"],
                        "source_path": row["source_path"],
                        "source_asset": row["source_asset"],
                        "main_manifest": row["main_manifest"],
                        "main_ab": row["main_ab"],
                        "main_data": row["main_data"],
                        "thumb_ab": row["thumb_ab"],
                        "thumb_tex": row["thumb_tex"],
                        "thumbnail_error": row["thumbnail_error"],
                    }
                )
                continue
            rows.append(
                {
                    "id": row["id"],
                    "source_type": "mod",
                    "source_label": "模组",
                    "zipmod_id": row["zipmod_id"],
                    "status": row["status"],
                    "thumbnail_status": row["thumbnail_status"],
                    "thumbnail_cache_path": row["thumbnail_cache_path"],
                    "thumbnail_url": (
                        thumbnail_url_for_cache_path(row["thumbnail_cache_path"])
                        or thumbnail_recovery_url_for_item(
                            row["id"],
                            row["status"],
                            row["thumbnail_status"],
                            row["kind"],
                            row["thumb_tex"],
                        )
                    ),
                    "unity3d_status": row["unity3d_status"],
                    "unity3d_source": row["unity3d_source"],
                    "unity3d_error": row["unity3d_error"],
                    "name": row["name"],
                    "kind": row["kind"],
                    "author": row["author"] or UNKNOWN_AUTHOR,
                    "source_mod": row["source_mod"] or row["source_file_name"],
                    "zipmod_guid": row["zipmod_guid"],
                    "item_id": row["item_id"],
                    "csv_path": row["csv_path"],
                    "main_ab": row["main_ab"],
                }
            )
        return {
            "exists": True,
            "database_path": str(resolved),
            "rows": rows,
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": has_more,
            "filters": {
                "search": search,
                "kind": kind,
                "author": author,
                "status": status,
                "usage": usage,
                "source": source,
            },
        }
    finally:
        conn.close()


def list_workbench_template_items(
    db_path: Path = DEFAULT_DB_PATH,
    offset: int = 0,
    limit: int = 30,
    search: str = "",
    author: str = "",
    kind: str = "",
) -> dict:
    """List indexed items whose main Unity3D can be used as a workbench template."""
    resolved = db_path.resolve()
    offset = max(0, int(offset))
    limit = min(100, max(1, int(limit)))
    search = str(search or "").strip()
    author = str(author or "").strip()
    kind = str(kind or "").strip()
    if not resolved.exists() or not resolved.is_file():
        return {
            "exists": False,
            "database_path": str(resolved),
            "rows": [],
            "offset": offset,
            "limit": limit,
            "total": 0,
            "has_more": False,
        }

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        where_clauses = [
            "zipmods.scan_status != 'stale'",
            "mod_items.parse_status = 'ok'",
            "LOWER(TRIM(COALESCE(mod_items.main_ab, ''))) LIKE '%.unity3d'",
            "COALESCE(mod_items.unity3d_status, '') IN ('in_mod', 'in_game', 'not_in_mod')",
            "TRIM(COALESCE(mod_items.kind, '')) NOT IN ('__map_scene__', '__game_map_scene__', '__game_studio_map_scene__')",
        ]
        params: list[str] = []
        if author:
            if author == UNKNOWN_AUTHOR:
                where_clauses.append(
                    "TRIM(COALESCE(NULLIF(mod_items.zipmod_author, ''), zipmods.author, '')) = ''"
                )
            else:
                where_clauses.append(
                    "TRIM(COALESCE(NULLIF(mod_items.zipmod_author, ''), zipmods.author, '')) LIKE ? ESCAPE '\\' COLLATE NOCASE"
                )
                params.append(f"%{escape_like(author)}%")
        if kind:
            where_clauses.append("TRIM(COALESCE(mod_items.kind, '')) = ?")
            params.append(kind)
        if search:
            search_pattern = f"%{escape_like(search)}%"
            where_clauses.append(
                """
                (
                    mod_items.name LIKE ? ESCAPE '\\'
                    OR mod_items.item_id LIKE ? ESCAPE '\\'
                    OR mod_items.main_ab LIKE ? ESCAPE '\\'
                    OR mod_items.main_data LIKE ? ESCAPE '\\'
                    OR mod_items.zipmod_guid LIKE ? ESCAPE '\\'
                    OR zipmods.name LIKE ? ESCAPE '\\'
                    OR zipmods.file_name LIKE ? ESCAPE '\\'
                    OR zipmods.author LIKE ? ESCAPE '\\'
                )
                """
            )
            params.extend([search_pattern] * 8)

        where_clause = "WHERE " + " AND ".join(f"({clause})" for clause in where_clauses)
        total = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                {where_clause}
                """,
                params,
            ).fetchone()[0]
        )
        rows = [
            {
                "id": row["id"],
                "zipmod_id": row["zipmod_id"],
                "name": row["name"],
                "kind": row["kind"],
                "author": row["zipmod_author"] or row["zipmod_manifest_author"] or UNKNOWN_AUTHOR,
                "source_mod": row["zipmod_name"] or row["zipmod_file_name"],
                "zipmod_guid": row["zipmod_guid"],
                "item_id": row["item_id"],
                "csv_path": row["csv_path"],
                "main_manifest": row["main_manifest"],
                "main_ab": row["main_ab"],
                "main_data": row["main_data"],
                "unity3d_status": row["unity3d_status"],
                "thumbnail_url": thumbnail_url_for_cache_path(row["thumbnail_cache_path"]),
            }
            for row in conn.execute(
                f"""
                SELECT mod_items.id, mod_items.zipmod_id, mod_items.name, mod_items.kind,
                       mod_items.zipmod_guid, mod_items.item_id, mod_items.csv_path,
                       mod_items.main_manifest, mod_items.main_ab, mod_items.main_data,
                       mod_items.unity3d_status, mod_items.thumbnail_cache_path,
                       mod_items.zipmod_author,
                       zipmods.name AS zipmod_name, zipmods.file_name AS zipmod_file_name,
                       zipmods.author AS zipmod_manifest_author
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                {where_clause}
                ORDER BY mod_items.name COLLATE NOCASE, mod_items.id
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            )
        ]
        return {
            "exists": True,
            "database_path": str(resolved),
            "rows": rows,
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + len(rows) < total,
        }
    finally:
        conn.close()
