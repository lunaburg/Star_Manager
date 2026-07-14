import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.achievements import (
    achievement_status,
    record_achievement_event,
    reset_achievements,
    update_achievement_preferences,
)
from star_manager.services.mod_database_core import init_db


class AchievementTests(unittest.TestCase):
    def test_static_and_event_achievement_progress(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "achievements.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        INSERT INTO character_cards(
                            file_path, parse_status, dependency_count, missing_count, last_scanned_at
                        ) VALUES ('card.png', 'ok', 4, 0, '2026-07-10T00:00:00Z')
                        """
                    )
            finally:
                conn.close()

            record_achievement_event("repairs", 40, "task:one", db_path=db_path)
            record_achievement_event("repairs", 60, "task:two", db_path=db_path)
            record_achievement_event("repairs", 60, "task:two", db_path=db_path)
            result = achievement_status(db_path)
            by_id = {item["id"]: item for item in result["achievements"]}

            self.assertTrue(by_id["zero_missing"]["unlocked"])
            self.assertEqual(by_id["doctor"]["progress"], 100)
            self.assertTrue(by_id["doctor"]["unlocked"])

    def test_preferences_and_reset(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "achievements.sqlite"
            sqlite3.connect(db_path).close()
            updated = update_achievement_preferences({"notifications": False}, db_path)
            self.assertFalse(updated["preferences"]["notifications"])

            record_achievement_event("repairs", 10, "task:repair", db_path=db_path)
            reset = reset_achievements(db_path)
            doctor = next(item for item in reset["achievements"] if item["id"] == "doctor")
            self.assertEqual(doctor["progress"], 0)
