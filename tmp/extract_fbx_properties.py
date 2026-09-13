from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from io_scene_fbx import parse_fbx
def walk(e):
 yield e
 for c in e.elems: yield from walk(c)
def clean(v):
 if isinstance(v,bytes):return v.decode('utf-8',errors='replace')
 if hasattr(v,'tolist'):return v.tolist()
 return v
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
 root,ver=parse_fbx.parse(str(a.input.resolve())); rows=[]
 for e in walk(root):
  eid=e.id.decode('utf-8',errors='replace')
  if eid not in ('Texture','Material','LayerElementUV','P'):continue
  prop=[clean(x) for x in e.props]
  if eid=='P' or eid in ('Texture','Material','LayerElementUV'):
   rows.append({'id':eid,'props':prop})
 a.output.resolve().write_text(json.dumps({'version':ver,'rows':rows},ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8');print(json.dumps({'ok':True,'rows':len(rows)}))
if __name__=='__main__':main()
