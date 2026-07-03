import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


class BulkApplyItemThumbnailTaskTests(unittest.TestCase):
    def test_bulk_apply_relocates_items_after_each_zipmod_reindex(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mods.sqlite3"
            source_image = root / "source.png"
            source_image.write_bytes(b"png")
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                conn.execute(
                    """
                    INSERT INTO zipmods (
                        guid, name, version, author, file_path, relative_path, file_name,
                        file_size, modified_at, scan_status, scan_error,
                        last_scanned_at, created_at, updated_at
                    )
                    VALUES ('sample.guid', 'Sample', '1', 'Author', 'sample.zipmod',
                        'sample.zipmod', 'sample.zipmod', 1, 'now', 'ok', '', 'now', 'now', 'now')
                    """
                )
                self._insert_items(conn)
                first_id, second_id = [
                    int(row[0])
                    for row in conn.execute("SELECT id FROM mod_items ORDER BY item_id")
                ]
                conn.commit()
            finally:
                conn.close()

            imported_ids = []

            def fake_import(item_id, _image_path):
                imported_ids.append(int(item_id))
                if len(imported_ids) == 1:
                    replacement_conn = sqlite3.connect(db_path)
                    try:
                        replacement_conn.execute("DELETE FROM mod_items WHERE zipmod_id = 1")
                        self._insert_items(replacement_conn)
                        replacement_conn.commit()
                    finally:
                        replacement_conn.close()
                return {"ok": True, "item_id": int(item_id)}

            task = bridge.TaskState(id="task", task_type="bulk_apply_item_thumbnail")
            with patch.object(bridge, "DEFAULT_DB_PATH", db_path), patch.object(
                bridge, "import_zipmod_item_thumbnail", side_effect=fake_import
            ):
                bridge.run_task(
                    task,
                    {
                        "source_image_path": str(source_image),
                        "target_item_ids": [first_id, second_id],
                    },
                )

            self.assertEqual(task.status, "completed")
            self.assertEqual(task.data["imported_count"], 2)
            self.assertEqual(imported_ids[0], first_id)
            self.assertNotEqual(imported_ids[1], second_id)

    def _insert_items(self, conn):
        for csv_item_id, name in (("10", "First"), ("20", "Second")):
            conn.execute(
                """
                INSERT INTO mod_items (
                    zipmod_id, zipmod_guid, zipmod_author, csv_path, item_id, kind, name,
                    main_manifest, main_ab, main_data, thumb_ab, thumb_tex,
                    thumbnail_cache_path, thumbnail_status, thumbnail_error,
                    unity3d_status, unity3d_error, parse_status, parse_error,
                    created_at, updated_at
                )
                VALUES (
                    1, 'sample.guid', 'Author', 'abdata/list/sample.csv', ?, '314', ?,
                    '', '', '', '', '', '', 'missing', '', '', '', 'ok', '', 'now', 'now'
                )
                """,
                (csv_item_id, name),
            )


if __name__ == "__main__":
    unittest.main()
