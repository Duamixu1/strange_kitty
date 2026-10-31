#!/bin/zsh
# 走路随动层验收：无头 Chrome 跑 tour.html?walktest=1 两遍（改前 old：&layer=0&turn=old；改后 new），
# 再跑一遍按住 Shift（sprint：快走 1 秒后加速成跑）。每 1/24 秒一帧存到 assets/processed/shots/walktest_<old|new|sprint>_NNN.jpg，
# 拼成左右对比视频 walktest_对比.mp4（old | new）和单独的 walktest_跑.mp4。
# 用法：tools/walk_video.sh [地点，默认 wanya]     dev 服务器要开着（[::1]:5173）
loc=${1:-wanya}
cd "$(dirname $0)/.."
shots=assets/processed/shots
for tag in old new sprint; do
  rm -f $shots/walktest_${tag}_*.jpg(N)
  extra=""; [ $tag = old ] && extra="&layer=0&turn=old"; [ $tag = sprint ] && extra="&sprint=1"
  prof=$(mktemp -d)
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --user-data-dir=$prof --window-size=960,720 \
    --enable-gpu --use-angle=metal --ignore-gpu-blocklist "http://[::1]:5173/tour.html?loc=$loc&walktest=1$extra" >/dev/null 2>&1 &
  pid=$!; last=-1; same=0
  for i in {1..120}; do
    sleep 2; n=$(ls $shots | grep -c "^walktest_${tag}_")
    if [ $n -gt 30 ] && [ $n = $last ]; then same=$((same + 1)); [ $same -ge 2 ] && break; else same=0; fi
    last=$n
  done
  kill $pid 2>/dev/null; rm -rf $prof 2>/dev/null
  echo "$tag: $n 帧"
done
uv run --with pillow --with imageio --with imageio-ffmpeg python - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as iio
S = Path("assets/processed/shots")
old, new = sorted(S.glob("walktest_old_*.jpg")), sorted(S.glob("walktest_new_*.jpg"))
f = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 26)
w = iio.get_writer(S / "walktest_对比.mp4", fps=24, codec="libx264", quality=8, macro_block_size=8)
for i in range(max(len(old), len(new))):
    a = Image.open(old[min(i, len(old) - 1)]); b = Image.open(new[min(i, len(new) - 1)])
    c = Image.new("RGB", (a.width + b.width + 8, a.height), "#322D48"); c.paste(a, (0, 0)); c.paste(b, (a.width + 8, 0))
    d = ImageDraw.Draw(c); d.text((16, 12), "改前", fill="#F1E9DA", font=f); d.text((a.width + 24, 12), "改后", fill="#F1E9DA", font=f)
    w.append_data(__import__("numpy").asarray(c))
w.close(); print(S / "walktest_对比.mp4")
sp = sorted(S.glob("walktest_sprint_*.jpg"))
if sp:
    w = iio.get_writer(S / "walktest_跑.mp4", fps=24, codec="libx264", quality=8, macro_block_size=8)
    for p in sp: w.append_data(__import__("numpy").asarray(Image.open(p)))
    w.close(); print(S / "walktest_跑.mp4")
PY
