import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from app import server  # noqa: E402


class RestoredZipmodIndexTests(unittest.TestCase):
    def test_restored_zipmod_index_passes_all_required_paths(self):
        game_dir = r"D:\\HS2"
        restored_path = r"D:\\HS2\\mods\\Author\\sample.zipmod"
        expected = {"guid": "sample.guid"}

        with patch.object(server, "index_single_zipmod", return_value=expected) as index:
            result = server._index_restored_zipmod(game_dir, restored_path)

        self.assertIs(result, expected)
        index.assert_called_once_with(
            Path(game_dir),
            server.DEFAULT_DB_PATH,
            server.DEFAULT_THUMBNAIL_DIR,
            Path(restored_path),
        )


if __name__ == "__main__":
    unittest.main()
