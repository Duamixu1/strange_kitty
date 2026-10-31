"""
用 JSON 姿势库给 Tripo 骨架手 K 动作，导出 GLB，顺便渲染每个姿势的正面/侧面图供检查。

姿势写法（tools/poses/*.json）：
  "poses": { "stand": { "base": null, "R_Upperarm": {"pitch": 10, "yaw": 0, "roll": -60, "move": [0,0,0]} , ... } }
  角度单位度，都在"角色坐标系"里：pitch 绕角色的左右轴（正 = 骨头远端往前甩），
  yaw 绕上下轴（正 = 往左转），roll 绕前后轴（正 = 远端往左倒）。move 是 [左, 前, 上] 位移，模型单位（全身高 1.0）。
  旋转是在绑定姿势基础上追加的，父骨头转了子骨头跟着走。"base" 指向另一个姿势先套用再覆盖。
  "animations": { "idle_k": {"fps": 24, "keys": [["stand", 0], ["breathe", 48], ["stand", 96]]} }
  同一姿势连续两个关键帧 = 停顿。关键帧之间贝塞尔缓动。

用法：
  Blender -b --python tools/blender_pose_anim.py -- --in assets/processed/kusuriuri_v1_anim_lite.glb \
      --poses tools/poses/kusuriuri.json --out assets/processed/kusuriuri_v1_posed.glb \
      [--render 输出目录] [--drop-presets] [--only idle_k walk_k]
"""
import argparse, json, math, os, sys
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True)
p.add_argument("--poses", required=True)
p.add_argument("--out")
p.add_argument("--render")
p.add_argument("--drop-presets", action="store_true")
p.add_argument("--only", nargs="*")
p.add_argument("--props", help="道具 GLB 目录（assets/processed/props）。给了就在检查图里把道具挂上，导出的 GLB 不含道具")
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
spec = json.load(open(a.poses, encoding="utf-8"))
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
# 形态键先全部归零：导出时当前值会变成网格的默认权重（妖化只在 exorcise_k 里打开）
for _o in bpy.data.objects:
    if _o.type == "MESH" and _o.data.shape_keys:
        for _kb in _o.data.shape_keys.key_blocks: _kb.value = 0.0
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
scene = bpy.context.scene
scene.render.fps = 24

# ---- 角色坐标系：上 = 世界 Z，左 = 左锁骨尾到右锁骨尾（投影到地面），前 = 左 × 上 ----
def tail_w(name):
    b = arm.data.bones[name]; return arm.matrix_world @ b.tail_local
L = tail_w("L_Clavicle") - tail_w("R_Clavicle"); L.z = 0; L.normalize()
UP = Vector((0, 0, 1)); FRONT = L.cross(UP).normalized()
# pose_bone.matrix 是骨架对象坐标系，不是世界坐标。骨架对象本身可能被转过（blender_lite 统一朝向），
# 所以摆姿势用的轴要换算到骨架坐标；世界坐标的轴只给渲染相机用。
_inv = arm.matrix_world.to_3x3().inverted()
L_A, UP_A, FRONT_A = (_inv @ L).normalized(), (_inv @ UP).normalized(), (_inv @ FRONT).normalized()
print(f"[pose] left={tuple(round(x,2) for x in L)} front={tuple(round(x,2) for x in FRONT)} (骨架坐标 front={tuple(round(x,2) for x in FRONT_A)})")

def rot_about(axis, deg, pivot):
    return Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-pivot)

def depth(b):
    d = 0
    while b.parent: b = b.parent; d += 1
    return d
ORDER = sorted(arm.pose.bones, key=lambda pb: depth(pb.bone))

def reset_pose():
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()

def resolve(name, seen=()):
    if name in seen: raise ValueError(f"姿势循环引用 {name}")
    d = dict(spec["poses"][name]); base = d.pop("base", None)
    out = resolve(base, seen + (name,)) if base else {}
    out.update(d); return out

BIND_FIX = spec.get("bind_fix", {})  # 先把这个模型的绑定姿势扳到"手臂自然下垂"，再叠姿势库的角度；换模型只改这里

def rot_spec(s, head):
    R = Matrix.Identity(4)
    if s.get("pitch"): R = rot_about(L_A, s["pitch"], head) @ R
    if s.get("roll"):  R = rot_about(FRONT_A, s["roll"], head) @ R
    if s.get("yaw"):   R = rot_about(UP_A, s["yaw"], head) @ R
    return R

def apply_pose(name):
    reset_pose()
    bones = resolve(name)
    for pb in ORDER:
        s = bones.get(pb.name); fix = BIND_FIX.get(pb.name)
        if not s and not fix: continue
        M = pb.matrix.copy(); head = M.translation.copy()
        if s and s.get("world"):
            # 朝向不继承父骨头这一帧的转动：先回到绑定朝向（位置跟着父骨头走），再叠这里写的角度。
            # 走路时骨盆扭转、侧倾，大腿用这个保持在角色的前后平面里摆，脚不会被骨盆带着往旁边甩
            M = Matrix.Translation(head) @ pb.bone.matrix_local.to_3x3().to_4x4()
        R = Matrix.Identity(4)
        if fix: R = rot_spec(fix, head) @ R
        if s:   R = rot_spec(s, head) @ R
        M2 = R @ M
        if s and s.get("move"):
            mv = s["move"]; M2 = Matrix.Translation(L_A * mv[0] + FRONT_A * mv[1] + UP_A * mv[2]) @ M2
        if s and s.get("local"):   # 骨头自身坐标轴的旋转（度），手指用：X = 指根连线，握拳就是绕 X 转
            lx, ly, lz = (math.radians(x) for x in s["local"])
            M2 = M2 @ (Matrix.Rotation(lz, 4, "Z") @ Matrix.Rotation(ly, 4, "Y") @ Matrix.Rotation(lx, 4, "X"))
        pb.matrix = M2
        if s and s.get("scale") is not None: pb.scale = (s["scale"],) * 3   # 缩放（手缩进袖子用），子骨头跟着缩
        bpy.context.view_layer.update()
    aim = bones.get("aim")
    if aim: apply_aim(aim, name)


def apply_aim(aim, pose_name):
    """aim = {"socket": 挂点名, "dir": [左, 前, 上]}：只转挂点所在的骨头（手腕），把挂点 +Z（剑身方向）转到 dir。
    相当于把瞄准约束烘进姿势。打印手腕转了多少度，超过 70° 看起来就像手腕折断了，要改手臂。"""
    sock = bpy.data.objects[aim["socket"]]
    pb = arm.pose.bones[sock.parent_bone]
    d = aim["dir"]; target = (L_A * d[0] + FRONT_A * d[1] + UP_A * d[2]).normalized()
    inv = arm.matrix_world.inverted()
    def blade():
        return (inv.to_3x3() @ (sock.matrix_world.to_3x3() @ Vector((0, 0, 1)))).normalized()
    # 先绕手骨自身的轴自转（前臂旋转，自然），把剑身转到离目标最近的位置；剩下的再弯手腕
    ax = (pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
    b = blade()
    bp = (b - ax * b.dot(ax)); tp = (target - ax * target.dot(ax))
    twist = 0.0
    if bp.length > 1e-4 and tp.length > 1e-4:
        bp.normalize(); tp.normalize()
        twist = math.atan2(ax.dot(bp.cross(tp)), bp.dot(tp))
    head = pb.matrix.translation.copy()
    R1 = Matrix.Rotation(twist, 4, ax)
    pb.matrix = Matrix.Translation(head) @ R1 @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()
    q = blade().rotation_difference(target)
    pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()
    ang = math.degrees(q.angle)
    print(f"[pose] 瞄准 {pose_name}: 前臂自转 {math.degrees(twist):.0f}°，手腕弯 {ang:.0f}°" + ("  ← 弯太多，改手臂" if ang > 60 else ""))

def capture_pose(name):
    """在没有动作驱动的状态下摆姿势，把每根骨头的基础旋转/位移记下来"""
    apply_pose(name)
    return {pb.name: (pb.rotation_quaternion.copy(), pb.location.copy(), pb.scale.copy()) for pb in arm.pose.bones}

def key_pose(basis, frame, scaled=(), chains=()):
    for pb in arm.pose.bones:
        # 骨链（下摆、大袖、长发）默认不进关键帧，查看器里由弹簧骨驱动；动作的姿势里写了某节骨链（走路时下摆跟腿摆），
        # 就给这个动作打它的帧，弹簧骨把它当目标形状、在上面叠余摆（web/src/spring.js）
        if pb.name.startswith("chain_") and pb.name not in chains: continue
        q, loc, sc = basis[pb.name]
        pb.rotation_quaternion = q; pb.location = loc; pb.scale = sc
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        pb.keyframe_insert("location", frame=frame)
        if pb.name in scaled: pb.keyframe_insert("scale", frame=frame)   # 只有这个动作里缩放过的骨头才打缩放帧

# ---- 挂点 ----
# spec["sockets"] 里每一项生成一个空节点，挂在指定骨头上（parent_type=BONE），导出成那根骨头的子节点。
# 查看器按名字找到它，把道具 GLB 原样挂上去：道具的原点 = 挂点原点，道具的 +Z（Blender）= 挂点的 +Z。
#   palm  ：手掌中心。取这根骨头权重 > 0.5 的顶点做主成分分析：最长轴 = 手指方向，最短轴 = 掌心法线，
#           中间轴 = 握柄方向。挂点 +Z 沿握柄（flip 换向），-Y 沿手指（刀刃朝向），用来握剑。
#   back  ：背后表面。z = 骨头头部高度 + dz（按身高比例），y = 那一圈顶点里最靠后的（含头发），朝向和角色一致。
#   front ：腹前表面，同上取最靠前的，用来挂天秤。
# 朝向约定：blender_lite 已把角色转成面朝 -Y，所以"后" = +Y，"前" = -Y。
def mesh_world_verts(group=None, min_w=0.5):
    pts = []
    for o in bpy.data.objects:
        if o.type != "MESH": continue
        gi = o.vertex_groups[group].index if group and group in o.vertex_groups else None
        if group and gi is None: continue
        mw = o.matrix_world
        for v in o.data.vertices:
            if gi is not None:
                w = next((g.weight for g in v.groups if g.group == gi), 0.0)
                if w < min_w: continue
            pts.append(mw @ v.co)
    return pts

def make_sockets():
    socks = spec.get("sockets", {})
    if not socks: return {}
    reset_pose()
    import numpy as np
    allv = np.array([tuple(v) for v in mesh_world_verts()])
    H = allv[:, 2].max() - allv[:, 2].min()
    made = {}
    for name, d in socks.items():
        bone = arm.data.bones[d["bone"]]
        head = arm.matrix_world @ bone.head_local; tail = arm.matrix_world @ bone.tail_local
        if d["type"] == "palm":
            # 原点 = 这根骨头权重 > 0.5 的顶点的中心（掌心）。握柄方向（挂点 +Z）= 垂直于手骨、最接近参考方向的那个方向；
            # 参考方向默认是角色正前方（绑定姿势里手臂下垂，剑朝前伸出去），grip_ref 可改成 back/up/down/left/right。
            pts = np.array([tuple(v) for v in mesh_world_verts(d["bone"])])
            c = Vector(pts.mean(axis=0))
            along = (tail - head).normalized()
            refs = {"front": FRONT, "back": -FRONT, "up": UP, "down": -UP, "left": L, "right": -L}
            ref = refs[d.get("grip_ref", "front")]
            z = (ref - along * ref.dot(along)).normalized()
            y = -along; x = y.cross(z).normalized(); y = z.cross(x).normalized()
            M = Matrix((x, y, z)).transposed().to_4x4(); M.translation = c
            info = f"掌心 {len(pts)} 个顶点，握柄朝 {d.get('grip_ref', 'front')}"
        else:
            zc = head.z + d.get("dz", 0.0) * H
            src = np.array([tuple(v) for o in bpy.data.objects if o.type == "MESH" and o.name.split(".")[0] in d["meshes"]
                            for v in (o.matrix_world @ w.co for w in o.data.vertices)]) if d.get("meshes") else allv
            band = src[(np.abs(src[:, 2] - zc) < 0.03 * H) & (np.abs(src[:, 0] - head.x) < 0.06 * H)]
            # 用百分位数不用极值：翘起的发梢、衣角会把挂点拉离身体。pct 可改（背面默认 97、腹前默认 3），
            # meshes 只量这几个网格，inset 再往身体里收多少（模型单位，正值 = 往身体中心）
            pct = d.get("pct", 97 if d["type"] == "back" else 3)
            yy = np.percentile(band[:, 1], pct) + (-1 if d["type"] == "back" else 1) * d.get("inset", 0.0)
            M = Matrix.Translation(Vector((head.x, yy, zc)))
            info = f"{'背面' if d['type']=='back' else '腹前'} y={yy:.3f} z={zc:.3f}（{len(band)} 个顶点）"
        e = bpy.data.objects.new(name, None); e.empty_display_type = "ARROWS"; e.empty_display_size = 0.05 * H
        scene.collection.objects.link(e)
        e.parent = arm; e.parent_type = "BONE"; e.parent_bone = d["bone"]
        bpy.context.view_layer.update()
        e.matrix_world = M
        bpy.context.view_layer.update()
        made[name] = e
        print(f"[pose] 挂点 {name} → {d['bone']}：{info}")
    return made

SOCKETS = make_sockets()

def attach_props():
    """检查图用：把道具 GLB 导进来挂到挂点上；返回 {道具名: 对象列表}，导出前删掉"""
    if not a.props or not spec.get("props"): return {}
    out = {}
    for pid, d in spec["props"].items():
        f = os.path.join(a.props, f"{pid}.glb")
        if not os.path.exists(f): print(f"[pose] 没有道具 {f}，跳过"); continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=f)
        new = [o for o in bpy.data.objects if o not in before]
        roots = [o for o in new if o.parent is None]
        sock = SOCKETS[d["socket"]]
        for r in roots:
            r.parent = sock; r.matrix_parent_inverse = Matrix.Identity(4); r.matrix_basis = Matrix.Identity(4)
        out[pid] = new
        print(f"[pose] 道具 {pid} 挂到 {d['socket']}")
    bpy.context.view_layer.update()
    return out

PROP_OBJS = attach_props()

# ---- 建动作 ----
if arm.animation_data is None: arm.animation_data_create()
if a.drop_presets:
    for tr in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(tr)
    for ac in list(bpy.data.actions): bpy.data.actions.remove(ac)
anims = spec["animations"]
names = a.only or list(anims)
arm.animation_data.action = None
for tr in arm.animation_data.nla_tracks: tr.mute = True
cache = {}
for name in names:
    for pose_name, _ in anims[name]["keys"]:
        if pose_name not in cache: cache[pose_name] = capture_pose(pose_name)
for tr in arm.animation_data.nla_tracks: tr.mute = False
for name in names:
    an = anims[name]
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    scaled = {b for pn, _ in an["keys"] for b, s in resolve(pn).items() if isinstance(s, dict) and s.get("scale") is not None}
    chains = {b for pn, _ in an["keys"] for b in resolve(pn) if b.startswith("chain_")}
    for pose_name, frame in an["keys"]:
        key_pose(cache[pose_name], frame, scaled, chains)
    # 关键帧默认就是贝塞尔自动钳制，等于姿势间缓入缓出，不用再改插值（Blender 5 的 Action 没有 fcurves 属性）
    act.use_frame_range = True; act.frame_range = (an["keys"][0][1], an["keys"][-1][1])
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new(); tr.name = name
    strip = tr.strips.new(name, int(an["keys"][0][1]), act)
    if hasattr(strip, "action_slot") and len(act.slots): strip.action_slot = act.slots[0]
    print(f"[pose] 动作 {name}: {len(an['keys'])} 个关键帧, {an['keys'][-1][1]} 帧")
arm.animation_data.action = None
reset_pose()

# ---- 形态键动画（妖化）：spec["morphs"][动作名][形态键名] = [[帧, 值], ...] ----
# 每个带这个形态键的网格建一条关键帧，放进和骨骼动作同名的 NLA 轨道；导出用 NLA_TRACKS 模式，同名轨道合成一个 glTF 动画
n_morph = 0
for anim_name, keys in spec.get("morphs", {}).items():
    if anim_name not in names: continue
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys]:
        sk = ob.data.shape_keys
        hit = [k for k in keys if k in sk.key_blocks]
        if not hit: continue
        if sk.animation_data is None: sk.animation_data_create()
        act = bpy.data.actions.new(f"{anim_name}__{ob.name}")
        sk.animation_data.action = act
        for kn in hit:
            kb = sk.key_blocks[kn]
            for fr, val in keys[kn]:
                kb.value = val; kb.keyframe_insert("value", frame=fr)
            kb.value = 0.0
        sk.animation_data.action = None
        tr = sk.animation_data.nla_tracks.new(); tr.name = anim_name
        st = tr.strips.new(anim_name, int(anims[anim_name]["keys"][0][1]), act)
        if hasattr(st, "action_slot") and len(act.slots): st.action_slot = act.slots[0]
        n_morph += 1
        print(f"[pose] 形态键动画 {anim_name} → {ob.name}：{hit}")

# ---- 渲染检查图 ----
if a.render:
    os.makedirs(a.render, exist_ok=True)
    for tr in arm.animation_data.nla_tracks: tr.mute = True
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = 540; scene.render.resolution_y = 900
    world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.83, 0.78, 1)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 3
    sun.rotation_euler = (math.radians(50), 0, math.radians(30)); scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.lens = 60
    lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
    for o in bpy.data.objects:
        if o.type == "MESH":
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    h = 1.0  # 模型全身高 1.0
    center = Vector((arm.matrix_world.translation.x, arm.matrix_world.translation.y, 0)) + UP * 0.5
    hip = arm.matrix_world @ arm.data.bones["Hip"].head_local; center.x, center.y = hip.x, hip.y
    cam.data.lens = 85
    def shoot(fname, dir_vec):
        pos = center + dir_vec.normalized() * 3.2
        cam.location = pos; cam.rotation_euler = (center - pos).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(a.render, fname); bpy.ops.render.render(write_still=True)
    poses = set(pn for name in names for pn, _ in anims[name]["keys"])
    for pn in sorted(poses):
        for pid, objs in PROP_OBJS.items():
            only = spec["props"][pid].get("poses")
            for o in objs: o.hide_render = bool(only) and pn not in only
        apply_pose(pn)
        shoot(f"{pn}_front.png", FRONT); shoot(f"{pn}_side.png", -L)
        print(f"[pose] 渲染 {pn}")
    reset_pose()
    for tr in arm.animation_data.nla_tracks: tr.mute = False

for objs in PROP_OBJS.values():
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
if a.out:
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=False,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_image_format="JPEG", export_jpeg_quality=85,
        export_animations=True, export_skins=True, export_yup=True,
        export_morph=True, export_morph_normal=False,
        export_animation_mode="NLA_TRACKS")   # 同名 NLA 轨道（骨骼 + 形态键）合成一个动画
    print(f"[pose] wrote {a.out} {os.path.getsize(a.out)/1e6:.1f} MB")
