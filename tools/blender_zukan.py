"""
药箱立绘（图鉴）：Blender 平光渲染模型（只显示贴图颜色、透明底），斜侧 30°，存 PNG；再用 tools/zukan_compose.py 贴到纸色底上。
  Blender -b --python tools/blender_zukan.py -- --in assets/processed/bakeneko_tv_posed.glb --out 临时.png [--yaw -65] [--frame 0] [--clip idle_k]
  --yaw -65：斜侧、脸朝画面左边，和其他立绘一致
模型朝 -Y（和药郎一样）。
"""
import argparse, math, sys
import bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser(); ap.add_argument("--in", dest="inp"); ap.add_argument("--out"); ap.add_argument("--yaw", type=float, default=35); ap.add_argument("--frame", type=int, default=0)
ap.add_argument("--clip", default="idle_k", help="用哪个动作的姿势（不写就是 idle_k，没有这个动作就保持导入时的）")
a = ap.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
_act = next((x for x in bpy.data.actions if x.name.split("|")[0] == a.clip or x.name.startswith(a.clip)), None)
for _o in bpy.data.objects:
    if _o.type == "ARMATURE" and _act is not None:
        _o.animation_data_create().action = _act
        try: _o.animation_data.action_slot = _act.slots[0]
        except Exception: pass
for o in list(bpy.data.objects):
    if o.name.startswith("Icosphere"): bpy.data.objects.remove(o)
sc = bpy.context.scene; sc.frame_set(a.frame)
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in bpy.data.objects:
    if o.type == "MESH":
        e = o.evaluated_get(dg); m = e.to_mesh(); pts += [o.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
c = (lo + hi) / 2; size = max(hi - lo)
cam = bpy.data.cameras.new("cam"); cam.type = "ORTHO"; cam.ortho_scale = size * 1.25
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
y = math.radians(a.yaw); d = Vector((-math.sin(y), -math.cos(y), 0.18)).normalized()   # 从角色前方偏左看过去，略俯视
co.location = c + d * size * 3
co.rotation_euler = (c - co.location).to_track_quat("-Z", "Y").to_euler()
sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading
sh.light = "FLAT"; sh.color_type = "TEXTURE"; sh.show_object_outline = False
sc.render.film_transparent = True; sc.render.resolution_x = 1400; sc.render.resolution_y = 1400
sc.view_settings.view_transform = "Standard"
sc.render.filepath = a.out; bpy.ops.render.render(write_still=True)
print("[zukan] wrote", a.out)
