from __future__ import annotations
import argparse,sys
from pathlib import Path
import bpy
from mathutils import Vector

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--uv',required=True);p.add_argument('--back',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
 meshes=[o for o in bpy.data.objects if o.type=='MESH']
 for o in bpy.data.objects:
  if o.type=='ARMATURE':o.hide_render=True
  if o.type=='MESH':
   for m in o.modifiers:
    if m.type=='ARMATURE':m.show_render=False
 image=bpy.data.images.get('base_color_texture')
 if not image: raise RuntimeError('base image missing')
 mat=bpy.data.materials.new('alpha_debug');mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
 out=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');tex=nt.nodes.new('ShaderNodeTexImage');coord=nt.nodes.new('ShaderNodeTexCoord');tex.image=image;tex.interpolation='Closest';
 nt.links.new(coord.outputs['UV'],tex.inputs['Vector']);nt.links.new(tex.outputs['Alpha'],em.inputs['Color']);nt.links.new(em.outputs['Emission'],out.inputs['Surface']);em.inputs['Strength'].default_value=1.0
 for o in meshes:o.data.materials.clear();o.data.materials.append(mat)
 lo=Vector((1e9,1e9,1e9));hi=Vector((-1e9,-1e9,-1e9))
 for o in meshes:
  for v in o.data.vertices:
   q=o.matrix_world@v.co;lo=Vector((min(lo[i],q[i]) for i in range(3)));hi=Vector((max(hi[i],q[i]) for i in range(3)))
 target=(lo+hi)/2;size=hi-lo;cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);bpy.context.scene.collection.objects.link(cam);bpy.context.scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=max(float(size.z)*1.12,.01);cam.location=target+Vector((0,(1 if a.back else -1)*max(float(size.y)*3,.5),0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=700;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('World');scene.world.color=(.03,.03,.03);scene.render.film_transparent=False;scene.render.filepath=str(a.output.resolve());bpy.ops.render.render(write_still=True);print('rendered',a.output)
if __name__=='__main__':main()
