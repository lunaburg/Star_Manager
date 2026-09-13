from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

def clear(obj):
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.customdata_custom_splitnormals_clear(); bpy.ops.object.mode_set(mode='OBJECT'); obj.data.update(calc_edges=True)
def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
    rows=[]
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        clear(o);m=o.data
        for idx in [4877,3398,7362]:
            if idx>=len(m.polygons):continue
            f=m.polygons[idx];dots=[float(f.normal.dot(m.corner_normals[li].vector)) for li in f.loop_indices]
            rows.append({'face':idx,'normal':[float(x) for x in f.normal],'dots':dots})
    a.output.resolve().write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(rows,ensure_ascii=False))
if __name__=='__main__':main()
