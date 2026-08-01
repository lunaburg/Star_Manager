import tempfile
import unittest
from pathlib import Path

from star_manager.core.card_parser import extract_character_profile_from_card_data
from star_manager.core.card_metadata import read_card_favorite, set_card_favorite_file
from star_manager.core.character_profile import (
    CharacterProfileUpdateError,
    replace_character_card_cover_file,
    replace_profile_block,
    update_character_profile_file,
    validate_profile_updates,
)
from star_manager.core.coordinate_card import find_png_end, pack_dotnet_string, pack_msgpack, png_dimensions


def build_character_card(parameter, parameter2=None):
    blocks = [("Parameter", "0.0.1", pack_msgpack(parameter))]
    if parameter2 is not None:
        blocks.append(("Parameter2", "0.0.0", pack_msgpack(parameter2)))
    block_infos = []
    position = 0
    block_data = b""
    for name, version, blob in blocks:
        block_infos.append({"name": name, "version": version, "pos": position, "size": len(blob)})
        block_data += blob
        position += len(blob)
    table = pack_msgpack({"lstInfo": block_infos})
    header = b"".join([
        b"\x00\x00\x00\x00",
        (100).to_bytes(4, "little"),
        pack_dotnet_string("【AIS_Chara】"),
        pack_dotnet_string("1.0.0"),
        (0).to_bytes(4, "little"),
        pack_dotnet_string("card-id"),
        pack_dotnet_string("user-id"),
        len(table).to_bytes(4, "little"),
    ])
    return header + table + len(block_data).to_bytes(8, "little") + block_data


class CharacterProfileUpdateTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "version": "0.0.1", "sex": 1, "fullname": "Original", "personality": 5,
            "birthMonth": 4, "birthDay": 10, "voiceRate": 0.5,
            "hsWish": [2, 5, 11], "futanari": False,
        }
        self.updates = {
            "fullname": "新的名字", "personality": 13, "birthMonth": 2,
            "birthDay": 29, "voiceRate": 0.75, "futanari": True,
        }

    def test_rewrites_parameter_and_preserves_unedited_values(self):
        data = build_character_card(self.profile, {"personality": 5, "other": 9})
        updated = replace_profile_block(data, "Parameter", self.updates)
        updated = replace_profile_block(updated, "Parameter2", {"personality": 13})
        profile = extract_character_profile_from_card_data(updated)
        self.assertEqual(profile["fullname"], "新的名字")
        self.assertEqual(profile["personality"], 13)
        self.assertEqual(profile["sex"], 1)
        self.assertEqual(profile["hsWish"], [2, 5, 11])
        self.assertAlmostEqual(profile["voiceRate"], 0.75)

    def test_updates_file_atomically_and_preserves_png_prefix(self):
        card_data = build_character_card(self.profile)
        png_prefix = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00IENDabcd"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(png_prefix + card_data[4:])
            profile = update_character_profile_file(path, self.updates)
            self.assertEqual(path.read_bytes()[: len(png_prefix)], png_prefix)
            self.assertEqual(profile["fullname"], "新的名字")

    def test_validates_birthday_and_rejects_sex_change(self):
        with self.assertRaises(CharacterProfileUpdateError):
            validate_profile_updates(dict(self.updates, birthMonth=2, birthDay=30))
        with self.assertRaises(CharacterProfileUpdateError):
            validate_profile_updates(dict(self.updates, sex=0))

    def test_replaces_cover_and_preserves_appended_character_data(self):
        from PIL import Image

        card_data = build_character_card(self.profile)
        png_prefix = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00IENDabcd"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            card_path = root / "card.png"
            image_path = root / "cover.png"
            card_path.write_bytes(png_prefix + card_data[4:])
            set_card_favorite_file(card_path, True)
            Image.new("RGB", (400, 200), (220, 40, 70)).save(image_path)
            before = card_path.read_bytes()
            before_payload = before[find_png_end(before):]

            report = replace_character_card_cover_file(card_path, image_path)

            after = card_path.read_bytes()
            after_png_end = find_png_end(after)
            self.assertEqual(png_dimensions(after[:after_png_end]), (143, 200))
            self.assertEqual(after[after_png_end:], before_payload)
            self.assertEqual((report["width"], report["height"]), (143, 200))
            self.assertTrue(read_card_favorite(card_path))
            self.assertEqual(extract_character_profile_from_card_data(after[after_png_end - 4:])["fullname"], "Original")

    def test_replaces_cover_with_selected_native_resolution_crop(self):
        from PIL import Image

        card_data = build_character_card(self.profile)
        png_prefix = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00IENDabcd"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            card_path = root / "card.png"
            image_path = root / "large-cover.png"
            card_path.write_bytes(png_prefix + card_data[4:])
            Image.new("RGB", (1600, 1584), (32, 80, 140)).save(image_path)

            report = replace_character_card_cover_file(
                card_path,
                image_path,
                {"left": 0.1, "top": 0.0, "width": 1134 / 1600, "height": 1.0},
            )

            after = card_path.read_bytes()
            after_png_end = find_png_end(after)
            self.assertEqual(png_dimensions(after[:after_png_end]), (1134, 1584))
            self.assertEqual((report["width"], report["height"]), (1134, 1584))


if __name__ == "__main__":
    unittest.main()
