from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
env = UnityPy.load(str(Path(sys.argv[1])))
trans = {}
names = {}
for o in env.objects:
    if o.type.name == "Transform":
        d = o.read()
        trans[o.path_id] = d
        go = d.m_GameObject.deref()
        names[o.path_id] = go.read().m_Name if go else ""
def full_path(tid):
    parts = []
    seen = set()
    while tid and tid in trans and tid not in seen:
        seen.add(tid)
        parts.append(names.get(tid, ""))
        father = trans[tid].m_Father
        tid = father.path_id if father else 0
    return "/".join(reversed([x for x in parts if x]))
for tid in trans:
    p = full_path(tid)
    if any(x in p for x in ["cf_J_Hips", "cf_J_Root", "cf_J_Spine01"]):
        print(tid, repr(p))
