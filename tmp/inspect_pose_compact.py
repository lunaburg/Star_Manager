from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
import attr


def compact(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return {"len": len(value), "head": [compact(x) for x in value[:2]]}
    if attr.has(type(value)):
        result = {}
        for field in attr.fields(type(value)):
            key = field.name
            item = getattr(value, key)
            if key in {"m_SampleArray", "m_ValueArrayDelta", "m_ValueArrayReferencePose", "m_IndexArray"}:
                result[key] = {"len": len(item) if item is not None else None}
            elif key in {"m_DenseClip", "m_StreamedClip", "m_Binding", "m_Clip"}:
                result[key] = {"type": type(item).__name__ if item is not None else None}
            else:
                result[key] = compact(item)
        return result
    return repr(value)


for path in map(Path, sys.argv[1:]):
    print(f"=== {path} ===")
    env = UnityPy.load(str(path))
    clips = [obj for obj in env.objects if obj.type.name == "AnimationClip"]
    print("clips", len(clips))
    for obj in clips[:8]:
        data = obj.read()
        print("clip", obj.path_id, data.m_Name, "sample", data.m_SampleRate, "legacy", data.m_Legacy)
        mc = data.m_MuscleClip
        print("  muscle", compact(mc))
        binding = data.m_ClipBindingConstant
        print("  binding", compact(binding))
        print("  curves", len(data.m_FloatCurves), len(data.m_PositionCurves), len(data.m_RotationCurves), len(data.m_ScaleCurves))
