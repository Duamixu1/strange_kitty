"""
量一个角色腿的尺寸，给 tools/walk_gen.py 换角色用（不同 Tripo 模型的骨架比例、绑定姿势的腿斜度都不一样）。

  Blender -b --python tools/rig_legs.py -- --in assets/processed/asa_lite.glb --height 1.46 --out tools/npc_poses/asa_legs.json

height：游戏里这个角色按包围盒归一到多高（米，见 web/src/data/tour/*.json 配角的 height；药郎 1.7）。
输出（米、度）：unit 1 模型单位多少米；每条腿 thigh / calf 侧面投影长度、绑定姿势往后斜的角度；hip_half 髋关节离 Hip 中心的左右距离；
ankle_rest 脚踝在髋关节外侧多少（左为正）；leg3d 大腿、小腿三维长度；hip_z / ankle_z 绑定姿势髋关节、脚踝离地高度；arm_abduct 上臂张开角。
"""
import argparse, json, math, sys
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True)
p.add_argument("--height", type=float, required=True)
p.add_argument("--out", required=True)
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
lo, hi = 1e9, -1e9
for o in bpy.data.objects:
    if o.type != "MESH" or o.parent != arm: continue
    for c in o.bound_box:
        z = (o.matrix_world @ Vector(c)).z; lo = min(lo, z); hi = max(hi, z)
U = a.height / (hi - lo)
W = lambda b, tail=False: arm.matrix_world @ (arm.data.bones[b].tail_local if tail else arm.data.bones[b].head_local)
Lv = W("L_Clavicle", True) - W("R_Clavicle", True); Lv.z = 0; Lv.normalize()
UP = Vector((0, 0, 1)); FRONT = Lv.cross(UP).normalized()
hipc = W("Hip")
out = {"unit": round(U, 4), "height": a.height, "hip_z": round((W("L_Thigh").z - lo) * U, 4), "ankle_z": round((W("L_Foot").z - lo) * U, 4),
       "leg": {}, "hip_half": {}, "ankle_rest": {}}
for s in "LR":
    seg = {}
    for b in ("Thigh", "Calf"):
        d = W(f"{s}_{b}", True) - W(f"{s}_{b}")
        fwd, up = d.dot(FRONT), d.z
        seg[b] = (round(math.hypot(fwd, up) * U, 4), round(math.degrees(math.atan2(-fwd, -up)), 2))   # 侧面投影长度、往后斜（正 = 往后）
    out["leg"][s] = [seg["Thigh"][0], seg["Calf"][0], seg["Thigh"][1], seg["Calf"][1]]
    # 三维长度：A 字站姿的腿往外斜，侧面投影比真腿短；走路时腿收到竖直，长度要按三维的算，不然脚踝落得比算的低
    out.setdefault("leg3d", {})[s] = [round((W(f"{s}_{b}", True) - W(f"{s}_{b}")).length * U, 4) for b in ("Thigh", "Calf")]
    out["hip_half"][s] = round(abs((W(f"{s}_Thigh") - hipc).dot(Lv)) * U, 4)
    out["ankle_rest"][s] = round((W(f"{s}_Foot") - W(f"{s}_Thigh")).dot(Lv) * U, 4)
# 上臂张开角（正面看，上臂和竖直向下的夹角，度）：配角姿势库的 bind_fix 按它把 A 字手臂放下
out["arm_abduct"] = {}
for s in "LR":
    d = W(f"{s}_Upperarm", True) - W(f"{s}_Upperarm")
    out["arm_abduct"][s] = round(math.degrees(math.atan2(abs(d.dot(Lv)), -d.z)), 1)
json.dump(out, open(a.out, "w"), indent=1)
print("[legs]", json.dumps(out, ensure_ascii=False))
