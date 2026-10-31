"""
新配角的姿势库：从模板生成 tools/npc_poses/<名字>.json（站姿 stand / 呼吸 breathe / 瞥一眼 glance + 待机 idle_k），
bind_fix 按这个模型的上臂张开角算（tools/rig_legs.py 量的 arm_abduct，存在 tools/npc_poses/<名字>_legs.json）。

  python3 tools/npc_setup.py shino --female
  python3 tools/npc_setup.py tokuji              # 男：手自然垂在身体两侧
  然后 walk_gen.py 生成走路、npc_gestures.py 写站姿动作、blender_pose_anim.py 出 <名字>_posed.glb（见 docs/17 第十节）

bind_fix 的经验式：放下手臂的 roll = 上臂张开角 - 9.5°（阿浅、阿龟、歌山三个模型手调出来的值都在这条线上，差不到 1°）。
已经有姿势库的话只更新 bind_fix 和 stand / breathe / glance / idle_k，别的姿势和动作（走路、站姿动作）原样保留。
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
name = sys.argv[1]; female = "--female" in sys.argv
legs = json.loads((ROOT / f"tools/npc_poses/{name}_legs.json").read_text())
ab = legs["arm_abduct"]

if female:   # 同阿浅：两手拢在身前，前臂扭一下让大袖垂下来
    stand = json.loads((ROOT / "tools/npc_poses/asa.json").read_text(encoding="utf-8"))["poses"]["stand"]
else:        # 男：手自然垂在身体两侧、略往前，前臂同样扭一下让袖子垂下来
    stand = {"Spine01": {"pitch": -1}, "Spine02": {"pitch": -1}, "Head": {"pitch": 3},
             "L_Upperarm": {"pitch": -6, "roll": -2}, "R_Upperarm": {"pitch": -6, "roll": 2},
             "L_Forearm": {"pitch": -18, "yaw": -8, "local": [0, 70, 0]}, "R_Forearm": {"pitch": -18, "yaw": 8, "local": [0, -70, 0]}}
p = ROOT / f"tools/npc_poses/{name}.json"
lib = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"poses": {}, "animations": {}}
lib["_说明"] = (f"{name} 待机姿势（游14，tools/npc_setup.py 生成{'，女：同阿浅' if female else '，男'}）。写法同 tools/poses/kusuriuri_v2.json："
                "角度单位度、角色坐标系；朝下的骨头 pitch 负值 = 往前抬；roll 正值 = 远端往角色左边倒。"
                f"bind_fix 按上臂张开角（左 {ab['L']}°、右 {ab['R']}°）减 9.5° 把 A 字手臂放下。前臂 local Y 扭 ±70° 让大袖下垂。")
lib["bind_fix"] = {"L_Upperarm": {"roll": -round(ab["L"] - 9.5)}, "R_Upperarm": {"roll": round(ab["R"] - 9.5)}}
lib["poses"]["stand"] = stand
lib["poses"]["breathe"] = {"base": "stand", "Spine02": {"pitch": -2.2}, "L_Clavicle": {"roll": -1}, "R_Clavicle": {"roll": 1},
                           "Head": {"pitch": stand["Head"]["pitch"] + 0.8}, "Hip": {"move": [0, 0, 0.003]}}
lib["poses"]["glance"] = {"base": "breathe", "Head": {"pitch": stand["Head"]["pitch"] - 1, "yaw": 10}, "NeckTwist02": {"yaw": 4}}
lib["animations"]["idle_k"] = {"fps": 24, "keys": [["stand", 0], ["breathe", 54], ["stand", 108], ["breathe", 150], ["glance", 168],
                                                   ["glance", 210], ["breathe", 228], ["stand", 264]]}
p.write_text(json.dumps(lib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(name, "bind_fix", lib["bind_fix"])
