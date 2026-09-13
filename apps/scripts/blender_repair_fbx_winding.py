"""Detect and repair isolated triangle winding errors in an FBX.

This is different from comparing imported custom normals: a reversed face can
carry a matching reversed custom normal and therefore look valid to a normal
alignment scan.  A consistently oriented triangle mesh must traverse every
shared manifold edge in the opposite direction on its two adjacent faces.

The repair keeps the smaller parity group in each connected component as the
outlier group, reverses only that group, clears stale split normals, and
exports a new FBX.  The source is never overwritten.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import bmesh
import bpy
from mathutils import Vector


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="诊断并修复 FBX 三角面绕序错误。")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--action", choices=("analyze", "repair"), default="analyze")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _import_fbx(path: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(path),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX 导入失败：{sorted(result)}")


def _snapshot() -> tuple[dict[str, dict[str, object]], dict[str, list[str]]]:
    meshes = {}
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        meshes[obj.name] = {
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
    armatures = {
        obj.name: sorted(bone.name for bone in obj.data.bones)
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
    }
    return meshes, armatures


def _edge_direction(vertices: tuple[int, int]) -> tuple[tuple[int, int], int]:
    first, second = vertices
    edge = tuple(sorted((first, second)))
    return edge, 1 if (first, second) == edge else -1


def _winding_report(mesh: bpy.types.Mesh) -> dict[str, object]:
    polygons = list(mesh.polygons)
    edge_faces: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    skipped_faces: list[int] = []
    for polygon in polygons:
        vertices = tuple(polygon.vertices)
        if len(vertices) != 3:
            skipped_faces.append(polygon.index)
            continue
        for offset in range(3):
            edge, direction = _edge_direction((vertices[offset], vertices[(offset + 1) % 3]))
            edge_faces[edge].append((polygon.index, direction))

    adjacency: dict[int, list[tuple[int, int, tuple[int, int]]]] = defaultdict(list)
    boundary_edges = 0
    nonmanifold_edges = 0
    for edge, faces in edge_faces.items():
        if len(faces) == 1:
            boundary_edges += 1
            continue
        if len(faces) != 2:
            nonmanifold_edges += 1
            continue
        (first_face, first_direction), (second_face, second_direction) = faces
        # A consistent orientation requires opposite directed edge signs.
        constraint = 0 if first_direction != second_direction else 1
        adjacency[first_face].append((second_face, constraint, edge))
        adjacency[second_face].append((first_face, constraint, edge))

    visited: dict[int, int] = {}
    components: list[dict[str, object]] = []
    for polygon in polygons:
        root = polygon.index
        if root in visited or len(polygon.vertices) != 3:
            continue
        visited[root] = 0
        queue = deque([root])
        component_faces: list[int] = []
        contradictions: list[dict[str, object]] = []
        while queue:
            current = queue.popleft()
            component_faces.append(current)
            for other, constraint, edge in adjacency.get(current, []):
                expected = visited[current] ^ constraint
                if other not in visited:
                    visited[other] = expected
                    queue.append(other)
                elif visited[other] != expected:
                    contradictions.append(
                        {"face_a": current, "face_b": other, "edge": list(edge)}
                    )

        parity_zero = [face for face in component_faces if visited[face] == 0]
        parity_one = [face for face in component_faces if visited[face] == 1]
        component_vertices = sorted(
            {
                vertex
                for face_index in component_faces
                for vertex in polygons[face_index].vertices
            }
        )
        coordinates = [mesh.vertices[index].co for index in component_vertices]
        bounds_min = [min(float(coordinate[axis]) for coordinate in coordinates) for axis in range(3)]
        bounds_max = [max(float(coordinate[axis]) for coordinate in coordinates) for axis in range(3)]
        face_details = []
        if len(component_faces) <= 6:
            for face_index in component_faces:
                polygon = polygons[face_index]
                center = sum(
                    (mesh.vertices[index].co for index in polygon.vertices),
                    Vector((0.0, 0.0, 0.0)),
                ) / len(polygon.vertices)
                face_details.append(
                    {
                        "face": face_index,
                        "vertices": list(polygon.vertices),
                        "center": [round(float(value), 8) for value in center],
                        "normal": [round(float(value), 8) for value in polygon.normal],
                        "area": round(float(polygon.area), 10),
                    }
                )
        if len(parity_one) < len(parity_zero):
            proposed = parity_one
        elif len(parity_zero) < len(parity_one):
            proposed = parity_zero
        else:
            proposed = []
        components.append(
            {
                "root_face": root,
                "face_count": len(component_faces),
                "parity_zero_count": len(parity_zero),
                "parity_one_count": len(parity_one),
                "proposed_reversed_faces": proposed,
                "contradiction_count": len(contradictions),
                "contradictions": contradictions[:20],
                "bounds_min": [round(value, 8) for value in bounds_min],
                "bounds_max": [round(value, 8) for value in bounds_max],
                "face_details": face_details,
            }
        )

    proposed_faces = sorted(
        face
        for component in components
        if not component["contradictions"]
        for face in component["proposed_reversed_faces"]
    )
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "loops": len(mesh.loops),
        "non_triangle_faces": skipped_faces,
        "manifold_boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "component_count": len(components),
        "components": components,
        "proposed_reversed_faces": proposed_faces,
    }


def _clear_custom_normals(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.mode_set(mode="OBJECT")


def _reverse_faces(mesh: bpy.types.Mesh, indices: list[int]) -> None:
    if not indices:
        return
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[index] for index in indices])
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
    finally:
        bm.free()


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
    if "FINISHED" not in result or not path.is_file():
        raise RuntimeError(f"FBX 导出失败：{sorted(result)}")


def main() -> int:
    args = _args()
    source = args.input.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve() if args.output else None
    if args.action == "repair":
        if output is None or output == source:
            raise ValueError("repair 必须指定不同于源文件的 --output")
        if output.exists():
            raise FileExistsError(f"输出文件已存在：{output}")

    _import_fbx(source)
    before_meshes, before_armatures = _snapshot()
    object_reports = []
    total_proposed = 0
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        report = _winding_report(obj.data)
        object_reports.append({"object": obj.name, "mesh": obj.data.name, **report})
        total_proposed += len(report["proposed_reversed_faces"])
        if args.action == "repair":
            _reverse_faces(obj.data, report["proposed_reversed_faces"])
            _clear_custom_normals(obj)
            obj.data.update(calc_edges=True)

    result = {
        "ok": True,
        "action": args.action,
        "source": str(source),
        "output": str(output) if output else None,
        "source_sha256": _sha256(source),
        "output_sha256": None,
        "proposed_reversed_faces_total": total_proposed,
        "objects": object_reports,
        "verified": False,
    }
    if args.action == "repair":
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="star-manager-fbx-winding-", dir=output.parent) as temp_dir:
            temporary_output = Path(temp_dir) / output.name
            _export_fbx(temporary_output)
            _import_fbx(temporary_output)
            after_meshes, after_armatures = _snapshot()
            if before_meshes != after_meshes or before_armatures != after_armatures:
                raise RuntimeError("重新导入验证失败：网格或骨架结构发生变化")
            shutil.copyfile(temporary_output, output)
        result["output_sha256"] = _sha256(output)
        result["verified"] = True

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    print(serialized)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(serialized + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
