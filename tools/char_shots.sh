#!/bin/zsh
# 无头 Chrome 打开 character.html?auto=...，按动作定格拍图（带弹簧骨、道具、平涂描边），存 assets/processed/shots/<prefix>_*.jpg
# 用法：tools/char_shots.sh <prefix> <model> <动作:秒,动作:秒,...> [机位 1,3,4]
#   tools/char_shots.sh tourpose processed/kusuriuri_v2_posed_layered.glb gaze_k:2,pose_fold_k:1 1,4
# dev 服务器要先开着（[::1]:5173）。内置浏览器 WebGL 被禁时走这条
prefix=$1; model=$2; auto=$3; views=${4:-1,4}   # 环境变量 EXTRA 原样拼到网址后面，比如 EXTRA="&move=1.022" 边走边拍
cd "$(dirname $0)/.."
rm -f assets/processed/shots/${prefix}_*.jpg(N)
want=$(( $(echo $auto | tr ',' '\n' | wc -l) * $(echo $views | tr ',' '\n' | wc -l) ))
prof=$(mktemp -d)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=$prof --window-size=900,1100 \
  --enable-gpu --use-angle=metal --ignore-gpu-blocklist "http://[::1]:5173/character.html?model=$model$EXTRA&auto=$auto&views=$views&prefix=$prefix" >/dev/null 2>&1 &
pid=$!
for i in {1..90}; do
  [ $(ls assets/processed/shots | grep -c "^${prefix}_") -ge $want ] && break; sleep 2
done
sleep 1; kill $pid 2>/dev/null; rm -rf $prof 2>/dev/null
ls assets/processed/shots | grep "^${prefix}_"
