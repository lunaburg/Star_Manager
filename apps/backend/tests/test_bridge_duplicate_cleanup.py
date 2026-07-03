import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bridge import choose_safe_duplicate_cleanup_action  # noqa: E402


class BulkDuplicateCleanupActionTests(unittest.TestCase):
    def test_recommended_duplicate_keep_promotes_primary(self):
        analysis = {
            "recommendation": {
                "keep": {"role": "duplicate", "duplicate_id": 42},
                "primary_should_delete": True,
            },
            "candidates": [
                {
                    "role": "primary",
                    "exists": True,
                    "recommended_action": "delete",
                    "unique_item_count": 0,
                },
                {
                    "role": "duplicate",
                    "duplicate_id": 42,
                    "exists": True,
                    "recommended_action": "keep",
                    "unique_item_count": 0,
                    "recommendation_reasons": ["most_complete"],
                },
                {
                    "role": "duplicate",
                    "duplicate_id": 99,
                    "exists": True,
                    "recommended_action": "delete",
                    "unique_item_count": 0,
                },
            ],
        }

        action, cleanup_ids, promote_duplicate_id, reason = choose_safe_duplicate_cleanup_action(analysis)

        self.assertEqual(action, "promote")
        self.assertEqual(cleanup_ids, [99])
        self.assertEqual(promote_duplicate_id, 42)
        self.assertEqual(reason, "")

    def test_primary_with_unique_items_is_not_promoted(self):
        analysis = {
            "recommendation": {
                "keep": {"role": "duplicate", "duplicate_id": 42},
                "primary_should_delete": True,
            },
            "candidates": [
                {
                    "role": "primary",
                    "exists": True,
                    "recommended_action": "delete",
                    "unique_item_count": 1,
                },
                {
                    "role": "duplicate",
                    "duplicate_id": 42,
                    "exists": True,
                    "recommended_action": "keep",
                    "recommendation_reasons": ["most_complete"],
                },
            ],
        }

        action, cleanup_ids, promote_duplicate_id, reason = choose_safe_duplicate_cleanup_action(analysis)

        self.assertEqual(action, "skip")
        self.assertEqual(cleanup_ids, [])
        self.assertIsNone(promote_duplicate_id)
        self.assertIn("unique item", reason)


if __name__ == "__main__":
    unittest.main()
