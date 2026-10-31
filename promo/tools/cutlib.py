"""剪辑公共部分：路径、字卡、片名、片段渲染 render()、开头快剪 MONTAGE。cut_v1.py（无人声）和 cut_v2.py（配口播）共用。"""
import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "promo"
A = P / "raw/探案版实录_结局A.mp4"
B = P / "raw/探案版实录_结局B.mp4"
YP = P / "药郎角色样片_v2.mp4"                  # 竖版 1206×1608，配乐同一首，拍点对得上
SHADER = P / "raw/过程_shader.mp4"; CODE = P / "raw/过程_code.mp4"
SH = ROOT / "assets/processed/shots"; SC = ROOT / "assets/concept/scenes"
FF = str(Path.home() / "socialmedia/tools/bin/ffmpeg")
FONTDIR = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData"
YUANTI = FONTDIR + "/Yuanti.ttc"
SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"   # 明朝体缺简体字（药、给、戏会变方块）
WORK = P / "raw/_cut_work"; WORK.mkdir(parents=True, exist_ok=True)
FPS = 30
PAPER, INK, BAR = "0xF1E9DA", "0x191627", 138

# ---------- 便签 / 片名图 ----------
import sys; sys.path.insert(0, str(Path(__file__).parent))
from label_styles import label   # 标签样式（2026-10-30 用户选了 A 竖排字卡；对比图 promo/raw/标签方案对比.jpg）
LABEL_STYLE = "A"

def note_png(title, line=None):
    f = WORK / f"label{LABEL_STYLE}_{title}_{line or ''}.png".replace("/", "_").replace(" ", "")
    if not f.exists(): label(LABEL_STYLE, title, line).save(f)
    return f

def title_png():
    """片名卡：只有一行大标题（2026-10-30 用户要求去掉下面那行红色小字）"""
    f = WORK / "title.png"
    im = Image.new("RGBA", (1920, 1080), (25, 22, 39, 110)); d = ImageDraw.Draw(im)
    big = ImageFont.truetype(SONGTI, 112, index=1)
    t1 = "一个为药郎而存在的空间"
    x0, y0, x1, y1 = big.getbbox(t1); w1, h1 = x1 - x0, y1 - y0
    top, bottom = 430, 650
    d.rectangle((960 - w1 / 2 - 70, top, 960 + w1 / 2 + 70, bottom), fill=(241, 233, 218, 240), outline=(50, 45, 72, 255), width=5)
    d.text((960 - w1 / 2 - x0, (top + bottom) / 2 - h1 / 2 - y0), t1, font=big, fill=(50, 45, 72))
    im.save(f); return f

# ---------- 片段 ----------
# ("v", 源, 入点, 成片秒数, 速度, 选项) / ("img", 图, 秒数, 选项)
# 选项：fit = full（16:9 原样）| blurfit（竖版：两侧流动纹样）| cover（铺满）| letter（宽银幕黑边 + 纸色底）| pan（横向扫过）
#       z = (起, 止) 推拉；note = (标题, 小字)；over = 叠一张全屏 PNG
MONTAGE = [
    # 人物
    ("img", SH / "npc_对话_asa.jpg", 0.5, dict(fit="cover", z=(1.08, 1.0), note=("阿浅",))),
    ("img", SH / "npc_对话_kame.jpg", 0.5, dict(fit="cover", z=(1.0, 1.06), note=("阿龟",))),       # 用对话近景截图：游戏画面放大后对话框会压到字幕
    ("img", SH / "npc_对话_utayama.jpg", 0.5, dict(fit="cover", z=(1.0, 1.06), note=("歌山",))),
    ("img", SH / "cut_02_散线.jpg", 0.5, dict(fit="cover", z=(1.0, 1.1), note=("物怪·手鞠",))),
    # 场景
    ("v", A, 6.4, 0.5, 1.0, dict(note=("大奥·长廊",))),
    ("v", A, 44.6, 0.5, 1.0, dict(note=("女中的房间",))),
    # 药郎：拔剑 → 脸 + 剑 → 举剑 → 横斩 → 收剑（直接用样片同一段，拍点一致）
    ("v", YP, 3.0, 1.5, 1.0, dict(fit="blurfit", note=("药郎",))),
    ("v", YP, 4.5, 0.5, 1.0, dict(fit="blurfit")),
    ("v", YP, 5.0, 1.0, 1.0, dict(fit="blurfit")),
    ("v", YP, 6.0, 2.5, 1.0, dict(fit="blurfit")),
    ("v", A, 117.2, 0.5, 1.0, dict(note=("中庭",))),
    ("v", A, 134.6, 0.5, 1.0, dict(note=("阿雪的空房",))),
    # 片名
    ("v", A, 128.4, 2.0, 1.0, dict(z=(1.0, 1.06), over="title")),
    # 工具和过程
    ("img", SC / "11_药贩子_建模三视图.png", 1.0, dict(fit="letter", z=(1.0, 1.05), note=("先画设定图", "正面 · 侧面 · 背面"))),
    ("img", ROOT / "assets/tripo_raw/kusuriuri_v2_preview.webp", 1.0, dict(fit="letter", z=(1.0, 1.08), note=("Tripo", "设定图变成 3D 模型"))),
    ("img", SC / "06_走廊_360全景.png", 1.0, dict(fit="pan", note=("360 全景图", "一张图画满四周"))),
    ("v", A, 80.6, 1.0, 1.0, dict(z=(1.0, 1.06), note=("World Labs", "全景图变成能走的房间"))),
    ("img", SH / "k2_对比_第二批动作.jpg", 1.0, dict(fit="pan", note=("Blender", "一个姿势一个姿势调"))),
    ("img", SH / "layer_12_横斩_侧面_开_逐节.jpg", 1.0, dict(fit="cover", z=(1.0, 1.08), note=("衣服拆层", "挂上骨链自己摆"))),
    ("v", SHADER, 0.3, 1.5, 2.3, dict(note=("Three.js", "平涂 · 描边 · 和纸"))),
    ("v", CODE, 0.3, 1.0, 1.6, dict(note=("Claude Code", "代码都是它写的"))),
    ("v", YP, 1.5, 1.0, 1.0, dict(fit="blurfit", note=("Claude Code", "开好几个对话分工"))),
]

def run(args): subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]
bm = json.loads((P / "raw/探案版实录_结局B.markers.json").read_text())

def zoom(z, n):
    z0, z1 = z
    return (f"scale=3840:2160,zoompan=z='{z0}+({z1}-{z0})*on/{max(n - 1, 1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps={FPS}")

def render(c, out, t_at=0.0):
    kind = c[0]
    if kind == "img": _, src, dur, o = c; ss = None; sp = 1.0
    else:
        _, src, ss, dur, sp, o = c
        if kind == "vB": src, ss = B, bm["08_结果卡"] + 0.3
    n = round(dur * FPS)
    fit = o.get("fit", "full"); inputs = []
    if kind == "img": inputs = ["-loop", "1", "-framerate", str(FPS), "-i", str(src)]; pre = ""
    else: inputs = ["-ss", str(ss), "-i", str(src)]; pre = f"setpts=(PTS-STARTPTS)/{sp},fps={FPS},tpad=stop_mode=clone:stop_duration={dur:.2f},"   # 素材不够长就停在最后一帧，保证镜头时长准
    if "crop" in o: cx, cy, cw, ch = o["crop"]; pre += f"crop={cw}:{ch}:{cx}:{cy},"
    k = 1
    if fit == "blurfit":   # 竖版：两侧是流动纹样（pattern_bg.py），按它在成片里的时间生成，连着的镜头纹样接着滚
        bg = WORK / f"bg_{t_at:.2f}_{dur:.2f}.mp4"
        if not bg.exists(): subprocess.run([str(Path.home() / "socialmedia/tools/.venv/bin/python"), str(Path(__file__).with_name("pattern_bg.py")), str(bg), str(dur), str(t_at)], check=True, capture_output=True)
        inputs += ["-i", str(bg)]; k = 2
        g = f"[0:v]{pre}scale=-2:1080[fg];[1:v][fg]overlay=(W-w)/2:0"
    elif fit == "cover": g = f"[0:v]{pre}scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
    elif fit == "letter":
        g = (f"[0:v]{pre}scale=1760:{1080 - 2 * BAR - 40}:force_original_aspect_ratio=decrease,pad=1920:{1080 - 2 * BAR}:(ow-iw)/2:(oh-ih)/2:color={PAPER},"
             f"pad=1920:1080:0:{BAR}:color={INK}")
    elif fit == "pan":   # 宽图：缩到宽银幕高度，横向从左扫到右
        g = (f"[0:v]{pre}scale=w='max(2600,iw*{1080 - 2 * BAR}/ih)':h=-2,crop=1920:{1080 - 2 * BAR}:x='(iw-1920)*0.15+(iw-1920)*0.7*n/{n}':y='(ih-{1080 - 2 * BAR})/2',pad=1920:1080:0:{BAR}:color={INK}")
    else: g = f"[0:v]{pre}null"
    if "z" in o: g += "," + zoom(o["z"], n)
    if "fadeout" in o: g += f",fade=t=out:st={dur - o['fadeout']:.3f}:d={o['fadeout']}"
    g += "[v0]"; last = "v0"
    for png in ([title_png()] if o.get("over") == "title" else []) + ([note_png(*o["note"])] if "note" in o else []):
        inputs += ["-i", str(png)]; g += f";[{last}][{k}:v]overlay=0:0[v{k}]"; last = f"v{k}"; k += 1
    run([*inputs, "-filter_complex", g, "-map", f"[{last}]", "-frames:v", str(n), *ENC, str(out)])
    return n

