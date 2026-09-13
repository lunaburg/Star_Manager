from pathlib import Path
import sys
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

anim = UnityPy.load(str(Path(sys.argv[1])))
skel = UnityPy.load(str(Path(sys.argv[2])))
name = sys.argv[3]
obj = next(o for o in anim.objects if o.type.name == "AnimationClip" and o.read().m_Name == name)
d = obj.read()
vals = d.m_MuscleClip.m_Clip.data.m_ConstantClip.data
bindings = d.m_ClipBindingConstant.genericBindings
transforms = {}
names = {}
for o in skel.objects:
    if o.type.name == "Transform":
        td = o.read()
        transforms[o.path_id] = td
        go = td.m_GameObject.deref()
        names[o.path_id] = go.read().m_Name if go else ""
def full(tid):
    out = []
    seen = set()
    while tid and tid in transforms and tid not in seen:
        seen.add(tid)
        out.append(names[tid])
        f = transforms[tid].m_Father
        tid = f.path_id if f else 0
    return "/".join(reversed(out))
by_path = {}
for tid, td in transforms.items():
    complete = full(tid)
    parts = complete.split("/")
    for i in range(len(parts)):
        by_path["/".join(parts[i:])] = td
paths = {}
for p in by_path:
    parts = p.split("/")
    for i in range(len(parts)):
        suffix = "/".join(parts[i:])
        paths[zlib.crc32(suffix.encode()) & 0xffffffff] = suffix
def vec(value):
    return (value.x, value.y, value.z)
def quat(value):
    return (value.x, value.y, value.z, value.w)
for i in range(10):
    b = bindings[i]
    p = paths.get(int(b.path))
    t = by_path.get(p)
    print(i, p, "constpos", vals[i*3:i*3+3], "localpos", vec(t.m_LocalPosition) if t else None, "localrot", quat(t.m_LocalRotation) if t else None, "localscale", vec(t.m_LocalScale) if t else None)
print("rotation values")
for i in range(3):
    print(i, paths.get(int(bindings[352+i].path)), vals[1056+i*4:1056+i*4+4])
print("scale values")
for i in range(3):
    print(i, paths.get(int(bindings[704+i].path)), vals[2464+i*3:2464+i*3+3])
