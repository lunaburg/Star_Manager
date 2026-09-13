import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services import trash  # noqa: E402


class TrashTests(unittest.TestCase):
    def test_move_restore_and_permanent_delete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "game" / "UserData" / "chara" / "female" / "sample.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"card")
            trash_root = root / "runtime" / "trash"

            with patch.object(trash, "TRASH_ROOT", trash_root):
                record = trash.move_to_trash(
                    source,
                    "cards",
                    name="Sample",
                    metadata={"game_dir": str(root / "game"), "relative_path": "female/sample.png"},
                )
                self.assertFalse(source.exists())
                self.assertTrue((trash_root / "cards" / record["id"] / "record.json").exists())
                self.assertEqual(trash.list_trash()["total"], 1)

                restored = trash.restore_trash_entry("cards", record["id"])
                self.assertTrue(restored["ok"])
                self.assertEqual(source.read_bytes(), b"card")
                self.assertEqual(trash.list_trash()["total"], 0)

                second = trash.move_to_trash(source, "cards")
                deleted = trash.permanently_delete_trash_entry("cards", second["id"])
                self.assertTrue(deleted["ok"])
                self.assertFalse(source.exists())
                self.assertEqual(trash.list_trash()["total"], 0)

    def test_restore_rejects_existing_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "sample.zipmod"
            source.write_bytes(b"archive")
            trash_root = root / "runtime" / "trash"

            with patch.object(trash, "TRASH_ROOT", trash_root):
                record = trash.move_to_trash(source, "mods")
                source.write_bytes(b"replacement")
                result = trash.restore_trash_entry("mods", record["id"])
                self.assertFalse(result["ok"])
                self.assertIn("同名文件", result["error"])


if __name__ == "__main__":
    unittest.main()
