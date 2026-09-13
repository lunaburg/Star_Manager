from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


for path in map(Path, sys.argv[1:-1]):
    env = UnityPy.load(str(path))
    wanted = sys.argv[-1]
    print("===", path)
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        data = obj.read()
        if data.m_Name != wanted:
            continue
        clip = data.m_MuscleClip.m_Clip.data
        bindings = data.m_ClipBindingConstant.genericBindings
        transforms = sum(int(item.typeID) == 4 for item in bindings) // 3
        constant = clip.m_ConstantClip.data
        dense = clip.m_DenseClip
        print("path_id", obj.path_id, "name", data.m_Name, "bindings", len(bindings), "transforms", transforms, "constant", len(constant), "dense", dense.m_CurveCount, dense.m_FrameCount, "sample", data.m_SampleRate, "start", data.m_MuscleClip.m_StartTime, "stop", data.m_MuscleClip.m_StopTime, "delta", len(data.m_MuscleClip.m_ValueArrayDelta))
        print("constant_head", [round(float(x), 5) for x in constant[:30]])
        print("constant_tail", [round(float(x), 5) for x in constant[-20:]])
