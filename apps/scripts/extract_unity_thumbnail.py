from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


VENDOR = Path(__file__).resolve().parents[1] / "backend" / ".vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

import UnityPy  # type: ignore  # noqa: E402


def read_thumb_refs(csv_path: Path) -> list[dict[str, str]]:
    text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.reader(text.splitlines()))
    header_index = next(
        i for i, row in enumerate(rows) if "ThumbAB" in row and "ThumbTex" in row
    )
    header = rows[header_index]
    refs: list[dict[str, str]] = []
    for row in rows[header_index + 1 :]:
        if not row or all(not cell.strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        item = dict(zip(header, padded))
        if item.get("ThumbAB") and item.get("ThumbTex"):
            refs.append(item)
    return refs


def save_named_image(bundle_path: Path, asset_name: str, output_path: Path) -> str:
    env = UnityPy.load(str(bundle_path))
    available: list[str] = []

    for container_path, obj in env.container.items():
        path = str(container_path).replace("\\", "/")
        stem = Path(path).stem
        name = Path(path).name
        if asset_name not in {path, stem, name}:
            continue

        data = obj.read()
        image = getattr(data, "image", None)
        if image is None:
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return path

    for obj in env.objects:
        if obj.type.name not in {"Texture2D", "Sprite"}:
            continue
        data = obj.read()
        name = getattr(data, "name", "") or ""
        if name:
            available.append(name)
        if name != asset_name:
            continue

        image = getattr(data, "image", None)
        if image is None:
            raise RuntimeError(f"Asset '{asset_name}' has no readable image data.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return name

    container_names = [Path(str(key).replace("\\", "/")).name for key in env.container.keys()]
    available_text = ", ".join(sorted(set(available + container_names))[:50])
    raise RuntimeError(
        f"Thumbnail asset '{asset_name}' was not found in {bundle_path}. "
        f"Available image-like assets: {available_text}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mod_root", type=Path)
    parser.add_argument("--csv", dest="csv_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("test/extracted_thumbnails"))
    args = parser.parse_args()

    mod_root = args.mod_root.resolve()
    csv_paths = [args.csv_path] if args.csv_path else list((mod_root / "abdata" / "list").rglob("*.csv"))
    if not csv_paths:
        raise RuntimeError(f"No CSV list files found under {mod_root / 'abdata' / 'list'}")

    exported: list[Path] = []
    for csv_path in csv_paths:
        csv_path = csv_path.resolve()
        for row in read_thumb_refs(csv_path):
            bundle_path = mod_root / "abdata" / row["ThumbAB"].replace("/", "\\")
            asset_name = row["ThumbTex"]
            item_name = row.get("Name") or asset_name
            item_id = row.get("ID") or "item"
            file_stem = f"{item_id}_{item_name}"
            safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in file_stem)
            output_path = args.output_dir.resolve() / f"{safe_name}_{asset_name}.png"
            save_named_image(bundle_path, asset_name, output_path)
            exported.append(output_path)
            print(output_path)

    if not exported:
        raise RuntimeError("No thumbnail references were exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
