import sqlite3
import os
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.card_database import (  # noqa: E402
    build_card_database,
    resolve_dependency_records,
)
from star_manager.services.card_library import (  # noqa: E402
    dependency_record_value,
    resolve_card_dependencies,
)
from star_manager.services.mod_database_core import (  # noqa: E402
    init_db,
    timestamp_to_utc,
)


class CharacterCardDependencyTests(unittest.TestCase):
    def test_card_preparation_uses_multiple_workers(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "UserData" / "chara"
            root.mkdir(parents=True)
            card_paths = [root / "a.png", root / "b.png"]
            for card_path in card_paths:
                card_path.write_bytes(b"card")

            thread_names: set[str] = set()
            barrier = threading.Barrier(2)

            def fake_prepare_card_record(card_path, root, preview_dir, conn, now, *args, **kwargs):
                thread_names.add(threading.current_thread().name)
                barrier.wait(timeout=5)
                stat = card_path.stat()
                return {
                    "file_path": str(card_path.resolve()),
                    "relative_path": card_path.name,
                    "file_name": card_path.name,
                    "card_uid": "",
                    "chara_name": card_path.stem,
                    "tags_json": "[]",
                    "favorite": False,
                    "rating": 0,
                    "metadata_file_size": stat.st_size,
                    "metadata_modified_ns": stat.st_mtime_ns,
                    "preview_cache_path": "",
                    "modified_at": timestamp_to_utc(stat.st_mtime),
                    "parse_status": "not_ais",
                    "dependency_count": 0,
                    "missing_count": 0,
                    "last_scanned_at": now,
                    "dependencies": [],
                    "reused": False,
                    "replace_dependencies": True,
                }

            with patch(
                "star_manager.services.card_database.validate_card_root",
                return_value=(True, root, ""),
            ), patch(
                "star_manager.services.card_database.choose_card_database_worker_count",
                return_value=2,
            ), patch(
                "star_manager.services.card_database.prepare_card_record",
                side_effect=fake_prepare_card_record,
            ):
                stats = build_card_database(
                    Path(temp_dir),
                    db_path=Path(temp_dir) / "star_manager.sqlite",
                    preview_dir=Path(temp_dir) / "previews",
                )

            self.assertEqual(stats["worker_count"], 2)
            self.assertEqual(len(thread_names), 2)

    def test_incremental_build_relinks_only_cards_affected_by_changed_mods(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "UserData" / "chara"
            root.mkdir(parents=True)
            card_paths = [root / "a.png", root / "b.png"]
            for card_path in card_paths:
                card_path.write_bytes(b"cached-card")

            db_path = Path(temp_dir) / "star_manager.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    zipmod_ids = {}
                    item_ids = {}
                    for guid in ["example.changed", "example.untouched"]:
                        cursor = conn.execute(
                            """
                            INSERT INTO zipmods (
                                guid, name, file_path, relative_path, file_name, scan_status,
                                last_scanned_at, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (guid, guid, f"{guid}.zipmod", f"{guid}.zipmod", f"{guid}.zipmod", "ok", now, now, now),
                        )
                        zipmod_ids[guid] = cursor.lastrowid
                        item_cursor = conn.execute(
                            """
                            INSERT INTO mod_items (
                                zipmod_id, zipmod_guid, item_id, kind, name, parse_status,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (cursor.lastrowid, guid, "1", "240", guid, "ok", now, now),
                        )
                        item_ids[guid] = item_cursor.lastrowid

                    for card_path, guid in zip(
                        card_paths, ["example.changed", "example.untouched"]
                    ):
                        card_stat = card_path.stat()
                        card_cursor = conn.execute(
                            """
                            INSERT INTO character_cards (
                                file_path, relative_path, file_name, modified_at,
                                metadata_file_size, metadata_modified_ns, parse_status,
                                dependency_count, missing_count, last_scanned_at
                            ) VALUES (?, ?, ?, ?, ?, ?, 'ok', 1, 1, ?)
                            """,
                            (
                                str(card_path.resolve()),
                                card_path.name,
                                card_path.name,
                                timestamp_to_utc(card_stat.st_mtime),
                                card_stat.st_size,
                                card_stat.st_mtime_ns,
                                now,
                            ),
                        )
                        conn.execute(
                            """
                            INSERT INTO character_card_dependencies (
                                card_id, mod_id, category_no, slot, resolve_status
                            ) VALUES (?, ?, '240', '1', 'missing_zipmod')
                            """,
                            (card_cursor.lastrowid, guid),
                        )

                with patch(
                    "star_manager.services.card_database.validate_card_root",
                    return_value=(True, root, ""),
                ):
                    stats = build_card_database(
                        Path(temp_dir),
                        db_path=db_path,
                        preview_dir=Path(temp_dir) / "previews",
                        affected_mod_guids={" EXAMPLE.CHANGED "},
                    )

                rows = {
                    row["mod_id"]: row
                    for row in conn.execute(
                        """
                        SELECT mod_id, zipmod_id, mod_item_id, resolve_status
                        FROM character_card_dependencies
                        """
                    )
                }
                self.assertEqual(rows["example.changed"]["resolve_status"], "resolved")
                self.assertEqual(rows["example.changed"]["zipmod_id"], zipmod_ids["example.changed"])
                self.assertEqual(rows["example.changed"]["mod_item_id"], item_ids["example.changed"])
                self.assertEqual(rows["example.untouched"]["resolve_status"], "missing_zipmod")
                self.assertIsNone(rows["example.untouched"]["zipmod_id"])
                self.assertEqual(stats["relinked_cards"], 1)
                self.assertEqual(stats["untouched_cards"], 1)
            finally:
                conn.close()

    def test_incremental_build_reparses_when_file_signature_changes_within_same_second(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "UserData" / "chara"
            root.mkdir(parents=True)
            card_path = root / "changed.png"
            card_path.write_bytes(b"old-card")
            old_stat = card_path.stat()
            card_path.write_bytes(b"new-card-content")
            changed_stat = card_path.stat()
            os.utime(
                card_path,
                ns=(changed_stat.st_atime_ns, old_stat.st_mtime_ns + 1),
            )
            changed_stat = card_path.stat()
            self.assertEqual(timestamp_to_utc(old_stat.st_mtime), timestamp_to_utc(changed_stat.st_mtime))

            db_path = Path(temp_dir) / "star_manager.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    conn.execute(
                        """
                        INSERT INTO character_cards (
                            file_path, modified_at, metadata_file_size, metadata_modified_ns,
                            parse_status, last_scanned_at
                        ) VALUES (?, ?, ?, ?, 'ok', '')
                        """,
                        (
                            str(card_path.resolve()),
                            timestamp_to_utc(old_stat.st_mtime),
                            old_stat.st_size,
                            old_stat.st_mtime_ns,
                        ),
                    )
            finally:
                conn.close()

            with patch(
                "star_manager.services.card_database.validate_card_root",
                return_value=(True, root, ""),
            ):
                stats = build_card_database(
                    Path(temp_dir),
                    db_path=db_path,
                    preview_dir=Path(temp_dir) / "previews",
                )

            self.assertEqual(stats["reused_cards"], 0)
            self.assertEqual(stats["changed_cards"], 1)

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

    def test_card_detail_distinguishes_same_slot_across_kinds(self):
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
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "tubge.CJYF",
                            "[TuBge]CJ",
                            str(Path(temp_dir) / "cj.zipmod"),
                            "cj.zipmod",
                            "cj.zipmod",
                            "ok",
                            now,
                            now,
                            now,
                        ),
                    )
                    zipmod_id = cursor.lastrowid
                    for kind, name in [
                        ("241", "[TuBge]CJ Bot"),
                        ("245", "[TuBge]CJ Pantyhose"),
                        ("240", "[TuBge]CJ Top"),
                    ]:
                        conn.execute(
                            """
                            INSERT INTO mod_items (
                                zipmod_id, zipmod_guid, item_id, kind, name, parse_status,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (zipmod_id, "tubge.CJYF", "0", kind, name, "ok", now, now),
                        )

                records = [
                    {
                        "ModID": "tubge.CJYF",
                        "CategoryNo": 240,
                        "Slot": 0,
                        "Property": "outfit.ChaFileClothes.ClothesTop",
                    },
                    {
                        "ModID": "tubge.CJYF",
                        "CategoryNo": 241,
                        "Slot": 0,
                        "Property": "outfit.ChaFileClothes.ClothesBot",
                    },
                    {
                        "ModID": "tubge.CJYF",
                        "CategoryNo": 245,
                        "Slot": 0,
                        "Property": "outfit.ChaFileClothes.ClothesPantyhose",
                    },
                ]
                with patch(
                    "star_manager.services.card_library.extract_auto_resolver_records_from_card",
                    return_value=records,
                ):
                    dependencies = resolve_card_dependencies("test.png", db_path=db_path)

                self.assertEqual(
                    [dependency["item"]["name"] for dependency in dependencies],
                    ["[TuBge]CJ Top", "[TuBge]CJ Bot", "[TuBge]CJ Pantyhose"],
                )
                self.assertEqual(
                    [dependency["item"]["kind"] for dependency in dependencies],
                    ["240", "241", "245"],
                )
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
