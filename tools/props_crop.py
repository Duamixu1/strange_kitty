# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "scipy"]
# ///
"""
从道具概念图里把单个道具抠出来，给 Tripo 单图生成模型用。输出 assets/concept/props/<id>.png（纸色底的方图）。

做法：按和纸底色的色差做前景遮罩，稍微膨胀把细链子、流苏连起来，再按连通区域取：
只保留"整个包围盒都落在框选范围里"的区域，这样相邻的刀鞘、侧视图会被自动丢掉。
框选坐标是原图像素（3840×2160）。

  uv run tools/props_crop.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
PROPS = [
    # id, 源图, 框选 (x0, y0, x1, y1)
    ("sword", "assets/concept/scenes/09_退魔之剑.png", (40, 580, 3760, 1170)),
    ("medicine_chest", "assets/concept/scenes/10_药箱与天秤.png", (1060, 50, 2110, 1120)),
    ("scale", "assets/concept/scenes/10_药箱与天秤.png", (2120, 90, 3830, 1400)),
]

def main():
    out_dir = ROOT / "assets/concept/props"; out_dir.mkdir(parents=True, exist_ok=True)
    for pid, src, (x0, y0, x1, y1) in PROPS:
        im = Image.open(ROOT / src).convert("RGB"); a = np.asarray(im).astype(int)
        bg = np.median(a[:60, :60].reshape(-1, 3), axis=0)
        fg = np.abs(a - bg).sum(axis=2) > 70
        fg = ndimage.binary_dilation(fg, iterations=4)
        lab, n = ndimage.label(fg)
        keep = np.zeros_like(fg)
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            ys, xs = sl
            area = (lab[sl] == i).sum()
            inside = xs.start >= x0 and xs.stop <= x1 and ys.start >= y0 and ys.stop <= y1
            if inside and area > 400:
                keep |= lab == i
        ys, xs = np.where(keep)
        bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        crop = np.asarray(im)[by0:by1, bx0:bx1].copy()
        mask = keep[by0:by1, bx0:bx1]
        crop[~mask] = bg.astype(np.uint8)          # 框里不属于这个道具的像素刷成纸色
        pad = int(0.06 * max(crop.shape[:2]))
        S = max(crop.shape[:2]) + 2 * pad
        sq = Image.new("RGB", (S, S), tuple(int(v) for v in bg))
        sq.paste(Image.fromarray(crop), ((S - crop.shape[1]) // 2, (S - crop.shape[0]) // 2))
        if S > 2048: sq = sq.resize((2048, 2048), Image.LANCZOS)
        sq.save(out_dir / f"{pid}.png")
        print(pid, "bbox", (bx0, by0, bx1, by1), "->", sq.size)

if __name__ == "__main__":
    main()
