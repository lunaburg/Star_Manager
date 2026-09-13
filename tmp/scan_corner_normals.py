from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
    rows=[]
    for o in bpy.data.objects:
        if o.type!='MESH': continue
        m=o.data; m.update(calc_edges=True)
        for f in m.polygons:
            dots=[float(f.normal.dot(m.corner_normals[li].vector)) for li in f.loop_indices]
            rows.append({'face':f.index,'center':[float(x) for x in sum((m.vertices[i].co for i in f.vertices),Vector())/len(f.vertices)],'area':float(f.area),'normal':[float(x) for x in f.normal],'dots':dots,'min_dot':min(dots),'avg_dot':float(sum(dots)/len(dots))})
    rows.sort(key=lambda x:x['min_dot']); a.output.resolve().write_text(json.dumps(rows[:200],ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'ok':True,'faces':len(rows),'lowest':rows[:10]},ensure_ascii=False))
if __name__=='__main__': main()
