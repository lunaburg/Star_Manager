import sqlite3
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services.mod_database_queries import (  # noqa: E402
    BUILTIN_SOURCE_LABEL,
    export_zipmods,
    hydrate_current_game_state_thumbnails,
    list_mod_item_filters,
    list_mod_items,
    list_workbench_template_items,
    list_zipmods,
    MAP_SCENE_FILTER_KIND,
    resolve_thumbnail_cache_path,
    thumbnail_url_for_cache_path,
)


class CurrentGameThumbnailTests(unittest.TestCase):
    def test_hydrates_only_a_unique_resolver_match(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            thumbnail_path = root / "thumbnails" / "item.png"
            thumbnail_path.parent.mkdir(parents=True)
            thumbnail_path.write_bytes(b"png")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    zipmod_id = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, file_path, relative_path, file_name,
                            scan_status, last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        (
                            "sample.current",
                            "Sample Current",
                            str(root / "sample.zipmod"),
                            "sample.zipmod",
                            "sample.zipmod",
                            now,
                            now,
                            now,
                        ),
                    ).lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name,
                            thumbnail_cache_path, thumbnail_status, thumb_tex,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'ready', 'ThumbTex', 'ok', ?, ?)
                        """,
                        (
                            zipmod_id,
                            "sample.current",
                            "00123",
                            "240",
                            "Current Dress",
                            str(thumbnail_path),
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            state = hydrate_current_game_state_thumbnails(
                {
                    "available": True,
                    "clothes": [
                        {
                            "categoryNo": 240,
                            "localSlot": 900001,
                            "resolverRecords": [
                                {"guid": "SAMPLE.CURRENT", "slot": 123}
                            ],
                        },
                        {
                            "categoryNo": 240,
                            "localSlot": 1,
                            "resolverRecords": [],
                        },
                    ],
                    "faces": [
                        {
                            "categoryNo": 210,
                            "localSlot": 2,
                            "resolverRecords": [
                                {"guid": "SAMPLE.CURRENT", "slot": 123}
                            ],
                        }
                    ],
                },
                db_path=db_path,
            )

        self.assertEqual(state["clothes"][0]["thumbnailUrl"], "/mods/items/1/thumbnail")
        self.assertEqual(state["clothes"][1]["thumbnailUrl"], "")
        self.assertEqual(state["faces"][0]["thumbnailUrl"], "")

    def test_hydrates_builtin_thumbnail_by_game_dir_category_and_local_slot(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            game_dir = root / "game"
            thumbnail_path = root / "thumbnails" / "builtin.png"

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    conn.execute(
                        """
                        INSERT INTO builtin_items (
                            game_dir_key, game_dir, category_no, item_id, name,
                            thumbnail_cache_path, thumbnail_status, resource_status,
                            created_at, updated_at
                        ) VALUES (?, ?, '240', '1', 'Vanilla Dress', ?, 'ready', 'in_game', ?, ?)
                        """,
                        (
                            str(game_dir.resolve()).casefold(),
                            str(game_dir),
                            str(thumbnail_path),
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            with patch(
                "star_manager.services.mod_database_queries.thumbnail_url_for_cache_path",
                return_value="/mods/thumbnails?path=builtin",
            ):
                state = hydrate_current_game_state_thumbnails(
                    {
                        "available": True,
                        "clothes": [
                            {
                                "categoryNo": 240,
                                "localSlot": 1,
                                "resolverRecords": [],
                            }
                        ],
                    },
                    db_path=db_path,
                    game_dir=game_dir,
                )

        self.assertEqual(
            state["clothes"][0]["thumbnailUrl"],
            "/mods/thumbnails?path=builtin",
        )


class WorkbenchTemplateItemQueryTests(unittest.TestCase):
    def test_lists_only_available_main_unity3d_items(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    package_id = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, author, file_path, relative_path, file_name,
                            scan_status, last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        (
                            "sample.template",
                            "Sample Template Mod",
                            "Author",
                            str(root / "sample.zipmod"),
                            "Author/sample.zipmod",
                            "sample.zipmod",
                            now,
                            now,
                            now,
                        ),
                    ).lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name,
                            main_manifest, main_ab, main_data, unity3d_status,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)
                        """,
                        (
                            package_id,
                            "sample.template",
                            "1001",
                            "240",
                            "Database Dress",
                            "abdata",
                            "Author/dress.unity3d",
                            "DressRoot",
                            "in_mod",
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name,
                            main_manifest, main_ab, unity3d_status,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)
                        """,
                        (
                            package_id,
                            "sample.template",
                            "1002",
                            "240",
                            "Missing Dress",
                            "abdata",
                            "Author/missing.unity3d",
                            "missing",
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, item_id, kind, name,
                            main_manifest, main_ab, unity3d_status,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)
                        """,
                        (
                            package_id,
                            "sample.template",
                            "1003",
                            "240",
                            "Image Only",
                            "abdata",
                            "Author/image.png",
                            "in_mod",
                            now,
                            now,
                        ),
                    )
            finally:
                conn.close()

            result = list_workbench_template_items(db_path=db_path)
            searched = list_workbench_template_items(db_path=db_path, search="DressRoot")
            filtered = list_workbench_template_items(db_path=db_path, author="auth", kind="240")
            wrong_author = list_workbench_template_items(db_path=db_path, author="Other")

        self.assertTrue(result["exists"])
        self.assertEqual(result["total"], 1)
        self.assertEqual([row["name"] for row in result["rows"]], ["Database Dress"])
        self.assertEqual(result["rows"][0]["main_data"], "DressRoot")
        self.assertEqual(searched["total"], 1)
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(wrong_author["total"], 0)


class BuiltinItemQueryTests(unittest.TestCase):
    def test_lists_current_game_builtin_items_without_changing_default_mod_query(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            game_dir = root / "game"
            thumbnail_path = root / "thumbnails" / "builtin.png"
            thumbnail_path.parent.mkdir(parents=True)
            thumbnail_path.write_bytes(b"png")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    conn.execute(
                        """
                        INSERT INTO builtin_items (
                            game_dir_key, game_dir, category_no, item_id, name,
                            source_path, main_ab, thumbnail_cache_path, thumbnail_status,
                            resource_status, created_at, updated_at
                        ) VALUES (?, ?, '240', '1', 'Vanilla Dress', ?, ?, ?, 'ready', 'in_game', ?, ?)
                        """,
                        (
                            str(game_dir.resolve()).casefold(),
                            str(game_dir),
                            "abdata/list/characustom/clothes.unity3d",
                            "abdata/abdata/vanilla.unity3d",
                            str(thumbnail_path),
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO builtin_items (
                            game_dir_key, game_dir, category_no, item_id, name,
                            created_at, updated_at
                        ) VALUES (?, ?, '504', '2', 'Hidden Unknown Kind', ?, ?)
                        """,
                        (str(game_dir.resolve()).casefold(), str(game_dir), now, now),
                    )
            finally:
                conn.close()

            default_result = list_mod_items(db_path=db_path)
            all_result = list_mod_items(
                db_path=db_path,
                source="all",
                game_dir=game_dir,
            )
            builtin_result = list_mod_items(
                db_path=db_path,
                source="builtin",
                game_dir=game_dir,
                kind="240",
                author="游戏本体",
            )

        self.assertEqual(default_result["total"], 0)
        self.assertEqual(all_result["total"], 1)
        self.assertEqual(all_result["rows"][0]["source_type"], "builtin")
        self.assertEqual(all_result["rows"][0]["source_mod"], "游戏本体")
        self.assertEqual(all_result["rows"][0]["thumbnail_status"], "ready")
        self.assertEqual(builtin_result["total"], 1)

    def test_item_filters_scope_builtin_kinds_to_current_game(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            first_game = root / "game-one"
            second_game = root / "game-two"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    for game_dir, category_no, item_id in (
                        (first_game, "240", "1"),
                        (second_game, "300", "2"),
                        (first_game, "504", "3"),
                    ):
                        conn.execute(
                            """
                            INSERT INTO builtin_items (
                                game_dir_key, game_dir, category_no, item_id,
                                name, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                str(game_dir.resolve()).casefold(),
                                str(game_dir),
                                category_no,
                                item_id,
                                f"Builtin {category_no}",
                                now,
                                now,
                            ),
                        )
            finally:
                conn.close()

            scoped = list_mod_item_filters(db_path=db_path, game_dir=first_game)
            unscoped = list_mod_item_filters(db_path=db_path)

        self.assertEqual(scoped["kinds"], ["240"])
        self.assertIn(BUILTIN_SOURCE_LABEL, scoped["authors"])
        self.assertEqual(unscoped["kinds"], ["240", "300"])


class ItemPaginationTests(unittest.TestCase):
    def test_incremental_page_can_skip_count_and_reports_has_more(self):
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
                            guid, name, file_path, relative_path, file_name,
                            scan_status, last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        (
                            "pagination.sample",
                            "Pagination sample",
                            str(root / "sample.zipmod"),
                            "sample.zipmod",
                            "sample.zipmod",
                            now,
                            now,
                            now,
                        ),
                    ).lastrowid
                    for index, name in enumerate(("Alpha", "Bravo", "Charlie", "Delta"), start=1):
                        conn.execute(
                            """
                            INSERT INTO mod_items (
                                zipmod_id, zipmod_guid, item_id, kind, name,
                                parse_status, created_at, updated_at
                            ) VALUES (?, ?, ?, '240', ?, 'ok', ?, ?)
                            """,
                            (zipmod_id, "pagination.sample", str(index), name, now, now),
                        )
            finally:
                conn.close()

            result = list_mod_items(
                db_path=db_path,
                offset=2,
                limit=1,
                include_total=False,
            )

        self.assertIsNone(result["total"])
        self.assertTrue(result["has_more"])
        self.assertEqual([row["name"] for row in result["rows"]], ["Charlie"])


class ZipmodExportTests(unittest.TestCase):
    def test_map_filter_matches_all_map_kind_variants(self):
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
                        ("sample.map", "Sample Map", str(root / "map.zipmod"), "map.zipmod", "map.zipmod", now, now, now),
                    ).lastrowid
                    for index, kind in enumerate(("__map_scene__", "__game_map_scene__", "__game_studio_map_scene__"), start=1):
                        conn.execute(
                            """
                            INSERT INTO mod_items (
                                zipmod_id, zipmod_guid, item_id, kind, name,
                                parse_status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, 'ok', ?, ?)
                            """,
                            (zipmod_id, "sample.map", f"map-{index}", kind, f"Map {index}", now, now),
                        )
            finally:
                conn.close()

            result = list_mod_items(db_path=db_path, kind=MAP_SCENE_FILTER_KIND)

        self.assertEqual([row["name"] for row in result["rows"]], ["Map 1", "Map 2", "Map 3"])

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

    def test_zipmod_author_filter_matches_partial_author_and_escapes_like_wildcards(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-01-01T00:00:00+00:00"
                with conn:
                    for index, author in enumerate(("[c123w]liino01", "[c123w]liino02", "[c123x]liino01")):
                        conn.execute(
                            """
                            INSERT INTO zipmods (
                                guid, name, author, file_path, relative_path, file_name,
                                scan_status, last_scanned_at, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                            """,
                            (
                                f"sample.{index}",
                                f"Sample {index}",
                                author,
                                str(root / f"sample-{index}.zipmod"),
                                f"sample-{index}.zipmod",
                                f"sample-{index}.zipmod",
                                now,
                                now,
                                now,
                            ),
                        )
            finally:
                conn.close()

            result = list_zipmods(db_path=db_path, author="[c123w")
            wildcard_result = list_zipmods(db_path=db_path, author="[c123w%")

        self.assertEqual(result["total"], 2)
        self.assertEqual(
            {row["author"] for row in result["rows"]},
            {"[c123w]liino01", "[c123w]liino02"},
        )
        self.assertEqual(wildcard_result["total"], 0)


class StudioItemQueryTests(unittest.TestCase):
    def test_lists_studio_items_without_thumbnail_or_thumb_filter_failure(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "mod_database.sqlite"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                now = "2026-09-17T00:00:00+00:00"
                with conn:
                    zipmod_id = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, author, file_path, relative_path, file_name,
                            scan_status, last_scanned_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        ("studio.guid", "Studio Sample", "Author", str(root / "studio.zipmod"), "studio.zipmod", "studio.zipmod", now, now, now),
                    ).lastrowid
                    conn.execute(
                        """
                        INSERT INTO mod_items (
                            zipmod_id, zipmod_guid, zipmod_author, csv_path, item_id, kind,
                            item_domain, studio_group_id, studio_group_name,
                            studio_category_id, studio_category_name, name, main_manifest,
                            main_ab, main_data, thumbnail_status, unity3d_status,
                            parse_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?)
                        """,
                        (
                            zipmod_id, "studio.guid", "Author", "abdata/studio/info/author/ItemList_01_8460_06.csv",
                            "2", "__studio_item__", "studio", "8460", "Author Group", "6", "Animals",
                            "Bull", "abdata", "author/data_prefab_000.unity3d", "Bull", "not_applicable", "in_mod", now, now,
                        ),
                    )
            finally:
                conn.close()

            result = list_mod_items(db_path=db_path, kind="__studio_item__")
            thumb_result = list_mod_items(db_path=db_path, kind="__studio_item__", status="thumb")
            zipmod_result = list_zipmods(db_path=db_path)
            thumbnail_zipmods = list_zipmods(db_path=db_path, status="thumbnail")
            warning_zipmods = list_zipmods(db_path=db_path, status="warning")
            normal_zipmods = list_zipmods(db_path=db_path, status="normal")

        self.assertEqual(result["total"], 1)
        item = result["rows"][0]
        self.assertEqual(item["item_domain"], "studio")
        self.assertEqual(item["thumbnail_status"], "not_applicable")
        self.assertEqual(item["thumbnail_url"], "")
        self.assertEqual(item["studio_group_name"], "Author Group")
        self.assertEqual(item["studio_category_name"], "Animals")
        self.assertEqual(thumb_result["total"], 0)
        self.assertEqual(zipmod_result["total"], 1)
        self.assertEqual(zipmod_result["rows"][0]["thumbnail_issue_count"], 0)
        self.assertEqual(thumbnail_zipmods["total"], 0)
        self.assertEqual(warning_zipmods["total"], 0)
        self.assertEqual(normal_zipmods["total"], 1)


if __name__ == "__main__":
    unittest.main()
