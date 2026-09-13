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
print("count", len(bindings) // 3)
for i, binding in enumerate(bindings[:80]):
    print(i, int(binding.attribute), int(binding.path))
