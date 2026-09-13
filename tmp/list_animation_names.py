from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
for path in map(Path, sys.argv[1:]):
    env = UnityPy.load(str(path))
    print("===", path)
    for index, obj in enumerate(x for x in env.objects if x.type.name == "AnimationClip"):
        print(index, obj.path_id, obj.read().m_Name)
