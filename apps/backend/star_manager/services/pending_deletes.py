from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from star_manager.core.runtime_paths import runtime_root


PENDING_DELETE_ROOT = runtime_root() / "pending-deletes"
_PENDING_DELETE_RETRY_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record_path(operation_id: str) -> Path:
    if not operation_id or Path(operation_id).name != operation_id:
        raise ValueError("Invalid pending delete id")
    return (PENDING_DELETE_ROOT / f"{operation_id}.json").resolve()


def _write_record(record: dict) -> None:
    path = _record_path(str(record["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def enqueue_pending_delete(operation: str, payload: dict, error: str = "") -> dict:
    normalized_payload = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    for existing in list_pending_deletes():
        if existing.get("operation") == str(operation) and existing.get("payload") == normalized_payload:
            return existing
    operation_id = uuid4().hex
    record = {
        "id": operation_id,
        "operation": str(operation),
        "payload": normalized_payload,
        "created_at": _now(),
        "updated_at": _now(),
        "attempts": 0,
        "last_error": str(error or ""),
    }
    _write_record(record)
    return record


def list_pending_deletes() -> list[dict]:
    if not PENDING_DELETE_ROOT.is_dir():
        return []
    records: list[dict] = []
    for path in PENDING_DELETE_ROOT.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(record, dict) and record.get("id") == path.stem:
            records.append(record)
    records.sort(key=lambda item: str(item.get("created_at") or ""))
    return records


def update_pending_delete(record: dict, error: str) -> dict:
    updated = dict(record)
    updated["attempts"] = int(updated.get("attempts") or 0) + 1
    updated["updated_at"] = _now()
    updated["last_error"] = str(error or "")
    _write_record(updated)
    return updated


def remove_pending_delete(operation_id: str) -> None:
    _record_path(operation_id).unlink(missing_ok=True)


def acquire_retry_lock() -> bool:
    return _PENDING_DELETE_RETRY_LOCK.acquire(blocking=False)


def release_retry_lock() -> None:
    _PENDING_DELETE_RETRY_LOCK.release()


def is_transient_file_lock_error(error: BaseException) -> bool:
    """Return whether Windows is reporting a sharing/lock failure.

    Do not queue ordinary path, archive, or permission errors: those need to be
    shown to the user instead of being retried forever.
    """
    current: BaseException | None = error
    while current is not None:
        winerror = getattr(current, "winerror", None)
        if winerror in {32, 33}:
            return True
        message = str(current).lower()
        if any(
            marker in message
            for marker in (
                "sharing violation",
                "used by another process",
                "being used by another process",
                "另一个程序正在使用",
                "另一进程正在使用",
            )
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


def start_pending_delete_worker() -> None:
    """Retry locked deletions while the backend is alive.

    The queue is deliberately file-backed, so restarting the manager does not
    lose a deletion request.  The worker is best-effort; the HTTP endpoint is
    also available for an immediate manual retry and diagnostics.
    """
    def run() -> None:
        while True:
            time.sleep(5)
            if not list_pending_deletes():
                continue
            try:
                from star_manager.services.mod_database_assets import retry_pending_deletes

                retry_pending_deletes()
            except Exception as error:  # keep the backend alive if a retry is malformed
                print(f"Pending deletion retry failed: {error}", flush=True)

    threading.Thread(target=run, name="pending-delete-worker", daemon=True).start()
