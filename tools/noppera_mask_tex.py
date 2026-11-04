# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""无面的面具贴图（docs/18 第九节）：象牙白的漆面，细裂纹，两道朱红隈取（主笔加一道细的副笔），一道金缮，短短的朱红嘴线。没有眼睛、鼻子。
贴图是正方形，面具椭圆铺满内切圆（tools/blender_add_mask.py 的 UV 就是这么排的）。先 2 倍大画再缩小，边缘干净。
  uv run tools/noppera_mask_tex.py  → assets/processed/noppera_mask.png"""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets/processed/noppera_mask.png"
S = 2048; R = S / 2
IVORY, RIM, CRACK = (239, 232, 216), (206, 196, 172), (214, 204, 182)
CRIMSON, GOLD, GOLD_D, VERMIL = (178, 33, 48), (201, 162, 58), (150, 112, 30), (205, 64, 44)
P = lambda u, v: (R + u * R, R - v * R)       # u 往右、v 往上（-1~1）→ 像素


def bez(p0, p1, p2, n=60):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def stroke(d, pts, w0, w1, col):
    """沿折线画一笔，宽度从 w0 收到 w1（像毛笔收锋）"""
    L, R2 = [], []
    for i, (x, y) in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; n = math.hypot(dx, dy) or 1
        t = i / (len(pts) - 1); w = (w0 + (w1 - w0) * t ** 0.8) * (0.6 + 0.4 * min(1, t * 6))   # 起笔稍细、中间最粗、收锋
        L.append((x - dy / n * w, y + dx / n * w)); R2.append((x + dy / n * w, y - dx / n * w))
    d.polygon([P(*p) for p in L + R2[::-1]], fill=col)


im = Image.new("RGB", (S, S), IVORY); d = ImageDraw.Draw(im)
rnd = random.Random(7)
for _ in range(34):   # 细裂纹：随机折线，颜色只比底色深一点
    x, y = rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8); a = rnd.uniform(0, 2 * math.pi); pts = [P(x, y)]
    for _ in range(rnd.randint(3, 7)):
        a += rnd.uniform(-0.9, 0.9); l = rnd.uniform(0.03, 0.09); x += math.cos(a) * l; y += math.sin(a) * l; pts.append(P(x, y))
    d.line(pts, fill=CRACK, width=3)
for s in (-1, 1):     # 隈取：从眉心往外上方扫到太阳穴，主笔 + 下面一道细的副笔
    stroke(d, bez((0.08 * s, 0.12), (0.38 * s, 0.22), (0.7 * s, 0.62)), 0.075, 0.004, CRIMSON)
    stroke(d, bez((0.2 * s, 0.0), (0.45 * s, 0.08), (0.72 * s, 0.38)), 0.028, 0.003, CRIMSON)
seam = [(-0.5, 0.86), (-0.36, 0.55), (-0.42, 0.38), (-0.18, 0.12), (-0.22, -0.08), (0.04, -0.32), (0.0, -0.46), (0.26, -0.82)]   # 金缮：一道折线裂缝
d.line([P(*p) for p in seam], fill=GOLD_D, width=22, joint="curve"); d.line([P(*p) for p in seam], fill=GOLD, width=13, joint="curve")
br = [(-0.18, 0.12), (0.06, 0.2), (0.16, 0.42)]; d.line([P(*p) for p in br], fill=GOLD_D, width=14, joint="curve"); d.line([P(*p) for p in br], fill=GOLD, width=8, joint="curve")
stroke(d, bez((-0.13, -0.53), (0.0, -0.57), (0.13, -0.53), 20), 0.02, 0.012, VERMIL)   # 嘴：短短一道
d.ellipse([P(-0.985, 0.985), P(0.985, -0.985)], outline=RIM, width=18)                  # 面具边沿淡淡一圈
im = im.resize((1024, 1024), Image.LANCZOS)
im.save(OUT); print(f"wrote {OUT}")
