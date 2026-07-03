from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path


VENDOR = Path(__file__).resolve().parents[1] / "backend" / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import UnityPy  # type: ignore  # noqa: E402


def decode_csv(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("/")


def find_header(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows):
        columns = {cell.strip() for cell in row}
        if {"ID", "Name"}.issubset(columns):
            return index
    return None


def read_refs(zf: zipfile.ZipFile) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for name in sorted(zf.namelist()):
        normalized = normalize(name)
        if not normalized.lower().startswith("abdata/list/"):
            continue
        if not normalized.lower().endswith(".csv"):
            continue

        rows = list(csv.reader(io.StringIO(decode_csv(zf.read(name)))))
        header_index = find_header(rows)
        if header_index is None:
            continue
        header = [cell.strip() for cell in rows[header_index]]
        list_kind = rows[0][0].strip() if rows and rows[0] else ""
        for row in rows[header_index + 1 :]:
            if not row or all(not cell.strip() for cell in row):
                continue
            padded = row + [""] * max(0, len(header) - len(row))
            item = dict(zip(header, padded))
            refs.append(
                {
                    "csv_path": normalized,
                    "list_kind": list_kind,
                    "id": (item.get("ID") or "").strip(),
                    "name": (item.get("Name") or "").strip(),
                    "thumb_ab": (item.get("ThumbAB") or "").strip(),
                    "thumb_tex": (item.get("ThumbTex") or "").strip(),
                }
            )
    return refs


def find_member(zf: zipfile.ZipFile, target: str) -> str | None:
    target = normalize(target).lower()
    for name in zf.namelist():
        if normalize(name).lower() == target:
            return name
    return None


def list_bundle_images(data: bytes) -> list[dict[str, object]]:
    env = UnityPy.load(data)
    images: list[dict[str, object]] = []
    for container_path, obj in env.container.items():
        path = str(container_path).replace("\\", "/")
        try:
            asset = obj.read()
            image = getattr(asset, "image", None)
            if image is None:
                continue
            name = getattr(asset, "name", "") or ""
            images.append(
                {
                    "source": "container",
                    "key": path,
                    "name": name,
                    "type": obj.type.name,
                    "size": image.size,
                }
            )
        except Exception as exc:  # noqa: BLE001
            images.append({"source": "container", "key": path, "error": str(exc)})

    for obj in env.objects:
        if obj.type.name not in {"Texture2D", "Sprite"}:
            continue
        try:
            asset = obj.read()
            image = getattr(asset, "image", None)
            if image is None:
                continue
            name = getattr(asset, "name", "") or ""
            images.append(
                {
                    "source": "object",
                    "key": name,
                    "name": name,
                    "type": obj.type.name,
                    "size": image.size,
                }
            )
        except Exception as exc:  # noqa: BLE001
            images.append({"source": "object", "key": "", "error": str(exc)})
    return images


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zipmod", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    zipmod = args.zipmod.resolve()
    with zipfile.ZipFile(zipmod, "r") as zf:
        refs = read_refs(zf)
        print(f"zipmod: {zipmod}")
        print(f"csv thumbnail refs: {len(refs)}")
        for ref in refs[: args.limit]:
            source = f"abdata/{normalize(ref['thumb_ab'])}"
            member = find_member(zf, source)
            print()
            print(
                f"item {ref['id']} kind={ref['list_kind']} name={ref['name']} "
                f"thumb_ab={ref['thumb_ab']} thumb_tex={ref['thumb_tex']}"
            )
            print(f"source member: {member or 'NOT FOUND'}")
            if member is None:
                continue
            images = list_bundle_images(zf.read(member))
            print(f"image assets in source: {len(images)}")
            target = ref["thumb_tex"].lower()
            matches = [
                image for image in images if target and target in str(image.get("key", "")).lower()
            ]
            print(f"assets containing thumb_tex: {len(matches)}")
            for image in (matches or images)[: args.limit]:
                print(image)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
