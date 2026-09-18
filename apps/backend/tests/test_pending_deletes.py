import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services import pending_deletes, trash  # noqa: E402
from star_manager.services.mod_database_assets import delete_zipmod, retry_pending_deletes  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


class PendingDeleteTests(unittest.TestCase):
    def test_locked_zipmod_is_queued_and_retried_without_losing_database_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "game" / "mods" / "locked.zipmod"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"archive")
            db_path = root / "mods.sqlite"
            trash_root = root / "runtime" / "trash"
            pending_root = root / "runtime" / "pending-deletes"

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO zipmods (
                        guid, name, file_path, relative_path, file_name,
                        scan_status, last_scanned_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'ok', '', '', '')
                    """,
                    ("guid-locked", "Locked", str(source.resolve()), "locked.zipmod", source.name),
                )
            conn.close()

            lock_error = PermissionError(13, "sharing violation")
            lock_error.winerror = 32
            with patch.object(trash, "TRASH_ROOT", trash_root), patch.object(
                pending_deletes, "PENDING_DELETE_ROOT", pending_root
            ), patch(
                "star_manager.services.mod_database_assets.move_to_trash",
                side_effect=lock_error,
            ):
                result = delete_zipmod(1, db_path=db_path)

            self.assertTrue(result["ok"])
            self.assertTrue(result["queued"])
            self.assertTrue(source.exists())
            self.assertTrue((pending_root).is_dir())
            self.assertEqual(len(list(pending_root.glob("*.json"))), 1)
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM zipmods").fetchone()[0], 1)
            conn.close()

            with patch.object(trash, "TRASH_ROOT", trash_root), patch.object(
                pending_deletes, "PENDING_DELETE_ROOT", pending_root
            ):
                retried = retry_pending_deletes()
            self.assertEqual(retried["completed_count"], 1)
            self.assertEqual(retried["waiting_count"], 0)
            self.assertFalse(source.exists())
            with patch.object(pending_deletes, "PENDING_DELETE_ROOT", pending_root), patch.object(
                trash, "TRASH_ROOT", trash_root
            ):
                self.assertEqual(len(pending_deletes.list_pending_deletes()), 0)
                self.assertEqual(trash.list_trash()["total"], 1)
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM zipmods").fetchone()[0], 0)
            conn.close()


if __name__ == "__main__":
    unittest.main()
