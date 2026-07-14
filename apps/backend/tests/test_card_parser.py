from unittest.mock import patch

from star_manager.core import card_parser


def test_profile_prefers_parameter2_personality():
    blocks = {
        "Parameter": (
            {"name": "Parameter", "version": "0.0.1", "pos": 10, "size": 20},
            b"parameter",
        ),
        "Parameter2": (
            {"name": "Parameter2", "version": "0.0.0", "pos": 30, "size": 10},
            b"parameter2",
        ),
    }
    profiles = {
        b"parameter": {"fullname": "Test", "personality": 5},
        b"parameter2": {"personality": 13},
    }

    with (
        patch.object(card_parser, "extract_png_extra_data", return_value=b"card"),
        patch.object(card_parser, "read_card_marker", return_value="【AIS_Chara】"),
        patch.object(card_parser, "get_card_block", side_effect=lambda _, name: blocks.get(name)),
        patch.object(card_parser, "parse_partial_profile_map", side_effect=lambda blob: profiles[blob]),
    ):
        profile = card_parser.extract_character_profile_from_card("test.png")

    assert profile["personality"] == 13
    assert profile["_block"]["name"] == "Parameter"


def test_profile_falls_back_to_parameter_personality():
    parameter = (
        {"name": "Parameter", "version": "0.0.1", "pos": 10, "size": 20},
        b"parameter",
    )

    with (
        patch.object(card_parser, "extract_png_extra_data", return_value=b"card"),
        patch.object(card_parser, "read_card_marker", return_value="【AIS_Chara】"),
        patch.object(
            card_parser,
            "get_card_block",
            side_effect=lambda _, name: parameter if name == "Parameter" else None,
        ),
        patch.object(
            card_parser,
            "parse_partial_profile_map",
            return_value={"fullname": "Test", "personality": 5},
        ),
    ):
        profile = card_parser.extract_character_profile_from_card("test.png")

    assert profile["personality"] == 5
