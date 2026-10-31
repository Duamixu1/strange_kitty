"""快剪镜头左上角的名字标签，几种风格。label(style, 标题, 小字) → 1920×1080 透明 PNG（Image）。
颜色全部取游戏色板（docs/02_设定.md）。字体：标题宋体（Songti SC），小字圆体。
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"          # 0 Black, 1 Bold
YUANTI = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData/Yuanti.ttc"  # 0 Regular, 2 Bold
PAPER, CORAL, CRIMSON, GOLD, TEAL, NAVY, INK = (241, 233, 218), (230, 102, 122), (180, 42, 71), (220, 198, 124), (73, 179, 166), (42, 42, 78), (50, 45, 72)
X, Y = 72, 168          # 左上角，避开 2.39:1 黑边（138 px）
f = lambda path, size, i: ImageFont.truetype(path, size, index=i)

def _shadow(im, box, r=10, a=90):
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle(box, fill=(0, 0, 0, a))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(r)))

def _soft_text(im, xy, text, font, fill):
    """浅色字 + 柔和的墨色投影（代替粗描边）"""
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + 1, xy[1] + 2), text, font=font, fill=INK + (255,), stroke_width=3, stroke_fill=INK + (255,))
    sh = sh.filter(ImageFilter.GaussianBlur(5)); im.alpha_composite(sh); im.alpha_composite(sh)
    ImageDraw.Draw(im).text(xy, text, font=font, fill=fill)

def vlen(text, font, gap=4):
    """竖排的总高度：汉字一字一格，连续的拉丁字母 / 数字转 90° 排成一段"""
    h = 0
    for run, latin in _runs(text):
        h += font.getlength(run) + gap * 2 if latin else len(run) * (font.size + gap)
    return h

def _runs(text):
    out = []
    for ch in text.strip():
        if ch == " " and not (out and out[-1][1]): continue    # 汉字之间的空格不要；英文单词之间的保留
        latin = ch.isascii() and ch != "·"
        if out and out[-1][1] == latin: out[-1][0] += ch
        else: out.append([ch, latin])
    return out

def vertical(d, x, y, text, font, fill, gap=4, im=None):
    for run, latin in _runs(text):
        if latin:   # 拉丁字母：整段顺时针转 90°，像日文竖排里的英文
            run = run.strip(); w = int(font.getlength(run)) + 4; tmp = Image.new("RGBA", (w, font.size + 12), (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((2, 0), run, font=font, fill=fill)
            r = tmp.rotate(-90, expand=True); im.alpha_composite(r, (int(x - r.width / 2), int(y + gap)))
            y += w + gap * 2
        else:
            for ch in run:
                w = font.getlength(ch); d.text((x - w / 2, y), ch, font=font, fill=fill); y += font.size + gap
    return y

def style_A(t, s):   # 竖排字卡：和游戏里的房名卡一样，纸色竖条 + 双墨线，标题竖排宋体，小字竖排在左侧一列
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ft = f(SONGTI, 54, 1); fs = f(YUANTI, 28, 0)
    hmain = vlen(t, ft) + 64; hsub = (vlen(s, fs, 3) + 64) if s else 0
    h = max(hmain, hsub); w = 96 + (60 if s else 0)
    box = (X, Y, X + w, Y + h); _shadow(im, (X + 6, Y + 8, X + w + 6, Y + h + 8)); d = ImageDraw.Draw(im)
    d.rectangle(box, fill=PAPER + (245,), outline=INK, width=4); d.rectangle((X + 8, Y + 8, X + w - 8, Y + h - 8), outline=INK, width=2)
    vertical(d, X + w - 48, Y + 32, t, ft, INK, im=im)
    if s: d.line((X + 64, Y + 26, X + 64, Y + h - 26), fill=CORAL, width=2); vertical(d, X + 34, Y + 34, s, fs, CRIMSON, 3, im=im)
    return im

def style_B(t, s):   # 朱印：深红方块白字（像落款印章），小字在印旁边，白字墨描边，没有底
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ft = f(SONGTI, 50, 0); fs = f(YUANTI, 32, 2)
    tw = ft.getlength(t); w, h = int(tw + 52), 86
    d.rounded_rectangle((X, Y, X + w, Y + h), radius=6, fill=CRIMSON + (240,))
    d.rounded_rectangle((X + 6, Y + 6, X + w - 6, Y + h - 6), radius=4, outline=PAPER + (200,), width=2)
    d.text((X + 26, Y + 14), t, font=ft, fill=PAPER)
    if s: _soft_text(im, (X + w + 22, Y + 26), s, fs, PAPER)
    return im

def style_C(t, s):   # 墨条金字：墨色横条，左边一道金线，标题金色宋体，小字纸色
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ft = f(SONGTI, 48, 1); fs = f(YUANTI, 28, 0)
    w = int(max(ft.getlength(t), fs.getlength(s) if s else 0) + 70); h = 84 + (44 if s else 0)
    d.rectangle((X, Y, X + w, Y + h), fill=INK + (225,)); d.rectangle((X, Y, X + 8, Y + h), fill=GOLD)
    d.text((X + 36, Y + 16), t, font=ft, fill=GOLD)
    if s: d.text((X + 36, Y + 82), s, font=fs, fill=PAPER)
    return im

def style_D(t, s):   # 极简：不要底，纸色宋体 + 墨描边，前面一小段珊瑚色短线，小字在下
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ft = f(SONGTI, 58, 1); fs = f(YUANTI, 30, 2)
    d.rectangle((X, Y + 34, X + 34, Y + 40), fill=CORAL)
    _soft_text(im, (X + 50, Y), t, ft, PAPER)
    if s: _soft_text(im, (X + 52, Y + 78), s, fs, PAPER)
    return im

def style_E(t, s):   # 斜切色带：珊瑚色平行四边形 + 墨边，白字；小字在下面一条窄墨带里
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ft = f(SONGTI, 50, 0); fs = f(YUANTI, 28, 0)
    tw = ft.getlength(t); w = int(tw + 80); h = 80; k = 22
    d.polygon([(X + k, Y), (X + w + k, Y), (X + w - k, Y + h), (X - k + k, Y + h)], fill=CORAL, outline=INK, width=4)
    d.text((X + 40, Y + 12), t, font=ft, fill=PAPER)
    if s:
        sw = int(fs.getlength(s) + 50)
        d.polygon([(X + 12, Y + h + 8), (X + sw + 12, Y + h + 8), (X + sw, Y + h + 52), (X, Y + h + 52)], fill=INK + (235,))
        d.text((X + 26, Y + h + 14), s, font=fs, fill=PAPER)
    return im

def style_F(t, s):   # 纸卡 + 青海波边：纸色卡片，左边一条青海波（游戏里的纹样），墨细框；标题墨色宋体，小字深红
    im = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    ft = f(SONGTI, 46, 1); fs = f(YUANTI, 28, 0)
    w = int(max(ft.getlength(t), fs.getlength(s) if s else 0) + 112); h = 82 + (42 if s else 0)
    _shadow(im, (X + 6, Y + 8, X + w + 6, Y + h + 8)); d = ImageDraw.Draw(im)
    d.rectangle((X, Y, X + w, Y + h), fill=PAPER + (248,))
    from pathlib import Path
    pat = Image.open(Path(__file__).resolve().parents[2] / "web/public/textures/patterns/seigaiha.png").convert("L").resize((128, 64))
    band = Image.new("RGBA", (40, h), NAVY + (255,)); lines = Image.new("RGBA", (40, h), (79, 116, 191, 255))
    m = Image.new("L", (40, h)); 
    for yy in range(0, h, 64): m.paste(pat.crop((0, 0, 40, 64)), (0, yy))
    band.paste(lines, (0, 0), m); im.paste(band, (X, Y))
    d = ImageDraw.Draw(im); d.rectangle((X, Y, X + w, Y + h), outline=INK, width=3); d.line((X + 40, Y, X + 40, Y + h), fill=INK, width=3)
    d.text((X + 64, Y + 14), t, font=ft, fill=INK)
    if s: d.text((X + 66, Y + 78), s, font=fs, fill=CRIMSON)
    return im

STYLES = {"A": ("竖排字卡", style_A), "B": ("朱印", style_B), "C": ("墨条金字", style_C), "D": ("极简描边", style_D), "E": ("斜切色带", style_E), "F": ("纸卡青海波边", style_F)}

def label(style, title, sub=None):
    return STYLES[style][1](title, sub)
