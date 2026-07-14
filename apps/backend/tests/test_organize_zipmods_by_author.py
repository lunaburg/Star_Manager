import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402


class Reporter:
    def progress(self, *_args):
        pass

    def message(self, *_args):
        pass

    def title(self, *_args):
        pass


class OrganizeZipmodsByAuthorTests(unittest.TestCase):
    def test_moves_all_zipmods_without_overwriting_collisions(self):
        with TemporaryDirectory() as temp_dir:
            game_dir = Path(temp_dir)
            (game_dir / "mods" / "one").mkdir(parents=True)
            (game_dir / "mods" / "two").mkdir(parents=True)
            (game_dir / "abdata").mkdir()
            (game_dir / "UserData" / "chara").mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").touch()
            self._write_zipmod(game_dir / "mods" / "one" / "same.zipmod", "Author:One")
            self._write_zipmod(game_dir / "mods" / "two" / "same.zipmod", "Author:One")

            result = bridge.organize_all_zipmods_by_author(str(game_dir), Reporter())

            self.assertTrue(result["ok"])
            self.assertEqual(result["moved_count"], 2)
            targets = sorted((game_dir / "mods" / "Author_One").glob("*.zipmod"))
            self.assertEqual([path.name for path in targets], ["same.zipmod", "same_1.zipmod"])
            self.assertEqual(result["removed_empty_dir_count"], 2)
            self.assertFalse((game_dir / "mods" / "one").exists())
            self.assertFalse((game_dir / "mods" / "two").exists())
            self.assertTrue((game_dir / "mods").is_dir())

    @staticmethod
    def _write_zipmod(path: Path, author: str):
        manifest = (
            "<manifest><guid>sample.guid</guid><name>Sample</name>"
            f"<version>1</version><author>{author}</author></manifest>"
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("manifest.xml", manifest)


if __name__ == "__main__":
    unittest.main()
