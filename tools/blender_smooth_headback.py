"""
把"双面头"后脑勺那张脸的凸起（鼻子、眉骨、嘴）抹平：选出头部在头中心后面的顶点，按方向投影到一个椭球面上
（离选区边界近的渐变），让侧面剪影变成圆的后脑勺。试过反复拉普拉斯平滑（--mode smooth），整片往里缩、露出洞，不用（游14 徳次，配合 blender_head_back.py 涂色）。蒙皮权重、贴图 UV 不变，只动顶点位置。

  Blender -b --python tools/blender_smooth_headback.py -- --in assets/processed/tokuji_lite.glb --out assets/processed/tokuji_lite.glb \
      [--back 0.02] [--iters 60] [--top 0.55]
--back：离头中心往后多远的顶点才动（模型单位）；--top：头顶往上这么多倍头半径以上的不动（留住发髻）。
"""
import argparse, sys
import bpy, bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True); p.add_argument("--out", required=True)
p.add_argument("--back", type=float, default=0.02); p.add_argument("--iters", type=int, default=60)
p.add_argument("--top", type=float, default=0.55)
p.add_argument("--mode", choices=["ellipsoid", "smooth"], default="ellipsoid")
p.add_argument("--fade", type=float, default=0.03, help="从 --back 往后这么远的范围内渐变到完全投影")
a = p.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
L = arm.matrix_world @ arm.data.bones["L_Clavicle"].tail_local - arm.matrix_world @ arm.data.bones["R_Clavicle"].tail_local; L.z = 0; L.normalize()
BACK = -L.cross(Vector((0, 0, 1))).normalized()
neck_z = (arm.matrix_world @ arm.data.bones["Head"].head_local).z
moved = 0
for o in [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm and "Head" in o.vertex_groups]:
    gi = o.vertex_groups["Head"].index; mw = o.matrix_world; inv = mw.inverted()
    hw = {v.index: next((g.weight for g in v.groups if g.group == gi), 0.0) for v in o.data.vertices}
    head = [mw @ o.data.vertices[i].co for i, w in hw.items() if w > 0.5]
    hc = sum(head, Vector()) / len(head)
    r = max((p_ - hc).length for p_ in head) * 0.6
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    sel = []
    for v in bm.verts:
        w = mw @ v.co
        if hw[v.index] > 0.3 and w.z > neck_z and (w - hc).dot(BACK) > a.back and w.z < hc.z + a.top * r:
            sel.append(v)
    if a.mode == "smooth":   # 反复平滑：整片会往里缩、露出洞（试过，不用）
        for _ in range(a.iters):
            bmesh.ops.smooth_vert(bm, verts=sel, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    else:   # 投影到椭球：后、左右、上下三个半轴按选中区域的分位数取，凸起压回去、凹处推出来；离边界近的按距离渐变
        UP = Vector((0, 0, 1)); LAT = UP.cross(BACK)
        rel = [(mw @ v.co) - hc for v in sel]
        q = lambda xs, f: sorted(xs)[int(len(xs) * f)]
        ab = q([d.dot(BACK) for d in rel], 0.6); al = q([abs(d.dot(LAT)) for d in rel], 0.95); au = q([abs(d.dot(UP)) for d in rel], 0.95)
        print(f"[smooth] 椭球半轴 后 {ab:.3f} 左右 {al:.3f} 上下 {au:.3f}")
        for v, d in zip(sel, rel):
            n = d.normalized()
            rr = 1 / ((n.dot(BACK) / ab) ** 2 + (n.dot(LAT) / al) ** 2 + (n.dot(UP) / au) ** 2) ** 0.5
            t = min(1.0, max(0.0, (d.dot(BACK) - a.back) / a.fade))
            t = t * t * (3 - 2 * t)
            v.co = inv @ (hc + n * (d.length * (1 - t) + rr * t))
    bm.to_mesh(o.data); bm.free(); o.data.update(); moved += len(sel)
    print(f"[smooth] {o.name}: 头中心 {tuple(round(x, 3) for x in hc)}，平滑 {len(sel)} 个顶点 × {a.iters} 遍")
bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", export_draco_mesh_compression_enable=True,
                          export_draco_mesh_compression_level=6, export_image_format="JPEG", export_jpeg_quality=85,
                          export_animations=True, export_skins=True, export_yup=True)
print(f"[smooth] wrote {a.out}")
