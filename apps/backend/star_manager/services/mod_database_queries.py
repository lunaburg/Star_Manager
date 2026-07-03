from __future__ import annotations

import re
import shutil
import sqlite3
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    UNKNOWN_AUTHOR,
    get_database_metadata,
    init_db,
    utc_now,
)


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


def database_status(db_path: Path = DEFAULT_DB_PATH) -> dict:
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
        init_db(conn)
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
                      OR COALESCE(unity3d_status, '') = 'in_game'
                      OR COALESCE(unity3d_in_game_count, 0) > 0
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


def list_mod_item_filters(db_path: Path = DEFAULT_DB_PATH) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found", "authors": [], "kinds": []}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
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
        kinds = [
            row["kind"]
            for row in conn.execute(
                """
                SELECT DISTINCT TRIM(kind) AS kind
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE zipmods.scan_status != 'stale'
                  AND TRIM(kind) != ''
                ORDER BY CAST(kind AS INTEGER), kind COLLATE NOCASE
                """
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
) -> dict:
    resolved = db_path.resolve()
    offset = max(0, int(offset))
    limit = min(500, max(1, int(limit)))
    author = str(author or "").strip()
    status = str(status or "").strip()
    usage = str(usage or "").strip()
    if not resolved.exists() or not resolved.is_file():
        return {
            "exists": False,
            "database_path": str(resolved),
            "rows": [],
            "offset": offset,
            "limit": limit,
            "total": 0,
            "has_more": False,
            "filters": {"author": author, "status": status, "usage": usage},
        }

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        where_sql = ""
        params: list[str] = []
        where_clauses: list[str] = ["scan_status != 'stale'"]
        if author:
            if author == UNKNOWN_AUTHOR:
                where_clauses.append("TRIM(COALESCE(author, '')) = ''")
            else:
                where_clauses.append("TRIM(author) = ?")
                params.append(author)
        if status == "normal":
            where_clauses.append(
                """
                scan_status = 'ok'
                AND TRIM(COALESCE(author, '')) != ''
                AND COALESCE(unity3d_status, '') NOT IN ('missing', 'in_game', 'error')
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
                    OR COALESCE(unity3d_status, '') IN ('missing', 'in_game', 'error')
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
                    OR COALESCE(unity3d_status, '') = 'in_game'
                    OR COALESCE(unity3d_in_game_count, 0) > 0
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
                "unity3d_in_mod_count": row["unity3d_in_mod_count"],
                "unity3d_in_game_count": row["unity3d_in_game_count"],
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
                       unity3d_status, unity3d_in_mod_count, unity3d_in_game_count,
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
            "filters": {"author": author, "status": status, "usage": usage},
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
    if export_layout not in {"tree", "by_author"}:
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

            target = (target_root / relative).resolve()
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
                       mod_items.main_manifest, mod_items.main_ab, mod_items.thumb_ab
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                WHERE mod_items.zipmod_id IN ({item_placeholders})
                  AND mod_items.unity3d_status = 'in_game'
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
) -> dict:
    resolved = db_path.resolve()
    offset = max(0, int(offset))
    limit = min(1000, max(1, int(limit)))
    search = str(search or "").strip()
    kind = str(kind or "").strip()
    author = str(author or "").strip()
    status = str(status or "").strip()
    usage = str(usage or "").strip()
    if not resolved.exists() or not resolved.is_file():
        return {
            "exists": False,
            "database_path": str(resolved),
            "rows": [],
            "offset": offset,
            "limit": limit,
            "total": 0,
            "has_more": False,
            "filters": {"search": search, "kind": kind, "author": author, "status": status, "usage": usage},
        }

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        params: list[int | str] = []
        where_clauses: list[str] = ["zipmods.scan_status != 'stale'"]
        if zipmod_id is not None:
            where_clauses.append("mod_items.zipmod_id = ?")
            params.append(int(zipmod_id))
        if search:
            where_clauses.append(
                """
                (
                    mod_items.name LIKE ? ESCAPE '\\'
                    OR mod_items.item_id LIKE ? ESCAPE '\\'
                    OR mod_items.zipmod_guid LIKE ? ESCAPE '\\'
                )
                """
            )
            search_pattern = f"%{escape_like(search)}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        if kind:
            where_clauses.append("TRIM(mod_items.kind) = ?")
            params.append(kind)
        if author:
            if author == UNKNOWN_AUTHOR:
                where_clauses.append("TRIM(COALESCE(mod_items.zipmod_author, '')) = ''")
            else:
                where_clauses.append("TRIM(mod_items.zipmod_author) = ?")
                params.append(author)
        if status == "ready":
            where_clauses.append(
                """
                mod_items.parse_status = 'ok'
                AND COALESCE(mod_items.unity3d_status, '') NOT IN ('missing', 'error')
                AND mod_items.thumbnail_status IN ('ready', 'ok')
                """
            )
        elif status == "error":
            where_clauses.append(
                "mod_items.parse_status != 'ok' OR COALESCE(mod_items.unity3d_status, '') IN ('missing', 'error')"
            )
        elif status == "thumb":
            where_clauses.append(
                """
                mod_items.parse_status = 'ok'
                AND COALESCE(mod_items.unity3d_status, '') NOT IN ('missing', 'error')
                AND (mod_items.thumbnail_status = '' OR mod_items.thumbnail_status NOT IN ('ready', 'ok'))
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
                      AND ccd.mod_item_id = mod_items.id
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
                      AND ccd.mod_item_id = mod_items.id
                )
                """
            )
        where_clause = "WHERE " + " AND ".join(f"({clause})" for clause in where_clauses) if where_clauses else ""

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
                "status": row["parse_status"],
                "thumbnail_status": row["thumbnail_status"],
                "thumbnail_cache_path": row["thumbnail_cache_path"],
                "thumbnail_url": thumbnail_url_for_cache_path(row["thumbnail_cache_path"]),
                "unity3d_status": row["unity3d_status"],
                "unity3d_error": row["unity3d_error"],
                "name": row["name"],
                "kind": row["kind"],
                "author": row["zipmod_author"] or UNKNOWN_AUTHOR,
                "source_mod": row["zipmod_name"] or row["zipmod_file_name"],
                "zipmod_guid": row["zipmod_guid"],
                "item_id": row["item_id"],
                "csv_path": row["csv_path"],
            }
            for row in conn.execute(
                """
                SELECT mod_items.id, mod_items.zipmod_id, mod_items.parse_status, mod_items.thumbnail_status,
                       mod_items.thumbnail_cache_path, mod_items.unity3d_status,
                       mod_items.unity3d_error, mod_items.name, mod_items.kind,
                       mod_items.zipmod_author, mod_items.zipmod_guid, mod_items.item_id, mod_items.csv_path,
                       zipmods.name AS zipmod_name, zipmods.file_name AS zipmod_file_name
                FROM mod_items
                INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
                {where_clause}
                ORDER BY mod_items.name COLLATE NOCASE, mod_items.id
                LIMIT ? OFFSET ?
                """.format(where_clause=where_clause),
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
            "filters": {"search": search, "kind": kind, "author": author, "status": status, "usage": usage},
        }
    finally:
        conn.close()
