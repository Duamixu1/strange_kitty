# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""游览版第一步：积木走廊 vs 泼溅走廊对比图。顶上一行是预告片参考帧，下面每个机位一行：左积木、右泼溅。
  tools/kit_shots.sh kit && tools/kit_shots.sh splat
  uv run tools/kit_compare_sheet.py
  → assets/processed/shots/kitcmp_对比_积木vs泼溅.jpg
  uv run tools/kit_compare_sheet.py view <区块名>
  → assets/processed/shots/kitview_<区块名>_对比.jpg：左上是大奥积木走廊（画风基准），后面是这个区块的各机位"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SH = ROOT / "assets/processed/shots"
SHOTS = ["1_入口一点透视", "2_药郎正侧面", "3_贴近左墙0.8米", "4_回头看门口"]
W, GAP, LAB = 760, 14, 30
try: font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 22)
except OSError: font = ImageFont.load_default()


def fit(p, w):
    im = Image.open(p).convert("RGB"); return im.resize((w, round(im.height * w / im.width)))


if len(sys.argv) > 2 and sys.argv[1] == "view":
    plan = sys.argv[2]
    shots = [SH / "kitcmp_kit_1_入口一点透视.jpg"] + sorted(SH.glob(f"kitview_{plan}_[0-9]*.jpg"))
    labels = ["画风基准 · 大奥积木走廊"] + [p.stem.replace(f"kitview_{plan}_", f"{plan} · ") for p in shots[1:]]
    ims = [fit(p, W) for p in shots]; rh = ims[0].height; rows = (len(ims) + 1) // 2
    sheet = Image.new("RGB", (W * 2 + GAP * 3, GAP + rows * (LAB + rh + GAP)), "#F1E9DA"); d = ImageDraw.Draw(sheet)
    for k, (im, lb) in enumerate(zip(ims, labels)):
        x, y = GAP + (k % 2) * (W + GAP), GAP + (k // 2) * (LAB + rh + GAP)
        d.text((x, y), lb, fill="#322D48", font=font); sheet.paste(im, (x, y + LAB))
    out = SH / f"kitview_{plan}_对比.jpg"; sheet.save(out, quality=88); print(out); sys.exit()

ref = Image.open(ROOT / "assets/concept/ref/ref_04s_走廊_大奥主廊.jpg").convert("RGB")
ref = ref.crop((0, 138, ref.width, ref.height - 138))   # 去掉黑边
ref = ref.resize((W, round(ref.height * W / ref.width)))
rows = [(fit(SH / f"kitcmp_kit_{s}.jpg", W), fit(SH / f"kitcmp_splat_{s}.jpg", W), s) for s in SHOTS]
rh = rows[0][0].height
H = GAP + LAB + ref.height + GAP + len(rows) * (LAB + rh + GAP)
sheet = Image.new("RGB", (W * 2 + GAP * 3, H), "#F1E9DA"); d = ImageDraw.Draw(sheet)
y = GAP
d.text((GAP, y), "参考：唐傘预告片 大奥主廊（只放本机）", fill="#322D48", font=font)
d.text((GAP * 2 + W, y), "左列 积木版（Blender 脚本 + 概念图贴襖绘）   右列 泼溅版（World Labs）", fill="#322D48", font=font)
sheet.paste(ref, (GAP, y + LAB)); y += LAB + ref.height + GAP
for a, b, s in rows:
    d.text((GAP, y), f"积木 · {s}", fill="#322D48", font=font); d.text((GAP * 2 + W, y), f"泼溅 · {s}", fill="#322D48", font=font)
    sheet.paste(a, (GAP, y + LAB)); sheet.paste(b, (GAP * 2 + W, y + LAB)); y += LAB + rh + GAP
out = SH / "kitcmp_对比_积木vs泼溅.jpg"
sheet.save(out, quality=88); print(out)
