from pathlib import Path
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
clip_name = sys.argv[2]
obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == clip_name)
data = obj.read()
values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
bindings = [binding for binding in data.m_ClipBindingConstant.genericBindings if int(binding.typeID) == 4]
count = len(bindings) // 3
print("count", count)
for index in range(count):
    base = count * 3 + index * 4
    q = values[base : base + 4]
    if max(abs(float(q[0])), abs(float(q[1])), abs(float(q[2]))) > 1e-4:
        print(index, [round(float(value), 5) for value in q], "path_hash", int(bindings[index].path))
