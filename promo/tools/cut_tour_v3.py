"""
游览版视频《这把剑，他自己拔不出来》粗剪（逐字稿 promo/逐字稿_游览版_v3.md）。

素材：
  promo/raw/tour_v3/<镜头>/f_NNNN.jpg   tools/record_tour.mjs + shots_v3.json 录的（30 fps；m 开头是手机横屏 1688×780）
  promo/raw/audio_v3/*.wav             tools/render_audio.mjs + audio_v3.json，游览版自己的声音引擎合成的音乐、环境声、音效
  promo/raw/voice_v3/L*.wav、H*.wav    用户录的配音（11-03），tools/voice_cut_v3.py 切成句；L 是拔剑和收，H 是花絮
  promo/翻车集/                         花絮
  web/public/textures/kit/map_scroll_painted.jpg  绘卷总地图

用法：uv run --with numpy --with pillow --with scipy --with imageio --with imageio-ffmpeg python promo/tools/cut_tour_v3.py [--from 秒 --to 秒]（只出一段预览）
输出：promo/游览版_形真理_粗剪v3.mp4
前半段（0~4 节）只有字幕和声音；后半段（5~6 节）和花絮（7 节）是用户的口播，配竖排字幕。
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "promo"
RAW = P / "raw/tour_v3"; AUD = P / "raw/audio_v3"; VO = P / "raw/voice_v3"; NG = P / "翻车集"
FF = str(Path.home() / "socialmedia/tools/bin/ffmpeg")
W, H, FPS, SR = 1920, 1080, 30, 44100
OUT = P / "游览版_形真理_粗剪v3.mp4"   # v0 11-03 第一版（慢、横排字幕、讲捕鼠夹）；v1 竖排字幕、压节奏；v2 地点之间换成襖转场；v3 换成用户的配音，花絮改成口播
hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
PAPER, INK, CRIMSON, NAVY = hx("#F1E9DA"), hx("#322D48"), hx("#B42A47"), hx("#2A2A4E")
SONGTI = "/System/Library/Fonts/Songti.ttc"   # 宋体 SC（明朝体那一路的衬线）；ヒラギノ明朝没有简体字
ss = lambda x: x * x * (3 - 2 * x)
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))

# ---------------------------------------------------------------- 画面素材
_cache = {}
def jpg(path):
    if path not in _cache:
        if len(_cache) > 64: _cache.clear()
        _cache[path] = np.asarray(Image.open(path).convert("RGB"))
    return _cache[path]

_nframes = {}
def clip_frame(name, t):
    if name not in _nframes: _nframes[name] = len(list((RAW / name).glob("f_*.jpg")))
    i = int(clamp(round(t * FPS), 0, _nframes[name] - 1))
    return jpg(RAW / name / f"f_{i:04d}.jpg")

# 纹样底（手机横屏、竖版、翻车素材垫在下面）：pattern_bg.py 的单纹样版
sys.path.insert(0, str(Path(__file__).parent))
import pattern_bg as PB
def pattern(t):
    off = int(PB.SINGLE[4] * t) % W
    return np.clip(PB.sheet[:H, off:off + W] + PB.grain, 0, 255).astype(np.uint8)

def on_pattern(img, t, h=1000, zoom=0.0):
    """把一张图（ndarray 或 PIL）按高度 h 放在纹样底正中，墨框"""
    im = img if isinstance(img, Image.Image) else Image.fromarray(img)
    s = h * (1 + zoom) / im.height; w2, h2 = int(im.width * s), int(im.height * s)
    if w2 > W - 60: s = (W - 60) / im.width; w2, h2 = int(im.width * s), int(im.height * s)
    im = im.resize((w2, h2), Image.LANCZOS)
    bg = Image.fromarray(pattern(t)); x, y = (W - w2) // 2, (H - h2) // 2
    ImageDraw.Draw(bg).rectangle((x - 10, y - 10, x + w2 + 9, y + h2 + 9), fill=INK)
    bg.paste(im, (x, y)); return np.asarray(bg)

def phone(img, t):
    """手机横屏录屏套一个墨色手机壳，放在纹样底上"""
    im = Image.fromarray(img).resize((1560, 721), Image.LANCZOS)
    bg = Image.fromarray(pattern(t)); d = ImageDraw.Draw(bg)
    x, y = (W - 1560) // 2, (H - 721) // 2
    d.rounded_rectangle((x - 46, y - 30, x + 1560 + 46, y + 721 + 30), radius=70, fill=INK)
    d.rounded_rectangle((x - 40, y - 24, x + 1560 + 40, y + 721 + 24), radius=64, outline=(90, 84, 120), width=3)
    d.ellipse((x - 30, y + 721 // 2 - 9, x - 12, y + 721 // 2 + 9), fill=(20, 18, 30))   # 前置摄像头
    bg.paste(im, (x, y)); return np.asarray(bg)

def black(t): return np.full((H, W, 3), (18, 16, 26), np.uint8)

MAP = Image.open(ROOT / "web/public/textures/kit/map_scroll_painted.jpg").convert("RGB")
PLACES = {p["id"]: p for p in json.load(open(ROOT / "web/src/data/tour/map.json"))["places"]}
def mview(cx, cy, h):
    w = h * 16 / 9; cx = clamp(cx, w / 2, MAP.width - w / 2); cy = clamp(cy, h / 2, MAP.height - h / 2)
    return np.asarray(MAP.resize((W, H), Image.BILINEAR, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)))
def place_c(pid): r = PLACES[pid]["rect"]; return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
def map_move(a, b, dur):
    """地图从 a=(cx,cy,h) 移到 b，中途稍微拉远一点"""
    def f(t):
        u = ss(clamp(t / dur)); bump = 1 + 0.25 * np.sin(np.pi * u) * (a[2] < 900)
        return mview(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, (a[2] + (b[2] - a[2]) * u) * bump)
    return f
def map_full(t):
    z = 1 + 0.05 * t / 6; w, h = int(W * z), int(640 * z)
    im = MAP.resize((w, h), Image.LANCZOS).crop(((w - W) // 2, 0, (w - W) // 2 + W, h))
    bg = Image.new("RGB", (W, H), (18, 16, 26)); bg.paste(im, (0, (H - h) // 2)); return np.asarray(bg)

def fusuma(fn, t, t_open=0.35, dur=0.9):
    """拉门打开：两扇纸门从中间往两边滑开，露出后面的画面"""
    out = Image.fromarray(fn(t)); p = ss(clamp((t - t_open) / dur))
    if p >= 1: return np.asarray(out)
    d = ImageDraw.Draw(out); half = W // 2; off = int(half * p)
    for side in (-1, 1):
        x0 = 0 - off if side < 0 else half + off; x1 = x0 + half
        d.rectangle((x0, 0, x1, H), fill=PAPER)
        d.rectangle((x0 + 12, 12, x1 - 12, H - 12), outline=INK, width=10)
        for k in range(1, 5): d.line((x0 + 12, k * H // 5, x1 - 12, k * H // 5), fill=(200, 192, 178), width=3)
        hx_ = x1 - 90 if side < 0 else x0 + 90
        d.ellipse((hx_ - 28, H // 2 - 28, hx_ + 28, H // 2 + 28), outline=INK, width=8)   # 引手
    return np.asarray(out)

# 地点转场（11-03 用户定 B 襖样式，title_cards.py 的 card_B_layers）：
#   0~0.45 秒两扇门从两边合上，盖住上一个镜头；0.3~0.7 短册从上面落下来；停一下；
#   1.35~1.65 短册往上收、变淡；1.45~2.3 两扇门往两边拉开，边拉边变淡，露出下一个地方（下一个镜头已经在动）
import title_cards as TC
DOOR_DUR, OPEN_T0 = 2.3, 1.45
_tc = {}
def tc_layers(pid):
    if pid not in _tc:
        L = TC.card_B_layers(next(P for P in TC.PLACES if P["id"] == pid))
        _tc[pid] = {k: np.asarray(v).astype(np.float32) for k, v in L.items()}
    return _tc[pid]

def over(dst, src, x, y, alpha=1.0):
    h, w = src.shape[:2]; x, y = int(round(x)), int(round(y))
    x0, x1, y0, y1 = max(0, x), min(W, x + w), max(0, y), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or alpha <= 0: return
    sp = src[y0 - y:y1 - y, x0 - x:x1 - x]; a = sp[..., 3:4] / 255 * alpha
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + sp[..., :3] * a

def door_trans(pid, prev_fn, prev_t, next_fn):
    L = tc_layers(pid); half = W // 2
    out_back = lambda u: 1 + 2.2 * (u - 1) ** 3 + 1.2 * (u - 1) ** 2   # 落下时稍微冲过头再回来
    def f(t):
        if t < 0.45:   # 合门
            base = prev_fn(prev_t).astype(np.float32); p = 1 - (1 - t / 0.45) ** 3; a = 0.35 + 0.65 * p
            off = half * (1 - p)
        elif t < OPEN_T0:
            base = np.zeros((H, W, 3), np.float32); off, a = 0.0, 1.0
        else:          # 拉开 + 变淡
            base = next_fn(t - OPEN_T0).astype(np.float32); q = ss(clamp((t - OPEN_T0) / (DOOR_DUR - OPEN_T0)))
            off, a = half * q, 1 - q ** 1.2
        over(base, L["left"], -off, 0, a); over(base, L["right"], half + off, 0, a)
        if 0.3 <= t < 1.65:   # 短册
            if t < 0.7: dy, sa = -1100 * (1 - out_back(clamp((t - 0.3) / 0.4))), 1.0
            elif t < 1.35: dy, sa = 0.0, 1.0
            else: v = ss(clamp((t - 1.35) / 0.3)); dy, sa = -240 * v, 1 - v
            over(base, L["strip"], 0, dy, sa)
        return np.clip(base, 0, 255).astype(np.uint8)
    return f

DOOR_SFX = [(0.0, "sfx_slide", 0.7), (0.42, "sfx_hyoshigi", 0.9), (OPEN_T0, "sfx_slide", 0.9)]
def door(pid, name, t0):
    """在时间线上加一段地点转场；下一个镜头 name 从 t0 开始，转场里已经播了 DOOR_DUR - OPEN_T0 秒，返回接着播的起点"""
    prev = SEGS[-1]
    seg(DOOR_DUR, door_trans(pid, prev["fn"], prev["dur"] - 1 / FPS, C(name, t0)), sfx=DOOR_SFX)
    return t0 + DOOR_DUR - OPEN_T0

# ---------------------------------------------------------------- 字幕和印章
# 字幕竖排（11-03 用户定）：第一句在画面左侧一列，第二句（"/" 后面）在右侧一列；字体报隶（粗隶书，比宋体更像怪化猫的字卡）
import glob as _glob
BAOLI = sorted(_glob.glob("/System/Library/AssetsV2/**/Baoli.ttc", recursive=True))[0]
PUNCT = "，。、！？"
_txt = {}
def _finish(lay, sh):
    lay = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), lay)
    a = np.asarray(lay).astype(np.float32); ys, xs = np.nonzero(a[..., 3] > 0)
    box = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
    return (a[box[0]:box[1], box[2]:box[3]], box)

def vcol(d, ds, txt, xc, y0, size, fill=PAPER):
    """一列竖排：每字一格，标点放在格子右上角"""
    f = ImageFont.truetype(BAOLI, size); step = size * 1.08
    for i, ch in enumerate(txt):
        y = y0 + i * step
        if ch in PUNCT: x, y = xc + size * 0.1, y - size * 0.35
        else: x = xc - d.textlength(ch, font=f) / 2
        ds.text((x, y), ch, font=f, fill=(0, 0, 0, 210), stroke_width=12, stroke_fill=(0, 0, 0, 210))
        d.text((x, y), ch, font=f, fill=fill + (255,), stroke_width=4, stroke_fill=INK + (255,))

def text_layer(text, center=False, size=None):
    key = (text, center, size)
    if key in _txt: return _txt[key]
    cols = [c.strip() for c in text.split("/")]
    size = size or 76
    size = min(size, int(880 / (1.08 * max(len(c) for c in cols))))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    if center:   # 黑场：几列挨着放在正中，从左往右读
        gap = size * 1.7; xs = [W / 2 + (i - (len(cols) - 1) / 2) * gap for i in range(len(cols))]
        for c, x in zip(cols, xs): vcol(d, ds, c, x, (H - len(c) * size * 1.08) / 2, size)
    else:        # 画面上：第一句左边，第二句右边
        vcol(d, ds, cols[0], 150, 120, size)
        if len(cols) > 1: vcol(d, ds, cols[1], W - 150, 120, size)
    _txt[key] = _finish(lay, sh); return _txt[key]

def card3(i):
    """形真理字卡：三列，每列一个大字 + 下面一句小字，从左往右"""
    key = ("card3", i)
    if key in _txt: return _txt[key]
    big, small = [("形", "它是什么"), ("真", "发生了什么"), ("理", "为什么")][i]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ds = ImageDraw.Draw(sh)
    x = W / 2 + (i - 1) * 300
    vcol(d, ds, big, x, 230, 150, fill=hx("#E6667A"))
    vcol(d, ds, small, x, 430, 62)
    _txt[key] = _finish(lay, sh); return _txt[key]

def seal_layer(ch):
    key = ("seal", ch)
    if key in _txt: return _txt[key]
    S = 120; im = Image.new("RGBA", (S + 20, S + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, S + 10, S + 10), radius=10, fill=CRIMSON + (235,), outline=PAPER + (255,), width=4)
    f = ImageFont.truetype(BAOLI, 92); tw = d.textlength(ch, font=f)
    d.text((10 + (S - tw) / 2, 14), ch, font=f, fill=PAPER + (255,))
    a = np.asarray(im).astype(np.float32); x, y = W - 210, H - 200   # 右下角，让开右侧那列字幕
    _txt[key] = (a, (y, y + a.shape[0], x, x + a.shape[1])); return _txt[key]

def blend(frame, layer, alpha):
    if alpha <= 0: return frame
    a, (y0, y1, x0, x1) = layer
    reg = frame[y0:y1, x0:x1].astype(np.float32); m = a[..., 3:4] / 255 * alpha
    frame[y0:y1, x0:x1] = (reg * (1 - m) + a[..., :3] * m).astype(np.uint8); return frame

# ---------------------------------------------------------------- 时间线
# 每段：(秒数, 画面函数 f(t), 字幕 [(起, 止, 文字, 居中?)], 声音 [(秒, 文件, 音量)], 印章 (秒, 字) 或 None)
SEGS = []
def seg(dur, fn, subs=(), sfx=(), seal=None, tag=""):
    SEGS.append(dict(dur=dur, fn=fn, subs=list(subs), sfx=list(sfx), seal=seal, tag=tag))
C = lambda name, t0=0.0, speed=1.0: (lambda t: clip_frame(name, t0 + t * speed))
M = lambda name, t0=0.0: (lambda t: phone(clip_frame(name, t0 + t), t))
vo_len = lambda k: wave.open(str(VO / f"{k}.wav")).getnframes() / SR

# v1（11-03 用户：节奏太慢、在前面一个场景走来走去；字幕竖排；捕鼠夹画面里没有，先不讲）：每个镜头压到 2~3.5 秒，
# "规矩"挪到坂井家红廊下（万屋外景只在冷开场和万屋那节出现），坂井家的"形"换成屋后的小坟
# 0. 冷开场：定格 + 字幕，雨声进来时画面才动
seg(1.3, lambda t: clip_frame("s0_soto_open", 0), [(0.15, 1.3, "怪化猫/第几集？", False)], tag="冷开场")
seg(1.8, C("s0_soto_open", 1.4))
# 1. 规矩
seg(3.2, C("s1a_rouka", 0.4), [(0.2, 3.1, "这个卖药的/背着一把剑", False)], tag="规矩")
seg(2.6, C("s1b_rouka"), [(0.15, 2.5, "可这把剑/他自己拔不出来", False)])
seg(1.6, black, [(0.15, 1.55, "要先弄清楚/三样东西", True)])
seg(3.0, black, [(0.15, 3.0, "", "c3a"), (0.75, 3.0, "", "c3b"), (1.35, 3.0, "", "c3c")],
    sfx=[(0.15, "sfx_hyoshigi", 0.8), (0.75, "sfx_hyoshigi", 0.8), (1.35, "sfx_hyoshigi", 0.9)])
sx, sy = place_c("sakai")
t0 = door("sakai", "s2a_gate", 1.0)
# 2. 坂井家 · 形
seg(2.5, C("s2a_gate", t0), [(0.1, 2.4, "一户武家/在嫁女儿", False)], tag="坂井家")
seg(2.4, C("s2b_ozashiki", 0.6), [(0.15, 2.3, "上上下下/都在笑", False)])
seg(3.6, C("s2c_grave", 0.2), [(0.2, 3.5, "屋后却有一座小坟/摆着新鲜的花", False)], seal=(0.2, "形"))
seg(1.0, C("s2d_misshitsu", 0.8), sfx=[(0.0, "sfx_taiko", 0.5)])
wx, wy = place_c("wanya")
t0 = door("wanya", "s3a_bridge", 1.2)
# 3. 万屋 · 真
seg(2.6, C("s3a_bridge", t0), [(0.1, 2.5, "一个下雨的晚上", False)], tag="万屋")
seg(3.0, C("s3b_glassdoor", 0.5), [(0.15, 2.9, "有人推开旅馆的门/求一间房", False)], sfx=[(0.05, "sfx_slide", 0.6)])
seg(2.8, C("s3c_rouka", 1.0), [(0.15, 2.7, "顶层那间屋子/从来不给客人住", False)])
seg(3.2, lambda t: fusuma(C("s3d_ozashiki", 0.5), t, t_open=0.15, dur=0.7), [(0.9, 3.1, "那天晚上/门开了", False)], sfx=[(0.15, "sfx_slide", 1.0)], seal=(0.9, "真"))
ox, oy = place_c("ooku")
t0 = door("ooku", "s4a_corridor", 1.6)
# 4. 大奥 · 理
seg(3.0, C("s4a_corridor", t0), [(0.1, 2.9, "一个男人/进不来的地方", False)], tag="大奥")
seg(3.2, C("s4b_courtyard", 1.2), [(0.15, 3.1, "新来的女中/进门第一件事", False)], seal=(0.15, "理"))
seg(2.2, C("s4c_well", 0.6), [(0.1, 2.15, "把最心爱的东西/丢进这口井", False)], sfx=[(1.0, "splash", 0.9)])
seg(2.4, C("s4d_lookup", 0.5), [(0.7, 2.4, "为什么", False)], sfx=[(0.7, "sfx_bell", 0.5)])
# 5. 拔剑（口播，11-03 换成用户的录音；口播也配竖排字幕，字幕去掉"的话呢"这类口头词）
V = {k: vo_len(k) for k in "L1 L2 L3 L4 L5 L6 L7 L8 H0 H1 H2 H3 H4 H5 H6".split()}
def vo(k, at, subs=(), pad=0.35, fn=black, sfx=(), tag="", seal=None):
    """一句口播一段：at 秒开口，字幕 [(相对开口的起, 止, 文字)]，止填 None 就到这句说完"""
    seg(at + V[k] + pad, fn, [(at + a0, at + (V[k] + 0.1 if a1 is None else a1), txt, False) for a0, a1, txt in subs],
        sfx=[(at, "VO:" + k, 1.0)] + list(sfx), tag=tag, seal=seal)
seg(0.3, black, tag="拔剑")
l2 = 0.3 + V["L1"] + 0.1   # "不过在这里"还压在地图上，"按 X 就行"切到拔剑
seg(l2 + V["L2"] + 0.1, map_full, [(0.3, 1.75, "形，真，理", False), (1.8, l2 - 0.05, "三样凑不齐/剑就拔不出来", False), (l2, l2 + V["L2"], "不过在这里", False)],
    sfx=[(0.3, "VO:L1", 1.0), (l2, "VO:L2", 1.0)])
vo("L3", 0.05, [(0, None, "按X就行")], pad=2.7, fn=C("s5_sword", 1.0), sfx=[(0.8, "sfx_unsheathe", 0.9)])
vo("L4", 0.2, [(0, None, "手机上/点一下也可以")], pad=0.5, fn=M("m3_sword", 0.6), sfx=[(0.45, "sfx_unsheathe", 0.7)])
vo("L5", 0.25, [(0, None, "就是按得/不太好看")], pad=0.3, fn=lambda t: on_pattern(read_ext("008", t + 2.2), t), sfx=[(0.0, "sfx_taiko", 0.9)])
# 6. 收
vo("L6", 0.3, [(0, None, "这三个地方/我都照着原作搭出来了")], fn=C("s6_niwa_bridge", 0.6), tag="收")
# m1 在 2.5 秒穿过房间转场（白一帧）、后面镜头贴墙，只用前 2.4 秒，后面接坂井家厨房走过（没用过的镜头）
vo("L7", 0.2, [(0, None, "结局你可以扮成他/自己去探索来看")], fn=lambda t: M("m1_stick_walk")(t) if t < 2.4 else clip_frame("s2c_kitchen", t - 2.4))
vo("L8", 0.2, [(0, None, "链接在简介/手机和电脑都可以用")], pad=0.5, fn=M("m2_card", 2.6), sfx=[(0.4, "sfx_paper", 0.8)])
# 7. 花絮（口播：番头双面头 → 高斯泼溅穿模 → 脚 → 调好了 → 接下来要做的 → 来试玩）
seg(V["H0"] + 0.6, black, [(0.15, V["H0"] + 0.55, "花絮", "big")], sfx=[(0.1, "sfx_hyoshigi", 1.2), (0.3, "VO:H0", 1.0)], tag="花絮")
TOKUJI = Image.open(NG / "004_徳次_双面头_改前改后.jpg").convert("RGB")
vo("H1", 0.1, [(0.2, 2.85, "其实番头的后脑勺/是个双面人"), (2.9, 4.3, "所以后面/还有一张脸"), (4.35, None, "但是后来/改掉了")],
   fn=lambda t: on_pattern(np.asarray(TOKUJI.crop((0, 0, 900, 506))), t, h=860, zoom=0.04 * t) if t < 4.45 else on_pattern(np.asarray(TOKUJI), t, h=860),
   sfx=[(0.0, "sfx_hyoshigi", 1.2), (4.45, "sfx_hyoshigi", 1.0)])
BOX = np.asarray(Image.open(NG / "001_药郎走路_药箱离体.webp").convert("RGB"))
vo("H2", 0.1, [(0, 1.5, "因为用的是/高斯泼溅"), (1.55, None, "所以/会有一些穿模")],
   fn=lambda t: clip_frame("s7_blur", 1.5 + t) if t < 1.65 else on_pattern(BOX, t, h=980, zoom=0.03 * (t - 1.65)), sfx=[(1.65, "sfx_hyoshigi", 1.2)])
vo("H3", 0.05, [(0, 2.2, "包括他的脚/可能也有一些"), (2.25, None, "折叠起来了")], fn=lambda t: on_pattern(read_ext("003", t + 0.6), t, h=900), sfx=[(0.0, "sfx_hyoshigi", 1.2)])
vo("H4", 0.05, [(0, None, "最后/还是调好了")], pad=0.45, fn=C("s1a_back", 1.0))
vo("H5", 0.1, [(0, 3.0, "接下来/可能还会做一些动作"), (3.1, 5.0, "还有/物怪的出现"), (5.1, None, "可能增加一些/真实打斗砍击的感觉")],
   fn=lambda t: on_pattern(read_ext("yp", 3.0 + t), t, h=1000) if t < 3.15 else (clip_frame("s2d_misshitsu", t - 3.15) if t < 5.15 else clip_frame("s5_sword", 4.9 + t - 5.15)),
   sfx=[(3.15, "sfx_taiko", 0.6), (5.15 + 1.0, "sfx_slash", 0.6), (5.15 + 2.6, "sfx_sheath", 0.6)])
vo("H6", 0.1, [(0, None, "大家来试玩一下/多给一点建议吧")], pad=0.3, fn=lambda t: map_full(t + 2))
seg(1.8, black, [(0.1, 1.8, "链接在简介/电脑手机都能玩", True)])

EXT = {"003": (NG / "003_药郎冲刺_前脚踢出下摆_改前.mp4", 0, 99), "008": (NG / "008_药郎拔剑_剑穿袖子_药箱乱甩_改前.mp4", 0, 99),
       "yp": (P / "药郎角色样片_v2.mp4", 3.0, 6.3)}   # 样片是竖版 1206×1608，只留用到的几秒，不然整条进内存太大
_ext = {}
def read_ext(k, t):
    if k not in _ext:
        import imageio.v2 as iio
        path, a, b = EXT[k]; r = iio.get_reader(str(path)); fps = r.get_meta_data()["fps"]
        _ext[k] = ({i: f for i, f in enumerate(r) if a * fps <= i <= b * fps}, fps)
    fr, fps = _ext[k]; i = int(t * fps); return fr[min(max(i, min(fr)), max(fr))]

# 段落起点
t = 0.0
for S in SEGS: S["t0"] = t; t += S["dur"]
TOTAL = t
starts = {S["tag"]: S["t0"] for S in SEGS if S["tag"]}

# ---------------------------------------------------------------- 声音
def wav(name):
    if name == "splash": return splash()
    path = (VO / f"{name[3:]}.wav") if name.startswith("VO:") else AUD / f"{name}.wav"
    w = wave.open(str(path)); n = w.getnframes(); ch = w.getnchannels()
    a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    a = a.reshape(-1, ch)
    return np.repeat(a, 2, 1) if ch == 1 else a

def splash():
    """东西落进井里：一下水声 + 井里的回声（噪声低通，几次衰减的延迟）"""
    rng = np.random.default_rng(4); n = int(SR * 2.5); t = np.arange(n) / SR
    from scipy.signal import butter, sosfilt
    hit = rng.standard_normal(n) * np.exp(-t / 0.06); hit = sosfilt(butter(2, [300, 2500], "band", fs=SR, output="sos"), hit)
    bub = np.sin(2 * np.pi * (500 + 900 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.09) * 0.4
    s = hit + bub; out = s.copy()
    for k, (d, g) in enumerate(((0.19, 0.5), (0.38, 0.3), (0.57, 0.18), (0.76, 0.1))):
        i = int(d * SR); out[i:] += sosfilt(butter(2, 1200 - k * 200, "low", fs=SR, output="sos"), s)[: n - i] * g
    out *= 0.6 / np.abs(out).max(); return np.stack([out, out], 1)

def drip():
    t = np.arange(int(SR * 0.3)) / SR
    s = np.sin(2 * np.pi * (1500 - 2600 * t) * t) * np.exp(-t / 0.035) * 0.25; return np.stack([s, s], 1)

N = int(TOTAL * SR) + SR
mix = {k: np.zeros((N, 2), np.float32) for k in ("music", "amb", "sfx", "vo")}
def put(bus, a, t0, gain=1.0):
    i = int(t0 * SR); a = a[: max(0, N - i)]; mix[bus][i:i + len(a)] += a * gain
def bed(bus, name, t0, t1, gain, fin=0.6, fout=0.8, offset=0.0):
    a = wav(name); n = int((t1 - t0) * SR); o = int(offset * SR)
    reps = (o + n) // len(a) + 2; a = np.tile(a, (reps, 1))[o:o + n].copy()
    env = np.ones(n, np.float32); fi, fo = int(fin * SR), int(fout * SR)
    env[:fi] = np.linspace(0, 1, fi); env[n - fo:] *= np.linspace(1, 0, fo)
    put(bus, a * env[:, None], t0, gain)

seg_t = lambda i: SEGS[i]["t0"]
by_tag = lambda tag: next(i for i, S in enumerate(SEGS) if S["tag"] == tag)
A = 12.0   # 游戏里环境声录得很轻，统一放大
i_s, i_w, i_o = by_tag("坂井家"), by_tag("万屋"), by_tag("大奥")
# 环境声：按镜头
bed("amb", "amb_rain", starts["冷开场"] + 1.3, starts["冷开场"] + 3.1, 0.11 * A, fin=0.1, fout=0.4)
bed("amb", "amb_room", starts["规矩"], starts["规矩"] + 5.8, 0.3 * A)
bed("amb", "amb_crowd", seg_t(i_s) - 0.85, seg_t(i_s + 1), 0.10 * A, fin=0.4, fout=0.3)
bed("amb", "amb_crowd_in", seg_t(i_s + 1), seg_t(i_s + 2) + 0.3, 0.18 * A, fin=0.2, fout=0.4)   # 走到屋后，热闹一下子收掉
bed("amb", "amb_wind", seg_t(i_s + 2), seg_t(i_s + 4), 0.08 * A, fin=0.4)
bed("amb", "amb_rain", seg_t(i_w) - 0.85, seg_t(i_w + 1) + 0.3, 0.11 * A, fin=0.4)
bed("amb", "amb_rain_in", seg_t(i_w + 1), seg_t(i_w + 3), 0.25 * A)
bed("amb", "amb_room", seg_t(i_w + 3), seg_t(i_w + 4), 0.3 * A)
bed("amb", "amb_wind", seg_t(i_o) - 0.85, starts["拔剑"] - 1.6, 0.12 * A, fin=0.4, fout=0.3)
# 音乐：前半段低沉（dark），"为什么"那一下收掉；拔剑后接 dark 轻一点；花絮换坂井家的三味线
m0 = starts["规矩"]; m1 = starts["拔剑"] - 1.6
bed("music", "music_dark", m0, m1, 3.2, fin=1.5, fout=0.4)
bed("music", "music_dark", starts["拔剑"] + 0.3, starts["花絮"], 1.5, fin=1.0, fout=0.8, offset=40)
bed("music", "music_sakai", starts["花絮"] + 0.1, TOTAL, 1.3, fin=0.2, fout=1.2)
for i, S in enumerate(SEGS):
    for (ts, name, g) in S["sfx"]: put("vo" if name.startswith("VO:") else "sfx", wav(name), S["t0"] + ts, g)
def duck(t0, t1, g):
    i0, i1 = int(t0 * SR), int(t1 * SR); n = i1 - i0; env = np.full(n, g, np.float32); r = min(int(0.3 * SR), n // 2)
    env[:r] = np.linspace(1, g, r); env[n - r:] = np.linspace(g, 1, r); mix["music"][i0:i1] *= env[:, None]
duck(seg_t(i_s + 2) + 0.1, seg_t(i_s + 3) + 0.8, 0.35)    # 小坟
duck(seg_t(i_w + 3) + 0.1, seg_t(i_w + 3) + 2.0, 0.3)     # 门开了
# 口播时音乐让开
vo_env = np.abs(mix["vo"]).max(1)
from scipy.ndimage import maximum_filter1d, uniform_filter1d
vo_env = uniform_filter1d(maximum_filter1d((vo_env > 0.01).astype(np.float32), int(0.4 * SR)), int(0.3 * SR))
mix["music"] *= (1 - 0.55 * vo_env)[:, None]; mix["amb"] *= (1 - 0.4 * vo_env)[:, None]
# 11-03 用户嫌口播不清楚：原来整条按音乐的峰值归一，人声只比音乐高 4 dB。现在音乐、环境声、音效按原来的办法归一，
# 人声单独定音量（说话时的均方根到 -17 dBFS，原录音不做任何处理），最后整体峰值超了才一起往下压
bedmix = (mix["music"] + mix["amb"] + mix["sfx"])[: int(TOTAL * SR)]; bedmix *= 0.89 / max(1e-6, np.abs(bedmix).max())
vo_on = vo_env[: int(TOTAL * SR)] > 0.5; vo = mix["vo"][: int(TOTAL * SR)]
vo_gain = 10 ** (-17 / 20) / max(1e-6, np.sqrt((vo[vo_on] ** 2).mean()))
master = bedmix + vo * vo_gain
master *= min(1.0, 0.97 / max(1e-6, np.abs(master).max()))

# ---------------------------------------------------------------- 输出
def render(t0=0.0, t1=TOTAL, out=OUT):
    tmpv = P / "raw/_cut_tour_v3_video.mp4"; tmpa = P / "raw/_cut_tour_v3_audio.wav"
    a = master[int(t0 * SR): int(t1 * SR)]
    with wave.open(str(tmpa), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(tmpv)], stdin=subprocess.PIPE)
    n0, n1 = round(t0 * FPS), round(t1 * FPS); si = 0
    for fi in range(n0, n1):
        t = fi / FPS
        while si < len(SEGS) - 1 and t >= SEGS[si + 1]["t0"]: si += 1
        S = SEGS[si]; lt = t - S["t0"]
        fr = np.array(S["fn"](lt), dtype=np.uint8, copy=True)
        if fr.shape[:2] != (H, W): fr = np.asarray(Image.fromarray(fr).resize((W, H), Image.LANCZOS)).copy()
        for (a0, a1, txt, mode) in S["subs"]:
            if not (a0 <= lt <= a1): continue
            al = min(clamp((lt - a0) / 0.3), clamp((a1 - lt) / 0.3))
            if isinstance(mode, str) and mode != "big": blend(fr, card3("c3a c3b c3c".split().index(mode)), al)   # 形真理字卡
            elif mode == "big": blend(fr, text_layer(txt, True, 170), al)
            else: blend(fr, text_layer(txt, mode), al)
        if S["seal"] and lt >= S["seal"][0]:
            k = clamp((lt - S["seal"][0]) / 0.25); blend(fr, seal_layer(S["seal"][1]), k * min(1, clamp((S["dur"] - lt) / 0.25)))
        # 段与段之间：花絮前、拔剑前是黑场切，其余直切
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(tmpv), "-i", str(tmpa), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    print(out, f"{t1 - t0:.1f} 秒")

if __name__ == "__main__":
    print("总长", round(TOTAL, 1), "秒；各节起点", {k: round(v, 1) for k, v in starts.items()})
    if "--from" in sys.argv:
        a, b = float(sys.argv[sys.argv.index("--from") + 1]), float(sys.argv[sys.argv.index("--to") + 1])
        render(a, b, P / "raw/_preview.mp4")
    else: render()
