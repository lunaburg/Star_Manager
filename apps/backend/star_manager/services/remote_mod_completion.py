from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
import re
import sqlite3
from threading import Lock
from time import monotonic
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Iterable

from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.card_library import (
    is_ais_card,
    inspect_clothes_card_file,
    resolve_card_dependencies,
    resolve_card_file,
    resolve_dependency_records,
    resolve_coordinate_file,
    resolve_scene_file,
    validate_card_root,
    validate_coordinate_root,
    validate_scene_root,
)
from star_manager.core.scene_card import inspect_scene_card_file
from star_manager.services.mod_database import index_single_zipmod
from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    utc_now,
)
from star_manager.services.mod_database_assets import read_manifest
from star_manager.core.runtime_paths import runtime_root


DEFAULT_REMOTE_INDEX_PATH = runtime_root() / "remote" / "remote_zipmod_index.sqlite"
DEFAULT_REMOTE_INSTALL_DIRNAME = "Remote"
REMOTE_INDEX_SOURCE = "https://sideload.betterrepack.com/download/AISHS2/"
MAX_SELECTED_CANDIDATES = 100
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
MAX_PARALLEL_DOWNLOADS = 3
USER_AGENT = "Star-Manager-card-mod-completion/1.0"


class RemoteDownloadCancelled(RuntimeError):
    """Raised when the user cancels a remote mod download task."""


def normalize_guid(value: object) -> str:
    return str(value or "").strip().casefold()


def _remote_index_connection(index_path: Path) -> sqlite3.Connection:
    resolved = index_path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Remote mod index not found: {resolved}")
    connection = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _candidate_payload(row: sqlite3.Row) -> dict:
    return {
        "remote_id": int(row["id"]),
        "guid": str(row["guid"] or ""),
        "guid_norm": str(row["guid_norm"] or ""),
        "name": str(row["name"] or row["file_name"] or "zipmod"),
        "version": str(row["version"] or ""),
        "author": str(row["author"] or ""),
        "file_name": str(row["file_name"] or ""),
        "relative_path": str(row["relative_path"] or ""),
        "file_size": int(row["file_size"] or 0),
        "manifest_status": str(row["manifest_status"] or ""),
        "download_url": str(row["download_url"] or ""),
        "source_url": str(row["source_url"] or ""),
    }


def _dependency_usage(dependency: dict) -> dict:
    return {
        "category_no": str(dependency.get("category_no") or ""),
        "slot": str(dependency.get("slot") or ""),
        "local_slot": str(dependency.get("local_slot") or ""),
        "property": str(dependency.get("property") or ""),
        "name": str(dependency.get("name") or ""),
    }


def _read_remote_candidates(
    connection: sqlite3.Connection,
    guid_norm: str,
) -> list[dict]:
    rows = connection.execute(
        """
        SELECT id, source_url, download_url, relative_path, file_name,
               guid, guid_norm, name, version, author, file_size,
               manifest_status
        FROM remote_zipmods
        WHERE present = 1
          AND manifest_status = 'ok'
          AND guid_norm = ?
        ORDER BY file_size DESC, version COLLATE NOCASE DESC,
                 file_name COLLATE NOCASE
        """,
        (guid_norm,),
    ).fetchall()
    return [_candidate_payload(row) for row in rows]


def _group_missing_dependencies(
    dependencies: Iterable[dict],
    connection: sqlite3.Connection,
) -> tuple[list[dict], int]:
    """Group unresolved card/scene dependencies by the manifest GUID."""

    grouped: dict[str, dict] = {}
    local_item_missing = 0
    for dependency in dependencies:
        guid = str(dependency.get("mod_id") or "").strip()
        guid_norm = normalize_guid(guid)
        if not guid_norm or dependency.get("matched"):
            continue
        group = grouped.setdefault(
            guid_norm,
            {
                "guid": guid,
                "guid_norm": guid_norm,
                "usage_count": 0,
                "missing_mod_count": 0,
                "local_item_missing_count": 0,
                "usages": [],
            },
        )
        if dependency.get("zipmod"):
            local_item_missing += 1
            group["local_item_missing_count"] += 1
        else:
            group["missing_mod_count"] += 1
        usage = _dependency_usage(dependency)
        usage_key = tuple(usage.values())
        if usage_key not in {tuple(item.values()) for item in group["usages"]}:
            group["usages"].append(usage)
        group["usage_count"] += 1

    groups: list[dict] = []
    for group in grouped.values():
        candidates = _read_remote_candidates(connection, group["guid_norm"])
        group["candidates"] = candidates
        group["candidate_count"] = len(candidates)
        group["can_download"] = bool(candidates)
        has_local_item_missing = bool(group["local_item_missing_count"])
        group["mod_installed"] = bool(group["local_item_missing_count"])
        group["item_missing"] = has_local_item_missing
        if has_local_item_missing:
            group["display_name"] = group["guid"]
            group["can_download"] = False
            group["status"] = "local_item_missing"
            group["status_label"] = "模组存在，物品缺失"
            group["reason"] = "本地数据库已有该模组，但没有找到场景/卡片所需的具体物品记录"
        elif candidates:
            group["display_name"] = candidates[0]["name"]
            group["status"] = "available"
            group["status_label"] = "可补全"
            group["reason"] = "远程索引中找到可下载模组"
        else:
            group["display_name"] = group["guid"]
            group["status"] = "unavailable"
            group["status_label"] = "不可补全"
            group["reason"] = "远程索引中没有有效 manifest 记录"
        groups.append(group)

    groups.sort(key=lambda item: (not item["can_download"], item["display_name"].casefold()))
    return groups, local_item_missing


def _missing_mod_result(
    card_path: Path,
    relative_path: str,
    dependencies: Iterable[dict],
    connection: sqlite3.Connection,
    *,
    resource_type: str,
    index_path: Path,
) -> dict:
    groups, local_item_missing = _group_missing_dependencies(dependencies, connection)
    available_groups = [item for item in groups if item["can_download"]]
    unavailable_groups = [item for item in groups if not item["can_download"]]
    return {
        "ok": True,
        "resource_type": resource_type,
        "card_path": str(card_path),
        "relative_path": str(relative_path),
        "index_path": str(index_path.resolve()),
        "source_url": REMOTE_INDEX_SOURCE,
        "missing_count": len(groups),
        "available_count": len(available_groups),
        "unavailable_count": len(unavailable_groups),
        "local_item_missing_count": local_item_missing,
        "groups": groups,
        "available": available_groups,
        "unavailable": unavailable_groups,
    }


def inspect_card_missing_mods(
    game_dir: str,
    relative_path: str,
    index_path: Path = DEFAULT_REMOTE_INDEX_PATH,
) -> dict:
    """Return remote candidates for GUIDs missing from one character card."""

    if not is_hs2_game_dir(game_dir):
        return {"ok": False, "error": "Please select a valid HS2 game directory."}
    is_valid, root, error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "Character-card directory is invalid."}
    try:
        card_path = resolve_card_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not card_path.is_file() or not is_ais_card(str(card_path)):
        return {"ok": False, "error": "Character card not found."}

    try:
        dependencies = resolve_card_dependencies(str(card_path))
        connection = _remote_index_connection(index_path)
    except (OSError, sqlite3.Error) as exc:
        return {"ok": False, "error": str(exc)}

    try:
        result = _missing_mod_result(
            card_path,
            relative_path,
            dependencies,
            connection,
            resource_type="character_card",
            index_path=index_path,
        )
    finally:
        connection.close()
    return result


def inspect_scene_missing_mods(
    game_dir: str,
    relative_path: str,
    index_path: Path = DEFAULT_REMOTE_INDEX_PATH,
) -> dict:
    """Return remote candidates for unresolved dependencies in one scene card."""

    if not is_hs2_game_dir(game_dir):
        return {"ok": False, "error": "Please select a valid HS2 game directory."}
    is_valid, root, error = validate_scene_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "Scene-card directory is invalid."}
    try:
        card_path = resolve_scene_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    parsed = inspect_scene_card_file(card_path)
    if not parsed or not parsed.get("is_scene_card"):
        return {"ok": False, "error": "Scene card not found or invalid."}

    try:
        dependencies = resolve_dependency_records(parsed.get("dependencies") or [])
        connection = _remote_index_connection(index_path)
    except (OSError, sqlite3.Error) as exc:
        return {"ok": False, "error": str(exc)}

    try:
        result = _missing_mod_result(
            card_path,
            relative_path,
            dependencies,
            connection,
            resource_type="scene_card",
            index_path=index_path,
        )
    finally:
        connection.close()
    return result


def inspect_clothes_missing_mods(
    game_dir: str,
    relative_path: str,
    index_path: Path = DEFAULT_REMOTE_INDEX_PATH,
) -> dict:
    """Return remote candidates for unresolved dependencies in one clothes card."""

    if not is_hs2_game_dir(game_dir):
        return {"ok": False, "error": "Please select a valid HS2 game directory."}
    is_valid, root, error = validate_coordinate_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": error or "Clothes-card directory is invalid."}
    try:
        card_path = resolve_coordinate_file(root, relative_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    parsed = inspect_clothes_card_file(card_path)
    if not parsed:
        return {"ok": False, "error": "Clothes card not found or invalid."}

    try:
        dependencies = resolve_dependency_records(parsed.get("dependencies") or [])
        connection = _remote_index_connection(index_path)
    except (OSError, sqlite3.Error) as exc:
        return {"ok": False, "error": str(exc)}

    try:
        result = _missing_mod_result(
            card_path,
            relative_path,
            dependencies,
            connection,
            resource_type="clothes_card",
            index_path=index_path,
        )
    finally:
        connection.close()
    return result


def _safe_component(value: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "").strip())
    cleaned = cleaned.rstrip(" .") or fallback
    if cleaned.upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }:
        cleaned = f"_{cleaned}"
    return cleaned[:180].rstrip(" .") or fallback


def _safe_relative_path(relative_path: str, file_name: str) -> Path:
    raw_parts = str(relative_path or "").replace("\\", "/").split("/")
    parts = [
        _safe_component(part, "unknown")
        for part in raw_parts
        if part and part not in {".", ".."}
    ]
    safe_file = _safe_component(file_name, "remote.zipmod")
    if not parts or parts[-1].casefold() != safe_file.casefold():
        parts.append(safe_file)
    return Path(*parts)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _allowed_remote_url(url: str, source_url: str) -> bool:
    target = urllib.parse.urlsplit(url)
    source = urllib.parse.urlsplit(source_url)
    return (
        target.scheme == "https"
        and source.scheme == "https"
        and target.netloc.casefold() == source.netloc.casefold()
        and target.path.startswith(source.path.rstrip("/") + "/")
    )


def _open_remote(url: str, source_url: str, timeout: float = 60.0):
    opener = urllib.request.build_opener(_NoRedirectHandler())
    current = url
    for _ in range(4):
        if not _allowed_remote_url(current, source_url):
            raise ValueError("Remote download URL is outside the indexed source.")
        request = urllib.request.Request(
            current,
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        )
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in {301, 302, 303, 307, 308}:
                raise RuntimeError(f"HTTP {exc.code} while downloading remote mod") from exc
            location = exc.headers.get("Location")
            exc.close()
            if not location:
                raise RuntimeError("Remote download redirect has no Location header.")
            current = urllib.parse.urljoin(current, location)
            continue
        status = int(getattr(response, "status", 200) or 200)
        if status in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise RuntimeError("Remote download redirect has no Location header.")
            current = urllib.parse.urljoin(current, location)
            continue
        return response
    raise RuntimeError("Too many redirects while downloading remote mod.")


def _resolve_candidates(
    connection: sqlite3.Connection,
    remote_ids: Iterable[object],
) -> list[dict]:
    ids: list[int] = []
    seen: set[int] = set()
    for value in remote_ids:
        try:
            candidate_id = int(value)
        except (TypeError, ValueError):
            continue
        if candidate_id > 0 and candidate_id not in seen:
            ids.append(candidate_id)
            seen.add(candidate_id)
    if not ids:
        raise ValueError("No remote mod candidates selected.")
    if len(ids) > MAX_SELECTED_CANDIDATES:
        raise ValueError(f"Select no more than {MAX_SELECTED_CANDIDATES} remote mods at once.")
    placeholders = ",".join("?" for _ in ids)
    rows = connection.execute(
        f"""
        SELECT id, source_url, download_url, relative_path, file_name,
               guid, guid_norm, name, version, author, file_size,
               manifest_status
        FROM remote_zipmods
        WHERE id IN ({placeholders}) AND present = 1 AND manifest_status = 'ok'
        """,
        ids,
    ).fetchall()
    if len(rows) != len(ids):
        raise ValueError("One or more selected remote mods are no longer available in the index.")
    candidates = [_candidate_payload(row) for row in rows]
    guid_set = {item["guid_norm"] for item in candidates if item["guid_norm"]}
    if len(guid_set) != len(candidates):
        raise ValueError("Select only one remote version for each GUID.")
    return candidates


def _existing_guid(path: Path) -> str:
    try:
        return normalize_guid(read_manifest(path).guid)
    except (OSError, zipfile.BadZipFile):
        return ""


def _download_candidate(
    candidate: dict,
    game_dir: Path,
    progress_callback: Callable[[int, int], None] | None = None,
    control_callback: Callable[[], None] | None = None,
    target_lock=None,
) -> dict:
    mods_root = (game_dir / "mods").resolve()
    install_root = (mods_root / DEFAULT_REMOTE_INSTALL_DIRNAME).resolve()
    relative = _safe_relative_path(candidate["relative_path"], candidate["file_name"])
    target = (install_root / relative).resolve()
    if install_root not in target.parents:
        raise ValueError("Remote target path escaped the game mods directory.")

    def choose_available_target() -> dict | None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and _existing_guid(target) == candidate["guid_norm"]:
            return {
                **candidate,
                "status": "already_exists",
                "target_path": str(target),
                "downloaded_size": target.stat().st_size,
            }
        return None

    with (target_lock if target_lock is not None else nullcontext()):
        existing = choose_available_target()
        if existing is not None:
            return existing
        if target.exists():
            stem = target.stem
            suffix = target.suffix or ".zipmod"
            for index in range(1, 1000):
                alternative = target.with_name(f"{stem} ({index}){suffix}")
                if not alternative.exists():
                    target = alternative
                    break
            else:
                raise FileExistsError(f"Could not find a free target name for {target.name}")

    temporary = target.with_name(f".{target.name}.{candidate['guid_norm'][:12]}.part")
    temporary.unlink(missing_ok=True)
    downloaded = 0
    response = None
    try:
        if control_callback:
            control_callback()
        response = _open_remote(candidate["download_url"], candidate["source_url"])
        expected = int(response.headers.get("Content-Length") or 0)
        with temporary.open("wb") as output:
            while True:
                if control_callback:
                    control_callback()
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, expected)
        response.close()
        response = None
        if control_callback:
            control_callback()
        if expected and downloaded != expected:
            raise RuntimeError(f"Downloaded size mismatch: expected {expected}, got {downloaded}")
        with zipfile.ZipFile(temporary, "r") as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise RuntimeError(f"ZIP CRC validation failed: {bad_member}")
        manifest = read_manifest(temporary)
        if manifest.scan_status != "ok" or normalize_guid(manifest.guid) != candidate["guid_norm"]:
            raise RuntimeError("Downloaded ZIPMOD manifest GUID does not match the selected candidate.")
        with (target_lock if target_lock is not None else nullcontext()):
            if target.exists():
                stem = target.stem
                suffix = target.suffix or ".zipmod"
                for index in range(1, 1000):
                    alternative = target.with_name(f"{stem} ({index}){suffix}")
                    if not alternative.exists():
                        target = alternative
                        break
                else:
                    raise FileExistsError(f"Could not find a free target name for {target.name}")
            temporary.replace(target)
        return {
            **candidate,
            "status": "downloaded",
            "target_path": str(target),
            "downloaded_size": downloaded,
            "manifest_verified": True,
        }
    except Exception:
        if response is not None:
            response.close()
        temporary.unlink(missing_ok=True)
        raise


def download_card_missing_mods(
    game_dir: str,
    remote_ids: Iterable[object],
    progress_callback: Callable[[float, str], None] | Callable[[float, str, dict], None] | None = None,
    control_callback: Callable[[], None] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    """Download all selected candidates, then install/index them in a second phase."""

    game_root = Path(game_dir).expanduser().resolve()
    if not is_hs2_game_dir(game_root):
        raise ValueError("Please select a valid HS2 game directory.")
    connection = _remote_index_connection(DEFAULT_REMOTE_INDEX_PATH)
    try:
        candidates = _resolve_candidates(connection, remote_ids)
    finally:
        connection.close()

    completed_by_id: dict[int, dict] = {}
    failures_by_id: dict[int, dict] = {}
    total = max(len(candidates), 1)
    progress_lock = Lock()
    target_lock = Lock()
    candidate_state = {
        int(candidate["remote_id"]): {
            "done": 0,
            "expected": max(int(candidate.get("file_size") or 0), 1),
            "download_progress": 0.0,
            "install_progress": 0.0,
        }
        for candidate in candidates
    }
    speed_timestamp = monotonic()
    speed_bytes = 0
    current_speed = 0.0

    def emit_progress(
        value: float,
        message: str,
        *,
        phase: str,
        phase_progress: float,
        current_file: str = "",
        completed_files: int = 0,
        total_files: int = len(candidates),
    ) -> None:
        nonlocal speed_timestamp, speed_bytes, current_speed
        if progress_callback is None:
            return
        with progress_lock:
            downloaded_bytes = sum(item["done"] for item in candidate_state.values())
            now = monotonic()
            elapsed = now - speed_timestamp
            if phase == "download" and elapsed >= 0.05:
                current_speed = max(0.0, (downloaded_bytes - speed_bytes) / elapsed)
                speed_timestamp = now
                speed_bytes = downloaded_bytes
            elif phase != "download":
                current_speed = 0.0
            total_bytes = sum(item["expected"] for item in candidate_state.values())
            details = {
                "phase": phase,
                "phase_progress": round(max(0.0, min(100.0, phase_progress)), 1),
                "download_speed_bps": round(current_speed, 1),
                "downloaded_bytes": downloaded_bytes,
                "total_bytes": total_bytes,
                "current_file": current_file,
                "completed_files": completed_files,
                "total_files": total_files,
            }
            try:
                progress_callback(round(value, 1), message, details)
            except TypeError as error:
                try:
                    progress_callback(round(value, 1), message)
                except TypeError:
                    raise error

    def download_phase_progress() -> float:
        return sum(item["download_progress"] for item in candidate_state.values()) / total

    def install_phase_progress(installed_count: int, current_progress: float = 0.0) -> float:
        install_total = max(len(candidates), 1)
        return ((installed_count + current_progress / 100.0) / install_total) * 100.0

    def report_download(candidate: dict, done: int, expected: int) -> None:
        if control_callback:
            control_callback()
        state = candidate_state[int(candidate["remote_id"])]
        state["done"] = max(int(done or 0), 0)
        if expected:
            state["expected"] = max(int(expected), 1)
        state["download_progress"] = min(100.0, state["done"] / state["expected"] * 100.0)
        emit_progress(
            download_phase_progress() * 0.5,
            f"Downloading {candidate['file_name']}",
            phase="download",
            phase_progress=download_phase_progress(),
            current_file=candidate["file_name"],
        )

    def download_one(candidate: dict) -> dict:
        return _download_candidate(
            candidate,
            game_root,
            lambda done, expected: report_download(candidate, done, expected),
            control_callback,
            target_lock,
        )

    emit_progress(
        0,
        f"Starting download of {len(candidates)} remote mod(s)",
        phase="download",
        phase_progress=0,
    )
    downloaded_by_id: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_DOWNLOADS, len(candidates))) as executor:
        futures = {executor.submit(download_one, candidate): candidate for candidate in candidates}
        for future in as_completed(futures):
            candidate = futures[future]
            remote_id = int(candidate["remote_id"])
            try:
                result = future.result()
                state = candidate_state[remote_id]
                state["done"] = max(int(result.get("downloaded_size") or 0), state["done"])
                state["download_progress"] = 100.0
                downloaded_by_id[remote_id] = result
                emit_progress(
                    download_phase_progress() * 0.5,
                    f"Downloaded {candidate['file_name']}",
                    phase="download",
                    phase_progress=download_phase_progress(),
                    current_file=candidate["file_name"],
                    completed_files=len(downloaded_by_id) + len(failures_by_id),
                )
            except RemoteDownloadCancelled:
                raise
            except Exception as error:
                candidate_state[remote_id]["download_progress"] = 100.0
                failures_by_id[remote_id] = {
                    "remote_id": remote_id,
                    "guid": candidate["guid"],
                    "file_name": candidate["file_name"],
                    "error": str(error),
                }
            if remote_id in failures_by_id:
                emit_progress(
                    download_phase_progress() * 0.5,
                    f"Download failed: {candidate['file_name']}",
                    phase="download",
                    phase_progress=download_phase_progress(),
                    current_file=candidate["file_name"],
                    completed_files=len(downloaded_by_id) + len(failures_by_id),
                )

    if control_callback:
        control_callback()
    install_total = len(downloaded_by_id)
    emit_progress(
        50 if candidates else 0,
        f"Starting installation of {install_total} downloaded mod(s)",
        phase="install",
        phase_progress=0 if install_total else 100,
        completed_files=0,
        total_files=install_total,
    )
    installed_count = 0
    processed_install_count = 0
    for candidate in candidates:
        remote_id = int(candidate["remote_id"])
        result = downloaded_by_id.get(remote_id)
        if result is None:
            continue
        state = candidate_state[remote_id]
        target = Path(result["target_path"])

        def report_index(value: int, message: str, state=state, candidate=candidate) -> None:
            if control_callback:
                control_callback()
            current_progress = min(max(int(value or 0), 0), 100)
            state["install_progress"] = current_progress
            emit_progress(
                50 + install_phase_progress(installed_count, current_progress) * 0.5,
                message,
                phase="install",
                phase_progress=install_phase_progress(installed_count, current_progress),
                current_file=candidate["file_name"],
                completed_files=installed_count,
                total_files=install_total,
            )

        try:
            result["index"] = index_single_zipmod(
                game_root,
                db_path,
                thumbnail_dir,
                target,
                report_index,
            )
            state["install_progress"] = 100.0
            installed_count += 1
            completed_by_id[remote_id] = result
        except RemoteDownloadCancelled:
            raise
        except Exception as error:
            state["install_progress"] = 100.0
            failures_by_id[remote_id] = {
                "remote_id": remote_id,
                "guid": candidate["guid"],
                "file_name": candidate["file_name"],
                "error": str(error),
            }
        processed_install_count += 1
        emit_progress(
            50 + install_phase_progress(processed_install_count, 0) * 0.5,
            f"Installed {installed_count}/{install_total} remote mods",
            phase="install",
            phase_progress=install_phase_progress(processed_install_count),
            current_file=candidate["file_name"],
            completed_files=installed_count,
            total_files=install_total,
        )

    completed = [
        completed_by_id[int(candidate["remote_id"])]
        for candidate in candidates
        if int(candidate["remote_id"]) in completed_by_id
    ]
    failures = [
        failures_by_id[int(candidate["remote_id"])]
        for candidate in candidates
        if int(candidate["remote_id"]) in failures_by_id
    ]

    affected_mod_guids = sorted(
        {
            normalize_guid(
                (result.get("index") or {}).get("guid") or result.get("guid")
            )
            for result in completed
            if normalize_guid(
                (result.get("index") or {}).get("guid") or result.get("guid")
            )
        }
    )
    return {
        "ok": not failures,
        "selected_count": len(candidates),
        "completed_count": len(completed),
        "failure_count": len(failures),
        "affected_mod_guids": affected_mod_guids,
        "completed": completed,
        "failures": failures,
        "downloaded_bytes": sum(item["done"] for item in candidate_state.values()),
        "total_bytes": sum(item["expected"] for item in candidate_state.values()),
        "installed_count": len(completed),
        "message": f"Completed installation of {len(completed)} of {len(candidates)} remote mod(s).",
        "finished_at": utc_now(),
    }
