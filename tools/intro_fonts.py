# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools", "brotli"]
# ///
"""
缘起手册的毛笔字体（11-07 文案w；用户："正文用刘建毛草，其他你决定"）。
只抽手册里实际用到的字，做成很小的 woff2 放在自己站点上（不走 Google Fonts：国内常打不开）。

  中文正文  刘建毛草（草书）   → web/public/fonts/intro_zh_body.woff2   （intro.cards 的 t）
  中文标题  志莽行书（行书）   → web/public/fonts/intro_zh_title.woff2  （intro.cards 的 k、go 按钮）
  日文      祐字肅（毛笔）     → web/public/fonts/intro_ja.woff2        （text.ja.json 的 k / t / go）
  英文      Cormorant 斜体     → web/public/fonts/intro_en.woff2        （拉丁字母全套，以后改字也不用重做）

都是 SIL OFL 开源字体（github.com/google/fonts/ofl/...），原文件第一次跑时下到 assets/fonts/_src/（不进 git）。
改了 intro.cards 的字以后重跑一次：  uv run tools/intro_fonts.py
少了的字浏览器会退回宋体，不会坏，只是那个字不是毛笔。
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/fonts/_src"
OUT = ROOT / "web/public/fonts"
TEXT = ROOT / "web/src/data/tour"
GH = "https://github.com/google/fonts/raw/main/ofl/"
FONTS = {
    "LiuJianMaoCao-Regular.ttf": "liujianmaocao/LiuJianMaoCao-Regular.ttf",
    "ZhiMangXing-Regular.ttf": "zhimangxing/ZhiMangXing-Regular.ttf",
    "YujiSyuku-Regular.ttf": "yujisyuku/YujiSyuku-Regular.ttf",
    "CormorantGaramond-Italic.ttf": "cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf",
}


def fetch():
    SRC.mkdir(parents=True, exist_ok=True)
    for name, path in FONTS.items():
        dst = SRC / name
        if not dst.exists():
            print("下载", name)
            urllib.request.urlretrieve(GH + path, dst)


def cards(fname):
    return json.loads((TEXT / fname).read_text(encoding="utf-8")).get("intro.cards", [])


def subset(font, text, out, extra=()):
    chars = "".join(sorted(set(text + " ·・、。，")))
    args = [sys.executable, "-m", "fontTools.subset", str(SRC / font), f"--text={chars}", f"--output-file={OUT / out}",
            "--flavor=woff2", "--layout-features=*", "--no-hinting", *extra]
    subprocess.run(args, check=True)
    print(f"{out}: {len(set(chars))} 字，{(OUT / out).stat().st_size // 1024} KB")


def main():
    fetch()
    OUT.mkdir(parents=True, exist_ok=True)
    zh, ja = cards("text.json"), cards("text.ja.json")
    subset("LiuJianMaoCao-Regular.ttf", "".join(c.get("t", "") for c in zh), "intro_zh_body.woff2")
    subset("ZhiMangXing-Regular.ttf", "".join(c.get("k", "") + c.get("go", "") for c in zh) + "展开长卷", "intro_zh_title.woff2")
    subset("YujiSyuku-Regular.ttf", "".join(c.get("k", "") + c.get("t", "") + c.get("go", "") for c in ja) + "絵巻をひらく", "intro_ja.woff2")
    latin = "".join(chr(i) for i in range(0x20, 0x7F)) + "ŌōĀāŪūĒēĪī’‘“”—–…·"
    subset("CormorantGaramond-Italic.ttf", latin, "intro_en.woff2")


if __name__ == "__main__":
    main()
