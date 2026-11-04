"""
无面（のっぺらぼう，docs/18 第九节）的动作：和其他物怪同一套名字 idle_k / appear_k / charge_k / lunge_k / hit_k / vanish_k。
人形（Tripo 绑的骨），走配角的姿势库（tools/npc_poses/noppera.json，tools/npc_setup.py 生成的站姿上改），做法同 zashiki_gen.py。
站在地上（不像座敷童子那样飘），高个子，动作慢、头老是歪着；蓄力时两手抬到脸前像要把脸摘下来，扑的时候整个人往前滑。

  脸是另加的面具（Tripo 把脸做成了头发，见 tools/blender_add_mask.py），先贴面具再出动作：
  Blender -b --python tools/blender_add_mask.py -- --in assets/processed/noppera_lite_nomask.glb --tex assets/processed/noppera_mask.png --out assets/processed/noppera_lite.glb
  python3 tools/npc_setup.py noppera && python3 tools/noppera_gen.py
  Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/noppera_lite.glb --poses tools/npc_poses/noppera.json \
      --out assets/processed/noppera_posed.glb
"""
import json, math
from pathlib import Path

LIB = Path(__file__).resolve().parent / "npc_poses/noppera.json"


def arms(pitch, roll=0, fore=-10, yaw=0):
    """两臂一起：pitch 负 = 往前抬，roll = 往外张（左正右负），yaw = 往里收（左负右正）"""
    return {"L_Upperarm": {"pitch": pitch, "roll": roll, "yaw": -yaw}, "R_Upperarm": {"pitch": pitch, "roll": -roll, "yaw": yaw},
            "L_Forearm": {"pitch": fore}, "R_Forearm": {"pitch": fore}}


def sway(up=0.0, tilt=0.0, side=0.0, lean=0.0):
    """站着微微晃：髋上下（模型单位，身高 1.0）、左右，头歪 tilt 度，上身前倾 lean 度"""
    return {"base": "stand", "Hip": {"move": [side, 0, up]}, "Spine01": {"pitch": lean, "roll": -tilt * 0.2}, "Spine02": {"pitch": lean * 0.5},
            "Head": {"pitch": 4, "roll": tilt}, **arms(4, 8, -12)}


def build():
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    P = lib["poses"]
    for k in [k for k in P if k.startswith("nw_")]: del P[k]
    idle = []
    for i, f in enumerate(range(0, 65, 8)):   # 2.7 秒一循环：慢慢左右晃，头往一边歪着、跟着晃
        ph = 2 * math.pi * f / 64
        P[f"nw_idle_{i}"] = sway(-0.004 + 0.004 * math.sin(ph * 2), 16 + 6 * math.sin(ph), 0.008 * math.sin(ph), 3)
        idle.append([f"nw_idle_{i}", f])
    P["nw_sunk"] = {**sway(-0.75, 0, 0, 10), "Head": {"pitch": 30}, **arms(10, 30, -10)}
    P["nw_rise"] = {**sway(0.01, -10, 0, -4), **arms(-10, 20, -15)}
    # 蓄力：两手抬到脸前（掌心朝脸），头往后仰，像要把脸摘下来
    P["nw_charge"] = {**sway(-0.01, 8, 0, -8), "Head": {"pitch": -16, "roll": 8}, **arms(-62, 0, -100, 30)}
    P["nw_charge2"] = {**P["nw_charge"], "Head": {"pitch": -20, "roll": 14}, **arms(-66, 0, -105, 32)}
    # 扑：整个人往前倾着滑过去，两手往前伸
    P["nw_lunge"] = {**sway(-0.02, 0, 0, 30), "Head": {"pitch": -14}, **arms(-85, 10, -5),
                     "L_Thigh": {"pitch": -20}, "R_Thigh": {"pitch": 18}, "R_Calf": {"pitch": 15}}
    P["nw_hit"] = {**sway(0.0, -22, 0, -16), "Head": {"pitch": -28, "roll": -22}, **arms(20, 30, -30)}
    P["nw_hit2"] = {**sway(0.0, 10, 0, -4), "Head": {"pitch": -6, "roll": 12}}
    P["nw_vanish"] = {**sway(0.15, 0, 0, -10), "Head": {"pitch": -24}, **arms(-30, 70, 0)}
    P["nw_vanish2"] = {**sway(0.4, 0, 0, -14), "Head": {"pitch": -30}, **arms(-40, 85, 0)}
    A = lib["animations"]
    A["idle_k"] = {"fps": 24, "keys": idle}
    A["appear_k"] = {"fps": 24, "keys": [["nw_sunk", 0], ["nw_rise", 18], ["nw_idle_0", 26]]}
    A["charge_k"] = {"fps": 24, "keys": [["nw_idle_0", 0], ["nw_charge", 8], ["nw_charge2", 14], ["nw_charge", 19]]}
    A["lunge_k"] = {"fps": 24, "keys": [["nw_charge", 0], ["nw_lunge", 5], ["nw_lunge", 9], ["nw_idle_0", 14]]}
    A["hit_k"] = {"fps": 24, "keys": [["nw_idle_0", 0], ["nw_hit", 3], ["nw_hit2", 8], ["nw_idle_0", 12]]}
    A["vanish_k"] = {"fps": 24, "keys": [["nw_idle_0", 0], ["nw_vanish", 12], ["nw_vanish2", 30]]}
    for k in ("walk_k",): A.pop(k, None)
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写回 {LIB.name}：{', '.join(k for k in A)}")


if __name__ == "__main__":
    build()
