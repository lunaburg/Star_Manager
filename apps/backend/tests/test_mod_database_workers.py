import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database import (  # noqa: E402
    choose_build_worker_count,
    get_build_worker_limit,
)
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


if __name__ == "__main__":
    unittest.main()
