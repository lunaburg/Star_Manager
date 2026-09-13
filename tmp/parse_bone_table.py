from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

env = UnityPy.load(str(Path(sys.argv[1])))
obj = next(o for o in env.objects if o.type.name == "MonoBehaviour" and o.read().m_Name == "Bone_00")
b = obj.get_raw_data()
pos = 40
n = struct.unpack_from("<I", b, pos)[0]
cols = struct.unpack_from("<I", b, pos+4)[0]
pos += 8
def string(pos):
    length = struct.unpack_from("<I", b, pos)[0]
    start = pos + 4
    value = b[start:start+length].decode("utf-8")
    return value, (start + length + 3) & ~3
for _ in range(cols):
    _, pos = string(pos)
print("data", pos, "rows", n)
for row in range(20):
    start = pos
    print("row", row, "start", start)
    print(b[start:start+80].hex())
    a, b1, c = struct.unpack_from("<3I", b, pos)
    pos += 12
    print("  ints", a, b1, c)
    for j in range(2):
        s, pos = string(pos)
        print("  str", j, repr(s))
    vals = struct.unpack_from("<3I", b, pos)
    pos += 12
    print("  tail", vals)
