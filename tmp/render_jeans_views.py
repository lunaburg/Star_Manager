from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--highlight-face', type=int, default=-1)
    p.add_argument('--back', action='store_true')
    p.add_argument('--face', type=int, default=-1)
    p.add_argument('--flat', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()), use_anim=False, use_custom_normals=True, ignore_leaf_bones=False, automatic_bone_orientation=False)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for o in bpy.data.objects:
        if o.type == 'ARMATURE': o.hide_render = True
        if o.type == 'MESH':
            for m in o.modifiers:
                if m.type == 'ARMATURE': m.show_render = False
    lo = Vector((1e9,1e9,1e9)); hi = Vector((-1e9,-1e9,-1e9))
    for o in meshes:
        for v in o.data.vertices:
            q = o.matrix_world @ v.co
            lo = Vector((min(lo[i], q[i]) for i in range(3)))
            hi = Vector((max(hi[i], q[i]) for i in range(3)))
    target = (lo+hi)/2; size=hi-lo
    camd=bpy.data.cameras.new('Camera'); cam=bpy.data.objects.new('Camera',camd); bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera=cam
    camd.type='ORTHO'; camd.ortho_scale=max(float(size.z)*1.12, 0.01)
    if a.face >= 0 and meshes:
        mesh = meshes[0]
        poly = mesh.data.polygons[a.face]
        target = mesh.matrix_world @ (sum((mesh.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices))
        world_normal = (mesh.matrix_world.to_3x3() @ poly.normal).normalized()
        camd.ortho_scale = 0.025
        cam.location = target + world_normal * (0.2 if not a.back else -0.2)
    else:
        # Front/back views use world Z as vertical; local Z maps to world -Y.
        cam.location=target+Vector((0,(1 if a.back else -1)*max(float(size.y)*3,0.5),0))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    for o in meshes: o.select_set(False)
    if a.flat:
        white = bpy.data.materials.new('flat_opaque')
        white.use_nodes = True
        bsdf = white.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (0.55, 0.55, 0.55, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.65
        for o in meshes:
            o.data.materials.clear()
            o.data.materials.append(white)
    if a.highlight_face >= 0:
        red = bpy.data.materials.new('highlight')
        red.diffuse_color = (1.0, 0.02, 0.02, 1.0)
        red.use_nodes = True
        bsdf = red.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.4
        for o in meshes:
            o.data.materials.append(red)
            if a.highlight_face < len(o.data.polygons):
                o.data.polygons[a.highlight_face].material_index = len(o.data.materials) - 1
        if a.face >= 0 and meshes:
            o = meshes[0]
            pface = o.data.polygons[a.face]
            coords = [(o.matrix_world @ o.data.vertices[i].co) + (o.matrix_world.to_3x3() @ pface.normal).normalized() * 0.0005 for i in pface.vertices]
            md = bpy.data.meshes.new('highlight_triangle_mesh')
            md.from_pydata(coords, [], [(0, 1, 2)])
            ho = bpy.data.objects.new('highlight_triangle', md)
            bpy.context.scene.collection.objects.link(ho)
            md.materials.append(red)
    scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=700; scene.render.resolution_y=900; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.world=bpy.data.worlds.new('World'); scene.world.color=(0.03,0.03,0.03); scene.render.film_transparent=False
    ld=bpy.data.lights.new('Key','AREA'); ld.energy=500; ld.shape='DISK'; ld.size=0.5; l=bpy.data.objects.new('Key',ld); scene.collection.objects.link(l); l.location=target+Vector((0,-0.2,0.3)); l.rotation_euler=(target-l.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(a.output.resolve()); bpy.ops.render.render(write_still=True)
    print('rendered', a.output)


if __name__=='__main__': main()
