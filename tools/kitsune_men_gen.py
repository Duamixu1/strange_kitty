"""
狐面男（のっぺらぼう篇的狐面の男）的物怪动作：和其他物怪同一套名字 idle_k / appear_k / charge_k / lunge_k / hit_k / vanish_k，做法同 noppera_gen.py。
人形（Tripo 绑的骨），站姿库 tools/npc_poses/kitsune_men.json 由 tools/build_npc.sh 生成（走路、站姿动作留着，牢房里也能当配角走）。
性子：比无面从容，像在台上——腰板直，右手常抬到面具边上；蓄力时捏住面具边像要摘，扑的时候袖子一甩往前滑。

  面具是另加的网格 kitsune_mask（按贴图轮廓裁的，见 tools/blender_add_mask.py --cut），游戏里按名字找到就能摘，下面是空脸：
  Blender -b --python tools/blender_add_mask.py -- --in assets/processed/kitsune_men_lite_nomask.glb --tex assets/processed/kitsune_mask.png \
      --out assets/processed/kitsune_men_lite.glb --face 0.010,0.905,0.054,0.074 --name kitsune_mask --cut --grid 72,96
  python3 tools/kitsune_men_gen.py
  Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/kitsune_men_lite.glb --poses tools/npc_poses/kitsune_men.json \
      --out assets/processed/kitsune_men_posed.glb && tools/build_npc_lite.sh kitsune_men
"""
import json, math
from pathlib import Path

LIB = Path(__file__).resolve().parent / "npc_poses/kitsune_men.json"


def arm(side, pitch, roll=0, fore=-10, yaw=0):
    """一只手：pitch 负 = 往前抬，roll = 往外张，yaw = 往里收（左右自动换号）"""
    s = 1 if side == "L" else -1
    return {f"{side}_Upperarm": {"pitch": pitch, "roll": s * roll, "yaw": -s * yaw}, f"{side}_Forearm": {"pitch": fore}}


def mask_hand(lift=0.0):
    """右手抬到面具右边，lift 0→1 越来越像要摘下来"""
    return arm("R", -64 - 6 * lift, 6, -116 - 4 * lift, 32 + 2 * lift)


def pose(up=0.0, tilt=0.0, side=0.0, lean=0.0, turn=0.0):
    """髋上下、左右（模型单位，身高 1.0），头歪 tilt 度，上身前倾 lean 度，上身扭 turn 度；左手垂着微张"""
    return {"base": "stand", "Hip": {"move": [side, 0, up]}, "Spine01": {"pitch": lean, "roll": -tilt * 0.15, "yaw": turn * 0.5},
            "Spine02": {"pitch": lean * 0.5, "yaw": turn * 0.5}, "Head": {"pitch": 2, "roll": tilt},
            **arm("L", 6, 10, -14), **arm("R", 6, 10, -14)}


def build():
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    P = lib["poses"]
    for k in [k for k in P if k.startswith("kw_")]: del P[k]
    idle = []
    for i, f in enumerate(range(0, 73, 8)):   # 3 秒一循环：腰板直，轻轻晃，右手搭在面具边，头慢慢歪
        ph = 2 * math.pi * f / 72
        P[f"kw_idle_{i}"] = {**pose(-0.003 + 0.003 * math.sin(ph * 2), 8 + 5 * math.sin(ph), 0.005 * math.sin(ph), -2, 4 * math.sin(ph)),
                             **mask_hand(0.1 + 0.1 * math.sin(ph))}
        idle.append([f"kw_idle_{i}", f])
    # 出场：深深一躬（右手按胸），慢慢直起来，手抬到面具上
    P["kw_bow"] = {**pose(-0.03, 0, 0, 48), "Head": {"pitch": 20}, **arm("R", -40, 0, -100, 40), **arm("L", 20, 20, -20)}
    P["kw_rise"] = {**pose(-0.005, -6, 0, 10), "Head": {"pitch": 8, "roll": -6}, **arm("R", -50, 4, -105, 30)}
    # 蓄力：捏住面具边，头往后仰、往一边歪，左手往外张开
    P["kw_charge"] = {**pose(-0.01, 14, 0, -8, -10), "Head": {"pitch": -14, "roll": 14}, **mask_hand(0.8), **arm("L", -10, 45, -25)}
    P["kw_charge2"] = {**P["kw_charge"], "Head": {"pitch": -20, "roll": 20}, **mask_hand(1.0), **arm("L", -16, 55, -20)}
    # 扑：身子前倾着滑过去，右手从面具上甩开往前抓，左手往后
    P["kw_lunge"] = {**pose(-0.02, -4, 0, 26, 18), "Head": {"pitch": -16}, **arm("R", -88, 14, -8, 4), **arm("L", 30, 30, -10),
                     "L_Thigh": {"pitch": -22}, "R_Thigh": {"pitch": 18}, "R_Calf": {"pitch": 16}}
    # 挨打：往后一仰，两手护着面具
    P["kw_hit"] = {**pose(0.0, -20, 0, -18, -8), "Head": {"pitch": -26, "roll": -20}, **mask_hand(0.6), **arm("L", -55, 0, -110, 30)}
    P["kw_hit2"] = {**pose(0.0, 6, 0, -4), "Head": {"pitch": -4, "roll": 8}, **mask_hand(0.3)}
    # 消失：转身，两手张开往上升
    P["kw_vanish"] = {**pose(0.12, 0, 0, -8, 30), "Head": {"pitch": -18}, **arm("L", -30, 70, 0), **arm("R", -30, 70, 0)}
    P["kw_vanish2"] = {**pose(0.38, 0, 0, -12, 60), "Head": {"pitch": -26}, **arm("L", -40, 88, 0), **arm("R", -40, 88, 0)}
    A = lib["animations"]
    A["idle_k"] = {"fps": 24, "keys": idle}
    A["appear_k"] = {"fps": 24, "keys": [["kw_bow", 0], ["kw_bow", 6], ["kw_rise", 22], ["kw_idle_0", 32]]}
    A["charge_k"] = {"fps": 24, "keys": [["kw_idle_0", 0], ["kw_charge", 9], ["kw_charge2", 16], ["kw_charge", 22]]}
    A["lunge_k"] = {"fps": 24, "keys": [["kw_charge", 0], ["kw_lunge", 5], ["kw_lunge", 9], ["kw_idle_0", 15]]}
    A["hit_k"] = {"fps": 24, "keys": [["kw_idle_0", 0], ["kw_hit", 3], ["kw_hit2", 9], ["kw_idle_0", 13]]}
    A["vanish_k"] = {"fps": 24, "keys": [["kw_idle_0", 0], ["kw_vanish", 12], ["kw_vanish2", 30]]}
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写回 {LIB.name}：{', '.join(k for k in A)}")


if __name__ == "__main__":
    build()
