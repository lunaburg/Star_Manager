from pathlib import Path
import math
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


anim_path = Path(sys.argv[1])
skel_path = Path(sys.argv[2])
clip_name = sys.argv[3]
anim = UnityPy.load(str(anim_path))
skel = UnityPy.load(str(skel_path))
clip_obj = next(o for o in anim.objects if o.type.name == "AnimationClip" and o.read().m_Name == clip_name)
clip = clip_obj.read()
values = clip.m_MuscleClip.m_Clip.data.m_ConstantClip.data
bindings = clip.m_ClipBindingConstant.genericBindings
transforms = {}
names = {}
for obj in skel.objects:
    if obj.type.name != "Transform":
        continue
    data = obj.read()
    transforms[obj.path_id] = data
    go = data.m_GameObject.deref()
    names[obj.path_id] = go.read().m_Name if go else ""


def full_path(transform_id):
    parts = []
    seen = set()
    while transform_id and transform_id in transforms and transform_id not in seen:
        seen.add(transform_id)
        parts.append(names.get(transform_id, ""))
        father = transforms[transform_id].m_Father
        transform_id = father.path_id if father else 0
    return "/".join(reversed([part for part in parts if part]))


paths = {}
transform_by_suffix = {}
for transform_id in transforms:
    path = full_path(transform_id)
    parts = path.split("/")
    for index in range(len(parts)):
        suffix = "/".join(parts[index:])
        paths[zlib.crc32(suffix.encode("utf-8")) & 0xFFFFFFFF] = suffix
        transform_by_suffix[suffix] = transforms[transform_id]


def vec(value):
    return (float(value.x), float(value.y), float(value.z))


def quat(value):
    return (float(value.x), float(value.y), float(value.z), float(value.w))


transform_bindings = [binding for binding in bindings if int(binding.typeID) == 4]
count = len(transform_bindings) // 3
print("transform bindings", count, "values", len(values))
for index in range(count):
    binding = transform_bindings[index]
    path = paths.get(int(binding.path), "")
    transform = transform_by_suffix.get(path)
    pos = tuple(values[index * 3 : index * 3 + 3])
    rot_start = count * 3 + index * 4
    rotation = tuple(values[rot_start : rot_start + 4])
    scale_start = count * 7 + index * 3
    scale = tuple(values[scale_start : scale_start + 3])
    if transform:
        rest_pos = vec(transform.m_LocalPosition)
        rest_rot = quat(transform.m_LocalRotation)
        rest_scale = vec(transform.m_LocalScale)
        pos_delta = max(abs(pos[i] - rest_pos[i]) for i in range(3))
        rot_delta = max(abs(rotation[i] - rest_rot[i]) for i in range(4))
        scale_delta = max(abs(scale[i] - rest_scale[i]) for i in range(3))
    else:
        pos_delta = rot_delta = scale_delta = float("nan")
    if index < 60:
        print(index, path.rsplit("/", 1)[-1], "pos", tuple(round(x, 5) for x in pos), "rest_d", round(pos_delta, 5), "rot", tuple(round(x, 5) for x in rotation), "rest_d", round(rot_delta, 5), "scale_d", round(scale_delta, 5))
