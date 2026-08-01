import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import (  # noqa: E402
    list_character_card_tags,
    list_character_cards,
)
from star_manager.services.mod_database_core import init_db  # noqa: E402


class CardLibraryListingTests(unittest.TestCase):
    def test_uses_indexed_character_name_instead_of_file_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card = game / "UserData" / "chara" / "female" / "HS2ChaF_20260719.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")
            stat = card.stat()

            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, chara_name, tags_json, favorite, rating,
                        metadata_file_size, metadata_modified_ns, parse_status,
                        dependency_count, missing_count, last_scanned_at
                    ) VALUES (?, '永劫无间', '["古装"]', 1, 4, ?, ?, 'ok', 0, 0, '')
                    """,
                    (str(card.resolve()), stat.st_size, stat.st_mtime_ns),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_character_card_listing_data",
                side_effect=AssertionError("unchanged indexed cards must not read PNG payloads"),
            ):
                result = list_character_cards(str(game), "female", db_path=db_path)

            self.assertEqual(result["cards"][0]["name"], "永劫无间")
            self.assertIn("original=1", result["cards"][0]["cover_url"])
            self.assertNotIn("original=1", result["cards"][0]["thumbnail_url"])
            self.assertTrue(result["cards"][0]["favorite"])
            self.assertEqual(result["cards"][0]["rating"], 4)
            self.assertEqual(result["cards"][0]["tags"], ["古装"])

    def test_reads_character_name_for_unindexed_card(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir)
            card = game / "UserData" / "chara" / "female" / "HS2ChaF_20260719.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_character_card_listing_data",
                return_value={"name": "卡内姓名", "favorite": False, "rating": 0, "tags": []},
            ):
                result = list_character_cards(
                    str(game),
                    "female",
                    db_path=game / "missing.sqlite",
                )

            self.assertEqual(result["cards"][0]["name"], "卡内姓名")

    def test_lists_indexed_dependency_counts_for_each_card(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card = game / "UserData" / "chara" / "female" / "missing.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")
            stat = card.stat()

            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, metadata_file_size, metadata_modified_ns, parse_status,
                        dependency_count, missing_count, last_scanned_at
                    ) VALUES (?, ?, ?, 'ok', 6, 2, '')
                    """,
                    (str(card.resolve()), stat.st_size, stat.st_mtime_ns),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                result = list_character_cards(str(game), "female", db_path=db_path)

            self.assertTrue(result["ok"])
            self.assertEqual(result["cards"][0]["dependency_count"], 6)
            self.assertEqual(result["cards"][0]["missing_count"], 2)

    def test_unindexed_card_has_unknown_dependency_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir)
            card = game / "UserData" / "chara" / "female" / "new.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_character_card_listing_data",
                return_value={"name": "new", "favorite": False, "rating": 0, "tags": []},
            ):
                result = list_character_cards(
                    str(game),
                    "female",
                    db_path=game / "missing.sqlite",
                )

            self.assertIsNone(result["cards"][0]["dependency_count"])
            self.assertIsNone(result["cards"][0]["missing_count"])

    def test_library_scope_lists_matching_tags_recursively_and_ignores_navi(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir)
            card_root = game / "UserData" / "chara"
            matching = card_root / "female" / "Collection" / "matching.png"
            other = card_root / "male" / "other.png"
            ignored = card_root / "navi" / "ignored.png"
            for card in (matching, other, ignored):
                card.parent.mkdir(parents=True, exist_ok=True)
                card.write_bytes(b"card")

            def listing_data(card_path):
                tags = ["礼服"] if card_path.name != "other.png" else ["运动"]
                return {"name": card_path.stem, "favorite": False, "rating": 0, "tags": tags}

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_character_card_listing_data",
                side_effect=listing_data,
            ):
                result = list_character_cards(
                    str(game),
                    db_path=game / "missing.sqlite",
                    recursive=True,
                    tag="礼服",
                )

            self.assertTrue(result["recursive"])
            self.assertEqual(result["tag"], "礼服")
            self.assertEqual(
                [card["relative_path"] for card in result["cards"]],
                ["female/Collection/matching.png"],
            )

    def test_changed_indexed_card_refreshes_listing_cache_without_hiding_database_change(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card = game / "UserData" / "chara" / "female" / "changed.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"changed-card")
            stat = card.stat()
            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, chara_name, modified_at, metadata_file_size,
                        metadata_modified_ns, parse_status, last_scanned_at
                    ) VALUES (?, '旧姓名', 'old-index-signature', 1, 1, 'ok', '')
                    """,
                    (str(card.resolve()),),
                )
            conn.close()

            listing = {"name": "新姓名", "favorite": True, "rating": 5, "tags": ["礼服"]}
            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_character_card_listing_data",
                return_value=listing,
            ) as read_listing:
                result = list_character_cards(str(game), "female", db_path=db_path)

            self.assertEqual(result["cards"][0]["name"], "新姓名")
            self.assertTrue(result["cards"][0]["favorite"])
            read_listing.assert_called_once_with(card)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT * FROM character_cards").fetchone()
            finally:
                conn.close()
            self.assertEqual(row["modified_at"], "old-index-signature")
            self.assertEqual(row["metadata_file_size"], stat.st_size)
            self.assertEqual(row["metadata_modified_ns"], stat.st_mtime_ns)
            self.assertEqual(row["chara_name"], "新姓名")
            self.assertEqual(row["tags_json"], '["礼服"]')

    def test_global_tag_catalog_backfills_once_then_reads_sqlite_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            card = game / "UserData" / "chara" / "female" / "tagged.png"
            card.parent.mkdir(parents=True)
            card.write_bytes(b"card")
            db_path = root / "cards.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            with conn:
                conn.execute(
                    """
                    INSERT INTO character_cards (
                        file_path, parse_status, last_scanned_at
                    ) VALUES (?, 'ok', '')
                    """,
                    (str(card.resolve()),),
                )
            conn.close()

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.read_card_tags",
                return_value=["粉发", "礼服"],
            ) as read_tags:
                first = list_character_card_tags(str(game), db_path=db_path)

            self.assertFalse(first["cached"])
            self.assertEqual(first["tags"], ["礼服", "粉发"])
            read_tags.assert_called_once_with(card)

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.read_card_tags",
                side_effect=AssertionError("PNG metadata should not be read after backfill"),
            ):
                second = list_character_card_tags(str(game), db_path=db_path)

            self.assertTrue(second["cached"])
            self.assertEqual(second["tags"], ["礼服", "粉发"])


if __name__ == "__main__":
    unittest.main()
