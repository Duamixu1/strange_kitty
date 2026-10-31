#!/bin/zsh
# 无头 Chrome 拍积木的验收图（内置浏览器 WebGL 被禁时走这条；无头 Chrome 用 Metal 渲染）。dev 服务器要先开着，[::1]:5173
#   tools/kit_shots.sh kit|splat        kit_compare.html 四个机位 → assets/processed/shots/kitcmp_<mode>_*.jpg
#   tools/kit_shots.sh map              绘卷总地图底稿 map_diorama → kitview_map_diorama_0_长卷.jpg（3840×1280）
#   tools/kit_shots.sh view <区块名>    kit_view.html 俯视 + 平面图里写的 shot → assets/processed/shots/kitview_<区块名>_*.jpg
mode=${1:-kit}
cd "$(dirname $0)/.."
size=1280,720
if [ $mode = map ]; then
  # 绘卷总地图底稿：3840×1280 长卷，相机约 40° 俯角、长焦（近似正交）
  prefix="kitview_map_diorama_"; size=3840,1280; need=1
  url="kit_view.html?glb=map_diorama&name=长卷&cam=35,58,68&look=35,2.2,-1.5&fov=14.8&noplayer=1&auto=1"
elif [ $mode = view ]; then
  plan=$2; prefix="kitview_${plan}_"; url="kit_view.html?plan=$plan&auto=1"
  need=$(python3 -c "import json;print(len(json.load(open('web/src/data/tour/${plan}_walk.json'))['shots'])+1)")
else
  prefix="kitcmp_${mode}_"; url="kit_compare.html?mode=$mode&auto=1"; need=4
fi
rm -f assets/processed/shots/${prefix}*.jpg(N)
prof=$(mktemp -d)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=$prof --window-size=$size \
  --enable-gpu --use-angle=metal --ignore-gpu-blocklist "http://[::1]:5173/$url" >/dev/null 2>&1 &
pid=$!
for i in {1..90}; do
  n=$(ls assets/processed/shots | grep -c "^${prefix}")
  [ $n -ge $need ] && break; sleep 2
done
sleep 1; kill $pid 2>/dev/null; sleep 1; rm -rf $prof 2>/dev/null
ls assets/processed/shots | grep "^${prefix}"
