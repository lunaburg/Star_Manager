import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import (  # noqa: E402
    build_clothes_card_tree,
    get_clothes_card_detail,
    list_clothes_cards,
    resolve_coordinate_file,
)


class ClothesCardLibraryTests(unittest.TestCase):
    def make_game(self, root: Path) -> tuple[Path, Path]:
        game = root / "game"
        coordinate = game / "UserData" / "coordinate"
        (coordinate / "female" / "summer").mkdir(parents=True)
        (coordinate / "male").mkdir(parents=True)
        return game, coordinate

    def test_tree_and_list_keep_coordinate_cards_separate_from_character_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, coordinate = self.make_game(Path(temp_dir))
            valid = coordinate / "female" / "summer" / "dress.png"
            ordinary = coordinate / "female" / "summer" / "ordinary.png"
            character = game / "UserData" / "chara" / "female" / "character.png"
            valid.write_bytes(b"clothes")
            ordinary.write_bytes(b"ordinary")
            character.parent.mkdir(parents=True)
            character.write_bytes(b"character")

            parsed = {
                "marker": "【AIS_Clothes】",
                "name": "Summer Dress",
                "clothes_parts": [{}] * 8,
                "accessory_parts": [{}] * 20,
                "dependencies": [{"mod_id": "example.mod"}],
                "dependency_count": 1,
                "plugins": ["moreAccessories"],
                "plugin_count": 1,
            }
            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.inspect_clothes_card_listing_file",
                side_effect=lambda path: parsed if path == valid else None,
            ) as inspect_listing:
                tree = build_clothes_card_tree(str(game))
                result = list_clothes_cards(
                    str(game), "female/summer", index_path=Path(temp_dir) / "clothes.sqlite"
                )

            self.assertTrue(tree["ok"])
            self.assertEqual(tree["total"], 2)
            self.assertTrue(tree["tree"]["children"][0]["children"][0]["count_is_candidate"])
            self.assertTrue(result["ok"])
            self.assertEqual([item["filename"] for item in result["cards"]], ["dress.png"])
            self.assertEqual(result["cards"][0]["name"], "Summer Dress")
            self.assertFalse(result["cards"][0]["metadata_pending"])
            self.assertEqual(result["candidate_total"], 2)
            self.assertFalse(result["indexing"])
            self.assertEqual(inspect_listing.call_count, 2)

    def test_list_supports_offset_and_limit_for_progressive_loading(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, coordinate = self.make_game(Path(temp_dir))
            first = coordinate / "female" / "first.png"
            second = coordinate / "female" / "second.png"
            third = coordinate / "female" / "third.png"
            for path in (first, second, third):
                path.write_bytes(b"clothes")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.inspect_clothes_card_listing_file",
                return_value={"marker": "【AIS_Clothes】", "name": "Card"},
            ):
                result = list_clothes_cards(
                    str(game), "female", offset=1, limit=1,
                    index_path=Path(temp_dir) / "clothes.sqlite",
                )

            self.assertTrue(result["ok"])
            self.assertEqual([item["filename"] for item in result["cards"]], ["second.png"])
            self.assertEqual(result["offset"], 1)
            self.assertEqual(result["limit"], 1)
            self.assertTrue(result["has_more"])
            self.assertEqual(result["total"], 3)

    def test_listing_cache_reuses_unchanged_files_and_reparses_changed_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, coordinate = self.make_game(Path(temp_dir))
            files = [coordinate / "female" / f"card-{index}.png" for index in range(3)]
            for file_path in files:
                file_path.write_bytes(b"clothes")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.inspect_clothes_card_listing_file",
                side_effect=lambda path: {"marker": "【AIS_Clothes】", "name": path.stem},
            ) as inspect_listing:
                index_path = Path(temp_dir) / "clothes.sqlite"
                first = list_clothes_cards(str(game), "female", offset=0, limit=1, index_path=index_path)
                second = list_clothes_cards(str(game), "female", offset=2, limit=1, index_path=index_path)

                self.assertEqual([card["filename"] for card in first["cards"]], ["card-0.png"])
                self.assertEqual([card["filename"] for card in second["cards"]], ["card-2.png"])
                self.assertEqual(first["total"], 3)
                self.assertEqual(second["total"], 3)
                self.assertEqual(inspect_listing.call_count, 3)

                files[0].write_bytes(b"changed card")
                list_clothes_cards(str(game), "female", offset=0, limit=1, index_path=index_path)
                self.assertEqual(inspect_listing.call_count, 4)

    def test_detail_returns_parsed_summary_and_rejects_character_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, coordinate = self.make_game(Path(temp_dir))
            card = coordinate / "female" / "outfit.png"
            card.write_bytes(b"clothes")
            parsed = {
                "marker": "【AIS_Clothes】",
                "version": "0.0.0",
                "name": "Outfit",
                "clothes_parts": [{"slot": 0, "label": "上衣", "id": 100}],
                "accessory_parts": [],
                "dependencies": [{"mod_id": "example.mod", "property": "ChaFileClothes.ClothesTop"}],
                "dependency_count": 1,
                "plugins": ["moreAccessories"],
                "plugin_count": 1,
                "coordinate_size": 128,
                "extension_name": "KKEx",
                "extension_version": 3,
                "extension_size": 40,
            }
            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.inspect_clothes_card_file", return_value=parsed
            ):
                result = get_clothes_card_detail(str(game), "female/outfit.png")

            self.assertTrue(result["ok"])
            self.assertEqual(result["card"]["name"], "Outfit")
            self.assertEqual(result["card"]["dependencies"][0]["mod_id"], "example.mod")

            with self.assertRaises(ValueError):
                resolve_coordinate_file(coordinate, "../chara/female/character.png")


if __name__ == "__main__":
    unittest.main()
