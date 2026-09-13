"""Remove armatures, skin modifiers, and vertex groups from an FBX.

The mesh data and materials are kept in the rest pose.  This script is run by
Blender in background mode from the Workbench item tools.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export an FBX as a static mesh without skinning.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def _preserve_world_parent(obj: bpy.types.Object) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world_matrix


def _remove_skin(mesh_objects: list[bpy.types.Object]) -> dict[str, int]:
    removed_modifiers = 0
    removed_vertex_groups = 0
    for mesh in mesh_objects:
        _preserve_world_parent(mesh)
        for modifier in list(mesh.modifiers):
            if modifier.type == "ARMATURE":
                mesh.modifiers.remove(modifier)
                removed_modifiers += 1
        removed_vertex_groups += len(mesh.vertex_groups)
        mesh.vertex_groups.clear()
        mesh.data.update()

    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    return {
        "mesh_count": len(mesh_objects),
        "removed_armature_modifiers": removed_modifiers,
        "removed_vertex_groups": removed_vertex_groups,
    }


def _export_static_mesh(output_path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise RuntimeError("FBX 中没有可导出的 Mesh")
    for obj in mesh_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    result = bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"MESH"},
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=True,
        use_custom_props=True,
        bake_anim=False,
        path_mode="AUTO",
        embed_textures=False,
        axis_forward="-Z",
        axis_up="Y",
        apply_unit_scale=True,
        use_space_transform=True,
        bake_space_transform=True,
        apply_scale_options="FBX_SCALE_NONE",
    )
    if "FINISHED" not in result or not output_path.is_file():
        raise RuntimeError(f"静态 FBX 导出失败：{sorted(result)}")


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
        result = bpy.ops.import_scene.fbx(
            filepath=str(source),
            use_anim=False,
            use_custom_normals=True,
            ignore_leaf_bones=True,
            automatic_bone_orientation=False,
        )
        if "FINISHED" not in result:
            raise RuntimeError(f"FBX 导入失败：{sorted(result)}")
        mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        report = _remove_skin(mesh_objects)
        _export_static_mesh(temp_output)
        os.replace(temp_output, output)
        print(json.dumps({"ok": True, "input": str(source), "output": str(output), **report}, ensure_ascii=False))
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
