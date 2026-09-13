from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    return p.parse_args(sys.argv[sys.argv.index('--') + 1:])


def v3(v):
    return [round(float(x), 7) for x in v]


def sample_alpha(image, pixels, uv, flip_v=False):
    if not image or not pixels or not image.size[0] or not image.size[1] or image.channels < 4:
        return None
    u = float(uv[0]) % 1.0
    v = (1.0 - float(uv[1]) if flip_v else float(uv[1])) % 1.0
    x = min(image.size[0] - 1, max(0, round(u * (image.size[0] - 1))))
    y = min(image.size[1] - 1, max(0, round(v * (image.size[1] - 1))))
    return float(pixels[(y * image.size[0] + x) * image.channels + 3])


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
    out = {'objects': [], 'materials': [], 'images': []}
    for image in bpy.data.images:
        info = {'name': image.name, 'filepath': image.filepath, 'size': list(image.size)}
        try:
            info['channels'] = image.channels
            info['has_alpha'] = image.channels >= 4
            if image.size[0] and image.size[1]:
                pixels = list(image.pixels[:])
                if image.channels >= 4:
                    alpha = pixels[3::image.channels]
                    info['alpha_min'] = min(alpha)
                    info['alpha_max'] = max(alpha)
                    info['alpha_lt_1_count'] = sum(a < 0.999 for a in alpha)
                    info['alpha_eq_0_count'] = sum(a < 0.001 for a in alpha)
        except Exception as e:
            info['pixel_error'] = str(e)
        out['images'].append(info)
    for mat in bpy.data.materials:
        mi = {
            'name': mat.name,
            'blend_method': getattr(mat, 'surface_render_method', None),
            'surface_render_method': getattr(mat, 'surface_render_method', None),
            'use_nodes': mat.use_nodes,
            'nodes': [],
            'links': [],
        }
        if mat.use_nodes:
            for n in mat.node_tree.nodes:
                ni = {'name': n.name, 'type': n.bl_idname, 'label': n.label, 'inputs': {}}
                for inp in n.inputs:
                    if inp.is_linked:
                        ni['inputs'][inp.name] = {'linked': True}
                    else:
                        if not hasattr(inp, 'default_value'):
                            continue
                        val = inp.default_value
                        try:
                            val = list(val) if hasattr(val, '__len__') and not isinstance(val, str) else val
                        except Exception:
                            pass
                        if isinstance(val, (int, float, str, bool, list)):
                            ni['inputs'][inp.name] = val
                if n.type == 'TEX_IMAGE' and n.image:
                    ni['image'] = n.image.name
                mi['nodes'].append(ni)
            for link in mat.node_tree.links:
                mi['links'].append([link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name])
        out['materials'].append(mi)
    alpha_image = bpy.data.images.get('base_color_texture')
    alpha_pixels = list(alpha_image.pixels[:]) if alpha_image else None
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o:o.name):
        mesh = obj.data
        mesh.update(calc_edges=True)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) != 2)
        boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
        bm.free()
        loose = sum(1 for v in mesh.vertices if not v.link_edges) if hasattr(mesh.vertices[0], 'link_edges') else None
        oi = {
            'name': obj.name, 'vertices': len(mesh.vertices), 'edges': len(mesh.edges), 'faces': len(mesh.polygons), 'loops': len(mesh.loops),
            'uv_layers': list(mesh.uv_layers.keys()), 'nonmanifold_edges': nonmanifold, 'boundary_edges': boundary,
            'vertex_groups': sorted(g.name for g in obj.vertex_groups),
            'modifiers': [(m.name, m.type, getattr(m, 'show_viewport', None), getattr(m, 'show_render', None)) for m in obj.modifiers],
            'materials': [m.name if m else None for m in mesh.materials],
            'face_material_counts': dict(Counter(p.material_index for p in mesh.polygons)),
            'sample_faces': {},
            'alpha_scan': {},
        }
        alpha_stats = {}
        for uv_name in mesh.uv_layers.keys():
            uv_stats = {}
            for flip_v in (False, True):
                values = []
                transparent_faces = []
                for p in mesh.polygons:
                    center_uv = sum((mesh.uv_layers[uv_name].data[li].uv for li in p.loop_indices), Vector((0.0, 0.0))) / len(p.loop_indices)
                    a = sample_alpha(alpha_image, alpha_pixels, center_uv, flip_v)
                    values.append(a if a is not None else 1.0)
                    if a is not None and a < 0.5:
                        transparent_faces.append(p.index)
                uv_stats['flip_v_' + str(flip_v).lower()] = {
                    'min': min(values), 'max': max(values), 'lt_0_5': len(transparent_faces),
                    'sample_transparent_faces': transparent_faces[:100],
                }
            alpha_stats[uv_name] = uv_stats
        oi['alpha_scan'] = alpha_stats
        for idx in [4876, 4877, 4878]:
            if idx >= len(mesh.polygons):
                continue
            p = mesh.polygons[idx]
            sample = {'center': v3(sum((mesh.vertices[i].co for i in p.vertices), Vector()) / len(p.vertices)), 'normal': v3(p.normal), 'area': p.area, 'vertices': list(p.vertices), 'loops': []}
            for li in p.loop_indices:
                row = {'loop': li, 'vertex': mesh.loops[li].vertex_index, 'normal': v3(mesh.corner_normals[li].vector)}
                for uv in mesh.uv_layers:
                    row[uv.name] = [float(uv.data[li].uv.x), float(uv.data[li].uv.y)]
                sample['loops'].append(row)
            for uv_name in mesh.uv_layers.keys():
                uvs = [mesh.uv_layers[uv_name].data[li].uv for li in p.loop_indices]
                center_uv = sum(uvs, Vector((0.0, 0.0))) / len(uvs)
                sample.setdefault('alpha', {})[uv_name] = {
                    'center': [sample_alpha(alpha_image, alpha_pixels, center_uv, flip) for flip in (False, True)],
                    'corners': [[sample_alpha(alpha_image, alpha_pixels, uv, flip) for flip in (False, True)] for uv in uvs],
                }
            oi['sample_faces'][str(idx)] = sample
        out['objects'].append(oi)
    args.output.resolve().write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'objects': len(out['objects']), 'materials': len(out['materials'])}))


if __name__ == '__main__':
    main()
