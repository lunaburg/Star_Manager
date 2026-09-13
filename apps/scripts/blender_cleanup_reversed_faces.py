"""Analyze or remove exactly overlapping, opposite-facing FBX faces.

The command-line workflow never overwrites the source FBX.  It first groups
faces by quantized object-local vertex positions, accepts only two-face groups
whose geometric normals are nearly opposite, and keeps the face that points
farther away from the mesh bounding-box center.  Repair output is exported to
a temporary FBX and re-imported before it replaces the requested output path.

Examples::

    blender.exe --background --factory-startup \
      --python apps/scripts/blender_cleanup_reversed_faces.py -- \
      --input clothing.fbx --action analyze --report analysis.json

    blender.exe --background --factory-startup \
      --python apps/scripts/blender_cleanup_reversed_faces.py -- \
      --input clothing.fbx --action repair --output clothing.normals-repaired.fbx \
      --report clothing.normals-repaired.json

The file can still be run interactively from Blender's Scripting workspace.
With no command-line arguments it selects proposed faces on the selected mesh
objects.  Change ``INTERACTIVE_ACTION`` to ``DELETE`` only after inspection.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector


INTERACTIVE_ACTION = "SELECT"
DEFAULT_POSITION_TOLERANCE = 1.0e-6
DEFAULT_OPPOSITE_NORMAL_DOT = -0.999
OUTWARD_SCORE_EPSILON = 1.0e-8
BACKUP_COLLECTION_NAME = "__StarManager_ReversedFace_Backups"


def _script_args() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def _parse_args(arguments: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="分析或清理 FBX 中位置重合且朝向相反的重复面。",
    )
    parser.add_argument("--input", required=True, type=Path, help="源 FBX 文件")
    parser.add_argument(
        "--action",
        choices=("analyze", "repair"),
        default="analyze",
        help="analyze 只分析；repair 导出清理后的副本",
    )
    parser.add_argument("--output", type=Path, help="修复输出 FBX")
    parser.add_argument("--report", type=Path, help="UTF-8 JSON 报告路径")
    parser.add_argument(
        "--position-tolerance",
        type=float,
        default=DEFAULT_POSITION_TOLERANCE,
        help="判定顶点位置相同的容差（Blender 对象局部单位）",
    )
    parser.add_argument(
        "--opposite-normal-dot",
        type=float,
        default=DEFAULT_OPPOSITE_NORMAL_DOT,
        help="判定法向相反的点积上限",
    )
    return parser.parse_args(arguments)


def _default_output(source: Path) -> Path:
    return source.with_name(f"{source.stem}.normals-repaired{source.suffix}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _position_key(co: Vector, tolerance: float) -> tuple[int, int, int]:
    return tuple(round(float(axis) / tolerance) for axis in co)


def _face_key(
    face: bmesh.types.BMFace,
    tolerance: float,
) -> tuple[int, tuple[tuple[int, int, int], ...]]:
    positions = tuple(sorted(_position_key(vertex.co, tolerance) for vertex in face.verts))
    return len(face.verts), positions


def _bounding_box_center(bm: bmesh.types.BMesh) -> Vector:
    if not bm.verts:
        return Vector((0.0, 0.0, 0.0))
    minimum = Vector((float("inf"), float("inf"), float("inf")))
    maximum = Vector((float("-inf"), float("-inf"), float("-inf")))
    for vertex in bm.verts:
        for axis in range(3):
            minimum[axis] = min(minimum[axis], vertex.co[axis])
            maximum[axis] = max(maximum[axis], vertex.co[axis])
    return (minimum + maximum) * 0.5


def _find_reverse_duplicates(
    bm: bmesh.types.BMesh,
    *,
    position_tolerance: float,
    opposite_normal_dot: float,
) -> tuple[set[bmesh.types.BMFace], dict[str, int]]:
    """Return safe removal candidates and diagnostic group counters."""

    bm.normal_update()
    center = _bounding_box_center(bm)
    groups: dict[tuple, list[bmesh.types.BMFace]] = defaultdict(list)
    for face in bm.faces:
        groups[_face_key(face, position_tolerance)].append(face)

    proposed: set[bmesh.types.BMFace] = set()
    counters = {
        "position_duplicate_groups": 0,
        "reverse_duplicate_groups": 0,
        "ambiguous_groups": 0,
        "multi_face_groups": 0,
        "same_direction_groups": 0,
        "material_mismatch_groups": 0,
        "separate_vertex_groups": 0,
    }

    for faces in groups.values():
        if len(faces) < 2:
            continue
        counters["position_duplicate_groups"] += 1
        if len(faces) != 2:
            counters["multi_face_groups"] += 1
            continue

        first, second = faces
        if first.normal.dot(second.normal) > opposite_normal_dot:
            counters["same_direction_groups"] += 1
            continue

        if first.material_index != second.material_index:
            counters["material_mismatch_groups"] += 1
        if {vertex.index for vertex in first.verts} != {vertex.index for vertex in second.verts}:
            counters["separate_vertex_groups"] += 1

        first_score = first.normal.dot(first.calc_center_median() - center)
        second_score = second.normal.dot(second.calc_center_median() - center)
        if abs(first_score - second_score) <= OUTWARD_SCORE_EPSILON:
            counters["ambiguous_groups"] += 1
            continue

        counters["reverse_duplicate_groups"] += 1
        proposed.add(second if first_score > second_score else first)

    return proposed, counters


def _object_analysis(
    obj: bpy.types.Object,
    *,
    position_tolerance: float,
    opposite_normal_dot: float,
) -> tuple[dict[str, object], set[int]]:
    mesh = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        proposed, counters = _find_reverse_duplicates(
            bm,
            position_tolerance=position_tolerance,
            opposite_normal_dot=opposite_normal_dot,
        )
        proposed_indices = {face.index for face in proposed}
    finally:
        bm.free()

    report: dict[str, object] = {
        "object": obj.name,
        "mesh": mesh.name,
        "vertices_before": len(mesh.vertices),
        "edges_before": len(mesh.edges),
        "faces_before": len(mesh.polygons),
        "loops_before": len(mesh.loops),
        "faces_proposed": len(proposed_indices),
        "shape_keys": (
            [block.name for block in mesh.shape_keys.key_blocks]
            if mesh.shape_keys and mesh.shape_keys.key_blocks
            else []
        ),
        "materials": [material.name if material else "" for material in mesh.materials],
        **counters,
    }
    return report, proposed_indices


def _delete_face_indices(obj: bpy.types.Object, face_indices: set[int]) -> None:
    if not face_indices:
        return
    mesh = obj.data
    if mesh.shape_keys and mesh.shape_keys.key_blocks:
        raise ValueError(
            f"Mesh {obj.name} 含 Shape Keys；删除拓扑会使其失效，脚本拒绝自动修复"
        )
    if mesh.users > 1:
        obj.data = mesh.copy()
        mesh = obj.data

    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        faces = [bm.faces[index] for index in sorted(face_indices)]
        # ``FACES_ONLY`` would retain the duplicate shell's now-unused edges
        # and vertices.  Blender's FBX exporter drops those loose elements,
        # which makes the in-memory and round-tripped topology disagree.
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
    finally:
        bm.free()


def _mesh_snapshot() -> dict[str, dict[str, object]]:
    return {
        obj.name: {
            "vertices": len(obj.data.vertices),
            "edges": len(obj.data.edges),
            "faces": len(obj.data.polygons),
            "loops": len(obj.data.loops),
            "uv_layers": list(obj.data.uv_layers.keys()),
            "materials": [material.name if material else "" for material in obj.data.materials],
            "vertex_groups": sorted(group.name for group in obj.vertex_groups),
        }
        for obj in sorted(
            (candidate for candidate in bpy.data.objects if candidate.type == "MESH"),
            key=lambda candidate: candidate.name,
        )
    }


def _armature_snapshot() -> dict[str, list[str]]:
    return {
        obj.name: sorted(bone.name for bone in obj.data.bones)
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
    }


def _import_fbx(source: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(source),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise ValueError(f"Blender 导入 FBX 失败：{sorted(result)}")
    if not any(obj.type == "MESH" for obj in bpy.data.objects):
        raise ValueError("FBX 中没有 Mesh 对象")


def _export_fbx(output: Path) -> None:
    result = bpy.ops.export_scene.fbx(
        filepath=str(output),
        use_selection=False,
        object_types={"EMPTY", "ARMATURE", "MESH", "OTHER"},
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=False,
        use_custom_props=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
        axis_forward="-Z",
        axis_up="Y",
    )
    if "FINISHED" not in result or not output.is_file():
        raise ValueError(f"Blender 导出 FBX 失败：{sorted(result)}")


def _verify_round_trip(
    output: Path,
    expected_meshes: dict[str, dict[str, object]],
    expected_armatures: dict[str, list[str]],
) -> None:
    _import_fbx(output)
    actual_meshes = _mesh_snapshot()
    actual_armatures = _armature_snapshot()
    if expected_meshes.keys() != actual_meshes.keys():
        raise ValueError(
            "导出验证失败：Mesh 对象集合发生变化："
            f"expected={sorted(expected_meshes)}, actual={sorted(actual_meshes)}"
        )
    for name, expected in expected_meshes.items():
        actual = actual_meshes[name]
        for field in (
            "vertices",
            "edges",
            "faces",
            "loops",
            "uv_layers",
            "materials",
            "vertex_groups",
        ):
            if expected[field] != actual[field]:
                raise ValueError(
                    f"导出验证失败：Mesh {name} 的 {field} 发生变化："
                    f"expected={expected[field]!r}, actual={actual[field]!r}"
                )
    if expected_armatures != actual_armatures:
        raise ValueError("导出验证失败：骨架对象或骨骼名称发生变化")


def process_fbx(
    source: Path,
    output: Path | None,
    *,
    action: str,
    position_tolerance: float,
    opposite_normal_dot: float,
) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    if source.suffix.lower() != ".fbx":
        raise ValueError("输入文件必须是 .fbx")
    if position_tolerance <= 0:
        raise ValueError("position-tolerance 必须大于零")
    if not -1.0 <= opposite_normal_dot < 0.0:
        raise ValueError("opposite-normal-dot 必须在 [-1, 0) 范围内")

    resolved_output: Path | None = None
    if action == "repair":
        resolved_output = (output or _default_output(source)).expanduser().resolve()
        if resolved_output == source:
            raise ValueError("输出路径不能与源文件相同；脚本不会覆盖源 FBX")
        if resolved_output.exists():
            raise FileExistsError(f"输出文件已存在：{resolved_output}")

    _import_fbx(source)
    object_reports: list[dict[str, object]] = []
    proposed_by_object: dict[str, set[int]] = {}
    for obj in sorted(
        (candidate for candidate in bpy.data.objects if candidate.type == "MESH"),
        key=lambda candidate: candidate.name,
    ):
        object_report, proposed = _object_analysis(
            obj,
            position_tolerance=position_tolerance,
            opposite_normal_dot=opposite_normal_dot,
        )
        object_reports.append(object_report)
        proposed_by_object[obj.name] = proposed

    proposed_total = sum(len(indices) for indices in proposed_by_object.values())
    report: dict[str, object] = {
        "ok": True,
        "action": action,
        "source": str(source),
        "output": str(resolved_output) if resolved_output else None,
        "source_sha256": _sha256(source),
        "output_sha256": None,
        "position_tolerance": position_tolerance,
        "opposite_normal_dot": opposite_normal_dot,
        "faces_proposed_total": proposed_total,
        "faces_removed_total": 0,
        "verified": False,
        "objects": object_reports,
    }
    if action == "analyze":
        return report

    assert resolved_output is not None
    for obj in (candidate for candidate in bpy.data.objects if candidate.type == "MESH"):
        _delete_face_indices(obj, proposed_by_object[obj.name])
    for object_report in object_reports:
        obj = bpy.data.objects[object_report["object"]]
        object_report["vertices_after"] = len(obj.data.vertices)
        object_report["edges_after"] = len(obj.data.edges)
        object_report["faces_after"] = len(obj.data.polygons)
        object_report["loops_after"] = len(obj.data.loops)

    expected_meshes = _mesh_snapshot()
    expected_armatures = _armature_snapshot()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = resolved_output.with_name(
        f".{resolved_output.stem}.tmp-{os.getpid()}{resolved_output.suffix}"
    )
    try:
        _export_fbx(temporary_output)
        _verify_round_trip(temporary_output, expected_meshes, expected_armatures)
        os.replace(temporary_output, resolved_output)
    finally:
        if temporary_output.exists():
            temporary_output.unlink()

    report["faces_removed_total"] = proposed_total
    report["output_sha256"] = _sha256(resolved_output)
    report["verified"] = True
    return report


def _backup_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.get(BACKUP_COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(BACKUP_COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    collection.hide_render = True
    collection.hide_select = True
    return collection


def _create_backup(obj: bpy.types.Object) -> bpy.types.Object:
    backup = obj.copy()
    backup.data = obj.data.copy()
    backup.name = f"{obj.name}__before_reverse_cleanup"
    backup.data.name = f"{obj.data.name}__before_reverse_cleanup"
    _backup_collection().objects.link(backup)
    backup.hide_render = True
    backup.hide_set(True)
    return backup


def _interactive_main() -> None:
    action = INTERACTIVE_ACTION.strip().upper()
    if action not in {"SELECT", "DELETE"}:
        raise ValueError('INTERACTIVE_ACTION must be either "SELECT" or "DELETE"')
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    objects = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError("Select at least one clothing mesh object before running the script")

    results: list[dict[str, object]] = []
    for obj in objects:
        report, proposed = _object_analysis(
            obj,
            position_tolerance=DEFAULT_POSITION_TOLERANCE,
            opposite_normal_dot=DEFAULT_OPPOSITE_NORMAL_DOT,
        )
        if action == "SELECT":
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                bm.faces.ensure_lookup_table()
                for face in bm.faces:
                    face.select = face.index in proposed
                bm.select_mode = {"FACE"}
                bm.select_flush_mode()
                bm.to_mesh(obj.data)
                obj.data.update()
            finally:
                bm.free()
            report["status"] = "selected"
        else:
            if proposed:
                _create_backup(obj)
                _delete_face_indices(obj, proposed)
            report["status"] = "cleaned"
        results.append(report)

    print("\n=== Star Manager reverse-face cleanup ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if action == "SELECT":
        bpy.context.view_layer.objects.active = objects[0]
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.object.mode_set(mode="EDIT")
        print("Detection finished. Inspect selected faces with Face Orientation.")
    else:
        print(f"Cleanup finished. Backups are in '{BACKUP_COLLECTION_NAME}'.")


def _command_line_main(arguments: list[str]) -> int:
    args = _parse_args(arguments)
    source = args.input.expanduser()
    output = args.output.expanduser() if args.output else None
    try:
        report = process_fbx(
            source,
            output,
            action=args.action,
            position_tolerance=args.position_tolerance,
            opposite_normal_dot=args.opposite_normal_dot,
        )
    except Exception as error:
        report = {
            "ok": False,
            "action": args.action,
            "source": str(source),
            "output": str(output) if output else None,
            "error": str(error),
        }
        exit_code = 1
    else:
        exit_code = 0

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    print(serialized)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(serialized + "\n", encoding="utf-8")
    return exit_code


def main() -> int:
    arguments = _script_args()
    if arguments:
        return _command_line_main(arguments)
    _interactive_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
