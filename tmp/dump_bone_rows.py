from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
obj = next(o for o in env.objects if o.type.name == "MonoBehaviour" and o.read().m_Name == "Bone_00")
raw = obj.get_raw_data()
pos = 40
row_count = struct.unpack_from("<I", raw, pos)[0]
pos += 4


def read_string(offset):
    length = struct.unpack_from("<I", raw, offset)[0]
    start = offset + 4
    end = (start + length + 3) & ~3
    return raw[start : start + length].decode("utf-8", errors="replace"), end


def read_list(offset):
    count = struct.unpack_from("<I", raw, offset)[0]
    offset += 4
    values = []
    for _ in range(count):
        value, offset = read_string(offset)
        values.append(value)
    return values, offset


for row_index in range(row_count):
    values, pos = read_list(pos)
    if row_index == 0:
        print("header", row_index, len(values), [value.encode("unicode_escape").decode("ascii") for value in values])
    elif row_index <= int(sys.argv[2]) if len(sys.argv) > 2 else row_index <= 60:
        print("row", row_index - 1, values[:2], [value.encode("unicode_escape").decode("ascii") for value in values[2:]])
