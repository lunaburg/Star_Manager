import io
import hashlib
import sqlite3
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import bridge  # noqa: E402
from star_manager.services.mod_database_assets import (  # noqa: E402
    read_manifest,
    update_zipmod_manifest_author,
)
from star_manager.services.mod_database_core import init_db  # noqa: E402
from star_manager.services import mod_database_assets  # noqa: E402


class BulkAuthorUpdateTests(unittest.TestCase):
    def test_bulk_task_skips_rewrite_when_author_already_matches(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path, db_path, thumbnail_dir, zipmod_id = self._create_fixture(root)
            original_bytes = zipmod_path.read_bytes()
            original_stat = zipmod_path.stat()
            original_hash = hashlib.sha256(original_bytes).hexdigest()

            def update_author(identifier, author):
                return update_zipmod_manifest_author(
                    identifier,
                    author,
                    db_path=db_path,
                    thumbnail_dir=thumbnail_dir,
                )

            task = bridge.TaskState(id="author-no-op", task_type="bulk_update_zipmod_authors")
            with patch.object(bridge, "update_zipmod_manifest_author", side_effect=update_author):
                with patch.object(
                    mod_database_assets,
                    "rewrite_zip_members",
                    side_effect=AssertionError("no-op author updates must not rewrite the archive"),
                ):
                    with patch.object(
                        mod_database_assets,
                        "_replace_mod_items",
                        side_effect=AssertionError("no-op author updates must not rescan items"),
                    ):
                        bridge.run_task(
                            task,
                            {"zipmod_ids": [zipmod_id], "author": "Author"},
                        )

            self.assertEqual(task.status, "completed")
            self.assertEqual(task.data["updated_count"], 0)
            self.assertEqual(task.data["unchanged_count"], 1)
            self.assertEqual(task.data["failure_count"], 0)
            self.assertEqual(zipmod_path.read_bytes(), original_bytes)
            self.assertEqual(hashlib.sha256(zipmod_path.read_bytes()).hexdigest(), original_hash)
            self.assertEqual(zipmod_path.stat().st_mtime_ns, original_stat.st_mtime_ns)

    def test_manifest_author_is_preserved_while_stale_database_value_is_repaired(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zipmod_path, db_path, thumbnail_dir, zipmod_id = self._create_fixture(
                root,
                db_author="Stale Author",
            )
            original_bytes = zipmod_path.read_bytes()
            original_stat = zipmod_path.stat()
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO mod_items (
                        zipmod_id, zipmod_guid, zipmod_author, item_id, parse_status,
                        created_at, updated_at
                    ) VALUES (?, 'sample.guid', 'Stale Author', '1', 'ok', 'old', 'old')
                    """,
                    (zipmod_id,),
                )
                conn.commit()
            finally:
                conn.close()

            with patch.object(
                mod_database_assets,
                "rewrite_zip_members",
                side_effect=AssertionError("database reconciliation must not rewrite the archive"),
            ):
                with patch.object(
                    mod_database_assets,
                    "_replace_mod_items",
                    side_effect=AssertionError("database reconciliation must not rescan items"),
                ):
                    result = update_zipmod_manifest_author(
                        zipmod_id,
                        "Author",
                        db_path=db_path,
                        thumbnail_dir=thumbnail_dir,
                    )

            self.assertTrue(result["ok"])
            self.assertTrue(result.get("reconciled", False))
            self.assertFalse(result.get("no_op", False))
            self.assertEqual(read_manifest(zipmod_path).author, "Author")
            self.assertEqual(zipmod_path.read_bytes(), original_bytes)
            self.assertEqual(zipmod_path.stat().st_mtime_ns, original_stat.st_mtime_ns)
            conn = sqlite3.connect(db_path)
            try:
                self.assertEqual(
                    conn.execute("SELECT author FROM zipmods WHERE id = ?", (zipmod_id,)).fetchone()[0],
                    "Author",
                )
                self.assertEqual(
                    conn.execute("SELECT zipmod_author FROM mod_items WHERE zipmod_id = ?", (zipmod_id,)).fetchone()[0],
                    "Author",
                )
            finally:
                conn.close()

    def test_rewrite_preserves_compressed_payloads_with_descriptors_and_zip64(self):
        with TemporaryDirectory() as temp_dir:
            zipmod_path = Path(temp_dir) / "sample.zipmod"
            manifest = (
                b"<manifest><guid>sample.guid</guid><name>Sample</name>"
                b"<version>1</version><author>Author</author></manifest>"
            )
            compressed_payload = (bytes(range(256)) * 4096)
            stored_payload = b"stored resource" * 4096
            buffer = _NonSeekableBuffer()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.comment = b"preserve archive comment"
                archive.writestr("manifest.xml", manifest)
                archive.writestr("abdata/compressed.bin", compressed_payload)
                stored_info = zipfile.ZipInfo("abdata/stored.bin")
                stored_info.compress_type = zipfile.ZIP_STORED
                archive.writestr(stored_info, stored_payload)
                with archive.open("abdata/forced-zip64.bin", "w", force_zip64=True) as target:
                    target.write(b"zip64 payload")
            zipmod_path.write_bytes(buffer.getvalue())

            with zipfile.ZipFile(zipmod_path, "r") as source:
                self.assertTrue(all(info.flag_bits & 0x0008 for info in source.infolist()))
                payloads_before = {
                    name: _compressed_payload(zipmod_path, source.getinfo(name))
                    for name in ("abdata/compressed.bin", "abdata/stored.bin", "abdata/forced-zip64.bin")
                }

            mod_database_assets.rewrite_zip_members(zipmod_path, {"manifest.xml": manifest})

            with zipfile.ZipFile(zipmod_path, "r") as result:
                self.assertIsNone(result.testzip())
                self.assertEqual(result.comment, b"preserve archive comment")
                self.assertTrue(all(not (info.flag_bits & 0x0008) for info in result.infolist()))
                self.assertEqual(result.read("manifest.xml"), manifest)
                self.assertEqual(result.read("abdata/compressed.bin"), compressed_payload)
                self.assertEqual(result.read("abdata/stored.bin"), stored_payload)
                self.assertEqual(result.read("abdata/forced-zip64.bin"), b"zip64 payload")
                for name, payload in payloads_before.items():
                    self.assertEqual(_compressed_payload(zipmod_path, result.getinfo(name)), payload)
            self.assertEqual(read_manifest(zipmod_path).author, "Author")

    def _create_fixture(self, root: Path, db_author: str = "Author"):
        zipmod_path = root / "game" / "mods" / "Author" / "sample.zipmod"
        zipmod_path.parent.mkdir(parents=True)
        with zipfile.ZipFile(zipmod_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "manifest.xml",
                "<manifest><guid>sample.guid</guid><name>Sample</name>"
                "<version>1</version><author>Author</author></manifest>",
            )

        db_path = root / "runtime" / "star_manager.sqlite"
        thumbnail_dir = root / "runtime" / "thumbnails"
        db_path.parent.mkdir(parents=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            init_db(conn)
            now = "2026-01-01T00:00:00+00:00"
            zipmod_id = conn.execute(
                """
                INSERT INTO zipmods (
                    guid, name, version, author, file_path, relative_path, file_name,
                    file_size, scan_status, last_scanned_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ok', ?, ?, ?)
                """,
                (
                    "sample.guid",
                    "Sample",
                    "1",
                    db_author,
                    str(zipmod_path),
                    "Author/sample.zipmod",
                    zipmod_path.name,
                    zipmod_path.stat().st_size,
                    now,
                    now,
                    now,
                ),
            ).lastrowid
            conn.commit()
        finally:
            conn.close()
        return zipmod_path, db_path, thumbnail_dir, int(zipmod_id)


class _NonSeekableBuffer(io.BytesIO):
    def seekable(self):
        return False

    def seek(self, *_args, **_kwargs):
        raise io.UnsupportedOperation("not seekable")


def _compressed_payload(path: Path, info: zipfile.ZipInfo) -> bytes:
    with path.open("rb") as archive:
        archive.seek(info.header_offset)
        header = archive.read(zipfile.sizeFileHeader)
        fields = __import__("struct").unpack(zipfile.structFileHeader, header)
        filename_size, extra_size = fields[-2:]
        data_offset = info.header_offset + zipfile.sizeFileHeader + filename_size + extra_size
        archive.seek(data_offset)
        return archive.read(info.compress_size)


if __name__ == "__main__":
    unittest.main()
