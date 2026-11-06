"""
配角跪坐（游32 老尼 roni、瑠璃姫 ruri）：把 tools/npc_poses/<名字>.json 改成跪坐。
坐姿的腿和髋写进 stand；所有写了 Hip move 的姿势都往下挪同样的量（不然一点头、一张望就站起来了）；删掉走路。
先跑完 npc_setup.py 和 npc_gestures.py 再跑这个；重跑 npc_gestures.py 以后要再跑一次。
  python3 tools/npc_seat.py roni [--drop 0.43 --thigh -80 --calf 150 --foot -10]
查看器里看坐姿要加 &drift=0（不然查看器会把髋往下的那段位移归零，人浮在半空；游戏里没有这层）
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(); p.add_argument("name"); p.add_argument("--drop", type=float, default=None)   # 不给就按 <名字>_legs.json 算：髋落到约 0.1（身高 1），小腿贴地、坐在脚跟上
p.add_argument("--thigh", type=float, default=-80); p.add_argument("--calf", type=float, default=150); p.add_argument("--foot", type=float, default=-10)
# 11-06 老尼试过三组（-86/168/-30、-80/150/-10、-88/172/-45），这组两手放在膝上、下摆最顺；下摆前角会插到地下 0.1 左右，游戏里被地板挡住
a = p.parse_args()
f = ROOT / f"tools/npc_poses/{a.name}.json"
if a.drop is None:
    _l = json.loads((ROOT / f"tools/npc_poses/{a.name}_legs.json").read_text())
    a.drop = round(_l["hip_z"] / _l["height"] - 0.10, 3)   # 老尼 0.426、瑠璃姫、源慧各按自己的腿算
lib = json.loads(f.read_text(encoding="utf-8")); P = lib["poses"]
if lib.get("_seated") and "L_Thigh" in P["stand"]:   # npc_setup.py 重写过 stand 就不算坐着了
    raise SystemExit(f"{a.name} 已经是坐姿了（先重跑 npc_setup.py / npc_gestures.py 再坐）")
seat = {"L_Thigh": {"world": True, "pitch": a.thigh, "roll": -4}, "R_Thigh": {"world": True, "pitch": a.thigh, "roll": 4},
        "L_Calf": {"pitch": a.calf}, "R_Calf": {"pitch": a.calf}, "L_Foot": {"pitch": a.foot}, "R_Foot": {"pitch": a.foot}}
for k in [k for k in P if k.startswith("walk_")]: del P[k]
lib["animations"].pop("walk_k", None)
P["stand"].update(seat)
for k, pose in P.items():
    if k != "stand" and "Hip" not in pose: continue
    hip = pose.get("Hip", {}); mv = list(hip.get("move", [0, 0, 0])); mv[2] = round(mv[2] - a.drop, 4); pose["Hip"] = {**hip, "move": mv}
lib["_seated"] = {"drop": a.drop, "thigh": a.thigh, "calf": a.calf, "foot": a.foot}
f.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(a.name, "跪坐：", lib["_seated"], "动作：", ", ".join(lib["animations"]))
