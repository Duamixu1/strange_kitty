"""
把 Tripo 原始模型（没绑骨）转一圈渲染，绑骨前先检查（比如后脑勺有没有长出一张脸，游14 徳次）。

  Blender -b --python tools/blender_turnaround.py -- --in assets/tripo_raw/tokuji3.glb --out 目录
  → 目录/turn_{front,right,back,left,headback}.png（正、右、背、左、后脑勺近景），贴图原色，不打光
"""
import argparse, math, os, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser(); p.add_argument("--in", dest="inp", required=True); p.add_argument("--out", required=True)
a = p.parse_args(argv)
os.makedirs(a.out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
sc = bpy.context.scene
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for o in meshes:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
ctr = (lo + hi) / 2; H = hi.z - lo.z
# 贴图原色：把每个材质的 Base Color 直接接到 Emission，不受光照影响
for m in bpy.data.materials:
    if not m.use_nodes: continue
    nt = m.node_tree; bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None); out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if not bsdf or not out: continue
    em = nt.nodes.new("ShaderNodeEmission")
    link = next((l for l in nt.links if l.to_socket == bsdf.inputs["Base Color"]), None)
    if link: nt.links.new(link.from_socket, em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
sc.render.resolution_x = 600; sc.render.resolution_y = 900
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.88, 0.82, 1)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 85
# Tripo 导入后人朝 -Y 还是 +X 不一定：取包围盒较薄的水平轴当前后
fwd = Vector((0, -1, 0)) if (hi.y - lo.y) < (hi.x - lo.x) else Vector((1, 0, 0))
side = fwd.cross(Vector((0, 0, 1)))
def shoot(name, d, target, dist):
    cam.location = target + d.normalized() * dist
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(a.out, f"turn_{name}.png"); bpy.ops.render.render(write_still=True)
for name, d in (("front", fwd), ("right", side), ("back", -fwd), ("left", -side)):
    shoot(name, d, ctr, H * 3.4)
head = Vector((ctr.x, ctr.y, hi.z - H * 0.08))
shoot("headback", -fwd + Vector((0, 0, 0.15)), head, H * 0.9)
print(f"[turn] → {a.out}")
