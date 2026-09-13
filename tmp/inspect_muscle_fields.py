from pathlib import Path
import sys
import attr
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
env = UnityPy.load(str(Path(sys.argv[1])))
name = sys.argv[2]
o = next(x for x in env.objects if x.type.name == "AnimationClip" and x.read().m_Name == name)
d = o.read()
mc = d.m_MuscleClip
print(type(mc).__name__)
for f in attr.fields(type(mc)):
    v = getattr(mc, f.name)
    if isinstance(v, list):
        print(f.name, type(v).__name__, len(v), repr(v[:3]))
    else:
        print(f.name, type(v).__name__, repr(v)[:1000])
