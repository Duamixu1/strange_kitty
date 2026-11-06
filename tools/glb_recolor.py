# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""物怪变体（docs/18 第九节）：不重新建模，只把 GLB 里那张贴图换个配色，网格、骨架、动作原样留着，不花积分。
  uv run tools/glb_recolor.py                 按 VARIANTS 全出一遍 → assets/processed/<变体名>_posed.glb
  uv run tools/glb_recolor.py --dump 目录     把原贴图和换色后的贴图存出来对比
换色在 HSV 里按色相 / 明度挑像素（规则见 VARIANTS），边缘用软过渡，墨线（很暗、不饱和的像素）不动。"""
import json, struct, sys, io
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "assets/processed"


def rgb2hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; mx = a.max(-1); mn = a.min(-1); d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return np.stack([h, np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0), mx], -1)


def hsv2rgb(x):
    h, s, v = x[..., 0] % 360, x[..., 1], x[..., 2]; c = v * s; hp = h / 60; xx = c * (1 - np.abs(hp % 2 - 1)); m = v - c
    z = np.zeros_like(h); k = np.floor(hp).astype(int) % 6
    rgb = np.select([k[..., None] == i for i in range(6)], [np.stack(t, -1) for t in [(c, xx, z), (xx, c, z), (z, c, xx), (z, xx, c), (xx, z, c), (c, z, xx)]])
    return rgb + m[..., None]


def hue_near(h, c, w): return np.clip(1 - (np.abs((h - c + 180) % 360 - 180) - w) / 12, 0, 1)   # 离色相 c 在 ±w 度内 = 1，再往外 12 度软过渡


def recolor(img, rules):
    a = np.asarray(img.convert("RGB")).astype(float) / 255; x = rgb2hsv(a); out = x.copy()
    for r in rules:
        h, s, v = x[..., 0], x[..., 1], x[..., 2]
        m = np.ones_like(h)
        if "hue" in r: m *= hue_near(h, *r["hue"])
        if "smin" in r: m *= np.clip((s - r["smin"]) / 0.1, 0, 1)
        if "smax" in r: m *= np.clip((r["smax"] - s) / 0.08, 0, 1)
        if "vmax" in r: m *= np.clip((r["vmax"] - v) / 0.08, 0, 1)
        if "vmin" in r: m *= np.clip((v - r["vmin"]) / 0.08, 0, 1)
        t = out.copy()
        if "to_hue" in r: t[..., 0] = r["to_hue"]
        if "sat" in r: t[..., 1] = np.clip(x[..., 1] * r["sat"], 0, 1)
        if "sat_to" in r: t[..., 1] = r["sat_to"]   # 直接定饱和度（黑、白、灰本来没有饱和度，乘不上去）
        if "val" in r: t[..., 2] = np.clip(r["val"][0] + x[..., 2] * r["val"][1], 0, 1)   # 新明度 = 常数 + 原明度 × 倍数
        # 色相按圆周插，饱和度、明度线性插
        dh = (t[..., 0] - out[..., 0] + 180) % 360 - 180
        out[..., 0] = out[..., 0] + dh * m; out[..., 1:] = out[..., 1:] * (1 - m[..., None]) + t[..., 1:] * m[..., None]
    return Image.fromarray((np.clip(hsv2rgb(out), 0, 1) * 255).astype(np.uint8))


# 变体：名字 → 原模型、换色规则。scale / speed / count 是给代码的建议（出场时缩放、动作播放倍率、一次出几只），写在 docs/18 第九节
VARIANTS = {
    # 白化猫：黑底毛色翻成骨白、微带紫，金红火纹不动
    "bakeneko_shiro": dict(src="bakeneko", rules=[{"vmax": 0.45, "val": (0.97, 0.2), "sat": 0.08, "to_hue": 265}]),
    # 小化猫（一群）：用原配色，只是小、快、三只一起出，不另出模型
    # 黑唐伞：朱红伞纸压成墨黑带一点靛蓝，靛蓝那条带子换成朱红
    "karakasa_kuro": dict(src="karakasa", rules=[{"hue": (225, 25), "smin": 0.25, "to_hue": 355, "sat": 1.2, "val": (0.25, 0.9)},
                                                  {"hue": (2, 16), "smin": 0.42, "to_hue": 235, "sat": 0.55, "val": (0.04, 0.32)}]),
    # 青座敷：朱红和服换成青绿，金色手鞠纹、粉梅花不动
    "zashiki_ao": dict(src="zashiki", rules=[{"hue": (0, 16), "smin": 0.45, "vmin": 0.25, "to_hue": 172, "sat": 0.85, "val": (0.0, 0.85)}]),
}


def read_glb(path):
    b = path.read_bytes(); jl = struct.unpack("<I", b[12:16])[0]; j = json.loads(b[20:20 + jl])
    o = 20 + jl; bl = struct.unpack("<I", b[o:o + 4])[0]; return j, bytearray(b[o + 8:o + 8 + bl])


def write_glb(path, j, binb):
    js = json.dumps(j, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4); binb = bytes(binb) + b"\0" * (-len(binb) % 4)
    total = 12 + 8 + len(js) + 8 + len(binb)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binb), 0x004E4942) + binb)


def replace_image(j, binb, idx, data):
    """换掉第 idx 张图的字节：它后面的 bufferView 整体往后挪（按 4 字节对齐）"""
    bv = j["bufferViews"][j["images"][idx]["bufferView"]]; o, n = bv.get("byteOffset", 0), bv["byteLength"]
    pad = (-len(data)) % 4; new = data + b"\0" * pad; shift = len(new) - (n + (-n) % 4)
    rest = binb[o + n + (-n) % 4:]
    for v in j["bufferViews"]:
        if v.get("byteOffset", 0) > o: v["byteOffset"] += shift
    bv["byteLength"] = len(data)
    out = binb[:o] + new + rest; j["buffers"][0]["byteLength"] = len(out); return out


def main():
    dump = Path(sys.argv[sys.argv.index("--dump") + 1]) if "--dump" in sys.argv else None
    for name, v in VARIANTS.items():
        j, binb = read_glb(P / f"{v['src']}_posed.glb")
        for i, im in enumerate(j["images"]):
            bv = j["bufferViews"][im["bufferView"]]; o = bv.get("byteOffset", 0)
            src = Image.open(io.BytesIO(bytes(binb[o:o + bv["byteLength"]])))
            dst = recolor(src, v["rules"]); buf = io.BytesIO(); dst.save(buf, "JPEG", quality=88)
            if dump: dump.mkdir(parents=True, exist_ok=True); src.convert("RGB").save(dump / f"{name}_{i}_原.jpg"); dst.save(dump / f"{name}_{i}_变.jpg")
            binb = replace_image(j, binb, i, buf.getvalue()); im["mimeType"] = "image/jpeg"
        out = P / f"{name}_posed.glb"; write_glb(out, j, binb); print(f"{name}: {out.relative_to(ROOT)} {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
