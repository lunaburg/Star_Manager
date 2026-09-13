"""Recalculate Blender mesh normals outside and export a verified FBX copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser(description="按 Blender Recalculate Outside 重建 FBX 面法线。")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


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


def snapshot():
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
        }
    armatures = {
        obj.name: sorted(bone.name for bone in obj.data.bones)
        for obj in bpy.data.objects
        if obj.type == "ARMATURE"
    }
    return meshes, armatures


def clear_custom_normals(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.mode_set(mode="OBJECT")


def recalculate_outside(obj):
    mesh = obj.data
    before = [polygon.normal.copy() for polygon in mesh.polygons]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    result = bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    if "FINISHED" not in result:
        raise RuntimeError(f"Mesh {obj.name} 法线重建失败：{sorted(result)}")
    mesh.update(calc_edges=True)
    changed = []
    for polygon, previous in zip(mesh.polygons, before):
        if previous.length and polygon.normal.length and previous.dot(polygon.normal) < -0.5:
            center = sum((mesh.vertices[index].co for index in polygon.vertices), Vector((0.0, 0.0, 0.0))) / len(polygon.vertices)
            changed.append(
                {
                    "face": polygon.index,
                    "center": [round(float(value), 8) for value in center],
                    "normal_before": [round(float(value), 8) for value in previous],
                    "normal_after": [round(float(value), 8) for value in polygon.normal],
                    "area": round(float(polygon.area), 10),
                }
            )
    clear_custom_normals(obj)
    return changed


def export_fbx(path: Path):
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


def main():
    args = parse_args()
    source = args.input.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    if source == output:
        raise ValueError("输出路径不能覆盖源文件")
    if output.exists() and not args.dry_run:
        raise FileExistsError(f"输出文件已存在：{output}")

    import_fbx(source)
    before_meshes, before_armatures = snapshot()
    objects = []
    flipped_total = 0
    for obj in sorted((item for item in bpy.data.objects if item.type == "MESH"), key=lambda item: item.name):
        changed = recalculate_outside(obj)
        flipped_total += len(changed)
        objects.append({"object": obj.name, "mesh": obj.data.name, "flipped_faces": changed})

    report = {
        "ok": True,
        "dry_run": args.dry_run,
        "source": str(source),
        "output": None if args.dry_run else str(output),
        "source_sha256": sha256(source),
        "output_sha256": None,
        "flipped_faces_total": flipped_total,
        "objects": objects,
        "verified": False,
    }
    if not args.dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="star-manager-fbx-recalculate-", dir=output.parent) as temp_dir:
            temporary_output = Path(temp_dir) / output.name
            export_fbx(temporary_output)
            import_fbx(temporary_output)
            after_meshes, after_armatures = snapshot()
            if before_meshes != after_meshes or before_armatures != after_armatures:
                raise RuntimeError("重新导入验证失败：网格或骨架结构发生变化")
            shutil.copyfile(temporary_output, output)
        report["output_sha256"] = sha256(output)
        report["verified"] = True

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    print(serialized)
    if args.report:
        report_path = args.report.expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(serialized + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
