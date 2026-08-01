import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from star_manager.services.card_library import (
    export_character_dependency_package,
    export_character_card_coordinate,
    set_character_card_as_navi,
)


class CardLibraryNaviTests(unittest.TestCase):
    def test_replaces_selected_navi_slot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir)
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"new-card")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ):
                result = set_character_card_as_navi(str(game), "female/card.png", "sitri")

            self.assertTrue(result["ok"])
            self.assertEqual((game / "UserData" / "chara" / "navi" / "sitri.png").read_bytes(), b"new-card")

    def test_rejects_unknown_slot(self):
        result = set_character_card_as_navi("", "", "other")
        self.assertFalse(result["ok"])

    def test_exports_coordinate_to_matching_sex_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir)
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"character-card")

            def fake_convert(source_path, output_path, **kwargs):
                self.assertEqual(source_path, source.resolve())
                self.assertEqual(kwargs["name"], "My:Outfit")
                output_path.write_bytes(b"coordinate-card")
                return {
                    "coordinate_dependencies": 3,
                    "copied_plugins": ["resolver"],
                    "skipped_plugins": ["body-plugin"],
                    "output_size": 15,
                }

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.convert_character_card",
                side_effect=fake_convert,
            ):
                result = export_character_card_coordinate(
                    str(game), "female/card.png", "My:Outfit"
                )

            target = game / "UserData" / "coordinate" / "female" / "My_Outfit.png"
            self.assertTrue(result["ok"])
            self.assertEqual(Path(result["target_path"]), target)
            self.assertEqual(target.read_bytes(), b"coordinate-card")
            self.assertEqual(result["coordinate_dependencies"], 3)
            self.assertEqual(result["skipped_plugins"], ["body-plugin"])

    def test_exports_coordinate_to_configured_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            game = Path(temp_dir) / "game"
            output_dir = Path(temp_dir) / "exports"
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.parent.mkdir(parents=True)
            output_dir.mkdir()
            source.write_bytes(b"character-card")

            def fake_convert(_source_path, output_path, **_kwargs):
                output_path.write_bytes(b"coordinate-card")
                return {"output_size": 15}

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.convert_character_card",
                side_effect=fake_convert,
            ):
                result = export_character_card_coordinate(
                    str(game), "female/card.png", "", str(output_dir)
                )

            target = output_dir / "card.png"
            self.assertTrue(result["ok"])
            self.assertEqual(Path(result["target_path"]), target)
            self.assertEqual(target.read_bytes(), b"coordinate-card")

    def test_exports_compressed_portable_dependency_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            output_dir = root / "exports"
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.parent.mkdir(parents=True)
            output_dir.mkdir()
            source.write_bytes(b"character-card")
            dependencies = [
                {"mod_id": "sample.guid", "category_no": "300", "zipmod": {"id": 7, "guid": "sample.guid", "name": "Sample"}},
                {"mod_id": "sample.guid", "category_no": "301", "zipmod": {"id": 7, "guid": "sample.guid", "name": "Sample"}},
                {"mod_id": "missing.guid", "category_no": "110", "zipmod": None},
            ]

            def fake_export(ids, target_dir, mode, layout, **_kwargs):
                self.assertEqual(list(ids), [7])
                self.assertEqual((mode, layout), ("copy", "portable"))
                target = Path(target_dir)
                (target / "mods" / "Sideloader").mkdir(parents=True)
                (target / "mods" / "Sideloader" / "sample.zipmod").write_bytes(b"zipmod")
                (target / "abdata" / "chara").mkdir(parents=True)
                (target / "abdata" / "chara" / "sample.unity3d").write_bytes(b"bundle")
                return {
                    "ok": True,
                    "exported_count": 1,
                    "exported_unity3d_count": 1,
                    "failure_count": 0,
                    "failures": [],
                }

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.resolve_card_dependencies", return_value=dependencies
            ), patch(
                "star_manager.services.card_library.export_zipmods", side_effect=fake_export
            ):
                result = export_character_dependency_package(
                    str(game), "female/card.png", str(output_dir), True
                )

            self.assertTrue(result["ok"])
            self.assertTrue(result["compressed"])
            self.assertEqual(result["exported_zipmod_count"], 1)
            self.assertEqual(result["missing_mod_ids"], ["missing.guid"])
            with zipfile.ZipFile(result["target_path"]) as archive:
                names = set(archive.namelist())
                self.assertIn("UserData/chara/female/card.png", names)
                self.assertIn("mods/Sideloader/sample.zipmod", names)
                self.assertIn("abdata/chara/sample.unity3d", names)
                self.assertIn("Star_Manager_依赖清单.json", names)

    def test_filters_portable_dependencies_by_selected_types(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            output_dir = root / "exports"
            source = game / "UserData" / "chara" / "female" / "card.png"
            source.parent.mkdir(parents=True)
            output_dir.mkdir()
            source.write_bytes(b"character-card")
            dependencies = [
                {"mod_id": "face.guid", "property": "ChaFileFace.EyebrowId", "zipmod": {"id": 7, "guid": "face.guid"}},
                {"mod_id": "clothes.guid", "category_no": "240", "zipmod": {"id": 8, "guid": "clothes.guid"}},
                {"mod_id": "hair.missing", "category_no": "300", "zipmod": None},
                {"mod_id": "other.missing", "category_no": "348", "zipmod": None},
            ]

            def fake_export(ids, _target_dir, mode, layout, **_kwargs):
                self.assertEqual(list(ids), [7])
                self.assertEqual((mode, layout), ("copy", "portable"))
                return {
                    "ok": True,
                    "exported_count": 1,
                    "exported_unity3d_count": 0,
                    "failure_count": 0,
                    "failures": [],
                }

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.resolve_card_dependencies", return_value=dependencies
            ), patch(
                "star_manager.services.card_library.export_zipmods", side_effect=fake_export
            ):
                result = export_character_dependency_package(
                    str(game),
                    "female/card.png",
                    str(output_dir),
                    False,
                    ["face", "hair"],
                )

            manifest = json.loads((Path(result["target_path"]) / "Star_Manager_依赖清单.json").read_text(encoding="utf-8"))
            self.assertTrue(result["ok"])
            self.assertEqual(result["selected_dependency_types"], ["face", "hair"])
            self.assertEqual(result["dependency_count"], 2)
            self.assertEqual(result["total_dependency_count"], 4)
            self.assertEqual(result["missing_mod_ids"], ["hair.missing"])
            self.assertEqual(manifest["excluded_dependency_record_count"], 2)
            self.assertEqual(manifest["unclassified_dependency_record_count"], 1)

    def test_exports_uncompressed_portable_dependency_package(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            output_dir = root / "exports"
            source = game / "UserData" / "chara" / "male" / "hero.png"
            source.parent.mkdir(parents=True)
            output_dir.mkdir()
            source.write_bytes(b"character-card")

            with patch("star_manager.services.card_library.is_hs2_game_dir", return_value=True), patch(
                "star_manager.services.card_library.is_ais_card", return_value=True
            ), patch(
                "star_manager.services.card_library.resolve_card_dependencies", return_value=[]
            ):
                result = export_character_dependency_package(
                    str(game), "male/hero.png", str(output_dir), False
                )

            target = Path(result["target_path"])
            self.assertTrue(result["ok"])
            self.assertFalse(result["compressed"])
            self.assertEqual((target / "UserData" / "chara" / "male" / "hero.png").read_bytes(), b"character-card")
            self.assertTrue((target / "Star_Manager_依赖清单.json").is_file())


if __name__ == "__main__":
    unittest.main()
