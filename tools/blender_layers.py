"""
药贩子分层 + 骨链：把下摆、两只大袖、长发从 Tripo 的整块网格里分出来，各挂一组骨链，重刷权重。
输入 blender_lite.py --keep-rig 的轻量绑骨模型，输出 assets/processed/<name>_layered.glb，
再交给 blender_pose_anim.py 套姿势库。骨链名以 chain_ 开头，不进关键帧，运行时由查看器的弹簧骨驱动。

为什么要做：Tripo 自动绑骨把腰以下整片绑在大腿和小腿上、大袖垂下的部分也绑在大腿上，
弓步一分腿下摆就被扯成一张膜（横斩那一拍最明显）。改成：下摆挂在骨盆上的一圈骨链、大袖挂在手臂上的骨链、
长发挂在头上的骨链，腿只负责把骨链推开（查看器里的碰撞体）。

分层全部用"位置 + 贴图颜色"的连续规则，不按网格连通区域：Tripo 的网格被 UV 接缝切成两百多块，
同一位置的接缝顶点必须拿到一样的权重，不然一动就裂开。所以每个顶点的权重只由它的位置和颜色决定。

  Blender -b --python tools/blender_layers.py -- --in assets/processed/kusuriuri_v2_lite.glb \
      --out assets/processed/kusuriuri_v2_layered.glb [--check 目录]   # --check 只渲分层上色图，不导出
"""
import argparse, math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out")
ap.add_argument("--check")
a = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
# Tripo 骨架附带一个没有蒙皮的小球（骨头显示用），不导出
for o in [o for o in bpy.data.objects if o.type == "MESH" and len(o.vertex_groups) == 0]:
    bpy.data.objects.remove(o, do_unlink=True)
body = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
me = body.data
mw = body.matrix_world
N = len(me.vertices)
P = np.array([tuple(mw @ v.co) for v in me.vertices])
gname = {g.index: g.name for g in body.vertex_groups}
W0 = [{gname[g.group]: g.weight for g in v.groups} for v in me.vertices]
def bw(i, names): return sum(W0[i].get(n, 0.0) for n in names)

def bone(name):
    b = arm.data.bones[name]; return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local

# ---- 角色坐标：blender_lite 已把角色转成面朝 -Y ----
cx = float(np.median(P[P[:, 2] < 0.25][:, 0])); cy = float(np.median(P[P[:, 2] < 0.25][:, 1]))
hip_h, _ = bone("Pelvis")
Z_ROOT = hip_h.z - 0.005                     # 下摆骨链的起点高度（骨盆）
print(f"[layers] 中心 x={cx:.3f} y={cy:.3f}，骨盆高 {hip_h.z:.3f}，顶点 {N}")

# ---- 贴图颜色（按 UV 取） ----
img = next(n.image for n in me.materials[0].node_tree.nodes if n.type == "TEX_IMAGE" and n.image)
iw, ih = img.size; px = np.array(img.pixels[:]).reshape(ih, iw, 4)
vuv = np.zeros((N, 2)); uvl = me.uv_layers.active.data
for poly in me.polygons:
    for li in poly.loop_indices: vuv[me.loops[li].vertex_index] = uvl[li].uv
C = px[np.clip((vuv[:, 1] * (ih - 1)).astype(int), 0, ih - 1), np.clip((vuv[:, 0] * (iw - 1)).astype(int), 0, iw - 1), :3]
C = np.clip(C, 0, 1) ** (1 / 2.2)            # 线性 → sRGB，阈值按肉眼颜色写

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

kd = KDTree(N)
for i in range(N): kd.insert(P[i], i)
kd.balance()
def smooth(field, r):
    out = np.zeros(N)
    for i in range(N):
        hits = kd.find_range(P[i], r)
        out[i] = np.mean([field[j] for _, j, _ in hits]) if hits else field[i]
    return out

# ---- 脚：凉鞋和脚背，保持原权重 ----
foot = np.array([bw(i, ["L_Foot", "R_Foot", "L_ToeBase", "R_ToeBase"]) for i in range(N)])
# 只有以脚骨为主的顶点（凉鞋、足袋）才留在腿上；袴的底边虽然贴地，也要跟下摆走，否则迈步时会拉出一条楔子
# 脚 = 以脚骨为主的顶点 + 贴地且水平方向离脚骨 7.5 厘米以内的顶点（凉鞋、足袋、袴的裤脚），3.5 厘米以下全跟脚，往上到 18 厘米渐变成跟下摆。
# v2 的脚踝骨几乎贴地，鞋跟顶点没有脚骨权重，只按权重判断会漏掉鞋跟，迈步时鞋被拉长
near_foot = np.zeros(N)
for side in ("L", "R"):
    fh, _ = bone(f"{side}_Foot"); _, tt = bone(f"{side}_ToeBase")
    seg = np.array([tt.x - fh.x, tt.y - fh.y]); L2 = max(seg @ seg, 1e-9)
    rel = P[:, :2] - np.array([fh.x, fh.y])
    t = np.clip(rel @ seg / L2, -0.6, 1.2)
    dist = np.linalg.norm(rel - t[:, None] * seg[None, :], axis=1)
    near_foot = np.maximum(near_foot, sstep(0.09, 0.065, dist) * sstep(0.18, 0.035, P[:, 2]))   # 过渡区加高到 18 厘米（小腿中段）：袴的下半截像裤腿一样跟腿走，迈步时不在贴地处拉出薄片
foot = np.maximum(sstep(0.35, 0.6, foot), near_foot)

# ---- 衣身轮廓：袖子底以下的下摆宽度，按高度线性拟合，往上延伸 ----
lowz = (P[:, 2] > 0.06) & (P[:, 2] < 0.27)   # 不排除脚：外缘 98% 分位本来就不受里面的脚影响，排除了反而让袖子边界随脚的规则变
zs = np.arange(0.06, 0.27, 0.02)
half = [np.percentile(np.abs(P[lowz & (P[:, 2] >= z) & (P[:, 2] < z + 0.02)][:, 0] - cx), 98) for z in zs]
k1, k0 = np.polyfit(zs + 0.01, half, 1)
def body_half(z): return np.maximum(k0 + k1 * z, 0.085)
print(f"[layers] 衣身半宽 = {k0:.3f} + {k1:.3f}·z（z=0.1 时 {body_half(0.1):.3f}，z=0.5 时 {body_half(0.5):.3f}）")

# ---- 大袖：在衣身轮廓之外，并且垂在手臂下面 ----
def arm_line(side):
    s, _ = bone(f"{side}_Upperarm"); h, _ = bone(f"{side}_Hand"); return s, h
sleeve = {}
for side, sgn in (("L", 1), ("R", -1)):
    s, h = arm_line(side)
    dx = (P[:, 0] - cx) * sgn
    out_body = sstep(body_half(P[:, 2]) + 0.005, body_half(P[:, 2]) + 0.035, dx)
    t = np.clip((P[:, 0] - s.x) / (h.x - s.x), 0, 1)
    z_arm = s.z + (h.z - s.z) * t
    hang = sstep(0.03, 0.08, z_arm - P[:, 2])                  # 手臂下方 3~8 厘米（模型单位）开始算袖子
    in_span = sstep(-0.02, 0.01, dx - abs(s.x - cx)) * (dx < abs(h.x - cx) + 0.06)
    handw = np.array([bw(i, [f"{side}_Hand"]) for i in range(N)])
    sleeve[side] = np.clip(out_body * hang * in_span * (1 - handw) * sstep(0.24, 0.28, P[:, 2]), 0, 1)
sl_any = np.maximum(sleeve["L"], sleeve["R"])

# ---- 长发：颜色是淡紫白或粉，位置在腰以上、头以下、身后，不在手上 ----
# 只取披在背后的长发；胸前两缕短发贴着胸口，跟头和胸走就行，不挂骨链
r, g, b = C[:, 0], C[:, 1], C[:, 2]
pale = (np.min(C, axis=1) > 0.62) & ((np.max(C, axis=1) - np.min(C, axis=1)) < 0.25)
# 发梢是偏紫的粉（蓝 ≥ 绿），衣服的珊瑚色是偏黄的鲑鱼粉（蓝 < 绿），靠这一条分开
pink = (r > 0.72) & (g > 0.45) & (g < 0.8) & (b > g - 0.02) & ((r - g) > 0.1) & ((r - g) < 0.42)
handw = np.array([bw(i, ["L_Hand", "R_Hand", "L_ForearmTwist02", "R_ForearmTwist02"]) for i in range(N)])
head_h, _ = bone("Head")
hair_raw = ((pale | pink) & (P[:, 2] > 0.4) & (P[:, 2] < head_h.z + 0.02) & (handw < 0.3)
            & (P[:, 1] > cy + 0.02) & (np.abs(P[:, 0] - cx) < 0.16)).astype(float)
hair_raw *= (1 - sl_any)
hair = sstep(0.35, 0.65, smooth(hair_raw, 0.018))          # 空间平滑：衣服上零星的白色纹样线会被抹掉
hair *= sstep(head_h.z - 0.02, head_h.z - 0.09, P[:, 2])    # 头部以上留在头骨上
print(f"[layers] 头发候选 {int(hair_raw.sum())}，平滑后 > 0.5 的 {int((hair > 0.5).sum())}")

# ---- 下摆：腰以下，减去袖子、脚、头发 ----
hem = sstep(Z_ROOT + 0.01, Z_ROOT - 0.06, P[:, 2]) * (1 - foot) * (1 - sl_any) * (1 - hair)
print(f"[layers] 下摆 {int((hem > 0.5).sum())}，左袖 {int((sleeve['L'] > 0.5).sum())}，右袖 {int((sleeve['R'] > 0.5).sum())}，头发 {int((hair > 0.5).sum())}")

LAYERS = {"hem": hem, "sleeve_L": sleeve["L"], "sleeve_R": sleeve["R"], "hair": hair}

if a.check:
    os.makedirs(a.check, exist_ok=True)
    cols = {"hem": (0.2, 0.5, 1.0), "sleeve_L": (1.0, 0.55, 0.1), "sleeve_R": (1.0, 0.2, 0.6), "hair": (0.3, 0.95, 0.4)}
    ca = me.color_attributes.new("cls", "BYTE_COLOR", "POINT")
    for i in range(N):
        c = np.array([0.85, 0.85, 0.85])
        for k, f in LAYERS.items(): c = c * (1 - f[i]) + np.array(cols[k]) * f[i]
        ca.data[i].color = (*c, 1)
    m = bpy.data.materials.new("cls"); m.use_nodes = True; nt = m.node_tree
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "cls"
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(vc.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
    me.materials.clear(); me.materials.append(m)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = 700; scene.render.resolution_y = 900
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = 1.1
    c0 = Vector((cx, cy, 0.5))
    for name, d in [("front", Vector((0, -1, 0))), ("side", Vector((1, 0, 0))), ("back", Vector((0, 1, 0)))]:
        cam.location = c0 + d * 3; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(a.check, f"cls_{name}.png"); bpy.ops.render.render(write_still=True)
    sys.exit(0)

# ======================================================================
# 手指：Tripo 的骨架没有手指骨，握剑是张开的手掌。每只手加四指 2 节（四指当一个整体，远看握拳足够，比逐根拆五指稳）。
# 拇指不单独做：这个模型的拇指鼓得不明显，按形状找会把手腕和袖口误判成拇指，一弯就把袖口撕开；握剑时拇指本来就顺着剑柄贴着。
# 用顶点实际的指尖位置量长度，不用骨头长度（Tripo 的左手骨只有右手的一半长）。
# ======================================================================
FRONT_W = Vector((0, -1, 0))
HANDS = {}
for side in ("L", "R"):
    h, t = bone(f"{side}_Hand"); along = (t - h).normalized()
    across = (FRONT_W - along * FRONT_W.dot(along)).normalized(); normal = along.cross(across).normalized()
    wv = np.array([W0[i].get(f"{side}_Hand", 0.0) for i in range(N)])
    idx = np.where(wv > 0.3)[0]
    Q = P[idx] - np.array(h)
    sv = Q @ np.array(along); av = Q @ np.array(across); nv = Q @ np.array(normal)
    D = float(np.percentile(sv, 99.5)); k = 0.52 * D; m = 0.76 * D
    fing = sv > k
    palm = (sv > 0.1 * D) & (sv < 0.5 * D)
    plo, phi = np.percentile(av[palm], 2), np.percentile(av[palm], 98)
    flo, fhi = np.percentile(av[fing], 5), np.percentile(av[fing], 95)
    tsign = -1 if (flo - plo) > (phi - fhi) else 1
    edge = flo if tsign < 0 else fhi
    thumb = np.zeros_like(sv)   # 拇指不单独做，见上
    def centroid(mask): return Vector(tuple(np.array(h) + Q[mask].mean(axis=0)))
    kn = centroid(fing & (np.abs(sv - k) < 0.08 * D) & (thumb < 0.5))
    md = centroid(np.abs(sv - m) < 0.08 * D)
    tp = centroid(sv > 0.93 * D)
    HANDS[side] = dict(idx=idx, sv=sv, thumb=thumb, k=k, m=m, D=D, kn=kn, md=md, tp=tp, normal=normal, along=along, across=across)
    print(f"[layers] {side} 手：指尖距腕 {D:.3f}，指根 {k:.3f}，四指 {int((sv > k).sum())} 个顶点")

# ======================================================================
# 骨链
# ======================================================================
inv = arm.matrix_world.inverted()
bpy.context.view_layer.objects.active = arm
for o in bpy.data.objects: o.select_set(o is arm)
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones

def add_chain(name, joints, parent):
    """joints：世界坐标的关节点（含末端），生成 len-1 节骨头 + 一个末端小骨头（查看器拿它算最后一节的指向）"""
    prev = eb[parent]; names = []
    pts = [inv @ Vector(p) for p in joints]
    end = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.02
    for i, (h, t) in enumerate(zip(pts, pts[1:] + [end])):
        nm = f"{name}_{i}" if i < len(pts) - 1 else f"{name}_end"
        b = eb.new(nm); b.head = h; b.tail = t; b.parent = prev; b.use_connect = i > 0
        b.use_deform = i < len(pts) - 1
        prev = b; names.append(nm)
    return names[:-1]

ang = np.arctan2(P[:, 1] - cy, P[:, 0] - cx)
rad = np.hypot(P[:, 0] - cx, P[:, 1] - cy)

# ---- 下摆：骨盆一圈 12 条，每条 3 节 ----
K = 12; NB = 3
hem_chains = []; hem_zb = []
for k in range(K):
    th = -math.pi + 2 * math.pi * k / K
    d = np.angle(np.exp(1j * (ang - th)))
    sec = (np.abs(d) < math.pi / K * 1.2) & (hem > 0.5)
    sec_top = (np.abs(d) < math.pi / K * 1.2) & (sl_any < 0.5) & (hair < 0.5)   # 腰带处 hem 权重还没到 0.5，用这一圈
    zb = np.percentile(P[sec][:, 2], 3)
    # 每一节的高度上量衣摆外表面（85% 分位，避开里层的白袴），让骨链贴着外层衣服走，离腿远一点
    joints = []
    for i in range(NB + 1):
        zi = Z_ROOT + (zb - Z_ROOT) * i / NB
        band = (sec_top if i == 0 else sec) & (np.abs(P[:, 2] - zi) < 0.035)
        ri = np.percentile(rad[band], 85) if band.sum() > 20 else (joints[-1] - Vector((cx, cy, joints[-1].z))).length
        if i == 0: ri *= 0.95
        joints.append(Vector((cx + math.cos(th) * ri, cy + math.sin(th) * ri, zi)))
    hem_chains.append(add_chain(f"chain_hem_{k:02d}", joints, "Pelvis")); hem_zb.append(zb)
hem_zb = np.array(hem_zb)

# ---- 大袖：每边两条（上臂、前臂），每条 2 节，直直垂到袖底 ----
sleeve_chains = {}
for side in ("L", "R"):
    S, Hd = arm_line(side); chains = []
    elbow, _ = bone(f"{side}_Forearm")
    xs_sl = P[sleeve[side] > 0.5][:, 0]
    sgn = 1 if side == "L" else -1
    for q in (20, 85):
        xk = float(np.percentile(xs_sl * sgn, q)) * sgn          # 袖子顶点左右分布的 20%、85% 分位
        u = min(max((xk - S.x) / (Hd.x - S.x), 0.0), 1.0); A = S.lerp(Hd, u)
        par = f"{side}_Upperarm" if abs(xk - cx) < abs(elbow.x - cx) else f"{side}_Forearm"
        near = (sleeve[side] > 0.5) & (np.abs(P[:, 0] - xk) < 0.03)
        zb = np.percentile(P[near][:, 2], 2); yb = float(np.median(P[near & (P[:, 2] < zb + 0.05)][:, 1]))
        root = Vector((xk, A.y, A.z - 0.03)); bottom = Vector((xk, yb, zb))
        joints = [root.lerp(bottom, i / 2) for i in range(3)]
        chains.append((add_chain(f"chain_sleeve_{side}_{'in' if q < 50 else 'out'}", joints, par), xk, root.z, zb))
        print(f"[layers] 袖链 {side} x={xk:.3f} 挂 {par}，从 z={root.z:.3f} 到 {zb:.3f}")
    sleeve_chains[side] = chains

# ---- 长发：头后 5 条，每条 3 节 ----
hair_chains = []
z_root_h = head_h.z - 0.04
for xo in (-0.08, -0.04, 0.0, 0.04, 0.08):
    xk = cx + xo
    near = (hair > 0.3) & (np.abs(P[:, 0] - xk) < 0.03)
    up = near & (P[:, 2] > z_root_h - 0.05)
    yr = np.percentile(P[up][:, 1], 50) if up.sum() > 10 else cy + 0.06
    zb = np.percentile(P[near][:, 2], 3); yb = float(np.median(P[near & (P[:, 2] < zb + 0.05)][:, 1]))
    root = Vector((xk, yr, z_root_h)); bottom = Vector((xk, yb, zb))
    joints = [root.lerp(bottom, i / 3) for i in range(4)]
    hair_chains.append((add_chain(f"chain_hair_{int(round((xo + 0.08) / 0.04))}", joints, "Head"), xk, zb))

for side, Hd in HANDS.items():
    for nm, pts, par in ((f"{side}_Fingers", [Hd["kn"], Hd["md"], Hd["tp"]], f"{side}_Hand"),):
        prev = eb[par]
        for i, (a0, a1) in enumerate(zip(pts, pts[1:])):
            b = eb.new(f"{nm}_{i}"); b.head = inv @ a0; b.tail = inv @ a1; b.parent = prev; b.use_connect = i > 0
            b.align_roll(inv.to_3x3() @ Hd["normal"])     # Z 轴对掌心法线，局部 X 就是指根连线，握拳 = 绕 X 转
            prev = b
bpy.ops.object.mode_set(mode="OBJECT")
n_bones = sum(len(c) for c in hem_chains) + sum(len(c[0]) for v in sleeve_chains.values() for c in v) + sum(len(c[0]) for c in hair_chains)
print(f"[layers] 新增骨链骨头 {n_bones} 节（下摆 {K} 条、大袖 4 条、长发 {len(hair_chains)} 条）")

# ======================================================================
# 权重
# ======================================================================
def seg_weights(t, n):
    """链上参数 t∈[0,1] → [(骨头序号, 权重)]，相邻两节线性过渡"""
    f = min(max(t * n - 0.5, 0.0), n - 1.0); i0 = int(math.floor(f)); i1 = min(i0 + 1, n - 1); b = f - i0
    return [(i0, 1 - b), (i1, b)] if i1 != i0 else [(i0, 1.0)]

LEG = [n for n in body.vertex_groups.keys() if any(k in n for k in ("Thigh", "Calf"))]
newW = []
for i in range(N):
    w = dict(W0[i])
    # 原来绑在腿上的权重：袖子区域转给前臂，其余转给骨盆；脚保留
    legw = sum(w.pop(n, 0.0) for n in LEG if n in w)
    if legw > 0:
        keep = legw * foot[i]
        sl_side = "L" if sleeve["L"][i] >= sleeve["R"][i] else "R"
        dest = f"{sl_side}_Forearm" if max(sleeve["L"][i], sleeve["R"][i]) > 0.02 else "Pelvis"
        w[dest] = w.get(dest, 0) + legw - keep
        if keep > 0:   # 留给原来的腿骨，按原比例
            tot = sum(W0[i].get(n, 0) for n in LEG)
            for n in LEG:
                if W0[i].get(n): w[n] = w.get(n, 0) + keep * W0[i][n] / tot
    tot = sum(w.values()) or 1.0
    w = {k: v / tot for k, v in w.items()}
    out = {}
    lay = hem[i] + sleeve["L"][i] + sleeve["R"][i] + hair[i]
    if lay > 1: hem[i] /= lay; sleeve["L"][i] /= lay; sleeve["R"][i] /= lay; hair[i] /= lay; lay = 1.0
    for k_, v in w.items(): out[k_] = v * (1 - lay)
    if hem[i] > 0:
        f = (ang[i] + math.pi) / (2 * math.pi) * K; k1 = int(math.floor(f)) % K; k2 = (k1 + 1) % K; al = f - math.floor(f)
        zb = hem_zb[k1] * (1 - al) + hem_zb[k2] * al
        t = min(max((Z_ROOT - P[i, 2]) / (Z_ROOT - zb), 0.0), 1.0)
        for (bi, bwt) in seg_weights(t, NB):
            out[hem_chains[k1][bi]] = out.get(hem_chains[k1][bi], 0) + hem[i] * (1 - al) * bwt
            out[hem_chains[k2][bi]] = out.get(hem_chains[k2][bi], 0) + hem[i] * al * bwt
    for side in ("L", "R"):
        sv = sleeve[side][i]
        if sv <= 0: continue
        (c1, x1, zr1, zb1), (c2, x2, zr2, zb2) = sleeve_chains[side]
        al = min(max((P[i, 0] - x1) / (x2 - x1), 0.0), 1.0)
        zr = zr1 * (1 - al) + zr2 * al; zb = zb1 * (1 - al) + zb2 * al
        t = min(max((zr - P[i, 2]) / (zr - zb), 0.0), 1.0)
        for (bi, bwt) in seg_weights(t, 2):
            out[c1[bi]] = out.get(c1[bi], 0) + sv * (1 - al) * bwt
            out[c2[bi]] = out.get(c2[bi], 0) + sv * al * bwt
    if hair[i] > 0:
        xs = np.array([c[1] for c in hair_chains])
        f = np.interp(P[i, 0], xs, np.arange(len(xs))); k1 = int(math.floor(f)); k2 = min(k1 + 1, len(xs) - 1); al = f - k1
        zb = hair_chains[k1][2] * (1 - al) + hair_chains[k2][2] * al
        t = min(max((z_root_h - P[i, 2]) / (z_root_h - zb), 0.0), 1.0)
        for (bi, bwt) in seg_weights(t, 3):
            out[hair_chains[k1][0][bi]] = out.get(hair_chains[k1][0][bi], 0) + hair[i] * (1 - al) * bwt
            out[hair_chains[k2][0][bi]] = out.get(hair_chains[k2][0][bi], 0) + hair[i] * al * bwt
    newW.append(out)

for side, Hd in HANDS.items():
    hb = f"{side}_Hand"; k, m, D = Hd["k"], Hd["m"], Hd["D"]
    for j, vi in enumerate(Hd["idx"]):
        w = newW[vi].get(hb, 0.0)
        if w <= 0: continue
        sv = Hd["sv"][j]; th = float(Hd["thumb"][j])
        f = float(sstep(k - 0.06 * D, k + 0.06 * D, sv)) * (1 - th)
        f1 = float(sstep(m - 0.06 * D, m + 0.06 * D, sv))
        moves = {f"{side}_Fingers_0": w * f * (1 - f1), f"{side}_Fingers_1": w * f * f1}
        newW[vi][hb] = w - sum(moves.values())
        for nm, v in moves.items():
            if v > 1e-4: newW[vi][nm] = newW[vi].get(nm, 0) + v

# 写回顶点组（glTF 每个顶点最多 4 个影响，导出时取最大的 4 个再归一）
for vg in list(body.vertex_groups): body.vertex_groups.remove(vg)
groups = {}
for i, out in enumerate(newW):
    top = sorted(out.items(), key=lambda kv: -kv[1])[:4]; tot = sum(v for _, v in top) or 1.0
    for nm, v in top:
        if v / tot < 1e-3: continue
        if nm not in groups: groups[nm] = body.vertex_groups.new(name=nm)
        groups[nm].add([i], v / tot, "REPLACE")
print(f"[layers] 重刷权重完成，顶点组 {len(groups)} 个")

# ======================================================================
# 拆成独立网格层（按每个面的平均类别）
# ======================================================================
cls = np.stack([1 - np.clip(hem + sleeve["L"] + sleeve["R"] + hair, 0, 1), hem, sleeve["L"], sleeve["R"], hair], axis=1)
LAYER_NAMES = ["kusuriuri_body", "kusuriuri_hem", "kusuriuri_sleeve_L", "kusuriuri_sleeve_R", "kusuriuri_hair"]
face_cls = np.array([np.argmax(cls[list(p.vertices)].mean(axis=0)) for p in me.polygons])
counts = {LAYER_NAMES[c]: int((face_cls == c).sum()) for c in range(5)}
print(f"[layers] 面数 {counts}")
body.name = LAYER_NAMES[0]
for c in range(4, 0, -1):
    bpy.context.view_layer.objects.active = body
    for o in bpy.data.objects: o.select_set(o is body)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    fc = np.array([np.argmax(cls[list(p.vertices)].mean(axis=0)) for p in body.data.polygons]) if c < 4 else face_cls
    # 拆过一次后 body 的顶点编号变了，重新按位置算类别
    if c < 4:
        Pb = np.array([tuple(body.matrix_world @ v.co) for v in body.data.vertices])
        idx = [kd.find(p)[1] for p in Pb]
        fc = np.array([np.argmax(cls[[idx[v] for v in p.vertices]].mean(axis=0)) for p in body.data.polygons])
    for p, k in zip(body.data.polygons, fc): p.select = bool(k == c)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
    new = [o for o in bpy.context.selected_objects if o is not body][0]
    new.name = LAYER_NAMES[c]
print("[layers] 网格层：", [o.name for o in bpy.data.objects if o.type == "MESH"])

if a.out:
    for o in bpy.data.objects: o.select_set(False)
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=False,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_image_format="JPEG", export_jpeg_quality=85, export_animations=False, export_skins=True, export_yup=True)
    print(f"[layers] wrote {a.out} {os.path.getsize(a.out)/1e6:.1f} MB")
