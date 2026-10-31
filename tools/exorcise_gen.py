"""
退魔三拍 exorcise_k 的挥剑段（游21，10-31 重做）：蓄势 slash_wind → 迈步 slash_step → 横斩 slash → 收脚 recover_step → 收剑 recover，
算好写回 tools/poses/kusuriuri_v2.json（覆盖这几个姿势和 exorcise_k 的关键帧），再跑 blender_pose_anim.py 出模型。

用户说"挥剑这里还是有很多问题"（翻车集 008）。原来的写法和改法：
- 横斩：整个人（Hip）往左转 18°、两节脊柱再转 36°，右臂横过胸前，剑横着从胸前和两只大袖中间穿过去。
  改成肩膀只转 20° 左右，右臂往正前方伸直，剑往左前方平着指出去，离身体一臂远；左臂往后收，左袖让开剑路。
- 弓步：原来只把髋往前下挪、两条大腿各掰一个角度，后腿膝盖是反着弯的（R_Calf -35），脚不在地上，
  下摆没打帧、被腿撑成一团，下摆还拖地。改成和走路同一套腿 IK（walk_gen.leg_ik）：右脚不动，左脚往前迈一步落地，
  髋往前、往下沉，两只脚都踩在地上；迈步、收脚各加一个抬脚的中间帧，脚不在地上滑。
  下摆骨链按两条大腿的角度打帧（同走路的"下摆跟腿"，权重换成弓步的：前片跟前腿、后片跟后腿）。
- 节奏点不变：1.25 秒抽剑（30 帧）、3.08 秒妖化（74 帧）、5.1 秒横斩（123 帧）、7.9 秒收剑（190 帧）。

  python3 tools/exorcise_gen.py [k=v ...]     # 参数见 P，比如 step=0.40 drop=0.05
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import walk_gen as wg

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "tools/poses/kusuriuri_v2.json"
wg.use_char("kusuriuri")

P = dict(
    step=0.42,       # 左脚往前迈多远（米）
    hip_fwd=0.16,    # 弓步时髋往前挪（米）
    drop=0.05,       # 弓步时髋往下沉（米）
    foot_in=0.03,    # 迈出去的左脚往中线收多少（米，A 字站两脚隔 20 厘米）
    lift=0.07,       # 迈步、收脚时脚抬多高（米）
    pelvis=-6,       # 弓步骨盆扭转（度，左脚在前 = 左髋往前 = 往右转 = 负）
    wind_back=0.03,  # 蓄势时髋往后挪（米）
    wind_drop=0.015,
)
for kv in sys.argv[1:]:
    k, v = kv.split("="); P[k] = float(v)

RS_UP, RS_FORE, RS_FY, RS_DIR = -45, -110, 0, [0.35, 0.55, 0.75]   # 收脚时右臂：剑从左前方平指收回到竖直
GRIP = {"R_Fingers_0": {"local": [75, 0, 0]}, "R_Fingers_1": {"local": [80, 0, 0]}}


def rest_fwd(side):
    """绑定姿势脚踝在髋关节前面多少（米，负 = 在后面）：大腿、小腿本来就往后斜一点"""
    tl, cl, a0, c0 = wg.LEG[side]
    return -(tl * math.sin(math.radians(a0)) + cl * math.sin(math.radians(c0)))


def legs(foot, hip_fwd, drop, pelvis_yaw=0.0):
    """foot = {side: (前后, 左右, 离地)}：脚踝相对绑定位置往前挪多少、往中线收多少、抬多高（米）。
    髋往前 hip_fwd、往下 drop。返回腿、Hip、Pelvis 的姿势，以及两腿的大腿 / 膝盖角（给下摆用）"""
    pose, th, kn = {}, {}, {}
    pv = {"yaw": pelvis_yaw, "roll": 0.0, "sway_m": 0.0, "foot_half": 0.0}
    dn0 = wg.REST_DN - drop
    for s in "LR":
        df, din, h = foot[s]
        sg = 1 if s == "L" else -1
        fwd = rest_fwd(s) + df - hip_fwd
        dfwd, dz = wg.hip_shift(s, pv)
        side = wg.ANKLE_REST[s] - sg * din                          # 脚踝在髋关节左右哪边（左为正）
        # 脚的左右位置基本不动（A 字站的宽度，只往里收几厘米），在侧面投影里解 IK：投影长度正好还原绑定姿势
        #（走路用三维长度 + 闭环修正，这里没修正表，用三维长度绑定姿势本身就会解成膝盖弯 25°）
        tl, cl, a0, c0 = wg.LEG[s]
        a, c, clamped = wg.leg_ik(fwd - dfwd, dn0 + dz - h, tl, cl)
        pt = a - a0; pc = c - c0 - pt
        roll = math.degrees(math.asin(max(-0.5, min(0.5, (side - wg.ANKLE_REST[s]) / (dn0 - h)))))
        toe = 0.0
        pose[f"{s}_Thigh"] = {"world": True, "pitch": round(pt, 2), "roll": round(roll, 2)}
        pose[f"{s}_Calf"] = {"pitch": round(pc, 2)}
        pose[f"{s}_Foot"] = {"pitch": round(-(pt + pc) + toe, 2)}
        th[s], kn[s] = pt, pc
        if clamped: print(f"  ! {s} 腿够不着（前 {fwd:.3f}，下 {dn0 - h:.3f}）")
        print(f"  {s}: 脚踝在髋前 {fwd:+.3f} 米，大腿 {pt:+.1f}°，膝盖弯 {pc:+.1f}°")
    pose["Hip"] = {"move": [0, round(hip_fwd / wg.UNIT, 4), round(-drop / wg.UNIT, 4)]}
    if pelvis_yaw: pose["Pelvis"] = {"yaw": pelvis_yaw}
    return pose, th, kn


# 下摆骨链（12 条，00 右侧、01~05 前片从右到左、06 左侧、07~11 后片从左到右）跟腿的权重 (左腿, 右腿)。
# 弓步两腿一前一后张开 60° 左右，走路那套后片只跟 10~18% 不够，后腿会从后片里戳出来；这里前片跟前腿（左），后片跟后腿（右）
HEM_LUNGE = {0: (0.05, 0.45), 1: (0.25, 0.35), 2: (0.45, 0.2), 3: (0.65, 0.05), 4: (0.75, 0.0), 5: (0.7, 0.0),
             6: (0.45, 0.05), 7: (0.2, 0.25), 8: (0.1, 0.45), 9: (0.05, 0.55), 10: (0.0, 0.6), 11: (0.0, 0.55)}


def hem(th, kn):
    """第 1 节绕髋跟大腿转；前片在前腿膝盖弯的地方往回收一点，布在膝盖处鼓成弧；后片下面两节往后多甩一点，不贴着后腿小腿"""
    out = {}
    for k, (wl, wr) in HEM_LUNGE.items():
        a = wl * th["L"] + wr * th["R"]
        knee = wl * kn["L"] + wr * kn["R"]
        front = 1 <= k <= 5
        out[f"chain_hem_{k:02d}_0"] = {"pitch": round(a, 2)}
        out[f"chain_hem_{k:02d}_1"] = {"pitch": round(0.45 * knee + 0.2 * max(0.0, -a), 2) if front else round(0.3 * knee, 2)}
        out[f"chain_hem_{k:02d}_2"] = {"pitch": round(0.15 * knee, 2)}
    return out


# ---- 逐帧烘焙（10-31 第二版）：关键姿势之间不再让 Blender 整身一起插值，在这里按骨头错开时间算好每 2 帧一个姿势 ----
# 原来全身每根骨头在同一帧到位、同一帧停，定住的地方完全静止，看着像木偶。现在：
#   1. 错开（LEAD，帧）：髋和腿先动，腰、胸、肩依次晚一点，右手和剑按关键帧准时到（节奏点不变），左手、头再晚一点
#   2. 关键帧之间用单调三次插值（不过冲、过关键帧时速度连续），不在每个关键帧都停一下
#   3. 余摆：妖化甩臂、横斩都"过头一点再回来"（awaken_over、slash_over）；蓄势越拧越紧（slash_wind_deep）
#   4. 呼吸：定住的时候胸口、肩膀、头一直有很小的起伏（2.6 秒一次），剑尖跟着微微晃
LEAD = {"Hip": 3, "Pelvis": 3, "Waist": 2.5, "Spine01": 2, "Spine02": 1.2, "R_Clavicle": 0.8, "L_Clavicle": 0.5,
        "R_Upperarm": 0.5, "Head": -1.5, "L_Upperarm": -1.5, "L_Forearm": -2.5, "L_Hand": -3}
def lead_of(b):
    if b in LEAD: return LEAD[b]
    if b.startswith(("L_Thigh", "R_Thigh", "L_Calf", "R_Calf", "L_Foot", "R_Foot", "chain_hem")): return 3
    return 0


def resolve(lib, n):
    d = dict(lib["poses"][n]); b = d.pop("base", None); out = resolve(lib, b) if b else {}; out.update(d); return out


def mono(ts, vs, t):
    """单调三次插值（Fritsch–Carlson）：过关键帧时速度连续、不过冲，两个相同的值之间保持不动"""
    if t <= ts[0]: return vs[0]
    if t >= ts[-1]: return vs[-1]
    n = len(ts); d = [(vs[i + 1] - vs[i]) / (ts[i + 1] - ts[i]) for i in range(n - 1)]
    m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0 else 3 * (ts[i + 1] - ts[i - 1]) / ((2 * ts[i + 1] - ts[i] - ts[i - 1]) / d[i - 1] + (ts[i + 1] + ts[i] - 2 * ts[i - 1]) / d[i]) for i in range(1, n - 1)] + [d[-1]]
    i = max(j for j in range(n - 1) if ts[j] <= t); h = ts[i + 1] - ts[i]; u = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    return h00 * vs[i] + h10 * h * m[i] + h01 * vs[i + 1] + h11 * h * m[i + 1]


def bake(lib, keys, f0, f1, step):
    flat = [(resolve(lib, n), f) for n, f in keys]
    ts = [f for _, f in flat]
    bones = sorted({b for p, _ in flat for b in p if b != "aim"})
    out = {}
    for f in range(f0, f1 + 1, step):
        pose = {}
        for b in bones:
            tt = min(max(f + lead_of(b), f0), f1)
            spec = {}
            for ch in ("pitch", "yaw", "roll"):
                vs = [p.get(b, {}).get(ch, 0.0) for p, _ in flat]
                if any(vs): spec[ch] = round(mono(ts, vs, tt), 2)
            for ch in ("move", "local"):
                vs = [p.get(b, {}).get(ch) for p, _ in flat]
                if any(v is not None for v in vs):
                    vs = [v or [0, 0, 0] for v in vs]
                    spec[ch] = [round(mono(ts, [v[k] for v in vs], tt), 5) for k in range(3)]
            if any(p.get(b, {}).get("world") for p, _ in flat) or b.endswith("_Thigh"): spec["world"] = True   # 站姿里髋没转，加不加 world 一样
            if spec: pose[b] = spec
        # 呼吸：2.6 秒一次，胸口先、头晚一点，剑尖跟着微微晃
        ph = 2 * math.pi * (f - f0) / 62
        for b, amp, lag in (("Spine01", 0.9, 0), ("Spine02", 0.8, 0.4), ("Head", -0.7, 0.9)):
            pose.setdefault(b, {}); pose[b]["pitch"] = round(pose[b].get("pitch", 0) + amp * math.sin(ph - lag), 2)
        for b, amp in (("L_Clavicle", -0.8), ("R_Clavicle", 0.8)):
            pose.setdefault(b, {}); pose[b]["roll"] = round(pose[b].get("roll", 0) + amp * math.sin(ph - 0.3), 2)
        dirs = [p["aim"]["dir"] for p, _ in flat]
        dv = [mono(ts, [d[k] for d in dirs], f) for k in range(3)]
        dv[2] += 0.015 * math.sin(ph * 1.3 + 1)
        nrm = math.sqrt(sum(x * x for x in dv)); pose["aim"] = {"socket": "socket_R_Hand", "dir": [round(x / nrm, 4) for x in dv]}
        out[f"exo_{f:03d}"] = pose
    return out


def morphs():
    """妖化形态键：awaken_hair / awaken_hair2 是两套分缕错开的火焰形（tools/blender_awaken.py），
    66→77 帧炸开（冲过头到 1.12 再回 1），之后两套此消彼长地交替（1.4 次/秒，再叠一个慢的晃动），火舌一跳一跳地动；190→220 落回。
    表情（缩瞳、露齿）照旧 74 帧切入、197 帧切回"""
    env_t, env_v = [0, 66, 77, 84, 190, 220, 250], [0, 0, 1.12, 1.0, 1.0, 0, 0]
    A, B = [[0, 0]], [[0, 0]]
    for f in range(66, 223, 3):
        e = mono(env_t, env_v, f)
        x = (f - 76) / 24
        w = 0.5 + 0.5 * math.cos(2 * math.pi * 1.4 * x + 0.9 * math.sin(2 * math.pi * 0.55 * x)) if f > 76 else 1.0
        w = 1.0 - (1.0 - w) * min(1.0, max(0.0, (f - 76) / 9))   # 炸开时只用第一套，之后慢慢开始交替
        A.append([f, round(e * w, 3)]); B.append([f, round(e * (1 - w), 3)])
    A.append([250, 0]); B.append([250, 0])
    return {"awaken_hair": A, "awaken_hair2": B,
            "awaken_eyes": [[0, 0], [73, 0], [74, 1], [196, 1], [197, 0], [250, 0]],
            "awaken_mouth": [[0, 0], [73, 0], [74, 1], [196, 1], [197, 0], [250, 0]]}


def build():
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    poses = lib["poses"]
    planted = {"L": (0.0, 0.0, 0.0), "R": (0.0, 0.0, 0.0)}
    lunge = {"L": (P["step"], P["foot_in"], 0.0), "R": (0.0, 0.0, 0.0)}
    mid = {"L": (P["step"] * 0.5, P["foot_in"] * 0.5, P["lift"]), "R": (0.0, 0.0, 0.0)}

    print("蓄势 slash_wind")
    lw, _, _ = legs(planted, -P["wind_back"], P["wind_drop"], pelvis_yaw=-4)
    # 上身：原来的 Hip 往右转 10° 拆给两节脊柱（Hip 一转腿和脚也跟着转，脚会在地上拧）
    poses["slash_wind"] = {"base": "stand", **lw,
        "Spine01": {"yaw": -28, "pitch": -2}, "Spine02": {"yaw": -12}, "Head": {"yaw": 16},
        "R_Upperarm": {"pitch": 35, "roll": -85}, "R_Forearm": {"pitch": -40, "yaw": 40},
        "L_Upperarm": {"pitch": 15, "roll": 22}, "L_Forearm": {"pitch": -45},
        "aim": {"socket": "socket_R_Hand", "dir": [-0.3, -0.6, 0.75]}, **GRIP}

    print("迈步 slash_step（左脚抬起、走到一半）")
    ls, th, kn = legs(mid, P["hip_fwd"] * 0.45, P["drop"] * 0.4, pelvis_yaw=P["pelvis"] * 0.5)
    poses["slash_step"] = {"base": "stand", **ls, **hem(th, kn),
        "Spine01": {"yaw": -6, "pitch": 3}, "Spine02": {"yaw": -2}, "Head": {"yaw": 4},
        "R_Upperarm": {"pitch": -30, "roll": -55}, "R_Forearm": {"pitch": -65, "yaw": 15},
        "L_Upperarm": {"pitch": 25, "roll": 22}, "L_Forearm": {"pitch": -30},
        "aim": {"socket": "socket_R_Hand", "dir": [-0.45, 0.85, 0.1]}, **GRIP}

    print("横斩 slash（弓步）")
    ll, th, kn = legs(lunge, P["hip_fwd"], P["drop"], pelvis_yaw=P["pelvis"])
    # 肩膀往左转 22°（原来 Hip 18 + 脊柱 36 = 54°，右臂横过胸前，剑从胸前、两只袖子中间穿过）；
    # 右臂往正前方平伸，剑往左前方平指出去；左臂往后下收，左袖让开剑路
    poses["slash"] = {"base": "stand", **ll, **hem(th, kn),
        "Spine01": {"yaw": 14, "pitch": 7}, "Spine02": {"yaw": 8, "pitch": 2}, "Head": {"yaw": -14, "pitch": -3},
        "R_Clavicle": {"yaw": 6},
        "R_Upperarm": {"pitch": -58, "yaw": -2}, "R_Forearm": {"pitch": -79, "yaw": 4},   # 前臂 -75 是抵掉 bind_fix 的（站姿同），再 -4 = 伸直
        "L_Upperarm": {"pitch": 32, "roll": 18}, "L_Forearm": {"pitch": -20},
        "aim": {"socket": "socket_R_Hand", "dir": [0.85, 0.5, -0.08]}, **GRIP}

    print("收脚 recover_step（左脚抬起往回收）")
    lr, th, kn = legs(mid, P["hip_fwd"] * 0.5, P["drop"] * 0.5, pelvis_yaw=P["pelvis"] * 0.5)
    poses["recover_step"] = {"base": "stand", **lr, **hem(th, kn),
        "Spine01": {"pitch": 3, "yaw": 5}, "Spine02": {"pitch": 2, "yaw": 2}, "Head": {"pitch": 6},
        "R_Upperarm": {"pitch": RS_UP, "roll": 5}, "R_Forearm": {"pitch": RS_FORE, "yaw": RS_FY},
        "L_Upperarm": {"pitch": 12}, "L_Forearm": {"pitch": -30},
        "aim": {"socket": "socket_R_Hand", "dir": RS_DIR}, **GRIP}

    # 收剑：原来上臂往后、前臂反关节 30°，剑尖朝下贴着右腿。手是从垂下来的大袖正中间伸出来的（Tripo 的袖口开在袖片中间），
    # 手放低时剑往哪边指都要穿过袖片或下摆（量出来右袖 26 个、下摆 36 个顶点在剑身 1.5 厘米内）。
    # 改成和起手 draw_ready 对称：剑竖在胸前、低头收势，剑身朝上离袖子、下摆都远；9.8 秒剑消失时回站姿
    poses["recover"] = {"base": "draw_ready", "Spine01": {"pitch": 2}, "Spine02": {"pitch": 3}, "Head": {"pitch": 10}}

    # 余摆、蓄力的几个姿势（10-31 第二版，用户："整个动作有点怪异，不是很自然流畅"）
    poses["draw_ready_b"] = {"base": "draw_ready", "Spine01": {"pitch": -3}, "Spine02": {"pitch": -2}, "Head": {"pitch": -7}}   # 握剑时慢慢抬头、挺胸，接妖化
    poses["awaken_over"] = {"base": "awaken", "Spine01": {"pitch": -8}, "Spine02": {"pitch": -11}, "Head": {"pitch": -14},
        "R_Upperarm": {"pitch": -12, "roll": -58}, "L_Upperarm": {"pitch": -12, "roll": 68}}   # 妖化那一下两臂甩得比定住时更开，再收回来
    poses["slash_wind_deep"] = {**poses["slash_wind"], "Spine01": {"yaw": -33, "pitch": -3}, "Spine02": {"yaw": -14}, "Head": {"yaw": 19}}   # 蓄势越拧越紧
    poses["slash_over"] = {**poses["slash"], "Spine01": {"yaw": 19, "pitch": 8}, "Spine02": {"yaw": 11, "pitch": 2},
        "aim": {"socket": "socket_R_Hand", "dir": [0.92, 0.36, -0.12]}}                    # 斩过头一点再回到定住的位置
    poses["slash_hold"] = {**poses["slash"], "Spine01": {"yaw": 13, "pitch": 8}, "Head": {"yaw": -12, "pitch": -1}}   # 定住时慢慢沉一点

    # 关键姿势的时间（帧）。剑和右手按这个时间到位（音效、红线的节奏点不变）；身体比手早、左手比右手晚，见 LEAD
    KEYS = [["draw_ready", 30], ["draw_ready_b", 62], ["draw_ready_b", 66], ["awaken_over", 78], ["awaken", 86], ["awaken", 100],
            ["slash_wind", 110], ["slash_wind_deep", 118], ["slash_step", 121], ["slash", 123], ["slash_over", 126], ["slash", 133],
            ["slash_hold", 165], ["recover_step", 177], ["recover", 190], ["recover", 220]]
    frames = bake(lib, KEYS, 30, 220, 2)
    for k in [k for k in poses if k.startswith("exo_")]: del poses[k]   # 上一次烘的
    poses.update(frames)
    lib["animations"]["exorcise_k"] = {"fps": 24, "keys": [["stand", 0]] + [[n, int(n[4:])] for n in frames] + [["stand", 250]]}
    lib["morphs"]["exorcise_k"] = morphs()
    sw = lib["props"]["sword"]["poses"]
    for n in ("slash_step", "recover_step"):
        if n not in sw: sw.append(n)
    LIB.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写回 {LIB.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
