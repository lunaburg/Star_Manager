from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy

source = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "anim_f_00.unity3d"
env = UnityPy.load(str(source))
obj = next(o for o in env.objects if o.type.name == "AnimationClip" and o.read().m_Name == "f_manekin")
data = obj.read()
values = data.m_MuscleClip.m_Clip.data.m_ConstantClip.data
old = values[1056:1060]
values[1056:1060] = [0.1, 0.2, 0.3, 0.9]
obj.save_typetree(data)
env.save(out_path=str(out_dir), pack="none")
print("saved", out, out.stat().st_size, "old", old)
check = UnityPy.load(str(out))
obj2 = next(o for o in check.objects if o.type.name == "AnimationClip" and o.read().m_Name == "f_manekin")
print("check", obj2.read().m_MuscleClip.m_Clip.data.m_ConstantClip.data[1056:1060])
