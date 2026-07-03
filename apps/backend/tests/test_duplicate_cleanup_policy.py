import importlib.util
import sqlite3
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

BRIDGE_PATH = BACKEND_ROOT / "app" / "bridge.py"
spec = importlib.util.spec_from_file_location("star_manager_bridge", BRIDGE_PATH)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)

from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services.mod_database_assets import (  # noqa: E402
    _duplicate_delete_reasons,
    _duplicate_keep_sort_key,
    _version_sort_key,
    delete_primary_and_promote_duplicate,
)


class DuplicateCleanupPolicyTests(unittest.TestCase):
    def test_version_sort_treats_v_prefix_as_equivalent(self):
        self.assertEqual(_version_sort_key("v1.0"), _version_sort_key("1.0"))
        self.assertEqual(_version_sort_key("V 1.0"), _version_sort_key("1.0"))
        self.assertLess(_version_sort_key("v1.0"), _version_sort_key("1.1"))

    def test_allows_cleanup_when_v_prefix_versions_are_equivalent(self):
        version_key = _version_sort_key("1.0")
        duplicate_ids, reason = bridge.choose_safe_duplicate_cleanup_ids(
            {
                "candidates": [
                    {
                        "role": "primary",
                        "exists": True,
                        "version": "v1.0",
                        "recommendation_reasons": ["latest_version", "most_complete"],
                        "missing_item_count_vs_union": 0,
                        "completeness_score": 20,
                    },
                    {
                        "role": "duplicate",
                        "duplicate_id": 44,
                        "version": "1.0",
                        "recommendation_reasons": ["latest_version", "most_complete"],
                        "unique_item_count": 0,
                        "completeness_score": 20,
                    },
                ],
                "summary": {"latest_version": "1.0", "latest_version_key": version_key},
            }
        )

        self.assertEqual(duplicate_ids, [44])
        self.assertEqual(reason, "")

    def test_recommends_newer_more_complete_duplicate_over_primary(self):
        primary = {
            "index": 0,
            "role": "primary",
            "version": "1.0",
            "recommendation_reasons": [],
            "missing_item_count_vs_union": 2,
            "unique_item_count": 0,
            "completeness_score": 130,
            "ok_item_count": 10,
            "unity3d_in_mod_count": 10,
            "file_size": 13,
        }
        duplicate = {
            "index": 1,
            "role": "duplicate",
            "version": "3.0",
            "recommendation_reasons": ["latest_version", "most_complete", "largest_file"],
            "missing_item_count_vs_union": 0,
            "unique_item_count": 2,
            "completeness_score": 156,
            "ok_item_count": 12,
            "unity3d_in_mod_count": 12,
            "file_size": 16,
        }

        keep = max([primary, duplicate], key=_duplicate_keep_sort_key)

        self.assertIs(keep, duplicate)
        self.assertEqual(
            _duplicate_delete_reasons(primary, keep),
            ["missing_items", "no_unique_items", "lower_completeness", "older_version", "smaller_file"],
        )

    def test_promotes_duplicate_after_deleting_primary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_dir = root / "game"
            mods_dir = game_dir / "mods"
            mods_dir.mkdir(parents=True)
            primary_path = mods_dir / "old.zipmod"
            duplicate_path = mods_dir / "new.zipmod"

            def write_zipmod(path: Path, version: str, item_ids: list[str]) -> None:
                rows = [
                    "300\r\n",
                    "0\r\n",
                    "list.bytes\r\n",
                    "ID,Kind,Possess,Name,EN_US,MainManifest,MainAB,MainData,ThumbAB,ThumbTex\r\n",
                ]
                for item_id in item_ids:
                    rows.append(
                        f"{item_id},0,1,Item {item_id},0,abdata,chara/sample/main.unity3d,main,chara/sample/main.unity3d,thumb\r\n"
                    )
                with zipfile.ZipFile(path, "w") as zf:
                    zf.writestr(
                        "manifest.xml",
                        (
                            "<manifest>"
                            "<guid>sample.guid</guid>"
                            "<name>Sample</name>"
                            f"<version>{version}</version>"
                            "<author>Tester</author>"
                            "</manifest>"
                        ),
                    )
                    zf.writestr("abdata/list/characustom/sample.csv", "".join(rows))
                    zf.writestr("abdata/chara/sample/main.unity3d", b"bundle")

            write_zipmod(primary_path, "1.0", ["1"])
            write_zipmod(duplicate_path, "2.0", ["1", "2"])

            db_path = root / "star_manager.sqlite"
            now = "2026-01-01T00:00:00+00:00"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                init_db(conn)
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO zipmods (
                            guid, name, version, author, file_path, relative_path, file_name,
                            file_size, modified_at, scan_status, last_scanned_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                        """,
                        (
                            "sample.guid",
                            "Sample",
                            "1.0",
                            "Tester",
                            str(primary_path),
                            "old.zipmod",
                            "old.zipmod",
                            primary_path.stat().st_size,
                            now,
                            now,
                            now,
                            now,
                        ),
                    )
                    zipmod_id = int(cursor.lastrowid)
                    dup_cursor = conn.execute(
                        """
                        INSERT INTO duplicate_zipmods (
                            guid, primary_zipmod_id, file_path, relative_path, file_name,
                            version, author, file_size, modified_at, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "sample.guid",
                            zipmod_id,
                            str(duplicate_path),
                            "new.zipmod",
                            "new.zipmod",
                            "2.0",
                            "Tester",
                            duplicate_path.stat().st_size,
                            now,
                            now,
                            now,
                        ),
                    )
                    duplicate_id = int(dup_cursor.lastrowid)
            finally:
                conn.close()

            result = delete_primary_and_promote_duplicate(
                zipmod_id,
                duplicate_id,
                db_path=db_path,
                thumbnail_dir=root / "thumbs",
            )

            self.assertTrue(result["ok"], result)
            self.assertFalse(primary_path.exists())
            self.assertTrue(duplicate_path.exists())
            self.assertEqual(result["item_count"], 2)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT * FROM zipmods WHERE guid = 'sample.guid'").fetchone()
                self.assertEqual(row["file_path"], str(duplicate_path.resolve()))
                self.assertEqual(row["version"], "2.0")
                self.assertEqual(row["item_count"], 2)
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) FROM duplicate_zipmods WHERE guid = 'sample.guid'").fetchone()[0],
                    0,
                )
            finally:
                conn.close()

    def test_allows_cleanup_when_unity3d_differs_but_completeness_is_safe(self):
        duplicate_ids, reason = bridge.choose_safe_duplicate_cleanup_ids(
            {
                "candidates": [
                    {
                        "role": "primary",
                        "exists": True,
                        "recommendation_reasons": ["most_complete"],
                        "missing_item_count_vs_union": 0,
                        "completeness_score": 20,
                    },
                    {
                        "role": "duplicate",
                        "duplicate_id": 42,
                        "recommendation_reasons": [],
                        "unique_item_count": 0,
                        "completeness_score": 18,
                        "unity3d_safe_against_primary": False,
                    },
                ]
            }
        )

        self.assertEqual(duplicate_ids, [42])
        self.assertEqual(reason, "")

    def test_blocks_cleanup_when_duplicate_has_better_completeness_score(self):
        duplicate_ids, reason = bridge.choose_safe_duplicate_cleanup_ids(
            {
                "candidates": [
                    {
                        "role": "primary",
                        "exists": True,
                        "recommendation_reasons": ["most_complete"],
                        "missing_item_count_vs_union": 0,
                        "completeness_score": 20,
                    },
                    {
                        "role": "duplicate",
                        "duplicate_id": 43,
                        "recommendation_reasons": [],
                        "unique_item_count": 0,
                        "completeness_score": 21,
                    },
                ]
            }
        )

        self.assertEqual(duplicate_ids, [])
        self.assertEqual(reason, "A duplicate has a better completeness score")


if __name__ == "__main__":
    unittest.main()
