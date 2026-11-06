"""
小红书封面（3:4，1080×1440），配《游览版_形真理》视频。全部代码画：游览版录屏帧 + 游戏色板、纹样、报隶字，不用原片素材。
  uv run --with pillow --with numpy python promo/tools/xhs_cover.py
  → promo/封面_小红书_游览版_{A,B,C}.jpg 和对比图 promo/raw/封面_小红书_对比.jpg
A 大奥长廊里正面站着的药郎（紫幔、蝴蝶）满版 + 横排大字"走进怪化猫"
B 三个地方竖着三条并排（坂井家红廊 / 万屋玻璃门 / 大奥长廊），每条挂短册
C 角色样片举剑那一帧，两扇襖（万屋青海波）往两边拉开大半，竖排"这把剑 他自己拔不出来"
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
sys.path.insert(0, str(Path(__file__).parent))
import title_cards as TC

P = Path(__file__).resolve().parents[1]
RAW = P / "raw/tour_v3"
W, H = 1080, 1440
C = TC.C; BAOLI = TC.BAOLI; SONGTI = TC.SONGTI

def frame(name, i, box=None, size=(W, H)):
    im = Image.open(RAW / name / f"f_{i:04d}.jpg").convert("RGB")
    if box: im = im.crop(box)
    return im.resize(size, Image.LANCZOS)

def paper(w, h, color=C["paper"]):
    g = np.asarray(Image.open(TC.TEX / "paper.png").convert("L").resize((1024, 1024)), np.float32) / 255 - 0.5
    g = np.tile(g, (h // 1024 + 1, w // 1024 + 1))[:h, :w, None]
    a = np.empty((h, w, 3), np.float32); a[:] = color
    return Image.fromarray(np.clip(a * (1 + g * 0.35), 0, 255).astype(np.uint8))

def htext(img, txt, xc, y, size, fill=C["paper"], offset=True, stroke=10):
    """横排大字：后面错开一层朱色（套色没对准），墨色粗描边"""
    d = ImageDraw.Draw(img); f = ImageFont.truetype(BAOLI, size)
    x = xc - d.textlength(txt, font=f) / 2
    if offset: d.text((x + size * 0.05, y + size * 0.05), txt, font=f, fill=C["crimson"], stroke_width=stroke, stroke_fill=C["crimson"])
    d.text((x, y), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=C["ink"])

def vtext(img, txt, xc, y0, size, fill=C["paper"], stroke=8, step=1.06, offset=True):
    d = ImageDraw.Draw(img); f = ImageFont.truetype(BAOLI, size)
    for i, ch in enumerate(txt):
        x = xc - d.textlength(ch, font=f) / 2; y = y0 + i * size * step
        if ch in "，。": x, y = xc + size * 0.1, y - size * 0.35
        if offset: d.text((x + size * 0.05, y + size * 0.05), ch, font=f, fill=C["crimson"], stroke_width=stroke, stroke_fill=C["crimson"])
        d.text((x, y), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=C["ink"])

def band(img, y0, y1, color, alpha=235):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle((0, y0, W, y1), fill=color + (alpha,))
    img.alpha_composite(lay)

def shade(img, y0, y1, top=True, strength=170):
    """上/下压一层暗渐变，让字压得住画面"""
    a = np.zeros((H, W), np.float32); n = y1 - y0
    ramp = np.linspace(1, 0, n) if top else np.linspace(0, 1, n)
    a[y0:y1] = ramp[:, None] * strength
    if top: a[:y0] = strength
    else: a[y1:] = strength
    lay = Image.new("RGBA", (W, H), C["navy"] + (0,)); lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.alpha_composite(lay)

def frame_border(img, color=C["ink"], w=14):
    ImageDraw.Draw(img).rectangle((0, 0, W - 1, H - 1), outline=color, width=w)

def tag_row(img, y, items, size=40):
    """底部一排小签：和纸底、墨边"""
    d = ImageDraw.Draw(img); f = ImageFont.truetype(BAOLI, size)
    ws = [d.textlength(t, font=f) + 56 for t in items]; gap = 22; x = (W - sum(ws) - gap * (len(items) - 1)) / 2
    for t, w in zip(items, ws):
        d.rounded_rectangle((x, y, x + w, y + size + 34), radius=12, fill=C["paper"], outline=C["ink"], width=5)
        d.text((x + 28, y + 14), t, font=f, fill=C["ink"]); x += w + gap

# ---------------------------------------------------------------- A
def cover_A():
    img = frame("s4a_corridor", 20, box=(375, 0, 1185, 1080)).convert("RGBA")
    shade(img, 120, 640, top=True, strength=200)
    shade(img, 1120, 1300, top=False, strength=150)
    htext(img, "走进怪化猫", W // 2, 110, 210)
    vline = ImageDraw.Draw(img); vline.rectangle((W // 2 - 300, 390, W // 2 + 300, 396), fill=C["ochre"])
    # 11-03 用户定：讲目标是第一季全部场景；报隶里的拉丁字母是斜的，"TV"两个字母换宋体粗
    runs = [("第一季 ", BAOLI, 0), ("TV", SONGTI, 1), (" 版的所有场景", BAOLI, 0)]; size = 70; d = ImageDraw.Draw(img)
    fonts = [ImageFont.truetype(f, size, index=i) for _, f, i in runs]; ws = [d.textlength(t, font=f) for (t, _, _), f in zip(runs, fonts)]
    x = (W - sum(ws)) / 2
    for (t, _, _), f, w in zip(runs, fonts, ws):
        d.text((x, 425 + (4 if f.path == SONGTI else 0)), t, font=f, fill=C["paper"], stroke_width=7, stroke_fill=C["ink"]); x += w
    htext(img, "目前开发了", W // 2, 1200, 50, offset=False, stroke=6)
    tag_row(img, 1290, ["坂井家", "万屋", "大奥"], 46)
    TC.seal(img, "形", W - 200, 1120, S=130)
    frame_border(img)
    return img.convert("RGB")

# ---------------------------------------------------------------- B
def strip_label(img, P_, xc, y0):
    """短册：红头写"其几"，下面竖排地名"""
    SW, SH = 150, 380; x0 = xc - SW // 2
    d = ImageDraw.Draw(img)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((x0 + 10, y0 + 12, x0 + SW + 10, y0 + SH + 12), fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    img.paste(paper(SW, SH), (x0, y0)); d = ImageDraw.Draw(img)
    d.rectangle((x0, y0, x0 + SW, y0 + 52), fill=C["crimson"])
    f = ImageFont.truetype(BAOLI, 36); d.text((xc - d.textlength(P_["no"], font=f) / 2, y0 + 6), P_["no"], font=f, fill=C["paper"])
    d.rectangle((x0, y0, x0 + SW, y0 + SH), outline=C["ink"], width=6)
    size = 100 if len(P_["title"]) == 2 else 88
    vtext(img, P_["title"], xc, y0 + 70 + (SH - 70 - len(P_["title"]) * size * 1.06) / 2, size, fill=C["ink"], stroke=0, offset=False)

def cover_B():
    img = paper(W, H).convert("RGBA")
    shots = [("s1a_rouka", 60, 660), ("s3b_glassdoor", 45, 1000), ("s4a_corridor", 170, 960)]   # 每条以 x 为中心裁
    PW, top, bot = 340, 400, 1300; gap = (W - 3 * PW) // 4
    for k, (n, i, cx) in enumerate(shots):
        h_src = 1080; w_src = int(h_src * PW / (bot - top))
        im = frame(n, i, box=(cx - w_src // 2, 0, cx + w_src // 2, h_src), size=(PW, bot - top))
        x = gap + k * (PW + gap)
        ImageDraw.Draw(img).rectangle((x - 9, top - 9, x + PW + 8, bot + 8), fill=C["ink"])
        img.paste(im, (x, top))
        strip_label(img, TC.PLACES[k], x + PW // 2, bot - 300)
    # 顶上：纹样横条 + 标题
    img.paste(TC.pattern(W, 60, "seigaiha", 0.5, C["navy"], C["blue"]), (0, 0))
    ImageDraw.Draw(img).rectangle((0, 60, W, 66), fill=C["ochre"])
    htext(img, "怪化猫的三个地方", W // 2, 105, 118, fill=C["paper"])
    htext(img, "我都做成了能走进去的游戏", W // 2, 262, 62, fill=C["ink"], offset=False, stroke=0)
    tag_row(img, 1338, ["电脑手机都能玩", "免费"], 40)
    frame_border(img)
    return img.convert("RGB")

# ---------------------------------------------------------------- C
def cover_C():
    # 游览版里的拔剑镜头剑身太长，3:4 里装不下人和剑；用角色样片（竖版 1206×1608，正好 3:4）举剑那一帧
    import imageio.v2 as iio
    base = Image.fromarray(iio.get_reader(str(P / "药郎角色样片_v2.mp4")).get_data(int(5.0 * 30))).resize((W, H), Image.LANCZOS).convert("RGBA")
    L = TC.card_B_layers(TC.PLACES[1])   # 万屋的襖（青海波）
    half = W // 2
    left = L["left"].resize((half, H)); right = L["right"].resize((half, H))
    off = 370   # 拉开大半
    base.alpha_composite(left, (-off, 0)); base.alpha_composite(right, (half + off, 0))
    # 中间画面压暗一点上沿，放竖排字
    vis = half - off   # 每扇门露出来的宽度，字写在门上
    vtext(base, "这把剑", vis // 2, 150, 120)
    vtext(base, "他自己拔不出来", W - vis // 2, 150, 100, step=1.04)
    band(base, 1250, 1440, C["ink"], 235)
    htext(base, "在我这儿，按 X 就行", W // 2, 1278, 70, offset=False, stroke=0)
    f = ImageFont.truetype(BAOLI, 36); d = ImageDraw.Draw(base); t = "怪化猫同人 · 坂井家 万屋 大奥 · 电脑手机都能玩"
    d.text((W / 2 - d.textlength(t, font=f) / 2, 1376), t, font=f, fill=C["ochre"])
    frame_border(base)
    return base.convert("RGB")

if __name__ == "__main__":
    ims = []
    for k, fn in (("A", cover_A), ("B", cover_B), ("C", cover_C)):
        im = fn(); im.save(P / f"封面_小红书_游览版_{k}.jpg", quality=93); ims.append(im)
    sheet = Image.new("RGB", (3 * 540 + 40, 720 + 20), C["paper"])
    for i, im in enumerate(ims): sheet.paste(im.resize((540, 720), Image.LANCZOS), (10 + i * 550, 10))
    sheet.save(P / "raw/封面_小红书_对比.jpg", quality=90); print("ok")
