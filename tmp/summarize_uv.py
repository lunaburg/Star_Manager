from __future__ import annotations
import argparse,json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
def area(u):
 a,b,c=u;return .5*((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
 out={}
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  m=o.data
  for u in m.uv_layers:
   vals=[u.data[i].uv for i in range(len(u.data))]; ars=[area([u.data[li].uv for li in f.loop_indices]) for f in m.polygons]
   bins={}
   for f,x in zip(m.polygons,ars):
    c=sum((m.vertices[i].co for i in f.vertices),Vector())/3
    key=(round(float(c.x),1),round(float(c.y),1),round(float(c.z),1))
    d=bins.setdefault(key,[0,0,0]);d[0]+=1;d[1]+=int(abs(x)<=1e-12);d[2]+=abs(x)
   out[u.name]={'min':[min(v.x for v in vals),min(v.y for v in vals)],'max':[max(v.x for v in vals),max(v.y for v in vals)],'zero':sum(abs(x)<=1e-12 for x in ars),'small':sum(abs(x)<=1e-7 for x in ars),'abs_area_min':min(abs(x) for x in ars),'abs_area_max':max(abs(x) for x in ars),'regions':sorted(({'key':k,'faces':v[0],'zero':v[1],'area_sum':v[2]} for k,v in bins.items()),key=lambda x:(-x['zero'],-x['faces']))[:30]}
 a.output.resolve().write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
