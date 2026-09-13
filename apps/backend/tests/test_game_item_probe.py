from star_manager.services import game_item_probe


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def read(self):
        import json

        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_probe_proxy_allowlists_endpoints():
    result = game_item_probe.proxy_game_item_probe("/api/items")
    assert result == {"ok": False, "error": "Unsupported game item probe endpoint."}


def test_probe_proxy_wraps_successful_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.method
        seen["body"] = request.data
        seen["timeout"] = timeout
        return _Response(202, {"accepted": True, "commandId": "abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={"type": "clothes", "categoryNo": 240, "slot": 1},
    )

    assert result == {
        "ok": True,
        "data": {"accepted": True, "commandId": "abc", "status": "queued"},
    }
    assert seen["url"] == "http://127.0.0.1:7880/api/apply"
    assert seen["method"] == "POST"
    assert b'"categoryNo": 240' in seen["body"]
    assert seen["timeout"] == 2.0


def test_probe_proxy_forwards_context_endpoint(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["method"] = request.method
        seen["timeout"] = timeout
        return _Response(200, {"available": True, "scene": "hscene"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe("/api/context")

    assert result == {
        "ok": True,
        "data": {"available": True, "scene": "hscene"},
    }
    assert seen == {
        "url": "http://127.0.0.1:7880/api/context",
        "method": "GET",
        "timeout": 2.0,
    }


def test_probe_proxy_exposes_upstream_command_error(monkeypatch):
    def fake_urlopen(_request, timeout):
        del timeout
        return _Response(409, {"errorCode": "ambiguous_mapping", "error": "multiple localSlot values"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/command",
        query={"id": "abc"},
    )

    assert result["ok"] is False
    assert result["error_code"] == "ambiguous_mapping"
    assert result["data"]["errorCode"] == "ambiguous_mapping"
    assert result["upstream_status"] == 409


def test_probe_proxy_forwards_hair_slot_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        del timeout
        seen["body"] = request.data
        return _Response(202, {"accepted": True, "commandId": "hair-abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={
            "type": "hair",
            "hairSlotNo": 2,
            "categoryNo": 302,
            "slot": 1,
        },
    )

    assert result["ok"] is True
    assert b'"type": "hair"' in seen["body"]
    assert b'"hairSlotNo": 2' in seen["body"]


def test_probe_proxy_forwards_face_eye_slot_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        del timeout
        seen["body"] = request.data
        return _Response(202, {"accepted": True, "commandId": "face-abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={
            "type": "face",
            "facePartNo": 1,
            "categoryNo": 317,
            "slot": 4,
        },
    )

    assert result["ok"] is True
    assert b'"type": "face"' in seen["body"]
    assert b'"facePartNo": 1' in seen["body"]


def test_probe_proxy_forwards_body_paint_slot_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        del timeout
        seen["body"] = request.data
        return _Response(202, {"accepted": True, "commandId": "body-abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={
            "type": "body",
            "bodyPartNo": 1,
            "categoryNo": 313,
            "slot": 4,
        },
    )

    assert result["ok"] is True
    assert b'"type": "body"' in seen["body"]
    assert b'"bodyPartNo": 1' in seen["body"]


def test_probe_proxy_forwards_builtin_local_slot_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        del timeout
        seen["body"] = request.data
        return _Response(202, {"accepted": True, "commandId": "builtin-abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={"type": "clothes", "categoryNo": 240, "localSlot": 1001},
    )

    assert result["ok"] is True
    assert b'"localSlot": 1001' in seen["body"]
    assert b'"guid"' not in seen["body"]


def test_probe_proxy_forwards_hscene_target_payload(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        del timeout
        seen["body"] = request.data
        return _Response(202, {"accepted": True, "commandId": "hscene-abc", "status": "queued"})

    monkeypatch.setattr(game_item_probe, "urlopen", fake_urlopen)
    result = game_item_probe.proxy_game_item_probe(
        "/api/apply",
        method="POST",
        payload={
            "type": "clothes",
            "target": "hscene",
            "sex": 1,
            "characterIndex": 0,
            "categoryNo": 240,
            "localSlot": 100008284,
        },
    )

    assert result["ok"] is True
    assert b'"target": "hscene"' in seen["body"]
    assert b'"sex": 1' in seen["body"]
    assert b'"characterIndex": 0' in seen["body"]


def test_card_loader_validates_and_forwards_selected_sections(monkeypatch):
    from pathlib import Path

    class _CardPath:
        suffix = ".png"

        def read_bytes(self):
            return b"card"

    card_path = _CardPath()
    card_root = Path("D:/HS2/UserData/chara")
    seen = {}

    monkeypatch.setattr(
        game_item_probe,
        "validate_card_root",
        lambda _game_dir: (True, card_root, ""),
    )
    monkeypatch.setattr(game_item_probe, "resolve_card_file", lambda _root, _path: card_path)
    monkeypatch.setattr(game_item_probe, "is_ais_card", lambda _path: True)
    monkeypatch.setattr(game_item_probe, "make_card_data", lambda _data: (b"card-data", 0))
    monkeypatch.setattr(game_item_probe, "read_card_marker", lambda _data: "【AIS_Chara】")

    def fake_proxy(api_path, *, method="GET", query=None, payload=None, timeout=2.0):
        del query, timeout
        seen["api_path"] = api_path
        seen["method"] = method
        seen["payload"] = payload
        return {"ok": True, "data": {"accepted": True, "commandId": "card-abc"}}

    monkeypatch.setattr(game_item_probe, "proxy_game_item_probe", fake_proxy)
    result = game_item_probe.load_character_card_to_game(
        "D:/HS2",
        "female/favorites/card.png",
        {"face": True, "body": False, "hair": True, "parameter": False, "clothes": False, "accessory": True},
    )

    assert result["ok"] is True
    assert seen["api_path"] == "/api/apply"
    assert seen["method"] == "POST"
    assert seen["payload"] == {
        "type": "card",
        "path": "UserData/chara/female/favorites/card.png",
        "face": True,
        "body": False,
        "hair": True,
        "parameter": False,
        "clothes": False,
        "accessory": True,
    }


def test_card_loader_forwards_clothes_and_accessory_together(monkeypatch):
    from pathlib import Path

    class _CardPath:
        suffix = ".png"

        def read_bytes(self):
            return b"card"

    monkeypatch.setattr(
        game_item_probe,
        "validate_card_root",
        lambda _game_dir: (True, Path("D:/HS2/UserData/chara"), ""),
    )
    monkeypatch.setattr(game_item_probe, "resolve_card_file", lambda _root, _path: _CardPath())
    monkeypatch.setattr(game_item_probe, "is_ais_card", lambda _path: True)
    monkeypatch.setattr(game_item_probe, "make_card_data", lambda _data: (b"card-data", 0))
    monkeypatch.setattr(game_item_probe, "read_card_marker", lambda _data: "【AIS_Chara】")

    seen = {}

    def fake_proxy(api_path, *, method="GET", query=None, payload=None, timeout=2.0):
        del query, timeout
        seen["api_path"] = api_path
        seen["method"] = method
        seen["payload"] = payload
        return {"ok": True, "data": {"accepted": True, "commandId": "card-combined"}}

    monkeypatch.setattr(game_item_probe, "proxy_game_item_probe", fake_proxy)
    result = game_item_probe.load_character_card_to_game(
        "D:/HS2",
        "female/card.png",
        {name: name in {"clothes", "accessory"} for name in game_item_probe.CARD_LOAD_SECTIONS},
    )

    assert result["ok"] is True
    assert seen["api_path"] == "/api/apply"
    assert seen["method"] == "POST"
    assert seen["payload"]["clothes"] is True
    assert seen["payload"]["accessory"] is True


def test_card_loader_rejects_empty_selection(monkeypatch):
    from pathlib import Path

    class _CardPath:
        suffix = ".png"

        def read_bytes(self):
            return b"card"

    monkeypatch.setattr(
        game_item_probe,
        "validate_card_root",
        lambda _game_dir: (True, Path("D:/HS2/UserData/chara"), ""),
    )
    monkeypatch.setattr(game_item_probe, "resolve_card_file", lambda _root, _path: _CardPath())
    monkeypatch.setattr(game_item_probe, "is_ais_card", lambda _path: True)
    monkeypatch.setattr(game_item_probe, "make_card_data", lambda _data: (b"card-data", 0))
    monkeypatch.setattr(game_item_probe, "read_card_marker", lambda _data: "【AIS_Chara】")
    result = game_item_probe.load_character_card_to_game(
        "D:/HS2",
        "female/card.png",
        {name: False for name in game_item_probe.CARD_LOAD_SECTIONS},
    )

    assert result == {
        "ok": False,
        "error": "请至少选择一项人物卡内容",
        "error_code": "invalid_card_selection",
    }


def test_card_loader_rejects_path_traversal(monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(
        game_item_probe,
        "validate_card_root",
        lambda _game_dir: (True, Path("D:/HS2/UserData/chara"), ""),
    )
    result = game_item_probe.load_character_card_to_game(
        "D:/HS2",
        "female/../male/card.png",
        {"face": True},
    )

    assert result["ok"] is False
    assert result["error_code"] == "invalid_card_path"
