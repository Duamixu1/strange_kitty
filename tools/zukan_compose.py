# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""药箱立绘合成：透明底渲染图按包围盒裁出，缩到高 350（宽不超过 600），放在 720×450 纸色底中间、脚底在 y=400。
  uv run tools/zukan_compose.py 渲染.png assets/processed/zukan/<id>.jpg"""
import sys
import numpy as np
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA"); a = np.asarray(im)[..., 3]
ys, xs = np.where(a > 8); im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
s = min(350 / im.height, 600 / im.width); im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
bg = Image.new("RGB", (720, 450), (241, 234, 218)); bg.paste(im, ((720 - im.width) // 2, 400 - im.height), im)
bg.save(out, quality=90); print("wrote", out, im.size)
