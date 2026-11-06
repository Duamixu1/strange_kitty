"""
配角"演戏"：每个人按人设有自己的待机（呼吸快慢、站相、重心换脚、往哪儿瞟）和两三个招牌小动作（11-06 用户："给角色都做一些
符合角色设定的动作绑骨，不要太机械"）。写进 tools/npc_poses/<名字>.json，原有的 walk_k、look_around_k 等不动。

  python3 tools/npc_acting.py [名字 ...]          # 不写就是 PERSONA 里所有人
  python3 tools/npc_acting.py --test-arms tokuji  # 把 ARMS 里每个手势排成 armtest_k，出模型拍图核手位
  然后 Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/<名字>_lite.glb --poses tools/npc_poses/<名字>.json \
       --out assets/processed/<名字>_posed.glb && tools/build_npc_lite.sh <名字>

不机械的几个办法：
  1. 跟随：每个动作带 lag，身子先到、脖子、头、上臂、前臂、手依次晚 1~5 帧（看东西的动作反过来，头先转、身子后跟）。
  2. 停顿不死停：同一个姿势要停一会儿时，后一帧自动加一点漂移（头再低一点、呼吸起伏），见 hold()。
  3. 待机不是对称的三段：呼吸快慢、深浅按人设，中间换一次重心（髋往一边挪、另一条腿松膝），瞟一眼的方向和时长各人不同，
     帧距故意不等。
  4. 站相：rest 是每个人自己的底姿（驼背、挺胸、手拢在肚子上、背着手、按刀……），待机和小动作都从 rest 出发回到 rest；
     走路还是 stand，游戏里切换有 0.35 秒淡入淡出。
角度约定同姿势库：朝上的骨头 pitch 正 = 往前低；手臂 pitch 负 = 往前抬；yaw 正 = 往角色左边转；roll 正 = 远端往角色左边倒；
Hip move = [左, 前, 上]（身高 1.0）。手臂一律用 arm() 写绝对值（男女站姿的手不一样，叠增量会掰坏），躯干、头写增量。
跪坐的人（tools/npc_seat.py 坐过的，lib["_seated"]）不动腿、不换重心，Hip 上下在坐姿基础上加。
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TORSO = ("Hip", "Waist", "Spine01", "Spine02", "NeckTwist01", "NeckTwist02", "Head", "L_Clavicle", "R_Clavicle")

# 跟随：身子先动，头、手后到（帧，24 帧/秒）
LAG_BODY = {"Spine02": 1, "NeckTwist01": 2, "NeckTwist02": 2, "Head": 3, "L_Clavicle": 1, "R_Clavicle": 1,
            "L_Upperarm": 2, "R_Upperarm": 2, "L_Forearm": 4, "R_Forearm": 4, "L_Hand": 5, "R_Hand": 5}
# 看东西：头先转，脖子、胸、腰依次跟上，手最后
LAG_LOOK = {"Head": 0, "NeckTwist02": 1, "NeckTwist01": 1, "Spine02": 3, "Spine01": 5, "Waist": 6, "Hip": 6,
            "L_Upperarm": 5, "R_Upperarm": 5, "L_Forearm": 7, "R_Forearm": 7, "L_Hand": 8, "R_Hand": 8}


# ---------------- 积木 ----------------
def add(*ds):
    """合并几个增量姿势：数值相加，move 按分量加；带 abs 的骨头整个覆盖"""
    out = {}
    for d in ds:
        for b, v in (d or {}).items():
            if v.get("abs"):
                out[b] = dict(v); continue
            o = dict(out.get(b, {}))
            for k, x in v.items():
                if k == "move": o["move"] = [a + c for a, c in zip(o.get("move", [0, 0, 0]), x)]
                elif k in ("pitch", "yaw", "roll"): o[k] = round(o.get(k, 0) + x, 2)
                else: o[k] = x
            out[b] = o
    return out


def arm(side, pitch, out=0.0, fore=-18.0, yin=8.0, uyaw=0.0, hand=None):
    """一只手臂（绝对值）：pitch 负 = 往前抬，out 正 = 往外张（负 = 往身上贴），fore = 前臂弯（负 = 往前上折），
    yin = 前臂往里收，uyaw = 上臂往里转，hand = 手腕 {pitch, yaw, roll}"""
    s = 1 if side == "L" else -1
    d = {f"{side}_Upperarm": {"abs": True, "pitch": pitch, "roll": s * out, "yaw": -s * uyaw},
         f"{side}_Forearm": {"abs": True, "pitch": fore, "yaw": -s * yin}}
    if hand: d[f"{side}_Hand"] = {"abs": True, **hand}
    return d


def both(pitch, out=0.0, fore=-18.0, yin=8.0, uyaw=0.0, **kw):
    return {**arm("L", pitch, out, fore, yin, uyaw, **kw), **arm("R", pitch, out, fore, yin, uyaw, **kw)}


def T(sp1=0, sp2=0, head=0, hyaw=0, hroll=0, syaw=0, sroll=0, hip=(0, 0, 0), neck=0):
    """躯干增量：sp1/sp2 腰、胸往前低，head 头低（负 = 抬），hyaw 头往左转，hroll 头往左歪，syaw 上身往左扭，sroll 上身往左倒"""
    d = {"Spine01": {"pitch": sp1, "yaw": syaw * 0.45, "roll": sroll * 0.6}, "Spine02": {"pitch": sp2, "yaw": syaw * 0.55, "roll": sroll * 0.4},
         "NeckTwist02": {"pitch": neck, "yaw": hyaw * 0.3}, "Head": {"pitch": head, "yaw": hyaw * 0.7, "roll": hroll}}
    if any(hip): d["Hip"] = {"move": list(hip)}
    return d


def look(deg, up=0.0):
    """往左（正）/右（负）看，头带着胸稍微跟"""
    return T(head=-up, hyaw=deg, syaw=deg * 0.25)


def breath(k=1.0):
    return {"Spine02": {"pitch": -1.8 * k}, "L_Clavicle": {"roll": -1.0 * k}, "R_Clavicle": {"roll": 1.0 * k},
            "Head": {"pitch": 0.7 * k}, "Hip": {"move": [0, 0, 0.0025 * k]}}


def bow(deg):
    """从腰往前躬（屁股往后坐一点保持平衡）"""
    return {**T(sp1=deg * 0.5, sp2=deg * 0.35, head=deg * 0.25, hip=(0, -0.0003 * deg, -0.0002 * deg))}


def shift(side, k=1.0, seated=False):
    """重心换到左（1）/右（-1）脚：髋往那边挪，另一条腿松膝，上身往回找平"""
    if seated: return T(sroll=-side * 1.2 * k, hroll=side * 1.0 * k)
    free = "R" if side > 0 else "L"
    return add(T(sroll=-side * 1.8 * k, hroll=side * 1.2 * k, hip=(0.007 * side * k, 0, -0.0025 * k)),
               {f"{free}_Thigh": {"pitch": -4 * k}, f"{free}_Calf": {"pitch": 8 * k}, f"{free}_Foot": {"pitch": -3 * k}})


def hold(d, k=1.0):
    """停顿后半段：头再沉一点、吸一口气，不死停"""
    return add(d, {"Head": {"pitch": 1.4 * k, "roll": 0.6 * k}}, breath(0.6 * k))


def mirror(d):
    """左右镜像（L_ ↔ R_，yaw / roll 取反，move x 取反）"""
    out = {}
    for b, v in d.items():
        nb = "R_" + b[2:] if b.startswith("L_") else "L_" + b[2:] if b.startswith("R_") else b
        nv = dict(v)
        for k in ("yaw", "roll"):
            if k in nv: nv[k] = -nv[k]
        if "move" in nv: nv["move"] = [-nv["move"][0], nv["move"][1], nv["move"][2]]
        out[nb] = nv
    return out


# ---------------- 手势（绝对手位；--test-arms 拍图核过，11-06 三轮） ----------------
# 前臂的 pitch 是叠在上臂上的：手到胸口 ≈ 上臂 -20~-30 + 前臂 -60~-75（合起来 -90 左右），再大手就跑到脸前。
# 背手、叉腰、碰帽檐试了几轮都不像（没有 IK，大袖也把手挡了），不用：老头改揣袖子，演员改抚鬓角。
ARMS = {
    "m_down": both(-6, -2, -18, 8),                         # 男站姿：手垂在两侧
    "clasp": both(-10, -6, -55, 40),                        # 女站姿：两手拢在身前
    "belly": both(-4, -3, -40, 54),                         # 两手护着小腹（志乃）
    "gassho": both(-28, -16, -72, 62),                     # 胸前合掌
    "fold": {**arm("L", -16, -6, -74, 82), **arm("R", -20, -4, -70, 78)},   # 抱臂
    "rub": both(-20, -10, -60, 56),                          # 两手在胸前搓（老板娘、福田）
    "hug": both(-26, -14, -72, 88),                        # 抱着自己（冷、怕）
    "open": both(-34, 34, -30, -6),                         # 两手摊开（"诸位放心"）
    "sleeves": both(-14, -6, -58, 64),                      # 两手揣进袖子里
    # 单手（右手）；左手另配
    "R_mouth": arm("R", -42, -26, -122, 48),                # 手掩嘴
    "R_temple": arm("R", -55, -16, -138, 36),               # 手到鬓角 / 耳边
    "R_eyes": arm("R", -46, -30, -128, 72),                 # 揉眼（手捂到右眼）                 # 揉眼
    "R_chin": arm("R", -46, -22, -130, 34),                 # 托下巴
    "R_headback": arm("R", -112, 26, -128, 6),              # 挠后脑勺
    "R_point": arm("R", -52, 6, -52, 6),                    # 往前指 / 点人
    "R_palm": arm("R", -34, 10, -64, 18, hand={"roll": -40}),   # 伸手要东西，手心朝上
    "R_wave": arm("R", -40, 18, -96, -6),                   # 抬手往外摆（赶人 / 说话比划）
    "R_shoulder": arm("R", -42, -30, -74, 84),             # 右手按左肩（捶肩）
    "R_chest": arm("R", -28, -22, -72, 74),                # 手按胸口
    "R_fan": arm("R", -62, 30, -78, -12),                   # 举扇（柳）：手抬到肩前往外
    "L_sword": arm("L", -5, -15, -52, 24),                  # 左手按刀（兵衛的站姿）
    "L_sword_grip": arm("L", -12, -12, -70, 34),            # 左手握紧刀鞘往上提一点
    "R_hilt": arm("R", -24, -26, -46, 62),                  # 右手搭刀柄（左腰）
}
ARMS["L_mouth"] = mirror(ARMS["R_mouth"])
ARMS["L_down"] = {k: v for k, v in ARMS["m_down"].items() if k.startswith("L_")}
ARMS["L_clasp"] = {k: v for k, v in ARMS["clasp"].items() if k.startswith("L_")}
ARMS["L_belly"] = {k: v for k, v in ARMS["belly"].items() if k.startswith("L_")}
ARMS["L_fold"] = {k: v for k, v in ARMS["fold"].items() if k.startswith("L_")}
ARMS["L_sleeves"] = {k: v for k, v in ARMS["sleeves"].items() if k.startswith("L_")}


def H(*names):
    """几个手势拼一起（后面的覆盖前面的）"""
    out = {}
    for n in names: out.update(ARMS[n])
    return out


# ---------------- 生成 ----------------
def compose(stand, *deltas):
    """stand + 增量 / 绝对手位 → 完整姿势（base: stand，每根动过的骨头写全）"""
    out = copy.deepcopy(stand)
    for b, v in add(*deltas).items():
        o = dict(out.get(b, {}))
        if v.get("abs"):
            for k in ("pitch", "yaw", "roll"): o[k] = v.get(k, 0)
            if b.endswith("_Hand") or b.endswith("_Upperarm"): o.pop("local", None)
        else:
            for k in ("pitch", "yaw", "roll"):
                if k in v: o[k] = round(o.get(k, 0) + v[k], 2)
            if "move" in v: o["move"] = [round(a + c, 4) for a, c in zip(o.get("move", [0, 0, 0]), v["move"])]
        out[b] = o
    return {"base": "stand", **{b: v for b, v in out.items() if b != "base"}}


def resolve(P, name):
    d = dict(P[name]); b = d.pop("base", None); out = resolve(P, b) if b else {}; out.update(d); return out


def test_arms(name):
    p = ROOT / f"tools/npc_poses/{name}.json"; lib = json.loads(p.read_text(encoding="utf-8"))
    stand = resolve(lib["poses"], "stand"); keys = []
    for i, (k, v) in enumerate(ARMS.items()):
        lib["poses"][f"at_{k}"] = compose(stand, v); keys.append([f"at_{k}", i * 10])
    lib["animations"] = {"armtest_k": {"fps": 24, "keys": keys}}
    out = Path(sys.argv[-1]) if sys.argv[-1].endswith(".json") else ROOT / f"tools/npc_poses/_armtest_{name}.json"
    out.write_text(json.dumps(lib, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, " ".join(f"{k}:{i * 10}" for i, k in enumerate(ARMS)))




# ---------------- 人设 ----------------
# rest：底姿（躯干增量 + 手势）；breath：一口气几秒（紧张的人短）；amp：呼吸深浅；sway：换重心的幅度（0 = 不换）；
# glance：待机里瞟一眼（度，左正右负）和抬头多少；fidget：待机里插一下的小动作（增量）；
# acts：{动作名: (跟随方式, [(增量, 秒) ..., (None, 回到底姿的秒数)])}，增量相对 rest，"hold" = 停在上一个姿势、带漂移
def rub2(k):   # 搓手：两只前臂一前一后错开
    return {"L_Forearm": {"yaw": -6 * k, "pitch": 3 * k}, "R_Forearm": {"yaw": 6 * k, "pitch": -3 * k}}


def jig(bone, key, amt):   # 某根骨头小幅来回（拍肩、摆手、揉眼）
    return {bone: {key: amt}}


SEQ_SHAKE = [(T(hyaw=11), .22), (T(hyaw=-11), .25), (T(hyaw=7), .22), (T(hyaw=-3), .2)]

PERSONA = {
    # ---- 大奥 ----
    "asa": dict(note="新来的女中，胆小、想家，偷偷留着娘给的小镜子", rest=T(sp2=2, head=5), breath=2.6, amp=1.1, sway=0.8, glance=(-24, 0),
                fidget=add(rub2(0.6), T(head=3)),
                acts={"mirror_k": ("body", [(add(H("rub"), T(sp2=4, head=16)), .7), ("hold", 1.2), (add(H("rub"), T(head=6), look(-24)), .45),
                                            (add(H("hug"), T(sp2=6, head=12)), .45), ("hold", .8), (None, .8)]),
                      "shy_bow_k": ("body", [(add(bow(14), T(head=6)), .45), ("hold", .35), (T(head=4), .35), (add(bow(8)), .3), (None, .55)]),
                      "look_back_k": ("look", [(add(look(-38), T(sroll=2)), .45), ("hold", .7), (look(-10), .3), (None, .5)])}),
    "kame": dict(note="女中，嘴碎，爱打听，说完又怕被人听见", rest=T(sp2=1, head=2), breath=2.4, sway=1.2, glance=(26, 0),
                 acts={"whisper_k": ("look", [(look(25), .35), (look(-25), .45), (add(H("R_mouth", "L_clasp"), T(sp2=5, sroll=6, hroll=7, hyaw=14)), .45),
                                              ("hold", 1.1), (look(-12), .3), (None, .55)]),
                       "tsk_k": ("look", [(add(T(head=4), breath(1.6)), .45)] + SEQ_SHAKE + [(T(head=3), .3), (None, .45)]),
                       "fix_collar_k": None}),
    "utayama": dict(note="老女，几十年守着规矩，冷、慢、居高临下", rest=T(sp1=-2, sp2=-3, head=-3), breath=4.0, amp=0.7, sway=0.4, glance=(8, 0),
                    acts={"stern_k": ("body", [(T(head=-8, sp2=-2), 1.0), ("hold", .9), (T(head=-6, hyaw=6), .45), (T(head=-6, hyaw=-6), .5), (T(head=-4), .4), (None, 1.0)]),
                          "turn_slow_k": None, "touch_hair_k": None}),
    # ---- 万屋 ----
    "shino": dict(note="怀着孩子投宿，护着肚子，又怕后面有人追", rest=add(H("belly"), T(sp1=-2, head=6)), breath=3.0, sway=0.7, glance=(-18, 0),
                  acts={"cradle_k": ("body", [(T(head=18, hroll=6), .9), (add(T(head=18, hroll=6, sroll=3), {"Hip": {"move": [0.005, 0, 0]}}), 1.0),
                                              (add(T(head=17, hroll=4, sroll=-3), {"Hip": {"move": [-0.005, 0, 0]}}), 1.1), ("hold", .6), (None, 1.0)]),
                        "thank_bow_k": ("body", [(bow(26), .7), ("hold", .6), (bow(8), .5), (None, .6)]),
                        "look_back_k": ("look", [(add(look(-40), T(sp2=2)), .5), ("hold", .8), (look(-8), .4), (None, .6)])}),
    "hisayo": dict(note="老板娘，笑脸迎客，一问起楼里的旧事就躲", rest=add(H("rub"), T(sp2=3, head=3)), breath=3.2, sway=0.9, glance=(14, 0),
                   fidget=rub2(0.7),
                   acts={"welcome_k": ("body", [(add(bow(10), rub2(1)), .45), (add(bow(13), rub2(-1)), .3), (add(bow(12), rub2(1)), .3),
                                                (add(bow(6), rub2(-0.5)), .35), (None, .55)]),
                         "evasive_k": ("look", [(add(H("R_mouth", "L_clasp"), look(-26), T(hroll=-5)), .55), ("hold", 1.0), (look(-8), .35), (None, .6)])}),
    "tokuji": dict(note="万屋的伙计，弓着背，夜里老听见楼上有小孩跑，心里发毛", rest=T(sp1=3, sp2=4, head=4), breath=2.8, sway=1.1, glance=(-14, -6),
                   acts={"scratch_k": ("body", [(add(H("R_headback"), T(hroll=-8, head=4)), .55), (add(H("R_headback"), T(hroll=-8, head=4), jig("R_Forearm", "pitch", 8)), .22),
                                                (add(H("R_headback"), T(hroll=-9, head=5), jig("R_Forearm", "pitch", -6)), .22), (add(H("R_headback"), T(hroll=-7, head=3)), .22), (None, .6)]),
                         "listen_up_k": ("look", [(T(head=-22, hyaw=10, sp2=-3), .7), ("hold", 1.2), (look(-16, up=10), .45), (None, .7)])}),
    # ---- 坂井家 ----
    "kayo": dict(note="女中，从早忙到晚，手脚闲不住，爽快", rest=T(head=2), breath=2.6, sway=1.3, glance=(18, 0),
                 acts={"shoulder_k": ("body", [(add(H("R_shoulder"), T(hroll=-10, hyaw=-6)), .5), (add(H("R_shoulder"), T(hroll=-11, hyaw=-6), jig("R_Forearm", "pitch", -8)), .2),
                                               (add(H("R_shoulder"), T(hroll=-10, hyaw=-6)), .2), (add(H("R_shoulder"), T(hroll=-12, hyaw=-5), jig("R_Forearm", "pitch", -8)), .2),
                                               (add(H("R_shoulder"), T(hroll=-9, hyaw=-4)), .2), (None, .5)]),
                       "stretch_neck_k": ("body", [(T(hroll=14), .5), (T(hroll=-14), .7), (add(T(sp2=-6, head=-8), breath(1.5)), .6), (None, .6)]),
                       "fix_collar_k": None}),
    "yoshiyuki": dict(note="坂井家的老人，背驼了，说起旧事出神，咳嗽", rest=add(H("sleeves"), T(sp1=7, sp2=8, head=2)), breath=3.8, amp=0.8, sway=0.5, glance=(10, 4),
                      acts={"cough_k": ("body", [(add(H("R_mouth", "L_sleeves"), T(sp2=4)), .45), (add(H("R_mouth", "L_sleeves"), T(sp2=11, head=4)), .2),
                                                 (add(H("R_mouth", "L_sleeves"), T(sp2=4)), .18), (add(H("R_mouth", "L_sleeves"), T(sp2=10, head=3)), .2), ("hold", .4), (None, .8)]),
                            "remember_k": ("look", [(look(15, up=10), 1.2), ("hold", 1.5), (T(head=10), 1.0), (None, 1.0)]),
                            "turn_slow_k": None}),
    "odajima": dict(note="家臣，今晚守夜，手不离刀，越看廊下越不踏实", rest=add(H("L_sword"), T(sp1=-2, sp2=-2)), breath=3.0, sway=0.6, glance=(26, 0),
                    acts={"grip_k": ("look", [(add(H("L_sword_grip", "R_hilt"), look(30), T(sp1=2)), .4), ("hold", .8), (add(H("L_sword_grip", "R_hilt"), look(-22)), .6),
                                              (add(H("L_sword_grip"), T(head=2)), .5), (None, .7)]),
                          "peer_k": ("body", [(T(sp1=6, sp2=4, head=-6, hyaw=-10), .8), ("hold", 1.2), (None, .8)])}),
    # ---- 笛小路家 ----
    "muromachi": dict(note="来比香的公家，嫌规矩多、闷，抱着胳膊不耐烦", rest=add(H("fold"), T(sp1=2, head=2)), breath=3.0, sway=1.5, glance=(-20, 0),
                      acts={"sigh_k": ("body", [(add(breath(2.6), T(head=-4)), .8), (add(T(sp2=7, head=9), {"L_Clavicle": {"roll": 3}, "R_Clavicle": {"roll": -3}}), .6), ("hold", .6), (None, .8)]),
                            "neck_roll_k": ("look", [(T(hroll=12), .4), (T(head=12), .35), (T(hroll=-12), .35), (T(head=-6), .35), (None, .5)])}),
    "nakarai": dict(note="也来比香，一心惦记那块香木，闻过就忘不掉", rest=add(H("sleeves"), T(head=1)), breath=3.4, sway=0.7, glance=(16, 6),
                    acts={"sniff_k": ("body", [(add(T(head=-14, sp2=-4), breath(2.0)), 1.0), ("hold", 1.0), (T(head=4, sp2=3), .9), (None, .8)]),
                          "snow_k": ("look", [(look(25, up=12), .8), ("hold", 1.0)] + SEQ_SHAKE[:2] + [(None, .7)])}),
    "osawa": dict(note="闻了三十年香的老行家，睡眼，自得，嘴上风雅", rest=add(H("sleeves"), T(sp1=-3, sp2=-2, head=-4)), breath=3.6, amp=0.8, sway=0.6, glance=(10, 0),
                  acts={"doze_k": ("body", [(T(head=22, sp2=5), 1.5), ("hold", .4), (T(head=-6, sp2=-2), .2), (look(10), .4), (None, .6)]),
                        "fuuga_k": ("body", [(add(H("R_chin", "L_sleeves"), T(head=6)), .6), (add(H("R_chin", "L_sleeves"), T(head=-2)), .35),
                                             (add(H("R_chin", "L_sleeves"), T(head=8)), .35), ("hold", .5), (None, .7)])}),
    "roni": dict(note="老尼，跪坐，眼睛不好，听谁说的都不一样", rest=T(sp1=6, sp2=6, head=6), breath=4.0, amp=0.7, sway=0.3, glance=(12, 0),
                 acts={"seat_bow_k": ("body", [(bow(24), 1.0), ("hold", 1.0), (None, 1.0)]),
                       "puzzled_k": ("look", [(T(hroll=12, hyaw=8), .9), ("hold", 1.2)] + SEQ_SHAKE[:2] + [(None, .9)])}),
    "ruri": dict(note="瑠璃姫，跪坐，以袖掩口，眼神往旁边飘", rest=T(head=3), breath=3.4, sway=0.4, glance=(-16, 0),
                 acts={"sleeve_mouth_k": ("body", [(add(H("R_mouth", "L_clasp"), look(-14), T(head=6)), .7), ("hold", 1.2), (None, .8)]),
                       "glance_k": ("look", [(look(28, up=-3), .9), ("hold", 1.0), (None, 1.0)])}),
    # ---- そらりす丸 ----
    "genkei": dict(note="老僧，跪坐，五十年天天为一个人诵经，心里有愧", rest=T(sp1=4, sp2=5, head=8), breath=4.2, amp=0.8, sway=0.3, glance=(0, -4),
                   acts={"pray_k": ("body", [(add(H("gassho"), bow(16)), 1.2), ("hold", 1.0), (add(H("gassho"), bow(18)), 1.0), (None, 1.2)]),
                         "grief_k": ("body", [(add(H("R_chest", "L_clasp"), T(head=20, sp2=6)), 1.2), ("hold", 1.5), (None, 1.2)])}),
    "sogen": dict(note="小和尚，听师父的话，胆小，老往舱门那边看", rest=T(sp2=2, head=5), breath=2.6, sway=0.9, glance=(-22, 0),
                  acts={"gassho_bow_k": ("body", [(add(H("gassho"), bow(20)), .5), ("hold", .45), (add(H("gassho"), bow(6)), .4), (None, .6)]),
                        "nervous_look_k": ("look", [(look(-30), .35), (look(25), .5), ("hold", .4), (None, .5)])}),
    "yanagi": dict(note="修验者柳幻殃斉，爱显摆、说话带比划，胸挺着", rest=T(sp1=-3, sp2=-5, head=-4), breath=3.0, sway=1.2, glance=(20, 4),
                   acts={"flourish_k": ("body", [(add(H("R_fan"), T(sp2=-6, head=-8, syaw=10)), .5), ("hold", .5), (add(H("R_point"), T(syaw=-8, head=-3)), .5),
                                                 ("hold", .4), (None, .7)]),
                         "boast_k": ("body", [(add(H("R_chin"), T(sp1=-6, sp2=-4, head=-10)), .6), (add(H("R_chin"), T(sp1=-6, sp2=-6, head=-12)), .18),
                                              (add(H("R_chin"), T(sp1=-6, sp2=-3, head=-9)), .18), (add(H("R_chin"), T(sp1=-6, sp2=-6, head=-12)), .18), (None, .7)])}),
    "sasaki": dict(note="佐々木兵衛，剑客，按着刀，刀在鞘里响", rest=T(sp1=-1), breath=3.2, sway=0.6, glance=(22, 0),
                   acts={"hilt_k": ("body", [(add(H("R_hilt", "L_sword_grip"), T(head=14, hyaw=12)), .7), ("hold", 1.2), (None, .8)]),
                         "scan_k": ("look", [(look(35), .9), ("hold", .8), (look(-30), 1.0), ("hold", .6), (None, .8)])}),
    "oyo": dict(note="阿庸，帮佣的妇人，规矩、低眉顺眼", rest=T(sp2=3, head=5), breath=3.0, sway=0.8, glance=(-14, 0),
                acts={"polite_bow_k": ("body", [(bow(22), .6), ("hold", .5), (None, .7)]), "fix_collar_k": None}),
    # ---- 地铁 ----
    "masao": dict(note="送牛奶的小孩，闲不住，看得见别人看不见的东西", rest=T(sp1=-1, head=-2), breath=2.2, sway=1.6, glance=(20, 8),
                  acts={"bounce_k": ("body", [(T(hip=(0, 0, 0.006)), .2), (add(T(hip=(0, 0, -0.008)), {"L_Thigh": {"pitch": -6}, "R_Thigh": {"pitch": -6}, "L_Calf": {"pitch": 12}, "R_Calf": {"pitch": 12}}), .2),
                                              (T(hip=(0, 0, 0.006)), .2), (add(T(hip=(0, 0, -0.008)), {"L_Thigh": {"pitch": -6}, "R_Thigh": {"pitch": -6}, "L_Calf": {"pitch": 12}, "R_Calf": {"pitch": 12}}), .2), (None, .3)]),
                        "point_k": ("look", [(add(H("R_point"), look(20, up=6)), .5), ("hold", 1.0), (None, .6)])}),
    "kinoshita": dict(note="司机，累、心虚，那晚他闭了一下眼", rest=T(sp1=5, sp2=6, head=8), breath=3.4, amp=1.2, sway=0.8, glance=(-10, -4),
                      acts={"rub_eyes_k": ("body", [(add(H("R_eyes"), T(head=10)), .7), (add(H("R_eyes"), T(head=11), jig("R_Forearm", "yaw", 6)), .25),
                                                    (add(H("R_eyes"), T(head=10), jig("R_Forearm", "yaw", -6)), .25), (add(H("R_eyes"), T(head=12)), .25), (None, .8)]),
                            "nod_off_k": ("body", [(T(head=24, sp2=4), 1.4), (T(head=-4, sp2=-3), .2), (look(18), .4), (None, .7)])}),
    "haru": dict(note="瞒着婆婆跑出来，嘴上念佛，心里藏事", rest=T(sp2=3, head=6), breath=2.8, sway=0.8, glance=(-22, 0),
                 acts={"pray_quick_k": ("body", [(add(H("gassho"), bow(8)), .4), (add(H("gassho"), bow(3)), .3), (add(H("gassho"), bow(9)), .3), (None, .5)]),
                       "furtive_k": ("look", [(look(-30), .4), (look(25), .5), (add(H("hug"), T(head=8)), .5), ("hold", .6), (None, .6)]),
                       "fix_collar_k": None}),
    "chiyo": dict(note="咖啡馆女招待，一心想上电影，爱摆姿势", rest=T(sp1=-2, sp2=-3, head=-3), breath=2.6, sway=1.4, glance=(16, 0),
                  acts={"pose_k": ("body", [(add(H("R_temple", "L_clasp"), T(head=-6, hroll=8, syaw=10), shift(1, 1.5)), .7), ("hold", 1.2), (None, .7)]),
                        "giggle_k": ("body", [(add(H("R_mouth", "L_clasp"), T(head=4, hroll=5)), .4), (add(H("R_mouth", "L_clasp"), T(head=5, hroll=5, sp2=2)), .15),
                                              (add(H("R_mouth", "L_clasp"), T(head=3, hroll=6, sp2=-1)), .15), (add(H("R_mouth", "L_clasp"), T(head=5, hroll=5, sp2=2)), .15),
                                              (None, .5)])}),
    "moriya": dict(note="每朝日报的记者，老练，一问稿子就装傻", rest=T(), breath=3.0, sway=1.0, glance=(-16, 0),
                   acts={"think_k": ("look", [(add(H("R_chin"), look(-20, up=6)), .7), ("hold", 1.4), (None, .7)]),
                         "shrug_k": ("body", [(add(H("R_palm"), {"L_Clavicle": {"roll": -6}, "R_Clavicle": {"roll": 6}}, T(hroll=6), look(-14)), .4), ("hold", .6), (None, .6)])}),
    "fukuda": dict(note="地铁的老板，得意，挺着胸，说话张开手", rest=T(sp1=-3, sp2=-6, head=-5), breath=3.6, amp=1.2, sway=0.7, glance=(12, 0),
                   acts={"open_k": ("body", [(add(H("open"), T(head=-6)), .7), ("hold", 1.0), (None, .8)]),
                         "rub_hands_k": ("body", [(add(H("rub"), T(head=4)), .5), (add(H("rub"), rub2(1)), .3), (add(H("rub"), rub2(-1)), .3), (add(H("rub"), rub2(1)), .3), (None, .6)])}),
    # ---- 牢房 ----
    "ocho": dict(note="お蝶，忍着，低着头，什么都说记不清", rest=T(sp1=4, sp2=6, head=14), breath=3.0, amp=0.7, sway=0.3, glance=(-8, -4),
                 acts={"endure_k": ("body", [(add(H("hug"), T(head=20, sp2=8)), 1.0), ("hold", 1.5), (None, 1.2)]),
                       "forget_k": ("look", [(add(look(18, up=-4), T(hroll=10)), 1.2), ("hold", 1.5), (None, 1.2)])}),
    "ocho_mother": dict(note="お蝶的娘，要强，嘴上全是为女儿好", rest=T(sp1=-2, sp2=-2, head=-2), breath=2.8, sway=0.9, glance=(14, 0),
                        acts={"insist_k": ("body", [(add(H("R_point", "L_clasp"), T(head=4, syaw=8)), .4), (add(H("R_point", "L_clasp"), T(head=6, syaw=8), jig("R_Forearm", "pitch", -14)), .2),
                                                    (add(H("R_point", "L_clasp"), T(head=4, syaw=8)), .2), (add(H("R_point", "L_clasp"), T(head=6, syaw=8), jig("R_Forearm", "pitch", -14)), .2), (None, .5)]),
                              "firm_nod_k": ("body", [(T(head=12), .25), (T(head=-2), .25), (T(head=12), .25), (None, .5)])}),
    "shuto": dict(note="婆婆，嫌媳妇磨蹭，守着这家的规矩", rest=T(sp1=4, sp2=5, head=-2), breath=3.2, sway=0.5, glance=(-12, 0),
                  acts={"shoo_k": ("body", [(add(H("R_wave", "L_clasp"), look(-10)), .3), (add(H("R_wave", "L_clasp"), look(-10), jig("R_Forearm", "yaw", -16)), .2),
                                            (add(H("R_wave", "L_clasp"), look(-10)), .2), (add(H("R_wave", "L_clasp"), look(-10), jig("R_Forearm", "yaw", -16)), .2), (None, .5)]),
                        "scold_k": ("body", [(T(sp1=6, head=-6, hyaw=10), .4), (T(sp1=6, head=4, hyaw=10), .25), (T(sp1=6, head=-4, hyaw=10), .25), ("hold", .4), (None, .6)])}),
    "kazumasa": dict(note="お蝶的丈夫，抱着胳膊，眼睛不看人，伸手就要茶", rest=add(H("fold"), T(sp1=-2, sp2=-3, head=-4)), breath=3.4, sway=0.8, glance=(20, 4),
                     acts={"demand_k": ("body", [(add(H("R_palm", "L_fold"), look(-20)), .4), ("hold", .9), (add(H("R_palm", "L_fold"), look(-20), jig("R_Hand", "pitch", -20)), .2),
                                                 (add(H("R_palm", "L_fold"), look(-20)), .2), (None, .6)]),
                           "turn_away_k": ("look", [(look(35, up=6), .5), ("hold", 1.0), (None, .7)])}),
}
# 地铁乘客人偶：像人偶，几乎不喘气，偶尔脖子"咔"地歪一下（快进快出）
for _n in ("mnq_bare", "mnq_suit", "mnq_dress", "mnq_kimono"):
    PERSONA[_n] = dict(note="地铁乘客人偶，不该会动", rest=T(), breath=4.5, amp=0.15, sway=0.1, glance=(0, 0), doll=True, acts={})


def build_idle(c, mk):
    """待机：底姿上呼吸几轮，中间换一次重心、瞟一眼、插一个小动作；帧距不等，最后回到底姿接上循环"""
    b = 24 * c["breath"]; amp = c.get("amp", 1.0); sw = c.get("sway", 1.0); seated = mk.seated
    gy, gu = c.get("glance", (12, 0)); side = 1 if gy >= 0 else -1
    if c.get("doll"):
        tic = T(hroll=9 * side, hyaw=-6)
        P = {"rest": {}, "in": breath(amp), "tic": tic, "tic2": add(tic, T(hroll=1))}
        seq = [("rest", 0), ("in", .5), ("rest", 1.0), ("rest", 1.9), ("tic", 1.94), ("tic2", 2.6), ("tic", 2.62), ("rest", 2.68), ("in", 3.2), ("rest", 3.8)]
    else:
        sh = shift(side, sw, seated)
        P = {"rest": {}, "in": breath(amp), "out": add(T(head=0.8), breath(-0.25 * amp)), "shin": add(sh, breath(amp)), "sh": add(sh, breath(0.2 * amp)),
             "gl": add(sh, look(gy, gu), breath(0.5 * amp)), "fid": add(c.get("fidget") or T(head=2.5, hroll=-1.5 * side), breath(0.4 * amp)),
             "in2": add(breath(0.8 * amp), T(hroll=-1.0 * side))}
        P["glh"] = hold(P["gl"])
        seq = [("rest", 0), ("in", .45), ("out", 1.0), ("shin", 1.5), ("sh", 2.05), ("gl", 2.4), ("glh", 3.1), ("shin", 3.55), ("fid", 4.1),
               ("fid", 4.45), ("in2", 4.85), ("out", 5.35), ("rest", 5.8)]
    keys = []
    for pn, f in seq:
        keys.append([mk.pose(f"idle_{pn}", P[pn]), round(f * b)])
    return {"fps": 24, "keys": keys, "lag": {**LAG_BODY, "Head": 2}}


def build_act(name, spec, mk, tempo=1.0):
    kind, steps = spec
    keys = [[mk.pose("rest", {}), 0]]; t = 0.0; prev = {}
    for i, (d, sec) in enumerate(steps):
        t += sec * tempo
        if d is None:
            keys.append([mk.pose("rest", {}), round(t * 24)]); break
        if d == "hold": d = hold(prev)
        prev = d
        keys.append([mk.pose(f"{name[:-2]}_{i}", d), round(t * 24)])
    # 帧不能重复（太快的小段四舍五入撞了），撞了往后挪一帧
    for i in range(1, len(keys)):
        if keys[i][1] <= keys[i - 1][1]: keys[i][1] = keys[i - 1][1] + 1
    return {"fps": 24, "keys": keys, "lag": LAG_LOOK if kind == "look" else LAG_BODY}


class Maker:
    """把增量姿势叠到 stand + rest 上，写进姿势库，名字前缀 a_"""
    def __init__(self, lib, rest):
        self.P = lib["poses"]; self.stand = resolve(self.P, "stand"); self.rest = rest; self.seated = bool(lib.get("_seated"))

    def pose(self, name, delta):
        d = delta
        if self.seated:   # 坐着不动腿
            d = {b: v for b, v in delta.items() if not any(b.startswith(f"{s}_{x}") for s in "LR" for x in ("Thigh", "Calf", "Foot"))}
        self.P[f"a_{name}"] = compose(self.stand, self.rest, d)
        return f"a_{name}"


def run(name):
    c = PERSONA[name]; p = ROOT / f"tools/npc_poses/{name}.json"
    if not p.exists(): print(name, "没有姿势库，跳过"); return
    lib = json.loads(p.read_text(encoding="utf-8"))
    for k in [k for k in lib["poses"] if k.startswith("a_")]: del lib["poses"][k]
    mk = Maker(lib, c["rest"])
    A = lib["animations"]
    A["idle_k"] = build_idle(c, mk)
    made = []
    for an, spec in c["acts"].items():
        if spec is None: continue   # 沿用已有的（fix_collar_k、turn_slow_k 这些）
        A[an] = build_act(an, spec, mk); made.append(an)
    lib["acting"] = {"note": c["note"], "idles": [a for a in c["acts"] if a in A]}
    p.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: idle_k {A['idle_k']['keys'][-1][1] / 24:.1f} 秒；" + "，".join(f"{a} {A[a]['keys'][-1][1] / 24:.1f} 秒" for a in made)
          + f"；游戏 idles 用 {lib['acting']['idles']}")


if __name__ == "__main__":
    if "--test-arms" in sys.argv:
        test_arms(sys.argv[sys.argv.index("--test-arms") + 1]); sys.exit()
    for n in (sys.argv[1:] or PERSONA): run(n)
