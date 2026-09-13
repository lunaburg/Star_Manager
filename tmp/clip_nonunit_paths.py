from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
name = sys.argv[2]
obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == name)
data = obj.read()
bindings = [binding for binding in data.m_ClipBindingConstant.genericBindings if int(binding.typeID) == 4]
count = len(bindings) // 3
values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data

transforms = {}
names = {}
for obj in env.objects:
    if obj.type.name == "Transform":
        td = obj.read()
        transforms[obj.path_id] = td
        go = td.m_GameObject.deref()
        names[obj.path_id] = go.read().m_Name if go else ""


def full_path(tid):
    parts = []
    seen = set()
    while tid and tid in transforms and tid not in seen:
        seen.add(tid)
        parts.append(names.get(tid, ""))
        father = transforms[tid].m_Father
        tid = father.path_id if father else 0
    return "/".join(reversed([part for part in parts if part]))


paths = {}
for tid in transforms:
    path = full_path(tid)
    parts = path.split("/")
    for index in range(len(parts)):
        suffix = "/".join(parts[index:])
        paths[zlib.crc32(suffix.encode("utf-8")) & 0xFFFFFFFF] = suffix


print("count", count)
for index in range(count):
    start = count * 7 + index * 3
    scale = values[start : start + 3]
    if any(abs(float(value) - 1.0) > 1e-5 for value in scale):
        print(index, paths.get(int(bindings[index].path), ""), [round(float(value), 6) for value in scale])
