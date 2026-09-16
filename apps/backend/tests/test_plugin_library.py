from pathlib import Path

from star_manager.services import plugin_library


def _game(tmp_path: Path) -> Path:
    (tmp_path / "HoneySelect2.exe").write_bytes(b"")
    (tmp_path / "BepInEx" / "Plugins" / "Pack").mkdir(parents=True)
    (tmp_path / "BepInEx" / "patchers").mkdir()
    (tmp_path / "BepInEx" / "core").mkdir()
    return tmp_path


def test_scan_groups_filters_and_preserves_bad_dll(tmp_path, monkeypatch):
    game = _game(tmp_path)
    for relative in ("Plugins/Pack/Test.dll", "patchers/Fix.dll", "core/BepInEx.dll"):
        (game / "BepInEx" / relative).write_bytes(b"not a managed dll")

    def fake_metadata(path):
        if path.name == "Test.dll":
            return plugin_library.AssemblyMetadata(
                assembly_name="Test.Assembly", assembly_version="1.2.3.4",
                plugin_guid="example.test", plugin_name="Test Plugin", plugin_version="2.0",
                dependencies=[{"guid": "example.api", "minimum_version": "1.0"}],
            )
        raise ValueError("不是 .NET 程序集")

    monkeypatch.setattr(plugin_library, "read_dotnet_metadata", fake_metadata)
    result = plugin_library.scan_bepinex_plugins(str(game), search="test", category="plugin", db_path=tmp_path / "cache.sqlite")
    assert result["ok"] is True
    assert result["data"]["summary"] == {"total": 1, "plugins": 1, "patchers": 0, "core": 0, "metadata_errors": 0, "duplicates": 0, "described": 0, "with_dependencies": 1}
    assert result["data"]["total"] == 1
    assert result["data"]["items"][0]["plugin_guid"] == "example.test"


def test_scan_rejects_missing_bepinex(tmp_path):
    (tmp_path / "HoneySelect2.exe").write_bytes(b"")
    result = plugin_library.scan_bepinex_plugins(str(tmp_path))
    assert result == {"ok": False, "error": "所选游戏目录中不存在 BepInEx 文件夹"}


def test_ser_string_decoder_reads_plugin_constructor_arguments():
    blob = b"\x01\x00\x0bexample.mod\x04Name\x051.2.3"
    assert plugin_library._read_ser_strings(blob) == ["example.mod", "Name", "1.2.3"]


def test_description_prefers_metadata_and_recognizes_known_plugin():
    metadata = plugin_library.AssemblyMetadata(description="Author supplied description")
    assert plugin_library.describe_plugin(metadata, Path("Anything.dll"), "plugin") == ("Author supplied description", "assembly")
    known = plugin_library.AssemblyMetadata(plugin_name="HS2_BetterHScenes")
    description, source = plugin_library.describe_plugin(known, Path("HS2_BetterHScenes.dll"), "plugin")
    assert "H 场景" in description
    assert source == "catalog"
    switcher = plugin_library.AssemblyMetadata(plugin_name="HS2_HCharaSwitcher")
    description, source = plugin_library.describe_plugin(switcher, Path("HS2_HCharaSwitcher.dll"), "plugin")
    assert "H 场景" in description and "更换" in description
    assert source == "catalog"


def test_plugin_descriptions_are_loaded_from_external_catalog(tmp_path):
    catalog = tmp_path / "plugin_descriptions.json"
    catalog.write_text(
        '{"catalog":{"exampleplugin":"External description"},'
        '"inference_rules":[{"keywords":["sample"],"description":"Inferred description"}],'
        '"fallbacks":{"plugin":"Fallback description"}}',
        encoding="utf-8",
    )
    loaded = plugin_library.load_plugin_descriptions(catalog)
    assert loaded["catalog"] == {"exampleplugin": "External description"}
    assert loaded["inference_rules"] == [(('sample',), "Inferred description")]
    assert loaded["fallbacks"] == {"plugin": "Fallback description"}
    assert len(plugin_library.PLUGIN_DESCRIPTIONS) == 149
    assert plugin_library.PLUGIN_DESCRIPTIONS["hs2lightprobesreset"].startswith("在切换或载入地图后")


def test_config_and_translation_joint_description(tmp_path):
    bepinex = tmp_path / "BepInEx"
    config = bepinex / "config"
    translation = bepinex / "Translation" / "zh-CN" / "Text" / "Plugin"
    config.mkdir(parents=True)
    translation.mkdir(parents=True)
    (config / "HS2_ExtraGroups.cfg").write_text(
        "## Plugin GUID: HS2_ExtraGroups\n[Requires restart!]\nGroups Count = 5\nGirls Count = 20\n",
        encoding="utf-8",
    )
    (translation / "HS2_ExtraGroups.txt").write_text(
        "HS2_ExtraGroups=女团扩增数插件\nGroups Count=团体数量\nGirls Count=每组少女数量\n",
        encoding="utf-8",
    )
    index = plugin_library.build_support_index(bepinex)
    metadata = plugin_library.AssemblyMetadata(plugin_guid="HS2_ExtraGroups", plugin_name="HS2_ExtraGroups")
    result = plugin_library.describe_from_support_files(metadata, Path("HS2_ExtraGroups.dll"), index)
    assert result is not None
    description, source, confidence, evidence = result
    assert description == "女团扩增数插件，可配置团体数量、每组少女数量。部分设置需要重启游戏后生效。"
    assert source == "config+translation"
    assert confidence == "high"
    assert len(evidence) == 2


def test_sqlite_cache_skips_unchanged_dll_and_invalidates_on_change(tmp_path, monkeypatch):
    game = _game(tmp_path)
    dll = game / "BepInEx" / "Plugins" / "Pack" / "Cached.dll"
    dll.write_bytes(b"first")
    calls = []

    def fake_metadata(path):
        calls.append(path)
        return plugin_library.AssemblyMetadata(plugin_guid="example.cached", plugin_name="Cached", plugin_version="1.0")

    monkeypatch.setattr(plugin_library, "read_dotnet_metadata", fake_metadata)
    db_path = tmp_path / "plugin-cache.sqlite"
    first = plugin_library.scan_bepinex_plugins(str(game), db_path=db_path)
    second = plugin_library.scan_bepinex_plugins(str(game), db_path=db_path)
    assert first["data"]["cached"] is False
    assert second["data"]["cached"] is True
    assert len(calls) == 1

    dll.write_bytes(b"changed")
    third = plugin_library.scan_bepinex_plugins(str(game), db_path=db_path)
    assert third["data"]["cached"] is False
    assert len(calls) == 2


def test_plugin_toggle_renames_dll_and_preserves_stable_scan_identity(tmp_path, monkeypatch):
    game = _game(tmp_path)
    dll = game / "BepInEx" / "Plugins" / "Pack" / "Toggle.dll"
    dll.write_bytes(b"plugin")

    disabled = plugin_library.set_bepinex_plugin_enabled(
        str(game), "BepInEx/Plugins/Pack/Toggle.dll", False
    )
    assert disabled["ok"] is True
    assert disabled["data"]["enabled"] is False
    assert not dll.exists()
    assert (dll.parent / "Toggle.dl_").exists()

    def fake_metadata(path):
        return plugin_library.AssemblyMetadata(
            assembly_name="Toggle.Assembly",
            plugin_guid="example.toggle",
            plugin_name="Toggle",
            plugin_version="1.0",
        )

    monkeypatch.setattr(plugin_library, "read_dotnet_metadata", fake_metadata)
    scanned = plugin_library.scan_bepinex_plugins(str(game), db_path=tmp_path / "cache.sqlite")
    item = scanned["data"]["items"][0]
    assert item["id"] == "bepinex/plugins/pack/toggle.dll"
    assert item["enabled"] is False
    assert item["relative_path"].endswith("Toggle.dl_")

    enabled = plugin_library.set_bepinex_plugin_enabled(
        str(game), "BepInEx/Plugins/Pack/Toggle.dl_", True
    )
    assert enabled["ok"] is True
    assert enabled["data"]["enabled"] is True
    assert dll.exists()


def test_plugin_toggle_rejects_paths_outside_plugin_area_and_existing_target(tmp_path):
    game = _game(tmp_path)
    outside = tmp_path / "outside.dll"
    outside.write_bytes(b"outside")
    rejected = plugin_library.set_bepinex_plugin_enabled(str(game), "../outside.dll", False)
    assert rejected["ok"] is False
    assert outside.exists()

    dll = game / "BepInEx" / "Plugins" / "Pack" / "Conflict.dll"
    dll.write_bytes(b"active")
    (dll.parent / "Conflict.dl_").write_bytes(b"disabled")
    conflict = plugin_library.set_bepinex_plugin_enabled(
        str(game), "BepInEx/Plugins/Pack/Conflict.dll", False
    )
    assert conflict["ok"] is False
    assert dll.read_bytes() == b"active"


def test_legacy_disabled_plugin_is_migrated_to_dl_suffix(tmp_path):
    game = _game(tmp_path)
    legacy = game / "BepInEx" / "Plugins" / "Pack" / "Legacy.dll.disabled"
    legacy.write_bytes(b"legacy")

    migrated = plugin_library.set_bepinex_plugin_enabled(
        str(game), "BepInEx/Plugins/Pack/Legacy.dll.disabled", False
    )

    assert migrated["ok"] is True
    assert migrated["data"]["enabled"] is False
    assert not legacy.exists()
    assert (legacy.parent / "Legacy.dl_").exists()
