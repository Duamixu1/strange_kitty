#!/bin/zsh
# 配角模型精简版：<名字>_posed.glb → <名字>_posed_lite.glb（docs/17 第十九节）。配角离镜头远：
#   1. 面数减到 55%（gltf-transform simplify，误差上限 0.1% 模型半径；原来 8~10 万面，比药郎全身还多）
#   2. draco 重新量化（位置 11 位、法线 7 位、UV 10 位、权重 8 位）
#   3. tools/glb_lite_player.py：删动作通道、共用 accessor、删多余关键帧、贴图 1024 边 质量 62
# 用法：tools/build_npc_lite.sh [名字 ...]（不写就是九个配角）
set -e
cd "$(dirname $0)/.."
if (( $# )); then names=($@); else names=(hisayo tokuji shino asa kame utayama kayo odajima yoshiyuki); fi
tmp=$(mktemp -d)
for n in $names; do
  src=assets/processed/${n}_posed.glb; out=assets/processed/${n}_posed_lite.glb
  npx --yes @gltf-transform/cli@4.5.1 simplify $src $tmp/s.glb --ratio 0.55 --error 0.001 >/dev/null
  npx --yes @gltf-transform/cli@4.5.1 draco $tmp/s.glb $tmp/d.glb --quantize-position 11 --quantize-normal 7 --quantize-texcoord 10 --quantize-generic 8 --encode-speed 0 --decode-speed 5 >/dev/null
  uv run -q --with numpy --with pillow python -I tools/glb_lite_player.py $tmp/d.glb $out --tex 1024,62 --sharp 60 --tol 0.3 >/dev/null
  echo "$n: $(( $(stat -f %z $src) / 1024 )) KB → $(( $(stat -f %z $out) / 1024 )) KB（gzip $(( $(gzip -9c $out | wc -c) / 1024 )) KB）"
done
rm -rf $tmp
