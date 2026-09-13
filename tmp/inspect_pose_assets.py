from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


def dump(obj, fields):
    print(f"[{obj.type.name}] path_id={obj.path_id} name={getattr(obj, 'name', '')!r}")
    data = obj.read()
    for field in fields:
        try:
            value = getattr(data, field)
            print(f"  {field}={value!r}")
        except Exception as exc:
            print(f"  {field}=<error {exc}>")


for path in map(Path, sys.argv[1:]):
    print(f"=== {path} ===")
    env = UnityPy.load(str(path))
    by_type = {}
    for obj in env.objects:
        by_type.setdefault(obj.type.name, []).append(obj)
    print("types:", {key: len(value) for key, value in sorted(by_type.items())})
    for obj in by_type.get("AnimationClip", [])[:3]:
        dump(obj, ["m_Name", "m_AnimationType", "m_Legacy", "m_Compressed", "m_SampleRate", "m_MuscleClip", "m_ClipBindingConstant", "m_FloatCurves", "m_PositionCurves", "m_RotationCurves", "m_ScaleCurves"])
    for obj in by_type.get("AnimatorController", [])[:2]:
        dump(obj, ["m_Name", "m_Controller", "m_AnimatorParameters", "m_AnimatorLayers"])
