import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.remote_character_page import (  # noqa: E402
    RemoteCharacterPageError,
    _parse_search_response,
    fetch_character_page,
)


class _FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self.body


def _search_body(card_id=7, hit_count=49):
    return json.dumps({
        "type": "success",
        "data": {
            "searchHitCount": hit_count,
            "cards": [{
                "cardType": "AI",
                "id": card_id,
                "cardData": {"name": "Sample", "gender": "Female"},
                "fileSize": 12,
                "downloadCount": 3,
                "votes": 1,
                "tags": [],
                "dateCreatedUtc": "2026-10-02T10:13:29",
            }],
        },
    }).encode("utf-8")


def _scene_search_body(card_id=26710, hit_count=10000):
    return json.dumps({
        "type": "success",
        "data": {
            "searchHitCount": hit_count,
            "cards": [{
                "cardType": "AISCENE",
                "id": card_id,
                "customName": "Sample Scene",
                "cardData": {"maleCount": 2, "femaleCount": 3, "objectCount": 42},
                "uploader": {"username": "Scene Author"},
                "fileSize": 17987222,
                "downloadCount": 126,
                "votes": 0,
                "tags": [],
                "dateCreatedUtc": "2026-09-30T11:23:39",
            }],
        },
    }).encode("utf-8")


class RemoteCharacterPageTests(unittest.TestCase):
    def test_search_response_builds_same_host_card_urls_and_page_count(self):
        cards, page_count = _parse_search_response(_search_body())

        self.assertEqual(page_count, 3)
        self.assertEqual(cards[0]["id"], 7)
        self.assertEqual(cards[0]["name"], "Sample")
        self.assertEqual(cards[0]["cover_url"], "https://db.bepis.moe/card/thumb/AI_000007_thumb.webp")
        self.assertEqual(cards[0]["detail_url"], "https://db.bepis.moe/aishoujo/view/7")
        self.assertEqual(cards[0]["uploader"], "Anonymous")
        self.assertEqual(cards[0]["date_created_utc"], "2026-10-02T10:13:29")

    def test_fetch_uses_json_api_and_caches_metadata_without_downloading_covers(self):
        calls = []

        def open_remote(url, timeout=30.0):
            calls.append((url, timeout))
            return _FakeResponse(_search_body())

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "star_manager.services.remote_character_page.REMOTE_CHARACTER_PAGE_CACHE_ROOT",
            Path(temp_dir),
        ), patch("star_manager.services.remote_character_page._open_remote", side_effect=open_remote):
            first = fetch_character_page("https://db.bepis.moe/aishoujo?page=2")
            cached = fetch_character_page("https://db.bepis.moe/aishoujo?page=2")

            self.assertFalse(first["cached"])
            self.assertTrue(cached["cached"])
            self.assertEqual(first["page_count"], 3)
            self.assertEqual(calls, [("https://db.bepis.moe/api/frontend/search?cardType=AI&page=2", 12.0)])
            cache_dir = next(Path(temp_dir).iterdir())
            self.assertEqual(sorted(path.name for path in cache_dir.iterdir()), ["manifest.json"])

    def test_scene_page_builds_landscape_card_metadata_and_separate_cache(self):
        calls = []

        def open_remote(url, timeout=30.0):
            calls.append((url, timeout))
            return _FakeResponse(_scene_search_body())

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "star_manager.services.remote_character_page.REMOTE_CHARACTER_PAGE_CACHE_ROOT",
            Path(temp_dir),
        ), patch("star_manager.services.remote_character_page._open_remote", side_effect=open_remote):
            first = fetch_character_page("https://db.bepis.moe/aiscenes?page=2")
            cached = fetch_character_page("https://db.bepis.moe/aiscenes?page=2")

        card = first["cards"][0]
        self.assertFalse(first["cached"])
        self.assertTrue(cached["cached"])
        self.assertEqual(first["page_count"], 417)
        self.assertEqual(card["card_type"], "AISCENE")
        self.assertEqual(card["name"], "Sample Scene")
        self.assertEqual(card["uploader"], "Scene Author")
        self.assertEqual((card["male_count"], card["female_count"], card["object_count"]), (2, 3, 42))
        self.assertEqual(card["cover_url"], "https://db.bepis.moe/card/thumb/AISCENE_026710_thumb.webp")
        self.assertEqual(card["detail_url"], "https://db.bepis.moe/aiscenes/view/26710")
        self.assertEqual(calls, [("https://db.bepis.moe/api/frontend/search?cardType=AISCENE&page=2", 12.0)])

    def test_invalid_api_data_raises_for_browser_fallback(self):
        with self.assertRaises(RemoteCharacterPageError):
            _parse_search_response(b"<html>not json</html>")
        with self.assertRaises(RemoteCharacterPageError):
            _parse_search_response(_scene_search_body())
        with self.assertRaises(RemoteCharacterPageError):
            _parse_search_response(_search_body(), "AISCENE")
        with self.assertRaises(RemoteCharacterPageError):
            _parse_search_response(json.dumps({"type": "success", "data": {"cards": []}}).encode())
        with self.assertRaises(RemoteCharacterPageError):
            _parse_search_response(json.dumps({
                "type": "success",
                "data": {"searchHitCount": 1, "cards": [{"cardType": "OTHER", "id": 7, "cardData": {}, "tags": []}]},
            }).encode())

    def test_rejects_unsupported_pages_and_query_parameters(self):
        for url in (
            "https://example.com/aishoujo?page=2",
            "https://db.bepis.moe/aishoujo/view/7",
            "https://db.bepis.moe/aishoujo?page=0",
            "https://db.bepis.moe/aishoujo?page=2&page=3",
            "https://db.bepis.moe/aishoujo?url=https://example.com",
            "https://db.bepis.moe/aiscenes/view/7",
            "https://db.bepis.moe/aiscenes?page=0",
            "https://db.bepis.moe:abc/aishoujo?page=2",
        ):
            with self.subTest(url=url), self.assertRaises(RemoteCharacterPageError):
                fetch_character_page(url)


if __name__ == "__main__":
    unittest.main()
