import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402


class CardDependencyRefreshTaskTests(unittest.TestCase):
    def test_cancel_control_marks_remote_download_for_cancellation(self):
        store = bridge.TaskStore()
        task = bridge.TaskState(id="task", task_type="download_card_missing_mods", status="running")
        store._tasks[task.id] = task

        controlled = store.control_task(task.id, "cancel")

        self.assertIs(controlled, task)
        self.assertTrue(task.cancel_requested)
        self.assertFalse(task.pause_requested)
        self.assertEqual(task.phase_message, "正在取消下载")

    def test_cancelled_remote_download_becomes_terminal_task_state(self):
        task = bridge.TaskState(id="task", task_type="download_card_missing_mods")

        with patch.object(
            bridge,
            "download_card_missing_mods",
            side_effect=bridge.RemoteDownloadCancelled("Download cancelled by user."),
        ):
            bridge.run_task(task, {"game_dir": "D:/HS2", "remote_ids": [7]})

        self.assertEqual(task.status, "cancelled")
        self.assertEqual(task.phase, "cancelled")
        self.assertEqual(task.error, "下载已取消")
        self.assertEqual(task.download_speed_bps, 0)

    def test_remote_completion_rebuilds_cards_using_affected_mod_guids(self):
        task = bridge.TaskState(id="task", task_type="download_card_missing_mods")
        download_result = {
            "ok": True,
            "message": "完成",
            "affected_mod_guids": ["Example.Guid"],
        }
        card_stats = {"relinked_cards": 1, "missing_dependencies": 0}

        with (
            patch.object(bridge, "download_card_missing_mods", return_value=download_result) as download,
            patch.object(bridge, "build_card_database", return_value=card_stats) as build_cards,
            patch.object(bridge, "is_hs2_game_dir", return_value=True),
        ):
            bridge.run_task(
                task,
                {
                    "game_dir": "D:/HS2",
                    "db_path": "D:/runtime/cards.sqlite",
                    "thumbnail_dir": "D:/runtime/thumbnails",
                    "preview_dir": "D:/runtime/previews",
                    "remote_ids": [7],
                },
            )

        self.assertEqual(task.status, "completed")
        self.assertEqual(task.data["card_stats"], card_stats)
        self.assertEqual(download.call_args.kwargs["db_path"], Path("D:/runtime/cards.sqlite"))
        self.assertEqual(build_cards.call_args.kwargs["affected_mod_guids"], ["Example.Guid"])
        self.assertEqual(build_cards.call_args.kwargs["mode"], "incremental")


if __name__ == "__main__":
    unittest.main()
