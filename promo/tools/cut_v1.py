"""探案版"带你玩一遍"粗剪 v1：开头加约 21 秒快剪（人物 → 场景 → 药郎拔剑横斩 → 片名 → 工具和过程），切点卡配乐 v2 的拍子（120 BPM，一拍 0.5 秒）。
后面接 v0 的八段（开头那段改成只用结果卡，拔剑已经在快剪里）。没有人声。
用法：python cut_v1.py
"""
import json, subprocess
from pathlib import Path
from cutlib import *

SECTIONS = [
    ("快剪", MONTAGE, []),
    ("开头", [("v", A, 181.2, 4.8, 1.0, {})],
     ["这是我用 AI 做的一个怪化猫小游戏", "能从头玩到结尾", "今天带你玩一遍"]),
    ("推门", [("v", A, 0.8, 6.8, 1.0, {}), ("img", SC / "06_走廊_360全景.png", 6.0, dict(fit="letter", z=(1.0, 1.06))), ("v", A, 110.2, 4.4, 1.0, {}), ("v", A, 12.0, 2.6, 1.0, {})],
     ["开场你是药郎，站在大奥门口", "推门进去，是这条走廊", "这条走廊不是一块块搭出来的", "我先画了一张全景图，丢给 World Labs", "它直接生成一个能走进去的 3D 房间", "后面三间房和中庭，都是这么来的"]),
    ("规则", [("v", A, 8.9, 6.2, 0.6, {}), ("v", A, 34.6, 5.4, 1.0, {})],
     ["玩法用的是原作的规矩", "药郎要弄清物怪的形、真和理，才能拔剑", "我把它做成一个天秤", "两件对得上的东西放上去，天秤平了，一个字就亮"]),
    ("形", [("v", A, 15.0, 5.0, 1.0, {}), ("v", A, 22.0, 4.0, 1.5, {}), ("v", A, 29.4, 5.2, 1.0, {}), ("v", A, 41.7, 2.5, 1.0, {})],
     ["进门左手有一幅画，地上有一截线", "两样一配，形就亮了", "这个天秤还是个指南针", "离线索越近晃得越厉害，不知道去哪跟着它走就行"]),
    ("真", [("v", A, 44.2, 3.2, 1.0, {}), ("v", A, 48.0, 4.0, 1.0, {}), ("v", A, 77.0, 5.0, 1.0, {}), ("v", A, 86.0, 4.0, 1.0, {}),
            ("img", SC / "18_歌山_建模三视图.png", 2.8, dict(fit="letter", z=(1.0, 1.05))), ("img", SH / "npc_查看器_待机.jpg", 2.8, dict(fit="letter", z=(1.0, 1.05))), ("v", A, 96.4, 4.6, 1.0, {})],
     ["右手第一间是女中的房间，阿龟会给你半张家书", "再去对面翻歌山桌上的登记簿，真也亮了", "里面的人都是先画一张设定图", "再丢给 Tripo 生成 3D 模型", "画风是后面用代码套上去的：平涂、描边、和纸的纹理"]),
    ("理", [("v", A, 115.6, 5.4, 1.0, {}), ("v", A, 122.0, 3.0, 1.0, {}), ("v", A, 132.4, 4.6, 1.0, {}), ("v", A, 148.4, 6.6, 1.3, {})],
     ["最后一个是理", "井里能捞出一只手鞠，尽头那间空房还有两样东西", "最后一下你只能选一个", "选哪个，决定了你看到的结局，一共有两个", "故事是我自己编的，没照搬电影"]),
    ("拔剑", [("v", A, 165.6, 15.0, 1.0, {}), ("img", SH / "layer_对比_分层骨链.jpg", 5.0, dict(fit="letter", z=(1.0, 1.05)))],
     ["三个字齐了，药郎拔剑", "这套动作没用现成的，是一个姿势一个姿势调的", "做到横斩出了个问题：他的大袖被两条腿扯成了一张膜", "后来把衣服拆成几层，各挂一串骨头", "现在走起来，袖子和头发都会晃"]),
    ("结尾", [("v", A, 36.0, 5.0, 1.0, {}), ("vB", None, 0, 4.5, 1.0, {}), ("v", A, 181.2, 6.8, 1.0, {})],
     ["代码基本是 Claude Code 写的", "我开了好几个对话，一个当总指挥，其他的分别管角色、场景、玩法、文案", "我自己干的是做判断：先做哪一步，像不像，积分值不值得花", "最后说一句，这是同人，免费的，不卖东西", "画面里的模型和场景，都是自己生成的"]),
]

parts, spans, t = [], [], 0.0
for si, (name, clips, subs) in enumerate(SECTIONS):
    t0 = t
    for ci, c in enumerate(clips):
        out = WORK / f"{si:02d}_{ci:02d}.mp4"
        n = render(c, out, t); parts.append(out); t += n / FPS
    spans.append((name, t0, t, subs))
    print(f"  {name}: {t0:.2f}–{t:.2f}", flush=True)
(WORK / "parts.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
video = WORK / "video.mp4"
run(["-f", "concat", "-safe", "0", "-i", str(WORK / "parts.txt"), "-c", "copy", str(video)])
total = t

def split(s):
    if len(s) <= 20: return [s]
    cuts = [i for i, ch in enumerate(s) if ch in "，：" and 4 <= i < len(s) - 4]
    if not cuts: return [s]
    i = min(cuts, key=lambda i: abs(i - len(s) / 2))
    return split(s[:i]) + split(s[i + 1:])
def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h}:{m:02d}:{s:05.2f}"
ev = []
for name, a, b, subs in spans:
    subs = [x for s in subs for x in split(s)]
    if not subs: continue
    w = [max(len(s), 6) for s in subs]; span = b - a - 0.4; cur = a + 0.2
    for s, k in zip(subs, w):
        d = span * k / sum(w); ev.append(f"Dialogue: 0,{ts(cur)},{ts(cur + d - 0.08)},Sub,,0,0,0,,{s.rstrip('，')}"); cur += d
ass = WORK / "subs.ass"
ass.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Yuanti SC,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,4,0,2,80,80,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

# 配乐：前 19 秒原样（快剪就是按它的拍点切的），之后循环 11.5–19 秒那段（7.5 秒 = 15 拍），结尾 3 秒淡出
music = P / "配乐_v2.wav"; out = P / "探案版_带你玩一遍_粗剪v1.mp4"
run(["-i", str(video), "-i", str(music), "-filter_complex",
     f"[0:v]subtitles={ass.as_posix()}:fontsdir={FONTDIR}[v];"
     f"[1:a]asplit[m1][m2];[m1]atrim=0:19,asetpts=PTS-STARTPTS[a0];[m2]atrim=11.5:19,asetpts=PTS-STARTPTS,aloop=loop=-1:size=330750[a1];"
     f"[a0][a1]concat=n=2:v=0:a=1,atrim=0:{total:.3f},volume=0.8,afade=t=out:st={total - 3:.3f}:d=3[a]",
     "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", str(out)])
print(out, f"{total:.1f}s")
