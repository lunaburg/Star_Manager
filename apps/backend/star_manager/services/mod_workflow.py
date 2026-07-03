import os
import shutil
from dataclasses import dataclass, field

from star_manager.core.card_parser import extract_mod_guids_from_card, is_ais_card
from star_manager.core.zipmod_utils import (
    copy_zipmods_preserving_tree,
    find_files,
    find_missing_abdata_paths,
    find_zipmod_files,
    get_manifest_value,
    is_hs2_game_dir,
    move_zipmods_preserving_tree,
)
from star_manager.services.mod_database import find_zipmod_paths_by_guid
from star_manager.tools.mod_sorter import sort_zipmod


@dataclass
class WorkflowReporter:
    on_progress: object = None
    on_message: object = None
    on_title: object = None
    on_result: object = None

    def progress(self, current, total):
        value = 100 if total <= 0 else current / total * 100
        if self.on_progress:
            self.on_progress(value)

    def message(self, text):
        if self.on_message:
            self.on_message(text)

    def title(self, text):
        if self.on_title:
            self.on_title(text)

    def result(self, text):
        if self.on_result:
            self.on_result(text)


@dataclass
class ExtractOptions:
    game_dir: str
    input_dir: str
    output_dir: str = ""
    card_paths: set[str] = field(default_factory=set)
    zipmod_extract_mode: str = "copy"


@dataclass
class ExtractResult:
    output_dir: str
    card_paths: set[str]
    required_guids: set[str]
    matched_mod_paths: set[str]
    database_matched_mod_paths: set[str]
    missing_mods: set[str]
    missing_abdata: set[str]


@dataclass
class SortResult:
    output_dir: str
    processed_count: int


def search_ais_cards(input_dir, reporter=None):
    if not os.path.isdir(input_dir):
        raise ValueError("No input directory selected.")

    reporter = reporter or WorkflowReporter()
    reporter.title("Search AIS cards")
    card_paths = set()
    file_paths = sorted(find_files(input_dir))

    for index, file_path in enumerate(file_paths, start=1):
        reporter.progress(index, len(file_paths))
        if file_path.lower().endswith(".png") and is_ais_card(file_path):
            card_paths.add(file_path)

    return card_paths


def extract_mods(options, reporter=None):
    reporter = reporter or WorkflowReporter()

    if not is_hs2_game_dir(options.game_dir):
        raise ValueError("No valid game directory selected.")
    if not os.path.isdir(options.input_dir):
        raise ValueError("No input directory selected.")

    card_paths = set(options.card_paths or search_ais_cards(options.input_dir, reporter))
    if not card_paths:
        raise ValueError("No AIS cards found in input directory.")

    output_dir = options.output_dir
    if not os.path.isdir(output_dir):
        output_dir = os.path.join(options.input_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        reporter.result(f"No output directory selected. Using default: {output_dir}")

    output_mods_dir = os.path.join(output_dir, "mods")
    output_card_dir = os.path.join(output_dir, "UserData", "chara", "female")
    game_mods_dir = os.path.join(options.game_dir, "mods")

    os.makedirs(output_mods_dir, exist_ok=True)
    os.makedirs(output_card_dir, exist_ok=True)

    reporter.message("Reading required mod GUIDs from AIS cards...")
    required_guids = get_depend_mods_guids(card_paths, reporter)

    reporter.message("Copying AIS cards to output directory...")
    copy_cards_to_output(card_paths, output_card_dir, reporter)

    reporter.message("Searching matching zipmods from mod database...")
    matched_mod_paths, database_missing_mods = get_depend_mods_paths_from_database(
        required_guids, game_mods_dir, reporter
    )
    database_matched_mod_paths = set(matched_mod_paths)

    if database_missing_mods:
        reporter.message("Searching remaining matching zipmods from game directory...")
        zipmod_files = find_zipmod_files(game_mods_dir)
        fallback_matched_paths, missing_mods = get_depend_mods_paths(database_missing_mods, zipmod_files, reporter)
        matched_mod_paths.update(fallback_matched_paths)
    else:
        missing_mods = set()

    is_move_mode = options.zipmod_extract_mode == "move"
    reporter.message(("Moving" if is_move_mode else "Copying") + " required zipmods to output directory...")
    transfer_depend_mods_to_output(matched_mod_paths, game_mods_dir, output_mods_dir, is_move_mode, reporter)

    reporter.message("Searching missing unity3d / abdata files...")
    missing_abdata = copy_missing_abdata(options.game_dir, output_dir, reporter)

    return ExtractResult(
        output_dir=output_dir,
        card_paths=card_paths,
        required_guids=required_guids,
        matched_mod_paths=matched_mod_paths,
        database_matched_mod_paths=database_matched_mod_paths,
        missing_mods=missing_mods,
        missing_abdata=missing_abdata,
    )


def get_depend_mods_guids(card_paths, reporter=None):
    reporter = reporter or WorkflowReporter()
    reporter.title("Read mod GUIDs")
    required_guids = set()
    for index, card_path in enumerate(sorted(card_paths), start=1):
        reporter.progress(index, len(card_paths))
        required_guids.update(extract_mod_guids_from_card(card_path))
    reporter.result(f"Required mod count: {len(required_guids)}")
    return required_guids


def get_depend_mods_paths_from_database(required_guids, game_mods_dir, reporter=None):
    reporter = reporter or WorkflowReporter()
    reporter.title("Find required mods in database")
    reporter.progress(0, 1)
    matched_paths, missing_guids = find_zipmod_paths_by_guid(required_guids, mods_dir=game_mods_dir)
    reporter.progress(1, 1)
    reporter.result(f"Found {len(matched_paths)} matching mods from database.")
    if missing_guids:
        reporter.message(f"Database missing {len(missing_guids)} required mods; falling back to file scan.")
    return matched_paths, missing_guids


def get_depend_mods_paths(required_guids, zipmod_files, reporter=None):
    reporter = reporter or WorkflowReporter()
    reporter.title("Find required mods")
    missing_guids = set(required_guids)
    matched_paths = set()
    scanned_count = 0

    if not missing_guids:
        reporter.result("No required mods to search.")
        reporter.progress(1, 1)
        return matched_paths, missing_guids

    for index, zipmod_path in enumerate(zipmod_files, start=1):
        scanned_count = index
        reporter.progress(index, len(zipmod_files))
        guid = get_manifest_value(zipmod_path, "guid")
        if guid in missing_guids:
            missing_guids.remove(guid)
            matched_paths.add(zipmod_path)

            reporter.message(
                f"Matched {len(matched_paths)}/{len(required_guids)} mods after scanning {scanned_count}/{len(zipmod_files)} zipmods."
            )

            if not missing_guids:
                reporter.progress(len(zipmod_files), len(zipmod_files))
                reporter.message(
                    f"All required mods found. Stopped after scanning {scanned_count}/{len(zipmod_files)} zipmods."
                )
                break

    reporter.result(
        f"Found {len(matched_paths)} matching mods. Scanned {scanned_count}/{len(zipmod_files)} zipmods."
    )
    return matched_paths, missing_guids


def copy_cards_to_output(card_paths, output_card_dir, reporter=None):
    reporter = reporter or WorkflowReporter()
    reporter.title("Copy cards")
    for index, card_path in enumerate(sorted(card_paths), start=1):
        reporter.progress(index, len(card_paths))
        shutil.copy2(card_path, output_card_dir)
    reporter.result(f"Copied {len(card_paths)} cards to output directory.")


def transfer_depend_mods_to_output(depend_mod_paths, game_mods_dir, output_mods_dir, is_move_mode, reporter=None):
    reporter = reporter or WorkflowReporter()
    action = "Move" if is_move_mode else "Copy"
    action_done = "Moved" if is_move_mode else "Copied"
    transfer = move_zipmods_preserving_tree if is_move_mode else copy_zipmods_preserving_tree
    reporter.title(f"{action} required mods")
    for index, depend_mod_path in enumerate(sorted(depend_mod_paths), start=1):
        reporter.progress(index, len(depend_mod_paths))
        transfer({depend_mod_path}, game_mods_dir, output_mods_dir)
    reporter.result(f"{action_done} {len(depend_mod_paths)} mods to output directory.")


def copy_missing_abdata(game_dir, output_dir, reporter=None):
    reporter = reporter or WorkflowReporter()
    reporter.title("Copy missing abdata")
    output_mods_dir = os.path.join(output_dir, "mods")
    game_abdata_dir = os.path.join(game_dir, "abdata")
    output_abdata_dir = os.path.join(output_dir, "abdata")
    os.makedirs(output_abdata_dir, exist_ok=True)

    missing_abdata = find_missing_abdata_paths(output_mods_dir)
    not_found = set()
    for index, rel_path in enumerate(sorted(missing_abdata), start=1):
        reporter.progress(index, len(missing_abdata))
        source_path = os.path.join(game_abdata_dir, rel_path)
        target_path = os.path.join(output_abdata_dir, rel_path)
        if os.path.exists(source_path):
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
        else:
            not_found.add(rel_path)
    return not_found


def sort_mods(input_dir, output_dir=None, delete_empty=False, reporter=None):
    from star_manager.core.zipmod_utils import remove_empty_dirs

    if not os.path.isdir(input_dir):
        raise ValueError("No input directory selected.")

    reporter = reporter or WorkflowReporter()
    reporter.title("Sort zipmods")
    reporter.message(f"Sorting zipmods in input directory: {input_dir}")

    output_dir = output_dir or input_dir
    zipmod_files = find_zipmod_files(input_dir)
    sort_dir = os.path.join(output_dir, "sort")
    error_dirs = {
        "corrupted": os.path.join(output_dir, "error", "corrupted"),
        "no_manifest": os.path.join(output_dir, "error", "no_manifest"),
        "other_error": os.path.join(output_dir, "error", "other_error"),
        "no_author": os.path.join(output_dir, "error", "no_author"),
    }

    os.makedirs(sort_dir, exist_ok=True)
    for directory in error_dirs.values():
        os.makedirs(directory, exist_ok=True)

    for index, zipmod_file in enumerate(zipmod_files, start=1):
        reporter.progress(index, len(zipmod_files))
        sort_zipmod(zipmod_file, sort_dir, error_dirs)

    if delete_empty:
        remove_empty_dirs(input_dir, [sort_dir, os.path.join(output_dir, "error")])

    return SortResult(output_dir=output_dir, processed_count=len(zipmod_files))
