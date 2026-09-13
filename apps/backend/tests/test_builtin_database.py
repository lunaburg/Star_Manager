import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.builtin_database import (  # noqa: E402
    BuiltinItem,
    build_builtin_items_index,
    normalize_game_dir_key,
    resolve_builtin_coordinate_dependencies,
)
from star_manager.services.card_library import resolve_character_card_dependencies  # noqa: E402
from star_manager.services.mod_database_core import ThumbnailResult, init_db  # noqa: E402


class BuiltinDatabaseTests(unittest.TestCase):
    def test_scans_and_replaces_items_for_one_game_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            list_bundle = game / "abdata" / "list" / "characustom" / "00.unity3d"
            main_bundle = game / "abdata" / "chara" / "00" / "fo_top_00.unity3d"
            thumb_bundle = game / "abdata" / "chara" / "thumb" / "00" / "fo_top_00.unity3d"
            for path in (list_bundle, main_bundle, thumb_bundle):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"bundle")
            db_path = root / "star-manager.sqlite"
            thumbnail_dir = root / "thumbnails"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            item = BuiltinItem(
                game_dir_key=normalize_game_dir_key(game),
                game_dir=str(game.resolve()),
                category_no="240",
                item_id="1",
                name="原版上衣",
                name_en="Top",
                name_zh_cn="",
                name_zh_tw="",
                source_path="abdata/list/characustom/00.unity3d",
                source_asset="fo_top_00",
                main_manifest="abdata",
                main_ab="chara/00/fo_top_00.unity3d",
                main_data="p_cf_top_onepiece1",
                thumb_ab="chara/thumb/00/fo_top_00.unity3d",
                thumb_tex="p_cf_top_onepiece1",
            )

            with patch(
                "star_manager.services.builtin_database._read_bundle_items",
                return_value=[item],
            ), patch(
                "star_manager.services.builtin_database._extract_builtin_thumbnail",
                return_value=ThumbnailResult("", "missing", "test"),
            ):
                stats = build_builtin_items_index(conn, game, thumbnail_dir, mode="full")

            row = conn.execute(
                "SELECT category_no, item_id, name, resource_status FROM builtin_items"
            ).fetchone()
            self.assertEqual(stats["builtin_list_bundles"], 1)
            self.assertEqual(stats["builtin_items"], 1)
            self.assertEqual(dict(row), {
                "category_no": "240",
                "item_id": "1",
                "name": "原版上衣",
                "resource_status": "in_game",
            })

            conn.close()

    def test_coordinate_ids_resolve_by_category_and_skip_empty_slots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            db_path = root / "star-manager.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            key = normalize_game_dir_key(game)
            conn.execute(
                """
                INSERT INTO builtin_items (
                    game_dir_key, game_dir, category_no, item_id, name,
                    source_path, thumbnail_status, resource_status, parser_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (key, str(game.resolve()), "240", "1", "原版上衣", "abdata/list/characustom/00.unity3d", "missing", "in_game", "1", "now", "now"),
            )
            conn.commit()
            conn.close()

            dependencies = resolve_builtin_coordinate_dependencies(
                game,
                {
                    "clothes_parts": [
                        {"slot": 0, "id": 1},
                        {"slot": 3, "id": 0},
                    ],
                    "accessory_parts": [
                        {"slot": 0, "type": 350, "id": 1},
                    ],
                },
                db_path,
            )

            self.assertEqual(len(dependencies), 1)
            self.assertEqual(dependencies[0]["category_no"], "240")
            self.assertEqual(dependencies[0]["source_type"], "builtin")
            self.assertTrue(dependencies[0]["matched"])

            occupied = resolve_builtin_coordinate_dependencies(
                game,
                {"clothes_parts": [{"slot": 0, "id": 1}], "accessory_parts": []},
                db_path,
                occupied_dependencies=[
                    {
                        "category_no": "240",
                        "property": "outfit.ChaFileClothes.ClothesTop",
                    }
                ],
            )
            self.assertEqual(occupied, [])

    def test_character_card_coordinate_items_are_added_to_uar_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            db_path = root / "star-manager.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            key = normalize_game_dir_key(game)
            conn.execute(
                """
                INSERT INTO builtin_items (
                    game_dir_key, game_dir, category_no, item_id, name,
                    source_path, thumbnail_status, resource_status, parser_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    str(game.resolve()),
                    "240",
                    "1",
                    "原版人物卡上衣",
                    "abdata/list/characustom/00.unity3d",
                    "missing",
                    "in_game",
                    "1",
                    "now",
                    "now",
                ),
            )
            conn.commit()
            conn.close()

            uar_dependency = {
                "mod_id": "example.mod",
                "category_no": "240",
                "slot": "100",
                "local_slot": "",
                "property": "outfit.ChaFileClothes.ClothesTop",
                "matched": False,
                "zipmod": None,
                "item": None,
            }
            with patch(
                "star_manager.services.card_library.resolve_card_dependencies",
                return_value=[uar_dependency],
            ), patch(
                "star_manager.services.card_library.extract_character_coordinate_parts",
                return_value={
                    "clothes_parts": [{"slot": 0, "id": 1}],
                    "accessory_parts": [],
                },
            ):
                dependencies = resolve_character_card_dependencies(
                    "character.png", game, db_path=db_path
                )

            self.assertEqual(len(dependencies), 1)
            self.assertEqual(dependencies[0]["mod_id"], "example.mod")


if __name__ == "__main__":
    unittest.main()
