"""Attach the HS2 skeleton from a reference FBX to an unskinned mesh.

The target mesh keeps its geometry, materials, UVs, object transforms, vertex
groups, and modifiers.  Only an Armature object and its bone hierarchy are
copied from the reference FBX.  The mesh is parented to that Armature object,
but no Armature modifier or vertex groups are created.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach an HS2 skeleton without skinning an FBX mesh.")
    parser.add_argument("--input", required=True, type=Path, help="Unskinned mesh FBX")
    parser.add_argument("--skeleton", required=True, type=Path, help="Reference FBX containing the HS2 Armature")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def _validate_fbx(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.suffix.lower() != ".fbx":
        raise ValueError(f"{label} must be a valid .fbx file")
    return resolved


def _import_fbx(path: Path) -> None:
    result = bpy.ops.import_scene.fbx(
        filepath=str(path),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=True,
        automatic_bone_orientation=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX import failed: {sorted(result)}")


def _preserve_world_parent(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    world_matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.parent_type = "OBJECT"
    obj.matrix_world = world_matrix


def _remove_unwanted_objects(target_meshes: list[bpy.types.Object], armature: bpy.types.Object) -> None:
    keep = set(target_meshes)
    keep.add(armature)
    for obj in list(bpy.context.scene.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)


def _normalize_mesh_transforms(target_meshes: list[bpy.types.Object]) -> None:
    for index, mesh in enumerate(target_meshes):
        mesh.data.transform(mesh.matrix_basis.copy())
        mesh.location = (0.0, 0.0, 0.0)
        mesh.rotation_mode = "XYZ"
        mesh.rotation_euler = (0.0, 0.0, 0.0)
        mesh.scale = (1.0, 1.0, 1.0)
        safe_name = f"Mesh_{index}"
        mesh.name = safe_name
        mesh.data.name = safe_name


def _export(output_path: Path, target_meshes: list[bpy.types.Object], armature: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in target_meshes:
        mesh.select_set(True)
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    result = bpy.ops.export_scene.fbx(
        filepath=str(output_path),
        use_selection=True,
        object_types={"MESH", "ARMATURE"},
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
        bake_space_transform=False,
        apply_scale_options="FBX_SCALE_NONE",
    )
    if "FINISHED" not in result or not output_path.is_file():
        raise RuntimeError(f"FBX export failed: {sorted(result)}")


def main() -> int:
    args = _parse_args()
    source = _validate_fbx(args.input, "Input mesh")
    skeleton_source = _validate_fbx(args.skeleton, "Skeleton reference")
    output = args.output.expanduser().resolve()
    if source == skeleton_source:
        raise ValueError("Input mesh and skeleton reference must be different files")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output.with_name(f".{output.stem}.tmp-{os.getpid()}{output.suffix}")
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _import_fbx(source)
        target_meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        if not target_meshes:
            raise RuntimeError("Input FBX does not contain a Mesh")

        objects_before_skeleton = set(bpy.context.scene.objects)
        _import_fbx(skeleton_source)
        imported_objects = [obj for obj in bpy.context.scene.objects if obj not in objects_before_skeleton]
        armatures = [obj for obj in imported_objects if obj.type == "ARMATURE"]
        if not armatures:
            raise RuntimeError("Skeleton reference FBX does not contain an Armature")
        armature = armatures[0]

        # Parent the mesh at object level only.  No skin modifier or groups are added.
        for mesh in target_meshes:
            _preserve_world_parent(mesh, armature)
        _normalize_mesh_transforms(target_meshes)
        _remove_unwanted_objects(target_meshes, armature)
        _export(temp_output, target_meshes, armature)
        os.replace(temp_output, output)

        mesh_modifiers = sum(
            sum(1 for modifier in mesh.modifiers if modifier.type == "ARMATURE")
            for mesh in target_meshes
        )
        vertex_groups = sum(len(mesh.vertex_groups) for mesh in target_meshes)
        print(json.dumps({
            "ok": True,
            "input": str(source),
            "skeleton": str(skeleton_source),
            "output": str(output),
            "mesh_count": len(target_meshes),
            "armature_count": 1,
            "bone_count": len(armature.data.bones),
            "armature_modifiers": mesh_modifiers,
            "vertex_groups": vertex_groups,
            "skinned": False,
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
