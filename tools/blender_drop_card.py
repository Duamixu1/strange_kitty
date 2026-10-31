"""
删掉 Tripo 模型头上的"薄片"：发梳、发簪之类细小饰物有时被做成一整片薄平板，侧面看是一块方片（游14 志乃）。
按连通块找：脖子以上、某一个方向厚度不到 --thin（模型单位，身高约 1.0，默认 0.004）、面积够大的块，整块删掉再导出。

  Blender -b --python tools/blender_drop_card.py -- --in assets/processed/shino_lite.glb --out assets/processed/shino_lite.glb [--dry]
--dry 只打印找到的块（中心、尺寸、面数），不删。头发卷、碎发也是小块，阈值放松时用 --near x,y,z --radius r 圈定位置（先 --dry 看中心坐标）。
志乃：先默认阈值删掉两小片，再 --thin 0.015 --min-size 0.035 --axis x --near 0.026,0.1,0.9 --radius 0.045 删掉那块 16×18 厘米的发梳板和它下面两片。
"""
import argparse, sys
import bpy, bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True); p.add_argument("--out")
p.add_argument("--thin", type=float, default=0.004); p.add_argument("--min-size", type=float, default=0.03)
p.add_argument("--dry", action="store_true")
p.add_argument("--near", help="只删中心在这个点附近的块：x,y,z（模型单位，Blender 坐标）")
p.add_argument("--radius", type=float, default=0.06)
p.add_argument("--axis", choices=["x", "y", "z"], help="只删在这个方向最薄的块（薄板朝向，Blender 坐标）")
a = p.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
neck_z = (arm.matrix_world @ arm.data.bones["Head"].head_local).z
removed = 0
for o in [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]:
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    mw = o.matrix_world; seen = set(); kill = []
    for f0 in bm.faces:
        if f0.index in seen: continue
        comp, stack = [], [f0]; seen.add(f0.index)
        while stack:   # 按共用顶点连通
            f = stack.pop(); comp.append(f)
            for v in f.verts:
                for g in v.link_faces:
                    if g.index not in seen: seen.add(g.index); stack.append(g)
        pts = [mw @ v.co for f in comp for v in f.verts]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        dim = hi - lo; c = (hi + lo) / 2
        dims = sorted(dim)
        near = Vector(map(float, a.near.split(","))) if a.near else None
        if near is not None and (c - near).length > a.radius: continue
        if a.axis and min(range(3), key=lambda k: dim[k]) != "xyz".index(a.axis): continue
        if c.z > neck_z and dims[0] < a.thin and dims[1] > a.min_size:
            print(f"[card] {o.name} 块 中心 {tuple(round(x, 3) for x in c)} 尺寸 {tuple(round(x, 4) for x in dim)} {len(comp)} 个面")
            kill.extend(comp)
    if kill and not a.dry:
        bmesh.ops.delete(bm, geom=list(set(kill)), context="FACES"); bm.to_mesh(o.data); removed += len(set(kill))
    bm.free()
print(f"[card] 删了 {removed} 个面")
if a.out and not a.dry:
    bpy.ops.export_scene.gltf(filepath=a.out, export_format="GLB", export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=6, export_image_format="JPEG", export_jpeg_quality=85,
                              export_animations=True, export_skins=True, export_yup=True)
    print(f"[card] wrote {a.out}")
