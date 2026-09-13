import io
import sqlite3
import sys
import threading
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services import remote_mod_completion as completion  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._stream = io.BytesIO(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size=-1):
        return self._stream.read(size)

    def close(self):
        self._stream.close()


def _remote_db(path: Path, rows: list[tuple]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE remote_zipmods (
                id INTEGER PRIMARY KEY,
                source_url TEXT NOT NULL,
                download_url TEXT NOT NULL,
                relative_path TEXT NOT NULL DEFAULT '',
                file_name TEXT NOT NULL DEFAULT '',
                guid TEXT NOT NULL DEFAULT '',
                guid_norm TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                version TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                file_size INTEGER,
                manifest_status TEXT NOT NULL DEFAULT '',
                present INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO remote_zipmods (
                id, source_url, download_url, relative_path, file_name,
                guid, guid_norm, name, version, author, file_size,
                manifest_status, present
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
    finally:
        connection.close()


class RemoteModCompletionTests(unittest.TestCase):
    def test_batch_downloads_run_concurrently_before_single_file_indexing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "HS2"
            (game_dir / "mods").mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").write_bytes(b"")
            remote_db = root / "remote.sqlite"
            source = "https://sideload.betterrepack.com/download/AISHS2/"
            rows = [
                (
                    index,
                    source,
                    f"{source}{index}.zipmod",
                    f"{index}.zipmod",
                    f"{index}.zipmod",
                    f"sample.guid.{index}",
                    f"sample.guid.{index}",
                    f"Sample {index}",
                    "1",
                    "Author",
                    10,
                    "ok",
                    1,
                )
                for index in range(1, 4)
            ]
            _remote_db(remote_db, rows)
            thread_ids = set()
            barrier = threading.Barrier(3)
            progress_events = []

            def fake_download(candidate, game_root, progress_callback=None, control_callback=None, target_lock=None):
                thread_ids.add(threading.get_ident())
                barrier.wait(timeout=5)
                target = Path(game_root) / "mods" / "Remote" / candidate["file_name"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"zipmod")
                return {
                    **candidate,
                    "status": "downloaded",
                    "target_path": str(target),
                    "downloaded_size": 6,
                }

            with (
                patch.object(completion, "DEFAULT_REMOTE_INDEX_PATH", remote_db),
                patch.object(completion, "_download_candidate", side_effect=fake_download),
                patch.object(completion, "index_single_zipmod", return_value={"guid": "indexed"}) as index,
            ):
                result = completion.download_card_missing_mods(
                    str(game_dir), [1, 2, 3],
                    progress_callback=lambda _value, _message, details: progress_events.append(details),
                    db_path=root / "local.sqlite", thumbnail_dir=root / "thumbnails",
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["completed_count"], 3)
            self.assertEqual(index.call_count, 3)
            self.assertEqual(len(thread_ids), 3)
            phases = [event["phase"] for event in progress_events]
            self.assertIn("download", phases)
            self.assertIn("install", phases)
            self.assertLess(max(i for i, phase in enumerate(phases) if phase == "download"), min(i for i, phase in enumerate(phases) if phase == "install"))
            self.assertTrue(all("download_speed_bps" in event for event in progress_events))

    def test_safe_relative_path_discards_traversal_and_invalid_windows_names(self):
        path = completion._safe_relative_path(
            r"../Author/CON:bad/../../mod?.zipmod",
            "mod?.zipmod",
        )

        self.assertEqual(path.parts, ("Author", "CON_bad", "mod_.zipmod"))
        self.assertNotIn("..", path.parts)

    def test_resolve_candidates_rejects_two_versions_of_same_guid(self):
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "remote.sqlite"
            source = "https://sideload.betterrepack.com/download/AISHS2/"
            row = (
                1, source, source + "a.zipmod", "a.zipmod", "a.zipmod",
                "sample.guid", "sample.guid", "Sample", "1", "Author", 10, "ok", 1,
            )
            _remote_db(db_path, [row, (2, *row[1:])])
            connection = completion._remote_index_connection(db_path)
            try:
                with self.assertRaisesRegex(ValueError, "one remote version"):
                    completion._resolve_candidates(connection, [1, 2])
            finally:
                connection.close()

    def test_download_verifies_manifest_and_removes_partial_file_on_failure(self):
        with TemporaryDirectory() as temp_dir:
            game_dir = Path(temp_dir) / "HS2"
            (game_dir / "mods").mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").write_bytes(b"")
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, "w") as archive:
                archive.writestr(
                    "manifest.xml",
                    "<manifest><guid>actual.guid</guid><name>Sample</name></manifest>",
                )
            candidate = {
                "guid_norm": "selected.guid",
                "download_url": "https://sideload.betterrepack.com/download/AISHS2/sample.zipmod",
                "source_url": "https://sideload.betterrepack.com/download/AISHS2/",
                "relative_path": "Author/sample.zipmod",
                "file_name": "sample.zipmod",
            }

            with patch.object(completion, "_open_remote", return_value=_FakeResponse(payload.getvalue())):
                with self.assertRaisesRegex(RuntimeError, "manifest GUID"):
                    completion._download_candidate(candidate, game_dir)

            target = game_dir / "mods" / "Remote" / "Author" / "sample.zipmod"
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_cancelled_download_removes_partial_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "HS2"
            (game_dir / "mods").mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").write_bytes(b"")
            candidate = {
                "guid_norm": "selected.guid",
                "download_url": "https://sideload.betterrepack.com/download/AISHS2/sample.zipmod",
                "source_url": "https://sideload.betterrepack.com/download/AISHS2/",
                "relative_path": "Author/sample.zipmod",
                "file_name": "sample.zipmod",
            }
            callback_count = 0

            def cancel_after_download_starts():
                nonlocal callback_count
                callback_count += 1
                if callback_count >= 2:
                    raise completion.RemoteDownloadCancelled("Download cancelled by user.")

            with patch.object(completion, "_open_remote", return_value=_FakeResponse(b"partial")):
                with self.assertRaises(completion.RemoteDownloadCancelled):
                    completion._download_candidate(
                        candidate,
                        game_dir,
                        control_callback=cancel_after_download_starts,
                    )

            target = game_dir / "mods" / "Remote" / "Author" / "sample.zipmod"
            self.assertFalse(target.exists())
            self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_existing_valid_file_is_reindexed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "HS2"
            target = game_dir / "mods" / "Remote" / "sample.zipmod"
            target.parent.mkdir(parents=True)
            (game_dir / "HoneySelect2.exe").write_bytes(b"")
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr(
                    "manifest.xml",
                    "<manifest><guid>sample.guid</guid><name>Sample</name></manifest>",
                )

            remote_db = root / "remote.sqlite"
            source = "https://sideload.betterrepack.com/download/AISHS2/"
            _remote_db(remote_db, [(
                7, source, source + "sample.zipmod", "sample.zipmod", "sample.zipmod",
                "sample.guid", "sample.guid", "Sample", "1", "Author", target.stat().st_size, "ok", 1,
            )])
            db_path = root / "local.sqlite"
            thumbnail_dir = root / "thumbnails"

            with (
                patch.object(completion, "DEFAULT_REMOTE_INDEX_PATH", remote_db),
                patch.object(completion, "index_single_zipmod", return_value={"guid": "sample.guid"}) as index,
            ):
                result = completion.download_card_missing_mods(
                    str(game_dir), [7], db_path=db_path, thumbnail_dir=thumbnail_dir,
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["completed"][0]["status"], "already_exists")
            self.assertEqual(result["affected_mod_guids"], ["sample.guid"])
            index.assert_called_once_with(
                game_dir.resolve(), db_path.resolve(), thumbnail_dir.resolve(), target.resolve(), unittest.mock.ANY,
            )


if __name__ == "__main__":
    unittest.main()
