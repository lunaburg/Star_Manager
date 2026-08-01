import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import delete_character_card  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


class CardLibraryDeleteTests(unittest.TestCase):
    def test_deletes_valid_card_database_record_and_preview(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card = game / "UserData" / "chara" / "female" / "delete-me.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")
            preview_dir = root / "previews"
            preview = preview_dir / "aa" / "bb" / "preview.png"
            preview.parent.mkdir(parents=True)
            preview.write_bytes(b"preview")
            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (file_path, preview_cache_path, parse_status, last_scanned_at)
                    VALUES (?, ?, 'ok', '')
                    """,
                    (str(card.resolve()), str(preview.resolve())),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ):
                result = delete_character_card(str(game), "female/delete-me.png", db_path, preview_dir)

            self.assertTrue(result["ok"])
            self.assertFalse(card.exists())
            self.assertFalse(preview.exists())
            conn = sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM character_cards").fetchone()[0], 0)
            conn.close()

    def test_rejects_path_outside_character_card_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card_root = game / "UserData" / "chara"
            card_root.mkdir(parents=True)
            outside = game / "keep.png"
            outside.write_bytes(b"keep")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                result = delete_character_card(str(game), "../../keep.png", root / "missing.sqlite")

            self.assertFalse(result["ok"])
            self.assertTrue(outside.exists())

if __name__ == "__main__":
    unittest.main()
