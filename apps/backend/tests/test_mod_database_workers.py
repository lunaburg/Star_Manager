import sqlite3
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services import mod_database  # noqa: E402
from star_manager.services.mod_database import (  # noqa: E402
    build_candidates_from_file_stats,
    choose_build_worker_count,
    get_build_worker_limit,
    should_report_prepare_progress,
)
from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services.card_database import (  # noqa: E402
    choose_card_database_worker_count,
    get_card_database_worker_limit,
)


class ModDatabaseWorkerTests(unittest.TestCase):
    def test_worker_limit_is_capped_at_eight_workers(self):
        with patch("star_manager.services.mod_database.os.cpu_count", return_value=32):
            self.assertEqual(get_build_worker_limit(), 8)

    def test_worker_limit_keeps_one_worker_on_single_processor(self):
        with patch("star_manager.services.mod_database.os.cpu_count", return_value=1):
            self.assertEqual(get_build_worker_limit(), 1)

    def test_requested_worker_count_is_clamped_without_task_size(self):
        with patch("star_manager.services.mod_database.os.cpu_count", return_value=32):
            self.assertEqual(choose_build_worker_count(), 8)
            self.assertEqual(choose_build_worker_count(4), 4)
            self.assertEqual(choose_build_worker_count(8), 8)
            self.assertEqual(choose_build_worker_count(16), 8)
            self.assertEqual(choose_build_worker_count(32), 8)
            self.assertEqual(choose_build_worker_count(0), 1)

    def test_card_database_uses_the_same_worker_limit_and_setting(self):
        with patch("star_manager.services.card_database.os.cpu_count", return_value=32):
            self.assertEqual(get_card_database_worker_limit(), 8)
            self.assertEqual(choose_card_database_worker_count(8), 8)
            self.assertEqual(choose_card_database_worker_count(16), 8)
            self.assertEqual(choose_card_database_worker_count(32), 8)

    def test_prepare_progress_reports_every_hundred_and_the_final_item(self):
        reported = [
            completed
            for completed in range(1, 251)
            if should_report_prepare_progress(completed, 250)
        ]
        self.assertEqual(reported, [100, 200, 250])
        self.assertTrue(should_report_prepare_progress(1, 1))
        self.assertTrue(should_report_prepare_progress(99, 99))
        self.assertFalse(should_report_prepare_progress(99, 250))

    def test_changed_manifests_use_configured_workers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game_dir = Path(temp_dir)
            mods_dir = game_dir / "mods"
            mods_dir.mkdir()
            for name in ("first", "second"):
                with zipfile.ZipFile(mods_dir / f"{name}.zipmod", "w") as archive:
                    archive.writestr(
                        "manifest.xml",
                        f"<manifest><guid>{name}.guid</guid></manifest>",
                    )

            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            init_db(conn)
            barrier = threading.Barrier(2, timeout=5)
            thread_ids: set[int] = set()
            original_read_manifest = mod_database.read_manifest

            def concurrent_read_manifest(path: Path):
                thread_ids.add(threading.get_ident())
                barrier.wait()
                return original_read_manifest(path)

            with patch(
                "star_manager.services.mod_database.read_manifest",
                side_effect=concurrent_read_manifest,
            ):
                candidates, changed_paths, stats = build_candidates_from_file_stats(
                    conn,
                    game_dir,
                    force_full=True,
                    worker_count=2,
                )

            self.assertEqual(len(candidates), 2)
            self.assertEqual(len(changed_paths), 2)
            self.assertEqual(stats["changed_zipmods"], 2)
            self.assertEqual(len(thread_ids), 2)
            conn.close()


if __name__ == "__main__":
    unittest.main()
