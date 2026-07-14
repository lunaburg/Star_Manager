import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from star_manager.services.card_library import set_character_card_as_navi


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


if __name__ == "__main__":
    unittest.main()
