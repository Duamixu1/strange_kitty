"""探案版"带你玩一遍"画面粗剪 v0：没有人声，只有实机画面 + 脚本字幕 + 配乐 v2（循环）。
给你对着录口播用，录完再按口播重新对时间。脚本见 promo/脚本_探案版_v1.md。
用法：python cut_v0.py   （在任意目录）
"""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "promo"
A = P / "raw/探案版实录_结局A.mp4"
B = P / "raw/探案版实录_结局B.mp4"
FF = str(Path.home() / "socialmedia/tools/bin/ffmpeg")
FONTDIR = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/4a418d1fa4860652a3241e8ee457806c8557fc64.asset/AssetData"
WORK = P / "raw/_cut_v0"; WORK.mkdir(parents=True, exist_ok=True)
FPS = 30
PAPER = "0xF1E9DA"
INK = "0x191627"   # 游戏宽银幕黑边的颜色
BAR = 138          # 2.39:1 黑边，上下各 138 px

# 每段：(段名, 片段列表, 字幕)。片段 = ("v", 源, 入点, 出点, 速度) 或 ("img", 图, 秒数)
# 时间都是 raw/探案版实录_结局A.mp4 里的秒数（镜头时间点见同名 .markers.json）
SECTIONS = [
    ("开头", [("v", A, 170.0, 175.6, 1.0), ("v", A, 181.2, 185.6, 1.0)],
     ["这是我用 AI 做的一个怪化猫小游戏", "能从头玩到结尾", "今天带你玩一遍"]),
    ("推门", [("v", A, 0.8, 7.6, 1.0), ("img", ROOT / "assets/concept/scenes/06_走廊_360全景.png", 6.0), ("v", A, 110.2, 114.6, 1.0), ("v", A, 12.0, 14.6, 1.0)],
     ["开场你是药郎，站在大奥门口", "推门进去，是这条走廊", "这条走廊不是一块块搭出来的", "我先画了一张全景图，丢给 World Labs", "它直接生成一个能走进去的 3D 房间", "后面三间房和中庭，都是这么来的"]),
    ("规则", [("v", A, 8.9, 12.6, 0.6), ("v", A, 34.6, 40.0, 1.0)],
     ["玩法用的是原作的规矩", "药郎要弄清物怪的形、真和理，才能拔剑", "我把它做成一个天秤", "两件对得上的东西放上去，天秤平了，一个字就亮"]),
    ("形", [("v", A, 15.0, 20.0, 1.0), ("v", A, 22.0, 28.0, 1.5), ("v", A, 29.4, 34.6, 1.0), ("v", A, 41.7, 44.2, 1.0)],
     ["进门左手有一幅画，地上有一截线", "两样一配，形就亮了", "这个天秤还是个指南针", "离线索越近晃得越厉害，不知道去哪跟着它走就行"]),
    ("真", [("v", A, 44.2, 47.4, 1.0), ("v", A, 48.0, 52.0, 1.0), ("v", A, 77.0, 82.0, 1.0), ("v", A, 86.0, 90.0, 1.0),
            ("img", ROOT / "assets/concept/scenes/18_歌山_建模三视图.png", 2.8), ("img", ROOT / "assets/processed/shots/npc_查看器_待机.jpg", 2.8),("v", A, 96.4, 101.0, 1.0)],
     ["右手第一间是女中的房间，阿龟会给你半张家书", "再去对面翻歌山桌上的登记簿，真也亮了", "里面的人都是先画一张设定图", "再丢给 Tripo 生成 3D 模型", "画风是后面用代码套上去的：平涂、描边、和纸的纹理"]),
    ("理", [("v", A, 115.6, 121.0, 1.0), ("v", A, 122.0, 125.0, 1.0), ("v", A, 132.4, 137.0, 1.0), ("v", A, 148.4, 157.0, 1.3)],
     ["最后一个是理", "井里能捞出一只手鞠，尽头那间空房还有两样东西", "最后一下你只能选一个", "选哪个，决定了你看到的结局，一共有两个", "故事是我自己编的，没照搬电影"]),
    ("拔剑", [("v", A, 165.6, 180.6, 1.0), ("img", ROOT / "assets/processed/shots/layer_对比_分层骨链.jpg", 5.0)],
     ["三个字齐了，药郎拔剑", "这套动作没用现成的，是一个姿势一个姿势调的", "做到横斩出了个问题：他的大袖被两条腿扯成了一张膜", "后来把衣服拆成几层，各挂一串骨头", "现在走起来，袖子和头发都会晃"]),
    ("结尾", [("v", A, 36.0, 41.0, 1.0), ("v", B, None, None, 1.0), ("v", A, 181.2, 188.0, 1.0)],
     ["代码基本是 Claude Code 写的", "我开了好几个对话，一个当总指挥，其他的分别管角色、场景、玩法、文案", "我自己干的是做判断：先做哪一步，像不像，积分值不值得花", "最后说一句，这是同人，免费的，不卖东西", "画面里的模型和场景，都是自己生成的"]),
]

def run(args): subprocess.run([FF, "-y", "-loglevel", "error", *args], check=True)

def nframes(path):
    out = subprocess.run([FF, "-i", str(path), "-map", "0:v", "-c", "copy", "-f", "null", "-"], capture_output=True, text=True).stderr
    return int([l for l in out.splitlines() if "frame=" in l][-1].split("frame=")[1].split()[0])

ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]
bm = json.loads((P / "raw/探案版实录_结局B.markers.json").read_text())
parts, sec_spans, t = [], [], 0.0
for si, (name, clips, subs) in enumerate(SECTIONS):
    t0 = t
    for ci, c in enumerate(clips):
        out = WORK / f"{si:02d}_{ci:02d}.mp4"
        if c[0] == "img":
            _, img, dur = c
            # 图片：缩进画面，和纸色底，慢慢推近
            n = int(dur * FPS)
            run(["-loop", "1", "-t", str(dur), "-i", str(img), "-vf",
                 f"scale=1760:{1080 - 2 * BAR - 40}:force_original_aspect_ratio=decrease,pad=1920:{1080 - 2 * BAR}:(ow-iw)/2:(oh-ih)/2:color={PAPER},pad=1920:1080:0:{BAR}:color={INK},"
                 f"scale=3840:2160,zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps={FPS}", *ENC, str(out)])
        else:
            _, src, ss, to, sp = c
            if src == B:   # 结局 B 的结果卡
                ss, to = bm["08_结果卡"] + 0.3, bm["08_结果卡"] + 4.8
            run(["-ss", str(ss), "-to", str(to), "-i", str(src), "-vf", f"setpts=(PTS-STARTPTS)/{sp},fps={FPS}", *ENC, str(out)])
        n = nframes(out); parts.append(out); t += n / FPS
    sec_spans.append((name, t0, t, subs))

(WORK / "parts.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
video = WORK / "video.mp4"
run(["-f", "concat", "-safe", "0", "-i", str(WORK / "parts.txt"), "-c", "copy", str(video)])
total = t

# 字幕：一律单行（两行会压到游戏自己的对话框上），长句在逗号 / 冒号处拆成前后两条
def split(s):
    if len(s) <= 20: return [s]
    cuts = [i for i, ch in enumerate(s) if ch in "，：" and 4 <= i < len(s) - 4]
    if not cuts: return [s]
    i = min(cuts, key=lambda i: abs(i - len(s) / 2))
    return split(s[:i]) + split(s[i + 1:])
# 字幕：每段里按字数分配时间
def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h}:{m:02d}:{s:05.2f}"
ev = []
for name, a, b, subs in sec_spans:
    subs = [x for s in subs for x in split(s)]
    w = [max(len(s), 6) for s in subs]; span = b - a - 0.4; cur = a + 0.2
    for s, k in zip(subs, w):
        d = span * k / sum(w)
        text = s.rstrip("，")
        ev.append(f"Dialogue: 0,{ts(cur)},{ts(cur + d - 0.08)},Sub,,0,0,0,,{text}")
        cur += d
ass = WORK / "subs.ass"
ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Yuanti SC,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,4,0,2,80,80,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

# 配乐：24 秒一段，循环到全长，结尾 3 秒淡出
music = P / "配乐_v2.wav"
loops = int(total // 24) + 1
out = P / "探案版_带你玩一遍_粗剪v0.mp4"
run(["-i", str(video), "-stream_loop", str(loops), "-i", str(music),
     "-filter_complex", f"[0:v]subtitles={ass.as_posix()}:fontsdir={FONTDIR}[v];[1:a]atrim=0:{total:.3f},volume=0.8,afade=t=in:d=0.5,afade=t=out:st={total - 3:.3f}:d=3[a]",
     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
(WORK / "sections.json").write_text(json.dumps([{"段": n, "起": round(a, 2), "止": round(b, 2)} for n, a, b, _ in sec_spans], ensure_ascii=False, indent=1))
print(out, f"{total:.1f}s")
for n, a, b, _ in sec_spans: print(f"  {n}: {a:.1f}–{b:.1f}")
