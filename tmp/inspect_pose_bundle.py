from pathlib import Path
import sys
import attr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
for obj in env.objects:
    if obj.type.name not in {"AssetBundle", "AnimatorController"}:
        continue
    data = obj.read()
    print("===", obj.type.name, obj.path_id)
    for field in attr.fields(type(data)):
        value = getattr(data, field.name)
        if isinstance(value, list):
            print(field.name, "list", len(value), repr(value[:3]))
        else:
            print(field.name, repr(value)[:1200])
