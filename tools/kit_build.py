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
PANELS = {"F": "fusuma", "S": "shoji", "U": "udoor", "G": "glassdoor", "E": "glassdoor", "H": "katomado_shoji", "N": "fusuma2", "A": "lattice_win"}   # A：格子窗（笛小路家长廊左墙，游31）   # N：第二种襖（同一间房两种襖绘，坂井家大座敷正面家纹襖）   # H：火灯窗障子（大座敷左墙）   # E：长得像玻璃门的出入口（功能同 U）
WALLS = set("#KDM") | set(PANELS) | set(DIAG)                  # M：土壁上贴画（大座敷八角凸间的美人画）
FLOOR_OF = {".": "tatami", "=": "engawa", "_": "earth", "T": "toko", ",": "gravel", "~": "water", "b": "bridge", "s": "snow", "^": "stair"}   # s 雪地、^ 台阶（笛小路家，游31）
LOW = ("earth", "snow")   # 比地板低 doma 米的地面：土间、雪庭   # 白砂、水（不能走）、拱桥
FURN = set("PRYhrktLwpcZJWXQOnmv")   # 游31 加：n 香几、m 香柜、v 几帐                                   # 坂井家加：p 红灯柱、c 圆坐垫、Z 灶台、J 陶罐、W 古井、X 白无垢衣架                                               # 高台、柜台、屏风、椅子、庭石：地面跟周围，摆家具，不能走
MARKS = set("@o123456789l") | FURN                                # l：头顶吊一盏红提灯，人能走
DIRS = {"E": (1, 0), "W": (-1, 0), "S": (0, 1), "N": (0, -1)}
KAMOI, NAGESHI = 1.76, 1.86        # 鸭居下沿、长押下沿（米）
T_WALL, T_PANEL, POST = 0.1, 0.03, 0.12


class Plan:
    def __init__(self, name):
        text = (PLANS / f"{name}.txt").read_text(encoding="utf-8")
        head, _, body = text.partition("\n---\n")
        self.cfg = {"name": name, "height": "2.7", "ceiling": "sao"}
        self.shots, self.roles = [], {"kokabe": "plaster", "stair": "engawa", "rail": "wood", "dais": "dais", "dais_trim": "ochre", "under": "kage", "tree": "fue_tree", "far": "fue_far", "gate_wood": "wood"}   # 长押以上的小壁默认和下半截一样
        self.zones, self.cur = [], None   # zone: i0,j0,i1,j1 | 角色=材质, …：这个格子范围里换材质（笛小路家红色之间，游31）；cur 是正在搭的格子
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
            elif k == "zone":
                rect, _, kvs = v.partition("|")
                self.zones.append((tuple(int(t) for t in rect.split(",")), {a.strip(): b.strip() for a, b in (kv.split("=") for kv in kvs.split(","))}))
            else: self.cfg[k] = v
        rows = [r.rstrip() for r in body.rstrip("\n").split("\n")]
        self.w = max(len(r) for r in rows); self.h = len(rows)
        self.g = [r.ljust(self.w) for r in rows]
        self.H = float(self.cfg["height"])
        self.roles.setdefault("ceiling", self.cfg["ceiling"])
        self.on = lambda k: self.cfg.get(k, "").lower() in ("on", "yes", "1", "true")
        self.k = float(self.cfg.get("timber", "1"))      # 木料粗细倍数：柱、鸭居、长押一起放大（万屋 1.8）
        self.post = POST * self.k
        self.koshi = float(self.cfg.get("koshi", "0"))
        self.kamoi = float(self.cfg.get("kamoi", KAMOI))   # 鸭居高（襖、障子、门洞的高度），坂井家婚礼大座敷 2.4：襖顶到鸭居，上面只剩一窄条小壁
        self.nageshi = self.kamoi + (NAGESHI - KAMOI)
        self.doma = float(self.cfg.get("doma", "0"))   # 土间比上框低多少米（坂井家玄关 0.36）：土间地面、墙脚、挨着土间的门都往下伸这么多
        self.hfun = []   # [(矩形, f(x, z) → 地面高度)]：拱桥这种不平的地面，写进可走格子的 floor   # 腰板高度（米），0 = 没有；有的话土壁下面这一截换成 koshi 材质

    def R(self, role):
        """材质角色 → 材质 key（平面图里 mat: wood=wood_dark 这样换），没换就是角色名本身；正在搭的格子在某个 zone 里就先用 zone 的"""
        if self.cur and self.zones:
            i, j = self.cur
            for (i0, j0, i1, j1), roles in self.zones:
                if i0 <= i <= i1 and j0 <= j <= j1 and role in roles: return roles[role]
        return self.roles.get(role, role)

    def at_xz(self, x, z): return (int(x // CELL), int(z // CELL))

    def low(self, i, j): return self.floor(i, j) in LOW

    def at(self, i, j):
        return self.g[j][i] if 0 <= i < self.w and 0 <= j < self.h else " "

    def wall(self, i, j): return self.at(i, j) in WALLS

    def base(self, i, j):
        """墙格上门扇、敷居的底高：挨着土间（8 邻里有 earth 格）就是 -doma，别的 0"""
        if not self.doma: return 0.0
        return -self.doma if any(self.floor(i + dx, j + dz) in LOW for dx in (-1, 0, 1) for dz in (-1, 0, 1)) else 0.0

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
    for reg in P.regions("tatami"): P.cur = reg[0]; lay_tatami(P, reg, walk)
    P.cur = None
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
    for kind in ("engawa", "earth", "snow"):
        for reg in P.regions(kind):
            xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
            along_x = (max(xs) - min(xs)) >= (max(zs) - min(zs))
            if kind == "engawa" and P.cfg.get("seams") == "across": along_x = not along_x   # 板缝横过廊下（万屋长廊）
            y = -P.doma if kind in LOW else 0.0
            for (a, b) in reg:
                P.cur = (a, b); r = P.cell_rect(a, b); floor_quad(P.R(kind), r, y=y, along_x=along_x); walk.append(mrect(r))
    P.cur = None
    if P.doma and any(P.floor(i, j) == "earth" for j in range(P.h) for i in range(P.w)): doma_step(P, block)
    if any(P.floor(i, j) in ("snow", "stair") for j in range(P.h) for i in range(P.w)): koran(P, walk, block)
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
        for sx in (-1, 1):   # 鲜花分两边（游29 第二轮：正中让给香炉）
            for k in range(4):
                a = 2 * math.pi * k / 4 + sx; sphere(rnd.choice(["coral", "ochre", "pink", "crimson", "lavender"]), (cx + sx * 0.24 + math.cos(a) * 0.06, 0.1, gz + 0.2 + math.sin(a) * 0.06), 0.065, seg=8, rings=5)
        grave_offering(cx, gz + 0.3)
        block.append((cx - 0.6, cz - 0.55, cx + 0.6, gz + 0.5))
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


def grave_offering(cx, cz):
    """坟前（游29 第二轮，合掌互动的地方）：藏青小香炉插三根线香（香头朱红），前面一小朱漆碟放一条鱼干"""
    cylinder("navy", (cx, 0.03, cz), 0.075, 0.07, seg=14); cylinder("navy", (cx, 0.1, cz), 0.085, 0.015, seg=14)
    for k in range(3): cylinder("navy", (cx + math.cos(2.1 * k) * 0.06, 0, cz + math.sin(2.1 * k) * 0.06), 0.012, 0.03, seg=6)
    for k, (dx, lean) in enumerate(((-0.025, -0.05), (0.0, 0.0), (0.025, 0.05))):
        tbox("green", (cx + dx, 0.1, cz), (cx + dx + lean, 0.3, cz - 0.01), 0.008)
        tbox("coral", (cx + dx + lean, 0.3, cz - 0.01), (cx + dx + lean * 1.06, 0.315, cz - 0.01), 0.011)
    cz2 = cz + 0.17
    cylinder("crimson", (cx, 0, cz2), 0.085, 0.018, seg=16)
    dried_fish((cx - 0.065, 0.024, cz2), (cx + 0.065, 0.024, cz2), (0, 1, 0), 0.04)


def tbox(key, p0, p1, w):
    """两点之间一根方截面细杆（任意方向），截面边长 w"""
    a, b = V(p0), V(p1); d = (b - a).normalized()
    up = V(0, 1, 0) if abs(d.y) < 0.9 else V(1, 0, 0)
    u = d.cross(up).normalized() * (w / 2); v = d.cross(u).normalized() * (w / 2)
    c = [a + u + v, a - u + v, a - u - v, a + u - v]; e = [b + u + v, b - u + v, b - u - v, b + u - v]
    mid = (a + b) / 2
    for k in range(4):
        q = [c[k], c[(k + 1) % 4], e[(k + 1) % 4], e[k]]
        face(key, q, [(0, 0), (1, 0), (1, 1), (0, 1)], want=tuple(sum(q, V(0, 0, 0)) / 4 - mid))
    face(key, c, [(0, 0)] * 4, want=tuple(-d)); face(key, e, [(0, 0)] * 4, want=tuple(d))


def dried_fish(head, tail, normal, h):
    """一条鱼干（平的，两面）：head→tail 是身长，normal 是鱼身朝的方向，h 是身高；焦茶色（贴着白障子、朱红碟子都看得清），用 bead_ 材质（镜头射线不撞它）"""
    a, b, n = V(head), V(tail), V(normal).normalized(); L = (b - a).length; d = (b - a).normalized(); up = n.cross(d).normalized()
    P_ = lambda s, t: a + d * (s * L) + up * (t * h)
    body = [P_(0, 0), P_(0.15, 0.45), P_(0.55, 0.5), P_(0.82, 0.18), P_(0.82, -0.18), P_(0.55, -0.45), P_(0.15, -0.4)]
    tail_ = [P_(0.8, 0), P_(1.0, 0.45), P_(0.95, 0), P_(1.0, -0.45)]
    for sg in (1, -1):
        face("bead_kogecha", body, [(0, 0)] * len(body), want=tuple(n * sg)); face("bead_kogecha", tail_, [(0, 0)] * 4, want=tuple(n * sg))
    for sg in (1, -1): sphere("paper", P_(0.12, 0.12) + n * sg * 0.003, h * 0.1, seg=6, rings=3)   # 白眼点


def hand_print(key, w=1.0):
    """一个小孩的手印（平的，原点在掌心，贴在 x = 0 的面上、朝 +x）：掌 + 五指，宽约 0.07 米"""
    def blob(cy, cz, ry, rz, n=10):
        return [(0.0, cy + math.sin(2 * math.pi * k / n) * ry, cz + math.cos(2 * math.pi * k / n) * rz) for k in range(n)]
    face(key, blob(0, 0, 0.03 * w, 0.028 * w, 12), [(0, 0)] * 12, want=(1, 0, 0))
    for k, (ang, L) in enumerate(((-1.25, 0.03), (-0.45, 0.042), (0, 0.046), (0.42, 0.043), (0.8, 0.036))):
        cy, cz = math.cos(ang) * (0.026 + L / 2) * w, math.sin(ang) * (0.026 + L / 2) * w
        pts = blob(cy, cz, L / 2 * w, 0.007 * w, 8)
        rot = [(0.0, cy + (py - cy) * math.cos(ang) - (pz - cz) * math.sin(ang), cz + (py - cy) * math.sin(ang) + (pz - cz) * math.cos(ang)) for _, py, pz in pts]
        face(key, rot, [(0, 0)] * 8, want=(1, 0, 0))


def jizo(h, seed):
    """一尊小地藏（原点脚下，朝 +z）：灰石身子、圆头、红围兜、红帽，高约 h"""
    k = h / 0.36
    box("lavender", (0, 0.025 * k, 0), (0.22 * k, 0.05 * k, 0.18 * k))
    cone("lavender", (0, 0.05 * k, 0), 0.09 * k, 0.075 * k, 0.17 * k, seg=12)
    sphere("lavender", (0, 0.27 * k, 0), 0.07 * k, seg=12, rings=6)
    cone("crimson", (0, 0.315 * k, 0), 0.06 * k, 0.0, 0.07 * k, seg=10)   # 红帽
    zf = 0.085 * k   # 红围兜：挂在胸前的一块倒梯形
    face("crimson", [(-0.075 * k, 0.21 * k, zf - 0.012 * k), (0.075 * k, 0.21 * k, zf - 0.012 * k), (0.05 * k, 0.11 * k, zf + 0.004), (-0.05 * k, 0.11 * k, zf + 0.004)], [(0, 0)] * 4, want=(0, 0.3, 1))
    for sx in (-1, 1): sphere("ink", (sx * 0.022 * k, 0.28 * k, 0.062 * k), 0.007 * k, seg=5, rings=3)   # 眯眼


def placed(kind, x, z, yaw, P, block, y=0.0):
    """平面图 place: 按米摆的小东西（游29 第二轮，坂井家厨房："这家明明该有猫"）。yaw 度，0 = 长边顺 x；y 抬高（手印的高度）"""
    acc("rock" if kind == "rock" else "kage")
    before = {k: len(g["v"]) for k, g in G.items()}
    if kind == "kage_up":   # 万屋门前桥边抬头望楼上的黑影人（11-05 文案）：身子往后仰、头抬起来，原点脚下，朝 -z（楼在北边）
        hgt = 1.6
        n0 = {kk: len(g["v"]) for kk, g in G.items()}
        cone("kage", (0, 0, 0), 0.23, 0.13, hgt * 0.74, seg=10)
        for kk, g in G.items():   # 身子往后（+z）仰 13°
            for i in range(n0.get(kk, 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x, v_.y, v_.z + v_.y * 0.24)
        tbox("kage", (0, hgt * 0.72, 0.17), (0, hgt * 0.8, 0.25), 0.09)   # 脖子往后
        sphere("kage", (0, hgt * 0.85, 0.28), hgt * 0.085, seg=10, rings=6)
        sphere("kage", (0, hgt * 0.91, 0.2), hgt * 0.05, seg=8, rings=5)   # 下巴朝前上方翘出一点：仰着脸
        for k in range(5): sphere("pink", (math.cos(2 * math.pi * k / 5) * 0.06, hgt + 0.02, 0.32 + math.sin(2 * math.pi * k / 5) * 0.06), 0.045, seg=6, rings=4)
        sphere("ochre", (0, hgt + 0.03, 0.32), 0.03, seg=6, rings=4)
    elif kind == "rock":   # 庭石（yaw 那一位当放大倍数用：rock x,z,倍数）
        rock(0, 0, int(x * 31 + z * 7), k=yaw); yaw = 0.0
    elif kind == "hand":   # 襖下沿的小手印（万屋二楼长廊）：墨色，贴在 x = 0 朝 +x，yaw 180 就朝 -x
        hand_print("kage")
    elif kind == "jizo":   # 一排四尊小地藏（万屋室内庭庭石后），排在 x 方向，朝 +z
        for k, (dx, h) in enumerate(((-0.6, 0.34), (-0.2, 0.3), (0.2, 0.36), (0.6, 0.28))):
            n0 = {kk: len(g["v"]) for kk, g in G.items()}; jizo(h, k)
            for kk, g in G.items():
                for i in range(n0.get(kk, 0), len(g["v"])): g["v"][i] = g["v"][i] + V(dx, 0, (k % 2) * 0.04)
    elif kind == "pine":   # 雪庭的松（yaw 那一位当高度，米）：墨色干、几层平展的松针团，顶上压雪
        fue_pine(yaw or 2.6); yaw = 0.0
    elif kind == "mossrock":   # 半埋在雪里的石头，顶上绿苔、一角压雪（参考 12；yaw 那一位当大小）
        k = yaw or 1.0; rock(0, 0, int(x * 31 + z * 7), k=k); g_ = G["rock"]
        for i in range(before.get("rock", 0), len(g_["v"])): g_["v"][i] = g_["v"][i] - V(0, 0.18 * k, 0)   # 往雪里埋
        flat_ball("fue_moss", (0.05 * k, 0.22 * k, 0.02), 0.32 * k, 0.1 * k); flat_ball("fue_snow", (-0.18 * k, 0.2 * k, -0.08 * k), 0.24 * k, 0.08 * k)
        yaw = 0.0
    elif kind == "twigs":   # 雪上几根枯枝
        import random
        rnd = random.Random(int(x * 13 + z * 3))
        for q in range(4):
            a = rnd.uniform(0, math.pi); L = rnd.uniform(0.4, 0.9); ox, oz = rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)
            tbox("fue_tree", (ox, 0.02, oz), (ox + math.cos(a) * L, 0.04, oz + math.sin(a) * L), 0.025)
            tbox("fue_tree", (ox + math.cos(a) * L * 0.5, 0.03, oz + math.sin(a) * L * 0.5), (ox + math.cos(a + 0.6) * L * 0.8, 0.05, oz + math.sin(a + 0.6) * L * 0.8), 0.015)
    elif kind in ("foot", "foot_r", "paw", "paw_r"):   # 雪上的小孩脚印 / 兽爪印（朝 +x 走，yaw 转），fue_print 淡墨
        sg = -1 if kind.endswith("_r") else 1
        if kind.startswith("foot"):
            pts = [(0.09 * math.cos(2 * math.pi * q / 12), 0.006, 0.042 * math.sin(2 * math.pi * q / 12)) for q in range(12)]
            face("fue_print", pts, [(0, 0)] * 12, want=(0, 1, 0))
            for q in range(5): flat_ball("fue_print", (0.115, 0.006, (q - 2) * 0.017 * sg), 0.011, 0.002, seg=6, rings=3)
        else:
            flat_ball("fue_print", (0, 0.006, 0), 0.055, 0.002, seg=8, rings=3)
            for q in range(4):
                a = (q - 1.5) * 0.45; cx_, cz_ = math.cos(a) * 0.1, math.sin(a) * 0.1
                flat_ball("fue_print", (cx_, 0.006, cz_), 0.024, 0.002, seg=6, rings=3)
                tbox("fue_print", (cx_ + 0.01, 0.007, cz_), (cx_ + 0.07 * math.cos(a), 0.007, cz_ + 0.07 * math.sin(a)), 0.012)   # 爪尖拖出的一道
    elif kind == "hime":   # 御簾后面坐着的瑠璃姫（文案 kou.1：看不清脸）：墨影，正坐、长发垂到背后，朝 +z；退魔后藏起来（fue_hime_color hide）
        cone("fue_hime", (0, 0, 0), 0.42, 0.2, 0.42, seg=12)              # 铺开的衣摆
        cone("fue_hime", (0, 0.38, 0), 0.2, 0.13, 0.42, seg=10)           # 上身
        sphere("fue_hime", (0, 0.92, 0.0), 0.11, seg=10, rings=6)         # 头
        tbox("fue_hime", (0, 0.95, -0.06), (0, 0.3, -0.22), 0.16)         # 长发
    elif kind == "baretree":   # 枯树（yaw 那一位当高度）：墨色枝杈分四层
        bare_tree(0, 0, yaw or 4.0, int(x * 17 + z * 5), P.R("tree")); yaw = 0.0
    elif kind == "pinwheel_stick":   # 纸风车的竹竿（轮子是 act_pinwheel，代码转它），轴心在 y 0.55、竿前 0.02
        tbox("wood_dark", (0, 0, 0), (0, 0.56, 0), 0.016)
    elif kind in ("trap", "trap_open"):
        # 捕鼠夹（比实物大一号、颜色对比强：浅木底板、墨色弹簧夹、朱红诱饵）：长 0.32 顺 x、宽 0.16
        box("ochre", (0, 0.015, 0), (0.32, 0.03, 0.16)); box("wood_dark", (0, 0.031, 0), (0.3, 0.002, 0.14))
        tbox("ink", (-0.02, 0.04, -0.07), (-0.02, 0.04, 0.07), 0.014)   # 弹簧轴
        for sz in (-0.06, 0.06): cylinder("ink", (-0.02, 0.03, sz), 0.022, 0.02, seg=8)   # 两头的弹簧卷
        if kind == "trap_open":   # 张开：夹杆翻起 70°，压杆顺着底板伸到诱饵，诱饵是一小块朱红
            ang = math.radians(70); L = 0.13
            tip = lambda sz: (-0.02 - math.cos(ang) * L, 0.04 + math.sin(ang) * L, sz)
            for sz in (-0.06, 0.06): tbox("ink", (-0.02, 0.04, sz), tip(sz), 0.012)
            tbox("ink", tip(-0.06), tip(0.06), 0.012)
            tbox("ink", (-0.02, 0.036, 0), (0.09, 0.036, 0), 0.008); box("coral", (0.1, 0.045, 0), (0.05, 0.03, 0.05))
        else:   # 合上：夹杆拍在前头，什么也没夹到
            for sz in (-0.06, 0.06): tbox("ink", (-0.02, 0.04, sz), (0.12, 0.04, sz), 0.012)
            tbox("ink", (0.12, 0.04, -0.06), (0.12, 0.04, 0.06), 0.012); box("coral", (0.06, 0.04, 0), (0.04, 0.02, 0.04))
    elif kind == "fish":   # 梁上垂下一串鱼干，六条，一条也没少
        tbox("ink", (0, P.H, 0), (0, 1.95, 0), 0.012)
        for k in range(6):   # 一条朝左一条朝右交错着挂，哪个方向看过去都有几条是正面
            y = 2.7 - k * 0.13; a = 0.75 if k % 2 else -0.75
            dried_fish((0, y, 0), (0, y - 0.26, 0.0), (math.cos(a), 0, math.sin(a)), 0.095)
    elif kind == "ricebag":   # 两个米俵摞着（横放的草包、两道绳），稻草色
        for k, (dx, y) in enumerate(((0, 0.2), (0.0, 0.56))):
            n0 = {kk: len(g["v"]) for kk, g in G.items()}
            cylinder("ochre", (0, -0.32, 0), 0.2, 0.64, seg=14)
            for bz in (-0.18, 0.18): cylinder("ink", (0, bz - 0.02, 0), 0.205, 0.04, seg=14, caps=False)
            for kk, g in G.items():   # 竖着做好再放倒：绕 x 转 90°，抬到 y
                for i in range(n0.get(kk, 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x + dx, -v_.z + y, v_.y)
    elif kind == "basket":   # 空的旧竹篮：扁圆筐 + 一圈竹编带 + 提手，竹青褪成灰绿
        cone("teal", (0, 0, 0), 0.17, 0.22, 0.18, seg=14); cylinder("green", (0, 0.17, 0), 0.225, 0.025, seg=14, caps=False)
        face("ink", [(math.cos(2 * math.pi * k / 14) * 0.165, 0.012, math.sin(2 * math.pi * k / 14) * 0.165) for k in range(14)], [(0, 0)] * 14, want=(0, 1, 0))   # 筐里头空的，看得到黑底
        for k in range(12):   # 提手：半圈竹条
            a, b_ = math.pi * k / 12, math.pi * (k + 1) / 12
            tbox("teal", (math.cos(a) * 0.2, 0.18 + math.sin(a) * 0.2, 0), (math.cos(b_) * 0.2, 0.18 + math.sin(b_) * 0.2, 0), 0.02)
    else:
        raise ValueError(f"place: 不认识 {kind}")
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)); xs, zs = [], []
    sc = 1.25 if kind.startswith("trap") else 1.0   # 捕鼠夹放大一号，从厨房观点那么远也认得出
    c, s_ = c * sc, s_ * sc
    for k, g in G.items():   # 原点做好，转 yaw、挪到 (x, z)
        for i in range(before.get(k, 0), len(g["v"])):
            v_ = g["v"][i]; g["v"][i] = V(x + v_.x * c - v_.z * s_, v_.y * sc, z + v_.x * s_ + v_.z * c)
            if v_.y < 1.0: xs.append(g["v"][i].x); zs.append(g["v"][i].z)
    if y:
        for k, g in G.items():
            for i in range(before.get(k, 0), len(g["v"])): g["v"][i] = g["v"][i] + V(0, y, 0)
    if kind in ("ricebag", "basket", "jizo", "kage_up", "rock", "mossrock"): block.append((min(xs), min(zs), max(xs), max(zs)))
    if kind in ("pine", "baretree"): block.append((x - 0.25, z - 0.25, x + 0.25, z + 0.25))   # 只挡树干   # 捕鼠夹不挡路（踩得过去），鱼干挂在头顶


def plan_places(P, block):
    for spec in filter(None, (t.strip() for t in P.cfg.get("place", "").split(";"))):
        kind, nums = spec.split(None, 1)   # place: 种类 x,z[,yaw 度]; …（米）
        v = [float(t) for t in nums.split(",")]
        dy = -P.doma if P.low(*P.at_xz(v[0], v[1])) else 0.0   # 雪庭里的东西跟着地面往下
        placed(kind, v[0], v[1], v[2] if len(v) > 2 else 0.0, P, block, y=(v[3] if len(v) > 3 else 0.0) + dy)


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
        # 顶层的窗不亮（11-05 文案：楼上外廊提灯都亮着，只有顶层黑着）：墨色窗面 + 焦茶窗格
        face("kage", [(xa, f3 + 0.55, zf + 0.01), (xb, f3 + 0.55, zf + 0.01), (xb, f3 + 2.3, zf + 0.01), (xa, f3 + 2.3, zf + 0.01)], [(0, 0)] * 4, want=(0, 0, 1))
        for q in range(1, 4): box(P.R("wood"), (xa + (xb - xa) * q / 4, f3 + 1.425, zf + 0.025), (0.04, 1.75, 0.03))
        for q in range(1, 4): box(P.R("wood"), ((xa + xb) / 2, f3 + 0.55 + 1.75 * q / 4, zf + 0.025), (xb - xa, 0.04, 0.03))
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
    inset = 0.025 if key in ("fusuma", "fusuma2", "glassdoor") and not (P.on("gate") and P.at(i, j) == "E") else 0.0
    span = int(P.cfg.get("fusuma_span", "4"))   # 一幅襖绘横跨几扇（坂井家雄鸡襖 6、浪涛襖 5），从这一排的第一扇算起
    if key in ("fusuma", "fusuma2") or (P.on("gate") and P.at(i, j) == "E"):   # 门洞（gate: on）里看进去的景整片连着，不每格重复
        ch = P.at(i, j); di, dj = (1, 0) if axis == "x" else (0, 1); a = 0
        while P.at(i - (a + 1) * di, j - (a + 1) * dj) == ch: a += 1
        if ch == "E":
            span = a + 1
            while P.at(i + (span - a) * di, j + (span - a) * dj) == ch: span += 1
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
        P.cur = (i, j + sg) if axis == "x" else (i + sg, j)   # 这一面朝的那一格（zone 按房间换材质时，隔断两面可以不一样）
        face(P.R(key), pts, [(m0, 0), (m1, 0), (m1, 1), (m0, 1)], want=n)
        if key in ("fusuma", "fusuma2") and P.cfg.get("hikite") == "genji":   # 引手做成源氏香纹（参考 11、14）：每扇靠一边、离地 0.85
            ch = P.at(i, j); di, dj = (1, 0) if axis == "x" else (0, 1); a = 0
            while P.at(i - (a + 1) * di, j - (a + 1) * dj) == ch: a += 1
            side = (-1 if a % 2 else 1) * 0.3   # 相邻两扇的引手朝中缝
            hx, hz = (cx + side, cz) if axis == "x" else (cx, cz + side)
            genji_crest((hx, y0 + 0.85, hz + sg * (T_PANEL / 2 + 0.006)) if axis == "x" else (hx + sg * (T_PANEL / 2 + 0.006), y0 + 0.85, hz), axis, sg, 0.06, P)


def plan_walls(P, block, segs):
    H = P.H; posts = set(); free = set()   # free：平面图上的 o，门厅柱网这种独立柱，比墙里的柱再粗一档
    for j in range(P.h):
        for i in range(P.w):
            c = P.at(i, j); P.cur = (i, j)
            if c == "o": free.add(P.center(i, j)); continue
            if c not in WALLS: continue
            cx, cz = P.center(i, j); axis = P.wall_axis(i, j)
            if c in "FSUDGEHNA" and axis:
                b0 = P.base(i, j)
                if c != "D":
                    panel(P, i, j, axis, PANELS[c], (cx, cz))
                    if not (c == "E" and P.on("gate")):   # 门洞里看进去的景（gate: on）不要门框，不然中间一道竖线像关着的两扇门
                        wbox(P.R("wood") if c in "SA" else P.R("frame"), (cx, cz), axis, CELL, T_PANEL, b0, P.kamoi, block)   # 框，贴图面在 panel() 里
                    else: wbox(P.R("frame"), (cx, cz), axis, CELL, 0.001, b0, b0 + 0.002, block)   # 只挡路
                    P.cur = (i, j)
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
    ph = float(P.cfg.get("post_h", H))   # 独立柱 o 的高（外廊出檐下面的柱子不能顶穿屋檐，游31）
    for pts, size, top in ((posts, P.post, H), (free, P.post * 1.35, ph)):
        for (x, z) in pts:
            P.cur = P.at_xz(x, z)
            box(P.R("wood"), (x, (top - P.doma) / 2, z), (size, top + P.doma, size))
            block.append((x - size / 2, z - size / 2, x + size / 2, z + size / 2))
            if pts is free and P.on("genji_posts"):   # 柱头的源氏香纹（参考 04：外廊柱子上一枚枚的纹）
                for sg in (-1, 1): genji_crest((x, ph - 0.45, z + sg * (size / 2 + 0.004)), "x", sg, 0.13, P)
    P.cur = None


def plan_furniture(P, block):
    """家具格：P 高台、R 柜台、Y 屏风（一排一组），h 椅子（一格一把，背靠墙、朝房间）"""
    for ch in "PRY":
        for reg in P.regions(lambda i, j, ch=ch: P.at(i, j) == ch):
            xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
            x0, z0, x1, z1 = mrect((min(xs), min(zs), max(xs) + 1, max(zs) + 1))
            P.cur = reg[0]
            if ch == "P":   # 高台：青磁侧面 + 地毯台面 + 山吹压边（笛小路家：dais_h 0.24、白台面、黑白格边）
                h = float(P.cfg.get("dais_h", "0.32"))
                box(P.R("dais_side"), ((x0 + x1) / 2, h / 2, (z0 + z1) / 2), (x1 - x0, h, z1 - z0))
                face(P.R("dais"), [(x0, h + 0.002, z0), (x1, h + 0.002, z0), (x1, h + 0.002, z1), (x0, h + 0.002, z1)], [(0, 1), (1, 1), (1, 0), (0, 0)], want=(0, 1, 0))
                for (a, b, c_, d) in ((x0, z0, x1, z0), (x0, z1, x1, z1), (x0, z0, x0, z1), (x1, z0, x1, z1)):
                    box(P.R("dais_trim"), ((a + c_) / 2, h + 0.02, (b + d) / 2), (max(c_ - a, 0.06), 0.04, max(d - b, 0.06)))
                if P.on("misu"): misu(P, x0, z0, x1, z1)
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
    P.cur = None
    for j in range(P.h):
        for i in range(P.w):
            P.cur = (i, j); n0 = snap()
            fue_prop(P.at(i, j), *P.center(i, j), P, block, i * 13 + j * 7)
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
            if P.low(i, j): shift_since(n0, -P.doma)   # 雪庭、土间里的庭石、石灯笼跟着地面往下
    P.cur = None
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
    ceiling_skip_cells(P)
    skip = set(t.strip() for t in P.cfg.get("ceiling_skip", "").split(",") if t.strip())   # 这些地面种类上不封顶（坂井家厨房外的后院白砂）
    for j in range(P.h):
        for i in range(P.w):
            if not P.floor(i, j) or P.floor(i, j) in skip or (i, j) in P.noceil: continue
            P.cur = (i, j); x0, z0, x1, z1 = mrect(P.cell_rect(i, j))
            pts = [(x0, P.H, z0), (x1, P.H, z0), (x1, P.H, z1), (x0, P.H, z1)]
            face(P.R("ceiling"), pts, [(p[0] / CELL, -p[2] / CELL) for p in pts], want=(0, -1, 0))
    P.cur = None


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
    P.noceil = set()
    plan_floors(P, walk, block); plan_walls(P, block, segs); plan_furniture(P, block); plan_ceiling(P); plan_rugs(P); plan_places(P, block)
    if P.cfg.get("facade") == "wanya": facade(P, block)
    if P.cfg.get("facade") == "sakai": facade_sakai(P, block)
    if P.cfg.get("surround") == "machi": surroundings(P)
    if P.on("gate"): fue_gate(P, block)
    if P.cfg.get("wall_cap"): wall_cap(P)
    for spec in filter(None, (t.strip() for t in P.cfg.get("eaves", "").split(";"))):   # eaves: x0,x1,墙面z,墙面y,出深,落差（米）
        x0, x1, zw, y, dep, drop = (float(t) for t in spec.split(","))
        pent_roof(x0, x1, zw, y, dep, drop=drop, key=P.R("roof"))
    if P.cfg.get("surround") == "yuki": yuki_surround(P)
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


# ---------------------------------------------------------------- 拾遗小物件（游29，docs/19 第五节）
# 原点就是地点 JSON finds 里的 pos（y = 0 落在地面），朝向烘在模型里；都小于 0.4 米，要走近才看得清
def build_find_candy():
    """坂井家门前：地上撒落的喜糖纸，红、白、山吹、粉几张，两头拧着"""
    import random
    rnd = random.Random(29)
    for k in range(7):
        a = rnd.uniform(0, math.pi); r = rnd.uniform(0, 0.15); t = rnd.uniform(0, 2 * math.pi)
        cx, cz = math.cos(t) * r, math.sin(t) * r; y = 0.004 + k * 0.0015
        key = ["crimson", "paper", "ochre", "pink", "crimson", "paper", "ochre"][k]
        ux, uz = math.cos(a), math.sin(a); vx, vz = -uz, ux
        P_ = lambda s_, w_: (cx + ux * s_ + vx * w_, y, cz + uz * s_ + vz * w_)
        face(key, [P_(-0.03, -0.02), P_(0.03, -0.02), P_(0.03, 0.02), P_(-0.03, 0.02)], [(0, 0)] * 4, want=(0, 1, 0))   # 糖纸身
        for sg in (-1, 1):   # 两头拧出来的小耳朵
            face(key, [P_(sg * 0.03, 0), P_(sg * 0.055, -0.018), P_(sg * 0.055, 0.018)], [(0, 0)] * 3, want=(0, 1, 0))
    export(OUT / "find_candy.glb")


def build_find_claw():
    """坂井家红色廊下：西墙一根朱红柱子朝廊下那面，离地 0.08~0.27 米四道斜抓痕（原点在柱面脚下，痕朝 +x）"""
    for k in range(4):
        z0 = -0.05 + k * 0.028; y0, y1 = 0.08 + k * 0.012, 0.27 - (k % 2) * 0.03
        pts = [(0.004, y0, z0 + 0.04), (0.004, y0 + 0.01, z0 + 0.046), (0.004, y1, z0 + 0.006), (0.004, y1 + 0.004, z0)]
        face("kage", [pts[0], pts[1], pts[3], pts[2]], [(0, 0)] * 4, want=(1, 0, 0))
    export(OUT / "find_claw.glb")


def build_find_bowl():
    """坂井家密室：角落一只倒扣的空猫碗，白瓷，碗口一圈藍边，底足朝天"""
    cone("blue", (0, 0, 0), 0.09, 0.087, 0.012, seg=20)
    cone("paper", (0, 0.012, 0), 0.087, 0.062, 0.045, seg=20)
    face("paper", [(math.cos(2 * math.pi * i / 20) * 0.062, 0.057, math.sin(2 * math.pi * i / 20) * 0.062) for i in range(20)], [(0, 0)] * 20, want=(0, 1, 0))
    cylinder("blue", (0, 0.057, 0), 0.038, 0.012, seg=20)
    export(OUT / "find_bowl.glb")


def build_find_zori():
    """万屋门前：红桥边一只小孩的草鞋（长 0.15），只有一只、泡湿了：草色压成焦茶、底下一滩水，朱红鞋带，歪着放"""
    face("blue", [(math.cos(2 * math.pi * k / 14) * 0.13 + 0.01, 0.003, math.sin(2 * math.pi * k / 14) * 0.085) for k in range(14)], [(0, 0)] * 14, want=(0, 1, 0))
    n0 = {k: len(g["v"]) for k, g in G.items()}
    pts = [(math.cos(2 * math.pi * k / 16) * 0.075, 0, math.sin(2 * math.pi * k / 16) * (0.032 if math.cos(2 * math.pi * k / 16) < 0 else 0.036)) for k in range(16)]
    face("kogecha", [(px, 0.016, pz) for px, _, pz in pts], [(0, 0)] * 16, want=(0, 1, 0))
    for k in range(16):
        a, b = pts[k], pts[(k + 1) % 16]
        face("ink", [(a[0], 0, a[2]), (b[0], 0, b[2]), (b[0], 0.016, b[2]), (a[0], 0.016, a[2])], [(0, 0)] * 4, want=((a[0] + b[0]) / 2, 0, (a[2] + b[2]) / 2))
    for sz in (-0.026, 0.026): tbox("crimson", (0.045, 0.018, 0), (-0.02, 0.04, sz), 0.012)   # 前绪 + 两边鼻绪
    tbox("crimson", (-0.02, 0.04, -0.026), (-0.03, 0.018, -0.03), 0.01); tbox("crimson", (-0.02, 0.04, 0.026), (-0.03, 0.018, 0.03), 0.01)
    c, s_ = math.cos(0.5), math.sin(0.5)
    for k, g in G.items():
        for i in range(n0.get(k, 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x * c - v_.z * s_, v_.y, v_.x * s_ + v_.z * c)
    export(OUT / "find_zori.glb")


def build_find_hand():
    """万屋二楼长廊：襖下沿一个很矮的小手印（原点掌心，贴面朝 +x；放在东侧襖上要转 180°，代码按 finds 的 yaw 转，或者直接用朝 -x 的版本）"""
    hand_print("kage", 0.9)
    for g in G.values(): g["v"] = [V(-v_.x, v_.y, -v_.z) for v_ in g["v"]]   # 转 180°：朝 -x（东侧襖朝廊下那面）
    export(OUT / "find_hand.glb")


def build_find_rattle():
    """万屋门厅账台：一只没人认领的拨浪鼓（でんでん太鼓），躺在台面上：朱红鼓身、纸白鼓面、焦茶柄、两颗墨珠"""
    n0 = {k: len(g["v"]) for k, g in G.items()}
    cylinder("crimson", (0, -0.016, 0), 0.05, 0.032, seg=16, caps=False)   # 先竖着做，再放倒（鼓轴顺 z）
    for y, n in ((-0.016, -1), (0.016, 1)):   # 鼓面朱红漆，磨掉一半露出木色（11-05 文案）
        rim = lambda a0, a1: [(0, y, 0)] + [(math.cos(a) * 0.05, y, math.sin(a) * 0.05) for a in (a0 + (a1 - a0) * t / 8 for t in range(9))]
        face("crimson", rim(0.4, 0.4 + math.pi), [(0, 0)] * 10, want=(0, n, 0))
        face("ochre", rim(0.4 + math.pi, 0.4 + 2 * math.pi), [(0, 0)] * 10, want=(0, n, 0))
    for k, g in G.items():
        for i in range(n0.get(k, 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x, v_.z + 0.05, v_.y)
    tbox("wood_dark", (0.05, 0.05, 0), (0.2, 0.012, 0), 0.014)   # 柄斜着搭在台面上
    for sz in (-1, 1):
        tbox("ink", (0, 0.05, sz * 0.016), (-0.02, 0.008, sz * 0.07), 0.003); sphere("ink", (-0.02, 0.008, sz * 0.07), 0.009, seg=6, rings=4)
    export(OUT / "find_rattle.glb")


def build_act_pinwheel():
    """万屋室内庭小地藏旁的纸风车轮（act props，move: spin）：原点在轴心，轮面在 XY、朝 +z，代码绕 Z 转"""
    cols = ["crimson", "ochre", "teal", "pink"]
    for k in range(4):
        a = math.pi / 2 * k; r = 0.11
        p0 = (0, 0, 0.004); p1 = (math.cos(a) * r, math.sin(a) * r, 0.004); p2 = (math.cos(a + 0.9) * r * 0.75, math.sin(a + 0.9) * r * 0.75, 0.012)
        face(cols[k], [p0, p1, p2], [(0, 0)] * 3, want=(0, 0, 1)); face(cols[k], [p0, p1, p2], [(0, 0)] * 3, want=(0, 0, -1))
    sphere("ochre", (0, 0, 0.016), 0.012, seg=6, rings=4)
    export(OUT / "act_pinwheel.glb")


# ---------------------------------------------------------------- 大奥叠在扫描房间上的小积木（游29，docs/20 第三节）
def two_sided(key, pts, n):
    face(key, pts, [(0, 0)] * len(pts), want=n); face(key, pts, [(0, 0)] * len(pts), want=tuple(-v for v in n))


def build_act_kasa():
    """主廊墙边的旧唐伞·伞面（act props，move: kasa）：原点在伞顶尖，伞面往下张开，半径 0.45、垂 0.28；
    朱红油纸 + 一圈纸白蛇目、山吹伞骨。代码平时把它 XZ 缩到 0.2 当收着，做的时候撑开"""
    N, R = 16, 0.45
    prof = [(0.0, 0.0), (0.1, -0.03), (0.2, -0.08), (0.28, -0.13), (0.37, -0.2), (R, -0.28)]   # (半径, 高)
    for i in range(N):
        a0, a1 = 2 * math.pi * i / N, 2 * math.pi * (i + 1) / N
        for k in range(len(prof) - 1):
            (r0, y0), (r1, y1) = prof[k], prof[k + 1]
            key = "paper" if k == 2 else "crimson"
            pts = [(math.cos(a0) * r0, y0, math.sin(a0) * r0), (math.cos(a1) * r0, y0, math.sin(a1) * r0), (math.cos(a1) * r1, y1, math.sin(a1) * r1), (math.cos(a0) * r1, y1, math.sin(a0) * r1)]
            if r0 == 0: pts = pts[1:]
            mid = sum((V(p_) for p_ in pts), V(0, 0, 0)) / len(pts)
            face(key, pts, [(0, 0)] * len(pts), want=tuple(V(mid.x, 0.6, mid.z))); face(key, pts, [(0, 0)] * len(pts), want=tuple(V(-mid.x, -0.6, -mid.z)))
        a = a0; tbox("ochre", (0, -0.2, 0), (math.cos(a) * (R - 0.01), -0.275, math.sin(a) * (R - 0.01)), 0.008)   # 伞骨（下面的撑骨）
    cylinder("ink", (0, -0.005, 0), 0.03, 0.04, seg=10)   # 顶上的头纸
    cylinder("ochre", (0, -0.23, 0), 0.025, 0.05, seg=10)   # 轆轤
    export(OUT / "act_kasa.glb")


def build_act_kasa_e():
    """唐伞的伞柄（静态，原点地面）：竹柄立到 1.2 米接伞面顶尖，下面一截藤缠的握把"""
    tbox("wood_dark", (0, 0.0, 0), (0, 1.2, 0), 0.026)
    tbox("ochre", (0, 0.02, 0), (0, 0.28, 0), 0.034)
    for k in range(5): cylinder("kogecha", (0, 0.04 + k * 0.05, 0), 0.019, 0.01, seg=8)
    export(OUT / "act_kasa_e.glb")


CL_W, CL_H, CL_D = 1.8, 1.23, 0.26   # 阿雪空房东墙壁橱（扫描里那对红百叶门，门面 x≈6.37，z -11.9~-10.1，离地 0.77~2.0）


def closet_door(x0, z0):
    """一扇红百叶门（局部：x 顺墙 0.9、y 往上、门面朝 +z），焦茶框、朱红百叶、墨色缝、山吹拉手"""
    w, h, t = CL_W / 2, CL_H, 0.025
    box("kogecha", (x0 + w / 2, h / 2, z0 + t / 2), (w, h, t))
    for k in range(13):
        y = 0.08 + k * (h - 0.16) / 12
        box("crimson", (x0 + w / 2, y, z0 + t + 0.004), (w - 0.1, 0.06, 0.008))
    box("ochre", (x0 + (w - 0.08 if x0 == 0 else 0.08), h / 2, z0 + t + 0.012), (0.03, 0.12, 0.012))


def build_act_closet():
    """壁橱静态部分（原点：壁橱左下贴墙那个角；局部 x 顺墙、y 往上、z 朝屋里；props yaw -π/2 摆到东墙）：
    黑里子、两侧红板、中间一层搁板、右扇门（不动）。左扇门 act_closet_door 在它前面滑开"""
    W, H, D = CL_W, CL_H, CL_D
    face("ink", [(0, 0, 0.012), (W, 0, 0.012), (W, H, 0.012), (0, H, 0.012)], [(0, 0)] * 4, want=(0, 0, 1))
    box("kogecha", (W / 2, 0.015, D / 2), (W, 0.03, D)); box("kogecha", (W / 2, H - 0.015, D / 2), (W, 0.03, D))
    box("kogecha", (W / 2, 0.62, D / 2), (W - 0.06, 0.025, D - 0.02))
    for x in (0.015, W - 0.015): box("crimson", (x, H / 2, D / 2), (0.03, H, D))
    closet_door(W / 2, D)
    export(OUT / "act_closet.glb")


def build_act_closet_door():
    """壁橱左扇拉门（move: slide）：原点在门左下，门宽 0.9 顺 +x，拉开时沿 +x 滑到右扇门前面"""
    closet_door(0, 0)
    export(OUT / "act_closet_door.glb")


def build_act_closet_wet():
    """壁橱里一排湿东西（show: after，原点和 act_closet 一样：左下贴墙角，x 顺墙、z 朝屋里）：
    梳子、木屐、小人偶、布包（11-05 文案），底下连成一滩水，水还顺着柜沿滴到地上。左扇门拉开只露左半边（x 0~0.9），东西都摆在左半边"""
    yb = 0.03
    face("blue", [(0.45 + math.cos(2 * math.pi * k / 20) * 0.42, yb + 0.001, 0.13 + math.sin(2 * math.pi * k / 20) * 0.11) for k in range(20)], [(0, 0)] * 20, want=(0, 1, 0))   # 一滩水
    for k in range(4): box("blue", (0.25 + k * 0.17, yb - 0.06 - (k % 2) * 0.05, CL_D + 0.004), (0.012, 0.12 + (k % 2) * 0.1, 0.004))   # 顺着柜沿往下淌
    face("blue", [(0.45 + math.cos(2 * math.pi * k / 18) * 0.38, -0.765, 0.45 + math.sin(2 * math.pi * k / 18) * 0.18) for k in range(18)], [(0, 0)] * 18, want=(0, 1, 0))   # 地上一滩（柜底离地 0.77）
    # 梳子（半月梳）
    pts = [(0.15 + math.cos(math.pi * k / 12) * 0.08, yb + 0.006, 0.12 - math.sin(math.pi * k / 12) * 0.05) for k in range(13)]
    face("kogecha", pts, [(0, 0)] * 13, want=(0, 1, 0))
    for k in range(14): box("kogecha", (0.08 + k * 0.011, yb + 0.006, 0.145), (0.005, 0.006, 0.05))
    # 木屐一只，侧翻着：木底 + 两个齿 + 红鼻绪
    box("ochre", (0.36, yb + 0.06, 0.13), (0.1, 0.12, 0.022)); box("ochre", (0.33, yb + 0.06, 0.15), (0.018, 0.1, 0.04)); box("ochre", (0.4, yb + 0.06, 0.15), (0.018, 0.1, 0.04))
    tbox("crimson", (0.36, yb + 0.1, 0.12), (0.36, yb + 0.03, 0.105), 0.01)
    # 小人偶
    x = 0.55
    cylinder("crimson", (x, yb, 0.13), 0.045, 0.12, seg=12); box("ochre", (x, yb + 0.085, 0.13), (0.1, 0.02, 0.1))
    sphere("paper", (x, yb + 0.16, 0.13), 0.045, seg=10, rings=6); sphere("ink", (x, yb + 0.175, 0.118), 0.047, seg=10, rings=6); sphere("paper", (x, yb + 0.16, 0.142), 0.04, seg=10, rings=6)
    # 布包（风吕敷，藤紫，结打在上面）
    sphere("wisteria", (0.75, yb + 0.07, 0.13), 0.09, seg=12, rings=6)
    sphere("wisteria", (0.75, yb + 0.16, 0.13), 0.025, seg=8, rings=5)   # 顶上一个平结，两只布角往两边横着垂（原来两只尖角像猫耳朵）
    for sx in (-1, 1): tbox("wisteria", (0.75, yb + 0.16, 0.13), (0.75 + sx * 0.07, yb + 0.13, 0.15), 0.022)
    export(OUT / "act_closet_wet.glb")


def build_find_kanzashi():
    """大奥主廊：地上一根掉落的发簪（长 0.2）：山吹簪脚 + 朱红小花 + 两串垂珠"""
    tbox("ochre", (-0.1, 0.006, 0), (0.07, 0.006, 0.0), 0.009)
    for k in range(4): sphere("crimson", (0.085 + math.cos(2 * math.pi * k / 5) * 0.02, 0.012, math.sin(2 * math.pi * k / 5) * 0.02), 0.016, seg=6, rings=4)   # 五颗少了一颗（11-05 文案）
    sphere("ochre", (0.085, 0.02, 0), 0.01, seg=6, rings=4)
    for sz in (-1, 1):
        for k in range(3): sphere("pink" if k % 2 else "paper", (0.11 + k * 0.02, 0.006, sz * (0.025 + k * 0.012)), 0.007, seg=5, rings=3)
    export(OUT / "find_kanzashi.glb")


def build_find_crane():
    """女中房：圆窗下一只纸鹤（宽 0.16）：两片翅膀、长脖子尖嘴、尾巴，纸白带一点粉"""
    two_sided("paper", [(0, 0.04, 0), (-0.02, 0.045, -0.08), (0.03, 0.05, -0.02)], (0, 1, 0))
    two_sided("paper", [(0, 0.04, 0), (-0.02, 0.045, 0.08), (0.03, 0.05, 0.02)], (0, 1, 0))
    two_sided("pink", [(-0.04, 0.0, 0), (0.0, 0.04, 0), (0.04, 0.0, 0)], (0, 0, 1))   # 身子
    two_sided("paper", [(0.03, 0.02, 0), (0.07, 0.09, 0), (0.08, 0.085, 0)], (0, 0, 1))   # 脖子
    two_sided("paper", [(0.075, 0.09, 0), (0.1, 0.08, 0), (0.08, 0.083, 0)], (0, 0, 1))   # 嘴
    two_sided("paper", [(-0.03, 0.02, 0), (-0.08, 0.07, 0), (-0.07, 0.075, 0)], (0, 0, 1))   # 尾
    for k, (r, a) in enumerate(((0.012, 0), (0.008, 1.3), (0.007, 2.6), (0.006, 4.0), (0.009, 5.1))):   # 右翅上一个洇开的墨字（11-05 文案）
        cx_, cz_ = 0.004 + math.cos(a) * 0.008, 0.045 + math.sin(a) * 0.008
        face("ink", [(cx_ + math.cos(2 * math.pi * q / 8) * r, 0.0465, cz_ + math.sin(2 * math.pi * q / 8) * r) for q in range(8)], [(0, 0)] * 8, want=(0, 1, 0))
    for g in G.values(): g["v"] = [v_ * 1.7 for v_ in g["v"]]   # 放大一号（0.16 宽在女中房里几乎看不见）
    export(OUT / "find_crane.glb")


def build_find_letter():
    """歌山房文机：一封没写完的信，只写了一行（展开的卷纸 0.22×0.12），旁边一方墨砚，笔搁在砚边（11-05 文案）"""
    box("paper", (0, 0.002, 0), (0.22, 0.004, 0.12))
    box("ink", (0.08, 0.0045, -0.01), (0.006, 0.001, 0.08))   # 一行字
    box("ink", (0.08, 0.0045, 0.042), (0.008, 0.001, 0.008))   # 末尾一滴墨
    box("ink", (0.0, 0.012, 0.13), (0.09, 0.024, 0.06)); box("navy", (0.0, 0.0245, 0.12), (0.07, 0.002, 0.035))   # 墨砚 + 墨池
    tbox("kogecha", (-0.06, 0.026, 0.16), (0.05, 0.026, 0.155), 0.008); cone("ink", (0.05, 0.026, 0.155), 0.005, 0.0, 0.0001, seg=6)   # 笔，笔头搁在砚边
    tbox("ink", (0.05, 0.026, 0.155), (0.065, 0.025, 0.154), 0.01)
    export(OUT / "find_letter.glb")


# ---------------------------------------------------------------- 笛小路家的拾遗和 act（游32，文案线 11-06 物件清单）
def build_find_geta():
    """拾遗 1（门前雪里）：一只木屐，鞋带断了，一头耷拉在雪上；四周雪是平的（脚印不画就是平的）。原点在木屐中心，长边顺 x"""
    box("fue_geta", (0, 0.05, 0), (0.24, 0.025, 0.1))
    for x in (-0.06, 0.06): box("fue_geta", (x, 0.02, 0), (0.025, 0.04, 0.09))   # 两个齿
    tbox("crimson", (0.08, 0.065, 0), (0.0, 0.1, 0.045), 0.012); tbox("crimson", (0.0, 0.1, 0.045), (-0.07, 0.066, 0.04), 0.012)   # 还连着的一边
    tbox("crimson", (0.0, 0.1, -0.045), (-0.05, 0.03, -0.12), 0.012); tbox("crimson", (-0.05, 0.03, -0.12), (-0.13, 0.008, -0.16), 0.012)   # 断了耷拉到雪上
    flat_ball("fue_snow", (-0.02, 0.0, 0.0), 0.2, 0.03)   # 一半陷在雪里
    export(OUT / "find_geta.glb")


def build_find_kouhukuro():
    """拾遗 2（长廊障子边）：一只小香包挂在障子框上，绣源氏香纹，挂绳是新的（朱红）。原点在挂钩，包往下垂；贴墙那面朝 -x"""
    tbox("crimson", (0, 0, 0), (0, -0.16, 0), 0.008)
    n0 = snap(); flat_ball("fue_kinran", (0, -0.26, 0), 0.075, 0.1)
    g = G["fue_kinran"]
    for i in range(n0.get("fue_kinran", 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x * 0.55, v_.y, v_.z)   # 压扁成荷包
    cone("fue_kinran", (0, -0.2, 0), 0.04, 0.012, 0.05, seg=8)
    sphere("crimson", (0, -0.165, 0), 0.016, seg=6, rings=4)
    class _P:   # genji_crest 要 P.R
        R = staticmethod(lambda r: {"genji_plate": "fue_genji_plate", "genji_line": "fue_genji_line"}.get(r, r))
    genji_crest((0.043, -0.27, 0), "z", 1, 0.035, _P)
    export(OUT / "find_kouhukuro.glb")


def build_find_koufuda():
    """拾遗 3（红色之间地上）：一枚碎成两半的香札（比香写答案的小木片），背面写名字的地方被抹黑。原点在中心，平放"""
    box("fue_fuda", (-0.045, 0.004, 0), (0.07, 0.008, 0.05)); box("ink", (-0.05, 0.0085, 0), (0.04, 0.001, 0.03))
    n0 = snap(); box("fue_fuda", (0, 0.004, 0), (0.06, 0.008, 0.05)); box("ink", (0.005, 0.0085, -0.005), (0.035, 0.001, 0.02))
    for k, g in G.items():   # 另一半错开、转一点
        for i in range(n0.get(k, 0), len(g["v"])):
            v_ = g["v"][i]; c, s_ = math.cos(0.5), math.sin(0.5); g["v"][i] = V(0.06 + v_.x * c - v_.z * s_, v_.y, 0.03 + v_.x * s_ + v_.z * c)
    export(OUT / "find_koufuda.glb")


KB_W, KB_D, KB_H = 0.8, 0.42, 1.1   # 香柜：宽（顺 z）、深（顺 x，正面朝 +x）、高


def build_act_koubako():
    """act 打开香柜（文案：多层香柜，拉开以后是锦缎包了好几层的包）：三层黑漆厨子棚，上两层开放摆小香盒，最下层是个抽屉洞。
    正面朝 +x（地点 JSON 里 yaw -1.5708 就朝 +z）。原点在底面中心"""
    lac = "fue_lacquer"; W, D, H = KB_W, KB_D, KB_H
    for y in (0.0, 0.36, 0.72, H - 0.03): box(lac, (0, y + 0.015, 0), (D, 0.03, W))
    box(lac, (-D / 2 + 0.015, H / 2, 0), (0.03, H, W))   # 背板
    for sz in (-1, 1): box(lac, (0, H / 2, sz * (W / 2 - 0.015)), (D, H, 0.03))   # 侧板
    face("ink", [(D / 2 - 0.03, 0.04, -W / 2 + 0.03), (D / 2 - 0.03, 0.04, W / 2 - 0.03), (D / 2 - 0.03, 0.35, W / 2 - 0.03), (D / 2 - 0.03, 0.35, -W / 2 + 0.03)], [(0, 0)] * 4, want=(1, 0, 0))   # 抽屉洞里黑的
    for y, n in ((0.39, 3), (0.75, 2)):
        for k in range(n):
            z = -W / 2 + W * (k + 0.5) / n
            box(lac, (0, y + 0.07, z), (0.2, 0.12, 0.18)); box("fue_genji_line", (0, y + 0.135, z), (0.21, 0.01, 0.19))
    box("fue_genji_line", (D / 2, H - 0.015, 0), (0.01, 0.02, W))   # 顶边一道纸白
    export(OUT / "act_koubako.glb")


def build_act_koubako_drawer():
    """抽屉（move: slide 往 +x 拉出）：前板带源氏香纹拉手，里面放着锦缎包，包口翻开露出一截发黑的朽木，断口碎成红渣（参考 18）。
    原点在抽屉底面中心（关着时和柜子同心）"""
    lac = "fue_lacquer"; W, D = KB_W - 0.08, KB_D - 0.06
    box(lac, (0, 0.01, 0), (D, 0.02, W))
    for sz in (-1, 1): box(lac, (0, 0.09, sz * (W / 2 - 0.01)), (D, 0.18, 0.02))
    box(lac, (-D / 2 + 0.01, 0.09, 0), (0.02, 0.18, W))
    box(lac, (D / 2 - 0.01, 0.15, 0), (0.03, 0.3, W + 0.04))   # 前板
    class _P:
        R = staticmethod(lambda r: {"genji_plate": "fue_genji_plate", "genji_line": "fue_genji_line"}.get(r, r))
    genji_crest((D / 2 + 0.006, 0.15, 0), "z", 1, 0.05, _P)
    # 锦缎包（几层布叠着，最上面一层翻开）
    for k, (h, r) in enumerate(((0.05, 0.3), (0.09, 0.27), (0.12, 0.24))):
        key = "fue_nishiki" if k < 2 else "fue_kinran"   # 外面几层素锦、最里一层织纹
        n0 = snap(); flat_ball(key, (0, 0.05 + h * 0.5, 0), r, h * 0.6)
        g = G[key]
        for i in range(n0.get(key, 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x * 0.5, v_.y, v_.z)
    two_sided("crimson", [(0.02, 0.18, -0.1), (0.17, 0.15, -0.16), (0.2, 0.12, 0.15), (0.03, 0.17, 0.12)], (0.3, 1, 0))   # 翻开的布角：朱红里子
    # 朽木：一截发黑的木头横在包上，一头断口发红碎渣
    n0 = snap(); cylinder("fue_kuchiki", (0, 0, 0), 0.045, 0.34, seg=9)
    g = G["fue_kuchiki"]
    for i in range(n0.get("fue_kuchiki", 0), len(g["v"])): v_ = g["v"][i]; g["v"][i] = V(v_.x, 0.235 + v_.z, v_.y - 0.17)   # 放倒顺 z
    import random
    rnd = random.Random(18)
    for _ in range(14):   # 断口（+z 那头）的红渣
        sphere("crimson", (rnd.uniform(-0.04, 0.04), 0.235 + rnd.uniform(-0.04, 0.04), 0.17 + rnd.uniform(0, 0.05)), rnd.uniform(0.008, 0.016), seg=5, rings=3)
    for _ in range(8): sphere("fue_kuchiki", (rnd.uniform(-0.06, 0.08), 0.19, 0.2 + rnd.uniform(0, 0.08)), rnd.uniform(0.006, 0.012), seg=5, rings=3)
    export(OUT / "act_koubako_drawer.glb")


CUSTOM = {"ooku_doors": build_ooku_doors, "map_diorama": build_map_diorama,
          "act_kasa": build_act_kasa, "act_kasa_e": build_act_kasa_e, "act_closet": build_act_closet, "act_closet_door": build_act_closet_door,
          "act_closet_wet": build_act_closet_wet, "find_kanzashi": build_find_kanzashi, "find_crane": build_find_crane, "find_letter": build_find_letter,
          "find_zori": build_find_zori, "find_hand": build_find_hand, "find_rattle": build_find_rattle, "act_pinwheel": build_act_pinwheel,
          "find_candy": build_find_candy, "find_claw": build_find_claw, "find_bowl": build_find_bowl,
          "find_geta": build_find_geta, "find_kouhukuro": build_find_kouhukuro, "find_koufuda": build_find_koufuda,
          "act_koubako": build_act_koubako, "act_koubako_drawer": build_act_koubako_drawer}




# ---------------------------------------------------------------- 笛小路家（TV《鵺》，游31，11-06；参考 assets/concept/ref/fuenokouji/，只看不裁）
def snap(): return {k: len(g["v"]) for k, g in G.items()}


def shift_since(n0, dy):
    if not dy: return
    for k, g in G.items():
        for i in range(n0.get(k, 0), len(g["v"])): g["v"][i] = g["v"][i] + V(0, dy, 0)


def ceiling_skip_cells(P):
    """天花不封顶的格子：雪地、台阶（外廊外面露天）"""
    for j in range(P.h):
        for i in range(P.w):
            if P.floor(i, j) in ("snow", "stair"): P.noceil.add((i, j))


def koran(P, walk, block):
    """寝殿造的高廊（参考 03、04）：地板（廊板 / 榻榻米）比雪庭高 doma 米，交界处一圈高栏（柱、笠木、中贯、地覆）、
    檐边一道封檐板，下面往里缩 0.5 米一道墨色挡板（地板下的暗处），每两格一根短柱支着；
    ^ 连成一片是一段宽台阶（参考 03 中间那段），朝着有地板的那边往上，两侧有侧板和斜扶手。
    整块的地面高度写进 P.hfun：雪地、土间 -doma，台阶按位置斜着，别的 0"""
    d = P.doma
    raised = lambda f: f is not None and f not in LOW and f != "stair"
    stairs = {}
    for reg in P.regions("stair"):
        xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
        x0, z0, x1, z1 = mrect((min(xs), min(zs), max(xs) + 1, max(zs) + 1))
        up = (0, -1)
        for k, (dx, dz) in DIRS.items():
            if any(raised(P.floor(a + dx, b + dz)) for a, b in reg): up = (dx, dz); break
        info = (x0, z0, x1, z1, up)
        for c in reg: stairs[c] = info
        P.cur = reg[0]; key = P.R("stair")
        along_z = up[0] == 0
        L = (z1 - z0) if along_z else (x1 - x0)
        n = max(2, round(d / 0.18)); rise, run = d / n, L / n
        for k in range(n):   # 第 k 级（从下往上）：从地面到这一级顶面的一块
            top = -d + rise * (k + 1)
            if along_z:
                za, zb = (z1 - run * (k + 1), z1 - run * k) if up[1] < 0 else (z0 + run * k, z0 + run * (k + 1))
                box(key, ((x0 + x1) / 2, (top - d) / 2, (za + zb) / 2), (x1 - x0, top + d, zb - za), tile=CELL)
            else:
                xa, xb = (x1 - run * (k + 1), x1 - run * k) if up[0] < 0 else (x0 + run * k, x0 + run * (k + 1))
                box(key, ((xa + xb) / 2, (top - d) / 2, (z0 + z1) / 2), (xb - xa, top + d, z1 - z0), tile=CELL)
        rail = P.R("rail")
        for side in (0, 1):   # 两侧侧板 + 斜扶手，挡住不让人从台阶侧面掉下雪地
            if along_z:
                x = x0 + 0.04 if side == 0 else x1 - 0.04
                lo, hi = (z1, z0) if up[1] < 0 else (z0, z1)
                pts = [(x, -d, lo), (x, -d + 0.3, lo), (x, 0.3, hi), (x, -d, hi)]
                two_sided(rail, pts, (1, 0, 0))
                tbox(rail, (x, -d + 0.8, lo), (x, 0.8, hi), 0.06)
                for zz, yy in ((lo, -d), (hi, 0.0)): box(rail, (x, yy + 0.4, zz), (0.08, 0.8, 0.08))
                block.append((x - 0.05, min(lo, hi), x + 0.05, max(lo, hi)))
            else:
                z = z0 + 0.04 if side == 0 else z1 - 0.04
                lo, hi = (x1, x0) if up[0] < 0 else (x0, x1)
                pts = [(lo, -d, z), (lo, -d + 0.3, z), (hi, 0.3, z), (hi, -d, z)]
                two_sided(rail, pts, (0, 0, 1))
                tbox(rail, (lo, -d + 0.8, z), (hi, 0.8, z), 0.06)
                for xx, yy in ((lo, -d), (hi, 0.0)): box(rail, (xx, yy + 0.4, z), (0.08, 0.8, 0.08))
                block.append((min(lo, hi), z - 0.05, max(lo, hi), z + 0.05))
        walk.append((x0, z0, x1, z1))
    P.cur = None
    # 高栏：地板格朝雪地的边，按线合并
    lines = {}
    for j in range(P.h):
        for i in range(P.w):
            if not raised(P.floor(i, j)): continue
            x0, z0, x1, z1 = mrect(P.cell_rect(i, j))
            for k, (dx, dz) in DIRS.items():
                if P.floor(i + dx, j + dz) not in LOW: continue
                if dz: lines.setdefault(("x", round(z0 if dz < 0 else z1, 4), dz), []).append((x0, x1, (i, j)))
                else: lines.setdefault(("z", round(x0 if dx < 0 else x1, 4), dx), []).append((z0, z1, (i, j)))
    for (ax, c, sg), segs_ in lines.items():
        segs_.sort()
        runs = []
        for a0, a1, cell in segs_:
            if runs and abs(runs[-1][1] - a0) < 1e-6: runs[-1][1] = a1
            else: runs.append([a0, a1, cell])
        for a0, a1, cell in runs:
            P.cur = cell; rail = P.R("rail"); wood = P.R("wood"); under = P.R("under")
            ci = c - sg * 0.07   # 栏杆往地板里缩一点
            L = a1 - a0; m = (a0 + a1) / 2
            def bx(key, along_c, y0, y1, thick, cc):
                if ax == "x": box(key, (along_c, (y0 + y1) / 2, cc), (L, y1 - y0, thick))
                else: box(key, (cc, (y0 + y1) / 2, along_c), (thick, y1 - y0, L))
            for y0, y1, t in ((0.0, 0.06, 0.09), (0.42, 0.47, 0.05), (0.82, 0.88, 0.08)):   # 地覆、中贯、笠木
                bx(rail, m, y0, y1, t, ci)
            npost = max(1, round(L / CELL))
            for q in range(npost + 1):
                a = a0 + L * q / npost
                if ax == "x": box(rail, (a, 0.42, ci), (0.07, 0.84, 0.07))
                else: box(rail, (ci, 0.42, a), (0.07, 0.84, 0.07))
            bx(wood, m, -0.14, 0.0, 0.05, c)   # 封檐板
            back = c - sg * 0.5   # 地板下的暗处：往里缩 0.5 米一道挡板 + 底面
            if ax == "x":
                face(under, [(a0, -d, back), (a1, -d, back), (a1, -0.14, back), (a0, -0.14, back)], [(0, 0)] * 4, want=(0, 0, sg))
                face(under, [(a0, -0.14, back), (a1, -0.14, back), (a1, -0.14, c), (a0, -0.14, c)], [(0, 0)] * 4, want=(0, -1, 0))
            else:
                face(under, [(back, -d, a0), (back, -d, a1), (back, -0.14, a1), (back, -0.14, a0)], [(0, 0)] * 4, want=(sg, 0, 0))
                face(under, [(back, -0.14, a0), (back, -0.14, a1), (c, -0.14, a1), (c, -0.14, a0)], [(0, 0)] * 4, want=(0, -1, 0))
            for q in range(int(L / (2 * CELL)) + 1):   # 短柱
                a = a0 + 0.2 + q * 2 * CELL
                if a > a1 - 0.1: break
                pc = c - sg * 0.25
                if ax == "x": box(wood, (a, (-d - 0.14) / 2, pc), (0.14, d - 0.14, 0.14))
                else: box(wood, (pc, (-d - 0.14) / 2, a), (0.14, d - 0.14, 0.14))
            if ax == "x": block.append((a0, ci - 0.05, a1, ci + 0.05))
            else: block.append((ci - 0.05, a0, ci + 0.05, a1))
    P.cur = None
    def hf(x, z):
        i, j = P.at_xz(x, z)
        f = P.floor(i, j)
        if f is None:   # 墙格那半格按旁边的地面算
            near = [P.floor(i + dx, j + dz) for dx, dz in DIRS.values() if P.floor(i + dx, j + dz)]
            f = near[0] if near else None
            if f == "stair": return None
        if f == "stair":
            x0, z0, x1, z1, up = stairs[(i, j)]
            if up[0] == 0: t = (z1 - z) / (z1 - z0) if up[1] < 0 else (z - z0) / (z1 - z0)
            else: t = (x1 - x) / (x1 - x0) if up[0] < 0 else (x - x0) / (x1 - x0)
            return -d + d * max(0.0, min(1.0, t))
        return -d if f in LOW else 0.0
    P.hfun.append(((0, 0, P.w * CELL, P.h * CELL), hf))


def genji_crest(c, axis, sg, r, P):
    """源氏香纹（参考 13、14）：六角形底板 + 里面五根竖条，顶上横条把其中几根连起来（"花散里"的图样）。
    贴在墙面 / 门面上：axis 是那面墙的走向，sg 是朝哪边。底板角色 genji_plate（默认墨），条子角色 genji_line（默认纸白）"""
    cx, cy, cz = c
    to3 = (lambda a, y, o=0.0: (cx - sg * a, cy + y, cz + sg * o)) if axis == "x" else (lambda a, y, o=0.0: (cx + sg * o, cy + y, cz + sg * a))
    n = (0, 0, sg) if axis == "x" else (sg, 0, 0)
    plate, line = P.R("genji_plate"), P.R("genji_line")
    face(plate, [to3(r * math.cos(math.pi / 3 * k + math.pi / 6), r * math.sin(math.pi / 3 * k + math.pi / 6)) for k in range(6)], [(0, 0)] * 6, want=n)
    w = r * 0.09; xs = [r * (-0.5 + 0.25 * k) for k in range(5)]; top, bot = r * 0.45, -r * 0.5
    def bar(a0, y0, a1, y1):
        face(line, [to3(a0, y0, 0.002), to3(a1, y0, 0.002), to3(a1, y1, 0.002), to3(a0, y1, 0.002)], [(0, 0)] * 4, want=n)
    for k, a in enumerate(xs): bar(a - w / 2, bot, a + w / 2, top if k != 2 else top - r * 0.2)
    bar(xs[0] - w / 2, top - w, xs[1] + w / 2, top)    # 一、二根连
    bar(xs[3] - w / 2, top - w, xs[4] + w / 2, top)    # 四、五根连
    bar(xs[1] - w / 2, top - r * 0.2 - w, xs[3] + w / 2, top - r * 0.2)   # 二、四根低一档连，第三根从中间穿


def fue_prop(ch, cx, cz, P, block, seed):
    """香之间的家具（参考 02、05、07、10）：n 香几（黑漆矮几，上面香炉、香盘、几根香箸）、m 香柜（三层黑漆厨子棚，上面小香盒）、
    v 几帐（T 字木架垂两幅帘，帘子角色 kicho）"""
    lac, line = P.R("lacquer"), P.R("genji_line")
    if ch == "n":
        box(lac, (cx, 0.27, cz), (1.1, 0.05, 0.5))
        for sx in (-0.5, 0.5):
            for sz in (-0.2, 0.2): box(lac, (cx + sx, 0.125, cz + sz), (0.05, 0.25, 0.05))
        box(line, (cx, 0.296, cz), (1.0, 0.004, 0.4))   # 台面一道纸白描边
        box(lac, (cx, 0.3, cz), (0.96, 0.006, 0.36))
        cylinder(P.R("censer"), (cx - 0.25, 0.3, cz), 0.07, 0.08, seg=10); cylinder(line, (cx - 0.25, 0.38, cz), 0.075, 0.01, seg=10)
        kouban(cx + 0.12, 0.3, cz)
        for k in range(3): tbox(lac, (cx + 0.38, 0.31, cz - 0.08 + k * 0.05), (cx + 0.46, 0.31, cz + 0.06 + k * 0.05), 0.012)
        block.append((cx - 0.58, cz - 0.28, cx + 0.58, cz + 0.28))
    elif ch == "m" and P.cfg.get("koubako") == "act":   # 香柜是 act 的小积木（act_koubako），平面图这格只挡路
        block.append((cx - 0.42, cz - 0.3, cx + 0.42, cz + 0.3))
    elif ch == "m":
        w_, d_, h_ = 0.8, 0.4, 1.1
        for y in (0.04, 0.4, 0.75, h_): box(lac, (cx, y, cz), (w_, 0.04, d_))
        for sx in (-1, 1):
            for sz in (-1, 1): box(lac, (cx + sx * (w_ / 2 - 0.02), h_ / 2, cz + sz * (d_ / 2 - 0.02)), (0.04, h_, 0.04))
        for y, n in ((0.06, 2), (0.42, 3), (0.77, 1), (h_ + 0.02, 2)):   # 每层摆小香盒（纸白边）
            for k in range(n):
                x = cx - w_ / 2 + w_ * (k + 0.5) / n
                box(lac, (x, y + 0.07, cz), (0.18, 0.12, 0.18)); box(line, (x, y + 0.135, cz), (0.19, 0.01, 0.19))
        block.append((cx - w_ / 2, cz - d_ / 2, cx + w_ / 2, cz + d_ / 2))
    elif ch == "v":
        wood, cloth = P.R("wood"), P.R("kicho")
        box(wood, (cx, 0.03, cz), (0.6, 0.06, 0.3)); box(wood, (cx, 0.75, cz), (0.05, 1.5, 0.05)); box(wood, (cx, 1.5, cz), (1.0, 0.05, 0.05))
        for sx in (-0.25, 0.25):
            face(cloth, [(cx + sx - 0.24, 0.2, cz), (cx + sx + 0.24, 0.2, cz), (cx + sx + 0.24, 1.48, cz), (cx + sx - 0.24, 1.48, cz)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, 1))
            face(cloth, [(cx + sx - 0.24, 0.2, cz), (cx + sx + 0.24, 0.2, cz), (cx + sx + 0.24, 1.48, cz), (cx + sx - 0.24, 1.48, cz)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 0, -1))
        block.append((cx - 0.5, cz - 0.15, cx + 0.5, cz + 0.15))


def gate_ruin(P, x0, x1, cz, hh):
    """退魔后（参考 19）：门是废墟——茅草顶塌了半边、门板歪掉一扇、墙上裂缝、雪化了长出草，墙外樱花开着。
    这些都用 fue_ruin_* / fue_grass / fue_sakura 材质：水墨时 kit.js 藏起来，recolorKit(…, "color") 时才出来；原来的门（fue_gate_*）彩色时藏起来"""
    import random
    rnd = random.Random(19); rw = "fue_ruin_wood"; mx = (x0 + x1) / 2
    for x, tilt in ((x0 - 0.1, 0.0), (x1 + 0.1, 0.12)):   # 两根柱，右边那根歪了
        tbox(rw, (x, 0, cz), (x + tilt, hh, cz), 0.26)
    tbox(rw, (x0 - 0.5, P.kamoi + 0.1, cz), (x1 + 0.6, P.kamoi - 0.15, cz), 0.2)   # 冠木一头塌下来
    # 塌了半边的茅草顶：左坡还在，右半边垂到地上
    face("fue_ruin_roof", [(x0 - 0.9, hh + 0.05, cz - 1.1), (mx, hh + 0.2, cz - 1.1), (mx, hh + 0.75, cz), (x0 - 0.9, hh + 0.65, cz)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 1, -1))
    face("fue_ruin_roof", [(x0 - 0.9, hh + 0.05, cz + 1.1), (mx, hh + 0.2, cz + 1.1), (mx, hh + 0.75, cz), (x0 - 0.9, hh + 0.65, cz)], [(0, 0), (1, 0), (1, 1), (0, 1)], want=(0, 1, 1))
    face("fue_ruin_roof", [(mx, hh + 0.75, cz - 1.0), (mx, hh + 0.75, cz + 1.0), (x1 + 1.2, 0.2, cz + 1.3), (x1 + 1.2, 0.2, cz - 1.3)], [(0, 1), (1, 1), (1, 0), (0, 0)], want=(1, 1, 0))
    face("fue_ruin_roof", [(mx, hh + 0.75, cz - 1.0), (mx, hh + 0.75, cz + 1.0), (x1 + 1.2, 0.2, cz + 1.3), (x1 + 1.2, 0.2, cz - 1.3)], [(0, 1), (1, 1), (1, 0), (0, 0)], want=(-1, -1, 0))
    lw = (x1 - x0) / 2   # 门板：左扇还挂着（歪），右扇倒在地上
    obox(rw, (x0, cz + 0.1), (x0 + lw * 0.95, cz + 0.35), 0.06, 0.2, P.kamoi - 0.25)
    face(rw, [(x1 - 0.1, 0.03, cz + 0.4), (x1 + 0.7, 0.03, cz + 0.9), (x1 + 0.2, 0.08, cz + 2.4), (x1 - 0.6, 0.08, cz + 1.9)], [(0, 0)] * 4, want=(0, 1, 0))
    # 墙上裂缝（墙格两面）
    for j in range(P.h):
        for i in range(P.w):
            if P.at(i, j) != "#" or rnd.random() > 0.35: continue
            cx, cz_ = P.center(i, j)
            for sg in (-1, 1):
                z = cz_ + sg * (T_WALL / 2 + 0.008); x, y = cx + rnd.uniform(-0.3, 0.3), P.H - 0.2; pts = []
                for k in range(6):
                    nx, ny = x + rnd.uniform(-0.12, 0.12), y - rnd.uniform(0.15, 0.3)
                    face("fue_ruin_crack", [(x - 0.012, y, z), (x + 0.012, y, z), (nx + 0.012, ny, z), (nx - 0.012, ny, z)], [(0, 0)] * 4, want=(0, 0, sg))
                    x, y = nx, ny
    # 草：雪地格上一丛丛
    for j in range(P.h):
        for i in range(P.w):
            if P.floor(i, j) != "snow": continue
            for _ in range(2):
                gx, gz = (i + rnd.random()) * CELL, (j + rnd.random()) * CELL
                for k in range(5):
                    a = rnd.uniform(0, math.pi); hgt = rnd.uniform(0.15, 0.35)
                    two_sided("fue_grass", [(gx - 0.03 * math.cos(a), 0, gz - 0.03 * math.sin(a)), (gx + 0.03 * math.cos(a), 0, gz + 0.03 * math.sin(a)), (gx + rnd.uniform(-0.08, 0.08), hgt, gz + rnd.uniform(-0.08, 0.08))], (math.sin(a), 0, -math.cos(a)))
    # 墙外的樱花（北边墙后、门两侧）
    for (tx, tz) in ((x0 - 3.2, cz - 2.4), (x1 + 2.8, cz - 2.0), (x0 - 6.5, cz - 1.6), (x1 + 6.0, cz - 2.8), (1.0, cz + 7.5)):
        tbox("fue_ruin_wood", (tx, 0, tz), (tx + 0.2, 2.4, tz), 0.2)
        for k in range(7):
            a = 2 * math.pi * k / 7; flat_ball("fue_sakura", (tx + math.cos(a) * 0.9, 2.7 + rnd.uniform(-0.3, 0.5), tz + math.sin(a) * 0.9), rnd.uniform(0.6, 0.9), rnd.uniform(0.4, 0.55))
        flat_ball("fue_sakura", (tx + 0.2, 3.3, tz), 0.9, 0.6)


def misu(P, x0, z0, x1, z1):
    """御簾（文案：高台挂御簾，后面坐着瑠璃姫，隔着帘看不清脸）：挂在高台朝房间那边（+z）的边上，从 2.35 米垂到 1.2 米，
    正好挡住坐着的人的脸、露出下半身；上面一道帽额，两头垂朱红的总角结"""
    z = z1 + 0.02; key = P.R("misu"); yb = float(P.cfg.get("misu_y", "1.2"))   # 帘子下沿（笛小路家 0.95：瑠璃姫配角跪坐在台上，脸挡住、露衣摆）
    for zz, n in ((z, (0, 0, 1)), (z, (0, 0, -1))):
        face(key, [(x0, yb, zz), (x1, yb, zz), (x1, 2.35, zz), (x0, 2.35, zz)], [(0, 0), ((x1 - x0) / 0.9, 0), ((x1 - x0) / 0.9, 1), (0, 1)], want=n)
    box(P.R("lacquer"), ((x0 + x1) / 2, 2.4, z), (x1 - x0 + 0.1, 0.1, 0.05))   # 帽额
    for x in (x0 + 0.15, x1 - 0.15):
        tbox(P.R("misu_cord"), (x, 2.35, z + 0.03), (x, yb + 0.3, z + 0.03), 0.025)
        sphere(P.R("misu_cord"), (x, yb + 0.27, z + 0.03), 0.05, seg=8, rings=5)
    for x in (x0, x1): tbox(P.R("lacquer"), (x, 2.45, z), (x, P.H, z), 0.03)   # 吊绳


def kouban(cx, y, cz, k=1.0):
    """组香的香盘（参考 06）：黑漆格子盒 5×2，格里交替嵌菊纹银片（纸白十六瓣）和金色方片（山吹）"""
    w, d = 0.42 * k, 0.18 * k
    box("fue_lacquer", (cx, y + 0.02 * k, cz), (w, 0.04 * k, d))
    for i in range(5):
        for j in range(2):
            x = cx - w / 2 + w * (i + 0.5) / 5; z = cz - d / 2 + d * (j + 0.5) / 2; yy = y + 0.041 * k
            if (i + j) % 3 == 1: box("fue_gold", (x, yy, z), (0.045 * k, 0.004, 0.045 * k))
            else:
                pts = [(x + math.cos(2 * math.pi * q / 16) * 0.032 * k * (1 if q % 2 else 0.8), yy + 0.002, z + math.sin(2 * math.pi * q / 16) * 0.032 * k * (1 if q % 2 else 0.8)) for q in range(16)]
                face("fue_silver", pts, [(0, 0)] * 16, want=(0, 1, 0))


def fue_pine(h):
    """雪庭的松（参考 04 左边）：墨色弯干、三四团平展的松针，每团顶上一层雪。原点在树根"""
    pts = [(0, 0), (0.15, h * 0.3), (0.05, h * 0.55), (-0.2, h * 0.78)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]): tbox("fue_tree", (ax, ay, 0), (bx, by, 0.02), 0.14)
    for k, (x, y, r) in enumerate(((0.45, h * 0.42, 0.7), (-0.4, h * 0.6, 0.6), (0.2, h * 0.75, 0.55), (-0.25, h * 0.92, 0.45))):
        tbox("fue_tree", (pts[1][0] if k % 2 == 0 else pts[2][0], y - 0.1, 0), (x, y, 0), 0.06)
        for q in range(4):   # 一团松针 = 几个压扁的球挤在一起，顶上一层雪也是压扁的球（11-06 第一版的扁圆柱像飞盘）
            ox, oz, rr = (-0.4 + 0.27 * q) * r, (0.15 if q % 2 else -0.12) * r, r * (0.42 if q in (1, 2) else 0.32)
            flat_ball("fue_pine", (x + ox, y, oz), rr, rr * 0.38)
            flat_ball("fue_snow", (x + ox, y + rr * 0.2, oz), rr * 0.86, rr * 0.22)


def flat_ball(key, c, r, ry, seg=10, rings=5):
    """压扁的球（松针团、雪）：半径 r，竖直半径 ry"""
    n0 = snap(); sphere(key, (0, 0, 0), 1.0, seg=seg, rings=rings)
    g = G[key]
    for i in range(n0.get(key, 0), len(g["v"])):
        v_ = g["v"][i]; g["v"][i] = V(c[0] + v_.x * r, c[1] + v_.y * ry, c[2] + v_.z * r)


def bare_tree(x, z, h, seed, key):
    """枯树（参考 12、17）：墨色枝杈，四层分叉"""
    import random
    rnd = random.Random(seed)
    def branch(p, d, L, w, depth):
        q = p + d * L
        tbox(key, tuple(p), tuple(q), w)
        if depth == 0: return
        for _ in range(rnd.randint(2, 3)):
            nd = (d + V(rnd.uniform(-0.9, 0.9), rnd.uniform(0.0, 0.6), rnd.uniform(-0.9, 0.9))).normalized()
            branch(q, nd, L * rnd.uniform(0.55, 0.75), max(0.015, w * 0.6), depth - 1)
    branch(V(x, 0, z), V(0, 1, 0), h * 0.42, 0.16 * h / 4, 4)


def fue_gate(P, block):
    """板葺的门（参考 16、17：棟門）：一片连着的 E 是门洞；两根粗柱、冠木、两坡屋顶（角色 gate_roof，退魔后是茅草）"""
    for reg in P.regions(lambda i, j: P.at(i, j) == "E"):
        xs = [c[0] for c in reg]; zs = [c[1] for c in reg]
        x0, z0, x1, z1 = mrect((min(xs), min(zs), max(xs) + 1, max(zs) + 1)); cz = (z0 + z1) / 2
        P.cur = reg[0]; wood = P.R("gate_wood"); hh = P.kamoi + 0.5
        for x in (x0 - 0.1, x1 + 0.1):
            box(wood, (x, hh / 2, cz), (0.26, hh, 0.26)); block.append((x - 0.13, cz - 0.13, x + 0.13, cz + 0.13))
        box(wood, ((x0 + x1) / 2, P.kamoi + 0.12, cz), (x1 - x0 + 0.9, 0.22, 0.2))   # 冠木
        box(wood, ((x0 + x1) / 2, hh, cz), (x1 - x0 + 0.5, 0.12, 0.9))
        gable(P.R("gate_roof"), x0 - 0.9, x1 + 0.9, cz - 1.1, cz + 1.1, hh + 0.08, hh + 0.75)
        box(wood, ((x0 + x1) / 2, hh + 0.78, cz), (x1 - x0 + 1.9, 0.08, 0.12))   # 屋脊
        lw = (x1 - x0) / 2   # 门一直开着（文案："门还开着，它在等谁"）：两扇板门往里（-z）推开 80°
        for hx, sg in ((x0, 1), (x1, -1)):
            a = math.radians(80); ex, ez = hx + sg * math.cos(a) * lw, cz - 0.1 - math.sin(a) * lw
            obox(wood, (hx, cz - 0.1), (ex, ez), 0.06, 0.05, P.kamoi)
            for yy in (0.4, P.kamoi - 0.4): obox(wood, (hx + sg * 0.03, cz - 0.13), (ex, ez - 0.03), 0.09, yy, yy + 0.08)   # 横档
        if P.on("ruin"): gate_ruin(P, x0, x1, cz, hh)
    P.cur = None


def wall_cap(P):
    """土塀压顶（参考 16）：墙格连成一排，顶上一道小两坡瓦；wall_cap: all 或者写行号（逗号隔开）"""
    v = P.cfg["wall_cap"]; rows = None if v == "all" else {int(t) for t in v.split(",")}
    for j in range(P.h):
        if rows is not None and j not in rows: continue
        i = 0
        while i < P.w:
            if P.at(i, j) != "#": i += 1; continue
            i0 = i
            while i < P.w and P.at(i, j) == "#": i += 1
            x0, x1 = i0 * CELL, i * CELL; cz = (j + 0.5) * CELL
            P.cur = (i0, j)
            gable(P.R("roof"), x0, x1, cz - 0.32, cz + 0.32, P.H - 0.02, P.H + 0.28)
    P.cur = None


def yuki_surround(P):
    """雪景四周（surround: yuki）：雪地往外铺到 40 米（高度跟雪庭），远处一圈淡墨的枯树、屋顶剪影"""
    import random
    Wm, Dm = P.w * CELL, P.h * CELL; R_ = 40.0; y = -P.doma; g = P.R("snow")
    for r in ((-R_, -R_, Wm + R_, 0), (-R_, Dm, Wm + R_, Dm + R_), (-R_, 0, 0, Dm), (Wm, 0, Wm + R_, Dm)):
        x0, z0, x1, z1 = r
        face(g, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], [(x0 / CELL, -z0 / CELL), (x1 / CELL, -z0 / CELL), (x1 / CELL, -z1 / CELL), (x0 / CELL, -z1 / CELL)], want=(0, 1, 0))
    for j in range(P.h):   # 区块里空着的格子（外廊旁边没画东西的地方）也铺雪，不然从虎之间斜看出去地上有个洞
        for i in range(P.w):
            if P.at(i, j) == " ": floor_quad(g, (i, j, i + 1, j + 1), y=y)
    rnd = random.Random(11); far = P.R("far")
    for n in range(26):
        a = 2 * math.pi * n / 26 + rnd.uniform(-0.08, 0.08); r = rnd.uniform(20, 34)
        cx, cz = Wm / 2 + math.cos(a) * r, Dm / 2 + math.sin(a) * r
        n0 = snap(); bare_tree(cx, cz, rnd.uniform(5, 9), n, far); shift_since(n0, y)
    for n in range(6):
        a = 2 * math.pi * n / 6 + 0.4; r = rnd.uniform(26, 34)
        cx, cz = Wm / 2 + math.cos(a) * r, Dm / 2 + math.sin(a) * r; w_, d_ = rnd.uniform(8, 14), rnd.uniform(6, 9)
        box(far, (cx, y + 1.5, cz), (w_, 3.0, d_)); gable(far, cx - w_ / 2 - 0.6, cx + w_ / 2 + 0.6, cz - d_ / 2 - 0.6, cz + d_ / 2 + 0.6, y + 3.0, y + 5.5)


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
