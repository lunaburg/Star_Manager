from __future__ import annotations

import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.services.mod_database import build_database  # noqa: E402
from star_manager.services.mod_database import read_items_from_csv  # noqa: E402
from star_manager.services.mod_database import repair_zipmod_unity3d_from_game  # noqa: E402


def write_zipmod(path: Path, guid: str, main_ab: str, include_unity3d: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "manifest.xml",
            f"""
<manifest schema-ver="1">
  <guid>{guid}</guid>
  <name>{guid}</name>
  <version>1.0</version>
  <author>tester</author>
</manifest>
""".strip(),
        )
        zf.writestr(
            "abdata/list/characustom/items.csv",
            "\n".join(
                [
                    "240,,,,,,,,",
                    "meta,,,,,,,,",
                    "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,ThumbAB,ThumbTex",
                    f"1,0,1,{guid},abdata,{main_ab},asset,,",
                ]
            ),
        )
        if include_unity3d:
            zf.writestr(f"abdata/{main_ab}", b"bundle")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="star-manager-unity3d-") as temp_dir:
        root = Path(temp_dir)
        game_dir = root / "game"
        mods_dir = game_dir / "mods"
        game_abdata = game_dir / "abdata" / "author"
        db_path = root / "star_manager.sqlite"
        thumbnail_dir = root / "thumbnails"

        write_zipmod(mods_dir / "in_mod.zipmod", "guid-in-mod", "author/in_mod.unity3d", True)
        write_zipmod(mods_dir / "in_game.zipmod", "guid-in-game", "author/in_game.unity3d", False)
        write_zipmod(mods_dir / "missing.zipmod", "guid-missing", "author/missing.unity3d", False)
        game_abdata.mkdir(parents=True, exist_ok=True)
        (game_abdata / "in_game.unity3d").write_bytes(b"bundle")

        stats = build_database(game_dir, db_path, thumbnail_dir)
        assert stats["mod_items"] == 3, stats

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            item_rows = {
                row["zipmod_guid"]: row["unity3d_status"]
                for row in conn.execute("SELECT zipmod_guid, unity3d_status FROM mod_items")
            }
            zipmod_rows = {
                row["guid"]: (
                    row["unity3d_status"],
                    row["unity3d_in_mod_count"],
                    row["unity3d_in_game_count"],
                    row["unity3d_missing_count"],
                )
                for row in conn.execute(
                    """
                    SELECT guid, unity3d_status, unity3d_in_mod_count,
                           unity3d_in_game_count, unity3d_missing_count
                    FROM zipmods
                    """
                )
            }
        finally:
            conn.close()

        assert item_rows == {
            "guid-in-mod": "in_mod",
            "guid-in-game": "in_game",
            "guid-missing": "missing",
        }, item_rows
        assert zipmod_rows == {
            "guid-in-mod": ("in_mod", 1, 0, 0),
            "guid-in-game": ("in_game", 0, 1, 0),
            "guid-missing": ("missing", 0, 0, 1),
        }, zipmod_rows

        conn = sqlite3.connect(db_path)
        try:
            zipmod_id = conn.execute(
                "SELECT id FROM zipmods WHERE guid = 'guid-in-game'"
            ).fetchone()[0]
        finally:
            conn.close()
        repaired = repair_zipmod_unity3d_from_game(
            zipmod_id,
            "abdata/author/in_game.unity3d",
            db_path,
            thumbnail_dir,
        )
        assert repaired["ok"], repaired
        conn = sqlite3.connect(db_path)
        try:
            status = conn.execute(
                "SELECT unity3d_status FROM zipmods WHERE guid = 'guid-in-game'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert status == "in_mod", status
        with zipfile.ZipFile(mods_dir / "in_game.zipmod", "r") as zf:
            assert "abdata/author/in_game.unity3d" in zf.namelist()

    print("unity3d status checks passed")
    return 0


def test_csv_item_kind_comes_from_list_metadata() -> None:
    mapped_csv = "\n".join(
        [
            "240,,,,,,,,",
            "meta,,,,,,,,",
            "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,ThumbAB,ThumbTex",
            "1,999,1,Allowed Item,abdata,author/item.unity3d,asset,,",
        ]
    ).encode("utf-8")
    mapped_items = read_items_from_csv("abdata/list/mapped.csv", mapped_csv)
    assert len(mapped_items) == 1, mapped_items
    assert mapped_items[0].kind == "240", mapped_items[0]
    assert mapped_items[0].name == "Allowed Item", mapped_items[0]

    unknown_csv = "\n".join(
        [
            "999,,,,,,,,",
            "meta,,,,,,,,",
            "ID,Kind,Possess,Name,MainManifest,MainAB,MainData,ThumbAB,ThumbTex",
            "1,240,1,Skipped Item,abdata,author/item.unity3d,asset,,",
        ]
    ).encode("utf-8")
    unknown_items = read_items_from_csv("abdata/list/unknown.csv", unknown_csv)
    assert len(unknown_items) == 1, unknown_items
    assert unknown_items[0].kind == "999", unknown_items[0]
    assert unknown_items[0].name == "Skipped Item", unknown_items[0]


def test_legacy_database_migration() -> None:
    with tempfile.TemporaryDirectory(prefix="star-manager-legacy-db-") as temp_dir:
        db_path = Path(temp_dir) / "legacy.sqlite"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE zipmods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guid TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL DEFAULT '',
                    version TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL DEFAULT '',
                    file_path TEXT NOT NULL,
                    relative_path TEXT NOT NULL DEFAULT '',
                    file_name TEXT NOT NULL DEFAULT '',
                    item_count INTEGER NOT NULL DEFAULT 0,
                    scan_status TEXT NOT NULL,
                    scan_error TEXT NOT NULL DEFAULT '',
                    last_scanned_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE mod_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    zipmod_id INTEGER NOT NULL REFERENCES zipmods(id) ON DELETE CASCADE,
                    zipmod_guid TEXT NOT NULL,
                    zipmod_author TEXT NOT NULL DEFAULT '',
                    csv_path TEXT NOT NULL DEFAULT '',
                    item_id TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT '',
                    name TEXT NOT NULL DEFAULT '',
                    main_manifest TEXT NOT NULL DEFAULT '',
                    main_ab TEXT NOT NULL DEFAULT '',
                    main_data TEXT NOT NULL DEFAULT '',
                    thumb_ab TEXT NOT NULL DEFAULT '',
                    thumb_tex TEXT NOT NULL DEFAULT '',
                    parse_status TEXT NOT NULL,
                    parse_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(zipmod_guid, item_id)
                );
                """
            )
            conn.row_factory = sqlite3.Row
            from star_manager.services.mod_database import init_db  # noqa: PLC0415

            init_db(conn)
            zipmod_columns = {row["name"] for row in conn.execute("PRAGMA table_info(zipmods)")}
            item_columns = {row["name"] for row in conn.execute("PRAGMA table_info(mod_items)")}
            assert "unity3d_status" in zipmod_columns
            assert "unity3d_status" in item_columns
        finally:
            conn.close()


if __name__ == "__main__":
    test_csv_item_kind_comes_from_list_metadata()
    test_legacy_database_migration()
    raise SystemExit(main())
