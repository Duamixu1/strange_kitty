# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""总地图长卷打补丁：只重画一块（比如大奥门口），缩回原尺寸羽化贴回，别处不动、热区不改。

  uv run tools/kit_map_patch.py <补丁图> <x0> <y0> <x1> <y1> [羽化像素=60]
  例：uv run tools/kit_map_patch.py assets/concept/scenes/21_总地图_大奥门.png 0 300 900 1100
  → web/public/textures/kit/map_scroll_painted.jpg（覆盖；改之前的一版另存 map_scroll_painted_前一版.jpg）
    assets/processed/shots/map_scroll_补丁对比.jpg（上旧下新，只截补丁那一段）
贴在长卷边缘（x0=0 之类）的那一边不羽化。
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SCROLL = ROOT / "web/public/textures/kit/map_scroll_painted.jpg"
patch_p, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:6])
fe = int(sys.argv[6]) if len(sys.argv) > 6 else 60

base = Image.open(SCROLL).convert("RGB")
base.save(SCROLL.with_name("map_scroll_painted_前一版.jpg"), quality=92)
w, h = x1 - x0, y1 - y0
patch = Image.open(patch_p).convert("RGB").resize((w, h), Image.LANCZOS)

# 羽化遮罩：离边 fe 像素以内线性过渡；贴着长卷边缘的那一边不过渡
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
d = np.full((h, w), np.inf, np.float32)
if x0 > 0: d = np.minimum(d, xx)
if x1 < base.width: d = np.minimum(d, w - 1 - xx)
if y0 > 0: d = np.minimum(d, yy)
if y1 < base.height: d = np.minimum(d, h - 1 - yy)
mask = Image.fromarray((np.clip(d / fe, 0, 1) * 255).astype(np.uint8))

out = base.copy(); out.paste(patch, (x0, y0), mask)
out.save(SCROLL, quality=90)
a, b = base.crop((x0, y0, x1, y1)), out.crop((x0, y0, x1, y1))
sheet = Image.new("RGB", (w, h * 2 + 10), "#F1E9DA"); sheet.paste(a, (0, 0)); sheet.paste(b, (0, h + 10))
sheet.save(ROOT / "assets/processed/shots/map_scroll_补丁对比.jpg", quality=88)
print("→", SCROLL)
