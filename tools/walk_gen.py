"""
按步态参数用两节腿 IK 算走路，逐帧写进姿势库（tools/poses/kusuriuri_v2.json），不用手调腿的角度。

  python3 tools/walk_gen.py walk2_k                 # 正常走：一步 0.58 米，1.17 秒两步，1.0 米/秒
  python3 tools/walk_gen.py walk_fast_k --fast      # 快走（Shift）
  python3 tools/walk_gen.py run_k --run             # 跑
  python3 tools/walk_gen.py walk_k --char tokuji --npc-m   # 配角男，步子大一点
  python3 tools/walk_gen.py walk_k --char asa --npc  # 配角小碎步（腿的尺寸先用 tools/rig_legs.py 量好放 tools/npc_poses/<角色>_legs.json）
  然后照常跑 blender_pose_anim.py 重建，再用 tools/walk_measure.py 量。

思路：支撑脚（贴地那只）在角色坐标里从髋前 F 米匀速退到髋后 B 米，查看器 / 游戏里身体按同样速度往前走，脚就钉在地上不滑；
后半段脚跟抬起（脚尖还在地上），摆动脚走一条抬高 lift 的弧线到下一个落点。髋的高度随步态起伏（单脚支撑时最高）。
每帧给出脚踝相对髋关节的前后、上下位置，解出大腿和小腿的绝对角度，再减掉绑定姿势里的角度，就是姿势库里的 pitch。
腿骨尺寸（1.7 米身高）见 LEG，左右腿绑定姿势的后斜角不一样（右大腿 7.6°、左 3.5°），不分开算右脚会陷进地里 1.5 厘米；
髋关节高 0.972、脚踝高 0.017（tools/walk_measure.py 量的）。pitch 正值 = 远端往后（朝下的骨头），脚的 pitch 正值 = 脚尖往下。
姿势名 <动作名去掉 _k>_00、_01……（生成的，别手改），动作每帧一个关键帧，帧间插值误差可以忽略。
"""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSES = ROOT / "tools/poses/kusuriuri_v2.json"
# 下面这几个写死的数是 10-30 第一版用的，10-31 起运行时都被 use_char() 从 tools/poses/kusuriuri_legs.json 覆盖（只留作默认值）
UNIT = 1.715                       # 1 模型单位 = 1.715 米（全身包围盒高 1.0）
# 每条腿：大腿、小腿侧面投影长度（米），绑定姿势里大腿、小腿往后斜的角度（度）。左右不对称（Tripo 绑的骨架），分开算
LEG = {"L": (0.3859, 0.5701, 3.46, 4.01), "R": (0.3846, 0.5750, 7.56, 4.30)}
T_LEN, C_LEN = 0.3846, 0.5701       # 算髋高度上限用短的那条
HIP_Z, ANKLE_Z = 0.972, 0.017      # 绑定姿势髋关节、脚踝离地高度
REST_DN = HIP_Z - ANKLE_Z
FOOT = 0.12                        # 脚踝到脚掌着地点的距离（算脚跟抬起时脚转多少度）

# 下摆骨链（tools/blender_layers.py 生成，12 条挂在 Pelvis 上，每条 3 节：髋→膝、膝→小腿、小腿→地）跟着腿主动摆：
# (左腿权重, 右腿权重, 前片)。前片跟同侧大腿 50~70%，正中那条取更靠前的那条腿；侧片 30%；后片 10~20%。
# 根部方位按绑定姿势量的（x 往左、y 往后，髋中心 x=0.01）：01~05 在前，00 右侧、06 左侧，07~11 在后。
HEM = {0: (0, 0.3, False), 1: (0, 0.7, True), 2: (0.15, 0.6, True), 3: (0.6, 0.6, True), 4: (0.6, 0.15, True), 5: (0.7, 0, True),
       6: (0.3, 0, False), 7: (0.18, 0, False), 8: (0.15, 0.05, False), 9: (0.1, 0.1, False), 10: (0.05, 0.15, False), 11: (0, 0.18, False)}

GAITS = {
    # frames：一个循环（两步）几帧，24 帧/秒；stance：一只脚贴地占循环的比例；F/B：支撑期脚踝从髋前 F 退到髋后 B（米）
    # lift：摆动脚最高抬多少；heel：离地前脚跟抬多高；hip_hi：髋到脚踝竖直距离的上限（单脚支撑时，膝盖微弯）
    # 上身（10-31 用户说"太机械"重做）：pelvis_yaw / pelvis_roll 骨盆扭转、侧倾（度），sway 髋往支撑脚挪（米），
    # spine_yaw 肩膀反扭（两节脊柱合计），lean 前倾，nod 点头，tilt 常带的歪头（度）；arm_L / arm_R 上臂前后摆幅（故意不对称），
    # fore 前臂往前摆时多弯；lag_* 比腿晚几帧；foot_half 脚踝离中线多远（米，绑定姿势是 A 字站，不收就岔着腿走）；hand：手的缩放（< 1 = 手缩进袖子里，走路时袖口不露手）
    "walk": dict(frames=30, stance=0.6, F=0.26, B=0.47, lift=0.10, heel=0.06, hip_hi=0.946, hand=0.05,
                 pelvis_yaw=5.5, pelvis_roll=3.0, sway=0.015, spine_yaw=5.0, lean=2.5, nod=1.0, tilt=2.5,
                 arm_L=12, arm_R=9, fore=10, lag_spine=2, lag_head=3, lag_arm=3, foot_half=0.07),
    "fast": dict(frames=18, stance=0.55, F=0.24, B=0.50, lift=0.11, heel=0.10, hip_hi=0.940, hand=0.05, swing_k=1.2,
                 pelvis_yaw=7.0, pelvis_roll=3.0, sway=0.012, spine_yaw=6.0, lean=5.0, nod=1.2, tilt=2.0,
                 arm_L=17, arm_R=14, fore=12, lag_spine=1, lag_head=2, lag_arm=2, foot_half=0.065),
    # 跑（10-31 用户要的"加速 / 冲刺"）：stance < 0.5，两只脚都离地的腾空段；手肘常弯 elbow，前倾更多
    # 10-31 第二版（用户："左前脚太靠前，别扭；跑起来不优雅、不帅"）：落脚在髋下面（F 小），往后蹬得长（B 大）；
    # 摆动腿先把小腿折到身后（swing_k、lift_k）再往前送，不从下摆里往前踢；身体从腰起整体前倾 waist_lean，下巴放平（chin）；
    # 骨盆、上身几乎不左右倾，头完全稳住（head_counter 1 = 完全抵掉肩膀扭转）；手臂收在身侧略往后（arm_back）只小摆；
    # 下摆整体往后拖 hem_trail（迎风）；髋几乎不上下颠（hip_hi 压低、腾空短），是往前滑不是往上蹦
    "run": dict(frames=14, stance=0.42, F=0.18, B=0.52, lift=0.30, heel=0.10, hip_hi=0.915, hand=0.05,
                swing_k=1.6, lift_k=0.7, waist_lean=10.0, chin=0.9, head_counter=1.0, arm_back=8, hem_trail=6,
                pelvis_yaw=5.0, pelvis_roll=1.0, sway=0.004, spine_yaw=4.0, lean=0.0, nod=0.0, tilt=0.0,
                arm_L=6, arm_R=5, fore=4, elbow=12, lag_spine=1, lag_head=1, lag_arm=2, foot_half=0.05),
    # 配角女中小碎步（10-31 游15）：和服下摆窄，步子小、脚抬得低、两脚几乎一条线；手照站姿拢在身前（摆臂只给一点），手不缩
    # hip_hi=None：按这个角色的腿长自动取（腿长 × 0.99，hip_frac 可改）
    "npc": dict(frames=22, stance=0.62, F=0.15, B=0.22, lift=0.045, heel=0.025, hip_hi=None, hand=1.0,
                pelvis_yaw=3.0, pelvis_roll=2.0, sway=0.010, spine_yaw=2.5, lean=1.0, nod=0.6, tilt=1.5,
                arm_L=2, arm_R=2, fore=0, lag_spine=2, lag_head=3, lag_arm=3, foot_half=0.04),
    # 配角男（游14 徳次、小田島）：步子比女中大一点，手垂在身侧小摆
    "npc_m": dict(frames=26, stance=0.6, F=0.20, B=0.36, lift=0.07, heel=0.04, hip_hi=None, hand=1.0,
                  pelvis_yaw=4.0, pelvis_roll=2.5, sway=0.012, spine_yaw=3.5, lean=1.5, nod=0.8, tilt=1.0,
                  arm_L=7, arm_R=6, fore=4, lag_spine=2, lag_head=3, lag_arm=3, foot_half=0.06),
}
CHAR, MERGE = "kusuriuri", False   # MERGE：上身的角度叠加在这个角色站姿的角度上（配角的站姿手臂有 yaw / local 扭，不能覆盖）


LEG3D = None   # 腿的三维长度（大腿、小腿，米）；use_char 读进来


def use_char(name):
    """换角色：腿的尺寸从 tools/rig_legs.py 量好的 json 读（药郎 tools/poses/kusuriuri_legs.json，配角 tools/npc_poses/<名字>_legs.json）。
    10-31 起药郎也读量出来的数：原来写死的是按走路第一帧量的（换算 1.715，游戏里按绑定姿势是 1.700），而且腿长用的是侧面投影"""
    global CHAR, MERGE, POSES, UNIT, LEG, LEG3D, T_LEN, C_LEN, HIP_Z, ANKLE_Z, REST_DN, FOOT, HEM, HIP_HALF, ANKLE_REST
    if name == "kusuriuri":
        d = json.loads((ROOT / "tools/poses/kusuriuri_legs.json").read_text())
    else:
        d = json.loads((ROOT / f"tools/npc_poses/{name}_legs.json").read_text())
        CHAR, MERGE = name, True
        POSES = ROOT / f"tools/npc_poses/{name}.json"; HEM = {}
    UNIT = d["unit"]; LEG = {s: tuple(v) for s, v in d["leg"].items()}
    # 三维长度：A 字站姿的腿往外斜，侧面投影比真腿短。走路时腿收到接近竖直，用投影长度算会让脚踝落得比算的低，
    # 闭环修正只好让膝盖多弯去补，整个支撑期膝盖都弯着 25°~33°，像半蹲（10-31 用户看小田島："很奇怪"）
    LEG3D = {s: tuple(v) for s, v in d.get("leg3d", {k: v[:2] for k, v in d["leg"].items()}).items()}
    # 按总长较短的那一整条腿算够得着的范围。原来大腿、小腿各取较短的，Tripo 骨架左右比例不一样时拼出来比哪条腿都短，
    # 髋被压低、膝盖一直弯着，走路像半蹲（10-31 用户看小田島："很奇怪"：短了 4 厘米，髋低 6~10 厘米）
    sh = min("LR", key=lambda s_: LEG3D[s_][0] + LEG3D[s_][1]); T_LEN, C_LEN = LEG3D[sh]
    HIP_Z, ANKLE_Z = d["hip_z"], d["ankle_z"]; REST_DN = HIP_Z - ANKLE_Z
    FOOT = 0.12 * d["height"] / 1.7
    HIP_HALF = dict(d["hip_half"]); ANKLE_REST = dict(d["ankle_rest"])


def smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def foot_at(u, g):
    """单只脚在自己的相位 u（0 = 脚跟着地）时：脚踝前后位置（米，相对髋关节，前为正）、离地高度、脚尖往下的角度（度）"""
    st = g["stance"]
    if u < st:
        s = u / st
        fwd = g["F"] - (g["F"] + g["B"]) * s
        h = g["heel"] * smooth((s - 0.6) / 0.4)
        toe = math.degrees(math.asin(min(h / FOOT, 0.9)))
        if s < 0.15: toe -= 10 * (1 - s / 0.15)          # 刚落地脚尖还翘着，0.15 之内放平
        return fwd, h, toe
    s = (u - st) / (1 - st)
    # 摆动脚在地面上看是从起点平滑地挪到落点（离地、落地那一刻对地速度都是 0），换回相对髋的坐标要减掉身体走过的距离。
    # 这样离地时相对髋的速度正好接上支撑期的 -v，落地时对地不蹭
    v = (g["F"] + g["B"]) / g["stance"]                         # 每个循环相位单位走多少米（相对髋）
    tsw = 1 - st
    # swing_k > 1：摆动脚在后面多留一会儿（小腿折到身后），最后才往前送到落点，不往前甩；lift_k < 1：抬得最高的时刻提前（脚跟收在臀下）
    fwd = -g["B"] + ((g["F"] + g["B"]) + v * tsw) * smooth(s ** g.get("swing_k", 1.0)) - v * tsw * s
    h = g["heel"] * (1 - s) ** 2 + g["lift"] * math.sin(math.pi * s ** g.get("lift_k", 1.0)) ** 1.3   # 正好在摆动结束时落地
    toe0 = math.degrees(math.asin(min(g["heel"] / FOOT, 0.9)))
    toe = toe0 * (1 - s) ** 2 - 10 * s ** 2                # 离地时脚尖朝下，落地前翘起 10°
    return fwd, h, toe


WORLD = "noworld" not in sys.argv
HIP_HALF = {"L": 0.0907, "R": 0.0921}   # 髋关节离骨盆中心的左右距离（米），骨盆转动时髋关节被带着走


def pelvis_at(ph, g):
    """骨盆这一相位的扭转、侧倾（度）和髋往两边挪的距离（米）。左脚着地（ph = 0）时左脚最靠前：
    扭转 = 前腿那侧往前（左侧往前 = 往右转 = yaw 负）；侧倾在对侧脚着地后不久最大，摆动腿那侧往下沉
    （ph ≈ 0.12 右腿刚离地，右侧沉 = 左侧高 = roll 正）；髋挪向支撑脚，左脚支撑期中点 stance/2 时最靠左"""
    return {"yaw": -g["pelvis_yaw"] * math.cos(2 * math.pi * ph),
            "roll": g["pelvis_roll"] * math.cos(2 * math.pi * (ph - 0.12)),
            "sway_m": g["sway"] * math.cos(2 * math.pi * (ph - g["stance"] / 2)), "foot_half": g["foot_half"]}


def hip_shift(side, pv):
    """骨盆转了以后这一侧髋关节往前挪多少、往上挪多少（米）。yaw 正 = 往左转：左髋往后、右髋往前；roll 正：左髋高、右髋低"""
    d = HIP_HALF[side]; sg = 1 if side == "L" else -1
    return -sg * d * math.sin(math.radians(pv["yaw"])), sg * d * math.sin(math.radians(pv["roll"]))


# 脚踝左右位置：绑定姿势是 A 字站，两个脚踝隔 39 厘米，走路照这个宽度就是岔着腿走。走路时脚踝落在离中线 foot_half 米处
# （正常人走路两脚内侧几乎在一条线上）。大腿 roll 把脚踝挪过去，同时抵掉髋往两边晃，支撑脚左右不动。
ANKLE_REST = {"L": 0.0899, "R": -0.1171}   # 绑定姿势脚踝在髋关节外侧多少（米，左为正；左右不对称，Tripo 的骨架）


def leg_want(side, pv):
    """脚踝此刻该在髋关节左右哪边、多远（米，左为正）：落在离中线 foot_half 处，减掉髋的左右晃"""
    sg = 1 if side == "L" else -1
    return sg * pv["foot_half"] - (sg * HIP_HALF[side] + pv["sway_m"])


def leg_roll(side, pv, dn):
    """这条腿的 roll（度，正 = 远端往角色左边）：脚踝从绑定位置挪到 leg_want"""
    return math.degrees(math.asin(max(-0.5, min(0.5, (leg_want(side, pv) - ANKLE_REST[side]) / dn))))


FIX_DIR = ROOT / "tools/poses"


def load_fix(name):
    """闭环修正表 tools/poses/walk_fix_<动作名>.json：{帧: {L_side, R_side, L_up, R_up}}（米）。
    骨盆扭转、侧倾和腿内收这几样转动叠在一起，用几何近似算不准到毫米，所以拿 Blender 实测的误差逐帧补回来"""
    f = fix_path(name)
    return json.loads(f.read_text()) if f.exists() else {}


def fix_path(name):
    return FIX_DIR / (f"walk_fix_{name}.json" if CHAR == "kusuriuri" else f"walk_fix_{CHAR}_{name}.json")


def learn(name, csv_path, g):
    """读 tools/walk_measure.py --csv 的逐帧结果，把支撑期脚踝的左右偏差、高度偏差累加进修正表。
    每一帧都补（按步态相位知道这一帧脚该在哪，不靠"离地多高"去猜支撑期）：高度对准绑定姿势脚踝高度加这一帧设计的抬起量，
    左右对准这只脚支撑期的平均位置"""
    import csv
    rows = list(csv.DictReader(open(csv_path)))
    N = g["frames"]; fix = load_fix(name)
    href = float(rows[0]["rest_ankle"])
    for side, off in (("L", 0.0), ("R", 0.5)):
        st = [i for i in range(N) if (i / N - off) % 1.0 < g["stance"]]
        mid = sum(float(rows[i][side + "_side"]) for i in st) / len(st)
        for i in range(N):   # 每一帧都补：高度对准"绑定脚踝高 + 这一帧设计的抬起量"，左右对准支撑期平均（摆动时脚走直线）
            h = foot_at((i / N - off) % 1.0, g)[1]
            e = fix.setdefault(str(i), {})
            e[side + "_side"] = round(e.get(side + "_side", 0.0) + float(rows[i][side + "_side"]) - mid, 5)
            e[side + "_up"] = round(e.get(side + "_up", 0.0) + float(rows[i][side + "_up"]) - (href + h), 5)
    fix_path(name).write_text(json.dumps(fix, indent=1))
    print(f"修正表更新：{len(fix)} 帧")


def leg_ik(fwd, dn, T_LEN, C_LEN):
    """脚踝在髋关节前 fwd 米、下 dn 米：返回大腿、小腿的绝对后斜角（度），以及是否够不着（被夹住）"""
    D = math.hypot(fwd, dn); reach = (T_LEN + C_LEN) * 0.998
    clamped = D > reach
    D = min(D, reach)
    cb = (D * D - T_LEN ** 2 - C_LEN ** 2) / (2 * T_LEN * C_LEN)
    b = math.acos(max(-1.0, min(1.0, cb)))                  # 膝盖弯曲（小腿相对大腿往后转），≥ 0
    line = math.atan2(-fwd, dn)                             # 髋→脚踝连线的后斜角
    alpha = math.asin(C_LEN * math.sin(b) / D)              # 大腿比连线往前多少（膝盖朝前）
    a = line - alpha
    return math.degrees(a), math.degrees(a + b), clamped


def build(name, g):
    global STAND
    lib = json.loads(POSES.read_text(encoding="utf-8"))["poses"]
    def resolve(n):
        d = dict(lib[n]); b = d.pop("base", None); out = resolve(b) if b else {}; out.update(d); return out
    STAND = resolve("stand")
    N = g["frames"]; prefix = name[:-2] if name.endswith("_k") else name
    poses, keys, report = {}, [], []
    # 髋的高度：每帧取两条腿都够得着的最高点（留 0.6% 余量，膝盖不完全绷直），不超过 hip_hi，再循环平滑三遍；
    # 平滑会把个别帧抬高，所以每遍之后再压回够得着的范围
    reach = {s_: (LEG3D[s_][0] + LEG3D[s_][1]) * 0.992 for s_ in "LR"}
    # 配角：髋高上限 = 腿长 × 0.99，单脚支撑时膝盖弯十几度（原来 0.975，膝盖一直弯 28° 左右，像半蹲）
    if g.get("hip_hi") is None: g["hip_hi"] = (T_LEN + C_LEN) * g.get("hip_frac", 0.99)
    cap = []
    for i in range(N):
        lim = g["hip_hi"]
        pv = pelvis_at(i / N, g)
        for side, off in (("L", 0.0), ("R", 0.5)):
            fwd, h, _ = foot_at((i / N - off) % 1.0, g)
            dfwd, dz = hip_shift(side, pv)
            # 三维距离：髋关节到脚踝 = 前后、上下、左右三个分量，腿够得着的竖直距离要扣掉前后和左右
            lim = min(lim, math.sqrt(max(reach[side] ** 2 - (fwd - dfwd) ** 2 - leg_want(side, pv) ** 2, 0)) + h - dz)
        cap.append(lim)
    hip = cap[:]
    for _ in range(3):
        hip = [min(cap[i], (hip[i - 1] + 2 * hip[i] + hip[(i + 1) % N]) / 4) for i in range(N)]
    print(f"  髋到脚踝竖直距离 {min(hip):.3f}~{max(hip):.3f}（上下起伏 {100 * (max(hip) - min(hip)):.1f} 厘米）")
    fix = load_fix(name)
    bob_lo, bob_hi = min(hip), max(hip)
    bobn = [(2 * (x - bob_lo) / max(bob_hi - bob_lo, 1e-6)) - 1 for x in hip]   # 髋上下归一到 -1..1（1 = 最高）
    for i in range(N):
        ph = i / N
        hip_dn = hip[i]
        pv = pelvis_at(ph, g)
        pose = {"base": "stand"}
        for side, off in (("L", 0.0), ("R", 0.5)):
            u = (ph - off) % 1.0
            fwd, h, toe = foot_at(u, g)
            # 骨盆扭转、侧倾把这一侧髋关节带前带后、带高带低，IK 用挪过之后的髋关节算，脚在地上的位置不变
            dfwd, dz = hip_shift(side, pv)
            fx = fix.get(str(i), {})
            pv = dict(pv, foot_half=pv["foot_half"] - (1 if side == "L" else -1) * fx.get(side + "_side", 0.0))
            dz += fx.get(side + "_up", 0.0)          # 实测脚踝偏高就让腿再伸长一点（dn 变大）
            tl, cl, a0, c0 = LEG[side]
            # 腿往里收（leg_roll）以后竖直方向短了一点，IK 用侧面投影上该有的长度
            tl, cl = LEG3D[side]
            a, c, clamped = leg_ik(fwd - dfwd, math.hypot(hip_dn + dz - h, leg_want(side, pv)), tl, cl)
            pt = a - a0; pc = c - c0 - pt
            # world：大腿朝向不跟骨盆转（只跟它走位置），roll 抵掉髋往两边晃，支撑脚不左右蹭
            pose[f"{side}_Thigh"] = {"world": WORLD, "pitch": round(pt, 2), "roll": round(leg_roll(side, pv, hip_dn - h), 2)}
            pose[f"{side}_Calf"] = {"pitch": round(pc, 2)}
            pose[f"{side}_Foot"] = {"pitch": round(-(pt + pc) + toe, 2)}
            if clamped: report.append(f"帧 {i} {side} 够不着（前 {fwd:.2f} 下 {hip_dn - h:.3f}）")
        # 上身连带（都按相位算，"晚几帧"就是相位往后挪）：
        #   骨盆：前腿那侧往前扭、摆动腿那侧往下沉，整个髋往支撑脚那边挪、上下起伏（起伏来自上面腿够得着的高度）
        #   上身：两节脊柱合起来反着骨盆扭、比骨盆晚 lag_spine 帧，侧倾也反着骨盆一半；整体往前倾 lean
        #   头：几乎抵掉肩膀的扭转（脸朝前），点头比上下起伏晚 lag_head 帧，常带一点歪头
        #   手臂：和同侧腿反向摆、比腿晚 lag_arm 帧，前臂往前摆时多弯一点、再晚 2 帧；锁骨跟着起落；左右幅度不一样
        lag = lambda f: 2 * math.pi * (ph - f / N)
        sh = g["spine_yaw"] * math.cos(lag(g["lag_spine"]))                       # 肩膀扭转（正 = 往左转）
        sr = -0.5 * g["pelvis_roll"] * math.cos(lag(g["lag_spine"]) - 2 * math.pi * 0.12)
        pose["Hip"] = {"move": [round(pv["sway_m"] / UNIT, 4), 0, round((hip_dn - REST_DN) / UNIT, 4)]}
        pose["Pelvis"] = {"yaw": round(pv["yaw"], 2), "roll": round(pv["roll"], 2)}
        if g.get("waist_lean"): pose["Waist"] = {"pitch": g["waist_lean"]}           # 从腰起整个上身一起前倾，不是弯脊柱
        pose["Spine01"] = {"pitch": round(g["lean"] * 0.6, 2), "yaw": round(sh * 0.5, 2), "roll": round(sr * 0.5, 2)}
        pose["Spine02"] = {"pitch": round(g["lean"] * 0.4, 2), "yaw": round(sh * 0.5, 2), "roll": round(sr * 0.5, 2)}
        hb = bobn[(i - g["lag_head"]) % N]
        pose["Head"] = {"pitch": round(2 - g["lean"] * 0.5 - g.get("waist_lean", 0) * g.get("chin", 0) - g["nod"] * hb, 2),
                        "yaw": round(-g.get("head_counter", 0.7) * sh, 2), "roll": round(g["tilt"] - 0.5 * sr, 2)}
        ca = math.cos(lag(g["lag_arm"]))                                           # 左臂：+1 = 最往后（左脚最靠前时晚几帧）
        cf = math.cos(lag(g["lag_arm"] + 2))
        ab = g.get("arm_back", 0)                                                  # 手臂整体往后收一点（跑：收在身侧）
        pose["L_Upperarm"] = {"pitch": round(ab + g["arm_L"] * ca, 2), "roll": 3}
        pose["R_Upperarm"] = {"pitch": round(ab - g["arm_R"] * ca, 2), "roll": -3}
        el = g.get("elbow", 0)                                                     # 跑步时手肘常弯
        pose["L_Forearm"] = {"pitch": round(-el - g["fore"] * max(0.0, -cf), 2)}
        pose["R_Forearm"] = {"pitch": round(-75 - el - g["fore"] * max(0.0, cf), 2)}   # 右前臂站姿本来就是 -75（抵掉 bind_fix）
        pose["L_Clavicle"] = {"roll": round(2 * ca, 2)}                            # 左臂往前摆时左肩抬（roll 负 = 抬）
        pose["R_Clavicle"] = {"roll": round(2 * ca, 2)}                            # 右臂往前摆（ca = +1）时右肩抬（roll 正 = 抬）
        if g["hand"] != 1.0: pose["L_Hand"] = {"scale": g["hand"]}; pose["R_Hand"] = {"scale": g["hand"]}
        if MERGE:   # 配角：上面算的是相对站姿的增量，叠到站姿原有的角度上（站姿的 yaw、local 扭之类原样保留）
            pose["R_Forearm"]["pitch"] = round(pose["R_Forearm"]["pitch"] + 75, 2)   # 上面那个 -75 是药郎骨架的，配角没有
            for b in ("Spine01", "Spine02", "Head", "L_Upperarm", "R_Upperarm", "L_Forearm", "R_Forearm", "L_Clavicle", "R_Clavicle"):
                base = dict(STAND.get(b, {}))
                for k in ("pitch", "roll", "yaw"):
                    if k in pose[b] or k in base: base[k] = round(base.get(k, 0) + pose[b].get(k, 0), 2)
                pose[b] = base
        # 下摆：第 1 节（髋→膝）按大腿角度乘权重前后摆，越往下摆幅越大是绕髋转自然带出来的；
        # 前片在膝盖往前顶、膝盖弯的时候，下面两节往回收一点，布在膝盖那里鼓成一个弧。查看器 / 游戏里弹簧骨叠在这上面只做余摆
        th = {s: pose[f"{s}_Thigh"]["pitch"] for s in "LR"}
        kn = {s: pose[f"{s}_Calf"]["pitch"] for s in "LR"}   # 膝盖弯曲（正值 = 小腿往后）
        for k, (wl, wr, front) in HEM.items():
            if front and wl and wr:   # 正中前片：哪条腿在前跟哪条
                s0 = "L" if th["L"] < th["R"] else "R"; a = (wl if s0 == "L" else wr) * th[s0]; knee = kn[s0] * (wl if s0 == "L" else wr)
            else:
                a = wl * th["L"] + wr * th["R"]; knee = wl * kn["L"] + wr * kn["R"]
            push = max(0.0, -a) if front else 0.0                  # 前片被膝盖往前顶的量
            pose[f"chain_hem_{k:02d}_0"] = {"pitch": round(a + g.get("hem_trail", 0), 2)}
            pose[f"chain_hem_{k:02d}_1"] = {"pitch": round(0.45 * knee + 0.25 * push, 2) if front else round(0.3 * knee, 2)}
            pose[f"chain_hem_{k:02d}_2"] = {"pitch": round(0.15 * knee, 2)}
        pn = f"{prefix}_{i:02d}"; poses[pn] = pose; keys.append([pn, i])
    keys.append([f"{prefix}_00", N])
    T = N / 24; v = (g["F"] + g["B"]) / (g["stance"] * T)
    print(f"{name}: {N} 帧 = {T:.3f} 秒两步，设计速度 {v:.3f} 米/秒，步幅 {v * T / 2:.3f} 米，抬脚 {g['lift']} 米")
    for r in report: print("  ", r)
    return poses, {"fps": 24, "keys": keys}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "walk2_k"
    use_char(sys.argv[sys.argv.index("--char") + 1] if "--char" in sys.argv else "kusuriuri")
    g = dict(GAITS["npc_m" if "--npc-m" in sys.argv else "npc" if "--npc" in sys.argv else "run" if "--run" in sys.argv else "fast" if "--fast" in sys.argv else "walk"])
    if "--learn" in sys.argv:   # python3 tools/walk_gen.py walk2_k [--fast/--run] --learn 量出来的.csv（再跑一遍生成）
        learn(name, sys.argv[sys.argv.index("--learn") + 1], g); sys.exit()
    for kv in [x for x in sys.argv if "=" in x and not x.startswith("--")]:   # 调参试验：python3 tools/walk_gen.py walk2_k pelvis_roll=0 sway=0
        k, v = kv.split("=", 1); g[k] = float(v) if "." in v else int(v)
    raw = POSES.read_text(encoding="utf-8"); d = json.loads(raw)
    prefix = name[:-2] if name.endswith("_k") else name
    for k in [k for k in d["poses"] if k.startswith(prefix + "_") and k[len(prefix) + 1:].isdigit()]: del d["poses"][k]
    poses, anim = build(name, g)
    d["poses"].update(poses); d["animations"][name] = anim
    POSES.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
