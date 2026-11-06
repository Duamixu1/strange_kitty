"""
游览版视频：每个故事前面的转场图（地点字卡）。全部代码画，只用游戏色板、游戏里的四张纹样和和纸纹理，不花积分。

  uv run --with pillow --with numpy python promo/tools/title_cards.py
  → promo/raw/title_cards/A_<地点>.png、B_<地点>.png（1920×1080）和对比图 _对比.jpg

两套样式：
  A 字卡：和纸底，两侧整条纹样板（每个地点一种纹样一种底色），中间竖排大字地名（报隶，墨色，后面错开一层朱色，像套色木版没对准），
    左边竖排篇名，右边"其一/其二/其三"，右下朱印（形/真/理），金霞横穿两侧纹样板
  B 襖：整屏两扇拉门（焦茶门框、门心铺纹样、圆引手），中缝上挂一张竖条短册写地名；剪辑时两扇门可以往两边拉开，直接进画面
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import glob

ROOT = Path(__file__).resolve().parents[2]
TEX = ROOT / "web/public/textures"
OUT = ROOT / "promo/raw/title_cards"; OUT.mkdir(parents=True, exist_ok=True)
W, H = 1920, 1080
hx = lambda s: tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
C = {k: hx(v) for k, v in dict(paper="#F1E9DA", coral="#E6667A", crimson="#B42A47", ochre="#DCC67C", green="#59B86A", teal="#49B3A6",
                                  blue="#4F74BF", wisteria="#6A4C8C", navy="#2A2A4E", lavender="#D6D3EF", pink="#E7A3B5", ink="#322D48", kogecha="#573F33").items()}
BAOLI = sorted(glob.glob("/System/Library/AssetsV2/**/Baoli.ttc", recursive=True))[0]
SONGTI = "/System/Library/Fonts/Songti.ttc"

PLACES = [
    dict(id="sakai", title="坂井家", no="其一", sub="化猫篇", seal="形", pat="asanoha", scale=0.42, bg=C["crimson"], fg=C["pink"], accent=C["ochre"]),
    dict(id="wanya", title="万屋", no="其二", sub="座敷童子篇", seal="真", pat="seigaiha", scale=0.5, bg=C["navy"], fg=C["blue"], accent=C["coral"]),
    dict(id="ooku", title="大奥", no="其三", sub="唐伞篇", seal="理", pat="shippo", scale=0.36, bg=C["wisteria"], fg=C["lavender"], accent=C["ochre"]),
]

def paper_bg(color=C["paper"]):
    g = np.asarray(Image.open(TEX / "paper.png").convert("L").resize((1024, 1024)), np.float32) / 255 - 0.5
    g = np.tile(g, (2, 2))[:H, :W, None]
    a = np.empty((H, W, 3), np.float32); a[:] = color
    return Image.fromarray(np.clip(a * (1 + g * 0.35), 0, 255).astype(np.uint8))

def pattern(w, h, name, scale, bg, fg):
    m = Image.open(TEX / f"patterns/{name}.png").convert("L")
    m = m.resize((int(m.width * scale), int(m.height * scale)), Image.LANCZOS)
    a = np.asarray(m, np.float32)[..., None] / 255
    t = np.array(bg, np.float32) * (1 - a) + np.array(fg, np.float32) * a
    t = np.tile(t, (h // t.shape[0] + 2, w // t.shape[1] + 2, 1))[:h, :w]
    g = np.asarray(Image.open(TEX / "paper.png").convert("L").resize((w, h)), np.float32)[..., None] / 255 - 0.5
    return Image.fromarray(np.clip(t * (1 + g * 0.3), 0, 255).astype(np.uint8))

def kasumi(d, x, y, L, h=70):
    """金霞：圆角长条，墨边，里面一道细线"""
    d.rounded_rectangle((x, y, x + L, y + h), radius=h // 2, fill=C["ochre"], outline=C["ink"], width=6)
    d.rounded_rectangle((x + h * 0.6, y + h * 0.32, x + L * 0.62, y + h * 0.68), radius=10, outline=C["ink"] + (130,), width=3)

def vtext(d, txt, xc, y0, size, font=BAOLI, fill=C["ink"], step=1.04, index=0, stroke=0, stroke_fill=None):
    f = ImageFont.truetype(font, size, index=index)
    for i, ch in enumerate(txt):
        tw = d.textlength(ch, font=f)
        d.text((xc - tw / 2, y0 + i * size * step), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return y0 + len(txt) * size * step

def seal(img, ch, x, y, S=150):
    s = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(s)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=12, fill=C["crimson"] + (240,))
    d.rounded_rectangle((8, 8, S - 9, S - 9), radius=8, outline=C["paper"] + (255,), width=4)
    f = ImageFont.truetype(BAOLI, int(S * 0.72)); tw = d.textlength(ch, font=f)
    d.text(((S - tw) / 2, S * 0.08), ch, font=f, fill=C["paper"])
    # 印泥不匀：随机擦掉一点
    a = np.asarray(s).copy(); rng = np.random.default_rng(ord(ch))
    mask = rng.random(a.shape[:2]) < 0.06; a[mask, 3] = (a[mask, 3] * 0.35).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a).rotate(-4, resample=Image.BICUBIC, expand=True), (x, y))

def title_block(img, P, xc, yc, size):
    """竖排大字：先错开一层朱色，再压墨色（套色没对准的木版感）"""
    d = ImageDraw.Draw(img)
    h = len(P["title"]) * size * 1.04; y0 = yc - h / 2
    vtext(d, P["title"], xc + 9, y0 + 7, size, fill=C["coral"] + (255,))
    vtext(d, P["title"], xc, y0, size, fill=C["ink"] + (255,))
    return y0, y0 + h

def card_A(P):
    img = paper_bg().convert("RGBA"); d = ImageDraw.Draw(img)
    PW = 540
    for x0 in (0, W - PW):
        img.paste(pattern(PW, H, P["pat"], P["scale"], P["bg"], P["fg"]), (x0, 0))
        edge = PW if x0 == 0 else W - PW
        d.rectangle((edge - 9, 0, edge + 9, H), fill=C["ink"]); d.rectangle((edge - 3, 0, edge + 3, H), fill=C["accent"] if "accent" not in P else P["accent"])
    for (x, y, L) in ((-120, 150, 560), (60, 760, 420), (W - 470, 300, 520), (W - 330, 880, 400)):
        kasumi(d, x, y, L)
    # 中间：地名 + 篇名 + 其几 + 印
    size = 250 if len(P["title"]) == 2 else 215
    y0, y1 = title_block(img, P, W // 2, H // 2 - 20, size)
    vtext(d, P["no"], W // 2 + 220, y0 + 10, 64, fill=C["crimson"])
    vtext(d, P["sub"], W // 2 - 215, y1 - len(P["sub"]) * 50 * 1.1, 50, font=SONGTI, index=0, fill=C["ink"], step=1.1)
    seal(img, P["seal"], W // 2 + 150, int(y1) - 160)
    # 外框
    d.rectangle((22, 22, W - 23, H - 23), outline=C["ink"], width=10)
    return img.convert("RGB")

def card_B_layers(P):
    """襖拆成三层给剪辑做转场：左门、右门（各 960×1080，含金霞）、短册（整屏透明底，含挂绳和投影）"""
    doors = paper_bg().convert("RGBA"); d = ImageDraw.Draw(doors)
    for x0 in (0, W // 2):   # 两扇襖
        doors.paste(pattern(W // 2 - 70, H - 70, P["pat"], P["scale"], P["bg"], P["fg"]), (x0 + 35, 35))
        d.rectangle((x0, 0, x0 + W // 2 - 1, H - 1), outline=C["kogecha"], width=35)
        d.rectangle((x0 + 33, 33, x0 + W // 2 - 34, H - 34), outline=C["ink"], width=4)
        hxp = x0 + W // 2 - 120 if x0 == 0 else x0 + 120   # 引手：靠中缝
        d.ellipse((hxp - 40, H // 2 - 40, hxp + 40, H // 2 + 40), fill=C["ink"], outline=C["ochre"], width=8)
        d.ellipse((hxp - 20, H // 2 - 20, hxp + 20, H // 2 + 20), fill=C["kogecha"])
    for (x, y, L) in ((80, 170, 520), (W - 640, 230, 560), (160, 840, 460), (W - 520, 900, 420)):   # 都不跨中缝，跟着门走
        kasumi(d, x, y, L, h=64)
    # 短册：挂绳 + 投影 + 竖条纸
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    SW, y0, y1 = 330, 120, 960; x0 = W // 2 - SW // 2
    d.line((W // 2, 0, W // 2, y0), fill=C["crimson"], width=6)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((x0 + 14, y0 + 16, x0 + SW + 14, y1 + 16), fill=(0, 0, 0, 110))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    strip = paper_bg().crop((0, 0, SW, y1 - y0)); img.paste(strip, (x0, y0)); d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + SW, y0 + 70), fill=C["crimson"])
    fno = ImageFont.truetype(BAOLI, 46); d.text((W // 2 - d.textlength(P["no"], font=fno) / 2, y0 + 10), P["no"], font=fno, fill=C["paper"])   # 红头上横写
    d.rectangle((x0, y0, x0 + SW, y1), outline=C["ink"], width=8); d.rectangle((x0 + 16, y0 + 86, x0 + SW - 16, y1 - 16), outline=C["ink"], width=3)
    size = 200 if len(P["title"]) == 2 else 165
    title_block(img, P, W // 2 + 22, y0 + 86 + 40 + len(P["title"]) * size * 0.52, size)   # 靠上，下面留给篇名和印
    vtext(d, P["sub"], x0 + 52, y1 - 30 - len(P["sub"]) * 38 * 1.1, 38, font=SONGTI, fill=C["ink"], step=1.1)
    seal(img, P["seal"], x0 + SW - 140, y1 - 150, S=110)
    return dict(left=doors.crop((0, 0, W // 2, H)), right=doors.crop((W // 2, 0, W, H)), strip=img)

def card_B(P):
    L = card_B_layers(P); img = Image.new("RGBA", (W, H))
    img.paste(L["left"], (0, 0)); img.paste(L["right"], (W // 2, 0)); img.alpha_composite(L["strip"])
    return img.convert("RGB")

if __name__ == "__main__":
    ims = []
    for style, fn in (("A", card_A), ("B", card_B)):
        for P in PLACES:
            im = fn(P); im.save(OUT / f"{style}_{P['id']}.png"); ims.append(im)
    sheet = Image.new("RGB", (640 * 3 + 40, 360 * 2 + 30), C["paper"])
    for i, im in enumerate(ims): sheet.paste(im.resize((640, 360), Image.LANCZOS), (10 + (i % 3) * 650, 10 + (i // 3) * 370))
    sheet.save(OUT / "_对比.jpg", quality=90); print(OUT)
