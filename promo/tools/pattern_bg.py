"""竖版镜头放进横版画面时，两侧的流动纹样底（代替模糊垫底）。
默认（2026-10-30 用户定）：只用一种纹样，一整张铺在竖版画面后面，深色底 + 低对比线，慢慢横向流动；中间套墨框。
STYLE = "strips" 是第一版：两侧各三条不同纹样的竖带 + 金边 + 金霞，用户觉得太花，留着备用。
中间留 810 宽给竖版画面（1206×1608 缩到 1080 高）。
用法：python pattern_bg.py <输出.mp4> <秒数> [起始秒，接着上一段动]
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
PAT = ROOT / "web/public/textures/patterns"
FF = str(Path.home() / "socialmedia/tools/bin/ffmpeg")
W, H, FPS = 1920, 1080, 30
CW = 810; X0 = (W - CW) // 2; X1 = X0 + CW
hx = lambda s: np.array([int(s[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
PAPER, CORAL, CRIMSON, GOLD, GREEN, TEAL, INDIGO, WIS, NAVY, LAV, PINK, INK = map(hx, [
    "#F1E9DA", "#E6667A", "#B42A47", "#DCC67C", "#59B86A", "#49B3A6", "#4F74BF", "#6A4C8C", "#2A2A4E", "#D6D3EF", "#E7A3B5", "#322D48"])

def tile(name, scale, bg, fg, w):
    """纹样遮罩上色，横向缩到 scale 倍，纵向平铺到够滚动的高度"""
    m = Image.open(PAT / f"{name}.png").convert("L")
    m = m.resize((max(1, int(m.width * scale)), max(1, int(m.height * scale))), Image.LANCZOS)
    a = np.asarray(m, np.float32)[..., None] / 255
    t = bg * (1 - a) + fg * a
    reps_x = w // t.shape[1] + 2; reps_y = (H * 2) // t.shape[0] + 2
    return np.tile(t, (reps_y, reps_x, 1))[:, :w]

# 每侧三条竖带：(纹样, 缩放, 底色, 线色, 速度 px/s，正 = 往下)
SW = (X0 - 2 * 14) // 3
LEFT = [("seigaiha", 0.30, INDIGO, PAPER, 70), ("asanoha", 0.26, CORAL, PINK * 0.5 + PAPER * 0.5, -55), ("shippo", 0.24, NAVY, GOLD, 85)]
RIGHT = [("ichimatsu", 0.16, CRIMSON, CORAL, -80), ("seigaiha", 0.30, TEAL, PAPER, 60), ("asanoha", 0.26, WIS, LAV, -70)]
strips = {}
for side, specs in (("L", LEFT), ("R", RIGHT)):
    strips[side] = [(tile(n, s, bg, fg, SW), v) for n, s, bg, fg, v in specs]

STYLE = "single"
SINGLE = ("seigaiha", 0.34, NAVY, INDIGO * 0.55 + NAVY * 0.45, 36)   # 纹样、缩放、底色、线色、横向速度 px/s
sheet = tile(SINGLE[0], SINGLE[1], SINGLE[2], SINGLE[3], W * 2)

# 和纸颗粒
rng = np.random.default_rng(3)
grain = (rng.normal(0, 1, (H, W, 1)).astype(np.float32) * 5)

def kasumi(t):
    """金霞：圆角长条，墨边，水平飘过两侧（中间被竖版画面盖住）"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y, L, speed, phase in ((150, 420, 60, 0), (520, 360, -45, 700), (860, 480, 50, 300)):
        x = (phase + speed * t) % (W + L) - L
        for xx in (x, x - (W + L)):
            d.rounded_rectangle((xx, y, xx + L, y + 64), radius=32, fill=(220, 198, 124, 255), outline=(50, 45, 72, 255), width=5)
            d.rounded_rectangle((xx + 40, y + 20, xx + L * 0.6, y + 44), radius=12, outline=(50, 45, 72, 120), width=3)
    return np.asarray(im, np.float32)

def frame(t):
    if STYLE == "single":
        off = int(SINGLE[4] * t) % W
        out = sheet[:H, off:off + W].copy()
        out[:, X0 - 10:X1 + 10] = INK
        return np.clip(out + grain, 0, 255).astype(np.uint8)
    out = np.zeros((H, W, 3), np.float32); out[:] = INK
    for side, x_start in (("L", 0), ("R", X1)):
        x = x_start + 14
        for k, (tex, v) in enumerate(strips[side]):
            off = int(v * t) % (tex.shape[0] - H)
            out[:, x + k * SW:x + (k + 1) * SW] = tex[off:off + H] if v > 0 else tex[tex.shape[0] - H - off:tex.shape[0] - off]
        for k in (1, 2):   # 带间金边：金 10px，两侧墨线
            b = x + k * SW; out[:, b - 9:b + 9] = INK; out[:, b - 5:b + 5] = GOLD
    k = kasumi(t); a = k[..., 3:4] / 255
    out = out * (1 - a) + k[..., :3] * a
    out[:, X0 - 10:X1 + 10] = INK                        # 中间画面的墨框
    out = out + grain
    return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    dst, dur = sys.argv[1], float(sys.argv[2]); t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    n = round(dur * FPS)
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(frame(t0 + i / FPS).tobytes())
    p.stdin.close(); p.wait()
    print(dst, n, "帧")
