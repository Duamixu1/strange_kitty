"""
座敷童子（万屋的物怪，docs/18）的动作：和化猫、唐伞同一套名字 idle_k / appear_k / charge_k / lunge_k / hit_k / vanish_k。
它是人形（Tripo 绑的骨），所以走配角的姿势库（tools/npc_poses/zashiki.json，tools/npc_setup.py 生成的站姿上改），
不走 blender_rig_creature.py。整只是飘着的：脚离地、脚尖往下垂，头老是歪着，像人偶。

  python3 tools/npc_setup.py zashiki --female && python3 tools/zashiki_gen.py
  Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/zashiki_lite.glb --poses tools/npc_poses/zashiki.json \
      --out assets/processed/zashiki_posed.glb
"""
import json, math
from pathlib import Path

LIB = Path(__file__).resolve().parent / "npc_poses/zashiki.json"


def arms(pitch, roll=0, fore=-10):
    """两臂一起：pitch 负 = 往前抬，roll = 往外张（左正右负，配角的绑定姿势已经由 bind_fix 放下来了）。前臂伸直、不扭（盖掉站姿里拢手的扭转）"""
    return {"L_Upperarm": {"pitch": pitch, "roll": roll}, "R_Upperarm": {"pitch": pitch, "roll": -roll},
            "L_Forearm": {"pitch": fore}, "R_Forearm": {"pitch": fore}}


def float_pose(up=0.08, tilt=0.0, sway=0.0):
    """飘着：髋抬起来（模型单位，身高 1.0），脚尖往下垂，头歪"""
    return {"base": "stand", "Hip": {"move": [sway, 0, up]}, "L_Foot": {"pitch": 25}, "R_Foot": {"pitch": 22},
            "L_Thigh": {"pitch": 4}, "R_Thigh": {"pitch": -2}, "L_Calf": {"pitch": 8}, "R_Calf": {"pitch": 12},
            "Head": {"pitch": 6, "roll": tilt}, **arms(-8, 6, -20)}


def build():
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    P = lib["poses"]
    for k in [k for k in P if k.startswith("zw_")]: del P[k]
    idle = []
    for i, f in enumerate(range(0, 49, 6)):   # 2 秒一循环：上下飘、头慢慢往两边歪
        ph = 2 * math.pi * f / 48
        P[f"zw_idle_{i}"] = float_pose(0.08 + 0.015 * math.sin(ph), 14 * math.sin(ph * 0.5 + 0.6), 0.01 * math.sin(ph * 0.5))
        idle.append([f"zw_idle_{i}", f])
    P["zw_sunk"] = {**float_pose(-0.7, 0), "Head": {"pitch": 30}}
    P["zw_rise"] = float_pose(0.12, -8)
    P["zw_charge"] = {**float_pose(0.06, 22), "Spine01": {"pitch": -10}, "Spine02": {"pitch": -6}, "Head": {"pitch": -14, "roll": 22}, **arms(-70, 10, 0)}
    P["zw_charge2"] = {**P["zw_charge"], "Head": {"pitch": -12, "roll": 28}, **arms(-74, 14, 0)}
    P["zw_lunge"] = {**float_pose(0.14, 0), "Spine01": {"pitch": 24}, "Spine02": {"pitch": 10}, "Head": {"pitch": 6, "roll": 6}, **arms(-95, 4, 0),
                     "L_Thigh": {"pitch": 30}, "R_Thigh": {"pitch": 36}, "L_Calf": {"pitch": 30}, "R_Calf": {"pitch": 24}}
    P["zw_hit"] = {**float_pose(0.1, -18), "Spine01": {"pitch": -18}, "Spine02": {"pitch": -8}, "Head": {"pitch": -25, "roll": -18}, **arms(30, 20, -30)}
    P["zw_hit2"] = {**float_pose(0.09, 10), "Spine01": {"pitch": -6}, "Head": {"pitch": -6, "roll": 12}}
    P["zw_vanish"] = {**float_pose(0.45, 0), "Spine01": {"pitch": -12}, "Head": {"pitch": -22}, **arms(-20, 70, 0)}
    P["zw_vanish2"] = {**float_pose(0.7, 0), "Spine01": {"pitch": -16}, "Head": {"pitch": -28}, **arms(-30, 85, 0)}
    A = lib["animations"]
    A["idle_k"] = {"fps": 24, "keys": idle}
    A["appear_k"] = {"fps": 24, "keys": [["zw_sunk", 0], ["zw_rise", 16], ["zw_idle_0", 24]]}
    A["charge_k"] = {"fps": 24, "keys": [["zw_idle_0", 0], ["zw_charge", 7], ["zw_charge2", 13], ["zw_charge", 19]]}
    A["lunge_k"] = {"fps": 24, "keys": [["zw_charge", 0], ["zw_lunge", 4], ["zw_lunge", 8], ["zw_idle_0", 14]]}
    A["hit_k"] = {"fps": 24, "keys": [["zw_idle_0", 0], ["zw_hit", 3], ["zw_hit2", 8], ["zw_idle_0", 12]]}
    A["vanish_k"] = {"fps": 24, "keys": [["zw_idle_0", 0], ["zw_vanish", 12], ["zw_vanish2", 30]]}
    for k in ("walk_k",): A.pop(k, None)   # 物怪不走路（npc_setup 没生成，保险起见）
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写回 {LIB.name}：{', '.join(k for k in A)}")


if __name__ == "__main__":
    build()
