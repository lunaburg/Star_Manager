"""Repair isolated FBX face-winding/custom-normal conflicts.

The source FBX is never overwritten. Faces whose geometric normal is opposite
to the average imported corner normal are reversed, stale custom split normals
are cleared, and Blender exports a new FBX with tangent space enabled.

Run through Blender:
    blender.exe --background --factory-startup \
      --python blender_repair_fbx_normals.py -- \
      --input source.fbx --output repaired.fbx --report repaired.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import bmesh
import bpy
from mathutils import Vector


DEFAULT_ALIGNMENT_THRESHOLD = -0.05


def script_args() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="修复 FBX 局部面绕序与自定义法线方向冲突。"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--alignment-threshold",
        type=float,
        default=DEFAULT_ALIGNMENT_THRESHOLD,
        help="低于该面法线/角点法线点积的面会被翻转。",
    )
    return parser.parse_args(script_args())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_fbx(path: Path) -> None:
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


def object_snapshot() -> dict[str, object]:
    meshes: dict[str, dict[str, object]] = {}
    for obj in sorted(
        (value for value in bpy.data.objects if value.type == "MESH"),
        key=lambda value: value.name,
    ):
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
    return {"meshes": meshes, "armatures": armatures}


def normal_alignment(mesh: bpy.types.Mesh, polygon: bpy.types.MeshPolygon) -> float:
    average = Vector((0.0, 0.0, 0.0))
    for loop_index in polygon.loop_indices:
        average += mesh.corner_normals[loop_index].vector
    if average.length_squared <= 0.0:
        return 0.0
    return float(polygon.normal.dot(average.normalized()))


def scan_conflicts(mesh: bpy.types.Mesh, threshold: float) -> list[dict[str, object]]:
    mesh.update(calc_edges=True)
    conflicts: list[dict[str, object]] = []
    for polygon in mesh.polygons:
        alignment = normal_alignment(mesh, polygon)
        if alignment >= threshold:
            continue
        center = sum(
            (mesh.vertices[index].co for index in polygon.vertices),
            Vector((0.0, 0.0, 0.0)),
        ) / len(polygon.vertices)
        conflicts.append(
            {
                "face": polygon.index,
                "alignment_before": round(alignment, 7),
                "center": [round(float(value), 7) for value in center],
                "vertices": list(polygon.vertices),
            }
        )
    return conflicts


def reverse_faces(mesh: bpy.types.Mesh, face_indices: list[int]) -> None:
    if not face_indices:
        return
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        faces = [bm.faces[index] for index in face_indices]
        bmesh.ops.reverse_faces(bm, faces=faces)
        bm.normal_update()
        bm.to_mesh(mesh)
        mesh.update(calc_edges=True)
    finally:
        bm.free()


def clear_custom_normals(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.mode_set(mode="OBJECT")


def export_fbx(path: Path) -> None:
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


def compare_snapshots(before: dict[str, object], after: dict[str, object]) -> None:
    if before != after:
        raise RuntimeError(
            "重新导入验证失败：网格/骨架结构发生变化。\n"
            + json.dumps({"before": before, "after": after}, ensure_ascii=False)
        )


def repair(source: Path, output: Path, threshold: float) -> dict[str, object]:
    source = source.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if source.suffix.lower() != ".fbx" or output.suffix.lower() != ".fbx":
        raise ValueError("输入和输出都必须是 .fbx")
    if source == output:
        raise ValueError("输出路径不能覆盖源文件")
    if output.exists():
        raise FileExistsError(f"输出文件已存在：{output}")
    if threshold >= 0.0:
        raise ValueError("alignment-threshold 必须小于 0")

    import_fbx(source)
    before_snapshot = object_snapshot()
    object_reports: list[dict[str, object]] = []
    for obj in sorted(
        (value for value in bpy.data.objects if value.type == "MESH"),
        key=lambda value: value.name,
    ):
        conflicts = scan_conflicts(obj.data, threshold)
        reverse_faces(obj.data, [int(item["face"]) for item in conflicts])
        clear_custom_normals(obj)
        obj.data.update(calc_edges=True)
        after_alignments = [
            normal_alignment(obj.data, polygon)
            for polygon in obj.data.polygons
        ]
        object_reports.append(
            {
                "object": obj.name,
                "mesh": obj.data.name,
                "conflicting_faces": conflicts,
                "faces_reversed": len(conflicts),
                "minimum_alignment_after": round(min(after_alignments), 7)
                if after_alignments
                else None,
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "loops": len(obj.data.loops),
                "uv_layers": list(obj.data.uv_layers.keys()),
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="star-manager-fbx-normal-repair-", dir=output.parent
    ) as temp_dir:
        temporary_output = Path(temp_dir) / output.name
        export_fbx(temporary_output)
        shutil.copyfile(temporary_output, output)

    import_fbx(output)
    compare_snapshots(before_snapshot, object_snapshot())
    report = {
        "ok": True,
        "source": str(source),
        "output": str(output),
        "source_sha256": sha256(source),
        "output_sha256": sha256(output),
        "alignment_threshold": threshold,
        "objects": object_reports,
        "verified": True,
    }
    return report


def main() -> int:
    args = parse_args()
    try:
        report = repair(args.input, args.output, args.alignment_threshold)
    except Exception as error:
        report = {
            "ok": False,
            "source": str(args.input),
            "output": str(args.output),
            "error": str(error),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    print(serialized)
    if args.report:
        args.report.expanduser().resolve().write_text(
            serialized + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
