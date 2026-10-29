"""
药郎角色样片剪辑：从录屏中间素材逐帧取画面，做裁剪、推拉、变速、特写、闪白、片头片尾字。

输入 raw.mp4：录屏右侧预览区（1988x1800，60fps），左上角操作说明和鼠标箭头在 clean() 里逐帧处理。
输出 3:4 竖屏 1206x1608，30fps，切点全部卡在 120 BPM 的拍子上（和 music.py 对应）。

用法：python edit.py raw.mp4 out_video.mp4 原始录屏.mov
（开场的界面推进镜头直接读原始录屏整帧）
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FF = '/Users/duami/socialmedia/tools/bin/ffmpeg'
SRC_W, SRC_H, SRC_FPS = 1988, 1800, 60
OUT_W, OUT_H, FPS = 1206, 1608, 30
BASE_H = 1800  # z=1 时取整个高度，宽度按 3:4

# 每个镜头：输出起止(秒), 素材起点, 速度, 镜头运动 (z0,z1, cx0,cy0, cx1,cy1), 缓动, 附加效果
SHOTS = [
    # 开场：Claude 操作界面全景，1.5 秒后推进到右侧预览窗口（落点和下一镜同构图）
    dict(o=(0.0, 3.0), s=0.33, sp=0.7, ui=dict(hold=1.5, land=(975, 837), zl=1.075), fx=['fadein']),
    # 挥剑提前：拔剑 → 脸+剑特写 → 举剑 → 横斩 → 收剑
    dict(o=(3.0, 4.5), s=40.0, sp=1.27, z=(1.0, 1.0), c=((958, 917), (958, 917))),              # 拔剑（推进落点按这一镜的构图对齐）
    dict(o=(4.5, 5.0), s=41.9, sp=1.0, z=(2.3, 2.45), c=((900, 620), (905, 620))),              # 特写：脸+剑
    dict(o=(5.0, 6.0), s=43.1, sp=1.5, z=(1.0, 1.1), c=((960, 900), (910, 860)), fx=['shake_in']),  # 举剑亮相
    dict(o=(6.0, 8.5), s=44.90, sp=0.667, z=(1.35, 1.0), c=((1150, 860), (1110, 900)), ease='out_fast', fx=['flash', 'shake']),  # 横斩
    dict(o=(8.5, 9.5), s=46.90, sp=1.5, z=(1.0, 1.0), c=((1000, 900), (1000, 900))),            # 收剑
    # 片名 + 角色展示
    dict(o=(9.5, 11.5), s=3.62, sp=0.79, z=(1.0, 1.08), c=((1000, 900), (1000, 860)), fx=['title', 'flash_soft']),
    dict(o=(11.5, 12.5), s=5.30, sp=1.85, z=(1.05, 1.05), c=((1000, 900), (1000, 900))),        # 背面药箱
    dict(o=(12.5, 13.5), s=7.30, sp=3.8, z=(1.05, 1.0), c=((1000, 900), (990, 900))),           # 转身
    dict(o=(13.5, 14.5), s=15.0, sp=1.0, z=(2.0, 2.0), c=((980, 960), (990, 590)), ease='inout'),  # 特写：天秤 → 脸
    dict(o=(14.5, 15.5), s=16.0, sp=2.0, z=(1.15, 1.0), c=((980, 880), (980, 900)), ease='out'),   # 拉回全身
    dict(o=(15.5, 17.5), s=26.0, sp=2.0, z=(1.55, 1.68), c=((1044, 905), (1044, 900))),         # 宽银幕
    dict(o=(17.5, 19.0), s=63.0, sp=2.0, z=(1.0, 1.0), c=((984, 900), (984, 900)), fx=['flash_soft']),  # 伸手
    dict(o=(19.0, 21.5), s=74.0, sp=2.0, z=(1.0, 1.07), c=((916, 900), (930, 880)), fx=['fadeout']),    # 侧身离开
    dict(o=(21.5, 24.0), s=None, fx=['end']),                                                     # 片尾字
]
TOTAL = 24.0

# 录屏整帧尺寸、预览区在整帧里的位置（和 raw.mp4 的裁剪一致）
FULL_W, FULL_H = 4096, 2254
VIEW_X, VIEW_Y = 2108, 287


def ease(x, kind):
    x = min(max(x, 0.0), 1.0)
    if kind == 'inout':
        return x * x * (3 - 2 * x)
    if kind == 'out':
        return 1 - (1 - x) ** 2
    if kind == 'out_fast':  # 撞上去之后快速回弹
        return 1 - (1 - min(x * 4, 1)) ** 3
    return x


# ---------- 文字层 ----------
MINCHO = '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc'
SONG = '/System/Library/Fonts/Supplemental/Songti.ttc'
INK = (40, 30, 45)
RED = (178, 34, 40)


def text_layer_title():
    """竖排「薬売り」+ 红色小印章"""
    im = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(MINCHO, 118, index=1)
    x, y = 70, 230
    for ch in '薬売り':
        d.text((x, y), ch, font=f, fill=INK + (255,))
        y += 140
    # 印章
    sx, sy, s = 92, y + 30, 76
    d.rectangle([sx, sy, sx + s, sy + s], fill=RED + (235,))
    fs = ImageFont.truetype(MINCHO, 30, index=1)
    for i, ch in enumerate('物怪'):
        d.text((sx + 23, sy + 4 + i * 34), ch, font=fs, fill=(245, 235, 220, 255))
    return np.array(im)


def text_layer_end():
    im = Image.new('RGBA', (OUT_W, OUT_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(MINCHO, 92, index=1)
    f2 = ImageFont.truetype(SONG, 40, index=1)
    t1 = '形・真・理'
    w = d.textlength(t1, font=f1)
    d.text(((OUT_W - w) / 2, OUT_H / 2 - 110), t1, font=f1, fill=(236, 226, 205, 255))
    t2 = '怪化猫二创 · 药郎 3D 角色样片'
    w = d.textlength(t2, font=f2)
    d.text(((OUT_W - w) / 2, OUT_H / 2 + 40), t2, font=f2, fill=(200, 60, 60, 255))
    return np.array(im)


def comp(frame, layer, alpha):
    if alpha <= 0:
        return frame
    a = layer[..., 3:4].astype(np.float32) / 255 * alpha
    return (frame * (1 - a) + layer[..., :3] * a).astype(np.uint8)


# ---------- 读素材 ----------
class Reader:
    """顺序解码一段素材，按需取第 n 帧（允许跳帧）"""

    def __init__(self, path, start, dur, w=SRC_W, h=SRC_H, vf=None):
        cmd = [FF, '-loglevel', 'error', '-ss', f'{start:.3f}', '-i', path, '-t', f'{dur + 0.2:.3f}']
        if vf:
            cmd += ['-vf', vf]
        self.p = subprocess.Popen(cmd + ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.idx = -1
        self.cur = None
        self.w, self.h = w, h
        self.size = w * h * 3

    def get(self, n):
        while self.idx < n:
            b = self.p.stdout.read(self.size)
            if len(b) < self.size:
                break
            self.cur = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3)
            self.idx += 1
        return self.cur

    def close(self):
        self.p.stdout.close()
        self.p.kill()


# ---------- 清理录屏痕迹 ----------
HELP = (0, 0, 752, 278)     # 左上角操作说明框（实际到 716,242）外扩，只在右边和下边羽化
HELP_SRC_X = 1988 - 752    # 从右上角同样大小的一块空白纸面取样
FEATHER = 16
_hm = np.zeros((HELP[3] - HELP[1], HELP[2] - HELP[0]), np.float32)
_hm[:-FEATHER, :-FEATHER] = 1
HELP_MASK = cv2.GaussianBlur(_hm, (0, 0), FEATHER / 3)
HELP_MASK[:-FEATHER * 2, :-FEATHER * 2] = 1  # 框内必须完全盖住
HELP_MASK = HELP_MASK[..., None]
CORE = np.load(__file__.rsplit('/', 1)[0] + '/cursor_core.npy')
CORE_F = CORE.astype(np.float32)
RING = cv2.dilate(CORE, np.ones((5, 5), np.uint8)) - CORE
CUR_MASK = cv2.dilate(CORE, np.ones((7, 7), np.uint8))
PAD = 8


def clean(fr):
    fr = fr.copy()
    # 1) 盖掉操作说明：取右上角纸面，按周边亮度配色后羽化贴上
    x0, y0, x1, y1 = HELP
    w = x1 - x0
    dst = fr[y0:y1, x0:x1].astype(np.float32)
    src = fr[y0:y1, HELP_SRC_X:HELP_SRC_X + w].astype(np.float32)
    ring_dst = fr[y1:y1 + 30, x0:x1].reshape(-1, 3).mean(0)
    ring_src = fr[y1:y1 + 30, HELP_SRC_X:HELP_SRC_X + w].reshape(-1, 3).mean(0)
    src = src + (ring_dst - ring_src)
    fr[y0:y1, x0:x1] = np.clip(dst * (1 - HELP_MASK) + src * HELP_MASK, 0, 255).astype(np.uint8)
    # 2) 擦掉鼠标箭头
    g = fr.mean(2)
    B = ((g < 70) & ((fr.max(2).astype(np.int16) - fr.min(2)) < 40)).astype(np.float32)
    r = cv2.matchTemplate(B, CORE_F, cv2.TM_CCOEFF_NORMED)
    _, mx, _, (x, y) = cv2.minMaxLoc(r)
    if mx > 0.88:
        h, w = CORE.shape
        ys, xs = slice(y - PAD, y + h + PAD), slice(x - PAD, x + w + PAD)
        m = np.zeros(g.shape, np.uint8)
        m[y:y + h, x:x + w] = CUR_MASK * 255
        sub = fr[ys, xs]
        fr[ys, xs] = cv2.inpaint(np.ascontiguousarray(sub), np.ascontiguousarray(m[ys, xs]), 4, cv2.INPAINT_TELEA)
    return fr


def view(frame, z, cx, cy, dx=0.0, dy=0.0):
    """以 (cx,cy) 为中心、缩放 z 取 3:4 画面，用仿射变换保证亚像素平滑"""
    h = BASE_H / z
    w = h * 3 / 4
    s = OUT_H / h
    x0, y0 = cx - w / 2 + dx, cy - h / 2 + dy
    M = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
    return cv2.warpAffine(frame, M, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def ui_frame(fr, lt, dur, hold, land, zl=1.0):
    """整屏录屏 → 推进到预览窗口。fr 是整帧（4096x2254）。"""
    s_full = OUT_W / FULL_W                      # 整屏铺满宽度
    c_full = np.array([FULL_W / 2, FULL_H / 2])
    s_hold = s_full * 1.06
    s_land = OUT_H / BASE_H * zl                 # 落点缩放，和下一镜人物大小一致
    c_land = np.array([VIEW_X + land[0], VIEW_Y + land[1]])
    if lt < hold:
        p = 0.0
        sc = s_full + (s_hold - s_full) * ease(lt / hold, 'out')
        c = c_full
    else:
        p = ease((lt - hold) / (dur - hold), 'inout')
        sc = s_hold * (s_land / s_hold) ** p      # 缩放按几何插值，推进速度均匀
        w = (1 / sc - 1 / s_hold) / (1 / s_land - 1 / s_hold)
        c = c_full + (c_land - c_full) * w
    # 推进后半段把预览区里的说明框和箭头渐渐清掉，落点和后面镜头一致
    a = min(1.0, max(0.0, (p - 0.5) / 0.4))
    if a > 0:
        fr = fr.copy()
        v = fr[VIEW_Y:VIEW_Y + SRC_H, VIEW_X:VIEW_X + SRC_W]
        fr[VIEW_Y:VIEW_Y + SRC_H, VIEW_X:VIEW_X + SRC_W] = (v * (1 - a) + clean(v) * a).astype(np.uint8)
    # 缩得很小时先用面积插值降采样，界面文字不闪
    pre = 1.0
    if sc < 0.6:
        pre = min(1.0, sc * 1.5)
        fr = cv2.resize(fr, None, fx=pre, fy=pre, interpolation=cv2.INTER_AREA)
    k = sc / pre
    M = np.float32([[k, 0, OUT_W / 2 - c[0] * sc], [0, k, OUT_H / 2 - c[1] * sc]])
    img = cv2.warpAffine(fr, M, (OUT_W, OUT_H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    cover = cv2.warpAffine(np.full(fr.shape[:2], 255, np.uint8), M, (OUT_W, OUT_H), flags=cv2.INTER_LINEAR)
    if cover.min() < 255:
        # 屏幕没铺满的上下部分：同一帧放大、模糊、压暗当背景
        small = cv2.resize(fr, (64, 36), interpolation=cv2.INTER_AREA)
        bg = cv2.resize(small, (int(OUT_H * 16 / 9) + 2, OUT_H), interpolation=cv2.INTER_CUBIC)
        x0 = (bg.shape[1] - OUT_W) // 2
        bg = cv2.GaussianBlur(bg[:, x0:x0 + OUT_W], (0, 0), 25).astype(np.float32) * 0.45
        m = cover[..., None].astype(np.float32) / 255
        # 屏幕边缘加一点阴影
        sh = cv2.GaussianBlur(cover, (0, 0), 18)[..., None].astype(np.float32) / 255
        bg = bg * (1 - 0.6 * sh)
        img = (img * m + bg * (1 - m)).astype(np.uint8)
    return img


def main(src, out, full_src):
    title = text_layer_title()
    end = text_layer_end()
    enc = subprocess.Popen(
        [FF, '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OUT_W}x{OUT_H}',
         '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', out],
        stdin=subprocess.PIPE)
    rng = np.random.default_rng(3)
    nframes = int(round(TOTAL * FPS))
    for sh in SHOTS:
        o0, o1 = sh['o']
        fx = sh.get('fx', [])
        rd = None
        if 'ui' in sh:
            rd = Reader(full_src, sh['s'], (o1 - o0) * sh['sp'], FULL_W, FULL_H, vf='fps=60')
        elif sh['s'] is not None:
            rd = Reader(src, sh['s'], (o1 - o0) * sh['sp'])
        f0, f1 = int(round(o0 * FPS)), min(int(round(o1 * FPS)), nframes)
        for k in range(f0, f1):
            t = k / FPS
            lt = t - o0
            x = lt / (o1 - o0)
            if rd is None:
                img = np.zeros((OUT_H, OUT_W, 3), np.uint8)
                a = min(1, max(0, (lt - 0.15) / 0.5)) * min(1, max(0, (o1 - t - 0.1) / 0.5))
                img = comp(img, end, a)
                enc.stdin.write(img.tobytes())
                continue
            n = int(round(lt * sh['sp'] * SRC_FPS))
            if 'ui' in sh:
                img = ui_frame(rd.get(n), lt, o1 - o0, sh['ui']['hold'], sh['ui']['land'], sh['ui'].get('zl', 1.0)).astype(np.float32)
                if 'fadein' in fx:
                    img *= min(1, lt / 0.4)
                enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
                continue
            fr = clean(rd.get(n))
            e =ease(x, sh.get('ease', 'inout' if sh['z'][0] != sh['z'][1] else 'lin'))
            z = sh['z'][0] + (sh['z'][1] - sh['z'][0]) * e
            (cx0, cy0), (cx1, cy1) = sh['c']
            cx, cy = cx0 + (cx1 - cx0) * e, cy0 + (cy1 - cy0) * e
            dx = dy = 0.0
            if 'shake' in fx and lt < 0.35:
                amp = 22 * (1 - lt / 0.35)
                dx, dy = rng.uniform(-amp, amp), rng.uniform(-amp, amp)
            if 'shake_in' in fx and lt < 0.15:
                amp = 10 * (1 - lt / 0.15)
                dx, dy = rng.uniform(-amp, amp), rng.uniform(-amp, amp)
            img = view(fr, z, cx, cy, dx, dy).astype(np.float32)
            if 'fadein' in fx:
                img *= min(1, lt / 0.45)
            if 'fadeout' in fx:
                img *= min(1, max(0, (o1 - t) / 0.8))
            if 'flash' in fx and lt < 0.25:
                a = 1 - lt / 0.25
                img = img * (1 - a) + 255 * a
            if 'flash_soft' in fx and lt < 0.12:
                a = 0.5 * (1 - lt / 0.12)
                img = img * (1 - a) + 255 * a
            img = np.clip(img, 0, 255).astype(np.uint8)
            if 'title' in fx:
                a = min(1, max(0, (lt - 0.35) / 0.4))
                img = comp(img, title, a)
            enc.stdin.write(img.tobytes())
        if rd:
            rd.close()
        print(f'shot {o0:5.2f}-{o1:5.2f} done', flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
