from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--face',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
 o=next(x for x in bpy.data.objects if x.type=='MESH');m=o.data;m.update(calc_edges=True);f=m.polygons[a.face]; out={'target':a.face,'neighbors':[]}
 target_verts=set(f.vertices)
 for q in m.polygons:
  if q.index==f.index: continue
  shared=target_verts.intersection(q.vertices)
  if shared:
   c=sum((m.vertices[i].co for i in q.vertices),Vector())/len(q.vertices)
   out['neighbors'].append({'face':q.index,'shared':sorted(shared),'center':[float(x) for x in c],'normal':[float(x) for x in q.normal],'dot':float(f.normal.dot(q.normal)),'area':float(q.area),'corner_dots':[float(q.normal.dot(m.corner_normals[li].vector)) for li in q.loop_indices]})
 out['neighbors'].sort(key=lambda x:(-len(x['shared']),x['face']));a.output.resolve().write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
