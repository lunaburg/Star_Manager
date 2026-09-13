from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


def fields(value):
    return list(vars(value)) if hasattr(value, "__dict__") else []


path = Path(sys.argv[1])
env = UnityPy.load(str(path))
for obj in [x for x in env.objects if x.type.name == "AnimationClip"][:20]:
    data = obj.read()
    mc = data.m_MuscleClip
    clip = mc.m_Clip.data
    dense = clip.m_DenseClip
    print(
        obj.path_id,
        data.m_Name,
        "dense", type(dense).__name__,
        "begin", dense.m_BeginTime,
        "curves", dense.m_CurveCount,
        "frames", dense.m_FrameCount,
        "samples", len(dense.m_SampleArray),
        "const", type(clip.m_ConstantClip.data).__name__ if clip.m_ConstantClip else None,
        "stream", type(clip.m_StreamedClip.data).__name__ if clip.m_StreamedClip else None,
        "index", len(mc.m_IndexArray),
        "delta", len(mc.m_ValueArrayDelta),
        "binding", len(data.m_ClipBindingConstant.genericBindings),
    )
    if data.m_Name in {"S_Idle", "Joy", "Anger", "Sorrow", "Shame", "Dependence"}:
        print("  sample head", dense.m_SampleArray[:20])
        print("  index head", mc.m_IndexArray[:30])
        print("  delta head", mc.m_ValueArrayDelta[:30])
        print("  dense fields", fields(dense))
        print("  clip fields", fields(clip))
