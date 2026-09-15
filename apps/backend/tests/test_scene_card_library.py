import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_library import (  # noqa: E402
    build_scene_card_tree,
    get_scene_card_detail,
    list_scene_cards,
    resolve_scene_file,
    resolve_dependency_records,
)
from star_manager.services.mod_database_core import init_db  # noqa: E402


class SceneCardLibraryTests(unittest.TestCase):
    def make_game(self, root: Path) -> tuple[Path, Path]:
        game = root / "game"
        scene = game / "UserData" / "studio" / "scene"
        (scene / "室内").mkdir(parents=True)
        (scene / "室外").mkdir(parents=True)
        return game, scene

    def test_tree_and_list_use_studio_scene_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, scene = self.make_game(Path(temp_dir))
            first = scene / "室内" / "living-room.png"
            second = scene / "室外" / "garden.png"
            ordinary = scene / "室内" / "notes.txt"
            first.write_bytes(b"scene")
            second.write_bytes(b"scene")
            ordinary.write_text("ignore", encoding="utf-8")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                tree = build_scene_card_tree(str(game))
                result = list_scene_cards(str(game), "室内", limit=1)

            self.assertTrue(tree["ok"])
            self.assertEqual(tree["total"], 2)
            self.assertTrue(result["ok"])
            self.assertEqual([item["filename"] for item in result["cards"]], ["living-room.png"])
            self.assertEqual(result["cards"][0]["name"], "living-room")
            self.assertIn("/library/scene/image?", result["cards"][0]["thumbnail_url"])
            self.assertTrue(result["has_more"] is False)

    def test_scene_detail_returns_file_metadata_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, scene = self.make_game(Path(temp_dir))
            card = scene / "室内" / "living-room.png"
            card.write_bytes(b"scene")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True):
                result = get_scene_card_detail(str(game), "室内/living-room.png")

            self.assertTrue(result["ok"])
            self.assertEqual(result["card"]["relative_path"], "室内/living-room.png")
            self.assertEqual(result["card"]["file_size"], len(b"scene"))
            self.assertIn("original=1", result["card"]["cover_url"])

            with self.assertRaises(ValueError):
                resolve_scene_file(scene, "../coordinate/female/outfit.png")

    def test_scene_detail_includes_resolved_scene_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game, scene = self.make_game(Path(temp_dir))
            card = scene / "室内" / "school-pool.png"
            card.write_bytes(b"scene")
            parsed = {
                "is_scene_card": True,
                "scene_marker": "【StudioNEOV2】",
                "plugin_ids": ["com.bepis.sideloader.universalautoresolver"],
                "dependencies": [{
                    "ModID": "com.example.schoolpool",
                    "Name": "com.example.schoolpool",
                    "Property": "StudioScene.Map",
                    "DependencyType": "scene",
                }],
                "dependency_count": 1,
            }
            resolved = [{
                "id": "scene:com.example.schoolpool:0",
                "mod_id": "com.example.schoolpool",
                "name": "com.example.schoolpool",
                "property": "StudioScene.Map",
                "dependency_type": "scene",
                "source_type": "scene",
                "matched": True,
                "zipmod": {"name": "School Pool", "guid": "com.example.schoolpool"},
                "item": None,
            }]

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.inspect_scene_card_file", return_value=parsed
            ), patch(
                "star_manager.services.card_library.resolve_dependency_records", return_value=resolved
            ):
                result = get_scene_card_detail(str(game), "室内/school-pool.png")

            self.assertTrue(result["ok"])
            self.assertEqual(result["card"]["plugin_ids"], parsed["plugin_ids"])
            self.assertEqual(result["card"]["dependency_count"], 1)
            self.assertEqual(result["card"]["dependencies"][0]["dependency_type"], "scene")

    def test_scene_item_dependencies_match_indexed_item_by_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "mods.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            init_db(conn)
            conn.execute(
                """
                INSERT INTO zipmods (guid, name, file_path, scan_status, last_scanned_at, created_at, updated_at)
                VALUES (?, ?, ?, 'ready', ?, ?, ?)
                """,
                ("alex7997.patterns", "Pattern Pack", "pattern.zipmod", "now", "now", "now"),
            )
            zipmod_id = conn.execute("SELECT id FROM zipmods WHERE guid = ?", ("alex7997.patterns",)).fetchone()[0]
            conn.execute(
                """
                INSERT INTO mod_items (zipmod_id, zipmod_guid, item_id, kind, name, parse_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'ready', ?, ?)
                """,
                (zipmod_id, "alex7997.patterns", "184", "348", "Pattern 184", "now", "now"),
            )
            conn.commit()
            conn.close()

            resolved = resolve_dependency_records(
                [{
                    "ModID": "alex7997.patterns",
                    "Slot": 184,
                    "LocalSlot": 100002838,
                    "Property": "StudioScene.Pattern",
                    "DependencyType": "scene_pattern",
                }],
                db_path=db_path,
            )

            self.assertEqual(len(resolved), 1)
            self.assertTrue(resolved[0]["matched"])
            self.assertEqual(resolved[0]["item"]["name"], "Pattern 184")


if __name__ == "__main__":
    unittest.main()
