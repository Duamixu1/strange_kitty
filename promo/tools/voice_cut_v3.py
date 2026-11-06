"""
把用户录的配音（promo/raw/voice_v3/原始.m4a → 原始_立体声.wav，44.1k 立体声；11-03 用户嫌声音不清楚：原录音两个声道不一样，混成单声道会抵消掉一部分，所以保留原来的两个声道，不做任何处理）切成一句一句，给 cut_tour_v3.py 用。
每句是原始录音里的一段或几段（几段时中间的"然后""嗯"去掉）；边界用逐段转写试出来的固定秒数（自动吸附到最安静处会切掉字尾），两头 15ms 淡入淡出。
  ~/socialmedia/tools/.venv/bin/python promo/tools/voice_cut_v3.py   → promo/raw/voice_v3/<句名>.wav + _连起来.wav（核对用）
"""
import wave, sys
from pathlib import Path
import numpy as np
D = Path(__file__).resolve().parents[1] / "raw/voice_v3"
SR = 44100
w = wave.open(str(D / "原始_立体声.wav")); A = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
# 句名: [(起, 止), ...]   原始录音秒数
CUTS = {   # 边界是 11-03 逐段转写试出来的（tools 外的 probe：切一段、重采样到 16k 转写，看头尾字齐不齐、"然后"去没去掉）
    "L1": [(0.0, 3.8)],                  # 形，真，理。三样凑不齐，剑就拔不出来。
    "L2": [(3.8, 5.57)],                 # 不过在这里的话呢，
    "L3": [(5.57, 6.6)],                 # 按 X 就行。
    "L4": [(7.3, 10.35)],                # （然后）手机上点一下，也可以。
    "L5": [(10.35, 12.29)],              # 就是按的不太好看。
    "L6": [(12.29, 15.73)],              # 这三个地方我都照着原作搭出来了。
    "L7": [(15.73, 21.02)],              # 结局你可以扮成他，自己去探索来看。
    "L8": [(21.6, 25.6)],                # （然后）链接在简介。手机和电脑都可以使用。
    "H0": [(27.0, 28.96)],               # （然后）关于花絮这里的话呢
    "H1": [(34.7, 41.1)],                # 其实番头的后脑勺是双面人，所以后面有一张脸，但是改的时候改掉了。
    "H2": [(41.4, 44.52)],               # （然后）因为用的是高斯泼溅，所以会有一些穿模。
    "H3": [(44.52, 46.62), (48.0, 49.03)], # 包括他的脚可能也有一些（嗯）折叠起来了。
    "H4": [(49.505, 50.55)],             # （然后都）最后还是调好了。
    "H5": [(50.55, 61.4)],               # 接下来可能还会做一些动作，还有物怪的出现，就是可能增加一些真实打斗砍击的感觉。
    "H6": [(61.4, 64.97)],               # 大家来试玩一下，多给一点建议吧。
}
fade = np.linspace(0, 1, int(0.015 * SR), dtype=np.float32)
def piece(a, b):
    x = A[int(a * SR): int(b * SR)].copy(); x[:len(fade)] *= fade[:, None]; x[-len(fade):] *= fade[::-1, None]; return x
def save(name, x):
    with wave.open(str(D / f"{name}.wav"), "wb") as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

allx, gap = [], np.zeros((int(0.8 * SR), 2), np.float32)
for name, parts in CUTS.items():
    x = np.concatenate([np.concatenate([piece(a, b), np.zeros((int(0.18 * SR), 2), np.float32)]) if k < len(parts) - 1 else piece(a, b) for k, (a, b) in enumerate(parts)])
    save(name, x); allx += [x, gap]
    print(name, f"{len(x) / SR:.2f}s")
save("_连起来", np.concatenate(allx))
