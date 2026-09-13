from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


path = Path(sys.argv[1])
names = sys.argv[2:]
env = UnityPy.load(str(path))
for name in names:
    obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == name)
    data = obj.read()
    transform_count = sum(int(binding.typeID) == 4 for binding in data.m_ClipBindingConstant.genericBindings) // 3
    clip = data.m_MuscleClip.m_Clip.data
    values = clip.m_ConstantClip.data
    delta = data.m_MuscleClip.m_ValueArrayDelta
    print(name, "transforms", transform_count, "constant", len(values), "delta", len(delta), "dense", clip.m_DenseClip.m_CurveCount)
    print("pos", "head", [round(float(x), 4) for x in values[:30]], "tail", [round(float(x), 4) for x in values[max(0, transform_count * 3 - 15) : transform_count * 3 + 15]])
    if len(values) >= transform_count * 7:
        print("rot", [round(float(x), 4) for x in values[transform_count * 3 : transform_count * 3 + 40]])
    if len(values) >= transform_count * 10:
        print("scale", [round(float(x), 4) for x in values[transform_count * 7 : transform_count * 7 + 30]])
