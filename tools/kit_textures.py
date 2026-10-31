# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""游览版积木的贴图：一部分从已经出过的概念图里裁（不花积分），一部分程序画（只用色板 13 色，第 13 色焦茶 #573F33 只给木头用）。

  uv run tools/kit_textures.py
  → web/public/textures/kit/*.png（尺寸和对应的米数见 TILE，tools/kit_build.py 按同样的米数排 UV）

裁的：
  mural_L / mural_R   03_走廊_左墙、04_走廊_右墙 地面线以上的整幅墙画（地面线按绿色行自动找）
  end_far             02_走廊全景 尽头的红白扇门洞 + 上方挂饰画
  door_near           05_走廊_回头 近端的木门 + 门楣花鸟
画的（都能无缝平铺）：
  carpet   珊瑚底、樱花 + 山吹卷草，一格 1.2 米
  boards   青磁绿廊板，每 0.91 米一道墨线（横过走廊），一格 0.91 米
  drape    藤紫幔、纸白十二瓣菊，一格 0.36×0.72 米
  andon    行灯纸罩：青磁底、藍色菱格、中间红菱
  chochin  红提灯：深红底、粉色卷云
平面图积木用的（docs/16_积木平面图格式.md）。UV 约定：v 向上 = 图片向上（kit.js 里 flipY=false）：
  tatami   一张畳：u 顺长边，上下两条藍色畳缘
  fusuma   襖绘，横向连续，一幅 = 4 扇（4×0.91 米宽、1.76 米高），u 横向平铺
  shoji    一扇障子：山吹框、藍色细格、下面腰板
  udoor    楼梯口的襖：深红底、纸白霞、山吹框
  sao      竿缘天井，一格 0.91 米，两根山吹竿缘
  goten    格天井，一格 0.91 米：深红格、山吹格心、纸白菊
  engawa   廊板（木色），一格 0.91 米，板缝顺 u
  earth    土间，一格 0.91 米
  kakejiku 挂轴：藤紫裱边、纸白画心、墨圆相、朱印
万屋（座敷童子）用的，参考 assets/concept/ref/wanya/（只看不裁，图案自己画）：
  goten_teal 青磁格天井：墨框、青磁格心、山吹小花，一格 0.91 米
  glassdoor  彩色玻璃门（一扇）：焦茶木框和下半截木板、青磁玻璃、山吹铅条圆环
  fanlight   门楣半圆彩色玻璃：半圆贴底边，放射花瓣
  lattice    火灯窗里的斜格子：纸白底、青磁菱格、墨线
  byobu      金屏风：山吹底、纸白霞、藍色水、珊瑚花枝，横向一整幅
  koshiita   腰板：焦茶竖板条，一格 1 米（obox 的 UV 按米），墨色板缝
  deck       拱桥桥面：深红底、墨色横板缝，一格 0.91 米
  gravel     庭的白砂：纸白底、淡藤耙纹，一格 0.91 米
  katomado_shoji 大座敷左墙的火灯窗障子（一扇）：山吹底板、深红框、上半钟形障子窗（纸白 + 墨细格）、下半腰板
  fusuma_hana    大座敷右墙的花卉襖（4 扇一幅）：纸白底、青磁卷草、珊瑚和鴇色的花
  frieze_flower  长押以上的画带（1 米见方能平铺，obox 的 UV 按米）：淡纸色底、鴇色莲苞 + 萌葱叶
  fanlight_lotus / fanlight_star / fanlight_crest  八角厅的大拱形彩色玻璃（参考 11）：半圆贴底边，墨色铅条，三种花样（莲花、五芒星、家纹）
  ougi_wall  室内庭后墙的扇面画（参考 12）：纸白底上散着几把展开的扇子（山吹、萌葱、珊瑚）和朱点，横向一整幅
坂井家（怪～ayakashi～ 化猫，参考 assets/concept/ref/sakai/，只看不裁）：
  noren_kamon     门楼正中的红底白家纹大幕            fusuma_kamon  金地白家纹襖（4 扇一幅，参考 12）
  maku_sanshoku   萌葱 / 深红 / 墨 三色竖条幔，1 米一组  maku_green    门楼檐下一条萌葱幕带，白家纹隔一米一个
  chochin_kamon   纸白提灯身上一个家纹                  itado         深焦茶木板门（钉头、横档）
  fusuma_nami     靛蓝大浪涛襖（4 扇一幅，参考 07）       rug_tsuru     婚礼大座敷的蓝底白鹤大地毯（参考 07）
  zabuton_maru    红蓝同心圆的圆坐垫（参考 06）           floor_black   黑漆地板（客间），一格 0.91 米
  panels_color    红色廊下上方的彩色色块带（参考 10）     goten_blue    密室的藍色格天井（参考 11）
  wall_darkred    密室暗红正壁（暗纹）                  lattice_red   密室墙：青磁底、深红格子（参考 11）
  wall_gray       红色廊下的灰墙（色板没有灰：纸白 + 55% 细墨点）   earth_dark   厨房深灰土间（墨点更密）
  goten_black     红色廊下的黑格天花                                panels_ybg   廊下上方的黄蓝绿色块带（参考 10）
  shiromuku       藏在密室里的白无垢（纸白底、淡藤暗纹、深红里衬）
  dou_sign   万屋门头的"同"字圆牌：深红底、纸白圈、墨色"同"字（字体画，屏幕里的招牌，不是总地图）
  stone      门厅石地：色板没有灰，用纸白底 + 约 40% 的细墨点压成灰，墨色石缝，一格 0.91 米
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "assets/concept/scenes"
OUT = ROOT / "web/public/textures/kit"
OUT.mkdir(parents=True, exist_ok=True)
C = {"paper": "#F1E9DA", "coral": "#E6667A", "crimson": "#B42A47", "ochre": "#DCC67C", "green": "#59B86A", "teal": "#49B3A6",
     "blue": "#4F74BF", "wisteria": "#6A4C8C", "navy": "#2A2A4E", "lavender": "#D6D3EF", "pink": "#E7A3B5", "ink": "#322D48", "kogecha": "#573F33"}
SS = 2   # 先画 2 倍再缩，边缘抗锯齿


def floor_line(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    rows = ((g > r + 30) & (g > b - 10)).mean(1)
    return next(i for i in range(len(rows)) if rows[i] > 0.6)


def crops():
    for key, src in (("mural_L", "03_走廊_左墙.png"), ("mural_R", "04_走廊_右墙.png")):
        im = Image.open(SC / src).convert("RGB")
        y = floor_line(im) - 6
        im.crop((0, 0, im.width, y)).resize((2048, round(2048 * y / im.width)), Image.LANCZOS).save(OUT / f"{key}.jpg", quality=90)
        print(key, "地面线", y)
    Image.open(SC / "02_走廊全景.png").convert("RGB").crop((2170, 760, 2720, 1420)).resize((550 * 2, 660 * 2), Image.LANCZOS).save(OUT / "end_far.jpg", quality=90)
    Image.open(SC / "05_走廊_回头.png").convert("RGB").crop((1150, 760, 1810, 1420)).resize((660 * 2, 660 * 2), Image.LANCZOS).save(OUT / "door_near.jpg", quality=90)


def tiled(size, draw_fn):
    """在 3×3 拼块上画、取中间那块，跨边的图形自然无缝"""
    w, h = size[0] * SS, size[1] * SS
    big = Image.new("RGB", (w * 3, h * 3))
    d = ImageDraw.Draw(big)
    draw_fn(d, w, h, big)
    return big.crop((w, h, w * 2, h * 2)).resize(size, Image.LANCZOS)


def petal_flower(d, cx, cy, r, n, fill, inner=None, outline=None, ratio=0.42, notch=False):
    """n 瓣花：每瓣是一个绕中心旋转的椭圆近似多边形"""
    for k in range(n):
        a0 = 2 * math.pi * k / n
        pts = []
        for t in np.linspace(-1, 1, 24):
            # 花瓣轮廓：极坐标里的一片叶形，樱花瓣尖端带个缺口
            ang = a0 + t * math.pi / n * 0.95
            rr = r * (1 - 0.18 * (1 - abs(t)) ** 8 if notch else 1) * (math.cos(t * math.pi / 2) ** ratio)
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        pts.append((cx, cy))
        d.polygon(pts, fill=fill, outline=outline)
    if inner: d.ellipse((cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18), fill=inner)


def carpet():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["coral"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                # 山吹卷草：两道错开的 S 弧
                for (cx, cy, s) in ((0.0, 0.5, 1), (0.5, 0.0, -1), (1.0, 0.5, 1), (0.5, 1.0, -1)):
                    for k in range(2):
                        r = w * (0.17 + 0.05 * k)
                        bb = (X + cx * w - r, Y + cy * h - r, X + cx * w + r, Y + cy * h + r)
                        d.arc(bb, 200 if s > 0 else 20, 340 if s > 0 else 160, fill=C["ochre"], width=int(w * 0.012))
                petal_flower(d, X + 0.25 * w, Y + 0.25 * h, w * 0.21, 5, C["pink"], inner=C["ochre"], notch=True)
                petal_flower(d, X + 0.75 * w, Y + 0.75 * h, w * 0.21, 5, C["pink"], inner=C["ochre"], notch=True)
                petal_flower(d, X + 0.75 * w, Y + 0.25 * h, w * 0.1, 5, C["paper"], inner=C["coral"], notch=True)
                petal_flower(d, X + 0.25 * w, Y + 0.75 * h, w * 0.1, 5, C["paper"], inner=C["coral"], notch=True)
    tiled((1024, 1024), f).save(OUT / "carpet.png")


def boards():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["green"])
        rng = np.random.default_rng(3)
        for oy in range(3):
            for ox in range(3):
                X, Y = ox * w, oy * h
                # 木纹：几道很淡的青磁细线
                for _ in range(10):
                    y = Y + rng.uniform(0.08, 0.92) * h
                    d.line((X, y, X + w, y + rng.uniform(-4, 4)), fill=C["teal"], width=SS)
                d.line((X, Y, X + w, Y), fill=C["ink"], width=int(w * 0.008))   # 板缝（v=0 那条边）
    tiled((512, 512), f).save(OUT / "boards.png")


def drape():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["wisteria"])
        rng = np.random.default_rng(5)
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for _ in range(6):   # 布纹的深色擦痕
                    x = X + rng.uniform(0, w); d.line((x, Y, x + rng.uniform(-20, 20), Y + h), fill=C["navy"], width=SS * 2)
                petal_flower(d, X + w * 0.5, Y + h * 0.25, w * 0.34, 12, C["paper"], inner=C["ochre"], ratio=0.6)
                petal_flower(d, X + w * 0.5, Y + h * 0.75, w * 0.18, 12, C["lavender"], ratio=0.6)
    tiled((256, 512), f).save(OUT / "drape.png")


def andon():
    w, h = 256 * SS, 384 * SS
    im = Image.new("RGB", (w, h), C["teal"]); d = ImageDraw.Draw(im)
    step = w / 6
    for k in range(-12, 13):   # 斜菱格
        d.line((k * step, 0, k * step + h, h), fill=C["navy"], width=SS * 2)
        d.line((k * step + h, 0, k * step, h), fill=C["navy"], width=SS * 2)
    cx, cy, r = w / 2, h / 2, w * 0.2
    d.polygon([(cx, cy - r * 1.3), (cx + r, cy), (cx, cy + r * 1.3), (cx - r, cy)], fill=C["paper"])
    r *= 0.72
    d.polygon([(cx, cy - r * 1.3), (cx + r, cy), (cx, cy + r * 1.3), (cx - r, cy)], fill=C["crimson"])
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ochre"], width=SS * 8)
    im.resize((256, 384), Image.LANCZOS).save(OUT / "andon.png")


def chochin():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["crimson"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for (cx, cy) in ((0.3, 0.3), (0.75, 0.7)):   # 卷云：三圈同心弧
                    for k in range(3):
                        r = w * (0.06 + 0.04 * k)
                        d.arc((X + cx * w - r, Y + cy * h - r, X + cx * w + r, Y + cy * h + r), 160, 420, fill=C["pink"], width=SS * 2)
                for k in range(8):   # 竹骨横线
                    y = Y + h * k / 8; d.line((X, y, X + w, y), fill=C["coral"], width=SS)
    tiled((512, 512), f).save(OUT / "chochin.png")


def tatami():
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["green"]); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7)
    for k in range(70):   # 蔺草纹：顺长边的细线
        y = h * (0.08 + 0.84 * k / 70); d.line((0, y, w, y), fill=C["teal"] if k % 2 else "#63BE72", width=SS)
    for y0 in (0, h - h * 0.075):   # 畳缘
        d.rectangle((0, y0, w, y0 + h * 0.075), fill=C["navy"])
        for x in range(0, w, int(w / 16)): d.ellipse((x + 6, y0 + h * 0.025, x + 6 + h * 0.025, y0 + h * 0.05), fill=C["lavender"])
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    im.resize((512, 256), Image.LANCZOS).save(OUT / "tatami.png")


def kumo(d, cx, cy, ww, hh, fill, edge):
    """霞（すやり霞）：几段圆头长条叠在一起"""
    for k, (dx, dy, f) in enumerate(((0, 0, 1.0), (ww * 0.18, -hh * 0.55, 0.7), (-ww * 0.12, hh * 0.55, 0.6))):
        l, r = cx + dx - ww * f / 2, cx + dx + ww * f / 2
        d.rounded_rectangle((l, cy + dy - hh / 2, r, cy + dy + hh / 2), radius=hh / 2, fill=fill, outline=edge, width=SS * 3)


def fusuma():
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["ochre"])
        for ox in range(3):
            X, Y = ox * w, h
            step = h / 9   # 金箔方格
            for k in range(int(w / step) + 1): d.line((X + k * step, Y, X + k * step, Y + h), fill="#E6D493", width=SS)
            for k in range(10): d.line((X, Y + k * step, X + w, Y + k * step), fill="#E6D493", width=SS)
            # 下面一道青海波水
            for row in range(3):
                for k in range(-1, 26):
                    cx = X + k * w / 24 + (w / 48 if row % 2 else 0); cy = Y + h * (0.86 + row * 0.05)
                    for rr in (0.045, 0.032, 0.019):
                        d.pieslice((cx - h * rr, cy - h * rr, cx + h * rr, cy + h * rr), 180, 360, fill=C["blue"] if rr != 0.032 else C["lavender"])
            d.rectangle((X, Y + h * 0.93, X + w, Y + h), fill=C["blue"])
            # 霞
            for (fx, fy, fw) in ((0.18, 0.2, 0.34), (0.62, 0.35, 0.42), (0.35, 0.62, 0.3), (0.85, 0.7, 0.26)):
                kumo(d, X + fx * w, Y + fy * h, fw * w, h * 0.07, C["paper"], C["ochre"])
            # 一枝山茶：藍枝 + 珊瑚花
            br = [(0.02, 0.55), (0.12, 0.42), (0.22, 0.38), (0.3, 0.27)]
            d.line([(X + a * w, Y + b * h) for a, b in br], fill=C["navy"], width=SS * 10, joint="curve")
            for (a, b, r) in ((0.12, 0.42, 0.05), (0.22, 0.36, 0.06), (0.3, 0.27, 0.045), (0.07, 0.5, 0.04)):
                petal_flower(d, X + a * w, Y + b * h, h * r, 5, C["coral"], inner=C["ochre"], ratio=0.3)
            for (a, b) in ((0.55, 0.52), (0.7, 0.18), (0.92, 0.45)):
                petal_flower(d, X + a * w, Y + b * h, h * 0.035, 5, C["pink"], inner=C["crimson"], notch=True)
    tiled((W, H), f).save(OUT / "fusuma.png")


def shoji():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    fr = w * 0.07; koshi = h * 0.17
    for k in range(1, 4): d.line((fr + (w - 2 * fr) * k / 4, 0, fr + (w - 2 * fr) * k / 4, h - koshi), fill=C["navy"], width=SS * 3)
    for k in range(1, 8): y = (h - koshi) * k / 8; d.line((0, y, w, y), fill=C["navy"], width=SS * 3)
    d.rectangle((0, h - koshi, w, h), fill=C["ochre"]); d.line((0, h - koshi, w, h - koshi), fill=C["ink"], width=SS * 3)
    for k in range(1, 4): d.line((w * k / 4, h - koshi, w * k / 4, h), fill="#C9B26A", width=SS * 2)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ochre"], width=int(fr))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    im.resize((256, 496), Image.LANCZOS).save(OUT / "shoji.png")


def udoor():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["crimson"]); d = ImageDraw.Draw(im)
    for (fy, fw) in ((0.22, 0.9), (0.5, 0.7), (0.74, 0.85)): kumo(d, w * 0.5, h * fy, w * fw, h * 0.05, C["paper"], C["ochre"])
    d.ellipse((w * 0.78, h * 0.46, w * 0.9, h * 0.52), fill=C["ochre"], outline=C["ink"], width=SS * 2)   # 引手
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ochre"], width=int(w * 0.06))
    im.resize((256, 496), Image.LANCZOS).save(OUT / "udoor.png")


def sao():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(5): d.line((X + w * (0.1 + 0.2 * k), Y, X + w * (0.12 + 0.2 * k), Y + h), fill=C["lavender"], width=SS * 2)   # 板纹
                for k in range(2):
                    x = X + w * (0.25 + 0.5 * k)
                    d.rectangle((x - w * 0.03, Y, x + w * 0.03, Y + h), fill=C["ochre"], outline=C["ink"], width=SS * 2)
    tiled((512, 512), f).save(OUT / "sao.png")


def goten():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    m = w * 0.09
    d.rectangle((m, m, w - m, w - m), fill=C["ochre"], outline=C["ink"], width=SS * 3)
    d.rectangle((m * 1.8, m * 1.8, w - m * 1.8, w - m * 1.8), outline=C["crimson"], width=SS * 3)
    petal_flower(d, w / 2, w / 2, w * 0.24, 16, C["paper"], inner=C["coral"], ratio=0.5)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "goten.png")


def engawa():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["ochre"])
        rng = np.random.default_rng(11)
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(6):
                    y = Y + h * k / 6
                    for _ in range(3):   # 木纹
                        yy = y + rng.uniform(0.15, 0.85) * h / 6; d.line((X, yy, X + w, yy + rng.uniform(-3, 3)), fill="#CDB565", width=SS)
                    d.line((X, y, X + w, y), fill=C["ink"], width=SS * 2)
    tiled((512, 512), f).save(OUT / "engawa.png")


def earth():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill="#C9B26A")
        rng = np.random.default_rng(13)
        for _ in range(900):
            x, y, r = rng.uniform(0, w * 3), rng.uniform(0, h * 3), rng.uniform(1, 4) * SS
            d.ellipse((x - r, y - r, x + r, y + r), fill=[C["wisteria"], C["ochre"], C["paper"]][rng.integers(3)])
    tiled((512, 512), f).save(OUT / "earth.png")


def kakejiku():
    w, h = 256 * SS, 640 * SS
    im = Image.new("RGB", (w, h), C["wisteria"]); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.04, w, h * 0.1), fill=C["navy"]); d.rectangle((0, h * 0.86, w, h * 0.92), fill=C["navy"])   # 一文字
    d.rectangle((w * 0.12, h * 0.12, w * 0.88, h * 0.84), fill=C["paper"], outline=C["ochre"], width=SS * 4)
    cx, cy, r = w * 0.5, h * 0.4, w * 0.27   # 圆相
    d.arc((cx - r, cy - r, cx + r, cy + r), 120, 430, fill=C["ink"], width=int(w * 0.05))
    d.rectangle((w * 0.6, h * 0.7, w * 0.7, h * 0.74), fill=C["crimson"])   # 朱印
    for k in range(4): d.line((w * 0.32, h * (0.62 + 0.035 * k), w * 0.32, h * (0.64 + 0.035 * k)), fill=C["ink"], width=SS * 4)
    d.rectangle((0, 0, w, h * 0.025), fill=C["ochre"]); d.rectangle((0, h * 0.975, w, h), fill=C["ochre"])   # 轴
    im.resize((256, 640), Image.LANCZOS).save(OUT / "kakejiku.png")


def goten_teal():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["ink"]); d = ImageDraw.Draw(im)
    m = w * 0.07
    d.rectangle((m, m, w - m, w - m), fill=C["teal"])
    d.rectangle((m * 2, m * 2, w - m * 2, w - m * 2), outline=C["paper"], width=SS * 3)
    petal_flower(d, w / 2, w / 2, w * 0.13, 8, C["ochre"], inner=C["crimson"], ratio=0.5)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "goten_teal.png")


def glassdoor():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["kogecha"]); d = ImageDraw.Draw(im)   # 门框是焦茶木
    m = w * 0.1
    d.rectangle((m, m, w - m, h * 0.62), fill=C["teal"])
    d.rectangle((m, h * 0.66, w - m, h - m), fill=C["kogecha"])   # 下面是木板
    d.rectangle((m * 1.6, h * 0.7, w - m * 1.6, h - m * 1.6), outline=C["ink"], width=SS * 3)
    cx, cy = w / 2, h * 0.34
    for r, col in ((w * 0.3, C["ochre"]), (w * 0.22, C["blue"]), (w * 0.12, C["coral"])):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col, outline=C["ochre"], width=SS * 4)
    for k in range(1, 4): d.line((m, h * 0.62 * k / 4, w - m, h * 0.62 * k / 4), fill=C["ochre"], width=SS * 2)
    d.line((w / 2, m, w / 2, h * 0.62), fill=C["ochre"], width=SS * 2)
    d.ellipse((w * 0.78, h * 0.6, w * 0.86, h * 0.64), fill=C["ochre"])   # 把手
    im.resize((256, 496), Image.LANCZOS).save(OUT / "glassdoor.png")


def fanlight():
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["ink"]); d = ImageDraw.Draw(im)
    cx, cy, R = w / 2, h, h * 0.98
    cols = [C["blue"], C["teal"], C["lavender"], C["pink"], C["blue"], C["teal"], C["lavender"], C["pink"], C["blue"]]
    n = len(cols)
    for k in range(n):   # 放射的花瓣玻璃
        a0, a1 = 180 + 180 * k / n, 180 + 180 * (k + 1) / n
        d.pieslice((cx - R, cy - R, cx + R, cy + R), a0, a1, fill=cols[k], outline=C["ochre"], width=SS * 3)
    r2 = R * 0.38
    d.pieslice((cx - r2, cy - r2, cx + r2, cy + r2), 180, 360, fill=C["ochre"], outline=C["ink"], width=SS * 3)
    for k in range(n):   # 花瓣尖
        a = math.pi + math.pi * (k + 0.5) / n; r = R * 0.72
        petal_flower(d, cx + math.cos(a) * r, cy + math.sin(a) * r, R * 0.1, 5, C["paper"], inner=C["coral"], ratio=0.4)
    d.arc((cx - R, cy - R, cx + R, cy + R), 180, 360, fill=C["ochre"], width=SS * 8)
    im.resize((512, 256), Image.LANCZOS).save(OUT / "fanlight.png")


def lattice():
    w = 256 * SS
    im = Image.new("RGB", (w, w), C["paper"]); d = ImageDraw.Draw(im)
    step = w / 7
    for k in range(-8, 9):
        d.line((k * step, 0, k * step + w, w), fill=C["teal"], width=SS * 5)
        d.line((k * step + w, 0, k * step, w), fill=C["teal"], width=SS * 5)
    for k in range(-8, 9):
        d.line((k * step, 0, k * step + w, w), fill=C["ink"], width=SS)
        d.line((k * step + w, 0, k * step, w), fill=C["ink"], width=SS)
    im.resize((256, 256), Image.LANCZOS).save(OUT / "lattice.png")


def byobu():
    w, h = 2048 * SS // 2, 640 * SS // 2
    im = Image.new("RGB", (w, h), C["ochre"]); d = ImageDraw.Draw(im)
    step = h / 8
    for k in range(int(w / step) + 1): d.line((k * step, 0, k * step, h), fill="#E6D493", width=SS)
    for k in range(9): d.line((0, k * step, w, k * step), fill="#E6D493", width=SS)
    d.polygon([(0, h * 0.78), (w * 0.3, h * 0.7), (w * 0.6, h * 0.82), (w, h * 0.72), (w, h), (0, h)], fill=C["blue"])
    for (fx, fy, fw) in ((0.15, 0.18, 0.28), (0.55, 0.12, 0.35), (0.82, 0.4, 0.3), (0.35, 0.5, 0.25)):
        kumo(d, fx * w, fy * h, fw * w, h * 0.08, C["paper"], C["ochre"])
    d.line([(w * 0.62, h * 0.95), (w * 0.66, h * 0.6), (w * 0.74, h * 0.42), (w * 0.86, h * 0.33)], fill=C["navy"], width=SS * 8, joint="curve")
    for (a, b, r) in ((0.66, 0.6, 0.05), (0.74, 0.42, 0.06), (0.86, 0.33, 0.05), (0.7, 0.5, 0.035)):
        petal_flower(d, w * a, h * b, h * r * 1.4, 5, C["coral"], inner=C["paper"], ratio=0.3)
    im.resize((1024, 320), Image.LANCZOS).save(OUT / "byobu.png")


def koshiita():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["kogecha"]); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(17)
    for k in range(10):
        x = w * k / 10
        for _ in range(4):   # 木纹：浅一点的焦茶细线（和墨色硬边过渡，不做渐变）
            xx = x + rng.uniform(0.15, 0.85) * w / 10; d.line((xx, 0, xx + rng.uniform(-4, 4), w), fill="#64493B", width=SS)
        d.line((x, 0, x, w), fill=C["ink"], width=SS * 3)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "koshiita.png")


def stone():
    w = 512
    rng = np.random.default_rng(19)
    paper = np.array([int(C["paper"][i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
    ink = np.array([int(C["ink"][i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
    dots = rng.random((w, w)) < 0.4          # 像素级墨点，远看平均成灰（参考帧 09 的门厅地面偏深）
    a = np.where(dots[..., None], ink, paper).astype(np.uint8)
    im = Image.fromarray(a); d = ImageDraw.Draw(im)
    d.line((0, 0, w, 0), fill=C["ink"], width=4); d.line((0, 0, 0, w), fill=C["ink"], width=4)
    d.line((w // 2, w // 2, w, w // 2), fill=C["ink"], width=3)   # 半块错缝
    im.save(OUT / "stone.png")


def deck():
    w = 256 * SS
    im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    for k in range(6): y = w * k / 6; d.line((0, y, w, y), fill=C["ink"], width=SS * 2)
    d.line((0, 0, 0, w), fill=C["ink"], width=SS * 3); d.line((w - 1, 0, w - 1, w), fill=C["ink"], width=SS * 3)
    im.resize((256, 256), Image.LANCZOS).save(OUT / "deck.png")


def gravel():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        for oy in range(3):
            for ox in range(3):
                X, Y = ox * w, oy * h
                for k in range(8):   # 耙纹：平行的浅波浪线
                    y = Y + h * (k + 0.5) / 8
                    pts = [(X + w * t / 32, y + math.sin(t / 32 * 2 * math.pi) * h * 0.02) for t in range(33)]
                    d.line(pts, fill=C["lavender"], width=SS * 3)
    tiled((512, 512), f).save(OUT / "gravel.png")


def katomado_shoji():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["ochre"]); d = ImageDraw.Draw(im)
    for k in range(0, h, SS * 18): d.line((0, k, w, k), fill="#E6D493", width=SS)   # 金箔细纹
    cx, top, bot, hw = w / 2, h * 0.1, h * 0.62, w * 0.34
    def bell(s):
        pts = []
        for k in range(21):   # 尖拱 + 两肩外撇 + 下摆
            t = k / 20; y = top + (bot - top) * t
            if t < 0.45: x = hw * s * max(0.0, math.sin(t / 0.45 * math.pi / 2)) ** 0.7
            elif t < 0.6: x = hw * s * (1 + 0.08 * math.sin((t - 0.45) / 0.15 * math.pi))
            else: x = hw * s * (1 + 0.15 * ((t - 0.6) / 0.4) ** 2)
            pts.append((cx + x, y))
        return pts + [(2 * cx - x, y) for x, y in reversed(pts)]
    d.polygon(bell(1.18), fill=C["crimson"], outline=C["ink"])
    d.polygon(bell(1.0), fill=C["paper"], outline=C["ink"])
    for k in range(1, 5): x = cx - hw + 2 * hw * k / 5; d.line((x, top + 30, x, bot), fill=C["ink"], width=SS * 2)
    for k in range(1, 7): y = top + (bot - top) * k / 7; d.line((cx - hw * 1.1, y, cx + hw * 1.1, y), fill=C["ink"], width=SS * 2)
    d.polygon(bell(1.0), outline=C["ink"])
    d.rectangle((w * 0.08, h * 0.7, w * 0.92, h * 0.94), fill=C["teal"], outline=C["ink"], width=SS * 3)   # 腰板（青磁，07 里障子下面那条）
    for k in range(3): petal_flower(d, w * (0.25 + 0.25 * k), h * 0.82, w * 0.07, 5, C["ochre"], inner=C["crimson"], ratio=0.4)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["crimson"], width=int(w * 0.06))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 3)
    im.resize((256, 496), Image.LANCZOS).save(OUT / "katomado_shoji.png")


def fusuma_hana():
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        rng = np.random.default_rng(23)
        for ox in range(3):
            X, Y = ox * w, h
            for k in range(7):   # 卷草：几条带卷头的青磁曲线
                x0, y0 = X + w * (k + 0.3) / 7, Y + h * rng.uniform(0.25, 0.8)
                pts = [(x0 + math.cos(t) * w * 0.035 * (1 + t / 4), y0 + math.sin(t) * h * 0.07 * (1 + t / 4)) for t in np.linspace(0, 4 * math.pi, 40)]
                d.line(pts, fill=C["teal"], width=SS * 5, joint="curve")
                petal_flower(d, x0 + w * 0.04, y0 - h * 0.12, h * 0.05, 5, C["coral"], inner=C["ochre"], ratio=0.35)
                petal_flower(d, x0 - w * 0.03, y0 + h * 0.14, h * 0.035, 5, C["pink"], inner=C["crimson"], notch=True)
            d.rectangle((X, Y + h * 0.9, X + w, Y + h), fill=C["lavender"])
    tiled((W, H), f).save(OUT / "fusuma_hana.png")


def frieze_flower():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill="#EEF0E3" if False else C["paper"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for (cx, cy) in ((0.25, 0.3), (0.75, 0.75)):
                    x, y = X + cx * w, Y + cy * h
                    d.ellipse((x - w * 0.11, y + h * 0.02, x + w * 0.11, y + h * 0.12), fill=C["green"], outline=C["ink"], width=SS * 2)   # 叶
                    d.polygon([(x, y - h * 0.16), (x + w * 0.08, y - h * 0.02), (x, y + h * 0.04), (x - w * 0.08, y - h * 0.02)], fill=C["pink"], outline=C["ink"])   # 莲苞
                    d.line((x, y - h * 0.12, x, y + h * 0.02), fill=C["coral"], width=SS * 2)
    tiled((512, 512), f).save(OUT / "frieze_flower.png")


def dais():
    """大座敷高台地毯（第二版，参考 06、07 的华丽地毯）：藍底、青磁边带 + 山吹卷草、中间大珊瑚牡丹、四角小花"""
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["teal"]); d = ImageDraw.Draw(im)
    for k in range(0, w, int(w / 16)):   # 边带卷草
        for (x, y) in ((k, w * 0.03), (k, w * 0.97), (w * 0.03, k), (w * 0.97, k)):
            d.arc((x - w * 0.025, y - w * 0.025, x + w * 0.025, y + w * 0.025), 0, 270, fill=C["ochre"], width=SS * 3)
    d.rectangle((w * 0.07, w * 0.07, w * 0.93, w * 0.93), fill=C["navy"], outline=C["ochre"], width=SS * 6)
    d.rectangle((w * 0.11, w * 0.11, w * 0.89, w * 0.89), outline=C["crimson"], width=SS * 3)
    petal_flower(d, w / 2, w / 2, w * 0.27, 10, C["coral"], ratio=0.3)
    petal_flower(d, w / 2, w / 2, w * 0.19, 10, C["pink"], ratio=0.3)
    petal_flower(d, w / 2, w / 2, w * 0.1, 8, C["crimson"], inner=C["ochre"], ratio=0.35)
    for a in range(8):   # 牡丹外一圈叶
        t = 2 * math.pi * a / 8 + 0.2; x, y = w / 2 + math.cos(t) * w * 0.32, w / 2 + math.sin(t) * w * 0.32
        d.ellipse((x - w * 0.05, y - w * 0.025, x + w * 0.05, y + w * 0.025), fill=C["green"], outline=C["ink"], width=SS * 2)
    for (cx, cy) in ((0.2, 0.2), (0.8, 0.2), (0.2, 0.8), (0.8, 0.8)):
        petal_flower(d, w * cx, w * cy, w * 0.06, 6, C["lavender"], inner=C["ochre"], ratio=0.4)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "dais.png")


def dou_sign():
    from PIL import ImageFont
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    d.ellipse((w * 0.08, w * 0.08, w * 0.92, w * 0.92), fill=C["paper"], outline=C["ink"], width=SS * 8)
    d.ellipse((w * 0.16, w * 0.16, w * 0.84, w * 0.84), outline=C["crimson"], width=SS * 10)
    font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", int(w * 0.48))
    bb = d.textbbox((0, 0), "同", font=font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (w - (bb[3] - bb[1])) / 2 - bb[1]), "同", fill=C["ink"], font=font)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "dou_sign.png")


def fanlight_big(kind):
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["ink"]); d = ImageDraw.Draw(im)
    cx, cy, R = w / 2, h, h * 0.98
    cols = [C["teal"], C["blue"], C["lavender"], C["green"], C["pink"]]
    for k in range(10):   # 外圈放射的玻璃格
        a0, a1 = 180 + 18 * k, 180 + 18 * (k + 1)
        d.pieslice((cx - R, cy - R, cx + R, cy + R), a0, a1, fill=cols[k % len(cols)], outline=C["ink"], width=SS * 4)
    r2 = R * 0.62
    d.pieslice((cx - r2, cy - r2, cx + r2, cy + r2), 180, 360, fill=C["paper"], outline=C["ink"], width=SS * 4)
    if kind == "lotus":   # 莲花：一圈鴇色花瓣 + 山吹花心
        for k in range(7):
            a = math.pi + math.pi * (k + 0.5) / 7; x, y = cx + math.cos(a) * r2 * 0.55, cy + math.sin(a) * r2 * 0.55
            d.ellipse((x - r2 * 0.18, y - r2 * 0.28, x + r2 * 0.18, y + r2 * 0.28), fill=C["pink"], outline=C["ink"], width=SS * 3)
        d.pieslice((cx - r2 * 0.3, cy - r2 * 0.3, cx + r2 * 0.3, cy + r2 * 0.3), 180, 360, fill=C["ochre"], outline=C["ink"], width=SS * 3)
    elif kind == "star":  # 五芒星：深红星 + 青磁圆
        rr = r2 * 0.75; ccy = cy - rr * 0.55
        d.ellipse((cx - rr, ccy - rr, cx + rr, ccy + rr), fill=C["teal"], outline=C["ink"], width=SS * 3)
        pts = [(cx + math.cos(-math.pi / 2 + k * 4 * math.pi / 5) * rr * 0.9, ccy + math.sin(-math.pi / 2 + k * 4 * math.pi / 5) * rr * 0.9) for k in range(5)]
        d.polygon(pts, fill=C["crimson"], outline=C["ink"])
    else:                 # 家纹：藍圆里一朵山吹十六瓣菊
        rr = r2 * 0.7; ccy = cy - rr * 0.6
        d.ellipse((cx - rr, ccy - rr, cx + rr, ccy + rr), fill=C["blue"], outline=C["ink"], width=SS * 3)
        petal_flower(d, cx, ccy, rr * 0.85, 16, C["ochre"], inner=C["crimson"], ratio=0.5)
    d.arc((cx - R, cy - R, cx + R, cy + R), 180, 360, fill=C["ochre"], width=SS * 8)
    im.resize((512, 256), Image.LANCZOS).save(OUT / f"fanlight_{kind}.png")


def ougi_wall():
    w, h = 2048, 640
    im = Image.new("RGB", (w * SS, h * SS), C["paper"]); d = ImageDraw.Draw(im)
    W, H = w * SS, h * SS
    rng = np.random.default_rng(29)
    for k in range(9):   # 扇子：一段扇形，里面几道扇骨，扇面上一两个圆点
        cx, cy, R = W * (0.06 + 0.11 * k) + rng.uniform(-40, 40), H * rng.uniform(0.45, 0.85), H * rng.uniform(0.32, 0.45)
        a0 = rng.uniform(190, 230); a1 = a0 + rng.uniform(95, 125); col = [C["ochre"], C["green"], C["coral"], C["teal"]][k % 4]
        d.pieslice((cx - R, cy - R, cx + R, cy + R), a0, a1, fill=col, outline=C["ink"], width=SS * 3)
        d.pieslice((cx - R * 0.35, cy - R * 0.35, cx + R * 0.35, cy + R * 0.35), a0, a1, fill=C["paper"], outline=C["ink"], width=SS * 2)
        for t in np.linspace(a0, a1, 7)[1:-1]:
            a = math.radians(t); d.line((cx + math.cos(a) * R * 0.35, cy + math.sin(a) * R * 0.35, cx + math.cos(a) * R, cy + math.sin(a) * R), fill=C["ink"], width=SS)
        for _ in range(2):
            a = math.radians(rng.uniform(a0 + 15, a1 - 15)); rr = R * rng.uniform(0.55, 0.85); rd = R * 0.08
            d.ellipse((cx + math.cos(a) * rr - rd, cy + math.sin(a) * rr - rd, cx + math.cos(a) * rr + rd, cy + math.sin(a) * rr + rd), fill=C["crimson"])
    im.resize((w, h), Image.LANCZOS).save(OUT / "ougi_wall.png")


def kamon(d, cx, cy, r, col, width=None):
    """坂井家家纹（参考 12）：一个粗白圈，里面一个转 45° 的井桁"""
    w = width or r * 0.2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=int(w))
    L = r * 0.78; o = r * 0.24
    for sg in (-1, 1):
        for (ax, ay) in ((1, 1), (1, -1)):   # 两组平行斜杠，组成转了 45° 的"井"
            px, py = -ay * o * sg, ax * o * sg
            d.line((cx + px - ax * L * 0.7071, cy + py - ay * L * 0.7071, cx + px + ax * L * 0.7071, cy + py + ay * L * 0.7071), fill=col, width=int(w * 0.85))


def noren_kamon():
    w, h = 512 * SS, 320 * SS
    im = Image.new("RGB", (w, h), C["crimson"]); d = ImageDraw.Draw(im)
    for k in range(1, 4): d.line((w * k / 4, h * 0.08, w * k / 4, h), fill="#9E2440", width=SS * 3)   # 幕的接缝
    kamon(d, w / 2, h * 0.55, h * 0.36, C["paper"])
    d.rectangle((0, 0, w, h * 0.08), fill=C["ink"])
    im.resize((512, 320), Image.LANCZOS).save(OUT / "noren_kamon.png")


def fusuma_kamon():
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["ochre"])
        for ox in range(3):
            X, Y = ox * w, h
            for k in range(0, int(h), SS * 22): d.line((X, Y + k, X + w, Y + k), fill="#E6D493", width=SS)
            for (fx, fy, fr) in ((0.12, 0.22, 0.2), (0.38, 0.62, 0.24), (0.62, 0.2, 0.18), (0.86, 0.66, 0.23)):
                kamon(d, X + fx * w, Y + fy * h, h * fr, C["paper"])
    tiled((W, H), f).save(OUT / "fusuma_kamon.png")


def maku_sanshoku():
    w = 300 * SS
    im = Image.new("RGB", (w, w), C["green"]); d = ImageDraw.Draw(im)
    d.rectangle((w / 3, 0, w * 2 / 3, w), fill=C["crimson"]); d.rectangle((w * 2 / 3, 0, w, w), fill=C["ink"])
    for k in range(3): d.line((w * k / 3, 0, w * k / 3, w), fill=C["ink"], width=SS * 2)
    im.resize((300, 300), Image.LANCZOS).save(OUT / "maku_sanshoku.png")


def maku_green():
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["green"]); d = ImageDraw.Draw(im)
    kamon(d, w / 2, h / 2, h * 0.36, C["paper"])
    d.line((0, h * 0.06, w, h * 0.06), fill=C["paper"], width=SS * 4); d.line((0, h * 0.94, w, h * 0.94), fill=C["paper"], width=SS * 4)
    im.resize((512, 256), Image.LANCZOS).save(OUT / "maku_green.png")


def chochin_kamon():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["paper"]); d = ImageDraw.Draw(im)
    for k in range(10): d.line((0, w * k / 10, w, w * k / 10), fill=C["lavender"], width=SS * 2)
    for x0 in (0.0, 0.5): kamon(d, w * (x0 + 0.25), w * 0.5, w * 0.17, C["crimson"])
    im.resize((512, 512), Image.LANCZOS).save(OUT / "chochin_kamon.png")


def itado():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["kogecha"]); d = ImageDraw.Draw(im)
    for k in range(1, 5): d.line((w * k / 5, 0, w * k / 5, h), fill=C["ink"], width=SS * 2)
    for y in (0.15, 0.5, 0.85):
        d.rectangle((0, h * y - SS * 10, w, h * y + SS * 10), fill=C["ink"])
        for x in (0.15, 0.5, 0.85): d.ellipse((w * x - SS * 7, h * y - SS * 7, w * x + SS * 7, h * y + SS * 7), fill=C["ochre"])
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 6)
    im.resize((256, 496), Image.LANCZOS).save(OUT / "itado.png")


def fusuma_nami():
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        rng = np.random.default_rng(31)
        for ox in range(3):
            X, Y = ox * w, h
            for row in range(5):   # 一排排卷浪：深藍浪身 + 白浪头的卷爪
                yb = Y + h * (0.35 + row * 0.16)
                for k in range(-1, 7):
                    cx = X + w * (k + (0.5 if row % 2 else 0)) / 6; R = h * rng.uniform(0.17, 0.24)
                    d.pieslice((cx - R, yb - R, cx + R, yb + R), 180, 360, fill=C["navy"] if row % 2 else C["blue"], outline=C["ink"], width=SS * 3)
                    d.pieslice((cx - R * 0.7, yb - R * 0.7, cx + R * 0.7, yb + R * 0.7), 180, 360, fill=C["blue"] if row % 2 else C["navy"])
                    for j in range(5):   # 浪头的白爪
                        a = math.pi + math.pi * (0.55 + 0.08 * j); rr = R * 0.98
                        x, y = cx + math.cos(a) * rr, yb + math.sin(a) * rr
                        d.ellipse((x - R * 0.08, y - R * 0.08, x + R * 0.08, y + R * 0.08), fill=C["paper"], outline=C["ink"], width=SS)
            d.rectangle((X, Y + h * 0.95, X + w, Y + h), fill=C["navy"])
    tiled((W, H), f).save(OUT / "fusuma_nami.png")


def rug_tsuru():
    w, h = 1024 * SS, 768 * SS
    im = Image.new("RGB", (w, h), C["crimson"]); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.04, h * 0.05, w * 0.96, h * 0.95), fill=C["blue"], outline=C["paper"], width=SS * 6)
    cx, cy = w * 0.5, h * 0.52
    for side in (-1, 1):   # 两扇张开的翅膀：几层白羽 + 墨色翼尖
        for k in range(6):
            r = w * (0.34 - 0.04 * k); a0, a1 = (200, 250) if side < 0 else (290, 340)
            d.pieslice((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), a0, a1, fill=C["paper"] if k else C["ink"], outline=C["ink"], width=SS * 2)
    d.ellipse((cx - w * 0.05, cy - h * 0.12, cx + w * 0.05, cy + h * 0.16), fill=C["paper"], outline=C["ink"], width=SS * 3)   # 身子
    d.line((cx, cy - h * 0.1, cx + w * 0.04, cy - h * 0.3), fill=C["ink"], width=SS * 14)   # 脖子
    d.ellipse((cx + w * 0.025, cy - h * 0.36, cx + w * 0.065, cy - h * 0.29), fill=C["paper"], outline=C["ink"], width=SS * 2)
    d.ellipse((cx + w * 0.035, cy - h * 0.365, cx + w * 0.055, cy - h * 0.34), fill=C["crimson"])   # 丹顶
    for (fx, fy) in ((0.15, 0.2), (0.85, 0.8), (0.15, 0.8), (0.85, 0.2)): kumo(d, w * fx, h * fy, w * 0.16, h * 0.05, C["lavender"], C["paper"])
    im.resize((1024, 768), Image.LANCZOS).save(OUT / "rug_tsuru.png")


def zabuton_maru():
    w = 256 * SS
    im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    for k, col in enumerate((C["crimson"], C["blue"], C["paper"], C["blue"], C["crimson"], C["ochre"])):
        r = w * 0.5 * (1 - k * 0.16); d.ellipse((w / 2 - r, w / 2 - r, w / 2 + r, w / 2 + r), fill=col, outline=C["ink"], width=SS * 2)
    for a in range(16):
        t = 2 * math.pi * a / 16; d.line((w / 2 + math.cos(t) * w * 0.42, w / 2 + math.sin(t) * w * 0.42, w / 2 + math.cos(t) * w * 0.48, w / 2 + math.sin(t) * w * 0.48), fill=C["paper"], width=SS * 3)
    im.resize((256, 256), Image.LANCZOS).save(OUT / "zabuton_maru.png")


def floor_black():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["ink"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(4): d.line((X, Y + h * k / 4, X + w, Y + h * k / 4), fill="#2A2640", width=SS * 2)
    tiled((256, 256), f).save(OUT / "floor_black.png")


def panels_color():
    w, h = 1024 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["lavender"]); d = ImageDraw.Draw(im)
    cols = [C["teal"], C["ochre"], C["blue"], C["crimson"]]
    for k in range(4):
        d.rectangle((w * (k / 4 + 0.03), h * 0.12, w * ((k + 1) / 4 - 0.03), h * 0.88), fill=cols[k], outline=C["ink"], width=SS * 3)
    im.resize((1024, 256), Image.LANCZOS).save(OUT / "panels_color.png")


def goten_blue():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["ink"]); d = ImageDraw.Draw(im)
    m = w * 0.06
    d.rectangle((m, m, w - m, w - m), fill=C["blue"])
    for k in range(5):   # 格心里淡淡的浪
        y = w * (0.3 + 0.1 * k); d.arc((w * 0.15, y - w * 0.08, w * 0.85, y + w * 0.08), 200, 340, fill=C["lavender"], width=SS * 3)
    d.rectangle((m * 1.8, m * 1.8, w - m * 1.8, w - m * 1.8), outline=C["paper"], width=SS * 2)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "goten_blue.png")


def wall_darkred():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["crimson"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for (fx, fy) in ((0.25, 0.25), (0.75, 0.75)):
                    petal_flower(d, X + w * fx, Y + h * fy, w * 0.14, 8, "#9E2440", ratio=0.5)
    tiled((512, 512), f).save(OUT / "wall_darkred.png")


def lattice_red():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["teal"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(4):
                    d.line((X + w * k / 4, Y, X + w * k / 4, Y + h), fill=C["crimson"], width=SS * 6)
                    d.line((X, Y + h * k / 4, X + w, Y + h * k / 4), fill=C["crimson"], width=SS * 6)
    tiled((256, 256), f).save(OUT / "lattice_red.png")


def dotted(name, frac, base="paper", size=512):
    rng = np.random.default_rng(37)
    b = np.array([int(C[base][i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
    ink = np.array([int(C["ink"][i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
    a = np.where((rng.random((size, size)) < frac)[..., None], ink, b).astype(np.uint8)
    Image.fromarray(a).save(OUT / f"{name}.png")


def goten_black():
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["ink"]); d = ImageDraw.Draw(im)
    m = w * 0.07
    d.rectangle((m, m, w - m, w - m), fill="#2A2640", outline=C["kogecha"], width=SS * 6)
    im.resize((512, 512), Image.LANCZOS).save(OUT / "goten_black.png")


def panels_ybg():
    w, h = 1024 * SS, 256 * SS
    im = Image.new("RGB", (w, h), C["crimson"]); d = ImageDraw.Draw(im)
    for k, col in enumerate((C["ochre"], C["blue"], C["green"], C["ochre"])):
        d.rectangle((w * (k / 4 + 0.015), h * 0.1, w * ((k + 1) / 4 - 0.015), h * 0.9), fill=col, outline=C["ink"], width=SS * 3)
    im.resize((1024, 256), Image.LANCZOS).save(OUT / "panels_ybg.png")


def shiromuku():
    w, h = 384 * SS, 512 * SS
    im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    for k in range(10): petal_flower(d, w * (0.15 + 0.7 * ((k * 37) % 10) / 10), h * (0.1 + 0.08 * k), w * 0.06, 8, C["lavender"], ratio=0.5)
    d.polygon([(w * 0.5, 0), (w * 0.42, h * 0.3), (w * 0.58, h * 0.3)], fill=C["crimson"])   # 领口露出的深红里衬
    d.rectangle((0, 0, w - 1, h - 1), outline=C["lavender"], width=SS * 4)
    im.resize((384, 512), Image.LANCZOS).save(OUT / "shiromuku.png")


if __name__ == "__main__":
    crops(); carpet(); boards(); drape(); andon(); chochin()
    tatami(); fusuma(); shoji(); udoor(); sao(); goten(); engawa(); earth(); kakejiku()
    goten_teal(); glassdoor(); fanlight(); lattice(); byobu(); koshiita(); stone(); deck(); gravel(); katomado_shoji(); fusuma_hana(); frieze_flower(); dais(); dou_sign()
    for k in ("lotus", "star", "crest"): fanlight_big(k)
    ougi_wall()
    noren_kamon(); fusuma_kamon(); maku_sanshoku(); maku_green(); chochin_kamon(); itado(); fusuma_nami(); rug_tsuru()
    zabuton_maru(); floor_black(); panels_color(); goten_blue(); wall_darkred(); lattice_red(); shiromuku()
    dotted("wall_gray", 0.55); dotted("earth_dark", 0.74); goten_black(); panels_ybg()
    print("→", OUT)
