from __future__ import annotations

import os
import re
import sys
import importlib.util
import sqlite3
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from time import perf_counter, sleep, time
from uuid import uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.core.card_parser import extract_png_extra_data, read_card_marker
from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.achievements import record_achievement_event
from star_manager.services.card_database import build_card_database
from star_manager.services.card_library import (
    DEFAULT_CARD_PREVIEW_DIR,
    add_character_card_tags,
    delete_character_card,
    export_character_dependency_package,
    get_card_root,
    move_character_card,
)
from star_manager.services.mod_database import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    analyze_duplicate_zipmods,
    bulk_repair_zipmods_unity3d_from_game,
    build_database,
    index_single_zipmod,
    cleanup_duplicate_zipmods,
    delete_mod_item,
    delete_primary_and_promote_duplicate,
    delete_zipmod,
    export_zipmods,
    import_zipmod_item_thumbnail,
    list_mod_items,
    update_zipmod_manifest_author,
)
from star_manager.services.mod_database_assets import (
    find_zip_member,
    inspect_zipmod_archive,
    iter_zip_csv_items,
    normalize_zip_path,
    read_manifest,
    unity3d_reference_paths,
)
from star_manager.services.remote_mod_completion import RemoteDownloadCancelled, download_card_missing_mods
from star_manager.services.mod_database_core import init_db
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
    pause_requested: bool = False
    cancel_requested: bool = False
    phase: str = ""
    phase_progress: float = 0
    download_speed_bps: float = 0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    current_file: str = ""
    phase_message: str = ""
    finished_at: float = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "paused": self.status == "paused",
            "progress": self.progress,
            "title": self.title,
            "messages": list(self.messages),
            "error": self.error,
            "data": self.data,
            "phase": self.phase,
            "phase_progress": self.phase_progress,
            "download_speed_bps": self.download_speed_bps,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "current_file": self.current_file,
            "phase_message": self.phase_message,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finished_at": self.finished_at,
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

    def control_task(self, task_id: str, action: str) -> TaskState | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if task.task_type != "download_card_missing_mods":
                raise ValueError("Only remote mod download tasks can be controlled.")
            if task.status in {"completed", "failed", "cancelled"}:
                raise ValueError("This download task has already finished.")
            if action == "pause":
                task.pause_requested = True
                task.status = "paused"
                task.download_speed_bps = 0
                task.messages.append("Download paused")
            elif action == "resume":
                if task.cancel_requested:
                    raise ValueError("This download task is being cancelled.")
                task.pause_requested = False
                task.status = "running"
                task.messages.append("Download resumed")
            elif action == "cancel":
                task.cancel_requested = True
                task.pause_requested = False
                task.download_speed_bps = 0
                task.phase_message = "正在取消下载"
                task.messages.append("Download cancellation requested")
            else:
                raise ValueError("Unsupported task control action.")
            task.updated_at = time()
            return task


task_store = TaskStore()
SUPPORTED_TASK_TYPES = {
    "check_game_dir",
    "extract_mods",
    "sort_mods",
    "build_card_database",
    "build_mod_database",
    "index_single_zipmod",
    "download_card_missing_mods",
    "import_external_zipmods",
    "export_character_dependency_package",
    "bulk_export_zipmods",
    "bulk_organize_zipmods",
    "organize_all_zipmods_by_author",
    "bulk_cleanup_duplicate_zipmods",
    "bulk_delete_zipmods",
    "bulk_delete_character_cards",
    "bulk_add_character_card_tags",
    "bulk_move_character_cards",
    "bulk_repair_zipmods_unity3d",
    "bulk_update_zipmod_authors",
    "bulk_apply_item_thumbnail",
    "bulk_delete_error_items",
}

SUPPORTED_API_ROUTES = {
    "/library/cards",
    "/trash",
    "/trash/empty",
    "/trash/<kind>/<id>/restore",
    "/trash/<kind>/<id>/delete",
    "/library/cards/detail",
    "/library/cards/image",
    "/library/cards/replace-cover",
    "/library/cards/export-coordinate",
    "/library/cards/set-navi",
    "/library/cards/delete",
    "/library/cards/set-favorite",
    "/library/cards/set-rating",
    "/library/cards/set-tags",
    "/library/cards/tags",
    "/library/cards/update-profile",
    "/library/cards/tree",
    "/library/cards/changes",
    "/library/cards/folders/create",
    "/library/cards/folders/rename",
    "/library/clothes/tree",
    "/library/clothes",
    "/library/clothes/detail",
    "/library/clothes/image",
    "/library/scene/tree",
    "/library/scene",
    "/library/scene/detail",
    "/library/scene/image",
    "/library/scene/missing-mods",
    "/cards/database",
    "/plugins",
    "/plugins/status",
    "/plugins/toggle",
    "/game/special-settings",
    "/game/special-settings/toggle",
    "/tools/sims4/package-fbx",
    "/workbench/unity3d/assets",
    "/workbench/unity3d/duplicate",
    "/workbench/unity3d/import-texture",
    "/workbench/unity3d/model-preview",
    "/workbench/template-items",
    "/mods/database",
    "/mods/items",
    "/mods/items/filters",
    "/mods/zipmods/authors",
    "/mods/thumbnails",
    "/mods/models/<file.glb>",
    "/mods/zipmods/<id>/diagnostics",
    "/mods/zipmods/<id>/repair-unity3d",
    "/mods/zipmods/<id>/update-author",
    "/mods/zipmods/<id>/cleanup-duplicates",
    "/mods/zipmods/<id>/delete",
    "/mods/items/<id>/import-thumbnail",
    "/mods/items/<id>/export-thumbnail",
    "/mods/items/<id>/open-unity3d",
    "/mods/items/<id>/export-unity3d",
    "/mods/items/<id>/model-preview",
    "/mods/items/<id>/delete",
    "/mods/zipmods",
    "/library/cards/missing-mods",
    "/game-item-probe/status",
    "/game-item-probe/current",
    "/game-item-probe/context",
    "/game-item-probe/command",
    "/game-item-probe/apply",
    "/game-card-loader/load",
    "/tasks/<task_id>/control",
}

BACKEND_REVISION = "sims4-workbench-tpose-mesh-v2-unity3d-preprocess-v1-game-item-probe-v2-hair-slots-card-load-v1-unity3d-export-v1-trash-v2-card-single-delete-v1-scene-remote-completion-v1-weighted-database-progress-v1"

# The database task's top-bar progress is a weighted estimate of the phase
# timings captured in the UI reference run. The mod database service reports
# its own 0..100 phase scale, so the bridge maps that scale into the first four
# weighted phases before the character-card database takes the remaining share.
DATABASE_PHASE_DURATIONS_SECONDS = {
    "builtin_resource_index": 2.5,
    "zipmod_scan": 70.6,
    "item_parse": 472.9,
    "database_write": 1.1,
    "character_card_database": 65.9,
}
DATABASE_TOTAL_DURATION_SECONDS = sum(DATABASE_PHASE_DURATIONS_SECONDS.values())
DATABASE_PHASE_ENDS = {}
_database_progress_total = 0.0
for _database_phase, _database_duration in DATABASE_PHASE_DURATIONS_SECONDS.items():
    _database_progress_total += _database_duration
    DATABASE_PHASE_ENDS[_database_phase] = (
        _database_progress_total / DATABASE_TOTAL_DURATION_SECONDS * 100
    )
DATABASE_MOD_DATABASE_PROGRESS_END = DATABASE_PHASE_ENDS["database_write"]


def weighted_mod_database_progress(value: float) -> float:
    """Map the mod-database service progress to the screenshot's time weights."""
    raw_progress = max(0.0, min(100.0, float(value or 0)))
    phase_ranges = (
        (0.0, 5.0, 0.0, DATABASE_PHASE_ENDS["builtin_resource_index"]),
        (
            5.0,
            12.0,
            DATABASE_PHASE_ENDS["builtin_resource_index"],
            DATABASE_PHASE_ENDS["zipmod_scan"],
        ),
        (
            12.0,
            15.0,
            DATABASE_PHASE_ENDS["zipmod_scan"],
            DATABASE_PHASE_ENDS["zipmod_scan"],
        ),
        (
            15.0,
            70.0,
            DATABASE_PHASE_ENDS["zipmod_scan"],
            DATABASE_PHASE_ENDS["item_parse"],
        ),
        (
            70.0,
            72.0,
            DATABASE_PHASE_ENDS["item_parse"],
            DATABASE_PHASE_ENDS["item_parse"],
        ),
        (
            72.0,
            100.0,
            DATABASE_PHASE_ENDS["item_parse"],
            DATABASE_PHASE_ENDS["database_write"],
        ),
    )
    for raw_start, raw_end, weighted_start, weighted_end in phase_ranges:
        if raw_progress <= raw_end:
            fraction = (raw_progress - raw_start) / (raw_end - raw_start)
            return weighted_start + fraction * (weighted_end - weighted_start)
    return DATABASE_MOD_DATABASE_PROGRESS_END


def weighted_character_card_database_progress(value: float) -> float:
    """Map character-card progress to the final weighted database phase."""
    raw_progress = max(0.0, min(100.0, float(value or 0)))
    return DATABASE_MOD_DATABASE_PROGRESS_END + raw_progress / 100 * (
        100 - DATABASE_MOD_DATABASE_PROGRESS_END
    )


def _safe_author_directory(author: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(author or "").strip())
    name = name.rstrip(" .") or "未知作者"
    if name.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }:
        name = f"_{name}"
    return name[:120].rstrip(" .") or "未知作者"


def organize_all_zipmods_by_author(game_dir: str, reporter: WorkflowReporter) -> dict:
    game_root = Path(game_dir).expanduser().resolve()
    if not is_hs2_game_dir(game_root):
        raise ValueError("请先选择有效的 HS2 游戏目录。")

    mods_root = (game_root / "mods").resolve()
    zipmod_paths = sorted(
        (path.resolve() for path in mods_root.rglob("*.zipmod") if path.is_file()),
        key=lambda path: str(path).lower(),
    )
    moved: list[dict] = []
    unchanged: list[dict] = []
    failures: list[dict] = []
    removed_empty_dirs: list[str] = []
    total = max(len(zipmod_paths), 1)

    reporter.title("按作者整理全部模组")
    reporter.message(f"找到 {len(zipmod_paths)} 个 zipmod，开始按作者整理")
    for index, source in enumerate(zipmod_paths, start=1):
        try:
            manifest = read_manifest(source)
            author_dir = _safe_author_directory(manifest.author)
            target_dir = (mods_root / author_dir).resolve()
            if target_dir != mods_root and mods_root not in target_dir.parents:
                raise ValueError("作者目录超出 mods 范围")
            target = target_dir / source.name
            if source.parent == target_dir:
                unchanged.append({"source": str(source), "author": manifest.author or "未知作者"})
            else:
                counter = 1
                while target.exists():
                    target = target_dir / f"{source.stem}_{counter}{source.suffix}"
                    counter += 1
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                moved.append({
                    "source": str(source),
                    "target": str(target),
                    "author": manifest.author or "未知作者",
                })
        except (OSError, ValueError) as exc:
            failures.append({"path": str(source), "error": str(exc)})
        finally:
            reporter.progress(index * 70, total)
            if should_report_step(index, total):
                reporter.message(f"已处理 {index}/{len(zipmod_paths)} 个 zipmod")

    for directory in sorted(
        (path for path in mods_root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
            removed_empty_dirs.append(str(directory))
        except OSError:
            pass
    if removed_empty_dirs:
        reporter.message(f"已删除 {len(removed_empty_dirs)} 个空目录")

    return {
        "ok": len(failures) == 0,
        "game_dir": str(game_root),
        "mods_dir": str(mods_root),
        "scanned_count": len(zipmod_paths),
        "moved_count": len(moved),
        "unchanged_count": len(unchanged),
        "removed_empty_dir_count": len(removed_empty_dirs),
        "failure_count": len(failures),
        "moved": moved,
        "unchanged": unchanged,
        "removed_empty_dirs": removed_empty_dirs,
        "failures": failures,
    }


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


def format_elapsed_seconds(duration_ms: object) -> str:
    try:
        seconds = max(0.0, float(duration_ms or 0)) / 1000
    except (TypeError, ValueError):
        seconds = 0.0
    return f"{seconds:.1f} 秒"


def wait_for_task_resume(task: TaskState) -> None:
    if task.cancel_requested:
        raise RemoteDownloadCancelled("Download cancelled by user.")
    while task.pause_requested:
        if task.cancel_requested:
            raise RemoteDownloadCancelled("Download cancelled by user.")
        task.status = "paused"
        task.updated_at = time()
        sleep(0.1)
    if task.status == "paused":
        task.status = "running"
        task.updated_at = time()


def should_report_step(index: int, total: int) -> bool:
    return index == total or index % 10 == 0


def rebuild_affected_character_cards(
    game_dir: str,
    db_path: Path,
    preview_dir: Path,
    affected_mod_guids,
    reporter: WorkflowReporter,
    worker_count: int | str | None = None,
) -> dict | None:
    guids = sorted(
        {
            str(guid or "").strip()
            for guid in affected_mod_guids or []
            if str(guid or "").strip()
        },
        key=str.casefold,
    )
    if not guids:
        return None

    reporter.message(
        f"Refreshing character card dependencies for {len(guids)} changed mod(s)"
    )
    return build_card_database(
        Path(game_dir),
        db_path,
        preview_dir,
        lambda _value, message: reporter.message(message),
        mode="incremental",
        affected_mod_guids=guids,
        worker_count=worker_count,
    )


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


def _unique_import_target(
    import_dir: Path,
    source_path: Path,
    used_targets: set[Path],
    *,
    suffix: str | None = None,
) -> Path:
    stem = source_path.stem
    target_suffix = suffix if suffix is not None else (source_path.suffix or ".zipmod")
    target_name = f"{stem}{target_suffix}" if suffix is not None else source_path.name
    target = import_dir / target_name
    index = 1
    while target.exists() or target in used_targets:
        target = import_dir / f"{stem} ({index}){target_suffix}"
        index += 1
    used_targets.add(target)
    return target


def _ais_card_marker(source_path: Path) -> str | None:
    try:
        return read_card_marker(extract_png_extra_data(source_path))
    except Exception:
        return None


def _database_worker_options(payload: dict) -> dict[str, object]:
    """Forward the configured database worker count when a task supplies it."""
    if "worker_count" not in payload:
        return {}
    return {"worker_count": payload.get("worker_count")}


def _duplicate_ids_for_guid(guid: str, db_path: Path) -> list[int]:
    resolved = db_path.resolve()
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        return [
            int(row["id"])
            for row in conn.execute(
                "SELECT id FROM duplicate_zipmods WHERE guid = ? ORDER BY id",
                (guid,),
            ).fetchall()
        ]
    finally:
        conn.close()


def _primary_id_for_guid(guid: str, db_path: Path) -> int | None:
    resolved = db_path.resolve()
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        row = conn.execute("SELECT id FROM zipmods WHERE guid = ?", (guid,)).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()


def _iter_external_abdata_roots(source_dir: Path) -> list[Path]:
    roots: list[Path] = []
    if source_dir.name.casefold() == "abdata" and source_dir.is_dir():
        roots.append(source_dir)
    roots.extend(path for path in source_dir.rglob("abdata") if path.is_dir())

    unique: dict[str, Path] = {}
    for root in roots:
        try:
            unique[str(root.resolve()).casefold()] = root.resolve()
        except OSError:
            continue
    return sorted(unique.values(), key=lambda item: str(item).casefold())


def _external_unity3d_index(source_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for abdata_root in _iter_external_abdata_roots(source_dir):
        for path in sorted(abdata_root.rglob("*.unity3d")):
            if not path.is_file():
                continue
            try:
                relative = path.resolve().relative_to(abdata_root.resolve()).as_posix()
            except ValueError:
                continue
            key = normalize_zip_path(f"abdata/{relative}").casefold()
            index.setdefault(key, path.resolve())
    return index


def _repair_imported_zipmod_unity3d(zipmod_path: Path, source_dir: Path) -> dict:
    source_index = _external_unity3d_index(source_dir)
    if not source_index:
        return {"repaired_count": 0, "moved": [], "missing": [], "source_count": 0}

    referenced: list[str] = []
    for item in iter_zip_csv_items(zipmod_path):
        if item.parse_status != "ok":
            continue
        referenced.extend(unity3d_reference_paths(item))

    wanted: list[str] = []
    seen: set[str] = set()
    for reference in referenced:
        normalized = normalize_zip_path(reference)
        if not normalized:
            continue
        key = normalized.casefold()
        if key not in seen:
            seen.add(key)
            wanted.append(normalized)

    if not wanted:
        return {"repaired_count": 0, "moved": [], "missing": [], "source_count": len(source_index)}

    missing: list[str] = []
    moves: list[tuple[str, Path]] = []
    with zipfile.ZipFile(zipmod_path, "r") as zf:
        for arcname in wanted:
            if find_zip_member(zf, arcname) is not None:
                continue
            source_path = source_index.get(arcname.casefold())
            if source_path is None or not source_path.is_file():
                missing.append(arcname)
                continue
            moves.append((arcname, source_path))

    moved: list[dict] = []
    if moves:
        with zipfile.ZipFile(zipmod_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            for arcname, source_path in moves:
                zf.write(source_path, arcname)
                moved.append({"path": arcname, "source_path": str(source_path)})
        for _arcname, source_path in moves:
            try:
                source_path.unlink()
            except OSError:
                pass

    return {
        "repaired_count": len(moved),
        "moved": moved,
        "missing": missing,
        "source_count": len(source_index),
    }


def _import_external_zipmods(task: TaskState, payload: dict, reporter: WorkflowReporter) -> dict:
    game_dir = Path(str(payload.get("game_dir") or "")).resolve()
    source_dir = Path(str(payload.get("source_dir") or payload.get("input_dir") or "")).resolve()
    db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH)).resolve()
    thumbnail_dir = Path(str(payload.get("thumbnail_dir") or DEFAULT_THUMBNAIL_DIR)).resolve()
    preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR)).resolve()

    if not is_hs2_game_dir(str(game_dir)):
        raise ValueError("Please select a valid HS2 game directory before importing zipmods.")
    if not source_dir.is_dir():
        raise ValueError(f"Import folder not found: {source_dir}")
    archive_paths = sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".zipmod", ".zip"}
    )
    zipmod_paths = [path for path in archive_paths if path.suffix.casefold() == ".zipmod"]
    zip_paths = [path for path in archive_paths if path.suffix.casefold() == ".zip"]
    invalid: list[dict] = []
    recognized_zip_paths: list[Path] = []
    for source_path in zip_paths:
        is_zipmod, error = inspect_zipmod_archive(source_path)
        if is_zipmod:
            recognized_zip_paths.append(source_path)
        else:
            invalid.append(
                {
                    "source_path": str(source_path),
                    "status": "invalid_zipmod_structure",
                    "error": error,
                }
            )
    recognized_zip_path_set = set(recognized_zip_paths)
    candidate_paths = [
        path
        for path in archive_paths
        if path.suffix.casefold() == ".zipmod" or path in recognized_zip_path_set
    ]
    png_paths = sorted(path for path in source_dir.rglob("*.png") if path.is_file())
    if candidate_paths and not db_path.exists():
        raise ValueError("Mod database not found. Rebuild the database before importing external zipmods.")

    task.title = "Import external zipmods"
    reporter.message(f"Scanning external folder: {source_dir}")
    reporter.message(
        f"Found {len(zipmod_paths)} zipmod file(s); recognized {len(recognized_zip_paths)} zip archive(s) as zipmod"
    )
    card_import_dir = get_card_root(str(game_dir)) / "female" / "imported"
    card_import_dir.mkdir(parents=True, exist_ok=True)
    coordinate_import_dir = game_dir / "UserData" / "coordinate" / "female" / "imoprted"
    coordinate_import_dir.mkdir(parents=True, exist_ok=True)
    import_dir = game_dir / "mods" / "Imported"
    import_dir.mkdir(parents=True, exist_ok=True)
    used_targets: set[Path] = set()
    used_card_targets: set[Path] = set()
    used_coordinate_targets: set[Path] = set()
    copied: list[dict] = []
    unity3d_repaired: list[dict] = []
    imported_cards: list[dict] = []
    imported_coordinates: list[dict] = []
    non_card_pngs: list[str] = []
    failures: list[dict] = []

    card_total = max(len(png_paths), 1)
    for index, source_path in enumerate(png_paths, start=1):
        try:
            marker = _ais_card_marker(source_path)
            if marker == "【AIS_Clothes】":
                target_path = _unique_import_target(coordinate_import_dir, source_path, used_coordinate_targets)
                shutil.copy2(source_path, target_path)
                imported_coordinates.append({"source_path": str(source_path), "target_path": str(target_path)})
            elif marker == "【AIS_Chara】":
                target_path = _unique_import_target(card_import_dir, source_path, used_card_targets)
                shutil.copy2(source_path, target_path)
                imported_cards.append({"source_path": str(source_path), "target_path": str(target_path)})
            else:
                non_card_pngs.append(str(source_path))
                set_step_progress(task, index, card_total, start=2, end=14)
                continue
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            failures.append({"source_path": str(source_path), "error": str(exc)})
        set_step_progress(task, index, card_total, start=2, end=14)
        if should_report_step(index, card_total):
            reporter.message(
                f"Imported {len(imported_cards)} character and {len(imported_coordinates)} clothes card PNG files"
            )

    total = max(len(candidate_paths), 1)
    for index, source_path in enumerate(candidate_paths, start=1):
        manifest = read_manifest(source_path)
        if manifest.scan_status != "ok" or not manifest.guid:
            invalid.append(
                {
                    "source_path": str(source_path),
                    "status": manifest.scan_status,
                    "error": manifest.scan_error,
                }
            )
            set_step_progress(task, index, total, start=14, end=25)
            continue
        try:
            is_zip_source = source_path.suffix.casefold() == ".zip"
            target_path = _unique_import_target(
                import_dir,
                source_path,
                used_targets,
                suffix=".zipmod" if is_zip_source else None,
            )
            shutil.copy2(source_path, target_path)
            repair_result = _repair_imported_zipmod_unity3d(target_path, source_dir)
            copied_item = {
                "guid": manifest.guid,
                "source_path": str(source_path),
                "target_path": str(target_path),
                "source_extension": source_path.suffix.casefold(),
            }
            if repair_result.get("repaired_count"):
                copied_item["unity3d_repair"] = repair_result
                unity3d_repaired.append({"guid": manifest.guid, "zipmod_path": str(target_path), **repair_result})
            copied.append(copied_item)
        except OSError as exc:
            failures.append({"source_path": str(source_path), "error": str(exc)})
        set_step_progress(task, index, total, start=14, end=25)
        if should_report_step(index, total):
            reporter.message(f"Copied {index}/{total} external zipmod candidate(s) into game mods")

    if copied:
        reporter.message("Rebuilding database after import copy")
        def report_database_progress(value: int, message: str) -> None:
            reporter.progress(25 + value * 0.45, 100)
            reporter.message(message)

        build_database(
            game_dir,
            db_path,
            thumbnail_dir,
            report_database_progress,
            mode="incremental",
            **_database_worker_options(payload),
        )

    imported: list[dict] = []
    promoted: list[dict] = []
    skipped: list[dict] = []
    cleaned: list[dict] = []
    processed_guids: set[str] = set()
    copied_by_guid: dict[str, list[dict]] = {}
    for item in copied:
        copied_by_guid.setdefault(str(item.get("guid") or ""), []).append(item)
    guid_total = max(len({item["guid"] for item in copied}), 1)
    for index, guid in enumerate(sorted({item["guid"] for item in copied}), start=1):
        processed_guids.add(guid)
        zipmod_id = _primary_id_for_guid(guid, db_path)
        if not zipmod_id:
            skipped.append({"guid": guid, "reason": "Imported zipmod was not indexed"})
            set_step_progress(task, index, guid_total, start=70, end=94)
            continue

        duplicate_ids = _duplicate_ids_for_guid(guid, db_path)
        if not duplicate_ids:
            for copied_item in copied_by_guid.get(guid, []):
                imported.append(
                    {
                        "guid": guid,
                        "zipmod_id": zipmod_id,
                        "file_name": Path(str(copied_item.get("target_path") or "")).name,
                        "source_path": copied_item.get("source_path", ""),
                        "target_path": copied_item.get("target_path", ""),
                    }
                )
            set_step_progress(task, index, guid_total, start=70, end=94)
            continue

        analysis = analyze_duplicate_zipmods(zipmod_id, db_path=db_path, thumbnail_dir=thumbnail_dir)
        if not analysis.get("ok"):
            skipped.append({"guid": guid, "id": zipmod_id, "reason": str(analysis.get("error") or "Duplicate analysis failed")})
            set_step_progress(task, index, guid_total, start=70, end=94)
            continue

        action, cleanup_ids, promote_duplicate_id, reason = choose_safe_duplicate_cleanup_action(analysis)
        if action == "promote":
            result = delete_primary_and_promote_duplicate(zipmod_id, promote_duplicate_id, db_path=db_path, thumbnail_dir=thumbnail_dir)
            if result.get("ok"):
                if cleanup_ids:
                    cleanup_result = cleanup_duplicate_zipmods(
                        int(result.get("promoted_zipmod_id") or zipmod_id),
                        duplicate_ids=cleanup_ids,
                        db_path=db_path,
                    )
                    result = {**result, "cleanup_after_promote": cleanup_result}
                promoted.append(
                    {
                        "guid": guid,
                        "id": zipmod_id,
                        "file_name": Path(str(result.get("promoted_file_path") or "")).name,
                        **result,
                    }
                )
            else:
                failures.append({"guid": guid, "id": zipmod_id, "error": str(result.get("error") or "Promote imported zipmod failed")})
        elif action == "cleanup":
            result = cleanup_duplicate_zipmods(zipmod_id, duplicate_ids=cleanup_ids, db_path=db_path)
            if result.get("ok"):
                analysis_keep = (analysis.get("recommendation") or {}).get("keep") or {}
                cleaned.append(
                    {
                        "guid": guid,
                        "id": zipmod_id,
                        "kept_file_name": analysis_keep.get("file_name", ""),
                        "kept_file_path": analysis_keep.get("file_path", ""),
                        **result,
                    }
                )
                for copied_item in copied_by_guid.get(guid, []):
                    copied_target = str(copied_item.get("target_path") or "")
                    if copied_target and copied_target not in set(result.get("removed") or []):
                        imported.append(
                            {
                                "guid": guid,
                                "zipmod_id": zipmod_id,
                                "file_name": Path(copied_target).name,
                                "source_path": copied_item.get("source_path", ""),
                                "target_path": copied_target,
                            }
                        )
            else:
                failures.append({"guid": guid, "id": zipmod_id, "error": str(result.get("error") or "Duplicate cleanup failed")})
        else:
            skipped.append({"guid": guid, "id": zipmod_id, "reason": reason or "No safe duplicate action"})

        set_step_progress(task, index, guid_total, start=70, end=94)
        if should_report_step(index, guid_total):
            reporter.message(f"Compared {index}/{guid_total} imported GUIDs; promoted {len(promoted)}, skipped {len(skipped)}")

    reporter.progress(96, 100)
    if copied or imported_cards:
        reporter.message("Refreshing database after duplicate decisions")
        if copied:
            build_database(
                game_dir,
                db_path,
                thumbnail_dir,
                lambda _value, message: reporter.message(message),
                mode="incremental",
                **_database_worker_options(payload),
            )
        reporter.message("Refreshing character card dependencies after import")
        build_card_database(
            game_dir,
            db_path,
            preview_dir,
            lambda _value, message: reporter.message(message),
            mode="incremental",
            **_database_worker_options(payload),
        )

    return {
        "ok": True,
        "source_dir": str(source_dir),
        "target_dir": str(import_dir),
        "card_target_dir": str(card_import_dir),
        "coordinate_target_dir": str(coordinate_import_dir),
        "scanned_count": len(candidate_paths),
        "zipmod_scanned_count": len(zipmod_paths),
        "zip_scanned_count": len(zip_paths),
        "zip_recognized_count": len(recognized_zip_paths),
        "zip_renamed_count": sum(
            1 for item in copied if item.get("source_extension") == ".zip"
        ),
        "png_scanned_count": len(png_paths),
        "copied_count": len(copied),
        "unity3d_repaired_count": sum(int(item.get("repaired_count") or 0) for item in unity3d_repaired),
        "card_imported_count": len(imported_cards),
        "coordinate_imported_count": len(imported_coordinates),
        "non_card_png_count": len(non_card_pngs),
        "invalid_count": len(invalid),
        "imported_count": len(imported),
        "promoted_count": len(promoted),
        "cleaned_count": len(cleaned),
        "skipped_count": len(skipped),
        "failure_count": len(failures),
        "invalid": invalid,
        "unity3d_repaired": unity3d_repaired,
        "imported_cards": imported_cards,
        "imported_coordinates": imported_coordinates,
        "non_card_pngs": non_card_pngs,
        "imported": imported,
        "promoted": promoted,
        "cleaned": cleaned,
        "skipped": skipped,
        "failures": failures,
        "message": (
            f"Imported {len(imported)} zipmod GUID(s), promoted {len(promoted)} better duplicate(s), "
            f"recognized {len(recognized_zip_paths)} external zip archive(s) and normalized "
            f"{sum(1 for item in copied if item.get('source_extension') == '.zip')} imported filename(s), "
            f"repaired {sum(int(item.get('repaired_count') or 0) for item in unity3d_repaired)} unity3d file(s), "
            f"copied {len(imported_cards)} character card(s) and {len(imported_coordinates)} clothes card(s), "
            f"skipped {len(skipped)}, invalid {len(invalid)}, failed {len(failures)}"
        ),
    }


def run_task(task: TaskState, payload: dict) -> None:
    reporter = build_reporter(task)
    if not task.pause_requested:
        task.status = "running"
    task.updated_at = time()

    try:
        if task.task_type == "check_game_dir":
            game_dir = str(payload.get("game_dir") or "")
            task.title = "Check game directory"
            task.data = {"is_valid": is_hs2_game_dir(game_dir), "game_dir": game_dir}
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
            database_task_started_at = perf_counter()
            reporter.title("Build mod database")
            reporter.message(f"Building mod database from: {game_dir}")

            def report_database_progress(value: int, message: str) -> None:
                reporter.progress(weighted_mod_database_progress(value), 100)
                reporter.message(message)

            stats = build_database(
                Path(game_dir),
                db_path,
                thumbnail_dir,
                report_database_progress,
                mode=mode,
                worker_count=payload.get("worker_count"),
            )
            reporter.message("Building character card database")

            def report_card_database_progress(value: int, message: str) -> None:
                reporter.progress(weighted_character_card_database_progress(value), 100)
                reporter.message(message)

            card_database_started_at = perf_counter()
            card_stats = build_card_database(
                Path(game_dir),
                db_path,
                preview_dir,
                report_card_database_progress,
                mode=mode,
                affected_mod_guids=stats.get("affected_mod_guids"),
                worker_count=payload.get("worker_count"),
            )
            mod_timings = stats.get("timings") if isinstance(stats.get("timings"), dict) else {}
            card_timings = card_stats.get("timings") if isinstance(card_stats.get("timings"), dict) else {}
            timings = {
                "builtin_resource_index_ms": mod_timings.get("builtin_resource_index_ms", 0),
                "zipmod_scan_ms": mod_timings.get("zipmod_scan_ms", 0),
                "item_parse_ms": mod_timings.get("item_parse_ms", 0),
                "database_write_ms": mod_timings.get("database_write_ms", 0),
                "character_card_database_ms": card_timings.get(
                    "card_database_total_ms",
                    round((perf_counter() - card_database_started_at) * 1000, 2),
                ),
                "total_ms": round((perf_counter() - database_task_started_at) * 1000, 2),
            }
            task.data = {
                "database_path": str(db_path.resolve()),
                "thumbnail_dir": str(thumbnail_dir.resolve()),
                "thumbnail_profile_log": stats.get("thumbnail_profile_log", ""),
                "preview_dir": str(preview_dir.resolve()),
                "mode": mode,
                "stats": stats,
                "card_stats": card_stats,
                "timings": timings,
            }
            reporter.message(
                "数据库耗时汇总："
                f"原版资源索引 {format_elapsed_seconds(timings['builtin_resource_index_ms'])}；"
                f"zipmod 扫描 {format_elapsed_seconds(timings['zipmod_scan_ms'])}；"
                f"物品解析 {format_elapsed_seconds(timings['item_parse_ms'])}；"
                f"数据库写入 {format_elapsed_seconds(timings['database_write_ms'])}；"
                f"人物卡数据库 {format_elapsed_seconds(timings['character_card_database_ms'])}；"
                f"总耗时 {format_elapsed_seconds(timings['total_ms'])}"
            )
            reporter.message(f"Database created: {db_path.resolve()}")
            reporter.message(f"Thumbnail cache: {thumbnail_dir.resolve()}")
            if stats.get("thumbnail_profile_log"):
                reporter.message(f"Thumbnail profile log: {stats['thumbnail_profile_log']}")
            reporter.message(f"Card preview cache: {preview_dir.resolve()}")
        elif task.task_type == "index_single_zipmod":
            game_dir = str(payload.get("game_dir") or "")
            zipmod_path = str(payload.get("zipmod_path") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            thumbnail_dir = Path(str(payload.get("thumbnail_dir") or DEFAULT_THUMBNAIL_DIR))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            if not is_hs2_game_dir(game_dir):
                raise ValueError("Select a valid HS2 game directory before indexing a single zipmod.")
            reporter.title("Index single zipmod")
            reporter.message(f"Indexing only: {zipmod_path}")

            def report_single_zipmod_progress(value: int, message: str) -> None:
                reporter.progress(value, 100)
                reporter.message(message)

            stats = index_single_zipmod(
                Path(game_dir),
                db_path,
                thumbnail_dir,
                Path(zipmod_path),
                report_single_zipmod_progress,
            )
            card_stats = rebuild_affected_character_cards(
                game_dir,
                db_path,
                preview_dir,
                stats.get("affected_mod_guids"),
                reporter,
                worker_count=payload.get("worker_count"),
            )
            task.data = {
                "database_path": str(db_path.resolve()),
                "thumbnail_dir": str(thumbnail_dir.resolve()),
                "preview_dir": str(preview_dir.resolve()),
                "mode": "single",
                "stats": stats,
                "card_stats": card_stats,
            }
            reporter.message(f"Single zipmod indexed: {zipmod_path}")
        elif task.task_type == "download_card_missing_mods":
            remote_ids = payload.get("remote_ids") or []
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            thumbnail_dir = Path(str(payload.get("thumbnail_dir") or DEFAULT_THUMBNAIL_DIR))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            reporter.title("Download missing card mods")
            reporter.message(f"Preparing {len(remote_ids)} selected remote mod(s)")
            task.phase = "preparing"
            task.phase_progress = 0
            task.phase_message = "准备下载"
            task.updated_at = time()

            def report_remote_download(value: float, message: str, details: dict | None = None) -> None:
                wait_for_task_resume(task)
                reporter.progress(value, 100)
                reporter.message(message)
                details = details or {}
                task.phase = str(details.get("phase") or task.phase or "download")
                task.phase_progress = round(float(details.get("phase_progress") or 0), 1)
                task.download_speed_bps = round(float(details.get("download_speed_bps") or 0), 1)
                task.downloaded_bytes = max(0, int(details.get("downloaded_bytes") or 0))
                task.total_bytes = max(0, int(details.get("total_bytes") or 0))
                task.current_file = str(details.get("current_file") or "")
                task.phase_message = message
                task.updated_at = time()

            task.data = download_card_missing_mods(
                game_dir,
                remote_ids,
                progress_callback=report_remote_download,
                control_callback=lambda: wait_for_task_resume(task),
                db_path=db_path,
                thumbnail_dir=thumbnail_dir,
            )
            task.phase = "install"
            task.phase_progress = 95 if task.data.get("affected_mod_guids") else 100
            task.download_speed_bps = 0
            task.phase_message = "正在刷新人物卡依赖" if task.data.get("affected_mod_guids") else "模组已安装"
            task.progress = 99 if task.data.get("affected_mod_guids") else 100
            task.updated_at = time()
            card_stats = rebuild_affected_character_cards(
                game_dir,
                db_path,
                preview_dir,
                task.data.get("affected_mod_guids"),
                reporter,
                worker_count=payload.get("worker_count"),
            )
            if card_stats is not None:
                task.data["card_stats"] = card_stats
            if not task.data.get("ok"):
                raise ValueError(str(task.data.get("message") or "Remote mod download failed"))
            task.phase_progress = 100
            task.progress = 100
            task.phase_message = "模组安装完成"
            reporter.message(str(task.data.get("message") or "Remote mod download completed"))
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
                worker_count=payload.get("worker_count"),
            )
            task.data = {
                "database_path": str(db_path.resolve()),
                "preview_dir": str(preview_dir.resolve()),
                "mode": mode,
                "stats": stats,
            }
            reporter.message(f"Character card database created: {db_path.resolve()}")
            reporter.message(f"Card preview cache: {preview_dir.resolve()}")
        elif task.task_type == "import_external_zipmods":
            task.data = _import_external_zipmods(task, payload, reporter)
            reporter.message(str(task.data.get("message") or "External zipmod import completed"))
            if not task.data.get("ok"):
                raise ValueError("External zipmod import failed")
        elif task.task_type == "export_character_dependency_package":
            task.title = "生成角色卡便携依赖包"
            reporter.message("正在解析人物卡依赖")

            def report_package_progress(value: int, message: str) -> None:
                reporter.progress(value, 100)
                reporter.message(message)

            task.data = export_character_dependency_package(
                str(payload.get("game_dir") or ""),
                str(payload.get("path") or ""),
                str(payload.get("target_dir") or ""),
                bool(payload.get("compress", True)),
                payload.get("dependency_types") if "dependency_types" in payload else None,
                progress_callback=report_package_progress,
            )
            if not task.data.get("ok"):
                raise ValueError(str(task.data.get("error") or "便携依赖包生成失败"))
            reporter.message("便携依赖包已生成")
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
        elif task.task_type == "organize_all_zipmods_by_author":
            game_dir = str(payload.get("game_dir") or "")
            result = organize_all_zipmods_by_author(game_dir, reporter)
            reporter.message("文件整理完成，正在刷新本地索引")

            def report_database_progress(value: int, message: str) -> None:
                reporter.progress(70 + value * 0.3, 100)
                reporter.message(message)

            stats = build_database(
                Path(game_dir),
                Path(str(payload.get("db_path") or DEFAULT_DB_PATH)),
                Path(str(payload.get("thumbnail_dir") or DEFAULT_THUMBNAIL_DIR)),
                report_database_progress,
                mode="incremental",
                **_database_worker_options(payload),
            )
            result["stats"] = stats
            task.data = result
            reporter.message(
                f"整理完成：移动 {result['moved_count']} 个，"
                f"无需移动 {result['unchanged_count']} 个，"
                f"删除空目录 {result['removed_empty_dir_count']} 个，失败 {result['failure_count']} 个"
            )
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
            repair_count = sum(
                len(item.get("moved") or []) + len(item.get("copied") or [])
                for item in (task.data.get("repaired") or [])
            )
            record_achievement_event("repairs", repair_count, f"task:{task.id}:unity3d")
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
            freed_bytes = sum(int(item.get("freed_bytes") or 0) for item in cleaned)
            freed_bytes += sum(
                int((item.get("cleanup_after_promote") or {}).get("freed_bytes") or 0)
                for item in promoted
            )
            record_achievement_event("duplicate_bytes", freed_bytes, f"task:{task.id}:duplicates")
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
        elif task.task_type == "bulk_delete_character_cards":
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            card_paths = list(dict.fromkeys(
                str(path or "").strip()
                for path in (payload.get("card_paths") or [])
                if str(path or "").strip()
            ))
            if not card_paths:
                raise ValueError("请先选择要删除的人物卡。")

            task.title = "批量删除人物卡"
            reporter.message(f"正在删除 {len(card_paths)} 张人物卡")
            deleted: list[dict] = []
            failures: list[dict] = []
            total = len(card_paths)
            for index, relative_path in enumerate(card_paths, start=1):
                result = delete_character_card(game_dir, relative_path, db_path, preview_dir)
                if result.get("ok"):
                    deleted.append(result)
                else:
                    failures.append({
                        "id": relative_path,
                        "path": relative_path,
                        "error": str(result.get("error") or "人物卡删除失败"),
                    })
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"已处理 {index}/{total} 张人物卡；失败 {len(failures)} 张")
            task.data = {
                "ok": len(deleted) > 0 or len(failures) == 0,
                "selected_count": len(card_paths),
                "deleted_count": len(deleted),
                "failure_count": len(failures),
                "deleted": deleted,
                "failures": failures,
                "message": f"已删除 {len(deleted)} 张人物卡，失败 {len(failures)} 张",
            }
            if not task.data["ok"]:
                raise ValueError("批量删除人物卡失败")
        elif task.task_type == "bulk_add_character_card_tags":
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            preview_dir = Path(str(payload.get("preview_dir") or DEFAULT_CARD_PREVIEW_DIR))
            card_paths = list(dict.fromkeys(
                str(path or "").strip()
                for path in (payload.get("card_paths") or [])
                if str(path or "").strip()
            ))
            tags = payload.get("tags") or []
            if not card_paths:
                raise ValueError("请先选择要添加标签的人物卡。")
            if not tags:
                raise ValueError("请至少选择一个要添加的标签。")

            task.title = "批量添加人物卡标签"
            reporter.message(f"正在为 {len(card_paths)} 张人物卡添加标签")
            updated: list[dict] = []
            failures: list[dict] = []
            total = len(card_paths)
            for index, relative_path in enumerate(card_paths, start=1):
                result = add_character_card_tags(
                    game_dir,
                    relative_path,
                    tags,
                    db_path=db_path,
                    preview_dir=preview_dir,
                )
                if result.get("ok"):
                    updated.append(result)
                else:
                    failures.append({
                        "id": relative_path,
                        "path": relative_path,
                        "error": str(result.get("error") or "人物卡标签添加失败"),
                    })
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"已处理 {index}/{total} 张人物卡；失败 {len(failures)} 张")
            task.data = {
                "ok": len(updated) > 0 or len(failures) == 0,
                "selected_count": len(card_paths),
                "updated_count": len(updated),
                "failure_count": len(failures),
                "tags": list(tags),
                "updated": updated,
                "failures": failures,
                "message": f"已为 {len(updated)} 张人物卡添加标签，失败 {len(failures)} 张",
            }
            if not task.data["ok"]:
                raise ValueError("批量添加人物卡标签失败")
        elif task.task_type == "bulk_move_character_cards":
            game_dir = str(payload.get("game_dir") or "")
            db_path = Path(str(payload.get("db_path") or DEFAULT_DB_PATH))
            target_directory = str(payload.get("target_directory") or "").strip()
            card_paths = list(dict.fromkeys(
                str(path or "").strip()
                for path in (payload.get("card_paths") or [])
                if str(path or "").strip()
            ))
            if not card_paths:
                raise ValueError("请先选择要移动的人物卡。")
            if not target_directory:
                raise ValueError("请选择目标目录。")

            task.title = "批量移动人物卡"
            reporter.message(f"正在移动 {len(card_paths)} 张人物卡")
            moved: list[dict] = []
            failures: list[dict] = []
            total = len(card_paths)
            for index, relative_path in enumerate(card_paths, start=1):
                result = move_character_card(game_dir, relative_path, target_directory, db_path)
                if result.get("ok"):
                    moved.append(result)
                else:
                    failures.append({
                        "id": relative_path,
                        "path": relative_path,
                        "error": str(result.get("error") or "人物卡移动失败"),
                    })
                set_step_progress(task, index, total)
                if should_report_step(index, total):
                    reporter.message(f"已处理 {index}/{total} 张人物卡；失败 {len(failures)} 张")
            task.data = {
                "ok": len(moved) > 0 or len(failures) == 0,
                "selected_count": len(card_paths),
                "moved_count": len(moved),
                "failure_count": len(failures),
                "target_directory": target_directory,
                "moved": moved,
                "failures": failures,
                "message": f"已移动 {len(moved)} 张人物卡，失败 {len(failures)} 张",
            }
            if not task.data["ok"]:
                raise ValueError("批量移动人物卡失败")
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
            record_achievement_event("repairs", len(imported), f"task:{task.id}:thumbnails")
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
        if task.task_type == "download_card_missing_mods":
            task.phase = "completed"
            task.phase_progress = 100
            task.download_speed_bps = 0
        task.status = "completed"
        task.finished_at = time()
    except RemoteDownloadCancelled as error:
        task.error = "下载已取消"
        if task.task_type == "download_card_missing_mods":
            task.phase = "cancelled"
            task.phase_message = str(error)
            task.download_speed_bps = 0
        task.status = "cancelled"
        task.finished_at = time()
        task.messages.append("Download cancelled")
    except Exception as error:
        task.error = str(error)
        if task.task_type == "download_card_missing_mods":
            task.phase = "failed"
            task.phase_message = str(error)
            task.download_speed_bps = 0
        task.status = "failed"
        task.finished_at = time()
        task.messages.append(f"[Error] {error}")
    finally:
        if not task.finished_at:
            task.finished_at = time()
        task.updated_at = time()
