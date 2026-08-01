"""Recover XT UnityFS bundles protected by a four-byte marker and repeating XOR.

The corresponding resourceKit plugin strips the first four bytes and XORs the
remaining payload with a 20-byte file key. UnityFS has a deterministic 20-byte
prefix, so the file key can be recovered without the original machine ID.
Sources are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


XT_MARKER = b"\x01\x03\x03\x01"
UNITYFS_PREFIX = b"UnityFS\x00\x00\x00\x00\x06" + b"5.x.x\x00" + b"20"
KEY_LENGTH = len(UNITYFS_PREFIX)


def xor_repeating(data: bytes, key: bytes) -> bytes:
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def validate_unityfs_header(data: bytes) -> dict[str, object]:
    if not data.startswith(b"UnityFS\x00"):
        raise ValueError("Recovered payload is not a UnityFS bundle.")
    if len(data) < 40:
        raise ValueError("Recovered UnityFS header is truncated.")

    format_version = struct.unpack_from(">I", data, 8)[0]
    unity_version_end = data.find(b"\x00", 12)
    revision_end = data.find(b"\x00", unity_version_end + 1)
    if unity_version_end < 0 or revision_end < 0:
        raise ValueError("Recovered UnityFS version strings are malformed.")

    unity_version = data[12:unity_version_end].decode("ascii", "strict")
    unity_revision = data[unity_version_end + 1 : revision_end].decode("ascii", "strict")
    declared_size = struct.unpack_from(">Q", data, revision_end + 1)[0]
    if format_version != 6 or unity_version != "5.x.x":
        raise ValueError("Recovered UnityFS header has unexpected version fields.")
    if declared_size != len(data):
        raise ValueError(
            f"Recovered UnityFS declared size {declared_size} does not match {len(data)} bytes."
        )
    return {
        "format_version": format_version,
        "unity_version": unity_version,
        "unity_revision": unity_revision,
        "declared_size": declared_size,
    }


def recover(source: Path, output: Path, overwrite: bool = False) -> dict[str, object]:
    protected = source.read_bytes()
    if not protected.startswith(XT_MARKER):
        raise ValueError("File does not start with the XT 01 03 03 01 marker.")

    encrypted = protected[len(XT_MARKER) :]
    if len(encrypted) < KEY_LENGTH:
        raise ValueError("Encrypted payload is too short to recover its XOR key.")

    key = bytes(
        encrypted[index] ^ UNITYFS_PREFIX[index]
        for index in range(KEY_LENGTH)
    )
    decrypted = xor_repeating(encrypted, key)
    if not decrypted.startswith(UNITYFS_PREFIX):
        raise ValueError("Recovered payload does not have the expected UnityFS prefix.")
    header = validate_unityfs_header(decrypted)

    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(decrypted)

    return {
        "source": str(source),
        "output": str(output),
        "source_size": len(protected),
        "output_size": len(decrypted),
        "xor_key_hex": key.hex(),
        "unityfs": header,
        "source_sha256": hashlib.sha256(protected).hexdigest(),
        "output_sha256": hashlib.sha256(decrypted).hexdigest(),
    }


def classify(path: Path) -> str:
    with path.open("rb") as stream:
        header = stream.read(8)
    if header.startswith(XT_MARKER):
        return "encrypted"
    if header == b"UnityFS\x00":
        return "unityfs"
    return "unknown"


def recover_directory(
    source_root: Path,
    output_root: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if output_root == source_root or source_root in output_root.parents:
        raise ValueError("Output directory must be outside the source directory.")

    results: list[dict[str, object]] = []
    for source in sorted(source_root.rglob("*.unity3d")):
        relative = source.relative_to(source_root)
        kind = classify(source)
        if kind != "encrypted":
            results.append({
                "source": str(source),
                "relative_path": str(relative),
                "status": "skipped",
                "message": "Already standard UnityFS." if kind == "unityfs" else "Unknown format.",
            })
            continue

        output = output_root / relative.with_name(f"{relative.stem}.decrypted.unity3d")
        try:
            result = recover(source, output, overwrite)
            result.update({"relative_path": str(relative), "status": "ok"})
        except Exception as exc:
            result = {
                "source": str(source),
                "output": str(output),
                "relative_path": str(relative),
                "status": "error",
                "message": str(exc),
            }
        results.append(result)

    return {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "total": len(results),
        "ok": sum(item["status"] == "ok" for item in results),
        "skipped": sum(item["status"] == "skipped" for item in results),
        "errors": sum(item["status"] == "error" for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    if args.source.is_dir():
        result = recover_directory(args.source, args.output, args.overwrite)
    else:
        result = recover(args.source, args.output, args.overwrite)

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if isinstance(result, dict) and result.get("errors", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
