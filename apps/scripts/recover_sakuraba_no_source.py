r"""Recover the observed Sakuraba 26-3-S01 bundle without a normal template.

This is deliberately a profile-specific recovery tool for the sample discussed
in the project notes.  It reads only the protected Unity3D input.  The small
serialized-metadata bootstrap below is an embedded Unity 2018/Sakuraba format
fragment; it is not loaded from a normal asset file.

The protection observed in this sample has two deterministic layout effects:

* serialized metadata/object data after offset 0x96 is shifted by 16 bytes;
* the embedded .resS stream has the relation protected[16:] == normal[:-16].

The missing final 16 bytes cannot be recovered uniquely from the protected
file.  They are filled with the requested value and recorded in the report.
The source file is never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import UnityPy
except ImportError:  # pragma: no cover - optional validation dependency
    UnityPy = None

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from decrypt_unity3d import (  # noqa: E402
    decode_blocks_info,
    decode_bundle_stream,
    encode_bundle_stream,
    parse_blocks_info,
    parse_bundle_header,
    parse_serialized_metadata,
)


PROFILE_NAME = "sakuraba-26-3-s01-no-source"
UNITY_REVISION = "2018.4.11f1"
PROTECTED_PREFIX_SIZE = 0x96
ALIGNMENT_SHIFT = 0x10
METADATA_SIZE = 0x1DF75
SERIALIZED_DATA_OFFSET = 0x1DF90
ENCRYPTED_DATA_OFFSET = SERIALIZED_DATA_OFFSET + ALIGNMENT_SHIFT
UNKNOWN_TAIL_SIZE = 0x10

# Bytes 0..0x95 of the repaired SerializedFile.  This is the only embedded
# profile data; it is enough to restore the standard header and the beginning
# of the first TypeTree record.  The remaining TypeTree/object metadata is
# copied from the protected input after its 16-byte insertion.
BOOTSTRAP_PREFIX = bytes.fromhex(
    "0001df75029bae9c000000110001df9000000000323031382e342e313166310013000000"
    "01150000007300000000fffff46e8e30ecc293493f18ab27134210ee23000000e700000005"
    "0000001501008037000080ffffffff00000000008000000100010048030080ab010080ffff"
    "ffff0100000001800800010002013100008031000080ffffffff0200000001400800010003"
    "00de00"
)


class RecoveryError(RuntimeError):
    pass


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def fill_bytes(mode: str, size: int) -> bytes:
    if mode == "zero":
        return b"\x00" * size
    if mode == "ff":
        return b"\xff" * size
    raise RecoveryError(f"Unsupported tail fill mode: {mode}")


def default_output(source: Path) -> Path:
    suffix = ".no-source-recovered.unity3d"
    if source.name.lower().endswith(".unity3d"):
        return source.with_name(source.name[: -len(".unity3d")] + suffix)
    return source.with_name(source.name + suffix)


def load_bundle(path: Path):
    data = path.read_bytes()
    header = parse_bundle_header(data)
    info = parse_blocks_info(decode_blocks_info(data, header))
    stream = decode_bundle_stream(data, header, info)
    return data, header, info, stream


def recover_serialized_node(payload: bytes, tail_fill: bytes) -> tuple[bytes, dict]:
    if len(BOOTSTRAP_PREFIX) != PROTECTED_PREFIX_SIZE:
        raise RecoveryError("Internal bootstrap prefix has an invalid length.")
    if len(payload) < ENCRYPTED_DATA_OFFSET + UNKNOWN_TAIL_SIZE:
        raise RecoveryError("Serialized node is too small for the known profile.")
    if int.from_bytes(payload[0:4], "big") != METADATA_SIZE:
        raise RecoveryError(
            "Serialized metadata size does not match the Sakuraba 26-3-S01 profile."
        )
    metadata_end = 20 + METADATA_SIZE
    if metadata_end > SERIALIZED_DATA_OFFSET:
        raise RecoveryError("Profile metadata end exceeds the aligned data offset.")

    # The protected node contains 16 inserted/protected bytes at 0x96.  Its
    # bytes at 0xA6 onward correspond to normal bytes at 0x96 onward.
    repaired = bytearray()
    repaired += BOOTSTRAP_PREFIX
    repaired += payload[PROTECTED_PREFIX_SIZE + ALIGNMENT_SHIFT : metadata_end + ALIGNMENT_SHIFT]
    repaired += b"\x00" * (SERIALIZED_DATA_OFFSET - len(repaired))
    repaired += payload[ENCRYPTED_DATA_OFFSET:]
    repaired += tail_fill

    if len(repaired) != len(payload):
        raise RecoveryError(
            f"Recovered SerializedFile length {len(repaired)} differs from input "
            f"node length {len(payload)}."
        )
    repaired[4:8] = len(repaired).to_bytes(4, "big")
    repaired[8:12] = (17).to_bytes(4, "big")
    repaired[12:16] = SERIALIZED_DATA_OFFSET.to_bytes(4, "big")
    parsed = parse_serialized_metadata(repaired)
    for byte_start, byte_size in parsed.object_ranges:
        end = SERIALIZED_DATA_OFFSET + byte_start + byte_size
        if end > len(repaired):
            raise RecoveryError(
                f"Object range ends at 0x{end:x}, past SerializedFile length 0x{len(repaired):x}."
            )
    return bytes(repaired), {
        "metadata_size": METADATA_SIZE,
        "metadata_end": metadata_end,
        "data_offset": SERIALIZED_DATA_OFFSET,
        "protected_data_offset": ENCRYPTED_DATA_OFFSET,
        "node_size": len(payload),
        "object_count": parsed.object_count,
        "type_count": parsed.type_count,
        "unknown_tail_offset": len(repaired) - UNKNOWN_TAIL_SIZE,
        "unknown_tail_size": UNKNOWN_TAIL_SIZE,
    }


def recover_resource_node(payload: bytes, tail_fill: bytes) -> tuple[bytes, dict]:
    if len(payload) <= UNKNOWN_TAIL_SIZE:
        raise RecoveryError(".resS node is too small for the known 16-byte shift.")
    repaired = payload[ALIGNMENT_SHIFT:] + tail_fill
    if len(repaired) != len(payload):
        raise RecoveryError("Recovered .resS length differs from input length.")
    return repaired, {
        "protected_prefix_discarded": ALIGNMENT_SHIFT,
        "unknown_tail_size": UNKNOWN_TAIL_SIZE,
        "unknown_tail_offset": len(repaired) - UNKNOWN_TAIL_SIZE,
    }


def validate_with_unitypy(path: Path) -> dict:
    if UnityPy is None:
        return {"available": False, "error": "UnityPy is not installed."}
    try:
        environment = UnityPy.load(str(path))
        type_counts: dict[str, int] = {}
        texture_count = 0
        texture_decodable = 0
        for obj in environment.objects:
            type_name = obj.type.name
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            if type_name != "Texture2D":
                continue
            texture_count += 1
            try:
                obj.read().get_image_data()
            except Exception:
                continue
            texture_decodable += 1
        return {
            "available": True,
            "object_count": len(environment.objects),
            "type_counts": type_counts,
            "texture_count": texture_count,
            "texture_decodable_count": texture_decodable,
        }
    except Exception as exc:  # noqa: BLE001
        return {"available": True, "error": repr(exc)}


def normalize_encoded_bundle(data: bytes | bytearray, declared_size: int, size_offset: int) -> bytearray:
    rebuilt = bytearray(data)
    if len(rebuilt) > declared_size:
        rebuilt = rebuilt[:declared_size]
    if len(rebuilt) != declared_size:
        raise RecoveryError(
            f"Rebuilt bundle length {len(rebuilt)} does not match declared boundary "
            f"{declared_size}."
        )
    rebuilt[size_offset : size_offset + 8] = len(rebuilt).to_bytes(8, "big")
    return rebuilt


def infer_transform_tail_patch(path: Path, tail_fill: bytes, serialized_report: dict) -> dict | None:
    """Recover a missing Transform.m_Father pointer from its child inverse link.

    This is a data-structure inference, not a template lookup.  It is only
    applied when exactly one Transform reaches the serialized node end and
    exactly one other Transform lists it in m_Children.
    """
    if UnityPy is None:
        return None
    try:
        environment = UnityPy.load(str(path))
        candidates = []
        for obj in environment.objects:
            if obj.type.name != "Transform":
                continue
            end = int(obj.byte_start) + int(obj.byte_size)
            if end == int(serialized_report["node_size"]):
                candidates.append(obj)
        if len(candidates) != 1:
            return None
        target = candidates[0]
        if int(target.byte_size) < UNKNOWN_TAIL_SIZE:
            return None
        target_tree = target.read_typetree()
        target_id = int(target.path_id)
        parent_ids = []
        for obj in environment.objects:
            if obj.type.name != "Transform" or obj.path_id == target.path_id:
                continue
            tree = obj.read_typetree()
            for child in tree.get("m_Children", []) or []:
                if int(child.get("m_PathID", 0)) == target_id:
                    parent_ids.append(int(obj.path_id))
        if len(set(parent_ids)) != 1:
            return None
        parent_id = next(iter(set(parent_ids)))
        raw, header, info, stream = load_bundle(path)
        serialized_node = next(node for node in info.nodes if node.flags & 4)
        patch_start = (
            serialized_node.offset
            + int(target.byte_start)
            + int(target.byte_size)
            - UNKNOWN_TAIL_SIZE
        )
        if bytes(stream[patch_start : patch_start + UNKNOWN_TAIL_SIZE]) != tail_fill:
            return None
        patch = b"\x00" * 8 + parent_id.to_bytes(8, "little", signed=True)
        return {
            "path_id": target_id,
            "type": "Transform",
            "parent_path_id": parent_id,
            "stream_offset": patch_start,
            "bytes": patch,
            "raw": raw,
            "header": header,
            "info": info,
            "stream": stream,
        }
    except Exception:  # noqa: BLE001
        return None


def recover(source: Path, output: Path, tail_mode: str, overwrite: bool) -> dict:
    if output.exists() and not overwrite:
        raise RecoveryError(f"Output already exists: {output}")
    raw, header, info, stream = load_bundle(source)
    if header.unity_revision != UNITY_REVISION:
        raise RecoveryError(
            f"This profile supports Unity revision {UNITY_REVISION}, got {header.unity_revision}."
        )
    serialized = [node for node in info.nodes if node.flags & 4]
    resources = [node for node in info.nodes if node.name.lower().endswith(b".ress")]
    if len(serialized) != 1 or len(resources) != 1:
        raise RecoveryError(
            f"Expected one SerializedFile and one .resS node, got {len(serialized)} and {len(resources)}."
        )
    tail_fill = fill_bytes(tail_mode, UNKNOWN_TAIL_SIZE)
    working = bytearray(stream)
    serialized_node = serialized[0]
    resource_node = resources[0]
    serialized_payload = bytes(
        working[serialized_node.offset : serialized_node.offset + serialized_node.size]
    )
    resource_payload = bytes(
        working[resource_node.offset : resource_node.offset + resource_node.size]
    )
    repaired_serialized, serialized_report = recover_serialized_node(
        serialized_payload, tail_fill
    )
    repaired_resource, resource_report = recover_resource_node(resource_payload, tail_fill)
    working[serialized_node.offset : serialized_node.offset + serialized_node.size] = repaired_serialized
    working[resource_node.offset : resource_node.offset + resource_node.size] = repaired_resource
    rebuilt, _, _ = encode_bundle_stream(raw, header, info, bytes(working))
    # This protected sample has 16 physical bytes after the UnityFS declared
    # boundary.  They are not part of any storage block or node; do not carry
    # them into the recovered bundle.
    rebuilt = normalize_encoded_bundle(rebuilt, header.declared_size, header.size_offset)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rebuilt)

    heuristic_patch = infer_transform_tail_patch(output, tail_fill, serialized_report)
    if heuristic_patch is not None:
        patched_stream = bytearray(heuristic_patch["stream"])
        patch_start = int(heuristic_patch["stream_offset"])
        patched_stream[patch_start : patch_start + UNKNOWN_TAIL_SIZE] = heuristic_patch["bytes"]
        repacked, _, _ = encode_bundle_stream(
            heuristic_patch["raw"],
            heuristic_patch["header"],
            heuristic_patch["info"],
            bytes(patched_stream),
        )
        rebuilt = normalize_encoded_bundle(
            repacked,
            heuristic_patch["header"].declared_size,
            heuristic_patch["header"].size_offset,
        )
        output.write_bytes(rebuilt)

    final_raw, final_header, final_info, final_stream = load_bundle(output)
    final_serialized = next(node for node in final_info.nodes if node.flags & 4)
    final_payload = final_stream[
        final_serialized.offset : final_serialized.offset + final_serialized.size
    ]
    parsed = parse_serialized_metadata(final_payload)
    validation = validate_with_unitypy(output)
    report = {
        "profile": PROFILE_NAME,
        "source": str(source),
        "output": str(output),
        "source_sha256": sha256(raw),
        "output_sha256": sha256(rebuilt),
        "source_size": len(raw),
        "output_size": len(rebuilt),
        "declared_size": final_header.declared_size,
        "tail_fill": tail_mode,
        "tail_fill_sha256": sha256(tail_fill),
        "serialized_node": serialized_report,
        "resource_node": resource_report,
        "heuristic_object_tail_repair": (
            {
                key: value
                for key, value in heuristic_patch.items()
                if key in {"path_id", "type", "parent_path_id", "stream_offset"}
            }
            if heuristic_patch is not None
            else None
        ),
        "final_object_count": parsed.object_count,
        "final_type_count": parsed.type_count,
        "unitypy_validation": validation,
        "notes": [
            "The output is reconstructed from the protected input only.",
            "The final 16 bytes of the recovered SerializedFile tail and .resS tail are not uniquely known.",
            "The script may infer a missing Transform.m_Father pointer from a unique inverse m_Children link.",
            "Any remaining zero-fill is a structural placeholder, not a claim about the original bytes.",
        ],
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover the analyzed Sakuraba 26-3-S01 UnityFS file without a normal original."
    )
    parser.add_argument("input", type=Path, help="Protected .unity3d input file.")
    parser.add_argument("-o", "--output", type=Path, help="Output recovery path.")
    parser.add_argument(
        "--tail-fill",
        choices=("zero", "ff"),
        default="zero",
        help="Placeholder for the unrecoverable final 16 bytes (default: zero).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file.")
    parser.add_argument("--report", type=Path, help="Optional JSON report path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.input.resolve()
    output = (args.output or default_output(source)).resolve()
    try:
        if source == output:
            raise RecoveryError("Input and output must be different files.")
        report = recover(source, output, args.tail_fill, args.overwrite)
    except (OSError, RecoveryError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    report["status"] = "ok"
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    report_path = (args.report or output.with_suffix(output.suffix + ".json")).resolve()
    report_path.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
