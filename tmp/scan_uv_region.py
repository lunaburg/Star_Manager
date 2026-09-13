from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

def area(uvs):
 a,b,c=uvs;return .5*((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--face',type=int,default=4877);p.add_argument('--radius',type=float,default=0.8);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
 o=next(x for x in bpy.data.objects if x.type=='MESH');m=o.data;target=m.polygons[a.face];tc=sum((m.vertices[i].co for i in target.vertices),Vector())/3
 out=[]
 for f in m.polygons:
  c=sum((m.vertices[i].co for i in f.vertices),Vector())/3
  if (c-tc).length>a.radius:continue
  row={'face':f.index,'center':[float(x) for x in c],'area':float(f.area)}
  for uv in m.uv_layers:
   us=[uv.data[li].uv for li in f.loop_indices];row[uv.name]={'area':area(us),'uvs':[[float(x.x),float(x.y)] for x in us]}
  out.append(row)
 out.sort(key=lambda x:x['face']);a.output.resolve().write_text(json.dumps({'target':a.face,'target_center':[float(x) for x in tc],'faces':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'ok':True,'count':len(out)},ensure_ascii=False))
if __name__=='__main__':main()
