"""
修 Tripo 多视图偶尔出的"双面头"：后脑勺的贴图上也画了一张脸（游14 徳次）。
找头部（Head 骨权重 > 0.5）里法线朝后、又不是朝上的面，把它们在贴图上占的三角形涂成头发色，再写回 GLB。

  第一步 导出：Blender -b --python tools/blender_head_back.py -- --in assets/processed/tokuji_lite.glb --dump 目录
            → 目录/tex.png（原贴图）、目录/tris.json（要涂的 UV 三角形，像素坐标）
  第二步 涂色：uv run tools/paint_tris.py 目录 --color 2a2230      （见 tools/paint_tris.py）
  第三步 写回：Blender -b --python tools/blender_head_back.py -- --in assets/processed/tokuji_lite.glb --tex 目录/tex_fixed.png --out assets/processed/tokuji_lite.glb
--back × 0.1 是离头中心往后多远才算后脑勺（模型单位，默认 0.025），--up 法线朝上的分量上限（默认 0.55，头顶剃发那块不涂）。
"""
import argparse, json, os, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True)
p.add_argument("--dump"); p.add_argument("--tex"); p.add_argument("--out")
p.add_argument("--back", type=float, default=0.25); p.add_argument("--up", type=float, default=0.55)
a = p.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
L = arm.matrix_world @ arm.data.bones["L_Clavicle"].tail_local - arm.matrix_world @ arm.data.bones["R_Clavicle"].tail_local; L.z = 0; L.normalize()
FRONT = L.cross(Vector((0, 0, 1))).normalized(); BACK = -FRONT
neck_z = (arm.matrix_world @ arm.data.bones["Head"].head_local).z

if a.dump:
    os.makedirs(a.dump, exist_ok=True)
    tris = []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.parent != arm: continue
        gi = o.vertex_groups["Head"].index if "Head" in o.vertex_groups else None
        if gi is None: continue
        me = o.data; uv = me.uv_layers.active.data; mw = o.matrix_world; nm = mw.to_3x3()
        img = next((n.image for m in me.materials if m and m.use_nodes for n in m.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
        if img is None: continue
        W, H = img.size
        if not os.path.exists(os.path.join(a.dump, "tex.png")):
            img.filepath_raw = os.path.join(a.dump, "tex.png"); img.file_format = "PNG"; img.save()
        hw = {v.index: next((g.weight for g in v.groups if g.group == gi), 0.0) for v in me.vertices}
        # 按位置挑：头部（Head 骨权重 > 0.3、在脖子以上）里位于头中心后面的面；法线太朝上的（头顶剃发）不涂。
        # 只按法线挑会漏：Tripo 后脑勺那张脸的面有的法线朝侧面
        hc = sum((mw @ me.vertices[i].co for i in hw if hw[i] > 0.5), Vector()) / max(1, sum(1 for i in hw if hw[i] > 0.5))
        for f in me.polygons:
            if min(hw[i] for i in f.vertices) < 0.3: continue
            n = (nm @ f.normal).normalized(); c = mw @ f.center
            if c.z < neck_z or (c - hc).dot(BACK) < a.back * 0.1 or n.z > a.up: continue
            tris.append([[uv[l].uv[0] * W, (1 - uv[l].uv[1]) * H] for l in f.loop_indices])
    json.dump({"size": [W, H], "tris": tris}, open(os.path.join(a.dump, "tris.json"), "w"))
    print(f"[head] 要涂 {len(tris)} 个面，贴图 {W}x{H}")
if a.tex and a.out:
    # glTF 导进来的贴图是打包在文件里的，改 filepath 再 reload 还是读包里那份；所以载入新图、换进材质节点
    new = bpy.data.images.load(os.path.abspath(a.tex)); new.pack()
    for m in bpy.data.materials:
        if not (m and m.use_nodes): continue
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image and n.image != new: n.image = new
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6, export_image_format="JPEG", export_jpeg_quality=85,
                              export_animations=True, export_skins=True, export_yup=True)
    print(f"[head] wrote {a.out}")
