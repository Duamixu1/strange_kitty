#!/bin/zsh
# 无头 Chrome 打开 tour.html?loc=<地点>&selftest=1，把 [selftest] 结果打出来（走到观景点、开关说明卡、驻足动作、出口转场、
# 按 W 走、四个滤镜、两个拍照姿势）。用法：tools/tour_selftest.sh <地点> [<地点> ...]
# dev 服务器要开着（[::1]:5173）。
cd "$(dirname $0)/.."
for loc in "$@"; do
  prof=$(mktemp -d)
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=$prof --window-size=1280,720 \
    --enable-gpu --use-angle=metal --ignore-gpu-blocklist --enable-logging=stderr --v=0 \
    "http://[::1]:5173/tour.html?loc=$loc&selftest=1" 2>$prof.log >/dev/null &
  pid=$!
  for i in {1..90}; do sleep 2; grep -q "姿势切回" $prof.log && break; done
  sleep 1; kill $pid 2>/dev/null
  echo "== $loc：$(grep -c '\[selftest\] OK' $prof.log) 项通过，$(grep -c '\[selftest\] FAIL' $prof.log) 项失败"
  grep -o '\[selftest\] FAIL[^"]*\|Uncaught[^"]*' $prof.log
  rm -rf $prof $prof.log 2>/dev/null
done
