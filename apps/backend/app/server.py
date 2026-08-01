from __future__ import annotations

import email.utils
import base64
import binascii
import json
import mimetypes
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from bridge import SUPPORTED_TASK_TYPES, create_health_payload, task_store
from star_manager.core.coordinate_card import find_png_end
from star_manager.services.achievements import (
    achievement_status,
    record_achievement_event,
    reset_achievements,
    update_achievement_preferences,
)
from star_manager.services.card_database import card_database_status
from star_manager.services.card_library import (
    DEFAULT_CARD_PREVIEW_DIR,
    build_character_card_tree,
    create_character_card_directory,
    export_character_card_coordinate,
    get_character_card_detail,
    get_card_root,
    list_character_cards,
    list_character_card_tags,
    normalize_card_preview,
    replace_character_card_cover,
    rename_character_card_directory,
    resolve_card_file,
    set_character_card_as_navi,
    set_character_card_favorite,
    set_character_card_rating,
    set_character_card_tags,
    update_character_card_profile,
)
from star_manager.services.mod_database import (
    DEFAULT_THUMBNAIL_DIR,
    analyze_duplicate_zipmods,
    assess_database_changes,
    database_status,
    export_item_fbx,
    export_zipmod_item_thumbnail,
    import_zipmod_item_thumbnail,
    cleanup_duplicate_zipmods,
    delete_mod_item,
    delete_primary_and_promote_duplicate,
    delete_zipmod,
    get_zipmod_manifest,
    list_mod_item_filters,
    list_mod_items,
    list_zipmod_authors,
    list_zipmods,
    merge_duplicate_zipmod,
    repair_zipmod_unity3d_from_game,
    resolve_thumbnail_cache_path,
    prepare_item_model_preview,
    resolve_mannequin_model_file,
    resolve_model_preview_file,
    update_zipmod_manifest,
    update_zipmod_manifest_author,
    zipmod_unity3d_diagnostics,
)
from star_manager.services.plugin_library import scan_bepinex_plugins
from star_manager.services.sims4_workbench import export_sims4_package_lod0_fbx


def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return str(pid) in result.stdout

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_parent_watchdog(server: ThreadingHTTPServer) -> None:
    raw_parent_pid = os.environ.get("STAR_MANAGER_PARENT_PID", "")
    try:
        parent_pid = int(raw_parent_pid)
    except ValueError:
        return

    if parent_pid <= 0:
        return

    def watch_parent() -> None:
        while True:
            time.sleep(1)
            if not is_process_alive(parent_pid):
                print(f"Parent process {parent_pid} exited; stopping backend", flush=True)
                server.shutdown()
                return

    threading.Thread(target=watch_parent, name="parent-watchdog", daemon=True).start()


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        route = parsed_url.path
        if route == "/health":
            self.send_json(create_health_payload())
            return

        if route == "/mods/database":
            self.send_json({"ok": True, "database": database_status()})
            return

        if route.startswith("/mods/models/"):
            model_path = resolve_model_preview_file(route.removeprefix("/mods/models/"))
            if model_path is None:
                self.send_json({"ok": False, "error": "Model preview not found"}, status=404)
            else:
                self.send_file(str(model_path), model_path.parent.parent)
            return

        if route == "/mods/mannequin/body.fbx":
            mannequin_path = resolve_mannequin_model_file()
            if mannequin_path is None:
                self.send_json({"ok": False, "error": "Mannequin model not found"}, status=404)
            else:
                self.send_file(str(mannequin_path), mannequin_path.parent)
            return

        if route == "/achievements":
            self.send_json(achievement_status())
            return

        if route == "/mods/database/changes":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            self.send_json({"ok": True, "data": assess_database_changes(game_dir)})
            return

        if route == "/cards/database":
            self.send_json({"ok": True, "database": card_database_status()})
            return

        if route == "/plugins":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            result = scan_bepinex_plugins(
                game_dir,
                search=(query.get("search") or [""])[0],
                category=(query.get("category") or [""])[0],
                offset=self.parse_int_query(query, "offset", 0),
                limit=self.parse_int_query(query, "limit", 500),
                refresh=(query.get("refresh") or [""])[0].lower() in {"1", "true", "yes"},
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/mods/zipmods":
            query = parse_qs(parsed_url.query)
            offset = self.parse_int_query(query, "offset", 0)
            limit = self.parse_int_query(query, "limit", 200)
            author = query.get("author", [""])[0]
            status = query.get("status", [""])[0]
            usage = query.get("usage", [""])[0]
            zipmod_id = self.parse_int_query(query, "zipmod_id", 0)
            self.send_json({
                "ok": True,
                "data": list_zipmods(
                    offset=offset,
                    limit=limit,
                    author=author,
                    status=status,
                    usage=usage,
                    zipmod_id=zipmod_id,
                ),
            })
            return

        if route == "/mods/zipmods/authors":
            self.send_json({"ok": True, "data": list_zipmod_authors()})
            return

        if route == "/mods/items/filters":
            self.send_json({"ok": True, "data": list_mod_item_filters()})
            return

        if route == "/mods/items":
            query = parse_qs(parsed_url.query)
            offset = self.parse_int_query(query, "offset", 0)
            limit = self.parse_int_query(query, "limit", 500)
            zipmod_id = self.parse_optional_int_query(query, "zipmod_id")
            search = query.get("search", [""])[0]
            kind = query.get("kind", [""])[0]
            author = query.get("author", [""])[0]
            status = query.get("status", [""])[0]
            usage = query.get("usage", [""])[0]
            self.send_json({
                "ok": True,
                "data": list_mod_items(
                    offset=offset,
                    limit=limit,
                    zipmod_id=zipmod_id,
                    search=search,
                    kind=kind,
                    author=author,
                    status=status,
                    usage=usage,
                ),
            })
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/diagnostics"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/diagnostics")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = zipmod_unity3d_diagnostics(zipmod_id)
            self.send_json(result, status=200 if result.get("ok") else 404)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/duplicate-analysis"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/duplicate-analysis")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = analyze_duplicate_zipmods(zipmod_id)
            self.send_json(result, status=200 if result.get("ok") else 404)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/manifest"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/manifest")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = get_zipmod_manifest(zipmod_id)
            self.send_json(result, status=200 if result.get("ok") else 404)
            return

        if route == "/mods/thumbnails":
            query = parse_qs(parsed_url.query)
            thumbnail_path = unquote((query.get("path") or [""])[0])
            resolved_thumbnail = resolve_thumbnail_cache_path(thumbnail_path, DEFAULT_THUMBNAIL_DIR)
            if not resolved_thumbnail:
                self.send_json({"ok": False, "error": "File not found"}, status=404)
                return
            self.send_file(str(resolved_thumbnail), DEFAULT_THUMBNAIL_DIR)
            return

        if route == "/library/cards/tree":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            self.send_json(build_character_card_tree(game_dir))
            return

        if route == "/library/cards":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            relative_path = unquote((query.get("path") or [""])[0])
            scope = unquote((query.get("scope") or ["directory"])[0])
            tag = unquote((query.get("tag") or [""])[0])
            try:
                self.send_json(
                    list_character_cards(
                        game_dir,
                        relative_path,
                        recursive=scope == "library" and bool(tag.strip()),
                        tag=tag,
                    )
                )
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            return

        if route == "/library/cards/tags":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            result = list_character_card_tags(game_dir)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/detail":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            relative_path = unquote((query.get("path") or [""])[0])
            try:
                result = get_character_card_detail(game_dir, relative_path)
                self.send_json(result, status=200 if result.get("ok") else 404)
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            return

        if route == "/library/cards/image":
            query = parse_qs(parsed_url.query)
            game_dir = unquote((query.get("game_dir") or [""])[0])
            relative_path = unquote((query.get("path") or [""])[0])
            original_cover = (query.get("original") or [""])[0] == "1"
            root = get_card_root(game_dir)
            try:
                card_path = resolve_card_file(root, relative_path)
                if original_cover:
                    stat = card_path.stat()
                    card_data = card_path.read_bytes()
                    png_end = find_png_end(card_data)
                    self.send_bytes(
                        card_data[:png_end],
                        "image/png",
                        etag=f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}-cover-{png_end:x}"',
                        modified_at=stat.st_mtime,
                    )
                    return
                preview_path = normalize_card_preview(card_path)
                allowed_root = DEFAULT_CARD_PREVIEW_DIR if preview_path != card_path else root
                self.send_file(str(preview_path), allowed_root)
            except (OSError, ValueError) as error:
                self.send_json({"ok": False, "error": str(error)}, status=404)
            return

        if route == "/tasks":
            self.send_json({"ok": True, "tasks": task_store.list_tasks()})
            return

        if route.startswith("/tasks/"):
            task_id = route.removeprefix("/tasks/")
            task = task_store.get_task(task_id)
            if task is None:
                self.send_json({"ok": False, "error": f"Task not found: {task_id}"}, status=404)
                return
            self.send_json({"ok": True, "task": task.to_dict()})
            return

        self.send_json({"ok": False, "error": f"Unknown route: {route}"}, status=404)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        body = self.read_json_body()

        if route == "/tools/sims4/package-fbx":
            result = export_sims4_package_lod0_fbx(
                str(body.get("package_path") or ""),
                str(body.get("target_dir") or ""),
                str(body.get("blender_executable_path") or ""),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/set-navi":
            result = set_character_card_as_navi(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                str(body.get("slot") or ""),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/folders/create":
            result = create_character_card_directory(
                str(body.get("game_dir") or ""),
                str(body.get("parent_path") or ""),
                str(body.get("name") or ""),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/folders/rename":
            result = rename_character_card_directory(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                str(body.get("name") or ""),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/set-favorite":
            result = set_character_card_favorite(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                bool(body.get("favorite")),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/set-rating":
            result = set_character_card_rating(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                body.get("rating"),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/set-tags":
            result = set_character_card_tags(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                body.get("tags"),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/export-coordinate":
            result = export_character_card_coordinate(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                str(body.get("name") or ""),
                str(body.get("output_dir") or ""),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/update-profile":
            result = update_character_card_profile(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                body.get("profile") or {},
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/library/cards/replace-cover":
            result = replace_character_card_cover(
                str(body.get("game_dir") or ""),
                str(body.get("path") or ""),
                str(body.get("image_path") or ""),
                body.get("crop"),
            )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route == "/tasks":
            task_type = body.get("task_type", "")
            payload = body.get("payload") or {}
            if task_type not in SUPPORTED_TASK_TYPES:
                self.send_json({"ok": False, "error": f"Unsupported task type: {task_type}"}, status=400)
                return
            task = task_store.create_task(task_type, payload)
            self.send_json({"ok": True, "task": task.to_dict()})
            return

        if route == "/achievements/preferences":
            self.send_json(update_achievement_preferences(body))
            return

        if route == "/achievements/reset":
            self.send_json(reset_achievements())
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/repair-unity3d"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/repair-unity3d")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            reference_path = str(body.get("path") or "")
            result = repair_zipmod_unity3d_from_game(zipmod_id, reference_path)
            if result.get("ok"):
                repair_count = len(result.get("moved") or []) + len(result.get("copied") or [])
                record_achievement_event("repairs", repair_count, f"unity3d:{zipmod_id}:{reference_path}")
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/items/") and route.endswith("/import-thumbnail"):
            item_id = self.parse_route_int(route, "/mods/items/", "/import-thumbnail")
            if item_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            image_path = str(body.get("image_path") or "")
            image_data = str(body.get("image_data") or "")
            temporary_path = None
            if image_data:
                try:
                    prefix = "data:image/png;base64,"
                    if not image_data.startswith(prefix) or len(image_data) > 3_000_000:
                        raise ValueError("截图数据不是有效的 PNG")
                    decoded = base64.b64decode(image_data[len(prefix) :], validate=True)
                    if len(decoded) > 2_000_000 or not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                        raise ValueError("截图数据不是有效的 PNG")
                    upload_dir = DEFAULT_THUMBNAIL_DIR.parent / "thumbnail_uploads"
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    temporary_path = upload_dir / f"preview-{uuid.uuid4().hex}.png"
                    temporary_path.write_bytes(decoded)
                    image_path = str(temporary_path)
                except (ValueError, binascii.Error, OSError) as error:
                    self.send_json({"ok": False, "error": str(error)}, status=400)
                    return
            try:
                result = import_zipmod_item_thumbnail(item_id, image_path)
            finally:
                if temporary_path is not None:
                    try:
                        temporary_path.unlink(missing_ok=True)
                    except OSError:
                        pass
            if result.get("ok"):
                record_achievement_event("repairs", 1, f"thumbnail:{item_id}:{result.get('image_path', '')}")
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/items/") and route.endswith("/model-preview"):
            item_id = self.parse_route_int(route, "/mods/items/", "/model-preview")
            if item_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = prepare_item_model_preview(item_id)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/items/") and route.endswith("/export-fbx"):
            item_id = self.parse_route_int(route, "/mods/items/", "/export-fbx")
            if item_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = export_item_fbx(item_id, str(body.get("target_dir") or ""))
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/items/") and route.endswith("/export-thumbnail"):
            item_id = self.parse_route_int(route, "/mods/items/", "/export-thumbnail")
            if item_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            target_dir = str(body.get("target_dir") or "")
            result = export_zipmod_item_thumbnail(item_id, target_dir)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/items/") and route.endswith("/delete"):
            item_id = self.parse_route_int(route, "/mods/items/", "/delete")
            if item_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = delete_mod_item(item_id)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/update-author"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/update-author")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            author = str(body.get("author") or "")
            result = update_zipmod_manifest_author(zipmod_id, author)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/manifest"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/manifest")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            fields = {
                key: value
                for key, value in (body.get("fields") or {}).items()
                if key in {"name", "version", "author"}
            }
            result = update_zipmod_manifest(zipmod_id, fields)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/cleanup-duplicates"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/cleanup-duplicates")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            duplicate_ids = body.get("duplicate_ids")
            if duplicate_ids is not None and not isinstance(duplicate_ids, list):
                self.send_json({"ok": False, "error": "duplicate_ids must be a list"}, status=400)
                return
            result = cleanup_duplicate_zipmods(zipmod_id, duplicate_ids=duplicate_ids)
            if result.get("ok"):
                cleared = ",".join(str(value) for value in (result.get("cleared_ids") or []))
                record_achievement_event(
                    "duplicate_bytes",
                    int(result.get("freed_bytes") or 0),
                    f"duplicates:{result.get('guid', '')}:{cleared}",
                )
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/promote-duplicate"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/promote-duplicate")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = delete_primary_and_promote_duplicate(zipmod_id, body.get("duplicate_id"))
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/merge-duplicate"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/merge-duplicate")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = merge_duplicate_zipmod(zipmod_id, body.get("duplicate_id"))
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        if route.startswith("/mods/zipmods/") and route.endswith("/delete"):
            zipmod_id = self.parse_route_int(route, "/mods/zipmods/", "/delete")
            if zipmod_id is None:
                self.send_json({"ok": False, "error": f"Invalid route: {route}"}, status=400)
                return
            result = delete_zipmod(zipmod_id)
            self.send_json(result, status=200 if result.get("ok") else 400)
            return

        self.send_json({"ok": False, "error": f"Unknown route: {route}"}, status=404)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def parse_int_query(self, query: dict, key: str, default: int) -> int:
        try:
            return int((query.get(key) or [default])[0])
        except (TypeError, ValueError):
            return default

    def parse_optional_int_query(self, query: dict, key: str) -> int | None:
        try:
            values = query.get(key) or []
            if not values or values[0] == "":
                return None
            return int(values[0])
        except (TypeError, ValueError):
            return None

    def parse_route_int(self, route: str, prefix: str, suffix: str) -> int | None:
        if not route.startswith(prefix) or not route.endswith(suffix):
            return None
        raw = route[len(prefix) : len(route) - len(suffix)]
        try:
            return int(raw.strip("/"))
        except ValueError:
            return None

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(
        self,
        body: bytes,
        content_type: str,
        *,
        etag: str = "",
        modified_at: float | None = None,
    ) -> None:
        if etag and self.headers.get("if-none-match") == etag:
            self.send_response(304)
            self.send_header("etag", etag)
            self.send_header("access-control-allow-origin", "*")
            self.send_header("cache-control", "public, max-age=604800, immutable")
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("access-control-allow-origin", "*")
        self.send_header("cache-control", "public, max-age=604800, immutable")
        if etag:
            self.send_header("etag", etag)
        if modified_at is not None:
            self.send_header("last-modified", email.utils.formatdate(modified_at, usegmt=True))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path: str, allowed_root: Path) -> None:
        try:
            resolved = Path(file_path).resolve()
            root = allowed_root.resolve()
            if (resolved != root and root not in resolved.parents) or not resolved.is_file():
                self.send_json({"ok": False, "error": "File not found"}, status=404)
                return

            stat = resolved.stat()
            etag = f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
            if self.headers.get("if-none-match") == etag:
                self.send_response(304)
                self.send_header("etag", etag)
                self.send_header("access-control-allow-origin", "*")
                self.send_header("cache-control", "public, max-age=604800, immutable")
                self.end_headers()
                return

            body = resolved.read_bytes()
            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            self.send_header("access-control-allow-origin", "*")
            self.send_header("cache-control", "public, max-age=604800, immutable")
            self.send_header("etag", etag)
            self.send_header("last-modified", email.utils.formatdate(stat.st_mtime, usegmt=True))
            self.end_headers()
            self.wfile.write(body)
        except OSError as error:
            self.send_json({"ok": False, "error": str(error)}, status=404)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    port = int(os.environ.get("STAR_MANAGER_BACKEND_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), RequestHandler)
    start_parent_watchdog(server)
    print(f"Star_Manager backend listening on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
