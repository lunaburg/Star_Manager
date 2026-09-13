from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from star_manager.services.mod_database_core import DEFAULT_DB_PATH, init_db


ACHIEVEMENTS = (
    ("collector", "收藏家", "收录 1,000 张人物卡", 1000, "cards", "CARD"),
    ("zero_missing", "完美主义者", "完成一次依赖完整的角色卡资源库扫描", 1, "milestone", "ZERO"),
    ("archaeologist", "考古学家", "发现同一 GUID 的三个文件版本", 3, "versions", "GUID"),
    ("organizer", "整理大师", "清理 10 GB 重复资源", 10 * 1024**3, "bytes", "10G"),
    ("doctor", "急救医生", "修复 100 个缩略图或资源异常", 100, "repairs", "FIX"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path.resolve())
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS achievement_progress (
            achievement_id TEXT PRIMARY KEY,
            progress_value INTEGER NOT NULL DEFAULT 0,
            unlocked_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS achievement_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT NOT NULL UNIQUE,
            event_type TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 0,
            detail TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS achievement_preferences (
            key TEXT PRIMARY KEY,
            value INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    for key, default in (("enabled", 1), ("notifications", 1), ("hide_locked", 0)):
        conn.execute(
            "INSERT OR IGNORE INTO achievement_preferences(key, value) VALUES (?, ?)",
            (key, default),
        )
    conn.commit()
    return conn


def _upsert_max(conn: sqlite3.Connection, achievement_id: str, value: int) -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO achievement_progress(achievement_id, progress_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(achievement_id) DO UPDATE SET
            progress_value = MAX(progress_value, excluded.progress_value),
            updated_at = excluded.updated_at
        """,
        (achievement_id, max(0, int(value)), now),
    )


def record_achievement_event(
    event_type: str,
    value: int,
    event_key: str,
    detail: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    if value <= 0 or not event_key:
        return
    conn = _connect(db_path)
    try:
        enabled = conn.execute(
            "SELECT value FROM achievement_preferences WHERE key = 'enabled'"
        ).fetchone()[0]
        if not enabled:
            return
        with conn:
            inserted = conn.execute(
                "INSERT OR IGNORE INTO achievement_events(event_key, event_type, value, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (event_key, event_type, int(value), detail, _now()),
            ).rowcount
            if not inserted:
                return
            achievement_id = "organizer" if event_type == "duplicate_bytes" else "doctor"
            total = conn.execute(
                "SELECT COALESCE(SUM(value), 0) FROM achievement_events WHERE event_type = ?",
                (event_type,),
            ).fetchone()[0]
            _upsert_max(conn, achievement_id, int(total))
    finally:
        conn.close()


def achievement_status(db_path: Path = DEFAULT_DB_PATH) -> dict:
    conn = _connect(db_path)
    try:
        preferences = {
            row["key"]: bool(row["value"])
            for row in conn.execute("SELECT key, value FROM achievement_preferences")
        }
        if preferences.get("enabled", True):
            card_count = int(conn.execute("SELECT COUNT(*) FROM character_cards WHERE parse_status != 'stale'").fetchone()[0])
            dependency_count = int(conn.execute("SELECT COALESCE(SUM(dependency_count), 0) FROM character_cards WHERE parse_status != 'stale'").fetchone()[0])
            missing_count = int(conn.execute("SELECT COALESCE(SUM(missing_count), 0) FROM character_cards WHERE parse_status != 'stale'").fetchone()[0])
            version_count = int(conn.execute("SELECT COALESCE(MAX(version_count), 0) FROM (SELECT COUNT(*) + 1 AS version_count FROM duplicate_zipmods GROUP BY guid)").fetchone()[0])
            with conn:
                _upsert_max(conn, "collector", card_count)
                _upsert_max(conn, "archaeologist", version_count)
                if dependency_count > 0 and missing_count == 0:
                    _upsert_max(conn, "zero_missing", 1)

        rows = {
            row["achievement_id"]: row
            for row in conn.execute("SELECT * FROM achievement_progress")
        }
        result = []
        with conn:
            for achievement_id, title, description, target, unit, icon in ACHIEVEMENTS:
                row = rows.get(achievement_id)
                progress = int(row["progress_value"] if row else 0)
                unlocked_at = str(row["unlocked_at"] if row else "")
                if progress >= target and not unlocked_at:
                    unlocked_at = _now()
                    conn.execute(
                        "UPDATE achievement_progress SET unlocked_at = ?, updated_at = ? WHERE achievement_id = ?",
                        (unlocked_at, unlocked_at, achievement_id),
                    )
                result.append({
                    "id": achievement_id,
                    "title": title,
                    "description": description,
                    "progress": progress,
                    "target": target,
                    "unit": unit,
                    "icon": icon,
                    "unlocked": progress >= target,
                    "unlocked_at": unlocked_at,
                })
        return {
            "ok": True,
            "achievements": result,
            "unlocked_count": sum(1 for item in result if item["unlocked"]),
            "preferences": preferences,
        }
    finally:
        conn.close()


def update_achievement_preferences(values: dict, db_path: Path = DEFAULT_DB_PATH) -> dict:
    conn = _connect(db_path)
    try:
        with conn:
            for key in ("enabled", "notifications", "hide_locked"):
                if key in values:
                    conn.execute(
                        "INSERT INTO achievement_preferences(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                        (key, 1 if values[key] else 0),
                    )
        return achievement_status(db_path)
    finally:
        conn.close()


def reset_achievements(db_path: Path = DEFAULT_DB_PATH) -> dict:
    conn = _connect(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM achievement_events")
            conn.execute("DELETE FROM achievement_progress")
        return achievement_status(db_path)
    finally:
        conn.close()
