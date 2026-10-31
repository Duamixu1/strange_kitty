"""
游览版积木库：参数化积木 + 按文字平面图拼区块（格式见 docs/16_积木平面图格式.md）。

  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/kit_build.py                  大奥积木走廊（手写，不走平面图）
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/kit_build.py -- zashiki_demo  按 tools/kit_plans/zashiki_demo.txt 拼
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/kit_build.py -- all           kit_plans 里的全部
  → assets/processed/kit/<名字>.glb；平面图区块另出 web/src/data/tour/<名字>_walk.json（可走格子 + 出生点、观景点、楼梯口、验收机位）

写法：所有积木都是参数化函数，按游戏坐标（y 向上，单位米）往"每种材质一个网格"里加面，最后每种材质出一个物体，
材质名 kit_<key>，网页按 key 换成卡通材质（web/src/tour/kit.js）。贴图不进 GLB，UV 按米排或每块 0..1，
一格多少米和 tools/kit_textures.py 对应（TILE）。v 向上 = 贴图向上。
大奥走廊：长 13.2、高 5.5 和 web/src/world/cameras.json 的走廊一致；宽按泼溅走廊实测的 5 米（walkmap 可走 ±1.9，墙在 ±2.5）。
"""
import json, math, sys
from collections import Counter
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/processed/kit"
OUT.mkdir(parents=True, exist_ok=True)
PLANS = ROOT / "tools/kit_plans"
WALK_OUT = ROOT / "web/src/data/tour"

TILE = {"carpet": 1.2, "boards": 0.91, "drape": (0.36, 0.72), "chochin_h": 0.5}
W, L, H = 5.0, 13.2, 5.5          # 走廊宽、长、高（泼溅走廊墙面实际在 ±2.5 左右，按它来，不按 cameras.json 写的 6 米）
XW = W / 2                         # 墙面 x
BAYS = 5                           # 柱间数
BAY = L / BAYS

# ---------------------------------------------------------------- 网格累加器
G = {}   # key → {"v": [Vector], "f": [[idx]], "uv": [[(u,v)]]}


def acc(key):
    return G.setdefault(key, {"v": [], "f": [], "uv": []})


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def face(key, pts, uvs, want=None):
    """加一个面（游戏坐标）。want 给了就保证法线朝那边，不对就翻转顶点顺序"""
    pts = [V(p) for p in pts]
    if want is not None:
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if n.dot(V(want)) < 0: pts, uvs = pts[::-1], uvs[::-1]
    g = acc(key); i0 = len(g["v"])
    g["v"].extend(pts); g["f"].append(list(range(i0, i0 + len(pts)))); g["uv"].append(list(uvs))


def strip(key, rows, uvs, want=None):
    """rows: [[左点, 右点], ...] 连成一条带，共用顶点（平滑着色）。want(i) 返回第 i 段该朝的方向"""
    g = acc(key); i0 = len(g["v"])
    for a, b in rows: g["v"].extend([V(a), V(b)])
    for i in range(len(rows) - 1):
        q = [i0 + 2 * i, i0 + 2 * i + 1, i0 + 2 * i + 3, i0 + 2 * i + 2]
        u = [uvs[i][0], uvs[i][1], uvs[i + 1][1], uvs[i + 1][0]]
        if want is not None:
            p = [g["v"][k] for k in q]
            if (p[1] - p[0]).cross(p[2] - p[0]).dot(V(want(i))) < 0: q, u = q[::-1], u[::-1]
        g["f"].append(q); g["uv"].append(u)


def box(key, c, s, uv="m", tile=1.0):
    """长方体：中心 c、尺寸 s。uv='m' 每面按米 / tile 排，uv='unit' 每面 0..1"""
    c, s = V(c), V(s) / 2
    for ax in range(3):
        for sg in (-1, 1):
            n = V(0, 0, 0); n[ax] = sg
            a1, a2 = [k for k in range(3) if k != ax]
            pts, uvs = [], []
            for (p, q) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                o = V(0, 0, 0); o[ax] = sg * s[ax]; o[a1] = p * s[a1]; o[a2] = q * s[a2]
                pts.append(c + o)
                if uv == "unit": uvs.append(((p + 1) / 2, (q + 1) / 2))
                else: uvs.append(((c + o)[a1 if a1 != 1 else a2] / tile, (c + o)[a2 if a1 != 1 else a1] / tile))
            face(key, pts, uvs, want=n)


def cylinder(key, c, r, h, seg=16, caps=True, uv_h=None):
    """竖直圆柱：底面中心 c。侧面 u 绕一圈 0..1，v 按高度 / uv_h"""
    c = V(c); uv_h = uv_h or h
    rows, uvs = [], []
    for i in range(seg + 1):
        a = 2 * math.pi * i / seg
        d = V(math.cos(a) * r, 0, math.sin(a) * r)
        rows.append([c + d, c + d + V(0, h, 0)]); uvs.append([(i / seg, 0), (i / seg, h / uv_h)])
    strip(key, rows, uvs, want=None)
    # 方向：按上面的顺序，法线朝外（逆时针看外侧）；检查第一段
    g = G[key]; f = g["f"][-1]; p = [g["v"][k] for k in f]
    mid = sum(p, V(0, 0, 0)) / 4
    if (p[1] - p[0]).cross(p[2] - p[0]).dot(mid - (c + V(0, h / 2, 0))) < 0:
        for k in range(len(g["f"]) - seg, len(g["f"])): g["f"][k] = g["f"][k][::-1]; g["uv"][k] = g["uv"][k][::-1]
    if caps:
        for y, n in ((0, -1), (h, 1)):
            pts = [c + V(math.cos(2 * math.pi * i / seg) * r, y, math.sin(2 * math.pi * i / seg) * r) for i in range(seg)]
            face(key, pts, [(0.5 + 0.5 * math.cos(2 * math.pi * i / seg), 0.5 + 0.5 * math.sin(2 * math.pi * i / seg)) for i in range(seg)], want=(0, n, 0))


def cone(key, c, r0, r1, h, seg=12):
    c = V(c)
    rows = [[c + V(math.cos(2 * math.pi * i / seg) * r0, 0, math.sin(2 * math.pi * i / seg) * r0),
             c + V(math.cos(2 * math.pi * i / seg) * r1, h, math.sin(2 * math.pi * i / seg) * r1)] for i in range(seg + 1)]
    g = acc(key); n0 = len(g["f"])
    strip(key, rows, [[(i / seg, 0), (i / seg, 1)] for i in range(seg + 1)])
    for k in range(n0, len(g["f"])):
        p = [g["v"][j] for j in g["f"][k]]; mid = sum(p, V(0, 0, 0)) / 4
        out = V(mid.x - c.x, 0, mid.z - c.z)
        if (p[1] - p[0]).cross(p[2] - p[0]).dot(out) < 0: g["f"][k] = g["f"][k][::-1]; g["uv"][k] = g["uv"][k][::-1]


def sphere(key, c, r, seg=8, rings=5):
    c = V(c); g = acc(key); i0 = len(g["v"])
    for j in range(rings + 1):
        th = math.pi * j / rings
        for i in range(seg):
            ph = 2 * math.pi * i / seg
            g["v"].append(c + V(math.sin(th) * math.cos(ph) * r, math.cos(th) * r, math.sin(th) * math.sin(ph) * r))
    for j in range(rings):
        for i in range(seg):
            a, b = i0 + j * seg + i, i0 + j * seg + (i + 1) % seg
            q = [a, a + seg, b + seg, b]
            p = [g["v"][k] for k in q]; mid = sum(p, V(0, 0, 0)) / 4
            if (p[1] - p[0]).cross(p[2] - p[0]).length > 1e-12 and (p[1] - p[0]).cross(p[2] - p[0]).dot(mid - c) < 0: q = q[::-1]
            if (p[2] - p[0]).cross(p[3] - p[0]).length < 1e-12 and (p[1] - p[0]).cross(p[2] - p[0]).dot(mid - c) < 0: q = q[::-1]
            g["f"].append(q); g["uv"].append([(0, 0)] * 4)


def ribbon(key, path, width, facing, tile):
    """沿路径的布条。宽度方向 = 切线 × facing（facing 是布面该朝的方向），v 按弧长 / tile[1]"""
    facing = V(facing); rows, uvs, s = [], [], 0.0
    for i, p in enumerate(path):
        p = V(p)
        t = (V(path[min(i + 1, len(path) - 1)]) - V(path[max(i - 1, 0)])).normalized()
        w = t.cross(facing).normalized() * width / 2
        if i: s += (p - V(path[i - 1])).length
        rows.append([p - w, p + w]); uvs.append([(0, s / tile[1]), (width / tile[0], s / tile[1])])
    strip(key, rows, uvs, want=lambda i: facing)


def bezier(p0, p1, p2, n=24):
    p0, p1, p2 = V(p0), V(p1), V(p2)
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in (k / n for k in range(n + 1))]


def sag_curve(a, b, low, n=20):
    """两点间下垂的弧，最低点 y = low"""
    a, b = V(a), V(b); s = (a.y + b.y) / 2 - low
    return [a.lerp(b, t) - V(0, 4 * s * t * (1 - t), 0) for t in (k / n for k in range(n + 1))]


# ---------------------------------------------------------------- 积木
def floor_corridor():
    """廊板（两侧绿）+ 中间地毯：深红线 | 珊瑚边 | 绿线 | 花毯"""
    T = TILE["boards"]
    for sg in (-1, 1):
        x0, x1 = sorted((sg * 1.75, sg * XW))
        face("boards", [(x0, 0, 0), (x1, 0, 0), (x1, 0, -L), (x0, 0, -L)], [(x0 / T, 0), (x1 / T, 0), (x1 / T, L / T), (x0 / T, L / T)], want=(0, 1, 0))
        for (a, b, k, y) in ((1.70, 1.75, "crimson", 0.012), (1.25, 1.70, "coral", 0.012), (1.20, 1.25, "green", 0.014)):
            x0, x1 = sorted((sg * a, sg * b))
            box(k, ((x0 + x1) / 2, y / 2, -L / 2), (x1 - x0, y, L))
    box("carpet", (0, 0.009, -L / 2), (2.4, 0.018, L), tile=TILE["carpet"])


def mural_wall(side):
    """整面墙画：u 从观者左到右，v 从地到天花"""
    x = side * XW; n = (-side, 0, 0)
    us = (lambda z: -z / L) if side < 0 else (lambda z: (z + L) / L)
    pts = [(x, 0.12, 0), (x, 0.12, -L), (x, H, -L), (x, H, 0)]
    face("mural_L" if side < 0 else "mural_R", pts, [(us(p[2]), (p[1] - 0.12) / (H - 0.12)) for p in pts], want=n)
    box("ink", (x - side * 0.02, 0.06, -L / 2), (0.04, 0.12, L))                     # 墙脚墨线
    box("paper", (x - side * 0.06, 4.62, -L / 2), (0.12, 0.14, L))                   # 长押
    box("ochre", (x - side * 0.08, 5.4, -L / 2), (0.16, 0.2, L))                     # 天花下的横梁


def pillars(side):
    x = side * (XW - 0.1)
    for i in range(BAYS + 1):
        z = -i * BAY
        box("paper", (x, H / 2, z), (0.2, H, 0.2))
        box("crimson", (x, 0.08, z), (0.24, 0.16, 0.24))                             # 柱脚


def swags(side):
    """墙顶垂幔：每个柱间两层下垂的弧形布（山吹在后，纸白在前）"""
    x = side * XW
    for i in range(BAYS):
        z0, z1 = -i * BAY - 0.1, -(i + 1) * BAY + 0.1
        for (key, drop, out) in (("ochre", 1.15, 0.16), ("paper", 0.85, 0.3)):
            rows, uvs, n = [], [], 16
            for k in range(n + 1):
                t = k / n; z = z0 + (z1 - z0) * t; b = math.sin(math.pi * t)
                top = (x - side * 0.05, 5.3, z)
                bot = (x - side * (0.05 + out * b), 5.3 - (0.35 + drop * b), z)
                rows.append([bot, top]); uvs.append([(t, 0), (t, 1)])
            strip(key, rows, uvs, want=lambda i: (-side, 0, 0))


def chochin(c, key="chochin", k=1.0):
    """红提灯：上下墨色箍、纸身、底下流苏，吊绳到横梁。key 换灯身贴图（坂井家的家纹提灯 chochin_kamon），k 整体放大"""
    c = V(c); r, h = 0.17 * k, TILE["chochin_h"] * k
    cylinder(key, c, r, h, seg=16, caps=False, uv_h=h)
    cylinder("navy", c + V(0, -0.04 * k, 0), r * 0.82, 0.05 * k, seg=12)
    cylinder("navy", c + V(0, h - 0.01 * k, 0), r * 0.82, 0.05 * k, seg=12)
    cone("coral", c + V(0, -0.26 * k, 0), 0.0, 0.05 * k, 0.22 * k, seg=8)
    return c


def chochin_rows(side):
    """沿墙一排排吊挂：每柱间三串，中间那串三个、两边两个，高低错开"""
    x = side * (XW - 0.45)
    for i in range(BAYS):
        for j, f in enumerate((0.12, 0.31, 0.5, 0.69, 0.88)):
            z = -(i + f) * BAY
            n = 3 if j % 2 == 0 else 2
            top = 4.55 if j % 2 == 0 else 4.3
            for k in range(n): chochin((x, top - k * 0.62, z))
            box("ink", (x, (top + 0.5 + 5.3) / 2, z), (0.015, 5.3 - top - 0.5, 0.015))
            for k in range(n - 1): box("ink", (x, top - k * 0.62 - 0.07, z), (0.012, 0.12, 0.012))


def drapes(side):
    """藤紫幔：每根柱子顶上往两边斜垂到地，柱间再挂一道下垂的弧"""
    x = side * (XW - 0.22)
    face_to = (-side, 0, 0.0001)
    for i in range(BAYS + 1):
        z = -i * BAY
        for dz in (-1, 1):
            zt = z + dz * BAY * 0.42
            if zt > 0.01 or zt < -L - 0.01: continue
            path = bezier((x, 5.15, z), (x - side * 0.35, 1.6, z + dz * 0.25), (x - side * 0.12, 0.03, zt))
            ribbon("drape", path, 0.24, face_to, TILE["drape"])
    for i in range(BAYS):
        z0, z1 = -i * BAY, -(i + 1) * BAY
        ribbon("drape", sag_curve((x + side * 0.04, 5.05, z0), (x + side * 0.04, 5.05, z1), 2.9), 0.22, face_to, TILE["drape"])


def andon(c, side):
    """行灯：紫腿、藤紫底板、纸罩四面贴菱格、山吹上下框、藍色小屋顶"""
    c = V(c)
    for dx in (-0.2, 0.2):
        for dz in (-0.2, 0.2): box("navy", c + V(dx, 0.15, dz), (0.06, 0.3, 0.06))
    box("wisteria", c + V(0, 0.32, 0), (0.56, 0.05, 0.56))
    box("andon", c + V(0, 0.71, 0), (0.42, 0.72, 0.42), uv="unit")
    box("ochre", c + V(0, 0.36, 0), (0.48, 0.05, 0.48))
    box("ochre", c + V(0, 1.08, 0), (0.48, 0.05, 0.48))
    cone("navy", c + V(0, 1.1, 0), 0.34, 0.06, 0.16, seg=4)
    sphere("ochre", c + V(0, 1.3, 0), 0.04)


def andon_row(side):
    for i in range(BAYS):
        andon((side * (XW - 0.42), 0, -(i + 0.5) * BAY), side)   # 每柱间一盏，贴墙


BEADS = ["bead_" + k for k in ("coral", "ochre", "teal", "pink", "lavender", "blue", "green", "paper")]   # 珠子单独一套材质，网页里几乎不压阴影，仰视也是彩色


def ceiling():
    """格天井：纸白顶板 + 深红格梁，每段格梁下挂一串下垂的彩珠，交点再垂一小串"""
    face("paper", [(-XW, H, 0), (XW, H, 0), (XW, H, -L), (-XW, H, -L)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, -1, 0))
    step = 0.9
    xs = [-2.25 + step * k for k in range(6)]
    zs = [-0.3 - step * k for k in range(15)]
    for x in xs: box("crimson", (x, H - 0.05, -L / 2), (0.07, 0.1, L))
    for z in zs: box("crimson", (0, H - 0.05, z), (W, 0.1, 0.07))
    ci = 0
    def beads(a, b, low, n):
        nonlocal ci
        for p in sag_curve(a, b, low, n)[1:-1]:
            sphere(BEADS[ci % len(BEADS)], p, 0.045); ci += 1
    for x in xs:
        for a, b in zip(zs, zs[1:]): beads((x, H - 0.1, a), (x, H - 0.1, b), H - 0.42, 8)
    for z in zs:
        for a, b in zip(xs, xs[1:]): beads((a, H - 0.1, z), (b, H - 0.1, z), H - 0.36, 8)
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            if (i + j) % 2: continue
            for k in range(5): sphere(BEADS[(ci + k) % len(BEADS)], (x, H - 0.2 - k * 0.1, z), 0.04)
            ci += 3


def end_far():
    """尽头墙：纸白墙面，中间红柱门框里贴 02 尽头的扇面门洞画"""
    z = -L
    face("paper", [(-XW, 0, z), (XW, 0, z), (XW, H, z), (-XW, H, z)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
    w, h = 3.4, 3.4 * 660 / 550
    face("end_far", [(-w / 2, 0, z + 0.02), (w / 2, 0, z + 0.02), (w / 2, h, z + 0.02), (-w / 2, h, z + 0.02)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
    for sx in (-1, 1): box("crimson", (sx * (w / 2 + 0.14), h / 2, z + 0.12), (0.26, h, 0.24))
    box("crimson", (0, h + 0.12, z + 0.12), (w + 0.56, 0.24, 0.24))


def door_near():
    """近端墙：中间贴 05 回头看到的木门 + 门楣花鸟画，两侧纸白"""
    z = 0.0
    face("paper", [(-XW, 0, z), (XW, 0, z), (XW, H, z), (-XW, H, z)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, -1))
    s = 4.2
    face("door_near", [(s / 2, 0, z - 0.02), (-s / 2, 0, z - 0.02), (-s / 2, s, z - 0.02), (s / 2, s, z - 0.02)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, -1))
    box("ochre", (0, s + 0.1, z - 0.1), (s + 0.3, 0.2, 0.2))


def build_corridor():
    floor_corridor(); ceiling(); end_far(); door_near()
    for side in (-1, 1):
        mural_wall(side); pillars(side); swags(side); chochin_rows(side); drapes(side); andon_row(side)


# ---------------------------------------------------------------- 平面图区块（docs/16）
CELL = 0.91
DIAG = {"/": ((1, -1), (-1, 1)), "\\": ((-1, -1), (1, 1))}      # 斜墙：/ 连右上和左下，\ 连左上和右下
PANELS = {"F": "fusuma", "S": "shoji", "U": "udoor", "G": "glassdoor", "E": "glassdoor", "H": "katomado_shoji", "N": "fusuma2"}   # N：第二种襖（同一间房两种襖绘，坂井家大座敷正面家纹襖）   # H：火灯窗障子（大座敷左墙）   # E：长得像玻璃门的出入口（功能同 U）
WALLS = set("#KDM") | set(PANELS) | set(DIAG)                  # M：土壁上贴画（大座敷八角凸间的美人画）
FLOOR_OF = {".": "tatami", "=": "engawa", "_": "earth", "T": "toko", ",": "gravel", "~": "water", "b": "bridge"}   # 白砂、水（不能走）、拱桥
FURN = set("PRYhrktLwpcZJWXQO")                                   # 坂井家加：p 红灯柱、c 圆坐垫、Z 灶台、J 陶罐、W 古井、X 白无垢衣架                                               # 高台、柜台、屏风、椅子、庭石：地面跟周围，摆家具，不能走
MARKS = set("@o123456789l") | FURN                                # l：头顶吊一盏红提灯，人能走
DIRS = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}
KAMOI, NAGESHI = 1.76, 1.86        # 鸭居下沿、长押下沿（米）
T_WALL, T_PANEL, POST = 0.1, 0.03, 0.12


class Plan:
    def __init__(self, name):
        text = (PLANS / f"{name}.txt").read_text(encoding="utf-8")
        head, _, body = text.partition("\n---\n")
        self.cfg = {"name": name, "height": "2.7", "ceiling": "sao"}
        self.shots, self.roles = [], {"kokabe": "plaster"}   # 长押以上的小壁默认和下半截一样
        for line in head.splitlines():
            line = line.split("  ←")[0].strip()
            if not line or line.startswith("#") or ":" not in line: continue
            k, v = (t.strip() for t in line.split(":", 1))
            if k == "shot":
                nm, cam, look, pl = (t.strip() for t in v.split("|"))
                f = lambda t: [float(x) for x in t.split(",")]
                self.shots.append({"name": nm, "cam": f(cam), "look": f(look), "player": f(pl)})
            elif k == "mat":
                for kv in v.split(","):
                    r, key = (t.strip() for t in kv.split("=")); self.roles[r] = key
            else: self.cfg[k] = v
        rows = [r.rstrip() for r in body.rstrip("\n").split("\n")]
        self.w = max(len(r) for r in rows); self.h = len(rows)
        self.g = [r.ljust(self.w) for r in rows]
        self.H = float(self.cfg["height"])
        self.on = lambda k: self.cfg.get(k, "").lower() in ("on", "yes", "1", "true")
        self.k = float(self.cfg.get("timber", "1"))      # 木料粗细倍数：柱、鸭居、长押一起放大（万屋 1.8）
        self.post = POST * self.k
        self.koshi = float(self.cfg.get("koshi", "0"))
        self.kamoi = float(self.cfg.get("kamoi", KAMOI))   # 鸭居高（襖、障子、门洞的高度），坂井家婚礼大座敷 2.4：襖顶到鸭居，上面只剩一窄条小壁
        self.nageshi = self.kamoi + (NAGESHI - KAMOI)
        self.doma = float(self.cfg.get("doma", "0"))   # 土间比上框低多少米（坂井家玄关 0.36）：土间地面、墙脚、挨着土间的门都往下伸这么多
        self.hfun = []   # [(矩形, f(x, z) → 地面高度)]：拱桥这种不平的地面，写进可走格子的 floor   # 腰板高度（米），0 = 没有；有的话土壁下面这一截换成 koshi 材质

    def R(self, role):
        """材质角色 → 材质 key（平面图里 mat: wood=wood_dark 这样换），没换就是角色名本身"""
        return self.roles.get(role, role)

    def at(self, i, j):
        return self.g[j][i] if 0 <= i < self.w and 0 <= j < self.h else " "

    def wall(self, i, j): return self.at(i, j) in WALLS

    def base(self, i, j):
        """墙格上门扇、敷居的底高：挨着土间（8 邻里有 earth 格）就是 -doma，别的 0"""
        if not self.doma: return 0.0
        return -self.doma if any(self.floor(i + dx, j + dz) == "earth" for dx in (-1, 0, 1) for dz in (-1, 0, 1)) else 0.0

    def floor(self, i, j):
        """格子的地面种类；墙格、外面返回 None；标记格、家具格跟最近的地面（不算床之间）"""
        c = self.at(i, j)
        if c in FLOOR_OF: return FLOOR_OF[c]
        if c in MARKS:
            for r in range(1, 5):
                near = Counter(FLOOR_OF[self.at(i + dx, j + dz)] for dx in range(-r, r + 1) for dz in range(-r, r + 1)
                               if self.at(i + dx, j + dz) in FLOOR_OF and self.at(i + dx, j + dz) != "T")
                if near: return near.most_common(1)[0][0]
            return "tatami"
        return None

    def center(self, i, j): return ((i + 0.5) * CELL, (j + 0.5) * CELL)

    def edge(self, i, j, me):
        """me 这种地面朝 (i,j) 那边要不要伸半格：墙格要；床之间对别的地面也要（床框在柱心）"""
        if self.wall(i, j): return True
        return self.floor(i, j) == "toko" and me != "toko"

    def cell_rect(self, i, j):
        """格子的地面范围（格单位）：朝墙的方向伸半格；床之间朝别的地面缩半格"""
        me = self.floor(i, j)
        ex = {k: 0.5 if self.edge(i + dx, j + dz, me) else 0.0 for k, (dx, dz) in DIRS.items()}
        if me == "toko":
            for k, (dx, dz) in DIRS.items():
                f = self.floor(i + dx, j + dz)
                if f and f != "toko": ex[k] = -0.5
        return (i - ex["W"], j - ex["N"], i + 1 + ex["E"], j + 1 + ex["S"])

    def regions(self, test):
        """4 连通区域。test 是地面种类名，或者一个判断 (i, j) 的函数"""
        ok = test if callable(test) else (lambda i, j: self.floor(i, j) == test)
        seen, out = set(), []
        for j in range(self.h):
            for i in range(self.w):
                if (i, j) in seen or not ok(i, j): continue
                stack, reg = [(i, j)], []
                seen.add((i, j))
                while stack:
                    a, b = stack.pop(); reg.append((a, b))
                    for dx, dz in DIRS.values():
                        n = (a + dx, b + dz)
                        if n not in seen and ok(*n): seen.add(n); stack.append(n)
                out.append(reg)
        return out

    def wall_axis(self, i, j):
        """墙格走向：'x' 横、'z' 竖、None 拐角 / 丁字 / 孤立 / 斜"""
        if self.at(i, j) in DIAG: return None
        e, w_, n, s_ = (self.wall(i + dx, j + dz) for dx, dz in (DIRS["E"], DIRS["W"], DIRS["N"], DIRS["S"]))
        if (e or w_) and not (n or s_): return "x"
        if (n or s_) and not (e or w_): return "z"
        if not (e or w_ or n or s_) and not self.links(i, j):
            return "x" if (self.floor(i, j - 1) or self.floor(i, j + 1)) else "z"
        return None

    def links(self, i, j):
        """墙格往哪些方向连（像接水管）：上下左右的墙格；斜墙按 / \\ 的走向连斜对角，普通墙格也会接上指向它的斜墙"""
        c = self.at(i, j); out = [d for d in DIRS.values() if self.wall(i + d[0], j + d[1])]
        for d in ((1, -1), (-1, 1), (-1, -1), (1, 1)):
            n = self.at(i + d[0], j + d[1])
            if c in DIAG and d in DIAG[c] and n in WALLS: out.append(d)
            elif c not in DIAG and n in DIAG and (-d[0], -d[1]) in DIAG[n]: out.append(d)
        return out


def mrect(r):   # 格单位矩形 → 米
    return tuple(v * CELL for v in r)


def floor_quad(key, r, y=0.0, tile=CELL, along_x=True):
    x0, z0, x1, z1 = mrect(r)
    uv = (lambda x, z: (x / tile, -z / tile)) if along_x else (lambda x, z: (-z / tile, x / tile))
    pts = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    face(key, pts, [uv(p[0], p[2]) for p in pts], want=(0, 1, 0))


def tatami_mat(P, x0, z0, x1, z1):
    """一张畳（米）：侧面绿色、顶面贴 tatami，u 顺长边"""
    box(P.R("tatami_side"), ((x0 + x1) / 2, -0.02, (z0 + z1) / 2), (x1 - x0 - 0.004, 0.04, z1 - z0 - 0.004))
    pts = [(x0, 0.001, z0), (x1, 0.001, z0), (x1, 0.001, z1), (x0, 0.001, z1)]
    if x1 - x0 >= z1 - z0 - 1e-6: uvs = [(0, 1), (1, 1), (1, 0), (0, 0)]
    else: uvs = [(0, 0), (0, 1), (1, 1), (1, 0)]
    face(P.R("tatami"), pts, uvs, want=(0, 1, 0))


def tatami_border(P, rm):
    """畳四周一圈黑漆框（平面图 tatami_border: 宽度，大座敷参考 07），框上隔一段撒一朵山吹小花。rm 是畳区外框（米）"""
    b = float(P.cfg.get("tatami_border", "0"))
    if b > 0:
        X0, Z0, X1, Z1 = rm
        for q in ((X0, Z0, X1, Z0 + b), (X0, Z1 - b, X1, Z1), (X0, Z0 + b, X0 + b, Z1 - b), (X1 - b, Z0 + b, X1, Z1 - b)):
            face("lacquer", [(q[0], 0.004, q[1]), (q[2], 0.004, q[1]), (q[2], 0.004, q[3]), (q[0], 0.004, q[3])], [(0, 0)] * 4, want=(0, 1, 0))
        def crest(x, z):
            for k in range(4):
                a = math.pi / 2 * k + math.pi / 4
                pts = [(x + math.cos(a + t) * 0.14 * (1 - abs(t) / 0.7), 0.006, z + math.sin(a + t) * 0.14 * (1 - abs(t) / 0.7)) for t in (-0.6, -0.3, 0, 0.3, 0.6)] + [(x, 0.006, z)]
                face("ochre", pts, [(0, 0)] * len(pts), want=(0, 1, 0))
        n = max(2, int((X1 - X0) / 1.3))
        for k in range(n):
            x = X0 + (X1 - X0) * (k + 0.5) / n; crest(x, Z0 + b / 2); crest(x, Z1 - b / 2)
        n = max(2, int((Z1 - Z0) / 1.3))
        for k in range(n):
            z = Z0 + (Z1 - Z0) * (k + 0.5) / n; crest(X0 + b / 2, z); crest(X1 - b / 2, z)


def lay_tatami(P, reg, walk):
    xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
    i0, i1, j0, j1 = min(xs), max(xs), min(zs), max(zs)
    rect_ok = len(reg) == (i1 - i0 + 1) * (j1 - j0 + 1)
    side = lambda cells, d: all(P.edge(a + d[0], b + d[1], "tatami") for a, b in cells)
    if rect_ok:
        ex = {"W": side([(i0, j) for j in range(j0, j1 + 1)], DIRS["W"]), "E": side([(i1, j) for j in range(j0, j1 + 1)], DIRS["E"]),
              "N": side([(i, j0) for i in range(i0, i1 + 1)], DIRS["N"]), "S": side([(i, j1) for i in range(i0, i1 + 1)], DIRS["S"])}
        r = (i0 - 0.5 * ex["W"], j0 - 0.5 * ex["N"], i1 + 1 + 0.5 * ex["E"], j1 + 1 + 0.5 * ex["S"])
        W, D = r[2] - r[0], r[3] - r[1]
        if abs(W - round(W)) < 1e-6 and abs(D - round(D)) < 1e-6:
            W, D = round(W), round(D); long_x = W >= D
            A, B = (W, D) if long_x else (D, W)
            for row in range(B):           # 一排一排铺，奇数排错开一格，排尾不够就半畳
                pos = 1 if row % 2 else 0
                segs = [(0, 1)] if pos else []
                while pos < A:
                    n = 2 if pos + 2 <= A else 1; segs.append((pos, pos + n)); pos += n
                for a, b in segs:
                    if long_x: rr = (r[0] + a, r[1] + row, r[0] + b, r[1] + row + 1)
                    else: rr = (r[0] + row, r[1] + a, r[0] + row + 1, r[1] + b)
                    tatami_mat(P, *mrect(rr))
            walk.append(mrect(r))
            tatami_border(P, mrect(r))
            # 没伸到墙的边（一边挨墙一边挨地面的混合边）补木条
            for (a, b) in reg:
                for k, (dx, dz) in DIRS.items():
                    if ex[k] or not P.edge(a + dx, b + dz, "tatami"): continue
                    cr = P.cell_rect(a, b); c = (a, b, a + 1, b + 1)
                    strip_r = {"W": (cr[0], cr[1], c[0], cr[3]), "E": (c[2], cr[1], cr[2], cr[3]), "N": (cr[0], cr[1], cr[2], c[1]), "S": (cr[0], c[3], cr[2], cr[3])}[k]
                    floor_quad(P.R("wood"), strip_r); walk.append(mrect(strip_r))
            return
    rs = []
    for (a, b) in reg:                     # 不是长方形：每格半畳
        r = P.cell_rect(a, b); tatami_mat(P, *mrect(r)); walk.append(mrect(r)); rs.append(mrect(r))
    tatami_border(P, (min(q[0] for q in rs), min(q[1] for q in rs), max(q[2] for q in rs), max(q[3] for q in rs)))


def plan_floors(P, walk, block):
    for reg in P.regions("tatami"): lay_tatami(P, reg, walk)
    for reg in P.regions("gravel"):
        for (a, b) in reg: r = P.cell_rect(a, b); floor_quad(P.R("gravel"), r); walk.append(mrect(r))
    for reg in P.regions("water"):        # 水面低 0.22 米，和别的地面交界处立一圈石岸
        for (a, b) in reg:
            r = P.cell_rect(a, b); floor_quad("water", r, y=-0.22)
            x0, z0, x1, z1 = mrect(r)
            for k, (dx, dz) in DIRS.items():
                f = P.floor(a + dx, b + dz)
                if not f or f == "water": continue
                e = {"W": ((x0, z0), (x0, z1)), "E": ((x1, z1), (x1, z0)), "N": ((x1, z0), (x0, z0)), "S": ((x0, z1), (x1, z1))}[k]
                (ax, az), (bx, bz) = e
                face("stone", [(ax, -0.22, az), (bx, -0.22, bz), (bx, 0.0, bz), (ax, 0.0, az)], [(0, 0), (1, 0), (1, 0.25), (0, 0.25)], want=(-dx, 0, -dz))
    for reg in P.regions("bridge"): arch_bridge(P, reg, walk, block)
    for kind in ("engawa", "earth"):
        for reg in P.regions(kind):
            xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
            along_x = (max(xs) - min(xs)) >= (max(zs) - min(zs))
            if kind == "engawa" and P.cfg.get("seams") == "across": along_x = not along_x   # 板缝横过廊下（万屋长廊）
            y = -P.doma if kind == "earth" else 0.0
            for (a, b) in reg:
                r = P.cell_rect(a, b); floor_quad(P.R(kind), r, y=y, along_x=along_x); walk.append(mrect(r))
    if P.doma: doma_step(P, block)
    for reg in P.regions("toko"):          # 床之间：抬高的木台 + 床框 + 后墙挂轴
        rs = [mrect(P.cell_rect(a, b)) for a, b in reg]
        x0, z0, x1, z1 = min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)
        box(P.R("toko"), ((x0 + x1) / 2, 0.07, (z0 + z1) / 2), (x1 - x0, 0.14, z1 - z0), tile=CELL)
        block.append((x0, z0, x1, z1))
        open_dirs = Counter(k for a, b in reg for k, (dx, dz) in DIRS.items() if (f := P.floor(a + dx, b + dz)) and f != "toko")
        back = {"S": "N", "N": "S", "E": "W", "W": "E"}[open_dirs.most_common(1)[0][0]] if open_dirs else "N"
        fx = {"S": (x0, z1, x1, z1), "N": (x0, z0, x1, z0), "E": (x1, z0, x1, z1), "W": (x0, z0, x0, z1)}[{"N": "S", "S": "N", "E": "W", "W": "E"}[back]]
        box(P.R("frame"), ((fx[0] + fx[2]) / 2, 0.075, (fx[1] + fx[3]) / 2), (max(fx[2] - fx[0], 0.07), 0.15, max(fx[3] - fx[1], 0.07)))   # 床框
        w_, h_ = 0.55, 1.37; y0 = 0.62
        d = T_WALL / 2 + 0.006
        if back in "NS":
            z = z0 + d if back == "N" else z1 - d; cx = (x0 + x1) / 2; n = (0, 0, 1) if back == "N" else (0, 0, -1)
            pts = [(cx - w_ / 2, y0, z), (cx + w_ / 2, y0, z), (cx + w_ / 2, y0 + h_, z), (cx - w_ / 2, y0 + h_, z)]
            if back == "S": pts = [pts[1], pts[0], pts[3], pts[2]]
        else:
            x = x0 + d if back == "W" else x1 - d; cz = (z0 + z1) / 2; n = (1, 0, 0) if back == "W" else (-1, 0, 0)
            pts = [(x, y0, cz + w_ / 2), (x, y0, cz - w_ / 2), (x, y0 + h_, cz - w_ / 2), (x, y0 + h_, cz + w_ / 2)]
            if back == "E": pts = [pts[1], pts[0], pts[3], pts[2]]
        face("kakejiku", pts, [(0, 0), (1, 0), (1, 1), (0, 1)], want=n)


def doma_step(P, block):
    """土间和上面地板的交界（平面图 doma: 0.36，坂井家玄关参考 04）：交界处立焦茶上框（竖板 + 压顶横木），
    正对正门 E 的那段前面放一块纸白沓脱石，高度在土间和上框正中，药郎从石头上分两步走上去；
    上框别的地方挡一条，不让人从土间一步跨上 0.36 米。高度写进 P.hfun（交界处 0.1 米的小斜坡，脚不会一下弹上去）"""
    d = P.doma; edges = []   # (轴, 交界线坐标, 起, 止, 土间那边的符号)，米
    for j in range(P.h):
        for i in range(P.w):
            if P.floor(i, j) != "earth": continue
            x0, z0, x1, z1 = mrect(P.cell_rect(i, j))
            for k, (dx, dz) in DIRS.items():
                f = P.floor(i + dx, j + dz)
                if not f or f == "earth": continue
                if dz: edges.append(("x", z0 if dz < 0 else z1, x0, x1, -dz))
                else: edges.append(("z", x0 if dx < 0 else x1, z0, z1, -dx))
    ecols = [(i, j) for j in range(P.h) for i in range(P.w) if P.at(i, j) == "E"]
    ex = P.center(*ecols[0])[0] if ecols else None
    sw, sd, sh = 3 * CELL, 0.5, d / 2   # 沓脱石宽 3 格、深 0.5 米，顶面在一半高
    ramp = 0.05
    for ax, c, a0, a1, sg in edges:
        if ax == "x":
            face(P.R("wood"), [(a0, -d, c), (a1, -d, c), (a1, 0, c), (a0, 0, c)], [(a0, -d), (a1, -d), (a1, 0), (a0, 0)], want=(0, 0, sg))   # 上框竖板
            box(P.R("wood"), ((a0 + a1) / 2, -0.05, c + sg * 0.03), (a1 - a0, 0.11, 0.08))   # 压顶横木，往土间凸一点
            s0, s1 = (ex - sw / 2, ex + sw / 2) if ex is not None else (0, 0)
            for b0, b1 in ((a0, min(a1, s0)), (max(a0, s1), a1)):   # 沓脱石以外挡住
                if b1 - b0 > 1e-6: block.append((b0, min(c, c + sg * 0.06), b1, max(c, c + sg * 0.06)))
        else:
            face(P.R("wood"), [(c, -d, a0), (c, -d, a1), (c, 0, a1), (c, 0, a0)], [(a0, -d), (a1, -d), (a1, 0), (a0, 0)], want=(sg, 0, 0))
            box(P.R("wood"), (c + sg * 0.03, -0.05, (a0 + a1) / 2), (0.08, 0.11, a1 - a0))
            block.append((min(c, c + sg * 0.06), a0, max(c, c + sg * 0.06), a1))
    # 沓脱石：只做横向交界（土间在下面）上、对着正门的那块
    xs = [e for e in edges if e[0] == "x" and ex is not None and e[2] - 1e-6 <= ex <= e[3] + 1e-6]
    if xs:
        _, c, _, _, sg = xs[0]
        z0, z1 = sorted((c, c + sg * sd))
        box("kutsunugi", (ex, -d + sh / 2, (z0 + z1) / 2), (sw, sh, sd))
        box("kutsunugi", (ex, -d + 0.01, (z0 + z1) / 2 + sg * 0.03), (sw + 0.08, 0.02, sd + 0.06))   # 底下压一圈，像石头埋进土间
        def h(x, z, c=c, sg=sg):
            t = (z - c) * sg   # 往土间走是正
            on = ex - sw / 2 <= x <= ex + sw / 2
            def lerp(t, t0, y0, y1): return y0 + (y1 - y0) * max(0.0, min(1.0, (t - t0 + ramp) / (2 * ramp)))
            if not on: return 0.0 if t < 0 else -d
            return lerp(t, 0, 0.0, -sh) if t < sd / 2 else lerp(t, sd, -sh, -d)
    else:
        def h(x, z, c=None): return None
    # 整片土间（多伸 0.1 米到上框里）都记高度：不在沓脱石上的就是 -d
    rs = [mrect(P.cell_rect(i, j)) for j in range(P.h) for i in range(P.w) if P.floor(i, j) == "earth"]
    X0, Z0, X1, Z1 = min(r[0] for r in rs) - 0.1, min(r[1] for r in rs) - 0.1, max(r[2] for r in rs) + 0.1, max(r[3] for r in rs) + 0.1
    def earth(x, z):   # 墙格那半格（地面伸过去的部分）按旁边的地面格算
        i, j = int(x / CELL), int(z / CELL)
        if P.floor(i, j): return P.floor(i, j) == "earth"
        near = [P.floor(i + dx, j + dz) for dx, dz in DIRS.values() if P.floor(i + dx, j + dz)]
        return bool(near) and near[0] == "earth"
    def f(x, z):
        return h(x, z) if xs else (-d if earth(x, z) else 0.0)
    P.hfun.append(((X0, Z0, X1, Z1), f))


def arch_bridge(P, reg, walk, block):
    """红拱桥（万屋室内庭，参考帧 12）：一片连着的 b 格是一座桥，顺长边起拱（平面图 bridge_rise，默认 0.55 米），
    深红桥面 + 两侧栏杆、四角山吹宝珠；桥面高度记进 P.hfun，可走格子带 floor，药郎走上去贴着桥面"""
    xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
    x0, z0, x1, z1 = mrect((min(xs), min(zs), max(xs) + 1, max(zs) + 1))
    along_x = (x1 - x0) >= (z1 - z0)
    L, Wd = (x1 - x0, z1 - z0) if along_x else (z1 - z0, x1 - x0)
    rise = float(P.cfg.get("bridge_rise", "0.55")); N = 24
    yf = lambda s: rise * math.sin(math.pi * max(0.0, min(L, s)) / L)
    pt = lambda s, w, y: (x0 + s, y, z0 + w) if along_x else (x0 + w, y, z0 + s)
    m = 0.06
    for k in range(N):   # 桥面（顶面贴 deck 横板）、底面、两侧桥帮
        sa, sb = L * k / N, L * (k + 1) / N; ya, yb = yf(sa), yf(sb)
        face("deck", [pt(sa, m, ya), pt(sb, m, yb), pt(sb, Wd - m, yb), pt(sa, Wd - m, ya)], [(0, sa / 0.91), (0, sb / 0.91), (1, sb / 0.91), (1, sa / 0.91)], want=(0, 1, 0))
        face("crimson", [pt(sa, m, ya - 0.14), pt(sb, m, yb - 0.14), pt(sb, Wd - m, yb - 0.14), pt(sa, Wd - m, ya - 0.14)], [(0, 0)] * 4, want=(0, -1, 0))
        for w, sg in ((m, -1), (Wd - m, 1)):
            n = (0, 0, sg) if along_x else (sg, 0, 0)
            face("crimson", [pt(sa, w, max(ya - 0.3, -0.22)), pt(sb, w, max(yb - 0.3, -0.22)), pt(sb, w, yb), pt(sa, w, ya)], [(0, 0)] * 4, want=n)
    for w in (0.1, Wd - 0.1):   # 栏杆：柱 + 上下两道横木（分段跟着拱）
        for k in range(9):
            sp = L * (0.04 + 0.92 * k / 8); c = pt(sp, w, yf(sp))
            box("crimson", (c[0], c[1] + 0.38, c[2]), (0.07, 0.76, 0.07))
            if k in (0, 8): sphere("ochre", (c[0], c[1] + 0.84, c[2]), 0.07)
        for k in range(N):
            sa, sb = L * k / N, L * (k + 1) / N
            for hh, th in ((0.72, 0.06), (0.36, 0.04)):
                ya, yb = yf(sa) + hh, yf(sb) + hh; pa, pb = pt(sa, w, 0), pt(sb, w, 0)
                obox("crimson", (pa[0], pa[2]), (pb[0], pb[2]), th, (ya + yb) / 2 - th / 2, (ya + yb) / 2 + th / 2)
    walk.append((x0, z0, x1, z1))
    for w in (0.1, Wd - 0.1):   # 栏杆挡人（桥两头敞开）
        a, b = pt(0.25, w, 0), pt(L - 0.25, w, 0)
        block.append((min(a[0], b[0]) - 0.03, min(a[2], b[2]) - 0.03, max(a[0], b[0]) + 0.03, max(a[2], b[2]) + 0.03))
    P.hfun.append(((x0, z0, x1, z1), (lambda x, z: yf(x - x0)) if along_x else (lambda x, z: yf(z - z0))))


def sakai_prop(ch, cx, cz, P, block, seed):
    """坂井家的家具格（参考 assets/concept/ref/sakai/）"""
    import random
    rnd = random.Random(seed)
    if ch == "p":   # 红灯柱（02 婚礼门前）：深红柱 + 顶上一盏纸白方灯
        box("crimson", (cx, 1.25, cz), (0.12, 2.5, 0.12)); box(P.R("wood"), (cx, 0.08, cz), (0.4, 0.16, 0.4))
        box("paper", (cx, 2.75, cz), (0.32, 0.42, 0.32)); box("ink", (cx, 2.98, cz), (0.4, 0.05, 0.4)); box("ink", (cx, 2.52, cz), (0.36, 0.04, 0.36))
        block.append((cx - 0.2, cz - 0.2, cx + 0.2, cz + 0.2))
    elif ch == "c":   # 圆坐垫（06 客间）：红蓝同心圆
        pts = [(cx + math.cos(2 * math.pi * k / 24) * 0.42, 0.06, cz + math.sin(2 * math.pi * k / 24) * 0.42) for k in range(24)]
        face("zabuton_maru", pts, [(0.5 + 0.5 * math.cos(2 * math.pi * k / 24), 0.5 + 0.5 * math.sin(2 * math.pi * k / 24)) for k in range(24)], want=(0, 1, 0))
        cylinder("crimson", (cx, 0.0, cz), 0.42, 0.06, seg=24, caps=False)
    elif ch == "Z":   # 灶台（05 厨房）：白灰土台 + 两口黑锅 + 焦茶边
        box("plaster_white", (cx, 0.35, cz), (0.85, 0.7, 0.75)); box(P.R("wood"), (cx, 0.72, cz), (0.9, 0.05, 0.8))
        for dx in (-0.2, 0.2):
            cylinder("ink", (cx + dx, 0.72, cz), 0.16, 0.1, seg=14); sphere("ink", (cx + dx, 0.82, cz), 0.15, seg=12, rings=6)
        box("ink", (cx, 0.22, cz + 0.38), (0.3, 0.22, 0.02))   # 灶口
        block.append((cx - 0.45, cz - 0.4, cx + 0.45, cz + 0.4))
    elif ch == "J":   # 陶罐：青磁、山吹、焦茶几只
        for k in range(rnd.randint(2, 3)):
            x, z = cx + rnd.uniform(-0.2, 0.2), cz + rnd.uniform(-0.2, 0.2); r = rnd.uniform(0.12, 0.2); h = rnd.uniform(0.3, 0.55)
            col = rnd.choice(["teal", "ochre", "wood_dark", "green"])
            cylinder(col, (x, 0, z), r, h, seg=12); cone(col, (x, h, z), r, r * 0.55, 0.08, seg=12); cylinder(col, (x, h + 0.08, z), r * 0.5, 0.06, seg=10)
        block.append((cx - 0.35, cz - 0.35, cx + 0.35, cz + 0.35))
    elif ch == "W":   # 古井（13）：井桁木框 + 水面 + 小木顶，井前一座小石坟和一束鲜花
        for dz in (-0.45, 0.45): box("ochre", (cx, 0.4, cz + dz), (1.1, 0.8, 0.1))   # 井框是浅木色（参考 13），不跟厨房的近黑木
        for dx in (-0.5, 0.5): box("ochre", (cx + dx, 0.4, cz), (0.1, 0.8, 1.0))
        face("water", [(cx - 0.45, 0.45, cz - 0.4), (cx + 0.45, 0.45, cz - 0.4), (cx + 0.45, 0.45, cz + 0.4), (cx - 0.45, 0.45, cz + 0.4)], [(0, 0)] * 4, want=(0, 1, 0))
        gz = cz + 0.85
        box("stone", (cx, 0.3, gz), (0.28, 0.6, 0.2)); box("stone", (cx, 0.04, gz), (0.5, 0.08, 0.35))
        for k in range(7):   # 鲜花
            a = 2 * math.pi * k / 7; sphere(rnd.choice(["coral", "ochre", "pink", "crimson", "lavender"]), (cx + math.cos(a) * 0.2, 0.12, gz + 0.22 + math.sin(a) * 0.1), 0.07, seg=8, rings=5)
        block.append((cx - 0.6, cz - 0.55, cx + 0.6, gz + 0.35))
    elif ch == "Q":   # 吊架（05 厨房）：天花垂下的焦茶横杆，挂着锅、勺、干菜
        y = P.H - 0.9
        for dx in (-0.55, 0.55): box("ink", (cx + dx, (y + P.H) / 2, cz), (0.02, P.H - y, 0.02))
        box(P.R("wood"), (cx, y, cz), (1.3, 0.07, 0.07))
        for k in range(5):
            x = cx - 0.5 + k * 0.25; kind = rnd.choice(("pot", "ladle", "veg"))
            box("ink", (x, y - 0.12, cz), (0.015, 0.24, 0.015))
            if kind == "pot": cylinder("ink", (x, y - 0.42, cz), 0.1, 0.18, seg=10)
            elif kind == "ladle": box(P.R("wood"), (x, y - 0.4, cz), (0.03, 0.3, 0.03)); sphere(P.R("wood"), (x, y - 0.56, cz), 0.06, seg=8, rings=4)
            else:
                for n in range(3): sphere(rnd.choice(["ochre", "coral", "green"]), (x, y - 0.3 - n * 0.09, cz), 0.05, seg=6, rings=4)
    elif ch == "O":   # 水缸：大陶缸 + 木盖 + 水瓢
        cylinder("wood_dark", (cx, 0, cz), 0.36, 0.7, seg=16); cone("wood_dark", (cx, 0.7, cz), 0.36, 0.32, 0.06, seg=16)
        cylinder(P.R("wood"), (cx, 0.76, cz), 0.34, 0.04, seg=16); box(P.R("wood"), (cx + 0.1, 0.82, cz), (0.4, 0.03, 0.05))
        block.append((cx - 0.38, cz - 0.38, cx + 0.38, cz + 0.38))
    elif ch == "X":   # 白无垢衣架（11 密室）：焦茶衣桁 + 挂着的白无垢
        box(P.R("wood"), (cx, 1.65, cz), (1.5, 0.08, 0.08))
        for dx in (-0.65, 0.65): box(P.R("wood"), (cx + dx, 0.85, cz), (0.07, 1.7, 0.07)); box(P.R("wood"), (cx + dx, 0.04, cz), (0.07, 0.08, 0.5))
        face("shiromuku", [(cx - 0.6, 0.15, cz + 0.02), (cx + 0.6, 0.15, cz + 0.02), (cx + 0.6, 1.62, cz + 0.02), (cx - 0.6, 1.62, cz + 0.02)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
        face("shiromuku", [(cx + 0.6, 0.15, cz - 0.02), (cx - 0.6, 0.15, cz - 0.02), (cx - 0.6, 1.62, cz - 0.02), (cx + 0.6, 1.62, cz - 0.02)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, -1))
        block.append((cx - 0.7, cz - 0.25, cx + 0.7, cz + 0.25))


def bamboo(cx, cz, seed):
    """竹丛：材质名都以 kit_bamboo 开头（竿 kit_bamboo、节和叶 kit_bamboo_leaf），镜头射线按名字跳过它（follow_cam.js）"""
    import random
    rnd = random.Random(seed)
    for k in range(5):
        x, z = cx + rnd.uniform(-0.25, 0.25), cz + rnd.uniform(-0.25, 0.25); h = rnd.uniform(2.0, 3.0)
        cylinder("bamboo", (x, 0, z), 0.035, h, seg=6)
        for n in range(1, 6): cylinder("bamboo_leaf", (x, h * n / 6, z), 0.042, 0.03, seg=6)   # 竹节
        for n in range(4):   # 竹叶：竿顶附近几簇细长的叶
            a = rnd.uniform(0, 2 * math.pi); y = h * rnd.uniform(0.55, 0.95)
            ribbon("bamboo_leaf", [(x, y, z), (x + math.cos(a) * 0.25, y - 0.08, z + math.sin(a) * 0.25), (x + math.cos(a) * 0.45, y - 0.22, z + math.sin(a) * 0.45)], 0.07, (math.sin(a), 0.3, -math.cos(a)), (1, 1))


def rock(cx, cz, seed, k=1.0):
    """庭石：压扁、每个顶点随机缩放的球，色板淡藤；k 整体放大（室内庭 1.6）"""
    import random
    rnd = random.Random(seed); sx, sy, sz = (v * k for v in (rnd.uniform(0.45, 0.62), rnd.uniform(0.3, 0.5), rnd.uniform(0.42, 0.6)))
    g = acc("rock"); i0 = len(g["v"]); seg, rings = 9, 6; jit = {}
    for j in range(rings + 1):
        th = math.pi * j / rings
        for i in range(seg):
            ph = 2 * math.pi * i / seg; f = 1.0 if j in (0, rings) else rnd.uniform(0.8, 1.12)
            g["v"].append(Vector((cx + math.sin(th) * math.cos(ph) * sx * f, max(-0.05, math.cos(th) * sy * f + sy * 0.55), cz + math.sin(th) * math.sin(ph) * sz * f)))
    c = Vector((cx, sy * 0.55, cz))
    for j in range(rings):
        for i in range(seg):
            a, b = i0 + j * seg + i, i0 + j * seg + (i + 1) % seg
            q = [a, a + seg, b + seg, b]; pp = [g["v"][k] for k in q]; mid = sum(pp, Vector((0, 0, 0))) / 4
            nrm = (pp[1] - pp[0]).cross(pp[2] - pp[0])
            if nrm.length < 1e-12: nrm = (pp[2] - pp[0]).cross(pp[3] - pp[0])
            if nrm.dot(mid - c) < 0: q = q[::-1]
            g["f"].append(q); g["uv"].append([(0, 0)] * 4)


def kage(cx, cz, seed):
    """黑影人（座敷童子里的人群画成墨色剪影，头顶一朵小花）：没有参考帧，先做通用的；身高、花色随机"""
    import random
    rnd = random.Random(seed); hgt = rnd.uniform(1.45, 1.7); r = rnd.uniform(0.2, 0.26)
    cone("kage", (cx, 0, cz), r, r * 0.55, hgt * 0.78, seg=10)
    sphere("kage", (cx, hgt * 0.86, cz), hgt * 0.085, seg=10, rings=6)
    fy = hgt + 0.08; col = rnd.choice(["pink", "coral", "ochre"])
    for k in range(5):   # 五瓣小花，平放在头顶上方
        a = 2 * math.pi * k / 5 + rnd.uniform(0, 1)
        sphere(col, (cx + math.cos(a) * 0.07, fy, cz + math.sin(a) * 0.07), 0.05, seg=6, rings=4)
    sphere("ochre", (cx, fy + 0.01, cz), 0.035, seg=6, rings=4)


def pent_roof(x0, x1, zw, y, depth, drop=0.55, thick=0.18, key="roof"):
    """一层出檐（瓦顶）：从墙面 (zw, y) 往外 (+z) 斜下到 (zw+depth, y-drop) 的一块有厚度的瓦板，
    贴墙那头压一根屋脊（藏青方木），檐口一道山吹边，两头封墨色三角（第三轮，参考 01 的层层瓦顶）"""
    zo = zw + depth; yo = y - drop
    face(key, [(x0, yo, zo), (x1, yo, zo), (x1, y, zw), (x0, y, zw)], [(0, 0), (x1 - x0, 0), (x1 - x0, depth), (0, depth)], want=(0, 1, 0.6))
    face(key, [(x0, yo - thick, zo), (x1, yo - thick, zo), (x1, y - thick, zw), (x0, y - thick, zw)], [(0, 0)] * 4, want=(0, -1, -0.3))
    face("kage", [(x0, yo - thick, zo), (x1, yo - thick, zo), (x1, yo, zo), (x0, yo, zo)], [(0, 0)] * 4, want=(0, 0, 1))
    for x, sg in ((x0, -1), (x1, 1)):
        face("kage", [(x, y, zw), (x, yo, zo), (x, yo - thick, zo), (x, y - thick, zw)], [(0, 0)] * 4, want=(sg, 0, 0))
    box("ochre", ((x0 + x1) / 2, yo - thick / 2, zo + 0.02), (x1 - x0 + 0.04, thick * 0.6, 0.05))
    box("navy", ((x0 + x1) / 2, y + 0.08, zw + 0.08), (x1 - x0, 0.2, 0.22))


def facade(P, block):
    """外景北墙往上的整栋楼（正面朝 +z，街在南边；万屋雨中外观，参考帧 01、02）。第三轮（10-30）重写：
    楼身是一整块从地面连到顶的墙体（不再是悬空的窗格），一楼上方、二楼上方各一层斜坡瓦顶出檐，三楼外廊 + 深红栏杆 + 障子窗，
    顶上大两坡屋顶 + 正面千鸟破风（三角山墙）+ 屋脊，正门上方唐破风门头做成有厚度的弯顶，最突出。一楼的门窗就是平面图第 0 排"""
    H = P.H; zw = 0.5 * CELL; x0, x1 = 0.5 * CELL - 0.3, (P.w - 0.5) * CELL + 0.3; Wd = x1 - x0; cxm = (x0 + x1) / 2
    D = 9.0                                        # 楼身进深（往 -z）
    f2, f3 = H + 0.6, H + 0.6 + 2.8               # 二楼、三楼楼面
    ytop = f3 + 2.8                                # 三楼檐口
    n_bay = max(1, round(Wd / 1.82))
    # 楼身：一整块，从地面起，比一楼墙退后 5 厘米，侧面也能看到
    box("plaster_white", (cxm, ytop / 2, zw - 0.05 - D / 2), (Wd, ytop, D))
    for x in (x0, x1): box(P.R("wood"), (x, ytop / 2, zw - 0.02), (0.24, ytop, 0.24))      # 两角通柱
    # 一楼上方出檐（压在一楼墙顶）
    pent_roof(x0 - 0.4, x1 + 0.4, zw, H + 0.45, 1.5, drop=0.6)
    for k in range(n_bay):   # 檐下红提灯
        chochin((x0 + Wd * (k + 0.5) / n_bay, H - 0.85, zw + 0.95))
    # 二楼：格子窗带（焦茶格子 + 障子），柱
    zf = zw + 0.02
    for k in range(n_bay + 1): box(P.R("wood"), (x0 + Wd * k / n_bay, (f2 + f3) / 2, zf), (0.16, f3 - f2, 0.16))
    for k in range(n_bay):
        xa, xb = x0 + Wd * k / n_bay + 0.14, x0 + Wd * (k + 1) / n_bay - 0.14
        face("lattice", [(xa, f2 + 0.5, zf + 0.01), (xb, f2 + 0.5, zf + 0.01), (xb, f2 + 2.0, zf + 0.01), (xa, f2 + 2.0, zf + 0.01)], [(0, 0), (xb - xa, 0), (xb - xa, 1.5), (0, 1.5)], want=(0, 0, 1))
    box(P.R("wood"), (cxm, f2 + 0.25, zf + 0.02), (Wd, 0.12, 0.08)); box(P.R("wood"), (cxm, f2 + 2.15, zf + 0.02), (Wd, 0.12, 0.08))
    # 二楼上方出檐
    pent_roof(x0 - 0.3, x1 + 0.3, zw, f3 + 0.35, 1.3, drop=0.55)
    # 三楼：外廊 + 栏杆 + 障子窗（楼身前面挑出 1.1 米的外廊）
    for k in range(n_bay + 1): box(P.R("wood"), (x0 + Wd * k / n_bay, (f3 + ytop) / 2, zf), (0.16, ytop - f3, 0.16))
    for k in range(n_bay):
        xa, xb = x0 + Wd * k / n_bay + 0.14, x0 + Wd * (k + 1) / n_bay - 0.14
        face("shoji", [(xa, f3 + 0.55, zf + 0.01), (xb, f3 + 0.55, zf + 0.01), (xb, f3 + 2.3, zf + 0.01), (xa, f3 + 2.3, zf + 0.01)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
    box(P.R("wood"), (cxm, f3 + 0.45, zw + 1.0), (Wd, 0.1, 1.0))          # 外廊地板（压在出檐上面）
    for k in range(n_bay * 2 + 1): box("crimson", (x0 + Wd * k / (n_bay * 2), f3 + 0.9, zw + 1.48), (0.07, 0.8, 0.07))
    box("crimson", (cxm, f3 + 1.3, zw + 1.48), (Wd, 0.07, 0.09)); box("crimson", (cxm, f3 + 0.85, zw + 1.48), (Wd, 0.05, 0.06))
    for k in range(n_bay): chochin((x0 + Wd * (k + 0.5) / n_bay, ytop - 0.75, zw + 1.2))
    # 顶：大两坡屋顶（屋脊沿 x），前坡挑出 1.6 米；屋脊压一根藏青脊木，两头山吹鬼瓦
    zr = zw - D / 2 - 0.05
    gable("roof", x0 - 0.9, x1 + 0.9, zw - D - 1.0, zw + 1.6, ytop, ytop + 3.6)
    box("navy", (cxm, ytop + 3.65, zr - 0.15 + 0.45), (Wd + 1.6, 0.3, 0.4))
    for x in (x0 - 0.7, x1 + 0.7): sphere("ochre", (x, ytop + 3.85, zr + 0.3), 0.3)
    box("ochre", (cxm, ytop - 0.08, zw + 1.6), (Wd + 1.8, 0.1, 0.08))
    # 正面千鸟破风：前坡中间立一个三角山墙（纸白 + 焦茶框），自带小两坡顶
    cw, ch, zc = min(6.0, Wd * 0.45), 2.4, zw + 0.6
    face("plaster_white", [(cxm - cw / 2, ytop + 0.4, zc), (cxm + cw / 2, ytop + 0.4, zc), (cxm, ytop + 0.4 + ch, zc)], [(0, 0)] * 3, want=(0, 0, 1))
    gable("roof", cxm - cw / 2 - 0.4, cxm + cw / 2 + 0.4, zc - 3.0, zc + 0.5, ytop + 0.3, ytop + 0.4 + ch + 0.3, ridge_along_x=False)
    sphere("ochre", (cxm, ytop + 1.4, zc + 0.03), 0.35)
    # 唐破风门头：正门上方往外挑的弯屋顶（第四轮 10-30：压低、加厚，门柱缩短到门头高）。
    # 弯顶本身有厚度（顶面瓦、底面、前面深红破风板 + 山吹边），弯顶下面是纸白的山墙板，"同"字圆牌挂在板上，再下面是门
    ex = [i for i in range(P.w) if P.at(i, 0) == "E"]
    if ex:
        cx = (ex[0] + 0.5) * CELL; half = 2.3; yb = KAMOI + 0.75; dep = 2.0; rise = 0.75; th = 0.55
        prof = lambda t: yb + rise * math.sin(math.pi * t) - 0.18 * (1 - math.sin(math.pi * t)) ** 3
        N = 24; xs = [cx - half + 2 * half * k / N for k in range(N + 1)]; ys = [prof(k / N) for k in range(N + 1)]
        zf = zw + dep
        strip("roof", [[(x, y + th, zf), (x, y + th, zw)] for x, y in zip(xs, ys)], [[(k / N * 4, 0), (k / N * 4, 1)] for k in range(N + 1)], want=lambda i: (0, 1, 0))
        strip("roof", [[(x, y, zf), (x, y, zw)] for x, y in zip(xs, ys)], [[(0, 0), (0, 0)]] * (N + 1), want=lambda i: (0, -1, 0))
        strip("crimson", [[(x, y, zf), (x, y + th, zf)] for x, y in zip(xs, ys)], [[(k / N, 0), (k / N, 1)] for k in range(N + 1)], want=lambda i: (0, 0, 1))
        for k in range(N):
            ym = (ys[k] + ys[k + 1]) / 2
            obox("ochre", (xs[k], zf + 0.02), (xs[k + 1], zf + 0.02), 0.06, ym + th - 0.12, ym + th)
        for x, y in ((xs[0], ys[0]), (xs[-1], ys[-1])):   # 两头墨色封口
            face("kage", [(x, y, zw), (x, y, zf), (x, y + th, zf), (x, y + th, zw)], [(0, 0)] * 4, want=(1 if x > cx else -1, 0, 0))
        hw = half - 0.3   # 弯顶下的山墙板（纸白），板底就是门柱顶
        strip("plaster_white", [[(x, yb, zf - 0.06), (x, prof((x - cx + half) / (2 * half)), zf - 0.06)] for x in xs if abs(x - cx) <= hw + 1e-6],
              [[(0, 0), (0, 0)]] * len([x for x in xs if abs(x - cx) <= hw + 1e-6]), want=lambda i: (0, 0, 1))
        box(P.R("wood"), (cx, yb + 0.05, zf - 0.05), (2 * hw, 0.12, 0.14))   # 门头横梁
        for sx in (-1, 1):   # 门柱（到门头横梁为止，算碰撞）
            px, pz = cx + sx * hw, zf - 0.15
            box("crimson", (px, yb / 2, pz), (0.24, yb, 0.24)); block.append((px - 0.12, pz - 0.12, px + 0.12, pz + 0.12))
        sy = yb + 0.38; r = 0.34
        pts = [(cx + math.cos(2 * math.pi * k / 24) * r, sy + math.sin(2 * math.pi * k / 24) * r, zf - 0.02) for k in range(24)]
        face("dou_sign", pts, [(0.5 + 0.5 * math.cos(2 * math.pi * k / 24), 0.5 + 0.5 * math.sin(2 * math.pi * k / 24)) for k in range(24)], want=(0, 0, 1))


def facade_sakai(P, block):
    """坂井家门楼（长屋门，参考 01、02），第二版（10-30）：正门（E）上方一座独立门楼，宽约 9 米、居中，
    门楼本体比两边矮墙高；大两坡瓦顶压得很低、很厚（前挑 2 米，檐口一圈厚藏青瓦边 + 山吹线），藏青屋脊 + 鬼瓦；
    檐下一条萌葱家纹幕；正中挂红底白家纹大幕（门楼宽的三分之一）；两侧一对大家纹提灯。
    第 0 排其它墙是两边的矮墙（平面图 height 就是矮墙高），墙顶压一道瓦。墙面三色幔留着当婚礼那天的布置（mat: plaster=maku_sanshoku）"""
    H = P.H; zw = 0.5 * CELL; x0, x1 = 0.5 * CELL, (P.w - 0.5) * CELL
    ex = [i for i in range(P.w) if P.at(i, 0) == "E"]
    cx = (ex[0] + 0.5) * CELL if ex else (x0 + x1) / 2
    gw, gd, Hg = 9.0, 5.0, H + 1.5                         # 门楼宽、进深、檐口高
    gx0, gx1 = cx - gw / 2, cx + gw / 2
    box("wood_dark", (cx, Hg / 2, zw - 0.06 - gd / 2), (gw, Hg, gd))                 # 门楼本体（焦茶）
    face("plaster_white", [(gx0, H, zw - 0.04), (gx1, H, zw - 0.04), (gx1, Hg, zw - 0.04), (gx0, Hg, zw - 0.04)], [(0, 0)] * 4, want=(0, 0, 1))
    for k in range(7): box("wood_dark", (gx0 + gw * k / 6, (H + Hg) / 2, zw - 0.02), (0.18, Hg - H, 0.12))   # 白壁上的焦茶柱
    box("wood_dark", (cx, H + 0.06, zw), (gw, 0.12, 0.14))
    yb0, yb1 = Hg - 0.75, Hg - 0.12                         # 萌葱家纹幕带（每 1.5 米一个家纹）
    face("maku_green", [(gx0, yb0, zw + 0.02), (gx1, yb0, zw + 0.02), (gx1, yb1, zw + 0.02), (gx0, yb1, zw + 0.02)], [(0, 0), (gw / 1.5, 0), (gw / 1.5, 1), (0, 1)], want=(0, 0, 1))
    # 大瓦顶：压低、加厚
    gable("roof", gx0 - 1.2, gx1 + 1.2, zw - gd - 1.2, zw + 2.0, Hg, Hg + 3.2)
    for zz, ww in ((zw + 2.0, gw + 2.4), (zw - gd - 1.2, gw + 2.4)):
        box("navy", (cx, Hg - 0.16, zz), (ww, 0.32, 0.3)); box("ochre", (cx, Hg - 0.33, zz + (0.16 if zz > zw else -0.16)), (ww, 0.05, 0.03))
    for xx in (gx0 - 1.2, gx1 + 1.2): box("navy", (xx, Hg + 1.6, zw - gd / 2 + 0.4), (0.3, 0.3, gd + 3.2))   # 山墙边的厚瓦
    zr = zw + (2.0 - gd - 1.2) / 2
    box("navy", (cx, Hg + 3.25, zr), (gw + 2.0, 0.42, 0.55))
    for xx in (gx0 - 0.9, gx1 + 0.9): sphere("ochre", (xx, Hg + 3.5, zr), 0.38)
    for k in range(int((gw + 2.2) / 0.5)): box("wood_dark", (gx0 - 1.0 + k * 0.5, Hg - 0.02, zw + 1.0), (0.09, 0.09, 1.9))   # 椽头
    # 红底白家纹大幕（门楼宽的三分之一）+ 两侧大家纹提灯
    nw = gw / 3; ny0, ny1 = 0.95, yb0 - 0.05
    face("noren_kamon", [(cx - nw / 2, ny0, zw + 0.16), (cx + nw / 2, ny0, zw + 0.16), (cx + nw / 2, ny1, zw + 0.16), (cx - nw / 2, ny1, zw + 0.16)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
    box("ink", (cx, ny1 + 0.03, zw + 0.16), (nw + 0.2, 0.06, 0.06))
    for sx in (-1, 1):
        lx = cx + sx * (nw / 2 + 1.2)
        chochin((lx, 1.0, zw + 0.9), key="chochin_kamon", k=2.6)
        box("ink", (lx, (1.0 + 1.3 + Hg) / 2, zw + 0.9), (0.02, Hg - 2.3, 0.02))
    # 两边矮墙压一道瓦（门楼以外的第 0 排）
    for (a, b) in ((x0 - 0.2, gx0), (gx1, x1 + 0.2)):
        if b - a > 0.1: pent_roof(a, b, zw - 0.25, H + 0.35, 0.65, drop=0.35, thick=0.12)


def gable(key, x0, x1, z0, z1, y_eave, y_ridge, ridge_along_x=True):
    """两坡屋顶（藏青瓦）：屋脊沿 x（或沿 z），两坡从檐口 y_eave 到屋脊 y_ridge，两头三角山墙用 kage 墨色封上"""
    if ridge_along_x:
        zm = (z0 + z1) / 2
        face(key, [(x0, y_eave, z0), (x1, y_eave, z0), (x1, y_ridge, zm), (x0, y_ridge, zm)], [(0, 0), (x1 - x0, 0), (x1 - x0, 1), (0, 1)], want=(0, 1, -1))
        face(key, [(x0, y_eave, z1), (x1, y_eave, z1), (x1, y_ridge, zm), (x0, y_ridge, zm)], [(0, 0), (x1 - x0, 0), (x1 - x0, 1), (0, 1)], want=(0, 1, 1))
        for x, sg in ((x0, -1), (x1, 1)): face("kage", [(x, y_eave, z0), (x, y_eave, z1), (x, y_ridge, zm)], [(0, 0)] * 3, want=(sg, 0, 0))
    else:
        xm = (x0 + x1) / 2
        face(key, [(x0, y_eave, z0), (x0, y_eave, z1), (xm, y_ridge, z1), (xm, y_ridge, z0)], [(0, 0), (z1 - z0, 0), (z1 - z0, 1), (0, 1)], want=(-1, 1, 0))
        face(key, [(x1, y_eave, z0), (x1, y_eave, z1), (xm, y_ridge, z1), (xm, y_ridge, z0)], [(0, 0), (z1 - z0, 0), (z1 - z0, 1), (0, 1)], want=(1, 1, 0))
        for z, sg in ((z0, -1), (z1, 1)): face("kage", [(x0, y_eave, z), (x1, y_eave, z), (xm, y_ridge, z)], [(0, 0)] * 3, want=(0, 0, sg))


def machiya(P, x0, x1, zf, seed):
    """町家一间（正面朝 -z，对着万屋）：一楼焦茶格子门面 + 门口藏青暖帘和红提灯，二楼白墙格子窗，出檐 + 两坡大屋顶"""
    import random
    rnd = random.Random(seed); W_ = x1 - x0; xm = (x0 + x1) / 2; d = 7.0
    h1, h2 = 3.0, rnd.uniform(2.0, 2.5)
    box(P.R("kokabe"), (xm, h1 / 2, zf + d / 2), (W_ - 0.05, h1, d))
    face("koshiita", [(x0 + 0.05, 0, zf - 0.01), (x1 - 0.05, 0, zf - 0.01), (x1 - 0.05, 2.3, zf - 0.01), (x0 + 0.05, 2.3, zf - 0.01)], [(0, 0), (W_, 0), (W_, 2.3), (0, 2.3)], want=(0, 0, -1))
    dx = xm + rnd.uniform(-0.6, 0.6)
    face("navy", [(dx - 0.45, 1.3, zf - 0.03), (dx + 0.45, 1.3, zf - 0.03), (dx + 0.45, 2.25, zf - 0.03), (dx - 0.45, 2.25, zf - 0.03)], [(0, 0)] * 4, want=(0, 0, -1))   # 暖帘
    chochin((dx + 0.75, 2.0, zf - 0.35))
    for xx in (x0 + 0.08, x1 - 0.08): box(P.R("wood"), (xx, (h1 + h2) / 2, zf + 0.05), (0.16, h1 + h2, 0.16))
    face(P.R("roof"), [(x0, h1 - 0.1, zf - 0.9), (x1, h1 - 0.1, zf - 0.9), (x1, h1 + 0.35, zf + 0.4), (x0, h1 + 0.35, zf + 0.4)], [(0, 0), (W_, 0), (W_, 1), (0, 1)], want=(0, 1, -1))   # 一楼出檐
    box(P.R("kokabe"), (xm, h1 + h2 / 2, zf + 0.4 + d / 2), (W_ - 0.05, h2, d))
    face("lattice", [(x0 + 0.5, h1 + 0.5, zf + 0.39), (x1 - 0.5, h1 + 0.5, zf + 0.39), (x1 - 0.5, h1 + h2 - 0.4, zf + 0.39), (x0 + 0.5, h1 + h2 - 0.4, zf + 0.39)], [(0, 0), (W_ - 1, 0), (W_ - 1, 1), (0, 1)], want=(0, 0, -1))
    gable(P.R("roof"), x0 - 0.1, x1 + 0.1, zf - 0.4, zf + d + 0.8, h1 + h2, h1 + h2 + rnd.uniform(1.4, 2.0))


def surroundings(P):
    """外景四周（surround: machi）：地面往外铺到 40 米，水道对岸一排町家，两侧邻家墙后露出屋顶，远处一圈墨色屋顶剪影 + 零星亮窗。
    背对万屋看时不再是地面到头就是虚空"""
    import random
    Wm, Dm = P.w * CELL, P.h * CELL; R_ = 40.0; g = P.R("earth")
    for r in ((-R_, -R_, Wm + R_, 0), (-R_, Dm, Wm + R_, Dm + R_), (-R_, 0, 0, Dm), (Wm, 0, Wm + R_, Dm)):
        x0, z0, x1, z1 = r
        face(g, [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)], [(x0 / CELL, -z0 / CELL), (x1 / CELL, -z0 / CELL), (x1 / CELL, -z1 / CELL), (x0 / CELL, -z1 / CELL)], want=(0, 1, 0))
    zf = Dm + 3.2; x = -12.0; k = 0   # 对面町家，宽 3.6~5.5 米不等
    rnd = random.Random(7)
    while x < Wm + 12:
        w_ = rnd.choice((3.64, 4.55, 5.46)); machiya(P, x, x + w_, zf, k); x += w_; k += 1
    # 火见橹（参考帧 01 左边远处的瞭望塔）：四根焦茶柱 + 斜撑 + 顶上小屋顶和吊钟
    fx, fz, fh = -9.0, -9.0, 13.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            obox("wood_dark", (fx + sx * 1.2, fz + sz * 1.2), (fx + sx * 0.5, fz + sz * 0.5 + 0.001), 0.18, 0, 0.2)
            box("wood_dark", (fx + sx * (0.85 - 0.0), fh / 2, fz + sz * 0.85), (0.16, fh, 0.16))
    for k in range(1, 7):
        y = fh * k / 7
        for sz in (-1, 1): box("wood_dark", (fx, y, fz + sz * 0.85), (1.86, 0.1, 0.1))
        for sx in (-1, 1): box("wood_dark", (fx + sx * 0.85, y, fz), (0.1, 0.1, 1.86))
    box("wood_dark", (fx, fh, fz), (2.2, 0.15, 2.2)); box("crimson", (fx, fh + 0.45, fz + 1.05), (2.2, 0.06, 0.06))
    gable("roof", fx - 1.3, fx + 1.3, fz - 1.3, fz + 1.3, fh + 1.5, fh + 2.3)
    sphere("ochre", (fx, fh + 0.9, fz), 0.3)
    for (x0, x1) in ((-7.0, 0.0), (Wm, Wm + 7.0)):   # 两侧邻家：墙后的屋顶
        gable(P.R("roof"), x0, x1, -1.0, Dm + 0.5, 4.2, 6.4, ridge_along_x=False)
    for n in range(40):   # 远处剪影：离中心 28~45 米的一圈，避开万屋背后（那边有大楼挡着）
        a = 2 * math.pi * n / 40 + rnd.uniform(-0.05, 0.05); r = rnd.uniform(28, 45)
        cx, cz = Wm / 2 + math.cos(a) * r, Dm / 2 + math.sin(a) * r
        w_, d_, h_ = rnd.uniform(6, 11), rnd.uniform(5, 8), rnd.uniform(4, 9)
        box("kage", (cx, h_ / 2, cz), (w_, h_, d_))
        gable("kage", cx - w_ / 2 - 0.4, cx + w_ / 2 + 0.4, cz - d_ / 2 - 0.4, cz + d_ / 2 + 0.4, h_, h_ + rnd.uniform(1.5, 3.0))
        for _ in range(rnd.randint(0, 3)):   # 亮着的窗（朝中心那面）
            wy = rnd.uniform(1.5, h_ - 1.0); wx = rnd.uniform(-w_ / 2 + 1, w_ / 2 - 1)
            nx, nz = -math.cos(a), -math.sin(a)
            tx, tz = -nz, nx
            px, pz = cx + nx * (abs(nx) * w_ / 2 + abs(nz) * d_ / 2 + 0.02) + tx * wx * 0.6, cz + nz * (abs(nx) * w_ / 2 + abs(nz) * d_ / 2 + 0.02) + tz * wx * 0.6
            face("ochre", [(px - tx * 0.5, wy, pz - tz * 0.5), (px + tx * 0.5, wy, pz + tz * 0.5), (px + tx * 0.5, wy + 0.7, pz + tz * 0.5), (px - tx * 0.5, wy + 0.7, pz - tz * 0.5)], [(0, 0)] * 4, want=(nx, 0, nz))


def wbox(key, c, axis, length, thick, y0, y1, block=None):
    cx, cz = c
    s = (length, y1 - y0, thick) if axis == "x" else (thick, y1 - y0, length)
    box(key, (cx, (y0 + y1) / 2, cz), s)
    if block is not None: block.append((cx - s[0] / 2, cz - s[2] / 2, cx + s[0] / 2, cz + s[2] / 2))


def obox(key, p0, p1, thick, y0, y1, segs=None):
    """沿任意水平方向的长方体（斜墙用）：p0→p1 是中线（xz，米）"""
    ax, az = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(ax, az); ux, uz = ax / L, az / L; nx, nz = -uz, ux
    t = thick / 2
    c = lambda s, n, y: (p0[0] + ux * s + nx * n, y, p0[1] + uz * s + nz * n)
    for n_sg in (-1, 1):   # 两个大面
        face(key, [c(0, n_sg * t, y0), c(L, n_sg * t, y0), c(L, n_sg * t, y1), c(0, n_sg * t, y1)], [(0, y0), (L, y0), (L, y1), (0, y1)], want=(nx * n_sg, 0, nz * n_sg))
    for s_sg, s in ((-1, 0), (1, L)):   # 两头
        face(key, [c(s, -t, y0), c(s, t, y0), c(s, t, y1), c(s, -t, y1)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(ux * s_sg, 0, uz * s_sg))
    for y, sg in ((y0, -1), (y1, 1)):
        face(key, [c(0, -t, y), c(L, -t, y), c(L, t, y), c(0, t, y)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, sg, 0))
    if segs is not None: segs.append((p0[0], p0[1], p1[0], p1[1], t))


def wall_faces(axis, cx, cz, off):
    """贴在墙格两面的贴花：返回 [(把 (横向 a, 高 y) 变成三维点的函数, 法线)]，两面 a 都是从看的人左边到右边"""
    out = []
    for sg in (-1, 1):
        if axis == "x": out.append(((lambda a, y, sg=sg: (cx - sg * a, y, cz + sg * off)), (0, 0, sg)))
        else: out.append(((lambda a, y, sg=sg: (cx + sg * off, y, cz + sg * a)), (sg, 0, 0)))
    return out


def poly_decal(key, outline, uvf, axis, cx, cz, off):
    """一块多边形贴花（从形心扇形三角化，星形多边形都行），两面各一块"""
    mx = sum(p[0] for p in outline) / len(outline); my = sum(p[1] for p in outline) / len(outline)
    for to3, n in wall_faces(axis, cx, cz, off):
        for k in range(len(outline)):
            a, b = outline[k], outline[(k + 1) % len(outline)]
            face(key, [to3(mx, my), to3(*a), to3(*b)], [uvf(mx, my), uvf(*a), uvf(*b)], want=n)


FANLIGHT_KEYS = ["fanlight_lotus", "fanlight_star", "fanlight_crest"]


def fanlight(P, cx, cz, axis, n=0, wide=False):
    """门楣上的半圆彩色玻璃（万屋）：贴在小壁两面，半径到柱边。平面图 fanlight: big 时半径放大到 0.8 格、盖过两侧墙格
    （八角厅参考 11 的大拱窗），花样在莲花 / 五芒星 / 家纹三种里轮换"""
    big = P.cfg.get("fanlight") == "big"
    r, y0 = (CELL * (1.25 if wide else 0.8) if big else CELL / 2 - P.post / 2 - 0.02), P.kamoi + 0.07 * P.k   # wide：正门那扇，罩住两旁的玻璃门（门厅参考 05）
    r = min(r, P.H - y0 - 0.15)
    key = FANLIGHT_KEYS[n % 3] if big else "fanlight"
    off = T_WALL / 2 + 0.012 if big else T_WALL * 0.4 + 0.004
    pts = [(math.cos(math.pi * k / 24) * r, y0 + math.sin(math.pi * k / 24) * r) for k in range(25)]
    frame = [(x * 1.08, y0 + (y - y0) * 1.08) for x, y in pts]
    poly_decal(P.R("wood"), frame + [(-r * 1.08, y0)], lambda a, y: (0, 0), axis, cx, cz, off)
    poly_decal(key, pts + [(-r, y0)], lambda a, y: (0.5 + a / (2 * r), (y - y0) / r), axis, cx, cz, off + 0.004)


def katomado(P, cx, cz, axis):
    """火灯窗（万屋长廊，参考帧 10）：矮胖的钟形，下摆外张、两肩外撇、上面尖拱；焦茶外框 + 山吹细框 + 格子"""
    def bell(s):
        """宽约 0.72、高约 0.82 米（宽高差不多）"""
        def hw(y):
            if y <= 0.42: return 0.29 + 0.07 * (1 - y / 0.42) ** 2          # 下摆往外张
            if y <= 0.52: return 0.29 + 0.04 * math.sin((y - 0.42) / 0.10 * math.pi / 2)   # 两肩外撇
            t = (y - 0.52) / 0.30; return 0.33 * max(0.0, math.cos(t * math.pi / 2)) ** 0.7   # 尖拱
        ys = [k / 40 * 0.82 for k in range(41)]
        right = [(hw(y) * s, y * s) for y in ys]
        return [(-0.36 * s, 0.0)] + right + [(-x, y) for x, y in reversed(right[1:-1])]
    y0 = 0.95
    lift = lambda pts, dy: [(x, y0 + dy + y) for x, y in pts]
    poly_decal(P.R("wood"), lift(bell(1.18), -0.07), lambda a, y: (0, 0), axis, cx, cz, T_WALL / 2 + 0.004)
    poly_decal("ochre", lift(bell(1.06), -0.025), lambda a, y: (0, 0), axis, cx, cz, T_WALL / 2 + 0.007)
    poly_decal("lattice", lift(bell(1.0), 0), lambda a, y: (a / 0.5 + 0.5, (y - y0) / 0.5), axis, cx, cz, T_WALL / 2 + 0.010)


def mural_decal(P, i, j, axis, cx, cz):
    """M 格：土壁下半截贴一幅画，连成一排的 M 共用一幅（u 按这一排从头到尾），画是 mural（默认大奥左墙美人画，平面图 mural: 换）"""
    di, dj = (1, 0) if axis == "x" else (0, 1)
    a = 0
    while P.at(i - (a + 1) * di, j - (a + 1) * dj) == "M": a += 1
    n = 1
    while P.at(i - a * di + n * di, j - a * dj + n * dj) == "M": n += 1
    key = P.cfg.get("mural", "mural_L"); y0, y1 = max(0.3, P.koshi + 0.08), P.nageshi - 0.08
    if P.on("mural_full"): y0, y1 = 0.06, P.H - 0.06   # 整面墙一幅画（大座敷凸间的美人画屏风）：长押、腰板在 M 格上让开
    for to3, nrm in wall_faces(axis, cx, cz, T_WALL / 2 + 0.006):
        h = CELL / 2
        # wall_faces 两面的 a 方向相反，u 跟着翻，保证两面看到的都是正的画
        sgn = 1 if (nrm[0] + nrm[2]) > 0 else -1
        ua = lambda aa: (a + (aa + h) / CELL) / n if sgn > 0 else (a + (h - aa) / CELL) / n
        face(key, [to3(-h, y0), to3(h, y0), to3(h, y1), to3(-h, y1)], [(ua(-h), 0), (ua(h), 0), (ua(h), 1), (ua(-h), 1)], want=nrm)


def panel(P, i, j, axis, key, c):
    """一扇襖 / 障子 / 楼梯口襖 / 玻璃门的两面贴图（框在 plan_walls 里）。襖绘按整排连续（u = 沿轴格数 / 4）"""
    cx, cz = P.center(i, j); L, Hh = CELL, P.kamoi; y0 = P.base(i, j)
    inset = 0.025 if key in ("fusuma", "fusuma2", "glassdoor") else 0.0
    span = int(P.cfg.get("fusuma_span", "4"))   # 一幅襖绘横跨几扇（坂井家雄鸡襖 6、浪涛襖 5），从这一排的第一扇算起
    if key in ("fusuma", "fusuma2"):
        ch = P.at(i, j); di, dj = (1, 0) if axis == "x" else (0, 1); a = 0
        while P.at(i - (a + 1) * di, j - (a + 1) * dj) == ch: a += 1
        u0, u1 = (a % span) / span, (a % span + 1) / span
    else: u0, u1 = 0, 1
    off = T_PANEL / 2 + 0.002
    for sg in (-1, 1):
        if axis == "x":
            z = cz + sg * off; a, b = cx - L / 2 + inset, cx + L / 2 - inset
            pts = [(a, y0 + inset, z), (b, y0 + inset, z), (b, Hh - inset, z), (a, Hh - inset, z)]; n = (0, 0, sg)
        else:
            x = cx + sg * off; a, b = cz - L / 2 + inset, cz + L / 2 - inset
            pts = [(x, y0 + inset, a), (x, y0 + inset, b), (x, Hh - inset, b), (x, Hh - inset, a)]; n = (sg, 0, 0)
        # 两面各按"站在这一面看过去从左到右"排 u：法线朝 +x 或 -z 的那面要左右翻，不然有一面的襖绘是反的（坂井家雄鸡襖发现的）
        m0, m1 = (1 - u0, 1 - u1) if (axis == "z" and sg == 1) or (axis == "x" and sg == -1) else (u0, u1)   # 整幅一起镜像（扇的顺序和每扇里面都翻）
        face(P.R(key), pts, [(m0, 0), (m1, 0), (m1, 1), (m0, 1)], want=n)


def plan_walls(P, block, segs):
    H = P.H; posts = set(); free = set()   # free：平面图上的 o，门厅柱网这种独立柱，比墙里的柱再粗一档
    for j in range(P.h):
        for i in range(P.w):
            c = P.at(i, j)
            if c == "o": free.add(P.center(i, j)); continue
            if c not in WALLS: continue
            cx, cz = P.center(i, j); axis = P.wall_axis(i, j)
            if c in "FSUDGEHN" and axis:
                b0 = P.base(i, j)
                if c != "D":
                    panel(P, i, j, axis, PANELS[c], (cx, cz))
                    wbox(P.R("wood") if c == "S" else P.R("frame"), (cx, cz), axis, CELL, T_PANEL, b0, P.kamoi, block)   # 框，贴图面在 panel() 里
                k = P.k
                wbox(P.R("wood"), (cx, cz), axis, CELL, T_WALL * min(k, 1.4), P.kamoi, P.kamoi + 0.07 * k)  # 鸭居
                wbox(P.R("kokabe"), (cx, cz), axis, CELL, T_WALL * 0.8, P.kamoi + 0.07 * k, H)            # 小壁
                wbox(P.R("wood"), (cx, cz), axis, CELL, T_WALL + 0.05 * k, P.nageshi, P.nageshi + 0.1 * k)  # 长押
                wbox(P.R("wood"), (cx, cz), axis, CELL, T_WALL, b0, b0 + 0.015)                       # 敷居
                big = P.cfg.get("fanlight") == "big"
                nextE = big and any(P.at(i + (d if axis == "x" else 0), j + (d if axis == "z" else 0)) == "E" for d in (-1, 1))   # 正门旁边的玻璃门：让正门那扇大的罩住
                if c in "DGEU" and (P.on("fanlight") or big) and H - P.kamoi > 0.55 and (c != "U" or big) and not (c == "G" and nextE):
                    fanlight(P, cx, cz, axis, i + j, wide=(c == "E" and big))
                for sg in (-1, 1):   # 和不同种类的墙格交界处立柱
                    di, dj = (sg, 0) if axis == "x" else (0, sg)
                    if P.wall(i + di, j + dj) and P.at(i + di, j + dj) != c:
                        posts.add((cx + di * CELL / 2, cz + dj * CELL / 2))
                continue
            # 土壁（含火灯窗格、斜墙，拐角上的襖、障子也按土壁）：从中心往每个连着的方向伸到格边 / 格角。
            # 下半截（到长押）是 plaster，长押以上是 kokabe，万屋用来做"珊瑚墙 + 白小壁"；
            # 设了 koshi 的话最下面再一截腰板（万屋门厅：焦茶竖板条齐腰高），腰板顶上压一根木条
            nb = P.links(i, j)
            straight = len(nb) == 2 and nb[0][0] == -nb[1][0] and nb[0][1] == -nb[1][1]
            full = c == "M" and P.on("mural_full")
            for dx, dz in nb:
                ext = T_WALL / 2 if dx == 0 or dz == 0 else 0.03
                L = math.hypot(dx, dz) * CELL / 2 + ext; ux, uz = dx / math.hypot(dx, dz), dz / math.hypot(dx, dz)
                p0, p1 = (cx, cz), (cx + ux * L, cz + uz * L)
                if P.koshi > 0 and not full:
                    obox(P.R("koshi"), p0, p1, T_WALL + 0.02, -P.doma, P.koshi, segs)
                    obox(P.R("wood"), p0, p1, T_WALL + 0.04, P.koshi, P.koshi + 0.04 * P.k)
                    obox(P.R("plaster"), p0, p1, T_WALL, P.koshi + 0.04 * P.k, P.nageshi)
                else:
                    obox(P.R("plaster"), p0, p1, T_WALL, -P.doma, P.nageshi, segs)
                if full: obox(P.R("plaster"), p0, p1, T_WALL, P.nageshi, H)
                else:
                    obox(P.R("wood"), p0, p1, T_WALL + 0.05 * P.k, P.nageshi, P.nageshi + 0.1 * P.k)
                    obox(P.R("kokabe"), p0, p1, T_WALL, P.nageshi + 0.1 * P.k, H)
            if c == "K" and axis: katomado(P, cx, cz, axis)
            if c == "M" and axis: mural_decal(P, i, j, axis, cx, cz)
            if not nb: posts.add((cx, cz))
            elif not straight or (not full and ((axis == "x" and i % 2 == 0) or (axis == "z" and j % 2 == 0))):
                posts.add((cx, cz))   # 整面画的墙（mural_full）中间不立柱，只留两头
    for pts, size in ((posts, P.post), (free, P.post * 1.35)):
        for (x, z) in pts:
            box(P.R("wood"), (x, (H - P.doma) / 2, z), (size, H + P.doma, size))
            block.append((x - size / 2, z - size / 2, x + size / 2, z + size / 2))


def plan_furniture(P, block):
    """家具格：P 高台、R 柜台、Y 屏风（一排一组），h 椅子（一格一把，背靠墙、朝房间）"""
    for ch in "PRY":
        for reg in P.regions(lambda i, j, ch=ch: P.at(i, j) == ch):
            xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
            x0, z0, x1, z1 = mrect((min(xs), min(zs), max(xs) + 1, max(zs) + 1))
            if ch == "P":   # 高台：青磁侧面 + 地毯台面 + 山吹压边
                h = 0.32
                box(P.R("dais_side"), ((x0 + x1) / 2, h / 2, (z0 + z1) / 2), (x1 - x0, h, z1 - z0))
                face("dais", [(x0, h + 0.002, z0), (x1, h + 0.002, z0), (x1, h + 0.002, z1), (x0, h + 0.002, z1)], [(0, 1), (1, 1), (1, 0), (0, 0)], want=(0, 1, 0))
                for (a, b, c_, d) in ((x0, z0, x1, z0), (x0, z1, x1, z1), (x0, z0, x0, z1), (x1, z0, x1, z1)):
                    box("ochre", ((a + c_) / 2, h + 0.02, (b + d) / 2), (max(c_ - a, 0.06), 0.04, max(d - b, 0.06)))
                block.append((x0, z0, x1, z1))
                if P.on("dais_items"):   # 台面摆设：中间深红坐垫 + 小肘几，一角漆盒，一角高脚烛台
                    mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
                    box("crimson", (mx, h + 0.06, mz), (0.7, 0.1, 0.7)); box("ochre", (mx, h + 0.115, mz), (0.62, 0.01, 0.62))
                    box("ink", (mx, h + 0.22, mz - 0.55), (0.6, 0.04, 0.22))
                    for sx in (-0.25, 0.25): box("ink", (mx + sx, h + 0.11, mz - 0.55), (0.04, 0.2, 0.2))
                    box("ink", (x0 + 0.35, h + 0.15, z0 + 0.35), (0.34, 0.28, 0.34)); box("ochre", (x0 + 0.35, h + 0.3, z0 + 0.35), (0.36, 0.03, 0.36))
                    cylinder("ochre", (x1 - 0.3, h, z0 + 0.3), 0.025, 0.85, seg=8); cylinder("ink", (x1 - 0.3, h, z0 + 0.3), 0.12, 0.04, seg=10)
                    cylinder("crimson", (x1 - 0.3, h + 0.85, z0 + 0.3), 0.07, 0.05, seg=10); cylinder("paper", (x1 - 0.3, h + 0.9, z0 + 0.3), 0.02, 0.12, seg=6)
            elif ch == "R":   # 柜台
                m = 0.12
                box(P.R("wood"), ((x0 + x1) / 2, 0.47, (z0 + z1) / 2), (x1 - x0 - 2 * m, 0.94, z1 - z0 - 2 * m))
                box("ochre", ((x0 + x1) / 2, 0.97, (z0 + z1) / 2), (x1 - x0 - m, 0.05, z1 - z0 - m))
                block.append((x0 + m, z0 + m, x1 - m, z1 - m))
                if P.on("counter_sign"):   # 柜台正面（朝 +z）挂"同"字圆牌（八角厅接待台，参考 11）
                    mx, r = (x0 + x1) / 2, 0.3; zf = z1 - m + 0.006
                    pts = [(mx + math.cos(2 * math.pi * k / 20) * r, 0.5 + math.sin(2 * math.pi * k / 20) * r, zf) for k in range(20)]
                    face("dou_sign", pts, [(0.5 + 0.5 * math.cos(2 * math.pi * k / 20), 0.5 + 0.5 * math.sin(2 * math.pi * k / 20)) for k in range(20)], want=(0, 0, 1))
            else:             # 屏风：沿长边折成之字，两面贴 byobu
                along_x = (x1 - x0) >= (z1 - z0)
                n = len(reg) * 2; L = max(x1 - x0, z1 - z0); h = float(P.cfg.get("byobu_h", "1.75"))   # 屏风高（坂井家里间的金屏风放大到 2.6）
                pts = []
                for k in range(n + 1):
                    s = L * k / n; o = 0.07 * (1 if k % 2 else -1)
                    pts.append((x0 + s, (z0 + z1) / 2 + o) if along_x else ((x0 + x1) / 2 + o, z0 + s))
                for k in range(n):
                    (ax, az), (bx, bz) = pts[k], pts[k + 1]
                    face(P.R("byobu"), [(ax, 0.02, az), (bx, 0.02, bz), (bx, h, bz), (ax, h, az)], [(k / n, 0), ((k + 1) / n, 0), ((k + 1) / n, 1), (k / n, 1)])
                    box(P.R("frame"), ((ax + bx) / 2, h, (az + bz) / 2), (abs(bx - ax) + 0.03, 0.04, abs(bz - az) + 0.03))
                cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
                block.append((x0, cz - 0.12, x1, cz + 0.12) if along_x else (cx - 0.12, z0, cx + 0.12, z1))
    for j in range(P.h):
        for i in range(P.w):
            if P.at(i, j) == "r":
                cx, cz = P.center(i, j); k = float(P.cfg.get("rock_scale", "1")); rock(cx, cz, i * 31 + j, k)
                block.append((cx - 0.45 * k, cz - 0.45 * k, cx + 0.45 * k, cz + 0.45 * k))
            ch = P.at(i, j); cx, cz = P.center(i, j)
            if ch in "pcZJWXQO": sakai_prop(ch, cx, cz, P, block, i * 11 + j * 3)
            if P.at(i, j) == "w":   # 竹丛（室内庭，参考 12 右边）：几根青磁竹竿 + 萌葱竹叶
                cx, cz = P.center(i, j); bamboo(cx, cz, i * 7 + j * 3)
                block.append((cx - 0.3, cz - 0.3, cx + 0.3, cz + 0.3))
            if P.at(i, j) == "k":
                cx, cz = P.center(i, j); kage(cx, cz, i * 17 + j * 7)
                block.append((cx - 0.25, cz - 0.25, cx + 0.25, cz + 0.25))
            if P.at(i, j) == "l":   # 吊灯笼：提灯挂在天花下 1.3 米，墨色吊绳
                cx, cz = P.center(i, j); y = P.H - 1.3
                chochin((cx, y, cz)); box("ink", (cx, (y + 0.5 + P.H) / 2, cz), (0.015, P.H - y - 0.5, 0.015))
            if P.at(i, j) == "L":   # 石灯笼（外景桥头）：笠、火袋（亮着山吹）、竿、台座
                cx, cz = P.center(i, j)
                box("stone", (cx, 0.12, cz), (0.6, 0.24, 0.6)); cylinder("stone", (cx, 0.24, cz), 0.12, 0.8, seg=8)
                box("stone", (cx, 1.1, cz), (0.5, 0.12, 0.5)); box("ochre", (cx, 1.36, cz), (0.32, 0.4, 0.32))
                cone("stone", (cx, 1.56, cz), 0.48, 0.05, 0.32, seg=6); sphere("stone", (cx, 1.92, cz), 0.08)
                block.append((cx - 0.32, cz - 0.32, cx + 0.32, cz + 0.32))
            if P.at(i, j) == "t":
                cx, cz = P.center(i, j); toys(cx, cz, i * 13 + j * 5)
                block.append((cx - 0.25, cz - 0.25, cx + 0.25, cz + 0.25))
    W, D = P.w / 2, P.h / 2
    for j in range(P.h):
        for i in range(P.w):
            if P.at(i, j) != "h": continue
            cx, cz = P.center(i, j)
            back = next(((dx, dz) for dx, dz in DIRS.values() if P.wall(i + dx, j + dz)), None)
            if back is None:   # 不靠墙：背朝离房间中心远的那边
                v = (i + 0.5 - W, j + 0.5 - D); back = (1 if v[0] > 0 else -1, 0) if abs(v[0]) >= abs(v[1]) else (0, 1 if v[1] > 0 else -1)
            sc = float(P.cfg.get("chair_scale", "1")); chair(cx, cz, back, sc)
            block.append((cx - 0.3 * sc, cz - 0.3 * sc, cx + 0.3 * sc, cz + 0.3 * sc))


def toys(cx, cz, seed):
    """座敷童子的"孩子"：地上散落的小玩具——手鞠、陀螺、茶盘（按 seed 挑两三样）"""
    import random
    rnd = random.Random(seed)
    for k in range(rnd.randint(2, 3)):
        x, z = cx + rnd.uniform(-0.25, 0.25), cz + rnd.uniform(-0.25, 0.25); kind = rnd.choice(("temari", "koma", "tray"))
        if kind == "temari":
            r = 0.09; sphere(rnd.choice(["coral", "crimson", "teal"]), (x, r, z), r, seg=12, rings=8)
            cylinder("ochre", (x, r - 0.012, z), r * 1.02, 0.024, seg=12, caps=False)
        elif kind == "koma":
            cone("navy", (x, 0.0, z), 0.0, 0.07, 0.07, seg=10); cylinder("ochre", (x, 0.07, z), 0.07, 0.02, seg=10)
            cylinder("crimson", (x, 0.09, z), 0.012, 0.05, seg=6)
        else:
            box("ink", (x, 0.02, z), (0.32, 0.04, 0.22)); box("ochre", (x, 0.042, z), (0.3, 0.004, 0.2))
            for dx in (-0.07, 0.07): cylinder("paper", (x + dx, 0.044, z), 0.035, 0.05, seg=10)


def chair(cx, cz, back, k=1.0):
    """洋式扶手椅：藍色坐垫和靠背、山吹木框；k 整体放大（八角厅 1.3）"""
    bx, bz = back; px, pz = -bz, bx   # 靠背方向、横向
    at = lambda f, s, y: (cx + bx * f * k + px * s * k, y * k, cz + bz * f * k + pz * s * k)
    sz = lambda f, s, y: ((abs(bx) * f + abs(px) * s) * k, y * k, (abs(bz) * f + abs(pz) * s) * k)
    for f in (-0.22, 0.22):
        for s in (-0.22, 0.22): box("ochre", at(f, s, 0.2), sz(0.05, 0.05, 0.4))
    box("blue", at(0, 0, 0.45), sz(0.56, 0.5, 0.1))
    box("blue", at(0.24, 0, 0.85), sz(0.08, 0.5, 0.75))
    box("ochre", at(0.28, 0, 1.24), sz(0.06, 0.56, 0.06))
    for s in (-0.27, 0.27): box("ochre", at(0, s, 0.66), sz(0.56, 0.06, 0.06))


def oct_ceiling(P):
    """八角藻井（八角厅，参考 11）：天花下从中心放射八根焦茶梁到八角的角，两圈山吹环，中间一朵圆花。平面图 oct_ceiling: cx,cz,r（米）"""
    cx, cz, r = (float(v) for v in P.cfg["oct_ceiling"].split(","))
    y = P.H - 0.06
    corner = lambda k, rr: (cx + math.cos(math.pi / 8 + math.pi / 4 * k) * rr, cz + math.sin(math.pi / 8 + math.pi / 4 * k) * rr)
    for k in range(8):
        obox(P.R("wood"), (cx, cz), corner(k, r), 0.14, y - 0.08, y + 0.05)
        for rr, key in ((r * 0.55, "ochre"), (r, P.R("wood"))):
            obox(key, corner(k, rr), corner(k + 1, rr), 0.12, y - 0.1, y + 0.05)
    pts = [(cx + math.cos(2 * math.pi * k / 16) * 0.55, y - 0.12, cz + math.sin(2 * math.pi * k / 16) * 0.55) for k in range(16)]
    face("fanlight_lotus", pts, [(0.5 + 0.5 * math.cos(2 * math.pi * k / 16), 0.5 * abs(math.sin(2 * math.pi * k / 16))) for k in range(16)], want=(0, -1, 0))


def plan_rugs(P):
    """地毯（平面图 rug: x0,z0,x1,z1; …，单位是格，可以带小数）：深红底 + 山吹边，平铺在地面上一点点，人照常走"""
    for spec in filter(None, (t.strip() for t in P.cfg.get("rug", "").split(";"))):
        x0, z0, x1, z1 = (float(v) * CELL for v in spec.split(","))
        if P.cfg.get("rug_tex"):   # 贴图地毯（坂井家婚礼大座敷的鹤纹地毯）：整张贴，u 沿 x
            face(P.cfg["rug_tex"], [(x0, 0.008, z0), (x1, 0.008, z0), (x1, 0.008, z1), (x0, 0.008, z1)], [(0, 1), (1, 1), (1, 0), (0, 0)], want=(0, 1, 0))
            continue
        face("ochre", [(x0, 0.006, z0), (x1, 0.006, z0), (x1, 0.006, z1), (x0, 0.006, z1)], [(0, 0)] * 4, want=(0, 1, 0))
        m = 0.08
        face("crimson", [(x0 + m, 0.008, z0 + m), (x1 - m, 0.008, z0 + m), (x1 - m, 0.008, z1 - m), (x0 + m, 0.008, z1 - m)], [(0, 0)] * 4, want=(0, 1, 0))


def plan_ceiling(P):
    if P.cfg.get("oct_ceiling"): oct_ceiling(P)
    if P.cfg["ceiling"] == "none": return
    key = P.cfg["ceiling"]
    if P.cfg.get("ceiling_fit") == "room": return ceiling_fit(P, key)
    skip = set(t.strip() for t in P.cfg.get("ceiling_skip", "").split(",") if t.strip())   # 这些地面种类上不封顶（坂井家厨房外的后院白砂）
    for j in range(P.h):
        for i in range(P.w):
            if not P.floor(i, j) or P.floor(i, j) in skip: continue
            x0, z0, x1, z1 = mrect(P.cell_rect(i, j))
            pts = [(x0, P.H, z0), (x1, P.H, z0), (x1, P.H, z1), (x0, P.H, z1)]
            face(key, pts, [(p[0] / CELL, -p[2] / CELL) for p in pts], want=(0, -1, 0))


def ceiling_fit(P, key):
    """整片天花铺一张图（大座敷群鸡图）：UV 按所有地面格的外框 0..1 铺，不平铺"""
    rs = [mrect(P.cell_rect(i, j)) for j in range(P.h) for i in range(P.w) if P.floor(i, j)]
    bx0, bz0, bx1, bz1 = min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)
    for x0, z0, x1, z1 in rs:
        pts = [(x0, P.H, z0), (x1, P.H, z0), (x1, P.H, z1), (x0, P.H, z1)]
        face(key, pts, [((p[0] - bx0) / (bx1 - bx0), (p[2] - bz0) / (bz1 - bz0)) for p in pts], want=(0, -1, 0))


def walk_grid(P, walk, block, segs, cell=0.1, radius=0.25):
    Wm, Dm = P.w * CELL, P.h * CELL
    w, h = math.ceil(Wm / cell), math.ceil(Dm / cell)
    rows = []
    for j in range(h):
        z = (j + 0.5) * cell; row = []
        near = [b for b in block if b[1] - radius <= z <= b[3] + radius]
        nsegs = [s for s in segs if min(s[1], s[3]) - radius - s[4] <= z <= max(s[1], s[3]) + radius + s[4]]
        fl = [r for r in walk if r[1] <= z <= r[3]]
        for i in range(w):
            x = (i + 0.5) * cell
            ok = any(r[0] <= x <= r[2] for r in fl)
            if ok:
                for b in near:
                    dx = max(b[0] - x, 0, x - b[2]); dz = max(b[1] - z, 0, z - b[3])
                    if dx * dx + dz * dz < radius * radius: ok = False; break
            if ok:
                for (ax, az, bx, bz, t) in nsegs:   # 墙段（含斜墙）：点到线段距离
                    vx, vz = bx - ax, bz - az; ll = vx * vx + vz * vz
                    q = max(0, min(1, ((x - ax) * vx + (z - az) * vz) / ll)) if ll else 0
                    if math.hypot(x - ax - q * vx, z - az - q * vz) < radius + t: ok = False; break
            row.append("1" if ok else "0")
        rows.append("".join(row))
    out = {"name": P.cfg["name"], "_说明": "tools/kit_build.py 按 tools/kit_plans/<name>.txt 生成，别手改。格式见 docs/16_积木平面图格式.md 第四节",
           "cell": cell, "x0": 0, "z0": 0, "w": w, "h": h, "radius": radius, "rows": rows,
           "size": [round(Wm, 3), round(Dm, 3)], "height": P.H, "spawn": None, "views": {}, "stairs": [], "shots": P.shots}
    for j in range(P.h):
        for i in range(P.w):
            c = P.at(i, j); cx, cz = P.center(i, j)
            if c == "@": out["spawn"] = [round(cx, 3), round(cz, 3)]
            elif c.isdigit(): out["views"][c] = [round(cx, 3), round(cz, 3)]
            elif c in "UE":
                axis = P.wall_axis(i, j) or "x"
                for sg in (-1, 1):
                    nx, nz = ((0, sg) if axis == "x" else (sg, 0))
                    if P.floor(i + nx, j + nz):
                        out["stairs"].append({"door": [round(cx, 3), round(cz, 3)], "stand": [round(cx + nx * 0.5, 3), round(cz + nz * 0.5, 3)], "face": [-nx, -nz]})
    # 只留和出生点、观景点、楼梯口站位连着的格子：斜墙外侧、家具缝里会有走不到的小块，留着会让点地寻路和镜头去够它
    seeds = [out["spawn"]] + list(out["views"].values()) + [st["stand"] for st in out["stairs"]]
    grid = [list(r) for r in rows]; keep = set(); stack = []
    for sd in seeds:
        if sd:
            i, j = int(sd[0] / cell), int(sd[1] / cell)
            if 0 <= i < w and 0 <= j < h and grid[j][i] == "1": stack.append((i, j)); keep.add((i, j))
    while stack:
        i, j = stack.pop()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + di, j + dj)
            if 0 <= n[0] < w and 0 <= n[1] < h and n not in keep and grid[n[1]][n[0]] == "1": keep.add(n); stack.append(n)
    if keep:
        out["rows"] = ["".join("1" if (i, j) in keep else "0" for i in range(w)) for j in range(h)]
    if P.hfun:   # 有拱桥、下沉土间：出 floor（每格厘米，int16 小端 base64，走不到的格 -32768），和 walkmap.json 一个格式
        import base64, struct
        vals = []
        for j in range(h):
            for i in range(w):
                if out["rows"][j][i] != "1": vals.append(-32768); continue
                x, z = (i + 0.5) * cell, (j + 0.5) * cell
                ys = [f(x, z) for (r, f) in P.hfun if r[0] <= x <= r[2] and r[1] <= z <= r[3]]
                vals.append(round((max(ys) if ys else 0.0) * 100))
        out["floor"] = base64.b64encode(struct.pack(f"<{len(vals)}h", *vals)).decode()
    return out


def build_plan(name):
    G.clear()
    P = Plan(name); walk, block, segs = [], [], []
    plan_floors(P, walk, block); plan_walls(P, block, segs); plan_furniture(P, block); plan_ceiling(P); plan_rugs(P)
    if P.cfg.get("facade") == "wanya": facade(P, block)
    if P.cfg.get("facade") == "sakai": facade_sakai(P, block)
    if P.cfg.get("surround") == "machi": surroundings(P)
    WALK_OUT.mkdir(parents=True, exist_ok=True)
    wj = walk_grid(P, walk, block, segs)
    (WALK_OUT / f"{name}_walk.json").write_text(json.dumps(wj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = sum(r.count("1") for r in wj["rows"])
    print(f"   可走 {n} 格（{n * 0.01:.1f} 平方米），出生点 {wj['spawn']}，观景点 {list(wj['views'])}，楼梯口 {len(wj['stairs'])}")
    for st in wj["stairs"]:   # 楼梯口站位必须能站，不然转场后会卡住
        sx, sz = st["stand"]; ok = wj["rows"][int(sz / 0.1)][int(sx / 0.1)] == "1"
        if not ok: print("   !! 楼梯口站位不能站：", st)
    export(OUT / f"{name}.glb")


# ---------------------------------------------------------------- 大奥泼溅房间的门（游4）
# 泼溅房间门外那截走廊被 spz_clip 裁掉了，从房间里看门口是糊的。在每间房的门墙处（过道靠房间那头）立一对关着的金襖，
# 只在房间区块里加载（ooku.json 的房间区块写 kit: "ooku_doors"），走廊区块看到的还是泼溅里画的门。
OOKU_DOORS = [(3.9, -2.4, -1), (-3.95, -6.6, 1), (3.95, -11.0, -1), (-3.2, -12.5, 1)]   # (门的 x, 门中心 z, 朝房间外的 x 方向)；立在过道靠房间那头（门墙处），立在走廊那头的话走廊泼溅墙外脑补的幔帐会跑到门前面


def build_ooku_doors():
    W_, H_ = 1.9, 2.8
    for x, z, out in OOKU_DOORS:
        n = (-out, 0, 0)   # 朝房间里
        for k in range(2):
            z0, z1 = z - W_ / 2 + k * W_ / 2, z - W_ / 2 + (k + 1) * W_ / 2
            box("frame_crimson", (x + out * 0.03, H_ / 2, (z0 + z1) / 2), (0.05, H_, z1 - z0))
            pts = [(x - out * 0.002, 0.04, z0 + 0.04), (x - out * 0.002, 0.04, z1 - 0.04), (x - out * 0.002, H_ - 0.04, z1 - 0.04), (x - out * 0.002, H_ - 0.04, z0 + 0.04)]
            if out > 0: pts = [pts[1], pts[0], pts[3], pts[2]]
            u0, u1 = k / 4, (k + 1) / 4
            face("fusuma", pts, [(u0, 0), (u1, 0), (u1, 1), (u0, 1)], want=n)
        box("frame_crimson", (x + out * 0.03, H_ + 0.08, z), (0.12, 0.16, W_ + 0.3))   # 门楣
    export(OUT / "ooku_doors.glb")


# ---------------------------------------------------------------- 绘卷总地图的底稿（游5）
# 七个地点摆成微缩场景，沿 x 排成长卷（每个地点占 10 米），中间一条蜿蜒的河，地点之间飘金霞（すやり霞）。
# 用 kit_view.html?glb=map_diorama 拍成 3840×1280 的长图（tools/kit_shots.sh map），再交给图片模型按色板重画（花积分前先问）。
MAP_PLACES = [("ooku", "大奥"), ("wanya", "万屋"), ("sakai", "坂井家"), ("fuenokoji", "笛小路家"), ("solaris", "そらりす丸"), ("subway", "地下铁"), ("prison", "牢房")]
MAP_STEP = 10.0


def hall(cx, cz, w, d, h, wall, pillar, roof_h=1.0, roof="roof"):
    box(wall, (cx, h / 2, cz), (w, h, d))
    for sx in (-1, 1):
        for sz in (-1, 1): box(pillar, (cx + sx * w / 2, h / 2, cz + sz * d / 2), (0.14, h, 0.14))
    gable(roof, cx - w / 2 - 0.3, cx + w / 2 + 0.3, cz - d / 2 - 0.3, cz + d / 2 + 0.3, h, h + roof_h)


def cloud(cx, cy, cz, length, depth=0.9):
    """金霞：平放的圆头长条，纸白面 + 底下大一圈的山吹边"""
    for key, grow, dy in (("ochre", 0.12, -0.03), ("paper", 0.0, 0.0)):
        L, D = length / 2 + grow, depth / 2 + grow; pts = []
        for k in range(13): a = -math.pi / 2 + math.pi * k / 12; pts.append((cx + L - D + math.cos(a) * D, cy + dy, cz + math.sin(a) * D))
        for k in range(13): a = math.pi / 2 + math.pi * k / 12; pts.append((cx - L + D + math.cos(a) * D, cy + dy, cz + math.sin(a) * D))
        face(key, pts, [(0, 0)] * len(pts), want=(0, 1, 0))


def map_ooku(cx):   # 大奥：长廊殿 + 两排红提灯 + 红门
    hall(cx, -0.8, 7.0, 2.4, 1.7, "paper", "crimson", 1.1)
    for k in range(8): chochin((cx - 3.2 + k * 0.9, 1.0, 0.65))
    box("crimson", (cx - 1.0, 1.1, 1.8), (0.18, 2.2, 0.18)); box("crimson", (cx + 1.0, 1.1, 1.8), (0.18, 2.2, 0.18))
    box("crimson", (cx, 2.25, 1.8), (2.6, 0.18, 0.25)); box("navy", (cx, 2.45, 1.8), (2.9, 0.12, 0.45))
    for k in range(6): ribbon("drape", bezier((cx - 3.4 + k * 1.35, 1.6, 0.42), (cx - 2.9 + k * 1.35, 0.6, 0.6), (cx - 2.4 + k * 1.35, 1.6, 0.42)), 0.14, (0, 0, 1), TILE["drape"])


def map_wanya(cx):  # 万屋：三层木楼 + 外廊 + 门前红拱桥
    for s in range(3):
        y0 = s * 1.3; w = 4.4 - 0.4 * s
        box("plaster_coral" if s == 0 else "plaster_white", (cx, y0 + 0.65, -1.0), (w, 1.3, 2.4))
        for k in range(5): box("wood_dark", (cx - w / 2 + w * k / 4, y0 + 0.65, 0.22), (0.12, 1.3, 0.1))
        box("roof", (cx, y0 + 1.3, -0.6), (w + 0.9, 0.12, 3.4))
        if s: box("crimson", (cx, y0 + 0.35, 0.45), (w, 0.08, 0.06))
    gable("roof", cx - 2.0, cx + 2.0, -2.4, 0.4, 3.9, 5.0)
    for k in range(5): chochin((cx - 1.6 + k * 0.8, 0.85, 0.6))
    L = 2.4; z0 = 2.0   # 红拱桥（顺 z）
    for k in range(12):
        sa, sb = L * k / 12, L * (k + 1) / 12; ya, yb = 0.45 * math.sin(math.pi * sa / L), 0.45 * math.sin(math.pi * sb / L)
        face("crimson", [(cx - 0.45, ya, z0 + sa), (cx + 0.45, ya, z0 + sa), (cx + 0.45, yb, z0 + sb), (cx - 0.45, yb, z0 + sb)], [(0, 0)] * 4, want=(0, 1, 0))
        for xx in (cx - 0.45, cx + 0.45): obox("crimson", (xx, z0 + sa), (xx, z0 + sb), 0.05, (ya + yb) / 2 + 0.3, (ya + yb) / 2 + 0.36)


def map_sakai(cx):  # 坂井家：一层武家屋敷 + 土塀 + 古井
    hall(cx - 0.6, -0.9, 5.2, 2.6, 1.1, "paper", "wood_dark", 1.2)
    for k in range(9): box("plaster_white", (cx - 3.4 + k * 0.85, 0.35, 1.6), (0.85, 0.7, 0.2))
    box("roof", (cx, 0.75, 1.6), (7.8, 0.1, 0.45))
    cylinder("stone", (cx + 2.6, 0, 0.5), 0.45, 0.5, seg=14); cylinder("water", (cx + 2.6, 0.45, 0.5), 0.36, 0.06, seg=14)
    for sx in (-1, 1): box("wood_dark", (cx + 2.6 + sx * 0.4, 0.75, 0.5), (0.08, 1.0, 0.08))
    gable("roof", cx + 2.05, cx + 3.15, 0.1, 0.9, 1.2, 1.55)


def map_fuenokoji(cx):   # 笛小路家：单色水墨的宅邸（墨、纸白、淡藤），香炉一缕烟
    hall(cx, -1.0, 6.0, 2.6, 1.3, "lavender", "ink", 1.2, roof="kage")
    hall(cx + 2.4, 0.9, 2.2, 1.6, 1.0, "paper", "ink", 0.8, roof="kage")
    cylinder("ink", (cx - 1.5, 0, 1.2), 0.25, 0.45, seg=10)
    ribbon("paper", bezier((cx - 1.5, 0.5, 1.2), (cx - 1.0, 1.6, 1.0), (cx - 1.8, 2.6, 1.1)), 0.18, (0, 0, 1), (1, 1))


def map_solaris(cx):   # そらりす丸：海上的船 + 帆 + 海坊主的大眼
    face("water", [(cx - 4.5, 0.02, -2.6), (cx + 4.5, 0.02, -2.6), (cx + 4.5, 0.02, 2.6), (cx - 4.5, 0.02, 2.6)], [(0, 0)] * 4, want=(0, 1, 0))
    box("wood_dark", (cx, 0.35, 0.6), (4.2, 0.7, 1.3)); box("crimson", (cx, 0.75, 0.6), (4.4, 0.12, 1.4))
    cone("wood_dark", (cx + 2.1, 0.0, 0.6), 0.0, 0.65, 0.7, seg=4)
    cylinder("wood_dark", (cx, 0.7, 0.6), 0.07, 3.0, seg=8)
    face("paper", [(cx - 1.3, 1.2, 0.62), (cx + 1.3, 1.2, 0.62), (cx + 1.1, 3.4, 0.62), (cx - 1.1, 3.4, 0.62)], [(0, 0)] * 4, want=(0, 0, 1))
    sphere("paper", (cx - 0.5, 2.6, -2.3), 1.4, seg=16, rings=10); sphere("ochre", (cx - 0.5, 2.6, -1.0), 0.6, seg=14, rings=8); sphere("ink", (cx - 0.5, 2.6, -0.55), 0.3, seg=12, rings=6)


def map_subway(cx):    # 地下铁：大正风车厢 + 轨道
    for xx in (-0.45, 0.45): box("ink", (cx, 0.05, 0.5 + xx), (8.0, 0.1, 0.08))
    for k in range(16): box("wood_dark", (cx - 3.75 + k * 0.5, 0.02, 0.5), (0.12, 0.04, 1.3))
    box("teal", (cx, 0.85, 0.5), (5.6, 1.4, 1.5)); box("navy", (cx, 1.62, 0.5), (5.8, 0.14, 1.6))
    for k in range(6): face("ochre", [(cx - 2.5 + k * 0.9, 0.9, 1.26), (cx - 2.0 + k * 0.9, 0.9, 1.26), (cx - 2.0 + k * 0.9, 1.4, 1.26), (cx - 2.5 + k * 0.9, 1.4, 1.26)], [(0, 0)] * 4, want=(0, 0, 1))


def map_prison(cx):    # 牢房：石台上的木格牢
    box("stone", (cx, 0.15, 0.0), (3.4, 0.3, 2.6))
    for k in range(11): box("wood_dark", (cx - 1.5 + k * 0.3, 1.1, 1.2), (0.09, 1.6, 0.09))
    for yy in (0.35, 1.85): box("wood_dark", (cx, yy, 1.2), (3.2, 0.12, 0.12))
    box("plaster_white", (cx, 1.1, -1.2), (3.2, 1.6, 0.15)); gable("roof", cx - 1.9, cx + 1.9, -1.5, 1.5, 1.9, 2.6)
    kage(cx + 0.3, 0.2, 3)


def pine(x, z, h):
    cylinder("wood_dark", (x, 0, z), 0.08, h * 0.45, seg=6)
    for k, (r, y) in enumerate(((0.9, 0.35), (0.7, 0.6), (0.45, 0.82))):
        cone("green", (x, h * y, z), r * h / 2.2, 0.02, h * 0.28, seg=7)


def build_map_diorama():
    total = MAP_STEP * len(MAP_PLACES)
    face("paper", [(-60, 0, -60), (total + 60, 0, -60), (total + 60, 0, 40), (-60, 0, 40)], [(0, 0)] * 4, want=(0, 1, 0))
    rows = []   # 河：沿 x 蜿蜒的带子，从各地点前面绕过
    for k in range(181):
        x = -25 + (total + 50) * k / 180; z = 3.1 + 0.9 * math.sin(x / MAP_STEP * math.pi)
        rows.append([(x, 0.015, z - 0.7), (x, 0.015, z + 0.7)])
    strip("water", rows, [[(0, 0), (0, 0)]] * len(rows), want=lambda i: (0, 1, 0))
    fns = {"ooku": map_ooku, "wanya": map_wanya, "sakai": map_sakai, "fuenokoji": map_fuenokoji, "solaris": map_solaris, "subway": map_subway, "prison": map_prison}
    for i, (pid, _) in enumerate(MAP_PLACES): fns[pid](MAP_STEP * (i + 0.5))
    import random
    rnd = random.Random(5)
    for k in range(26):   # 后面一排低多边形山（以淡藤为主，偶尔青磁，压低，不抢地点）
        x = -15 + (total + 30) * k / 25 + rnd.uniform(-1.5, 1.5)
        cone(rnd.choice(["lavender", "lavender", "lavender", "teal"]), (x, 0, -13 - rnd.uniform(0, 4)), rnd.uniform(4, 6.5), 0.0, rnd.uniform(3, 5.5), seg=5)
    for i in range(len(MAP_PLACES) + 1):   # 地点之间：一两棵松
        x = MAP_STEP * i
        pine(x - 0.6, -1.6, rnd.uniform(2.2, 3.2)); pine(x + 0.9, 0.6, rnd.uniform(1.6, 2.4))
    for i in range(len(MAP_PLACES) + 1):   # 地点之间的金霞
        x = MAP_STEP * i
        cloud(x, 2.8, -2.4, 5.5); cloud(x + 0.8, 0.9, 4.4, 4.5)
    for k in range(14):   # 上下两条大霞带，把长卷上下填满（绘卷的框）
        x = -12 + (total + 24) * k / 13
        cloud(x + rnd.uniform(-2, 2), rnd.uniform(9.5, 11.5), rnd.uniform(-9, -7), rnd.uniform(8, 13), depth=1.6)
        cloud(x + rnd.uniform(-2, 2), 0.4, rnd.uniform(7.5, 9.5), rnd.uniform(8, 13), depth=1.8)
    export(OUT / "map_diorama.glb")
    print("   地点中心 x：", {pid: MAP_STEP * (i + 0.5) for i, (pid, _) in enumerate(MAP_PLACES)})


CUSTOM = {"ooku_doors": build_ooku_doors, "map_diorama": build_map_diorama}


# ---------------------------------------------------------------- 输出
def to_blender(p):   # 游戏 (x, y, z) → Blender (x, -z, y)，glTF 导出时再转回 y 向上
    return (p.x, -p.z, p.y)


def export(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    tris = 0
    for key, g in G.items():
        me = bpy.data.meshes.new(f"kit_{key}")
        me.from_pydata([to_blender(p) for p in g["v"]], [], g["f"])
        uv = me.uv_layers.new(name="UVMap")
        li = 0
        for f, uvs in zip(me.polygons, g["uv"]):
            for k, l in enumerate(f.loop_indices): uv.data[l].uv = uvs[k]
        me.validate(); me.update()
        me.shade_smooth() if hasattr(me, "shade_smooth") else None
        mat = bpy.data.materials.new(f"kit_{key}"); me.materials.append(mat)
        ob = bpy.data.objects.new(f"kit_{key}", me); bpy.context.scene.collection.objects.link(ob)
        tris += sum(len(f.vertices) - 2 for f in me.polygons)
    # 盒子、地板这些每面单独顶点，平滑着色也是硬边；圆柱、珠子、布条共用顶点，是软的
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", export_yup=True, export_normals=True,
                              export_texcoords=True, export_materials="PLACEHOLDER", export_apply=False)
    print(f"→ {path}  材质 {len(G)} 种，三角面 {tris}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        build_corridor(); export(OUT / "ooku_corridor_kit.glb")
    for name in (sorted(p.stem for p in PLANS.glob("*.txt")) + list(CUSTOM) if args == ["all"] else args):
        if name in CUSTOM: print("手写", name); G.clear(); CUSTOM[name](); continue
        print("平面图", name); build_plan(name)
