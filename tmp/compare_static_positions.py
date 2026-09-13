from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


env = UnityPy.load(str(Path(sys.argv[1])))
names = sys.argv[2:]
clips = {}
for obj in env.objects:
    if obj.type.name != "AnimationClip":
        continue
    data = obj.read()
    if data.m_Name in names:
        transform_count = sum(int(binding.typeID) == 4 for binding in data.m_ClipBindingConstant.genericBindings) // 3
        values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
        clips[data.m_Name] = (transform_count, values)

first_name = names[0]
count, first = clips[first_name]
for name in names[1:]:
    other_count, other = clips[name]
    print(first_name, name, "counts", count, other_count)
    diffs = []
    for index in range(min(count, other_count)):
        a = first[index * 3 : index * 3 + 3]
        b = other[index * 3 : index * 3 + 3]
        difference = max(abs(float(a[i]) - float(b[i])) for i in range(3))
        if difference > 1e-5:
            diffs.append((index, difference, [round(float(x), 4) for x in a], [round(float(x), 4) for x in b]))
    print("position differences", len(diffs), "head", diffs[:20])
    for index in range(min(count, other_count)):
        start = count * 7 + index * 3
        other_start = other_count * 7 + index * 3
        a = first[start : start + 3]
        b = other[other_start : other_start + 3]
        if max(abs(float(a[i]) - float(b[i])) for i in range(3)) > 1e-5:
            print("scale difference", index, [round(float(x), 4) for x in a], [round(float(x), 4) for x in b])
