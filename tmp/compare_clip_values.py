from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy
env=UnityPy.load(str(Path(sys.argv[1])))
for name in sys.argv[2:]:
 o=next(x for x in env.objects if x.type.name=='AnimationClip' and x.read().m_Name==name)
 d=o.read(); mc=d.m_MuscleClip; c=mc.m_Clip.data
 const=c.m_ConstantClip.data; delta=mc.m_ValueArrayDelta
 print(name,'const',len(const),'delta',len(delta),'delta_equals',all(abs(delta[i].m_Start-const[i])<1e-6 and abs(delta[i].m_Stop-const[i])<1e-6 for i in range(min(len(const),len(delta)))))
 print('startX',mc.m_StartX,'stopX',mc.m_StopX,'starttime',mc.m_StartTime,'stoptime',mc.m_StopTime)
