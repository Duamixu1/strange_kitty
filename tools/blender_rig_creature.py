"""
物怪（docs/18）里不是人形的：四条腿的化猫 bakeneko、火鼠 hinezumi、鵺 nue（共用一套四足骨架，骨头位置按各自的比例配，见 QUAD），
一条腿的唐伞 karakasa，没有腿的海坊主 umibozu（和唐伞一样按高度分节）。Tripo 的自动绑骨只认人形，
这里自己搭骨架、按离骨头的距离刷权重、按 MOTIONS 打关键帧，导出带动作的 GLB。

  Blender -b --python tools/blender_rig_creature.py -- --kind bakeneko --in assets/processed/bakeneko_lite.glb \
      --out assets/processed/bakeneko_posed.glb [--render 目录]

动作名（三只物怪一样，代码按名字播）：idle_k 飘着待机（循环）、appear_k 从墨里浮出来、charge_k 蓄力、lunge_k 扑、
hit_k 被札钉中、vanish_k 消散（化墨由代码做，这里只做最后那一下的姿势）。
化猫另有三段小化猫群用的待机（循环，都是站着）：idle_curious_k 好奇歪头、idle_groom_k 回头舔肩背、idle_sit_k 压低身子夹着尾巴（名字沿用，早先是坐着）。

角度写法和姿势库一样在角色坐标里：pitch 绕左右轴（正 = 骨头远端往前，朝上的骨头就是往前低）、yaw 绕上下轴（正 = 往角色左边）、
roll 绕前后轴（正 = 远端往角色左边倒）；move = [左, 前, 上]，米；scale = [左右, 前后, 上下] 只给唐伞的伞面用。
Blender 里角色朝 -Y（和药郎一样），所以左 = +X，前 = -Y。
"""
import argparse, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--kind", choices=["bakeneko", "hinezumi", "nue", "karakasa", "umibozu"], required=True)
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out")
ap.add_argument("--render")
a = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
mesh = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
mesh.name = a.kind; mesh.data.name = a.kind
# Tripo 出来脸朝 +X（转一圈渲染确认过），转成朝 -Y
mesh.matrix_world = Matrix.Rotation(math.radians(-90), 4, "Z") @ mesh.matrix_world
bpy.context.view_layer.objects.active = mesh; mesh.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
P = np.array([tuple(v.co) for v in mesh.data.vertices])
lo, hi = P.min(0), P.max(0); H = hi[2] - lo[2]
LEFT, FRONT, UP = Vector((1, 0, 0)), Vector((0, -1, 0)), Vector((0, 0, 1))
print(f"[creature] {a.kind}: {len(P)} 顶点，高 {H:.2f}，前后 {lo[1]:.2f}..{hi[1]:.2f}")


def V(left, front, up): return Vector((left, -front, up))


# ---- 骨架：(名字, 父, 头, 尾)，坐标 [左, 前, 上]（米） ----
ny, ty = -lo[1], -hi[1]                                                   # 最前（鼻尖）、最后
# 四足：脊柱各点 (前, 高)，“前”按鼻尖 ny、尾端 ty 算；腿根高度、膝盖高度；尾巴一串点（化猫往上翘、火鼠往后垂到地、鵺是一条往上盘的蛇）；
# crest 背上的火冠（只有火鼠，蓄力时往上窜）。数值按各自的侧面轮廓量的（docs/18 第九节）
QUAD = {
    # 化猫这只模型身子是斜着的：屁股偏左 10 厘米、胸口偏右 5 厘米、头偏右 10 厘米，尾巴根偏左 19 厘米（第四版按切片量的，
    # 第一到三版骨头全在正中线上，尾巴中间三节几乎没带上肉、头被耳朵骨头抢走）。点写成 (前, 高, 左)
    "bakeneko": dict(hips=[(-0.27, 0.62, 0.09), (-0.04, 0.64, 0.01)], spine=(0.17, 0.66, -0.05), neck=(0.21, 0.79, -0.10), head=(0.30, 1.0, -0.10),
                     legF=(0.56, 0.3), legB=(0.56, 0.3), feet_back=None,
                     tail=[(-0.36, 0.66, 0.19), (-0.34, 0.80, 0.17), (-0.24, 0.90, 0.11), (-0.20, 1.02, 0.08), (-0.25, 1.12, 0.14), (-0.33, 1.10, 0.18)],
                     ears={"L": (-0.03, 0.29), "R": (-0.17, 0.25)}, ear_z=(0.955, 0.985), smooth=12),   # 耳尖的 (左右, 前后)，高 1.03；耳朵只带 0.955 米以上的顶点
    "hinezumi": dict(hips=[(-0.36, 0.5), (-0.12, 0.52)], spine=(0.26, 0.55), neck=(0.38, 0.52), head=(0.53, 0.46),
                     legF=(0.48, 0.25), legB=(0.45, 0.24), feet_back=-0.45,      # 尾巴尖拖在地上，找后爪时不算它
                     tail=[(-0.40, 0.58), (-0.48, 0.65), (-0.53, 0.52), (-0.53, 0.32), (-0.51, 0.15), (-0.5, 0.04)],
                     crest=[(0.1, 0.8), (0.12, 1.0)]),
    "nue": dict(hips=[(-0.42, 0.7), (-0.15, 0.72)], spine=(0.3, 0.75), neck=(0.42, 0.88), head=(0.56, 0.95),
                legF=(0.62, 0.32), legB=(0.6, 0.32), feet_back=None,
                tail=[(-0.45, 0.78), (-0.5, 0.9), (-0.44, 1.0), (-0.34, 1.08), (-0.3, 1.18), (-0.38, 1.27), (-0.5, 1.32)]),
}
if a.kind in QUAD:
    Q = QUAD[a.kind]
    # 前爪、后爪的位置从脚底那一圈顶点里找：按前后分两组，每组按左右再分
    feet = P[P[:, 2] < lo[2] + 0.06]
    if Q["feet_back"] is not None: feet = feet[-feet[:, 1] > Q["feet_back"]]
    cy = (feet[:, 1].min() + feet[:, 1].max()) / 2
    def foot(front, left):
        f = feet[(feet[:, 1] < cy) == front]; cx = np.median(f[:, 0]); f = f[(f[:, 0] > cx) == left]
        return float(np.median(f[:, 0])), float(-np.median(f[:, 1]))    # 左, 前
    J = lambda t: V(t[2] if len(t) > 2 else 0, t[0], t[1])   # (前, 高[, 左])
    BONES = [("root", None, V(0, 0, 0), V(0, 0, 0.1)),
             ("hips", "root", J(Q["hips"][0]), J(Q["hips"][1])),
             ("spine", "hips", J(Q["hips"][1]), J(Q["spine"])),
             ("neck", "spine", J(Q["spine"]), J(Q["neck"])),
             ("head", "neck", J(Q["neck"]), J(Q["head"]))]
    tail = [J(t) for t in Q["tail"]]; NT = len(tail) - 1
    for i in range(NT): BONES.append((f"tail{i}", "hips" if i == 0 else f"tail{i - 1}", tail[i], tail[i + 1]))
    if "crest" in Q: BONES.append(("crest", "spine", V(0, *Q["crest"][0]), V(0, *Q["crest"][1])))
    for side, (x, f) in Q.get("ears", {}).items(): BONES.append((f"ear{side}", "head", V(x, f - 0.02, 0.95), V(x, f, 1.03)))   # 耳根到耳尖，小猫待机时耳朵会转
    for side, sn in (("L", True), ("R", False)):
        for end, fr, par in (("F", True, "spine"), ("B", False, "hips")):
            x, f = foot(fr, sn); top, knee = Q["leg" + end]
            BONES += [(f"leg{end}{side}0", par, V(x, f, top), V(x, f, knee)), (f"leg{end}{side}1", f"leg{end}{side}0", V(x, f, knee), V(x, f, 0.02))]
elif a.kind == "umibozu":
    # 没有腿：浪头底座、身子三节、胸口、头，一根一根往上叠（权重按高度分，同唐伞）
    zs = [0.0, 0.45, 0.95, 1.4, 1.7, 2.2]; names = ["base", "body0", "body1", "chest", "head"]
    BONES = [("root", None, V(0, 0, 0), V(0, 0, 0.05))] + [(n, "root" if i == 0 else names[i - 1], V(0, 0, zs[i]), V(0, 0, zs[i + 1])) for i, n in enumerate(names)]
else:
    BONES = [("root", None, V(0, 0, 0), V(0, 0, 0.05)),
             ("leg", "root", V(0, 0, 0.05), V(0, 0, 0.42)),
             ("body0", "leg", V(0, 0, 0.42), V(0, 0, 0.72)),
             ("body1", "body0", V(0, 0, 0.72), V(0, 0, 1.0)),
             ("body2", "body1", V(0, 0, 1.0), V(0, 0, 1.3))]

arm_data = bpy.data.armatures.new(f"{a.kind}_rig"); arm = bpy.data.objects.new(f"{a.kind}_rig", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
for n, par, h, t in BONES:
    b = arm_data.edit_bones.new(n); b.head = h; b.tail = t
    if par: b.parent = arm_data.edit_bones[par]; b.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

# ---- 权重：每个顶点按离各骨头线段的距离，取最近的三根，越近越重；离最近那根远 4 厘米以上的不要 ----
segs = [(n, np.array(tuple(h)), np.array(tuple(t))) for n, _, h, t in BONES if n != "root"]
D = np.zeros((len(P), len(segs)))
for j, (n, h, t) in enumerate(segs):
    d = t - h; u = np.clip(((P - h) @ d) / (d @ d), 0, 1); D[:, j] = np.linalg.norm(P - (h + u[:, None] * d), axis=1)
names = [n for n, _, _ in segs]
Q = QUAD.get(a.kind, {})
if "ear_z" in Q:   # 耳朵骨头在头顶里面，按距离会把整个脑壳抢过去（第三版压耳朵时整张脸跟着歪）：只许它带耳朵那一截
    z0, z1 = Q["ear_z"]; ramp = np.clip((P[:, 2] - z0) / (z1 - z0), 0, 1)
    for e in ("earL", "earR"): D[ramp <= 0, names.index(e)] += 10
dmin = D.min(1, keepdims=True)
W = np.exp(-((D - dmin) / 0.03) ** 2) * (D - dmin < 0.08)
if "ear_z" in Q:
    for e in ("earL", "earR"): W[:, names.index(e)] *= ramp
if Q.get("smooth"):   # 身子到头这一串（屁股、背、脖子、头）的权重沿着网格边抹匀，转头时脖子跟着弯，不在一个关节处折
    E = np.array([tuple(e.vertices) for e in mesh.data.edges]); deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    cs = [names.index(n) for n in ("hips", "spine", "neck", "head")]; S0 = W[:, cs].sum(1)
    _, grp = np.unique(np.round(P / 1e-4).astype(np.int64), axis=0, return_inverse=True); grp = grp.ravel(); gn = np.bincount(grp)
    for _ in range(Q["smooth"]):   # 贴图接缝处同一个位置有好几个顶点、彼此没有边相连，每轮把它们拉成同一个值，不然接缝处裂出白线
        X = W[:, cs]; acc = np.zeros_like(X); np.add.at(acc, E[:, 0], X[E[:, 1]]); np.add.at(acc, E[:, 1], X[E[:, 0]])
        X = 0.5 * X + 0.5 * acc / np.maximum(deg, 1)[:, None]
        G = np.zeros((len(gn), len(cs))); np.add.at(G, grp, X); X = (G / gn[:, None])[grp]
        W[:, cs] = X * (S0 / np.maximum(X.sum(1), 1e-9))[:, None]
if a.kind in ("karakasa", "umibozu"):   # 伞面、海坊主的袍子很宽，离中轴的距离对每节都差不多，按高度分：每个顶点只跟高度上最近的两节
    zc = np.array([(h[2] + t[2]) / 2 for _, h, t in segs]); W = np.exp(-((P[:, 2:3] - zc[None, :]) / (0.14 if a.kind == "karakasa" else 0.24)) ** 2)
W /= W.sum(1, keepdims=True)
for j, (n, _, _) in enumerate(segs):
    g = mesh.vertex_groups.new(name=n); idx = np.nonzero(W[:, j] > 0.01)[0]
    for i in idx: g.add([int(i)], float(W[i, j]), "REPLACE")
mesh.parent = arm; md = mesh.modifiers.new("Armature", "ARMATURE"); md.object = arm

# ---- 动作 ----
FPS = 24
def wave(n, per, fn):   # 循环动作：每 4 帧一个关键帧，按函数算
    return {f: fn(2 * math.pi * f / per) for f in range(0, n + 1, 4)}
sin = math.sin
if a.kind in QUAD:
    snake = a.kind == "nue"   # 鵺的尾巴是蛇：摆得更大、扑的时候蛇头往前咬
    def tail_wave(ph, amp=12, up=0):
        k = 1.6 if snake else 1.0
        return {f"tail{i}": {"yaw": amp * k * sin(ph - i * 0.7), "pitch": up * (0.5 if snake else 1)} for i in range(NT)}
    MOTIONS = {
        "idle_k": wave(48, 48, lambda ph: {"root": {"move": [0, 0, 0.02 + 0.015 * sin(ph)]}, "spine": {"pitch": 1.5 * sin(ph)}, "head": {"pitch": -2 * sin(ph - 0.5), "roll": 4 * sin(ph * 0.5)},
                                           **tail_wave(ph)}),
        "appear_k": {0: {"root": {"move": [0, 0, -0.55]}, "head": {"pitch": 25}, **tail_wave(0, 0, 30)}, 16: {"root": {"move": [0, 0, 0.06]}, "head": {"pitch": -10}, **tail_wave(1, 8)},
                     24: {"root": {"move": [0, 0, 0.02]}, **tail_wave(2)}},
        "charge_k": {0: {"root": {"move": [0, 0, 0.02]}, **tail_wave(0)},
                     6: {"root": {"move": [0, 0.04, -0.06]}, "hips": {"pitch": -8}, "spine": {"pitch": -14}, "neck": {"pitch": 18}, "head": {"pitch": 10},
                         "legFL0": {"pitch": -10}, "legFR0": {"pitch": -10}, "legBL0": {"pitch": 18}, "legBR0": {"pitch": 18}, **tail_wave(1, 4, -25)},
                     12: {"root": {"move": [0.01, 0.04, -0.07]}, "hips": {"pitch": -9}, "spine": {"pitch": -16}, "neck": {"pitch": 20}, "head": {"pitch": 12, "roll": 3},
                          "legFL0": {"pitch": -12}, "legFR0": {"pitch": -12}, "legBL0": {"pitch": 20}, "legBR0": {"pitch": 20}, **tail_wave(2, 4, -28)},
                     19: {"root": {"move": [-0.01, 0.04, -0.07]}, "hips": {"pitch": -9}, "spine": {"pitch": -16}, "neck": {"pitch": 20}, "head": {"pitch": 12, "roll": -3},
                          "legFL0": {"pitch": -12}, "legFR0": {"pitch": -12}, "legBL0": {"pitch": 20}, "legBR0": {"pitch": 20}, **tail_wave(3, 4, -28)}},
        "lunge_k": {0: {"root": {"move": [0, 0.04, -0.07]}, "spine": {"pitch": -16}, "neck": {"pitch": 20}, "legBL0": {"pitch": 20}, "legBR0": {"pitch": 20}, **tail_wave(0, 4, -28)},
                    4: {"root": {"move": [0, 0, 0.18]}, "hips": {"pitch": 6}, "spine": {"pitch": 4}, "neck": {"pitch": -12}, "head": {"pitch": -8},
                        "legFL0": {"pitch": -55}, "legFR0": {"pitch": -50}, "legFL1": {"pitch": -20}, "legFR1": {"pitch": -20},
                        "legBL0": {"pitch": 45}, "legBR0": {"pitch": 50}, **tail_wave(1, 3, 40)},
                    9: {"root": {"move": [0, 0, 0.04]}, "spine": {"pitch": 6}, "neck": {"pitch": 10}, "legFL0": {"pitch": -15}, "legFR0": {"pitch": -15}, "legBL0": {"pitch": 15}, "legBR0": {"pitch": 15}, **tail_wave(2, 6, 20)},
                    14: {"root": {"move": [0, 0, 0.02]}, **tail_wave(3)}},
        "hit_k": {0: {"root": {"move": [0, 0, 0.02]}, **tail_wave(0)},
                  3: {"root": {"move": [0, -0.06, 0.03]}, "spine": {"pitch": -10}, "neck": {"pitch": -25}, "head": {"pitch": -20, "roll": 10}, **tail_wave(1, 30, 30)},
                  7: {"root": {"move": [0, -0.04, 0.0]}, "spine": {"pitch": -6}, "neck": {"pitch": -10}, "head": {"pitch": -8, "roll": -6}, **tail_wave(2, 15, 10)},
                  12: {"root": {"move": [0, 0, 0.02]}, **tail_wave(3)}},
        "vanish_k": {0: {"root": {"move": [0, 0, 0.02]}, **tail_wave(0)},
                     10: {"root": {"move": [0, 0, 0.1]}, "hips": {"pitch": -35}, "spine": {"pitch": -10}, "neck": {"pitch": -30}, "head": {"pitch": -25},
                          "legFL0": {"pitch": -40}, "legFR0": {"pitch": -35}, **tail_wave(1, 10, 35)},
                     30: {"root": {"move": [0, 0, 0.45]}, "hips": {"pitch": -45}, "spine": {"pitch": -12}, "neck": {"pitch": -35}, "head": {"pitch": -30},
                          "legFL0": {"pitch": -50}, "legFR0": {"pitch": -45}, "legBL0": {"pitch": 20}, "legBR0": {"pitch": 25}, **tail_wave(3, 20, 45)}},
    }
    if a.kind == "hinezumi":   # 背上的火冠一直跳：待机小跳，蓄力往上窜，扑出去拉长，被钉中缩一下，消散时冲高
        for name, keys in MOTIONS.items():
            for f, spec in keys.items():
                base = {"idle_k": 1.0, "appear_k": 0.9, "charge_k": 1.35, "lunge_k": 1.2, "hit_k": 0.75, "vanish_k": 1.5}[name]
                w = 2 * math.pi * f / 48   # 频率取 48 帧（待机一圈）的整数倍，待机首尾接得上
                k = base + 0.12 * sin(14 * w) + 0.06 * sin(28 * w + 1)
                spec["crest"] = {"yaw": 8 * sin(10 * w), "scale": [1 + 0.08 * sin(18 * w), 1, k]}
    if a.kind == "bakeneko":
        # 小化猫群（docs/18 第九节）三只各播各的待机：老大好奇、老二回头舔肩背、老三压低身子怯生生的。三段都是循环，首尾同一帧；
        # 脖子、头、五节尾巴、两只耳朵每个关键帧都打（代码叠的偏移就可以关掉）
        def win(f, a, b, r):   # f 在 a~b 之间为 1，两头 r 帧平滑过渡
            u = min(max((f - a) / r, 0), 1) * min(max((b - f) / r, 0), 1); return u * u * (3 - 2 * u)
        def tails(ph, amp, up=0.0, curl=0.0):
            return {f"tail{i}": {"yaw": amp * sin(ph - i * 0.7) + curl, "pitch": up if i == 0 else up * 0.2} for i in range(NT)}
        def loop(n, fn, step=2): return {f: fn(f) for f in range(0, n + 1, step)}
        T = 2 * math.pi
        # 第四版（11-04 用户看第三版：“头扭的角度，脖子不动，侧脸奇怪”）：骨头按模型实测重摆、耳朵不再带整个脑壳、脖子到头的权重抹匀；
        # 转头分到背、脖子、头三处（头自己转得少），脖子和头用 rel（绕父骨头转过之后的轴），扭过去再低头不会拧脸
        MOTIONS["idle_curious_k"] = loop(96, lambda f: {
            "root": {"move": [0, 0, 0.02 + 0.01 * sin(T * f / 48)]}, "spine": {"pitch": 1.2 * sin(T * f / 48)},
            "neck": {"pitch": 6 - 2 * sin(T * f / 96), "yaw": 7 * sin(T * f / 96), "roll": 5 * win(f, 6, 44, 8) - 4 * win(f, 58, 86, 8), "rel": 1},
            "head": {"pitch": -12 + 3 * sin(T * f * 4 / 96), "yaw": 9 * sin(T * f / 96), "roll": 15 * win(f, 6, 44, 8) - 12 * win(f, 58, 86, 8), "rel": 1},   # 抬眼看人、歪一下头，鼻子一抽一抽
            "earL": {"yaw": 25 * win(f, 26, 34, 2)}, "earR": {"yaw": -25 * win(f, 66, 74, 2)},
            **tails(T * f / 48, 9)})
        def groom(f):
            back = 1 - win(f, 70, 100, 8)      # 回头舔左边肩背；70~100 帧转回来看人一眼
            return {"root": {"move": [0.006 * back, 0, 0.02]}, "hips": {"yaw": -4 * back}, "spine": {"pitch": 1.0 * sin(T * f / 60), "yaw": 14 * back},
                    "neck": {"pitch": 16 * back - 3 * (1 - back), "yaw": 40 * back, "roll": -6 * back, "rel": 1},
                    "head": {"pitch": 20 * back - 6 * (1 - back) + 6 * back * sin(T * f / 8), "yaw": 34 * back, "roll": -16 * back, "rel": 1},   # 头一点一点地舔
                    "earL": {"pitch": -10 * back}, "earR": {"pitch": -10 * back},
                    **tails(T * f / 60, 7, 0, -12 * back)}
        MOTIONS["idle_groom_k"] = loop(120, groom)
        def shy(f):
            back = win(f, 40, 64, 8)           # 回头往后看
            sh = 0.004 * sin(T * f * 6 / 96)   # 微微发抖
            # 腿只弯一点（第三版前腿肘往后、后腿膝往前弯太多，侧面看四条腿交叉成 X），怯主要靠低头、压耳朵、尾巴垂下来往肚子底下收
            return {"root": {"move": [sh, -0.015, -0.025]}, "hips": {"pitch": -4}, "spine": {"pitch": 5 + 1.5 * sin(T * f / 48), "yaw": 8 * back},
                    "legFL0": {"pitch": 7}, "legFR0": {"pitch": 7}, "legFL1": {"pitch": -14}, "legFR1": {"pitch": -14},
                    "legBL0": {"pitch": -16}, "legBR0": {"pitch": -16}, "legBL1": {"pitch": 30}, "legBR1": {"pitch": 30},
                    "neck": {"pitch": 30 - 12 * back, "yaw": 26 * back, "rel": 1},          # 缩着脖子，回头时抬一点
                    "head": {"pitch": -18 + 6 * back, "yaw": 28 * back, "roll": -5 + 3 * sin(T * f / 96), "rel": 1},   # 头低着，眼睛往上瞄
                    "earL": {"pitch": -35, "yaw": 6 * sin(T * f * 3 / 96)}, "earR": {"pitch": -35, "yaw": -6 * sin(T * f * 3 / 96)},   # 耳朵往后压
                    # 尾巴：五节现在离竖直 8°、45°、18°、-27°、-104°（0 = 朝上，正 = 往前；尾尖往后卷），目标 -125、-150、-170、-185、-195：
                    # 低低地往后弧下去、尾尖往里勾（第四版第一次直直垂到两腿中间，侧面看像多了一条腿）
                    **{f"tail{i}": {"pitch": [-133, -62, 7, 30, 52][i] + (4 * sin(T * f / 32) if i == NT - 1 else 0), "yaw": 0} for i in range(NT)}}
        MOTIONS["idle_sit_k"] = loop(96, shy)
    if snake:   # 扑的那一下蛇头跟着往前咬
        MOTIONS["lunge_k"][4].update({f"tail{NT - 2}": {"pitch": 35}, f"tail{NT - 1}": {"pitch": 45}})
elif a.kind == "umibozu":
    def lean(p, y=0.0, sw=1.0, head=0.0, hroll=0.0):   # 身子往前低 p 度（分到三节）、往左扭 y 度；sw 袍子往外鼓；头再低 head 度、歪 hroll 度
        return {"body0": {"pitch": p * 0.2, "yaw": y * 0.3}, "body1": {"pitch": p * 0.35, "yaw": y * 0.35, "scale": [sw, sw, 1]},
                "chest": {"pitch": p * 0.45, "yaw": y * 0.35}, "head": {"pitch": head, "roll": hroll, "yaw": y * 0.3}}
    MOTIONS = {
        "idle_k": wave(128, 64, lambda ph: {"root": {"move": [0, 0, 0.03 * sin(ph)]}, **lean(2 * sin(ph), 4 * sin(ph * 0.5), 1 + 0.02 * sin(ph), 0, 3 * sin(ph * 0.5 + 1))}),
        "appear_k": {0: {"root": {"move": [0, 0, -2.3]}, **lean(12, 0, 0.9, 20)}, 20: {"root": {"move": [0, 0, 0.1]}, **lean(-6, 0, 1.05, -10)}, 30: {"root": {"move": [0, 0, 0]}, **lean(0)}},
        "charge_k": {0: {"root": {"move": [0, 0, 0]}, **lean(0)}, 7: {"root": {"move": [0, -0.06, 0.04]}, **lean(-14, 0, 1.08, -12)},
                     13: {"root": {"move": [0, -0.07, 0.05]}, **lean(-16, 4, 1.1, -14, 4)}, 19: {"root": {"move": [0, -0.07, 0.05]}, **lean(-16, -4, 1.1, -14, -4)}},
        "lunge_k": {0: {"root": {"move": [0, -0.07, 0.05]}, **lean(-16, 0, 1.1, -14)}, 5: {"root": {"move": [0, 0.12, -0.04]}, **lean(38, 0, 0.95, 15)},
                    10: {"root": {"move": [0, 0.06, 0]}, **lean(18, 0, 1.0, 6)}, 16: {"root": {"move": [0, 0, 0]}, **lean(0)}},
        "hit_k": {0: {"root": {"move": [0, 0, 0]}, **lean(0)}, 3: {"root": {"move": [0, -0.08, 0.03]}, **lean(-20, 10, 1.06, -20, 10)},
                  7: {"root": {"move": [0, -0.04, 0]}, **lean(-6, -5, 1.0, -4, -4)}, 12: {"root": {"move": [0, 0, 0]}, **lean(0)}},
        "vanish_k": {0: {"root": {"move": [0, 0, 0]}, **lean(0)}, 12: {"root": {"move": [0, 0, -0.5], "yaw": 25}, **lean(8, 0, 1.12, 10)},
                     30: {"root": {"move": [0, 0, -2.4], "yaw": 60}, **lean(12, 0, 1.2, 14)}},
    }
else:
    def bend(p, y=0.0, sq=1.0, flare=1.0):   # 伞身往前弯 p 度（分到三节）、往左扭 y 度；sq：上下压扁，flare：伞面往外张
        return {"body0": {"pitch": p * 0.3, "yaw": y * 0.3, "scale": [flare ** 0.5, flare ** 0.5, sq]}, "body1": {"pitch": p * 0.35, "yaw": y * 0.35, "scale": [flare, flare, 1]},
                "body2": {"pitch": p * 0.35, "yaw": y * 0.35}}
    def hop(ph):
        h = max(0.0, sin(ph)); return {"root": {"move": [0, 0, 0.07 * h]}, **bend(4 * sin(ph * 2), 6 * sin(ph * 0.5), 1 - 0.06 * max(0.0, -sin(ph)))}
    MOTIONS = {
        "idle_k": wave(48, 24, hop),
        "appear_k": {0: {"root": {"move": [0, 0, -0.9]}, **bend(0, 0, 1, 0.8)}, 14: {"root": {"move": [0, 0, 0.12]}, **bend(-6, 0, 1.08, 1.05)}, 24: {"root": {"move": [0, 0, 0]}, **bend(0, 0, 0.94)}},
        "charge_k": {0: {"root": {"move": [0, 0, 0]}, **bend(0)}, 6: {"root": {"move": [0, -0.03, 0]}, **bend(-16, 0, 0.88, 1.18)},
                     12: {"root": {"move": [0.01, -0.03, 0]}, **bend(-18, 4, 0.86, 1.22)}, 19: {"root": {"move": [-0.01, -0.03, 0]}, **bend(-18, -4, 0.86, 1.22)}},
        "lunge_k": {0: {"root": {"move": [0, -0.03, 0]}, **bend(-18, 0, 0.86, 1.22)}, 4: {"root": {"move": [0, 0, 0.22]}, **bend(28, 0, 1.12, 0.9)},
                    9: {"root": {"move": [0, 0, 0.0]}, **bend(10, 0, 0.9, 1.05)}, 14: {"root": {"move": [0, 0, 0]}, **bend(0)}},
        "hit_k": {0: {"root": {"move": [0, 0, 0]}, **bend(0)}, 3: {"root": {"move": [0, -0.05, 0.04]}, **bend(-24, 12, 0.9, 1.1)},
                  7: {"root": {"move": [0, -0.03, 0]}, **bend(-8, -6, 1.04)}, 12: {"root": {"move": [0, 0, 0]}, **bend(0)}},
        "vanish_k": {0: {"root": {"move": [0, 0, 0]}, **bend(0)}, 10: {"root": {"move": [0, 0, 0.15], "yaw": 120}, **bend(-10, 0, 1.1, 1.35)},
                     30: {"root": {"move": [0, 0, 0.6], "yaw": 400}, **bend(-4, 0, 1.15, 1.5)}},
    }

bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="POSE")
depth = lambda b: 0 if not b.parent else 1 + depth(b.parent)
ORDER = sorted(arm.pose.bones, key=lambda pb: depth(pb.bone))
for pb in arm.pose.bones: pb.rotation_mode = "QUATERNION"

def rot_about(axis, deg, pivot):
    return Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-pivot)

def apply(spec):
    for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    for pb in ORDER:
        s = spec.get(pb.name)
        if not s: continue
        M = pb.matrix.copy(); head = M.translation.copy(); R = Matrix.Identity(4)
        if s.get("rel") and pb.parent:   # 轴跟着父骨头转：脖子已经扭过去了，头再低头、歪头是绕自己的轴（第三版绕世界轴，头扭到一边后再低头就变成了拧脸）
            Dp = (pb.parent.matrix @ pb.parent.bone.matrix_local.inverted()).to_3x3()
            L_, F_, U_ = Dp @ LEFT, Dp @ FRONT, Dp @ UP
            if s.get("roll"): R = rot_about(F_, s["roll"], head) @ R
            if s.get("pitch"): R = rot_about(L_, s["pitch"], head) @ R
            if s.get("yaw"): R = rot_about(U_, s["yaw"], head) @ R
        else:
            if s.get("pitch"): R = rot_about(LEFT, s["pitch"], head) @ R        # 绕左右轴：正 = 远端往前（前是 -Y，绕 +X 转正角远端往 -Y 走要取反）
            if s.get("roll"): R = rot_about(FRONT, s["roll"], head) @ R
            if s.get("yaw"): R = rot_about(UP, s["yaw"], head) @ R
        M2 = R @ M
        if s.get("move"): mv = s["move"]; M2 = Matrix.Translation(LEFT * mv[0] + FRONT * mv[1] + UP * mv[2]) @ M2
        pb.matrix = M2
        if s.get("scale"): sc = s["scale"]; pb.scale = (sc[0], sc[2], sc[1])   # 骨头本地 Y 沿骨头（往上），X、Z 是两个水平方向
        bpy.context.view_layer.update()

arm.animation_data_create()
for name, keys in MOTIONS.items():
    # 已经压进 NLA 的动作先静音：不然打第一帧时 view_layer.update() 会把前面的动作叠进来，第一帧被带歪
    #（11-04 小化猫坐着的待机第一帧屁股多沉了 0.36 米；排在 idle_k 后面的几段原来也都偏了一两厘米）
    for t2 in arm.animation_data.nla_tracks: t2.mute = True
    act = bpy.data.actions.new(name); arm.animation_data.action = act
    for f, spec in sorted(keys.items()):
        apply(spec)
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f); pb.keyframe_insert("location", frame=f); pb.keyframe_insert("scale", frame=f)
    last = max(keys)
    act.use_frame_range = True; act.frame_range = (0, last)
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new(); tr.name = name
    st = tr.strips.new(name, 0, act)
    if hasattr(st, "action_slot") and len(act.slots): st.action_slot = act.slots[0]
    print(f"[creature] 动作 {name}: {len(keys)} 个关键帧, {last} 帧 = {last / FPS:.2f} 秒")
for t2 in arm.animation_data.nla_tracks: t2.mute = False   # 导出按 NLA 轨道，静音的不会导出
apply({}); bpy.ops.object.mode_set(mode="OBJECT")

# 原名提示：pitch 的正方向。LEFT=+X，绕 +X 转正角时，朝上的骨头远端往 -Y（前）走——和姿势库"正值 = 往前低"一致
if a.render:
    os.makedirs(a.render, exist_ok=True)
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    sc.render.resolution_x = 500; sc.render.resolution_y = 500; sc.render.fps = FPS
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.88, 0.82, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (0.8, 0.2, 0.6)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
    tgt = Vector((0, 0, H * 0.5))
    for name, keys in MOTIONS.items():
        tr = arm.animation_data.nla_tracks[name]
        for t2 in arm.animation_data.nla_tracks: t2.mute = t2 is not tr
        for f in sorted(keys)[:: max(1, len(keys) // 3)]:
            sc.frame_set(f)
            for vn, d in (("front", Vector((0.4, -1, 0.25))), ("side", Vector((1, 0, 0.2)))):
                cam.location = tgt + d.normalized() * H * 3.2; cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
                sc.render.filepath = os.path.join(a.render, f"{a.kind}_{name}_{f:02d}_{vn}.png"); bpy.ops.render.render(write_still=True)
    for t2 in arm.animation_data.nla_tracks: t2.mute = False

if a.out:
    for o in bpy.data.objects: o.select_set(o in (arm, mesh))
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=True,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6, export_image_format="JPEG", export_jpeg_quality=85,
        export_animations=True, export_skins=True, export_yup=True, export_animation_mode="NLA_TRACKS")
    print(f"[creature] wrote {a.out} {os.path.getsize(a.out) / 1e6:.2f} MB")
