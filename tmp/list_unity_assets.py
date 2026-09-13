from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
for path in map(Path, sys.argv[1:]):
    env = UnityPy.load(str(path))
    print("===", path)
    for obj in env.objects:
        name = ""
        try:
            name = obj.read().m_Name
        except Exception:
            pass
        print(obj.type.name, obj.path_id, name)
