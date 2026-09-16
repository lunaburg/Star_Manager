from pathlib import Path

from star_manager.services.game_special_settings import (
    BLEEDING_MODPACK_NAME,
    get_game_special_settings,
    set_game_special_setting,
)


def _game(tmp_path: Path) -> Path:
    (tmp_path / "HoneySelect2.exe").write_bytes(b"")
    (tmp_path / "BepInEx" / "config").mkdir(parents=True)
    (tmp_path / "BepInEx" / "LauncherEN").mkdir(parents=True)
    return tmp_path


def test_console_setting_updates_only_logging_console_enabled(tmp_path):
    game = _game(tmp_path)
    config = game / "BepInEx" / "config" / "BepInEx.cfg"
    config.write_text(
        "[Logging.Console]\nEnabled = false\nPreventClose = false\n\n[Logging.Disk]\nEnabled = true\n",
        encoding="utf-8",
    )

    result = set_game_special_setting(str(game), "console", True)

    assert result["ok"] is True
    text = config.read_text(encoding="utf-8")
    assert "[Logging.Console]\nEnabled = true\nPreventClose = false" in text
    assert "[Logging.Disk]\nEnabled = true" in text
    state = get_game_special_settings(str(game))
    assert state["data"]["items"][0]["enabled"] is True


def test_experimental_setting_moves_modpack_and_marker_reversibly(tmp_path):
    game = _game(tmp_path)
    modpack = game / "mods" / BLEEDING_MODPACK_NAME
    modpack.mkdir(parents=True)
    (modpack / "sample.txt").write_text("keep", encoding="utf-8")

    enabled = set_game_special_setting(str(game), "experimental", True)

    assert enabled["ok"] is True
    assert not modpack.exists()
    moved = game / "mods.experimental" / BLEEDING_MODPACK_NAME
    assert (moved / "sample.txt").read_text(encoding="utf-8") == "keep"
    assert (game / "BepInEx" / "LauncherEN" / "ilikebleeding.txt").exists()

    disabled = set_game_special_setting(str(game), "experimental", False)

    assert disabled["ok"] is True
    assert not moved.exists()
    assert (game / "mods" / BLEEDING_MODPACK_NAME / "sample.txt").read_text(encoding="utf-8") == "keep"
    assert not (game / "BepInEx" / "LauncherEN" / "ilikebleeding.txt").exists()
