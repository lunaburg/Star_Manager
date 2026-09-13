from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
for path in map(Path, sys.argv[1:]):
    env=UnityPy.load(str(path))
    print("===", path)
    for o in env.objects:
        if o.type.name in {"AssetBundle", "AnimatorController"}:
            d=o.read()
            print(o.type.name, o.path_id, getattr(d, "m_Name", None), getattr(d, "m_Container", None))
