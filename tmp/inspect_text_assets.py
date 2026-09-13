from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
for path in map(Path, sys.argv[1:]):
    env = UnityPy.load(str(path))
    print("===", path)
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        d = obj.read()
        payload = d.m_Script
        print(d.m_Name, len(payload), repr(payload[:120]))
