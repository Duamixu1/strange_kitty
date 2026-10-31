# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""把一组定格截图横着拼成一条（侧面走路连续帧用）：uv run tools/strip.py 输出 标题 图1 图2 ...
每张按人物所在区域裁（去掉左右空白），统一高度，下面标文件名里的秒数。"""
import sys, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

out, title, files = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 22)
ims = []
for f in files:
    im = Image.open(f).convert("RGB"); w, h = im.size
    ims.append(im.crop((int(w * 0.2), int(h * 0.08), int(w * 0.8), int(h * 0.9))))
cw, ch = ims[0].size
sheet = Image.new("RGB", (cw * len(ims), ch + 70), "#F1E9DA"); d = ImageDraw.Draw(sheet)
d.text((10, 6), title, fill="#322D48", font=font)
for i, (im, f) in enumerate(zip(ims, files)):
    sheet.paste(im, (i * cw, 40))
    m = re.search(r"_([\d.]+)_[A-Z0-9]+\.jpg$", f)
    d.text((i * cw + 10, ch + 42), f"{m.group(1)} 秒" if m else Path(f).stem, fill="#322D48", font=font)
sheet.save(out, quality=88); print(out, sheet.size)
