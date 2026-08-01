"""Restore the fixed NB prefix in protected Unity3D files and repackage zipmods.

The NB format observed in the kinshin007 samples changes only the first 529
bytes.  A matching encrypted/plain pair is used to derive the position-wise
XOR mask; every candidate is validated as a UnityFS bundle before being
written to a separate output tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


PREFIX_SIZE = 529
NB_MAGIC = b"NB"
UNITYFS_MAGIC = b"UnityFS\x00"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def derive_mask(encrypted: bytes, plain: bytes) -> bytes:
    if len(encrypted) != len(plain):
        raise ValueError("mask pair has different file sizes")
    if encrypted[PREFIX_SIZE:] != plain[PREFIX_SIZE:]:
        raise ValueError("mask pair does not share an identical suffix")
    return bytes(a ^ b for a, b in zip(encrypted[:PREFIX_SIZE], plain[:PREFIX_SIZE]))


def restore_prefix(data: bytes, mask: bytes) -> bytes:
    if len(mask) != PREFIX_SIZE:
        raise ValueError("invalid mask length")
    if not data.startswith(NB_MAGIC):
        return data
    if len(data) < PREFIX_SIZE:
        raise ValueError("NB file is shorter than the protected prefix")
    restored = bytearray(data)
    restored[:PREFIX_SIZE] = bytes(a ^ b for a, b in zip(data[:PREFIX_SIZE], mask))
    if not restored.startswith(UNITYFS_MAGIC):
        raise ValueError("restored prefix is not UnityFS")
    return bytes(restored)


def validate_unityfs(data: bytes) -> tuple[str, int]:
    # Import the project's parser so validation follows the same rules as the
    # application.  The script is run from the repository's apps directory.
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import decrypt_unity3d as decoder  # type: ignore

    header = decoder.parse_bundle_header(data)
    if header.declared_size != len(data):
        raise ValueError(
            f"declared size {header.declared_size} != actual size {len(data)}"
        )
    info = decoder.parse_blocks_info(decoder.decode_blocks_info(data, header))
    if not info.nodes:
        raise ValueError("UnityFS has no nodes")
    return header.unity_revision, len(info.nodes)


def transform_zipmod(source: Path, destination: Path, mask: bytes) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    entries = 0
    unity_entries = 0
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(
        destination, "w", allowZip64=True
    ) as out:
        for info in src.infolist():
            payload = src.read(info.filename)
            entries += 1
            if info.filename.lower().endswith(".unity3d"):
                unity_entries += 1
                if payload.startswith(NB_MAGIC):
                    payload = restore_prefix(payload, mask)
                    revision, node_count = validate_unityfs(payload)
                    changed.append(
                        f"{info.filename} (Unity {revision}, {node_count} nodes)"
                    )
                else:
                    validate_unityfs(payload)
            out.writestr(info, payload)
    return {
        "source": str(source),
        "output": str(destination),
        "entries": entries,
        "unity3d_entries": unity_entries,
        "decrypted_entries": len(changed),
        "decrypted": changed,
        "sha256": sha256(destination.read_bytes()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--encrypted-pair", type=Path, required=True)
    parser.add_argument("--plain-pair", type=Path, required=True)
    args = parser.parse_args()

    mask = derive_mask(args.encrypted_pair.read_bytes(), args.plain_pair.read_bytes())
    sources = sorted(args.input_root.rglob("*.zipmod"))
    results: list[dict] = []
    for source in sources:
        relative = source.relative_to(args.input_root)
        destination = args.output_root / relative
        try:
            result = transform_zipmod(source, destination, mask)
            result["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            result = {"source": str(source), "status": "error", "error": str(exc)}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))

    args.output_root.mkdir(parents=True, exist_ok=True)
    report = args.output_root / "restore_report.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    errors = sum(result.get("status") != "ok" for result in results)
    print(json.dumps({"zipmods": len(results), "errors": errors, "report": str(report)}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
