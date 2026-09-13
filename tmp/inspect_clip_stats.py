from pathlib import Path
import sys
import math

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


def norm(values):
    return math.sqrt(sum(float(v) * float(v) for v in values))


for path in map(Path, sys.argv[1:]):
    env = UnityPy.load(str(path))
    print("===", path)
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        data = obj.read()
        name = data.m_Name
        if name not in set(sys.argv[2:]) and len(sys.argv) > 2:
            continue
        values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
        count = len(data.m_ClipBindingConstant.genericBindings)
        transform_count = sum(int(binding.typeID) == 4 for binding in data.m_ClipBindingConstant.genericBindings) // 3
        if transform_count:
            print(name, "transform_bindings", transform_count, "all_bindings", count, "values", len(values), "dense_curves", data.m_MuscleClip.m_Clip.data.m_DenseClip.m_CurveCount)
            if len(values) >= transform_count * 10:
                pos = values[: transform_count * 3]
                rot = values[transform_count * 3 : transform_count * 7]
                scale = values[transform_count * 7 : transform_count * 10]
                nonzero_pos = sum(norm(pos[i : i + 3]) > 1e-5 for i in range(0, len(pos), 3))
                nonidentity_rot = sum(norm(rot[i : i + 4]) > 1e-5 and abs(float(rot[i + 3])) < 0.99999 for i in range(0, len(rot), 4))
                nonunit_scale = sum(any(abs(float(v) - 1.0) > 1e-5 for v in scale[i : i + 3]) for i in range(0, len(scale), 3))
                print("  nonzero_pos", nonzero_pos, "nonidentity_rot", nonidentity_rot, "nonunit_scale", nonunit_scale)
