from pathlib import Path
import sys
import zlib
import attr
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

anim_path = Path(sys.argv[1])
skeleton_path = Path(sys.argv[2])
clip_name = sys.argv[3]
anim = UnityPy.load(str(anim_path))
skel = UnityPy.load(str(skeleton_path))
clip_obj = next(o for o in anim.objects if o.type.name == "AnimationClip" and o.read().m_Name == clip_name)
d = clip_obj.read()
vals = d.m_MuscleClip.m_Clip.data.m_ConstantClip.data
bindings = d.m_ClipBindingConstant.genericBindings
transforms = {}
names = {}
for o in skel.objects:
    if o.type.name != "Transform":
        continue
    td = o.read()
    transforms[o.path_id] = td
    go = td.m_GameObject.deref()
    names[o.path_id] = go.read().m_Name if go else ""
def full_path(tid):
    out = []
    seen = set()
    while tid and tid in transforms and tid not in seen:
        seen.add(tid)
        out.append(names.get(tid, ""))
        father = transforms[tid].m_Father
        tid = father.path_id if father else 0
    return "/".join(reversed([x for x in out if x]))
paths = {}
for tid in transforms:
    p = full_path(tid)
    parts = p.split("/")
    for i in range(len(parts)):
        suffix = "/".join(parts[i:])
        paths[zlib.crc32(suffix.encode()) & 0xffffffff] = suffix
print("objects", len(transforms), "bindings", len(bindings), "values", len(vals))
for i in list(range(18)) + list(range(1048, 1063)):
    b = bindings[i]
    a = int(b.attribute)
    typ = int(b.typeID)
    path = paths.get(int(b.path), "")
    print(i, "attr", a, "type", typ, "pathhash", int(b.path), "path", path)
print("values head groups:")
for start in range(0, 60, 10):
    print(start, vals[start:start+10])
print("binding attr counts", {a: sum(int(b.attribute) == a for b in bindings) for a in sorted(set(int(b.attribute) for b in bindings))})
