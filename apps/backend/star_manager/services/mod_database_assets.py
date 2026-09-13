from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote
import xml.etree.ElementTree as ET

from star_manager.core.runtime_paths import runtime_root
from star_manager.services.mod_database_core import (
    CsvItem,
    DEFAULT_DB_PATH,
    DEFAULT_THUMBNAIL_DIR,
    ManifestData,
    ThumbnailResult,
    Unity3dProvider,
    Unity3dStatus,
    VENDOR_DIR,
    ZipmodCandidate,
    init_db,
    timestamp_to_utc,
    utc_now,
)
from star_manager.services.trash import move_to_trash

if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

try:
    import UnityPy  # type: ignore
except ImportError:
    UnityPy = None  # type: ignore


THUMBNAIL_PROFILE_LOG_PATH = runtime_root() / "thumbnail_profile.log"
_THUMBNAIL_PROFILE_LOCK = threading.Lock()
_THUMBNAIL_PROFILE_CURRENT_PATH = THUMBNAIL_PROFILE_LOG_PATH
_THUMBNAIL_PROFILE_RUN_ID = ""
_THUMBNAIL_PROFILE_SEQUENCE = 0

KPLUG_MAP_CSV_PATH = "abdata/studio/info/kplug/map_kplug.csv"
MAP_SCENE_KIND = "__map_scene__"
GAME_MAP_SCENE_KIND = "__game_map_scene__"
DUAL_MAP_SCENE_KIND = "__game_studio_map_scene__"
GAME_MAPINFO_PREFIX = "abdata/map/list/mapinfo/"


def thumbnail_profile_path_for_run(started_at: str, run_id: str) -> Path:
    safe_started_at = re.sub(r"[^0-9A-Za-z]+", "", started_at)[:15] or "run"
    safe_run_id = re.sub(r"[^0-9A-Za-z]+", "", run_id)[:12] or uuid.uuid4().hex[:12]
    return runtime_root() / f"thumbnail_profile_{safe_started_at}_{safe_run_id}.jsonl"


def begin_thumbnail_profile(record: dict) -> Path:
    global _THUMBNAIL_PROFILE_CURRENT_PATH
    global _THUMBNAIL_PROFILE_RUN_ID
    global _THUMBNAIL_PROFILE_SEQUENCE

    run_id = str(record.get("run_id") or uuid.uuid4().hex)
    started_at = str(record.get("started_at") or utc_now())
    log_path = thumbnail_profile_path_for_run(started_at, run_id)
    record = dict(record)
    record["run_id"] = run_id

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with _THUMBNAIL_PROFILE_LOCK:
            _THUMBNAIL_PROFILE_CURRENT_PATH = log_path
            _THUMBNAIL_PROFILE_RUN_ID = run_id
            _THUMBNAIL_PROFILE_SEQUENCE = 0
            with log_path.open("w", encoding="utf-8") as log_file:
                log_file.write(
                    json.dumps(_thumbnail_profile_record(record), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
    except OSError:
        return log_path
    return log_path


def _thumbnail_profile_record(record: dict) -> dict:
    global _THUMBNAIL_PROFILE_SEQUENCE

    _THUMBNAIL_PROFILE_SEQUENCE += 1
    enriched = dict(record)
    enriched.setdefault("run_id", _THUMBNAIL_PROFILE_RUN_ID)
    enriched.setdefault("recorded_at", utc_now())
    enriched.setdefault("sequence", _THUMBNAIL_PROFILE_SEQUENCE)
    thread = threading.current_thread()
    enriched.setdefault("thread_name", thread.name)
    enriched.setdefault("thread_id", thread.ident)
    return enriched


def write_thumbnail_profile(record: dict) -> None:
    try:
        log_path = _THUMBNAIL_PROFILE_CURRENT_PATH
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with _THUMBNAIL_PROFILE_LOCK:
            with log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    json.dumps(_thumbnail_profile_record(record), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
    except OSError:
        return


def _replace_mod_items(
    conn: sqlite3.Connection,
    game_dir: Path,
    zipmod_id: int,
    candidate: ZipmodCandidate,
    thumbnail_dir: Path,
    now: str,
):
    from star_manager.services.mod_database import prepare_mod_items, replace_mod_items

    prepared = prepare_mod_items(game_dir, candidate, thumbnail_dir)
    return replace_mod_items(conn, zipmod_id, candidate, prepared, now)


def find_zipmods(
    game_dir: Path,
    progress_callback: Callable[[int], None] | None = None,
) -> list[Path]:
    mods_dir = game_dir / "mods"
    if not mods_dir.exists():
        return []
    paths: list[Path] = []
    for path in mods_dir.rglob("*.zipmod"):
        if not path.is_file():
            continue
        paths.append(path)
        if progress_callback is not None and (len(paths) == 1 or len(paths) % 100 == 0):
            progress_callback(len(paths))
    return sorted(paths)


def read_manifest(zipmod_path: Path) -> ManifestData:
    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            names = set(zf.namelist())
            if "manifest.xml" not in names:
                return ManifestData("", "", "", "", "missing_manifest", "manifest.xml not found")
            with zf.open("manifest.xml") as manifest_file:
                root = ET.parse(manifest_file).getroot()
    except zipfile.BadZipFile as exc:
        return ManifestData("", "", "", "", "read_error", f"bad zip file: {exc}")
    except (OSError, ET.ParseError) as exc:
        return ManifestData("", "", "", "", "invalid_manifest", str(exc))

    def text(name: str) -> str:
        element = root.find(name)
        return (element.text or "").strip() if element is not None else ""

    guid = text("guid")
    if not guid:
        return ManifestData("", text("name"), text("version"), text("author"), "invalid_manifest", "guid missing")
    author = text("author")
    if not author:
        return ManifestData(guid, text("name"), text("version"), "", "ok", "")
    return ManifestData(guid, text("name"), text("version"), author, "ok", "")


def inspect_zipmod_archive(zipmod_path: Path) -> tuple[bool, str]:
    """Check whether an archive has the minimum standard zipmod layout."""
    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            members = zf.infolist()
            exact_names = {info.filename for info in members}
            normalized_names = {
                normalize_zip_path(info.filename).casefold()
                for info in members
                if not info.is_dir()
            }
            if "manifest.xml" not in exact_names:
                return False, "manifest.xml not found at the archive root"
            if not any(name.startswith("abdata/") for name in normalized_names):
                return False, "abdata content not found"
            with zf.open("manifest.xml") as manifest_file:
                root = ET.parse(manifest_file).getroot()
            if str(root.tag or "").strip().casefold() != "manifest":
                return False, "manifest.xml root element is not manifest"
    except zipfile.BadZipFile as exc:
        return False, f"bad zip file: {exc}"
    except (OSError, ET.ParseError) as exc:
        return False, str(exc)

    manifest = read_manifest(zipmod_path)
    if manifest.scan_status != "ok" or not manifest.guid:
        return False, manifest.scan_error or "manifest guid missing"
    return True, ""


def _manifest_fields_from_root(root: ET.Element) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    seen: set[str] = set()
    for child in list(root):
        if not isinstance(child.tag, str):
            continue
        key = child.tag.strip()
        if not key or key in seen:
            continue
        fields.append({"key": key, "value": (child.text or "").strip()})
        seen.add(key)

    for key in ("guid", "name", "version", "author"):
        if key not in seen:
            fields.append({"key": key, "value": ""})
            seen.add(key)
    return fields


def _zipmod_row_payload(conn: sqlite3.Connection, zipmod_id: int) -> dict:
    row = conn.execute(
        """
        SELECT id, scan_status, name, author, version, item_count,
               unity3d_status, unity3d_not_in_mod_count, unity3d_in_mod_count,
               unity3d_in_game_count, unity3d_other_mod_count,
               unity3d_missing_count, unity3d_error, guid,
               file_name, relative_path, file_path, last_scanned_at, scan_error,
               (
                   SELECT COUNT(*)
                   FROM duplicate_zipmods d
                   WHERE d.guid = zipmods.guid
               ) AS duplicate_zipmod_count
        FROM zipmods
        WHERE id = ?
        """,
        (zipmod_id,),
    ).fetchone()
    if row is None:
        return {}
    return {
        "id": row["id"],
        "status": row["scan_status"],
        "name": row["name"] or row["file_name"],
        "author": row["author"] or "未知作者",
        "version": row["version"],
        "item_count": row["item_count"],
        "duplicate_zipmod_count": row["duplicate_zipmod_count"],
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


def build_candidates(
    game_dir: Path,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> list[ZipmodCandidate]:
    mods_dir = game_dir / "mods"
    candidates: list[ZipmodCandidate] = []

    def report_discovered(count: int) -> None:
        if progress_callback is not None:
            progress_callback("discover", count, 0)

    zipmod_paths = find_zipmods(game_dir, report_discovered)
    total = len(zipmod_paths)
    if progress_callback is not None:
        progress_callback("discover_done", total, total)

    for index, path in enumerate(zipmod_paths, start=1):
        stat = path.stat()
        manifest = read_manifest(path)
        relative_path = path.relative_to(mods_dir).as_posix()
        candidates.append(
            ZipmodCandidate(
                manifest=manifest,
                path=path.resolve(),
                relative_path=relative_path,
                file_size=stat.st_size,
                modified_at=timestamp_to_utc(stat.st_mtime),
            )
        )
        if progress_callback is not None and (
            index == total or index == 1 or index % 100 == 0
        ):
            progress_callback("manifest", index, total)
    return candidates


def get_existing_paths(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        row["guid"]: row["file_path"]
        for row in conn.execute("SELECT guid, file_path FROM zipmods")
    }


def choose_primary(
    candidates: list[ZipmodCandidate], existing_paths: dict[str, str]
) -> ZipmodCandidate:
    existing_path = existing_paths.get(candidates[0].manifest.guid)
    if existing_path:
        for candidate in candidates:
            if str(candidate.path) == existing_path:
                return candidate
    return sorted(
        candidates,
        key=lambda item: (-item.path.stat().st_mtime, -item.file_size, str(item.path).lower()),
    )[0]


def group_valid_candidates(
    candidates: Iterable[ZipmodCandidate],
) -> tuple[dict[str, list[ZipmodCandidate]], list[ZipmodCandidate]]:
    grouped: dict[str, list[ZipmodCandidate]] = {}
    invalid: list[ZipmodCandidate] = []
    for candidate in candidates:
        if candidate.manifest.guid:
            grouped.setdefault(candidate.manifest.guid, []).append(candidate)
        else:
            invalid.append(candidate)
    return grouped, invalid


def upsert_zipmod(conn: sqlite3.Connection, candidate: ZipmodCandidate, now: str) -> int:
    manifest = candidate.manifest
    conn.execute(
        """
        INSERT INTO zipmods (
            guid, name, version, author, file_path, relative_path, file_name,
            file_size, modified_at,
            scan_status, scan_error, last_scanned_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(guid) DO UPDATE SET
            name = excluded.name,
            version = excluded.version,
            author = excluded.author,
            file_path = excluded.file_path,
            relative_path = excluded.relative_path,
            file_name = excluded.file_name,
            file_size = excluded.file_size,
            modified_at = excluded.modified_at,
            scan_status = excluded.scan_status,
            scan_error = excluded.scan_error,
            last_scanned_at = excluded.last_scanned_at,
            updated_at = excluded.updated_at
        """,
        (
            manifest.guid,
            manifest.name,
            manifest.version,
            manifest.author,
            str(candidate.path),
            candidate.relative_path,
            candidate.path.name,
            candidate.file_size,
            candidate.modified_at,
            manifest.scan_status,
            manifest.scan_error,
            now,
            now,
            now,
        ),
    )
    row = conn.execute("SELECT id FROM zipmods WHERE guid = ?", (manifest.guid,)).fetchone()
    return int(row["id"])


def replace_duplicate_records(
    conn: sqlite3.Connection,
    primary_id: int,
    guid: str,
    duplicates: Iterable[ZipmodCandidate],
    now: str,
) -> int:
    conn.execute("DELETE FROM duplicate_zipmods WHERE guid = ?", (guid,))
    count = 0
    for candidate in duplicates:
        conn.execute(
            """
            INSERT INTO duplicate_zipmods (
                guid, primary_zipmod_id, file_path, relative_path, file_name,
                version, author, file_size, modified_at, reason, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'duplicate_guid', ?, ?)
            """,
            (
                guid,
                primary_id,
                str(candidate.path),
                candidate.relative_path,
                candidate.path.name,
                candidate.manifest.version,
                candidate.manifest.author,
                candidate.file_size,
                candidate.modified_at,
                now,
                now,
            ),
        )
        count += 1
    return count


def upsert_invalid_zipmod(conn: sqlite3.Connection, invalid: ZipmodCandidate, now: str) -> None:
    conn.execute(
        """
        INSERT INTO zipmods (
            guid, name, version, author, file_path, relative_path, file_name,
            file_size, modified_at, item_count, unity3d_status, unity3d_not_in_mod_count,
            unity3d_in_mod_count, unity3d_in_game_count, unity3d_other_mod_count,
            unity3d_missing_count, unity3d_error, scan_status, scan_error,
            last_scanned_at, created_at, updated_at
        )
        VALUES (?, '', '', '', ?, ?, ?, ?, ?, 0, '', 0, 0, 0, 0, 0, '', ?, ?, ?, ?, ?)
        ON CONFLICT(guid) DO UPDATE SET
            file_path = excluded.file_path,
            relative_path = excluded.relative_path,
            file_name = excluded.file_name,
            file_size = excluded.file_size,
            modified_at = excluded.modified_at,
            item_count = excluded.item_count,
            unity3d_status = excluded.unity3d_status,
            unity3d_not_in_mod_count = excluded.unity3d_not_in_mod_count,
            unity3d_in_mod_count = excluded.unity3d_in_mod_count,
            unity3d_in_game_count = excluded.unity3d_in_game_count,
            unity3d_other_mod_count = excluded.unity3d_other_mod_count,
            unity3d_missing_count = excluded.unity3d_missing_count,
            unity3d_error = excluded.unity3d_error,
            scan_status = excluded.scan_status,
            scan_error = excluded.scan_error,
            last_scanned_at = excluded.last_scanned_at,
            updated_at = excluded.updated_at
        """,
        (
            f"__invalid__:{invalid.path}",
            str(invalid.path),
            invalid.relative_path,
            invalid.path.name,
            invalid.file_size,
            invalid.modified_at,
            invalid.manifest.scan_status,
            invalid.manifest.scan_error,
            now,
            now,
            now,
        ),
    )


def remove_unseen_zipmods(conn: sqlite3.Connection, seen_guids: set[str]) -> int:
    if not seen_guids:
        result = conn.execute("DELETE FROM zipmods")
        return result.rowcount

    placeholders = ",".join("?" for _ in seen_guids)
    result = conn.execute(
        f"""
        DELETE FROM zipmods
        WHERE guid NOT IN ({placeholders})
        """,
        sorted(seen_guids),
    )
    return result.rowcount


def decode_csv_bytes(data: bytes) -> str:
    encoding, text = decode_csv_bytes_with_encoding(data)
    return text


def decode_csv_bytes_with_encoding(data: bytes) -> tuple[str, str]:
    candidates: list[tuple[int, int, str, str]] = []
    for index, encoding in enumerate(
        (
            "utf-8-sig",
            "utf-8",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "cp932",
            "gb18030",
        )
    ):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        candidates.append((csv_decode_score(text), index, encoding, text))
    if candidates:
        _score, _index, encoding, text = min(candidates)
        return encoding, text
    return "utf-8", data.decode("utf-8", errors="replace")


def csv_decode_score(text: str) -> int:
    score = 0
    private_use_count = sum(1 for char in text if "\ue000" <= char <= "\uf8ff")
    halfwidth_kana_count = sum(1 for char in text if "\uff61" <= char <= "\uff9f")
    replacement_count = text.count("\ufffd")
    control_count = sum(
        1
        for char in text
        if ord(char) < 32 and char not in {"\t", "\r", "\n"}
    )
    score += private_use_count * 100
    score += halfwidth_kana_count * 10
    score += replacement_count * 100
    score += control_count * 50

    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error:
        return score + 1000

    header_index = find_header_index(rows)
    if header_index is None:
        score += 200
    else:
        header = {cell.strip() for cell in rows[header_index]}
        expected_columns = {
            "ID",
            "Name",
            "MainAB",
            "MainData",
            "TexAB",
            "ThumbAB",
            "ThumbTex",
        }
        score -= len(header & expected_columns) * 5

    return score


def find_header_index(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        columns = {cell.strip() for cell in row}
        if {"ID", "Name"}.issubset(columns):
            return index
    return None


def value(row_map: dict[str, str], key: str) -> str:
    return (row_map.get(key) or "").strip()


def value_any(row_map: dict[str, str], keys: Iterable[str]) -> str:
    for key in keys:
        current = value(row_map, key)
        if current:
            return current
    return ""


def read_items_from_csv(csv_path: str, data: bytes) -> list[CsvItem]:
    try:
        text = decode_csv_bytes(data)
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        return [
            CsvItem(csv_path, "", "", "", "", "", "", "", "", "parse_error", str(exc))
        ]

    header_index = find_header_index(rows)
    if header_index is None:
        return [
            CsvItem(csv_path, "", "", "", "", "", "", "", "", "missing_header", "ID and Name header not found")
        ]

    list_kind = rows[0][0].strip() if rows and rows[0] else ""

    header = [cell.strip() for cell in rows[header_index]]
    items: list[CsvItem] = []
    for row in rows[header_index + 1 :]:
        if not row or all(not cell.strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        row_map = dict(zip(header, padded))
        item_id = value(row_map, "ID")
        if not item_id:
            items.append(
                CsvItem(csv_path, "", "", value(row_map, "Name"), "", "", "", "", "", "short_row", "ID missing")
            )
            continue
        items.append(
            CsvItem(
                csv_path=csv_path,
                item_id=item_id,
                kind=list_kind,
                name=value(row_map, "Name"),
                main_manifest=value_any(row_map, ("MainManifest", "MainTexManifest")),
                main_ab=value_any(row_map, ("MainAB", "MainTexAB")),
                main_data=value_any(row_map, ("MainData", "MainTex", "AddTex", "GlossTex")),
                tex_ab=value(row_map, "TexAB"),
                thumb_ab=value(row_map, "ThumbAB"),
                thumb_tex=value(row_map, "ThumbTex"),
                parse_status="ok",
                parse_error="",
            )
        )
    return items


def read_kplug_map_items(
    csv_path: str,
    data: bytes,
    kind: str = MAP_SCENE_KIND,
    display_name: str = "",
    thumbnail_references: list[tuple[str, str]] | None = None,
) -> list[CsvItem]:
    """Read kPlug MAPMOD registrations as read-only map-scene index items."""
    try:
        text = decode_csv_bytes(data)
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error:
        return []

    items: list[CsvItem] = []
    map_number = 0
    for row in rows:
        if not row or not any(cell.strip() for cell in row):
            continue
        if row[0].strip().upper() == "MAPMOD":
            continue
        if len(row) < 5:
            continue
        bundle_path = row[2].strip()
        if not bundle_path.lower().endswith(".unity3d"):
            continue
        map_number += 1
        map_id = row[0].strip()
        registered_name = row[3].strip()
        is_scene_alias = bool(re.fullmatch(r"scene\d*", registered_name, flags=re.IGNORECASE))
        map_name = (
            (display_name if is_scene_alias else registered_name)
            or row[1].strip()
            or f"地图场景 {map_number}"
        )
        thumb_ab, thumb_tex = (thumbnail_references or [])[map_number - 1] if (
            thumbnail_references and map_number <= len(thumbnail_references)
        ) else ("", "")
        items.append(
            CsvItem(
                csv_path=csv_path,
                item_id=f"kplug-map:{map_number}:{map_id or 'default'}",
                kind=kind,
                name=map_name,
                main_manifest=row[4].strip() or "abdata",
                main_ab=bundle_path,
                main_data=row[1].strip(),
                thumb_ab=thumb_ab,
                thumb_tex=thumb_tex,
                parse_status="ok",
                parse_error="",
            )
        )
    return items


def is_map_scene_item(item: CsvItem) -> bool:
    return item.kind in {MAP_SCENE_KIND, GAME_MAP_SCENE_KIND, DUAL_MAP_SCENE_KIND}


def read_game_mapinfo_items(
    mapinfo_paths: Iterable[str],
    display_name: str = "",
    thumbnail_references: list[tuple[str, str]] | None = None,
) -> list[CsvItem]:
    items: list[CsvItem] = []
    for index, path in enumerate(sorted(mapinfo_paths), start=1):
        normalized = normalize_zip_path(path)
        relative_path = normalized.removeprefix("abdata/")
        fallback_name = Path(relative_path).stem.replace("_mapdata_000", "")
        thumb_ab, thumb_tex = (thumbnail_references or [])[index - 1] if (
            thumbnail_references and index <= len(thumbnail_references)
        ) else ("", "")
        items.append(
            CsvItem(
                csv_path=normalized,
                item_id=f"game-map:{index}",
                kind=GAME_MAP_SCENE_KIND,
                name=display_name or fallback_name or f"游戏本体地图 {index}",
                main_manifest="abdata",
                main_ab=relative_path,
                main_data="mapinfo.asset",
                thumb_ab=thumb_ab,
                thumb_tex=thumb_tex,
                parse_status="ok",
                parse_error="",
            )
        )
    return items


def read_game_mapinfo_thumbnail_references(
    zf: zipfile.ZipFile,
    mapinfo_paths: Iterable[str],
) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    if UnityPy is None:
        return references

    for path in sorted(mapinfo_paths):
        try:
            env = UnityPy.load(zf.read(path))
            behaviour = next(
                (item for item in env.objects if item.type.name == "MonoBehaviour"),
                None,
            )
            if behaviour is None:
                continue
            payload = behaviour.read_typetree()
            parameters = payload.get("param") or []
            parameter = parameters[0] if parameters else {}
            thumb_ab = str(parameter.get("ThumbnailBundle_S") or "").strip()
            thumb_tex = str(parameter.get("ThumbnailAsset_S") or "").strip()
            references.append((thumb_ab, thumb_tex))
        except Exception:  # MapInfo metadata is optional for map recognition.
            references.append(("", ""))
    return references


def iter_open_zip_csv_items(
    zf: zipfile.ZipFile,
    map_display_name: str = "",
) -> Iterable[CsvItem]:
    names = sorted(zf.namelist())
    normalized_names = [name.replace("\\", "/") for name in names]
    mapinfo_paths = [
        name
        for name in normalized_names
        if name.lower().startswith(GAME_MAPINFO_PREFIX) and name.lower().endswith(".unity3d")
    ]
    has_kplug_map = any(name.lower() == KPLUG_MAP_CSV_PATH for name in normalized_names)
    thumbnail_references = read_game_mapinfo_thumbnail_references(zf, mapinfo_paths)
    for name in names:
        normalized = name.replace("\\", "/")
        if normalized.lower() == KPLUG_MAP_CSV_PATH:
            try:
                kind = DUAL_MAP_SCENE_KIND if mapinfo_paths else MAP_SCENE_KIND
                yield from read_kplug_map_items(
                    normalized,
                    zf.read(name),
                    kind,
                    map_display_name,
                    thumbnail_references,
                )
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                yield CsvItem(normalized, "", MAP_SCENE_KIND, "", "", "", "", "", "", "parse_error", str(exc))
            continue
        if not normalized.lower().startswith("abdata/list/"):
            continue
        if not normalized.lower().endswith(".csv"):
            continue
        try:
            yield from read_items_from_csv(normalized, zf.read(name))
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            yield CsvItem(normalized, "", "", "", "", "", "", "", "", "parse_error", str(exc))

    if mapinfo_paths and not has_kplug_map:
        yield from read_game_mapinfo_items(
            mapinfo_paths,
            map_display_name,
            thumbnail_references,
        )


def iter_zip_csv_items(zipmod_path: Path) -> Iterable[CsvItem]:
    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            yield from iter_open_zip_csv_items(zf)
    except (OSError, zipfile.BadZipFile) as exc:
        yield CsvItem("", "", "", "", "", "", "", "", "", "parse_error", str(exc))


def normalize_zip_path(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("/")


def normalize_abdata_path(root: str, path: str) -> str:
    path = normalize_zip_path(path)
    if not path:
        return ""
    if path.lower().startswith("abdata/"):
        return path
    return f"abdata/{path}"


def is_image_path(path: str) -> bool:
    return Path(path.lower()).suffix in {".png", ".jpg", ".jpeg", ".tga"}


def is_unity3d_path(path: str) -> bool:
    return Path(path.lower()).suffix == ".unity3d"


def unity3d_member_signatures(
    zipmod_path: Path,
    referenced_paths: Iterable[str] | None = None,
) -> tuple[dict[str, dict[str, object]], str]:
    signatures: dict[str, dict[str, object]] = {}
    wanted = {
        normalize_zip_path(path).lower()
        for path in (referenced_paths or [])
        if normalize_zip_path(str(path or ""))
    }
    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            for info in zf.infolist():
                normalized = normalize_zip_path(info.filename)
                if not is_unity3d_path(normalized):
                    continue
                key = normalized.lower()
                if wanted and key not in wanted:
                    continue
                signatures[key] = {
                    "crc": int(info.CRC),
                    "size": int(info.file_size),
                    "modified": "%04d-%02d-%02d %02d:%02d:%02d" % info.date_time,
                    "modified_key": tuple(int(part) for part in info.date_time),
                }
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        return {}, str(exc)
    return signatures, ""


def thumbnail_cache_path(
    thumbnail_dir: Path, zipmod_guid: str, item_id: str, thumb_ab: str, thumb_tex: str
) -> Path:
    key = hashlib.sha1(
        f"{zipmod_guid}|{item_id}|{thumb_ab}|{thumb_tex}".encode("utf-8", errors="replace")
    ).hexdigest()
    return thumbnail_dir / key[:2] / key[2:4] / f"{key}.png"


class ZipMemberIndex:
    def __init__(self, zf: zipfile.ZipFile):
        self.members_by_key: dict[str, str] = {}
        self.directory_keys: set[str] = set()
        self.directory_names_by_key: dict[str, str] = {}
        for name in zf.namelist():
            normalized = normalize_zip_path(name)
            for key in zip_path_match_keys(normalized):
                self.members_by_key.setdefault(key, name)

            current = Path(normalized).parent.as_posix()
            while current not in {"", "."}:
                current = normalize_zip_path(current).rstrip("/")
                for key in zip_path_match_keys(current):
                    directory_key = key.rstrip("/")
                    if directory_key:
                        self.directory_keys.add(directory_key)
                        self.directory_names_by_key.setdefault(directory_key, current)
                next_current = Path(current).parent.as_posix()
                if next_current == current:
                    break
                current = next_current

    def find_member(self, normalized_path: str) -> str | None:
        for key in zip_path_match_keys(normalized_path):
            member = self.members_by_key.get(key)
            if member is not None:
                return member
        return None

    def find_directory(self, normalized_path: str) -> str | None:
        target_keys = {key.rstrip("/") for key in zip_path_match_keys(normalized_path)}
        target_keys.discard("")
        if not target_keys:
            return None
        for target in target_keys:
            directory = self.directory_names_by_key.get(target)
            if directory is not None:
                return directory
        for target in target_keys:
            prefix = f"{target}/"
            if any(directory_key.startswith(prefix) for directory_key in self.directory_keys):
                return normalize_zip_path(normalized_path).rstrip("/")
        return None


def _unity3d_provider_entries(zf: zipfile.ZipFile) -> list[tuple[str, str, str, str]]:
    """Return lookup keys for Unity3D files and directory-backed bundles in one archive."""
    entries: dict[tuple[str, str], tuple[str, str, str]] = {}
    directory_index = ZipMemberIndex(zf)

    for member_name in zf.namelist():
        normalized = normalize_zip_path(member_name)
        if not normalized.casefold().startswith("abdata/"):
            continue
        if not is_unity3d_path(normalized):
            continue
        for key in zip_path_match_keys(normalized):
            entries.setdefault((key, "file"), (normalized, member_name, "file"))

    for directory_name in set(directory_index.directory_names_by_key.values()):
        normalized = normalize_zip_path(directory_name).rstrip("/")
        if not normalized.casefold().startswith("abdata/") or not normalized:
            continue
        for key in zip_path_match_keys(normalized):
            entries.setdefault((key, "directory"), (normalized, normalized, "directory"))

    return [
        (key, resource_path, member_path, source_kind)
        for (key, source_kind), (resource_path, member_path, _source_kind) in entries.items()
    ]


def load_unity3d_provider_index(conn: sqlite3.Connection) -> dict[str, list[Unity3dProvider]]:
    providers: dict[str, list[Unity3dProvider]] = {}
    for row in conn.execute(
        """
        SELECT zipmod_path, relative_path, guid, resource_key, resource_path,
               member_path, source_kind
        FROM unity3d_providers
        ORDER BY resource_key, zipmod_path COLLATE NOCASE
        """
    ):
        providers.setdefault(str(row["resource_key"]), []).append(
            Unity3dProvider(
                zipmod_path=str(row["zipmod_path"]),
                relative_path=str(row["relative_path"] or ""),
                guid=str(row["guid"] or ""),
                resource_path=str(row["resource_path"] or ""),
                member_path=str(row["member_path"] or ""),
                source_kind=str(row["source_kind"] or "file"),
            )
        )
    return providers


def refresh_unity3d_provider_index(
    conn: sqlite3.Connection,
    candidates: Iterable[ZipmodCandidate],
    now: str,
    force_full: bool = False,
) -> tuple[dict[str, list[Unity3dProvider]], bool, set[str]]:
    """Refresh the archive-level Unity3D provider index incrementally."""
    candidate_list = list(candidates)
    current_paths = {str(candidate.path.resolve()) for candidate in candidate_list}
    existing = {
        str(row["zipmod_path"]): row
        for row in conn.execute("SELECT * FROM unity3d_provider_archives")
    }
    changed = False
    changed_resource_keys: set[str] = set()
    if set(existing) != current_paths:
        changed = True
        obsolete_paths = set(existing) - current_paths
        if obsolete_paths:
            placeholders = ", ".join("?" for _ in obsolete_paths)
            changed_resource_keys.update(
                str(row["resource_key"])
                for row in conn.execute(
                    f"SELECT resource_key FROM unity3d_providers WHERE zipmod_path IN ({placeholders})",
                    tuple(sorted(obsolete_paths)),
                )
            )
    for candidate in candidate_list:
        zipmod_path = str(candidate.path.resolve())
        stat_matches = (
            not force_full
            and zipmod_path in existing
            and int(existing[zipmod_path]["file_size"] or 0) == int(candidate.file_size)
            and str(existing[zipmod_path]["modified_at"] or "") == str(candidate.modified_at)
        )
        if stat_matches:
            continue

        changed = True
        changed_resource_keys.update(
            str(row["resource_key"])
            for row in conn.execute(
                "SELECT resource_key FROM unity3d_providers WHERE zipmod_path = ?",
                (zipmod_path,),
            )
        )
        conn.execute("DELETE FROM unity3d_providers WHERE zipmod_path = ?", (zipmod_path,))
        scan_status = "ok"
        scan_error = ""
        entries: list[tuple[str, str, str, str]] = []
        try:
            with zipfile.ZipFile(candidate.path, "r") as zf:
                entries = _unity3d_provider_entries(zf)
        except (OSError, zipfile.BadZipFile) as exc:
            scan_status = "error"
            scan_error = str(exc)

        conn.execute(
            """
            INSERT INTO unity3d_provider_archives (
                zipmod_path, relative_path, guid, file_size, modified_at,
                scan_status, scan_error, scanned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(zipmod_path) DO UPDATE SET
                relative_path = excluded.relative_path,
                guid = excluded.guid,
                file_size = excluded.file_size,
                modified_at = excluded.modified_at,
                scan_status = excluded.scan_status,
                scan_error = excluded.scan_error,
                scanned_at = excluded.scanned_at
            """,
            (
                zipmod_path,
                candidate.relative_path,
                candidate.manifest.guid,
                candidate.file_size,
                candidate.modified_at,
                scan_status,
                scan_error,
                now,
            ),
        )
        if entries:
            changed_resource_keys.update(key for key, _resource_path, _member_path, _source_kind in entries)
            conn.executemany(
                """
                INSERT OR IGNORE INTO unity3d_providers (
                    zipmod_path, resource_key, resource_path, member_path,
                    source_kind, relative_path, guid, file_size, modified_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        zipmod_path,
                        key,
                        resource_path,
                        member_path,
                        source_kind,
                        candidate.relative_path,
                        candidate.manifest.guid,
                        candidate.file_size,
                        candidate.modified_at,
                        now,
                    )
                    for key, resource_path, member_path, source_kind in entries
                ),
            )

    if current_paths:
        placeholders = ", ".join("?" for _ in current_paths)
        conn.execute(
            f"DELETE FROM unity3d_provider_archives WHERE zipmod_path NOT IN ({placeholders})",
            tuple(sorted(current_paths)),
        )
    else:
        conn.execute("DELETE FROM unity3d_provider_archives")
    conn.execute(
        """
        DELETE FROM unity3d_providers
        WHERE NOT EXISTS (
            SELECT 1 FROM unity3d_provider_archives a
            WHERE a.zipmod_path = unity3d_providers.zipmod_path
        )
        """
    )
    return load_unity3d_provider_index(conn), changed, changed_resource_keys

class UnityThumbnailBundleCache:
    def __init__(self):
        self.bundles: dict[tuple[str, str], UnityThumbnailBundle | ThumbnailResult] = {}

    def load(
        self,
        source_key: tuple[str, str],
        bundle_bytes: bytes,
    ) -> "UnityThumbnailBundle | ThumbnailResult":
        cached = self.bundles.get(source_key)
        if cached is None:
            cached = UnityThumbnailBundle.from_bytes(bundle_bytes)
            self.bundles[source_key] = cached
        return cached

    def extract(
        self,
        source_key: tuple[str, str],
        bundle_bytes: bytes,
        thumb_tex: str,
        output_path: Path,
    ) -> ThumbnailResult:
        cached = self.load(source_key, bundle_bytes)
        if isinstance(cached, ThumbnailResult):
            return cached
        return cached.write_thumbnail(thumb_tex, output_path)


def unity3d_bundle_readability_error(
    zf: zipfile.ZipFile,
    member_name: str,
    bundle_cache: UnityThumbnailBundleCache | None = None,
) -> str:
    if not is_unity3d_path(member_name):
        return ""
    try:
        if UnityPy is None:
            return "UnityPy is not available"
        env = UnityPy.load(zf.read(member_name))
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        return f"Unity3D read failed: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"UnityPy load failed: {exc}"
    if not env.container and not env.objects:
        return "UnityPy loaded no objects"
    return ""


class ThumbnailSourceCache:
    def __init__(self):
        self.results: dict[tuple[str, ...], ThumbnailResult] = {}

    def get(self, source_key: tuple[str, ...], output_path: Path) -> ThumbnailResult | None:
        cached = self.results.get(source_key)
        if cached is None:
            return None
        if cached.status != "ready":
            self.results.pop(source_key, None)
            return None
        if not cached.cache_path:
            self.results.pop(source_key, None)
            return None

        cached_path = Path(cached.cache_path)
        if cached_path == output_path:
            if output_path.exists():
                return cached
            self.results.pop(source_key, None)
            return None
        if not cached_path.is_file():
            self.results.pop(source_key, None)
            return None

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached_path, output_path)
        except OSError:
            self.results.pop(source_key, None)
            return None
        return ThumbnailResult(str(output_path), "ready", "")

    def remember(self, source_key: tuple[str, ...], result: ThumbnailResult) -> None:
        if result.status == "ready":
            self.results[source_key] = result


class UnityThumbnailBundle:
    def __init__(self, images: list[tuple[str, object]], fallback_images: list[tuple[int, object]]):
        self.images = images
        self.fallback_images = fallback_images
        self.images_by_key: dict[str, object] = {}
        for name, image in images:
            for key in asset_lookup_keys(name):
                self.images_by_key.setdefault(key, image)

    @classmethod
    def from_bytes(cls, bundle_bytes: bytes) -> "UnityThumbnailBundle | ThumbnailResult":
        if UnityPy is None:
            return ThumbnailResult("", "error", "UnityPy is not available")

        try:
            env = UnityPy.load(bundle_bytes)
        except Exception as exc:  # noqa: BLE001 - keep indexing resilient.
            return ThumbnailResult("", "error", f"UnityPy load failed: {exc}")

        try:
            if not env.container and not env.objects:
                return ThumbnailResult("", "error", "UnityPy loaded no objects")

            images: list[tuple[str, object]] = []
            fallback_images: list[tuple[int, object]] = []
            for container_path, obj in env.container.items():
                try:
                    data = obj.read()
                    image = getattr(data, "image", None)
                except Exception:  # noqa: BLE001 - skip individual assets UnityPy cannot decode.
                    continue
                if image is None:
                    continue
                name = str(container_path)
                images.append((name, image))
                rank = fallback_thumbnail_rank(name)
                if rank:
                    fallback_images.append((rank, image))

            for obj in env.objects:
                if obj.type.name not in {"Texture2D", "Sprite"}:
                    continue
                try:
                    data = obj.read()
                    image = getattr(data, "image", None)
                except Exception:  # noqa: BLE001 - skip individual assets UnityPy cannot decode.
                    continue
                if image is None:
                    continue
                name = getattr(data, "name", "") or ""
                images.append((str(name), image))
                rank = fallback_thumbnail_rank(str(name))
                if rank:
                    fallback_images.append((rank, image))
            return cls(images, fallback_images)
        except Exception as exc:  # noqa: BLE001 - a broken asset should not abort DB build.
            return ThumbnailResult("", "error", f"thumbnail extract failed: {exc}")

    def write_thumbnail(self, thumb_tex: str, output_path: Path) -> ThumbnailResult:
        image = self.find_image(thumb_tex)
        if image is not None:
            return write_unity_thumbnail_image(image, output_path)
        return ThumbnailResult("", "missing", "thumbnail asset not found")

    def find_image(self, thumb_tex: str) -> object | None:
        for key in asset_lookup_keys(thumb_tex):
            image = self.images_by_key.get(key)
            if image is not None:
                return image
        if self.fallback_images:
            _rank, image = sorted(self.fallback_images, key=lambda item: item[0])[0]
            return image
        return None


def find_zip_member(
    zf: zipfile.ZipFile,
    normalized_path: str,
    index: ZipMemberIndex | None = None,
) -> str | None:
    if index is not None:
        return index.find_member(normalized_path)
    target_keys = zip_path_match_keys(normalized_path)
    for name in zf.namelist():
        if zip_path_match_keys(name) & target_keys:
            return name
    return None


def find_zip_directory(
    zf: zipfile.ZipFile,
    normalized_path: str,
    index: ZipMemberIndex | None = None,
) -> str | None:
    if index is not None:
        return index.find_directory(normalized_path)
    target_keys = {key.rstrip("/") for key in zip_path_match_keys(normalized_path)}
    target_keys.discard("")
    if not target_keys:
        return None
    for name in zf.namelist():
        normalized = normalize_zip_path(name).rstrip("/")
        name_keys = {key.rstrip("/") for key in zip_path_match_keys(normalized)}
        if name_keys & target_keys:
            return normalized
        if any(name_key.startswith(f"{target}/") for name_key in name_keys for target in target_keys):
            return normalize_zip_path(normalized_path).rstrip("/")
    return None


def zip_path_match_keys(path: str) -> set[str]:
    normalized = normalize_zip_path(path)
    if not normalized:
        return set()

    keys = {normalized.lower()}
    try:
        raw_name = normalized.encode("cp437")
    except UnicodeEncodeError:
        return keys

    for encoding in ("gb18030", "cp932"):
        try:
            repaired = raw_name.decode(encoding)
        except UnicodeDecodeError:
            continue
        keys.add(normalize_zip_path(repaired).lower())
    return keys


def unity3d_directory_fallback_path(reference: str) -> str:
    normalized = normalize_zip_path(reference)
    if is_unity3d_path(normalized):
        return normalize_zip_path(str(Path(normalized).with_suffix("")))
    return normalized


def find_zip_unity3d_or_directory(
    zf: zipfile.ZipFile,
    reference: str,
    index: ZipMemberIndex | None = None,
) -> str | None:
    member = find_zip_member(zf, reference, index)
    if member is not None:
        return member
    return find_zip_directory(zf, unity3d_directory_fallback_path(reference), index)


def resolve_game_unity3d_or_directory(game_dir: Path, reference: str) -> Path | None:
    file_path = resolve_game_abdata_path(game_dir, reference)
    if file_path.is_file():
        return file_path
    directory_path = resolve_game_abdata_path(game_dir, unity3d_directory_fallback_path(reference))
    if directory_path.is_dir():
        return directory_path
    return None


def unity3d_reference_paths(item: CsvItem) -> list[str]:
    paths: list[str] = []
    main_path = normalize_abdata_path(item.main_manifest, item.main_ab)
    if main_path and is_unity3d_path(main_path):
        paths.append(main_path)

    tex_path = normalize_abdata_path("abdata", item.tex_ab)
    if tex_path and is_unity3d_path(tex_path):
        paths.append(tex_path)

    thumb_path = normalize_abdata_path("abdata", item.thumb_ab)
    if thumb_path and is_unity3d_path(thumb_path):
        paths.append(thumb_path)

    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        key = path.lower()
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def main_unity3d_reference_paths(item: CsvItem) -> list[str]:
    main_path = normalize_abdata_path(item.main_manifest, item.main_ab)
    if main_path and is_unity3d_path(main_path):
        return [main_path]
    return []


def item_unity3d_reference_roles(item: CsvItem) -> list[tuple[str, str]]:
    """Return distinct MainAB/TexAB references with their CSV roles."""
    references: list[tuple[str, str]] = []
    main_path = normalize_abdata_path(item.main_manifest, item.main_ab)
    if main_path and is_unity3d_path(main_path):
        references.append((main_path, "main"))

    tex_path = normalize_abdata_path("abdata", item.tex_ab)
    if tex_path and is_unity3d_path(tex_path):
        if not main_path or tex_path.casefold() != main_path.casefold():
            references.append((tex_path, "tex"))
    return references


def is_common_game_chara_path(reference: str) -> bool:
    """Whether a game resource path is under the shared chara/00..60 area."""
    normalized = normalize_zip_path(reference).casefold()
    if normalized.startswith("abdata/"):
        normalized = normalized.removeprefix("abdata/")
    parts = normalized.split("/")
    if len(parts) < 3 or parts[0] != "chara":
        return False
    slot = parts[1]
    return len(slot) == 2 and slot.isdigit() and 0 <= int(slot) <= 60


def unity3d_provider_lookup_keys(reference: str) -> set[str]:
    normalized = normalize_abdata_path("abdata", reference)
    keys = set(zip_path_match_keys(normalized))
    if is_unity3d_path(normalized):
        keys.update(zip_path_match_keys(unity3d_directory_fallback_path(normalized)))
    return keys


def find_other_unity3d_providers(
    provider_index: dict[str, list[Unity3dProvider]] | None,
    reference: str,
    current_zipmod_path: str = "",
) -> list[Unity3dProvider]:
    if not provider_index:
        return []
    current_key = str(Path(current_zipmod_path).resolve()).casefold() if current_zipmod_path else ""
    providers: list[Unity3dProvider] = []
    seen_paths: set[str] = set()
    for key in unity3d_provider_lookup_keys(reference):
        for provider in provider_index.get(key, []):
            provider_key = str(Path(provider.zipmod_path).resolve()).casefold()
            if provider_key == current_key or provider_key in seen_paths:
                continue
            seen_paths.add(provider_key)
            providers.append(provider)
    return sorted(providers, key=lambda provider: provider.zipmod_path.casefold())


def item_error_unity3d_reference_paths(item: CsvItem) -> list[str]:
    return [path for path, _role in item_unity3d_reference_roles(item)]


def find_zip_resource_image(
    zf: zipfile.ZipFile,
    item: CsvItem,
    index: ZipMemberIndex | None = None,
) -> str | None:
    for resource_path in resource_image_candidates(item):
        member = find_zip_member(zf, resource_path, index)
        if member is not None:
            return member
    return None


def thumbnail_image_file_names(thumb_tex: str) -> list[str]:
    texture_name = normalize_zip_path(thumb_tex)
    if not texture_name:
        return []

    candidate_names = {texture_name}
    if not is_image_path(texture_name):
        candidate_names.update(f"{texture_name}{suffix}" for suffix in (".png", ".jpg", ".jpeg", ".tga"))
    return sorted(candidate_names)


def main_ab_thumbnail_image_candidates(item: CsvItem) -> list[str]:
    if not item.main_ab or not item.thumb_tex:
        return []

    main_path = normalize_abdata_path(item.main_manifest, item.main_ab)
    if not main_path:
        return []
    if is_unity3d_path(main_path):
        source_dir = Path(main_path).parent.as_posix()
    else:
        source_dir = unity3d_directory_fallback_path(main_path).rstrip("/")
    if source_dir in {"", "."}:
        return []

    paths = [f"{source_dir}/{name}" for name in thumbnail_image_file_names(item.thumb_tex)]
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        normalized = normalize_zip_path(path)
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def find_zip_direct_image_by_name(
    zf: zipfile.ZipFile,
    thumb_tex: str,
) -> str | None:
    candidate_keys = {normalize_zip_path(name).lower() for name in thumbnail_image_file_names(thumb_tex)}
    if not candidate_keys:
        return None

    matches: list[str] = []
    for name in zf.namelist():
        normalized = normalize_zip_path(name)
        if not normalized.lower().startswith("abdata/") or not is_image_path(normalized):
            continue
        if Path(normalized).name.lower() in candidate_keys:
            matches.append(name)
    if not matches:
        return None
    return sorted(matches, key=lambda value: (len(normalize_zip_path(value)), normalize_zip_path(value).lower()))[0]


def resolve_game_resource_image(game_dir: Path, item: CsvItem) -> Path | None:
    for resource_path in resource_image_candidates(item):
        candidate = game_dir / normalize_zip_path(resource_path)
        if candidate.is_file():
            return candidate
    return None


def resolve_game_abdata_path(game_dir: Path, abdata_path: str) -> Path:
    normalized = normalize_zip_path(abdata_path)
    if normalized.lower().startswith("abdata/"):
        normalized = normalized[len("abdata/") :]
    return game_dir / "abdata" / normalized


def resolve_game_dir_from_zipmod(file_path: str, relative_path: str) -> Path:
    zipmod_path = Path(file_path).resolve()
    relative_parent = Path(relative_path).parent
    mods_dir = zipmod_path.parent
    if str(relative_parent) not in {"", "."}:
        for _part in relative_parent.parts:
            mods_dir = mods_dir.parent
    return mods_dir.parent


def inspect_unity3d_status(
    game_dir: Path,
    zf: zipfile.ZipFile,
    item: CsvItem,
    index: ZipMemberIndex | None = None,
    provider_index: dict[str, list[Unity3dProvider]] | None = None,
    current_zipmod_path: str = "",
) -> Unity3dStatus:
    if item.parse_status != "ok":
        return Unity3dStatus("", "")

    reference_roles = item_unity3d_reference_roles(item)
    references = [path for path, _role in reference_roles]
    if not references:
        if find_zip_resource_image(zf, item, index) is not None:
            return Unity3dStatus("in_mod", "")
        game_resource = resolve_game_resource_image(game_dir, item)
        if game_resource is not None:
            return Unity3dStatus("not_in_mod", f"found in game abdata: {game_resource}", "game_abdata")
        return Unity3dStatus("missing", "no .unity3d path referenced by MainAB")

    found_in_game: list[str] = []
    found_in_other_mod: list[str] = []
    missing: list[str] = []
    for reference, role in reference_roles:
        if find_zip_unity3d_or_directory(zf, reference, index) is not None:
            continue
        game_resource = resolve_game_unity3d_or_directory(game_dir, reference)
        if game_resource is not None:
            if is_common_game_chara_path(reference):
                continue
            found_in_game.append(reference)
        providers = find_other_unity3d_providers(
            provider_index,
            reference,
            current_zipmod_path,
        )
        if providers:
            found_in_other_mod.append(reference)
            continue
        if game_resource is not None:
            continue
        if role == "main":
            missing.append(reference)

    if missing:
        return Unity3dStatus("missing", "missing: " + ", ".join(missing))
    if found_in_other_mod:
        return Unity3dStatus(
            "not_in_mod",
            "provided by other zipmod: " + ", ".join(found_in_other_mod),
            "other_zipmod",
        )
    if found_in_game:
        return Unity3dStatus(
            "not_in_mod",
            "found in game abdata: " + ", ".join(found_in_game),
            "game_abdata",
        )
    return Unity3dStatus("in_mod", "")


def summarize_zipmod_unity3d_status(conn: sqlite3.Connection, zipmod_id: int) -> dict[str, int | str]:
    counts = {"in_mod": 0, "not_in_mod": 0, "in_game": 0, "other_mod": 0, "missing": 0, "error": 0}
    for row in conn.execute(
        """
        SELECT unity3d_status, unity3d_source, COUNT(*) AS count
        FROM mod_items
        WHERE zipmod_id = ? AND unity3d_status != ''
        GROUP BY unity3d_status, unity3d_source
        """,
        (zipmod_id,),
    ):
        status = str(row["unity3d_status"])
        if status in counts:
            counts[status] += int(row["count"])
        if status == "not_in_mod":
            if str(row["unity3d_source"] or "") == "other_zipmod":
                counts["other_mod"] += int(row["count"])
            else:
                counts["in_game"] += int(row["count"])

    if counts["error"]:
        status = "error"
    elif counts["missing"]:
        status = "missing"
    elif counts["not_in_mod"]:
        status = "not_in_mod"
    elif counts["in_mod"]:
        status = "in_mod"
    else:
        status = ""

    missing_examples = [
        row["unity3d_error"]
        for row in conn.execute(
            """
            SELECT unity3d_error
            FROM mod_items
            WHERE zipmod_id = ? AND unity3d_status IN ('missing', 'error') AND unity3d_error != ''
            ORDER BY id
            LIMIT 3
            """,
            (zipmod_id,),
        )
    ]
    error = " | ".join(missing_examples)
    return {
        "status": status,
        "in_mod": counts["in_mod"],
        "not_in_mod": counts["not_in_mod"],
        "in_game": counts["in_game"],
        "other_mod": counts["other_mod"],
        "missing": counts["missing"],
        "error": error,
    }


def zipmod_unity3d_diagnostics(
    zipmod_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (zipmod_id,)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        game_dir = resolve_game_dir_from_zipmod(zipmod["file_path"], zipmod["relative_path"])
        issues_by_path: dict[str, dict] = {}
        item_rows = conn.execute(
            """
               SELECT id, item_id, name, kind, csv_path, main_manifest, main_ab, main_data,
                   tex_ab, thumb_ab, thumb_tex, unity3d_status, unity3d_source, unity3d_error
            FROM mod_items
            WHERE zipmod_id = ? AND unity3d_status IN ('not_in_mod', 'in_game', 'missing', 'error')
            ORDER BY csv_path, item_id
            """,
            (zipmod_id,),
        ).fetchall()

        zipmod_path = Path(zipmod["file_path"])
        provider_index = load_unity3d_provider_index(conn)
        try:
            with zipfile.ZipFile(zipmod_path, "r") as zf:
                zip_index = ZipMemberIndex(zf)
                for item in item_rows:
                    csv_item = CsvItem(
                        csv_path=item["csv_path"],
                        item_id=item["item_id"],
                        kind=item["kind"],
                        name=item["name"],
                        main_manifest=item["main_manifest"],
                        main_ab=item["main_ab"],
                        main_data=item["main_data"],
                        tex_ab=item["tex_ab"],
                        thumb_ab=item["thumb_ab"],
                        thumb_tex=item["thumb_tex"],
                        parse_status="ok",
                        parse_error="",
                    )
                    resolved_status = (
                        Unity3dStatus(
                            str(item["unity3d_status"] or ""),
                            str(item["unity3d_error"] or ""),
                            str(item["unity3d_source"] or ""),
                        )
                        if item["unity3d_status"] == "error"
                        else inspect_unity3d_status(
                            game_dir,
                            zf,
                            csv_item,
                            zip_index,
                            provider_index,
                            str(zipmod_path),
                        )
                    )
                    if (
                        resolved_status.status != item["unity3d_status"]
                        or resolved_status.source != str(item["unity3d_source"] or "")
                        or resolved_status.error != str(item["unity3d_error"] or "")
                    ):
                        conn.execute(
                            """
                            UPDATE mod_items
                            SET unity3d_status = ?, unity3d_source = ?, unity3d_error = ?, updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                resolved_status.status,
                                resolved_status.source,
                                resolved_status.error,
                                utc_now(),
                                item["id"],
                            ),
                        )
                    if resolved_status.status == "in_mod":
                        continue
                    if resolved_status.status == "error":
                        references = main_unity3d_reference_paths(csv_item) or [item["main_ab"] or "__unity3d_error__"]
                        for reference in references:
                            issue = issues_by_path.setdefault(
                                reference,
                                {
                                    "type": "unity3d",
                                    "status": "error",
                                    "path": reference,
                                    "game_path": "",
                                    "affected_count": 0,
                                    "affected_items": [],
                                    "solution": "",
                                    "repair_action": "",
                                },
                            )
                            issue["status"] = "error"
                            issue["affected_count"] += 1
                            if len(issue["affected_items"]) < 8:
                                issue["affected_items"].append(
                                    {
                                        "id": item["id"],
                                        "item_id": item["item_id"],
                                        "name": item["name"],
                                        "csv_path": item["csv_path"],
                                        "error": resolved_status.error,
                                    }
                                )
                        continue
                    for reference, role in item_unity3d_reference_roles(csv_item):
                        if find_zip_unity3d_or_directory(zf, reference) is not None:
                            continue
                        game_path = resolve_game_abdata_path(game_dir, reference)
                        game_resource = resolve_game_unity3d_or_directory(game_dir, reference)
                        providers = find_other_unity3d_providers(
                            provider_index,
                            reference,
                            str(zipmod_path),
                        )
                        if game_resource is None and not providers:
                            if role == "tex":
                                continue
                            status = "missing"
                        else:
                            if is_common_game_chara_path(reference):
                                continue
                            status = "not_in_mod"
                        effective_status = "not_in_mod" if providers or game_resource is not None else status
                        source = (
                            "other_zipmod"
                            if providers
                            else "game_abdata"
                            if game_resource is not None
                            else ""
                        )
                        issue = issues_by_path.setdefault(
                            reference,
                            {
                                "type": "unity3d",
                                "status": "missing" if effective_status == "missing" else "not_in_mod",
                                "path": reference,
                                "game_path": str(game_path) if game_resource is not None else "",
                                "source": source,
                                "other_zipmods": [],
                                "affected_count": 0,
                                "affected_items": [],
                                "solution": "",
                                "repair_action": "",
                            },
                        )
                        issue["status"] = (
                            "missing"
                            if issue["status"] == "missing" or effective_status == "missing"
                            else "not_in_mod"
                        )
                        if providers:
                            issue["source"] = "other_zipmod"
                            issue["game_path"] = str(game_path) if game_resource is not None else issue["game_path"]
                            existing_provider_paths = {
                                str(provider["path"])
                                for provider in issue["other_zipmods"]
                            }
                            for provider in providers:
                                if provider.zipmod_path in existing_provider_paths:
                                    continue
                                issue["other_zipmods"].append(
                                    {
                                        "path": provider.zipmod_path,
                                        "relative_path": provider.relative_path,
                                        "guid": provider.guid,
                                    }
                                )
                        elif game_resource is not None and issue["source"] != "other_zipmod":
                            issue["source"] = "game_abdata"
                        issue["affected_count"] += 1
                        if len(issue["affected_items"]) < 8:
                            issue["affected_items"].append(
                                {
                                    "id": item["id"],
                                    "item_id": item["item_id"],
                                    "name": item["name"],
                                    "csv_path": item["csv_path"],
                                }
                            )
        except (OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "error": f"Cannot read zipmod: {exc}"}

        summary = summarize_zipmod_unity3d_status(conn, zipmod_id)
        conn.execute(
            """
            UPDATE zipmods
            SET unity3d_status = ?,
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
                summary["status"],
                summary["not_in_mod"],
                summary["in_mod"],
                summary["in_game"],
                summary["other_mod"],
                summary["missing"],
                summary["error"],
                utc_now(),
                zipmod_id,
            ),
        )
        conn.commit()
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (zipmod_id,)).fetchone()

        issues = sorted(issues_by_path.values(), key=lambda issue: (issue["status"], issue["path"]))
        for issue in issues:
            if issue["status"] == "error":
                issue["solution"] = "This unity3d file exists in the zipmod, but UnityPy could not parse usable Unity resources from it. Reinstall or replace the source mod, then rebuild the database."
                issue["repair_action"] = ""
            elif issue["status"] == "not_in_mod":
                if issue.get("source") == "other_zipmod":
                    issue["solution"] = "This unity3d file is provided by another zipmod. The current zipmod does not contain its own copy."
                    issue["repair_action"] = ""
                else:
                    issue["solution"] = "Move this unity3d file from game abdata into the zipmod at the CSV-referenced path."
                    issue["repair_action"] = "copy_into_zipmod"
            else:
                issue["solution"] = "Find or reinstall the missing unity3d file, then rebuild the database."
                issue["repair_action"] = ""

        manifest_issue = None
        if not zipmod["author"]:
            manifest_issue = {
                "type": "manifest_author",
                "status": "missing",
                "path": "__manifest_author_missing__",
                "affected_count": 1,
                "affected_items": [
                    {
                        "id": zipmod["id"],
                        "item_id": zipmod["guid"],
                        "name": zipmod["name"] or zipmod["file_name"],
                        "csv_path": "manifest.xml",
                        "author": "",
                    }
                ],
                "solution": "Enter an author name and write it back into manifest.xml.",
                "repair_action": "update_manifest_author",
            }

        duplicate_rows = [
            {
                "id": row["id"],
                "item_id": row["file_name"],
                "name": row["file_name"],
                "csv_path": row["relative_path"],
                "file_path": row["file_path"],
                "version": row["version"],
                "author": row["author"],
                "file_size": row["file_size"],
                "modified_at": row["modified_at"],
            }
            for row in conn.execute(
                """
                SELECT id, file_path, relative_path, file_name, version, author, file_size, modified_at
                FROM duplicate_zipmods
                WHERE guid = ?
                ORDER BY modified_at DESC, file_name COLLATE NOCASE
                """,
                (zipmod["guid"],),
            )
        ]

        thumbnail_items = [
            {
                "id": row["id"],
                "item_id": row["item_id"],
                "name": row["name"],
                "csv_path": row["csv_path"],
                "thumb_ab": row["thumb_ab"],
                "thumb_tex": row["thumb_tex"],
                "thumbnail_status": row["thumbnail_status"],
                "thumbnail_error": row["thumbnail_error"],
                "thumbnail_error_detail": thumbnail_error_detail(row["thumbnail_error"]),
            }
            for row in conn.execute(
                """
                SELECT id, item_id, name, csv_path, thumb_ab, thumb_tex, thumbnail_status, thumbnail_error
                FROM mod_items
                WHERE zipmod_id = ?
                  AND parse_status = 'ok'
                  AND TRIM(COALESCE(kind, '')) NOT IN ('500', '501')
                  AND (thumbnail_status = '' OR thumbnail_status NOT IN ('ready', 'ok'))
                ORDER BY csv_path, item_id
                """,
                (zipmod_id,),
            )
        ]
        if thumbnail_items:
            issues.append(
                {
                    "type": "thumbnail",
                    "status": "missing",
                    "path": "__thumbnail_missing__",
                    "affected_count": len(thumbnail_items),
                    "affected_items": thumbnail_items,
                    "solution": "Choose an image for a single affected item. Star_Manager imports it into the zipmod and updates that item's CSV ThumbAB/ThumbTex fields.",
                    "repair_action": "import_thumbnail",
                }
            )
        if duplicate_rows:
            issues.append(
                {
                    "type": "duplicate_zipmod",
                    "status": "duplicate",
                    "path": "__duplicate_zipmod__",
                    "affected_count": len(duplicate_rows),
                    "affected_items": duplicate_rows,
                    "solution": "Remove the duplicate zipmod files, then keep only the primary record in the library.",
                    "repair_action": "cleanup_duplicate_zipmods",
                }
            )
        if manifest_issue is not None:
            issues.insert(0, manifest_issue)

        return {
            "ok": True,
            "zipmod": {
                "id": zipmod["id"],
                "name": zipmod["name"] or zipmod["file_name"],
                "file_path": zipmod["file_path"],
                "unity3d_status": zipmod["unity3d_status"],
                "unity3d_in_mod_count": zipmod["unity3d_in_mod_count"],
                "unity3d_in_game_count": zipmod["unity3d_in_game_count"],
                "unity3d_missing_count": zipmod["unity3d_missing_count"],
            },
            "can_delete": int(zipmod["unity3d_missing_count"] or 0) > 0
            and int(zipmod["unity3d_in_mod_count"] or 0) == 0
            and int(zipmod["unity3d_in_game_count"] or 0) == 0,
            "issues": issues,
        }
    finally:
        conn.close()


def thumbnail_error_detail(error: str) -> str:
    if not error:
        return "缩略图缓存未生成，数据库没有记录具体错误。"
    if error == "ThumbAB and ThumbTex are empty":
        return "CSV 未填写 ThumbAB/ThumbTex，无法定位缩略图资源。"
    if error == "ThumbTex is empty":
        return "CSV 未填写 ThumbTex，无法定位缩略图贴图资源。"
    if error.startswith("thumbnail source not found: "):
        path = error.removeprefix("thumbnail source not found: ").strip()
        return f"缩略图源文件不存在：{path}"
    if error == "thumbnail asset not found":
        return "缩略图 Unity3D 文件存在，但没有找到 ThumbTex 指向的贴图资源。"
    if error.startswith("UnityPy load failed: "):
        detail = error.removeprefix("UnityPy load failed: ").strip()
        return f"\u7f29\u7565\u56fe Unity3D \u6587\u4ef6\u65e0\u6cd5\u6253\u5f00\u6216\u8bfb\u53d6\u5931\u8d25\uff1a{detail}"
    if error == "UnityPy loaded no objects":
        return "\u7f29\u7565\u56fe Unity3D \u6587\u4ef6\u53ef\u52a0\u8f7d\uff0c\u4f46\u6ca1\u6709\u89e3\u6790\u51fa\u4efb\u4f55\u8d44\u6e90\uff0c\u7591\u4f3c\u6587\u4ef6\u5185\u5bb9\u4e0d\u53ef\u8bfb\u6216\u4e0d\u662f\u6709\u6548\u7684 Unity \u8d44\u6e90\u5305\u3002"
    if error.startswith("thumbnail extract failed: "):
        detail = error.removeprefix("thumbnail extract failed: ").strip()
        return f"缩略图资源提取或解码失败：{detail}"
    if error.startswith("Bad CRC-32"):
        return f"zipmod 内缩略图源文件校验失败：{error}"
    return error


def cleanup_duplicate_zipmods(
    zipmod_id: int,
    duplicate_ids: Iterable[int] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        try:
            ids_set = {int(value) for value in (duplicate_ids or []) if str(value).strip()}
        except (TypeError, ValueError):
            return {"ok": False, "error": "duplicate_ids must contain numeric ids"}
        if duplicate_ids is not None and not ids_set:
            return {"ok": False, "error": "No duplicate ids selected"}
        params: list[object] = [zipmod["guid"]]
        id_filter = ""
        if ids_set:
            placeholders = ",".join("?" for _ in ids_set)
            id_filter = f" AND id IN ({placeholders})"
            params.extend(sorted(ids_set))

        duplicates = conn.execute(
            f"""
            SELECT id, file_path, file_name, relative_path, file_size
            FROM duplicate_zipmods
            WHERE guid = ?{id_filter}
            """,
            params,
        ).fetchall()
        if not duplicates:
            return {"ok": False, "error": "No duplicate zipmods found"}

        removed: list[str] = []
        skipped: list[str] = []
        cleared_ids: list[int] = []
        freed_bytes = 0
        for row in duplicates:
            duplicate_id = int(row["id"])
            dup_path = Path(row["file_path"]).resolve()
            if dup_path.is_file():
                try:
                    trash_record = move_to_trash(
                        dup_path,
                        "mods",
                        name=str(row["file_name"] or dup_path.stem),
                        metadata={
                            "game_dir": resolve_game_dir_from_zipmod(
                                str(dup_path), str(row["relative_path"] or "")
                            ),
                            "relative_path": str(row["relative_path"] or ""),
                            "guid": str(zipmod["guid"] or ""),
                            "reason": "duplicate_cleanup",
                        },
                    )
                    removed.append(str(dup_path))
                    cleared_ids.append(duplicate_id)
                    freed_bytes += int(row["file_size"] or 0)
                except OSError as exc:
                    skipped.append(f"{dup_path}: {exc}")
            else:
                skipped.append(str(dup_path))
                cleared_ids.append(duplicate_id)

        if cleared_ids:
            placeholders = ",".join("?" for _ in cleared_ids)
            with conn:
                conn.execute(
                    f"DELETE FROM duplicate_zipmods WHERE guid = ? AND id IN ({placeholders})",
                    [zipmod["guid"], *cleared_ids],
                )

        return {
            "ok": True,
            "message": f"Removed {len(removed)} duplicate zipmod file(s)",
            "removed": removed,
            "skipped": skipped,
            "cleared_ids": cleared_ids,
            "freed_bytes": freed_bytes,
            "guid": zipmod["guid"],
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def delete_primary_and_promote_duplicate(
    zipmod_id: int,
    duplicate_id: int,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    try:
        duplicate_id = int(duplicate_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "duplicate_id must be numeric"}
    if duplicate_id <= 0:
        return {"ok": False, "error": "duplicate_id must be positive"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        duplicate = conn.execute(
            """
            SELECT *
            FROM duplicate_zipmods
            WHERE id = ? AND guid = ?
            """,
            (duplicate_id, zipmod["guid"]),
        ).fetchone()
        if duplicate is None:
            return {"ok": False, "error": f"Duplicate zipmod not found: {duplicate_id}"}

        promoted_path = Path(str(duplicate["file_path"])).resolve()
        if not promoted_path.is_file():
            return {"ok": False, "error": f"Promoted duplicate file is missing: {promoted_path}"}

        promoted_manifest = read_manifest(promoted_path)
        if promoted_manifest.guid != zipmod["guid"]:
            return {"ok": False, "error": "Promoted duplicate GUID does not match primary GUID"}
        if promoted_manifest.scan_status != "ok":
            return {"ok": False, "error": promoted_manifest.scan_error or promoted_manifest.scan_status}

        stat = promoted_path.stat()
        promoted = ZipmodCandidate(
            manifest=promoted_manifest,
            path=promoted_path,
            relative_path=str(duplicate["relative_path"] or ""),
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        primary_path = Path(str(zipmod["file_path"])).resolve()
        removed_primary_file = False
        if primary_path.is_file():
            move_to_trash(
                primary_path,
                "mods",
                name=str(zipmod["name"] or zipmod["file_name"] or primary_path.stem),
                metadata={
                    "game_dir": resolve_game_dir_from_zipmod(
                        str(primary_path), str(zipmod["relative_path"] or "")
                    ),
                    "relative_path": str(zipmod["relative_path"] or ""),
                    "guid": str(zipmod["guid"] or ""),
                    "reason": "promote_duplicate",
                },
            )
            removed_primary_file = True

        now = utc_now()
        game_dir = resolve_game_dir_from_zipmod(str(promoted.path), promoted.relative_path)
        prepared = None
        item_count = 0
        duplicate_items = 0

        from star_manager.services.mod_database import prepare_mod_items, replace_mod_items

        prepared = prepare_mod_items(game_dir, promoted, thumbnail_dir)
        with conn:
            promoted_zipmod_id = upsert_zipmod(conn, promoted, now)
            item_count, duplicate_items = replace_mod_items(conn, promoted_zipmod_id, promoted, prepared, now)
            conn.execute("DELETE FROM duplicate_zipmods WHERE id = ?", (duplicate_id,))
            if not removed_primary_file and primary_path.is_file():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO duplicate_zipmods (
                        guid, primary_zipmod_id, file_path, relative_path, file_name,
                        version, author, file_size, modified_at, reason, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'duplicate_guid', ?, ?)
                    """,
                    (
                        zipmod["guid"],
                        promoted_zipmod_id,
                        str(primary_path),
                        str(zipmod["relative_path"] or ""),
                        str(zipmod["file_name"] or primary_path.name),
                        str(zipmod["version"] or ""),
                        str(zipmod["author"] or ""),
                        int(zipmod["file_size"] or 0),
                        str(zipmod["modified_at"] or ""),
                        now,
                        now,
                    ),
                )
            conn.execute(
                "DELETE FROM duplicate_zipmods WHERE guid = ? AND file_path = ?",
                (zipmod["guid"], str(promoted.path)),
            )
            conn.execute(
                "UPDATE duplicate_zipmods SET primary_zipmod_id = ?, updated_at = ? WHERE guid = ?",
                (promoted_zipmod_id, now, zipmod["guid"]),
            )
            if removed_primary_file:
                conn.execute(
                    "DELETE FROM duplicate_zipmods WHERE guid = ? AND file_path = ?",
                    (zipmod["guid"], str(primary_path)),
                )

        return {
            "ok": True,
            "message": "Removed primary zipmod and promoted duplicate",
            "removed_primary_file": removed_primary_file,
            "removed_primary_path": str(primary_path),
            "promoted_zipmod_id": promoted_zipmod_id,
            "promoted_file_path": str(promoted.path),
            "guid": zipmod["guid"],
            "item_count": item_count,
            "duplicate_items": duplicate_items,
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def _item_signature_from_csv_item(item: CsvItem, guid: str) -> tuple[str, str, str]:
    return (str(guid or ""), str(item.item_id or ""), str(item.kind or ""))


def merge_duplicate_zipmod(
    zipmod_id: int,
    duplicate_id: int,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    try:
        duplicate_id = int(duplicate_id)
    except (TypeError, ValueError):
        return {"ok": False, "error": "duplicate_id must be numeric"}
    if duplicate_id <= 0:
        return {"ok": False, "error": "duplicate_id must be positive"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}
        duplicate = conn.execute(
            "SELECT * FROM duplicate_zipmods WHERE id = ? AND guid = ?",
            (duplicate_id, zipmod["guid"]),
        ).fetchone()
        if duplicate is None:
            return {"ok": False, "error": f"Duplicate zipmod not found: {duplicate_id}"}

        primary_path = Path(str(zipmod["file_path"])).resolve()
        duplicate_path = Path(str(duplicate["file_path"])).resolve()
        if not primary_path.is_file():
            return {"ok": False, "error": f"Primary zipmod file is missing: {primary_path}"}
        if not duplicate_path.is_file():
            return {"ok": False, "error": f"Duplicate zipmod file is missing: {duplicate_path}"}

        guid = str(zipmod["guid"] or "")
        replacements: dict[str, bytes] = {}
        copied_members: list[str] = []
        merged_items: list[dict] = []

        with zipfile.ZipFile(primary_path, "r") as primary_zf, zipfile.ZipFile(duplicate_path, "r") as duplicate_zf:
            primary_index = ZipMemberIndex(primary_zf)
            duplicate_index = ZipMemberIndex(duplicate_zf)
            primary_members = {normalize_zip_path(name).lower() for name in primary_zf.namelist()}
            existing_signatures = {
                _item_signature_from_csv_item(item, guid)
                for item in iter_open_zip_csv_items(primary_zf)
                if item.parse_status == "ok"
            }

            rows_by_csv: dict[str, list[list[str]]] = {}
            duplicate_csv_members = [
                name
                for name in duplicate_zf.namelist()
                if normalize_zip_path(name).lower().startswith("abdata/list/")
                and normalize_zip_path(name).lower().endswith(".csv")
            ]
            for duplicate_csv_member in sorted(duplicate_csv_members):
                csv_path = normalize_zip_path(duplicate_csv_member)
                csv_bytes = duplicate_zf.read(duplicate_csv_member)
                encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
                del encoding
                rows = list(csv.reader(io.StringIO(text, newline="")))
                header_index = find_header_index(rows)
                if header_index is None:
                    continue
                list_kind = rows[0][0].strip() if rows and rows[0] else ""
                header = [cell.strip() for cell in rows[header_index]]
                if "ID" not in header:
                    continue
                id_index = header.index("ID")
                name_index = header.index("Name") if "Name" in header else -1
                for row in rows[header_index + 1 :]:
                    if not row or len(row) <= id_index:
                        continue
                    item_id = row[id_index].strip()
                    if not item_id:
                        continue
                    signature = (guid, item_id, list_kind)
                    if signature in existing_signatures:
                        continue
                    rows_by_csv.setdefault(csv_path, []).append(row)
                    existing_signatures.add(signature)
                    merged_items.append(
                        {
                            "item_id": item_id,
                            "kind": list_kind,
                            "name": row[name_index].strip() if name_index >= 0 and len(row) > name_index else "",
                            "csv_path": csv_path,
                        }
                    )

            if not merged_items:
                return {"ok": False, "error": "No unique item rows to merge"}

            for csv_path, rows_to_append in rows_by_csv.items():
                primary_member = find_zip_member(primary_zf, csv_path, primary_index)
                duplicate_member = find_zip_member(duplicate_zf, csv_path, duplicate_index)
                if primary_member is not None:
                    replacements[csv_path] = append_csv_item_rows(primary_zf.read(primary_member), rows_to_append)
                elif duplicate_member is not None:
                    replacements[csv_path] = duplicate_zf.read(duplicate_member)

            for info in duplicate_zf.infolist():
                arcname = normalize_zip_path(info.filename)
                key = arcname.lower()
                if key in primary_members or key in {normalize_zip_path(path).lower() for path in replacements}:
                    continue
                if key == "manifest.xml":
                    continue
                replacements[arcname] = duplicate_zf.read(info.filename)
                copied_members.append(arcname)

        rewrite_zip_members(primary_path, replacements)

        move_to_trash(
            duplicate_path,
            "mods",
            name=str(duplicate["file_name"] or duplicate_path.stem),
            metadata={
                "game_dir": resolve_game_dir_from_zipmod(
                    str(duplicate_path), str(duplicate["relative_path"] or "")
                ),
                "relative_path": str(duplicate["relative_path"] or ""),
                "guid": guid,
                "reason": "merge_duplicate",
            },
        )
        now = utc_now()
        stat = primary_path.stat()
        candidate = ZipmodCandidate(
            manifest=read_manifest(primary_path),
            path=primary_path,
            relative_path=str(zipmod["relative_path"] or ""),
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        game_dir = resolve_game_dir_from_zipmod(str(primary_path), str(zipmod["relative_path"] or ""))
        with conn:
            _replace_mod_items(conn, game_dir, int(zipmod["id"]), candidate, thumbnail_dir, now)
            conn.execute(
                """
                UPDATE zipmods
                SET file_size = ?, modified_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (candidate.file_size, candidate.modified_at, now, int(zipmod["id"])),
            )
            conn.execute("DELETE FROM duplicate_zipmods WHERE id = ?", (duplicate_id,))
            conn.execute(
                "UPDATE duplicate_zipmods SET primary_zipmod_id = ?, updated_at = ? WHERE guid = ?",
                (int(zipmod["id"]), now, guid),
            )

        return {
            "ok": True,
            "message": f"Merged {len(merged_items)} unique item(s) from duplicate zipmod",
            "guid": guid,
            "zipmod_id": int(zipmod["id"]),
            "duplicate_id": duplicate_id,
            "merged_item_count": len(merged_items),
            "merged_items": merged_items[:20],
            "copied_member_count": len(copied_members),
            "copied_members": copied_members[:50],
            "deleted_duplicate_path": str(duplicate_path),
        }
    except (OSError, ValueError, zipfile.BadZipFile, csv.Error) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def _version_sort_key(version: str) -> list[tuple[int, object]]:
    parts: list[tuple[int, object]] = []
    normalized = str(version or "").strip()
    if re.match(r"^[vV]\s*\d", normalized):
        normalized = re.sub(r"^[vV]\s*", "", normalized, count=1)
    for token in re.findall(r"\d+|[A-Za-z]+", normalized):
        if token.isdigit():
            parts.append((1, int(token)))
        else:
            parts.append((0, token.lower()))
    if parts and all(part[0] == 1 for part in parts):
        while parts and parts[-1] == (1, 0):
            parts.pop()
    return parts


def _duplicate_item_signature(item, guid: str) -> tuple[str, str, str]:
    return (
        str(guid or ""),
        str(item.item_id or ""),
        str(item.kind or ""),
    )


def _unity3d_average_modified(signatures: dict[str, dict[str, object]]) -> tuple[int, str]:
    scores: list[int] = []
    for signature in signatures.values():
        modified_key = signature.get("modified_key")
        if not isinstance(modified_key, (list, tuple)) or len(modified_key) < 6:
            continue
        try:
            year, month, day, hour, minute, second = (int(part) for part in modified_key[:6])
            modified_at = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        scores.append(int(modified_at.timestamp()))
    if not scores:
        return -1, ""
    average = sum(scores) // len(scores)
    return average, datetime.fromtimestamp(average, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _duplicate_keep_sort_key(candidate: dict) -> tuple[int, int, int, int, int, int, int]:
    reasons = set(candidate.get("recommendation_reasons") or [])
    return (
        1 if "most_complete" in reasons else 0,
        int(candidate.get("completeness_score") or 0),
        1 if "latest_version" in reasons else 0,
        int(candidate.get("unity3d_average_modified_score") or -1),
        int(candidate.get("ok_item_count") or 0),
        int(candidate.get("unity3d_in_mod_count") or 0),
        int(candidate.get("file_size") or 0),
    )


def _duplicate_delete_reasons(candidate: dict, keep: dict) -> list[str]:
    reasons: list[str] = []
    if int(candidate.get("missing_item_count_vs_union") or 0) > 0:
        reasons.append("missing_items")
    if int(candidate.get("unique_item_count") or 0) == 0 and candidate.get("index") != keep.get("index"):
        reasons.append("no_unique_items")
    if int(candidate.get("completeness_score") or 0) < int(keep.get("completeness_score") or 0):
        reasons.append("lower_completeness")
    if "latest_version" not in set(candidate.get("recommendation_reasons") or []) and "latest_version" in set(keep.get("recommendation_reasons") or []):
        reasons.append("older_version")
    candidate_reasons = set(candidate.get("recommendation_reasons") or [])
    keep_reasons = set(keep.get("recommendation_reasons") or [])
    if (
        "latest_version" in candidate_reasons
        and "latest_version" in keep_reasons
        and int(candidate.get("unity3d_average_modified_score") or -1) < int(keep.get("unity3d_average_modified_score") or -1)
    ):
        reasons.append("older_unity3d_average")
    if int(candidate.get("file_size") or 0) < int(keep.get("file_size") or 0):
        reasons.append("smaller_file")
    if not reasons:
        reasons.append("redundant_candidate")
    return reasons


def analyze_duplicate_zipmods(
    zipmod_id: int,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        duplicate_rows = conn.execute(
            """
            SELECT id, file_path, relative_path, file_name, version, author, file_size, modified_at
            FROM duplicate_zipmods
            WHERE guid = ?
            ORDER BY modified_at DESC, file_name COLLATE NOCASE
            """,
            (zipmod["guid"],),
        ).fetchall()
        if not duplicate_rows:
            return {"ok": False, "error": "No duplicate zipmods found"}

        raw_candidates = [
            {
                "duplicate_id": None,
                "role": "primary",
                "file_path": zipmod["file_path"],
                "relative_path": zipmod["relative_path"],
                "file_name": zipmod["file_name"],
                "indexed_version": zipmod["version"],
                "indexed_author": zipmod["author"],
                "indexed_file_size": zipmod["file_size"],
                "indexed_modified_at": zipmod["modified_at"],
            },
            *[
                {
                    "duplicate_id": row["id"],
                    "role": "duplicate",
                    "file_path": row["file_path"],
                    "relative_path": row["relative_path"],
                    "file_name": row["file_name"],
                    "indexed_version": row["version"],
                    "indexed_author": row["author"],
                    "indexed_file_size": row["file_size"],
                    "indexed_modified_at": row["modified_at"],
                }
                for row in duplicate_rows
            ],
        ]

        from star_manager.services.mod_database import prepare_mod_items

        analyses: list[dict] = []
        signature_sets: list[set[tuple[str, str, str]]] = []
        all_signatures: set[tuple[str, str, str]] = set()
        latest_key: list[tuple[int, object]] = []
        best_completeness = -1
        best_file_size = -1
        best_unity3d_average_modified_score = -1

        for index, raw in enumerate(raw_candidates):
            path = Path(str(raw["file_path"])).resolve()
            stat = path.stat() if path.is_file() else None
            manifest = read_manifest(path) if path.is_file() else ManifestData("", "", "", "", "read_error", "zipmod file not found")
            candidate = ZipmodCandidate(
                manifest=manifest,
                path=path,
                relative_path=str(raw["relative_path"] or ""),
                file_size=stat.st_size if stat else int(raw["indexed_file_size"] or 0),
                modified_at=timestamp_to_utc(stat.st_mtime) if stat else str(raw["indexed_modified_at"] or ""),
            )
            game_dir = resolve_game_dir_from_zipmod(str(raw["file_path"]), str(raw["relative_path"] or ""))
            try:
                prepared = prepare_mod_items(game_dir, candidate, thumbnail_dir) if path.is_file() else None
                items = prepared.items if prepared is not None else []
                ok_count = prepared.ok_count if prepared is not None else 0
                duplicate_items = prepared.duplicate_items if prepared is not None else 0
                unity3d_in_mod = prepared.unity3d_in_mod_count if prepared is not None else 0
                unity3d_in_game = prepared.unity3d_in_game_count if prepared is not None else 0
                unity3d_missing = prepared.unity3d_missing_count if prepared is not None else 0
                unity3d_status = prepared.unity3d_status if prepared is not None else ""
                prepare_error = ""
            except Exception as exc:
                items = []
                ok_count = 0
                duplicate_items = 0
                unity3d_in_mod = 0
                unity3d_in_game = 0
                unity3d_missing = 0
                unity3d_status = ""
                prepare_error = str(exc)

            referenced_unity3d_paths = sorted(
                {
                    normalize_zip_path(reference).lower()
                    for item in items
                    for reference in unity3d_reference_paths(item)
                }
            )
            unity3d_signatures, unity3d_signature_error = (
                unity3d_member_signatures(path, referenced_unity3d_paths) if path.is_file() else ({}, "zipmod file not found")
            )
            unity3d_average_modified_score, unity3d_average_modified_at = _unity3d_average_modified(unity3d_signatures)
            signatures = {_duplicate_item_signature(item, manifest.guid or str(zipmod["guid"] or "")) for item in items}
            signature_sets.append(signatures)
            all_signatures.update(signatures)
            thumbnail_issue_count = sum(
                1
                for item in items
                if item.parse_status == "ok"
                and str(item.kind or "").strip() not in {"500", "501"}
                and (not item.thumbnail_status or item.thumbnail_status not in {"ready", "ok"})
            )
            parse_error_count = sum(1 for item in items if item.parse_status != "ok")
            completeness_score = ok_count * 10 + unity3d_in_mod * 3 - unity3d_missing * 5 - unity3d_in_game - thumbnail_issue_count - parse_error_count * 2
            version_key = _version_sort_key(manifest.version)
            latest_key = max(latest_key, version_key)
            best_completeness = max(best_completeness, completeness_score)
            best_file_size = max(best_file_size, candidate.file_size)
            best_unity3d_average_modified_score = max(best_unity3d_average_modified_score, unity3d_average_modified_score)
            analyses.append(
                {
                    "index": index,
                    "role": raw["role"],
                    "duplicate_id": raw["duplicate_id"],
                    "file_path": str(path),
                    "relative_path": raw["relative_path"],
                    "file_name": raw["file_name"],
                    "exists": path.is_file(),
                    "file_size": candidate.file_size,
                    "modified_at": candidate.modified_at,
                    "guid": manifest.guid,
                    "name": manifest.name,
                    "version": manifest.version,
                    "author": manifest.author,
                    "scan_status": manifest.scan_status,
                    "scan_error": manifest.scan_error or prepare_error,
                    "item_count": len(items),
                    "ok_item_count": ok_count,
                    "duplicate_item_count": duplicate_items,
                    "parse_error_count": parse_error_count,
                    "thumbnail_issue_count": thumbnail_issue_count,
                    "unity3d_status": unity3d_status,
                    "unity3d_in_mod_count": unity3d_in_mod,
                    "unity3d_in_game_count": unity3d_in_game,
                    "unity3d_missing_count": unity3d_missing,
                    "unity3d_referenced_member_count": len(referenced_unity3d_paths),
                    "unity3d_member_count": len(unity3d_signatures),
                    "unity3d_average_modified_score": unity3d_average_modified_score,
                    "unity3d_average_modified_at": unity3d_average_modified_at,
                    "unity3d_signatures": unity3d_signatures,
                    "unity3d_signature_error": unity3d_signature_error,
                    "completeness_score": completeness_score,
                    "version_key": version_key,
                    "sample_items": [
                        {
                            "item_id": item.item_id,
                            "kind": item.kind,
                            "name": item.name,
                            "csv_path": item.csv_path,
                            "unity3d_status": item.unity3d_status,
                            "thumbnail_status": item.thumbnail_status,
                            "parse_status": item.parse_status,
                        }
                        for item in items[:8]
                    ],
                }
            )

        primary_unity3d_signatures = analyses[0].get("unity3d_signatures") if analyses else {}
        latest_version_count = sum(1 for item in analyses if item.get("version") and item.get("version_key") == latest_key)
        for analysis, signatures in zip(analyses, signature_sets):
            missing = all_signatures - signatures
            unique = signatures - set().union(*(other for other in signature_sets if other is not signatures))
            unity3d_signatures = analysis.get("unity3d_signatures") or {}
            primary_keys = set(primary_unity3d_signatures or {})
            current_keys = set(unity3d_signatures)
            shared_keys = primary_keys & current_keys
            changed_keys = {
                key
                for key in shared_keys
                if (
                    unity3d_signatures.get(key, {}).get("crc"),
                    unity3d_signatures.get(key, {}).get("size"),
                )
                != (
                    (primary_unity3d_signatures or {}).get(key, {}).get("crc"),
                    (primary_unity3d_signatures or {}).get(key, {}).get("size"),
                )
            }
            newer_changed_keys = {
                key
                for key in changed_keys
                if tuple(unity3d_signatures.get(key, {}).get("modified_key") or ())
                > tuple((primary_unity3d_signatures or {}).get(key, {}).get("modified_key") or ())
            }
            reasons: list[str] = []
            if analysis["version_key"] == latest_key and analysis["version"]:
                reasons.append("latest_version")
            analysis["is_latest_version"] = "latest_version" in reasons
            analysis["is_strict_latest_version"] = bool(analysis["is_latest_version"] and latest_version_count == 1)
            if analysis["completeness_score"] == best_completeness:
                reasons.append("most_complete")
            if (
                int(analysis.get("unity3d_average_modified_score") or -1) == best_unity3d_average_modified_score
                and best_unity3d_average_modified_score >= 0
            ):
                reasons.append("newer_unity3d_average")
            if analysis["file_size"] == best_file_size:
                reasons.append("largest_file")
            analysis["missing_item_count_vs_union"] = len(missing)
            analysis["unique_item_count"] = len(unique)
            analysis["unity3d_missing_member_count_vs_primary"] = len(primary_keys - current_keys)
            analysis["unity3d_extra_member_count_vs_primary"] = len(current_keys - primary_keys)
            analysis["unity3d_changed_member_count_vs_primary"] = len(changed_keys)
            analysis["unity3d_newer_changed_member_count_vs_primary"] = len(newer_changed_keys)
            analysis["unity3d_matches_primary"] = (
                not analysis.get("unity3d_signature_error")
                and not changed_keys
                and not (primary_keys - current_keys)
            )
            analysis["unity3d_safe_against_primary"] = (
                not analysis.get("unity3d_signature_error")
                and not (primary_keys - current_keys)
                and not newer_changed_keys
            )
            analysis["recommendation_reasons"] = reasons
            analysis.pop("unity3d_signatures", None)
            analysis.pop("version_key", None)

        recommended_keep = max(analyses, key=_duplicate_keep_sort_key) if analyses else None
        recommended_delete: list[dict] = []
        if recommended_keep is not None:
            for analysis in analyses:
                should_delete = analysis["index"] != recommended_keep["index"] and int(analysis.get("unique_item_count") or 0) == 0
                should_merge = (
                    analysis["index"] != recommended_keep["index"]
                    and int(analysis.get("unique_item_count") or 0) > 0
                    and int(analysis.get("missing_item_count_vs_union") or 0) > 0
                    and int(analysis.get("item_count") or 0) > 0
                )
                analysis["recommended_action"] = (
                    "keep"
                    if analysis["index"] == recommended_keep["index"]
                    else ("delete" if should_delete else ("merge" if should_merge else "review"))
                )
                analysis["delete_reasons"] = [] if analysis["recommended_action"] != "delete" else _duplicate_delete_reasons(analysis, recommended_keep)
                if analysis["recommended_action"] == "delete":
                    recommended_delete.append(
                        {
                            "role": analysis["role"],
                            "duplicate_id": analysis["duplicate_id"],
                            "file_path": analysis["file_path"],
                            "file_name": analysis["file_name"],
                            "version": analysis["version"],
                            "reasons": analysis["delete_reasons"],
                        }
                    )

        primary_action = analyses[0].get("recommended_action", "") if analyses else ""
        return {
            "ok": True,
            "guid": zipmod["guid"],
            "primary_zipmod_id": int(zipmod["id"]),
            "union_item_count": len(all_signatures),
            "candidates": analyses,
            "recommendation": {
                "keep": {
                    "role": recommended_keep["role"],
                    "duplicate_id": recommended_keep["duplicate_id"],
                    "file_path": recommended_keep["file_path"],
                    "file_name": recommended_keep["file_name"],
                    "version": recommended_keep["version"],
                    "reasons": recommended_keep["recommendation_reasons"],
                } if recommended_keep is not None else None,
                "delete": recommended_delete,
                "primary_action": primary_action,
                "primary_should_delete": primary_action == "delete",
            },
            "summary": {
                "candidate_count": len(analyses),
                "latest_version": max((item["version"] for item in analyses), key=_version_sort_key, default=""),
                "best_completeness_score": best_completeness,
                "largest_file_size": best_file_size,
                "newest_unity3d_average_modified_score": best_unity3d_average_modified_score,
            },
        }
    finally:
        conn.close()


def delete_zipmod(
    zipmod_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        removed = False
        if zipmod_path.is_file():
            trash_record = move_to_trash(
                zipmod_path,
                "mods",
                name=str(zipmod["name"] or zipmod["file_name"] or zipmod_path.stem),
                metadata={
                    "game_dir": resolve_game_dir_from_zipmod(
                        str(zipmod_path), str(zipmod["relative_path"] or "")
                    ),
                    "relative_path": str(zipmod["relative_path"] or ""),
                    "guid": str(zipmod["guid"] or ""),
                    "reason": "delete_zipmod",
                },
            )
            removed = True
        else:
            trash_record = None

        with conn:
            conn.execute("DELETE FROM mod_items WHERE zipmod_id = ?", (int(zipmod_id),))
            conn.execute("DELETE FROM duplicate_zipmods WHERE guid = ?", (zipmod["guid"],))
            conn.execute("DELETE FROM zipmods WHERE id = ?", (int(zipmod_id),))

        return {
            "ok": True,
            "message": "Removed zipmod and related database records",
            "removed_file": removed,
            "file_path": str(zipmod_path),
            "guid": zipmod["guid"],
            "trash_id": str((trash_record or {}).get("id") or ""),
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def repair_zipmod_unity3d_from_game(
    zipmod_id: int,
    reference_path: str = "",
    preserve_source_paths: set[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (zipmod_id,)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        diagnostics = zipmod_unity3d_diagnostics(zipmod_id, resolved)
        if not diagnostics.get("ok"):
            return diagnostics
        repairable = [
            issue for issue in diagnostics["issues"]
            if issue["status"] == "not_in_mod" and issue["repair_action"] == "copy_into_zipmod"
        ]
        wanted = normalize_zip_path(reference_path)
        if wanted:
            repairable = [issue for issue in repairable if issue["path"].lower() == wanted.lower()]
        if not repairable:
            return {"ok": False, "error": "No repairable unity3d files found"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        game_dir = resolve_game_dir_from_zipmod(zipmod["file_path"], zipmod["relative_path"])
        moved: list[str] = []
        copied: list[str] = []
        preserved_sources = {str(Path(path).resolve()).casefold() for path in (preserve_source_paths or set())}
        with zipfile.ZipFile(zipmod_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
            existing = {normalize_zip_path(name).lower() for name in zf.namelist()}
            for issue in repairable:
                arcname = normalize_zip_path(issue["path"])
                if arcname.lower() in existing:
                    continue
                source = resolve_game_abdata_path(game_dir, arcname)
                if not source.is_file():
                    continue
                zf.write(source, arcname)
                if str(source.resolve()).casefold() in preserved_sources:
                    copied.append(arcname)
                else:
                    source.unlink()
                    moved.append(arcname)
                existing.add(arcname.lower())

        now = utc_now()
        stat = zipmod_path.stat()
        candidate = ZipmodCandidate(
            manifest=read_manifest(zipmod_path),
            path=zipmod_path,
            relative_path=zipmod["relative_path"],
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        with conn:
            _replace_mod_items(conn, game_dir, zipmod_id, candidate, thumbnail_dir, now)
            conn.execute(
                """
                UPDATE zipmods
                SET file_size = ?, modified_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (candidate.file_size, candidate.modified_at, now, zipmod_id),
            )

        return {
            "ok": True,
            "moved": moved,
            "copied": copied,
            "message": f"Moved {len(moved)} and copied {len(copied)} unity3d file(s) from game abdata into zipmod",
        }
    finally:
        conn.close()


def bulk_repair_zipmods_unity3d_from_game(
    zipmod_ids: Iterable[int],
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
    progress_callback: Callable[[str, int, int, int], None] | None = None,
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

    repaired: list[dict] = []
    skipped: list[dict] = []
    failures: list[dict] = []
    sources_by_zipmod: dict[int, set[str]] = {}
    source_zipmods: dict[str, set[int]] = {}

    resolved = db_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod_rows = {
            int(row["id"]): row
            for row in conn.execute(
                f"SELECT id, file_path, relative_path FROM zipmods WHERE id IN ({','.join('?' for _ in ids)})",
                ids,
            ).fetchall()
        }
    finally:
        conn.close()

    for index, zipmod_id in enumerate(ids, start=1):
        row = zipmod_rows.get(zipmod_id)
        if row is None:
            failures.append({"id": zipmod_id, "error": f"Zipmod not found: {zipmod_id}"})
            if progress_callback:
                progress_callback("analyze", index, len(ids), zipmod_id)
            continue
        diagnostics = zipmod_unity3d_diagnostics(zipmod_id, resolved)
        if not diagnostics.get("ok"):
            failures.append({"id": zipmod_id, "error": str(diagnostics.get("error") or "Repair analysis failed")})
            if progress_callback:
                progress_callback("analyze", index, len(ids), zipmod_id)
            continue
        game_dir = resolve_game_dir_from_zipmod(row["file_path"], row["relative_path"])
        for issue in diagnostics.get("issues") or []:
            if issue.get("status") != "not_in_mod" or issue.get("repair_action") != "copy_into_zipmod":
                continue
            source = resolve_game_abdata_path(game_dir, normalize_zip_path(str(issue.get("path") or "")))
            source_key = str(source.resolve()).casefold()
            sources_by_zipmod.setdefault(zipmod_id, set()).add(source_key)
            source_zipmods.setdefault(source_key, set()).add(zipmod_id)
        if progress_callback:
            progress_callback("analyze", index, len(ids), zipmod_id)

    shared_sources = {
        source
        for source, source_ids in source_zipmods.items()
        if len(source_ids) > 1
    }

    for index, zipmod_id in enumerate(ids, start=1):
        if any(item.get("id") == zipmod_id for item in failures):
            if progress_callback:
                progress_callback("repair", index, len(ids), zipmod_id)
            continue
        result = repair_zipmod_unity3d_from_game(
            zipmod_id,
            "",
            preserve_source_paths=(sources_by_zipmod.get(zipmod_id, set()) & shared_sources),
            db_path=db_path,
            thumbnail_dir=thumbnail_dir,
        )
        if result.get("ok"):
            moved = result.get("moved") or result.get("copied") or []
            moved_count = len(result.get("moved") or [])
            copied_count = len(result.get("copied") or [])
            if moved_count or copied_count:
                repaired.append(
                    {
                        "id": zipmod_id,
                        "moved": result.get("moved") or [],
                        "moved_count": moved_count,
                        "copied": result.get("copied") or [],
                        "copied_count": copied_count,
                    }
                )
            else:
                skipped.append({"id": zipmod_id, "reason": "No unity3d files moved"})
            if progress_callback:
                progress_callback("repair", index, len(ids), zipmod_id)
            continue

        error = str(result.get("error") or "Repair failed")
        if error == "No repairable unity3d files found":
            skipped.append({"id": zipmod_id, "reason": error})
        else:
            failures.append({"id": zipmod_id, "error": error})
        if progress_callback:
            progress_callback("repair", index, len(ids), zipmod_id)

    return {
        "ok": len(failures) == 0 or len(repaired) > 0 or len(skipped) > 0,
        "selected_count": len(ids),
        "repaired_count": len(repaired),
        "skipped_count": len(skipped),
        "failure_count": len(failures),
        "shared_source_count": len(shared_sources),
        "repaired": repaired,
        "skipped": skipped,
        "failures": failures,
        "message": f"Repaired {len(repaired)} zipmod(s), skipped {len(skipped)}, failed {len(failures)}",
    }


def safe_thumbnail_file_name(item_id: str, image_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", image_path.stem).strip("._-") or "thumbnail"
    item = re.sub(r"[^A-Za-z0-9._-]+", "_", str(item_id)).strip("._-") or "item"
    suffix = image_path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".tga"}:
        suffix = ".png"
    return f"{item}_{stem}{suffix}"


def thumbnail_csv_reference_for_arcname(image_arcname: str) -> tuple[str, str]:
    relative_image_path = normalize_zip_path(image_arcname).removeprefix("abdata/")
    relative_path = Path(relative_image_path)
    return normalize_zip_path(str(relative_path.parent)), relative_path.stem


def safe_export_thumbnail_file_name(item: sqlite3.Row) -> str:
    item_id = re.sub(r"[^A-Za-z0-9._-]+", "_", str(item["item_id"] or item["id"])).strip("._-") or "item"
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(item["name"] or "thumbnail")).strip(" ._") or "thumbnail"
    guid = re.sub(r"[^A-Za-z0-9._-]+", "_", str(item["zipmod_guid"] or "zipmod")).strip("._-")[:24] or "zipmod"
    return f"{item_id}__{name[:80]}__{guid}.png"


def export_zipmod_item_thumbnail(
    mod_item_id: int,
    target_dir: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    destination_dir = Path(target_dir).resolve()
    if not str(destination_dir).strip():
        return {"ok": False, "error": "Please choose an export directory"}

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        item = conn.execute("SELECT * FROM mod_items WHERE id = ?", (int(mod_item_id),)).fetchone()
        if item is None:
            return {"ok": False, "error": f"Item not found: {mod_item_id}"}
        if item["thumbnail_status"] not in {"ready", "ok"}:
            return {"ok": False, "error": "Current item thumbnail is not ready"}

        source = Path(str(item["thumbnail_cache_path"] or "")).resolve()
        if not source.is_file():
            return {"ok": False, "error": "Thumbnail cache file not found"}

        destination_dir.mkdir(parents=True, exist_ok=True)
        file_name = safe_export_thumbnail_file_name(item)
        destination = destination_dir / file_name
        index = 2
        while destination.exists():
            destination = destination_dir / f"{destination.stem}__{index}{destination.suffix}"
            index += 1
        shutil.copy2(source, destination)
        return {
            "ok": True,
            "item_id": int(mod_item_id),
            "source_path": str(source),
            "target_path": str(destination),
            "message": "Thumbnail exported",
        }
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def rewrite_csv_thumbnail_reference(
    csv_bytes: bytes,
    target_item_id: str,
    thumb_ab: str,
    thumb_tex: str,
) -> bytes:
    encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header_index = find_header_index(rows)
    if header_index is None:
        raise ValueError("CSV header not found")

    header = [cell.strip() for cell in rows[header_index]]
    if "ID" not in header:
        raise ValueError("CSV ID column not found")
    id_index = header.index("ID")

    def ensure_column(name: str) -> int:
        if name in header:
            return header.index(name)
        header.append(name)
        rows[header_index].append(name)
        return len(header) - 1

    thumb_ab_index = ensure_column("ThumbAB")
    thumb_tex_index = ensure_column("ThumbTex")
    max_columns = len(header)
    updated = False
    for row in rows[header_index + 1 :]:
        if len(row) <= id_index or row[id_index].strip() != str(target_item_id):
            continue
        if len(row) < max_columns:
            row.extend([""] * (max_columns - len(row)))
        row[thumb_ab_index] = thumb_ab
        row[thumb_tex_index] = thumb_tex
        updated = True
        break

    if not updated:
        raise ValueError(f"Item {target_item_id} not found in CSV")

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig" if encoding == "utf-8-sig" else encoding, errors="replace")


def rewrite_csv_without_item_row(
    csv_bytes: bytes,
    target_item_id: str,
) -> bytes:
    encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header_index = find_header_index(rows)
    if header_index is None:
        raise ValueError("CSV header not found")

    header = [cell.strip() for cell in rows[header_index]]
    if "ID" not in header:
        raise ValueError("CSV ID column not found")
    id_index = header.index("ID")

    removed = False
    kept_rows: list[list[str]] = []
    for index, row in enumerate(rows):
        if index <= header_index or removed:
            kept_rows.append(row)
            continue
        if len(row) > id_index and row[id_index].strip() == str(target_item_id):
            removed = True
            continue
        kept_rows.append(row)

    if not removed:
        raise ValueError(f"Item {target_item_id} not found in CSV")

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(kept_rows)
    return output.getvalue().encode("utf-8-sig" if encoding == "utf-8-sig" else encoding, errors="replace")


def append_csv_item_rows(
    csv_bytes: bytes,
    rows_to_append: list[list[str]],
) -> bytes:
    encoding, text = decode_csv_bytes_with_encoding(csv_bytes)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header_index = find_header_index(rows)
    if header_index is None:
        raise ValueError("CSV header not found")
    if not rows_to_append:
        return csv_bytes

    header_width = len(rows[header_index])
    output_rows = [list(row) for row in rows]
    for row in rows_to_append:
        padded = list(row) + [""] * max(0, header_width - len(row))
        output_rows.append(padded[: max(header_width, len(padded))])

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(output_rows)
    return output.getvalue().encode("utf-8-sig" if encoding == "utf-8-sig" else encoding, errors="replace")


def rewrite_zip_members(
    zipmod_path: Path,
    replacements: dict[str, bytes],
    removals: Iterable[str] | None = None,
) -> None:
    normalized_replacements = {
        normalize_zip_path(path).lower(): (normalize_zip_path(path), data)
        for path, data in replacements.items()
    }
    normalized_removals = {normalize_zip_path(path).lower() for path in removals or []}
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zipmod", dir=str(zipmod_path.parent)) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        written: set[str] = set()
        with zipfile.ZipFile(zipmod_path, "r") as source, zipfile.ZipFile(
            temp_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as target:
            for info in source.infolist():
                key = normalize_zip_path(info.filename).lower()
                if key in normalized_removals:
                    continue
                if key in normalized_replacements:
                    arcname, data = normalized_replacements[key]
                    target.writestr(arcname, data)
                    written.add(key)
                    continue
                target.writestr(info, source.read(info.filename))

            for key, (arcname, data) in normalized_replacements.items():
                if key not in written:
                    target.writestr(arcname, data)

        temp_path.replace(zipmod_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def delete_mod_item(
    mod_item_id: int,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        item = conn.execute("SELECT * FROM mod_items WHERE id = ?", (int(mod_item_id),)).fetchone()
        if item is None:
            return {"ok": False, "error": f"Item not found: {mod_item_id}"}
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (item["zipmod_id"],)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {item['zipmod_id']}"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        if not zipmod_path.is_file():
            return {"ok": False, "error": "Zipmod file not found"}

        item_count = int(conn.execute(
            "SELECT COUNT(*) FROM mod_items WHERE zipmod_id = ?",
            (int(item["zipmod_id"]),),
        ).fetchone()[0])
        if item_count <= 1:
            trash_record = move_to_trash(
                zipmod_path,
                "mods",
                name=str(zipmod["name"] or zipmod["file_name"] or zipmod_path.stem),
                metadata={
                    "game_dir": resolve_game_dir_from_zipmod(
                        str(zipmod_path), str(zipmod["relative_path"] or "")
                    ),
                    "relative_path": str(zipmod["relative_path"] or ""),
                    "guid": str(zipmod["guid"] or ""),
                    "reason": "delete_last_item",
                    "deleted_item_id": int(mod_item_id),
                },
            )
            with conn:
                conn.execute("DELETE FROM mod_items WHERE zipmod_id = ?", (int(item["zipmod_id"]),))
                conn.execute("DELETE FROM duplicate_zipmods WHERE guid = ?", (zipmod["guid"],))
                conn.execute("DELETE FROM zipmods WHERE id = ?", (int(item["zipmod_id"]),))
            return {
                "ok": True,
                "message": "Removed final item and deleted zipmod",
                "deleted_item_id": int(mod_item_id),
                "deleted_zipmod": True,
                "deleted_zipmod_path": str(zipmod_path),
                "trash_id": str(trash_record.get("id") or ""),
                "removed_unity3d": [],
            }

        csv_path = normalize_zip_path(item["csv_path"])
        deleted_item = CsvItem(
            csv_path=csv_path,
            item_id=str(item["item_id"]),
            kind=str(item["kind"] or ""),
            name=str(item["name"] or ""),
            main_manifest=str(item["main_manifest"] or ""),
            main_ab=str(item["main_ab"] or ""),
            main_data=str(item["main_data"] or ""),
            tex_ab=str(item["tex_ab"] or ""),
            thumb_ab=str(item["thumb_ab"] or ""),
            thumb_tex=str(item["thumb_tex"] or ""),
            parse_status=str(item["parse_status"] or "ok"),
            parse_error=str(item["parse_error"] or ""),
        )
        deleted_unity3d = unity3d_reference_paths(deleted_item)

        with zipfile.ZipFile(zipmod_path, "r") as zf:
            csv_member = find_zip_member(zf, csv_path)
            if csv_member is None:
                return {"ok": False, "error": f"CSV not found in zipmod: {csv_path}"}
            new_csv = rewrite_csv_without_item_row(zf.read(csv_member), str(item["item_id"]))

        remaining_references: set[str] = set()
        for remaining in iter_zip_csv_items(zipmod_path):
            if (
                normalize_zip_path(remaining.csv_path).lower() == csv_path.lower()
                and remaining.item_id == str(item["item_id"])
            ):
                continue
            remaining_references.update(path.lower() for path in unity3d_reference_paths(remaining))

        removals = [
            path for path in deleted_unity3d
            if path.lower() not in remaining_references
        ]
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            removals = [path for path in removals if find_zip_member(zf, path) is not None]

        rewrite_zip_members(zipmod_path, {csv_path: new_csv}, removals)

        now = utc_now()
        stat = zipmod_path.stat()
        candidate = ZipmodCandidate(
            manifest=read_manifest(zipmod_path),
            path=zipmod_path,
            relative_path=zipmod["relative_path"],
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        game_dir = resolve_game_dir_from_zipmod(zipmod["file_path"], zipmod["relative_path"])
        with conn:
            _replace_mod_items(conn, game_dir, int(zipmod["id"]), candidate, thumbnail_dir, now)
            conn.execute(
                """
                UPDATE zipmods
                SET file_size = ?, modified_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (candidate.file_size, candidate.modified_at, now, int(zipmod["id"])),
            )

        return {
            "ok": True,
            "message": "Removed item row from zipmod",
            "deleted_item_id": int(mod_item_id),
            "deleted_zipmod": False,
            "zipmod_id": int(zipmod["id"]),
            "csv_path": csv_path,
            "removed_unity3d": removals,
        }
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def update_zipmod_manifest_author(
    zipmod_id: int,
    author: str,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    return update_zipmod_manifest(
        zipmod_id,
        {"author": author},
        db_path=db_path,
        thumbnail_dir=thumbnail_dir,
        required_fields=("author",),
        success_message="作者已写入 manifest.xml",
    )


def get_zipmod_manifest(
    zipmod_id: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict:
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        if not zipmod_path.is_file():
            return {"ok": False, "error": "Zipmod file not found"}

        with zipfile.ZipFile(zipmod_path, "r") as source:
            manifest_member = find_zip_member(source, "manifest.xml")
            if manifest_member is None:
                return {"ok": False, "error": "manifest.xml not found"}
            manifest_data = source.read(manifest_member)

        root = ET.fromstring(manifest_data.decode("utf-8", errors="replace"))
        return {
            "ok": True,
            "fields": _manifest_fields_from_root(root),
            "zipmod": _zipmod_row_payload(conn, int(zipmod["id"])),
        }
    except (OSError, ET.ParseError, zipfile.BadZipFile, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def update_zipmod_manifest(
    zipmod_id: int,
    fields: dict,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
    required_fields: Iterable[str] = ("name", "version", "author"),
    success_message: str = "manifest.xml 已更新",
) -> dict:
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    allowed_fields = ("name", "version", "author")
    provided_fields = fields or {}
    values = {
        key: str(provided_fields[key] or "").strip()
        for key in allowed_fields
        if key in provided_fields
    }
    for key in required_fields:
        if not values.get(key):
            return {"ok": False, "error": f"请输入 {key}"}

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (int(zipmod_id),)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {zipmod_id}"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        if not zipmod_path.is_file():
            return {"ok": False, "error": "Zipmod file not found"}

        with zipfile.ZipFile(zipmod_path, "r") as source:
            manifest_member = find_zip_member(source, "manifest.xml")
            if manifest_member is None:
                return {"ok": False, "error": "manifest.xml not found"}
            manifest_data = source.read(manifest_member)

        root = ET.fromstring(manifest_data.decode("utf-8", errors="replace"))
        for key, value in values.items():
            element = root.find(key)
            if element is None:
                element = ET.SubElement(root, key)
            element.text = value
        manifest_output = ET.tostring(root, encoding="utf-8", xml_declaration=False)

        rewrite_zip_members(zipmod_path, {"manifest.xml": manifest_output})

        now = utc_now()
        stat = zipmod_path.stat()
        candidate = ZipmodCandidate(
            manifest=read_manifest(zipmod_path),
            path=zipmod_path,
            relative_path=zipmod["relative_path"],
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        game_dir = resolve_game_dir_from_zipmod(zipmod["file_path"], zipmod["relative_path"])
        with conn:
            _replace_mod_items(conn, game_dir, int(zipmod["id"]), candidate, thumbnail_dir, now)
            conn.execute(
                """
                UPDATE zipmods
                SET name = ?, version = ?, author = ?, file_size = ?, modified_at = ?,
                    scan_status = ?, scan_error = ?, last_scanned_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    candidate.manifest.name,
                    candidate.manifest.version,
                    candidate.manifest.author,
                    candidate.file_size,
                    candidate.modified_at,
                    candidate.manifest.scan_status,
                    candidate.manifest.scan_error,
                    now,
                    now,
                    int(zipmod["id"]),
                ),
            )

        return {
            "ok": True,
            "message": success_message,
            "fields": values,
            "zipmod": _zipmod_row_payload(conn, int(zipmod["id"])),
        }
    except (OSError, ET.ParseError, zipfile.BadZipFile, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def import_zipmod_item_thumbnail(
    mod_item_id: int,
    image_path: str,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    source_image = Path(image_path).resolve()
    if not source_image.is_file() or source_image.suffix.lower() != ".png":
        return {"ok": False, "error": "请选择 PNG 图片"}

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        item = conn.execute("SELECT * FROM mod_items WHERE id = ?", (int(mod_item_id),)).fetchone()
        if item is None:
            return {"ok": False, "error": f"Item not found: {mod_item_id}"}
        zipmod = conn.execute("SELECT * FROM zipmods WHERE id = ?", (item["zipmod_id"],)).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {item['zipmod_id']}"}

        zipmod_path = Path(zipmod["file_path"]).resolve()
        if not zipmod_path.is_file():
            return {"ok": False, "error": "Zipmod file not found"}

        csv_path = normalize_zip_path(item["csv_path"])
        item_key = str(item["item_id"] or "")
        image_arcname = normalize_zip_path(
            f"abdata/thumbnail/star_manager/{safe_thumbnail_file_name(item['item_id'], source_image)}"
        )
        csv_thumb_ab, csv_thumb_tex = thumbnail_csv_reference_for_arcname(image_arcname)

        with zipfile.ZipFile(zipmod_path, "r") as zf:
            csv_member = find_zip_member(zf, csv_path)
            if csv_member is None:
                return {"ok": False, "error": f"CSV not found in zipmod: {csv_path}"}
            new_csv = rewrite_csv_thumbnail_reference(
                zf.read(csv_member),
                str(item["item_id"]),
                csv_thumb_ab,
                csv_thumb_tex,
            )

        rewrite_zip_members(
            zipmod_path,
            {
                csv_path: new_csv,
                image_arcname: source_image.read_bytes(),
            },
        )

        now = utc_now()
        stat = zipmod_path.stat()
        candidate = ZipmodCandidate(
            manifest=read_manifest(zipmod_path),
            path=zipmod_path,
            relative_path=zipmod["relative_path"],
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        game_dir = resolve_game_dir_from_zipmod(zipmod["file_path"], zipmod["relative_path"])
        with conn:
            _replace_mod_items(conn, game_dir, int(zipmod["id"]), candidate, thumbnail_dir, now)
            conn.execute(
                """
                UPDATE zipmods
                SET file_size = ?, modified_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (candidate.file_size, candidate.modified_at, now, int(zipmod["id"])),
            )

        # Re-parsing a zipmod replaces its item rows, so return the newly
        # indexed row. The renderer can update its current page in place
        # without rebuilding/reloading the entire database list.
        updated = conn.execute(
            """
            SELECT mod_items.id, mod_items.zipmod_id, mod_items.parse_status,
                   mod_items.thumbnail_status, mod_items.thumbnail_cache_path,
                   mod_items.unity3d_status, mod_items.unity3d_error,
                   mod_items.name, mod_items.kind, mod_items.zipmod_author,
                   mod_items.zipmod_guid, mod_items.item_id, mod_items.csv_path,
                   mod_items.main_ab, zipmods.name AS zipmod_name,
                   zipmods.file_name AS zipmod_file_name
            FROM mod_items
            INNER JOIN zipmods ON zipmods.id = mod_items.zipmod_id
            WHERE mod_items.zipmod_id = ?
              AND mod_items.item_id = ?
            ORDER BY CASE WHEN mod_items.csv_path = ? THEN 0 ELSE 1 END,
                     mod_items.id
            LIMIT 1
            """,
            (int(zipmod["id"]), item_key, csv_path),
        ).fetchone()
        updated_item = None
        if updated is not None:
            cache_path = str(updated["thumbnail_cache_path"] or "")
            updated_item = {
                "id": updated["id"],
                "zipmod_id": updated["zipmod_id"],
                "status": updated["parse_status"],
                "thumbnail_status": updated["thumbnail_status"],
                "thumbnail_cache_path": cache_path,
                "thumbnail_url": f"/mods/thumbnails?path={quote(cache_path)}" if cache_path else "",
                "unity3d_status": updated["unity3d_status"],
                "unity3d_error": updated["unity3d_error"],
                "name": updated["name"],
                "kind": updated["kind"],
                "author": updated["zipmod_author"] or "未知作者",
                "source_mod": updated["zipmod_name"] or updated["zipmod_file_name"],
                "zipmod_guid": updated["zipmod_guid"],
                "item_id": updated["item_id"],
                "csv_path": updated["csv_path"],
                "main_ab": updated["main_ab"],
            }

        response = {
            "ok": True,
            "zipmod_id": int(zipmod["id"]),
            "item_id": int(mod_item_id),
            "image_path": image_arcname,
            "csv_path": csv_path,
            "message": "已导入缩略图并更新 CSV",
        }
        if updated_item is not None:
            response["item"] = updated_item
        return response
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()


def possible_direct_image_paths(thumb_ab: str, thumb_tex: str) -> list[str]:
    thumb_ab = normalize_zip_path(thumb_ab)
    thumb_tex = normalize_zip_path(thumb_tex)
    paths: list[str] = []
    thumb_ab_stem = normalize_zip_path(str(Path(thumb_ab).with_suffix(""))) if thumb_ab else ""

    if thumb_ab and is_image_path(thumb_ab):
        paths.append(f"abdata/{thumb_ab}")
    if thumb_ab and thumb_tex:
        paths.append(f"abdata/{thumb_ab.rstrip('/')}/{thumb_tex}")
        if not is_image_path(thumb_tex):
            for suffix in (".png", ".jpg", ".jpeg", ".tga"):
                paths.append(f"abdata/{thumb_ab.rstrip('/')}/{thumb_tex}{suffix}")
        if is_unity3d_path(thumb_ab):
            paths.append(f"abdata/{thumb_ab_stem.rstrip('/')}/{thumb_tex}")
            if not is_image_path(thumb_tex):
                for suffix in (".png", ".jpg", ".jpeg", ".tga"):
                    paths.append(f"abdata/{thumb_ab_stem.rstrip('/')}/{thumb_tex}{suffix}")
    if thumb_ab and thumb_tex and is_image_path(thumb_ab):
        paths.append(f"abdata/{thumb_ab}")

    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        normalized = normalize_zip_path(path)
        if normalized.lower() not in seen:
            seen.add(normalized.lower())
            result.append(normalized)
    return result


def is_paint_or_pattern_item(item: CsvItem) -> bool:
    return str(item.kind or "").strip() in {"313", "348"}


def resource_image_candidates(item: CsvItem) -> list[str]:
    if not is_paint_or_pattern_item(item) or not item.main_ab or not item.main_data:
        return []
    main_path = normalize_abdata_path(item.main_manifest, item.main_ab)
    resource_dir = unity3d_directory_fallback_path(main_path).rstrip("/")
    texture_name = normalize_zip_path(item.main_data)
    candidates = [f"{resource_dir}/{texture_name}"]
    if not is_image_path(texture_name):
        for suffix in (".png", ".jpg", ".jpeg", ".tga"):
            candidates.append(f"{resource_dir}/{texture_name}{suffix}")

    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        normalized = normalize_zip_path(candidate)
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def write_direct_thumbnail(
    zf: zipfile.ZipFile, member_name: str, output_path: Path
) -> ThumbnailResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(zf.read(member_name))
    return ThumbnailResult(str(output_path), "ready", "")


def write_unity_thumbnail_image(image: object, output_path: Path) -> ThumbnailResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return ThumbnailResult(str(output_path), "ready", "")


def asset_name_matches(candidate: str, target: str) -> bool:
    candidate = normalize_zip_path(candidate).lower()
    target = normalize_zip_path(target).lower()
    if not target:
        return False
    candidate_path = Path(candidate)
    target_path = Path(target)
    candidate_names = {
        candidate,
        candidate_path.name,
        candidate_path.stem,
    }
    target_names = {
        target,
        target_path.name,
        target_path.stem,
    }
    return bool(candidate_names & target_names)


def asset_lookup_keys(name: str) -> set[str]:
    normalized = normalize_zip_path(name).lower()
    if not normalized:
        return set()
    path = Path(normalized)
    return {
        normalized,
        path.name,
        path.stem,
    }


def fallback_thumbnail_rank(candidate: str) -> int:
    normalized = normalize_zip_path(candidate).lower()
    name = Path(normalized).name
    stem = Path(normalized).stem
    if stem in {"icon", "thumb", "thumbnail", "preview", "prev"}:
        return 10
    if name in {"thumb_none.png", "thumb_none.jpg", "thumb_none.jpeg"}:
        return 20
    if "thumb" in stem or "thumbnail" in stem or "preview" in stem:
        return 30
    return 0


def extract_unity_thumbnail(
    bundle_bytes: bytes, thumb_tex: str, output_path: Path
) -> ThumbnailResult:
    cache = UnityThumbnailBundleCache()
    return cache.extract(("bytes", hashlib.sha1(bundle_bytes).hexdigest()), bundle_bytes, thumb_tex, output_path)


def preextract_zip_unity_thumbnails(
    candidate: ZipmodCandidate,
    items: Iterable[CsvItem],
    thumbnail_dir: Path,
    zf: zipfile.ZipFile,
    index: ZipMemberIndex | None,
    bundle_cache: UnityThumbnailBundleCache,
    source_cache: ThumbnailSourceCache,
) -> None:
    zip_identity = str(candidate.path.resolve()).lower()
    grouped: dict[str, list[CsvItem]] = {}
    for item in items:
        if item.parse_status != "ok" or not item.thumb_ab or not item.thumb_tex:
            continue
        if is_image_path(item.thumb_ab) or not is_unity3d_path(item.thumb_ab):
            continue
        bundle_path = normalize_zip_path(f"abdata/{item.thumb_ab}")
        member_name = find_zip_member(zf, bundle_path, index)
        if member_name is None:
            continue
        grouped.setdefault(member_name, []).append(item)

    for member_name, bundle_items in grouped.items():
        member_key = member_name.lower()
        source_root = ("zip-unity", zip_identity, member_key)
        uncached_items: list[CsvItem] = []
        for item in bundle_items:
            source_key = (*source_root, item.thumb_tex)
            output_path = thumbnail_cache_path(
                thumbnail_dir,
                candidate.manifest.guid,
                item.item_id,
                item.thumb_ab,
                item.thumb_tex,
            )
            if output_path.exists():
                source_cache.remember(
                    source_key,
                    ThumbnailResult(str(output_path), "ready", ""),
                )
                continue
            if source_cache.get(source_key, output_path) is not None:
                continue
            uncached_items.append(item)
        if not uncached_items:
            continue

        try:
            bundle = bundle_cache.load(("zip", member_key), zf.read(member_name))
        except (OSError, KeyError, RuntimeError, zipfile.BadZipFile):
            continue
        if isinstance(bundle, ThumbnailResult):
            continue

        for item in uncached_items:
            output_path = thumbnail_cache_path(
                thumbnail_dir,
                candidate.manifest.guid,
                item.item_id,
                item.thumb_ab,
                item.thumb_tex,
            )
            source_key = (*source_root, item.thumb_tex)
            if source_cache.get(source_key, output_path) is not None:
                continue
            if output_path.exists():
                result = ThumbnailResult(str(output_path), "ready", "")
            else:
                result = bundle.write_thumbnail(item.thumb_tex, output_path)
            source_cache.remember(source_key, result)


def extract_thumbnail_from_zipmod(
    game_dir: Path,
    candidate: ZipmodCandidate,
    item: CsvItem,
    thumbnail_dir: Path,
    zf: zipfile.ZipFile | None = None,
    index: ZipMemberIndex | None = None,
    bundle_cache: UnityThumbnailBundleCache | None = None,
    source_cache: ThumbnailSourceCache | None = None,
) -> ThumbnailResult:
    started_at = time.perf_counter()

    def finish(
        result: ThumbnailResult,
        phase: str,
        cache_hit: bool = False,
        **details: object,
    ) -> ThumbnailResult:
        write_thumbnail_profile(
            {
                "zipmod_guid": candidate.manifest.guid,
                "zipmod_path": str(candidate.path),
                "zipmod_size": candidate.file_size,
                "zipmod_modified_at": candidate.modified_at,
                "item_id": item.item_id,
                "kind": item.kind,
                "csv_path": item.csv_path,
                "thumb_ab": item.thumb_ab,
                "thumb_tex": item.thumb_tex,
                "phase": phase,
                "status": result.status,
                "cache_hit": cache_hit,
                "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                "result_path": result.cache_path,
                "error": result.error,
                **details,
            }
        )
        return result

    if item.parse_status != "ok":
        return finish(ThumbnailResult("", "", ""), "skip_parse")
    if not item.thumb_ab and not item.thumb_tex:
        return finish(ThumbnailResult("", "missing", "ThumbAB and ThumbTex are empty"), "skip_empty")
    if not item.thumb_tex:
        return finish(ThumbnailResult("", "missing", "ThumbTex is empty"), "skip_empty_thumb_tex")

    output_path = thumbnail_cache_path(
        thumbnail_dir,
        candidate.manifest.guid,
        item.item_id,
        item.thumb_ab,
        item.thumb_tex,
    )
    if output_path.exists():
        return finish(
            ThumbnailResult(str(output_path), "ready", ""),
            "cache_hit",
            True,
            source_kind="output_cache",
            source_path=str(output_path),
        )

    active_bundle_cache = bundle_cache or UnityThumbnailBundleCache()
    active_source_cache = source_cache or ThumbnailSourceCache()

    def use_source_cache(source_key: tuple[str, ...]) -> ThumbnailResult | None:
        result = active_source_cache.get(source_key, output_path)
        if result is None:
            return None
        phase = "source_cache_hit" if result.status == "ready" else "source_cache_error"
        return finish(result, phase, True, source_kind="source_cache", source_key="|".join(source_key))

    def remember_source(source_key: tuple[str, ...], result: ThumbnailResult) -> ThumbnailResult:
        active_source_cache.remember(source_key, result)
        return result

    zip_identity = str(candidate.path.resolve()).lower()
    game_identity = str(game_dir.resolve()).lower()

    def extract_from_game_abdata() -> ThumbnailResult:
        for direct_path in possible_direct_image_paths(item.thumb_ab, item.thumb_tex):
            source_path = game_dir / normalize_zip_path(direct_path)
            if source_path.is_file():
                source_key = ("game-file", str(source_path.resolve()).lower())
                cached = use_source_cache(source_key)
                if cached is not None:
                    return cached
                source_stat = source_path.stat()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(source_path.read_bytes())
                return finish(
                    remember_source(source_key, ThumbnailResult(str(output_path), "ready", "")),
                    "game_direct_image",
                    source_kind="game_file",
                    source_path=str(source_path),
                    source_size=source_stat.st_size,
                    source_modified_at=timestamp_to_utc(source_stat.st_mtime),
                )

        source = game_dir / "abdata" / normalize_zip_path(item.thumb_ab)
        if source.is_file() and is_image_path(str(source)):
            source_key = ("game-file", str(source.resolve()).lower())
            cached = use_source_cache(source_key)
            if cached is not None:
                return cached
            source_stat = source.stat()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(source.read_bytes())
            return finish(
                remember_source(source_key, ThumbnailResult(str(output_path), "ready", "")),
                "game_image_file",
                source_kind="game_file",
                source_path=str(source),
                source_size=source_stat.st_size,
                source_modified_at=timestamp_to_utc(source_stat.st_mtime),
            )
        if source.is_dir() and item.thumb_tex:
            for image_name in possible_direct_image_paths("", item.thumb_tex):
                candidate_path = source / Path(image_name).name
                if candidate_path.is_file():
                    source_key = ("game-file", str(candidate_path.resolve()).lower())
                    cached = use_source_cache(source_key)
                    if cached is not None:
                        return cached
                    source_stat = candidate_path.stat()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(candidate_path.read_bytes())
                    return finish(
                        remember_source(source_key, ThumbnailResult(str(output_path), "ready", "")),
                        "game_directory_image",
                        source_kind="game_file",
                        source_path=str(candidate_path),
                        source_size=source_stat.st_size,
                        source_modified_at=timestamp_to_utc(source_stat.st_mtime),
                    )
        if source.is_file() and source.suffix.lower() == ".unity3d":
            source_key = ("game-unity", str(source.resolve()).lower(), item.thumb_tex)
            cached = use_source_cache(source_key)
            if cached is not None:
                return cached
            source_stat = source.stat()
            thumbnail = active_bundle_cache.extract(
                ("file", str(source.resolve()).lower()),
                source.read_bytes(),
                item.thumb_tex,
                output_path,
            )
            return finish(
                remember_source(source_key, thumbnail),
                "game_unity_bundle",
                source_kind="game_unity",
                source_path=str(source),
                source_size=source_stat.st_size,
                source_modified_at=timestamp_to_utc(source_stat.st_mtime),
            )
        for resource_path in resource_image_candidates(item):
            source_path = game_dir / normalize_zip_path(resource_path)
            if source_path.is_file():
                source_key = ("game-file", str(source_path.resolve()).lower())
                cached = use_source_cache(source_key)
                if cached is not None:
                    return cached
                source_stat = source_path.stat()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(source_path.read_bytes())
                return finish(
                    remember_source(source_key, ThumbnailResult(str(output_path), "ready", "")),
                    "game_resource_image",
                    source_kind="game_file",
                    source_path=str(source_path),
                    source_size=source_stat.st_size,
                    source_modified_at=timestamp_to_utc(source_stat.st_mtime),
                )
        missing_key = (
            "game-missing",
            game_identity,
            normalize_zip_path(item.thumb_ab).lower(),
            item.thumb_tex,
        )
        cached = use_source_cache(missing_key)
        if cached is not None:
            return cached
        return finish(
            remember_source(
                missing_key,
                ThumbnailResult(
                    "",
                    "missing",
                    f"thumbnail source not found: abdata/{normalize_zip_path(item.thumb_ab)}",
                ),
            ),
            "game_missing",
            source_kind="game_missing",
            source_path=str(source),
            source_key="|".join(missing_key),
        )

    def extract_from_zip(open_zf: zipfile.ZipFile, member_index: ZipMemberIndex | None) -> ThumbnailResult:
        for direct_path in possible_direct_image_paths(item.thumb_ab, item.thumb_tex):
            member_name = find_zip_member(open_zf, direct_path, member_index)
            if member_name is not None:
                source_key = ("zip-member", zip_identity, member_name.lower())
                cached = use_source_cache(source_key)
                if cached is not None:
                    return cached
                member_info = open_zf.getinfo(member_name)
                return finish(
                    remember_source(
                        source_key,
                        write_direct_thumbnail(open_zf, member_name, output_path),
                    ),
                    "zip_direct_image",
                    source_kind="zip_member",
                    source_member=member_name,
                    source_size=member_info.file_size,
                    source_compress_size=member_info.compress_size,
                )

        bundle_path = normalize_zip_path(f"abdata/{item.thumb_ab}")
        member_name = find_zip_member(open_zf, bundle_path, member_index)
        if member_name is None:
            for resource_path in resource_image_candidates(item):
                resource_member = find_zip_member(open_zf, resource_path, member_index)
                if resource_member is not None:
                    source_key = ("zip-member", zip_identity, resource_member.lower())
                    cached = use_source_cache(source_key)
                    if cached is not None:
                        return cached
                    member_info = open_zf.getinfo(resource_member)
                    return finish(
                        remember_source(
                            source_key,
                            write_direct_thumbnail(open_zf, resource_member, output_path),
                        ),
                        "zip_resource_image",
                        source_kind="zip_member",
                        source_member=resource_member,
                        source_size=member_info.file_size,
                        source_compress_size=member_info.compress_size,
                    )
            for candidate_path in main_ab_thumbnail_image_candidates(item):
                main_ab_member = find_zip_member(open_zf, candidate_path, member_index)
                if main_ab_member is not None:
                    source_key = ("zip-member", zip_identity, main_ab_member.lower())
                    cached = use_source_cache(source_key)
                    if cached is not None:
                        return cached
                    member_info = open_zf.getinfo(main_ab_member)
                    return finish(
                        remember_source(
                            source_key,
                            write_direct_thumbnail(open_zf, main_ab_member, output_path),
                        ),
                        "zip_main_ab_image_fallback",
                        source_kind="zip_member",
                        source_member=main_ab_member,
                        source_size=member_info.file_size,
                        source_compress_size=member_info.compress_size,
                    )
            image_member = find_zip_direct_image_by_name(open_zf, item.thumb_tex)
            if image_member is not None:
                source_key = ("zip-member", zip_identity, image_member.lower())
                cached = use_source_cache(source_key)
                if cached is not None:
                    return cached
                member_info = open_zf.getinfo(image_member)
                return finish(
                    remember_source(
                        source_key,
                        write_direct_thumbnail(open_zf, image_member, output_path),
                    ),
                    "zip_direct_image_name_fallback",
                    source_kind="zip_member",
                    source_member=image_member,
                    source_size=member_info.file_size,
                    source_compress_size=member_info.compress_size,
                )
            return extract_from_game_abdata()
        source_key = ("zip-unity", zip_identity, member_name.lower(), item.thumb_tex)
        cached = use_source_cache(source_key)
        if cached is not None:
            return cached
        member_info = open_zf.getinfo(member_name)
        thumbnail = active_bundle_cache.extract(
            ("zip", member_name.lower()),
            open_zf.read(member_name),
            item.thumb_tex,
            output_path,
        )
        if thumbnail.status == "ready":
            return finish(
                remember_source(source_key, thumbnail),
                "zip_unity_bundle",
                source_kind="zip_unity",
                source_member=member_name,
                source_size=member_info.file_size,
                source_compress_size=member_info.compress_size,
            )
        for resource_path in resource_image_candidates(item):
            resource_member = find_zip_member(open_zf, resource_path, member_index)
            if resource_member is not None:
                fallback_key = ("zip-member", zip_identity, resource_member.lower())
                cached = use_source_cache(fallback_key)
                if cached is not None:
                    return cached
                member_info = open_zf.getinfo(resource_member)
                return finish(
                    remember_source(
                        fallback_key,
                        write_direct_thumbnail(open_zf, resource_member, output_path),
                    ),
                    "zip_resource_fallback",
                    source_kind="zip_member",
                    source_member=resource_member,
                    source_size=member_info.file_size,
                    source_compress_size=member_info.compress_size,
                )
        return finish(
            remember_source(source_key, thumbnail),
            "zip_unity_bundle_fallback",
            source_kind="zip_unity",
            source_member=member_name,
            source_size=member_info.file_size,
            source_compress_size=member_info.compress_size,
        )

    try:
        if zf is not None:
            return extract_from_zip(zf, index)
        with zipfile.ZipFile(candidate.path, "r") as opened_zf:
            return extract_from_zip(opened_zf, ZipMemberIndex(opened_zf))
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        return finish(ThumbnailResult("", "error", str(exc)), "zip_error")


_THUMBNAIL_RECOVERY_LOCK = threading.Lock()


def ensure_mod_item_thumbnail(
    mod_item_id: int,
    db_path: Path = DEFAULT_DB_PATH,
    thumbnail_dir: Path = DEFAULT_THUMBNAIL_DIR,
) -> dict:
    """Resolve or lazily rebuild one item's thumbnail cache from its zipmod."""
    resolved_db = db_path.resolve()
    if not resolved_db.exists() or not resolved_db.is_file():
        return {"ok": False, "error": "Database not found"}

    from star_manager.services.mod_database_queries import resolve_thumbnail_cache_path

    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        item = conn.execute(
            "SELECT * FROM mod_items WHERE id = ?",
            (int(mod_item_id),),
        ).fetchone()
        if item is None:
            return {"ok": False, "error": f"Item not found: {mod_item_id}"}
        if str(item["parse_status"] or "") != "ok":
            return {"ok": False, "error": "Item parsing is not ready"}
        if not str(item["thumb_tex"] or "").strip():
            return {"ok": False, "error": "Item has no thumbnail texture reference"}

        resolved_cache = resolve_thumbnail_cache_path(
            str(item["thumbnail_cache_path"] or ""),
            thumbnail_dir,
        )
        if resolved_cache is not None:
            cache_path = str(resolved_cache)
            with conn:
                conn.execute(
                    """
                    UPDATE mod_items
                    SET thumbnail_cache_path = ?, thumbnail_status = 'ready',
                        thumbnail_error = '', updated_at = ?
                    WHERE id = ?
                    """,
                    (cache_path, utc_now(), int(mod_item_id)),
                )
            return {
                "ok": True,
                "item_id": int(mod_item_id),
                "thumbnail_cache_path": cache_path,
                "thumbnail_status": "ready",
                "thumbnail_url": f"/mods/thumbnails?path={quote(cache_path)}",
            }

        zipmod = conn.execute(
            "SELECT * FROM zipmods WHERE id = ?",
            (int(item["zipmod_id"]),),
        ).fetchone()
        if zipmod is None:
            return {"ok": False, "error": f"Zipmod not found: {item['zipmod_id']}"}

        zipmod_path = Path(str(zipmod["file_path"] or "")).resolve()
        if not zipmod_path.is_file():
            return {"ok": False, "error": "Zipmod file not found"}

        stat = zipmod_path.stat()
        candidate = ZipmodCandidate(
            manifest=ManifestData(
                str(zipmod["guid"] or item["zipmod_guid"] or ""),
                str(zipmod["name"] or ""),
                str(zipmod["version"] or ""),
                str(zipmod["author"] or ""),
                str(zipmod["scan_status"] or "ok"),
                str(zipmod["scan_error"] or ""),
            ),
            path=zipmod_path,
            relative_path=str(zipmod["relative_path"] or ""),
            file_size=stat.st_size,
            modified_at=timestamp_to_utc(stat.st_mtime),
        )
        csv_item = CsvItem(
            csv_path=str(item["csv_path"] or ""),
            item_id=str(item["item_id"] or ""),
            kind=str(item["kind"] or ""),
            name=str(item["name"] or ""),
            main_manifest=str(item["main_manifest"] or ""),
            main_ab=str(item["main_ab"] or ""),
            main_data=str(item["main_data"] or ""),
            tex_ab=str(item["tex_ab"] or ""),
            thumb_ab=str(item["thumb_ab"] or ""),
            thumb_tex=str(item["thumb_tex"] or ""),
            parse_status=str(item["parse_status"] or ""),
            parse_error=str(item["parse_error"] or ""),
        )
        game_dir = resolve_game_dir_from_zipmod(
            str(zipmod["file_path"] or ""),
            str(zipmod["relative_path"] or ""),
        )

        with _THUMBNAIL_RECOVERY_LOCK:
            # Another visible row may share the same cache key and finish while
            # this request is waiting for the extraction lock.
            resolved_cache = resolve_thumbnail_cache_path(
                str(item["thumbnail_cache_path"] or ""),
                thumbnail_dir,
            )
            if resolved_cache is None:
                result = extract_thumbnail_from_zipmod(
                    game_dir,
                    candidate,
                    csv_item,
                    thumbnail_dir,
                )
            else:
                result = ThumbnailResult(str(resolved_cache), "ready", "")

        cache_path = str(result.cache_path or "")
        if result.status == "ready" and not Path(cache_path).is_file():
            result = ThumbnailResult("", "error", "thumbnail cache was not written")

        with conn:
            conn.execute(
                """
                UPDATE mod_items
                SET thumbnail_cache_path = ?, thumbnail_status = ?,
                    thumbnail_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (cache_path, result.status, result.error, utc_now(), int(mod_item_id)),
            )

        if result.status != "ready" or not cache_path:
            return {
                "ok": False,
                "item_id": int(mod_item_id),
                "thumbnail_status": result.status,
                "thumbnail_error": result.error,
            }
        return {
            "ok": True,
            "item_id": int(mod_item_id),
            "thumbnail_cache_path": cache_path,
            "thumbnail_status": result.status,
            "thumbnail_url": f"/mods/thumbnails?path={quote(cache_path)}",
        }
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": str(exc)}
    finally:
        conn.close()
