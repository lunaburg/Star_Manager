from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixed',type=Path,required=True);p.add_argument('--full',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 def load(path, label):
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
  out=[]
  for o in bpy.data.objects:
   if o.type=='MESH':
    lo=Vector((1e9,1e9,1e9));hi=Vector((-1e9,-1e9,-1e9))
    for v in o.data.vertices:
     q=o.matrix_world@v.co;lo=Vector((min(lo[i],q[i]) for i in range(3)));hi=Vector((max(hi[i],q[i]) for i in range(3)))
    out.append({'name':o.name,'verts':len(o.data.vertices),'faces':len(o.data.polygons),'matrix':[list(r) for r in o.matrix_world],'lo':list(lo),'hi':list(hi),'groups':sorted(g.name for g in o.vertex_groups),'mods':[(m.type,m.object.name if m.object else None) for m in o.modifiers]})
  return {'label':label,'objects':out,'armatures':[o.name for o in bpy.data.objects if o.type=='ARMATURE']}
 result={'fixed':load(a.fixed,'fixed'),'full':load(a.full,'full')};a.output.resolve().write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
