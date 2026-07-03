from __future__ import annotations

import os
import sys
import importlib.util
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from time import time
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.card_database import build_card_database
from star_manager.services.card_library import DEFAULT_CARD_PREVIEW_DIR
from star_manager.services.mod_database import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    analyze_duplicate_zipmods,
    bulk_repair_zipmods_unity3d_from_game,
    build_database,
    cleanup_duplicate_zipmods,
    delete_mod_item,
    delete_primary_and_promote_duplicate,
    delete_zipmod,
    export_zipmods,
    import_zipmod_item_thumbnail,
    list_mod_items,
    update_zipmod_manifest_author,
)
from star_manager.services.mod_workflow import ExtractOptions, WorkflowReporter, extract_mods, search_ais_cards, sort_mods


@dataclass
class TaskState:
    id: str
    task_type: str
    status: str = "queued"
    progress: float = 0
    title: str = "Waiting"
    messages: list[str] = field(default_factory=list)
    error: str = ""
    data: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "title": self.title,
            "messages": list(self.messages),
            "error": self.error,
            "data": self.data,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskState] = {}
        self._lock = Lock()

    def create_task(self, task_type: str, payload: dict | None = None) -> TaskState:
        task = TaskState(
            id=uuid4().hex,
            task_type=task_type,
            title=task_type or "Unnamed task",
            messages=[f"Task submitted: {task_type}"],
        )
        with self._lock:
            self._tasks[task.id] = task
        Thread(target=run_task, args=(task, payload or {}), daemon=True).start()
        return task

    def get_task(self, task_id: str) -> TaskState | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [task.to_dict() for task in self._tasks.values()]


task_store = TaskStore()
SUPPORTED_TASK_TYPES = {
    "check_game_dir",
    "search_cards",
    "extract_mods",
    "sort_mods",
    "build_card_database",
    "build_mod_database",
    "bulk_export_zipmods",
    "bulk_organize_zipmods",
    "bulk_cleanup_duplicate_zipmods",
    "bulk_delete_zipmods",
    "bulk_repair_zipmods_unity3d",
    "bulk_update_zipmod_authors",
    "bulk_apply_item_thumbnail",
    "bulk_delete_error_items",
}

SUPPORTED_API_ROUTES = {
    "/library/cards",
    "/library/cards/detail",
    "/library/cards/image",
    "/library/cards/tree",
    "/cards/database",
    "/mods/database",
    "/mods/items",
    "/mods/items/filters",
    "/mods/thumbnails",
    "/mods/zipmods/<id>/diagnostics",
    "/mods/zipmods/<id>/repair-unity3d",
    "/mods/zipmods/<id>/update-author",
    "/mods/zipmods/<id>/cleanup-duplicates",
    "/mods/zipmods/<id>/delete",
    "/mods/items/<id>/import-thumbnail",
    "/mods/items/<id>/export-thumbnail",
    "/mods/items/<id>/delete",
    "/mods/zipmods",
}

BACKEND_REVISION = "item-thumbnail-tools-v2"


def create_health_payload() -> dict:
    runtime_modules = {
        name: importlib.util.find_spec(name) is not None
        for name in ("PIL", "UnityPy", "texture2ddecoder", "etcpak", "astc_encoder")
    }
    fallback_runtime_dir = Path(__file__).resolve().parents[2] / "runtime"
    configured_runtime_dir = Path(os.environ.get("STAR_MANAGER_RUNTIME_DIR", fallback_runtime_dir)).resolve()
    fmod_dll = Path(__file__).resolve().parent / "fmod_toolkit" / "libfmod" / "Windows" / "x64" / "fmod.dll"
    return {
        "ok": True,
        "message": "Python backend is ready.",
        "service": "Star_Manager",
        "transport": "http-api",
        "supported_task_types": sorted(SUPPORTED_TASK_TYPES),
        "supported_api_routes": sorted(SUPPORTED_API_ROUTES),
        "backend_revision": BACKEND_REVISION,
        "runtime_modules": runtime_modules,
        "runtime_dir": str(configured_runtime_dir),
        "fmod_dll_exists": fmod_dll.is_file(),
        "backend_source": str(Path(__file__).resolve()),
    }


def build_reporter(task: TaskState) -> WorkflowReporter:
    def set_progress(value):
        task.progress = round(max(0.0, min(100.0, float(value))), 1)
        task.updated_at = time()

    def add_message(text):
        task.messages.append(text)
        task.updated_at = time()

    def set_title(text):
        task.title = text
        task.updated_at = time()

    return WorkflowReporter(
        on_progress=set_progress,
        on_message=add_message,
        on_title=set_title,
        on_result=add_message,
    )


def parse_zipmod_ids(raw_ids) -> list[int]:
    ids_set: set[int] = set()
    for raw_id in raw_ids or []:
        try:
            zipmod_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if zipmod_id > 0:
            ids_set.add(zipmod_id)
    return sorted(ids_set)


def set_step_progress(task: TaskState, index: int, total: int, start: int = 5, end: int = 95) -> None:
    total = max(int(total or 1), 1)
    index = max(0, min(int(index or 0), total))
    task.progress = start + int(index / total * (end - start))
    task.updated_at = time()


def should_report_step(index: int, total: int) -> bool:
    return index == total or index % 10 == 0


def parse_item_ids(raw_ids) -> list[int]:
    ids_set: set[int] = set()
    for raw_id in raw_ids or []:
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if item_id > 0:
            ids_set.add(item_id)
    return sorted(ids_set)


def resolve_item_targets(item_ids: list[int]) -> list[dict]:
    if not item_ids:
        return []
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        targets: list[dict] = []
        for item_id in item_ids:
            row = conn.execute(
                """
                SELECT id, zipmod_guid, csv_path, item_id AS csv_item_id, kind, name
                FROM mod_items
                WHERE id = ?
                """,
                (int(item_id),),
            ).fetchone()
            if row is None:
                targets.append({"requested_id": int(item_id), "missing": True})
                continue
            targets.append(
                {
                    "requested_id": int(item_id),
                    "zipmod_guid": str(row["zipmod_guid"] or ""),
                    "csv_path": str(row["csv_path"] or ""),
                    "csv_item_id": str(row["csv_item_id"] or ""),
                    "kind": str(row["kind"] or ""),
                    "name": str(row["name"] or ""),
                }
            )
        return targets
    finally:
        conn.close()


def find_current_item_id(target: dict) -> int | None:
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT id
            FROM mod_items
            WHERE zipmod_guid = ?
              AND csv_path = ?
              AND item_id = ?
              AND kind = ?
            """,
            (
                target.get("zipmod_guid") or "",
                target.get("csv_path") or "",
                target.get("csv_item_id") or "",
                target.get("kind") or "",
            ),
        ).fetchone()
        if row is None:
            return None
        return int(row["id"])
    finally:
        conn.close()


def item_filter_payload(payload: dict) -> dict:
    return {
        "search": str(payload.get("search") or ""),
        "kind": str(payload.get("kind") or ""),
        "author": str(payload.get("author") or ""),
        "status": "error",
        "usage": str(payload.get("usage") or ""),
    }


def resolve_filtered_error_item_targets(payload: dict) -> tuple[list[dict], int]:
    filters = item_filter_payload(payload)
    first_page = list_mod_items(limit=1, **filters)
    total = int(first_page.get("total") or 0)
    if total <= 0:
        return [], 0

    result = list_mod_items(limit=1000, **filters)
    rows = result.get("rows") or []
    targets = [
        {
            "requested_id": int(row.get("id") or 0),
            "zipmod_guid": str(row.get("zipmod_guid") or ""),
            "csv_path": str(row.get("csv_path") or ""),
            "csv_item_id": str(row.get("item_id") or ""),
            "kind": str(row.get("kind") or ""),
            "name": str(row.get("name") or ""),
        }
        for row in rows
        if int(row.get("id") or 0) > 0
    ]
    return targets, total


def choose_safe_duplicate_cleanup_ids(analysis: dict) -> tuple[list[int], str]:
    candidates = analysis.get("candidates") or []
    primary = next((item for item in candidates if item.get("role") == "primary"), None)
    duplicates = [item for item in candidates if item.get("role") == "duplicate"]
    if not primary or not duplicates:
        return [], "No duplicate candidates found"
    if not primary.get("exists"):
        return [], "Primary zipmod file is missing"
    primary_reasons = set(primary.get("recommendation_reasons") or [])
    if int(primary.get("missing_item_count_vs_union") or 0) > 0:
        return [], "Duplicate file contains item records that the primary does not have"
    if "most_complete" not in primary_reasons:
        return [], "Primary zipmod is not the most complete candidate"
    if any(int(item.get("unique_item_count") or 0) > 0 for item in duplicates):
        return [], "At least one duplicate has unique item records"
    primary_score = int(primary.get("completeness_score") or 0)
    primary_is_latest = "latest_version" in primary_reasons or not primary.get("version")
    for item in duplicates:
        reasons = set(item.get("recommendation_reasons") or [])
        score = int(item.get("completeness_score") or 0)
        if score > primary_score:
            return [], "A duplicate has a better completeness score"
        if "latest_version" in reasons and not primary_is_latest:
            return [], "A duplicate appears to be a newer version"

    duplicate_ids = [
        int(item["duplicate_id"])
        for item in duplicates
        if item.get("duplicate_id")
    ]
    return duplicate_ids, ""


def choose_safe_duplicate_cleanup_action(analysis: dict) -> tuple[str, list[int], int | None, str]:
    candidates = analysis.get("candidates") or []
    recommendation = analysis.get("recommendation") or {}
    keep = recommendation.get("keep") or {}
    keep_role = keep.get("role")

    if keep_role == "primary":
        duplicate_ids, reason = choose_safe_duplicate_cleanup_ids(analysis)
        return ("cleanup", duplicate_ids, None, reason) if duplicate_ids else ("skip", [], None, reason)

    if keep_role != "duplicate":
        return "skip", [], None, "No recommended duplicate to promote"

    try:
        promote_duplicate_id = int(keep.get("duplicate_id") or 0)
    except (TypeError, ValueError):
        promote_duplicate_id = 0
    if promote_duplicate_id <= 0:
        return "skip", [], None, "Recommended duplicate is missing its duplicate id"

    primary = next((item for item in candidates if item.get("role") == "primary"), None)
    if not primary:
        return "skip", [], None, "Primary candidate not found"
    if not primary.get("exists"):
        return "skip", [], None, "Primary zipmod file is missing"
    if not recommendation.get("primary_should_delete") and primary.get("recommended_action") != "delete":
        return "skip", [], None, "Primary zipmod was not judged safe to delete"
    if int(primary.get("unique_item_count") or 0) > 0:
        return "skip", [], None, "Primary zipmod has unique item records"

    keep_candidate = next(
        (
            item
            for item in candidates
            if item.get("role") == "duplicate" and int(item.get("duplicate_id") or 0) == promote_duplicate_id
        ),
        None,
    )
    if not keep_candidate or not keep_candidate.get("exists"):
        return "skip", [], None, "Recommended duplicate file is missing"
    keep_reasons = set(keep_candidate.get("recommendation_reasons") or [])
    if "most_complete" not in keep_reasons:
        return "skip", [], None, "Recommended duplicate is not the most complete candidate"

    cleanup_ids = [
        int(item["duplicate_id"])
        for item in candidates
        if item.get("role") == "duplicate"
        and int(item.get("duplicate_id") or 0) != promote_duplicate_id
        and item.get("recommended_action") == "delete"
        and int(item.get("unique_item_count") or 0) == 0
    ]
    return "promote", cleanup_ids, promote_duplicate_id, ""


def run_task(task: TaskState, payload: dict) -> None:
    reporter = build_reporter(task)
    task.status = "running"
    task.updated_at = time()

    try:
        if task.task_type == "check_game_dir":
            game_dir = str(payload.get("game_dir") or "")
            task.title = "Check game directory"
            task.data = {"is_valid": is_hs2_game_dir(game_dir), "game_dir": game_dir}
        elif task.task_type == "search_cards":
            input_dir = str(payload.get("input_dir") or "")
            card_paths = search_ais_cards(input_dir, reporter)
            task.data = {"card_paths": sorted(card_paths), "card_count": len(card_paths)}
        elif task.task_type == "extract_mods":
            result = extract_mods(
                ExtractOptions(
                    game_dir=str(payload.get("game_dir") or ""),
                    input_dir=str(payload.get("input_dir") or ""),
                    output_dir=str(payload.get("output_dir") or ""),
                    card_paths=set(payload.get("card_paths") or []),
                    zipmod_extract_mode=str(payload.get("zipmod_extract_mode") or "copy"),
                ),
                reporter,
            )
            task.data = {
                "output_dir": result.output_dir,
                "card_paths": sorted(result.card_paths),
                "required_guid_count": len(result.required_guids),
                "matched_mod_count": len(result.matched_mod_paths),
                "database_matched_mod_count": len(result.database_matched_mod_paths),
                "missing_mods": sorted(result.missing_mods),
                "missing_abdata": sorted(result.missing_abdata),
            }
        elif task.task_type == "sort_mods":
            result = sort_mods(
                str(payload.get("input_dir") or ""),
                output_dir=str(payload.get("output_dir") or "") or None,
                delete_empty=bool(payload.get("delete_empty")),
                reporter=reporter,
            )
            task.data = {"output_dir": result.output_dir, "processed_count": result.processed_count}
        elif task.task_type == "build_mod_database":
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            thumbnail_dir = Path(str(payload.get("thumbnail_dir") or DEFAULT_THUMBNAIL_DIR))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            mode = str(payload.get("mode") or "incremental")
            if not is_hs2_game_dir(game_dir):
                raise ValueError("请先选择有效的 HS2 游戏目录，再创建模组数据库。")
            reporter.title("Build mod database")
            reporter.message(f"Building mod database from: {game_dir}")

            def report_database_progress(value: int, message: str) -> None:
                reporter.progress(value * 0.75, 100)
                reporter.message(message)

            stats = build_database(
                Path(game_dir),
                db_path,
                thumbnail_dir,
                report_database_progress,
                mode=mode,
            )
            reporter.message("Building character card database")

            def report_card_database_progress(value: int, message: str) -> None:
                reporter.progress(75 + value * 0.25, 100)
                reporter.message(message)

            card_stats = build_card_database(
                Path(game_dir),
                db_path,
                preview_dir,
                report_card_database_progress,
                mode=mode,
            )
            task.data = {
                "database_path": str(db_path.resolve()),
                "thumbnail_dir": str(thumbnail_dir.resolve()),
                "thumbnail_profile_log": stats.get("thumbnail_profile_log", ""),
                "preview_dir": str(preview_dir.resolve()),
                "mode": mode,
                "stats": stats,
                "card_stats": card_stats,
            }
            reporter.message(f"Database created: {db_path.resolve()}")
            reporter.message(f"Thumbnail cache: {thumbnail_dir.resolve()}")
            if stats.get("thumbnail_profile_log"):
                reporter.message(f"Thumbnail profile log: {stats['thumbnail_profile_log']}")
            reporter.message(f"Card preview cache: {preview_dir.resolve()}")
        elif task.task_type == "build_card_database":
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            mode = str(payload.get("mode") or "incremental")
            if not is_hs2_game_dir(game_dir):
                raise ValueError("请先选择有效的 HS2 游戏目录，再创建人物卡数据库。")
            reporter.title("Build character card database")
            reporter.message(f"Building character card database from: {game_dir}")

            def report_card_database_progress(value: int, message: str) -> None:
                reporter.progress(value, 100)
                reporter.message(message)

            stats = build_card_database(
                Path(game_dir),
                db_path,
                preview_dir,
                report_card_database_progress,
                mode=mode,
            )
            task.data = {
                "database_path": str(db_path.resolve()),
                "preview_dir": str(preview_dir.resolve()),
                "mode": mode,
                "stats": stats,
            }
            reporter.message(f"Character card database created: {db_path.resolve()}")
            reporter.message(f"Card preview cache: {preview_dir.resolve()}")
        elif task.task_type == "bulk_export_zipmods":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            mode = str(payload.get("mode") or "copy")
            target_dir = str(payload.get("target_dir") or "")
            task.title = "Export selected zipmods"
            reporter.message(f"Exporting {len(zipmod_ids)} zipmod(s)")

            def report_export_progress(index: int, total: int, zipmod_id: int) -> None:
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Exported {index}/{total} zipmods; latest id {zipmod_id}")

            result = export_zipmods(
                zipmod_ids,
                target_dir,
                mode,
                "tree",
                progress_callback=report_export_progress,
            )
            if not result.get("ok"):
                raise ValueError(str(result.get("error") or "Export failed"))
            task.data = result
        elif task.task_type == "bulk_organize_zipmods":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            target_dir = str(payload.get("target_dir") or "")
            task.title = "Organize selected zipmods"
            reporter.message(f"Organizing {len(zipmod_ids)} zipmod(s) by author")

            def report_organize_progress(index: int, total: int, zipmod_id: int) -> None:
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Organized {index}/{total} zipmods; latest id {zipmod_id}")

            result = export_zipmods(
                zipmod_ids,
                target_dir,
                "copy",
                "by_author",
                progress_callback=report_organize_progress,
            )
            if not result.get("ok"):
                raise ValueError(str(result.get("error") or "Organize failed"))
            task.data = result
        elif task.task_type == "bulk_repair_zipmods_unity3d":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            task.title = "Repair selected zipmods"
            reporter.message(f"Repairing unity3d files for {len(zipmod_ids)} zipmod(s)")

            def report_unity3d_repair_progress(stage: str, index: int, total: int, zipmod_id: int) -> None:
                if stage == "analyze":
                    set_step_progress(task, index, total, start=5, end=45)
                    if should_report_step(index, total):
                        reporter.message(f"Analyzed unity3d issues for {index}/{total} zipmods; latest id {zipmod_id}")
                    return
                set_step_progress(task, index, total, start=45, end=95)
                if should_report_step(index, total):
                    reporter.message(f"Repaired unity3d files for {index}/{total} zipmods; latest id {zipmod_id}")

            task.data = bulk_repair_zipmods_unity3d_from_game(
                zipmod_ids,
                progress_callback=report_unity3d_repair_progress,
            )
            reporter.message(str(task.data.get("message") or "unity3d repair completed"))
            if not task.data["ok"]:
                raise ValueError("unity3d repair failed")
        elif task.task_type == "bulk_cleanup_duplicate_zipmods":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            task.title = "Smart cleanup duplicate zipmods"
            reporter.message(f"Analyzing duplicate files for {len(zipmod_ids)} selected zipmod(s)")
            cleaned: list[dict] = []
            promoted: list[dict] = []
            skipped: list[dict] = []
            failures: list[dict] = []
            total = max(len(zipmod_ids), 1)
            for index, zipmod_id in enumerate(zipmod_ids, start=1):
                analysis = analyze_duplicate_zipmods(zipmod_id)
                if not analysis.get("ok"):
                    skipped.append({"id": zipmod_id, "reason": str(analysis.get("error") or "No duplicate zipmods found")})
                    set_step_progress(task, index, total)
                    continue

                action, duplicate_ids, promote_duplicate_id, reason = choose_safe_duplicate_cleanup_action(analysis)
                if action == "skip":
                    skipped.append({"id": zipmod_id, "guid": analysis.get("guid", ""), "reason": reason or "No safe cleanup target"})
                    set_step_progress(task, index, total)
                    continue

                if action == "promote":
                    result = delete_primary_and_promote_duplicate(zipmod_id, promote_duplicate_id)
                    if result.get("ok") and duplicate_ids:
                        promoted_zipmod_id = int(result.get("promoted_zipmod_id") or zipmod_id)
                        cleanup_result = cleanup_duplicate_zipmods(promoted_zipmod_id, duplicate_ids=duplicate_ids)
                        result = {
                            **result,
                            "cleanup_after_promote": cleanup_result,
                            "cleared_ids": cleanup_result.get("cleared_ids") if cleanup_result.get("ok") else [],
                        }
                    if result.get("ok"):
                        promoted.append({"id": zipmod_id, **result})
                    else:
                        failures.append({"id": zipmod_id, "guid": analysis.get("guid", ""), "error": str(result.get("error") or "Promote duplicate failed")})
                    set_step_progress(task, index, total)
                    if should_report_step(index, total):
                        reporter.message(f"Analyzed {index}/{total} zipmods; cleaned {len(cleaned)}, promoted {len(promoted)}, skipped {len(skipped)}")
                    continue

                result = cleanup_duplicate_zipmods(zipmod_id, duplicate_ids=duplicate_ids)
                if result.get("ok"):
                    cleaned.append({"id": zipmod_id, **result})
                else:
                    failures.append({"id": zipmod_id, "guid": analysis.get("guid", ""), "error": str(result.get("error") or "Cleanup failed")})

                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Analyzed {index}/{total} zipmods; cleaned {len(cleaned)}, promoted {len(promoted)}, skipped {len(skipped)}")

            task.data = {
                "ok": len(cleaned) > 0 or len(promoted) > 0 or len(skipped) > 0,
                "selected_count": len(zipmod_ids),
                "cleaned_count": len(cleaned),
                "promoted_count": len(promoted),
                "skipped_count": len(skipped),
                "failure_count": len(failures),
                "cleaned_duplicate_count": (
                    sum(len(item.get("cleared_ids") or []) for item in cleaned)
                    + sum(1 + len(item.get("cleared_ids") or []) for item in promoted)
                ),
                "cleaned": cleaned,
                "promoted": promoted,
                "skipped": skipped,
                "failures": failures,
                "message": f"Cleaned duplicate files for {len(cleaned)} zipmod(s), promoted {len(promoted)}, skipped {len(skipped)}, failed {len(failures)}",
            }
            if not task.data["ok"]:
                raise ValueError("Duplicate cleanup failed")
        elif task.task_type == "bulk_delete_zipmods":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            task.title = "Delete selected zipmods"
            reporter.message(f"Deleting {len(zipmod_ids)} selected zipmod(s)")
            deleted: list[dict] = []
            failures: list[dict] = []
            total = max(len(zipmod_ids), 1)
            for index, zipmod_id in enumerate(zipmod_ids, start=1):
                result = delete_zipmod(zipmod_id)
                if result.get("ok"):
                    deleted.append({"id": zipmod_id, **result})
                else:
                    failures.append({"id": zipmod_id, "error": str(result.get("error") or "Delete failed")})
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Deleted {index}/{total} zipmods; failed {len(failures)}")
            task.data = {
                "ok": len(deleted) > 0 or len(failures) == 0,
                "selected_count": len(zipmod_ids),
                "deleted_count": len(deleted),
                "failure_count": len(failures),
                "deleted": deleted,
                "failures": failures,
                "message": f"Deleted {len(deleted)} zipmod(s), failed {len(failures)}",
            }
            if not task.data["ok"]:
                raise ValueError("Bulk delete failed")
        elif task.task_type == "bulk_update_zipmod_authors":
            zipmod_ids = parse_zipmod_ids(payload.get("zipmod_ids") or [])
            author = str(payload.get("author") or "")
            task.title = "Update selected zipmod authors"
            reporter.message(f"Updating author for {len(zipmod_ids)} zipmod(s)")
            updated: list[dict] = []
            failures: list[dict] = []
            total = max(len(zipmod_ids), 1)
            for index, zipmod_id in enumerate(zipmod_ids, start=1):
                result = update_zipmod_manifest_author(zipmod_id, author)
                if result.get("ok"):
                    updated.append({"id": zipmod_id, **result})
                else:
                    failures.append({"id": zipmod_id, "error": str(result.get("error") or "Author update failed")})
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Updated {index}/{total} zipmod authors")
            task.data = {
                "ok": len(updated) > 0 or len(failures) == 0,
                "selected_count": len(zipmod_ids),
                "updated_count": len(updated),
                "failure_count": len(failures),
                "updated": updated,
                "failures": failures,
                "author": author,
                "message": f"Updated {len(updated)} zipmod author(s), failed {len(failures)}",
            }
            if not task.data["ok"]:
                raise ValueError("Author update failed")
        elif task.task_type == "bulk_apply_item_thumbnail":
            source_image = Path(str(payload.get("source_image_path") or "")).resolve()
            target_item_ids = parse_item_ids(payload.get("target_item_ids") or [])
            if not source_image.is_file() or source_image.suffix.lower() != ".png":
                raise ValueError("Source item thumbnail is not ready")
            task.title = "Apply item thumbnail"
            reporter.message(f"Applying thumbnail to {len(target_item_ids)} item(s)")
            target_items = resolve_item_targets(target_item_ids)
            imported: list[dict] = []
            failures: list[dict] = []
            total = max(len(target_items), 1)
            for index, target in enumerate(target_items, start=1):
                requested_id = int(target.get("requested_id") or 0)
                if target.get("missing"):
                    failures.append({"id": requested_id, "error": "Item not found"})
                    set_step_progress(task, index, total)
                    continue
                item_id = find_current_item_id(target)
                if item_id is None:
                    failures.append(
                        {
                            "id": requested_id,
                            "error": f"Item no longer exists: {target.get('name') or requested_id}",
                        }
                    )
                    set_step_progress(task, index, total)
                    continue
                result = import_zipmod_item_thumbnail(item_id, str(source_image))
                if result.get("ok"):
                    imported.append({"id": item_id, "requested_id": requested_id, **result})
                else:
                    failures.append({"id": requested_id, "error": str(result.get("error") or "Import failed")})
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Applied thumbnail to {index}/{total} items")
            task.data = {
                "ok": len(imported) > 0 or len(failures) == 0,
                "selected_count": len(target_item_ids),
                "imported_count": len(imported),
                "failure_count": len(failures),
                "source_image_path": str(source_image),
                "imported": imported,
                "failures": failures,
                "message": f"Applied thumbnail to {len(imported)} item(s), failed {len(failures)}",
            }
            if not task.data["ok"]:
                raise ValueError("Thumbnail apply failed")
        elif task.task_type == "bulk_delete_error_items":
            targets, total_count = resolve_filtered_error_item_targets(payload)
            if total_count > 1000:
                raise ValueError("Refine the filters before deleting more than 1000 error items at once")
            task.title = "Delete filtered error items"
            reporter.message(f"Deleting {len(targets)} filtered error item(s)")
            deleted: list[dict] = []
            failures: list[dict] = []
            total = max(len(targets), 1)
            for index, target in enumerate(targets, start=1):
                requested_id = int(target.get("requested_id") or 0)
                item_id = find_current_item_id(target)
                if item_id is None:
                    failures.append({
                        "id": requested_id,
                        "error": f"Item no longer exists: {target.get('name') or requested_id}",
                    })
                    set_step_progress(task, index, total)
                    continue
                result = delete_mod_item(item_id)
                if result.get("ok"):
                    deleted.append({"id": item_id, "requested_id": requested_id, **result})
                else:
                    failures.append({"id": requested_id, "error": str(result.get("error") or "Delete failed")})
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"Deleted {index}/{total} error items; failed {len(failures)}")
            task.data = {
                "ok": len(deleted) > 0 or len(failures) == 0,
                "selected_count": len(targets),
                "deleted_count": len(deleted),
                "failure_count": len(failures),
                "deleted": deleted,
                "failures": failures,
                "filters": item_filter_payload(payload),
                "message": f"Deleted {len(deleted)} error item(s), failed {len(failures)}",
            }
            if not task.data["ok"]:
                raise ValueError("Bulk error item delete failed")
        else:
            raise ValueError(f"Unknown task type: {task.task_type}")

        task.progress = 100
        task.status = "completed"
    except Exception as error:
        task.error = str(error)
        task.status = "failed"
        task.messages.append(f"[Error] {error}")
    finally:
        task.updated_at = time()
