from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import re
import sqlite3
from typing import Any

from star_manager.core.zipmod_utils import is_hs2_game_dir
from star_manager.services.mod_database_core import DEFAULT_DB_PATH, init_db, utc_now

try:
    import dnfile
except ImportError:  # pragma: no cover - reported through the API
    dnfile = None


SCAN_AREAS = (("plugin", "Plugins"),)


def _plugin_source_fingerprint(bepinex_root: Path) -> str:
    files: list[Path] = []
    for folder, pattern in ((bepinex_root / "Plugins", "*.dll"), (bepinex_root / "config", "*.cfg"), (bepinex_root / "Translation", "*.txt")):
        if folder.is_dir():
            files.extend(folder.rglob(pattern))
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: str(item).casefold()):
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = str(path.relative_to(bepinex_root)).replace("\\", "/")
        digest.update(f"{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode("utf-8"))
    return digest.hexdigest()


def _open_cache_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _read_plugin_cache(db_path: Path, game_dir: str, fingerprint: str) -> tuple[dict[str, Any], str] | None:
    try:
        with _open_cache_database(db_path) as conn:
            row = conn.execute("SELECT payload_json, scanned_at FROM bepinex_plugin_cache WHERE game_dir = ? AND fingerprint = ?", (game_dir, fingerprint)).fetchone()
        if not row:
            return None
        return json.loads(str(row["payload_json"])), str(row["scanned_at"])
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        return None


def _write_plugin_cache(db_path: Path, game_dir: str, fingerprint: str, payload: dict[str, Any]) -> str:
    scanned_at = utc_now()
    with _open_cache_database(db_path) as conn:
        conn.execute(
            """INSERT INTO bepinex_plugin_cache (game_dir, fingerprint, payload_json, scanned_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(game_dir) DO UPDATE SET fingerprint=excluded.fingerprint, payload_json=excluded.payload_json, scanned_at=excluded.scanned_at""",
            (game_dir, fingerprint, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), scanned_at),
        )
    return scanned_at


def _filter_plugin_payload(payload: dict[str, Any], search: str, category: str, offset: int, limit: int, *, cached: bool, scanned_at: str) -> dict[str, Any]:
    plugins = payload.get("items") or []
    needle = search.strip().lower()
    filtered = [item for item in plugins if (not category or category == "all" or item["category"] == category) and (not needle or needle in " ".join(str(item.get(key) or "") for key in ("name", "plugin_guid", "assembly_name", "relative_path")).lower())]
    offset = max(0, offset)
    limit = max(1, min(1000, limit))
    return {"ok": True, "data": {**payload, "cached": cached, "scanned_at": scanned_at, "total": len(filtered), "offset": offset, "limit": limit, "items": filtered[offset : offset + limit]}}


@dataclass
class AssemblyMetadata:
    assembly_name: str = ""
    assembly_version: str = ""
    plugin_guid: str = ""
    plugin_name: str = ""
    plugin_version: str = ""
    description: str = ""
    dependencies: list[dict[str, str]] = field(default_factory=list)
    processes: list[str] = field(default_factory=list)
    incompatibilities: list[str] = field(default_factory=list)
    assembly_references: list[str] = field(default_factory=list)


def _value(value: Any, default: Any = "") -> Any:
    return getattr(value, "value", value) if value is not None else default


def _heap_string(value: Any) -> str:
    raw = _value(value, "")
    return str(raw or "")


def _compressed_uint(blob: bytes, offset: int) -> tuple[int, int]:
    first = blob[offset]
    if first & 0x80 == 0:
        return first, offset + 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | blob[offset + 1], offset + 2
    return ((first & 0x1F) << 24) | (blob[offset + 1] << 16) | (blob[offset + 2] << 8) | blob[offset + 3], offset + 4


def _read_ser_strings(blob: bytes) -> list[str]:
    if len(blob) < 2 or blob[:2] != b"\x01\x00":
        return []
    values: list[str] = []
    offset = 2
    while offset < len(blob):
        if blob[offset] == 0xFF:
            values.append("")
            offset += 1
            continue
        try:
            length, start = _compressed_uint(blob, offset)
            end = start + length
            if end > len(blob):
                break
            text = blob[start:end].decode("utf-8")
            if not text or any(ord(char) < 0x20 for char in text):
                break
            values.append(text)
            offset = end
        except (IndexError, UnicodeDecodeError):
            break
    return values


def _attribute_type_name(row: Any) -> str:
    constructor = getattr(row, "Type", None)
    constructor_row = getattr(constructor, "row", None)
    owner = getattr(constructor_row, "Class", None)
    owner_row = getattr(owner, "row", None)
    return _heap_string(getattr(owner_row, "TypeName", ""))


def _blob_bytes(value: Any) -> bytes:
    raw = _value(value, b"")
    return bytes(raw) if isinstance(raw, (bytes, bytearray)) else b""


def read_dotnet_metadata(path: Path) -> AssemblyMetadata:
    if dnfile is None:
        raise RuntimeError("缺少 dnfile，无法解析 .NET DLL 元数据")
    pe = dnfile.dnPE(str(path), fast_load=False)
    try:
        if not getattr(pe, "net", None):
            raise ValueError("不是 .NET 程序集")
        result = AssemblyMetadata()
        tables = pe.net.mdtables
        assembly_rows = getattr(getattr(tables, "Assembly", None), "rows", []) or []
        if assembly_rows:
            row = assembly_rows[0]
            result.assembly_name = _heap_string(row.Name)
            result.assembly_version = f"{row.MajorVersion}.{row.MinorVersion}.{row.BuildNumber}.{row.RevisionNumber}"
        for row in getattr(getattr(tables, "AssemblyRef", None), "rows", []) or []:
            name = _heap_string(row.Name)
            if name and name not in result.assembly_references:
                result.assembly_references.append(name)
        for row in getattr(getattr(tables, "CustomAttribute", None), "rows", []) or []:
            name = _attribute_type_name(row)
            if name not in {"BepInPlugin", "BepInDependency", "BepInProcess", "BepInIncompatibility", "AssemblyDescriptionAttribute"}:
                continue
            strings = _read_ser_strings(_blob_bytes(row.Value))
            if name == "BepInPlugin" and len(strings) >= 3:
                result.plugin_guid, result.plugin_name, result.plugin_version = strings[:3]
            elif name == "BepInDependency" and strings:
                result.dependencies.append({"guid": strings[0], "minimum_version": strings[1] if len(strings) > 1 else ""})
            elif name == "BepInProcess" and strings:
                result.processes.append(strings[0])
            elif name == "BepInIncompatibility" and strings:
                result.incompatibilities.append(strings[0])
            elif name == "AssemblyDescriptionAttribute" and strings:
                result.description = strings[0]
        return result
    finally:
        close = getattr(pe, "close", None)
        if close:
            close()


PLUGIN_DESCRIPTION_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "plugin_descriptions.json"


def load_plugin_descriptions(path: Path = PLUGIN_DESCRIPTION_CATALOG_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    catalog = payload.get("catalog")
    rules = payload.get("inference_rules")
    fallbacks = payload.get("fallbacks")
    if not isinstance(catalog, dict) or not isinstance(rules, list) or not isinstance(fallbacks, dict):
        return {}
    return {
        "catalog": {
        str(key).strip().casefold(): str(description).strip()
        for key, description in catalog.items()
        if str(key).strip() and str(description).strip()
        },
        "inference_rules": [
            (tuple(str(keyword).casefold() for keyword in rule.get("keywords", []) if str(keyword).strip()), str(rule.get("description") or "").strip())
            for rule in rules
            if isinstance(rule, dict) and isinstance(rule.get("keywords"), list) and str(rule.get("description") or "").strip()
        ],
        "fallbacks": {str(key): str(description).strip() for key, description in fallbacks.items() if str(description).strip()},
    }


PLUGIN_DESCRIPTION_DATA = load_plugin_descriptions()
PLUGIN_DESCRIPTIONS = PLUGIN_DESCRIPTION_DATA.get("catalog", {})
DESCRIPTION_RULES = PLUGIN_DESCRIPTION_DATA.get("inference_rules", [])
DESCRIPTION_FALLBACKS = PLUGIN_DESCRIPTION_DATA.get("fallbacks", {})


def describe_plugin(metadata: AssemblyMetadata, path: Path, category: str) -> tuple[str, str]:
    identity = " ".join((metadata.plugin_name, metadata.plugin_guid, metadata.assembly_name, path.stem)).lower()
    compact = "".join(char for char in identity if char.isalnum())
    for key, description in PLUGIN_DESCRIPTIONS.items():
        if key in compact:
            return description, "catalog"
    if metadata.description.strip():
        return metadata.description.strip(), "assembly"
    for keywords, description in DESCRIPTION_RULES:
        if any(keyword in identity for keyword in keywords):
            return description, "inferred"
    fallback = DESCRIPTION_FALLBACKS.get(category) or DESCRIPTION_FALLBACKS.get("plugin") or ""
    return fallback, "generic"


def _normalize_identity(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _read_support_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def build_support_index(bepinex_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for kind, folder, pattern in (("config", bepinex_root / "config", "*.cfg"), ("translation", bepinex_root / "Translation", "*.txt")):
        if not folder.is_dir():
            continue
        for path in folder.rglob(pattern):
            text = _read_support_text(path)
            if not text:
                continue
            records.append({
                "kind": kind,
                "path": path,
                "relative_path": str(path.relative_to(bepinex_root.parent)).replace("\\", "/"),
                "stem": _normalize_identity(path.stem),
                "text": text,
                "normalized_text": _normalize_identity(text),
            })
    return records


def _matching_support_files(metadata: AssemblyMetadata, path: Path, support_index: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identities = {
        _normalize_identity(value)
        for value in (metadata.plugin_guid, metadata.plugin_name, metadata.assembly_name, path.stem)
        if len(_normalize_identity(value)) >= 5
    }
    matches = []
    for record in support_index:
        if any(identity == record["stem"] or identity in record["normalized_text"] for identity in identities):
            matches.append(record)
    return matches


def _translation_map(records: list[dict[str, Any]]) -> dict[str, str]:
    translations: dict[str, str] = {}
    for record in records:
        if record["kind"] != "translation":
            continue
        for raw_line in record["text"].splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//") or "=" not in line:
                continue
            source, translated = line.split("=", 1)
            source = re.sub(r"\{\{.*?\}\}|[▲▼]", "", source).strip()
            translated = re.sub(r"\{\{.*?\}\}|[▲▼]|\\n.*$", "", translated).strip()
            if source and translated:
                translations[source.casefold()] = translated
    return translations


def describe_from_support_files(metadata: AssemblyMetadata, path: Path, support_index: list[dict[str, Any]]) -> tuple[str, str, str, list[str]] | None:
    matches = _matching_support_files(metadata, path, support_index)
    configs = [record for record in matches if record["kind"] == "config"]
    translations = [record for record in matches if record["kind"] == "translation"]
    if not configs:
        return None
    translated = _translation_map(translations)
    setting_names: list[str] = []
    restart_required = False
    for record in configs:
        for raw_line in record["text"].splitlines():
            line = raw_line.strip()
            if "restart" in line.casefold():
                restart_required = True
            if not line or line.startswith(("#", "[")) or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            display = translated.get(key.casefold(), key)
            if display and display not in setting_names:
                setting_names.append(display)
    plugin_label = ""
    identity = _normalize_identity(metadata.plugin_name or metadata.plugin_guid or path.stem)
    for value in translated.values():
        clean = value.strip("▲▼ ")
        if "插件" in clean and (identity in _normalize_identity(clean) or not plugin_label):
            plugin_label = clean
    subject = plugin_label or metadata.plugin_name or path.stem
    if setting_names:
        description = f"{subject}，可配置{'、'.join(setting_names[:5])}。"
    else:
        description = f"{subject}；配置文件提供了可调整的插件选项。"
    if restart_required:
        description += "部分设置需要重启游戏后生效。"
    source = "config+translation" if translations else "config"
    confidence = "high" if translations and setting_names else "medium"
    evidence = [record["relative_path"] for record in matches]
    return description, source, confidence, evidence


def _scan_file(game_root: Path, path: Path, category: str, support_index: list[dict[str, Any]]) -> dict[str, Any]:
    stat = path.stat()
    record: dict[str, Any] = {
        "id": str(path.relative_to(game_root)).replace("\\", "/").lower(),
        "name": path.stem,
        "category": category,
        "relative_path": str(path.relative_to(game_root)).replace("\\", "/"),
        "file_path": str(path),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "metadata_status": "ok",
        "metadata_error": "",
    }
    try:
        metadata = read_dotnet_metadata(path)
        description, description_source = describe_plugin(metadata, path, category)
        support_description = describe_from_support_files(metadata, path, support_index)
        description_confidence = "high" if description_source in {"assembly", "catalog"} else "low"
        description_evidence: list[str] = []
        if support_description and description_source not in {"assembly", "catalog"}:
            description, description_source, description_confidence, description_evidence = support_description
        record.update({
            "assembly_name": metadata.assembly_name,
            "assembly_version": metadata.assembly_version,
            "plugin_guid": metadata.plugin_guid,
            "plugin_name": metadata.plugin_name,
            "plugin_version": metadata.plugin_version,
            "description": description,
            "description_source": description_source,
            "description_confidence": description_confidence,
            "description_evidence": description_evidence,
            "dependencies": metadata.dependencies,
            "processes": metadata.processes,
            "incompatibilities": metadata.incompatibilities,
            "assembly_references": metadata.assembly_references,
        })
        if metadata.plugin_name:
            record["name"] = metadata.plugin_name
    except Exception as error:  # one malformed DLL must not abort the library scan
        record.update({"metadata_status": "error", "metadata_error": str(error), "description": DESCRIPTION_FALLBACKS.get("metadata_error", ""), "description_source": "error", "description_confidence": "none", "description_evidence": [], "dependencies": [], "processes": [], "incompatibilities": [], "assembly_references": []})
    return record


def scan_bepinex_plugins(game_dir: str, *, search: str = "", category: str = "", offset: int = 0, limit: int = 500, refresh: bool = False, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    root = Path(game_dir).expanduser().resolve()
    if not is_hs2_game_dir(str(root)):
        return {"ok": False, "error": "请选择有效的 HS2 游戏目录"}
    bepinex_root = root / "BepInEx"
    if not bepinex_root.is_dir():
        return {"ok": False, "error": "所选游戏目录中不存在 BepInEx 文件夹"}

    game_identity = str(root).casefold()
    fingerprint = _plugin_source_fingerprint(bepinex_root)
    if not refresh:
        cached_result = _read_plugin_cache(db_path, game_identity, fingerprint)
        if cached_result:
            cached_payload, cached_at = cached_result
            return _filter_plugin_payload(cached_payload, search, category, offset, limit, cached=True, scanned_at=cached_at)

    plugins: list[dict[str, Any]] = []
    support_index = build_support_index(bepinex_root)
    for area_category, folder_name in SCAN_AREAS:
        folder = bepinex_root / folder_name
        if folder.is_dir():
            plugins.extend(_scan_file(root, path, area_category, support_index) for path in sorted(folder.rglob("*.dll"), key=lambda item: str(item).lower()))

    # A DLL in Plugins is not necessarily a BepInEx plugin. Only assemblies with
    # a successfully parsed BepInPlugin attribute and GUID belong in this library.
    plugins = [plugin for plugin in plugins if str(plugin.get("plugin_guid") or "").strip()]

    guid_counts: dict[str, int] = {}
    for plugin in plugins:
        guid = str(plugin.get("plugin_guid") or "").lower()
        if guid:
            guid_counts[guid] = guid_counts.get(guid, 0) + 1
    for plugin in plugins:
        guid = str(plugin.get("plugin_guid") or "").lower()
        plugin["status"] = "duplicate" if guid and guid_counts.get(guid, 0) > 1 else ("unreadable" if plugin["metadata_status"] == "error" else "ready")

    summary = {
        "total": len(plugins),
        "plugins": sum(item["category"] == "plugin" for item in plugins),
        "patchers": sum(item["category"] == "patcher" for item in plugins),
        "core": sum(item["category"] == "core" for item in plugins),
        "metadata_errors": sum(item["metadata_status"] == "error" for item in plugins),
        "duplicates": sum(item["status"] == "duplicate" for item in plugins),
        "described": sum(bool(item.get("description")) and item.get("description_source") != "generic" for item in plugins),
        "with_dependencies": sum(bool(item.get("dependencies")) for item in plugins),
    }
    payload = {"bepinex_path": str(bepinex_root), "summary": summary, "items": plugins}
    scanned_at = _write_plugin_cache(db_path, game_identity, fingerprint, payload)
    return _filter_plugin_payload(payload, search, category, offset, limit, cached=False, scanned_at=scanned_at)
