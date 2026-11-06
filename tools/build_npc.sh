#!/bin/zsh
# 新配角从 Tripo 绑好骨的模型一路出到 <名字>_posed_lite.glb（docs/17 第十节的流程，游32 起写成脚本）
# 用法：tools/build_npc.sh <名字> <身高米> [--female] [--npc-m] [--seat]
#   --female  女：两手拢在身前（npc_setup.py）      --npc-m  男步（walk_gen 的 npc_m，不给就是小碎步 npc）
#   --seat    跪坐（tools/npc_seat.py）：不出走路，所有姿势往下坐
# 输入 assets/tripo_raw/anims/<名字>_rigged.glb（tripo_v2.py 出的）；站姿动作要先在 tools/npc_gestures.py 的 WHO 里写上这个人
set -e
cd "$(dirname $0)/.."
n=$1; h=$2; shift 2
fem=(); gait=--npc; seat=0
for x in "$@"; do case $x in --female) fem=(--female);; --npc-m) gait=--npc-m;; --seat) seat=1;; esac; done
B=/Applications/Blender.app/Contents/MacOS/Blender
q() { "$@" 2>&1 | grep -E "^\[|Error|error|Traceback|wrote" | grep -v "^\[gltf" | tail -3 }
echo "== $n：精简（8 万面，保留骨骼）"
q $B -b --python tools/blender_lite.py -- --in assets/tripo_raw/anims/${n}_rigged.glb --out assets/processed/${n}_lite.glb --keep-rig --tris 80000
echo "== 量腿"
q $B -b --python tools/rig_legs.py -- --in assets/processed/${n}_lite.glb --height $h --out tools/npc_poses/${n}_legs.json
echo "== 站姿、待机"
python3 tools/npc_setup.py $n $fem
if (( ! seat )); then
  echo "== 走路 + 闭环修正三轮"
  rm -f tools/poses/walk_fix_${n}_walk_k.json
  tmp=$(mktemp -d)
  for i in 1 2 3; do
    python3 tools/walk_gen.py walk_k --char $n $gait > /dev/null
    q $B -b --python tools/blender_pose_anim.py -- --in assets/processed/${n}_lite.glb --poses tools/npc_poses/$n.json --out $tmp/w.glb --only walk_k
    $B -b --python tools/walk_measure.py -- --in $tmp/w.glb --clip walk_k --height $h --csv $tmp/w$i.csv 2>&1 | grep -E "速度|speed|m/s|米/秒" | tail -1
    python3 tools/walk_gen.py walk_k --char $n $gait --learn $tmp/w$i.csv > /dev/null
  done
  python3 tools/walk_gen.py walk_k --char $n $gait | tail -1
  rm -rf $tmp
fi
echo "== 站姿动作"
python3 tools/npc_gestures.py $n | grep "^$n "
(( seat )) && python3 tools/npc_seat.py $n
echo "== 出模型"
q $B -b --python tools/blender_pose_anim.py -- --in assets/processed/${n}_lite.glb --poses tools/npc_poses/$n.json --out assets/processed/${n}_posed.glb
echo "== 精简版"
tools/build_npc_lite.sh $n | tail -2
