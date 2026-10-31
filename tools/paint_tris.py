# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""把 tools/blender_head_back.py 导出的 UV 三角形在贴图上涂成一个颜色（往外扩 2 像素免得接缝漏色），存 tex_fixed.png 和对比图 compare.jpg。
  uv run tools/paint_tris.py 目录 --color 2a2230"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
p = argparse.ArgumentParser(); p.add_argument("dir"); p.add_argument("--color", default="2a2230"); a = p.parse_args()
d = Path(a.dir); spec = json.loads((d / "tris.json").read_text())
im = Image.open(d / "tex.png").convert("RGB")
mask = Image.new("L", im.size, 0); md = ImageDraw.Draw(mask)
for t in spec["tris"]: md.polygon([tuple(x) for x in t], fill=255)
mask = mask.filter(ImageFilter.MaxFilter(5))
col = tuple(int(a.color[i:i + 2], 16) for i in (0, 2, 4))
out = Image.composite(Image.new("RGB", im.size, col), im, mask)
out.save(d / "tex_fixed.png")
w = 900; s = w / im.width
Image.fromarray(__import__("numpy").hstack([__import__("numpy").asarray(im.resize((w, int(im.height * s)))), __import__("numpy").asarray(out.resize((w, int(im.height * s))))])).save(d / "compare.jpg")
print(f"涂了 {len(spec['tris'])} 个三角形 → {d / 'tex_fixed.png'}")
