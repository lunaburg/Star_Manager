from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote

from star_manager.core.card_parser import try_unpack_msgpack
from star_manager.services.mod_database_assets import (
    UnityPy,
    UnityThumbnailBundle,
)
from star_manager.services.mod_database_core import (
    DEFAULT_DB_PATH,
    ThumbnailResult,
    init_db,
    utc_now,
)


BUILTIN_LIST_PARSER_VERSION = "1"
BUILTIN_LIST_ROOT = Path("abdata/list/characustom")

CLOTHES_CATEGORY_BY_SLOT = {
    0: "240",
    1: "241",
    2: "242",
    3: "243",
    4: "244",
    5: "245",
    6: "246",
    7: "247",
}
CLOTHES_PROPERTY_BY_SLOT = {
    0: "ChaFileClothes.ClothesTop",
    1: "ChaFileClothes.ClothesBot",
    2: "ChaFileClothes.ClothesBra",
    3: "ChaFileClothes.ClothesShorts",
    4: "ChaFileClothes.ClothesGloves",
    5: "ChaFileClothes.ClothesPanst",
    6: "ChaFileClothes.ClothesSocks",
    7: "ChaFileClothes.ClothesShoes",
}
ACCESSORY_CATEGORY_NOS = {str(value) for value in range(351, 364)}


@dataclass(frozen=True)
class BuiltinItem:
    game_dir_key: str
    game_dir: str
    category_no: str
    item_id: str
    name: str
    name_en: str
    name_zh_cn: str
    name_zh_tw: str
    source_path: str
    source_asset: str
    main_manifest: str
    main_ab: str
    main_data: str
    thumb_ab: str
    thumb_tex: str


def normalize_game_dir_key(game_dir: Path | str) -> str:
    return str(Path(game_dir).resolve()).casefold()


def normalize_item_id(value: object) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        if text.isdigit():
            return str(int(text))
    except (TypeError, ValueError):
        pass
    return text


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8").strip()
        except UnicodeDecodeError:
            return value.decode("utf-8", errors="replace").strip()
    return str(value).strip()


def _display_text(value: object) -> str:
    text = _text(value)
    if text.casefold() in {"0", "none", "null", "-"}:
        return ""
    return text


def _meaningful_reference(value: object) -> str:
    text = _display_text(value)
    return "" if text in {"", "."} else text


def _path_signature(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        stat = path.stat()
    except OSError:
        return "missing"
    return f"{int(stat.st_size)}:{int(stat.st_mtime_ns)}"


def _normalize_abdata_reference(reference: str) -> str:
    normalized = str(reference or "").strip().replace("\\", "/").lstrip("/")
    if not normalized or normalized.casefold() in {"0", "none", "null"}:
        return ""
    if normalized.casefold().startswith("abdata/"):
        return normalized
    return f"abdata/{normalized}"


def _resolve_game_reference(game_dir: Path, reference: str) -> Path | None:
    normalized = _normalize_abdata_reference(reference)
    if not normalized:
        return None
    candidate = (game_dir / normalized).resolve()
    root = game_dir.resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate


def _read_text_asset(obj: object) -> bytes | None:
    try:
        data = obj.read()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - one damaged asset must not stop the scan.
        return None
    script = getattr(data, "m_Script", None)
    if isinstance(script, bytes):
        return script
    if isinstance(script, str):
        # UnityPy exposes binary TextAsset payloads as a string and preserves
        # non-UTF-8 bytes through surrogateescape. Reconstruct the original
        # MessagePack bytes before decoding them with the card parser.
        return script.encode("utf-8", errors="surrogateescape")
    return None


def _decode_list_payload(raw: bytes) -> dict | None:
    decoded = try_unpack_msgpack(raw)
    if not decoded or decoded[1] != len(raw) or not isinstance(decoded[0], dict):
        return None
    payload = decoded[0]
    if "ChaListData" not in _text(payload.get("mark")):
        return None
    if not isinstance(payload.get("lstKey"), list):
        return None
    if not isinstance(payload.get("dictList"), (dict, list)):
        return None
    return payload


def _payload_rows(payload: dict) -> list[list | tuple | dict]:
    raw_rows = payload.get("dictList")
    if isinstance(raw_rows, dict):
        return [row for row in raw_rows.values() if isinstance(row, (list, tuple, dict))]
    return [row for row in raw_rows if isinstance(row, (list, tuple, dict))]


def _row_fields(keys: list, row: list | tuple | dict) -> dict[str, object]:
    if isinstance(row, dict):
        return {_text(key): value for key, value in row.items()}
    return {
        _text(key): row[index]
        for index, key in enumerate(keys)
        if index < len(row)
    }


def _builtin_item_from_row(
    game_dir: Path,
    bundle_path: Path,
    payload: dict,
    fields: dict[str, object],
    source_asset: str,
) -> BuiltinItem | None:
    category_no = normalize_item_id(payload.get("categoryNo"))
    item_id = normalize_item_id(fields.get("ID"))
    if not category_no or not item_id:
        return None

    name = _display_text(fields.get("ZH_CN")) or _display_text(fields.get("ZH_TW"))
    name = name or _display_text(fields.get("EN_US")) or _display_text(fields.get("Name"))
    name = name or f"原版物品 {item_id}"
    try:
        source_path = bundle_path.relative_to(game_dir).as_posix()
    except ValueError:
        source_path = bundle_path.as_posix()
    return BuiltinItem(
        game_dir_key=normalize_game_dir_key(game_dir),
        game_dir=str(game_dir),
        category_no=category_no,
        item_id=item_id,
        name=name,
        name_en=_display_text(fields.get("EN_US")),
        name_zh_cn=_display_text(fields.get("ZH_CN")),
        name_zh_tw=_display_text(fields.get("ZH_TW")),
        source_path=source_path,
        source_asset=_text(payload.get("filePath")) or source_asset,
        main_manifest=_meaningful_reference(fields.get("MainManifest")),
        main_ab=_meaningful_reference(fields.get("MainAB")),
        main_data=_meaningful_reference(fields.get("MainData")),
        thumb_ab=_meaningful_reference(fields.get("ThumbAB")),
        thumb_tex=_meaningful_reference(fields.get("ThumbTex")),
    )


def _read_bundle_items(game_dir: Path, bundle_path: Path) -> list[BuiltinItem]:
    if UnityPy is None:
        raise RuntimeError("UnityPy is not available")
    environment = UnityPy.load(str(bundle_path))
    items: list[BuiltinItem] = []
    try:
        for obj in getattr(environment, "objects", []):
            if _text(getattr(getattr(obj, "type", None), "name", "")) != "TextAsset":
                continue
            raw = _read_text_asset(obj)
            if not raw:
                continue
            payload = _decode_list_payload(raw)
            if payload is None:
                continue
            keys = payload.get("lstKey") or []
            source_asset = _text(getattr(obj, "m_Name", ""))
            for raw_row in _payload_rows(payload):
                fields = _row_fields(keys, raw_row)
                item = _builtin_item_from_row(
                    game_dir,
                    bundle_path,
                    payload,
                    fields,
                    source_asset,
                )
                if item is not None:
                    items.append(item)
    finally:
        del environment
    return items


class _BuiltinThumbnailBundleCache:
    def __init__(self) -> None:
        self._bundles: dict[tuple[str, str], UnityThumbnailBundle | ThumbnailResult] = {}

    def load(self, path: Path) -> UnityThumbnailBundle | ThumbnailResult:
        key = (str(path), _path_signature(path))
        cached = self._bundles.get(key)
        if cached is not None:
            return cached
        if not path.is_file():
            result: UnityThumbnailBundle | ThumbnailResult = ThumbnailResult(
                "", "missing", f"thumbnail source not found: {path}"
            )
            self._bundles[key] = result
            return result
        try:
            result = UnityThumbnailBundle.from_bytes(path.read_bytes())
        except OSError as exc:
            result = ThumbnailResult("", "error", str(exc))
        self._bundles[key] = result
        return result


def _thumbnail_cache_path(thumbnail_dir: Path, item: BuiltinItem) -> Path:
    value = "|".join(
        (
            "builtin",
            item.game_dir_key,
            item.category_no,
            item.item_id,
        )
    )
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return thumbnail_dir / "builtin" / digest[:2] / digest[2:4] / f"{digest}.png"


def _extract_builtin_thumbnail(
    game_dir: Path,
    item: BuiltinItem,
    output_path: Path,
    bundle_cache: _BuiltinThumbnailBundleCache,
) -> ThumbnailResult:
    if not item.thumb_tex:
        return ThumbnailResult("", "missing", "thumbnail reference is empty")

    references: list[str] = []
    for reference in (item.thumb_ab, item.main_ab):
        normalized = _normalize_abdata_reference(reference)
        if normalized and normalized not in references:
            references.append(normalized)
    errors: list[str] = []
    for reference in references:
        source_path = _resolve_game_reference(game_dir, reference)
        if source_path is None or not source_path.is_file():
            errors.append(f"thumbnail source not found: {reference}")
            continue
        bundle = bundle_cache.load(source_path)
        if isinstance(bundle, ThumbnailResult):
            errors.append(bundle.error)
            continue
        result = bundle.write_thumbnail(item.thumb_tex, output_path)
        if result.status == "ready":
            return result
        errors.append(result.error or "thumbnail asset not found")
    return ThumbnailResult("", "missing", "; ".join(errors) or "thumbnail source not found")


def _builtin_source_signature(game_dir: Path, item: BuiltinItem, bundle_path: Path) -> str:
    main_path = _resolve_game_reference(game_dir, item.main_ab)
    thumb_path = _resolve_game_reference(game_dir, item.thumb_ab)
    return "|".join(
        (
            BUILTIN_LIST_PARSER_VERSION,
            _path_signature(bundle_path),
            _path_signature(main_path),
            _path_signature(thumb_path),
            item.category_no,
            item.item_id,
            item.main_ab,
            item.main_data,
            item.thumb_ab,
            item.thumb_tex,
            item.name,
        )
    )


def _resource_status(game_dir: Path, item: BuiltinItem) -> tuple[str, str]:
    if not item.main_ab:
        return "not_applicable", ""
    resource_path = _resolve_game_reference(game_dir, item.main_ab)
    if resource_path is not None and resource_path.is_file():
        return "in_game", ""
    return "missing", f"resource not found: {item.main_ab}"


def _thumbnail_url(cache_path: str, thumbnail_status: str) -> str:
    if not cache_path or thumbnail_status not in {"ready", "ok"}:
        return ""
    return f"/mods/thumbnails?path={quote(cache_path)}"


def build_builtin_items_index(
    conn: sqlite3.Connection,
    game_dir: Path,
    thumbnail_dir: Path,
    progress_callback: Callable[[int, str], None] | None = None,
    mode: str = "incremental",
) -> dict[str, object]:
    """Scan the game's ChaListData bundles and refresh builtin_items."""

    init_db(conn)
    game_dir = game_dir.resolve()
    thumbnail_dir = thumbnail_dir.resolve()
    game_dir_key = normalize_game_dir_key(game_dir)
    list_root = (game_dir / BUILTIN_LIST_ROOT).resolve()
    list_paths = sorted(
        (path for path in list_root.rglob("*.unity3d") if path.is_file())
        if list_root.is_dir()
        else [],
        key=lambda path: path.as_posix().casefold(),
    )
    force_full = str(mode or "incremental").casefold() == "full"
    stats: dict[str, object] = {
        "builtin_list_bundles": len(list_paths),
        "builtin_items": 0,
        "builtin_reused_items": 0,
        "builtin_thumbnail_ready": 0,
        "builtin_thumbnail_missing": 0,
        "builtin_parse_errors": 0,
        "builtin_duplicate_items": 0,
        "builtin_scan_complete": True,
        "builtin_errors": [],
    }
    if not list_paths:
        with conn:
            conn.execute("DELETE FROM builtin_items WHERE game_dir_key = ?", (game_dir_key,))
        return stats

    existing = {
        (str(row["category_no"]), str(row["item_id"])): row
        for row in conn.execute(
            "SELECT * FROM builtin_items WHERE game_dir_key = ?",
            (game_dir_key,),
        )
    }
    seen: set[tuple[str, str]] = set()
    thumbnail_cache = _BuiltinThumbnailBundleCache()
    total = max(len(list_paths), 1)
    now = utc_now()

    with conn:
        for index, bundle_path in enumerate(list_paths, start=1):
            if progress_callback is not None:
                progress_callback(
                    1 + round(index / total * 3, 1),
                    f"Reading original resource lists {index}/{total}",
                )
            try:
                items = _read_bundle_items(game_dir, bundle_path)
            except Exception as exc:  # noqa: BLE001 - retain usable bundles.
                stats["builtin_parse_errors"] = int(stats["builtin_parse_errors"]) + 1
                stats["builtin_scan_complete"] = False
                errors = stats["builtin_errors"]
                if isinstance(errors, list) and len(errors) < 20:
                    errors.append(f"{bundle_path.name}: {exc}")
                continue

            for item in items:
                key = (item.category_no, item.item_id)
                if key in seen:
                    stats["builtin_duplicate_items"] = int(stats["builtin_duplicate_items"]) + 1
                    continue
                seen.add(key)
                source_signature = _builtin_source_signature(game_dir, item, bundle_path)
                previous = existing.get(key)
                previous_cache = str(previous["thumbnail_cache_path"] or "") if previous else ""
                previous_status = str(previous["thumbnail_status"] or "") if previous else ""
                previous_signature = str(previous["source_signature"] or "") if previous else ""
                cache_path = Path(previous_cache) if previous_cache else _thumbnail_cache_path(thumbnail_dir, item)
                thumbnail_result: ThumbnailResult
                can_reuse = (
                    not force_full
                    and previous_signature == source_signature
                    and previous_status in {"ready", "ok"}
                    and cache_path.is_file()
                )
                if can_reuse:
                    thumbnail_result = ThumbnailResult(str(cache_path), "ready", "")
                    stats["builtin_reused_items"] = int(stats["builtin_reused_items"]) + 1
                else:
                    thumbnail_result = _extract_builtin_thumbnail(
                        game_dir,
                        item,
                        cache_path,
                        thumbnail_cache,
                    )
                if thumbnail_result.status == "ready":
                    stats["builtin_thumbnail_ready"] = int(stats["builtin_thumbnail_ready"]) + 1
                    thumbnail_cache_path = str(cache_path)
                else:
                    stats["builtin_thumbnail_missing"] = int(stats["builtin_thumbnail_missing"]) + 1
                    thumbnail_cache_path = ""
                resource_status, resource_error = _resource_status(game_dir, item)
                conn.execute(
                    """
                    INSERT INTO builtin_items (
                        game_dir_key, game_dir, category_no, item_id, name,
                        name_en, name_zh_cn, name_zh_tw, source_path, source_asset,
                        main_manifest, main_ab, main_data, thumb_ab, thumb_tex,
                        thumbnail_cache_path, thumbnail_status, thumbnail_error,
                        resource_status, resource_error, source_signature,
                        parser_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(game_dir_key, category_no, item_id) DO UPDATE SET
                        game_dir = excluded.game_dir,
                        name = excluded.name,
                        name_en = excluded.name_en,
                        name_zh_cn = excluded.name_zh_cn,
                        name_zh_tw = excluded.name_zh_tw,
                        source_path = excluded.source_path,
                        source_asset = excluded.source_asset,
                        main_manifest = excluded.main_manifest,
                        main_ab = excluded.main_ab,
                        main_data = excluded.main_data,
                        thumb_ab = excluded.thumb_ab,
                        thumb_tex = excluded.thumb_tex,
                        thumbnail_cache_path = excluded.thumbnail_cache_path,
                        thumbnail_status = excluded.thumbnail_status,
                        thumbnail_error = excluded.thumbnail_error,
                        resource_status = excluded.resource_status,
                        resource_error = excluded.resource_error,
                        source_signature = excluded.source_signature,
                        parser_version = excluded.parser_version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        item.game_dir_key,
                        item.game_dir,
                        item.category_no,
                        item.item_id,
                        item.name,
                        item.name_en,
                        item.name_zh_cn,
                        item.name_zh_tw,
                        item.source_path,
                        item.source_asset,
                        item.main_manifest,
                        item.main_ab,
                        item.main_data,
                        item.thumb_ab,
                        item.thumb_tex,
                        thumbnail_cache_path,
                        thumbnail_result.status,
                        thumbnail_result.error,
                        resource_status,
                        resource_error,
                        source_signature,
                        BUILTIN_LIST_PARSER_VERSION,
                        str(previous["created_at"] or now) if previous else now,
                        now,
                    ),
                )
                stats["builtin_items"] = int(stats["builtin_items"]) + 1

        if bool(stats["builtin_scan_complete"]):
            current_rows = conn.execute(
                "SELECT category_no, item_id FROM builtin_items WHERE game_dir_key = ?",
                (game_dir_key,),
            ).fetchall()
            stale_keys = [
                (str(row["category_no"]), str(row["item_id"]))
                for row in current_rows
                if (str(row["category_no"]), str(row["item_id"])) not in seen
            ]
            conn.executemany(
                "DELETE FROM builtin_items WHERE game_dir_key = ? AND category_no = ? AND item_id = ?",
                [(game_dir_key, category, item_id) for category, item_id in stale_keys],
            )
    return stats


def _builtin_item_payload(row: sqlite3.Row) -> dict[str, object]:
    thumbnail_status = str(row["thumbnail_status"] or "")
    resource_status = str(row["resource_status"] or "")
    return {
        "id": int(row["id"]),
        "source_type": "builtin",
        "source_mod": "游戏本体",
        "source_label": "游戏本体",
        "game_dir": row["game_dir"],
        "item_id": row["item_id"],
        "kind": row["category_no"],
        "category_no": row["category_no"],
        "name": row["name"],
        "thumbnail_status": thumbnail_status,
        "thumbnail_url": _thumbnail_url(str(row["thumbnail_cache_path"] or ""), thumbnail_status),
        "resource_status": resource_status,
        "status": "ready" if resource_status in {"in_game", "not_applicable"} else "missing",
        "main_ab": row["main_ab"],
        "main_data": row["main_data"],
        "source_path": row["source_path"],
    }


def _normalized_dependency_property(value: object) -> str:
    text = _text(value).casefold()
    if text.startswith("outfit."):
        text = text[len("outfit.") :]
    return text


def _occupied_coordinate_slots(
    dependencies: Iterable[dict[str, object]] | None,
) -> tuple[set[str], set[tuple[str, str]]]:
    """Collect Coordinate slots already claimed by UAR records.

    A sideloader item can leave the vanilla Coordinate ID in the card while
    UAR identifies the replacement mod item separately.  The UAR record is
    authoritative for that logical clothing/accessory slot.
    """
    occupied_categories: set[str] = set()
    occupied_properties: set[tuple[str, str]] = set()
    for dependency in dependencies or []:
        if not isinstance(dependency, dict):
            continue
        category_no = normalize_item_id(
            dependency.get("category_no")
            if dependency.get("category_no") is not None
            else dependency.get("CategoryNo")
        )
        if not category_no:
            continue
        property_name = _normalized_dependency_property(
            dependency.get("property")
            if dependency.get("property") is not None
            else dependency.get("Property")
        )
        if category_no in CLOTHES_CATEGORY_BY_SLOT.values() or not property_name:
            occupied_categories.add(category_no)
        elif category_no in ACCESSORY_CATEGORY_NOS:
            occupied_properties.add((category_no, property_name))
    return occupied_categories, occupied_properties


def resolve_builtin_coordinate_dependencies(
    game_dir: Path | str,
    parsed: dict[str, object],
    db_path: Path = DEFAULT_DB_PATH,
    occupied_dependencies: Iterable[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Resolve original Coordinate ids not already claimed by UAR records."""

    resolved_db = db_path.resolve()
    if not resolved_db.is_file():
        return []
    game_dir_path = Path(game_dir).resolve()
    game_dir_key = normalize_game_dir_key(game_dir_path)
    conn = sqlite3.connect(resolved_db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("SELECT 1 FROM builtin_items LIMIT 1")
    except sqlite3.OperationalError:
        conn.close()
        return []
    dependencies: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    occupied_categories, occupied_properties = _occupied_coordinate_slots(
        occupied_dependencies
    )

    def add(category_no: str, item_id: object, property_name: str) -> None:
        normalized_item_id = normalize_item_id(item_id)
        if not category_no or not normalized_item_id:
            return
        if normalized_item_id == "0":
            return
        normalized_property = _normalized_dependency_property(property_name)
        if (
            category_no in occupied_categories
            or (category_no, normalized_property) in occupied_properties
        ):
            return
        key = (category_no, normalized_item_id, property_name)
        if key in seen:
            return
        row = conn.execute(
            """
            SELECT * FROM builtin_items
            WHERE game_dir_key = ? AND category_no = ? AND item_id = ?
            LIMIT 1
            """,
            (game_dir_key, category_no, normalized_item_id),
        ).fetchone()
        if not row:
            return
        seen.add(key)
        item = _builtin_item_payload(row)
        dependencies.append(
            {
                "id": f"builtin:{game_dir_key}:{category_no}:{normalized_item_id}:{property_name}",
                "source_type": "builtin",
                "source_label": "游戏本体",
                "mod_id": "",
                "name": item["name"],
                "author": "",
                "property": property_name,
                "category_no": category_no,
                "slot": normalized_item_id,
                "local_slot": "",
                "matched": True,
                "zipmod": None,
                "item": item,
                "resolve_status": "builtin_resolved",
            }
        )

    for part in parsed.get("clothes_parts") or []:
        if not isinstance(part, dict):
            continue
        slot = int(part.get("slot") or 0)
        add(
            CLOTHES_CATEGORY_BY_SLOT.get(slot, ""),
            part.get("id"),
            CLOTHES_PROPERTY_BY_SLOT.get(slot, ""),
        )

    for part in parsed.get("accessory_parts") or []:
        if not isinstance(part, dict):
            continue
        category_no = normalize_item_id(part.get("type"))
        if category_no not in ACCESSORY_CATEGORY_NOS:
            continue
        slot = int(part.get("slot") or 0)
        add(
            category_no,
            part.get("id"),
            f"accessory{slot}.ChaFileAccessory.PartsInfo.id",
        )

    conn.close()
    return dependencies
