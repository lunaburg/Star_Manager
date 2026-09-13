from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import bpy

def alpha_at(image,pixels,uv):
    w,h=image.size[:]
    u=float(uv.x)%1.0; v=float(uv.y)%1.0
    x=min(w-1,max(0,round(u*(w-1))))
    y=min(h-1,max(0,round((1.0-v)*(h-1))))
    return float(pixels[(y*w+x)*image.channels+3])

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(a.input.resolve()),use_anim=False,use_custom_normals=True,ignore_leaf_bones=False,automatic_bone_orientation=False)
    image=bpy.data.images.get('base_color_texture'); pixels=list(image.pixels[:]) if image else None
    out={'image':image.name if image else None,'size':list(image.size) if image else None,'layers':{}}
    for o in bpy.data.objects:
        if o.type!='MESH':continue
        m=o.data
        for layer in m.uv_layers:
            stats={'faces':len(m.polygons),'opaque_all':0,'transparent_all':0,'mixed':0,'near_cutoff':0,'outside_uv':0,'mixed_faces':[],'near_cutoff_faces':[]}
            for f in m.polygons:
                alphas=[alpha_at(image,pixels,layer.data[li].uv) for li in f.loop_indices]
                if all(x>=0.999 for x in alphas):stats['opaque_all']+=1
                if all(x<=0.001 for x in alphas):stats['transparent_all']+=1
                if max(alphas)-min(alphas)>0.5:
                    stats['mixed']+=1
                    if len(stats['mixed_faces'])<500:stats['mixed_faces'].append({'face':f.index,'center':[float(x) for x in sum((m.vertices[i].co for i in f.vertices),__import__('mathutils').Vector())/len(f.vertices)],'alphas':alphas,'uvs':[[float(layer.data[li].uv.x),float(layer.data[li].uv.y)] for li in f.loop_indices],'area':float(f.area)})
                if any(0.001<x<0.999 for x in alphas):
                    stats['near_cutoff']+=1
                    if len(stats['near_cutoff_faces'])<100:stats['near_cutoff_faces'].append({'face':f.index,'alphas':alphas,'uvs':[[float(layer.data[li].uv.x),float(layer.data[li].uv.y)] for li in f.loop_indices]})
                if any(layer.data[li].uv.x<0 or layer.data[li].uv.x>1 or layer.data[li].uv.y<0 or layer.data[li].uv.y>1 for li in f.loop_indices):stats['outside_uv']+=1
            out['layers'][layer.name]=stats
    a.output.resolve().write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'ok':True,'layers':{k:{x:v[x] for x in ('opaque_all','transparent_all','mixed','near_cutoff','outside_uv')} for k,v in out['layers'].items()}},ensure_ascii=False))
if __name__=='__main__':main()
