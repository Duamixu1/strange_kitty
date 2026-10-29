# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "scipy"]
# ///
"""
妖化表情：在脸部正面原色图上缩瞳、露齿，输出贴片用的贴图。
输入 assets/processed/kusuriuri_awaken_face_base.png + kusuriuri_awaken_face.json（blender_awaken.py --stage render 生成），
输出 assets/processed/kusuriuri_awaken_face.png，再跑 blender_awaken.py --stage build。

  瞳孔：在眼框里找金色虹膜，把虹膜里的深色瞳孔刷成金色，再在中心画一个竖着的小瞳孔，虹膜整体提亮（参考帧 79s）
  嘴：  把原来的红唇抹成肤色，画一个往右上挑的张口狞笑：深色口腔、上下两排牙、藤紫色唇线
  uv run tools/awaken_face.py [--preview 输出对比图]
"""
import argparse, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "assets/processed/kusuriuri_awaken_face.json"
BASE = ROOT / "assets/processed/kusuriuri_awaken_face_base.png"
OUT = ROOT / "assets/processed/kusuriuri_awaken_face.png"
PUPIL = (28, 20, 38); IRIS_HI = np.array([242, 200, 75]); MOUTH_IN = (59, 18, 38); TEETH = (246, 242, 255)
LIP = (106, 76, 140); LINE = (50, 45, 72)


def eyes(img, box):
    x0, y0, x1, y1 = box
    reg = np.asarray(img)[y0:y1, x0:x1].astype(float) / 255
    r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]
    yellow = (r > 0.55) & (g > 0.45) & (b < 0.5) & ((r - b) > 0.22)
    lab, n = ndimage.label(ndimage.binary_closing(yellow, iterations=2))
    if n == 0: print("  没找到虹膜", box); return
    big = 1 + int(np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))))
    ys, xs = np.where(lab == big)
    if xs.max() - xs.min() < 30:   # 认出来的太小（左眼虹膜偏黄绿、被眼线切成几块），改用框里全部金色像素的范围
        ys, xs = np.where(yellow)
        xs_lo, xs_hi = np.percentile(xs, [4, 96]); ys_lo, ys_hi = np.percentile(ys, [4, 96])
        cx, cy, rx, ry = (xs_lo + xs_hi) / 2, (ys_lo + ys_hi) / 2, (xs_hi - xs_lo) / 2 + 3, (ys_hi - ys_lo) / 2 + 3
    else:
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        rx, ry = (xs.max() - xs.min()) / 2 + 2, (ys.max() - ys.min()) / 2 + 2
    yy, xx = np.mgrid[0:reg.shape[0], 0:reg.shape[1]]
    inside = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 0.8 ** 2
    lum = reg @ np.array([0.3, 0.59, 0.11])
    dark = inside & (lum < 0.42)
    arr = np.asarray(img).copy()
    sub = arr[y0:y1, x0:x1]
    iris_col = np.median(sub[yellow], axis=0) if yellow.sum() else IRIS_HI
    iris_col = np.clip(iris_col * 0.4 + IRIS_HI * 0.6, 0, 255)
    sub[dark] = iris_col
    sub[inside & yellow] = np.clip(sub[inside & yellow] * 0.55 + IRIS_HI * 0.45, 0, 255)   # 虹膜提亮
    arr[y0:y1, x0:x1] = sub
    img.paste(Image.fromarray(arr))
    # 小瞳孔：竖着的小椭圆，4 倍画再缩小抗锯齿
    k = 4; w, h = int(rx * 2 * k), int(ry * 2 * k)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    pr, pv = rx * 0.17 * k, ry * 0.5 * k
    d.ellipse([w / 2 - pr, h / 2 - pv, w / 2 + pr, h / 2 + pv], fill=PUPIL + (255,))
    lay = lay.resize((w // k, h // k), Image.LANCZOS)
    img.paste(lay, (int(x0 + cx - rx), int(y0 + cy - ry)), lay)
    print(f"  虹膜中心 ({x0 + cx:.0f},{y0 + cy:.0f}) 半径 {rx:.0f}×{ry:.0f}，刷掉深色瞳孔 {int(dark.sum())} 像素")


def mouth(img, box):
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0
    arr = np.asarray(img).copy(); sub = arr[y0:y1, x0:x1].astype(float) / 255
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    lum = sub @ np.array([0.3, 0.59, 0.11])
    skin = np.median(sub[lum > 0.82], axis=0)
    red = (r > 0.55) & (g < 0.5) & ((r - g) > 0.25)
    # 按嘴唇所在的椭圆柔和地抹成肤色，不切直线，免得下唇那块红被抹出方框
    yy, xx = np.mgrid[0:H, 0:W]
    ell = ((xx - 0.5 * W) / (0.47 * W)) ** 2 + ((yy - 0.45 * H) / (0.3 * H)) ** 2
    erase = ndimage.binary_dilation((red | (lum < 0.5)) & (ell < 1.0), iterations=3)
    lip_bottom = 0.45 * H + 0.3 * H
    sub[erase] = skin
    arr[y0:y1, x0:x1] = (np.clip(sub, 0, 1) * 255).astype(np.uint8)
    img.paste(Image.fromarray(arr))
    # 张口狞笑：4 倍画再缩小
    k = 4; lay = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    def P(u, v): return (u * W * k, v * H * k)
    def curve(p0, p1, p2, n=24):
        return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in np.linspace(0, 1, n)]
    L, R = P(0.1, 0.42), P(0.93, 0.26)
    top = curve(L, P(0.5, 0.02), R); bot = curve(R, P(0.48, 1.3), L)
    d.polygon(top + bot, fill=MOUTH_IN + (255,))
    # 上牙：沿上唇往下一条，按段切开；第三颗是尖牙
    up = curve(P(0.15, 0.38), P(0.5, 0.06), P(0.88, 0.29), 9)
    for i, (pa, pb) in enumerate(zip(up, up[1:])):
        hgt = 0.2 * H * k * (1.5 if i == 2 else 1.0)
        mx = ((pa[0] + pb[0]) / 2, max(pa[1], pb[1]) + hgt)
        tooth = [pa, pb, (pb[0] - 2, pb[1] + hgt * 0.8), mx, (pa[0] + 2, pa[1] + hgt * 0.8)] if i != 2 else [pa, pb, mx]
        d.polygon(tooth, fill=TEETH + (255,), outline=LINE + (255,))
    # 下牙：沿下唇往上一条，矮一点
    lo = curve(P(0.22, 0.62), P(0.48, 1.12), P(0.8, 0.5), 7)
    for pa, pb in zip(lo, lo[1:]):
        hgt = 0.13 * H * k
        d.polygon([pa, pb, (pb[0] - 2, pb[1] - hgt), (pa[0] + 2, pa[1] - hgt)], fill=TEETH + (255,), outline=LINE + (255,))
    # 唇线：藤紫，上唇细、下唇粗一点
    d.line(top, fill=LIP + (255,), width=int(2.2 * k), joint="curve")
    d.line(bot, fill=LIP + (255,), width=int(3.2 * k), joint="curve")
    lay = lay.resize((W, H), Image.LANCZOS)
    img.paste(lay, (x0, y0), lay)
    print(f"  嘴：唇底 y={y0 + lip_bottom:.0f}，肤色 {np.round(skin * 255).astype(int).tolist()}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--preview"); a = ap.parse_args()
    meta = json.load(open(META, encoding="utf-8"))
    img = Image.open(BASE).convert("RGB"); base = img.copy()
    for k in ("eye_R", "eye_L"): print(k); eyes(img, meta["boxes"][k])
    print("mouth"); mouth(img, meta["boxes"]["mouth"])
    img.save(OUT); print("wrote", OUT)
    if a.preview:
        both = Image.new("RGB", (img.width * 2 + 20, img.height), (220, 215, 205)); both.paste(base, (0, 0)); both.paste(img, (img.width + 20, 0))
        both.save(a.preview, quality=90)

if __name__ == "__main__":
    main()
