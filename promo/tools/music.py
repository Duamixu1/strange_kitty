"""
药郎角色样片的配乐：纯代码合成，没有任何采样，可放心商用/发布。

乐器：拍子木（歌舞伎开场的"梆梆"声）、太鼓、三味线（Karplus-Strong 拨弦 + 噪声击弦）、
能管（尖啸滑音）、铃、低频电子底音。音阶用日本"都节"音阶 E F A B C。
速度 120 BPM，一拍 0.5 秒，和剪辑的切点一一对应（见 edit.py 的 SHOTS）。

用法：python music.py 输出.wav
"""
import sys
import numpy as np
from numba import njit
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
LEN = 24.0
BEAT = 0.5
rng = np.random.default_rng(7)

N = int(SR * LEN)
dry = np.zeros((2, N))   # 干声
send = np.zeros((2, N))  # 送混响


def tt(d):
    return np.arange(int(SR * d)) / SR


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def put(sig, t0, gain=1.0, pan=0.0, rev=0.3):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    for ch, g in ((0, l), (1, r)):
        dry[ch, i:i + len(sig)] += sig * g
        send[ch, i:i + len(sig)] += sig * g * rev


# ---------- 乐器 ----------

def hyoshigi(vel=1.0):
    """拍子木：两块硬木对敲，高频衰减很快"""
    t = tt(0.25)
    s = np.zeros_like(t)
    for f, d, a in ((1720, 0.030, 1.0), (2610, 0.020, 0.7), (4050, 0.012, 0.45), (5900, 0.007, 0.3)):
        s += a * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    n = bp(rng.standard_normal(len(t)), 2000, 9000) * np.exp(-t / 0.003)
    s = s + 0.6 * n
    s2 = np.zeros_like(s)
    k = int(0.004 * SR)
    s2[k:] = s[:-k] * 0.5  # 两根木头不完全同时
    return (s + s2) * vel * 0.5


def taiko(pitch=60, vel=1.0, decay=0.5):
    t = tt(decay * 4)
    f = pitch * (1 + 1.4 * np.exp(-t / 0.018))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / decay)
    skin = lp(rng.standard_normal(len(t)), 400) * np.exp(-t / 0.05) * 1.5
    hit = bp(rng.standard_normal(len(t)), 800, 3000) * np.exp(-t / 0.004) * 0.25
    return np.tanh(1.6 * (body + skin + hit)) * vel


def ka(vel=1.0):
    """太鼓敲鼓边"""
    t = tt(0.12)
    s = np.sin(2 * np.pi * 980 * t) * np.exp(-t / 0.012) + 0.5 * np.sin(2 * np.pi * 1630 * t) * np.exp(-t / 0.008)
    s += 0.4 * bp(rng.standard_normal(len(t)), 1500, 6000) * np.exp(-t / 0.003)
    return s * vel * 0.45


@njit(cache=True)
def _ks(exc, period, n, loss, bright):
    buf = np.zeros(n)
    p = int(period)
    frac = period - p
    for i in range(n):
        x = exc[i] if i < len(exc) else 0.0
        a = buf[i - p] if i - p >= 0 else 0.0
        b = buf[i - p - 1] if i - p - 1 >= 0 else 0.0
        c = buf[i - p - 2] if i - p - 2 >= 0 else 0.0
        d = (1 - frac) * a + frac * b
        e = (1 - frac) * b + frac * c
        buf[i] = x + loss * (bright * d + (1 - bright) * 0.5 * (d + e))
    return buf


def shamisen(freq, vel=1.0, dur=0.9):
    n = int(SR * dur)
    exc = rng.standard_normal(int(SR / freq * 1.2))
    exc = exc - exc.mean()
    s = _ks(exc, SR / freq, n, 0.9975, 0.35)
    s /= np.abs(s).max() + 1e-9
    t = tt(dur)
    s *= np.minimum(1, (dur - t) / 0.05)  # 尾部收掉
    buzz = np.tanh(3.5 * s) - s  # 三味线的"嗡"（さわり）
    bachi = bp(rng.standard_normal(n), 1500, 7000) * np.exp(-t / 0.006) * 0.8  # 拨子打在皮上
    thump = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.02) * 0.4
    return (s + 0.5 * hp(buzz, 900) + bachi + thump) * vel * 0.35


def rin(freq=880, vel=1.0, dur=5.0):
    t = tt(dur)
    s = np.zeros_like(t)
    for m, a, d in ((1, 1, 3.5), (2.76, 0.5, 1.8), (5.40, 0.3, 0.9), (8.93, 0.15, 0.4)):
        s += a * np.sin(2 * np.pi * freq * m * t + rng.uniform(0, 6)) * np.exp(-t / d)
    s *= 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)  # 铃的拍频
    return s * vel * 0.18


def nohkan(t_dur=0.6, f0=1100, f1=2350, vel=1.0):
    """能管的"ひしぎ"：气声很重的尖啸，往上滑"""
    t = tt(t_dur)
    x = t / t_dur
    f = f0 + (f1 - f0) * (x ** 0.6) + 25 * np.sin(2 * np.pi * 7 * t) * x
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph)
    breath = bp(rng.standard_normal(len(t)), 1500, 5000) * 0.5
    env = np.minimum(1, t / 0.06) * np.minimum(1, (t_dur - t) / 0.08)
    return (tone + breath) * env * vel * 0.22


def metal_shing(vel=1.0, dur=1.6):
    """出鞘/收剑的金属声"""
    t = tt(dur)
    s = np.zeros_like(t)
    for f, d in ((2950, 0.9), (4480, 0.6), (6270, 0.4), (7810, 0.3), (9620, 0.2)):
        s += np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    scrape = hp(rng.standard_normal(len(t)), 4000) * np.exp(-t / 0.08) * 0.6
    return (s * 0.25 + scrape) * vel * 0.3


def riser(dur):
    t = tt(dur)
    x = t / dur
    n = rng.standard_normal(len(t))
    out = np.zeros_like(t)
    seg = 2048  # 分段扫频
    for i in range(0, len(t), seg):
        fc = 300 + 7000 * x[i] ** 2
        out[i:i + seg] = bp(n[i:i + seg], fc * 0.7, min(fc * 1.4, 20000))
    return out * (x ** 2) * 0.5


def drone(start, dur, root=82.41, gain=1.0):
    t = tt(dur)
    s = np.zeros_like(t)
    for f, a in ((root, 1), (root * 1.5, 0.5), (root * 2, 0.35), (root * 0.5, 0.6)):
        for det in (-0.25, 0.25):
            ph = 2 * np.pi * (f + det) * t
            for h in range(1, 6):  # 带几个泛音的锯齿
                s += a / h * np.sin(h * ph) / 2
    s = lp(s, 500)
    s *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t)
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.0)
    put(s * env * 0.06 * gain, start, pan=0, rev=0.5)


NOTE = dict(E2=82.41, E3=164.81, F3=174.61, A3=220.0, B3=246.94, C4=261.63,
            E4=329.63, F4=349.23, A4=440.0, B4=493.88, C5=523.25, E5=659.26)
RIFF = [  # 两小节一循环，(第几个八分音符, 音)
    [(0, 'E3'), (1, 'E4'), (3, 'B3'), (4, 'C4'), (6, 'B3'), (7, 'A3')],
    [(0, 'F3'), (2, 'F4'), (3, 'E4'), (5, 'C4'), (6, 'B3'), (7, 'F3')],
]


def riff_bar(t0, which, vel=1.0, octave=False):
    for k, n in RIFF[which]:
        f = NOTE[n]
        put(shamisen(f, vel * rng.uniform(0.85, 1.0)), t0 + k * BEAT / 2, pan=0.35, rev=0.25)
        if octave:
            put(shamisen(f * 2, vel * 0.55), t0 + k * BEAT / 2 + 0.008, pan=-0.3, rev=0.3)


# ---------- 编排 v2（秒，和 edit.py 的 SHOTS 对应：界面开场 → 挥剑 → 片名 → 展示） ----------

# 0–1.5 Claude 界面全景：铃 + 底音 + 两声拍子木
put(rin(880, 1.0, 6), 0.0, pan=-0.2, rev=0.7)
drone(0.0, 9.0)
put(hyoshigi(1.0), 0.0, pan=-0.1, rev=0.5)
put(hyoshigi(0.9), 1.0, pan=-0.1, rev=0.5)

# 1.5–3 推进到预览窗口：风声上扬 + 拍子木越敲越快
put(riser(1.5) * 0.8, 1.5, rev=0.4)
roll, gap = 2.0, 0.22
while roll < 2.95:
    put(hyoshigi(0.4 + 0.5 * (roll - 2.0)), roll, pan=-0.1, rev=0.3)
    roll += gap
    gap = max(0.05, gap * 0.8)

# 3–4.5 落地 + 拔剑
put(taiko(55, 1.1, 0.8), 3.0, rev=0.4)
put(hyoshigi(1.0), 3.0, rev=0.5)
put(metal_shing(0.8, 1.2), 3.25, pan=0.2, rev=0.5)
riff_bar(3.0, 0, 0.85)
put(taiko(62, 0.7), 3.5, rev=0.25)
put(taiko(62, 0.8), 4.0, rev=0.25)
put(ka(0.7), 3.75, pan=0.2)
put(ka(0.7), 4.25, pan=0.2)

# 4.5–5 脸+剑特写：能管尖啸
put(nohkan(0.55, 1150, 2400, 1.0), 4.45, pan=0.1, rev=0.6)

# 5–6 举剑亮相：一声大鼓，然后蓄力，最后一拍空出来
put(taiko(48, 1.2, 1.0), 5.0, rev=0.5)
put(hyoshigi(1.0), 5.0, rev=0.5)
put(shamisen(NOTE['E3'], 1.0, 0.9), 5.0, pan=0.3, rev=0.5)
put(shamisen(NOTE['F3'], 0.8, 0.4), 5.5, pan=0.3, rev=0.5)
put(riser(0.85), 5.05, rev=0.4)
drone(5.0, 1.0, root=87.31, gain=1.3)

# 6 横斩：重击
put(taiko(42, 1.6, 1.3), 6.0, rev=0.6)
put(hyoshigi(1.2), 6.0, rev=0.6)
put(metal_shing(1.3, 2.0), 6.0, pan=0.15, rev=0.7)
sub = np.sin(2 * np.pi * 38 * tt(1.5)) * np.exp(-tt(1.5) / 0.5)
put(sub * 0.6, 6.0, rev=0)
crash = bp(rng.standard_normal(int(SR * 2)), 2500, 12000) * np.exp(-tt(2) / 0.5) * 0.25
put(crash, 6.0, rev=0.8)

# 6–9.5 高潮：三味线八度 + 太鼓八分
drone(6.0, 4.0)
for b in range(2):
    t0 = 6.0 + b * 2
    riff_bar(t0, 0, 1.0, octave=True)
    if t0 + 1.0 < 9.4:
        riff_bar(t0 + 1.0, 1, 1.0, octave=True)
    for k in range(8):
        tk = t0 + k * BEAT / 2
        if tk >= 9.4:
            break
        if k in (0, 3, 4, 6):
            put(taiko(58 if k else 50, 1.0 if k in (0, 4) else 0.7), tk, rev=0.3)
        else:
            put(ka(0.7), tk, pan=0.2)
    put(hyoshigi(0.6), t0 + 3 * BEAT, pan=-0.2, rev=0.4)

# 9.5 收剑"叮" → 片名
put(metal_shing(0.9, 1.0), 9.3, pan=0.2, rev=0.5)
put(hyoshigi(1.1), 9.5, rev=0.6)
put(taiko(46, 1.0, 1.0), 9.5, rev=0.5)
put(rin(880, 0.9, 4), 9.5, pan=-0.2, rev=0.7)

# 9.5–11.5 片名：安静下来，三味线零星几声
drone(9.5, 12.5)
for tn, n, v in ((9.5, 'E3', 0.9), (10.25, 'B3', 0.6), (10.5, 'C4', 0.7), (11.0, 'A3', 0.7)):
    put(shamisen(NOTE[n], v, 0.9), tn, pan=0.3, rev=0.5)

# 11.5–15.5 角色展示：riff + 太鼓
for b in range(2):
    t0 = 11.5 + b * 2
    riff_bar(t0, 0, 0.9)
    riff_bar(t0 + 1.0, 1, 0.9)
    for k in (0, 2):
        put(taiko(62, 0.8), t0 + k * BEAT, rev=0.25)
    put(taiko(70, 0.5, 0.3), t0 + 3.5 * BEAT, rev=0.25)
    put(ka(0.8), t0 + 1.5 * BEAT, pan=0.2)
    put(ka(0.6), t0 + 3 * BEAT, pan=0.2)
for t0 in (11.5, 12.5, 13.5, 14.5):
    put(hyoshigi(0.35), t0, pan=-0.3, rev=0.4)

# 15.5–17.5 宽银幕：颤音 + 滚奏渐强
put(shamisen(NOTE['E3'], 1.0, 1.5), 15.5, pan=0.3, rev=0.5)
put(taiko(52, 0.9, 0.9), 15.5, rev=0.4)
t = 16.0
while t < 17.5:
    put(shamisen(NOTE['B4'] if int(t * 8) % 2 else NOTE['C5'], 0.25 + 0.35 * (t - 16.0) / 1.5, 0.3), t, pan=0.4, rev=0.4)
    t += 0.125
t = 16.5
while t < 17.5:
    put(taiko(68, 0.2 + 0.6 * (t - 16.5), 0.25), t, rev=0.2)
    t += 0.0625

# 17.5–21.5 收尾
put(taiko(50, 1.0, 0.8), 17.5, rev=0.4)
put(hyoshigi(0.9), 17.5, rev=0.5)
for b in range(2):
    t0 = 17.5 + b * 2
    v = 0.75 - 0.25 * b
    riff_bar(t0, 0, v)
    riff_bar(t0 + 1.0, 1, v)
    put(taiko(62, v), t0 + (0 if b else 2 * BEAT), rev=0.3)
    put(ka(0.5 * v), t0 + 1.5 * BEAT, pan=0.2)

# 21.5 片尾：拍子木 + 铃
put(hyoshigi(1.0), 21.5, rev=0.6)
put(rin(880, 1.1, 2.5), 21.5, pan=0.2, rev=0.8)
put(taiko(45, 0.9, 1.0), 21.5, rev=0.6)

# ---------- 混音 ----------
ir_t = tt(2.4)
ir = np.stack([lp(rng.standard_normal(len(ir_t)), 6000) * np.exp(-ir_t / 0.55) for _ in range(2)])
ir[:, : int(0.02 * SR)] = 0  # 预延迟
wet = np.stack([fftconvolve(send[c], ir[c])[:N] for c in range(2)])
wet /= np.abs(wet).max() + 1e-9
mix = dry / (np.abs(dry).max() + 1e-9) + 0.28 * wet
mix = hp(mix, 30)
mix = np.tanh(1.3 * mix) / np.tanh(1.3)
fade = np.ones(N)
fade[-int(SR * 0.5):] = np.linspace(1, 0, int(SR * 0.5))
mix *= fade
mix *= 0.89 / np.abs(mix).max()

out = sys.argv[1] if len(sys.argv) > 1 else 'music.wav'
from scipy.io import wavfile
wavfile.write(out, SR, (mix.T * 32767).astype(np.int16))
print('wrote', out, LEN, 's')
