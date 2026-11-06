"""
配角站着时的一次性小动作（游15，10-31 用户说配角原地站着太呆），写进 tools/npc_poses/<角色>.json。

  python3 tools/npc_gestures.py            # 三个人都写；可以重复跑，只覆盖下面这些姿势和动作
  然后 Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/<角色>_lite.glb --poses tools/npc_poses/<角色>.json --out assets/processed/<角色>_posed.glb

每个动作首尾都是 stand（和 idle_k 的首尾一样），游戏里播完接回待机不会跳。
姿势都写成"相对站姿的增量"，这里叠到各人站姿上：站姿的前臂有 yaw 和 local 扭（让大袖垂下来），直接覆盖会把手臂掰坏。
角度约定同姿势库：朝上的骨头 pitch 正 = 往前低，朝下的骨头 pitch 负 = 往前抬，yaw 正 = 往角色左边转，roll 正 = 远端往左倒。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 增量姿势：{骨头: {pitch/yaw/roll: 增量, move: 绝对}}。base 写另一个增量姿势的名字，先叠它
DELTA = {
    # ---- 阿浅、阿龟：女中 ----
    "collar_in": {"Spine02": {"pitch": 2}, "Head": {"pitch": 6}, "L_Upperarm": {"pitch": -8}, "R_Upperarm": {"pitch": -8},
                  "L_Forearm": {"pitch": -15}, "R_Forearm": {"pitch": -15}},
    "collar": {"Spine01": {"pitch": 1}, "Spine02": {"pitch": 4}, "Head": {"pitch": 14, "roll": 3},
               "L_Upperarm": {"pitch": -14, "roll": 4}, "R_Upperarm": {"pitch": -14, "roll": -4},
               "L_Forearm": {"pitch": -32}, "R_Forearm": {"pitch": -32}, "L_Clavicle": {"roll": -1.5}, "R_Clavicle": {"roll": 1.5}},
    "collar_tug": {"base": "collar", "L_Forearm": {"pitch": -27}, "R_Forearm": {"pitch": -27}, "Head": {"pitch": 15, "roll": 2}},
    "look_L": {"Spine02": {"yaw": 8}, "NeckTwist02": {"yaw": 10}, "Head": {"yaw": 22, "pitch": -2}, "Hip": {"move": [0.004, 0, 0]}},
    "look_R": {"Spine02": {"yaw": -7}, "NeckTwist02": {"yaw": -9}, "Head": {"yaw": -20, "pitch": -1}, "Hip": {"move": [-0.004, 0, 0]}},
    "nod_dn": {"Spine02": {"pitch": 3}, "Head": {"pitch": 15, "yaw": 6}, "NeckTwist01": {"pitch": 3}},
    "nod_up": {"Head": {"pitch": 2, "yaw": 6}},
    # ---- 歌山：老女，动作慢、幅度小 ----
    "turn_half": {"Spine01": {"yaw": 5}, "Spine02": {"yaw": 6}, "NeckTwist02": {"yaw": 4}, "Head": {"yaw": 6}, "Hip": {"move": [0.003, 0, 0]}},
    "turn": {"Spine01": {"yaw": 10}, "Spine02": {"yaw": 12}, "NeckTwist02": {"yaw": 8}, "Head": {"yaw": 12, "pitch": -2}, "Hip": {"move": [0.006, 0, 0]}},
    # 抬手抚鬓角：右臂往前上抬、往身体这边收（右臂 roll 正 = 往里），小臂折起来让手到右耳旁的鬓发；头往右手那边歪一点迎上去。
    # 试过把手再抬高去够头顶的发簪，小臂一折手就落到肩膀上，这副骨架没有 IK，停在鬓角最自然
    "pin_in": {"Head": {"roll": -3}, "R_Upperarm": {"pitch": -30, "roll": 10}, "R_Forearm": {"pitch": -45}, "R_Clavicle": {"roll": 3}},
    "pin": {"Head": {"roll": -8, "yaw": -8, "pitch": -2}, "Spine02": {"roll": 2}, "R_Upperarm": {"pitch": -60, "roll": 22},
            "R_Forearm": {"pitch": -100}, "R_Clavicle": {"roll": 7}},
    "pin_touch": {"base": "pin", "R_Forearm": {"pitch": -105}, "Head": {"roll": -9, "yaw": -8, "pitch": -3}},
    "tall": {"Spine01": {"pitch": -3}, "Spine02": {"pitch": -3}, "Head": {"pitch": -4}, "L_Clavicle": {"roll": -2}, "R_Clavicle": {"roll": 2},
             "Hip": {"move": [0, 0, 0.004]}},
    "settle": {"Spine02": {"pitch": 1}, "Head": {"pitch": 2, "roll": -2}, "Hip": {"move": [-0.004, 0, -0.002]}, "L_Upperarm": {"pitch": -2}, "R_Upperarm": {"pitch": -2}},
}
ANIMS = {
    # 名字: [(姿势, 帧)]，24 帧/秒
    "fix_collar_k": [("stand", 0), ("collar_in", 10), ("collar", 22), ("collar_tug", 32), ("collar", 42), ("collar_tug", 52), ("collar", 60), ("collar_in", 72), ("stand", 86)],
    "look_around_k": [("stand", 0), ("look_L", 16), ("look_L", 40), ("look_R", 64), ("look_R", 86), ("stand", 104)],
    "nod_k": [("stand", 0), ("nod_dn", 9), ("nod_up", 16), ("nod_dn", 23), ("stand", 36)],
    "turn_slow_k": [("stand", 0), ("turn_half", 24), ("turn", 48), ("turn", 84), ("turn_half", 108), ("stand", 132)],
    "touch_hair_k": [("stand", 0), ("pin_in", 14), ("pin", 28), ("pin_touch", 40), ("pin", 52), ("pin_touch", 62), ("pin", 72), ("pin_in", 86), ("stand", 102)],
    "posture_k": [("stand", 0), ("tall", 24), ("tall", 48), ("settle", 76), ("settle", 96), ("stand", 120)],
}
WHO = {"asa": ["fix_collar_k", "look_around_k", "nod_k"], "kame": ["fix_collar_k", "look_around_k", "nod_k"],
       "utayama": ["turn_slow_k", "touch_hair_k", "posture_k"],
       # 游14 新人物（万屋：志乃、久代、徳次；坂井家：加世、伊行、小田島）
       "shino": ["fix_collar_k", "look_around_k", "nod_k"], "hisayo": ["nod_k", "look_around_k", "posture_k"],
       "tokuji": ["look_around_k", "nod_k", "posture_k"], "kayo": ["fix_collar_k", "look_around_k", "nod_k"],
       "yoshiyuki": ["turn_slow_k", "nod_k", "posture_k"], "odajima": ["look_around_k", "posture_k", "nod_k"],
       # 游32 笛小路家（室町、半井、大澤站着；老尼、瑠璃姫跪坐，跑完这里再跑 tools/npc_seat.py）
       "muromachi": ["look_around_k", "nod_k", "posture_k"], "nakarai": ["look_around_k", "nod_k", "posture_k"],
       "osawa": ["look_around_k", "nod_k", "posture_k"], "roni": ["nod_k", "look_around_k", "posture_k"],
       "ruri": ["look_around_k", "nod_k", "fix_collar_k"],
       # 游32 そらりす丸（源慧可能改跪坐，见 tools/npc_seat.py）
       "genkei": ["nod_k", "look_around_k", "posture_k"], "sogen": ["nod_k", "look_around_k", "posture_k"],
       "yanagi": ["look_around_k", "nod_k", "posture_k"], "sasaki": ["look_around_k", "posture_k", "nod_k"],
       "oyo": ["nod_k", "posture_k", "look_around_k"],
       # 游32 地铁（docs/17 第二十二节）
       "moriya": ["look_around_k", "nod_k", "posture_k"], "masao": ["look_around_k", "nod_k", "posture_k"],
       "chiyo": ["fix_collar_k", "look_around_k", "nod_k"], "haru": ["fix_collar_k", "look_around_k", "nod_k"],
       "kinoshita": ["look_around_k", "nod_k", "posture_k"], "fukuda": ["look_around_k", "nod_k", "posture_k"],
       # 地铁乘客人偶（光身 / 西装礼帽 / 洋装钟形帽 / 和服）
       "mnq_bare": ["look_around_k", "posture_k", "nod_k"], "mnq_suit": ["look_around_k", "posture_k", "nod_k"],
       "mnq_dress": ["look_around_k", "fix_collar_k", "nod_k"], "mnq_kimono": ["look_around_k", "fix_collar_k", "nod_k"],
       # 游32 牢房（のっぺらぼう）
       "kitsune_men": ["look_around_k", "nod_k", "posture_k"], "ocho": ["fix_collar_k", "look_around_k", "nod_k"],
       "ocho_mother": ["nod_k", "look_around_k", "posture_k"], "shuto": ["nod_k", "look_around_k", "posture_k"],
       "kazumasa": ["look_around_k", "posture_k", "nod_k"]}


def resolve(lib, name):
    d = dict(lib[name]); b = d.pop("base", None); out = resolve(lib, b) if b else {}; out.update(d); return out


def flatten(name):
    d = dict(DELTA[name]); b = d.pop("base", None); out = flatten(b) if b else {}
    for bone, v in d.items(): out[bone] = {**out.get(bone, {}), **v}
    return out


import sys
ONLY = set(sys.argv[1:])   # 给了名字就只改这几个人的姿势库（几个人可以同时出模型，11-06 起）
for who, anims in WHO.items():
    if ONLY and who not in ONLY: continue
    p = ROOT / f"tools/npc_poses/{who}.json"
    if not p.exists(): continue   # 模型和姿势库还没做出来的先跳过
    lib = json.loads(p.read_text(encoding="utf-8"))
    stand = resolve(lib["poses"], "stand")
    used = {pn for a in anims for pn, _ in ANIMS[a] if pn != "stand"}
    for pn in used:
        pose = {"base": "stand"}
        for bone, dv in flatten(pn).items():
            b = dict(stand.get(bone, {}))
            for k in ("pitch", "roll", "yaw"):
                if k in dv: b[k] = round(b.get(k, 0) + dv[k], 2)
            if "move" in dv: b["move"] = dv["move"]
            pose[bone] = b
        lib["poses"][f"g_{pn}"] = pose
    for a in anims:
        lib["animations"][a] = {"fps": 24, "keys": [[pn if pn == "stand" else f"g_{pn}", f] for pn, f in ANIMS[a]]}
    p.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(who, "→", ", ".join(f"{a}（{ANIMS[a][-1][1] / 24:.1f} 秒）" for a in anims))
