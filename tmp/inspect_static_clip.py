from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
import attr

path = Path(sys.argv[1])
clip_name = sys.argv[2]
env = UnityPy.load(str(path))
obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == clip_name)
d = obj.read()
mc = d.m_MuscleClip
clip = mc.m_Clip.data
const = clip.m_ConstantClip.data
bindings = d.m_ClipBindingConstant.genericBindings
print("clip", obj.path_id, d.m_Name)
print("muscle", type(mc).__name__, "clip", type(clip).__name__)
print("dense", clip.m_DenseClip)
print("stream", clip.m_StreamedClip)
print("const type", type(const).__name__, "len", len(const), "head", const[:20])
print("index", type(mc.m_IndexArray).__name__, len(mc.m_IndexArray), mc.m_IndexArray[:20])
print("delta", type(mc.m_ValueArrayDelta).__name__, len(mc.m_ValueArrayDelta), mc.m_ValueArrayDelta[:20])
print("bindings", len(bindings))
for i, b in enumerate(bindings):
    if i < 30 or i >= len(bindings) - 10:
        print(i, {field.name: getattr(b, field.name) for field in attr.fields(type(b))})
print("types", sorted(set((int(b.typeID), int(b.attribute)) for b in bindings)))
