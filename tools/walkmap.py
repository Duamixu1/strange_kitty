# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""把各块 World Labs 泼溅的 collider.glb 按 cameras.json 的摆放投到世界坐标，栅格化成可走图。
规则：格子 0.1 米；可走 = 脚下有朝上的地面（世界 y 在 -0.6 到 0.5 之间）且腰到头（0.3 到 1.7 米）范围内
没有碰撞面落在身体半径 0.25 米内；门洞按 layout 里 rooms/courtyard 的 door 强制连通；没有泼溅的房间用矩形。
输出：web/src/data/walkmap.json（collision.js 读）和 assets/worldlabs/walkmap.png（肉眼检查）。
用法：uv run tools/walkmap.py [--cell 0.1] [--radius 0.25]"""
import argparse, base64, json, math, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CAMS = ROOT / "web/src/world/cameras.json"

def load_glb(path):
    b = path.read_bytes()
    ln = struct.unpack_from("<I", b, 12)[0]; j = json.loads(b[20:20 + ln])
    boff = 20 + ln; blen = struct.unpack_from("<I", b, boff)[0]; bin_ = b[boff + 8: boff + 8 + blen]
    def acc(i):
        a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
        dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a["componentType"]]
        n = {"SCALAR": 1, "VEC3": 3, "VEC2": 2}[a["type"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(bin_, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)
    V, F = [], []; base = 0
    for m in j["meshes"]:
        for p in m["primitives"]:
            v = acc(p["attributes"]["POSITION"]).astype(np.float64); f = acc(p["indices"]).reshape(-1, 3).astype(np.int64) + base
            V.append(v); F.append(f); base += len(v)
    return np.concatenate(V), np.concatenate(F)

def to_world(v, S):
    # 和 game.js 一致：先绕 X 转 180°（y→-y，z→-z），再绕 Y 转 yawDeg，缩放，平移
    x, y, z = v[:, 0], -v[:, 1], -v[:, 2]
    t = math.radians(S.get("yawDeg", 0)); c, s = math.cos(t), math.sin(t)
    xw, zw = x * c + z * s, -x * s + z * c
    out = np.stack([xw, y, zw], 1) * S["scale"]
    return out + np.array(S["position"])

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cell", type=float, default=0.1); ap.add_argument("--radius", type=float, default=0.25)
    ap.add_argument("--step", type=float, default=0.25, help="比脚下地面高出多少算障碍、相邻格高差多少算台阶")
    ap.add_argument("--body-hi", type=float, default=1.7)
    a = ap.parse_args(); cell = a.cell
    L = json.loads(CAMS.read_text(encoding="utf-8"))["layout"]
    meshes = []
    for S in L.get("splats", []):
        V, F = load_glb(ROOT / f"assets/worldlabs/{S['name']}/collider.glb")
        if str(S.get("quality", "")).endswith("_level"):       # 泼溅用了 spz_level.py 校平的文件，碰撞网格按同一条剖面校平
            lv = json.loads((ROOT / f"assets/worldlabs/{S['name']}/level.json").read_text(encoding="utf-8"))
            V = V.copy(); V[:, 1] -= np.interp(V[:, 2], lv["z"], lv["y"]) - lv["f0"]
        if "clipZmin" in S:
            keep = V[F].mean(1)[:, 2] >= S["clipZmin"]; F = F[keep]
        meshes.append((S["for"], to_world(V, S)[F]))   # (n,3,3)
        print(f"{S['name']}: {len(F)} 个三角形 → 世界")
    rects = []   # 没泼溅的房间和门洞
    have = {m[0] for m in meshes}; pad = 0.3
    for name, r in list(L["rooms"].items()) + [("courtyard", L["courtyard"])]:
        if name not in have:
            rects.append(("room", r["x"][0] + pad, r["x"][1] - pad, r["z"][0] + pad, r["z"][1] - pad))
        d = r["door"]; sgn = 1 if d[0] > 0 else -1
        rects.append(("door", min(d[0] - sgn * 1.6, d[0] + sgn * 1.2), max(d[0] - sgn * 1.6, d[0] + sgn * 1.2), d[2] - 0.6, d[2] + 0.6))
    pts = np.concatenate([m[1].reshape(-1, 3) for m in meshes])
    x0 = math.floor(min(pts[:, 0].min(), *[r[1] for r in rects]) - 0.5); x1 = math.ceil(max(pts[:, 0].max(), *[r[2] for r in rects]) + 0.5)
    z0 = math.floor(min(pts[:, 2].min(), *[r[3] for r in rects]) - 0.5); z1 = math.ceil(max(pts[:, 2].max(), *[r[4] for r in rects]) + 0.5)
    W, H = int((x1 - x0) / cell), int((z1 - z0) / cell)
    NONE = 9e9
    floor = np.full((H, W), NONE); blocked = np.zeros((H, W), bool)
    cxs = x0 + (np.arange(W) + 0.5) * cell; czs = z0 + (np.arange(H) + 0.5) * cell
    R = a.radius

    def cells_of(t, grow):
        P = t[:, [0, 2]]
        i0 = max(0, int((P[:, 0].min() - grow - x0) / cell)); i1 = min(W - 1, int((P[:, 0].max() + grow - x0) / cell))
        j0 = max(0, int((P[:, 1].min() - grow - z0) / cell)); j1 = min(H - 1, int((P[:, 1].max() + grow - z0) / cell))
        if i1 < i0 or j1 < j0: return None
        gx, gz = np.meshgrid(cxs[i0:i1 + 1], czs[j0:j1 + 1]); q = np.stack([gx, gz], -1)
        v0, v1, v2 = P[0], P[1] - P[0], P[2] - P[0]; den = v1[0] * v2[1] - v2[0] * v1[1]
        if abs(den) < 1e-12: inside = np.zeros(gx.shape, bool); l1 = l2 = np.zeros(gx.shape)
        else:
            d = q - v0; l1 = (d[..., 0] * v2[1] - v2[0] * d[..., 1]) / den; l2 = (v1[0] * d[..., 1] - d[..., 0] * v1[1]) / den
            inside = (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
        return i0, i1, j0, j1, q, P, inside, l1, l2

    # 第一遍：地面 = 这一格里最低的那层近水平面（走廊的泼溅地面是斜的，门口和尽头差 2 米，所以不能用固定高度带）
    tris = [T for _, T in meshes]
    for T in tris:
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ny = np.abs(n[:, 1]) / (np.linalg.norm(n, axis=1) + 1e-12)
        for t in T[ny > 0.7]:
            r = cells_of(t, 0.0)
            if r is None: continue
            i0, i1, j0, j1, q, P, inside, l1, l2 = r
            hgt = t[0, 1] + l1 * (t[1, 1] - t[0, 1]) + l2 * (t[2, 1] - t[0, 1])
            sub = floor[j0:j1 + 1, i0:i1 + 1]; np.minimum(sub, np.where(inside, hgt, NONE), out=sub)
    has = floor < NONE
    # 第二遍：障碍。竖直面（墙、柱，|ny|<0.3）按整面的高度范围判断：落在这一格"地面以上 step 到 body_hi"的身体带、离格子中心不到 R 就挡。
    # 斜面和水平面（屋檐、天空穹顶、桌面）按这一格正上方（或最近边上）的插值高度判断，不然中庭的天空穹顶这种大斜面会把整个院子挡掉。
    for T in tris:
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nyv = np.abs(n[:, 1]) / (np.linalg.norm(n, axis=1) + 1e-12)
        for t, ny_ in zip(T, nyv):
            if t[:, 1].min() > a.body_hi + 3 or t[:, 1].max() < -3: continue
            r = cells_of(t, R)
            if r is None: continue
            i0, i1, j0, j1, q, P, inside, l1, l2 = r
            f = floor[j0:j1 + 1, i0:i1 + 1]
            if ny_ < 0.3:
                band = (t[:, 1].max() > f + a.step) & (t[:, 1].min() < f + a.body_hi) & (f < NONE)
                if not band.any(): continue
                near = inside.copy()
                for e0, e1 in ((P[0], P[1]), (P[1], P[2]), (P[2], P[0])):
                    ev = e1 - e0; el = ev @ ev + 1e-12; tt = np.clip(((q - e0) @ ev) / el, 0, 1)
                    near |= np.linalg.norm(q - (e0 + tt[..., None] * ev), axis=-1) <= R
                blocked[j0:j1 + 1, i0:i1 + 1] |= near & band
            else:
                hgt = np.where(inside, t[0, 1] + l1 * (t[1, 1] - t[0, 1]) + l2 * (t[2, 1] - t[0, 1]), np.nan)
                dist = np.where(inside, 0.0, np.inf)
                for k0, k1 in ((0, 1), (1, 2), (2, 0)):
                    e0, e1 = P[k0], P[k1]; ev = e1 - e0; el = ev @ ev + 1e-12; tt = np.clip(((q - e0) @ ev) / el, 0, 1)
                    dd = np.linalg.norm(q - (e0 + tt[..., None] * ev), axis=-1); he = t[k0, 1] + tt * (t[k1, 1] - t[k0, 1])
                    better = (dd < dist) & ~inside
                    dist = np.where(better, dd, dist); hgt = np.where(better, he, hgt)
                hit = (dist <= R) & (hgt > f + a.step) & (hgt < f + a.body_hi) & (f < NONE)
                blocked[j0:j1 + 1, i0:i1 + 1] |= hit
    # 台阶：相邻格地面高差超过 step 的两边都不让站（桌面、矮柜顶会被当成"高一截的地面"）
    fz = np.where(has, floor, np.nan)
    for dj, di in ((1, 0), (0, 1)):
        a1 = fz[: H - dj, : W - di]; a2 = fz[dj:, di:]
        jump = np.abs(a1 - a2) > a.step
        blocked[: H - dj, : W - di] |= jump; blocked[dj:, di:] |= jump
    walk = has & ~blocked
    for kind, rx0, rx1, rz0, rz1 in rects:
        if kind == "door": continue          # 门洞不用固定矩形，下面按实际可走区挖通
        i0, i1 = int((rx0 - x0) / cell), int((rx1 - x0) / cell); j0, j1 = int((rz0 - z0) / cell), int((rz1 - z0) / cell)
        walk[j0:j1 + 1, i0:i1 + 1] = True
    # 门洞：先给可走格分连通块。从门口沿 x 往走廊方向挖，直到挖进"开场点所在的那一块"；往房间方向挖，直到挖进"房间矩形里最大的那一块"（各最多 4 米）
    def label(mask):
        lab = np.zeros(mask.shape, np.int32); k = 0
        for j0_, i0_ in zip(*np.where(mask)):
            if lab[j0_, i0_]: continue
            k += 1; st = [(j0_, i0_)]; lab[j0_, i0_] = k
            while st:
                j, i = st.pop()
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < H and 0 <= ii < W and mask[jj, ii] and not lab[jj, ii]: lab[jj, ii] = k; st.append((jj, ii))
        return lab
    lab = label(walk)
    start = L["gate"].get("start", [0, 0, -2.4]); main_id = lab[int((start[2] - z0) / cell), int((start[0] - x0) / cell)]
    carved = []
    for name, r in list(L["rooms"].items()) + [("courtyard", L["courtyard"])]:
        dx, _, dz = r["door"]; sgn = 1 if dx > 0 else -1
        ri0, ri1 = sorted((int((r["x"][0] - x0) / cell), int((r["x"][1] - x0) / cell))); rj0, rj1 = sorted((int((r["z"][0] - z0) / cell), int((r["z"][1] - z0) / cell)))
        ids, cnt = np.unique(lab[rj0:rj1 + 1, ri0:ri1 + 1][lab[rj0:rj1 + 1, ri0:ri1 + 1] > 0], return_counts=True)
        room_id = ids[np.argmax(cnt)] if len(ids) else -1
        j0, j1 = int((dz - 0.6 - z0) / cell), int((dz + 0.6 - z0) / cell); jm = (j0 + j1) // 2
        ic = int((dx - x0) / cell)
        for direction, target in ((-sgn, main_id), (sgn, room_id)):
            i = ic; steps = 0
            while 0 <= i < W and steps < int(4.0 / cell):
                if (lab[jm - 2: jm + 3, i] == target).all() and steps > 0: break
                walk[j0:j1 + 1, i] = True; i += direction; steps += 1
            carved.append((name, "→走廊" if target == main_id else "→房间", steps))
    print("门洞挖通：" + "，".join(f"{n}{d} {s * cell:.1f}m" for n, d, s in carved))
    for j in range(H):
        row = has[j]
        if walk[j].any() and (walk[j] & ~row).any() and row.any():
            idx = np.where(row)[0]
            for i in np.where(walk[j] & ~row)[0]:
                k = idx[np.argmin(np.abs(idx - i))]; floor[j, i] = floor[j, k]; has[j, i] = True
    # 只保留和开场点连通的区域，去掉泼溅里零碎的孤岛
    start = L["gate"].get("start", [0, 0, -2.4]); si, sj = int((start[0] - x0) / cell), int((start[2] - z0) / cell)
    seen = np.zeros_like(walk); stack = [(sj, si)]; seen[sj, si] = walk[sj, si]
    while stack:
        j, i = stack.pop()
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < H and 0 <= ii < W and walk[jj, ii] and not seen[jj, ii]: seen[jj, ii] = True; stack.append((jj, ii))
    islands = int(walk.sum() - seen.sum()); walk = seen
    out = {"cell": cell, "x0": x0, "z0": z0, "w": W, "h": H, "radius": R,
           "_说明": "rows[j][i] 为 '1' 表示格子中心 (x0+(i+0.5)*cell, z0+(j+0.5)*cell) 可站。tools/walkmap.py 生成，别手改",
           "rows": ["".join("1" if v else "0" for v in row) for row in walk],
           "_floor说明": "floor 是每格地面高度（厘米，int16 小端，base64，行优先），没有地面的格子是 -32768；门洞强制连通的格子取左右最近的地面",
           "floor": base64.b64encode(np.where(has, np.round(floor * 100), -32768).astype("<i2").tobytes()).decode()}
    (ROOT / "web/src/data/walkmap.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    # 预览图：可走白、有地面但被挡灰、无地面纸色；门洞和矩形用线框
    img = Image.new("RGB", (W * 4, H * 4), "#F1E9DA"); px = np.array(img)
    sc = np.kron(np.where(walk, 2, np.where(has, 1, 0)), np.ones((4, 4), int))
    px[sc == 1] = (160, 150, 160); px[sc == 2] = (255, 255, 255); img = Image.fromarray(px.astype(np.uint8)); dr = ImageDraw.Draw(img)
    for kind, rx0, rx1, rz0, rz1 in rects:
        dr.rectangle([(rx0 - x0) / cell * 4, (rz0 - z0) / cell * 4, (rx1 - x0) / cell * 4, (rz1 - z0) / cell * 4], outline=(230, 102, 122) if kind == "door" else (79, 116, 191), width=2)
    for name, r in list(L["rooms"].items()) + [("courtyard", L["courtyard"])]:
        dr.text(((r["x"][0] - x0) / cell * 4 + 6, (r["z"][0] - z0) / cell * 4 + 6), name, fill=(50, 45, 72))
    dr.text((6, 6), f"walkmap {cell} m/格  x {x0}..{x1}  z {z0}..{z1}  白=可走 灰=有地面被挡 纸=无地面  去掉孤岛 {islands} 格", fill=(50, 45, 72))
    img.save(ROOT / "assets/worldlabs/walkmap.png")
    print(f"栅格 {W}x{H}，可走 {int(walk.sum())} 格（{walk.sum() * cell * cell:.1f} 平方米），孤岛去掉 {islands} 格 → web/src/data/walkmap.json，预览 assets/worldlabs/walkmap.png")

if __name__ == "__main__":
    main()
