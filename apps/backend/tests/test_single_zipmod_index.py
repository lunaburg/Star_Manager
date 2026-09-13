import sqlite3
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database import index_single_zipmod  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


class SingleZipmodIndexTests(unittest.TestCase):
    def test_indexes_only_requested_zipmod(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "game"
            target_path = game_dir / "mods" / "Author" / "target.zipmod"
            other_path = game_dir / "mods" / "Other" / "other.zipmod"
            target_path.parent.mkdir(parents=True)
            other_path.parent.mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").write_bytes(b"")
            other_path.write_bytes(b"not a zipmod")

            with zipfile.ZipFile(target_path, "w") as archive:
                archive.writestr(
                    "manifest.xml",
                    "<manifest><guid>target.guid</guid><name>Target</name>"
                    "<version>1</version><author>Author</author></manifest>",
                )
                archive.writestr(
                    "abdata/list/target.csv",
                    "0\n0\nTarget\nID,Kind,Name,MainAB,MainData\n"
                    "100,1,Target Item,0,0\n",
                )

            db_path = root / "runtime" / "star-manager.sqlite"
            thumbnail_dir = root / "runtime" / "thumbnails"
            db_path.parent.mkdir(parents=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                conn.execute(
                    """
                    INSERT INTO zipmods (
                        guid, name, version, author, file_path, relative_path, file_name,
                        scan_status, last_scanned_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                    """,
                    (
                        "other.guid",
                        "Other",
                        "1",
                        "Other",
                        str(other_path),
                        "Other/other.zipmod",
                        other_path.name,
                        now,
                        now,
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            with patch(
                "star_manager.services.mod_database_assets.find_zipmods",
                side_effect=AssertionError("single zipmod indexing must not scan the mods directory"),
            ):
                stats = index_single_zipmod(
                    game_dir,
                    db_path,
                    thumbnail_dir,
                    target_path,
                )

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT guid, file_path, item_count FROM zipmods ORDER BY guid"
                ).fetchall()
                items = conn.execute(
                    "SELECT zipmod_guid, item_id, name FROM mod_items"
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(stats["scanned_zipmods"], 1)
            self.assertEqual([row["guid"] for row in rows], ["other.guid", "target.guid"])
            self.assertEqual(rows[0]["file_path"], str(other_path))
            self.assertEqual(rows[1]["file_path"], str(target_path))
            self.assertEqual([(row["zipmod_guid"], row["item_id"], row["name"]) for row in items], [
                ("target.guid", "100", "Target Item")
            ])


if __name__ == "__main__":
    unittest.main()
