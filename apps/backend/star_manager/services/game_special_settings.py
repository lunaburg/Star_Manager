from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from star_manager.core.zipmod_utils import is_hs2_game_dir


BLEEDING_MODPACK_NAME = "Sideloader Modpack - Bleeding Edge"
CONSOLE_SETTING_KEY = "console"
EXPERIMENTAL_SETTING_KEY = "experimental"


def _resolve_game_root(game_dir: str) -> tuple[Path | None, dict[str, Any] | None]:
    root = Path(game_dir).expanduser().resolve()
    if not is_hs2_game_dir(str(root)):
        return None, {"ok": False, "error": "请选择有效的 HS2 游戏目录"}
    return root, None


def _is_safe_directory(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def _is_safe_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8-sig"
    return raw.decode("utf-8"), "utf-8"


def _write_text_atomically(path: Path, text: str, encoding: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _set_bepinex_console_enabled(config_path: Path, enabled: bool) -> dict[str, Any]:
    if not _is_safe_file(config_path):
        return {"ok": False, "error": "BepInEx/config/BepInEx.cfg 不存在或不是普通文件"}
    try:
        text, encoding = _read_text(config_path)
    except (OSError, UnicodeDecodeError) as error:
        return {"ok": False, "error": f"读取 BepInEx.cfg 失败：{error}"}

    lines = text.splitlines(keepends=True)
    section_start = None
    section_end = len(lines)
    for index, line in enumerate(lines):
        if line.strip().casefold() == "[logging.console]":
            section_start = index
            break
    if section_start is not None:
        for index in range(section_start + 1, len(lines)):
            if lines[index].lstrip().startswith("["):
                section_end = index
                break

    value = "true" if enabled else "false"
    setting_pattern = re.compile(r"^(\s*Enabled\s*=\s*)(true|false)(.*)$", re.IGNORECASE)
    changed = False
    if section_start is not None:
        for index in range(section_start + 1, section_end):
            match = setting_pattern.match(lines[index].rstrip("\r\n"))
            if not match:
                continue
            line_ending = lines[index][len(lines[index].rstrip("\r\n")):]
            replacement = f"{match.group(1)}{value}{match.group(3)}{line_ending}"
            changed = replacement != lines[index]
            lines[index] = replacement
            break
        else:
            line_ending = "\r\n" if "\r\n" in text else "\n"
            insertion = f"Enabled = {value}{line_ending}"
            lines.insert(section_end, insertion)
            changed = True
    else:
        line_ending = "\r\n" if "\r\n" in text else "\n"
        prefix = "" if not text or text.endswith(("\n", "\r")) else line_ending
        lines.extend([f"{prefix}[Logging.Console]{line_ending}", f"Enabled = {value}{line_ending}"])
        changed = True

    if changed:
        try:
            _write_text_atomically(config_path, "".join(lines), encoding)
        except OSError as error:
            return {"ok": False, "error": f"写入 BepInEx.cfg 失败：{error}"}
    return {"ok": True, "changed": changed, "enabled": enabled}


def _special_paths(root: Path) -> dict[str, Path]:
    return {
        "config": root / "BepInEx" / "config" / "BepInEx.cfg",
        "marker": root / "BepInEx" / "LauncherEN" / "ilikebleeding.txt",
        "normal_modpack": root / "mods" / BLEEDING_MODPACK_NAME,
        "experimental_modpack": root / "mods.experimental" / BLEEDING_MODPACK_NAME,
    }


def _experimental_state(paths: dict[str, Path]) -> dict[str, Any]:
    marker_exists = _is_safe_file(paths["marker"])
    normal_exists = _is_safe_directory(paths["normal_modpack"])
    experimental_exists = _is_safe_directory(paths["experimental_modpack"])
    conflict = normal_exists and experimental_exists
    available = marker_exists or normal_exists or experimental_exists
    enabled = marker_exists or experimental_exists
    return {
        "available": available and not conflict,
        "enabled": enabled,
        "marker_exists": marker_exists,
        "normal_modpack_exists": normal_exists,
        "experimental_modpack_exists": experimental_exists,
        "conflict": conflict,
    }


def get_game_special_settings(game_dir: str) -> dict[str, Any]:
    root, error = _resolve_game_root(game_dir)
    if error:
        return error
    paths = _special_paths(root)
    console_available = _is_safe_file(paths["config"])
    console_enabled = False
    console_error = ""
    if console_available:
        try:
            text, _ = _read_text(paths["config"])
            section = re.search(r"(?ims)^\s*\[Logging\.Console\]\s*(.*?)(?=^\s*\[|\Z)", text)
            match = re.search(r"(?im)^\s*Enabled\s*=\s*(true|false)\b", section.group(1) if section else "")
            if match:
                console_enabled = match.group(1).casefold() == "true"
            else:
                console_error = "BepInEx.cfg 中未找到 [Logging.Console] 的 Enabled 设置"
        except (OSError, UnicodeDecodeError) as read_error:
            console_available = False
            console_error = str(read_error)

    experimental = _experimental_state(paths)
    experimental_error = "实验 Modpack 同时存在于 mods 和 mods.experimental" if experimental["conflict"] else ""
    return {
        "ok": True,
        "data": {
            "items": [
                {
                    "key": CONSOLE_SETTING_KEY,
                    "label": "激活控制台",
                    "available": console_available and not console_error,
                    "enabled": console_enabled,
                    "relative_path": "BepInEx/config/BepInEx.cfg",
                    "error": console_error,
                },
                {
                    "key": EXPERIMENTAL_SETTING_KEY,
                    "label": "实验模式",
                    "available": experimental["available"],
                    "enabled": experimental["enabled"],
                    "relative_path": "BepInEx/LauncherEN/ilikebleeding.txt",
                    "error": experimental_error,
                    **experimental,
                },
            ],
        },
    }


def _move_modpack(source: Path, destination: Path) -> None:
    if not _is_safe_directory(source):
        raise ValueError("Sideloader Modpack - Bleeding Edge 文件夹不存在或不是普通目录")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Sideloader Modpack - Bleeding Edge 的目标目录已存在")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def set_game_special_setting(game_dir: str, key: str, enabled: bool) -> dict[str, Any]:
    root, error = _resolve_game_root(game_dir)
    if error:
        return error
    paths = _special_paths(root)
    normalized_key = str(key or "").strip().casefold()
    if normalized_key == CONSOLE_SETTING_KEY:
        result = _set_bepinex_console_enabled(paths["config"], bool(enabled))
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"key": normalized_key, **result}}
    if normalized_key != EXPERIMENTAL_SETTING_KEY:
        return {"ok": False, "error": "未知的开始页设置"}

    state = _experimental_state(paths)
    if state["conflict"]:
        return {"ok": False, "error": "实验 Modpack 同时存在于 mods 和 mods.experimental，请先手动整理"}
    if not state["available"]:
        return {"ok": False, "error": "未找到 Sideloader Modpack - Bleeding Edge 文件夹"}
    try:
        if enabled:
            if state["normal_modpack_exists"]:
                _move_modpack(paths["normal_modpack"], paths["experimental_modpack"])
            paths["marker"].parent.mkdir(parents=True, exist_ok=True)
            if not paths["marker"].exists():
                paths["marker"].write_text("", encoding="utf-8")
        else:
            if state["experimental_modpack_exists"]:
                _move_modpack(paths["experimental_modpack"], paths["normal_modpack"])
            if paths["marker"].is_symlink():
                return {"ok": False, "error": "实验模式标记文件不支持符号链接"}
            paths["marker"].unlink(missing_ok=True)
    except (OSError, ValueError) as operation_error:
        return {"ok": False, "error": f"修改实验模式失败：{operation_error}"}

    return {"ok": True, "data": {"key": normalized_key, "enabled": bool(enabled), "changed": True}}
