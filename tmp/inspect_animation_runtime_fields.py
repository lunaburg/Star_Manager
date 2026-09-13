from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
import attr


path = Path(sys.argv[1])
name = sys.argv[2]
env = UnityPy.load(str(path))
obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == name)
data = obj.read()
for label, value in [("clip", data), ("muscle", data.m_MuscleClip), ("inner", data.m_MuscleClip.m_Clip.data), ("constant", data.m_MuscleClip.m_Clip.data.m_ConstantClip)]:
    print("===", label, type(value).__name__)
    for field in attr.fields(type(value)):
        item = getattr(value, field.name)
        if field.name in {"m_DenseClip", "m_StreamedClip", "m_ConstantClip", "m_Clip", "m_StartX", "m_StopX", "m_DeltaPose", "m_RootX", "m_LeftFootStartX", "m_RightFootStartX"}:
            print(field.name, repr(item)[:1200])
        elif isinstance(item, (list, tuple)):
            print(field.name, "list", len(item))
        else:
            print(field.name, repr(item)[:300])
