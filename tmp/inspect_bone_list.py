from pathlib import Path
import sys
import attr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

env = UnityPy.load(str(Path(sys.argv[1])))
obj = next(o for o in env.objects if o.type.name == "MonoBehaviour" and o.read().m_Name == "Bone_00")
d = obj.read()
print(type(d).__name__)
for field in attr.fields(type(d)):
    value = getattr(d, field.name)
    if isinstance(value, (list, tuple)):
        print(field.name, type(value).__name__, len(value), repr(value[:3]))
    else:
        print(field.name, type(value).__name__, repr(value)[:500])
