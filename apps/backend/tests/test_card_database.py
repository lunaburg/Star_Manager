import sqlite3
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_database import resolve_dependency_records  # noqa: E402
from star_manager.services.card_library import dependency_record_value  # noqa: E402
from star_manager.services.mod_database_core import init_db  # noqa: E402


class CharacterCardDependencyTests(unittest.TestCase):
    def test_slot_matches_item_id_with_leading_zeroes(self):
        with TemporaryDirectory() as temp_dir:
            conn = sqlite3.connect(Path(temp_dir) / "star_manager.sqlite")
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "sjjpl.top.228", "sjjpl_top228", str(Path(temp_dir) / "sjjpl.zipmod"),
                            "sjjpl.zipmod", "sjjpl.zipmod", "ok", now, now, now,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    item_cursor = conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, parse_status,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (zipmod_id, "sjjpl.top.228", "003", "242", "sjjpl_bra_228_3", "ok", now, now),
                    )

                dependencies = resolve_dependency_records(
                    conn,
                    [{"ModID": "sjjpl.top.228", "CategoryNo": 242, "Slot": 3}],
                )

                self.assertEqual(dependencies[0]["mod_item_id"], item_cursor.lastrowid)
                self.assertEqual(dependencies[0]["resolve_status"], "resolved")
            finally:
                conn.close()

    def test_card_detail_preserves_zero_slot(self):
        self.assertEqual(dependency_record_value(0), "0")
        self.assertEqual(dependency_record_value(None), "")

    def test_mod_id_matching_is_case_insensitive(self):
        with TemporaryDirectory() as temp_dir:
            conn = sqlite3.connect(Path(temp_dir) / "star_manager.sqlite")
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name, scan_status,
                            last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "SJJPL.Socks.19",
                            "sjjpl",
                            str(Path(temp_dir) / "sjjpl.zipmod"),
                            "sjjpl.zipmod",
                            "sjjpl.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    item_cursor = conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, parse_status,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (zipmod_id, "SJJPL.Socks.19", "19", "246", "sjjpl", "ok", now, now),
                    )

                dependencies = resolve_dependency_records(
                    conn,
                    [{"ModID": "sjjpl.socks.19", "CategoryNo": 246, "Slot": 19}],
                )

                self.assertEqual(dependencies[0]["zipmod_id"], zipmod_id)
                self.assertEqual(dependencies[0]["mod_item_id"], item_cursor.lastrowid)
                self.assertEqual(dependencies[0]["resolve_status"], "resolved")
            finally:
                conn.close()

    def test_zero_slot_matches_zero_item_id(self):
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "star_manager.sqlite"
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
                            last_scanned_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "ls.cloth.yrys",
                            "yrys",
                            str(Path(temp_dir) / "yrys.zipmod"),
                            "yrys.zipmod",
                            "yrys.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    item_cursor = conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name, parse_status,
                            created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            zipmod_id,
                            "ls.cloth.yrys",
                            "0",
                            "240",
                            "yrysTop",
                            "ok",
                            now,
                            now,
                        ),
                    )
                    item_id = item_cursor.lastrowid

                dependencies = resolve_dependency_records(
                    conn,
                    [
                        {
                            "ModID": "ls.cloth.yrys",
                            "CategoryNo": 240,
                            "Slot": 0,
                            "LocalSlot": 100018502,
                        }
                    ],
                )

                self.assertEqual(len(dependencies), 1)
                self.assertEqual(dependencies[0]["slot"], "0")
                self.assertEqual(dependencies[0]["zipmod_id"], zipmod_id)
                self.assertEqual(dependencies[0]["mod_item_id"], item_id)
                self.assertEqual(dependencies[0]["resolve_status"], "resolved")
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
