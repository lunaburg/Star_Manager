import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402


class BulkAddCharacterCardTagsTaskTests(unittest.TestCase):
    def test_bulk_task_adds_tags_to_each_card_without_replacing_existing_tags(self):
        task = bridge.TaskState(id="task", task_type="bulk_add_character_card_tags")

        def fake_add(_game_dir, relative_path, tags, **_kwargs):
            existing = ["原有"] if relative_path == "female/a.png" else ["另一标签"]
            return {
                "ok": True,
                "relative_path": relative_path,
                "tags": [*existing, *tags],
                "modified_at": 1,
            }

        with patch.object(bridge, "add_character_card_tags", side_effect=fake_add) as add_tags:
            bridge.run_task(
                task,
                {
                    "game_dir": "D:/HS2",
                    "card_paths": ["female/a.png", "female/b.png"],
                    "tags": ["批量新增"],
                },
            )

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.data["updated_count"], 2)
        self.assertEqual(task.data["failure_count"], 0)
        self.assertEqual(task.data["updated"][0]["tags"], ["原有", "批量新增"])
        self.assertEqual(task.data["updated"][1]["tags"], ["另一标签", "批量新增"])
        self.assertEqual(
            add_tags.call_args_list,
            [
                call(
                    "D:/HS2",
                    "female/a.png",
                    ["批量新增"],
                    db_path=bridge.DEFAULT_DB_PATH,
                    preview_dir=bridge.DEFAULT_CARD_PREVIEW_DIR,
                ),
                call(
                    "D:/HS2",
                    "female/b.png",
                    ["批量新增"],
                    db_path=bridge.DEFAULT_DB_PATH,
                    preview_dir=bridge.DEFAULT_CARD_PREVIEW_DIR,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
