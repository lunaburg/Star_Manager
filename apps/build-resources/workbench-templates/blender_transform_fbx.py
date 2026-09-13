"""Apply imported mesh rotation and scale while preserving the FBX armature.

This script is launched by Blender in background mode from the Workbench item
tools.  It mirrors selecting the imported meshes in Blender, applying Rotation
& Scale, and exporting without adding an extra user-defined transform.  The
armature transform must stay untouched because it is the coordinate-system and
unit-scale parent for skinned meshes exported by the Sims 4 workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Matrix


TRANSFORM_EPSILON = 1e-6


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply imported mesh rotation and scale to an FBX.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def _import_fbx(source: Path) -> None:
    result = bpy.ops.import_scene.fbx(
        filepath=str(source),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX 导入失败：{sorted(result)}")


def _has_nonzero_translation(matrix) -> bool:
    return any(abs(float(value)) > TRANSFORM_EPSILON for value in matrix.translation)


def _apply_imported_rotation_and_scale() -> dict:
    mesh_objects = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH"
    ]
    if not mesh_objects:
        raise RuntimeError("FBX 中没有可应用变换的 Mesh")
    changed_objects = sum(
        1
        for obj in mesh_objects
        if any(abs(value) > TRANSFORM_EPSILON for value in obj.rotation_euler)
        or any(abs(value - 1.0) > TRANSFORM_EPSILON for value in obj.scale)
    )
    translation_issue_names = [
        obj.name
        for obj in mesh_objects
        if _has_nonzero_translation(obj.matrix_basis)
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.context.view_layer.update()

    repaired_mesh_names = []
    for obj in mesh_objects:
        local_matrix = obj.matrix_basis.copy()
        if not _has_nonzero_translation(local_matrix):
            continue
        obj.data.transform(Matrix.Translation(local_matrix.translation))
        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)
        repaired_mesh_names.append(obj.name)

    bpy.context.view_layer.update()
    return {
        "object_count": len(mesh_objects),
        "changed_object_count": changed_objects,
        "alignment_issue_detected": bool(translation_issue_names),
        "alignment_repair_applied": bool(repaired_mesh_names),
        "translation_issue_count": len(translation_issue_names),
        "translation_repaired_count": len(repaired_mesh_names),
        "translation_repaired_mesh_names": repaired_mesh_names,
    }


def _export_fbx(output_path: Path) -> None:
    export_objects = [
        obj for obj in bpy.context.scene.objects
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}
    ]
    if not any(obj.type == "MESH" for obj in export_objects):
        raise RuntimeError("FBX 中没有可导出的 Mesh")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]
    result = bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"MESH", "ARMATURE", "EMPTY"},
        use_mesh_modifiers=True,
        use_mesh_edges=False,
        use_tspace=False,
        use_custom_props=False,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
        axis_forward="-Z",
        axis_up="Y",
        apply_unit_scale=True,
        use_space_transform=True,
        bake_space_transform=False,
        apply_scale_options="FBX_SCALE_NONE",
        add_leaf_bones=False,
    )
    if "FINISHED" not in result or not output_path.is_file():
        raise RuntimeError(f"FBX 导出失败：{sorted(result)}")


def main() -> int:
    args = _parse_args()
    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".fbx":
        raise ValueError("输入文件必须是有效的 .fbx")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f".{output.stem}.tmp-{os.getpid()}{output.suffix}")
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _import_fbx(source)
        transform_report = _apply_imported_rotation_and_scale()
        mesh_count = sum(1 for obj in bpy.context.scene.objects if obj.type == "MESH")
        armature_count = sum(1 for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
        _export_fbx(temp_output)
        os.replace(temp_output, output)
        print(json.dumps({
            "ok": True,
            "input": str(source),
            "output": str(output),
            **transform_report,
            "mesh_count": mesh_count,
            "armature_count": armature_count,
        }, ensure_ascii=False))
        return 0
    finally:
        if temp_output.exists():
            temp_output.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        raise
