from pathlib import Path
import sys
import zlib
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

anim_path = Path(sys.argv[1])
skeleton_path = Path(sys.argv[2])
anim = UnityPy.load(str(anim_path))
skel = UnityPy.load(str(skeleton_path))
clip = next(o for o in anim.objects if o.type.name == "AnimationClip" and o.read().m_Name == sys.argv[3])
bindings = clip.read().m_ClipBindingConstant.genericBindings
hashes = {int(b.path) for b in bindings if int(b.typeID) == 4}
transforms = {}
names = {}
for o in skel.objects:
    if o.type.name == "Transform":
        d = o.read()
        transforms[o.path_id] = d
        go = d.m_GameObject.deref()
        names[o.path_id] = go.read().m_Name if go else ""

def full_path(tid):
    parts = []
    seen = set()
    while tid and tid in transforms and tid not in seen:
        seen.add(tid)
        parts.append(names.get(tid, ""))
        father = transforms[tid].m_Father
        tid = father.path_id if father else 0
    return "/".join(reversed([p for p in parts if p]))

found = {}
for tid in transforms:
    path = full_path(tid)
    pieces = path.split("/")
    for i in range(len(pieces)):
        suffix = "/".join(pieces[i:])
        digest = zlib.crc32(suffix.encode("utf-8")) & 0xffffffff
        if digest in hashes:
            found[digest] = suffix

print("bindings", len(bindings), "transform bindings", sum(int(b.typeID) == 4 for b in bindings))
print("matched hashes", len(found))
for value in sorted(found.values()):
    print(value)
for target in ["cf_J_Hips", "cf_J_Head", "cf_J_Spine01", "cf_J_Spine02", "cf_J_Shoulder_R", "cf_J_ArmUp00_R", "cf_J_ArmLow01_R", "cf_J_Hand_R", "cf_J_Hand_Index01_R", "cf_J_LegUp00_R", "cf_J_Foot01_R", "cf_J_Toes01_R"]:
    matches = [p for p in found.values() if p.endswith(target)]
    print("target", target, matches)
