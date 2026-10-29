# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""检查等距柱状全景图的左右接缝。
用法：uv run tools/pano_seam.py <全景.png> [--fix 宽度px]
输出同目录：<名>_接缝居中.jpg（平移半圈，接缝在正中，肉眼看）、<名>_接缝放大.jpg
--fix N：把左右各 N 像素做环绕渐变融合，输出 <名>_fixed.png"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image

p = argparse.ArgumentParser(); p.add_argument("pano"); p.add_argument("--fix", type=int, default=0); a = p.parse_args()
src = Path(a.pano); im = Image.open(src).convert("RGB"); W, H = im.size
arr = np.asarray(im).astype(float)
print(f"尺寸 {W}x{H}，宽高比 {W / H:.3f}（应为 2.0）")
# 左右边缘一列的平均色差（0-255），再和相邻列的平均差比较
edge = np.abs(arr[:, 0] - arr[:, -1]).mean(); inner = np.abs(arr[:, 1:] - arr[:, :-1]).mean()
print(f"左右边缘色差 {edge:.1f}，图内相邻列平均色差 {inner:.1f} → 比值 {edge / max(inner, 1e-6):.1f}（接近 1 为无缝，>3 明显有缝）")
shift = np.roll(arr, W // 2, axis=1).astype(np.uint8)
mid = Image.fromarray(shift); mid.thumbnail((2400, 1200)); mid.save(src.with_name(src.stem + "_接缝居中.jpg"), quality=88)
c = W // 2; crop = Image.fromarray(shift).crop((c - 300, H // 4, c + 300, H * 3 // 4)); crop.save(src.with_name(src.stem + "_接缝放大.jpg"), quality=90)
if a.fix:
    # 偏移渐变：左右边缘每行的色差 d 各分一半，向图内 n 像素线性衰减，首尾两列都变成两边的平均值
    n = a.fix; out = arr.copy()
    d = (arr[:, 0] - arr[:, -1])[:, None, :]          # (H,1,3)
    ramp = (1 - np.arange(n) / n)[None, :, None]       # 边缘 1 → 图内 0
    out[:, :n] -= 0.5 * d * ramp
    out[:, -n:] += 0.5 * d * ramp[:, ::-1]
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(src.with_name(src.stem + "_fixed.png"))
    e2 = np.abs(out[:, 0] - out[:, -1]).mean(); print(f"修补后左右边缘色差 {e2:.1f} → {src.stem}_fixed.png（修补前 {edge:.1f}）")
