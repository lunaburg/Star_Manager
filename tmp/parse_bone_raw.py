from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

env = UnityPy.load(str(Path(sys.argv[1])))
obj = next(o for o in env.objects if o.type.name == "MonoBehaviour" and o.read().m_Name == "Bone_00")
b = obj.get_raw_data()
print("len", len(b))
for pos in range(0, 160, 4):
    print(f"{pos:04x}", b[pos:pos+4].hex(), struct.unpack("<I", b[pos:pos+4])[0])
pos = 4 + 8 + 4 + 4 + 8
name_len = struct.unpack_from("<I", b, pos)[0]
pos += 4
print("base_pos", pos, "name_len", name_len, b[pos:pos+name_len])
pos += name_len
pos = (pos + 3) & ~3
print("custom_pos", pos, b[pos:pos+32].hex())
count = struct.unpack_from("<I", b, pos)[0]
cols = struct.unpack_from("<I", b, pos + 4)[0]
pos += 8
print("table", count, cols)
def read_str(pos):
    n = struct.unpack_from("<I", b, pos)[0]
    pos += 4
    value = b[pos:pos+n].decode("utf-8")
    pos = (pos + n + 3) & ~3
    return value, pos
for i in range(cols):
    value, pos = read_str(pos)
    print("header", i, repr(value), "next", pos)
print("first_row_pos", pos, b[pos:pos+64].hex())
for i in range(20):
    if pos + 4 > len(b):
        break
    n = struct.unpack_from("<I", b, pos)[0]
    print("field", i, "pos", pos, "u32", n, "bytes", b[pos:pos+min(32, len(b)-pos)].hex())
    pos += 4
