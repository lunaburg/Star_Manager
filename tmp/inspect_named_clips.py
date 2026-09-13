from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


for path in map(Path, sys.argv[1:-1]):
    wanted = sys.argv[-1]
    env = UnityPy.load(str(path))
    print("===", path)
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        data = obj.read()
        if data.m_Name != wanted:
            continue
        bindings = data.m_ClipBindingConstant.genericBindings
        transform_count = sum(int(binding.typeID) == 4 for binding in bindings) // 3
        values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
        print("path", obj.path_id, "transform_count", transform_count, "constant", len(values), "dense", data.m_MuscleClip.m_Clip.data.m_DenseClip.m_CurveCount, "frames", data.m_MuscleClip.m_Clip.data.m_DenseClip.m_FrameCount, "stop", data.m_MuscleClip.m_StopTime)
        print("head", [round(float(value), 5) for value in values[:18]])
        print("root", "start", data.m_MuscleClip.m_StartX, "stop", data.m_MuscleClip.m_StopX)
        break
