from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

env = UnityPy.load(str(Path(sys.argv[1])))
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    data = obj.read()
    if getattr(data, "m_Name", "") == "Bone_00":
        raw = obj.get_raw_data()
        print("path", obj.path_id, "byte_size", obj.byte_size, "raw_len", len(raw))
        print(raw.hex())
