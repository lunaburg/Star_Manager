r"""Batch-repair the Sakuraba-style UnityFS protection seen in HS2 assets.

Example (PowerShell):

    python apps/scripts/decrypt_unity3d.py `
      "E:\protected-assets" `
      --output-dir "E:\decrypted-assets" `
      --template-root "E:\game\hs2\abdata"

Sources are never modified. Files without an exact Unity revision and TypeTree
fingerprint match are reported as failures instead of being written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import lz4.block
except ImportError as exc:  # pragma: no cover - environment-dependent error path
    raise SystemExit(
        "Missing dependency 'lz4'. Install apps/backend/requirements.txt first."
    ) from exc


PROTECTION_MARKER = bytes.fromhex("455a975ae1cab99356b210fc7c4c6c59")
UNITYFS_SIGNATURE = b"UnityFS\x00"
ARCHIVE_RESOURCE_PATTERN = re.compile(
    rb"archive:/([^/\x00]+)/([^/\x00]+?\.(?:resS|resource))\x00",
    re.IGNORECASE,
)
DEFAULT_SUFFIX = ".decrypted.unity3d"
TEMPLATE_FINGERPRINT_SIZE = 64


class UnityDecryptError(RuntimeError):
    pass


@dataclass
class BundleHeader:
    format_version: int
    unity_version: str
    unity_revision: str
    declared_size: int
    compressed_info_size: int
    uncompressed_info_size: int
    flags: int
    size_offset: int
    compressed_size_offset: int
    header_end: int


@dataclass
class StorageBlock:
    uncompressed_size: int
    compressed_size: int
    flags: int


@dataclass
class BundleNode:
    offset: int
    size: int
    flags: int
    name: bytes

    @property
    def decoded_name(self) -> str:
        return self.name.decode("utf-8", errors="replace")


@dataclass
class BlocksInfo:
    digest: bytes
    blocks: list[StorageBlock]
    nodes: list[BundleNode]


@dataclass
class ParsedMetadata:
    unity_version: str
    type_count: int
    class_ids: list[int]
    object_count: int
    object_ranges: list[tuple[int, int]]
    script_count: int
    externals: list[str]
    end_offset: int


@dataclass
class Template:
    source: Path
    unity_revision: str
    prefix: bytes


@dataclass
class RepairResult:
    source: Path
    output: Path | None
    status: str
    message: str
    sha256: str = ""
    repaired_nodes: int = 0


def read_cstring(data: bytes | bytearray, offset: int) -> tuple[bytes, int]:
    end = data.find(b"\x00", offset)
    if end < 0:
        raise UnityDecryptError(f"Missing NUL terminator at offset 0x{offset:x}.")
    return bytes(data[offset:end]), end + 1


def parse_bundle_header(data: bytes | bytearray) -> BundleHeader:
    if not data.startswith(UNITYFS_SIGNATURE):
        raise UnityDecryptError("Not a UnityFS bundle.")
    offset = len(UNITYFS_SIGNATURE)
    if offset + 4 > len(data):
        raise UnityDecryptError("Truncated UnityFS header.")
    format_version = int.from_bytes(data[offset : offset + 4], "big")
    offset += 4
    unity_version_raw, offset = read_cstring(data, offset)
    unity_revision_raw, offset = read_cstring(data, offset)
    if offset + 20 > len(data):
        raise UnityDecryptError("Truncated UnityFS size fields.")
    size_offset = offset
    declared_size = int.from_bytes(data[offset : offset + 8], "big")
    compressed_size_offset = offset + 8
    compressed_info_size = int.from_bytes(data[offset + 8 : offset + 12], "big")
    uncompressed_info_size = int.from_bytes(data[offset + 12 : offset + 16], "big")
    flags = int.from_bytes(data[offset + 16 : offset + 20], "big")
    header_end = offset + 20
    if format_version >= 7:
        header_end = (header_end + 15) & ~15
    return BundleHeader(
        format_version=format_version,
        unity_version=unity_version_raw.decode("ascii", errors="replace"),
        unity_revision=unity_revision_raw.decode("ascii", errors="replace"),
        declared_size=declared_size,
        compressed_info_size=compressed_info_size,
        uncompressed_info_size=uncompressed_info_size,
        flags=flags,
        size_offset=size_offset,
        compressed_size_offset=compressed_size_offset,
        header_end=header_end,
    )


def decompress_payload(payload: bytes, output_size: int, compression: int) -> bytes:
    if compression == 0:
        if len(payload) != output_size:
            raise UnityDecryptError(
                f"Uncompressed block has size {len(payload)}, expected {output_size}."
            )
        return payload
    if compression in (2, 3):
        try:
            result = lz4.block.decompress(payload, uncompressed_size=output_size)
        except Exception as exc:  # noqa: BLE001
            raise UnityDecryptError(f"LZ4 decompression failed: {exc}") from exc
        if len(result) != output_size:
            raise UnityDecryptError(
                f"LZ4 output has size {len(result)}, expected {output_size}."
            )
        return result
    raise UnityDecryptError(f"Unsupported Unity compression type {compression}.")


def compress_payload(payload: bytes, compression: int) -> bytes:
    if compression == 0:
        return payload
    if compression in (2, 3):
        mode = "high_compression" if compression == 3 else "default"
        return lz4.block.compress(payload, mode=mode, store_size=False)
    raise UnityDecryptError(f"Unsupported Unity compression type {compression}.")


def decode_blocks_info(data: bytes | bytearray, header: BundleHeader) -> bytes:
    start = header.header_end
    end = start + header.compressed_info_size
    if end > len(data):
        raise UnityDecryptError("Compressed block-info region extends past the file.")
    return decompress_payload(
        bytes(data[start:end]),
        header.uncompressed_info_size,
        header.flags & 0x3F,
    )


def parse_blocks_info(payload: bytes) -> BlocksInfo:
    if len(payload) < 20:
        raise UnityDecryptError("Truncated UnityFS block-info payload.")
    digest = payload[:16]
    block_count = int.from_bytes(payload[16:20], "big")
    if not 0 < block_count < 100_000:
        raise UnityDecryptError(f"Invalid storage block count {block_count}.")
    offset = 20
    blocks: list[StorageBlock] = []
    for _ in range(block_count):
        if offset + 10 > len(payload):
            raise UnityDecryptError("Truncated storage block table.")
        blocks.append(
            StorageBlock(
                uncompressed_size=int.from_bytes(payload[offset : offset + 4], "big"),
                compressed_size=int.from_bytes(payload[offset + 4 : offset + 8], "big"),
                flags=int.from_bytes(payload[offset + 8 : offset + 10], "big"),
            )
        )
        offset += 10
    if offset + 4 > len(payload):
        raise UnityDecryptError("Missing UnityFS node count.")
    node_count = int.from_bytes(payload[offset : offset + 4], "big")
    offset += 4
    if not 0 < node_count < 100_000:
        raise UnityDecryptError(f"Invalid bundle node count {node_count}.")
    nodes: list[BundleNode] = []
    for _ in range(node_count):
        if offset + 20 > len(payload):
            raise UnityDecryptError("Truncated UnityFS node table.")
        node_offset = int.from_bytes(payload[offset : offset + 8], "big")
        node_size = int.from_bytes(payload[offset + 8 : offset + 16], "big")
        node_flags = int.from_bytes(payload[offset + 16 : offset + 20], "big")
        offset += 20
        name, offset = read_cstring(payload, offset)
        nodes.append(BundleNode(node_offset, node_size, node_flags, name))
    if offset != len(payload):
        raise UnityDecryptError(
            f"Block-info payload has {len(payload) - offset} unexpected trailing bytes."
        )
    return BlocksInfo(digest, blocks, nodes)


def encode_blocks_info(info: BlocksInfo) -> bytes:
    output = bytearray(info.digest)
    output += len(info.blocks).to_bytes(4, "big")
    for block in info.blocks:
        output += block.uncompressed_size.to_bytes(4, "big")
        output += block.compressed_size.to_bytes(4, "big")
        output += block.flags.to_bytes(2, "big")
    output += len(info.nodes).to_bytes(4, "big")
    for node in info.nodes:
        output += node.offset.to_bytes(8, "big")
        output += node.size.to_bytes(8, "big")
        output += node.flags.to_bytes(4, "big")
        output += node.name + b"\x00"
    return bytes(output)


def resource_names_from_data(data: bytes | bytearray) -> list[bytes]:
    names: list[bytes] = []
    seen: set[bytes] = set()
    for match in ARCHIVE_RESOURCE_PATTERN.finditer(data):
        name = match.group(2)
        lowered = name.lower()
        if lowered not in seen:
            seen.add(lowered)
            names.append(name)
    return names


def repair_corrupted_node_names(info: BlocksInfo, bundle_data: bytes) -> bool:
    candidates = resource_names_from_data(bundle_data)
    if not candidates:
        return False
    changed = False
    used: set[bytes] = set()
    for node in info.nodes:
        lowered = node.name.lower()
        valid = (
            lowered.startswith(b"cab-")
            and (lowered.endswith(b".ress") or lowered.endswith(b".resource"))
        )
        if valid or node.flags & 4:
            continue
        matches = [candidate for candidate in candidates if candidate.lower() not in used]
        if len(matches) != 1:
            continue
        node.name = matches[0]
        used.add(matches[0].lower())
        changed = True
    return changed


def normalize_inserted_marker(data: bytes) -> tuple[bytearray, BundleHeader, BlocksInfo, str]:
    current = bytearray(data)
    header = parse_bundle_header(current)
    layer = "none"
    try:
        info = parse_blocks_info(decode_blocks_info(current, header))
    except UnityDecryptError:
        search_end = min(len(current), header.header_end + header.compressed_info_size + 16)
        marker_offset = current.find(PROTECTION_MARKER, header.header_end, search_end)
        if marker_offset < 0:
            raise
        del current[marker_offset : marker_offset + len(PROTECTION_MARKER)]
        header = parse_bundle_header(current)
        raw_info = decode_blocks_info(current, header)
        try:
            info = parse_blocks_info(raw_info)
        except UnityDecryptError:
            info = parse_blocks_info_lenient(raw_info)
        data_start = header.header_end + header.compressed_info_size
        if repair_corrupted_node_names(info, bytes(current[data_start:])):
            current = rebuild_bundle_info(current, header, info)
            header = parse_bundle_header(current)
            info = parse_blocks_info(decode_blocks_info(current, header))
        elif any(
            not (
                node.name.lower().startswith(b"cab-")
                and (
                    node.name.lower().endswith(b".ress")
                    or node.name.lower().endswith(b".resource")
                )
            )
            for node in info.nodes
            if not node.flags & 4
        ):
            raise UnityDecryptError(
                "The marker was removed from block info, but a damaged resource name "
                "could not be reconstructed from archive references."
            )
        layer = "double"

    data_start = header.header_end + header.compressed_info_size
    serialized_nodes = [node for node in info.nodes if node.flags & 4]
    if any((block.flags & 0x3F) != 0 for block in info.blocks):
        marker_search_allowed = False
    else:
        marker_search_allowed = True
    for node in serialized_nodes:
        if not marker_search_allowed:
            break
        node_start = data_start + node.offset
        physical = current.find(PROTECTION_MARKER, node_start, node_start + 64)
        if physical >= 0:
            del current[physical : physical + len(PROTECTION_MARKER)]
            layer = "single" if layer == "none" else layer
            break

    header = parse_bundle_header(current)
    if len(current) != header.declared_size:
        raise UnityDecryptError(
            f"After marker removal, file size {len(current)} does not match "
            f"UnityFS declared size {header.declared_size}."
        )
    info = parse_blocks_info(decode_blocks_info(current, header))
    return current, header, info, layer


def parse_blocks_info_lenient(payload: bytes) -> BlocksInfo:
    if len(payload) < 24:
        raise UnityDecryptError("Truncated damaged block-info payload.")
    block_count = int.from_bytes(payload[16:20], "big")
    if not 0 < block_count < 100_000:
        raise UnityDecryptError(f"Invalid storage block count {block_count}.")
    offset = 20
    blocks: list[StorageBlock] = []
    for _ in range(block_count):
        blocks.append(
            StorageBlock(
                int.from_bytes(payload[offset : offset + 4], "big"),
                int.from_bytes(payload[offset + 4 : offset + 8], "big"),
                int.from_bytes(payload[offset + 8 : offset + 10], "big"),
            )
        )
        offset += 10
    node_count = int.from_bytes(payload[offset : offset + 4], "big")
    offset += 4
    nodes: list[BundleNode] = []
    for index in range(node_count):
        if offset + 20 > len(payload):
            raise UnityDecryptError("Truncated damaged node table.")
        node_offset = int.from_bytes(payload[offset : offset + 8], "big")
        node_size = int.from_bytes(payload[offset + 8 : offset + 16], "big")
        node_flags = int.from_bytes(payload[offset + 16 : offset + 20], "big")
        offset += 20
        end = payload.find(b"\x00", offset)
        if end < 0:
            end = len(payload)
        name = payload[offset:end]
        offset = min(end + 1, len(payload))
        nodes.append(BundleNode(node_offset, node_size, node_flags, name))
        if index + 1 < node_count and offset >= len(payload):
            raise UnityDecryptError("Missing nodes after damaged resource name.")
    return BlocksInfo(payload[:16], blocks, nodes)


def rebuild_bundle_info(
    data: bytes | bytearray,
    header: BundleHeader,
    info: BlocksInfo,
) -> bytearray:
    uncompressed_info = encode_blocks_info(info)
    compressed_info = compress_payload(uncompressed_info, header.flags & 0x3F)
    old_data_start = header.header_end + header.compressed_info_size
    output = bytearray(data[: header.header_end])
    output += compressed_info
    output += data[old_data_start:]
    output[header.compressed_size_offset : header.compressed_size_offset + 4] = len(
        compressed_info
    ).to_bytes(4, "big")
    output[header.compressed_size_offset + 4 : header.compressed_size_offset + 8] = len(
        uncompressed_info
    ).to_bytes(4, "big")
    output[header.size_offset : header.size_offset + 8] = len(output).to_bytes(8, "big")
    return output


def decode_bundle_stream(
    data: bytes | bytearray,
    header: BundleHeader,
    info: BlocksInfo,
) -> bytes:
    position = header.header_end + header.compressed_info_size
    output = bytearray()
    for block in info.blocks:
        end = position + block.compressed_size
        if end > len(data):
            raise UnityDecryptError("Storage block extends past the bundle file.")
        output += decompress_payload(
            bytes(data[position:end]),
            block.uncompressed_size,
            block.flags & 0x3F,
        )
        position = end
    return bytes(output)


def encode_bundle_stream(
    data: bytearray,
    header: BundleHeader,
    info: BlocksInfo,
    stream: bytes,
) -> tuple[bytearray, BundleHeader, BlocksInfo]:
    expected_size = sum(block.uncompressed_size for block in info.blocks)
    if len(stream) != expected_size:
        raise UnityDecryptError(
            f"Bundle stream has size {len(stream)}, expected {expected_size}."
        )
    chunks: list[bytes] = []
    offset = 0
    for block in info.blocks:
        raw = stream[offset : offset + block.uncompressed_size]
        encoded = compress_payload(raw, block.flags & 0x3F)
        block.compressed_size = len(encoded)
        chunks.append(encoded)
        offset += block.uncompressed_size
    data_start = header.header_end + header.compressed_info_size
    # The old sizes were replaced above, so rebuild from the known UnityFS data boundary.
    trailing_start = data_start
    original_header = parse_bundle_header(data)
    original_info = parse_blocks_info(decode_blocks_info(data, original_header))
    trailing_start += sum(block.compressed_size for block in original_info.blocks)
    uncompressed_info = encode_blocks_info(info)
    compressed_info = compress_payload(uncompressed_info, header.flags & 0x3F)
    output = bytearray(data[: header.header_end])
    output += compressed_info
    output += b"".join(chunks)
    output += data[trailing_start:]
    output[header.compressed_size_offset : header.compressed_size_offset + 4] = len(
        compressed_info
    ).to_bytes(4, "big")
    output[header.compressed_size_offset + 4 : header.compressed_size_offset + 8] = len(
        uncompressed_info
    ).to_bytes(4, "big")
    output[header.size_offset : header.size_offset + 8] = len(output).to_bytes(8, "big")
    new_header = parse_bundle_header(output)
    new_info = parse_blocks_info(decode_blocks_info(output, new_header))
    return output, new_header, new_info


def standard_serialized_header(node: bytes) -> bool:
    if len(node) < 20:
        return False
    version = int.from_bytes(node[8:12], "big")
    file_size = int.from_bytes(node[4:8], "big")
    data_offset = int.from_bytes(node[12:16], "big")
    return 5 <= version <= 22 and file_size == len(node) and 20 <= data_offset <= len(node)


def template_from_bundle(path: Path) -> list[Template]:
    try:
        data = path.read_bytes()
        header = parse_bundle_header(data)
        if len(data) != header.declared_size:
            return []
        info = parse_blocks_info(decode_blocks_info(data, header))
        stream = decode_bundle_stream(data, header, info)
    except (OSError, UnityDecryptError):
        return []
    templates: list[Template] = []
    for node in info.nodes:
        if not node.flags & 4 or node.offset + node.size > len(stream):
            continue
        payload = stream[node.offset : node.offset + node.size]
        if len(payload) < 256 or not standard_serialized_header(payload):
            continue
        templates.append(
            Template(
                source=path,
                unity_revision=header.unity_revision,
                prefix=payload[:512],
            )
        )
    return templates


def candidate_template_paths(
    explicit: Iterable[Path],
    template_root: Path | None,
    target_name: str,
) -> Iterable[Path]:
    yielded: set[Path] = set()
    for path in explicit:
        resolved = path.resolve()
        if resolved not in yielded:
            yielded.add(resolved)
            yield resolved
    if template_root is None:
        return
    root = template_root.resolve()
    tokens = [token for token in re.split(r"[_\-.]+", target_name.lower()) if len(token) >= 4]
    all_paths = list(root.rglob("*.unity3d"))
    ranked = sorted(
        all_paths,
        key=lambda path: (
            -sum(token in path.name.lower() for token in tokens),
            path.stat().st_size,
            str(path).lower(),
        ),
    )
    for path in ranked:
        resolved = path.resolve()
        if resolved not in yielded:
            yielded.add(resolved)
            yield resolved


def find_template(
    node: bytes,
    revision: str,
    stable_offsets: Iterable[int],
    explicit: Iterable[Path],
    template_root: Path | None,
    target_name: str,
    cache: dict[Path, list[Template]],
) -> tuple[Template, int]:
    if len(node) < 256:
        raise UnityDecryptError("Serialized node is too small for template matching.")
    for path in candidate_template_paths(explicit, template_root, target_name):
        templates = cache.get(path)
        if templates is None:
            templates = template_from_bundle(path)
            cache[path] = templates
        for template in templates:
            if template.unity_revision != revision:
                continue
            for stable_offset in stable_offsets:
                fingerprint = node[
                    stable_offset : stable_offset + TEMPLATE_FINGERPRINT_SIZE
                ]
                if (
                    template.prefix[
                        stable_offset : stable_offset + TEMPLATE_FINGERPRINT_SIZE
                    ]
                    == fingerprint
                ):
                    return template, stable_offset
    raise UnityDecryptError(
        "No normal Unity3D template has the same Unity revision and TypeTree fingerprint. "
        "Pass a matching file with --template or a normal HS2 abdata directory with "
        "--template-root."
    )


def infer_type_count(data: bytes | bytearray, start: int = 41) -> int:
    offset = start
    count = 0
    while count < 4096 and offset + 31 <= len(data):
        class_id = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        stripped = data[offset + 4]
        if stripped not in (0, 1):
            break
        offset += 7
        if class_id == 114:
            offset += 16
        offset += 16
        if offset + 8 > len(data):
            break
        node_count = int.from_bytes(data[offset : offset + 4], "little", signed=True)
        buffer_size = int.from_bytes(data[offset + 4 : offset + 8], "little", signed=True)
        if not 0 <= node_count < 100_000 or not 0 <= buffer_size < 10_000_000:
            break
        next_offset = offset + 8 + node_count * 24 + buffer_size
        if next_offset > len(data):
            break
        offset = next_offset
        count += 1
    if count <= 0:
        raise UnityDecryptError("Could not infer a valid serialized type count.")
    return count


def parse_serialized_metadata(data: bytes | bytearray) -> ParsedMetadata:
    if len(data) < 64:
        raise UnityDecryptError("Serialized asset is too small.")
    version = int.from_bytes(data[8:12], "big")
    if version != 17:
        raise UnityDecryptError(f"Only serialized format 17 is supported, got {version}.")

    def i32(offset: int) -> int:
        if offset + 4 > len(data):
            raise UnityDecryptError("Serialized metadata is truncated.")
        return int.from_bytes(data[offset : offset + 4], "little", signed=True)

    def u32(offset: int) -> int:
        if offset + 4 > len(data):
            raise UnityDecryptError("Serialized metadata is truncated.")
        return int.from_bytes(data[offset : offset + 4], "little")

    offset = 20
    unity_raw, offset = read_cstring(data, offset)
    try:
        unity_version = unity_raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise UnityDecryptError("Invalid Unity version in serialized metadata.") from exc
    offset += 4
    if offset >= len(data):
        raise UnityDecryptError("Missing TypeTree flag.")
    enable_type_tree = data[offset]
    offset += 1
    if enable_type_tree != 1:
        raise UnityDecryptError("This repair expects an embedded TypeTree.")
    type_count = i32(offset)
    offset += 4
    if not 0 < type_count < 4096:
        raise UnityDecryptError(f"Invalid serialized type count {type_count}.")
    class_ids: list[int] = []
    for _ in range(type_count):
        class_id = i32(offset)
        class_ids.append(class_id)
        offset += 7
        if class_id == 114:
            offset += 16
        offset += 16
        node_count = i32(offset)
        string_buffer_size = i32(offset + 4)
        if not 0 <= node_count < 100_000 or not 0 <= string_buffer_size < 10_000_000:
            raise UnityDecryptError("Invalid TypeTree record.")
        offset += 8 + node_count * 24 + string_buffer_size

    object_count = i32(offset)
    offset += 4
    if not 0 <= object_count < 1_000_000:
        raise UnityDecryptError(f"Invalid object count {object_count}.")
    object_ranges: list[tuple[int, int]] = []
    for _ in range(object_count):
        offset = (offset + 3) & ~3
        byte_start = u32(offset + 8)
        byte_size = u32(offset + 12)
        type_index = i32(offset + 16)
        if not 0 <= type_index < type_count:
            raise UnityDecryptError(f"Object has invalid type index {type_index}.")
        object_ranges.append((byte_start, byte_size))
        offset += 20

    script_count = i32(offset)
    offset += 4
    if not 0 <= script_count < 100_000:
        raise UnityDecryptError(f"Invalid script-reference count {script_count}.")
    for _ in range(script_count):
        offset += 4
        offset = (offset + 3) & ~3
        offset += 8

    external_count = i32(offset)
    offset += 4
    if not 0 <= external_count < 100_000:
        raise UnityDecryptError(f"Invalid external-reference count {external_count}.")
    externals: list[str] = []
    for _ in range(external_count):
        _, offset = read_cstring(data, offset)
        offset += 20
        path_raw, offset = read_cstring(data, offset)
        externals.append(path_raw.decode("utf-8", errors="replace"))
    _, offset = read_cstring(data, offset)
    return ParsedMetadata(
        unity_version,
        type_count,
        class_ids,
        object_count,
        object_ranges,
        script_count,
        externals,
        offset,
    )


def repair_serialized_node(
    node: bytes,
    template: Template,
    stable_offset: int,
) -> tuple[bytes, ParsedMetadata]:
    repaired = bytearray(node)
    if len(repaired) < 256:
        raise UnityDecryptError("Serialized node is too small to repair.")
    if repaired[
        stable_offset : stable_offset + TEMPLATE_FINGERPRINT_SIZE
    ] != template.prefix[
        stable_offset : stable_offset + TEMPLATE_FINGERPRINT_SIZE
    ]:
        raise UnityDecryptError("Template fingerprint mismatch.")
    repaired[20:stable_offset] = template.prefix[20:stable_offset]
    repaired[4:8] = len(repaired).to_bytes(4, "big")
    repaired[8:12] = (17).to_bytes(4, "big")
    repaired[16:20] = b"\x00\x00\x00\x00"
    type_count = infer_type_count(repaired)
    repaired[37:41] = type_count.to_bytes(4, "little", signed=True)
    parsed = parse_serialized_metadata(repaired)
    metadata_size = parsed.end_offset - 20
    data_offset = (parsed.end_offset + 15) & ~15
    repaired[0:4] = metadata_size.to_bytes(4, "big")
    repaired[12:16] = data_offset.to_bytes(4, "big")
    if data_offset > len(repaired):
        raise UnityDecryptError("Calculated serialized data offset is past the node end.")
    for byte_start, byte_size in parsed.object_ranges:
        if data_offset + byte_start + byte_size > len(repaired):
            raise UnityDecryptError("An object range extends past the serialized node.")
    return bytes(repaired), parsed


def output_path_for(source: Path, input_root: Path, output_dir: Path) -> Path:
    relative = source.name if input_root.is_file() else source.relative_to(input_root)
    relative_path = Path(relative)
    name = relative_path.name
    if name.lower().endswith(".unity3d"):
        name = name[: -len(".unity3d")] + DEFAULT_SUFFIX
    else:
        name += DEFAULT_SUFFIX
    return output_dir / relative_path.parent / name


def decrypt_file(
    source: Path,
    output: Path,
    explicit_templates: list[Path],
    template_root: Path | None,
    template_cache: dict[Path, list[Template]],
    overwrite: bool,
) -> RepairResult:
    try:
        if output.exists() and not overwrite:
            raise UnityDecryptError(f"Output already exists: {output}")
        original = source.read_bytes()
        data, header, info, layer = normalize_inserted_marker(original)
        stream = bytearray(decode_bundle_stream(data, header, info))
        stable_offsets = range(160, 193) if layer == "single" else range(120, 161)
        repaired_nodes = 0
        descriptions: list[str] = []
        for node in info.nodes:
            if not node.flags & 4:
                continue
            end = node.offset + node.size
            if end > len(stream):
                raise UnityDecryptError(f"Node {node.decoded_name} extends past bundle data.")
            payload = bytes(stream[node.offset:end])
            if standard_serialized_header(payload):
                try:
                    parse_serialized_metadata(payload)
                except UnityDecryptError:
                    pass
                else:
                    continue
            template, stable_offset = find_template(
                payload,
                header.unity_revision,
                stable_offsets,
                explicit_templates,
                template_root,
                source.name,
                template_cache,
            )
            repaired, parsed = repair_serialized_node(payload, template, stable_offset)
            stream[node.offset:end] = repaired
            repaired_nodes += 1
            descriptions.append(
                f"{node.decoded_name}: {parsed.object_count} objects, "
                f"template={template.source.name}"
            )
        if repaired_nodes == 0 and layer == "none":
            return RepairResult(source, None, "skipped", "File is already a standard UnityFS bundle.")
        data, header, info = encode_bundle_stream(data, header, info, bytes(stream))
        final_stream = decode_bundle_stream(data, header, info)
        for node in info.nodes:
            if node.flags & 4:
                payload = final_stream[node.offset : node.offset + node.size]
                if not standard_serialized_header(payload):
                    raise UnityDecryptError(
                        f"Final validation failed for serialized node {node.decoded_name}."
                    )
                parse_serialized_metadata(payload)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        sha256 = hashlib.sha256(data).hexdigest()
        detail = f"repaired {layer}-layer protection"
        if descriptions:
            detail += "; " + "; ".join(descriptions)
        return RepairResult(source, output, "ok", detail, sha256, repaired_nodes)
    except (OSError, UnityDecryptError) as exc:
        return RepairResult(source, None, "error", str(exc))


def collect_inputs(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise SystemExit(f"Input path does not exist: {path}")
    iterator = path.rglob("*.unity3d") if recursive else path.glob("*.unity3d")
    return sorted(candidate for candidate in iterator if candidate.is_file())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-repair Sakuraba-style protected UnityFS files without modifying sources. "
            "A normal Unity3D file with the same TypeTree fingerprint is required."
        )
    )
    parser.add_argument("input", type=Path, help="Unity3D file or directory to scan.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory. Original files are never overwritten.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        action="append",
        default=[],
        help="Known-normal Unity3D template file. May be repeated.",
    )
    parser.add_argument(
        "--template-root",
        type=Path,
        help="Normal HS2 abdata directory searched recursively for matching templates.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recurse when input is a directory.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output files.")
    parser.add_argument("--json", action="store_true", help="Print one JSON object per input file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir == input_path or (input_path.is_dir() and output_dir == input_path):
        raise SystemExit("Output directory must differ from the input directory.")
    inputs = collect_inputs(input_path, not args.no_recursive)
    inputs = [source for source in inputs if output_dir not in source.parents]
    if not inputs:
        raise SystemExit("No .unity3d files found.")
    explicit_templates = [path.resolve() for path in args.template]
    for template in explicit_templates:
        if not template.is_file():
            raise SystemExit(f"Template file does not exist: {template}")
    template_root = args.template_root.resolve() if args.template_root else None
    if template_root is not None and not template_root.is_dir():
        raise SystemExit(f"Template root does not exist: {template_root}")

    cache: dict[Path, list[Template]] = {}
    results: list[RepairResult] = []
    for source in inputs:
        output = output_path_for(source, input_path, output_dir)
        result = decrypt_file(
            source,
            output,
            explicit_templates,
            template_root,
            cache,
            args.overwrite,
        )
        results.append(result)
        if args.json:
            print(
                json.dumps(
                    {
                        "source": str(result.source),
                        "output": str(result.output) if result.output else None,
                        "status": result.status,
                        "message": result.message,
                        "sha256": result.sha256 or None,
                        "repaired_nodes": result.repaired_nodes,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            marker = {"ok": "OK", "skipped": "SKIP", "error": "ERROR"}[result.status]
            print(f"[{marker}] {result.source}")
            print(f"       {result.message}")
            if result.output:
                print(f"       output: {result.output}")
                print(f"       sha256: {result.sha256}")

    ok_count = sum(result.status == "ok" for result in results)
    skipped_count = sum(result.status == "skipped" for result in results)
    error_count = sum(result.status == "error" for result in results)
    if not args.json:
        print(f"Summary: {ok_count} repaired, {skipped_count} skipped, {error_count} failed.")
    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
