import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402


class BuildModDatabaseTimingTests(unittest.TestCase):
    def test_database_progress_uses_reference_timing_weights(self):
        self.assertAlmostEqual(
            bridge.weighted_mod_database_progress(5),
            2.5 / 613 * 100,
            places=6,
        )
        self.assertAlmostEqual(
            bridge.weighted_mod_database_progress(12),
            (2.5 + 70.6) / 613 * 100,
            places=6,
        )
        self.assertAlmostEqual(
            bridge.weighted_mod_database_progress(15),
            (2.5 + 70.6) / 613 * 100,
            places=6,
        )
        self.assertAlmostEqual(
            bridge.weighted_mod_database_progress(70),
            (2.5 + 70.6 + 472.9) / 613 * 100,
            places=6,
        )
        self.assertAlmostEqual(
            bridge.weighted_mod_database_progress(100),
            (2.5 + 70.6 + 472.9 + 1.1) / 613 * 100,
            places=6,
        )
        self.assertAlmostEqual(
            bridge.weighted_character_card_database_progress(100),
            100,
            places=6,
        )

    def test_build_task_returns_phase_timings_and_finished_at(self):
        task = bridge.TaskState(id="task", task_type="build_mod_database")
        mod_stats = {
            "primary_zipmods": 2,
            "mod_items": 14,
            "timings": {
                "builtin_resource_index_ms": 11.1,
                "zipmod_scan_ms": 22.2,
                "item_parse_ms": 33.3,
                "database_write_ms": 44.4,
            },
        }
        card_stats = {
            "cards": 3,
            "dependencies": 9,
            "missing_dependencies": 1,
            "timings": {"card_database_total_ms": 55.5},
        }

        with (
            patch.object(bridge, "is_hs2_game_dir", return_value=True),
            patch.object(bridge, "build_database", return_value=mod_stats),
            patch.object(bridge, "build_card_database", return_value=card_stats),
        ):
            bridge.run_task(task, {"game_dir": "D:/HS2", "mode": "incremental"})

        self.assertEqual(task.status, "completed")
        self.assertGreater(task.finished_at, 0)
        timings = task.data["timings"]
        self.assertEqual(timings["builtin_resource_index_ms"], 11.1)
        self.assertEqual(timings["zipmod_scan_ms"], 22.2)
        self.assertEqual(timings["item_parse_ms"], 33.3)
        self.assertEqual(timings["database_write_ms"], 44.4)
        self.assertEqual(timings["character_card_database_ms"], 55.5)
        self.assertGreaterEqual(timings["total_ms"], 0)
        self.assertTrue(any("数据库耗时汇总" in message for message in task.messages))

    def test_build_task_maps_progress_callbacks_to_weighted_total(self):
        task = bridge.TaskState(id="task", task_type="build_mod_database")
        progress_events = []

        def fake_build_database(*args, **_kwargs):
            progress_callback = args[3]
            progress_callback(70, "item parsing")
            return {"timings": {}}

        def fake_build_card_database(*args, **_kwargs):
            progress_callback = args[3]
            progress_callback(100, "cards done")
            return {"timings": {"card_database_total_ms": 1.0}}

        task_reporter = bridge.build_reporter(task)
        task_reporter.on_progress = lambda value: progress_events.append(value)
        with (
            patch.object(bridge, "is_hs2_game_dir", return_value=True),
            patch.object(bridge, "build_database", side_effect=fake_build_database),
            patch.object(bridge, "build_card_database", side_effect=fake_build_card_database),
            patch.object(bridge, "build_reporter", return_value=task_reporter),
        ):
            bridge.run_task(task, {"game_dir": "D:/HS2", "mode": "incremental"})

        self.assertEqual(task.status, "completed")
        self.assertIn(
            bridge.weighted_mod_database_progress(70),
            progress_events,
        )
        self.assertIn(
            bridge.weighted_character_card_database_progress(100),
            progress_events,
        )
        self.assertEqual(task.progress, 100)

    def test_build_task_forwards_configured_worker_count(self):
        task = bridge.TaskState(id="task", task_type="build_mod_database")
        forwarded = []
        card_forwarded = []

        def fake_build_database(*_args, **kwargs):
            forwarded.append(kwargs.get("worker_count"))
            return {"timings": {}, "worker_count": 8, "worker_limit": 8}

        def fake_build_card_database(*_args, **kwargs):
            card_forwarded.append(kwargs.get("worker_count"))
            return {"timings": {}}

        with (
            patch.object(bridge, "is_hs2_game_dir", return_value=True),
            patch.object(bridge, "build_database", side_effect=fake_build_database),
            patch.object(bridge, "build_card_database", side_effect=fake_build_card_database),
        ):
            bridge.run_task(task, {"game_dir": "D:/HS2", "mode": "incremental", "worker_count": 8})

        self.assertEqual(task.status, "completed")
        self.assertEqual(forwarded, [8])
        self.assertEqual(card_forwarded, [8])


if __name__ == "__main__":
    unittest.main()
