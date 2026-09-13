from pathlib import Path
import io
import struct
import sys


def read_string(r):
    length = 0
    shift = 0
    while True:
        byte = r.read(1)[0]
        length |= (byte & 0x7F) << shift
        if byte < 0x80:
            return r.read(length).decode("utf-8")
        shift += 7


def read_vec3(r):
    return struct.unpack("<3f", r.read(12))


def read_bool_array(r):
    return [bool(r.read(1)[0]) for _ in range(struct.unpack("<I", r.read(4))[0])] if False else None


path = Path(sys.argv[1])
r = io.BytesIO(path.read_bytes())
print("marker", read_string(r).encode("unicode_escape").decode())
version, sex = struct.unpack("<2i", r.read(8))
name = read_string(r)
print("version", version, "sex", sex, "name", name, "payload_offset", r.tell())
group, category, no = struct.unpack("<3i", r.read(12))
normalized = struct.unpack("<f", r.read(4))[0] if version >= 101 else 0.0
enable_ik = bool(r.read(1)[0])
active_ik = [bool(r.read(1)[0]) for _ in range(5)]
ik_count = struct.unpack("<i", r.read(4))[0]
ik = {}
for _ in range(ik_count):
    index = struct.unpack("<i", r.read(4))[0]
    ik[index] = (read_vec3(r), read_vec3(r), read_vec3(r))
enable_fk = bool(r.read(1)[0])
active_fk = [bool(r.read(1)[0]) for _ in range(7)]
fk_count = struct.unpack("<i", r.read(4))[0]
fk = {}
for _ in range(fk_count):
    index = struct.unpack("<i", r.read(4))[0]
    fk[index] = (read_vec3(r), read_vec3(r), read_vec3(r))
expression = [bool(r.read(1)[0]) for _ in range(4)]
print("animation", group, category, no, "normalized", normalized)
print("IK", enable_ik, active_ik, "records", len(ik))
print("FK", enable_fk, active_fk, "records", len(fk))
for index, value in fk.items():
    print(" FK", index, "pos", tuple(round(x, 6) for x in value[0]), "rot", tuple(round(x, 6) for x in value[1]), "scale", value[2])
for index, value in ik.items():
    print(" IK", index, value)
print("expression", expression, "remaining", len(r.read()))
