import tempfile
import unittest
import struct
import zlib
from pathlib import Path

from star_manager.core.card_metadata import (
    CARD_METADATA_PLUGIN_ID,
    CardMetadataError,
    read_card_metadata,
    read_card_favorite,
    read_card_rating,
    read_card_tags,
    set_card_favorite_file,
    set_card_rating_file,
    set_card_tags_file,
)
from star_manager.core.card_parser import extract_png_extra_data, get_card_block, unpack_msgpack
from star_manager.core.coordinate_card import pack_dotnet_string, pack_msgpack


MINIMAL_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00IEND\xaeB`\x82"


def build_character_card(plugins=None, include_kkex=True):
    blocks = []
    if include_kkex:
        blocks.append(("KKEx", "3", pack_msgpack(plugins or {})))
    blocks.append(("Parameter", "0.0.1", pack_msgpack({"fullname": "Test"})))
    block_infos = []
    block_data = b""
    for name, version, blob in blocks:
        block_infos.append(
            {"name": name, "version": version, "pos": len(block_data), "size": len(blob)}
        )
        block_data += blob
    table = pack_msgpack({"lstInfo": block_infos})
    payload = b"".join(
        (
            (100).to_bytes(4, "little"),
            pack_dotnet_string("\u3010AIS_Chara\u3011"),
            pack_dotnet_string("1.0.0"),
            (0).to_bytes(4, "little"),
            pack_dotnet_string("card-id"),
            pack_dotnet_string("user-id"),
            len(table).to_bytes(4, "little"),
            table,
            len(block_data).to_bytes(8, "little"),
            block_data,
        )
    )
    return MINIMAL_PNG + payload


def read_plugins(path: Path):
    block = get_card_block(extract_png_extra_data(path), "KKEx")
    assert block is not None
    plugins, end = unpack_msgpack(block[1])
    assert end == len(block[1])
    return plugins


def add_obsolete_smfr_chunk(card: bytes) -> bytes:
    chunk_type = b"smFr"
    payload = b"\x01"
    checksum = zlib.crc32(payload, zlib.crc32(chunk_type)) & 0xFFFFFFFF
    chunk = struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", checksum)
    iend_start = card.index(b"IEND") - 4
    return card[:iend_start] + chunk + card[iend_start:]


class CardMetadataTests(unittest.TestCase):
    def test_reads_all_listing_metadata_in_one_result(self):
        metadata = [1, {"favorite": True, "rating": 3, "tags": ["古装", "红发"]}]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card({CARD_METADATA_PLUGIN_ID: metadata}))

            self.assertEqual(
                read_card_metadata(path),
                {"favorite": True, "rating": 3, "tags": ["古装", "红发"]},
            )

    def test_favorite_round_trip_uses_kkex_and_preserves_other_data(self):
        original_plugins = {"another.plugin": [2, {"value": b"keep-me"}]}
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card(original_plugins))

            set_card_favorite_file(path, True)
            self.assertTrue(read_card_favorite(path))
            plugins = read_plugins(path)
            self.assertEqual(plugins["another.plugin"], original_plugins["another.plugin"])
            self.assertEqual(plugins[CARD_METADATA_PLUGIN_ID], [1, {"favorite": True}])

            set_card_favorite_file(path, False)
            self.assertFalse(read_card_favorite(path))
            plugins = read_plugins(path)
            self.assertNotIn(CARD_METADATA_PLUGIN_ID, plugins)
            self.assertEqual(plugins["another.plugin"], original_plugins["another.plugin"])

    def test_preserves_future_star_manager_fields_when_toggling(self):
        metadata = [1, {"favorite": True, "cardId": "abc", "tags": ["one"]}]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card({CARD_METADATA_PLUGIN_ID: metadata}))

            set_card_favorite_file(path, False)

            self.assertFalse(read_card_favorite(path))
            self.assertEqual(
                read_plugins(path)[CARD_METADATA_PLUGIN_ID],
                [1, {"cardId": "abc", "tags": ["one"]}],
            )

    def test_rating_round_trip_preserves_favorite_and_future_fields(self):
        metadata = [1, {"favorite": True, "cardId": "abc", "tags": ["one"]}]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card({CARD_METADATA_PLUGIN_ID: metadata}))

            set_card_rating_file(path, 4)

            self.assertEqual(read_card_rating(path), 4)
            self.assertTrue(read_card_favorite(path))
            self.assertEqual(
                read_plugins(path)[CARD_METADATA_PLUGIN_ID],
                [1, {"favorite": True, "cardId": "abc", "tags": ["one"], "rating": 4}],
            )

            set_card_rating_file(path, 2)
            self.assertEqual(read_card_rating(path), 2)

    def test_rating_must_be_an_integer_from_one_to_five(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card())
            original = path.read_bytes()

            for invalid in (0, 6, True, 2.5):
                with self.subTest(rating=invalid):
                    with self.assertRaises(CardMetadataError):
                        set_card_rating_file(path, invalid)
                    self.assertEqual(path.read_bytes(), original)

    def test_tags_round_trip_preserves_rating_favorite_and_unknown_fields(self):
        metadata = [1, {"favorite": True, "rating": 5, "notes": "keep"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card({CARD_METADATA_PLUGIN_ID: metadata}))

            set_card_tags_file(path, ["粉发", "礼服", "粉发"])

            self.assertEqual(read_card_tags(path), ["粉发", "礼服"])
            self.assertTrue(read_card_favorite(path))
            self.assertEqual(read_card_rating(path), 5)
            self.assertEqual(
                read_plugins(path)[CARD_METADATA_PLUGIN_ID],
                [1, {"favorite": True, "rating": 5, "notes": "keep", "tags": ["粉发", "礼服"]}],
            )

            set_card_tags_file(path, [])
            self.assertEqual(read_card_tags(path), [])
            self.assertEqual(
                read_plugins(path)[CARD_METADATA_PLUGIN_ID],
                [1, {"favorite": True, "rating": 5, "notes": "keep"}],
            )

    def test_tags_validate_length_and_count_before_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card())
            original = path.read_bytes()

            for invalid in ([""], ["x" * 25], [str(index) for index in range(13)], [1]):
                with self.subTest(tags=invalid):
                    with self.assertRaises(CardMetadataError):
                        set_card_tags_file(path, invalid)
                    self.assertEqual(path.read_bytes(), original)

    def test_adds_kkex_block_when_card_does_not_have_one(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(build_character_card(include_kkex=False))

            set_card_favorite_file(path, True)

            self.assertTrue(read_card_favorite(path))
            self.assertEqual(read_plugins(path)[CARD_METADATA_PLUGIN_ID], [1, {"favorite": True}])

    def test_obsolete_png_marker_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "card.png"
            path.write_bytes(add_obsolete_smfr_chunk(build_character_card()))

            self.assertFalse(read_card_favorite(path))

if __name__ == "__main__":
    unittest.main()
