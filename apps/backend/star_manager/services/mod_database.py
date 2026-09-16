from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import os
import re
import sqlite3
import tempfile
from time import perf_counter
import uuid
import zipfile
from pathlib import Path
from typing import Callable, Iterable
import xml.etree.ElementTree as ET

from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    VENDOR_DIR,
    CsvItem,
    ManifestData,
    PreparedModItem,
    PreparedZipmodItems,
    ThumbnailResult,
    Unity3dProvider,
    Unity3dStatus,
    ZipmodCandidate,
    init_db,
    set_database_metadata,
    timestamp_to_utc,
    utc_now,
)
from star_manager.services.mod_database_queries import (
    database_status,
    export_zipmods,
    find_zipmod_paths_by_guid,
    list_mod_item_filters,
    list_mod_items,
    list_workbench_template_items,
    list_zipmod_authors,
    list_zipmods,
    resolve_thumbnail_cache_path,
)
from star_manager.services.model_preview import (
    list_unity3d_main_data_candidates,
    export_item_unity3d_file,
    preprocess_unity3d_asset,
    prepare_item_unity3d_file,
    prepare_item_model_preview,
    resolve_mannequin_model_file,
    resolve_model_preview_file,
)


from star_manager.services.mod_database_assets import (
    analyze_duplicate_zipmods,
    begin_thumbnail_profile,
    bulk_repair_zipmods_unity3d_from_game,
    cleanup_duplicate_zipmods,
    choose_primary,
    decode_csv_bytes_with_encoding,
    decode_csv_bytes,
    delete_mod_item,
    delete_primary_and_promote_duplicate,
    delete_zipmod,
    export_zipmod_item_thumbnail,
    ensure_mod_item_thumbnail,
    extract_thumbnail_from_zipmod,
    find_zipmods,
    find_header_index,
    get_zipmod_manifest,
    inspect_unity3d_status,
    is_map_scene_item,
    is_unity3d_path,
    main_unity3d_reference_paths,
    import_zipmod_item_thumbnail,
    iter_open_zip_csv_items,
    iter_zip_csv_items,
    get_existing_paths,
    group_valid_candidates,
    merge_duplicate_zipmod,
    normalize_zip_path,
    normalize_abdata_path,
    preextract_zip_unity_thumbnails,
    read_items_from_csv,
    read_manifest,
    repair_zipmod_unity3d_from_game,
    remove_unseen_zipmods,
    replace_duplicate_records,
    resolve_game_abdata_path,
    resolve_game_dir_from_zipmod,
    summarize_zipmod_unity3d_status,
    ThumbnailSourceCache,
    update_zipmod_manifest,
    update_zipmod_manifest_author,
    upsert_invalid_zipmod,
    upsert_zipmod,
    UnityThumbnailBundleCache,
    ZipMemberIndex,
    write_thumbnail_profile,
    zipmod_unity3d_diagnostics,
    refresh_unity3d_provider_index,
    unity3d_provider_lookup_keys,
)
from star_manager.services.builtin_database import build_builtin_items_index
from star_manager.services.card_library import (
    IGNORED_ROOT_CARD_DIRS,
    get_card_root,
    normalize_relative,
)


SCAN_PROGRESS = 5
FOUND_PROGRESS = 12
DISCOVER_END_PROGRESS = 7
PREPARE_START_PROGRESS = 15
PREPARE_END_PROGRESS = 70
WRITE_START_PROGRESS = 72
WRITE_END_PROGRESS = 96
FINALIZE_PROGRESS = 98
AUTO_REBUILD_MAX_CHANGES = 200
AUTO_REBUILD_MAX_RATIO = 0.05
MAX_DATABASE_WORKERS = 8


def get_build_worker_limit() -> int:
    """Return the safe configurable worker limit for mod database builds."""
    cpu_count = max(1, os.cpu_count() or 1)
    return max(1, min(MAX_DATABASE_WORKERS, cpu_count // 2))


def choose_build_worker_count(requested_worker_count: int | str | None = None) -> int:
    """Clamp the configured worker count without considering task size."""
    worker_limit = get_build_worker_limit()
    try:
        requested = int(requested_worker_count) if requested_worker_count is not None else worker_limit
    except (TypeError, ValueError):
        requested = worker_limit
    return max(1, min(worker_limit, requested))


def calculate_progress(current: int, total: int, start: int, end: int) -> float:
    if total <= 0:
        return float(end)
    clamped = min(max(current, 0), total)
    return start + clamped / total * (end - start)


def summarize_prepared_unity3d(
    items: list[PreparedModItem],
) -> tuple[str, int, int, int, int, int, str]:
    in_mod = 0
    not_in_mod = 0
    in_game = 0
    other_mod = 0
    missing = 0
    error = 0
    missing_examples: list[str] = []
    for item in items:
        if item.unity3d_status == "in_mod":
            in_mod += 1
        elif item.unity3d_status in {"in_game", "not_in_mod"}:
            not_in_mod += 1
            if item.unity3d_source == "other_zipmod":
                other_mod += 1
            else:
                in_game += 1
        elif item.unity3d_status == "missing":
            missing += 1
            if item.unity3d_error and len(missing_examples) < 3:
                missing_examples.append(item.unity3d_error)
        elif item.unity3d_status == "error":
            error += 1
            if item.unity3d_error and len(missing_examples) < 3:
                missing_examples.append(item.unity3d_error)

    if error:
        status = "error"
    elif missing:
        status = "missing"
    elif not_in_mod:
        status = "not_in_mod"
    elif in_mod:
        status = "in_mod"
    else:
        status = ""
    return status, in_mod, not_in_mod, in_game, other_mod, missing, " | ".join(missing_examples)


def thumbnail_error_indicates_unity3d_unreadable(item, thumbnail: ThumbnailResult) -> bool:
    if thumbnail.status != "error":
        return False
    if thumbnail.error not in {"UnityPy is not available", "UnityPy loaded no objects"} and not thumbnail.error.startswith("UnityPy load failed: "):
        return False
    if not item.thumb_ab or not is_unity3d_path(item.thumb_ab):
        return False
    thumb_ab = normalize_zip_path(item.thumb_ab).lower()
    thumb_ab = thumb_ab.removeprefix("abdata/")
    main_references = {
        normalize_zip_path(reference).lower().removeprefix("abdata/")
        for reference in main_unity3d_reference_paths(item)
    }
    return bool(main_references) and thumb_ab in main_references


def build_candidates_from_file_stats(
    conn: sqlite3.Connection,
    game_dir: Path,
    force_full: bool,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[list[ZipmodCandidate], set[str], dict[str, int]]:
    mods_dir = game_dir / "mods"
    existing_by_path = {
        str(row["file_path"]): row
        for row in conn.execute(
            """
            SELECT guid, name, version, author, file_path, relative_path,
                   file_size, modified_at, scan_status, scan_error
            FROM zipmods
            """
        )
    }

    def report_discovered(count: int) -> None:
        if progress_callback is not None:
            progress_callback("discover", count, 0)

    zipmod_paths = find_zipmods(game_dir, report_discovered)
    total = len(zipmod_paths)
    if progress_callback is not None:
        progress_callback("discover_done", total, total)

    candidates: list[ZipmodCandidate] = []
    changed_paths: set[str] = set()
    stats = {"reused_zipmods": 0, "changed_zipmods": 0}
    for index, path in enumerate(zipmod_paths, start=1):
        resolved_path = path.resolve()
        stat = path.stat()
        modified_at = timestamp_to_utc(stat.st_mtime)
        relative_path = path.relative_to(mods_dir).as_posix()
        existing = existing_by_path.get(str(resolved_path))
        can_reuse = (
            not force_full
            and existing is not None
            and int(existing["file_size"] or 0) == stat.st_size
            and str(existing["modified_at"] or "") == modified_at
            and str(existing["scan_status"] or "") != "stale"
        )
        if can_reuse:
            cached_guid = str(existing["guid"] or "")
            manifest_guid = "" if cached_guid.startswith("__invalid__:") else cached_guid
            manifest = ManifestData(
                manifest_guid,
                str(existing["name"] or ""),
                str(existing["version"] or ""),
                str(existing["author"] or ""),
                str(existing["scan_status"] or "ok"),
                str(existing["scan_error"] or ""),
            )
            stats["reused_zipmods"] += 1
        else:
            manifest = read_manifest(path)
            changed_paths.add(str(resolved_path))
            stats["changed_zipmods"] += 1

        candidates.append(
            ZipmodCandidate(
                manifest=manifest,
                path=resolved_path,
                relative_path=relative_path,
                file_size=stat.st_size,
                modified_at=modified_at,
            )
        )
        if progress_callback is not None and (
            index == total or index == 1 or index % 100 == 0
        ):
            progress_callback("manifest", index, total)
    return candidates, changed_paths, stats


def assess_database_changes(
    game_dir: Path | str,
    db_path: Path = DEFAULT_DB_PATH,
    auto_change_limit: int = AUTO_REBUILD_MAX_CHANGES,
    auto_change_ratio: float = AUTO_REBUILD_MAX_RATIO,
) -> dict:
    game_dir = Path(game_dir).resolve()
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {
            "ok": True,
            "exists": False,
            "needs_rebuild": True,
            "recommended_action": "manual_rebuild",
            "reason": "database_missing",
            "changes": {},
        }

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod_changes = assess_zipmod_file_changes(conn, game_dir)
        card_changes = assess_card_file_changes(conn, game_dir)
        total_changes = zipmod_changes["changed_total"] + card_changes["changed_total"]
        total_current = max(zipmod_changes["current_total"] + card_changes["current_total"], 1)
        ratio = total_changes / total_current
        needs_rebuild = total_changes > 0
        recommended_action = "none"
        reason = "up_to_date"
        if needs_rebuild:
            if total_changes <= auto_change_limit and ratio <= auto_change_ratio:
                recommended_action = "auto_incremental"
                reason = "small_change"
            else:
                recommended_action = "manual_rebuild"
                reason = "large_change"
        return {
            "ok": True,
            "exists": True,
            "needs_rebuild": needs_rebuild,
            "recommended_action": recommended_action,
            "reason": reason,
            "total_changes": total_changes,
            "change_ratio": ratio,
            "thresholds": {
                "auto_change_limit": auto_change_limit,
                "auto_change_ratio": auto_change_ratio,
            },
            "changes": {
                "zipmods": zipmod_changes,
                "cards": card_changes,
            },
        }
    finally:
        conn.close()


def assess_zipmod_file_changes(conn: sqlite3.Connection, game_dir: Path) -> dict[str, int]:
    current: dict[str, tuple[int, str]] = {}
    for path in find_zipmods(game_dir):
        stat = path.stat()
        current[str(path.resolve())] = (stat.st_size, timestamp_to_utc(stat.st_mtime))

    existing = {
        str(row["file_path"]): (int(row["file_size"] or 0), str(row["modified_at"] or ""))
        for row in conn.execute(
            "SELECT file_path, file_size, modified_at FROM zipmods WHERE scan_status != 'stale'"
        )
    }
    primary_total = len(existing)
    duplicate_existing = {
        str(row["file_path"]): (int(row["file_size"] or 0), str(row["modified_at"] or ""))
        for row in conn.execute(
            """
            SELECT d.file_path, d.file_size, d.modified_at
            FROM duplicate_zipmods d
            INNER JOIN zipmods z ON z.guid = d.guid
            WHERE z.scan_status != 'stale'
            """
        )
    }
    existing.update(duplicate_existing)
    added = len([path for path in current if path not in existing])
    removed = len([path for path in existing if path not in current])
    modified = len(
        [
            path
            for path, stat_key in current.items()
            if path in existing and existing[path] != stat_key
        ]
    )
    return {
        "current_total": len(current),
        "indexed_total": len(existing),
        "indexed_primary_total": primary_total,
        "indexed_duplicate_total": len(duplicate_existing),
        "added": added,
        "removed": removed,
        "modified": modified,
        "changed_total": added + removed + modified,
    }


def assess_card_file_changes(conn: sqlite3.Connection, game_dir: Path) -> dict[str, int]:
    root = get_card_root(str(game_dir))
    current: dict[str, str] = {}
    if root.is_dir():
        for path in root.rglob("*.png"):
            if not path.is_file():
                continue
            try:
                relative = path.resolve().relative_to(root.resolve())
            except ValueError:
                continue
            if relative.parts and relative.parts[0].casefold() in IGNORED_ROOT_CARD_DIRS:
                continue
            current[str(path.resolve())] = timestamp_to_utc(path.stat().st_mtime)

    existing = {
        str(row["file_path"]): str(row["modified_at"] or "")
        for row in conn.execute(
            "SELECT file_path, modified_at FROM character_cards WHERE parse_status != 'stale'"
        )
    }
    added = len([path for path in current if path not in existing])
    removed = len([path for path in existing if path not in current])
    modified = len(
        [
            path
            for path, modified_at in current.items()
            if path in existing and existing[path] != modified_at
        ]
    )
    return {
        "current_total": len(current),
        "indexed_total": len(existing),
        "added": added,
        "removed": removed,
        "modified": modified,
        "changed_total": added + removed + modified,
    }


def prepare_mod_items(
    game_dir: Path,
    candidate: ZipmodCandidate,
    thumbnail_dir: Path,
    provider_index: dict[str, list[Unity3dProvider]] | None = None,
) -> PreparedZipmodItems:
    ok_count = 0
    duplicate_items = 0
    seen_keys: set[tuple[str, str, str]] = set()
    prepared_items: list[PreparedModItem] = []
    bundle_cache = UnityThumbnailBundleCache()
    source_cache = ThumbnailSourceCache()

    status_zip: zipfile.ZipFile | None = None
    status_zip_index: ZipMemberIndex | None = None
    status_zip_error = ""
    try:
        status_zip = zipfile.ZipFile(candidate.path, "r")
        status_zip_index = ZipMemberIndex(status_zip)
    except (OSError, zipfile.BadZipFile) as exc:
        status_zip_error = str(exc)

    try:
        if status_zip is not None:
            csv_items = list(iter_open_zip_csv_items(status_zip, candidate.manifest.name))
            preextract_zip_unity_thumbnails(
                candidate,
                [
                    item
                    for item in csv_items
                    if not is_map_scene_item(item) or item.thumb_ab
                ],
                thumbnail_dir,
                status_zip,
                status_zip_index,
                bundle_cache,
                source_cache,
            )
        else:
            csv_items = list(iter_zip_csv_items(candidate.path))

        for item in csv_items:
            if not item.item_id:
                continue
            key = (candidate.manifest.guid, item.kind, item.item_id)
            if key in seen_keys:
                duplicate_items += 1
                continue
            seen_keys.add(key)
            thumbnail = (
                ThumbnailResult("", "ready", "")
                if is_map_scene_item(item) and not item.thumb_ab
                else extract_thumbnail_from_zipmod(
                    game_dir,
                    candidate,
                    item,
                    thumbnail_dir,
                    status_zip,
                    status_zip_index,
                    bundle_cache,
                    source_cache,
                )
            )
            if status_zip is None:
                unity3d = (
                    Unity3dStatus("missing", f"zipmod read failed: {status_zip_error}")
                    if item.parse_status == "ok"
                    else Unity3dStatus("", "")
                )
            else:
                unity3d = inspect_unity3d_status(
                    game_dir,
                    status_zip,
                    item,
                    status_zip_index,
                    provider_index,
                    str(candidate.path),
                )
                if unity3d.status == "in_mod" and thumbnail_error_indicates_unity3d_unreadable(item, thumbnail):
                    unity3d = Unity3dStatus(
                        "error",
                        f"unreadable thumbnail unity3d: abdata/{normalize_zip_path(item.thumb_ab)}: {thumbnail.error}",
                        "in_mod",
                    )
            prepared_items.append(
                PreparedModItem(
                    csv_path=item.csv_path,
                    item_id=item.item_id,
                    kind=item.kind,
                    name=item.name,
                    main_manifest=item.main_manifest,
                    main_ab=item.main_ab,
                    main_data=item.main_data,
                    tex_ab=item.tex_ab,
                    thumb_ab=item.thumb_ab,
                    thumb_tex=item.thumb_tex,
                    thumbnail_cache_path=thumbnail.cache_path,
                    thumbnail_status=thumbnail.status,
                    thumbnail_error=thumbnail.error,
                    unity3d_status=unity3d.status,
                    unity3d_source=unity3d.source,
                    unity3d_error=unity3d.error,
                    parse_status=item.parse_status,
                    parse_error=item.parse_error,
                )
            )
            if item.parse_status == "ok":
                ok_count += 1
    finally:
        if status_zip is not None:
            status_zip.close()

    unity3d_status, in_mod, not_in_mod, in_game, other_mod, missing, unity3d_error = summarize_prepared_unity3d(
        prepared_items
    )
    return PreparedZipmodItems(
        items=prepared_items,
        ok_count=ok_count,
        duplicate_items=duplicate_items,
        unity3d_status=unity3d_status,
        unity3d_in_mod_count=in_mod,
        unity3d_not_in_mod_count=not_in_mod,
        unity3d_in_game_count=in_game,
        unity3d_other_mod_count=other_mod,
        unity3d_missing_count=missing,
        unity3d_error=unity3d_error,
    )


def replace_mod_items(
    conn: sqlite3.Connection,
    zipmod_id: int,
    candidate: ZipmodCandidate,
    prepared: PreparedZipmodItems,
    now: str,
) -> tuple[int, int]:
    existing_rows = conn.execute(
        "SELECT id, zipmod_guid, kind, item_id FROM mod_items WHERE zipmod_id = ?",
        (zipmod_id,),
    ).fetchall()
    existing_by_key = {
        (str(row["zipmod_guid"] or ""), str(row["kind"] or ""), str(row["item_id"] or "")): int(row["id"])
        for row in existing_rows
    }
    remaining_ids = {int(row["id"]) for row in existing_rows}

    for item in prepared.items:
        key = (
            str(candidate.manifest.guid or ""),
            str(item.kind or ""),
            str(item.item_id or ""),
        )
        item_id = existing_by_key.get(key)
        values = (
            zipmod_id,
            candidate.manifest.guid,
            candidate.manifest.author,
            item.csv_path,
            item.item_id,
            item.kind,
            item.name,
            item.main_manifest,
            item.main_ab,
            item.main_data,
            item.tex_ab,
            item.thumb_ab,
            item.thumb_tex,
            item.thumbnail_cache_path,
            item.thumbnail_status,
            item.thumbnail_error,
            item.unity3d_status,
            item.unity3d_source,
            item.unity3d_error,
            item.parse_status,
            item.parse_error,
            now,
        )
        if item_id is not None:
            conn.execute(
                """
                UPDATE mod_items
                SET zipmod_id = ?, zipmod_guid = ?, zipmod_author = ?, csv_path = ?,
                    item_id = ?, kind = ?, name = ?, main_manifest = ?, main_ab = ?,
                    main_data = ?, tex_ab = ?, thumb_ab = ?, thumb_tex = ?, thumbnail_cache_path = ?,
                    thumbnail_status = ?, thumbnail_error = ?, unity3d_status = ?, unity3d_source = ?,
                    unity3d_error = ?, parse_status = ?, parse_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (*values, item_id),
            )
            remaining_ids.discard(item_id)
        else:
            cursor = conn.execute(
                """
                INSERT INTO mod_items (
                    zipmod_id, zipmod_guid, zipmod_author, csv_path, item_id, kind, name,
                    main_manifest, main_ab, main_data, tex_ab, thumb_ab, thumb_tex,
                    thumbnail_cache_path, thumbnail_status, thumbnail_error,
                    unity3d_status, unity3d_source, unity3d_error,
                    parse_status, parse_error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*values, now),
            )
            item_id = int(cursor.lastrowid)
            existing_by_key[key] = item_id

    if remaining_ids:
        placeholders = ", ".join("?" for _ in remaining_ids)
        conn.execute(
            f"DELETE FROM mod_items WHERE zipmod_id = ? AND id IN ({placeholders})",
            (zipmod_id, *sorted(remaining_ids)),
        )

    conn.execute(
        """
        UPDATE zipmods
        SET item_count = ?,
            unity3d_status = ?,
            unity3d_not_in_mod_count = ?,
            unity3d_in_mod_count = ?,
            unity3d_in_game_count = ?,
            unity3d_other_mod_count = ?,
            unity3d_missing_count = ?,
            unity3d_error = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            prepared.ok_count,
            prepared.unity3d_status,
            prepared.unity3d_not_in_mod_count,
            prepared.unity3d_in_mod_count,
            prepared.unity3d_in_game_count,
            prepared.unity3d_other_mod_count,
            prepared.unity3d_missing_count,
            prepared.unity3d_error,
            now,
            zipmod_id,
        ),
    )
    return prepared.ok_count, prepared.duplicate_items


def build_database(
    game_dir: Path,
    db_path: Path,
    thumbnail_dir: Path,
    progress_callback: Callable[[int, str], None] | None = None,
    mode: str = "incremental",
    worker_count: int | str | None = None,
) -> dict[str, object]:
    def report(value: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(value, message)

    game_dir = game_dir.resolve()
    db_path = db_path.resolve()
    thumbnail_dir = thumbnail_dir.resolve()
    build_started_at = perf_counter()
    phase_timings: dict[str, float] = {}
    db_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        now = utc_now()
        stats_started_at = now
        thumbnail_profile_run_id = uuid.uuid4().hex
        thumbnail_profile_log_path = begin_thumbnail_profile(
            {
                "event": "build_start",
                "run_id": thumbnail_profile_run_id,
                "mode": mode,
                "game_dir": str(game_dir),
                "thumbnail_dir": str(thumbnail_dir),
                "started_at": stats_started_at,
                "db_path": str(db_path),
                "profile_schema": 2,
            }
        )
        force_full = str(mode or "incremental").lower() == "full"
        report(1, "Scanning original game resource lists")
        builtin_started_at = perf_counter()
        builtin_stats = build_builtin_items_index(
            conn,
            game_dir,
            thumbnail_dir,
            progress_callback=report,
            mode=mode,
        )
        phase_timings["builtin_resource_index_ms"] = round(
            (perf_counter() - builtin_started_at) * 1000,
            2,
        )
        report(SCAN_PROGRESS, "Scanning mods/**/*.zipmod")
        zipmod_scan_started_at = perf_counter()
        existing_primary_paths = {
            str(row["guid"]): str(row["file_path"])
            for row in conn.execute(
                "SELECT guid, file_path FROM zipmods WHERE scan_status != 'stale'"
            )
            if str(row["guid"] or "") and not str(row["guid"]).startswith("__invalid__:")
        }
        existing_guids_by_path = {
            file_path: guid for guid, file_path in existing_primary_paths.items()
        }

        def report_scan_progress(stage: str, current: int, total: int) -> None:
            if stage == "discover":
                report(SCAN_PROGRESS, f"Discovered {current} zipmod files")
            elif stage == "discover_done":
                report(DISCOVER_END_PROGRESS, f"Found {current} zipmod files; reading manifests")
            elif stage == "manifest":
                report(
                    round(
                        calculate_progress(
                            current,
                            total,
                            DISCOVER_END_PROGRESS,
                            FOUND_PROGRESS,
                        ),
                        1,
                    ),
                    f"Read manifests {current}/{total} zipmod files",
                )

        candidates, changed_paths, reuse_stats = build_candidates_from_file_stats(
            conn,
            game_dir,
            force_full,
            report_scan_progress,
        )
        report(FOUND_PROGRESS, f"Found {len(candidates)} zipmod files")
        grouped, invalid = group_valid_candidates(candidates)
        existing_paths = get_existing_paths(conn)
        grouped_items = sorted(grouped.items())
        primary_by_guid = {
            guid: choose_primary(group, existing_paths)
            for guid, group in grouped_items
        }
        provider_index, provider_index_changed, changed_resource_keys = refresh_unity3d_provider_index(
            conn,
            candidates,
            utc_now(),
            force_full=force_full,
        )
        provider_affected_guids: set[str] = set()
        if provider_index_changed and changed_resource_keys:
            for row in conn.execute(
                """
                SELECT DISTINCT zipmod_guid, main_manifest, main_ab, tex_ab
                FROM mod_items
                WHERE parse_status = 'ok'
                """
            ):
                references = {
                    normalize_abdata_path(str(row["main_manifest"] or ""), str(row["main_ab"] or "")),
                    normalize_abdata_path("abdata", str(row["tex_ab"] or "")),
                }
                lookup_keys = {
                    key
                    for reference in references
                    if reference
                    for key in unity3d_provider_lookup_keys(reference)
                }
                if lookup_keys & changed_resource_keys:
                    guid = str(row["zipmod_guid"] or "").strip()
                    if guid:
                        provider_affected_guids.add(guid)
        phase_timings["zipmod_scan_ms"] = round(
            (perf_counter() - zipmod_scan_started_at) * 1000,
            2,
        )
        primary_changed_guids = {
            guid
            for guid, primary in primary_by_guid.items()
            if guid in existing_primary_paths
            and existing_primary_paths[guid] != str(primary.path)
        }
        replaced_item_guids = {
            guid
            for guid, primary in primary_by_guid.items()
            if force_full
            or str(primary.path) in changed_paths
            or guid in primary_changed_guids
            or guid in provider_affected_guids
        }
        current_guids = set(primary_by_guid)
        removed_guids = set(existing_primary_paths) - current_guids
        previous_guids_for_changed_paths = {
            existing_guids_by_path[path]
            for path in changed_paths
            if path in existing_guids_by_path
        }
        affected_mod_guids = (
            replaced_item_guids | removed_guids | previous_guids_for_changed_paths
        )
        actual_worker_count = choose_build_worker_count(worker_count)

        stats = {
            "zipmod_files": len(candidates),
            "invalid_zipmods": len(invalid),
            "primary_zipmods": 0,
            "duplicate_zipmods": 0,
            "duplicate_guid_count": 0,
            "mod_items": 0,
            "duplicate_items": 0,
            "stale_zipmods": 0,
            "reused_zipmods": reuse_stats["reused_zipmods"],
            "changed_zipmods": reuse_stats["changed_zipmods"],
            "thumbnail_profile_log": str(thumbnail_profile_log_path.resolve()),
            "thumbnail_profile_run_id": thumbnail_profile_run_id,
            "affected_mod_guids": sorted(affected_mod_guids, key=str.casefold),
            "affected_mod_guid_count": len(affected_mod_guids),
            "primary_changed_guid_count": len(primary_changed_guids),
            "worker_count": actual_worker_count,
            "worker_limit": get_build_worker_limit(),
            **builtin_stats,
        }
        report(
            PREPARE_START_PROGRESS,
            (
                f"Preparing {len(primary_by_guid)} primary zipmods with "
                f"{actual_worker_count} worker{'s' if actual_worker_count != 1 else ''}"
            ),
        )
        item_parse_started_at = perf_counter()
        prepared_by_guid: dict[str, PreparedZipmodItems] = {}
        primary_candidates = [
            primary_by_guid[guid]
            for guid, _group in grouped_items
            if guid in replaced_item_guids
        ]
        total_primary_candidates = len(primary_candidates)
        if actual_worker_count > 1:
            with ThreadPoolExecutor(max_workers=actual_worker_count) as executor:
                future_to_candidate = {
                    executor.submit(
                        prepare_mod_items,
                        game_dir,
                        candidate,
                        thumbnail_dir,
                        provider_index,
                    ): candidate
                    for candidate in primary_candidates
                }
                for completed_count, future in enumerate(as_completed(future_to_candidate), start=1):
                    candidate = future_to_candidate[future]
                    prepared_by_guid[candidate.manifest.guid] = future.result()
                    report(
                        round(
                            calculate_progress(
                                completed_count,
                                total_primary_candidates,
                                PREPARE_START_PROGRESS,
                                PREPARE_END_PROGRESS,
                            ),
                            1,
                        ),
                        (
                            f"Prepared {completed_count}/{total_primary_candidates} primary zipmods"
                        ),
                    )
        else:
            for completed_count, candidate in enumerate(primary_candidates, start=1):
                prepared_by_guid[candidate.manifest.guid] = prepare_mod_items(
                    game_dir,
                    candidate,
                    thumbnail_dir,
                    provider_index,
                )
                report(
                    round(
                        calculate_progress(
                            completed_count,
                            total_primary_candidates,
                            PREPARE_START_PROGRESS,
                            PREPARE_END_PROGRESS,
                        ),
                        1,
                    ),
                    f"Prepared {completed_count}/{total_primary_candidates} primary zipmods",
                )
        phase_timings["item_parse_ms"] = round(
            (perf_counter() - item_parse_started_at) * 1000,
            2,
        )
        report(WRITE_START_PROGRESS, "Prepared zipmod items; writing database records")

        database_write_started_at = perf_counter()
        with conn:
            conn.execute("DELETE FROM duplicate_zipmods")

            seen_guids: set[str] = set()
            for invalid_candidate in invalid:
                upsert_invalid_zipmod(conn, invalid_candidate, now)
                seen_guids.add(f"__invalid__:{invalid_candidate.path}")

            total_groups = max(len(grouped_items), 1)
            for index, (guid, group) in enumerate(grouped_items, start=1):
                primary = primary_by_guid[guid]
                duplicates = [candidate for candidate in group if candidate.path != primary.path]
                zipmod_id = upsert_zipmod(conn, primary, now)
                seen_guids.add(guid)
                stats["primary_zipmods"] += 1
                stats["duplicate_zipmods"] += replace_duplicate_records(
                    conn, zipmod_id, guid, duplicates, now
                )
                prepared = prepared_by_guid.get(guid)
                should_replace_items = (
                    guid in replaced_item_guids
                )
                if prepared is None and should_replace_items:
                    prepared = prepare_mod_items(
                        game_dir,
                        primary,
                        thumbnail_dir,
                        provider_index,
                    )
                if prepared is not None:
                    item_count, duplicate_items = replace_mod_items(
                        conn, zipmod_id, primary, prepared, now
                    )
                    stats["mod_items"] += item_count
                    stats["duplicate_items"] += duplicate_items
                else:
                    item_count = int(
                        conn.execute(
                            "SELECT COUNT(*) FROM mod_items WHERE zipmod_id = ? AND parse_status = 'ok'",
                            (zipmod_id,),
                        ).fetchone()[0]
                    )
                    stats["mod_items"] += item_count
                progress = round(
                    calculate_progress(
                        index,
                        total_groups,
                        WRITE_START_PROGRESS,
                        WRITE_END_PROGRESS,
                    ),
                    1,
                )
                report(
                    progress,
                    f"Indexed {index}/{total_groups} zipmods; {stats['mod_items']} items",
                )

            stats["stale_zipmods"] = remove_unseen_zipmods(conn, seen_guids)
            stats["duplicate_guid_count"] = int(
                conn.execute("SELECT COUNT(DISTINCT guid) FROM duplicate_zipmods").fetchone()[0]
            )
            set_database_metadata(conn, "last_built_at", now)
            report(FINALIZE_PROGRESS, "Finalizing database records")
        phase_timings["database_write_ms"] = round(
            (perf_counter() - database_write_started_at) * 1000,
            2,
        )
        stats["timings"] = {
            **phase_timings,
            "mod_database_total_ms": round((perf_counter() - build_started_at) * 1000, 2),
        }
        write_thumbnail_profile(
            {
                "event": "build_end",
                "run_id": thumbnail_profile_run_id,
                "mode": mode,
                "game_dir": str(game_dir),
                "thumbnail_dir": str(thumbnail_dir),
                "started_at": stats_started_at,
                "finished_at": utc_now(),
                "stats": stats,
            }
        )
        report(100, "Database rebuild completed")
        return stats
    finally:
        conn.close()


def index_single_zipmod(
    game_dir: Path,
    db_path: Path,
    thumbnail_dir: Path,
    zipmod_path: Path,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict[str, object]:
    """Index exactly one zipmod without scanning or pruning any other records."""

    def report(value: int, message: str) -> None:
        if progress_callback is not None:
            progress_callback(value, message)

    game_dir = game_dir.resolve()
    db_path = db_path.resolve()
    thumbnail_dir = thumbnail_dir.resolve()
    zipmod_path = zipmod_path.resolve()
    mods_dir = (game_dir / "mods").resolve()
    if not zipmod_path.is_file():
        raise ValueError(f"zipmod file not found: {zipmod_path}")
    try:
        relative_path = zipmod_path.relative_to(mods_dir).as_posix()
    except ValueError as error:
        raise ValueError("zipmod must be inside the selected game's mods directory") from error

    stat = zipmod_path.stat()
    candidate = ZipmodCandidate(
        manifest=read_manifest(zipmod_path),
        path=zipmod_path,
        relative_path=relative_path,
        file_size=stat.st_size,
        modified_at=timestamp_to_utc(stat.st_mtime),
    )
    if not candidate.manifest.guid:
        raise ValueError(
            f"cannot index zipmod without a valid manifest GUID: {zipmod_path.name}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        existing_zipmod = conn.execute(
            "SELECT id, file_path FROM zipmods WHERE guid = ?",
            (candidate.manifest.guid,),
        ).fetchone()
        report(
            10,
            (
                f"Updating existing GUID record: {candidate.manifest.guid}"
                if existing_zipmod is not None
                else f"Creating GUID record: {candidate.manifest.guid}"
            ),
        )
        # The single-mod task intentionally does not scan other zipmods or refresh
        # the archive-level provider index. Those operations belong to the full
        # database rebuild; this task only needs the target archive and the
        # existing GUID row in SQLite.
        prepared = prepare_mod_items(
            game_dir,
            candidate,
            thumbnail_dir,
            None,
        )
        report(70, f"Prepared {prepared.ok_count} items from {zipmod_path.name}")
        with conn:
            zipmod_id = upsert_zipmod(conn, candidate, now)
            item_count, duplicate_items = replace_mod_items(
                conn, zipmod_id, candidate, prepared, now
            )
            duplicate_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM duplicate_zipmods WHERE guid = ?",
                    (candidate.manifest.guid,),
                ).fetchone()[0]
            )
            set_database_metadata(conn, "last_built_at", now)
        report(100, f"Indexed target zipmod: {zipmod_path.name}")
        return {
            "zipmod_path": str(zipmod_path),
            "guid": candidate.manifest.guid,
            "primary_zipmods": 1,
            "mod_items": item_count,
            "duplicate_zipmods": duplicate_count,
            "duplicate_items": duplicate_items,
            "affected_mod_guids": [candidate.manifest.guid],
            "scanned_zipmods": 1,
        }
    finally:
        conn.close()


