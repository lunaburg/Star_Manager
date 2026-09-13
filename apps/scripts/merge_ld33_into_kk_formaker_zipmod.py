"""Add the LD 33 CuteyNip female pose to an existing ForMaker zipmod.

The base archive supplies the dedicated IKAB resource.  The output keeps the
base manifest, CSV entries, and IK bundle, then appends one CSV row and adds the
converted LD animation bundle.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_female_pose_zipmod import modify_template_clip, read_pose, verify_bundle  # noqa: E402


DEFAULT_CSV = "abdata/list/characustom/00/custom_pose_f_complete.csv"
DEFAULT_ANIMATION = "abdata/custom/LD_33_CuteyNip/anim_f_00.unity3d"


def decode_csv(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def load_csv_rows(data: bytes) -> tuple[list[list[str]], int, list[str]]:
    rows = list(csv.reader(io.StringIO(decode_csv(data))))
    for index, row in enumerate(rows):
        if {cell.strip() for cell in row} >= {"ID", "Name", "MainAB", "Clip", "IKAB", "IKData"}:
            return rows, index, [cell.strip() for cell in row]
    raise ValueError("the base ForMaker zipmod has no compatible characustom CSV header")


def append_pose_row(data: bytes, pose_name: str, item_id: int, main_ab: str) -> tuple[bytes, dict[str, object]]:
    rows, header_index, header = load_csv_rows(data)
    columns = {name: index for index, name in enumerate(header)}
    existing_rows = []
    for row in rows[header_index + 1 :]:
        if not row or all(not cell.strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        existing_rows.append(padded[: len(header)])
    if any(row[columns["ID"]].strip() == str(item_id) for row in existing_rows):
        raise ValueError(f"item ID already exists in base CSV: {item_id}")
    if any(row[columns["Name"]].strip() == pose_name for row in existing_rows):
        raise ValueError(f"pose name already exists in base CSV: {pose_name}")

    new_row = [""] * len(header)
    values = {
        "ID": str(item_id),
        "Kind": "1",
        "Possess": "1",
        "Name": pose_name,
        "EN_US": "0",
        "ZH_CN": "0",
        "ZH_TW": "0",
        "MainManifest": "abdata",
        "MainAB": main_ab,
        "MainData": "edit_F",
        "Clip": "mannequin",
        "IKAB": "custom/KK_Animations_-_Free_Sample_ForMaker/ik_f_00",
        "IKData": "edit_F",
    }
    for key, value in values.items():
        if key not in columns:
            raise ValueError(f"base CSV is missing required column: {key}")
        new_row[columns[key]] = value
    rows.append(new_row)

    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue().encode("utf-8"), {
        "header_index": header_index,
        "existing_item_count": len(existing_rows),
        "added_item_id": item_id,
        "added_name": pose_name,
        "ik_ab": values["IKAB"],
        "main_ab": main_ab,
    }


def copy_base_archive(
    base_zip: zipfile.ZipFile,
    output_path: Path,
    csv_member: str,
    updated_csv: bytes,
    animation_member: str,
    animation_path: Path,
) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for info in base_zip.infolist():
            if info.filename == csv_member:
                output.writestr(csv_member, updated_csv)
                continue
            if info.filename == animation_member:
                raise ValueError(f"animation path already exists in base zipmod: {animation_member}")
            output.writestr(info.filename, base_zip.read(info.filename))
        output.write(animation_path, animation_member)


def build(args: argparse.Namespace) -> dict[str, object]:
    base_path = args.base.resolve()
    pose_path = args.pose.resolve()
    reference_bundle = args.reference_bundle.resolve()
    skeleton_bundle = args.skeleton_bundle.resolve()
    output_path = args.output.resolve()
    for path in (base_path, pose_path, reference_bundle, skeleton_bundle):
        if not path.is_file():
            raise FileNotFoundError(f"required input does not exist: {path}")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output exists; pass --force to replace it: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pose = read_pose(pose_path)
    if pose["sex"] != 1:
        raise ValueError("the input pose is not female")
    with zipfile.ZipFile(base_path) as base_zip:
        if args.csv_member not in base_zip.namelist():
            raise ValueError(f"base zipmod has no CSV: {args.csv_member}")
        ik_member = "abdata/custom/KK_Animations_-_Free_Sample_ForMaker/ik_f_00.unity3d"
        if ik_member not in base_zip.namelist():
            raise ValueError(f"base zipmod has no reusable IK bundle: {ik_member}")
        csv_member = args.csv_member
        main_ab = args.main_ab.replace("\\", "/").strip("/")
        animation_member = f"abdata/{main_ab}"
        with tempfile.TemporaryDirectory(prefix=".ld33-merge-", dir=str(output_path.parent)) as temp:
            generated_animation = Path(temp) / "anim_f_00.unity3d"
            conversion = modify_template_clip(reference_bundle, skeleton_bundle, pose, generated_animation)
            verification = verify_bundle(generated_animation)
            updated_csv, csv_report = append_pose_row(
                base_zip.read(csv_member), pose["name"], args.item_id, main_ab
            )
            copy_base_archive(
                base_zip,
                output_path,
                csv_member,
                updated_csv,
                animation_member,
                generated_animation,
            )

    with zipfile.ZipFile(output_path) as result_zip:
        if result_zip.testzip() is not None:
            raise ValueError("merged zipmod failed CRC validation")
        required = {args.csv_member, animation_member, ik_member}
        missing = sorted(required - set(result_zip.namelist()))
        if missing:
            raise ValueError(f"merged zipmod entries missing: {missing}")
        result_rows, _, _ = load_csv_rows(result_zip.read(args.csv_member))
        added = [row for row in result_rows if len(row) > 0 and row[0].strip() == str(args.item_id)]
        if len(added) != 1:
            raise ValueError(f"merged CSV does not contain exactly one new item {args.item_id}")

    report = {
        "base_zipmod": str(base_path),
        "source_pose": str(pose_path),
        "output": str(output_path),
        "csv_member": args.csv_member,
        "animation_member": animation_member,
        "ik_member": ik_member,
        "csv": csv_report,
        "conversion": conversion,
        "verification": verification,
        "output_size": output_path.stat().st_size,
    }
    report_path = output_path.with_suffix(output_path.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--pose", type=Path, required=True)
    parser.add_argument("--reference-bundle", type=Path, required=True)
    parser.add_argument("--skeleton-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv-member", default=DEFAULT_CSV)
    parser.add_argument("--main-ab", default="custom/LD_33_CuteyNip/anim_f_00.unity3d")
    parser.add_argument("--item-id", type=int, default=33001)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(build(parse_args()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
