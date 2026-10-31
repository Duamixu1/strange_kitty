"""探案版"带你玩一遍" v2：开头快剪（同 v1）+ 你的口播（promo/voice/口播_剪辑.wav，由 voice_edit.py 剪好）。
每段画面的长度跟着口播走：段落起止和字幕时间都读 promo/voice/口播_剪辑.json；每段最后一个镜头自动补齐到下一段开头。
配乐：快剪那 21 秒是原曲音量，口播开始前 1 秒压到垫底，结尾淡出。
用法：python cut_v2.py
"""
import json, os, subprocess
from pathlib import Path
from cutlib import *

VO = json.loads((P / "voice/口播_剪辑.json").read_text())
VOICE = P / "voice/口播_剪辑.wav"
SH = ROOT / "assets/processed/shots"; SC = ROOT / "assets/concept/scenes"; ZY = ROOT.parent / "zhiyi-game/assets/concept/scenes"
DOC = P / "raw/过程_分工表.mp4"; GH = P / "raw/过程_github.mp4"
L = lambda **k: k   # 选项字典的简写

# 每段的镜头：("v", 源, 入点, 成片秒数, 速度, 选项) / ("img", 图, 秒数, 选项)。每段最后一个镜头的秒数会被改成"补齐到下一段"。
# 注释里的数字是这句话在段内的秒数（口播_剪辑.json）
VIS = {
    "缘起": [   # 0 喜欢药郎 / 1.3 纹样色彩好看 / 6.8 Tripo 共创计划 / 11.0 用这个模型 / 14.5 搭建药郎的世界
        ("v", YP, 10.0, 1.4, 1.0, L(fit="blurfit")),
        ("v", YP, 12.6, 2.8, 1.0, L(fit="blurfit")),
        ("img", ROOT / "assets/concept/00_色板.png", 1.3, L(fit="letter", z=(1.0, 1.05))),
        ("img", SC / "19_壁画_踢鞠童女.png", 1.4, L(fit="letter", z=(1.0, 1.08))),
        ("img", ROOT / "assets/tripo_raw/kusuriuri_v2_preview.webp", 2.1, L(fit="letter", z=(1.0, 1.08), note=("Tripo", "共创计划"))),
        ("img", SC / "11_药贩子_建模三视图.png", 2.1, L(fit="letter", z=(1.0, 1.05))),
        ("v", A, 110.2, 3.5, 1.0, L()),
        ("v", A, 44.6, 2.4, 1.0, L()),
        ("v", A, 117.2, 2.0, 1.0, L()),
    ],
    "开头": [("v", A, 181.2, 6.0, 1.0, L())],
    "推门": [   # 0 开场 / 2.9 推门 / 4.9 World Labs / 9.2 全景图 / 12.1 高斯泼溅 / 17.1 做好边界 / 18.9 房间和中庭
        ("v", A, 0.8, 4.9, 1.0, L()),
        ("v", A, 5.7, 3.0, 1.0, L(note=("World Labs",))),
        ("v", A, 110.4, 1.3, 1.0, L()),
        ("img", SC / "06_走廊_360全景.png", 2.9, L(fit="pan")),
        ("img", ROOT / "assets/worldlabs/对比_v1_v2_v3.jpg", 2.4, L(fit="letter", z=(1.0, 1.12))),
        ("v", A, 128.4, 2.6, 1.0, L()),
        ("img", ROOT / "assets/worldlabs/walkmap.png", 1.8, L(fit="letter", z=(1.0, 1.06))),
        ("v", A, 44.6, 2.1, 1.0, L()),
        ("v", A, 80.6, 2.0, 1.0, L()),
        ("v", A, 117.2, 2.0, 1.0, L()),
    ],
    "规则": [   # 0 规则 / 4.7 形真理 / 9.0 天秤 / 12.7 一个字亮 / 16.9 集齐
        ("v", A, 8.9, 4.7, 0.8, L()),
        ("v", A, 29.4, 5.2, 1.0, L()),
        ("v", A, 96.4, 4.6, 1.0, L()),
        ("v", B, 165.2, 4.9, 1.0, L()),
    ],
    "形": [   # 0 画和线 / 3.0 形 OK / 6.6 指南针 / 11.9 跟着走 / 14.4 铃铛 / 18.7 WASD / 22.1 自己玩 / 27.2 鼠标点击
        ("v", A, 15.0, 3.0, 1.0, L()),
        ("v", A, 31.0, 3.6, 1.0, L()),
        ("v", A, 36.5, 5.3, 1.0, L()),
        ("v", A, 41.7, 2.5, 1.0, L(crop=(1180, 640, 740, 416))),
        ("v", A, 76.0, 4.3, 1.0, L()),
        ("v", A, 12.0, 2.6, 1.0, L()),
        ("v", A, 110.2, 4.4, 1.0, L()),
        ("v", A, 128.4, 4.0, 1.0, L()),
        ("v", A, 22.0, 2.2, 1.0, L()),
    ],
    "真": [   # 0 女中房 / 2.5 阿龟阿浅 / 5.2 家书 / 7.9 登记簿 / 11.2 真亮 / 14.2 设定图 / 17.8 Tripo / 21.1 A 字型 / 26.0 画风代码 / 29.9 平涂描边和纸
        ("v", A, 44.2, 2.5, 1.0, L()),
        ("img", SH / "npc_对话_asa.jpg", 1.3, L(fit="cover", z=(1.06, 1.0), note=("阿浅",))),
        ("v", A, 48.0, 1.4, 1.0, L(note=("阿龟",))),
        ("v", A, 52.0, 2.7, 1.0, L()),
        ("v", A, 86.0, 3.3, 1.0, L(note=("歌山",))),
        ("v", A, 96.4, 3.0, 1.0, L()),
        ("img", SC / "18_歌山_建模三视图.png", 3.6, L(fit="letter", z=(1.0, 1.05))),
        ("img", ROOT / "assets/tripo_raw/kusuriuri_v2_preview.webp", 3.3, L(fit="letter", z=(1.0, 1.08), note=("Tripo", "设定图变成 3D 模型"))),
        ("img", SC / "16_阿浅_建模三视图.png", 2.5, L(fit="letter", z=(1.0, 1.05), note=("A 字型",))),
        ("img", SH / "npc_查看器_待机.jpg", 2.4, L(fit="letter", z=(1.0, 1.05))),
        ("v", SHADER, 0.3, 3.9, 1.0, L(note=("Three.js", "平涂 · 描边 · 和纸"))),
        ("v", CODE, 0.3, 4.9, 0.6, L()),
    ],
    "理": [   # 0 理 / 1.3 手鞠 / 3.7 空房 / 6.7 只能选一个 / 13.3 自己编的
        ("v", A, 112.0, 1.3, 1.0, L()),
        ("v", A, 122.0, 2.4, 1.0, L()),
        ("v", A, 132.4, 3.0, 1.0, L()),
        ("v", A, 148.4, 6.6, 1.3, L()),
        ("img", SC / "07_手鞠_本体.png", 2.3, L(fit="letter", z=(1.0, 1.06), note=("物怪·手鞠", "原创"))),
    ],
    "拔剑": [   # 0 拔剑 / 2.3 没用现成的 / 6.9 横斩出问题 / 9.0 扯成膜 / 11.9 头发 / 13.1 拆成几层 / 17.3 都会晃 / 19.8 脚好笑 / 22.2 折叠术
        ("v", A, 165.6, 2.3, 1.0, L()),
        ("v", YP, 3.0, 4.6, 1.0, L(fit="blurfit")),
        ("img", SH / "layer_01_横斩_关.jpg", 2.5, L(fit="letter", z=(1.0, 1.08))),
        ("img", SH / "layer_02_横斩_开.jpg", 2.5, L(fit="letter", z=(1.0, 1.08))),
        ("img", SH / "layer_12_横斩_侧面_开_逐节.jpg", 2.7, L(fit="cover", z=(1.0, 1.08), note=("衣服拆层", "挂上骨链自己摆"))),
        ("img", SH / "hairtest2_斜侧_1.jpg", 2.7, L(fit="letter", z=(1.0, 1.06))),
        ("v", YP, 11.5, 2.5, 1.0, L(fit="blurfit")),
        ("img", SH / "foot_横斩_侧面.jpg", 3.3, L(fit="letter", z=(1.0, 1.15))),
        ("img", SH / "foot_走路_侧面.jpg", 3.3, L(fit="letter", z=(1.0, 1.1))),
    ],
    "分工": [   # 0 命名总管 / 4.4 Claude Code / 8.7 总指挥 / 10.9 角色场景 / 13.2 彼此配合 / 16.9 Opus / 19.2 其他方面
        ("v", YP, 1.2, 4.4, 0.3, L(fit="blurfit")),
        ("v", DOC, 0.3, 8.8, 0.65, L(note=("Claude Code", "一条线一个对话"))),
        ("v", CODE, 0.3, 6.0, 0.6, L()),
        ("v", YP, 1.5, 4.0, 0.25, L(fit="blurfit")),
    ],
    "感想": [   # 0 电影 / 6.3 画风变化 / 9.8 极繁主义 / 13.5 给我妈看 / 17.5 唐朝角色 / 20.9 聊斋志异 / 26.2 角色人物 / 28.0 创作
        ("img", SC / "02_走廊全景.png", 3.2, L(fit="letter", z=(1.0, 1.06))),
        ("img", SC / "13_女中房_360全景.png", 3.2, L(fit="pan")),
        ("img", SC / "16_中庭_360全景.png", 3.4, L(fit="pan")),
        ("v", YP, 15.5, 2.0, 1.0, L(fit="blurfit")),
        ("v", A, 6.4, 1.7, 1.0, L()),
        ("img", ZY / "13_书生三视图.png", 4.0, L(fit="letter", z=(1.0, 1.05))),
        ("img", ZY / "18_天女_三视图.png", 3.4, L(fit="letter", z=(1.0, 1.05))),
        ("img", ZY / "14_寺院回廊全景.png", 3.6, L(fit="letter", z=(1.0, 1.08), note=("下一期", "聊斋志异"))),
        ("img", ZY / "32_画中殿.png", 3.4, L(fit="letter", z=(1.0, 1.06))),
        ("img", ZY / "16_孟龙潭_三视图.png", 3.0, L(fit="letter", z=(1.0, 1.05))),
    ],
    "结尾": [   # 0 万屋 / 5.6 整个场景 / 8.2 开源 / 11.1 GitHub / 14.1 感谢药郎 / 19.6 希望大家喜欢
        ("img", SH / "kitview_wanya_soto_1_正面.jpg", 1.9, L(fit="cover", z=(1.0, 1.06), note=("万屋", "TV 版 · 座敷童子"))),
        ("img", SH / "tour_wanya_niwa_拱桥.jpg", 1.9, L(fit="cover", z=(1.0, 1.06))),
        ("img", SH / "tour_wanya_ozashiki_正面看高台.jpg", 1.8, L(fit="cover", z=(1.0, 1.06))),
        ("img", SH / "kitview_map_diorama_0_长卷.jpg", 2.6, L(fit="pan")),
        ("v", GH, 0.3, 5.9, 1.0, L(note=("GitHub", "开源"))),
        ("v", YP, 9.6, 3.0, 1.0, L(fit="blurfit")),
        ("v", YP, 19.0, 2.5, 1.0, L(fit="blurfit")),
        ("v", A, 181.2, 4.5, 1.0, L(fadeout=1.2)),
    ],
}
TAIL = 1.6   # 最后一句说完后再停一会儿，淡出

def cached(c, out, t_at):
    """REUSE=1 时，已经渲染过的片段直接用（按帧数算长度），只改了后面几段时省时间"""
    if os.environ.get("REUSE") == "1" and out.exists():
        r = subprocess.run([FF, "-i", str(out), "-map", "0:v", "-c", "copy", "-f", "null", "-"], capture_output=True, text=True).stderr
        return int([l for l in r.splitlines() if "frame=" in l][-1].split("frame=")[1].split()[0])
    return render(c, out, t_at)

MLEN = 21.0  # 快剪长度（cutlib.MONTAGE 的总长）
def main():
    parts, t = [], 0.0
    for ci, c in enumerate(MONTAGE):
        out = WORK / f"m_{ci:02d}.mp4"; n = cached(c, out, t); parts.append(out); t += n / FPS
    assert abs(t - MLEN) < 0.05, t
    import wave
    with wave.open(str(VOICE)) as w: voice_len = w.getnframes() / w.getframerate()
    for i, sec in enumerate(VO):
        start = sec["start"]; end = VO[i + 1]["start"] if i + 1 < len(VO) else voice_len + TAIL
        target = end - start; clips = VIS[sec["name"]]; got = 0.0
        for ci, c in enumerate(clips):
            c = list(c)
            if ci == len(clips) - 1:   # 最后一个镜头补齐
                rest = target - got
                assert rest > 0.4, (sec["name"], rest)
                c[3 if c[0] != "img" else 2] = round(rest, 3)
            out = WORK / f"s{i:02d}_{ci:02d}.mp4"; n = cached(tuple(c), out, MLEN + start + got); parts.append(out); got += n / FPS
        print(f"  {sec['name']}: 口播 {target:.2f}s，画面 {got:.2f}s", flush=True)
    (WORK / "parts_v2.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    video = WORK / "video_v2.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(WORK / "parts_v2.txt"), "-c", "copy", str(video)])
    total = MLEN + voice_len + TAIL

    def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h}:{m:02d}:{s:05.2f}"
    ev = []
    allsubs = [(MLEN + x, txt) for sec in VO for x, txt in sec["subs"]]
    ends = {MLEN + sec["subs"][-1][0]: MLEN + sec["end"] + 0.25 for sec in VO}
    for k, (x, txt) in enumerate(allsubs):
        e = ends.get(x, allsubs[k + 1][0] - 0.06 if k + 1 < len(allsubs) else MLEN + voice_len)
        e = min(e, allsubs[k + 1][0] - 0.06) if k + 1 < len(allsubs) else e
        ev.append(f"Dialogue: 0,{ts(x)},{ts(e)},Sub,,0,0,0,,{txt}")
    ass = WORK / "subs_v2.ass"
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

    music = P / "配乐_v2.wav"; out = P / "探案版_带你玩一遍_v2.mp4"
    duck = f"volume='if(lt(t,{MLEN - 0.8}),0.8,if(lt(t,{MLEN + 0.4}),0.8-0.66*(t-{MLEN - 0.8})/1.2,0.14))':eval=frame"
    mix = WORK / "audio_v2.wav"
    run(["-i", str(music), "-i", str(VOICE), "-filter_complex",
         f"[0:a]asplit[m1][m2];[m1]atrim=0:19,asetpts=PTS-STARTPTS[a0];[m2]atrim=11.5:19,asetpts=PTS-STARTPTS,aloop=loop=-1:size=330750[a1];"
         f"[a0][a1]concat=n=2:v=0:a=1,atrim=0:{total:.3f},{duck},afade=t=out:st={total - 2.5:.3f}:d=2.5[mu];"
         f"[1:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int(MLEN * 1000)}|{int(MLEN * 1000)},apad=whole_dur={total:.3f}[vo];"
         f"[mu][vo]amix=inputs=2:normalize=0:duration=shortest,alimiter=limit=0.95[a]",
         "-map", "[a]", "-ar", "44100", str(mix)])
    run(["-i", str(video), "-i", str(mix), "-vf", f"subtitles={ass.as_posix()}:fontsdir={FONTDIR}",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", str(out)])
    print(out, f"{total:.1f}s")

main()
