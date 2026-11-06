"""
无面（のっぺらぼう）的脸：Tripo 把白漆能面那样的脸做成了黑头发（翻车集 011）。第一次在贴图上直接涂（脚本已删），
头发表面坑坑洼洼，白色涂歪了、隈取像刀痕（11-04 用户：“这个脸咋了”）。这里改成另外加一张面具：
  1. 在脸的位置铺一张椭圆网格（方格映射到圆盘，24×32），每个点从正前方往后打射线落到头上，
  2. 落点拟合成一张光滑的二次曲面（头发丝的起伏不跟），整体往前挪到头的前面，
  3. UV 按圆盘排，贴 tools/noppera_mask_tex.py 画的贴图，全部权重给 Head 骨，跟着头动。
  Blender -b --python tools/blender_add_mask.py -- --in assets/processed/noppera_lite_nomask.glb --tex assets/processed/noppera_mask.png --out assets/processed/noppera_lite.glb
模型坐标：身高 1.0，朝 -Y。FACE 是椭圆中心（左右、高度）和半宽、半高，按 Head 骨头和正面深度图量的。
"""
import argparse, sys
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp"); ap.add_argument("--tex"); ap.add_argument("--out")
ap.add_argument("--face", help="cx,cz,w,h：脸的椭圆中心（左右、高度）和半宽、半高，模型单位。不给就是无面的值；--face auto 按 Head 骨量")
ap.add_argument("--cut", action="store_true", help="按贴图轮廓裁网格：从四角漫水填充底色，落在底色上的格子删掉（狐面具，管线贴图都是 JPEG，不能靠透明）")
ap.add_argument("--grid", default="24,32", help="网格格数 NU,NV（--cut 时用细一点，比如 72,96）")
ap.add_argument("--name", default="noppera_mask", help="面具网格和材质的名字（狐面男用 kitsune_mask，代码按名字找来摘下）")
a = ap.parse_args(argv)
FACE = dict(cx=0.011, cz=0.905, w=0.052, h=0.068)
if a.face and a.face != "auto": FACE = dict(zip(["cx", "cz", "w", "h"], map(float, a.face.split(","))))
NU, NV = map(int, a.grid.split(","))
IN = None   # --cut：贴图里面具形状内为 True（行 0 在下，跟 Blender 的 UV 一样）
if a.cut:
    img = bpy.data.images.load(bpy.path.abspath(a.tex)); W, H = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)[:, :, :3]
    bg = px[0, 0]; near = np.abs(px - bg).max(-1) < 0.08
    reg = np.zeros_like(near); reg[0, :] = reg[-1, :] = reg[:, 0] = reg[:, -1] = True; reg &= near
    while True:
        g = reg.copy(); g[1:] |= reg[:-1]; g[:-1] |= reg[1:]; g[:, 1:] |= reg[:, :-1]; g[:, :-1] |= reg[:, 1:]; g &= near
        if (g == reg).all(): break
        reg = g
    IN = ~reg
    print(f"[mask] 贴图里面具占 {IN.mean() * 100:.0f}%")
    inside = lambda u, v: IN[min(H - 1, int(v * H)), min(W - 1, int(u * W))]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world); bvh = BVHTree.FromBMesh(bm)

# 1. 方格 → 圆盘（等面积那种映射，边上不挤），再落到头上
uu, vv = np.meshgrid(np.linspace(-1, 1, NU + 1), np.linspace(-1, 1, NV + 1))
du = uu * np.sqrt(1 - vv ** 2 / 2); dv = vv * np.sqrt(1 - uu ** 2 / 2)
X = FACE["cx"] + du * FACE["w"]; Z = FACE["cz"] + dv * FACE["h"]
hit = np.full(X.shape, np.nan)
for i in np.ndindex(X.shape):
    loc, *_ = bvh.ray_cast(Vector((X[i], -1.0, Z[i])), Vector((0, 1, 0)))
    if loc: hit[i] = loc.y
ok = ~np.isnan(hit)
if IN is not None: ok &= np.vectorize(lambda x, y: inside((x + 1) / 2, (y + 1) / 2))(du, dv)
print(f"[mask] 射线落到头上 {ok.sum()}/{ok.size}")
# 2. 拟合 y = c0 + c1 u + c2 v + c3 u² + c4 v² + c5 uv，然后整体往前挪，让 98% 的落点都在面具后面
A = np.stack([np.ones_like(du), du, dv, du ** 2, dv ** 2, du * dv], -1)
coef, *_ = np.linalg.lstsq(A[ok], hit[ok], rcond=None)
fit = A @ coef; res = hit - fit
shift = 0.005 + max(0.0, -np.quantile(res[ok], 0.02))
Y = fit - shift
print(f"[mask] 曲面 {np.round(coef, 4)}，往前挪 {shift * 1000:.1f} 毫米")

# 3. 建网格、UV、材质、权重
me = bpy.data.meshes.new(a.name); ob = bpy.data.objects.new(a.name, me); bpy.context.scene.collection.objects.link(ob)
verts = [(float(X[i]), float(Y[i]), float(Z[i])) for i in np.ndindex(X.shape)]
idx = lambda r, c: r * (NU + 1) + c
faces = [(idx(r, c), idx(r, c + 1), idx(r + 1, c + 1), idx(r + 1, c)) for r in range(NV) for c in range(NU)]
if IN is not None:   # 格子中心落在底色上的删掉，再删用不到的顶点（UV 按顶点号算，所以先建全网格再删）
    faces = [f for f in faces if inside((du.flat[f[0]] + du.flat[f[2]] + 2) / 4, (dv.flat[f[0]] + dv.flat[f[2]] + 2) / 4)]
me.from_pydata(verts, [], faces); me.update()
uvl = me.uv_layers.new(name="UVMap")
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index; r, c = divmod(vi, NU + 1)
        uvl.data[li].uv = ((du[r, c] + 1) / 2, (dv[r, c] + 1) / 2)
for poly in me.polygons: poly.use_smooth = True
if IN is not None:
    bm2 = bmesh.new(); bm2.from_mesh(me); bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if not v.link_faces], context="VERTS"); bm2.to_mesh(me); bm2.free()
mat = bpy.data.materials.new(a.name); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]; tn = mat.node_tree.nodes.new("ShaderNodeTexImage")
tn.image = bpy.data.images.load(bpy.path.abspath(a.tex)); mat.node_tree.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.6
me.materials.append(mat)
g = ob.vertex_groups.new(name="Head"); g.add(list(range(len(me.vertices))), 1.0, "REPLACE")
ob.parent = arm; ob.matrix_parent_inverse = arm.matrix_world.inverted()   # 扣掉骨架自己的旋转，不然导出后面具被转 90° 插进头里
md = ob.modifiers.new("Armature", "ARMATURE"); md.object = arm
print(f"[mask] 面具 {len(me.vertices)} 顶点，跟着 Head 骨")

bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", use_selection=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
    export_image_format="JPEG", export_jpeg_quality=85, export_normals=True, export_tangents=False, export_materials="EXPORT",
    export_animations=True, export_skins=True, export_yup=True, export_animation_mode="ACTIONS")
print(f"[mask] wrote {a.out}")
