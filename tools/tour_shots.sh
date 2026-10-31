#!/bin/zsh
# 无头 Chrome 打开 tour.html?loc=<地点>&auto=1，每个区块拍跟随镜头四个方向 + 每个观景点 + walk 文件里的验收机位，
# 存到 assets/processed/shots/tour_<地点>_*.jpg。用法：tools/tour_shots.sh <地点> [最多等多少秒，默认 300]
# 页面拍完最后存一张 tour_<地点>__done.jpg 当收工标记，脚本等到它出现才停（泼溅区块一张图可能要等十几秒，不能按"一阵没新图"判断）。
# dev 服务器要开着（[::1]:5173）。内置浏览器 WebGL 被禁时走这条。
loc=${1:?地点 id}; secs=${2:-300}
cd "$(dirname $0)/.."
shots=assets/processed/shots
rm -f $shots/tour_${loc}_*.jpg(N)
prof=$(mktemp -d)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=$prof --window-size=1280,720 \
  --enable-gpu --use-angle=metal --ignore-gpu-blocklist --enable-logging=stderr --v=0 \
  "http://[::1]:5173/tour.html?loc=$loc&auto=1" 2>$prof.log >/dev/null &
pid=$!
done=0
for i in $(seq 1 $((secs / 2))); do
  sleep 2
  [ -f $shots/tour_${loc}__done.jpg ] && { done=1; break; }
done
kill $pid 2>/dev/null
grep -E "CONSOLE|Uncaught" $prof.log | grep -v -E "\[vite\]|THREE.Clock" | cut -c1-300 | head -20
rm -rf $prof $prof.log 2>/dev/null
rm -f $shots/tour_${loc}__done.jpg
[ $done = 1 ] || echo "!! ${secs} 秒内没拍完（没等到收工标记），下面是已经拍到的"
ls $shots | grep "^tour_${loc}_"
