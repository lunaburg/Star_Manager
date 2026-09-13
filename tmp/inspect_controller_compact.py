from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend" / ".vendor"))
import UnityPy


path = Path(sys.argv[1])
env = UnityPy.load(str(path))
clips = [obj for obj in env.objects if obj.type.name == "AnimationClip"]
clip_by_id = {obj.path_id: obj for obj in clips}
for obj in [x for x in env.objects if x.type.name == "AnimatorController"]:
    d = obj.read()
    if sys.argv[2:] and d.m_Name not in set(sys.argv[2:]):
        continue
    print("controller", obj.path_id, d.m_Name)
    cc = d.m_Controller
    print("  clips", len(d.m_AnimationClips), [p.path_id for p in d.m_AnimationClips])
    print("  layers", len(cc.m_LayerArray), "state_machines", len(cc.m_StateMachineArray), "values", len(cc.m_Values.data.m_ValueArray))
    for li, layer_ptr in enumerate(cc.m_LayerArray):
        layer = layer_ptr.data
        sm = cc.m_StateMachineArray[layer.m_StateMachineIndex].data
        print("  layer", li, "sm", layer.m_StateMachineIndex, "states", len(sm.m_StateConstantArray))
        for si, state_ptr in enumerate(sm.m_StateConstantArray):
            state = state_ptr.data
            motion = None
            if state.m_BlendTreeConstantArray and state.m_BlendTreeConstantArray[0].data.m_NodeArray:
                node = state.m_BlendTreeConstantArray[0].data.m_NodeArray[0].data
                motion = node.m_ClipID
            clip = d.m_AnimationClips[motion].deref() if 0 <= motion < len(d.m_AnimationClips) else None
            print("    state", si, "hash", state.m_NameID, "motion_id", motion, "clip", clip.read().m_Name if clip else None)
