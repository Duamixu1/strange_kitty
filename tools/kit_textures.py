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
水墨一套（笛小路家，TV《鵺》，游31，11-06）：墨、灰、和纸白，只留朱红一点。灰色是墨和纸白按比例调的（色板本身没有灰，不另起新色）。
  kit.js 里 setKitMat("ink") / 地点 JSON "mat": "ink" 整套换上；没有专门水墨版的贴图在浏览器里按亮度压成灰（朱红保留）。
  tatami_ink   淡灰蔺草 + 墨色畳缘          shoji_ink   纸白、墨色细格、灰腰板
  fusuma_ink   水墨山水襖（4 扇一幅）：远山三层淡墨、近岸浓墨、雾带留白、一点朱红落日
  plaster_ink  灰泥：纸白底上淡墨斑（像和纸纤维），一格 1 米   kokabe_ink  长押以上淡灰
  engawa_ink   深灰廊板，墨线板缝          sao_ink     纸白板顶、墨色竿缘
  stone_ink    灰石板（墨点 30%）+ 墨缝     earth_ink   深灰土间        gravel_ink  枯山水白砂：纸白、淡墨耙纹（顺 u）
  roof_ink     灰瓦：本瓦一垄一垄（顺 v）
  （木头 wood_ink、框 frame_ink 是纯色，在 kit.js 里）
笛小路家（TV《鵺》，游31，参考 assets/concept/ref/fuenokouji/，只看不裁，图案自己画）：每张有水墨版 fue_* 和退魔后的彩色版 fue_*_color
  fue_tsuiji 筋塀（纸白 + 墨色横筋）      fue_boards 白廊板          fue_tatami 白榻榻米 + 墨缘      fue_shoji 大格白障子（参考 08 右）
  fue_lattice 格子窗（参考 08 左）       fue_fusuma_bokuun 墨云襖   fue_fusuma_hane 墨溅襖           fue_fusuma_tora 虎襖（占位）
  fue_fusuma_plain 素襖                 fue_byobu_budou 葡萄屏风   fue_ceiling 深色板天花           fue_ceiling_hane 墨溅天花
  fue_snow 雪地（彩色版落樱）            fue_gate_roof 门顶（彩色版茅草）  fue_gate_door 门里            fue_dais 高台白台面   fue_dais_edge 黑白格边（彩色版繧繝缘）
  fue_genji_wall 源氏香纹墙（参考 13，占位）  fue_kicho 几帐帘           fue_aka_* 红色之间（参考 10）：墙、襖、榻榻米、天花、台、帘
  墨云、墨溅、虎、葡萄、源氏香纹墙这五张是程序画的占位，正式的等出图（docs/22 第四节）
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




# ---------- 水墨一套（游31，笛小路家） ----------
def inkmix(t):
    """t=0 墨，t=1 纸白，中间是两者按比例调出来的灰"""
    a = np.array([int(C["ink"][i:i + 2], 16) for i in (1, 3, 5)], float)
    b = np.array([int(C["paper"][i:i + 2], 16) for i in (1, 3, 5)], float)
    return "#%02X%02X%02X" % tuple(int(round(x)) for x in a + (b - a) * t)


def tatami_ink():
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), inkmix(0.78)); d = ImageDraw.Draw(im)
    for k in range(70):
        y = h * (0.08 + 0.84 * k / 70); d.line((0, y, w, y), fill=inkmix(0.7) if k % 2 else inkmix(0.84), width=SS)
    for y0 in (0, h - h * 0.075):
        d.rectangle((0, y0, w, y0 + h * 0.075), fill=C["ink"])
        for x in range(0, w, int(w / 16)): d.ellipse((x + 6, y0 + h * 0.025, x + 6 + h * 0.025, y0 + h * 0.05), fill=inkmix(0.55))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    im.resize((512, 256), Image.LANCZOS).save(OUT / "tatami_ink.png")


def shoji_ink():
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    fr = w * 0.07; koshi = h * 0.17
    for k in range(1, 4): d.line((fr + (w - 2 * fr) * k / 4, 0, fr + (w - 2 * fr) * k / 4, h - koshi), fill=inkmix(0.25), width=SS * 2)
    for k in range(1, 8): y = (h - koshi) * k / 8; d.line((0, y, w, y), fill=inkmix(0.25), width=SS * 2)
    d.rectangle((0, h - koshi, w, h), fill=inkmix(0.45)); d.line((0, h - koshi, w, h - koshi), fill=C["ink"], width=SS * 3)
    for k in range(1, 4): d.line((w * k / 4, h - koshi, w * k / 4, h), fill=inkmix(0.3), width=SS * 2)
    d.rectangle((0, 0, w - 1, h - 1), outline=inkmix(0.15), width=int(fr))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    im.resize((256, 496), Image.LANCZOS).save(OUT / "shoji_ink.png")


def fusuma_ink():
    """水墨山水，一幅 4 扇横向连续：远山三层（越远越淡）、雾带留白、近处浓墨岸石和松、一点朱红落日。程序画，不照抄原作"""
    W, H = 2048, 990
    rng = np.random.default_rng(31)
    def ridge(x0, x1, base, amp, n, seed):
        r = np.random.default_rng(seed); xs = np.linspace(x0, x1, n)
        ys = base - amp * (0.55 + 0.45 * np.sin(np.linspace(0, math.pi * r.uniform(2, 4), n) + r.uniform(0, 6))) * r.uniform(0.6, 1.0, n) ** 0.3
        return list(zip(xs, ys))
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        for ox in range(3):
            X, Y = ox * w, h
            # 落日（唯一的朱红）
            d.ellipse((X + w * 0.71, Y + h * 0.12, X + w * 0.71 + h * 0.11, Y + h * 0.23), fill=C["crimson"])
            # 三层远山：每层一条起伏的山脊，下面填满，再盖一条雾带
            for k, (t, base, amp, sd) in enumerate(((0.82, 0.48, 0.22, 3), (0.62, 0.6, 0.2, 5), (0.4, 0.72, 0.16, 8))):
                pts = ridge(X - 20, X + w + 20, Y + h * base, h * amp, 60, sd)
                d.polygon(pts + [(X + w + 20, Y + h), (X - 20, Y + h)], fill=inkmix(t))
                for (fx, fw) in ((0.1 + 0.3 * k, 0.5), (0.65 - 0.2 * k, 0.4)):   # 雾带
                    kumo(d, X + fx * w, Y + h * (base + 0.06), fw * w, h * 0.05, C["paper"], C["paper"])
            # 近处：浓墨岸石 + 一棵斜松
            d.polygon([(X, Y + h * 0.84), (X + w * 0.12, Y + h * 0.78), (X + w * 0.22, Y + h * 0.82), (X + w * 0.3, Y + h * 0.9), (X + w * 0.3, Y + h), (X, Y + h)], fill=C["ink"])
            d.polygon([(X + w * 0.78, Y + h * 0.9), (X + w * 0.88, Y + h * 0.85), (X + w, Y + h * 0.88), (X + w, Y + h), (X + w * 0.78, Y + h)], fill=inkmix(0.15))
            tr = [(0.1, 0.8), (0.12, 0.62), (0.17, 0.48), (0.25, 0.38)]
            d.line([(X + a * w, Y + b * h) for a, b in tr], fill=C["ink"], width=SS * 9, joint="curve")
            for (a, b, r) in ((0.25, 0.37, 0.07), (0.18, 0.47, 0.055), (0.3, 0.42, 0.05), (0.13, 0.57, 0.045)):   # 松针团：扁椭圆
                d.ellipse((X + a * w - h * r * 1.8, Y + b * h - h * r * 0.5, X + a * w + h * r * 1.8, Y + b * h + h * r * 0.5), fill=inkmix(0.1))
            # 水面几道淡墨横线
            for k in range(6):
                y = Y + h * (0.9 + 0.015 * k); x0 = X + w * rng.uniform(0.35, 0.5); d.line((x0, y, x0 + w * rng.uniform(0.15, 0.3), y), fill=inkmix(0.55), width=SS * 2)
    tiled((W, H), f).save(OUT / "fusuma_ink.png")


def plaster_ink():
    """灰泥：纸白底上稀疏的淡墨斑和纤维，一格 1 米（墙 UV 按米）"""
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        rng = np.random.default_rng(41)
        for _ in range(260):
            x, y, r = rng.uniform(0, w * 3), rng.uniform(0, h * 3), rng.uniform(6, 22) * SS
            d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=inkmix(rng.uniform(0.86, 0.93)))
        for _ in range(500):   # 纤维
            x, y = rng.uniform(0, w * 3), rng.uniform(0, h * 3); a = rng.uniform(0, math.pi); L = rng.uniform(6, 16) * SS
            d.line((x, y, x + L * math.cos(a), y + L * math.sin(a)), fill=inkmix(0.8), width=SS)
    tiled((512, 512), f).save(OUT / "plaster_ink.png")


def engawa_ink():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.3))
        rng = np.random.default_rng(43)
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(6):
                    y = Y + h * k / 6
                    for _ in range(3):
                        yy = y + rng.uniform(0.15, 0.85) * h / 6; d.line((X, yy, X + w, yy + rng.uniform(-3, 3)), fill=inkmix(0.38), width=SS)
                    d.line((X, y, X + w, y), fill=C["ink"], width=SS * 2)
    tiled((512, 512), f).save(OUT / "engawa_ink.png")


def sao_ink():
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.88))
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(5): d.line((X + w * (0.1 + 0.2 * k), Y, X + w * (0.12 + 0.2 * k), Y + h), fill=inkmix(0.78), width=SS * 2)
                for k in range(2):
                    x = X + w * (0.25 + 0.5 * k)
                    d.rectangle((x - w * 0.03, Y, x + w * 0.03, Y + h), fill=inkmix(0.2), outline=C["ink"], width=SS * 2)
    tiled((512, 512), f).save(OUT / "sao_ink.png")


def dotted_ink(name, frac, base_t, size=512, joints=False):
    rng = np.random.default_rng(47)
    hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
    b, ink = hexrgb(inkmix(base_t)), hexrgb(C["ink"])
    im = Image.fromarray(np.where((rng.random((size, size)) < frac)[..., None], ink, b).astype(np.uint8))
    if joints:
        d = ImageDraw.Draw(im)
        d.line((0, 0, size, 0), fill=C["ink"], width=4); d.line((0, 0, 0, size), fill=C["ink"], width=4)
        d.line((size // 2, size // 2, size, size // 2), fill=C["ink"], width=3)
    im.save(OUT / f"{name}.png")


def gravel_ink():
    """枯山水白砂：纸白底、淡墨耙纹顺 u（一格 0.91 米 8 道）"""
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
        rng = np.random.default_rng(53)
        for _ in range(2500):
            x, y = rng.uniform(0, w * 3), rng.uniform(0, h * 3); d.point((x, y), fill=inkmix(0.7))
        for k in range(24):
            y = h * k / 8 + h / 16; d.line((0, y, w * 3, y), fill=inkmix(0.72), width=SS * 3)
    tiled((512, 512), f).save(OUT / "gravel_ink.png")


def roof_ink():
    """灰瓦：本瓦一垄一垄（顺 v），丸瓦深、平瓦浅，一格 1 米 4 垄"""
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.5))
        for k in range(12):
            x = w * k / 4
            d.rectangle((x - w * 0.035, 0, x + w * 0.035, h * 3), fill=inkmix(0.28), outline=C["ink"], width=SS * 2)
            for j in range(12): d.line((x - w * 0.035, h * j / 4, x + w * 0.035, h * j / 4), fill=C["ink"], width=SS)
    tiled((512, 512), f).save(OUT / "roof_ink.png")


def ink_set():
    tatami_ink(); shoji_ink(); fusuma_ink(); plaster_ink(); engawa_ink(); sao_ink(); gravel_ink(); roof_ink()
    dotted_ink("stone_ink", 0.3, 0.75, joints=True); dotted_ink("earth_ink", 0.5, 0.55)


# ---------- 笛小路家（游31）：水墨版 + 彩色版 ----------
def hexc(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mixc(a, b, t):
    a, b = hexc(C.get(a, a)), hexc(C.get(b, b)); return "#%02X%02X%02X" % tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def fue_save(im, name, size):
    im.resize(size, Image.LANCZOS).save(OUT / name)


def fue_tsuiji(color=False):
    w = 512 * SS; bg = C["paper"] if not color else mixc("paper", "ochre", 0.12); ln = inkmix(0.45) if not color else mixc("paper", "kogecha", 0.45)
    im = Image.new("RGB", (w, w), bg); d = ImageDraw.Draw(im); rng = np.random.default_rng(61)
    for _ in range(160):
        x, y, r = rng.uniform(0, w), rng.uniform(0, w), rng.uniform(6, 20) * SS
        d.ellipse((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=inkmix(0.9) if not color else mixc("paper", "ochre", 0.22))
    for k in range(5): y = w * (0.12 + 0.12 * k); d.line((0, y, w, y), fill=ln, width=SS * 3)
    fue_save(im, f"fue_tsuiji{'_color' if color else ''}.png", (512, 512))


def fue_boards(color=False):
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.9) if not color else C["ochre"])
        rng = np.random.default_rng(63)
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(6):
                    y = Y + h * k / 6
                    for _ in range(2):
                        yy = y + rng.uniform(0.2, 0.8) * h / 6; d.line((X, yy, X + w, yy), fill=inkmix(0.82) if not color else "#CDB565", width=SS)
                    d.line((X, y, X + w, y), fill=inkmix(0.35) if not color else C["kogecha"], width=SS * 2)
    tiled((512, 512), f).save(OUT / f"fue_boards{'_color' if color else ''}.png")


def fue_tatami():
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), inkmix(0.93)); d = ImageDraw.Draw(im)
    for k in range(70):
        y = h * (0.06 + 0.88 * k / 70); d.line((0, y, w, y), fill=inkmix(0.86) if k % 2 else inkmix(0.96), width=SS)
    for y0 in (0, h - h * 0.05): d.rectangle((0, y0, w, y0 + h * 0.05), fill=inkmix(0.25))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    fue_save(im, "fue_tatami.png", (512, 256))


def fue_shoji(color=False):
    w, h = 256 * SS, 496 * SS
    fr_c = C["ink"] if not color else C["kogecha"]
    im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.86, w, h), fill=inkmix(0.6) if not color else C["ochre"])   # 下面一截板
    d.rectangle((0, 0, w - 1, h - 1), outline=fr_c, width=int(w * 0.07))
    d.line((0, h * 0.86, w, h * 0.86), fill=fr_c, width=SS * 4)
    fue_save(im, f"fue_shoji{'_color' if color else ''}.png", (256, 496))


def fue_lattice(color=False):
    w, h = 256 * SS, 496 * SS
    bar = C["ink"] if not color else C["kogecha"]; win = inkmix(0.82) if not color else C["paper"]
    im = Image.new("RGB", (w, h), bar); d = ImageDraw.Draw(im)
    nx, ny = 5, 11; top, bot = h * 0.04, h * 0.8; m = w * 0.05
    for i in range(nx):
        for j in range(ny):
            x0 = m + (w - 2 * m) * i / nx; y0 = top + (bot - top) * j / ny
            d.rectangle((x0 + w * 0.025, y0 + h * 0.012, x0 + (w - 2 * m) / nx - w * 0.025, y0 + (bot - top) / ny - h * 0.012), fill=win)
    d.rectangle((0, bot + h * 0.02, w, h), fill=inkmix(0.3) if not color else C["kogecha"])
    fue_save(im, f"fue_lattice{'_color' if color else ''}.png", (256, 496))


def swirl(d, cx, cy, r, turns, width, fill, rng):
    """墨云的一团卷：渐开的螺线，笔触越卷越细"""
    pts = []
    for k in range(80):
        t = k / 79; a = turns * 2 * math.pi * t; rr = r * (1 - 0.85 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.7))
    for k in range(len(pts) - 1):
        wd = max(2, int(width * (1 - k / len(pts)) + 2)); d.line((pts[k], pts[k + 1]), fill=fill, width=wd)


def fue_fusuma_bokuun(color=False):
    """墨云襖（参考 02、11、14 的感觉，自己画）：灰纸底上大团浓淡墨云，卷着往一个方向流"""
    W, H = 2048, 990
    def f(d, w, h, im):
        bg = inkmix(0.86) if not color else C["ochre"]
        d.rectangle((0, 0, w * 3, h * 3), fill=bg)
        rng = np.random.default_rng(71)
        cols = [inkmix(0.15), inkmix(0.35), inkmix(0.6)] if not color else [C["teal"], C["blue"], C["paper"]]
        for ox in range(3):
            X, Y = ox * w, h
            for n in range(9):
                cx, cy = X + rng.uniform(0, w), Y + rng.uniform(0.15, 0.85) * h; r = rng.uniform(0.08, 0.2) * h
                col = cols[n % 3]
                for k in range(6):   # 一团云：几个椭圆叠起来
                    ox_, oy_ = rng.uniform(-1.6, 1.6) * r, rng.uniform(-0.5, 0.5) * r
                    d.ellipse((cx + ox_ - r, cy + oy_ - r * 0.55, cx + ox_ + r, cy + oy_ + r * 0.55), fill=col)
                swirl(d, cx + r * 1.4, cy - r * 0.2, r * 0.9, 1.6, SS * 10, cols[(n + 1) % 3], rng)
    tiled((W, H), f).save(OUT / f"fue_fusuma_bokuun{'_color' if color else ''}.png")


def splatter(d, w, h, X, Y, n, cols, rng, big=1.0):
    for _ in range(n):
        cx, cy = X + rng.uniform(0, w), Y + rng.uniform(0, h); r = rng.uniform(0.01, 0.06) * h * big; col = cols[rng.integers(len(cols))]
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
        for _ in range(rng.integers(3, 9)):   # 溅出去的细点和拖尾
            a = rng.uniform(0, 2 * math.pi); L = r * rng.uniform(1.5, 4)
            ex, ey = cx + math.cos(a) * L, cy + math.sin(a) * L; d.line((cx, cy, ex, ey), fill=col, width=max(2, int(r * 0.25)))
            rr = r * rng.uniform(0.1, 0.3); d.ellipse((ex - rr, ey - rr, ex + rr, ey + rr), fill=col)


def fue_fusuma_hane(color=False):
    """墨溅襖（参考 09 的感觉）：纸上甩满墨点墨线"""
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.9) if not color else C["paper"])
        rng = np.random.default_rng(73)
        cols = [C["ink"], inkmix(0.3), inkmix(0.55)] if not color else [C["navy"], C["coral"], C["teal"], C["wisteria"]]
        for ox in range(3):
            splatter(d, w, h, ox * w, h, 110, cols, rng, big=1.3)
            drips(d, w, h, ox * w, h, 26, cols, rng)
    tiled((W, H), f).save(OUT / f"fue_fusuma_hane{'_color' if color else ''}.png")


def drips(d, w, h, X, Y, n, cols, rng):
    """墨往下淌（文案：墨点一道道往下淌）：从一个墨点往下拖一条越来越细的线，底下一滴"""
    for _ in range(n):
        x, y = X + rng.uniform(0, w), Y + rng.uniform(0, 0.6) * h; L = rng.uniform(0.15, 0.45) * h; col = cols[rng.integers(len(cols))]
        wd = rng.uniform(0.008, 0.02) * h
        d.ellipse((x - wd * 1.6, y - wd * 1.6, x + wd * 1.6, y + wd * 1.6), fill=col)
        for k in range(12):
            t0, t1 = k / 12, (k + 1) / 12; ww = max(2, int(wd * (1 - t0 * 0.7)))
            d.line((x + math.sin(t0 * 3) * 3, y + L * t0, x + math.sin(t1 * 3) * 3, y + L * t1), fill=col, width=ww)
        r = wd * 0.9; d.ellipse((x - r, y + L - r, x + r, y + L + r * 1.4), fill=col)


def fue_wall_hane(color=False):
    """墨溅之间的墙（长押上下的土壁也溅满，往下淌），一格 1 米"""
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.86) if not color else C["paper"])
        rng = np.random.default_rng(77)
        cols = [C["ink"], inkmix(0.3)] if not color else [C["navy"], C["coral"], C["teal"]]
        for ox in range(3):
            for oy in range(3): splatter(d, w, h, ox * w, oy * h, 10, cols, rng, big=1.8); drips(d, w, h, ox * w, oy * h, 4, cols, rng)
    tiled((512, 512), f).save(OUT / f"fue_wall_hane{'_color' if color else ''}.png")


def fue_misu(color=False):
    """御簾：细竹条横着一道道（顺 u 平铺，一格 0.9 米 × 帘高），上下两道墨色缘，中间几道编线"""
    w, h = 512 * SS, 512 * SS
    base = inkmix(0.78) if not color else C["ochre"]; line = inkmix(0.55) if not color else "#C9B26A"; edge = C["ink"] if not color else C["crimson"]
    im = Image.new("RGB", (w, h), base); d = ImageDraw.Draw(im)
    for k in range(64): y = h * k / 64; d.line((0, y, w, y), fill=line, width=SS)
    for x in (0.25, 0.5, 0.75): d.line((w * x, 0, w * x, h), fill=edge, width=SS * 2)
    d.rectangle((0, 0, w, h * 0.06), fill=edge); d.rectangle((0, h * 0.94, w, h), fill=edge)
    fue_save(im, f"fue_misu{'_color' if color else ''}.png", (512, 512))


def fue_kinran(color=False):
    """锦缎（香柜里包东大寺的布、香包）：底上一排排小菱花"""
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.55) if not color else C["crimson"])
        for ox in range(3):
            for oy in range(3):
                for i in range(4):
                    for j in range(4):
                        cx, cy = ox * w + w * (i + 0.5 * (j % 2) + 0.25) / 4, oy * h + h * (j + 0.5) / 4
                        petal_flower(d, cx, cy, w * 0.07, 4, inkmix(0.92) if not color else C["ochre"], ratio=0.5)
    tiled((256, 256), f).save(OUT / f"fue_kinran{'_color' if color else ''}.png")


def fue_ceiling_hane(color=False):
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.75) if not color else C["paper"])
        rng = np.random.default_rng(75)
        cols = [C["ink"], inkmix(0.3)] if not color else [C["navy"], C["coral"], C["teal"]]
        for ox in range(3):
            for oy in range(3): splatter(d, w, h, ox * w, oy * h, 9, cols, rng, big=2.0)
    tiled((512, 512), f).save(OUT / f"fue_ceiling_hane{'_color' if color else ''}.png")


def fue_fusuma_tora(color=False):
    """虎襖（参考 15，占位）：一只伏着的虎，大块淡墨身子 + 浓墨横纹，头朝右。正式的等出图"""
    W, H = 2048, 990
    im = Image.new("RGB", (W * SS, H * SS), inkmix(0.88) if not color else C["paper"]); d = ImageDraw.Draw(im)
    w, h = W * SS, H * SS; body = inkmix(0.6) if not color else C["ochre"]; stripe = C["ink"]
    for (x, y, rx, ry) in ((0.45, 0.62, 0.22, 0.17), (0.62, 0.58, 0.12, 0.13), (0.3, 0.68, 0.12, 0.12)):   # 身子、肩、后腿
        d.ellipse((w * (x - rx), h * (y - ry), w * (x + rx), h * (y + ry)), fill=body)
    d.ellipse((w * 0.66, h * 0.38, w * 0.8, h * 0.6), fill=body)   # 头
    for (x, y) in ((0.7, 0.45), (0.76, 0.45)): d.ellipse((w * x - 12, h * y - 8, w * x + 12, h * y + 8), fill=stripe)   # 眼
    for k in range(12):   # 横纹
        x = w * (0.26 + 0.034 * k); d.line((x, h * 0.48, x + w * 0.02, h * 0.62), fill=stripe, width=SS * 9)
        d.line((x + w * 0.01, h * 0.64, x - w * 0.005, h * 0.76), fill=stripe, width=SS * 7)
    for k in range(8): x = w * (0.08 + 0.025 * k); d.arc((x, h * 0.5, x + w * 0.2, h * 0.9), 180, 260, fill=stripe, width=SS * 6)   # 尾巴
    for x in (0.55, 0.63, 0.38): d.ellipse((w * x - w * 0.03, h * 0.78, w * x + w * 0.03, h * 0.84), fill=body)   # 爪
    for k in range(6): d.line((w * (0.1 + 0.15 * k), h * 0.9, w * (0.18 + 0.15 * k), h * 0.86), fill=inkmix(0.6) if not color else C["green"], width=SS * 5)   # 草
    im.resize((W, H), Image.LANCZOS).save(OUT / f"fue_fusuma_tora{'_color' if color else ''}.png")


def fue_fusuma_plain(color=False):
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), inkmix(0.9) if not color else C["paper"]); d = ImageDraw.Draw(im)
    kumo(d, w * 0.5, h * 0.82, w * 0.9, h * 0.05, inkmix(0.78) if not color else C["lavender"], inkmix(0.78) if not color else C["lavender"])
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=int(w * 0.04))
    fue_save(im, f"fue_fusuma_plain{'_color' if color else ''}.png", (256, 496))


def fue_byobu_budou(color=False):
    """葡萄屏风（参考 02、05 的感觉）：藤蔓从上往下垂，叶子、一串串葡萄"""
    w, h = 2048 * SS // 2, 640 * SS // 2
    im = Image.new("RGB", (w, h), inkmix(0.9) if not color else C["ochre"]); d = ImageDraw.Draw(im)
    rng = np.random.default_rng(79)
    vine = inkmix(0.2) if not color else C["kogecha"]; leaf = [inkmix(0.45), inkmix(0.65)] if not color else [C["green"], C["teal"]]; grape = inkmix(0.15) if not color else C["wisteria"]
    for n in range(7):
        x = w * (0.05 + 0.14 * n + rng.uniform(-0.03, 0.03)); pts = [(x, 0)]
        for k in range(1, 8): pts.append((x + rng.uniform(-0.05, 0.05) * w, h * k / 8 * rng.uniform(0.7, 1.0)))
        d.line(pts, fill=vine, width=SS * 4, joint="curve")
        for (px, py) in pts[1:]:
            for _ in range(2):
                lx, ly, r = px + rng.uniform(-60, 60) * SS / 2, py + rng.uniform(-40, 40) * SS / 2, rng.uniform(28, 48) * SS / 2
                petal_flower(d, lx, ly, r, 5, leaf[rng.integers(2)], ratio=0.6)
            if rng.random() < 0.5:
                for k in range(10): gx, gy = px + rng.uniform(-14, 14) * SS / 2, py + 20 * SS / 2 + k * 7 * SS / 2; d.ellipse((gx - 9, gy - 9, gx + 9, gy + 9), fill=grape)
    im.resize((2048 // 2 * 2, 640), Image.LANCZOS).save(OUT / f"fue_byobu_budou{'_color' if color else ''}.png")


def fue_ceiling(color=False):
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.3) if not color else C["paper"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                for k in range(5): d.line((X + w * (0.1 + 0.2 * k), Y, X + w * (0.12 + 0.2 * k), Y + h), fill=inkmix(0.24) if not color else C["lavender"], width=SS * 2)
                for k in range(2):
                    x = X + w * (0.25 + 0.5 * k)
                    d.rectangle((x - w * 0.03, Y, x + w * 0.03, Y + h), fill=C["ink"] if not color else C["kogecha"], outline=C["ink"], width=SS * 2)
    tiled((512, 512), f).save(OUT / f"fue_ceiling{'_color' if color else ''}.png")


def fue_snow(color=False):
    """雪地：纸白底、淡墨的细影；彩色版是退魔后雪化了（11-06）：嫩草地、几块露土、落樱"""
    def f(d, w, h, im):
        rng = np.random.default_rng(81)
        if not color:
            d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"])
            for _ in range(300):
                x, y, r = rng.uniform(0, w * 3), rng.uniform(0, h * 3), rng.uniform(4, 14) * SS
                d.ellipse((x - r * 2, y - r * 0.4, x + r * 2, y + r * 0.4), fill=inkmix(0.93))
            return
        d.rectangle((0, 0, w * 3, h * 3), fill="#C9D29C")
        for _ in range(60):   # 露土
            x, y, r = rng.uniform(0, w * 3), rng.uniform(0, h * 3), rng.uniform(20, 60) * SS
            d.ellipse((x - r * 1.6, y - r * 0.6, x + r * 1.6, y + r * 0.6), fill="#C8B98E")
        for _ in range(900):   # 草叶
            x, y = rng.uniform(0, w * 3), rng.uniform(0, h * 3); d.line((x, y, x + rng.uniform(-4, 4) * SS, y - rng.uniform(6, 14) * SS), fill=rng.choice(["#A9B87E", "#B7C48C", "#9FAF73"]), width=SS)
        for _ in range(140):
            x, y = rng.uniform(0, w * 3), rng.uniform(0, h * 3); petal_flower(d, x, y, rng.uniform(5, 9) * SS, 5, C["pink"], notch=True)
    tiled((512, 512), f).save(OUT / f"fue_snow{'_color' if color else ''}.png")


def fue_gate_roof(color=False):
    def f(d, w, h, im):
        if not color:   # 板葺：一条条灰板
            d.rectangle((0, 0, w * 3, h * 3), fill=inkmix(0.55))
            for k in range(30): x = w * k / 10; d.line((x, 0, x, h * 3), fill=inkmix(0.3), width=SS * 2)
        else:            # 茅草：山吹底、焦茶细草纹
            d.rectangle((0, 0, w * 3, h * 3), fill=C["ochre"]); rng = np.random.default_rng(83)
            for _ in range(900):
                x, y = rng.uniform(0, w * 3), rng.uniform(0, h * 3); d.line((x, y, x + rng.uniform(-3, 3), y + rng.uniform(20, 40) * SS), fill=rng.choice([C["kogecha"], "#C9B26A"]), width=SS)
    tiled((512, 512), f).save(OUT / f"fue_gate_roof{'_color' if color else ''}.png")


def fue_gate_door(color=False):
    """门开着，从门洞看进去（文案：门一直开着）：门顶阴影下，是雪庭和远处寝殿的高廊、台阶；横向一整幅跨两格门洞。
    彩色版是退魔后：雪化了、草地、樱花、茅草屋顶"""
    w, h = 512 * SS, 496 * SS
    sky = C["paper"]; ground = C["paper"] if not color else mixc("green", "paper", 0.35)
    hall = inkmix(0.45) if not color else C["kogecha"]; roof = inkmix(0.3) if not color else C["ochre"]
    im = Image.new("RGB", (w, h), sky); d = ImageDraw.Draw(im)
    d.rectangle((0, h * 0.62, w, h), fill=ground)
    d.polygon([(w * 0.02, h * 0.36), (w * 0.98, h * 0.36), (w * 0.9, h * 0.28), (w * 0.1, h * 0.28)], fill=roof)   # 远处寝殿的屋檐
    d.rectangle((w * 0.06, h * 0.36, w * 0.94, h * 0.52), fill=inkmix(0.75) if not color else C["paper"])   # 障子一排
    for k in range(9): x = w * (0.06 + 0.11 * k); d.line((x, h * 0.36, x, h * 0.58), fill=hall, width=SS * 3)   # 廊柱
    d.rectangle((w * 0.04, h * 0.52, w * 0.96, h * 0.545), fill=hall)   # 廊板边
    for x0, x1 in ((0.04, 0.4), (0.6, 0.96)):   # 栏杆
        d.line((w * x0, h * 0.5, w * x1, h * 0.5), fill=hall, width=SS * 2)
    d.polygon([(w * 0.42, h * 0.545), (w * 0.58, h * 0.545), (w * 0.62, h * 0.62), (w * 0.38, h * 0.62)], fill=inkmix(0.8) if not color else C["ochre"])   # 台阶
    for k in range(4): y = h * (0.56 + 0.016 * k); d.line((w * (0.415 - 0.01 * k), y, w * (0.585 + 0.01 * k), y), fill=hall, width=SS)
    d.rectangle((0, h * 0.62, w, h * 0.63), fill=inkmix(0.85) if not color else C["green"])
    if color:
        rng = np.random.default_rng(91)
        for _ in range(8): x = rng.uniform(0, w); petal_flower(d, x, h * rng.uniform(0.18, 0.3), w * 0.05, 7, C["pink"], ratio=0.6)
    for y0 in range(6): d.line((0, h * 0.02 * y0, w, h * 0.02 * y0), fill=inkmix(0.2), width=SS * 4)   # 门顶阴影
    d.rectangle((0, 0, w, h * 0.08), fill=inkmix(0.2))
    fue_save(im, f"fue_gate_door{'_color' if color else ''}.png", (512, 496))


def fue_dais(color=False):
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["paper"] if not color else mixc("paper", "green", 0.15)); d = ImageDraw.Draw(im)
    for k in range(40): y = w * k / 40; d.line((0, y, w, y), fill=inkmix(0.92) if not color else mixc("paper", "green", 0.3), width=SS)
    fue_save(im, f"fue_dais{'_color' if color else ''}.png", (512, 512))


def fue_dais_edge(color=False, red=False):
    w = 512 * SS
    im = Image.new("RGB", (w, w), C["paper"]); d = ImageDraw.Draw(im)
    cols = [C["ink"], C["paper"]] if not color else [C["crimson"], C["ochre"], C["teal"], C["ochre"]]
    if red: cols = [C["ink"], C["crimson"]]
    for k in range(8): d.rectangle((w * k / 8, 0, w * (k + 1) / 8, w), fill=cols[k % len(cols)])
    fue_save(im, "fue_aka_dais_edge.png" if red else f"fue_dais_edge{'_color' if color else ''}.png", (512, 512))


def fue_genji_wall(color=False):
    """源氏香纹墙（参考 13 的感觉，占位）：灰墙上一枚大六角源氏香纹，旁边一笔淡墨扫过。正式的等出图"""
    w, h = 1024 * SS, 600 * SS
    im = Image.new("RGB", (w, h), inkmix(0.82) if not color else C["paper"]); d = ImageDraw.Draw(im)
    for k in range(8): d.line((w * (0.55 + 0.04 * k), h, w * (0.95 + 0.02 * k), 0), fill=inkmix(0.65) if not color else C["lavender"], width=SS * 14)
    cx, cy, r = w * 0.3, h * 0.45, h * 0.28
    ring = C["ink"] if not color else C["crimson"]; inner = inkmix(0.82) if not color else C["paper"]
    d.polygon([(cx + r * math.cos(math.pi / 3 * k + math.pi / 6), cy + r * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)], fill=ring)
    d.polygon([(cx + r * 0.8 * math.cos(math.pi / 3 * k + math.pi / 6), cy + r * 0.8 * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)], fill=inner)
    bw = r * 0.09; xs = [cx + r * (-0.5 + 0.25 * k) for k in range(5)]; top, bot = cy - r * 0.45, cy + r * 0.5
    bar_c = C["ink"] if not color else C["ochre"]
    for k, x in enumerate(xs): d.rectangle((x - bw / 2, top if k != 2 else top + r * 0.2, x + bw / 2, bot), fill=bar_c)
    d.rectangle((xs[0] - bw / 2, top, xs[1] + bw / 2, top + bw), fill=bar_c); d.rectangle((xs[3] - bw / 2, top, xs[4] + bw / 2, top + bw), fill=bar_c)
    d.rectangle((xs[1] - bw / 2, top + r * 0.2, xs[3] + bw / 2, top + r * 0.2 + bw), fill=bar_c)
    fue_save(im, f"fue_genji_wall{'_color' if color else ''}.png", (1024, 600))


def fue_kicho(color=False, red=False):
    w, h = 256 * SS, 512 * SS
    a, b = (C["paper"], C["ink"]) if not color else (C["paper"], C["crimson"])
    if red: a, b = C["crimson"], C["ink"]
    im = Image.new("RGB", (w, h), a); d = ImageDraw.Draw(im)
    for k in range(4): x = w * (0.1 + 0.25 * k); d.rectangle((x, 0, x + w * 0.06, h), fill=b)
    fue_save(im, "fue_aka_kicho.png" if red else f"fue_kicho{'_color' if color else ''}.png", (256, 512))


def fue_aka():
    """红色之间（参考 10）：整间朱红，墨色描框，暗一档的红做阴影纹理"""
    cr, dk = C["crimson"], mixc("crimson", "ink", 0.35)
    w = 512 * SS
    im = Image.new("RGB", (w, w), cr); d = ImageDraw.Draw(im); rng = np.random.default_rng(85)
    for _ in range(140):
        x, y, r = rng.uniform(0, w), rng.uniform(0, w), rng.uniform(6, 22) * SS; d.ellipse((x - r, y - r * 0.5, x + r, y + r * 0.5), fill=mixc("crimson", "ink", 0.12))
    fue_save(im, "fue_aka_wall.png", (512, 512))
    w, h = 256 * SS, 496 * SS
    im = Image.new("RGB", (w, h), mixc("crimson", "pink", 0.35)); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.12, h * 0.08, w * 0.88, h * 0.5), outline=dk, width=SS * 4)
    d.rectangle((w * 0.12, h * 0.56, w * 0.88, h * 0.9), outline=dk, width=SS * 4)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=int(w * 0.05))
    fue_save(im, "fue_aka_fusuma.png", (256, 496))
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), cr); d = ImageDraw.Draw(im)
    for k in range(70): y = h * (0.06 + 0.88 * k / 70); d.line((0, y, w, y), fill=mixc("crimson", "ink", 0.1) if k % 2 else mixc("crimson", "pink", 0.15), width=SS)
    for y0 in (0, h - h * 0.06): d.rectangle((0, y0, w, y0 + h * 0.06), fill=C["ink"])
    fue_save(im, "fue_aka_tatami.png", (512, 256))
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=dk)
        for ox in range(3):
            for oy in range(3):
                for k in range(2):
                    x = ox * w + w * (0.25 + 0.5 * k); d.rectangle((x - w * 0.03, oy * h, x + w * 0.03, oy * h + h), fill=C["ink"])
    tiled((512, 512), f).save(OUT / "fue_aka_ceiling.png")
    w = 512 * SS
    im = Image.new("RGB", (w, w), mixc("crimson", "pink", 0.25)); d = ImageDraw.Draw(im)
    for k in range(40): y = w * k / 40; d.line((0, y, w, y), fill=cr, width=SS)
    fue_save(im, "fue_aka_dais.png", (512, 512))
    fue_dais_edge(red=True); fue_kicho(red=True)


def fue_tatami_color():
    """退魔后的榻榻米：淡黄绿（参考 17、19 那种柔和的调子，不要原来 tatami.png 那么艳）"""
    w, h = 512 * SS, 256 * SS
    im = Image.new("RGB", (w, h), "#BFC98F"); d = ImageDraw.Draw(im)
    for k in range(70):
        y = h * (0.06 + 0.88 * k / 70); d.line((0, y, w, y), fill="#B3BE84" if k % 2 else "#C9D29C", width=SS)
    for y0 in (0, h - h * 0.05): d.rectangle((0, y0, w, y0 + h * 0.05), fill="#7A6A4E")
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 2)
    fue_save(im, "fue_tatami_color.png", (512, 256))


def fue_soften():
    """彩色版统一往原作结尾（参考 17、19）的柔和调子收：降饱和、提一点亮，绿往黄绿偏，蓝往藤灰偏，最后往纸白压一成"""
    import colorsys
    paper = np.array([int(C["paper"][i:i + 2], 16) for i in (1, 3, 5)], float) / 255
    for f in sorted(OUT.glob("fue_*_color.png")):
        a = np.asarray(Image.open(f).convert("RGB"), float) / 255
        flat = a.reshape(-1, 3); out = np.empty_like(flat)
        hsv = np.array([colorsys.rgb_to_hsv(*px) for px in flat])
        h, s_, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]
        green = (h > 0.17) & (h < 0.5); blue = (h >= 0.5) & (h < 0.75)
        h = np.where(green, h + (0.2 - h) * 0.55, h); s_ = np.where(green, s_ * 0.5, s_ * 0.62)
        s_ = np.where(blue, s_ * 0.6, s_); v = v * 0.9 + 0.08
        out = np.array([colorsys.hsv_to_rgb(*q) for q in zip(h, s_, np.clip(v, 0, 1))])
        out = out * 0.88 + paper * 0.12
        Image.fromarray((out.reshape(a.shape) * 255).clip(0, 255).astype(np.uint8)).save(f)


def fue_from_scenes():
    """笛小路家出的四张水墨图（scenes/47~50，游32，11-06 用户确认花积分）→ 贴图：水墨版原样缩到贴图尺寸存 jpg；
    彩色版不另出画（用户定），按亮度做柔和的渐变映射（墨 → 深色，灰 → 旧金 / 淡绿，纸白 → 纸白），往原作结尾那种调子收"""
    def ramp(stops):
        xs = [t for t, _ in stops]; cs = [np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], float) for _, c in stops]
        lut = np.zeros((256, 3))
        for v in range(256):
            t = v / 255; k = max(0, min(len(xs) - 2, next((q for q in range(len(xs) - 1) if t <= xs[q + 1]), len(xs) - 2)))
            u = (t - xs[k]) / (xs[k + 1] - xs[k]); lut[v] = cs[k] + (cs[k + 1] - cs[k]) * u
        return lut
    jobs = {   # 场景图 → (贴图名, 尺寸, 彩色渐变)
        "47_笛小路家_墨云襖": ("fue_fusuma_bokuun", (2496, 832), [(0, "#4A5170"), (0.45, "#8E9BB3"), (0.75, "#D6C48E"), (1, "#F3ECDC")]),
        "48_笛小路家_虎襖": ("fue_fusuma_tora", (2496, 832), [(0, "#4A3A30"), (0.4, "#A7834F"), (0.72, "#D9C38C"), (1, "#F1EADA")]),
        "49_笛小路家_源氏香纹墙": ("fue_genji_wall", (2048, 1120), [(0, "#6E3442"), (0.45, "#B9A0A0"), (0.8, "#E8DCC8"), (1, "#F4EDE0")]),
        "50_笛小路家_雪庭全景天空": ("fue_sky", (3840, 1920), [(0, "#6F6D8C"), (0.5, "#B7B6CC"), (0.8, "#EAD9DE"), (1, "#F7EFE8")]),
    }
    for sid, (name, size, stops) in jobs.items():
        src = SC / f"{sid}.png"
        if not src.exists(): print("还没有", src.name); continue
        im = Image.open(src).convert("RGB").resize(size, Image.LANCZOS)
        im.save(OUT / f"{name}.jpg", quality=88)
        L = np.asarray(im.convert("L"))
        Image.fromarray(ramp(stops)[L].astype(np.uint8)).save(OUT / f"{name}_color.jpg", quality=88)
        print("→", name, size)


def fue_sky_spring():
    """退魔后的天（11-06 总指挥：上色后雪停了、"原来外面早就是春天"）：从水墨全景 scenes/50 程序改——
    先去掉画上去的雪片（亮点：比 9 像素中值亮一截的换成中值），云的浓淡压一半，再按高度上色：
    天淡青到暖白，地平线一带樱粉雾，远山远树浅绿，下面三分之一是嫩草地。直接覆盖 fue_sky_color.jpg"""
    from PIL import ImageFilter
    src = SC / "50_笛小路家_雪庭全景天空.png"
    if not src.exists(): print("还没有", src.name); return
    im = Image.open(src).convert("L").resize((3840, 1920), Image.LANCZOS)
    a = np.asarray(im, float)
    for k, th in ((9, 10), (21, 5), (21, 4)):   # 雪片：比周围中值亮的点换成中值，小的、大的软雪团各过一遍
        med = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.MedianFilter(k)), float)
        a = np.where(a - med > th, med, a)
    a = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), float)
    H = a.shape[0]; y = np.linspace(0, 1, H)[:, None]
    L = a / 255
    hexa = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)
    def band(t, c0, c1): return c0 + (c1 - c0) * t[..., None]
    sky_t = np.clip(0.45 + 0.55 * L, 0, 1) * (0.55 + 0.45 * np.clip(y / 0.6, 0, 1))   # 云淡一半；越往天顶越青
    sky = band(sky_t, hexa("#86AFC6"), hexa("#F4F1E8"))      # 淡青 → 暖白
    haze = band(np.clip(L, 0, 1), hexa("#C89AA6"), hexa("#F3DDE2"))   # 樱粉雾
    hills = band(np.clip(L * 1.2, 0, 1), hexa("#6F8A62"), hexa("#DCE3C2"))   # 远山远树浅绿
    ground = band(np.clip(0.4 + 0.6 * L, 0, 1), hexa("#A9B87E"), hexa("#E3E6C4"))   # 嫩草地
    w = lambda c, s_: np.clip(1 - np.abs(y - c) / s_, 0, 1)[..., None]
    wh, wz, wg = w(0.66, 0.06), w(0.6, 0.12), np.clip((y - 0.7) / 0.05, 0, 1)[..., None]
    out = sky * (1 - wz) + haze * wz
    out = out * (1 - wh) + hills * wh
    out = out * (1 - wg) + ground * wg
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(OUT / "fue_sky_color.jpg", quality=88)
    print("→ fue_sky_color.jpg（春天）")


def fue_set():
    fue_tatami(); fue_aka()
    for c in (False, True):
        fue_tsuiji(c); fue_boards(c); fue_shoji(c); fue_lattice(c); fue_fusuma_bokuun(c); fue_fusuma_hane(c); fue_ceiling_hane(c)
        fue_fusuma_tora(c); fue_fusuma_plain(c); fue_byobu_budou(c); fue_ceiling(c); fue_snow(c); fue_gate_roof(c); fue_gate_door(c)
        fue_dais(c); fue_dais_edge(c); fue_genji_wall(c); fue_kicho(c); fue_wall_hane(c); fue_misu(c); fue_kinran(c)
    fue_tatami_color(); fue_soften()   # 彩色版最后统一压柔（11-06 总指挥：榻榻米绿太艳）
    fue_from_scenes()   # 出图的四张（墨云襖、虎襖、源氏香纹墙、雪庭全景天空）覆盖程序画的占位
    fue_sky_spring()    # 退魔后的天：去雪片、往春天靠


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:   # 只重画点名的几张：uv run tools/kit_textures.py ink_set fusuma_ink …
        for name in sys.argv[1:]: globals()[name]()
        print("→", OUT); sys.exit()
    crops(); carpet(); boards(); drape(); andon(); chochin()
    tatami(); fusuma(); shoji(); udoor(); sao(); goten(); engawa(); earth(); kakejiku()
    goten_teal(); glassdoor(); fanlight(); lattice(); byobu(); koshiita(); stone(); deck(); gravel(); katomado_shoji(); fusuma_hana(); frieze_flower(); dais(); dou_sign()
    for k in ("lotus", "star", "crest"): fanlight_big(k)
    ougi_wall()
    noren_kamon(); fusuma_kamon(); maku_sanshoku(); maku_green(); chochin_kamon(); itado(); fusuma_nami(); rug_tsuru()
    zabuton_maru(); floor_black(); panels_color(); goten_blue(); wall_darkred(); lattice_red(); shiromuku()
    dotted("wall_gray", 0.55); dotted("earth_dark", 0.74); goten_black(); panels_ybg()
    ink_set(); fue_set()
    print("→", OUT)
