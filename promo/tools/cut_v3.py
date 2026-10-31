"""探案版"带你玩一遍" v3：开头快剪 + 按口播稿 v3 重录的口播（promo/voice/口播v3_剪辑.wav，voice_edit.py v3 剪好）。
每段画面的长度跟着口播走：段落起止和字幕时间读 promo/voice/口播v3_剪辑.json；每段里的镜头按比例拉长或缩短到这段口播的长度。
镜头时长是按这一版口播里每句话的位置排的（注释里是句子在段内的秒数）。
配乐：快剪那 21 秒是原曲音量，口播开始前 1 秒压到垫底，结尾淡出。
用法：python cut_v3.py（REUSE=1 复用已渲染的片段）
      OVER=1 python cut_v3.py   口播从第 0 秒开始、盖在快剪上（缘起那段直接用快剪的画面），输出 _v4.mp4
"""
import json, os, subprocess
from pathlib import Path
from cutlib import *

VO = json.loads((P / "voice/口播v3_剪辑.json").read_text())
VOICE = P / "voice/口播v3_剪辑.wav"
SH = ROOT / "assets/processed/shots"; SC = ROOT / "assets/concept/scenes"; ZY = ROOT.parent / "zhiyi-game/assets/concept/scenes"
DOC = P / "raw/过程_分工表.mp4"; GH = P / "raw/过程_github.mp4"
L = lambda **k: k   # 选项字典的简写

# 每段的镜头：("v", 源, 入点, 成片秒数, 速度, 选项) / ("img", 图, 秒数, 选项)。每段最后一个镜头的秒数会被改成"补齐到下一段"。
# 注释里的数字是这句话在段内的秒数（口播_剪辑.json）
VIS = {
    "缘起": [   # 0 二创 / 4.5 纹样配色 / 8.5 Tripo 共创计划 / 12.2 World Labs、Blender、Tripo / 16.4 药郎的世界
        ("v", YP, 10.0, 1.6, 1.0, L(fit="blurfit")),
        ("v", YP, 12.6, 2.9, 1.0, L(fit="blurfit")),
        ("img", ROOT / "assets/concept/00_色板.png", 1.9, L(fit="letter", z=(1.0, 1.05))),
        ("img", SC / "19_壁画_踢鞠童女.png", 2.1, L(fit="letter", z=(1.0, 1.08))),
        ("img", ROOT / "assets/tripo_raw/kusuriuri_v2_preview.webp", 2.0, L(fit="letter", z=(1.0, 1.08), note=("Tripo", "共创计划"))),
        ("img", SC / "11_药贩子_建模三视图.png", 1.7, L(fit="letter", z=(1.0, 1.05))),
        ("v", A, 110.2, 2.4, 1.0, L()),
        ("v", A, 44.6, 1.9, 1.0, L()),
        ("v", A, 117.2, 1.9, 1.0, L()),
    ],
    "开头": [("v", A, 181.2, 6.0, 1.0, L())],
    "推门": [   # 0 唐伞的大奥 / 3.4 江户将军后宫 / 5.8 推门 / 8.0 World Labs / 10.7 全景图 / 14.0 泼溅空间 / 17.4 没有碰撞 / 19.4 点云边界 / 23.6 往里放东西 / 25.9 另外做的模型 / 28.0 飘在空中 / 29.6 描边透墙
        ("v", A, 0.8, 5.8, 1.0, L()),
        ("v", A, 5.7, 2.2, 1.0, L()),
        ("v", A, 110.4, 2.7, 1.0, L(note=("World Labs",))),
        ("img", SC / "06_走廊_360全景.png", 3.3, L(fit="pan")),
        ("img", ROOT / "assets/worldlabs/对比_v1_v2_v3.jpg", 3.4, L(fit="letter", z=(1.0, 1.12))),
        ("img", ROOT / "assets/worldlabs/walkmap.png", 3.0, L(fit="letter", z=(1.0, 1.06), note=("可走范围", "从点云里算出来"))),
        ("v", A, 128.4, 3.2, 1.0, L()),
        ("v", A, 44.6, 2.3, 1.0, L()),
        ("img", SH / "npc_查看器_待机.jpg", 2.1, L(fit="letter", z=(1.0, 1.05))),
        ("v", A, 80.6, 1.6, 1.0, L()),
        ("v", A, 117.2, 3.8, 1.0, L()),
    ],
    "规则": [   # 0 锈湖 / 3.0 空间不大 / 7.6 沿用原作 / 9.2 形真理 / 14.2 天秤 / 15.6 两件 / 18.1 平了亮字
        ("v", A, 128.4, 3.0, 1.0, L(note=("灵感", "锈湖"))),
        ("v", A, 132.4, 4.6, 1.0, L()),
        ("v", A, 8.9, 6.6, 0.6, L()),
        ("v", A, 29.4, 5.2, 1.0, L()),
        ("v", B, 165.2, 2.3, 1.0, L()),
    ],
    "形": [   # 0 一幅画 / 2.2 踢手鞠 / 4.5 彩线 / 7.0 形亮 / 8.8 指南针 / 12.6 越近越晃 / 14.9 响铃 / 18.6 出提示 / 21.0 操作改过 / 23.2 WASD / 25.2 试玩晕 / 29.4 鼠标点哪走哪 / 33.4 视角可以变化
        ("v", A, 15.0, 4.5, 1.0, L()),
        ("v", A, 22.0, 2.5, 1.0, L()),
        ("v", A, 31.0, 1.8, 1.0, L()),
        ("v", A, 36.5, 3.8, 1.0, L()),
        ("v", A, 41.7, 2.3, 1.0, L(crop=(1180, 640, 740, 416))),
        ("v", A, 76.0, 3.7, 1.0, L()),
        ("v", A, 128.4, 2.4, 1.0, L()),
        ("v", A, 110.2, 2.2, 1.0, L()),
        ("v", A, 12.0, 2.0, 1.0, L()),
        ("v", A, 112.0, 4.2, 1.0, L()),
        ("v", A, 77.0, 4.0, 1.0, L()),
        ("v", A, 6.4, 3.8, 1.0, L()),
    ],
    "真": [   # 0 女中房 / 3.0 阿龟家书 / 5.6 歌山登记簿 / 8.5 真亮 / 10.0 两样一对 / 12.3 阿雪 / 14.9 手鞠被没收 / 18.7 还原度 / 21.4 认得出又不描 / 26.2 色板设定图 / 30.0 A pose 交给 Tripo / 33.0 平涂描边和纸 / 35.8 代码
        ("v", A, 44.2, 3.0, 1.0, L()),
        ("v", A, 48.0, 2.6, 1.0, L(note=("阿龟",))),
        ("v", A, 86.0, 2.9, 1.0, L(note=("歌山",))),
        ("v", A, 96.4, 1.5, 1.0, L()),
        ("img", SC / "12_证物图标.png", 4.6, L(fit="letter", z=(1.0, 1.06), note=("阿雪的故事",))),
        ("img", SC / "08_手鞠_散线.png", 4.1, L(fit="letter", z=(1.0, 1.08))),
        ("img", SH / "npc_对话_asa.jpg", 2.7, L(fit="cover", z=(1.06, 1.0), note=("阿浅",))),
        ("img", SC / "18_歌山_建模三视图.png", 4.8, L(fit="letter", z=(1.0, 1.05))),
        ("img", SC / "16_阿浅_建模三视图.png", 3.8, L(fit="letter", z=(1.0, 1.05), note=("A pose",))),
        ("img", ROOT / "assets/tripo_raw/kusuriuri_v2_preview.webp", 3.0, L(fit="letter", z=(1.0, 1.08), note=("Tripo",))),
        ("v", SHADER, 0.3, 2.8, 1.2, L(note=("Three.js", "平涂 · 描边 · 和纸"))),
        ("v", CODE, 0.3, 2.9, 0.6, L()),
    ],
    "理": [   # 0 理 / 1.6 井里手鞠 / 4.4 江户时代常见 / 6.8 和服剩下的丝线 / 11.0 尽头空房 / 13.0 木线轴和家信 / 15.9 选一样 / 17.6 结局
        ("v", A, 112.0, 1.6, 1.0, L()),
        ("v", A, 122.0, 2.8, 1.0, L()),
        ("img", SC / "07_手鞠_本体.png", 6.6, L(fit="letter", z=(1.0, 1.1), note=("手鞠", "江户时代"))),
        ("v", A, 132.4, 2.0, 1.0, L()),
        ("v", A, 138.0, 2.9, 1.0, L()),
        ("v", A, 148.4, 5.2, 1.3, L()),
    ],
    "拔剑": [   # 0 拔剑 / 2.4 不是现成的 / 4.6 一个姿势一个姿势 / 7.4 横斩出问题 / 9.7 扯成膜 / 13.0 拆成几层 / 17.4 挂骨头 / 21.1 脚出事 / 23.4 折叠起来
        ("v", A, 165.6, 2.4, 1.0, L()),
        ("v", YP, 3.0, 5.0, 1.0, L(fit="blurfit")),
        ("img", SH / "layer_01_横斩_关.jpg", 2.3, L(fit="letter", z=(1.0, 1.08))),
        ("img", SH / "layer_02_横斩_开.jpg", 3.3, L(fit="letter", z=(1.0, 1.08))),
        ("img", SH / "hairtest2_斜侧_1.jpg", 2.4, L(fit="letter", z=(1.0, 1.06))),
        ("img", SH / "layer_12_横斩_侧面_开_逐节.jpg", 2.6, L(fit="cover", z=(1.0, 1.08), note=("衣服拆层", "挂上骨链自己摆"))),
        ("v", YP, 11.5, 3.1, 1.0, L(fit="blurfit")),
        ("img", SH / "foot_横斩_侧面.jpg", 2.3, L(fit="letter", z=(1.0, 1.15))),
        ("img", SH / "foot_走路_侧面.jpg", 2.1, L(fit="letter", z=(1.0, 1.1))),
    ],
    "分工": [   # 0 CC 写的 / 2.3 好几个对话 / 5.6 角色场景 / 9.0 不会有冲突 / 12.6 待办表 / 14.1 做判断 / 18.4 Opus
        ("v", YP, 1.2, 2.3, 0.3, L(fit="blurfit", note=("Claude Code",))),
        ("v", DOC, 0.3, 10.3, 0.65, L(note=("一条线", "一个对话"))),
        ("v", CODE, 0.3, 4.3, 0.6, L()),
        ("v", YP, 1.5, 4.1, 0.25, L(fit="blurfit")),
    ],
    "感想": [   # 0 说回电影 / 1.4 画风差别 / 5.3 极繁主义 / 8.5 我妈：唐宋角色 / 13.4 下一期，先跑的图 / 17.0 聊斋志异 / 19.6 有意思的人物 / 22.1 给建议
        ("img", SC / "02_走廊全景.png", 3.0, L(fit="letter", z=(1.0, 1.06))),
        ("img", SC / "13_女中房_360全景.png", 2.5, L(fit="pan")),
        ("v", YP, 15.5, 1.6, 1.0, L(fit="blurfit")),
        ("v", A, 6.4, 1.4, 1.0, L()),
        ("img", ZY / "13_书生三视图.png", 4.9, L(fit="letter", z=(1.0, 1.05))),
        ("img", ZY / "18_天女_三视图.png", 3.6, L(fit="letter", z=(1.0, 1.05))),
        ("img", ZY / "14_寺院回廊全景.png", 2.8, L(fit="letter", z=(1.0, 1.08), note=("下一期", "聊斋志异"))),
        ("img", ZY / "32_画中殿.png", 2.6, L(fit="letter", z=(1.0, 1.06))),
        ("img", ZY / "16_孟龙潭_三视图.png", 2.2, L(fit="letter", z=(1.0, 1.05))),
    ],
    "结尾": [   # 0 万屋 / 3.4 积木来搭 / 6.0 泼溅好看但糊 / 9.8 没法随便走 / 11.7 积木能走的多 / 15.4 开源，网站 / 19.5 大家也可以玩 / 20.4 GitHub 部署的网站 / 26.0 感谢药郎 / 28.0 希望你们喜欢
        ("img", SH / "kitview_wanya_soto_1_正面.jpg", 1.9, L(fit="cover", z=(1.0, 1.06), note=("万屋", "TV 版 · 座敷童子"))),
        ("img", SH / "tour_wanya_niwa_拱桥.jpg", 1.9, L(fit="cover", z=(1.0, 1.06))),
        ("img", SH / "tour_wanya_ozashiki_正面看高台.jpg", 1.8, L(fit="cover", z=(1.0, 1.06))),
        ("img", SH / "kitcmp_对比_积木vs泼溅.jpg", 5.0, L(fit="letter", z=(1.0, 1.1), note=("积木 vs 泼溅",))),
        ("img", SH / "kitview_map_diorama_0_长卷.jpg", 4.8, L(fit="pan")),
        ("v", GH, 0.3, 4.1, 1.0, L(note=("GitHub", "开源"))),
        ("img", P / "raw/网站截图.png", 6.5, L(fit="cover", z=(1.0, 1.12), note=("网页版", "duamixu1.github.io"))),
        ("v", YP, 9.6, 2.0, 1.0, L(fit="blurfit")),
        ("v", A, 181.2, 3.1, 1.0, L(fadeout=1.2)),
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
OVER = os.environ.get("OVER") == "1"
VOFF = 0.0 if OVER else MLEN   # 口播从成片第几秒开始
def main():
    tag = "v4" if OVER else "v3"
    parts, t = [], 0.0
    for ci, c in enumerate(MONTAGE):
        out = WORK / f"m_{ci:02d}.mp4"; n = cached(c, out, t); parts.append(out); t += n / FPS
    assert abs(t - MLEN) < 0.05, t
    import wave
    with wave.open(str(VOICE)) as w: voice_len = w.getnframes() / w.getframerate()
    for i, sec in enumerate(VO):
        start = VOFF + sec["start"]; end = VOFF + (VO[i + 1]["start"] if i + 1 < len(VO) else voice_len + TAIL)
        if end <= MLEN: print(f"  {sec['name']}: 盖在快剪上，不单独配画面"); continue
        start = max(start, MLEN)                            # 和快剪重叠的部分不再配画面
        target = end - start; clips = VIS[sec["name"]]; got = 0.0
        di = lambda c: 3 if c[0] != "img" else 2
        k = target / sum(c[di(c)] for c in clips)          # 整段按比例拉长 / 缩短到口播长度
        planned = 0.0
        for ci, c in enumerate(clips):
            c = list(c); planned += c[di(c)] * k
            c[di(c)] = round(max(0.4, planned - got), 3) if ci < len(clips) - 1 else round(target - got, 3)
            out = WORK / f"{'w' if OVER else 'u'}{i:02d}_{ci:02d}.mp4"; n = cached(tuple(c), out, start + got); parts.append(out); got += n / FPS
        print(f"  {sec['name']}: 口播 {target:.2f}s，画面 {got:.2f}s", flush=True)
    (WORK / f"parts_{tag}.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    video = WORK / f"video_{tag}.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(WORK / f"parts_{tag}.txt"), "-c", "copy", str(video)])
    total = max(MLEN, VOFF + voice_len + TAIL)

    def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h}:{m:02d}:{s:05.2f}"
    ev = []
    allsubs = [(VOFF + x, txt) for sec in VO for x, txt in sec["subs"]]
    ends = {VOFF + sec["subs"][-1][0]: VOFF + sec["end"] + 0.25 for sec in VO}
    for k, (x, txt) in enumerate(allsubs):
        e = ends.get(x, allsubs[k + 1][0] - 0.06 if k + 1 < len(allsubs) else VOFF + voice_len)
        e = min(e, allsubs[k + 1][0] - 0.06) if k + 1 < len(allsubs) else e
        ev.append(f"Dialogue: 0,{ts(x)},{ts(e)},Sub,,0,0,0,,{txt}")
    ass = WORK / f"subs_{tag}.ass"
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

    music = P / "配乐_v2.wav"; out = P / f"探案版_带你玩一遍_{'v4' if OVER else 'v3'}.mp4"
    if OVER:   # 口播一开始就有：快剪段配乐比口播段稍响（0.24），快剪结束时降到 0.14
        duck = f"volume='if(lt(t,{MLEN - 0.5}),0.24,if(lt(t,{MLEN + 0.5}),0.24-0.10*(t-{MLEN - 0.5}),0.14))':eval=frame"
    else:
        duck = f"volume='if(lt(t,{MLEN - 0.8}),0.8,if(lt(t,{MLEN + 0.4}),0.8-0.66*(t-{MLEN - 0.8})/1.2,0.14))':eval=frame"
    mix = WORK / f"audio_{tag}.wav"
    run(["-i", str(music), "-i", str(VOICE), "-filter_complex",
         f"[0:a]asplit[m1][m2];[m1]atrim=0:19,asetpts=PTS-STARTPTS[a0];[m2]atrim=11.5:19,asetpts=PTS-STARTPTS,aloop=loop=-1:size=330750[a1];"
         f"[a0][a1]concat=n=2:v=0:a=1,atrim=0:{total:.3f},{duck},afade=t=out:st={total - 2.5:.3f}:d=2.5[mu];"
         f"[1:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int(VOFF * 1000)}|{int(VOFF * 1000)},apad=whole_dur={total:.3f}[vo];"
         f"[mu][vo]amix=inputs=2:normalize=0:duration=shortest,alimiter=limit=0.95[a]",
         "-map", "[a]", "-ar", "44100", str(mix)])
    run(["-i", str(video), "-i", str(mix), "-vf", f"subtitles={ass.as_posix()}:fontsdir={FONTDIR}",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", str(out)])
    print(out, f"{total:.1f}s")

main()
