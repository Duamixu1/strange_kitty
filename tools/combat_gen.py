"""
物怪出没（docs/18）用的药郎动作：察觉、戒备、投札三种、结印、滑步闪避三种、袖挡、收势、退魔短版。
和退魔三拍同一套做法（tools/exorcise_gen.py）：关键姿势 → 按骨头错开时间逐帧烘焙（身体先动、手后到、带余摆），
腿用走路的 IK 解，脚踩在地上。写回 tools/poses/kusuriuri_v2.json，然后跑 blender_pose_anim.py 出模型。

  python3 tools/exorcise_gen.py wind_drop=0.008 && python3 tools/combat_gen.py

先跑 exorcise_gen：退魔短版要用它算好的 slash、slash_over、awaken_over 这些姿势。
每个动作的时长、出手时刻（札离手、剑砍到）、要代码配合的位移，见 CLIPS 和 docs/17 第十五节。
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import exorcise_gen as eg

LIB = eg.LIB
PINCH = {"R_Fingers_0": {"local": [35, 0, 0]}, "R_Fingers_1": {"local": [45, 0, 0]}}      # 两指夹着札
OPEN = {"R_Fingers_0": {"local": [5, 0, 0]}, "R_Fingers_1": {"local": [5, 0, 0]}}         # 札甩出去，手指张开
FLAT_L = {"L_Fingers_0": {"local": [8, 0, 0]}, "L_Fingers_1": {"local": [8, 0, 0]}}


def legs(drop=0.0, fwd=0.0, L=(0, 0, 0), R=(0, 0, 0), pelvis=0.0, hem=True):
    """eg.legs 的简写：两脚相对绑定位置挪 (前后, 往里收, 抬高)，髋往前 fwd、往下 drop（米）；顺手给下摆打跟腿的帧"""
    p, th, kn = eg.legs({"L": L, "R": R}, fwd, drop, pelvis_yaw=pelvis)
    if hem: p.update(eg.hem(th, kn))
    return p


def poses():
    P = {}
    # 戒备：膝盖微屈、上身稍前倾，右手在胸前夹着札，左手稍张开。遭遇时的待机（循环）
    P["ready"] = {"base": "stand", **legs(drop=0.02),
        "Spine01": {"pitch": 4}, "Spine02": {"pitch": 2}, "Head": {"pitch": -2},
        "R_Upperarm": {"pitch": -45, "yaw": 28}, "R_Forearm": {"pitch": -165},
        "L_Upperarm": {"pitch": 10, "roll": 12}, "L_Forearm": {"pitch": -20}, **PINCH, **FLAT_L}
    # 察觉：右手按帽檐、头往右偏、抬眼
    P["sense_a"] = {"base": "stand", **legs(drop=0.008),
        "Spine01": {"yaw": -8, "pitch": -2}, "Spine02": {"yaw": -4}, "Head": {"yaw": -22, "pitch": -6, "roll": 4},
        "R_Upperarm": {"pitch": -105, "roll": -28}, "R_Forearm": {"pitch": -190},
        "L_Upperarm": {"pitch": 4}, "L_Forearm": {"pitch": -10}, **OPEN}
    P["sense_b"] = {**P["sense_a"], "Head": {"yaw": -12, "pitch": -4, "roll": 2}}
    # 投札·单手甩（只用上半身轨道，走路时叠着播）：右手先收到左肩，再往右前方甩直
    P["flick_wind"] = {**P["ready"], "Spine01": {"yaw": 12, "pitch": 4}, "Spine02": {"yaw": 6}, "Head": {"yaw": -14},
        "R_Upperarm": {"pitch": -60, "yaw": 42}, "R_Forearm": {"pitch": -185}}
    P["flick_rel"] = {**P["ready"], "Spine01": {"yaw": -14, "pitch": 5}, "Spine02": {"yaw": -6}, "Head": {"yaw": 8},
        "R_Upperarm": {"pitch": -88, "yaw": 5}, "R_Forearm": {"pitch": -80}, **OPEN}
    P["flick_follow"] = {**P["flick_rel"], "Spine01": {"yaw": -18, "pitch": 6}, "R_Upperarm": {"pitch": -80, "yaw": -10}, "R_Forearm": {"pitch": -86}}
    # 投札·回身甩：先往左拧，再整个人往右甩开，右臂横着扫出去、大袖甩开
    P["spin_wind"] = {**P["ready"], **legs(drop=0.03, pelvis=10), "Spine01": {"yaw": 34, "pitch": 3}, "Spine02": {"yaw": 14}, "Head": {"yaw": -26},
        "R_Upperarm": {"pitch": -40, "yaw": 50}, "R_Forearm": {"pitch": -175}, "L_Upperarm": {"pitch": 25, "roll": 10}}
    P["spin_rel"] = {**P["ready"], **legs(drop=0.035, pelvis=-10), "Spine01": {"yaw": -34, "pitch": 4}, "Spine02": {"yaw": -14}, "Head": {"yaw": 22},
        "R_Upperarm": {"pitch": -10, "roll": -78}, "R_Forearm": {"pitch": -80}, "L_Upperarm": {"pitch": 10, "roll": 38}, "L_Forearm": {"pitch": -10}, **OPEN}
    P["spin_follow"] = {**P["spin_rel"], "Spine01": {"yaw": -40, "pitch": 4}, "Spine02": {"yaw": -17}, "R_Upperarm": {"pitch": 0, "roll": -72}}
    # 投札·撒一扇：两手交叉收在胸前，再往前往两边推开，一排札撒出去
    P["fan_gather"] = {**P["ready"], **legs(drop=0.035), "Spine01": {"pitch": 9}, "Spine02": {"pitch": 4}, "Head": {"pitch": 3},
        "R_Upperarm": {"pitch": -42, "yaw": 30}, "R_Forearm": {"pitch": -172}, "L_Upperarm": {"pitch": -42, "yaw": -30}, "L_Forearm": {"pitch": -97}}
    P["fan_push"] = {**P["ready"], **legs(drop=0.03, fwd=0.04), "Spine01": {"pitch": -4}, "Spine02": {"pitch": -2}, "Head": {"pitch": -4},
        "R_Upperarm": {"pitch": -80, "roll": -25}, "R_Forearm": {"pitch": -80}, "L_Upperarm": {"pitch": -80, "roll": 25}, "L_Forearm": {"pitch": -5}, **OPEN}
    P["fan_hold"] = {**P["fan_push"], "R_Upperarm": {"pitch": -74, "roll": -30}, "L_Upperarm": {"pitch": -74, "roll": 30}}
    # 结印：右手立在唇前，低头看手；左手垂在身侧
    P["seal"] = {**P["ready"], "Spine01": {"pitch": 3}, "Head": {"pitch": 7},
        "R_Upperarm": {"pitch": -55, "roll": 10}, "R_Forearm": {"pitch": -190}, "L_Upperarm": {"pitch": 15, "roll": 6}, "L_Forearm": {"pitch": -25}, **OPEN}
    P["seal_b"] = {**P["seal"], "Head": {"pitch": 9}, "Spine01": {"pitch": 4}}
    # 滑步后撤：先一沉，往后滑出去时上身前倾、两手往前带（大袖往前飘），落地再沉一下（位移由代码给）
    P["dodge_crouch"] = {**P["ready"], **legs(drop=0.06), "Spine01": {"pitch": 8}}
    P["dodge_back"] = {**P["ready"], **legs(drop=0.07, L=(0.1, 0, 0.04)), "Spine01": {"pitch": 22}, "Spine02": {"pitch": 8}, "Head": {"pitch": -16},
        "R_Upperarm": {"pitch": -70, "roll": -15}, "R_Forearm": {"pitch": -120}, "L_Upperarm": {"pitch": -60, "roll": 25}, "L_Forearm": {"pitch": -40}}
    P["dodge_land"] = {**P["ready"], **legs(drop=0.08), "Spine01": {"pitch": 12}, "Head": {"pitch": -8}}
    # 滑步侧闪：往哪边滑，上身往那边倾、头留在后面看着物怪
    for side, sg in (("L", 1), ("R", -1)):
        lead, trail = ("L", "R") if side == "L" else ("R", "L")
        foot = {lead: (0, -0.03, 0.04), trail: (0, 0, 0)}
        out = {"R_Upperarm": {"pitch": -10, "roll": -55}, "R_Forearm": {"pitch": -95}} if sg < 0 else {"L_Upperarm": {"pitch": -10, "roll": 55}, "L_Forearm": {"pitch": -20}}
        across = {"L_Upperarm": {"pitch": -40, "yaw": -30}, "L_Forearm": {"pitch": -80}} if sg < 0 else {"R_Upperarm": {"pitch": -40, "yaw": 30}, "R_Forearm": {"pitch": -165}}
        P[f"side_{side}"] = {**P["ready"], **legs(drop=0.06, **foot), "Spine01": {"roll": 18 * sg, "pitch": 8}, "Spine02": {"roll": 8 * sg}, "Head": {"roll": -14 * sg, "yaw": -18 * sg},
            **out, **across}
    # 袖挡：两臂交叉举到脸前，大袖挡住，上身往后仰、头扭开；退两步（位移由代码给）
    P["guard_hit"] = {**P["ready"], **legs(drop=0.035), "Spine01": {"pitch": -10}, "Spine02": {"pitch": -5}, "Head": {"yaw": 24, "pitch": 6},
        "R_Upperarm": {"pitch": -95, "roll": -10, "yaw": 25}, "R_Forearm": {"pitch": -160}, "L_Upperarm": {"pitch": -95, "roll": 10, "yaw": -25}, "L_Forearm": {"pitch": -85}}
    P["guard_hold"] = {**P["guard_hit"], "Spine01": {"pitch": -6}, "Head": {"yaw": 18, "pitch": 4}}
    # 收势：低头，右手顺一下左袖
    P["settle_a"] = {"base": "stand", **legs(drop=0.01), "Spine01": {"pitch": 4}, "Head": {"pitch": 14},
        "R_Upperarm": {"pitch": -35, "yaw": 40}, "R_Forearm": {"pitch": -160}, "L_Upperarm": {"pitch": -20}, "L_Forearm": {"pitch": -60}}
    P["settle_b"] = {**P["settle_a"], "Head": {"pitch": 10}, "R_Upperarm": {"pitch": -25, "yaw": 30}, "R_Forearm": {"pitch": -140}}
    # 跳跃（原地跳，人整个抬高由代码按抛物线给，docs/17 第十七节）：屈膝蓄力 → 蹬直离地（脚尖绷着）→ 空中收腿、两臂张开 → 落地前腿伸下来 → 落地屈膝缓冲
    P["jump_crouch"] = {**P["ready"], **legs(drop=0.13, fwd=0.02), "Spine01": {"pitch": 16}, "Spine02": {"pitch": 6}, "Head": {"pitch": -12},
        "R_Upperarm": {"pitch": -20, "roll": -20}, "R_Forearm": {"pitch": -130}, "L_Upperarm": {"pitch": 25, "roll": 18}, "L_Forearm": {"pitch": -25}}
    P["jump_push"] = {**P["ready"], **legs(drop=0.0), "L_Foot": {"pitch": 30}, "R_Foot": {"pitch": 30},
        "Spine01": {"pitch": -4}, "Spine02": {"pitch": -2}, "Head": {"pitch": -6},
        "R_Upperarm": {"pitch": -60, "roll": -35}, "R_Forearm": {"pitch": -120}, "L_Upperarm": {"pitch": -40, "roll": 40}, "L_Forearm": {"pitch": -20}}
    P["jump_tuck"] = {**P["ready"], **legs(drop=0.0, L=(0.06, 0.01, 0.2), R=(-0.02, 0.01, 0.15)), "Spine01": {"pitch": 10}, "Spine02": {"pitch": 4}, "Head": {"pitch": -8},
        "R_Upperarm": {"pitch": -35, "roll": -50}, "R_Forearm": {"pitch": -125}, "L_Upperarm": {"pitch": -20, "roll": 55}, "L_Forearm": {"pitch": -20}}
    P["jump_reach"] = {**P["ready"], **legs(drop=0.0, L=(0.03, 0, 0.04), R=(-0.01, 0, 0.03)), "L_Foot": {"pitch": 12}, "R_Foot": {"pitch": 12},
        "Spine01": {"pitch": 6}, "Head": {"pitch": -4},
        "R_Upperarm": {"pitch": -30, "roll": -40}, "R_Forearm": {"pitch": -130}, "L_Upperarm": {"pitch": -10, "roll": 45}, "L_Forearm": {"pitch": -20}}
    P["jump_land"] = {**P["ready"], **legs(drop=0.12, fwd=0.02), "Spine01": {"pitch": 18}, "Spine02": {"pitch": 6}, "Head": {"pitch": -12},
        "R_Upperarm": {"pitch": -30, "roll": -28}, "R_Forearm": {"pitch": -140}, "L_Upperarm": {"pitch": 10, "roll": 30}, "L_Forearm": {"pitch": -25}}
    P["jump_rise"] = {**P["ready"], **legs(drop=0.045), "Spine01": {"pitch": 8}, "Head": {"pitch": -4}}
    # 瞬移：侧身往右拧、右袖往外一甩、左手夹札立在胸前（这时人消失）；现身是另一段：微蹲、两臂还张着（袖子刚被带起），站起来手收回 ready
    P["blink_turn"] = {**P["ready"], **legs(drop=0.04, pelvis=-14), "Spine01": {"yaw": -30, "pitch": 4}, "Spine02": {"yaw": -14}, "Head": {"yaw": 34, "pitch": -2},
        "R_Upperarm": {"pitch": -25, "roll": -70}, "R_Forearm": {"pitch": -95}, "L_Upperarm": {"pitch": -50, "yaw": -32}, "L_Forearm": {"pitch": -125},
        "L_Fingers_0": {"local": [35, 0, 0]}, "L_Fingers_1": {"local": [45, 0, 0]}, **OPEN}
    P["blink_turn2"] = {**P["blink_turn"], "Spine01": {"yaw": -34, "pitch": 4}, "R_Upperarm": {"pitch": -20, "roll": -78}, "R_Forearm": {"pitch": -88}}
    P["blink_crouch"] = {**P["ready"], **legs(drop=0.1, fwd=0.02), "Spine01": {"pitch": 14}, "Spine02": {"pitch": 5}, "Head": {"pitch": -14},
        "R_Upperarm": {"pitch": -35, "roll": -45}, "R_Forearm": {"pitch": -120}, "L_Upperarm": {"pitch": -20, "roll": 45}, "L_Forearm": {"pitch": -30}}
    P["blink_rise"] = {**P["ready"], **legs(drop=0.04), "Spine01": {"pitch": 6}, "Head": {"pitch": -4},
        "R_Upperarm": {"pitch": -42, "roll": -8, "yaw": 18}, "R_Forearm": {"pitch": -155}}
    return P


# 动作：关键帧、烘焙范围、错开比例、出手时刻（秒）、要代码给的位移（米，秒）
CLIPS = {
    "ready_k":    dict(keys=[["ready", 0], ["ready", 62]], loop=True, breath=True, note="遭遇时的待机（循环，2.6 秒）"),
    "sense_k":    dict(keys=[["stand", 0], ["sense_a", 10], ["sense_b", 24], ["ready", 36]], note="察觉：按帽檐、侧头看（1.5 秒）"),
    "ofuda_flick_k": dict(keys=[["ready", 0], ["flick_wind", 5], ["flick_rel", 8], ["flick_follow", 10], ["ready", 15]], lead=0.5,
                          release=8 / 24, upper=True, note="投札·单手甩，只用上半身轨道（0.63 秒）"),
    "ofuda_spin_k": dict(keys=[["ready", 0], ["spin_wind", 7], ["spin_rel", 12], ["spin_follow", 15], ["ready", 22]], lead=0.6, release=12 / 24, note="投札·回身甩（0.92 秒）"),
    "ofuda_fan_k":  dict(keys=[["ready", 0], ["fan_gather", 8], ["fan_push", 12], ["fan_hold", 17], ["ready", 24]], lead=0.6, release=12 / 24, note="投札·撒一扇（1.0 秒）"),
    "seal_k":     dict(keys=[["ready", 0], ["seal", 8], ["seal_b", 22], ["ready", 29]], note="结印（1.2 秒）"),
    "dodge_back_k": dict(keys=[["ready", 0], ["dodge_crouch", 2], ["dodge_back", 5], ["dodge_land", 9], ["ready", 13]], lead=0.4,
                         move=dict(dir="back", dist=0.6, t=[0.08, 0.4]), note="滑步后撤（0.54 秒）"),
    "dodge_left_k": dict(keys=[["ready", 0], ["dodge_crouch", 2], ["side_L", 5], ["dodge_land", 9], ["ready", 13]], lead=0.4,
                           move=dict(dir="left", dist=0.6, t=[0.08, 0.4]), note="滑步往左（0.54 秒）"),
    "dodge_right_k": dict(keys=[["ready", 0], ["dodge_crouch", 2], ["side_R", 5], ["dodge_land", 9], ["ready", 13]], lead=0.4,
                           move=dict(dir="right", dist=0.6, t=[0.08, 0.4]), note="滑步往右（0.54 秒）"),
    "guard_k":    dict(keys=[["ready", 0], ["guard_hit", 4], ["guard_hold", 10], ["ready", 19]], lead=0.4,
                       move=dict(dir="back", dist=0.35, t=[0.05, 0.4]), note="袖挡，退两步（0.8 秒）"),
    "jump_k":     dict(keys=[["ready", 0], ["jump_crouch", 3], ["jump_push", 4], ["jump_tuck", 8], ["jump_reach", 12], ["jump_land", 14], ["jump_rise", 16], ["ready", 18]],
                       lead=0.25, takeoff=4 / 24, land=13 / 24, note="跳跃，原地（0.75 秒）：0.17 秒离地、0.54 秒落地，抬高由代码给"),
    "settle_k":   dict(keys=[["ready", 0], ["settle_a", 10], ["settle_b", 18], ["stand", 29]], note="收势（1.2 秒）"),
}


def build():
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    lib["poses"].update(poses())
    for k in [k for k in lib["poses"] if k.startswith("cb_")]: del lib["poses"][k]
    for name, c in CLIPS.items():
        keys = c["keys"]; f0, f1 = keys[0][1], keys[-1][1]
        frames = eg.bake(lib, keys, f0, f1, 1, prefix=f"cb_{name[:-2]}", lead_k=c.get("lead", 1.0), breath=c.get("breath", False))
        lib["poses"].update(frames)
        lib["animations"][name] = {"fps": 24, "keys": [[n, int(n.rsplit("_", 1)[1])] for n in frames]}
        print(f"{name}: {f1 + 0 - f0} 帧 = {(f1 - f0) / 24:.2f} 秒  {c['note']}")
    # 瞬移（0.5 秒）分两段烘焙，各自错开：消失前的侧身甩袖不会提前带出后半段的下蹲
    a = eg.bake(lib, [["ready", 0], ["blink_turn", 3], ["blink_turn2", 4]], 0, 4, 1, prefix="cb_blink", lead_k=0.3, breath=False)
    b = eg.bake(lib, [["blink_crouch", 5], ["blink_crouch", 6], ["blink_rise", 9], ["ready", 12]], 5, 12, 1, prefix="cb_blink", lead_k=0.5, breath=False)
    lib["poses"].update(a); lib["poses"].update(b)
    lib["animations"]["blink_k"] = {"fps": 24, "keys": [[n, int(n.rsplit("_", 1)[1])] for n in {**a, **b}]}
    print("blink_k: 12 帧 = 0.50 秒  瞬移：0.15 秒消失、0.25 秒现身（藏着的那 0.1 秒里切到下蹲）")
    # 退魔短版（3 秒）：抽剑、妖化、横斩、收剑，用退魔三拍的姿势压缩时间。剑砍到在 41 帧（1.71 秒）
    keys = [["draw_ready", 10], ["awaken_over", 19], ["awaken", 24], ["slash_wind_deep", 33], ["slash_step", 37], ["slash", 40],
            ["slash_over", 43], ["slash", 49], ["recover_step", 57], ["recover", 63]]
    frames = eg.bake(lib, keys, 10, 63, 1, prefix="exs", lead_k=0.6)
    lib["poses"].update(frames)
    for k in [k for k in lib["poses"] if k.startswith("exs_") and k not in frames]: del lib["poses"][k]
    lib["animations"]["exorcise_short_k"] = {"fps": 24, "keys": [["stand", 0]] + [[n, int(n[4:])] for n in frames] + [["stand", 72]]}
    A = [[0, 0], [15, 0], [20, 1.1], [24, 1.0], [30, 0.4], [36, 1.0], [42, 0.5], [48, 1.0], [56, 0.6], [62, 0], [72, 0]]
    lib["morphs"]["exorcise_short_k"] = {"awaken_hair": A, "awaken_hair2": [[f, round(max(0.0, (1.0 if 24 <= f <= 56 else 0.0) - v), 3)] for f, v in A],
        "awaken_eyes": [[0, 0], [17, 0], [18, 1], [61, 1], [62, 0], [72, 0]], "awaken_mouth": [[0, 0], [17, 0], [18, 1], [61, 1], [62, 0], [72, 0]]}
    print("exorcise_short_k: 72 帧 = 3.0 秒  退魔短版：0.42 秒抽剑、0.75 秒妖化、1.67 秒横斩砍到、2.4 秒收剑、2.58 秒妖化结束")
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写回 {LIB.relative_to(eg.ROOT)}")


if __name__ == "__main__":
    build()
