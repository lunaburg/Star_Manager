"""Small, allow-listed proxy for the HS2 Game Item Probe plugin.

The game-side plugin owns all Unity calls and listens on loopback. Keeping the
proxy here lets the renderer use the existing backendRequest bridge without
exposing an arbitrary HTTP forwarder from the desktop app.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from star_manager.core.card_parser import is_ais_card, read_card_marker
from star_manager.core.coordinate_card import make_card_data
from star_manager.services.card_library import (
    normalize_relative_path,
    resolve_card_file,
    validate_card_root,
)


PROBE_HOST = "127.0.0.1"
DEFAULT_PROBE_PORT = 7880
PROBE_API_PATHS = frozenset({
    "/api/status",
    "/api/current",
    "/api/context",
    "/api/apply",
    "/api/command",
})
CARD_LOAD_SECTIONS = ("face", "body", "hair", "parameter", "clothes", "accessory")


def probe_port() -> int:
    """Return the configured loopback port, falling back safely to 7880."""

    try:
        value = int(os.environ.get("STAR_MANAGER_GAME_ITEM_PROBE_PORT", DEFAULT_PROBE_PORT))
    except (TypeError, ValueError):
        return DEFAULT_PROBE_PORT
    return value if 1 <= value <= 65535 else DEFAULT_PROBE_PORT


def proxy_game_item_probe(
    api_path: str,
    *,
    method: str = "GET",
    query: Mapping[str, str] | None = None,
    payload: Mapping[str, Any] | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Call one known probe endpoint and normalize its result for the UI."""

    if api_path not in PROBE_API_PATHS:
        return {"ok": False, "error": "Unsupported game item probe endpoint."}

    query_values = {
        str(key): str(value)
        for key, value in (query or {}).items()
        if value is not None and str(value) != ""
    }
    query_suffix = f"?{urlencode(query_values)}" if query_values else ""
    url = f"http://{PROBE_HOST}:{probe_port()}{api_path}{query_suffix}"
    encoded_body = None
    headers = {}
    if payload is not None:
        encoded_body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        headers["content-type"] = "application/json; charset=utf-8"

    request = Request(
        url,
        data=encoded_body,
        headers=headers,
        method=str(method or "GET").upper(),
    )
    response_status = 0
    response_body = b""
    try:
        with urlopen(request, timeout=timeout) as response:
            response_status = int(response.status)
            response_body = response.read()
    except HTTPError as error:
        response_status = int(error.code or 502)
        try:
            response_body = error.read()
        except OSError:
            response_body = b""
    except (OSError, URLError, TimeoutError):
        return {
            "ok": False,
            "error": (
                "游戏物品探针未连接，请启动 HS2，并确认已安装 "
                "StarManager.GameItemProbe 插件。"
            ),
            "error_code": "probe_unavailable",
        }

    try:
        upstream_payload = json.loads(response_body.decode("utf-8")) if response_body else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "ok": False,
            "error": "游戏物品探针返回了无法识别的数据。",
            "error_code": "invalid_probe_response",
            "upstream_status": response_status or 502,
        }

    if not isinstance(upstream_payload, dict):
        return {
            "ok": False,
            "error": "游戏物品探针返回的数据格式无效。",
            "error_code": "invalid_probe_response",
            "upstream_status": response_status or 502,
        }

    if not 200 <= response_status < 300:
        return {
            "ok": False,
            "error": str(upstream_payload.get("error") or "游戏物品探针请求失败"),
            "error_code": str(
                upstream_payload.get("errorCode")
                or upstream_payload.get("error_code")
                or "probe_request_failed"
            ),
            "data": upstream_payload,
            "upstream_status": response_status or 502,
        }

    return {
        "ok": True,
        "data": upstream_payload,
    }


def load_character_card_to_game(
    game_dir: str,
    relative_path: str,
    sections: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate one library card, then submit its selected sections to the probe."""

    is_valid, root, root_error = validate_card_root(game_dir)
    if not is_valid:
        return {"ok": False, "error": root_error or "请选择有效的游戏目录", "error_code": "invalid_game_dir"}

    normalized_path = normalize_relative_path(relative_path)
    parts = normalized_path.split("/") if normalized_path else []
    if (
        len(parts) < 2
        or parts[0].casefold() not in {"female", "male"}
        or any(part in {".", ".."} for part in parts)
    ):
        return {
            "ok": False,
            "error": "人物卡路径必须位于 UserData/chara/female 或 male 目录内",
            "error_code": "invalid_card_path",
        }

    try:
        card_path = resolve_card_file(root, normalized_path)
    except (OSError, ValueError) as error:
        return {"ok": False, "error": str(error), "error_code": "invalid_card_path"}

    if card_path.suffix.casefold() != ".png" or not is_ais_card(str(card_path)):
        return {"ok": False, "error": "请选择有效的 AIS 人物卡 PNG", "error_code": "invalid_card"}

    try:
        card_data, _ = make_card_data(card_path.read_bytes())
        if read_card_marker(card_data) != "【AIS_Chara】":
            return {
                "ok": False,
                "error": "选择的文件不是 AIS 人物卡",
                "error_code": "invalid_card",
            }
    except (OSError, TypeError, ValueError) as error:
        return {"ok": False, "error": f"人物卡读取失败：{error}", "error_code": "invalid_card"}

    selected = {
        name: sections.get(name) is True
        for name in CARD_LOAD_SECTIONS
    } if sections is not None else {name: False for name in CARD_LOAD_SECTIONS}
    if not any(selected.values()):
        return {
            "ok": False,
            "error": "请至少选择一项人物卡内容",
            "error_code": "invalid_card_selection",
        }

    game_relative_path = Path("UserData") / "chara" / Path(*parts)
    payload: dict[str, Any] = {
        "type": "card",
        "path": str(game_relative_path).replace(os.sep, "/"),
        **selected,
    }
    return proxy_game_item_probe("/api/apply", method="POST", payload=payload)
