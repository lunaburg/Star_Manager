import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import (  # noqa: E402
    create_character_card_directory,
    move_character_card,
    rename_character_card_directory,
)
from star_manager.services.mod_database_core import init_db  # noqa: E402


class CardLibraryFolderTests(unittest.TestCase):
    def make_game(self, root: Path) -> Path:
        game = root / "game"
        (game / "UserData" / "chara" / "female").mkdir(parents=True)
        (game / "UserData" / "chara" / "male").mkdir(parents=True)
        return game

    def test_create_and_rename_managed_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = self.make_game(root)
            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                created = create_character_card_directory(str(game), "female", "收藏")
                renamed = rename_character_card_directory(
                    str(game), "female/收藏", "精选", root / "missing.sqlite"
                )

            self.assertTrue(created["ok"])
            self.assertTrue(renamed["ok"])
            self.assertTrue((game / "UserData" / "chara" / "female" / "精选").is_dir())

    def test_rename_updates_indexed_card_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = self.make_game(root)
            source_dir = game / "UserData" / "chara" / "female" / "Old"
            source_dir.mkdir()
            card = source_dir / "card.png"
            card.write_bytes(b"card")
            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, relative_path, file_name, parse_status, last_scanned_at
                    ) VALUES (?, ?, ?, 'ok', '')
                    """,
                    (str(card.resolve()), "female/Old/card.png", card.name),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                result = rename_character_card_directory(str(game), "female/Old", "New", db_path)

            self.assertTrue(result["ok"])
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT file_path, relative_path FROM character_cards"
            ).fetchone()
            conn.close()
            self.assertEqual(Path(row[0]), game / "UserData" / "chara" / "female" / "New" / "card.png")
            self.assertEqual(row[1], "female/New/card.png")

    def test_move_card_within_same_gender_and_update_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = self.make_game(root)
            source = game / "UserData" / "chara" / "female" / "Source" / "card.png"
            target_dir = game / "UserData" / "chara" / "female" / "Target"
            source.parent.mkdir()
            target_dir.mkdir()
            source.write_bytes(b"card")
            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, relative_path, file_name, parse_status, last_scanned_at
                    ) VALUES (?, ?, ?, 'ok', '')
                    """,
                    (str(source.resolve()), "female/Source/card.png", source.name),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ):
                result = move_character_card(
                    str(game), "female/Source/card.png", "female/Target", db_path
                )

            self.assertTrue(result["ok"])
            self.assertFalse(source.exists())
            self.assertTrue((target_dir / "card.png").is_file())
            conn = sqlite3.connect(db_path)
            relative_path = conn.execute(
                "SELECT relative_path FROM character_cards"
            ).fetchone()[0]
            conn.close()
            self.assertEqual(relative_path, "female/Target/card.png")

    def test_move_rejects_cross_gender_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = self.make_game(root)
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.write_bytes(b"card")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ):
                result = move_character_card(
                    str(game), "female/card.png", "male", root / "missing.sqlite"
                )

            self.assertFalse(result["ok"])
            self.assertIn("不能移动", result["error"])
            self.assertTrue(source.is_file())


if __name__ == "__main__":
    unittest.main()
