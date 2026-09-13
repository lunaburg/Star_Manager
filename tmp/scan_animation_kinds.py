from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


for path in map(Path, sys.argv[1:]):
    try:
        env = UnityPy.load(str(path))
    except Exception as exc:
        print(path, "ERROR", exc)
        continue
    clips = [obj for obj in env.objects if obj.type.name == "AnimationClip"]
    print("===", path, "clips", len(clips))
    counts = {}
    examples = []
    for obj in clips:
        d = obj.read()
        key = (
            d.m_AnimationType,
            d.m_Legacy,
            d.m_MuscleClip is not None,
            len(d.m_FloatCurves or []),
            len(d.m_PositionCurves or []),
            len(d.m_RotationCurves or []),
            len(d.m_ScaleCurves or []),
        )
        counts[key] = counts.get(key, 0) + 1
        if len(examples) < 30 and (d.m_MuscleClip is None or d.m_PositionCurves or d.m_RotationCurves):
            examples.append((obj.path_id, d.m_Name, key))
    for key, count in sorted(counts.items(), key=lambda item: repr(item[0])):
        print(" ", count, key)
    for example in examples:
        print("  example", example)
