"""
量走路动作：逐帧取两只脚踝（*_Foot 骨头头部）和脚尖（尾部）在角色坐标系里的位置，按 1.7 米身高换算成米，
算支撑脚的地面速度（贴地那只脚往后走的速度）、打滑（支撑期速度的波动）、抬脚高度、步幅。顺带打印腿骨长度。

  Blender -b --python tools/walk_measure.py -- --in assets/processed/kusuriuri_v2_posed_layered.glb --clip walk2_k [--csv 输出.csv]

支撑脚：两只脚里脚踝低的那只。地面速度 = 支撑期脚踝往后移的平均速度；查看器里身体按这个速度往前走，脚就不滑。
"""
import argparse, sys, math
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--in", dest="inp", required=True)
p.add_argument("--clip", required=True)
p.add_argument("--csv")
p.add_argument("--height", type=float, default=1.7, help="游戏里这个角色归一到多高（米）：药郎 1.7，阿浅 1.46、阿龟 1.42、歌山 1.57")
a = p.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a.inp)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc = bpy.context.scene

# 动作：glTF 导入后每个动画是一个 action（名字可能带后缀），挂到骨架上
act = next((ac for ac in bpy.data.actions if ac.name.split("|")[0].startswith(a.clip)), None)
if act is None: sys.exit(f"没找到动作 {a.clip}：{[ac.name for ac in bpy.data.actions]}")
if arm.animation_data is None: arm.animation_data_create()
for tr in arm.animation_data.nla_tracks: tr.mute = True
arm.animation_data.action = act
if hasattr(arm.animation_data, "action_slot") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
fps = sc.render.fps

def wpos(bone, tail=False):
    pb = arm.pose.bones[bone]; return arm.matrix_world @ (pb.tail if tail else pb.head)

# 身高：静止姿势下所有网格的包围盒（和查看器、游戏一样按包围盒归一到 1.7 米）
# 身高按绑定姿势量（游戏 player.js 加载时动作还没播，按绑定姿势的包围盒归一到 1.7 米）；走路第一帧会前倾下蹲，量出来偏矮、速度偏大 1%
arm.data.pose_position = "REST"; bpy.context.view_layer.update(); sc.frame_set(f0)
lo, hi = 1e9, -1e9
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "MESH" or o.parent != arm: continue   # 只算挂在骨架上的网格（导入时 Blender 会多出一个不相干的 Icosphere）
    for c in o.evaluated_get(dg).bound_box:
        z = (o.matrix_world @ Vector(c)).z; lo = min(lo, z); hi = max(hi, z)
S = a.height / (hi - lo)
arm.data.pose_position = "POSE"; bpy.context.view_layer.update(); sc.frame_set(f0)
# 左右轴用绑定姿势的锁骨（走路动作里上身会扭，用当前帧的锁骨量，前后行程会漏一部分进"左右晃"）
Lv = arm.matrix_world @ arm.data.bones["L_Clavicle"].tail_local - arm.matrix_world @ arm.data.bones["R_Clavicle"].tail_local; Lv.z = 0; Lv.normalize()
UP = Vector((0, 0, 1)); FRONT = Lv.cross(UP).normalized()
def char(v): return (v.dot(FRONT) * S, v.dot(Lv) * S, (v.z - lo) * S)   # 前、左、上（米）

rest = {b: (arm.data.bones[b].head_local, arm.data.bones[b].tail_local) for b in ("L_Thigh", "L_Calf", "L_Foot", "Hip")}
mw = arm.matrix_world.to_3x3()
lens = {b: ((mw @ (t - h)).length * S) for b, (h, t) in rest.items()}
print(f"[walk] 换算 {S:.4f} 米/单位；大腿 {lens['L_Thigh']:.3f} 米、小腿 {lens['L_Calf']:.3f}、脚 {lens['L_Foot']:.3f}；"
      f"髋（L_Thigh 头）高 {char(arm.matrix_world @ rest['L_Thigh'][0])[2]:.3f}，脚踝高 {char(arm.matrix_world @ rest['L_Foot'][0])[2]:.3f}")

rest_ankle = char(arm.matrix_world @ rest["L_Foot"][0])[2]   # 绑定姿势脚踝高度（同一个地面基准），支撑脚该踩在这个高度
rows = []
for f in range(f0, f1 + 1):
    sc.frame_set(f)
    r = {"f": f}
    for s in "LR":
        r[s] = char(wpos(f"{s}_Foot")); r[s + "t"] = char(wpos(f"{s}_Foot", True))
    r["hip"] = char(wpos("Hip"))
    rows.append(r)

# 支撑期 = 这只脚的脚踝在它自己最低点 0.5 厘米以内（脚跟抬起、摆动都不算）；相邻两帧都在支撑期时，记它往后移的速度
v = []
low = {s: min(r[s][2] for r in rows) for s in "LR"}
for s in "LR":
    for r0, r1 in zip(rows, rows[1:]):
        if r0[s][2] < low[s] + 0.005 and r1[s][2] < low[s] + 0.005: v.append(-(r1[s][0] - r0[s][0]) * fps)
print(f"[walk] 支撑期脚踝高度 L {low['L']:.3f} R {low['R']:.3f}（两边差 {100 * abs(low['L'] - low['R']):.1f} 厘米）")
side = {}
for s_ in "LR":
    st = [r for r in rows if r[s_][2] < low[s_] + 0.005]
    side[s_] = max(r[s_][1] for r in st) - min(r[s_][1] for r in st)
    hs = [r[s_][2] for r in st]; side[s_ + "z"] = max(hs) - min(hs)
mid = {s_: sum(r[s_][1] for r in rows if r[s_][2] < low[s_] + 0.005) / max(1, sum(1 for r in rows if r[s_][2] < low[s_] + 0.005)) for s_ in "LR"}
print(f"[walk] 两脚踝左右间距（支撑期平均）{100 * (mid['L'] - mid['R']):.1f} 厘米")
print(f"[walk] 支撑期脚踝左右晃 L {100 * side['L']:.1f} R {100 * side['R']:.1f} 厘米，上下 L {100 * side['Lz']:.1f} R {100 * side['Rz']:.1f} 厘米（都该接近 0）")
mean = sum(v) / len(v); sd = (sum((x - mean) ** 2 for x in v) / len(v)) ** 0.5
lift = {s: max(r[s][2] for r in rows) - min(r[s][2] for r in rows) for s in "LR"}
toe = {s: max(r[s + "t"][2] for r in rows) - min(r[s + "t"][2] for r in rows) for s in "LR"}
span = {s: max(r[s][0] for r in rows) - min(r[s][0] for r in rows) for s in "LR"}
hipz = [r["hip"][2] for r in rows]
dur = (f1 - f0) / fps
print(f"[walk] {a.clip}: {f1 - f0} 帧 = {dur:.2f} 秒一个循环")
print(f"[walk] 支撑脚地面速度 {mean:.3f} 米/秒（逐帧波动 ±{sd:.3f}，最小 {min(v):.3f} 最大 {max(v):.3f}）")
print(f"[walk] 脚踝前后行程 L {span['L']:.3f} R {span['R']:.3f} 米（≈ 步幅）；按速度算一个循环走 {mean * dur:.2f} 米")
print(f"[walk] 脚踝抬高 L {lift['L']:.3f} R {lift['R']:.3f} 米；脚尖抬高 L {toe['L']:.3f} R {toe['R']:.3f}；髋上下 {max(hipz) - min(hipz):.3f}")
if a.csv:
    with open(a.csv, "w") as fh:
        fh.write("frame,L_fwd,L_up,R_fwd,R_up,Lt_up,Rt_up,hip_up,L_side,R_side,rest_ankle\n")
        for r in rows: fh.write(f"{r['f']},{r['L'][0]:.4f},{r['L'][2]:.4f},{r['R'][0]:.4f},{r['R'][2]:.4f},{r['Lt'][2]:.4f},{r['Rt'][2]:.4f},{r['hip'][2]:.4f},{r['L'][1]:.4f},{r['R'][1]:.4f},{rest_ankle:.4f}\n")
