from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
obj = next(o for o in env.objects if o.type.name == "MonoBehaviour" and o.read().m_Name == "Bone_00")
raw = obj.get_raw_data()
pos = 40
row_count, column_count = struct.unpack_from("<2I", raw, pos)
pos += 8


def read_string(offset):
    length = struct.unpack_from("<I", raw, offset)[0]
    start = offset + 4
    end = (start + length + 3) & ~3
    return raw[start : start + length].decode("utf-8"), end


headers = []
for _ in range(column_count):
    value, pos = read_string(pos)
    headers.append(value)
print("rows", row_count, "columns", column_count, "headers", headers)
for row_index in range(row_count):
    values = []
    for _ in range(column_count):
        value, pos = read_string(pos)
        values.append(value)
    print(row_index, values)
