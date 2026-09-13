from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
def load(path):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False);o=next(x for x in bpy.data.objects if x.type=='MESH');return o
def main():
 p=argparse.ArgumentParser();p.add_argument('--a',type=Path,required=True);p.add_argument('--b',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 A=load(a.a);wa=[A.matrix_world@v.co for v in A.data.vertices]; Aname=A.name
 B=load(a.b);wb=[B.matrix_world@v.co for v in B.data.vertices]
 cell=1e-6;bins={}
 for i,q in enumerate(wb):bins.setdefault(tuple(round(float(x)/cell) for x in q),[]).append(i)
 matches=[];miss=[]
 for i,q in enumerate(wa):
  key=tuple(round(float(x)/cell) for x in q); cand=bins.get(key,[]); best=min(cand,key=lambda j:(wb[j]-q).length) if cand else None
  if best is None or (wb[best]-q).length>1e-5:miss.append(i)
  else:matches.append((i,best,float((wb[best]-q).length)))
 out={'a_name':Aname,'a_verts':len(wa),'b_verts':len(wb),'matched':len(matches),'missing':len(miss),'max_error':max((x[2] for x in matches),default=0),'missing_indices':miss[:200]}
 a.output.resolve().write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
