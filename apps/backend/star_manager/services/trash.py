from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from star_manager.core.runtime_paths import runtime_root


TRASH_ROOT = runtime_root() / "trash"
TRASH_KINDS = {"cards": "人物卡", "mods": "模组"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry_root(kind: str, entry_id: str) -> Path:
    if kind not in TRASH_KINDS or not entry_id or Path(entry_id).name != entry_id:
        raise ValueError("Invalid trash entry")
    return (TRASH_ROOT / kind / entry_id).resolve()


def move_to_trash(
    source_path: Path,
    kind: str,
    *,
    name: str = "",
    metadata: dict | None = None,
) -> dict:
    """Move one application-owned file into runtime/trash and write restore metadata."""
    source = Path(source_path).resolve()
    if kind not in TRASH_KINDS:
        raise ValueError(f"Unsupported trash kind: {kind}")
    if not source.is_file():
        raise FileNotFoundError(str(source))

    entry_id = uuid4().hex
    entry_root = _entry_root(kind, entry_id)
    payload_dir = entry_root / "payload"
    payload_dir.mkdir(parents=True, exist_ok=False)
    payload_path = payload_dir / source.name
    shutil.move(str(source), str(payload_path))

    safe_metadata = json.loads(json.dumps(metadata or {}, ensure_ascii=False, default=str))
    record = {
        "id": entry_id,
        "kind": kind,
        "kind_label": TRASH_KINDS[kind],
        "name": str(name or source.stem),
        "source_path": str(source),
        "payload_path": str(payload_path),
        "file_name": source.name,
        "deleted_at": _now(),
        **safe_metadata,
    }
    try:
        (entry_root / "record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        shutil.move(str(payload_path), str(source))
        shutil.rmtree(entry_root, ignore_errors=True)
        raise
    return record


def _read_entry(kind: str, entry_id: str) -> dict | None:
    entry_root = _entry_root(kind, entry_id)
    record_path = entry_root / "record.json"
    if not record_path.is_file():
        return None
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(record, dict) or record.get("id") != entry_id:
        return None
    file_name = str(record.get("file_name") or "")
    payload_dir = (entry_root / "payload").resolve()
    if not file_name or Path(file_name).name != file_name:
        return None
    payload_path = (payload_dir / file_name).resolve()
    if payload_path.parent != payload_dir:
        return None
    if not payload_path.is_file():
        return None
    return {**record, "payload_path": str(payload_path), "size": payload_path.stat().st_size}


def list_trash() -> dict:
    entries: list[dict] = []
    for kind in TRASH_KINDS:
        kind_root = TRASH_ROOT / kind
        if not kind_root.is_dir():
            continue
        for entry_root in kind_root.iterdir():
            if not entry_root.is_dir():
                continue
            record = _read_entry(kind, entry_root.name)
            if not record:
                continue
            entries.append(
                {
                    key: value
                    for key, value in record.items()
                    if key not in {"payload_path", "source_path"}
                }
                | {
                    "source_path": str(record.get("source_path") or ""),
                    "can_restore": not Path(str(record.get("source_path") or "")).exists(),
                }
            )
    entries.sort(key=lambda item: str(item.get("deleted_at") or ""), reverse=True)
    return {
        "ok": True,
        "root": str(TRASH_ROOT.resolve()),
        "entries": entries,
        "total": len(entries),
    }


def restore_trash_entry(kind: str, entry_id: str) -> dict:
    record = _read_entry(kind, entry_id)
    if not record:
        return {"ok": False, "error": "回收站条目不存在或文件已损坏", "stale": True}
    source = Path(str(record.get("source_path") or "")).resolve()
    if source.exists():
        return {"ok": False, "error": f"原位置已有同名文件：{source}"}
    source.parent.mkdir(parents=True, exist_ok=True)
    payload_path = Path(str(record["payload_path"])).resolve()
    shutil.move(str(payload_path), str(source))
    shutil.rmtree(_entry_root(kind, entry_id), ignore_errors=True)
    return {
        "ok": True,
        "kind": kind,
        "id": entry_id,
        "restored_path": str(source),
        "game_dir": str(record.get("game_dir") or ""),
        "relative_path": str(record.get("relative_path") or ""),
    }


def permanently_delete_trash_entry(kind: str, entry_id: str) -> dict:
    record = _read_entry(kind, entry_id)
    if not record:
        return {"ok": False, "error": "回收站条目不存在或文件已损坏", "stale": True}
    shutil.rmtree(_entry_root(kind, entry_id), ignore_errors=False)
    return {"ok": True, "kind": kind, "id": entry_id, "permanently_deleted": True}


def empty_trash() -> dict:
    removed = 0
    for kind in TRASH_KINDS:
        kind_root = TRASH_ROOT / kind
        if not kind_root.is_dir():
            continue
        for entry_root in kind_root.iterdir():
            if entry_root.is_dir():
                shutil.rmtree(entry_root)
                removed += 1
    return {"ok": True, "removed_count": removed}
