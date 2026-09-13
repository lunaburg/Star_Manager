"""Register every animation from KK Animations - Free Sample in the HS2 female pose list.

The original ForMaker archive intentionally registers only a small subset of the
animation collection.  This builder keeps the collection's animation bundles as
an external dependency, copies the original dedicated IK bundle, and generates a
complete Kind=501 characustom CSV.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

VENDOR = Path(__file__).resolve().parents[1] / "backend" / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import UnityPy  # type: ignore  # noqa: E402


IK_ARCHIVE_PATH = "abdata/custom/KK_Animations_-_Free_Sample_ForMaker/ik_f_00.unity3d"
CSV_ARCHIVE_PATH = "abdata/list/characustom/00/custom_pose_f_complete.csv"
CSV_HEADER = "ID,Kind,Possess,Name,EN_US,ZH_CN,ZH_TW,MainManifest,MainAB,MainData,Clip,IKAB,IKData"
IK_AB = "custom/KK_Animations_-_Free_Sample_ForMaker/ik_f_00"


def decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize_archive_path(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("/")


def find_csv_header(rows: list[list[str]], required: set[str]) -> tuple[int, list[str]]:
    for index, row in enumerate(rows):
        columns = {cell.strip() for cell in row}
        if required.issubset(columns):
            return index, [cell.strip() for cell in row]
    raise ValueError(f"CSV header not found; required={sorted(required)}")


def read_original_maker_ids(maker_zip: zipfile.ZipFile) -> dict[tuple[str, str, str], int]:
    candidates = [
        name
        for name in maker_zip.namelist()
        if normalize_archive_path(name).lower().startswith("abdata/list/characustom/")
        and normalize_archive_path(name).lower().endswith(".csv")
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected one original characustom CSV, found={candidates}")
    rows = list(csv.reader(io.StringIO(decode_text(maker_zip.read(candidates[0])))))
    header_index, header = find_csv_header(rows, {"ID", "Name", "MainAB", "Clip"})
    index = {name: position for position, name in enumerate(header)}
    result = {}
    for row in rows[header_index + 1 :]:
        if not row or all(not cell.strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        key = (
            padded[index["Name"]].strip(),
            padded[index["MainAB"]].strip(),
            padded[index["Clip"]].strip(),
        )
        result[key] = int(padded[index["ID"]].strip())
    return result


def read_animation_rows(full_zip: zipfile.ZipFile) -> list[dict[str, str]]:
    rows_out: list[dict[str, str]] = []
    for name in sorted(full_zip.namelist()):
        normalized = normalize_archive_path(name)
        if not normalized.lower().startswith("abdata/studio/info/"):
            continue
        if not normalized.lower().endswith(".csv") or "anime_" not in normalized.lower():
            continue
        rows = list(csv.reader(io.StringIO(decode_text(full_zip.read(name)))))
        header_index, header = find_csv_header(rows, {"表示順番", "管理番号", "表示名", "バンドルパス", "ファイル名", "クリップ名"})
        index = {column: position for position, column in enumerate(header)}
        for row in rows[header_index + 1 :]:
            if not row or all(not cell.strip() for cell in row):
                continue
            padded = row + [""] * max(0, len(header) - len(row))
            display_name = padded[index["表示名"]].strip()
            main_ab = padded[index["バンドルパス"]].strip()
            main_data = padded[index["ファイル名"]].strip()
            clip = padded[index["クリップ名"]].strip()
            if not display_name or not main_ab or not main_data or not clip:
                continue
            rows_out.append(
                {
                    "source_csv": normalized,
                    "display_name": display_name,
                    "main_ab": main_ab,
                    "main_data": main_data,
                    "clip": clip,
                }
            )
    if not rows_out:
        raise ValueError("no animation rows found in the full sample archive")
    return rows_out


def verify_animation_references(full_zip: zipfile.ZipFile, rows: list[dict[str, str]]) -> dict[str, object]:
    bundles = {row["main_ab"] for row in rows}
    checked: dict[str, dict[str, object]] = {}
    for bundle in sorted(bundles):
        archive_path = f"abdata/{bundle}"
        if archive_path not in full_zip.namelist():
            raise ValueError(f"animation bundle is missing from full sample: {archive_path}")
        environment = UnityPy.load(full_zip.read(archive_path))
        controllers = [
            obj
            for obj in environment.objects
            if obj.type.name == "AnimatorController" and obj.read().m_Name == "phPoses"
        ]
        if len(controllers) != 1:
            raise ValueError(f"expected one phPoses controller in {archive_path}, found={len(controllers)}")
        clip_names = {
            obj.read().m_Name
            for obj in environment.objects
            if obj.type.name == "AnimationClip"
        }
        referenced = {row["clip"] for row in rows if row["main_ab"] == bundle}
        missing = sorted(referenced - clip_names)
        if missing:
            raise ValueError(f"clips missing from {archive_path}: {missing}")
        checked[bundle] = {
            "controller": "phPoses",
            "animation_clip_count": len(clip_names),
            "referenced_clip_count": len(referenced),
        }
    return {"bundle_count": len(bundles), "bundles": checked}


def make_manifest() -> bytes:
    name = "KK Animations - Free Sample_ForMaker Complete"
    return (
        '<manifest schema-ver="1">\n'
        "  <guid>codex.studioanimemaker.kk_animations_free_sample_complete</guid>\n"
        f"  <name>{xml_escape(name)}</name>\n"
        "  <version>1.0.0</version>\n"
        "  <author>Codex</author>\n"
        "  <game>HS2</game>\n"
        "  <description>All animations from KK Animations - Free Sample registered as Chara Maker poses.</description>\n"
        "</manifest>\n"
    ).encode("utf-8")


def make_csv(rows: list[dict[str, str]], original_ids: dict[tuple[str, str, str], int]) -> tuple[bytes, dict[str, object]]:
    used_ids = set(original_ids.values())
    next_id = max(50008, max(used_ids, default=50007) + 1)
    assigned: set[int] = set()
    output_rows = []
    preserved_count = 0
    for row in rows:
        full_name = f"KK Animations - Free Sample {row['display_name']}"
        key = (full_name, row["main_ab"], row["clip"])
        item_id = original_ids.get(key)
        if item_id is not None and item_id not in assigned:
            preserved_count += 1
        else:
            while next_id in used_ids or next_id in assigned:
                next_id += 1
            item_id = next_id
            next_id += 1
        assigned.add(item_id)
        output_rows.append(
            f"{item_id},1,1,{full_name},0,0,0,abdata,{row['main_ab']},{row['main_data']},{row['clip']},{IK_AB},edit_F"
        )
    text = "\n".join(["501", "0", "73c8de55fb8d473a855d8abbcd978f17", CSV_HEADER, *output_rows, ""])
    return text.encode("utf-8"), {
        "row_count": len(output_rows),
        "preserved_original_ids": preserved_count,
        "assigned_id_min": min(assigned),
        "assigned_id_max": max(assigned),
    }


def build(args: argparse.Namespace) -> dict[str, object]:
    full_path = args.full.resolve()
    maker_path = args.maker.resolve()
    output_path = args.output.resolve()
    if not full_path.is_file() or not maker_path.is_file():
        raise FileNotFoundError("full sample and original ForMaker zipmods must exist")
    if output_path.exists() and not args.force:
        raise FileExistsError(f"output exists; pass --force to replace it: {output_path}")

    with zipfile.ZipFile(full_path) as full_zip, zipfile.ZipFile(maker_path) as maker_zip:
        rows = read_animation_rows(full_zip)
        reference_check = verify_animation_references(full_zip, rows)
        original_ids = read_original_maker_ids(maker_zip)
        csv_data, csv_report = make_csv(rows, original_ids)
        if IK_ARCHIVE_PATH not in maker_zip.namelist():
            raise ValueError(f"original ForMaker IK bundle is missing: {IK_ARCHIVE_PATH}")
        ik_data = maker_zip.read(IK_ARCHIVE_PATH)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            archive.writestr("manifest.xml", make_manifest())
            archive.writestr(CSV_ARCHIVE_PATH, csv_data)
            archive.writestr(IK_ARCHIVE_PATH, ik_data)

    with zipfile.ZipFile(output_path) as archive:
        expected = {"manifest.xml", CSV_ARCHIVE_PATH, IK_ARCHIVE_PATH}
        names = set(archive.namelist())
        if not expected.issubset(names):
            raise ValueError(f"generated entries missing: {sorted(expected - names)}")
        if archive.testzip() is not None:
            raise ValueError("generated zipmod failed CRC validation")

    report = {
        "source_full_zipmod": str(full_path),
        "source_formaker_zipmod": str(maker_path),
        "output": str(output_path),
        "csv_path": CSV_ARCHIVE_PATH,
        "ik_path": IK_ARCHIVE_PATH,
        "csv": csv_report,
        "references": reference_check,
        "output_size": output_path.stat().st_size,
    }
    report_path = output_path.with_suffix(output_path.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, required=True, help="full KK Animations sample zipmod")
    parser.add_argument("--maker", type=Path, required=True, help="original ForMaker zipmod")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    report = build(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
