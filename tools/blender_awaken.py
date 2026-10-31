"""
妖化形态（退魔三拍第 2 拍）：头发散开成火焰形 + 瞳孔缩小 + 露齿，做成形态键，交给 blender_pose_anim.py 烘进 exorcise_k。

  Blender -b --python tools/blender_awaken.py -- --stage render --in assets/processed/kusuriuri_v2_layered.glb
      → assets/processed/kusuriuri_awaken_face_base.png（脸部正面原色图）+ kusuriuri_awaken_face.json（相机参数、眼和嘴的框）
  uv run tools/awaken_face.py     → assets/processed/kusuriuri_awaken_face.png（缩瞳、露齿后的脸）
  Blender -b --python tools/blender_awaken.py -- --stage build --in assets/processed/kusuriuri_v2_layered.glb \
      --out assets/processed/kusuriuri_v2_layered_awaken.glb

形态键（导出到 glTF 是 morph target，名字照写）：
  awaken_hair   头发散开：头发顶点往外、往上飘成火焰形，发梢动得最多，头顶不动（在 kusuriuri_body、kusuriuri_hair 两个网格上）
                分成 22 缕，缕和缕之间凹成沟（10-31 第二版，第一版整片拉开像一张布）
  awaken_hair2  同样散开，缕的分界错开半缕、长短卷法另一套；exorcise_k 里两个交替播，火舌一跳一跳地动
  awaken_eyes   瞳孔缩小：两只眼睛上各一块贴片（kusuriuri_awaken_eyes），平时藏在脸皮后面，打开时翻到脸皮前面
  awaken_mouth  露齿：嘴上一块贴片（kusuriuri_awaken_mouth），同上
为什么表情用贴片：Tripo 的脸是画在贴图上的，而且脸在贴图里被切成很多碎块，形态键改不了瞳孔大小也张不了嘴，
所以从正面渲一张脸，在平面图上改好表情，再贴回脸上。
"""
import argparse, json, math, os, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--stage", choices=["render", "build"], required=True)
ap.add_argument("--in", dest="inp", required=True)
ap.add_argument("--out")
a = ap.parse_args(argv)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(ROOT, "assets/processed")
META = os.path.join(OUTDIR, "kusuriuri_awaken_face.json")
BASE_PNG = os.path.join(OUTDIR, "kusuriuri_awaken_face_base.png")
FACE_PNG = os.path.join(OUTDIR, "kusuriuri_awaken_face.png")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
hh = arm.matrix_world @ arm.data.bones["Head"].head_local
C = Vector((hh.x, hh.y, 0.865)); S = 0.11; RES = 1024          # 脸部正面的正交相机：中心、取景宽度（模型单位）、像素
body = bpy.data.objects["kusuriuri_body"]

def to_px(p): return ((p.x - C.x) / S + 0.5) * RES, (0.5 - (p.z - C.z) / S) * RES

def skin_polys():
    """朝前的面里，每个 4 毫米格子只取最靠后的那一层 = 脸皮（挡在脸前的头发更靠前）"""
    me = body.data; mw = body.matrix_world; cells = {}; info = []
    for p in me.polygons:
        c = mw @ p.center; n = (mw.to_3x3() @ p.normal).normalized()
        if abs(c.x - C.x) > S / 2 or abs(c.z - C.z) > S / 2 or n.y > -0.3 or c.y > hh.y: continue
        key = (int(math.floor((c.x - C.x) / 0.004)), int(math.floor((c.z - C.z) / 0.004)))
        info.append((p.index, key, c.y, c)); cells[key] = max(cells.get(key, -1e9), c.y)
    return [(i, c) for i, key, y, c in info if y > cells[key] - 0.004]

if a.stage == "render":
    for o in bpy.data.objects:
        if o.type != "MESH": continue
        for m in o.data.materials:
            nt = m.node_tree; img = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image), None)
            if not img: continue
            em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(img.outputs[0], em.inputs[0])
            nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = RES
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = S
    cam.location = C + Vector((0, -1, 0)); cam.rotation_euler = Vector((0, 1, 0)).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = BASE_PNG; bpy.ops.render.render(write_still=True)
    meta = {"_说明": "脸部正面正交相机：center 为相机中心（Blender 世界坐标，模型单位），width 为取景宽度，res 为像素。boxes 是眼和嘴贴片的范围（像素，左上为原点），右眼 = 画面左边那只；左眼框只取头发右边露出来的部分。",
            "center": list(C), "width": S, "res": RES,
            "boxes": {"eye_R": [105, 255, 330, 360], "eye_L": [590, 245, 790, 350], "mouth": [255, 640, 545, 740]}}
    if os.path.exists(META):   # 保留手调过的框
        meta["boxes"] = json.load(open(META, encoding="utf-8")).get("boxes", meta["boxes"])
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[awaken] 渲好 {BASE_PNG}，参数 {META}")
    sys.exit(0)

# ======================================================================
# build
# ======================================================================
meta = json.load(open(META, encoding="utf-8"))
C = Vector(meta["center"]); S = meta["width"]; RES = meta["res"]

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

# ---- 1. 表情贴片：复制眼、嘴所在的脸皮面片，按正面相机投影出新 UV，换成改好的脸 ----
skin = skin_polys()
def decal(name, boxes, key):
    keep = set()
    for i, c in skin:
        px, py = to_px(c)
        if any(b[0] <= px <= b[2] and b[1] <= py <= b[3] for b in boxes): keep.add(i)
    ob = body.copy(); ob.data = body.data.copy(); ob.name = name; ob.data.name = name
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # 新 UV：正面正交投影
    uv = bm.loops.layers.uv.active
    mw = ob.matrix_world
    for f in bm.faces:
        for l in f.loops:
            w = mw @ l.vert.co
            l[uv].uv = ((w.x - C.x) / S + 0.5, (w.z - C.z) / S + 0.5)
    bm.to_mesh(ob.data); bm.free()
    me = ob.data
    me.materials.clear()
    mat = bpy.data.materials.new(f"{name}_mat"); mat.use_nodes = True; nt = mat.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(FACE_PNG); tex.image.pack()
    nt.links.new(tex.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    me.materials.append(mat)
    # 形态键：平时藏在脸皮后面 1.2 毫米，打开时在脸皮前面 1.5 毫米（模型单位 1.0 = 身高 1.7 米）
    me.calc_normals_split() if hasattr(me, "calc_normals_split") else None
    rest = [v.co.copy() for v in me.vertices]; nrm = [v.normal.copy() for v in me.vertices]
    for v, p, n in zip(me.vertices, rest, nrm): v.co = p - n * 0.0007
    ob.shape_key_add(name="Basis", from_mix=False)
    k = ob.shape_key_add(name=key, from_mix=False)
    for i, (p, n) in enumerate(zip(rest, nrm)): k.data[i].co = p + n * 0.0009
    print(f"[awaken] 贴片 {name}：{len(me.polygons)} 个面，形态键 {key}")
    return ob

B = meta["boxes"]
eyes_ob = decal("kusuriuri_awaken_eyes", [B["eye_R"], B["eye_L"]], "awaken_eyes")
mouth_ob = decal("kusuriuri_awaken_mouth", [B["mouth"]], "awaken_mouth")

# ---- 2. 头发散开：头发顶点往外、往上飘成火焰形 ----
hair_meshes = [bpy.data.objects[n] for n in ("kusuriuri_body", "kusuriuri_hair") if n in bpy.data.objects]
img = next(n.image for n in body.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE" and n.image)
iw, ih = img.size; px = np.array(img.pixels[:]).reshape(ih, iw, 4)
recs = []   # (mesh, 顶点序号, 世界坐标, 颜色, 手的权重)
for ob in hair_meshes:
    me = ob.data; mw = ob.matrix_world; uvl = me.uv_layers.active.data
    vuv = np.zeros((len(me.vertices), 2))
    for poly in me.polygons:
        for li in poly.loop_indices: vuv[me.loops[li].vertex_index] = uvl[li].uv
    col = px[np.clip((vuv[:, 1] * (ih - 1)).astype(int), 0, ih - 1), np.clip((vuv[:, 0] * (iw - 1)).astype(int), 0, iw - 1), :3]
    col = np.clip(col, 0, 1) ** (1 / 2.2)
    hand_g = [ob.vertex_groups[n].index for n in ob.vertex_groups.keys() if "Hand" in n or "Fingers" in n]
    for v in me.vertices:
        hw = sum(g.weight for g in v.groups if g.group in hand_g)
        recs.append((ob, v.index, mw @ v.co, col[v.index], hw))
Pw = np.array([tuple(r[2]) for r in recs]); Cc = np.array([r[3] for r in recs]); HW = np.array([r[4] for r in recs])
r_, g_, b_ = Cc[:, 0], Cc[:, 1], Cc[:, 2]
pale = (np.min(Cc, axis=1) > 0.62) & ((np.max(Cc, axis=1) - np.min(Cc, axis=1)) < 0.25)
pink = (r_ > 0.72) & (g_ > 0.45) & (g_ < 0.8) & (b_ > g_ - 0.02) & ((r_ - g_) > 0.1) & ((r_ - g_) < 0.42)
HC = Vector((hh.x, hh.y + 0.01, 0.86))
# 只靠颜色在衣身上不可靠（衣服上偏浅的部分、腰带会被带着抬起来），所以分两块、各用确定的规则：
#   头部周围：帽子以下、下巴以上的浅色顶点，避开脸；往下 8 厘米软过渡，胸前那几缕不动
#   背后长发：分层时已经分好的 kusuriuri_hair 网格，整块都算
is_hairmesh = np.array([r[0].name == "kusuriuri_hair" for r in recs])
face_box = (np.abs(Pw[:, 0] - hh.x) < 0.06) & (Pw[:, 1] < hh.y + 0.005) & (Pw[:, 2] > 0.70) & (Pw[:, 2] < 0.93)
head_raw = ((pale | pink) & ~is_hairmesh & ~face_box & (HW < 0.2) & (Pw[:, 2] < 0.95)).astype(float) * sstep(0.70, 0.78, Pw[:, 2])
raw = np.maximum(head_raw, is_hairmesh.astype(float))
kd = KDTree(len(Pw))
for i, p in enumerate(Pw): kd.insert(p, i)
kd.balance()
sm = np.array([np.mean([raw[j] for _, j, _ in kd.find_range(p, 0.016)]) for p in Pw])
mask = raw * sstep(0.3, 0.6, sm)          # 平滑只用来剔掉零星的浅色点，不往外扩到旁边的衣服
d = Pw - np.array(HC); ang = np.arctan2(d[:, 1], d[:, 0])
out0 = d[:, :2] / np.maximum(np.linalg.norm(d[:, :2], axis=1, keepdims=True), 1e-6)
out0[:, 1] = np.where(out0[:, 1] > 0, out0[:, 1] * 0.3, out0[:, 1])   # 往后（+Y）的分量压到三成：背后有药箱，火焰从两侧和头周围冒出来
out0 /= np.maximum(np.linalg.norm(out0, axis=1, keepdims=True), 1e-6)
headlvl = sstep(0.95, 0.84, Pw[:, 2]) * sstep(0.70, 0.78, Pw[:, 2])   # 头部周围：帽檐下面到下巴
hang = np.clip((0.78 - Pw[:, 2]) / 0.3, 0, 1)                         # 背后长发：越往下越飘
N_LOCK = 22


def flame(seed, shift):
    """一套"分缕"的火焰形位移（10-31 第二版）。第一版是整片头发按 5 股正弦一起往外推，贴图被拉成一整片（翻车集 009）。
    现在绕头分 N_LOCK 缕，越往下越拧（火舌打旋）；每缕长短、往上翘、往旁边卷各不一样（seed 定），
    缕的中间推得最远、两缕交界处只推三成，交界处凹下去成一道沟，平涂的明暗和描边的内线（法线差）会沿着沟画出一缕一缕的发丝；
    每缕里再加 5 道细褶，像发丝。shift：缕的分界整体转多少（0~1 缕），两套错开交替播，火舌会动"""
    rng = np.random.default_rng(seed)
    L = rng.uniform(0.55, 1.45, N_LOCK); U = rng.uniform(0.75, 1.35, N_LOCK); CU = rng.uniform(-0.6, 0.6, N_LOCK)
    a = ang + 1.1 * (0.86 - Pw[:, 2]) + 2 * math.pi * shift / N_LOCK
    x = (a + math.pi) / (2 * math.pi) * N_LOCK
    k = np.floor(x).astype(int) % N_LOCK; uc = 2 * (x - np.floor(x)) - 1
    w = 1 - np.abs(uc) ** 1.6
    prof = 0.3 + 0.7 * w * L[k] + 0.06 * np.sin(x * 2 * math.pi * 5)       # 交界处统一 0.3，相邻两缕在沟里接得上，网格不撕开
    tip = hang ** 1.5
    th = CU[k] * tip * 0.9 * w                                            # 发梢往旁边卷（火舌打旋），缕中间卷得最多
    c, s_ = np.cos(th), np.sin(th)
    out = np.stack([out0[:, 0] * c - out0[:, 1] * s_, out0[:, 0] * s_ + out0[:, 1] * c], axis=1)
    spread = (0.065 * headlvl + 0.075 * hang ** 0.8) * prof
    lift = (0.02 * headlvl + 0.11 * hang ** 1.1) * (0.4 + 0.6 * w * U[k]) + 0.04 * tip * w * (U[k] - 0.75)
    disp = np.zeros_like(Pw); disp[:, :2] = out * spread[:, None]; disp[:, 2] = lift
    return disp * mask[:, None]


SETS = {"awaken_hair": flame(7, 0.0), "awaken_hair2": flame(23, 0.5)}
for name, disp in SETS.items():
    print(f"[awaken] {name}：{int((mask > 0.5).sum())} 个顶点，发梢最多抬高 {disp[:, 2].max():.3f}、外扩 {np.linalg.norm(disp[:, :2], axis=1).max():.3f}（模型单位）")
for ob in hair_meshes:
    ob.shape_key_add(name="Basis", from_mix=False)
    for name in SETS: ob.shape_key_add(name=name, from_mix=False)
inv = {ob.name: ob.matrix_world.inverted().to_3x3() for ob in hair_meshes}
for name, disp in SETS.items():
    for (ob, vi, _, _, _), dv in zip(recs, disp):
        if not dv.any(): continue
        kb = ob.data.shape_keys.key_blocks[name]
        kb.data[vi].co = kb.data[vi].co + inv[ob.name] @ Vector(tuple(dv))

# 形态键的当前值会被导出成网格的默认权重，必须是 0，否则不播妖化时头发也是散开的
for ob in bpy.data.objects:
    if ob.type == "MESH" and ob.data.shape_keys:
        for kb in ob.data.shape_keys.key_blocks: kb.value = 0.0

if a.out:
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=False,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
        export_image_format="JPEG", export_jpeg_quality=88, export_animations=False, export_skins=True,
        export_morph=True, export_morph_normal=True,   # 形态键带法线：分缕的沟才有明暗和内线（10-31 第二版）
        export_yup=True)
    print(f"[awaken] wrote {a.out} {os.path.getsize(a.out)/1e6:.1f} MB")
