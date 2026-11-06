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
そらりす丸（TV《海坊主》，游33，参考 assets/concept/ref/solaris/，只看不裁，图案自己画）：满眼是色（粉红、天青、柠黄、薄紫、朱红），sol_* 一套
  sol_deck 甲板板   sol_hull 船舷（上粉红大花、下天青海底城）   sol_sea / sol_sea_color 海（退魔前青灰起雾 / 退魔后蓝底金线浪）
  sol_pool 浮萍池   sol_uzu 漩涡池   sol_tile 红青格子地砖   sol_koshi 花菱格子天井   sol_mojing 柠黄鱼纹藻井（占位）   sol_pillar 天青花纹柱
  sol_wall_pink 粉红墙   sol_panel 红白漩涡板   sol_panel_door / sol_door 舱门   sol_shoji 白障子   sol_lattice 格子窗   sol_floor_ao 浅青地板
  sol_houou 凤凰画（占位）   sol_hata1~3 大幡（寿字、花菱、几何纹）   sol_sail 红漩涡帆   sol_fuda 贴满札的墙   sol_carpet 楼梯地毯   sol_tower 船楼板
  sol_lantern_r / _w 红白提灯
地下铁（TV《化猫》，大正末年，游34，参考帧待定，图案自己画）：sub_* 一套，大正摩登——白瓷砖、绿腰板、深红车身、黄铜、彩色玻璃
  sub_tile 白瓷砖   sub_tile_green 绿瓷砖腰板   sub_floor 站台水磨石   sub_edge 站台边水泥   sub_ballast 道砟   sub_tunnel 隧道口
  sub_posters 海报墙（占位）   sub_sign 站名牌   sub_car_ext 车身   sub_car_door 车门   sub_car_wall 车厢窗带（窗外黑）   sub_ad 车厢广告带
  sub_car_ceil / sub_car_floor 车厢天花、地板   sub_ceil 通道天花   sub_checker 黑白格地砖   sub_wall_cafe / _up 咖啡馆墙   sub_cafe_ceil
  sub_stained 彩色玻璃窗   sub_door 木门   sub_clock 钟面   sub_kaisatsu_sign 改札牌
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


def wall_gray():
    # 廊下的灰泥：纸与墨先调成灰，只在邻近的灰度间扫出细纹，近看不生黑白噪点。
    rng = np.random.default_rng(37)
    fiber = rng.normal(0, 1.8, (256, 256))
    y, x = np.mgrid[:256, :256] * (2 * math.pi / 256)
    wash = 2.8*np.sin(2*y + .8*np.sin(x)) + 1.4*np.cos(3*x - y)
    rgb = np.array([155, 148, 148]) + (fiber + wash)[..., None]
    Image.fromarray(rgb.astype(np.uint8)).save(OUT / "wall_gray.png")


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


# ---------- そらりす丸（游33）：满眼是色 ----------
def spiral(d, cx, cy, r, turns, width, fill):
    pts = [(cx + r * (1 - k / 90) * math.cos(turns * 2 * math.pi * k / 90), cy + r * (1 - k / 90) * math.sin(turns * 2 * math.pi * k / 90)) for k in range(91)]
    d.line(pts, fill=fill, width=width, joint="curve")


def hanabishi(d, cx, cy, r, petal, center):
    for k in range(4):
        a = math.pi / 2 * k + math.pi / 4
        d.ellipse((cx + math.cos(a) * r * 0.5 - r * 0.32, cy + math.sin(a) * r * 0.5 - r * 0.32, cx + math.cos(a) * r * 0.5 + r * 0.32, cy + math.sin(a) * r * 0.5 + r * 0.32), fill=petal)
    d.ellipse((cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18), fill=center)


def sol_save(im, name, size): im.resize(size, Image.LANCZOS).save(OUT / name)


def sol_set():
    rng = np.random.default_rng(101)
    # 甲板 / 地板：浅木板、浅青地板
    for name, base, line in (("sol_deck", mixc("paper", "ochre", 0.3), mixc("ochre", "kogecha", 0.35)), ("sol_floor_ao", mixc("teal", "paper", 0.62), mixc("teal", "paper", 0.3))):
        def f(d, w, h, im, base=base, line=line):
            d.rectangle((0, 0, w * 3, h * 3), fill=base)
            for k in range(18): y = h * k / 6; d.line((0, y, w * 3, y), fill=line, width=SS * 2)
        tiled((512, 512), f).save(OUT / f"{name}.png")
    # 船舷：上半粉红底大花，下半天青海底城（楼阁剪影 + 鱼），一格 = 船舷高（u 按米 / 高）
    w = 1024 * SS; im = Image.new("RGB", (w, w), C["pink"]); d = ImageDraw.Draw(im)
    d.rectangle((0, w * 0.5, w, w), fill=C["teal"]); d.rectangle((0, w * 0.47, w, w * 0.5), fill=C["crimson"])
    for k in range(9):
        x = w * (k + 0.5) / 9; y = w * (0.2 + 0.12 * (k % 2))
        petal_flower(d, x, y, w * 0.07, 8, [C["coral"], C["ochre"], C["wisteria"]][k % 3], inner=C["paper"], ratio=0.5)
        for q in range(3): petal_flower(d, x + w * 0.05 * (q - 1), y + w * 0.09, w * 0.025, 5, C["green"], ratio=0.6)
    for k in range(6):   # 海底城：楼阁剪影
        x = w * (0.08 + 0.16 * k); bw = w * 0.07; by = w * (0.86 - 0.04 * (k % 3))
        d.rectangle((x, by, x + bw, w * 0.96), fill=C["blue"]); d.polygon([(x - bw * 0.2, by), (x + bw * 1.2, by), (x + bw / 2, by - bw * 0.45)], fill=C["navy"])
    for k in range(10):
        fx, fy = rng.uniform(0, w), rng.uniform(0.56, 0.78) * w; d.ellipse((fx, fy, fx + w * 0.035, fy + w * 0.015), fill=C["ochre"]); d.polygon([(fx, fy + w * 0.0075), (fx - w * 0.012, fy), (fx - w * 0.012, fy + w * 0.015)], fill=C["ochre"])
    for k in range(4): y = w * (0.55 + 0.1 * k); d.arc((-w * 0.1, y - w * 0.05, w * 1.1, y + w * 0.05), 0, 180, fill=C["lavender"], width=SS * 3)
    sol_save(im, "sol_hull.png", (1024, 1024))
    # 海：琳派浪线（一格 4 米）。退魔前青灰起雾、退魔后蓝底金线
    for name, base, l1, l2 in (("sol_sea", "#7F9AA0", "#A9BCBE", "#5E7A82"), ("sol_sea_color", C["navy"], C["ochre"], C["blue"])):
        def f(d, w, h, im, base=base, l1=l1, l2=l2):
            d.rectangle((0, 0, w * 3, h * 3), fill=base)
            for row in range(18):
                y0 = h * row / 6
                for k in range(-1, 13):
                    x = w * k / 4 + (w / 8 if row % 2 else 0)
                    for q, col in ((0.0, l1), (0.035, l2), (0.07, l1)):
                        d.arc((x - w * 0.13, y0 - h * 0.06 + h * q, x + w * 0.13, y0 + h * 0.14 + h * q), 200, 340, fill=col, width=SS * 3)
        tiled((512, 512), f).save(OUT / f"{name}.png")
    # 浮萍池
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=mixc("teal", "navy", 0.35)); r2 = np.random.default_rng(103)
        for _ in range(220):
            x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(8, 22) * SS
            d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=[C["green"], mixc("green", "teal", 0.4), mixc("green", "ochre", 0.3)][r2.integers(3)])
        for _ in range(14): x, y = r2.uniform(0, w * 3), r2.uniform(0, h * 3); petal_flower(d, x, y, 14 * SS, 6, C["pink"], inner=C["ochre"], ratio=0.5)
    tiled((512, 512), f).save(OUT / "sol_pool.png")
    # 漩涡池（参考 0510）
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["navy"]); r2 = np.random.default_rng(107)
        for _ in range(130):
            spiral(d, r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(40, 110) * SS, 2.4, SS * 9, [C["ochre"], C["pink"], C["teal"], C["wisteria"], C["coral"]][r2.integers(5)])
    tiled((512, 512), f).save(OUT / "sol_uzu.png")
    # 红青格子地砖（一格 0.91 米 2×2）
    w = 512 * SS; im = Image.new("RGB", (w, w), C["paper"]); d = ImageDraw.Draw(im)
    for i in range(2):
        for j in range(2):
            col = C["teal"] if (i + j) % 2 else C["coral"]; x0, y0 = w * i / 2, w * j / 2
            d.rectangle((x0, y0, x0 + w / 2, y0 + w / 2), fill=col, outline=C["ink"], width=SS * 3)
            hanabishi(d, x0 + w / 4, y0 + w / 4, w * 0.13, C["paper"], C["ochre"])
    sol_save(im, "sol_tile.png", (512, 512))
    # 花菱格子天井（一格 0.91 米）：粉红格梁、纸白格心、朱红天青花菱
    w = 512 * SS; im = Image.new("RGB", (w, w), C["pink"]); d = ImageDraw.Draw(im); m = w * 0.08
    d.rectangle((m, m, w - m, w - m), fill=C["paper"], outline=C["crimson"], width=SS * 4)
    d.polygon([(w / 2, m * 1.8), (w - m * 1.8, w / 2), (w / 2, w - m * 1.8), (m * 1.8, w / 2)], fill=C["crimson"])
    d.polygon([(w / 2, m * 2.8), (w - m * 2.8, w / 2), (w / 2, w - m * 2.8), (m * 2.8, w / 2)], fill=C["paper"])
    hanabishi(d, w / 2, w / 2, w * 0.16, C["teal"], C["ochre"])
    for x in (m / 2, w - m / 2):
        for y in (m / 2, w - m / 2): d.ellipse((x - m * 0.3, y - m * 0.3, x + m * 0.3, y + m * 0.3), fill=C["ochre"])
    sol_save(im, "sol_koshi.png", (512, 512))
    # 柠黄鱼纹藻井（占位，参考 0600、1224 的感觉）：柠黄底鳞纹，中间一条大红鱼
    w = 1024 * SS; im = Image.new("RGB", (w, w), C["ochre"]); d = ImageDraw.Draw(im)
    for row in range(26):
        for k in range(27):
            cx_, cy_ = w * k / 26 + (w / 52 if row % 2 else 0), w * row / 26
            d.arc((cx_ - w / 52, cy_ - w / 52, cx_ + w / 52, cy_ + w / 52), 0, 180, fill=mixc("ochre", "kogecha", 0.3), width=SS * 2)
    d.ellipse((w * 0.2, w * 0.36, w * 0.72, w * 0.64), fill=C["crimson"], outline=C["ink"], width=SS * 5)
    d.polygon([(w * 0.7, w * 0.5), (w * 0.86, w * 0.36), (w * 0.86, w * 0.64)], fill=C["crimson"], outline=C["ink"])
    d.ellipse((w * 0.27, w * 0.45, w * 0.31, w * 0.49), fill=C["paper"]); d.ellipse((w * 0.28, w * 0.46, w * 0.3, w * 0.48), fill=C["ink"])
    for k in range(5): d.arc((w * (0.35 + 0.06 * k), w * 0.4, w * (0.45 + 0.06 * k), w * 0.6), 280, 80, fill=C["coral"], width=SS * 4)
    d.rectangle((0, 0, w - 1, w - 1), outline=C["pink"], width=int(w * 0.04))
    sol_save(im, "sol_mojing.png", (1024, 1024))
    # 天青花纹柱（一格 1 米）
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["teal"])
        for ox in range(3):
            for oy in range(3):
                X, Y = ox * w, oy * h
                d.line([(X + w * 0.5 + w * 0.3 * math.sin(t / 10 * math.pi * 2), Y + h * t / 10) for t in range(11)], fill=C["green"], width=SS * 5)
                for q in range(3): petal_flower(d, X + w * (0.3 + 0.2 * q), Y + h * (0.2 + 0.3 * q), w * 0.08, 5, [C["pink"], C["ochre"], C["coral"]][q], inner=C["paper"])
    tiled((256, 256), f).save(OUT / "sol_pillar.png")
    # 粉红墙：小花菱撒点
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["pink"])
        for i in range(12):
            for j in range(12): hanabishi(d, w * i / 4 + (w / 8 if j % 2 else 0), h * j / 4, w * 0.05, C["lavender"], C["coral"])
    tiled((512, 512), f).save(OUT / "sol_wall_pink.png")
    # 红白漩涡板（参考 1540 窗下那一排）
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"]); r2 = np.random.default_rng(109)
        for _ in range(30):
            x, y = r2.uniform(0, w * 3), r2.uniform(0, h * 3); spiral(d, x, y, r2.uniform(40, 90) * SS, 1.6, SS * 12, [C["coral"], C["crimson"]][r2.integers(2)])
        for k in range(9): d.line((0, h * k / 3 + h * 0.15, w * 3, h * k / 3 + h * 0.15), fill=C["teal"], width=SS * 4)
    tiled((512, 512), f).save(OUT / "sol_panel.png")
    # 舱门（一扇）：粉红框、天青心、柠黄金具
    for name, core in (("sol_panel_door", C["teal"]), ("sol_door", C["lavender"])):
        w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), C["pink"]); d = ImageDraw.Draw(im)
        d.rectangle((w * 0.12, h * 0.08, w * 0.88, h * 0.62), fill=core, outline=C["crimson"], width=SS * 4)
        d.rectangle((w * 0.12, h * 0.68, w * 0.88, h * 0.92), fill=C["paper"], outline=C["crimson"], width=SS * 4)
        hanabishi(d, w * 0.5, h * 0.35, w * 0.2, C["ochre"], C["crimson"]); d.ellipse((w * 0.78, h * 0.45, w * 0.86, h * 0.5), fill=C["ochre"])
        sol_save(im, f"{name}.png", (256, 496))
    # 白障子（尽头）
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    for k in range(1, 4): d.line((w * k / 4, 0, w * k / 4, h), fill=C["pink"], width=SS * 2)
    for k in range(1, 8): d.line((0, h * k / 8, w, h * k / 8), fill=C["pink"], width=SS * 2)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["crimson"], width=int(w * 0.06)); sol_save(im, "sol_shoji.png", (256, 496))
    # 格子窗（参考 1540 凤凰画两边）：深色细格，格里透出天青
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), C["ink"]); d = ImageDraw.Draw(im)
    for i in range(7):
        for j in range(13): d.rectangle((w * (0.08 + 0.12 * i), h * (0.06 + 0.068 * j), w * (0.08 + 0.12 * i) + w * 0.08, h * (0.06 + 0.068 * j) + h * 0.045), fill=mixc("teal", "navy", 0.3))
    d.rectangle((0, 0, w - 1, h - 1), outline=C["pink"], width=int(w * 0.06)); sol_save(im, "sol_lattice.png", (256, 496))
    # 凤凰画（占位）：纸白底，一只柠黄焦茶的鸟
    w, h = 768 * SS, 512 * SS; im = Image.new("RGB", (w, h), mixc("paper", "ochre", 0.15)); d = ImageDraw.Draw(im)
    d.ellipse((w * 0.35, h * 0.3, w * 0.62, h * 0.72), fill=C["ochre"], outline=C["kogecha"], width=SS * 4)
    d.ellipse((w * 0.52, h * 0.18, w * 0.66, h * 0.36), fill=C["ochre"], outline=C["kogecha"], width=SS * 4)
    for k in range(7): d.arc((w * (0.1 + 0.03 * k), h * (0.4 + 0.02 * k), w * (0.45 + 0.02 * k), h * (0.95 - 0.01 * k)), 180, 300, fill=[C["coral"], C["teal"], C["wisteria"]][k % 3], width=SS * 8)
    d.polygon([(w * 0.66, h * 0.26), (w * 0.72, h * 0.28), (w * 0.66, h * 0.3)], fill=C["crimson"])
    sol_save(im, "sol_houou.png", (768, 512))
    # 大幡三面（1:3）
    for k, (bg, kind) in enumerate(((C["teal"], "ju"), (C["coral"], "hana"), (C["navy"], "geo")), 1):
        w, h = 256 * SS, 768 * SS; im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
        for i in range(4):   # 下半菱格
            for j in range(10):
                x, y = w * (i + 0.5 * (j % 2)) / 4, h * (0.45 + 0.055 * j)
                d.polygon([(x, y - h * 0.027), (x + w * 0.12, y), (x, y + h * 0.027), (x - w * 0.12, y)], fill=[C["crimson"], C["green"], C["ochre"]][(i + j + k) % 3])
        if kind == "ju":
            d.rectangle((w * 0.1, h * 0.05, w * 0.9, h * 0.38), fill=C["paper"])
            try:
                from PIL import ImageFont
                fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", int(w * 0.62)); d.text((w * 0.5, h * 0.215), "寿", fill=C["ink"], font=fnt, anchor="mm")
            except Exception: pass
        elif kind == "hana": hanabishi(d, w * 0.5, h * 0.2, w * 0.36, C["paper"], C["crimson"]); hanabishi(d, w * 0.5, h * 0.2, w * 0.18, C["ochre"], C["teal"])
        else:
            for q in range(5): r_ = w * (0.38 - 0.07 * q); d.ellipse((w * 0.5 - r_, h * 0.2 - r_, w * 0.5 + r_, h * 0.2 + r_), outline=[C["ochre"], C["pink"]][q % 2], width=SS * 8)
        d.rectangle((0, 0, w - 1, h - 1), outline=C["ochre"], width=SS * 6)
        sol_save(im, f"sol_hata{k}.png", (256, 768))
    # 红漩涡帆（参考 1350）
    w = 512 * SS; im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    for q in range(7): spiral(d, w / 2, w / 2, w * (0.46 - 0.0 * q), 3.2, SS * 10, C["coral"] if q % 2 == 0 else C["ochre"]) if q == 0 else None
    spiral(d, w / 2, w / 2, w * 0.44, 3.0, SS * 14, C["ochre"]); spiral(d, w / 2, w / 2, w * 0.4, 3.0, SS * 6, C["coral"])
    for k in range(1, 4): d.line((0, w * k / 4, w, w * k / 4), fill=mixc("crimson", "ink", 0.3), width=SS * 3)
    sol_save(im, "sol_sail.png", (512, 512))
    # 贴满札的墙（参考 p5_0428）：土色墙上一排排纸札，札上眼睛 / 漩涡
    w, h = 1024 * SS, 600 * SS; im = Image.new("RGB", (w, h), mixc("ochre", "kogecha", 0.25)); d = ImageDraw.Draw(im); r2 = np.random.default_rng(113)
    for row in range(2):
        for k in range(7):
            x, y = w * (0.03 + 0.138 * k) + r2.uniform(-8, 8) * SS, h * (0.06 + 0.48 * row) + r2.uniform(-6, 6) * SS; fw, fh = w * 0.1, h * 0.4
            d.rectangle((x, y, x + fw, y + fh), fill=C["paper"], outline=mixc("paper", "ink", 0.3))
            if (k + row) % 2: d.ellipse((x + fw * 0.2, y + fh * 0.2, x + fw * 0.8, y + fh * 0.36), outline=C["ink"], width=SS * 4); d.ellipse((x + fw * 0.42, y + fh * 0.24, x + fw * 0.58, y + fh * 0.32), fill=C["ink"])
            else: spiral(d, x + fw * 0.5, y + fh * 0.28, fw * 0.3, 2.0, SS * 4, C["ink"])
            for q in range(3): d.line((x + fw * 0.2, y + fh * (0.5 + 0.12 * q), x + fw * 0.8, y + fh * (0.5 + 0.12 * q)), fill=C["ink"], width=SS * 5)
    sol_save(im, "sol_fuda.png", (1024, 600))
    # 楼梯地毯：紫绿大花
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["wisteria"])
        for i in range(9):
            for j in range(9): petal_flower(d, w * i / 3 + (w / 6 if j % 2 else 0), h * j / 3, w * 0.13, 6, C["green"] if (i + j) % 2 else C["lavender"], inner=C["ochre"], ratio=0.5)
    tiled((512, 512), f).save(OUT / "sol_carpet.png")
    # 船楼板：粉红 / 天青 / 柠黄格子板（一格 1 米）
    w = 512 * SS; im = Image.new("RGB", (w, w), C["pink"]); d = ImageDraw.Draw(im)
    for i in range(3):
        for j in range(3): d.rectangle((w * i / 3 + w * 0.02, w * j / 3 + w * 0.02, w * (i + 1) / 3 - w * 0.02, w * (j + 1) / 3 - w * 0.02), fill=[C["teal"], C["ochre"], C["lavender"]][(i + 2 * j) % 3], outline=C["crimson"], width=SS * 3)
    sol_save(im, "sol_tower.png", (512, 512))
    # 提灯：红 / 白
    for name, base, band in (("sol_lantern_r", C["crimson"], C["coral"]), ("sol_lantern_w", C["paper"], C["pink"])):
        def f(d, w, h, im, base=base, band=band):
            d.rectangle((0, 0, w * 3, h * 3), fill=base)
            for k in range(24): y = h * k / 8; d.line((0, y, w * 3, y), fill=band, width=SS * 2)
        tiled((256, 256), f).save(OUT / f"{name}.png")


def sol_from_scenes():
    """そらりす丸出的五张（scenes/51~55，游33，11-06 用户确认花积分）→ 贴图。55 是场景线自己出的版式图，切成三面大幡和一条船身花纹（自动找色块）"""
    def bg_mask(a):   # 和纸底（浅米色）以外的像素
        return ~((a[..., 0] > 205) & (a[..., 1] > 195) & (a[..., 2] > 170) & (np.abs(a[..., 0].astype(int) - a[..., 2].astype(int)) < 60))
    jobs = (("51_そらりす丸_雾海全景", "sol_sky.jpg", (3840, 1920)), ("52_そらりす丸_金云海全景", "sol_sky_color.jpg", (3840, 1920)),
            ("53_そらりす丸_鱼纹藻井", "sol_mojing.jpg", (1024, 1024)), ("54_そらりす丸_凤凰画", "sol_houou.jpg", (2048, 1120)))
    for sid, name, size in jobs:
        src = SC / f"{sid}.png"
        if src.exists(): Image.open(src).convert("RGB").resize(size, Image.LANCZOS).save(OUT / name, quality=88); print("→", name)
    src = SC / "55_そらりす丸_大幡和船身.png"
    if not src.exists(): return
    im = Image.open(src).convert("RGB"); a = np.asarray(im); H, W = a.shape[:2]; m = bg_mask(a)
    top = m[int(H * 0.2):int(H * 0.5)]; cols = top.mean(0) > 0.6   # 三面幡：上半截里大部分不是纸底的列
    segs, x = [], 0
    while x < W:
        if cols[x]:
            x0 = x
            while x < W and cols[x]: x += 1
            if x - x0 > W * 0.05: segs.append((x0, x))
        x += 1
    for k, (x0, x1) in enumerate(segs[:3], 1):
        rows = m[:int(H * 0.66), x0:x1].mean(1) > 0.9
        ys = np.where(rows)[0]; y0, y1 = ys.min(), ys.max(); y0 += int((y1 - y0) * 0.06)   # 去掉顶上挂杆那一截
        im.crop((x0 + 4, y0 + 4, x1 - 4, y1 - 4)).resize((256, 768), Image.LANCZOS).save(OUT / f"sol_hata{k}.png"); print("→ sol_hata", k, (x0, y0, x1, y1))
    rows = m[:, int(W * 0.1):int(W * 0.9)].mean(1) > 0.95; ys = np.where(rows[int(H * 0.6):])[0] + int(H * 0.6)
    band = im.crop((0, ys.min(), W, ys.max())); band.resize((2048, 1024), Image.LANCZOS).save(OUT / "sol_hull.jpg", quality=88); print("→ sol_hull", band.size)


# ---------- 地下铁（游34）：大正摩登 ----------
def sub_set():
    from PIL import ImageFont
    font = lambda n: ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", n)
    cream, green, wine, brass = mixc("paper", "ochre", 0.12), mixc("green", "navy", 0.45), mixc("crimson", "ink", 0.35), C["ochre"]
    # 白瓷砖（一格 1 米：横 6 竖 4 块，细灰缝，偶尔一块旧一点）
    w = 512 * SS; im = Image.new("RGB", (w, w), cream); d = ImageDraw.Draw(im); r2 = np.random.default_rng(201)
    for i in range(6):
        for j in range(4):
            if r2.random() < 0.15: d.rectangle((w * i / 6, w * j / 4, w * (i + 1) / 6, w * (j + 1) / 4), fill=mixc("paper", "ochre", 0.22))
    for i in range(7): d.line((w * i / 6, 0, w * i / 6, w), fill=mixc("paper", "ink", 0.25), width=SS * 2)
    for j in range(5): d.line((0, w * j / 4, w, w * j / 4), fill=mixc("paper", "ink", 0.25), width=SS * 2)
    sol_save(im, "sub_tile.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), green); d = ImageDraw.Draw(im)
    for i in range(9): d.line((w * i / 8, 0, w * i / 8, w), fill=mixc("green", "ink", 0.6), width=SS * 2)
    for j in range(5): d.line((0, w * j / 4, w, w * j / 4), fill=mixc("green", "ink", 0.6), width=SS * 2)
    d.rectangle((0, 0, w, w * 0.04), fill=cream); sol_save(im, "sub_tile_green.png", (512, 512))
    # 站台水磨石、站台边、道砟、隧道口
    def terrazzo(name, base, dots, n, grid=None):
        def f(d, w, h, im):
            d.rectangle((0, 0, w * 3, h * 3), fill=base); r3 = np.random.default_rng(203)
            for _ in range(n):
                x, y, r = r3.uniform(0, w * 3), r3.uniform(0, h * 3), r3.uniform(1.5, 5) * SS; d.ellipse((x - r, y - r, x + r, y + r), fill=dots[r3.integers(len(dots))])
            if grid:
                for k in range(4): d.line((0, h * k, w * 3, h * k), fill=grid, width=SS * 2); d.line((w * k, 0, w * k, h * 3), fill=grid, width=SS * 2)
        tiled((512, 512), f).save(OUT / f"{name}.png")
    terrazzo("sub_floor", mixc("paper", "lavender", 0.35), [C["lavender"], mixc("paper", "ink", 0.3), C["paper"]], 2500, mixc("paper", "ink", 0.35))
    terrazzo("sub_edge", mixc("paper", "ink", 0.35), [mixc("paper", "ink", 0.5), mixc("paper", "ink", 0.2)], 1500)
    terrazzo("sub_ballast", mixc("ink", "kogecha", 0.3), [mixc("paper", "ink", 0.55), mixc("kogecha", "ink", 0.4), mixc("paper", "ink", 0.7)], 4000)
    w = 512 * SS; im = Image.new("RGB", (w, w), mixc("ink", "navy", 0.3)); d = ImageDraw.Draw(im)
    for j in range(8):
        for i in range(5): d.rectangle((w * (i + 0.5 * (j % 2)) / 4, w * j / 8, w * (i + 0.5 * (j % 2) + 1) / 4 - SS * 3, w * (j + 1) / 8 - SS * 3), outline=mixc("navy", "ink", 0.2), width=SS * 2)
    sol_save(im, "sub_tunnel.png", (512, 512))
    # 站名牌
    w, h = 1024 * SS, 300 * SS; im = Image.new("RGB", (w, h), cream); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["navy"], width=SS * 14); d.rectangle((0, h * 0.72, w, h * 0.78), fill=wine)
    d.text((w / 2, h * 0.38), "上 野", fill=C["navy"], font=font(int(h * 0.5)), anchor="mm"); d.text((w / 2, h * 0.88), "UYENO", fill=C["navy"], font=font(int(h * 0.12)), anchor="mm")
    sol_save(im, "sub_sign.png", (1024, 300))
    # 海报墙（占位）：瓷砖墙上三张竖海报，大正浪漫的女人剪影和花
    w, h = 2048 * SS // 2, 1120 * SS // 2; im = Image.new("RGB", (w, h), cream); d = ImageDraw.Draw(im)
    for k, (bg, fg) in enumerate(((C["teal"], C["pink"]), (wine, brass), (C["wisteria"], C["paper"]))):
        x0 = w * (0.06 + 0.31 * k); x1 = x0 + w * 0.26; y0, y1 = h * 0.08, h * 0.92
        d.rectangle((x0, y0, x1, y1), fill=bg, outline=C["ink"], width=SS * 4)
        cx = (x0 + x1) / 2; d.ellipse((cx - w * 0.04, y0 + h * 0.18, cx + w * 0.04, y0 + h * 0.34), fill=C["paper"])   # 脸
        d.polygon([(cx - w * 0.09, y1 - h * 0.08), (cx + w * 0.09, y1 - h * 0.08), (cx + w * 0.03, y0 + h * 0.34), (cx - w * 0.03, y0 + h * 0.34)], fill=fg)
        d.ellipse((cx - w * 0.06, y0 + h * 0.12, cx + w * 0.06, y0 + h * 0.24), fill=C["ink"])   # 头发
        for q in range(4): petal_flower(d, x0 + w * 0.04 + q * w * 0.06, y0 + h * 0.08, w * 0.02, 5, fg, inner=C["ochre"])
        d.rectangle((x0 + w * 0.02, y1 - h * 0.07, x1 - w * 0.02, y1 - h * 0.03), fill=C["paper"])
    sol_save(im, "sub_posters.png", (2048, 1120))
    # 车身（一格 = 车身高 2.6 米，横两扇窗）：下深红、窗带纸白、窗里黑、上深红、腰线黄铜
    w = 512 * SS; im = Image.new("RGB", (w, w), wine); d = ImageDraw.Draw(im)
    d.rectangle((0, w * 0.2, w, w * 0.52), fill=cream)
    for k in range(2): x0 = w * (0.08 + 0.5 * k); d.rectangle((x0, w * 0.24, x0 + w * 0.34, w * 0.48), fill=C["ink"], outline=C["kogecha"], width=SS * 5)
    d.rectangle((0, w * 0.55, w, w * 0.57), fill=brass); d.rectangle((0, w * 0.17, w, w * 0.19), fill=brass)
    sol_save(im, "sub_car_ext.png", (512, 512))
    # 车门（木门、上半窗黑）、普通木门（检票口、咖啡馆）
    for name, win in (("sub_car_door", C["ink"]), ("sub_door", mixc("teal", "paper", 0.5))):
        w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), mixc("kogecha", "crimson", 0.25)); d = ImageDraw.Draw(im)
        d.rectangle((w * 0.15, h * 0.08, w * 0.85, h * 0.42), fill=win, outline=brass, width=SS * 4)
        d.rectangle((w * 0.15, h * 0.5, w * 0.85, h * 0.9), outline=mixc("kogecha", "ink", 0.3), width=SS * 4)
        d.ellipse((w * 0.78, h * 0.52, w * 0.86, h * 0.56), fill=brass); d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 3)
        sol_save(im, f"{name}.png", (256, 496))
    # 车厢窗带（一格 1 米：一扇窗，窗外黑）、广告带
    w = 512 * SS; im = Image.new("RGB", (w, w), mixc("kogecha", "ochre", 0.25)); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.08, w * 0.12, w * 0.92, w * 0.82), fill=mixc("ink", "navy", 0.4), outline=mixc("kogecha", "ink", 0.2), width=SS * 8)
    d.line((w * 0.08, w * 0.47, w * 0.92, w * 0.47), fill=mixc("kogecha", "ink", 0.2), width=SS * 4)
    sol_save(im, "sub_car_wall.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), cream); d = ImageDraw.Draw(im)
    for row in range(2):
        for k in range(2):
            x0, y0 = w * (0.04 + 0.5 * k), w * (0.06 + 0.5 * row); bg = [C["teal"], wine, C["wisteria"], C["ochre"]][(row * 2 + k) % 4]
            d.rectangle((x0, y0, x0 + w * 0.42, y0 + w * 0.38), fill=bg, outline=brass, width=SS * 3)
            petal_flower(d, x0 + w * 0.12, y0 + w * 0.19, w * 0.07, 6, C["paper"], inner=C["pink"])
            for q in range(3): d.line((x0 + w * 0.24, y0 + w * (0.12 + 0.07 * q), x0 + w * 0.38, y0 + w * (0.12 + 0.07 * q)), fill=C["paper"], width=SS * 4)
    sol_save(im, "sub_ad.png", (512, 512))
    # 天花、地板
    def boards(name, base, line, n=6):
        def f(d, w, h, im):
            d.rectangle((0, 0, w * 3, h * 3), fill=base)
            for k in range(n * 3): y = h * k / n; d.line((0, y, w * 3, y), fill=line, width=SS * 2)
        tiled((512, 512), f).save(OUT / f"{name}.png")
    boards("sub_car_ceil", cream, mixc("paper", "ochre", 0.4), 3); boards("sub_car_floor", mixc("kogecha", "ink", 0.15), mixc("kogecha", "ink", 0.45), 8)
    boards("sub_ceil", cream, mixc("paper", "ink", 0.2), 2); boards("sub_cafe_ceil", C["kogecha"], mixc("kogecha", "ochre", 0.4), 3)
    # 黑白格地砖（一格 0.91 米 4×4）
    w = 512 * SS; im = Image.new("RGB", (w, w), cream); d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            if (i + j) % 2: d.rectangle((w * i / 4, w * j / 4, w * (i + 1) / 4, w * (j + 1) / 4), fill=C["ink"])
    sol_save(im, "sub_checker.png", (512, 512))
    # 咖啡馆墙：下深红 + 金细线；上纸白 + 新艺术藤蔓
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=wine)
        for k in range(12): d.line((w * k / 4, 0, w * k / 4, h * 3), fill=mixc("crimson", "ochre", 0.3), width=SS * 2)
    tiled((512, 512), f).save(OUT / "sub_wall_cafe.png")
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=cream)
        for ox in range(3):
            d.line([(ox * w + w * (0.5 + 0.3 * math.sin(t / 12 * math.pi * 2)), h * t / 12 * 3) for t in range(13)], fill=C["teal"], width=SS * 4)
            for q in range(4): petal_flower(d, ox * w + w * (0.3 + 0.4 * (q % 2)), h * (0.4 + 0.75 * q), w * 0.06, 5, C["pink"], inner=C["ochre"])
    tiled((512, 512), f).save(OUT / "sub_wall_cafe_up.png")
    # 彩色玻璃窗（一扇 256×496）：铅条几何花
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), C["lavender"]); d = ImageDraw.Draw(im); r4 = np.random.default_rng(207)
    for i in range(4):
        for j in range(8):
            d.rectangle((w * i / 4, h * j / 8, w * (i + 1) / 4, h * (j + 1) / 8), fill=[C["lavender"], C["teal"], C["ochre"], C["pink"], mixc("lavender", "paper", 0.5)][r4.integers(5)])
    petal_flower(d, w / 2, h * 0.3, w * 0.3, 8, C["crimson"], inner=C["ochre"], outline=C["ink"])
    for i in range(5): d.line((w * i / 4, 0, w * i / 4, h), fill=C["ink"], width=SS * 3)
    for j in range(9): d.line((0, h * j / 8, w, h * j / 8), fill=C["ink"], width=SS * 3)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["kogecha"], width=int(w * 0.05)); sol_save(im, "sub_stained.png", (256, 496))
    # 钟面、改札牌
    w = 256 * SS; im = Image.new("RGB", (w, w), cream); d = ImageDraw.Draw(im)
    for k in range(12): a = 2 * math.pi * k / 12; d.line((w / 2 + math.cos(a) * w * 0.36, w / 2 + math.sin(a) * w * 0.36, w / 2 + math.cos(a) * w * 0.44, w / 2 + math.sin(a) * w * 0.44), fill=C["ink"], width=SS * 5)
    d.line((w / 2, w / 2, w / 2, w * 0.2), fill=C["ink"], width=SS * 6); d.line((w / 2, w / 2, w * 0.68, w * 0.56), fill=C["ink"], width=SS * 8)
    sol_save(im, "sub_clock.png", (256, 256))
    w, h = 256 * SS, 120 * SS; im = Image.new("RGB", (w, h), cream); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["navy"], width=SS * 6); d.text((w / 2, h / 2), "改 札", fill=C["navy"], font=font(int(h * 0.6)), anchor="mm")
    sol_save(im, "sub_kaisatsu_sign.png", (256, 120))


def sub_set2():
    """地下铁第二版（11-06 按参考帧，assets/concept/ref/subway/，只看不裁）：灰褐纸底、做旧划痕，大面积墨黑和米灰；点色只有酒红座椅、芥黄车身红顶、紫色挂钟。
    覆盖第一版里同名的几张（sub_floor、sub_sign、sub_car_*、sub_ceil、sub_cafe_ceil），新加黑大理石、人影广告墙、美人画（占位）、酒红黑菱格布等"""
    from PIL import ImageFont
    font = lambda n: ImageFont.truetype("/System/Library/Fonts/Supplemental/Songti.ttc", n)
    beige, paperb, ink, wine, mustard, gold = "#C9BBA0", "#DCD1BC", "#26232C", "#7A2A35", "#C9A23C", "#B89A4E"
    def grunge(im, seed, amt=1.0):   # 做旧：几道细划痕、一些斑点
        d = ImageDraw.Draw(im); r = np.random.default_rng(seed); w, h = im.size
        for _ in range(int(40 * amt)):
            x, y = r.uniform(0, w), r.uniform(0, h); L = r.uniform(20, 120) * SS; a = r.uniform(-0.4, 0.4) + (math.pi / 2 if r.random() < 0.5 else 0)
            d.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=(255, 250, 240) if r.random() < 0.5 else (40, 36, 40), width=1)
        for _ in range(int(300 * amt)):
            x, y, rr = r.uniform(0, w), r.uniform(0, h), r.uniform(1, 3) * SS; d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=mixc(beige, "kogecha", r.uniform(0.2, 0.6)))
        return im
    def marble(name, base, vein, seed, size=512):
        w = size * SS; im = Image.new("RGB", (w, w), base); d = ImageDraw.Draw(im); r = np.random.default_rng(seed)
        for _ in range(14):
            x, y = r.uniform(0, w), r.uniform(0, w); pts = [(x, y)]
            for _ in range(10): x += r.uniform(-60, 60) * SS; y += r.uniform(10, 70) * SS; pts.append((x, y))
            d.line(pts, fill=vein, width=int(r.uniform(1, 3) * SS))
        sol_save(grunge(im, seed, 0.5), f"{name}.png", (size, size))
    marble("sub_marble_black", ink, mixc(ink, "paper", 0.45), 301); marble("sub_ceil", mixc(ink, "kogecha", 0.2), mixc(ink, "paper", 0.35), 303)
    marble("sub_stone_gray", "#8E877B", "#B3AC9F", 305)
    # 站台地面：米灰石板、划痕
    w = 512 * SS; im = Image.new("RGB", (w, w), "#BDB3A2"); d = ImageDraw.Draw(im)
    for k in range(3): d.line((0, w * k / 2, w, w * k / 2), fill="#8E877B", width=SS * 3); d.line((w * k / 2, 0, w * k / 2, w), fill="#8E877B", width=SS * 3)
    sol_save(grunge(im, 307), "sub_floor.png", (512, 512))
    # 站名牌（参考 p10_0216）：米白板、墨字从右往左写"駅寿福"，下面一行小字，左右黑底金线装饰板
    w, h = 1024 * SS, 300 * SS; im = Image.new("RGB", (w, h), ink); d = ImageDraw.Draw(im)
    for x0 in (0, w * 0.82):
        for k in range(4): d.arc((x0 + w * 0.01, h * (0.1 + 0.2 * k), x0 + w * 0.17, h * (0.4 + 0.2 * k)), 200, 340, fill=gold, width=SS * 2)
    d.rectangle((w * 0.2, h * 0.08, w * 0.8, h * 0.92), fill=paperb, outline=ink, width=SS * 8)
    jfont = lambda n: ImageFont.truetype("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", n)   # 宋体没有"駅""鉄"这两个日文字形，站名牌用日文明朝
    d.text((w * 0.5, h * 0.38), "駅寿福", fill=ink, font=jfont(int(h * 0.42)), anchor="mm")
    d.text((w * 0.5, h * 0.78), "駅寿福鉄下地", fill=ink, font=jfont(int(h * 0.15)), anchor="mm")
    sol_save(grunge(im, 309, 0.4), "sub_sign.png", (1024, 300))
    # 站台广告墙（参考 p11_0955）：浅紫灰底，拱廊下一排人影剪影（和服、洋装、学生、绅士），墨黑和淡紫
    w, h = 2048 * SS // 2, 1120 * SS // 2; im = Image.new("RGB", (w, h), "#B9AEBC"); d = ImageDraw.Draw(im); r = np.random.default_rng(311)
    for k in range(18):
        x = w * (0.03 + 0.055 * k) + r.uniform(-8, 8); hh = h * r.uniform(0.55, 0.72); col = [ink, "#A88FAE", "#8E7E92"][k % 3]
        d.ellipse((x - w * 0.012, h * 0.95 - hh, x + w * 0.012, h * 0.95 - hh + h * 0.06), fill=col)
        d.polygon([(x - w * 0.018, h * 0.95 - hh + h * 0.06), (x + w * 0.018, h * 0.95 - hh + h * 0.06), (x + w * (0.02 + 0.012 * (k % 2)), h * 0.95), (x - w * (0.02 + 0.012 * (k % 2)), h * 0.95)], fill=col)
        if k % 4 == 1: d.rectangle((x - w * 0.014, h * 0.95 - hh - h * 0.03, x + w * 0.014, h * 0.95 - hh + h * 0.005), fill=ink)   # 礼帽
    d.rectangle((0, h * 0.95, w, h), fill="#8E7E92")
    for k in range(5): x = w * k / 4; d.rectangle((x - w * 0.01, 0, x + w * 0.01, h), fill=ink); d.arc((x, -h * 0.25, x + w / 4, h * 0.35), 0, 180, fill=ink, width=SS * 5)
    sol_save(grunge(im, 313, 0.6), "sub_silhouette.png", (2048, 1120))
    # 车身：芥黄、窗黑、腰线墨（一格 = 车身高，两扇窗）
    w = 512 * SS; im = Image.new("RGB", (w, w), mustard); d = ImageDraw.Draw(im)
    for k in range(2): x0 = w * (0.08 + 0.5 * k); d.rectangle((x0, w * 0.22, x0 + w * 0.34, w * 0.5), fill=ink, outline=mixc(mustard, "kogecha", 0.5), width=SS * 5)
    d.rectangle((0, w * 0.55, w, w * 0.58), fill=mixc(mustard, "kogecha", 0.6)); d.rectangle((0, 0, w, w * 0.1), fill="#8C2F2F")
    sol_save(grunge(im, 315, 0.5), "sub_car_ext.png", (512, 512))
    # 车厢：米色板墙、黑玻璃窗带金线花角（一格 1 米）
    def gold_corners(d, x0, y0, x1, y1, r):
        for (cx, cy, a0) in ((x0, y0, 0), (x1, y0, 90), (x1, y1, 180), (x0, y1, 270)):
            d.arc((cx - r, cy - r, cx + r, cy + r), a0, a0 + 90, fill=gold, width=SS * 3)
    w = 512 * SS; im = Image.new("RGB", (w, w), beige); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.08, w * 0.1, w * 0.92, w * 0.86), fill=ink, outline=mixc(beige, "kogecha", 0.5), width=SS * 8); gold_corners(d, w * 0.12, w * 0.14, w * 0.88, w * 0.82, w * 0.09)
    sol_save(grunge(im, 317, 0.5), "sub_car_wall.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), beige); d = ImageDraw.Draw(im)
    for k in range(3): x0 = w * (0.05 + 0.33 * k); d.rectangle((x0, w * 0.1, x0 + w * 0.26, w * 0.45), fill=ink, outline=gold, width=SS * 3)
    sol_save(grunge(im, 319, 0.4), "sub_car_wall_up.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), mixc(beige, "kogecha", 0.25)); d = ImageDraw.Draw(im)
    for k in range(5): d.line((w * k / 4, 0, w * k / 4, w), fill=mixc(beige, "kogecha", 0.55), width=SS * 3)
    sol_save(grunge(im, 321, 0.4), "sub_car_koshi.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), "#D2C6AF"); d = ImageDraw.Draw(im)
    for k in range(4): d.line((0, w * k / 3, w, w * k / 3), fill="#BFB29A", width=SS * 2)
    sol_save(grunge(im, 323, 0.3), "sub_car_ceil.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), "#CFC3A8"); d = ImageDraw.Draw(im)
    for k in range(3): d.line((0, w * k / 2, w, w * k / 2), fill="#9C907A", width=SS * 4); d.line((w * k / 2, 0, w * k / 2, w), fill="#9C907A", width=SS * 4)
    sol_save(grunge(im, 325), "sub_car_floor.png", (512, 512))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), mixc(beige, "kogecha", 0.3)); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.12, h * 0.06, w * 0.88, h * 0.7), fill=ink, outline=gold, width=SS * 3); gold_corners(d, w * 0.16, h * 0.09, w * 0.84, h * 0.67, w * 0.14)
    d.rectangle((0, 0, w - 1, h - 1), outline=ink, width=SS * 4); sol_save(grunge(im, 327, 0.4), "sub_car_door.png", (256, 496))
    # 美人画（占位，参考 p11_0213 的感觉）：白发女子侧脸、一只黑猫
    w, h = 512 * SS, 420 * SS; im = Image.new("RGB", (w, h), "#2E3A52"); d = ImageDraw.Draw(im)
    d.ellipse((w * 0.25, h * 0.18, w * 0.6, h * 0.75), fill="#F1E9DA"); d.ellipse((w * 0.36, h * 0.3, w * 0.62, h * 0.82), fill="#F3DDD3")
    d.ellipse((w * 0.48, h * 0.62, w * 0.53, h * 0.66), fill="#B42A47")
    d.ellipse((w * 0.62, h * 0.45, w * 0.9, h * 0.9), fill=ink); d.polygon([(w * 0.66, h * 0.5), (w * 0.69, h * 0.38), (w * 0.72, h * 0.48)], fill=ink); d.polygon([(w * 0.8, h * 0.48), (w * 0.84, h * 0.38), (w * 0.86, h * 0.5)], fill=ink)
    for x_ in (0.71, 0.8): d.ellipse((w * x_, h * 0.58, w * (x_ + 0.04), h * 0.62), fill=gold)
    sol_save(grunge(im, 329, 0.4), "sub_bijin.png", (512, 420))
    # 酒红黑菱格布（参考 p11_1704）、咖啡馆天花、深色窗
    w = 512 * SS; im = Image.new("RGB", (w, w), ink); d = ImageDraw.Draw(im)
    for i in range(-1, 5):
        for j in range(-1, 5):
            if (i + j) % 2 == 0:
                cx, cy = w * (i + 0.5) / 4, w * (j + 0.5) / 4; d.polygon([(cx, cy - w / 8), (cx + w / 8, cy), (cx, cy + w / 8), (cx - w / 8, cy)], fill=wine)
    sol_save(grunge(im, 331, 0.5), "sub_harlequin.png", (512, 512))
    w = 512 * SS; im = Image.new("RGB", (w, w), mixc(ink, "kogecha", 0.3)); d = ImageDraw.Draw(im)
    for k in range(4): d.line((0, w * k / 3, w, w * k / 3), fill=ink, width=SS * 4)
    sol_save(grunge(im, 333, 0.4), "sub_cafe_ceil.png", (512, 512))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), mixc(ink, "navy", 0.3)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=gold, width=int(w * 0.05)); d.line((w / 2, 0, w / 2, h), fill=gold, width=SS * 3); d.line((0, h * 0.45, w, h * 0.45), fill=gold, width=SS * 3)
    sol_save(grunge(im, 335, 0.3), "sub_window_dark.png", (256, 496))
    # 咖啡馆黑白方格墙（参考 p11_1558，一格 1 米 6×6）、挂钟改紫色
    w = 512 * SS; im = Image.new("RGB", (w, w), paperb); d = ImageDraw.Draw(im)
    for i in range(6):
        for j in range(6):
            if (i + j) % 2: d.rectangle((w * i / 6, w * j / 6, w * (i + 1) / 6, w * (j + 1) / 6), fill=ink)
    sol_save(grunge(im, 337, 0.5), "sub_checker.png", (512, 512))
    w = 256 * SS; im = Image.new("RGB", (w, w), "#8E6FA8"); d = ImageDraw.Draw(im); d.ellipse((w * 0.08, w * 0.08, w * 0.92, w * 0.92), fill=paperb)
    for k in range(12): a = 2 * math.pi * k / 12; d.line((w / 2 + math.cos(a) * w * 0.32, w / 2 + math.sin(a) * w * 0.32, w / 2 + math.cos(a) * w * 0.4, w / 2 + math.sin(a) * w * 0.4), fill=ink, width=SS * 5)
    d.line((w / 2, w / 2, w / 2, w * 0.22), fill=ink, width=SS * 6); d.line((w / 2, w / 2, w * 0.68, w * 0.56), fill=ink, width=SS * 8)
    sol_save(im, "sub_clock.png", (256, 256))


def sub_set3():
    """地下铁的 act / 拾遗小物（游34，文案线 11-06）：旧报纸（角落一小块"女记者跳桥自尽"）、初乘券、女演员剧照"""
    from PIL import ImageFont
    jf = lambda n: ImageFont.truetype("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", n)
    w, h = 1100 * SS // 2, 800 * SS // 2; im = Image.new("RGB", (w, h), "#D8CDB4"); d = ImageDraw.Draw(im); r = np.random.default_rng(401)
    d.text((w * 0.97, h * 0.04), "毎朝日報", fill="#26232C", font=jf(int(h * 0.09)), anchor="ra")
    for col in range(14):   # 竖排的字行（用细线代替），从右往左
        x = w * (0.9 - 0.06 * col)
        for k in range(int(r.integers(3, 6))):
            y0 = h * r.uniform(0.18, 0.6); d.line((x, y0, x, y0 + h * r.uniform(0.1, 0.3)), fill="#5A5248", width=SS * 2)
    d.rectangle((w * 0.04, h * 0.66, w * 0.36, h * 0.96), outline="#26232C", width=SS * 2)   # 角落那一小块
    d.text((w * 0.2, h * 0.73), "婦人記者", fill="#26232C", font=jf(int(h * 0.06)), anchor="mm")
    d.text((w * 0.2, h * 0.83), "橋より身を投ぐ", fill="#26232C", font=jf(int(h * 0.045)), anchor="mm")
    sol_save(im, "sub_news.png", (1100, 800))
    w, h = 400 * SS // 2, 200 * SS // 2; im = Image.new("RGB", (w, h), "#E4D7B8"); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.04, h * 0.08, w * 0.96, h * 0.92), outline="#7A2A35", width=SS * 2)
    d.text((w * 0.5, h * 0.36), "初 乗", fill="#7A2A35", font=jf(int(h * 0.3)), anchor="mm"); d.text((w * 0.5, h * 0.72), "福寿駅 ─ 開通記念", fill="#26232C", font=jf(int(h * 0.13)), anchor="mm")
    sol_save(im, "sub_kippu.png", (400, 200))
    w, h = 300 * SS // 2, 450 * SS // 2; im = Image.new("RGB", (w, h), "#E8E0CE"); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.06, h * 0.05, w * 0.94, h * 0.8), fill="#8A8072")
    d.ellipse((w * 0.32, h * 0.15, w * 0.68, h * 0.48), fill="#E9DCCB"); d.ellipse((w * 0.26, h * 0.1, w * 0.74, h * 0.34), fill="#26232C")
    d.polygon([(w * 0.2, h * 0.8), (w * 0.8, h * 0.8), (w * 0.64, h * 0.48), (w * 0.36, h * 0.48)], fill="#7A2A35")
    d.text((w * 0.5, h * 0.9), "銀幕の花", fill="#26232C", font=jf(int(h * 0.06)), anchor="mm")
    sol_save(im, "sub_bromide.png", (300, 450))


def pri_set():
    """牢房（のっぺらぼう，游35，参考帧到之前按方案画）：暗灰泥墙、草席、暗泥地；记忆里的座敷是表现主义笔触的襖、金屏风；心象是能舞台——桧木板、老松镜板（占位）、白洲、五色揚幕"""
    def save(im, name, size): im.resize(size, Image.LANCZOS).save(OUT / name)
    rng = np.random.default_rng(501)
    w = 512 * SS; im = Image.new("RGB", (w, w), mixc("kogecha", "paper", 0.4)); d = ImageDraw.Draw(im)   # 灰褐泥墙（第一版太黑，牢栅看不出来，提亮）
    for _ in range(400):
        x, y, r = rng.uniform(0, w), rng.uniform(0, w), rng.uniform(3, 14) * SS; d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=mixc("kogecha", "paper", rng.uniform(0.25, 0.5)))
    save(im, "pri_wall.png", (512, 512))
    w, h = 512 * SS, 256 * SS; im = Image.new("RGB", (w, h), mixc("ochre", "kogecha", 0.45)); d = ImageDraw.Draw(im)   # 草席
    for k in range(60): y = h * k / 60; d.line((0, y, w, y), fill=mixc("ochre", "kogecha", 0.6 if k % 2 else 0.3), width=SS)
    for y0 in (0, h * 0.94): d.rectangle((0, y0, w, y0 + h * 0.06), fill=mixc("kogecha", "ink", 0.3))
    save(im, "pri_straw.png", (512, 256))
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=mixc("kogecha", "paper", 0.15)); r2 = np.random.default_rng(503)
        for _ in range(1500): x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(1, 4) * SS; d.ellipse((x - r, y - r, x + r, y + r), fill=mixc("kogecha", "ink", r2.uniform(0.1, 0.6)))
    tiled((512, 512), f).save(OUT / "pri_earth.png")
    def boards(name, base, line):
        def f(d, w, h, im):
            d.rectangle((0, 0, w * 3, h * 3), fill=base)
            for k in range(18): d.line((0, h * k / 6, w * 3, h * k / 6), fill=line, width=SS * 2)
        tiled((512, 512), f).save(OUT / f"{name}.png")
    boards("pri_boards", mixc("kogecha", "ochre", 0.3), mixc("kogecha", "ink", 0.3)); boards("pri_stage", mixc("ochre", "paper", 0.35), mixc("ochre", "kogecha", 0.4))
    boards("pri_ceil", mixc("kogecha", "paper", 0.2), mixc("kogecha", "ink", 0.3))
    # 表现主义笔触的襖（4 扇一幅，横向连续）：粗重的扭曲笔触，藤紫、珊瑚、山吹压在纸白上
    W, H = 2048, 990
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=mixc("paper", "lavender", 0.3)); r2 = np.random.default_rng(505)
        for _ in range(60):
            x, y = r2.uniform(0, w * 3), h + r2.uniform(0, h); col = [C["wisteria"], C["coral"], C["ochre"], C["ink"], C["teal"]][r2.integers(5)]
            pts = [(x, y)]
            for _ in range(8): x += r2.uniform(-60, 60) * SS / 2; y += r2.uniform(-50, 50) * SS / 2; pts.append((x, y))
            d.line(pts, fill=col, width=int(r2.uniform(6, 20) * SS / 2), joint="curve")
    tiled((W, H), f).save(OUT / "pri_fusuma.png")
    # 金屏风（暗金底、墨色枯枝）、红毡、门
    w, h = 2048 * SS // 2, 640 * SS // 2; im = Image.new("RGB", (w, h), mixc("ochre", "kogecha", 0.25)); d = ImageDraw.Draw(im)
    for k in range(5):
        x = w * (0.1 + 0.2 * k); pts = [(x, h)]
        for q in range(6): x += rng.uniform(-40, 40); pts.append((x, h * (1 - 0.15 * (q + 1))))
        d.line(pts, fill=C["ink"], width=SS * 6, joint="curve")
    save(im, "pri_byobu.png", (2048, 640))
    w = 256 * SS; im = Image.new("RGB", (w, w), C["crimson"]); d = ImageDraw.Draw(im)
    for k in range(12): d.line((0, w * k / 12, w, w * k / 12), fill=mixc("crimson", "ink", 0.2), width=SS)
    save(im, "pri_red.png", (256, 256))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), mixc("kogecha", "ink", 0.2)); d = ImageDraw.Draw(im)
    for k in range(1, 6): d.line((w * k / 6, 0, w * k / 6, h), fill=C["ink"], width=SS * 3)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["ink"], width=SS * 5); save(im, "pri_door.png", (256, 496))
    # 老松镜板（占位）：桧木板底上一株老松（萌葱针团、焦茶干），整面墙一幅
    w, h = 1024 * SS, 1200 * SS // 2; im = Image.new("RGB", (w, h), mixc("ochre", "paper", 0.3)); d = ImageDraw.Draw(im)
    for k in range(9): d.line((w * k / 8, 0, w * k / 8, h), fill=mixc("ochre", "kogecha", 0.3), width=SS * 2)
    d.line([(w * 0.45, h), (w * 0.5, h * 0.7), (w * 0.4, h * 0.5), (w * 0.55, h * 0.3)], fill=C["kogecha"], width=SS * 28, joint="curve")
    for (x, y, r) in ((0.25, 0.45, 0.16), (0.7, 0.35, 0.18), (0.5, 0.22, 0.14), (0.3, 0.25, 0.1), (0.78, 0.55, 0.12)):
        d.ellipse((w * (x - r), h * (y - r * 0.45), w * (x + r), h * (y + r * 0.45)), fill=C["green"], outline=mixc("green", "ink", 0.4), width=SS * 3)
    save(im, "pri_kagami.png", (1024, 600))
    # 白洲（白色小卵石）、五色揚幕
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["paper"]); r2 = np.random.default_rng(507)
        for _ in range(1800): x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(2, 6) * SS; d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=mixc("paper", "lavender", r2.uniform(0.2, 0.8)))
    tiled((512, 512), f).save(OUT / "pri_shirasu.png")
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), C["paper"]); d = ImageDraw.Draw(im)
    for k, col in enumerate((C["wisteria"], C["paper"], C["crimson"], C["ochre"], C["green"])): d.rectangle((w * k / 5, 0, w * (k + 1) / 5, h), fill=col)
    save(im, "pri_agemaku.png", (256, 496))


def pri_set2():
    """牢房第二版（11-06 按参考帧 assets/concept/ref/prison/，只看不裁）：现实是墨绿牢墙、浅褐木格子，佐佐木家绿框白壁满是梅枝小鸟；
    心象是金红婚礼间（红白条富士鹤屏风、金底大树鹿流水、彩色大花地毯、花卉横楣）、粉红梅花房、彩色手鞠白拉门；结尾灰木长廊尽头金紫云和松"""
    def save(im, name, size): im.resize(size, Image.LANCZOS).save(OUT / name)
    rng = np.random.default_rng(601)
    green_d, green, gold = "#2F4A3C", "#6E9A4E", "#D8B44A"
    w = 512 * SS; im = Image.new("RGB", (w, w), green_d); d = ImageDraw.Draw(im)   # 墨绿牢墙
    for _ in range(500):
        x, y, r = rng.uniform(0, w), rng.uniform(0, w), rng.uniform(3, 12) * SS; d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=mixc(green_d, "ink", rng.uniform(0.1, 0.5)))
    save(im, "pri_wall.png", (512, 512))
    def branches(d, w, h, X, Y, n, col, bloom, birds, r2):
        for _ in range(n):
            x, y = X + r2.uniform(0, w), Y + r2.uniform(0, h); pts = [(x, y)]
            for _ in range(5): x += r2.uniform(-50, 50) * SS; y += r2.uniform(-40, 10) * SS; pts.append((x, y))
            d.line(pts, fill=col, width=int(r2.uniform(3, 7) * SS), joint="curve")
            for (px, py) in pts[1:]:
                for _ in range(2): petal_flower(d, px + r2.uniform(-12, 12) * SS, py + r2.uniform(-12, 12) * SS, r2.uniform(5, 9) * SS, 5, bloom[r2.integers(len(bloom))], inner=C["ochre"])
        for _ in range(birds):
            bx, by = X + r2.uniform(0, w), Y + r2.uniform(0, h); d.ellipse((bx - 10 * SS, by - 6 * SS, bx + 10 * SS, by + 6 * SS), fill=C["kogecha"]); d.polygon([(bx + 8 * SS, by), (bx + 16 * SS, by - 3 * SS), (bx + 16 * SS, by + 2 * SS)], fill=C["ochre"])
    # 绿框白壁上的梅枝小鸟工笔（一格 1 米能平铺）
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=mixc("paper", "ochre", 0.15)); r2 = np.random.default_rng(603)
        for ox in range(3):
            for oy in range(3): branches(d, w, h, ox * w, oy * h, 2, C["kogecha"], [C["paper"], C["pink"], C["coral"]], 1, r2)
    tiled((512, 512), f).save(OUT / "pri_ume_wall.png")
    # 粉红梅花房（墙）：粉底、满墙红白梅
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["pink"]); r2 = np.random.default_rng(605)
        for ox in range(3):
            for oy in range(3): branches(d, w, h, ox * w, oy * h, 4, C["crimson"], [C["paper"], C["crimson"], C["coral"]], 0, r2)
    tiled((512, 512), f).save(OUT / "pri_ume_pink.png")
    # 粉格子拉门（一扇）
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), mixc("pink", "paper", 0.4)); d = ImageDraw.Draw(im)
    for k in range(1, 4): d.line((w * k / 4, 0, w * k / 4, h), fill=C["wisteria"], width=SS * 4)
    for k in range(1, 6): d.line((0, h * k / 6, w, h * k / 6), fill=C["wisteria"], width=SS * 4)
    d.rectangle((0, 0, w - 1, h - 1), outline=C["crimson"], width=int(w * 0.05)); save(im, "pri_pink_lattice.png", (256, 496))
    # 彩色手鞠白拉门（4 扇一幅，参考 p7_0955）
    W_, H_ = 2048 * SS // 2, 990 * SS // 2; im = Image.new("RGB", (W_, H_), C["paper"]); d = ImageDraw.Draw(im)
    for (x, y, r) in ((0.15, 0.45, 0.2), (0.42, 0.62, 0.14), (0.66, 0.4, 0.17), (0.88, 0.7, 0.1), (0.3, 0.15, 0.06), (0.78, 0.12, 0.07), (0.55, 0.88, 0.05)):
        cx, cy, rr = W_ * x, H_ * y, H_ * r; d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=C["teal"], outline=C["ink"], width=SS * 3)
        for k in range(8):
            a0 = 2 * math.pi * k / 8; col = [C["blue"], C["coral"], C["ochre"], C["green"], C["wisteria"], C["crimson"]][(k + int(x * 10)) % 6]
            d.pieslice((cx - rr, cy - rr, cx + rr, cy + rr), math.degrees(a0), math.degrees(a0) + 22, fill=col)
        d.ellipse((cx - rr * 0.35, cy - rr * 0.35, cx + rr * 0.35, cy + rr * 0.35), fill=C["paper"], outline=C["ink"], width=SS * 2)
    for k in range(1, 4): d.line((W_ * k / 4, 0, W_ * k / 4, H_), fill=C["ink"], width=SS * 4)
    save(im, "pri_temari.png", (2048, 990))
    # 金底大树、梅、鹿、流水（婚礼间两侧墙，M 整面一幅）
    W_, H_ = 1600 * SS // 2, 900 * SS // 2; im = Image.new("RGB", (W_, H_), gold); d = ImageDraw.Draw(im)
    for k in range(4): y = H_ * (0.7 + 0.07 * k); d.line([(x, y + 14 * SS * math.sin(x / 80)) for x in range(0, W_, 20)], fill=C["blue"], width=SS * 10)
    d.line([(W_ * 0.3, H_), (W_ * 0.28, H_ * 0.6), (W_ * 0.35, H_ * 0.35), (W_ * 0.3, 0)], fill=C["kogecha"], width=SS * 40, joint="curve")
    for k in range(6): d.line([(W_ * 0.32, H_ * (0.2 + 0.1 * k)), (W_ * (0.55 + 0.05 * (k % 2)), H_ * (0.1 + 0.1 * k))], fill=C["kogecha"], width=SS * 10)
    branches(d, W_ * 0.6, H_ * 0.6, W_ * 0.35, 0, 6, C["kogecha"], [C["paper"], C["pink"]], 2, rng)
    for (x, y) in ((0.72, 0.55), (0.85, 0.6)):   # 鹿
        cx, cy = W_ * x, H_ * y; d.ellipse((cx - 50 * SS, cy - 22 * SS, cx + 50 * SS, cy + 22 * SS), fill=mixc("ochre", "kogecha", 0.5))
        for dx in (-35, -15, 20, 40): d.line((cx + dx * SS, cy + 15 * SS, cx + dx * SS, cy + 70 * SS), fill=mixc("ochre", "kogecha", 0.6), width=SS * 6)
        d.line((cx + 45 * SS, cy - 10 * SS, cx + 70 * SS, cy - 50 * SS), fill=mixc("ochre", "kogecha", 0.5), width=SS * 12); d.ellipse((cx + 60 * SS, cy - 70 * SS, cx + 90 * SS, cy - 45 * SS), fill=mixc("ochre", "kogecha", 0.5))
    save(im, "pri_gold_tree.png", (1600, 900))
    # 红白条富士鹤屏风（婚礼间正面）
    W_, H_ = 2048 * SS // 2, 640 * SS // 2; im = Image.new("RGB", (W_, H_), C["paper"]); d = ImageDraw.Draw(im)
    for k in range(10):
        if k % 2: d.rectangle((W_ * k / 10, 0, W_ * (k + 1) / 10, H_), fill=C["crimson"])
    d.polygon([(W_ * 0.3, H_ * 0.85), (W_ * 0.5, H_ * 0.25), (W_ * 0.7, H_ * 0.85)], fill=C["blue"]); d.polygon([(W_ * 0.44, H_ * 0.43), (W_ * 0.5, H_ * 0.25), (W_ * 0.56, H_ * 0.43)], fill=C["paper"])
    for (x, y) in ((0.15, 0.4), (0.85, 0.35)):
        cx, cy = W_ * x, H_ * y; d.ellipse((cx - 40 * SS, cy - 18 * SS, cx + 40 * SS, cy + 18 * SS), fill=C["paper"], outline=C["ink"], width=SS * 2)
        d.line((cx + 30 * SS, cy - 5 * SS, cx + 55 * SS, cy - 60 * SS), fill=C["paper"], width=SS * 8); d.ellipse((cx + 48 * SS, cy - 72 * SS, cx + 64 * SS, cy - 58 * SS), fill=C["crimson"])
    save(im, "pri_fuji_byobu.png", (2048, 640))
    # 花卉横楣（红底彩色大花）、彩色大花地毯、金云天花
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=C["crimson"]); r2 = np.random.default_rng(607)
        for _ in range(40): x, y = r2.uniform(0, w * 3), r2.uniform(0, h * 3); petal_flower(d, x, y, r2.uniform(18, 32) * SS, 8, [C["teal"], C["blue"], C["ochre"], C["wisteria"]][r2.integers(4)], inner=C["paper"], ratio=0.5)
    tiled((512, 512), f).save(OUT / "pri_frieze.png")
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=gold); r2 = np.random.default_rng(609)
        for _ in range(30): x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(30, 60) * SS; d.ellipse((x - r, y - r, x + r, y + r), fill=C["crimson"])
        for _ in range(60): x, y = r2.uniform(0, w * 3), r2.uniform(0, h * 3); petal_flower(d, x, y, r2.uniform(20, 40) * SS, 8, [C["teal"], C["blue"], C["pink"], C["green"], C["wisteria"]][r2.integers(5)], inner=C["ochre"], ratio=0.55)
    tiled((512, 512), f).save(OUT / "pri_flower_carpet.png")
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill=gold); r2 = np.random.default_rng(611)
        for _ in range(40): spiral(d, r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(30, 70) * SS, 1.5, SS * 6, mixc("ochre", "kogecha", 0.3))
    tiled((512, 512), f).save(OUT / "pri_gold_ceiling.png")
    # 人物屏风（佐佐木家座敷，占位）：米底上几个小人物（和服），淡彩
    W_, H_ = 2048 * SS // 2, 640 * SS // 2; im = Image.new("RGB", (W_, H_), mixc("paper", "ochre", 0.25)); d = ImageDraw.Draw(im)
    for k in range(7):
        cx = W_ * (0.08 + 0.14 * k); col = [C["blue"], C["crimson"], C["wisteria"], C["green"]][k % 4]
        d.polygon([(cx - 30 * SS, H_ * 0.85), (cx + 30 * SS, H_ * 0.85), (cx + 15 * SS, H_ * 0.4), (cx - 15 * SS, H_ * 0.4)], fill=col); d.ellipse((cx - 12 * SS, H_ * 0.3, cx + 12 * SS, H_ * 0.4), fill=C["paper"]); d.ellipse((cx - 14 * SS, H_ * 0.25, cx + 14 * SS, H_ * 0.33), fill=C["ink"])
    for k in range(1, 6): d.line((W_ * k / 6, 0, W_ * k / 6, H_), fill=mixc("ochre", "kogecha", 0.4), width=SS * 3)
    save(im, "pri_jinbutsu.png", (2048, 640))
    # 结尾：天空金紫云、松、寺（长廊尽头 M 整面）、灰木板墙
    W_, H_ = 1024 * SS // 2, 1200 * SS // 2; im = Image.new("RGB", (W_, H_), gold); d = ImageDraw.Draw(im)
    for k in range(6): y = H_ * (0.08 + 0.12 * k); kumo(d, W_ * rng.uniform(0.2, 0.8), y, W_ * rng.uniform(0.4, 0.8), H_ * 0.05, C["wisteria"] if k % 2 else mixc("wisteria", "pink", 0.5), C["wisteria"])
    d.rectangle((W_ * 0.4, H_ * 0.55, W_ * 0.6, H_ * 0.75), fill=C["crimson"]); d.polygon([(W_ * 0.34, H_ * 0.56), (W_ * 0.66, H_ * 0.56), (W_ * 0.5, H_ * 0.45)], fill=C["navy"])
    for (x, y, r) in ((0.15, 0.62, 0.14), (0.85, 0.58, 0.16), (0.3, 0.8, 0.12), (0.72, 0.82, 0.13)): d.ellipse((W_ * (x - r), H_ * (y - r * 0.4), W_ * (x + r), H_ * (y + r * 0.4)), fill=C["green"], outline=mixc("green", "ink", 0.5), width=SS * 3)
    d.rectangle((0, H_ * 0.88, W_, H_), fill=C["teal"]); save(im, "pri_sky_end.png", (1024, 1200))
    def f(d, w, h, im):
        d.rectangle((0, 0, w * 3, h * 3), fill="#7E7A74")
        for k in range(18): d.line((w * k / 6, 0, w * k / 6, h * 3), fill="#5E5A56", width=SS * 2)
    tiled((512, 512), f).save(OUT / "pri_greywood.png")


def pri_set3():
    """牢房拾遗：婚帖（竖写几行，新娘名字那一行被墨涂掉）"""
    from PIL import ImageFont
    jf = lambda n: ImageFont.truetype("/System/Library/Fonts/ヒラギノ明朝 ProN.ttc", n)
    w, h = 480 * SS // 2, 320 * SS // 2; im = Image.new("RGB", (w, h), mixc("paper", "pink", 0.2)); d = ImageDraw.Draw(im)
    d.rectangle((w * 0.04, h * 0.06, w * 0.96, h * 0.94), outline=C["crimson"], width=SS * 3)
    for k, t in enumerate(("婚礼之儀", "佐々木和正", "", "右 目出度く")):
        x = w * (0.82 - 0.2 * k)
        if t: d.text((x, h * 0.5), "\n".join(t), fill=C["ink"], font=jf(int(h * 0.1)), anchor="mm", spacing=2)
    x = w * 0.42; d.rectangle((x - w * 0.05, h * 0.14, x + w * 0.05, h * 0.86), fill=C["ink"])   # 新娘名字涂掉
    im.resize((480, 320), Image.LANCZOS).save(OUT / "pri_kontei.png")


def pri_set4():
    """牢房第三版（11-06 用户"多还原原著场景"，参考帧只看不裁）：厨房的粉柜、青灰箱 / 红褐箱（白家纹）、绿竹筐、黑木板门、白格子窗；
    座敷的小格子窗；彩色梅林（p6_0922）的彩点地和天"""
    def save(im, name, size): im.resize(size, Image.LANCZOS).save(OUT / name)
    w = 512 * SS // 2; im = Image.new("RGB", (w, w), "#E7B8C3"); d = ImageDraw.Draw(im)   # 粉柜：粉底白卷云
    for (x, y, r) in ((0.25, 0.7, 0.12), (0.5, 0.75, 0.1), (0.75, 0.7, 0.12), (0.35, 0.3, 0.08), (0.68, 0.32, 0.09)):
        spiral(d, w * x, w * y, w * r, 1.6, SS * 4, C["paper"])
    save(im, "pri_pinkbox.png", (512, 512))
    def mon_box(name, base, line):
        w = 512 * SS // 2; im = Image.new("RGB", (w, w), base); d = ImageDraw.Draw(im)
        d.rectangle((0, 0, w - 1, w - 1), outline=mixc(base, "ink", 0.4), width=SS * 6)
        cx = cy = w / 2; r = w * 0.2; d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=line, width=SS * 7)
        for k in range(3):   # 白家纹：圆里三枚叶
            a = 2 * math.pi * k / 3 - math.pi / 2; d.ellipse((cx + math.cos(a) * r * 0.45 - r * 0.28, cy + math.sin(a) * r * 0.45 - r * 0.28, cx + math.cos(a) * r * 0.45 + r * 0.28, cy + math.sin(a) * r * 0.45 + r * 0.28), fill=line)
        save(im, name, (512, 512))
    mon_box("pri_tub.png", "#7F96A6", C["paper"]); mon_box("pri_chest.png", "#7A3A34", mixc("paper", "pink", 0.3))
    w = 256 * SS; im = Image.new("RGB", (w, w), "#5E8A4A"); d = ImageDraw.Draw(im)   # 绿竹筐：斜编格
    for k in range(-12, 13):
        x = w * k / 12; d.line((x, 0, x + w, w), fill=mixc("#5E8A4A", "ink", 0.35), width=SS * 3); d.line((x + w, 0, x, w), fill=mixc("#5E8A4A", "paper", 0.25), width=SS * 2)
    save(im, "pri_zaru.png", (256, 256))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), "#4B4642"); d = ImageDraw.Draw(im)   # 黑木板门：竖板 + 三道横档
    for k in range(1, 7): d.line((w * k / 7, 0, w * k / 7, h), fill="#2E2A28", width=SS * 2)
    for y in (0.12, 0.5, 0.88): d.rectangle((0, h * y - SS * 6, w, h * y + SS * 6), fill="#3A3532")
    d.rectangle((0, 0, w - 1, h - 1), outline="#2A2624", width=SS * 6); save(im, "pri_plank_door.png", (256, 496))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), "#F1EEE8"); d = ImageDraw.Draw(im)   # 白格子窗（障子）：灰框
    for k in range(1, 4): d.line((w * k / 4, 0, w * k / 4, h), fill="#7D7A76", width=SS * 3)
    for k in range(1, 8): d.line((0, h * k / 8, w, h * k / 8), fill="#7D7A76", width=SS * 3)
    d.rectangle((0, 0, w - 1, h - 1), outline="#5E5A56", width=SS * 6); save(im, "pri_shoji_white.png", (256, 496))
    w, h = 256 * SS, 496 * SS; im = Image.new("RGB", (w, h), "#ECE8DE"); d = ImageDraw.Draw(im)   # 座敷的小格子窗：白底、青灰竖格
    for k in range(1, 9): d.rectangle((w * k / 9 - SS * 4, 0, w * k / 9 + SS * 4, h), fill="#6F8496")
    d.rectangle((0, 0, w - 1, h - 1), outline="#6E9A4E", width=SS * 10); save(im, "pri_koshi_win.png", (256, 496))
    pastel = ["#F3C6CF", "#C9D7EE", "#F5E6A8", "#D8C6EA", "#CFE6D2", "#F6D9B8"]
    splat = ["#C8324A", "#3E6FB8", "#E58AA0", "#7A5AA8", "#2E8C8A", "#E8B23A"]
    def f(d, w, h, im):   # 彩点地：粉彩大色块 + 小溅点
        d.rectangle((0, 0, w * 3, h * 3), fill="#F2E4DA"); r2 = np.random.default_rng(701)
        for _ in range(120): x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(30, 90) * SS; d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=pastel[r2.integers(len(pastel))])
        for _ in range(500): x, y, r = r2.uniform(0, w * 3), r2.uniform(0, h * 3), r2.uniform(2, 7) * SS; d.ellipse((x - r, y - r, x + r, y + r), fill=splat[r2.integers(len(splat))])
    tiled((512, 512), f).save(OUT / "pri_yume_ground.png")
    W_, H_ = 2048, 1024; im = Image.new("RGB", (W_, H_), "#F4E9D8"); d = ImageDraw.Draw(im); r2 = np.random.default_rng(703)   # 天：等距柱状，左右接缝（每笔左右各画一遍）
    for k in range(H_):
        t = k / H_; c = mixc("#CFE0F0", "#F7E7C4", min(1, t * 1.6)) if t < 0.5 else mixc("#F7E7C4", "#F2C9CF", (t - 0.5) * 2); d.line((0, k, W_, k), fill=c)
    def both(fn, x, *a):
        for ox in (-W_, 0, W_): fn(x + ox, *a)
    for _ in range(260):   # 粉彩大笔触
        x, y = r2.uniform(0, W_), r2.uniform(H_ * 0.15, H_ * 0.85); ww, hh = r2.uniform(60, 220), r2.uniform(14, 40); col = pastel[r2.integers(len(pastel))]
        both(lambda xx, yy, a, b, c_: d.ellipse((xx - a, yy - b, xx + a, yy + b), fill=c_), x, y, ww, hh, col)
    for _ in range(1600):   # 溅点
        x, y, r = r2.uniform(0, W_), r2.uniform(H_ * 0.1, H_ * 0.95), r2.uniform(1.5, 6); col = splat[r2.integers(len(splat))]
        both(lambda xx, yy, rr, c_: d.ellipse((xx - rr, yy - rr, xx + rr, yy + rr), fill=c_), x, y, r, col)
    im.save(OUT / "pri_yume_sky.jpg", quality=88)


def pri_from_scenes():
    """牢房出的八张（scenes/80~87，游35，11-06 用户确认花积分）→ 贴图。82 是两块方的花样（左地毯、右横楣），按纸底切开再做成能平铺"""
    def seamless(im):
        a = np.asarray(im, float); h, w = a.shape[:2]
        b = np.roll(np.roll(a, w // 2, 1), h // 2, 0)
        yy, xx = np.mgrid[0:h, 0:w]; m = np.clip(np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / (0.22 * w), 0, 1)[..., None]
        return Image.fromarray((a * m + b * (1 - m)).astype(np.uint8))
    jobs = (("80_牢房_金底大树鹿流水墙", "pri_gold_tree.jpg", (2048, 944)), ("81_牢房_富士鹤屏风", "pri_fuji_byobu.jpg", (2048, 683)),
            ("83_牢房_粉墙红白梅", "pri_ume_mural.jpg", (2048, 944)), ("84_牢房_手鞠白拉门", "pri_temari.jpg", (2048, 683)),
            ("85_牢房_梅枝小鸟工笔壁", "pri_kacho.jpg", (2048, 683)), ("86_牢房_人物屏风", "pri_jinbutsu.jpg", (2048, 853)),
            ("87_牢房_结尾金紫云松寺天空", "pri_sky_end.jpg", (1024, 1170)))
    for sid, name, size in jobs:
        src = SC / f"{sid}.png"
        if src.exists(): Image.open(src).convert("RGB").resize(size, Image.LANCZOS).save(OUT / name, quality=88); print("→", name)
        else: print("还没有", src.name)
    src = SC / "82_牢房_大花地毯和花卉横楣.png"
    if not src.exists(): print("还没有", src.name); return
    im = Image.open(src).convert("RGB"); a = np.asarray(im); H, W = a.shape[:2]
    paper = (a[..., 0] > 200) & (a[..., 1] > 190) & (a[..., 2] > 165) & (np.abs(a[..., 0].astype(int) - a[..., 2].astype(int)) < 60)
    cols = (~paper).mean(0) > 0.5; segs, x = [], 0
    while x < W:
        if cols[x]:
            x0 = x
            while x < W and cols[x]: x += 1
            if x - x0 > W * 0.2: segs.append((x0, x))
        x += 1
    if len(segs) < 2: segs = [(int(W * 0.03), int(W * 0.48)), (int(W * 0.52), int(W * 0.97))]; print("82 没切出两块，按比例切")
    for (x0, x1), name in zip(segs[:2], ("pri_flower_carpet.jpg", "pri_frieze.jpg")):
        rows = (~paper[:, x0:x1]).mean(1) > 0.5; ys = np.where(rows)[0]; y0, y1 = ys.min(), ys.max()
        m_ = int(min(x1 - x0, y1 - y0) * 0.03)
        seamless(im.crop((x0 + m_, y0 + m_, x1 - m_, y1 - m_)).resize((1024, 1024), Image.LANCZOS)).save(OUT / name, quality=88); print("→", name, (x0, y0, x1, y1))


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
    wall_gray(); dotted("earth_dark", 0.74); goten_black(); panels_ybg()
    ink_set(); fue_set(); sol_set(); sol_from_scenes(); sub_set(); sub_set2(); sub_set3(); pri_set(); pri_set2(); pri_set3(); pri_set4(); pri_from_scenes()
    print("→", OUT)
