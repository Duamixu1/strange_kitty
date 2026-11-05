#!/bin/zsh
# 药郎模型精简版：kusuriuri_v2_posed_layered.glb → kusuriuri_v2_posed_layered_lite.glb（docs/17 第十九节）
#   1. gltf-transform 重做 draco 量化（位置 10 位、法线 7 位、UV 10 位、权重 8 位）。要先做这一步：
#      它不认 16 位的稀疏 morph（写出来全是零，妖化头发不动了），所以 morph 存 16 位放在第 2 步
#   2. tools/glb_lite_player.py：删动作通道、共用 accessor、删多余关键帧、旋转和 morph 存 16 位、贴图重新压
# 用法：tools/build_player_lite.sh   （每次重出 kusuriuri_v2_posed_layered.glb 以后跑一遍）
set -e
cd "$(dirname $0)/.."
src=assets/processed/kusuriuri_v2_posed_layered.glb; out=assets/processed/kusuriuri_v2_posed_layered_lite.glb
tmp=$(mktemp -d)/draco.glb
npx --yes @gltf-transform/cli@4.5.1 draco $src $tmp --quantize-position 10 --quantize-normal 7 --quantize-texcoord 10 --quantize-generic 8 --encode-speed 0 --decode-speed 5
uv run -q --with numpy --with pillow python -I tools/glb_lite_player.py $tmp $out --tex 1024,62 --sharp 70 --face 512,78 --tol 0.3
rm -f $tmp
echo "原版 $(stat -f %z $src) 字节，gzip $(gzip -9c $src | wc -c | tr -d ' ')；精简 $(stat -f %z $out) 字节，gzip $(gzip -9c $out | wc -c | tr -d ' ')"
