"""Write validated tangent-space layers into an FBX by using Blender.

Run this script through Blender rather than normal Python. The source FBX is
never overwritten. The script imports the complete scene, calculates tangent
space for every UV layer, exports a new FBX with explicit tangent/binormal
layers, parses the exported binary FBX to verify those layers, and reimports it
to verify mesh topology and skin-group metadata.

Example:
    blender.exe --background --factory-startup \
      --python apps/scripts/blender_repair_fbx_tangents.py -- \
      --input source.fbx --output source.tangent-repaired.fbx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Iterable, Sequence

import bpy
from io_scene_fbx import parse_fbx


DEFAULT_EPSILON = 1.0e-6
DEFAULT_UV_EPSILON = 1.0e-12


def _script_args() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 Blender MikkTSpace 为 FBX 写入经过验证的 tangent/binormal 层。",
    )
    parser.add_argument("--input", required=True, type=Path, help="源 FBX 文件")
    parser.add_argument("--output", type=Path, help="输出 FBX，默认追加 .tangent-repaired.fbx")
    parser.add_argument("--report", type=Path, help="另存 UTF-8 JSON 报告")
    parser.add_argument("--dry-run", action="store_true", help="只分析和计算，不写出 FBX")
    parser.add_argument("--epsilon", type=float, default=DEFAULT_EPSILON)
    parser.add_argument("--uv-epsilon", type=float, default=DEFAULT_UV_EPSILON)
    return parser.parse_args(_script_args())


def _default_output(source: Path) -> Path:
    return source.with_name(f"{source.stem}.tangent-repaired{source.suffix}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _walk_fbx_elements(element: object) -> Iterable[object]:
    yield element
    for child in element.elems:
        yield from _walk_fbx_elements(child)


def _fbx_child(element: object, element_id: bytes) -> object | None:
    return next((child for child in element.elems if child.id == element_id), None)


def _property_text(element: object | None) -> str:
    if element is None or not element.props:
        return ""
    value = element.props[0]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _inspect_raw_tangent_layers(path: Path, epsilon: float) -> dict[str, object]:
    root, version = parse_fbx.parse(str(path))
    tangent_layers: list[dict[str, object]] = []
    binormal_layers = 0
    for element in _walk_fbx_elements(root):
        if element.id == b"LayerElementBinormal":
            binormal_layers += 1
            continue
        if element.id != b"LayerElementTangent":
            continue
        values_element = _fbx_child(element, b"Tangents")
        raw_values = list(values_element.props[0]) if values_element and values_element.props else []
        vectors = [raw_values[offset : offset + 3] for offset in range(0, len(raw_values), 3)]
        invalid_indices = [
            index
            for index, tangent in enumerate(vectors)
            if len(tangent) != 3
            or not all(math.isfinite(component) for component in tangent)
            or math.sqrt(sum(component * component for component in tangent)) <= epsilon
        ]
        tangent_layers.append(
            {
                "name": _property_text(_fbx_child(element, b"Name")),
                "mapping": _property_text(_fbx_child(element, b"MappingInformationType")),
                "reference": _property_text(_fbx_child(element, b"ReferenceInformationType")),
                "vector_count": len(vectors),
                "invalid_count": len(invalid_indices),
                "invalid_indices": invalid_indices[:100],
            }
        )
    return {
        "fbx_version": int(version),
        "tangent_layer_count": len(tangent_layers),
        "binormal_layer_count": binormal_layers,
        "tangent_layers": tangent_layers,
    }


def _uv_triangle_area(mesh: bpy.types.Mesh, polygon: bpy.types.MeshPolygon, uv_layer: object) -> float:
    if len(polygon.loop_indices) != 3:
        return float("nan")
    first, second, third = [uv_layer.data[index].uv for index in polygon.loop_indices]
    return 0.5 * (
        (second.x - first.x) * (third.y - first.y)
        - (second.y - first.y) * (third.x - first.x)
    )


def _mesh_snapshot() -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    for obj in sorted((value for value in bpy.data.objects if value.type == "MESH"), key=lambda value: value.name):
        mesh = obj.data
        snapshots[obj.name] = {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "loops": len(mesh.loops),
            "uv_layers": list(mesh.uv_layers.keys()),
            "materials": [material.name if material else "" for material in mesh.materials],
            "vertex_groups": sorted(group.name for group in obj.vertex_groups),
            "shape_keys": (
                [block.name for block in mesh.shape_keys.key_blocks]
                if mesh.shape_keys and mesh.shape_keys.key_blocks
                else []
            ),
        }
    return snapshots


def _armature_snapshot() -> dict[str, list[str]]:
    return {
        obj.name: sorted(bone.name for bone in obj.data.bones)
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
    }


def _calculate_scene_tangents(epsilon: float, uv_epsilon: float) -> list[dict[str, object]]:
    mesh_reports: list[dict[str, object]] = []
    meshes = sorted((obj for obj in bpy.data.objects if obj.type == "MESH"), key=lambda obj: obj.name)
    if not meshes:
        raise ValueError("FBX 中没有 Mesh 对象")

    for obj in meshes:
        mesh = obj.data
        if not mesh.uv_layers:
            raise ValueError(f"Mesh {obj.name} 没有 UV 层，无法计算切线")
        non_triangles = [polygon.index for polygon in mesh.polygons if len(polygon.loop_indices) != 3]
        if non_triangles:
            raise ValueError(
                f"Mesh {obj.name} 含有 {len(non_triangles)} 个非三角面；"
                "脚本不会在修复过程中隐式改变拓扑"
            )

        uv_reports: list[dict[str, object]] = []
        for uv_layer in mesh.uv_layers:
            degenerate_faces = [
                polygon.index
                for polygon in mesh.polygons
                if abs(_uv_triangle_area(mesh, polygon, uv_layer)) <= uv_epsilon
            ]
            mesh.calc_tangents(uvmap=uv_layer.name)
            invalid_loops = [
                loop.index
                for loop in mesh.loops
                if not all(math.isfinite(component) for component in loop.tangent)
                or loop.tangent.length <= epsilon
                or not math.isfinite(loop.bitangent_sign)
            ]
            uv_reports.append(
                {
                    "name": uv_layer.name,
                    "degenerate_uv_faces": len(degenerate_faces),
                    "degenerate_uv_face_indices": degenerate_faces[:200],
                    "invalid_tangent_loops": len(invalid_loops),
                    "invalid_tangent_loop_indices": invalid_loops[:200],
                }
            )
            mesh.free_tangents()
            if invalid_loops:
                raise ValueError(
                    f"Mesh {obj.name} 的 UV 层 {uv_layer.name} 仍有 "
                    f"{len(invalid_loops)} 个无效切线面角"
                )

        mesh_reports.append(
            {
                "object": obj.name,
                "mesh": mesh.name,
                "vertices": len(mesh.vertices),
                "polygons": len(mesh.polygons),
                "loops": len(mesh.loops),
                "uv_layers": uv_reports,
            }
        )
    return mesh_reports


def _import_fbx(path: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(path),
        use_custom_normals=True,
        use_anim=False,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise ValueError(f"Blender 导入 FBX 失败：{sorted(result)}")


def _export_fbx(path: Path) -> None:
    result = bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=False,
        object_types={"EMPTY", "CAMERA", "LIGHT", "ARMATURE", "MESH", "OTHER"},
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=True,
        use_custom_props=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
        axis_forward="-Z",
        axis_up="Y",
    )
    if "FINISHED" not in result:
        raise ValueError(f"Blender 导出 FBX 失败：{sorted(result)}")


def _compare_snapshots(
    before_meshes: dict[str, dict[str, object]],
    after_meshes: dict[str, dict[str, object]],
    before_armatures: dict[str, list[str]],
    after_armatures: dict[str, list[str]],
) -> None:
    if before_meshes.keys() != after_meshes.keys():
        raise ValueError(
            "验证失败：重新导入后的 Mesh 对象集合发生变化："
            f"before={sorted(before_meshes)}, after={sorted(after_meshes)}"
        )
    for name in before_meshes:
        before = before_meshes[name]
        after = after_meshes[name]
        for attribute in (
            "vertices",
            "edges",
            "polygons",
            "loops",
            "uv_layers",
            "materials",
            "vertex_groups",
            "shape_keys",
        ):
            if before[attribute] != after[attribute]:
                raise ValueError(
                    f"验证失败：Mesh {name} 的 {attribute} 发生变化："
                    f"before={before[attribute]!r}, after={after[attribute]!r}"
                )
    if before_armatures != after_armatures:
        raise ValueError("验证失败：重新导入后的骨架或骨骼名称发生变化")


def repair_fbx(
    source: Path,
    output: Path,
    *,
    epsilon: float,
    uv_epsilon: float,
    dry_run: bool,
) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if source.suffix.lower() != ".fbx":
        raise ValueError("输入文件必须是 .fbx")
    if source == output:
        raise ValueError("输出路径不能与源文件相同；脚本不会覆盖源 FBX")
    if output.exists():
        raise FileExistsError(f"输出文件已存在：{output}")
    if epsilon <= 0 or uv_epsilon <= 0:
        raise ValueError("epsilon 和 uv-epsilon 必须大于零")

    raw_before = _inspect_raw_tangent_layers(source, epsilon)
    _import_fbx(source)
    before_meshes = _mesh_snapshot()
    before_armatures = _armature_snapshot()
    mesh_reports = _calculate_scene_tangents(epsilon, uv_epsilon)

    report: dict[str, object] = {
        "ok": True,
        "dry_run": dry_run,
        "source": str(source),
        "output": None if dry_run else str(output),
        "source_sha256": _sha256(source),
        "output_sha256": None,
        "raw_tangents_before": raw_before,
        "raw_tangents_after": None,
        "verified": False,
        "meshes": mesh_reports,
    }
    if dry_run:
        return report

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="star-manager-fbx-tangent-", dir=output.parent) as temp_dir:
        temporary_output = Path(temp_dir) / output.name
        _export_fbx(temporary_output)
        raw_after = _inspect_raw_tangent_layers(temporary_output, epsilon)
        expected_layers = sum(len(mesh_report["uv_layers"]) for mesh_report in mesh_reports)
        if raw_after["tangent_layer_count"] < expected_layers:
            raise ValueError(
                "验证失败：导出的 tangent 层数量不足，"
                f"expected>={expected_layers}, actual={raw_after['tangent_layer_count']}"
            )
        if raw_after["binormal_layer_count"] < expected_layers:
            raise ValueError(
                "验证失败：导出的 binormal 层数量不足，"
                f"expected>={expected_layers}, actual={raw_after['binormal_layer_count']}"
            )
        invalid_exported = sum(
            int(layer["invalid_count"])
            for layer in raw_after["tangent_layers"]
        )
        if invalid_exported:
            raise ValueError(f"验证失败：导出的 FBX 仍有 {invalid_exported} 个无效切线向量")

        _import_fbx(temporary_output)
        _compare_snapshots(
            before_meshes,
            _mesh_snapshot(),
            before_armatures,
            _armature_snapshot(),
        )
        shutil.copyfile(temporary_output, output)

    report["raw_tangents_after"] = raw_after
    report["output_sha256"] = _sha256(output)
    report["verified"] = True
    return report


def main() -> int:
    args = _parse_args()
    source = args.input.expanduser()
    output = args.output.expanduser() if args.output else _default_output(source)
    try:
        report = repair_fbx(
            source,
            output,
            epsilon=args.epsilon,
            uv_epsilon=args.uv_epsilon,
            dry_run=args.dry_run,
        )
    except Exception as error:
        report = {
            "ok": False,
            "error": str(error),
            "source": str(source),
            "output": str(output),
        }
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
