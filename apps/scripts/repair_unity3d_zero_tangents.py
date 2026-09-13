"""Repair zero/invalid Mesh tangents in a Unity3D AssetBundle.

The script never overwrites the source file. For every affected vertex it
derives a tangent from adjacent triangles whose UV area is non-zero, writes the
replacement into the existing float32 tangent channel, saves a new bundle, and
then reloads that bundle to verify the repair and all non-tangent mesh data.

This is intentionally a narrow repair. It does not merge vertices, delete
triangles, rewrite UVs, recalculate valid authored tangents, or touch skinning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
from typing import Iterable, Sequence

import UnityPy
from UnityPy.export.MeshExporter import MeshHandler


DEFAULT_TANGENT_EPSILON = 1.0e-6
DEFAULT_UV_EPSILON = 1.0e-12


def _dot(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(left * right for left, right in zip(first, second))


def _subtract(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return (
        first[0] - second[0],
        first[1] - second[1],
        first[2] - second[2],
    )


def _cross(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length(value: Sequence[float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(value: Sequence[float], epsilon: float) -> tuple[float, float, float] | None:
    size = _length(value)
    if not math.isfinite(size) or size <= epsilon:
        return None
    return (value[0] / size, value[1] / size, value[2] / size)


def _is_invalid_tangent(tangent: Sequence[float], epsilon: float) -> bool:
    return (
        len(tangent) < 4
        or not all(math.isfinite(component) for component in tangent)
        or _length(tangent[:3]) <= epsilon
    )


def _triangle_tangent(
    positions: Sequence[Sequence[float]],
    uvs: Sequence[Sequence[float]],
    *,
    tangent_epsilon: float,
    uv_epsilon: float,
) -> tuple[tuple[float, float, float], float] | None:
    edge1 = _subtract(positions[1], positions[0])
    edge2 = _subtract(positions[2], positions[0])
    du1 = uvs[1][0] - uvs[0][0]
    dv1 = uvs[1][1] - uvs[0][1]
    du2 = uvs[2][0] - uvs[0][0]
    dv2 = uvs[2][1] - uvs[0][1]
    determinant = du1 * dv2 - dv1 * du2
    if not math.isfinite(determinant) or abs(determinant) <= uv_epsilon:
        return None

    tangent = tuple(
        (edge1[axis] * dv2 - edge2[axis] * dv1) / determinant
        for axis in range(3)
    )
    tangent = _normalize(tangent, tangent_epsilon)
    if tangent is None:
        return None

    face_area = _length(_cross(edge1, edge2)) * 0.5
    if not math.isfinite(face_area) or face_area <= tangent_epsilon * tangent_epsilon:
        return None
    return tangent, face_area


def _calculate_replacement_tangent(
    vertex_index: int,
    *,
    triangles_by_vertex: dict[int, list[tuple[int, tuple[int, int, int]]]],
    vertices: Sequence[Sequence[float]],
    normals: Sequence[Sequence[float]],
    tangents: Sequence[Sequence[float]],
    uvs: Sequence[Sequence[float]],
    tangent_epsilon: float,
    uv_epsilon: float,
) -> tuple[tuple[float, float, float, float], list[int]] | None:
    tangent_sum = [0.0, 0.0, 0.0]
    source_faces: list[int] = []

    for face_index, triangle in triangles_by_vertex.get(vertex_index, []):
        result = _triangle_tangent(
            [vertices[index] for index in triangle],
            [uvs[index] for index in triangle],
            tangent_epsilon=tangent_epsilon,
            uv_epsilon=uv_epsilon,
        )
        if result is None:
            continue
        face_tangent, face_area = result
        for axis in range(3):
            tangent_sum[axis] += face_tangent[axis] * face_area
        source_faces.append(face_index)

    normal = _normalize(normals[vertex_index][:3], tangent_epsilon)
    if normal is None or not source_faces:
        return None

    normal_component = _dot(tangent_sum, normal)
    orthogonal = tuple(
        tangent_sum[axis] - normal[axis] * normal_component
        for axis in range(3)
    )
    direction = _normalize(orthogonal, tangent_epsilon)
    if direction is None:
        return None

    original_w = tangents[vertex_index][3]
    handedness = -1.0 if math.isfinite(original_w) and original_w < 0 else 1.0
    return (direction[0], direction[1], direction[2], handedness), source_faces


def _mesh_snapshot(handler: MeshHandler) -> dict[str, object]:
    return {
        "vertices": tuple(handler.m_Vertices or ()),
        "normals": tuple(handler.m_Normals or ()),
        "uv0": tuple(handler.m_UV0 or ()),
        "uv1": tuple(handler.m_UV1 or ()),
        "bone_indices": tuple(handler.m_BoneIndices or ()),
        "bone_weights": tuple(handler.m_BoneWeights or ()),
        "indices": tuple(handler.m_IndexBuffer or ()),
        "tangents": tuple(handler.m_Tangents or ()),
    }


def _require_supported_mesh(mesh: object, handler: MeshHandler) -> tuple[object, object]:
    if tuple(handler.version) < (2018, 1):
        raise ValueError("只支持 Unity 2018.1 及以上版本的顶点通道布局")
    if getattr(mesh, "m_StreamData", None) and getattr(mesh.m_StreamData, "path", ""):
        raise ValueError("Mesh 顶点数据位于外部资源流中，当前脚本不会修改外部 resS 文件")

    compressed_mesh = getattr(mesh, "m_CompressedMesh", None)
    compressed_tangents = getattr(compressed_mesh, "m_Tangents", None)
    if compressed_tangents and int(getattr(compressed_tangents, "m_NumItems", 0) or 0) > 0:
        raise ValueError("Mesh 使用压缩切线数据，当前脚本只修改未压缩 float32 顶点通道")

    vertex_data = getattr(mesh, "m_VertexData", None)
    channels = list(getattr(vertex_data, "m_Channels", None) or [])
    if len(channels) <= 2:
        raise ValueError("Mesh 没有 Unity 2018+ tangent 顶点通道")
    tangent_channel = channels[2]
    if int(tangent_channel.dimension) != 4 or int(tangent_channel.format) != 0:
        raise ValueError(
            "只支持 dimension=4、format=Float32 的 tangent 顶点通道，"
            f"当前为 dimension={tangent_channel.dimension}、format={tangent_channel.format}"
        )
    if not getattr(vertex_data, "m_DataSize", None):
        raise ValueError("Mesh 顶点缓冲为空")
    return vertex_data, tangent_channel


def _patch_mesh_tangents(
    mesh: object,
    handler: MeshHandler,
    replacements: dict[int, tuple[float, float, float, float]],
) -> None:
    vertex_data, tangent_channel = _require_supported_mesh(mesh, handler)
    streams = handler.get_streams(list(vertex_data.m_Channels), int(vertex_data.m_VertexCount))
    stream = streams[int(tangent_channel.stream)]
    component_size = handler.get_channel_component_size(tangent_channel)
    if component_size != 4 or handler.get_channel_dtype(tangent_channel) != "f":
        raise ValueError("tangent 通道并非 float32，已停止以避免破坏顶点缓冲")

    data = bytearray(vertex_data.m_DataSize)
    endian = "<" if handler.endianess == "<" else ">"
    for vertex_index, tangent in replacements.items():
        offset = int(stream.offset) + int(tangent_channel.offset) + int(stream.stride) * vertex_index
        if offset < 0 or offset + 16 > len(data):
            raise ValueError(f"顶点 {vertex_index} 的 tangent 缓冲偏移越界")
        struct.pack_into(f"{endian}4f", data, offset, *tangent)

    vertex_data.m_DataSize = bytes(data)
    mesh.save()


def _save_environment(environment: object, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="star-manager-tangent-repair-", dir=output_path.parent) as temp_dir:
        environment.save(pack="original", out_path=temp_dir)
        saved_files = [path for path in Path(temp_dir).iterdir() if path.is_file()]
        if len(saved_files) != 1:
            raise ValueError(f"UnityPy 应生成 1 个资源文件，实际生成 {len(saved_files)} 个")
        shutil.copyfile(saved_files[0], output_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_mesh_handlers(path: Path) -> tuple[object, dict[int, tuple[object, MeshHandler]]]:
    environment = UnityPy.load(str(path))
    meshes: dict[int, tuple[object, MeshHandler]] = {}
    for obj in environment.objects:
        if obj.type.name != "Mesh":
            continue
        mesh = obj.read()
        handler = MeshHandler(mesh)
        handler.process()
        meshes[int(obj.path_id)] = (mesh, handler)
    return environment, meshes


def _selected_meshes(
    meshes: dict[int, tuple[object, MeshHandler]],
    path_ids: set[int],
) -> Iterable[tuple[int, object, MeshHandler]]:
    for path_id, (mesh, handler) in meshes.items():
        if not path_ids or path_id in path_ids:
            yield path_id, mesh, handler


def repair_file(
    source: Path,
    output: Path,
    *,
    mesh_path_ids: set[int],
    tangent_epsilon: float,
    uv_epsilon: float,
    dry_run: bool,
) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if source.suffix.lower() != ".unity3d":
        raise ValueError("输入文件必须是 .unity3d")
    if source == output:
        raise ValueError("输出路径不能与源文件相同；脚本不会覆盖源文件")
    if output.exists():
        raise FileExistsError(f"输出文件已存在：{output}")

    environment, meshes = _load_mesh_handlers(source)
    if not meshes:
        raise ValueError("Unity3D 中没有 Mesh 对象")
    missing_path_ids = mesh_path_ids.difference(meshes)
    if missing_path_ids:
        raise ValueError(f"找不到 Mesh path ID：{sorted(missing_path_ids)}")

    snapshots: dict[int, dict[str, object]] = {}
    replacements_by_mesh: dict[int, dict[int, tuple[float, float, float, float]]] = {}
    mesh_reports: list[dict[str, object]] = []

    for path_id, mesh, handler in _selected_meshes(meshes, mesh_path_ids):
        if not handler.m_Vertices or not handler.m_Normals or not handler.m_Tangents or not handler.m_UV0:
            raise ValueError(f"Mesh {path_id} 缺少位置、法线、切线或 UV0 数据")
        if not (
            len(handler.m_Vertices)
            == len(handler.m_Normals)
            == len(handler.m_Tangents)
            == len(handler.m_UV0)
        ):
            raise ValueError(f"Mesh {path_id} 的顶点属性数量不一致")

        triangles = [triangle for group in handler.get_triangles() for triangle in group]
        triangles_by_vertex: dict[int, list[tuple[int, tuple[int, int, int]]]] = {}
        for face_index, triangle in enumerate(triangles):
            if len(triangle) != 3:
                continue
            typed_triangle = (int(triangle[0]), int(triangle[1]), int(triangle[2]))
            for vertex_index in typed_triangle:
                triangles_by_vertex.setdefault(vertex_index, []).append((face_index, typed_triangle))

        invalid_vertices = [
            index
            for index, tangent in enumerate(handler.m_Tangents)
            if _is_invalid_tangent(tangent, tangent_epsilon)
        ]
        replacements: dict[int, tuple[float, float, float, float]] = {}
        repaired_vertices: list[dict[str, object]] = []
        unresolved: list[int] = []
        for vertex_index in invalid_vertices:
            result = _calculate_replacement_tangent(
                vertex_index,
                triangles_by_vertex=triangles_by_vertex,
                vertices=handler.m_Vertices,
                normals=handler.m_Normals,
                tangents=handler.m_Tangents,
                uvs=handler.m_UV0,
                tangent_epsilon=tangent_epsilon,
                uv_epsilon=uv_epsilon,
            )
            if result is None:
                unresolved.append(vertex_index)
                continue
            tangent, source_faces = result
            replacements[vertex_index] = tangent
            repaired_vertices.append(
                {
                    "vertex": vertex_index,
                    "position": list(handler.m_Vertices[vertex_index]),
                    "old_tangent": list(handler.m_Tangents[vertex_index]),
                    "new_tangent": list(tangent),
                    "source_faces": source_faces,
                }
            )

        if unresolved:
            raise ValueError(
                f"Mesh {path_id} 有无法从相邻非退化 UV 面恢复的切线顶点：{unresolved}；未写出文件"
            )

        snapshots[path_id] = _mesh_snapshot(handler)
        replacements_by_mesh[path_id] = replacements
        mesh_reports.append(
            {
                "path_id": path_id,
                "name": str(getattr(mesh, "m_Name", "") or ""),
                "vertex_count": len(handler.m_Vertices),
                "triangle_count": len(triangles),
                "invalid_tangents_before": len(invalid_vertices),
                "repaired_vertices": repaired_vertices,
                "invalid_tangents_after": 0 if replacements else len(invalid_vertices),
            }
        )

    total_replacements = sum(len(values) for values in replacements_by_mesh.values())
    report: dict[str, object] = {
        "ok": True,
        "dry_run": dry_run,
        "source": str(source),
        "output": None if dry_run or total_replacements == 0 else str(output),
        "source_sha256": _sha256(source),
        "output_sha256": None,
        "total_repaired_vertices": total_replacements,
        "verified": False,
        "meshes": mesh_reports,
    }
    if dry_run or total_replacements == 0:
        report["verified"] = total_replacements == 0
        return report

    for path_id, mesh, handler in _selected_meshes(meshes, mesh_path_ids):
        replacements = replacements_by_mesh[path_id]
        if replacements:
            _patch_mesh_tangents(mesh, handler, replacements)
    _save_environment(environment, output)

    _, repaired_meshes = _load_mesh_handlers(output)
    for path_id, replacements in replacements_by_mesh.items():
        if path_id not in repaired_meshes:
            raise ValueError(f"验证失败：输出文件缺少 Mesh {path_id}")
        _, repaired_handler = repaired_meshes[path_id]
        before = snapshots[path_id]
        after = _mesh_snapshot(repaired_handler)
        for attribute in ("vertices", "normals", "uv0", "uv1", "bone_indices", "bone_weights", "indices"):
            if after[attribute] != before[attribute]:
                raise ValueError(f"验证失败：Mesh {path_id} 的 {attribute} 在修复中发生变化")
        before_tangents = before["tangents"]
        after_tangents = after["tangents"]
        if len(before_tangents) != len(after_tangents):
            raise ValueError(f"验证失败：Mesh {path_id} 的 tangent 数量发生变化")
        for vertex_index, tangent in enumerate(after_tangents):
            if vertex_index in replacements:
                if _is_invalid_tangent(tangent, tangent_epsilon):
                    raise ValueError(f"验证失败：Mesh {path_id} 顶点 {vertex_index} 的切线仍无效")
            elif tangent != before_tangents[vertex_index]:
                raise ValueError(f"验证失败：Mesh {path_id} 顶点 {vertex_index} 的有效切线被意外修改")

    report["output_sha256"] = _sha256(output)
    report["verified"] = True
    return report


def _default_output(source: Path) -> Path:
    return source.with_name(f"{source.stem}.repaired{source.suffix}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="修复 Unity3D Mesh 中的零/无效切线，并写出经过重新载入验证的新文件。",
    )
    parser.add_argument("source", type=Path, help="源 .unity3d 文件")
    parser.add_argument("output", nargs="?", type=Path, help="输出文件，默认追加 .repaired.unity3d")
    parser.add_argument(
        "--mesh-path-id",
        type=int,
        action="append",
        default=[],
        help="只处理指定 Mesh path ID；可重复指定",
    )
    parser.add_argument("--tangent-epsilon", type=float, default=DEFAULT_TANGENT_EPSILON)
    parser.add_argument("--uv-epsilon", type=float, default=DEFAULT_UV_EPSILON)
    parser.add_argument("--dry-run", action="store_true", help="只分析，不写出文件")
    parser.add_argument("--report", type=Path, help="另存 UTF-8 JSON 报告")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source = args.source.expanduser()
    output = args.output.expanduser() if args.output else _default_output(source)
    try:
        report = repair_file(
            source,
            output,
            mesh_path_ids=set(args.mesh_path_id),
            tangent_epsilon=args.tangent_epsilon,
            uv_epsilon=args.uv_epsilon,
            dry_run=args.dry_run,
        )
    except Exception as error:
        report = {"ok": False, "error": str(error), "source": str(source), "output": str(output)}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    print(serialized)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(serialized + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
