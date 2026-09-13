from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from io_scene_fbx import parse_fbx

def val(v):
    if isinstance(v,bytes): return v.decode('utf-8',errors='replace')
    if isinstance(v,(list,tuple)) and len(v)>20:return f'<{type(v).__name__} len={len(v)}>'
    return v
def walk(e, path=()):
    yield e,path
    for c in e.elems: yield from walk(c,path+(e.id.decode('utf-8','replace'),))
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 root,ver=parse_fbx.parse(str(a.input.resolve())); rows=[]
 for e,path in walk(root):
  eid=e.id.decode('utf-8','replace')
  if eid in ('Texture','Video','Material','LayerElementUV','LayerElementTangent','LayerElementBinormal','LayerElementNormal','C'):
   rows.append({'id':eid,'path':list(path),'props':[val(x) for x in e.props],'children':[{'id':c.id.decode('utf-8','replace'),'props':[val(x) for x in c.props]} for c in e.elems]})
 out={'version':ver,'rows':rows};a.output.resolve().write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8'); print(json.dumps({'ok':True,'version':ver,'rows':len(rows)},ensure_ascii=False))
if __name__=='__main__':main()
