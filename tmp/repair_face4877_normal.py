from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--face', type=int, default=4877)
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:])


def export_fbx(path: Path):
    result = bpy.ops.export_scene.fbx(
        filepath=str(path.resolve()),
        use_selection=False,
        object_types={'EMPTY', 'ARMATURE', 'MESH', 'OTHER'},
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=True,
        use_custom_props=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode='AUTO',
        embed_textures=False,
        axis_forward='-Z',
        axis_up='Y',
    )
    if 'FINISHED' not in result or not path.is_file():
        raise RuntimeError(f'FBX export failed: {sorted(result)}')


def main():
    args = parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(
        filepath=str(args.input.resolve()),
        use_anim=False,
        use_custom_normals=True,
        ignore_leaf_bones=False,
        automatic_bone_orientation=False,
    )
    if 'FINISHED' not in result:
        raise RuntimeError(result)
    targets = []
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        mesh.update(calc_edges=True)
        if args.face >= len(mesh.polygons):
            raise ValueError(f'face {args.face} is out of range for {obj.name}')
        normals = [mesh.corner_normals[loop.index].vector.copy() for loop in mesh.loops]
        polygon = mesh.polygons[args.face]
        before = [float(polygon.normal.dot(normals[loop_index])) for loop_index in polygon.loop_indices]
        face_normal = polygon.normal.normalized()
        for loop_index in polygon.loop_indices:
            normals[loop_index] = face_normal.copy()
        mesh.normals_split_custom_set(normals)
        mesh.update(calc_edges=True)
        after = [float(polygon.normal.dot(mesh.corner_normals[loop_index].vector)) for loop_index in polygon.loop_indices]
        for uv_layer in mesh.uv_layers:
            mesh.calc_tangents(uvmap=uv_layer.name)
            mesh.free_tangents()
        targets.append({'object': obj.name, 'face': args.face, 'before_dots': before, 'after_dots': after})
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    export_fbx(args.output)
    print(json.dumps({'ok': True, 'input': str(args.input.resolve()), 'output': str(args.output.resolve()), 'targets': targets}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
