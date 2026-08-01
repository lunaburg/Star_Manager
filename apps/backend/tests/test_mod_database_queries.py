import sqlite3
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services.mod_database_queries import (  # noqa: E402
    export_zipmods,
    list_mod_items,
    list_zipmods,
    resolve_thumbnail_cache_path,
    thumbnail_url_for_cache_path,
)


class ZipmodExportTests(unittest.TestCase):
    def test_item_usage_filter_recovers_dependency_with_cleared_item_foreign_key(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    zipmod_id = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        (
                            "sample.used",
                            "Sample Used",
                            str(root / "sample.zipmod"),
                            "sample.zipmod",
                            "sample.zipmod",
                            now,
                            now,
                            now,
                        ),
                    ).lastrowid
                    item_id = conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?)
                        """,
                        (zipmod_id, "sample.used", "00123", "240", "Used Item", now, now),
                    ).lastrowid
                    card_id = conn.execute(
                        """
                        INSERT INTO character_cards (
                            file_path, file_name, modified_at, parse_status, last_scanned_at
                        ) VALUES (?, ?, ?, 'ok', ?)
                        """,
                        (str(root / "card.png"), "card.png", now, now),
                    ).lastrowid
                    conn.execute(
                        """
                        INSERT INTO character_card_dependencies (
                            card_id, mod_id, category_no, slot, zipmod_id,
                            mod_item_id, resolve_status
                        ) VALUES (?, ?, ?, ?, ?, NULL, 'resolved')
                        """,
                        (card_id, " SAMPLE.USED ", "240", "123", zipmod_id),
                    )
            finally:
                conn.close()

            used = list_mod_items(db_path=db_path, usage="used")
            unused = list_mod_items(db_path=db_path, usage="unused")

            self.assertEqual([row["id"] for row in used["rows"]], [item_id])
            self.assertEqual(unused["rows"], [])

    def test_thumbnail_url_remaps_old_runtime_cache_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current_thumbnail_dir = root / "current" / "thumbnails"
            key = "abcdef1234567890abcdef1234567890abcdef12"
            current_thumbnail = current_thumbnail_dir / key[:2] / key[2:4] / f"{key}.png"
            current_thumbnail.parent.mkdir(parents=True)
            current_thumbnail.write_bytes(b"png")

            old_cache_path = root / "old" / "runtime" / "thumbnails" / key[:2] / key[2:4] / f"{key}.png"
            url = thumbnail_url_for_cache_path(str(old_cache_path), thumbnail_dir=current_thumbnail_dir)

            self.assertIn("/mods/thumbnails?path=", url)
            self.assertIn(quote(str(current_thumbnail.resolve())), url)

    def test_resolve_thumbnail_cache_path_migrates_old_runtime_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current_thumbnail_dir = root / "current" / "thumbnails"
            key = "abcdef1234567890abcdef1234567890abcdef12"
            old_cache_path = root / "old" / "runtime" / "thumbnails" / key[:2] / key[2:4] / f"{key}.png"
            old_cache_path.parent.mkdir(parents=True)
            old_cache_path.write_bytes(b"old-png")

            resolved = resolve_thumbnail_cache_path(str(old_cache_path), thumbnail_dir=current_thumbnail_dir)
            expected = current_thumbnail_dir / key[:2] / key[2:4] / f"{key}.png"

            self.assertEqual(resolved, expected.resolve())
            self.assertEqual(expected.read_bytes(), b"old-png")

    def test_export_zipmods_includes_external_unity3d_under_abdata_tree(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path = root / "mods" / "Sideloader" / "sample.zipmod"
            zipmod_path.parent.mkdir(parents=True)
            with zipfile.ZipFile(zipmod_path, "w") as zf:
                zf.writestr("manifest.xml", "<manifest><guid>sample.guid</guid></manifest>")

            unity3d_path = root / "abdata" / "chara" / "sample" / "main.unity3d"
            unity3d_path.parent.mkdir(parents=True)
            unity3d_path.write_bytes(b"bundle")

            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at, unity3d_status,
                            unity3d_in_game_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "sample.guid",
                            "sample",
                            str(zipmod_path),
                            "Sideloader/sample.zipmod",
                            "sample.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                            "in_game",
                            1,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, main_manifest,
                            main_ab, main_data, thumb_ab, thumb_tex, thumbnail_status,
                            unity3d_status, parse_status, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zipmod_id,
                            "sample.guid",
                            "1",
                            "210",
                            "Sample",
                            "abdata",
                            "chara/sample/main.unity3d",
                            "main",
                            "",
                            "",
                            "missing",
                            "in_game",
                            "ok",
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            target_dir = root / "export"
            result = export_zipmods([zipmod_id], str(target_dir), "copy", db_path=db_path)

            self.assertTrue(result["ok"])
            self.assertEqual(result["exported_count"], 1)
            self.assertEqual(result["exported_unity3d_count"], 1)
            self.assertTrue((target_dir / "Sideloader" / "sample.zipmod").is_file())
            self.assertEqual((target_dir / "abdata" / "chara" / "sample" / "main.unity3d").read_bytes(), b"bundle")
            self.assertTrue(unity3d_path.is_file())

            portable_dir = root / "portable"
            portable_result = export_zipmods(
                [zipmod_id], str(portable_dir), "copy", "portable", db_path=db_path
            )
            self.assertTrue(portable_result["ok"])
            self.assertTrue((portable_dir / "mods" / "Sideloader" / "sample.zipmod").is_file())
            self.assertEqual(
                (portable_dir / "abdata" / "chara" / "sample" / "main.unity3d").read_bytes(),
                b"bundle",
            )

    def test_read_error_filter_matches_manifests_without_guid(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                rows = [
                    ("missing.guid", "missing.zipmod", "missing_manifest"),
                    ("invalid.guid", "invalid.zipmod", "invalid_manifest"),
                    ("badzip.guid", "badzip.zipmod", "read_error"),
                    ("ok.guid", "ok.zipmod", "ok"),
                ]
                with conn:
                    for guid, file_name, scan_status in rows:
                        conn.execute(
                            """
                            INSERT INTO zipmods (
                                guid, name, file_path, relative_path, file_name, scan_status,
                                last_scanned_at, created_at, updated_at
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                guid,
                                guid,
                                str(root / "mods" / file_name),
                                file_name,
                                file_name,
                                scan_status,
                                now,
                                now,
                                now,
                            ),
                        )
            finally:
                conn.close()

            result = list_zipmods(db_path=db_path, status="read_error")

            self.assertEqual(result["total"], 3)
            self.assertEqual(
                {row["guid"] for row in result["rows"]},
                {"badzip.guid", "invalid.guid", "missing.guid"},
            )

    def test_zipmod_id_filter_returns_only_the_requested_mod(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    requested_id = None
                    for index in range(2):
                        cursor = conn.execute(
                            """
                            INSERT INTO zipmods (
                                guid, name, author, file_path, relative_path, file_name,
                                scan_status, last_scanned_at, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                            """,
                            (
                                f"sample.{index}",
                                f"Sample {index}",
                                "same-author",
                                str(root / f"sample-{index}.zipmod"),
                                f"sample-{index}.zipmod",
                                f"sample-{index}.zipmod",
                                now,
                                now,
                                now,
                            ),
                        )
                        if index == 1:
                            requested_id = cursor.lastrowid
            finally:
                conn.close()

            result = list_zipmods(db_path=db_path, zipmod_id=requested_id)

            self.assertEqual(result["total"], 1)
            self.assertEqual(result["rows"][0]["id"], requested_id)


if __name__ == "__main__":
    unittest.main()
