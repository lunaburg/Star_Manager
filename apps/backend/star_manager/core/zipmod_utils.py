import csv
import io
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET


ERROR_CORRUPTED = "[E]corrupted"
ERROR_NO_MANIFEST = "[E]no_manifest"
ERROR_NO_VALUE = "[E]no_value"
ERROR_OTHER = "[E]other_error"


def find_files(root_dir, suffix=None):
    file_paths = set()
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if suffix is None or filename.lower().endswith(suffix.lower()):
                file_paths.add(os.path.join(root, filename))
    return file_paths


def find_zipmod_files(mods_dir):
    return sorted(find_files(mods_dir, ".zipmod"))


def is_hs2_game_dir(game_dir):
    return os.path.isdir(game_dir) and os.path.exists(os.path.join(game_dir, "HoneySelect2.exe"))


def get_manifest_value(zipmod_path, name):
    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            if "manifest.xml" not in zf.namelist():
                return ERROR_NO_MANIFEST

            with zf.open("manifest.xml") as xml_file:
                root = ET.parse(xml_file).getroot()
                element = root.find(name)
                if element is None or not element.text:
                    return ERROR_NO_VALUE
                return element.text.strip()
    except zipfile.BadZipFile:
        return ERROR_CORRUPTED
    except (ET.ParseError, OSError):
        return ERROR_OTHER


def copy_zipmods_preserving_tree(zipmod_paths, source_root, target_root):
    for zipmod_path in zipmod_paths:
        relative_path = os.path.relpath(zipmod_path, source_root)
        target_path = os.path.join(target_root, relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.copy2(zipmod_path, target_path)


def move_zipmods_preserving_tree(zipmod_paths, source_root, target_root):
    for zipmod_path in zipmod_paths:
        relative_path = os.path.relpath(zipmod_path, source_root)
        target_path = os.path.join(target_root, relative_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        shutil.move(zipmod_path, target_path)


def collect_missing_abdata_from_zipmod(zipmod_path):
    missing_abdata = set()

    try:
        with zipfile.ZipFile(zipmod_path, "r") as zf:
            zip_files = {os.path.normpath(name).lower().replace("\\", "/") for name in zf.namelist()}
            csv_files = [name for name in zf.namelist() if name.lower().endswith(".csv")]

            for csv_file in csv_files:
                try:
                    with zf.open(csv_file) as file:
                        text_file = io.TextIOWrapper(file, encoding="utf-8-sig", newline="")
                        reader = csv.reader(text_file)
                        rows = [next(reader) for _ in range(4)]

                        header_row = rows[3]
                        target_columns = [
                            index
                            for index, column in enumerate(header_row)
                            if column.strip() in {"MainAB", "ThumbAB"}
                        ]
                        if not target_columns:
                            continue

                        for row in reader:
                            for column_index in target_columns:
                                if column_index >= len(row):
                                    continue
                                ab_path = row[column_index].strip()
                                normalized_ab = os.path.normpath(ab_path).lower().replace("\\", "/")
                                if ab_path and not any(name.endswith(normalized_ab) for name in zip_files):
                                    missing_abdata.add(ab_path)
                except (StopIteration, csv.Error, UnicodeDecodeError):
                    continue
    except (zipfile.BadZipFile, OSError, UnicodeDecodeError):
        return set()

    return missing_abdata


def find_missing_abdata_paths(mods_dir):
    missing_abdata = set()
    for zipmod_path in find_zipmod_files(mods_dir):
        missing_abdata.update(collect_missing_abdata_from_zipmod(zipmod_path))
    return missing_abdata


def generate_zipmod_filename(target_dir, author, name):
    safe_author = sanitize_filename_part(author)
    safe_name = sanitize_filename_part(name) if name else None

    if safe_name:
        base_name = f"[{safe_author}]_{safe_name}"
    else:
        base_name = f"[{safe_author}]_Noname"

    return next_available_zipmod_path(target_dir, base_name)


def next_available_zipmod_path(target_dir, base_name):
    dest_path = os.path.join(target_dir, f"{base_name}.zipmod")
    if not os.path.exists(dest_path):
        return dest_path

    counter = 1
    while True:
        dest_path = os.path.join(target_dir, f"{base_name}_{counter}.zipmod")
        if not os.path.exists(dest_path):
            return dest_path
        counter += 1


def sanitize_filename_part(value):
    value = value or "Unknown"
    return re.sub(r'[<>:"/\\|?*]', "_", value).strip()


def remove_empty_dirs(root_dir, exclude_dirs):
    exclude_abs = [os.path.abspath(path) for path in exclude_dirs]

    for dirpath, _, _ in os.walk(root_dir, topdown=False):
        current_abs = os.path.abspath(dirpath)
        if any(current_abs == item or current_abs.startswith(item + os.sep) for item in exclude_abs):
            continue
        if not os.listdir(dirpath):
            os.rmdir(dirpath)
