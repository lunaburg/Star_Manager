r"""Extract LOD0 GEOM meshes and RLE2 texture swatches from a TS4 package.

The script reads a Sims 4 DBPF package directly and writes binary FBX 7.4 files.
It preserves positions, triangle faces, normals, and every UV set present in the
GEOM resource. Every DXT5 RLE2 resource is decoded to PNG, and each FBX refers
to the nearest texture resource as its default diffuse swatch. Positions and
FBX units are converted to the centimeter/Y-up convention used by the HS2
reference body. Skeletons, skinning, morphs, and animation are not exported.

Example (PowerShell):

    python apps/scripts/extract_ts4_package_fbx.py `
      "E:\download\(maya)Panda Dress.package" `
      --output-dir "apps\extracted\panda_dress\lod0_fbx"
"""

from __future__ import annotations

import argparse
import array
import io
import json
import re
import struct
import sys
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from PIL import Image, ImageChops


GEOM_RESOURCE_TYPE = 0x015A1849
RLE2_RESOURCE_TYPE = 0x3453CF95
ZLIB_COMPRESSION_TYPE = 0x5A42
HS2_POSITION_SCALE = 10.0
ALPHA_COVERAGE_THRESHOLD = 8
ALPHA_COVERAGE_MAX_DIMENSION = 1024
FBX_VERSION = 7400
FBX_HEADER = b"Kaydara FBX Binary  \x00\x1A\x00"
FBX_FOOTER_MAGIC = bytes.fromhex("FABCAB09D0C8D466B176FB831CF7267E")
FBX_FOOTER_TAIL = bytes.fromhex("F85A8C6ADEF5D97EECE90CE3758F290B")


class PackageFormatError(RuntimeError):
    pass


class GeomFormatError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResourceEntry:
    index: int
    type_id: int
    group_id: int
    instance_id: int
    offset: int
    compressed_size: int
    decompressed_size: int
    compression_type: int


@dataclass(frozen=True)
class MeshCandidate:
    resource: ResourceEntry
    mesh: dict[str, Any]


def read_package_index(package: bytes) -> list[ResourceEntry]:
    """Read a DBPF 2.x index, including optional shared TGI fields."""
    if len(package) < 0x60 or package[:4] != b"DBPF":
        raise PackageFormatError("The input is not a DBPF package.")

    major_version, minor_version = struct.unpack_from("<II", package, 4)
    if major_version != 2:
        raise PackageFormatError(
            f"Unsupported DBPF version {major_version}.{minor_version}; expected 2.x."
        )

    entry_count = struct.unpack_from("<I", package, 0x24)[0]
    index_size = struct.unpack_from("<I", package, 0x2C)[0]
    index_offset = struct.unpack_from("<Q", package, 0x40)[0]
    if index_offset + index_size > len(package):
        raise PackageFormatError("The DBPF index extends beyond the end of the file.")

    index_flags = struct.unpack_from("<I", package, index_offset)[0]
    if index_flags & ~0x07:
        raise PackageFormatError(
            f"Unsupported DBPF index flags 0x{index_flags:08X}."
        )
    shared_field_count = (index_flags & 0x07).bit_count()
    expected_size = (
        4
        + shared_field_count * 4
        + entry_count * (32 - shared_field_count * 4)
    )
    if index_size != expected_size:
        raise PackageFormatError(
            f"Unexpected DBPF index size {index_size}; expected {expected_size}."
        )

    entries: list[ResourceEntry] = []
    cursor = index_offset + 4
    shared_type = None
    shared_group = None
    shared_instance_high = None
    if index_flags & 0x01:
        shared_type = struct.unpack_from("<I", package, cursor)[0]
        cursor += 4
    if index_flags & 0x02:
        shared_group = struct.unpack_from("<I", package, cursor)[0]
        cursor += 4
    if index_flags & 0x04:
        shared_instance_high = struct.unpack_from("<I", package, cursor)[0]
        cursor += 4

    for entry_index in range(entry_count):
        if shared_type is None:
            type_id = struct.unpack_from("<I", package, cursor)[0]
            cursor += 4
        else:
            type_id = shared_type
        if shared_group is None:
            group_id = struct.unpack_from("<I", package, cursor)[0]
            cursor += 4
        else:
            group_id = shared_group

        instance_low = struct.unpack_from("<I", package, cursor)[0]
        cursor += 4
        if shared_instance_high is None:
            instance_high = struct.unpack_from("<I", package, cursor)[0]
            cursor += 4
        else:
            instance_high = shared_instance_high
        instance_id = (instance_high << 32) | instance_low

        (
            offset,
            compressed_size,
            decompressed_size,
            compression_type,
            _committed,
        ) = struct.unpack_from("<IIIHH", package, cursor)
        cursor += 16
        compressed_size &= 0x7FFFFFFF
        if offset + compressed_size > len(package):
            raise PackageFormatError(
                f"Resource {entry_index} extends beyond the package boundary."
            )
        entries.append(
            ResourceEntry(
                index=entry_index,
                type_id=type_id,
                group_id=group_id,
                instance_id=instance_id,
                offset=offset,
                compressed_size=compressed_size,
                decompressed_size=decompressed_size,
                compression_type=compression_type,
            )
        )
    if cursor != index_offset + index_size:
        raise PackageFormatError("DBPF index parsing ended at an unexpected offset.")
    return entries


def read_resource_payload(package: bytes, resource: ResourceEntry) -> bytes:
    payload = package[
        resource.offset : resource.offset + resource.compressed_size
    ]
    looks_like_zlib = len(payload) >= 2 and payload[0] == 0x78
    if resource.compression_type == ZLIB_COMPRESSION_TYPE or looks_like_zlib:
        try:
            payload = zlib.decompress(payload)
        except zlib.error as exc:
            raise PackageFormatError(
                f"Resource {resource.index} has invalid zlib data: {exc}"
            ) from exc
    elif len(payload) != resource.decompressed_size:
        raise PackageFormatError(
            f"Resource {resource.index} uses unsupported compression type "
            f"0x{resource.compression_type:04X}."
        )

    if len(payload) != resource.decompressed_size:
        raise PackageFormatError(
            f"Resource {resource.index} decoded to {len(payload)} bytes; "
            f"expected {resource.decompressed_size}."
        )
    return payload


def dds_header(width: int, height: int, mip_count: int) -> bytes:
    """Build a DDS header for a BC3/DXT5 mip chain."""
    flags = 0x00001007 | 0x00020000 | 0x00080000
    linear_size = ((width + 3) // 4) * ((height + 3) // 4) * 16
    header = bytearray(b"DDS ")
    header += struct.pack("<II", 124, flags)
    header += struct.pack("<IIIII", height, width, linear_size, 1, mip_count)
    header += b"\0" * (11 * 4)
    header += struct.pack("<II4sIIIII", 32, 4, b"DXT5", 0, 0, 0, 0, 0)
    header += struct.pack("<IIIII", 0x1000 | 0x400000 | 8, 0, 0, 0, 0)
    if len(header) != 128:
        raise AssertionError("Invalid DDS header size.")
    return bytes(header)


def decode_rle2(raw: bytes) -> tuple[bytes, int, int, int]:
    """Reconstruct a standard BC3/DXT5 DDS stream from a TS4 RLE2 resource."""
    if len(raw) < 36 or raw[:8] != b"DXT5RLE2":
        raise ValueError("Expected a DXT5RLE2 texture resource.")
    width, height, mip_count, unknown = struct.unpack_from("<HHHH", raw, 8)
    if width <= 0 or height <= 0 or mip_count <= 0:
        raise ValueError("RLE2 texture dimensions or mip count are invalid.")
    if unknown != 0:
        raise ValueError(f"Unexpected RLE2 header value {unknown}.")
    if 16 + mip_count * 20 > len(raw):
        raise ValueError("RLE2 mip headers extend beyond the resource.")

    headers = [
        struct.unpack_from("<iiiii", raw, 16 + mip * 20)
        for mip in range(mip_count)
    ]
    headers.append(
        (headers[0][1], headers[0][2], headers[0][3], headers[0][4], len(raw))
    )

    transparent_alpha = b"\x00\x05" + b"\x00" * 6
    transparent_white = b"\xFF\xFF" + b"\x00" * 6
    opaque_alpha = b"\x00\x05" + b"\xFF" * 6
    blocks = bytearray()

    for mip in range(mip_count):
        command_offset, offset2, offset3, offset0, offset1 = headers[mip]
        next_header = headers[mip + 1]
        offsets = (command_offset, offset2, offset3, offset0, offset1)
        if any(offset < 0 or offset > len(raw) for offset in offsets):
            raise ValueError(f"RLE2 mip {mip} contains an invalid stream offset.")
        while command_offset < next_header[0]:
            if command_offset + 2 > len(raw):
                raise ValueError(f"RLE2 mip {mip} has a truncated command stream.")
            command = struct.unpack_from("<H", raw, command_offset)[0]
            command_offset += 2
            operation = command & 3
            count = command >> 2
            for _ in range(count):
                if operation == 0:
                    blocks += transparent_alpha + transparent_white
                elif operation == 1:
                    if max(offset0 + 2, offset1 + 6, offset2 + 4, offset3 + 4) > len(raw):
                        raise ValueError(f"RLE2 mip {mip} data stream is truncated.")
                    blocks += raw[offset0 : offset0 + 2]
                    blocks += raw[offset1 : offset1 + 6]
                    blocks += raw[offset2 : offset2 + 4]
                    blocks += raw[offset3 : offset3 + 4]
                    offset0 += 2
                    offset1 += 6
                    offset2 += 4
                    offset3 += 4
                elif operation == 2:
                    if max(offset2 + 4, offset3 + 4) > len(raw):
                        raise ValueError(f"RLE2 mip {mip} data stream is truncated.")
                    blocks += opaque_alpha
                    blocks += raw[offset2 : offset2 + 4]
                    blocks += raw[offset3 : offset3 + 4]
                    offset2 += 4
                    offset3 += 4
                else:
                    raise ValueError(f"Unsupported RLE2 operation {operation}.")

        actual = (offset2, offset3, offset0, offset1)
        expected = next_header[1:]
        if actual != expected:
            raise ValueError(
                f"RLE2 mip {mip} offset mismatch: {actual} != {expected}."
            )

    return dds_header(width, height, mip_count) + bytes(blocks), width, height, mip_count


def parse_geom(raw: bytes) -> dict[str, Any]:
    """Parse the renderable part of a Sims 4 GEOM resource."""
    geom_start = raw.find(b"GEOM")
    if geom_start < 0:
        raise GeomFormatError("GEOM chunk signature not found.")
    cursor = geom_start

    tag, version, tgi_offset, _tgi_size, shader = struct.unpack_from(
        "<IIIII", raw, cursor
    )
    cursor += 20
    if tag != struct.unpack("<I", b"GEOM")[0]:
        raise GeomFormatError("Invalid GEOM chunk tag.")
    if version not in (0x05, 0x0C, 0x0D, 0x0E, 0x0F):
        raise GeomFormatError(f"Unsupported GEOM version 0x{version:X}.")

    if shader:
        mtnf_size = struct.unpack_from("<I", raw, cursor)[0]
        cursor += 4 + mtnf_size
    if cursor + 16 > len(raw):
        raise GeomFormatError("Truncated GEOM header.")

    merge_group, sort_order, vertex_count = struct.unpack_from("<IIi", raw, cursor)
    cursor += 12
    if vertex_count <= 0:
        raise GeomFormatError(f"Invalid GEOM vertex count {vertex_count}.")

    format_count = struct.unpack_from("<I", raw, cursor)[0]
    cursor += 4
    if not 1 <= format_count <= 32:
        raise GeomFormatError(f"Invalid GEOM vertex format count {format_count}.")

    vertex_formats: list[tuple[int, int, int]] = []
    for _ in range(format_count):
        usage, data_type, element_size = struct.unpack_from("<IIB", raw, cursor)
        cursor += 9
        if element_size <= 0:
            raise GeomFormatError(f"Invalid vertex element size {element_size}.")
        vertex_formats.append((usage, data_type, element_size))

    stride = sum(element_size for _, _, element_size in vertex_formats)
    if cursor + vertex_count * stride > len(raw):
        raise GeomFormatError("GEOM vertex data extends beyond the resource.")

    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    uv_sets: list[list[tuple[float, float]]] = []
    bone_indices: list[tuple[int, int, int, int]] = []
    bone_weights: list[tuple[int, int, int, int]] = []
    for _ in range(vertex_count):
        current_uv_set = 0
        current_bone_indices: tuple[int, int, int, int] | None = None
        current_bone_weights: tuple[int, int, int, int] | None = None
        for usage, _data_type, element_size in vertex_formats:
            element_start = cursor
            if usage == 1:
                if element_size < 12:
                    raise GeomFormatError("GEOM position element is too small.")
                positions.append(struct.unpack_from("<fff", raw, cursor))
            elif usage == 2:
                if element_size < 12:
                    raise GeomFormatError("GEOM normal element is too small.")
                normals.append(struct.unpack_from("<fff", raw, cursor))
            elif usage == 3:
                if element_size < 8:
                    raise GeomFormatError("GEOM UV element is too small.")
                while len(uv_sets) <= current_uv_set:
                    uv_sets.append([])
                uv_sets[current_uv_set].append(
                    struct.unpack_from("<ff", raw, cursor)
                )
                current_uv_set += 1
            elif usage == 4:
                if element_size < 4:
                    raise GeomFormatError("GEOM bone-index element is too small.")
                current_bone_indices = struct.unpack_from("<4B", raw, cursor)
            elif usage == 5:
                if element_size < 4:
                    raise GeomFormatError("GEOM bone-weight element is too small.")
                current_bone_weights = struct.unpack_from("<4B", raw, cursor)
            cursor = element_start + element_size
        if (current_bone_indices is None) != (current_bone_weights is None):
            raise GeomFormatError(
                "GEOM vertex contains incomplete bone index/weight data."
            )
        if current_bone_indices is not None and current_bone_weights is not None:
            bone_indices.append(current_bone_indices)
            bone_weights.append(current_bone_weights)

    if len(positions) != vertex_count:
        raise GeomFormatError(
            f"Expected {vertex_count} positions, found {len(positions)}."
        )
    if normals and len(normals) != vertex_count:
        raise GeomFormatError(
            f"Expected {vertex_count} normals, found {len(normals)}."
        )
    for uv_index, uv_set in enumerate(uv_sets):
        if len(uv_set) != vertex_count:
            raise GeomFormatError(
                f"UV set {uv_index} contains {len(uv_set)} entries; "
                f"expected {vertex_count}."
            )

    if cursor + 9 > len(raw):
        raise GeomFormatError("Truncated GEOM face header.")
    submesh_count = struct.unpack_from("<I", raw, cursor)[0]
    cursor += 4
    face_index_size = raw[cursor]
    cursor += 1
    face_index_count = struct.unpack_from("<I", raw, cursor)[0]
    cursor += 4
    if face_index_count % 3:
        raise GeomFormatError(
            f"GEOM face index count {face_index_count} is not divisible by three."
        )
    index_type = {1: "B", 2: "H", 4: "I"}.get(face_index_size)
    if index_type is None:
        raise GeomFormatError(f"Unsupported GEOM index size {face_index_size}.")
    if cursor + face_index_count * face_index_size > len(raw):
        raise GeomFormatError("GEOM face data extends beyond the resource.")

    indices = struct.unpack_from(
        f"<{face_index_count}{index_type}", raw, cursor
    )
    if max(indices, default=-1) >= vertex_count:
        raise GeomFormatError("A GEOM face references a missing vertex.")
    faces = [
        (indices[index], indices[index + 1], indices[index + 2])
        for index in range(0, len(indices), 3)
    ]

    bone_hashes: list[int] = []
    if bone_indices:
        used_bone_indices = [
            bone_index
            for vertex_indices, vertex_weights in zip(bone_indices, bone_weights)
            for bone_index, weight in zip(vertex_indices, vertex_weights)
            if weight > 0
        ]
        minimum_palette_size = max(used_bone_indices, default=-1) + 1
        tgi_table_start = geom_start + 12 + tgi_offset
        # GEOM 0x0F adds a four-byte field between the bone-hash palette and
        # the TGI table. Older versions place the palette directly before TGI.
        bone_palette_end = tgi_table_start - (4 if version == 0x0F else 0)
        if 4 <= bone_palette_end <= len(raw):
            for bone_count in range(max(1, minimum_palette_size), 257):
                palette_start = bone_palette_end - 4 - bone_count * 4
                if palette_start < 0:
                    continue
                if struct.unpack_from("<I", raw, palette_start)[0] != bone_count:
                    continue
                bone_hashes = list(
                    struct.unpack_from(
                        f"<{bone_count}I", raw, palette_start + 4
                    )
                )
                break
        if len(bone_indices) != vertex_count or len(bone_weights) != vertex_count:
            raise GeomFormatError("GEOM skinning data does not match vertex count.")
        if not bone_hashes:
            raise GeomFormatError("GEOM skinning data has no readable bone hash palette.")
        if max(used_bone_indices, default=-1) >= len(bone_hashes):
            raise GeomFormatError("GEOM skinning data references a missing bone hash.")

    return {
        "version": version,
        "shader": shader,
        "merge_group": merge_group,
        "sort_order": sort_order,
        "submesh_count": submesh_count,
        "vertex_count": vertex_count,
        "triangle_count": len(faces),
        "vertex_formats": vertex_formats,
        "positions": positions,
        "normals": normals,
        "uv_sets": uv_sets,
        "bone_indices": bone_indices,
        "bone_weights": bone_weights,
        "bone_hashes": bone_hashes,
        "faces": faces,
    }


def align_mesh_to_hs2(mesh: dict[str, Any]) -> dict[str, Any]:
    """Match HS2 FBX centimeters while preserving the shared Y-up axes."""
    return {
        **mesh,
        "positions": [
            (
                x * HS2_POSITION_SCALE,
                y * HS2_POSITION_SCALE,
                z * HS2_POSITION_SCALE,
            )
            for x, y, z in mesh["positions"]
        ],
    }


def combine_alpha_coverage(texture_paths: Sequence[Path]) -> Image.Image | None:
    """Combine texture alpha channels into one normalized coverage mask."""
    coverage: Image.Image | None = None
    for texture_path in texture_paths:
        with Image.open(texture_path) as image:
            alpha = image.convert("RGBA").getchannel("A")
            if coverage is None:
                coverage = alpha.copy()
                continue
            if alpha.size != coverage.size:
                alpha = alpha.resize(coverage.size, Image.Resampling.BOX)
            coverage = ImageChops.lighter(coverage, alpha)

    if coverage is None:
        return None
    largest_dimension = max(coverage.size)
    if largest_dimension > ALPHA_COVERAGE_MAX_DIMENSION:
        ratio = ALPHA_COVERAGE_MAX_DIMENSION / largest_dimension
        target_size = (
            max(1, round(coverage.width * ratio)),
            max(1, round(coverage.height * ratio)),
        )
        coverage = coverage.resize(target_size, Image.Resampling.BOX)
    return coverage


def uv_triangle_has_alpha_coverage(
    uv_triangle: Sequence[tuple[float, float]],
    alpha_data: bytes,
    width: int,
    height: int,
    threshold: int = ALPHA_COVERAGE_THRESHOLD,
) -> bool:
    """Return whether a UV triangle intersects a non-transparent alpha pixel."""
    pixel_points = [
        (u * (width - 1), v * (height - 1))
        for u, v in uv_triangle
    ]

    def sample(x: float, y: float) -> bool:
        if x < 0 or y < 0 or x > width - 1 or y > height - 1:
            return False
        return alpha_data[round(y) * width + round(x)] > threshold

    centroid = (
        sum(point[0] for point in pixel_points) / 3.0,
        sum(point[1] for point in pixel_points) / 3.0,
    )
    edge_midpoints = [
        (
            (pixel_points[index][0] + pixel_points[(index + 1) % 3][0]) / 2.0,
            (pixel_points[index][1] + pixel_points[(index + 1) % 3][1]) / 2.0,
        )
        for index in range(3)
    ]
    if any(sample(x, y) for x, y in [*pixel_points, *edge_midpoints, centroid]):
        return True

    minimum_y = max(0, int(min(point[1] for point in pixel_points)))
    maximum_y = min(height - 1, int(max(point[1] for point in pixel_points)) + 1)
    if maximum_y < minimum_y:
        return False

    for pixel_y in range(minimum_y, maximum_y + 1):
        scan_y = pixel_y + 0.5
        intersections: list[float] = []
        for index in range(3):
            first = pixel_points[index]
            second = pixel_points[(index + 1) % 3]
            low_y = min(first[1], second[1])
            high_y = max(first[1], second[1])
            if high_y == low_y or not low_y <= scan_y < high_y:
                continue
            factor = (scan_y - first[1]) / (second[1] - first[1])
            intersections.append(first[0] + factor * (second[0] - first[0]))
        if len(intersections) < 2:
            continue
        start_x = max(0, int(min(intersections)))
        end_x = min(width - 1, int(max(intersections)) + 1)
        if end_x < start_x:
            continue
        row_start = pixel_y * width + start_x
        row_end = pixel_y * width + end_x + 1
        if any(value > threshold for value in alpha_data[row_start:row_end]):
            return True
    return False


def filter_mesh_by_alpha_coverage(
    mesh: dict[str, Any],
    coverage: Image.Image | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Remove faces outside alpha coverage and compact all vertex attributes."""
    source_vertices = int(mesh["vertex_count"])
    source_triangles = int(mesh["triangle_count"])
    statistics = {
        "applied": False,
        "source_vertices": source_vertices,
        "source_triangles": source_triangles,
        "removed_vertices": 0,
        "removed_triangles": 0,
        "reason": "",
    }
    if coverage is None:
        statistics["reason"] = "no_texture_alpha"
        return mesh, statistics
    if not mesh["uv_sets"]:
        statistics["reason"] = "no_uv_set"
        return mesh, statistics

    alpha = coverage.convert("L")
    if alpha.getextrema()[0] > ALPHA_COVERAGE_THRESHOLD:
        statistics["applied"] = True
        statistics["reason"] = "texture_fully_opaque"
        return mesh, statistics

    alpha_data = alpha.tobytes()
    uv_set = mesh["uv_sets"][0]
    kept_faces = [
        face
        for face in mesh["faces"]
        if uv_triangle_has_alpha_coverage(
            [uv_set[index] for index in face],
            alpha_data,
            alpha.width,
            alpha.height,
        )
    ]
    if not kept_faces:
        statistics["reason"] = "filter_would_remove_all_faces"
        return mesh, statistics

    used_indices = sorted({index for face in kept_faces for index in face})
    index_map = {
        source_index: target_index
        for target_index, source_index in enumerate(used_indices)
    }
    filtered = {
        **mesh,
        "positions": [mesh["positions"][index] for index in used_indices],
        "normals": (
            [mesh["normals"][index] for index in used_indices]
            if mesh["normals"]
            else []
        ),
        "uv_sets": [
            [uv_set_item[index] for index in used_indices]
            for uv_set_item in mesh["uv_sets"]
        ],
        "bone_indices": (
            [mesh["bone_indices"][index] for index in used_indices]
            if mesh.get("bone_indices")
            else []
        ),
        "bone_weights": (
            [mesh["bone_weights"][index] for index in used_indices]
            if mesh.get("bone_weights")
            else []
        ),
        "faces": [
            tuple(index_map[index] for index in face)
            for face in kept_faces
        ],
        "vertex_count": len(used_indices),
        "triangle_count": len(kept_faces),
    }
    statistics.update(
        {
            "applied": True,
            "removed_vertices": source_vertices - len(used_indices),
            "removed_triangles": source_triangles - len(kept_faces),
            "reason": "alpha_coverage",
        }
    )
    return filtered, statistics


FbxProperty = tuple[str, Any]
FbxNode = tuple[str, list[FbxProperty], list["FbxNode"]]


def fbx_node(
    name: str,
    properties: Iterable[FbxProperty] = (),
    children: Iterable[FbxNode] = (),
) -> FbxNode:
    return name, list(properties), list(children)


def fbx_object_name(class_name: str, object_name: str) -> str:
    """Encode an FBX binary object name using the class/name separator."""
    return f"{object_name}\x00\x01{class_name}"


def encode_fbx_property(type_code: str, value: Any) -> bytes:
    code = type_code.encode("ascii")
    if type_code == "C":
        return code + struct.pack("<B", 1 if value else 0)
    if type_code == "I":
        return code + struct.pack("<i", int(value))
    if type_code == "L":
        return code + struct.pack("<q", int(value))
    if type_code == "D":
        return code + struct.pack("<d", float(value))
    if type_code == "S":
        encoded = str(value).encode("utf-8")
        return code + struct.pack("<I", len(encoded)) + encoded
    if type_code in ("d", "i"):
        array_type = "d" if type_code == "d" else "i"
        packed = array.array(array_type, value)
        if sys.byteorder != "little":
            packed.byteswap()
        uncompressed = packed.tobytes()
        if len(uncompressed) >= 1024:
            payload = zlib.compress(uncompressed, level=6)
            encoding = 1
        else:
            payload = uncompressed
            encoding = 0
        return (
            code
            + struct.pack("<III", len(packed), encoding, len(payload))
            + payload
        )
    raise ValueError(f"Unsupported FBX property type {type_code!r}.")


def encode_fbx_node(node: FbxNode, start_offset: int) -> bytes:
    name, properties, children = node
    encoded_name = name.encode("utf-8")
    encoded_properties = b"".join(
        encode_fbx_property(type_code, value)
        for type_code, value in properties
    )
    header_size = 13 + len(encoded_name)
    encoded_children = bytearray()
    child_start = start_offset + header_size + len(encoded_properties)
    for child in children:
        encoded_children += encode_fbx_node(
            child, child_start + len(encoded_children)
        )
    if children:
        encoded_children += b"\0" * 13

    end_offset = (
        start_offset
        + header_size
        + len(encoded_properties)
        + len(encoded_children)
    )
    return (
        struct.pack(
            "<IIIB",
            end_offset,
            len(properties),
            len(encoded_properties),
            len(encoded_name),
        )
        + encoded_name
        + encoded_properties
        + bytes(encoded_children)
    )


def fbx_p(
    name: str,
    type_name: str,
    label: str,
    flags: str,
    *values: float | int,
) -> FbxNode:
    properties: list[FbxProperty] = [
        ("S", name),
        ("S", type_name),
        ("S", label),
        ("S", flags),
    ]
    properties.extend(
        ("I", value) if isinstance(value, int) else ("D", value)
        for value in values
    )
    return fbx_node("P", properties)


def build_geometry_nodes(mesh: dict[str, Any]) -> list[FbxNode]:
    positions = [
        component
        for vertex in mesh["positions"]
        for component in vertex
    ]
    polygon_indices: list[int] = []
    for first, second, third in mesh["faces"]:
        polygon_indices.extend((first, second, -third - 1))

    children = [
        fbx_node("GeometryVersion", [("I", 124)]),
        fbx_node("Vertices", [("d", positions)]),
        fbx_node("PolygonVertexIndex", [("i", polygon_indices)]),
    ]

    normals = mesh["normals"]
    if normals:
        flat_normals = [
            component for normal in normals for component in normal
        ]
        children.append(
            fbx_node(
                "LayerElementNormal",
                [("I", 0)],
                [
                    fbx_node("Version", [("I", 101)]),
                    fbx_node("Name", [("S", "")]),
                    fbx_node("MappingInformationType", [("S", "ByVertice")]),
                    fbx_node("ReferenceInformationType", [("S", "Direct")]),
                    fbx_node("Normals", [("d", flat_normals)]),
                ],
            )
        )

    for uv_index, uv_set in enumerate(mesh["uv_sets"]):
        uv_values = [
            component
            for u, v in uv_set
            for component in (u, 1.0 - v)
        ]
        children.append(
            fbx_node(
                "LayerElementUV",
                [("I", uv_index)],
                [
                    fbx_node("Version", [("I", 101)]),
                    fbx_node("Name", [("S", f"UVChannel_{uv_index + 1}")]),
                    fbx_node("MappingInformationType", [("S", "ByVertice")]),
                    fbx_node("ReferenceInformationType", [("S", "Direct")]),
                    fbx_node("UV", [("d", uv_values)]),
                ],
            )
        )

    children.append(
        fbx_node(
            "LayerElementMaterial",
            [("I", 0)],
            [
                fbx_node("Version", [("I", 101)]),
                fbx_node("Name", [("S", "")]),
                fbx_node("MappingInformationType", [("S", "AllSame")]),
                fbx_node("ReferenceInformationType", [("S", "IndexToDirect")]),
                fbx_node("Materials", [("i", [0])]),
            ],
        )
    )

    primary_layer_elements: list[FbxNode] = []
    if normals:
        primary_layer_elements.append(
            fbx_node(
                "LayerElement",
                children=[
                    fbx_node("Type", [("S", "LayerElementNormal")]),
                    fbx_node("TypedIndex", [("I", 0)]),
                ],
            )
        )
    primary_layer_elements.append(
        fbx_node(
            "LayerElement",
            children=[
                fbx_node("Type", [("S", "LayerElementMaterial")]),
                fbx_node("TypedIndex", [("I", 0)]),
            ],
        )
    )
    if mesh["uv_sets"]:
        primary_layer_elements.append(
            fbx_node(
                "LayerElement",
                children=[
                    fbx_node("Type", [("S", "LayerElementUV")]),
                    fbx_node("TypedIndex", [("I", 0)]),
                ],
            )
        )
    children.append(
        fbx_node(
            "Layer",
            [("I", 0)],
            [fbx_node("Version", [("I", 100)])]
            + primary_layer_elements,
        )
    )

    for uv_index in range(1, len(mesh["uv_sets"])):
        children.append(
            fbx_node(
                "Layer",
                [("I", uv_index)],
                [
                    fbx_node("Version", [("I", 100)]),
                    fbx_node(
                        "LayerElement",
                        children=[
                            fbx_node("Type", [("S", "LayerElementUV")]),
                            fbx_node("TypedIndex", [("I", uv_index)]),
                        ],
                    ),
                ],
            )
        )
    return children


def build_fbx_nodes(
    mesh_name: str,
    mesh: dict[str, Any],
    object_seed: int,
    texture_path: Path | None = None,
    relative_texture_path: Path | None = None,
) -> list[FbxNode]:
    geometry_id = 1_000_000 + object_seed * 10
    model_id = geometry_id + 1
    material_id = geometry_id + 2
    texture_id = geometry_id + 3
    video_id = geometry_id + 4
    document_id = 100

    timestamp = [
        fbx_node("Version", [("I", 1000)]),
        fbx_node("Year", [("I", 2026)]),
        fbx_node("Month", [("I", 7)]),
        fbx_node("Day", [("I", 22)]),
        fbx_node("Hour", [("I", 0)]),
        fbx_node("Minute", [("I", 0)]),
        fbx_node("Second", [("I", 0)]),
        fbx_node("Millisecond", [("I", 0)]),
    ]
    global_properties = [
        fbx_p("UpAxis", "int", "Integer", "", 1),
        fbx_p("UpAxisSign", "int", "Integer", "", 1),
        fbx_p("FrontAxis", "int", "Integer", "", 2),
        fbx_p("FrontAxisSign", "int", "Integer", "", 1),
        fbx_p("CoordAxis", "int", "Integer", "", 0),
        fbx_p("CoordAxisSign", "int", "Integer", "", 1),
        fbx_p("OriginalUpAxis", "int", "Integer", "", -1),
        fbx_p("OriginalUpAxisSign", "int", "Integer", "", 1),
        fbx_p("UnitScaleFactor", "double", "Number", "", 1.0),
        fbx_p("OriginalUnitScaleFactor", "double", "Number", "", 1.0),
    ]
    model_properties = [
        fbx_p("Lcl Translation", "Lcl Translation", "", "A", 0.0, 0.0, 0.0),
        fbx_p("Lcl Rotation", "Lcl Rotation", "", "A", 0.0, 0.0, 0.0),
        fbx_p("Lcl Scaling", "Lcl Scaling", "", "A", 1.0, 1.0, 1.0),
        fbx_p("DefaultAttributeIndex", "int", "Integer", "", 0),
    ]
    diffuse_color = (1.0, 1.0, 1.0) if texture_path else (0.8, 0.8, 0.8)
    material_properties = [
        fbx_p(
            "DiffuseColor",
            "Color",
            "",
            "A",
            *diffuse_color,
        ),
        fbx_p("DiffuseFactor", "Number", "", "A", 1.0),
        fbx_p("SpecularColor", "Color", "", "A", 0.0, 0.0, 0.0),
        fbx_p("Shininess", "Number", "", "A", 0.0),
        fbx_p("Opacity", "Number", "", "A", 1.0),
    ]

    definition_types = [
        fbx_node(
            "ObjectType",
            [("S", "Model")],
            [fbx_node("Count", [("I", 1)])],
        ),
        fbx_node(
            "ObjectType",
            [("S", "Geometry")],
            [fbx_node("Count", [("I", 1)])],
        ),
        fbx_node(
            "ObjectType",
            [("S", "Material")],
            [fbx_node("Count", [("I", 1)])],
        ),
    ]
    object_nodes = [
        fbx_node(
            "Geometry",
            [
                ("L", geometry_id),
                ("S", fbx_object_name("Geometry", mesh_name)),
                ("S", "Mesh"),
            ],
            build_geometry_nodes(mesh),
        ),
        fbx_node(
            "Model",
            [
                ("L", model_id),
                ("S", fbx_object_name("Model", mesh_name)),
                ("S", "Mesh"),
            ],
            [
                fbx_node("Version", [("I", 232)]),
                fbx_node("Properties70", children=model_properties),
                fbx_node("Shading", [("C", True)]),
                fbx_node("Culling", [("S", "CullingOff")]),
            ],
        ),
        fbx_node(
            "Material",
            [
                ("L", material_id),
                ("S", fbx_object_name("Material", mesh_name)),
                ("S", ""),
            ],
            [
                fbx_node("Version", [("I", 102)]),
                fbx_node("ShadingModel", [("S", "phong")]),
                fbx_node("MultiLayer", [("I", 0)]),
                fbx_node("Properties70", children=material_properties),
            ],
        ),
    ]
    connection_nodes = [
        fbx_node("C", [("S", "OO"), ("L", geometry_id), ("L", model_id)]),
        fbx_node("C", [("S", "OO"), ("L", model_id), ("L", 0)]),
        fbx_node("C", [("S", "OO"), ("L", material_id), ("L", model_id)]),
    ]

    if texture_path is not None and relative_texture_path is not None:
        texture_name = f"{mesh_name}_diffuse"
        native_texture = str(texture_path.resolve())
        relative_texture = relative_texture_path.as_posix()
        definition_types.extend(
            [
                fbx_node(
                    "ObjectType",
                    [("S", "Texture")],
                    [fbx_node("Count", [("I", 1)])],
                ),
                fbx_node(
                    "ObjectType",
                    [("S", "Video")],
                    [fbx_node("Count", [("I", 1)])],
                ),
            ]
        )
        object_nodes.extend(
            [
                fbx_node(
                    "Texture",
                    [
                        ("L", texture_id),
                        ("S", fbx_object_name("Texture", texture_name)),
                        ("S", "TextureVideoClip"),
                    ],
                    [
                        fbx_node("Type", [("S", "TextureVideoClip")]),
                        fbx_node("Version", [("I", 202)]),
                        fbx_node("TextureName", [("S", f"Texture::{texture_name}")]),
                        fbx_node("Media", [("S", f"Video::{texture_name}")]),
                        fbx_node("FileName", [("S", native_texture)]),
                        fbx_node("RelativeFilename", [("S", relative_texture)]),
                        fbx_node("ModelUVTranslation", [("D", 0.0), ("D", 0.0)]),
                        fbx_node("ModelUVScaling", [("D", 1.0), ("D", 1.0)]),
                        fbx_node("Texture_Alpha_Source", [("S", "Black")]),
                        fbx_node("Cropping", [("I", 0), ("I", 0), ("I", 0), ("I", 0)]),
                        fbx_node("UVSet", [("S", "UVChannel_1")]),
                    ],
                ),
                fbx_node(
                    "Video",
                    [
                        ("L", video_id),
                        ("S", fbx_object_name("Video", texture_name)),
                        ("S", "Clip"),
                    ],
                    [
                        fbx_node("Type", [("S", "Clip")]),
                        fbx_node("Properties70"),
                        fbx_node("UseMipMap", [("I", 0)]),
                        fbx_node("Filename", [("S", native_texture)]),
                        fbx_node("RelativeFilename", [("S", relative_texture)]),
                    ],
                ),
            ]
        )
        connection_nodes.extend(
            [
                fbx_node(
                    "C",
                    [
                        ("S", "OP"),
                        ("L", texture_id),
                        ("L", material_id),
                        ("S", "DiffuseColor"),
                    ],
                ),
                fbx_node("C", [("S", "OO"), ("L", video_id), ("L", texture_id)]),
            ]
        )

    return [
        fbx_node(
            "FBXHeaderExtension",
            children=[
                fbx_node("FBXHeaderVersion", [("I", 1003)]),
                fbx_node("FBXVersion", [("I", FBX_VERSION)]),
                fbx_node("EncryptionType", [("I", 0)]),
                fbx_node("CreationTimeStamp", children=timestamp),
                fbx_node(
                    "Creator",
                    [("S", "Star Manager TS4 LOD0 FBX extractor")],
                ),
            ],
        ),
        fbx_node(
            "GlobalSettings",
            children=[
                fbx_node("Version", [("I", 1000)]),
                fbx_node("Properties70", children=global_properties),
            ],
        ),
        fbx_node(
            "Documents",
            children=[
                fbx_node("Count", [("I", 1)]),
                fbx_node(
                    "Document",
                    [("L", document_id), ("S", "Scene"), ("S", "Scene")],
                    [
                        fbx_node("Properties70"),
                        fbx_node("RootNode", [("L", 0)]),
                    ],
                ),
            ],
        ),
        fbx_node("References"),
        fbx_node(
            "Definitions",
            children=[
                fbx_node("Version", [("I", 100)]),
                fbx_node("Count", [("I", len(definition_types))]),
            ] + definition_types,
        ),
        fbx_node("Objects", children=object_nodes),
        fbx_node("Connections", children=connection_nodes),
        fbx_node("Takes", children=[fbx_node("Current", [("S", "")])]),
    ]


def write_fbx(
    path: Path,
    mesh_name: str,
    mesh: dict[str, Any],
    object_seed: int,
    texture_path: Path | None = None,
    relative_texture_path: Path | None = None,
) -> None:
    data = bytearray(FBX_HEADER + struct.pack("<I", FBX_VERSION))
    for node in build_fbx_nodes(
        mesh_name,
        mesh,
        object_seed,
        texture_path,
        relative_texture_path,
    ):
        data += encode_fbx_node(node, len(data))
    data += b"\0" * 13
    data += FBX_FOOTER_MAGIC
    data += b"\0" * 4
    data += struct.pack("<I", FBX_VERSION)
    data += b"\0" * 120
    data += FBX_FOOTER_TAIL
    path.write_bytes(data)


def safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned or "model"


def select_lod0_meshes(candidates: Sequence[MeshCandidate]) -> list[MeshCandidate]:
    """Choose the vertex-richest resource for every shared GEOM instance ID."""
    families: dict[int, list[MeshCandidate]] = defaultdict(list)
    for candidate in candidates:
        families[candidate.resource.instance_id].append(candidate)
    selected = [
        max(
            family,
            key=lambda item: (
                item.mesh["vertex_count"],
                item.mesh["triangle_count"],
                -item.resource.index,
            ),
        )
        for family in families.values()
    ]
    return sorted(selected, key=lambda item: item.resource.index)


def extract_lod0_fbx(package_path: Path, output_dir: Path) -> dict[str, Any]:
    package = package_path.read_bytes()
    resources = read_package_index(package)
    geom_resources = [
        resource
        for resource in resources
        if resource.type_id == GEOM_RESOURCE_TYPE
    ]
    if not geom_resources:
        raise PackageFormatError("No GEOM resources were found in the package.")

    candidates: list[MeshCandidate] = []
    failures = []
    for resource in geom_resources:
        try:
            raw = read_resource_payload(package, resource)
            mesh = align_mesh_to_hs2(parse_geom(raw))
        except (PackageFormatError, GeomFormatError, struct.error) as exc:
            failures.append(
                {
                    "resource_index": resource.index,
                    "instance": f"0x{resource.instance_id:016X}",
                    "error": str(exc),
                }
            )
            continue
        candidates.append(MeshCandidate(resource=resource, mesh=mesh))

    if not candidates:
        raise GeomFormatError(
            "GEOM resources were present, but none could be parsed as a mesh."
        )

    selected = select_lod0_meshes(candidates)
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = safe_stem(package_path.stem)

    texture_resources = [
        resource
        for resource in resources
        if resource.type_id == RLE2_RESOURCE_TYPE
    ]
    texture_dir = output_dir / "textures"
    decoded_textures: list[tuple[ResourceEntry, dict[str, Any], Path]] = []
    texture_failures: list[dict[str, Any]] = []
    if texture_resources:
        texture_dir.mkdir(parents=True, exist_ok=True)
    for texture_index, resource in enumerate(texture_resources, start=1):
        texture_file = (
            f"texture_{texture_index:02d}_r{resource.index:04d}_"
            f"{resource.instance_id:016X}.png"
        )
        texture_path = texture_dir / texture_file
        try:
            raw = read_resource_payload(package, resource)
            dds, width, height, mip_count = decode_rle2(raw)
            with Image.open(io.BytesIO(dds)) as image:
                rgba = image.convert("RGBA")
                rgba.load()
                alpha_histogram = rgba.getchannel("A").histogram()
                alpha_minimum, alpha_maximum = rgba.getchannel("A").getextrema()
                alpha_covered_pixels = sum(
                    alpha_histogram[ALPHA_COVERAGE_THRESHOLD + 1 :]
                )
                alpha_coverage = alpha_covered_pixels / (width * height)
                rgba.save(texture_path, format="PNG")
        except (OSError, PackageFormatError, ValueError, struct.error) as exc:
            texture_failures.append(
                {
                    "resource_index": resource.index,
                    "instance": f"0x{resource.instance_id:016X}",
                    "error": str(exc),
                }
            )
            continue
        record = {
            "file": texture_file,
            "relative_path": (Path("textures") / texture_file).as_posix(),
            "resource_index": resource.index,
            "type": f"0x{resource.type_id:08X}",
            "group": f"0x{resource.group_id:08X}",
            "instance": f"0x{resource.instance_id:016X}",
            "width": width,
            "height": height,
            "mip_count": mip_count,
            "alpha_min": alpha_minimum,
            "alpha_max": alpha_maximum,
            "alpha_coverage": alpha_coverage,
            "has_transparency": alpha_minimum <= ALPHA_COVERAGE_THRESHOLD,
            "bytes": texture_path.stat().st_size,
        }
        decoded_textures.append((resource, record, texture_path))

    family_information: dict[int, dict[str, Any]] = {}
    for selected_candidate in selected:
        instance_id = selected_candidate.resource.instance_id
        family_candidates = [
            candidate_item
            for candidate_item in candidates
            if candidate_item.resource.instance_id == instance_id
        ]
        resource_indices = [
            candidate_item.resource.index for candidate_item in family_candidates
        ]
        family_information[instance_id] = {
            "candidates": family_candidates,
            "resource_indices": resource_indices,
            "last_resource_index": max(resource_indices),
            "selected_resource_index": selected_candidate.resource.index,
        }

    textures_by_family: dict[
        int,
        list[tuple[ResourceEntry, dict[str, Any], Path]],
    ] = defaultdict(list)
    for decoded_texture in decoded_textures:
        texture_resource = decoded_texture[0]
        owner_instance = min(
            family_information,
            key=lambda instance_id: (
                min(
                    abs(texture_resource.index - family_index)
                    for family_index in family_information[instance_id][
                        "resource_indices"
                    ]
                ),
                (
                    0
                    if texture_resource.index
                    >= family_information[instance_id]["last_resource_index"]
                    else 1
                ),
                family_information[instance_id]["selected_resource_index"],
            ),
        )
        decoded_texture[1]["model_instance"] = f"0x{owner_instance:016X}"
        textures_by_family[owner_instance].append(decoded_texture)

    exported = []
    skin_work_dir = output_dir / ".skin_work"
    for model_index, candidate in enumerate(selected, start=1):
        resource = candidate.resource
        mesh = candidate.mesh
        mesh_name = (
            f"{package_name}_model{model_index:02d}_lod0_"
            f"{resource.instance_id:016X}"
        )
        output_path = output_dir / f"{mesh_name}.fbx"
        family = family_information[resource.instance_id]
        family_candidates = family["candidates"]
        family_resource_indices = family["resource_indices"]
        family_last_index = family["last_resource_index"]
        family_textures = textures_by_family.get(
            resource.instance_id,
            decoded_textures,
        )
        default_candidates = family_textures
        default_texture = (
            min(
                default_candidates,
                key=lambda item: (
                    min(
                        abs(item[0].index - family_index)
                        for family_index in family_resource_indices
                    ),
                    0 if item[0].index >= family_last_index else 1,
                    item[0].index,
                ),
            )
            if default_candidates
            else None
        )
        coverage_textures = []
        if default_texture:
            default_record = default_texture[1]
            if default_record["has_transparency"]:
                coverage_textures = [
                    texture
                    for texture in family_textures
                    if texture[1]["width"] == default_record["width"]
                    and texture[1]["height"] == default_record["height"]
                    and texture[1]["has_transparency"]
                    and abs(
                        texture[1]["alpha_coverage"]
                        - default_record["alpha_coverage"]
                    )
                    <= 0.01
                ]
            else:
                coverage_textures = [default_texture]
        coverage = combine_alpha_coverage(
            [texture[2] for texture in coverage_textures]
        )
        mesh, coverage_statistics = filter_mesh_by_alpha_coverage(mesh, coverage)
        coverage_statistics["texture_files"] = [
            texture[1]["file"] for texture in coverage_textures
        ]
        skin_data_relative_path = ""
        if mesh.get("bone_hashes") and mesh.get("bone_indices"):
            skin_work_dir.mkdir(parents=True, exist_ok=True)
            skin_data_path = skin_work_dir / f"{mesh_name}.skin.json"
            skin_data_path.write_text(
                json.dumps(
                    {
                        "mesh_name": mesh_name,
                        "vertex_count": mesh["vertex_count"],
                        "bone_hashes": mesh["bone_hashes"],
                        "bone_indices": [
                            value
                            for vertex_indices in mesh["bone_indices"]
                            for value in vertex_indices
                        ],
                        "bone_weights": [
                            value
                            for vertex_weights in mesh["bone_weights"]
                            for value in vertex_weights
                        ],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            skin_data_relative_path = skin_data_path.relative_to(output_dir).as_posix()
        write_fbx(
            output_path,
            mesh_name,
            mesh,
            resource.index,
            default_texture[2] if default_texture else None,
            Path(default_texture[1]["relative_path"]) if default_texture else None,
        )

        positions = mesh["positions"]
        bounds_min = [min(axis) for axis in zip(*positions)]
        bounds_max = [max(axis) for axis in zip(*positions)]
        family_size = len(family_candidates)
        exported.append(
            {
                "file": output_path.name,
                "resource_index": resource.index,
                "type": f"0x{resource.type_id:08X}",
                "group": f"0x{resource.group_id:08X}",
                "instance": f"0x{resource.instance_id:016X}",
                "source_lod_candidates": family_size,
                "vertices": mesh["vertex_count"],
                "triangles": mesh["triangle_count"],
                "uv_sets": len(mesh["uv_sets"]),
                "has_normals": bool(mesh["normals"]),
                "has_skinning_data": bool(skin_data_relative_path),
                "bone_palette_size": len(mesh.get("bone_hashes") or []),
                "skin_data_relative_path": skin_data_relative_path,
                "bounds_min": bounds_min,
                "bounds_max": bounds_max,
                "bytes": output_path.stat().st_size,
                "removed_untextured_vertices": coverage_statistics[
                    "removed_vertices"
                ],
                "removed_untextured_triangles": coverage_statistics[
                    "removed_triangles"
                ],
                "alpha_coverage_filter": coverage_statistics,
                "default_texture": (
                    {
                        "file": default_texture[1]["file"],
                        "relative_path": default_texture[1]["relative_path"],
                        "resource_index": default_texture[1]["resource_index"],
                        "instance": default_texture[1]["instance"],
                    }
                    if default_texture
                    else None
                ),
            }
        )

    textures = [record for _resource, record, _path in decoded_textures]
    manifest = {
        "source": str(package_path.resolve()),
        "output_dir": str(output_dir.resolve()),
        "dbpf_resource_count": len(resources),
        "geom_resource_count": len(geom_resources),
        "parsed_geom_count": len(candidates),
        "skipped_non_lod0_count": len(candidates) - len(selected),
        "exported_model_count": len(exported),
        "rle2_resource_count": len(texture_resources),
        "texture_count": len(textures),
        "selection_rule": (
            "Group GEOM resources by instance ID and select the resource with "
            "the highest vertex count in each group."
        ),
        "geometry_filter_rule": (
            "Remove triangles whose primary UV does not intersect alpha coverage "
            "in any matching diffuse swatch, then compact unused vertices."
        ),
        "fbx_version": FBX_VERSION,
        "coordinate_system": {
            "target": "Honey Select 2 FBX",
            "up_axis": "+Y in FBX / +Z after Blender import",
            "front_axis": "+Z in FBX / -Y after Blender import",
            "unit": "centimeter",
            "source_position_scale": HS2_POSITION_SCALE,
        },
        "exports": exported,
        "textures": textures,
        "failures": failures,
        "texture_failures": texture_failures,
        "limitations": [
            "GEOM bone indices, weights, and bone hashes are preserved for the Workbench rigging stage.",
            "Blend shapes and animation are not exported.",
            "All supported RLE2 swatches are exported as external PNG files.",
            "Each FBX references one default swatch chosen by resource-index proximity.",
            "Faces outside the combined diffuse-swatch alpha coverage are removed before export.",
            "Positions are scaled and declared in the same centimeter/Y-up convention as the HS2 reference body FBX.",
            "All source UV sets and vertex normals are preserved when present.",
        ],
    }
    manifest_path = output_dir / "extraction_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract only the largest LOD0 GEOM mesh from each model family "
            "in a Sims 4 DBPF package and write binary FBX 7.4 files."
        )
    )
    parser.add_argument("package", type=Path, help="Path to a .package file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Destination directory. Defaults to <package-name>_lod0_fbx next "
            "to the package."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    package_path = args.package.expanduser().resolve()
    if not package_path.is_file():
        print(f"error: package file not found: {package_path}", file=sys.stderr)
        return 2
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else package_path.with_name(f"{safe_stem(package_path.stem)}_lod0_fbx")
    )
    try:
        manifest = extract_lod0_fbx(package_path, output_dir)
    except (OSError, PackageFormatError, GeomFormatError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Exported {manifest['exported_model_count']} LOD0 FBX file(s) to "
        f"{output_dir}"
    )
    print(f"Decoded {manifest['texture_count']} RLE2 texture swatch(es) to PNG.")
    for exported in manifest["exports"]:
        print(
            f"- {exported['file']}: {exported['vertices']} vertices, "
            f"{exported['triangles']} triangles, {exported['uv_sets']} UV set(s)"
        )
    print(
        f"Skipped {manifest['skipped_non_lod0_count']} lower-detail GEOM resource(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
