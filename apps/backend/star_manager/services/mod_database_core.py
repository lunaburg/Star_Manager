from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from star_manager.core.runtime_paths import BACKEND_ROOT, runtime_root

DEFAULT_DB_PATH = runtime_root() / "star_manager.sqlite"
DEFAULT_THUMBNAIL_DIR = runtime_root() / "thumbnails"
VENDOR_DIR = BACKEND_ROOT / ".vendor"
UNKNOWN_AUTHOR = "\u672a\u77e5\u4f5c\u8005"

MOD_ITEMS_COLUMNS = [
    "id",
    "zipmod_id",
    "zipmod_guid",
    "zipmod_author",
    "csv_path",
    "item_id",
    "kind",
    "name",
    "main_manifest",
    "main_ab",
    "main_data",
    "tex_ab",
    "thumb_ab",
    "thumb_tex",
    "thumbnail_cache_path",
    "thumbnail_status",
    "thumbnail_error",
    "unity3d_status",
    "unity3d_source",
    "unity3d_error",
    "parse_status",
    "parse_error",
    "created_at",
    "updated_at",
]


@dataclass(frozen=True)
class ManifestData:
    guid: str
    name: str
    version: str
    author: str
    scan_status: str
    scan_error: str


@dataclass(frozen=True)
class ZipmodCandidate:
    manifest: ManifestData
    path: Path
    relative_path: str
    file_size: int
    modified_at: str


@dataclass(frozen=True)
class CsvItem:
    csv_path: str
    item_id: str
    kind: str
    name: str
    main_manifest: str
    main_ab: str
    main_data: str
    thumb_ab: str
    thumb_tex: str
    parse_status: str
    parse_error: str
    tex_ab: str = ""


@dataclass(frozen=True)
class ThumbnailResult:
    cache_path: str
    status: str
    error: str


@dataclass(frozen=True)
class Unity3dStatus:
    status: str
    error: str
    source: str = ""


@dataclass(frozen=True)
class Unity3dProvider:
    zipmod_path: str
    relative_path: str
    guid: str
    resource_path: str
    member_path: str
    source_kind: str


@dataclass(frozen=True)
class PreparedModItem:
    csv_path: str
    item_id: str
    kind: str
    name: str
    main_manifest: str
    main_ab: str
    main_data: str
    thumb_ab: str
    thumb_tex: str
    thumbnail_cache_path: str
    thumbnail_status: str
    thumbnail_error: str
    unity3d_status: str
    unity3d_error: str
    parse_status: str
    parse_error: str
    unity3d_source: str = ""
    tex_ab: str = ""


@dataclass(frozen=True)
class PreparedZipmodItems:
    items: list[PreparedModItem]
    ok_count: int
    duplicate_items: int
    unity3d_status: str
    unity3d_in_mod_count: int
    unity3d_in_game_count: int
    unity3d_missing_count: int
    unity3d_error: str
    unity3d_not_in_mod_count: int = 0
    unity3d_other_mod_count: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def timestamp_to_utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def mod_items_needs_unique_key_migration(conn: sqlite3.Connection) -> bool:
    for row in conn.execute("PRAGMA index_list(mod_items)"):
        index_name = str(row[1])
        is_unique = int(row[2] or 0) == 1
        if not is_unique:
            continue
        columns = [
            str(index_row[2])
            for index_row in conn.execute(f"PRAGMA index_info({index_name})")
        ]
        return columns != ["zipmod_guid", "kind", "item_id"]
    return True


def migrate_mod_items_unique_key(conn: sqlite3.Connection) -> None:
    if not mod_items_needs_unique_key_migration(conn):
        return

    columns_sql = ", ".join(MOD_ITEMS_COLUMNS)
    conn.executescript(
        """
        CREATE TABLE mod_items_new (
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
            tex_ab TEXT NOT NULL DEFAULT '',
            thumb_ab TEXT NOT NULL DEFAULT '',
            thumb_tex TEXT NOT NULL DEFAULT '',
            thumbnail_cache_path TEXT NOT NULL DEFAULT '',
            thumbnail_status TEXT NOT NULL DEFAULT '',
            thumbnail_error TEXT NOT NULL DEFAULT '',
            unity3d_status TEXT NOT NULL DEFAULT '',
            unity3d_source TEXT NOT NULL DEFAULT '',
            unity3d_error TEXT NOT NULL DEFAULT '',
            parse_status TEXT NOT NULL,
            parse_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(zipmod_guid, kind, item_id)
        );
        """
    )
    conn.execute(
        f"""
        INSERT OR IGNORE INTO mod_items_new ({columns_sql})
        SELECT {columns_sql}
        FROM mod_items
        """
    )
    conn.executescript(
        """
        DROP TABLE mod_items;
        ALTER TABLE mod_items_new RENAME TO mod_items;
        """
    )


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS zipmods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL DEFAULT '',
            version TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL,
            relative_path TEXT NOT NULL DEFAULT '',
            file_name TEXT NOT NULL DEFAULT '',
            file_size INTEGER NOT NULL DEFAULT 0,
            modified_at TEXT NOT NULL DEFAULT '',
            item_count INTEGER NOT NULL DEFAULT 0,
            unity3d_status TEXT NOT NULL DEFAULT '',
            unity3d_not_in_mod_count INTEGER NOT NULL DEFAULT 0,
            unity3d_in_mod_count INTEGER NOT NULL DEFAULT 0,
            unity3d_in_game_count INTEGER NOT NULL DEFAULT 0,
            unity3d_other_mod_count INTEGER NOT NULL DEFAULT 0,
            unity3d_missing_count INTEGER NOT NULL DEFAULT 0,
            unity3d_error TEXT NOT NULL DEFAULT '',
            scan_status TEXT NOT NULL,
            scan_error TEXT NOT NULL DEFAULT '',
            last_scanned_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS mod_items (
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
            tex_ab TEXT NOT NULL DEFAULT '',
            thumb_ab TEXT NOT NULL DEFAULT '',
            thumb_tex TEXT NOT NULL DEFAULT '',
            thumbnail_cache_path TEXT NOT NULL DEFAULT '',
            thumbnail_status TEXT NOT NULL DEFAULT '',
            thumbnail_error TEXT NOT NULL DEFAULT '',
            unity3d_status TEXT NOT NULL DEFAULT '',
            unity3d_source TEXT NOT NULL DEFAULT '',
            unity3d_error TEXT NOT NULL DEFAULT '',
            parse_status TEXT NOT NULL,
            parse_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(zipmod_guid, kind, item_id)
        );

        CREATE TABLE IF NOT EXISTS builtin_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_dir_key TEXT NOT NULL,
            game_dir TEXT NOT NULL,
            category_no TEXT NOT NULL,
            item_id TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            name_en TEXT NOT NULL DEFAULT '',
            name_zh_cn TEXT NOT NULL DEFAULT '',
            name_zh_tw TEXT NOT NULL DEFAULT '',
            source_path TEXT NOT NULL DEFAULT '',
            source_asset TEXT NOT NULL DEFAULT '',
            main_manifest TEXT NOT NULL DEFAULT '',
            main_ab TEXT NOT NULL DEFAULT '',
            main_data TEXT NOT NULL DEFAULT '',
            thumb_ab TEXT NOT NULL DEFAULT '',
            thumb_tex TEXT NOT NULL DEFAULT '',
            thumbnail_cache_path TEXT NOT NULL DEFAULT '',
            thumbnail_status TEXT NOT NULL DEFAULT '',
            thumbnail_error TEXT NOT NULL DEFAULT '',
            resource_status TEXT NOT NULL DEFAULT '',
            resource_error TEXT NOT NULL DEFAULT '',
            source_signature TEXT NOT NULL DEFAULT '',
            parser_version TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(game_dir_key, category_no, item_id)
        );

        CREATE TABLE IF NOT EXISTS duplicate_zipmods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT NOT NULL,
            primary_zipmod_id INTEGER REFERENCES zipmods(id) ON DELETE SET NULL,
            file_path TEXT NOT NULL,
            relative_path TEXT NOT NULL DEFAULT '',
            file_name TEXT NOT NULL DEFAULT '',
            version TEXT NOT NULL DEFAULT '',
            author TEXT NOT NULL DEFAULT '',
            file_size INTEGER NOT NULL DEFAULT 0,
            modified_at TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT 'duplicate_guid',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS character_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            relative_path TEXT NOT NULL DEFAULT '',
            file_name TEXT NOT NULL DEFAULT '',
            card_uid TEXT NOT NULL DEFAULT '',
            chara_name TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            favorite INTEGER NOT NULL DEFAULT 0,
            rating INTEGER NOT NULL DEFAULT 0,
            metadata_file_size INTEGER NOT NULL DEFAULT 0,
            metadata_modified_ns INTEGER NOT NULL DEFAULT 0,
            preview_cache_path TEXT NOT NULL DEFAULT '',
            modified_at TEXT NOT NULL DEFAULT '',
            parse_status TEXT NOT NULL,
            dependency_count INTEGER NOT NULL DEFAULT 0,
            missing_count INTEGER NOT NULL DEFAULT 0,
            last_scanned_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS character_card_dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL REFERENCES character_cards(id) ON DELETE CASCADE,
            mod_id TEXT NOT NULL DEFAULT '',
            category_no TEXT NOT NULL DEFAULT '',
            slot TEXT NOT NULL DEFAULT '',
            local_slot TEXT NOT NULL DEFAULT '',
            zipmod_id INTEGER REFERENCES zipmods(id) ON DELETE SET NULL,
            mod_item_id INTEGER REFERENCES mod_items(id) ON DELETE SET NULL,
            resolve_status TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS database_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS unity3d_provider_archives (
            zipmod_path TEXT PRIMARY KEY,
            relative_path TEXT NOT NULL DEFAULT '',
            guid TEXT NOT NULL DEFAULT '',
            file_size INTEGER NOT NULL DEFAULT 0,
            modified_at TEXT NOT NULL DEFAULT '',
            scan_status TEXT NOT NULL DEFAULT '',
            scan_error TEXT NOT NULL DEFAULT '',
            scanned_at TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS unity3d_providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zipmod_path TEXT NOT NULL,
            resource_key TEXT NOT NULL,
            resource_path TEXT NOT NULL,
            member_path TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT 'file',
            relative_path TEXT NOT NULL DEFAULT '',
            guid TEXT NOT NULL DEFAULT '',
            file_size INTEGER NOT NULL DEFAULT 0,
            modified_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            UNIQUE(zipmod_path, resource_key)
        );

        CREATE INDEX IF NOT EXISTS idx_unity3d_providers_resource_key
            ON unity3d_providers(resource_key);
        CREATE INDEX IF NOT EXISTS idx_unity3d_providers_zipmod_path
            ON unity3d_providers(zipmod_path);

        CREATE TABLE IF NOT EXISTS bepinex_plugin_cache (
            game_dir TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            scanned_at TEXT NOT NULL
        );

        """
    )
    ensure_column(conn, "zipmods", "file_size", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "modified_at", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "zipmods", "unity3d_status", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "zipmods", "unity3d_not_in_mod_count", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "unity3d_in_mod_count", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "unity3d_in_game_count", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "unity3d_other_mod_count", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "unity3d_missing_count", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "zipmods", "unity3d_error", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "thumbnail_cache_path", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "thumbnail_status", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "thumbnail_error", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "tex_ab", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "unity3d_status", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "unity3d_source", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "mod_items", "unity3d_error", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "character_cards", "tags_json", "TEXT NOT NULL DEFAULT '[]'")
    ensure_column(conn, "character_cards", "favorite", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "character_cards", "rating", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "character_cards", "metadata_file_size", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "character_cards", "metadata_modified_ns", "INTEGER NOT NULL DEFAULT 0")
    migrate_mod_items_unique_key(conn)
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_zipmods_file_path ON zipmods(file_path);
        CREATE INDEX IF NOT EXISTS idx_zipmods_guid ON zipmods(guid);
        CREATE INDEX IF NOT EXISTS idx_zipmods_author ON zipmods(author);
        CREATE INDEX IF NOT EXISTS idx_zipmods_scan_status ON zipmods(scan_status);
        CREATE INDEX IF NOT EXISTS idx_zipmods_unity3d_status ON zipmods(unity3d_status);

        CREATE INDEX IF NOT EXISTS idx_mod_items_zipmod_id ON mod_items(zipmod_id);
        CREATE INDEX IF NOT EXISTS idx_mod_items_guid_item ON mod_items(zipmod_guid, item_id);
        CREATE INDEX IF NOT EXISTS idx_mod_items_guid_kind_item ON mod_items(zipmod_guid, kind, item_id);
        CREATE INDEX IF NOT EXISTS idx_mod_items_author ON mod_items(zipmod_author);
        CREATE INDEX IF NOT EXISTS idx_mod_items_kind ON mod_items(kind);
        CREATE INDEX IF NOT EXISTS idx_mod_items_name ON mod_items(name);
        CREATE INDEX IF NOT EXISTS idx_mod_items_name_nocase_id
            ON mod_items(name COLLATE NOCASE, id);
        CREATE INDEX IF NOT EXISTS idx_mod_items_parse_status ON mod_items(parse_status);
        CREATE INDEX IF NOT EXISTS idx_mod_items_unity3d_status ON mod_items(unity3d_status);

        CREATE INDEX IF NOT EXISTS idx_builtin_items_game_category_item
            ON builtin_items(game_dir_key, category_no, item_id);
        CREATE INDEX IF NOT EXISTS idx_builtin_items_name
            ON builtin_items(game_dir_key, name);
        CREATE INDEX IF NOT EXISTS idx_builtin_items_name_nocase_id
            ON builtin_items(game_dir_key, name COLLATE NOCASE, id);
        CREATE INDEX IF NOT EXISTS idx_builtin_items_thumbnail_status
            ON builtin_items(thumbnail_status);

        CREATE INDEX IF NOT EXISTS idx_duplicate_zipmods_guid ON duplicate_zipmods(guid);

        CREATE INDEX IF NOT EXISTS idx_character_cards_file_path ON character_cards(file_path);
        CREATE INDEX IF NOT EXISTS idx_character_cards_relative_path ON character_cards(relative_path);
        CREATE INDEX IF NOT EXISTS idx_character_cards_card_uid ON character_cards(card_uid);
        CREATE INDEX IF NOT EXISTS idx_character_cards_chara_name ON character_cards(chara_name);
        CREATE INDEX IF NOT EXISTS idx_character_cards_parse_status ON character_cards(parse_status);

        CREATE INDEX IF NOT EXISTS idx_character_card_dependencies_card_id ON character_card_dependencies(card_id);
        CREATE INDEX IF NOT EXISTS idx_character_card_dependencies_mod_id ON character_card_dependencies(mod_id);
        CREATE INDEX IF NOT EXISTS idx_character_card_dependencies_zipmod_id ON character_card_dependencies(zipmod_id);
        CREATE INDEX IF NOT EXISTS idx_character_card_dependencies_mod_item_id ON character_card_dependencies(mod_item_id);
        CREATE INDEX IF NOT EXISTS idx_character_card_dependencies_resolve_status ON character_card_dependencies(resolve_status);
        """
    )


def set_database_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO database_metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def get_database_metadata(conn: sqlite3.Connection, key: str) -> str:
    row = conn.execute("SELECT value FROM database_metadata WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else ""


def ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, definition: str
) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})")
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
