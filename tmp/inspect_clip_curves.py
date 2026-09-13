from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
env=UnityPy.load(str(Path(sys.argv[1])))
for o in env.objects:
    if o.type.name!='AnimationClip': continue
    d=o.read()
    print(d.m_Name, 'pos',len(d.m_PositionCurves or []),'rot',len(d.m_RotationCurves or []),'scale',len(d.m_ScaleCurves or []),'euler',len(d.m_EulerCurves or []),'float',len(d.m_FloatCurves or []))
    if d.m_EulerCurves:
        print(' euler first', d.m_EulerCurves[0])
