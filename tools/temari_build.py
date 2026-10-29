"""
手鞠物怪本体：程序画贴图 + 正球，不花积分。纹样以 assets/concept/scenes/07_手鞠_本体.png 左边那颗为准：
两极各一朵 12 瓣菊花星（珊瑚瓣压在山吹瓣上，中心墨点），中纬是山吹线围出的三角格（藍 / 青磁 / 藤），
赤道一圈藍底纸白青海波，上下各一道山吹线收边。只用色板 12 色，描边墨色 #322D48。

  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/temari_build.py
  → assets/processed/temari.glb（半径 0.36 米，球心为原点，两极朝 ±Y，和 web/src/world/temari.js 一致）
    assets/processed/temari_tex.png（贴图，等距柱状投影 2048x1024）
    assets/processed/shots/temari_*.png（三个角度的预览）
"""
import math, os, sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/processed"
RADIUS = 0.36
W, H, SS = 2048, 1024, 2          # 先画 2 倍再缩小，边缘抗锯齿

HEX = {"paper": "F1E9DA", "coral": "E6667A", "crimson": "B42A47", "ochre": "DCC67C", "teal": "49B3A6",
       "indigo": "4F74BF", "wisteria": "6A4C8C", "navy": "2A2A4E", "lavender": "D6D3EF", "ink": "322D48"}
NAMES = list(HEX)
COL = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in HEX.values()], dtype=np.float32)
L = {n: i for i, n in enumerate(NAMES)}

N_PETAL = 12          # 菊花瓣数（07 左边那颗约 12 瓣）
KIKU = 52.0           # 菊花区从极点到瓣尖的余纬（度）：07 里菊花盖住大半个上半球
BAND = 24.0           # 青海波带的半宽（纬度）
P_WAVE = 360 / 10     # 青海波水平周期（度），整除 360 才无缝


def petal(c, a, length, widest=0.6, fill=0.55):
    """叶形花瓣，按球面上的实际宽度画（不按经度扇区，否则越靠极点越细）。
    c 余纬（度），a 在本瓣扇区里的偏移（-0.5~0.5），fill = 最宽处占一个扇区宽度的比例。"""
    t = c / length
    shape = np.where(t < widest, np.sqrt(np.clip(t / widest, 0, 1)), np.clip((1 - t) / (1 - widest), 0, 1) ** 0.8)
    sect = 2 * math.pi / N_PETAL
    hmax = fill * math.sin(math.radians(widest * length)) * sect      # 最宽处的半宽（单位球上的弧长）
    a_lim = hmax * shape / np.maximum(np.sin(np.radians(c)) * sect, 1e-6)
    return (t <= 1) & (np.abs(a) <= a_lim)


def paint():
    w, h = W * SS, H * SS
    lon = (np.arange(w) + 0.5) / w * 360.0
    lat = 90.0 - (np.arange(h) + 0.5) / h * 180.0
    LON, LAT = np.meshgrid(lon, lat)
    c = 90.0 - np.abs(LAT)                                   # 到最近极点的余纬
    south = LAT < 0
    lonp = np.where(south, LON + 180.0 / N_PETAL, LON)      # 南极花瓣错开半瓣
    lab = np.full((h, w), L["indigo"], dtype=np.int16)

    # 1) 中纬三角格：山吹锯齿线把 KIKU-8 到 赤道带 之间分成上下交错的三角
    sect = 360.0 / N_PETAL
    f = (lonp / sect) % 1.0
    k = np.floor(lonp / sect).astype(int)
    z0 = KIKU - 14
    zone = (c > z0) & (np.abs(LAT) > BAND)
    span = (90 - BAND) - z0
    s = np.clip((c - z0) / span, 0, 1)              # 0 = 靠极点，1 = 靠赤道
    zig = np.abs(f - 0.5) * 2                                 # 0 在扇区中线，1 在扇区边
    up = zig < (1 - s)                                        # 尖朝赤道的三角 vs 尖朝极点的三角
    tri_cols = np.array([L["teal"], L["wisteria"], L["indigo"], L["teal"], L["indigo"], L["wisteria"]])
    tri = np.where(up, tri_cols[k % 6], tri_cols[(k + 3) % 6])
    lab = np.where(zone, tri, lab)
    # 菊花区的底色（花瓣缝里露出来的）
    lab = np.where(c <= z0, L["navy"], lab)

    # 2) 菊花：后层山吹瓣（错开半瓣、更长），前层珊瑚瓣
    a_back = ((lonp / sect + 0.5) % 1.0) - 0.5
    a_front = ((lonp / sect) % 1.0) - 0.5
    back = petal(c, a_back, KIKU, widest=0.6, fill=0.48)
    front = petal(c, a_front, KIKU - 7, widest=0.55, fill=0.4)
    lab = np.where(back, L["ochre"], lab)
    lab = np.where(front, L["coral"], lab)
    vein = front & (np.abs(a_front) * np.sin(np.radians(c)) < 0.004) & (c > 5) & (c < (KIKU - 7) * 0.8)   # 瓣中线，按球面等粗；描边之后再画
    lab = np.where(c < 2.2, L["ink"], lab)                   # 中心墨点

    # 3) 赤道青海波：一排排圆，后画的（靠下的）压住前面的
    band = np.abs(LAT) <= BAND
    R = P_WAVE / 2
    step = R / 2
    rows = np.arange(BAND + R, -BAND - R - step, -step)
    wave = np.full((h, w), -1, dtype=np.int16)
    for j, yc in enumerate(rows):
        off = (P_WAVE / 2) if j % 2 else 0.0
        dx = ((LON - off) % P_WAVE) - P_WAVE / 2
        dy = LAT - yc
        d = np.sqrt(dx * dx + dy * dy) / R
        inside = band & (d < 1.0)
        ring = np.full((h, w), L["indigo"], dtype=np.int16)
        for r0, r1 in [(0.86, 0.93), (0.62, 0.69), (0.38, 0.45), (0.0, 0.2)]:
            ring = np.where((d >= r0) & (d < r1), L["paper"], ring)
        wave = np.where(inside, ring, wave)
    lab = np.where(band & (wave >= 0), wave, lab)

    # 4) 带边：山吹线
    edge = (np.abs(np.abs(LAT) - BAND) < 1.1)
    lab = np.where(edge, L["ochre"], lab)
    # 三角格的锯齿线也画成山吹
    zz = zone & (np.abs(zig - (1 - s)) < 0.06 / np.maximum(np.cos(np.radians(LAT)), 0.2))
    lab = np.where(zz & ~edge, L["ochre"], lab)

    # 5) 描边：颜色分界处画墨线。经向的线在高纬被等距柱状拉宽，按 1/cos(lat) 加粗水平方向才能在球面上等粗
    diff_y = np.zeros_like(lab, dtype=bool)
    diff_y[1:] |= lab[1:] != lab[:-1]
    diff_x = np.zeros_like(lab, dtype=bool)
    diff_x[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    diff_x[:, 0] |= lab[:, 0] != lab[:, -1]
    base = 1.6 * SS
    ink = np.zeros_like(diff_y)
    for dy in range(-int(base), int(base) + 1):
        ink |= np.roll(diff_y, dy, axis=0)
    for y in range(h):
        row = diff_x[y]
        if not row.any():
            continue
        wpx = int(min(base / max(math.cos(math.radians(lat[y])), 0.03), w / 8))
        cs = np.concatenate([[0], np.cumsum(np.concatenate([row[-wpx:], row, row[:wpx]]))])
        win = cs[2 * wpx + 1:] - cs[:-2 * wpx - 1]
        ink[y] |= win[: w] > 0
    keep_center = c < 2.2
    lab = np.where(ink & ~keep_center, L["ink"], lab)
    lab = np.where(vein, L["paper"], lab)

    img = COL[lab]                                            # h, w, 3
    img = img.reshape(H, SS, W, SS, 3).mean(axis=(1, 3))      # 缩回 2048x1024
    return img / 255.0


def build(img):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 贴图
    im = bpy.data.images.new("temari_tex", W, H, alpha=False)
    rgba = np.ones((H, W, 4), dtype=np.float32)
    rgba[..., :3] = img[::-1]                                 # Blender 图像原点在左下
    im.pixels.foreach_set(rgba.ravel())                       # 不要在这之后改 colorspace：会把像素清空成黑色（默认已是 sRGB）
    im.update()
    tex_path = OUT / "temari_tex.png"
    im.filepath_raw = str(tex_path); im.file_format = "PNG"; im.save()
    im.pack()
    # 球
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=RADIUS, location=(0, 0, 0))
    ob = bpy.context.active_object; ob.name = "temari"
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new("temari"); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = im
    nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    ob.data.materials.append(mat)
    return ob, mat, im


def render(ob):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.view_settings.view_transform = "Standard"   # 不加这句颜色会被 AgX 压灰，和色板对不上
    sc.display.shading.light = "FLAT"; sc.display.shading.color_type = "TEXTURE"
    sc.render.resolution_x = sc.render.resolution_y = 900
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.88, 0.82, 0.7)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = RADIUS * 2.3
    shots = OUT / "shots"; shots.mkdir(parents=True, exist_ok=True)
    for name, (el, az) in {"side": (0, 0), "tilt": (35, 30), "top": (89.9, 0)}.items():
        e, z = math.radians(el), math.radians(az)
        d = 3.0
        cam.location = (d * math.cos(e) * math.sin(z), -d * math.cos(e) * math.cos(z), d * math.sin(e))
        cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(shots / f"temari_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    img = paint()
    ob, mat, im = build(img)
    out = OUT / "temari.glb"
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=False,
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                              export_image_format="AUTO", export_yup=True)
    print(f"[temari] wrote {out} {os.path.getsize(out) / 1e6:.2f} MB")
    if "--no-render" not in sys.argv:
        render(ob)


main()
