// 游览版的声音：全部现场合成（Web Audio），不用音频文件，不用原片配乐（14 第九节）。
// 三路：BGM（按地点生成的小调：古筝 / 三味线 / 八音盒拨弦 + 低音持续音，偶尔尺八、太鼓、铃，每次听都不一样，乐句之间留"间"）、
//       环境声（雨、屋里听雨、风、人声嘈杂、室内底噪）、音效（转场拍子木 + 拉门、开卡铃、关卡纸声、快门、脚步）。
// 浏览器要用户先点一下才出声：tour.js 在第一次 pointerdown / keydown 调 unlock()。
// 调度：scheduleUntil(t) 把 t 以前要响的音都排进 AudioContext 的时间线；在线每 100 毫秒往前排 0.4 秒，
// 离线录音（renderDemo，验收用：录成 WAV 看波形、发给用户听）一次排完。
// 拨弦是 Karplus-Strong（一段噪声在延迟环里反复低通，像弦的振动慢慢衰减），算一次缓存成 AudioBuffer。

const SCALES = { in: [0, 1, 5, 7, 8], yo: [0, 2, 5, 7, 9], hira: [0, 2, 3, 7, 8] };   // 都节、阳、平调子（五声，日本传统音阶）
// 每个地点的曲子：root 主音（MIDI），lead 主奏乐器，density 每个八分音符出音的概率，drone 低音持续音两个音，
// flute 乐句停下时吹一声尺八的概率，bell 铃，taiko 太鼓（每小节第一拍的概率）
const MUSIC = {
  map:   { root: 50, scale: "in",   bpm: 54, lead: "koto",     density: 0.3,  drone: [38, 45], flute: 0.3,  bell: 0.15 },
  ooku:  { root: 52, scale: "in",   bpm: 58, lead: "koto",     density: 0.45, drone: [40, 47], flute: 0.35, bell: 0.08 },
  wanya: { root: 69, scale: "hira", bpm: 66, lead: "musicbox", density: 0.4,  drone: [45, 52], flute: 0.1,  bell: 0.15 },
  sakai: { root: 50, scale: "yo",   bpm: 84, lead: "shamisen", density: 0.5,  drone: [38, 45], flute: 0.1,  bell: 0.05, taiko: 0.7 },
  dark:  { root: 50, scale: "in",   bpm: 46, lead: "koto",     density: 0.15, drone: [38, 44], flute: 0.2,  bell: 0.3 },   // 密室、阿雪的空房
};
const DARK = ["sakai.misshitsu", "ooku.yuki"];
// 环境声：按"地点.区块"，再按"地点.*"，都没有就是室内底噪
const AMBIENCE = {
  map: ["wind_soft"],
  "wanya.soto": ["rain"], "wanya.*": ["rain_in"],
  "sakai.omote": ["crowd", "wind_soft"], "sakai.ozashiki": ["crowd_in"], "sakai.daidokoro": ["wind_soft"],
  "ooku.courtyard": ["wind_soft"],
};
// 脚步声的地面：按区块定（积木地面没有逐格材质）。坂井家玄关土间（比地板低）在 tour.js 里按高度改成石头
const FLOOR = {
  "ooku.corridor": "wood", "ooku.courtyard": "gravel", "ooku.*": "tatami",
  "wanya.soto": "wet", "wanya.genkan": "stone", "wanya.rouka": "wood", "wanya.niwa": "wood", "wanya.ozashiki": "tatami",
  "sakai.omote": "stone", "sakai.rouka": "wood", "sakai.daidokoro": "stone", "sakai.*": "tatami",
};
const pick = (table, loc, zone, def) => table[`${loc}.${zone}`] ?? table[`${loc}.*`] ?? table[loc] ?? def;
const mtof = (m) => 440 * 2 ** ((m - 69) / 12);
const rnd = (a, b) => a + Math.random() * (b - a);

class Engine {
  constructor(ctx) {
    this.ctx = ctx;
    const g = (v, to) => { const n = ctx.createGain(); n.gain.value = v; if (to) n.connect(to); return n; };
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 3; comp.connect(ctx.destination);
    this.master = g(0.85, comp);
    this.music = g(0.75, this.master); this.amb = g(0.4, this.master); this.sfxBus = g(0.95, this.master);
    // 混响：程序造的冲激响应（双声道噪声按指数衰减 2.4 秒），像木结构大屋子
    this.verb = ctx.createConvolver(); this.verb.buffer = this.impulse(2.4); this.verb.connect(g(0.5, this.master));
    this.white = this.noise(2, false); this.brown = this.noise(4, true);
    this.ks = new Map(); this.m = null; this.ambNodes = []; this.ambTicks = []; this.droneNodes = [];
  }
  impulse(sec) {
    const { ctx } = this, n = Math.floor(ctx.sampleRate * sec), b = ctx.createBuffer(2, n, ctx.sampleRate);
    for (let c = 0; c < 2; c++) { const d = b.getChannelData(c); for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3.2) * (i < 200 ? i / 200 : 1); }
    return b;
  }
  noise(sec, brown) {
    const { ctx } = this, n = Math.floor(ctx.sampleRate * sec), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
    let last = 0;
    for (let i = 0; i < n; i++) { const w = Math.random() * 2 - 1; if (brown) { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; } else d[i] = w; }
    // 首尾交叉淡化 1000 个采样，循环接缝不出咔哒声
    for (let i = 0; i < 1000; i++) { const k = i / 1000; d[i] = d[i] * k + d[n - 1000 + i] * (1 - k); }
    return b;
  }
  src(buf, t, { loop = false, rate = 1, offset = 0 } = {}) {
    const s = this.ctx.createBufferSource(); s.buffer = buf; s.loop = loop; s.playbackRate.value = rate; s.start(t, offset); return s;
  }
  filt(type, f, q = 1) { const n = this.ctx.createBiquadFilter(); n.type = type; n.frequency.value = f; n.Q.value = q; return n; }
  env(t, a, peak, d, to) {   // 增益包络：a 秒升到 peak，d 秒指数衰减到无声
    const n = this.ctx.createGain(); n.gain.setValueAtTime(0.0001, t); n.gain.linearRampToValueAtTime(peak, t + a); n.gain.exponentialRampToValueAtTime(0.0001, t + a + d); n.connect(to); return n;
  }
  pan(v, to) { const p = this.ctx.createStereoPanner(); p.pan.value = v; p.connect(to); return p; }
  chain(...nodes) { for (let i = 0; i < nodes.length - 1; i++) nodes[i].connect(nodes[i + 1]); return nodes[0]; }
  send(node, amt) { const s = this.ctx.createGain(); s.gain.value = amt; node.connect(s); s.connect(this.verb); }

  // ---- 乐器 ----
  pluckBuf(freq, kind) {
    const key = `${kind}:${freq.toFixed(1)}`;
    if (this.ks.has(key)) return this.ks.get(key);
    const sr = this.ctx.sampleRate, dur = kind === "shamisen" ? 1.6 : 3.2, n = Math.floor(sr * dur), N = Math.max(2, Math.round(sr / freq));
    const damp = kind === "shamisen" ? 0.992 : 0.997, bright = kind === "shamisen" ? 0.95 : 0.55;
    const b = this.ctx.createBuffer(1, n, sr), d = b.getChannelData(0), ring = new Float32Array(N);
    let p = 0; for (let i = 0; i < N; i++) { p = bright * (Math.random() * 2 - 1) + (1 - bright) * p; ring[i] = p; }
    let idx = 0, peak = 0;
    for (let i = 0; i < n; i++) { const v = ring[idx], nx = ring[(idx + 1) % N]; ring[idx] = damp * 0.5 * (v + nx); d[i] = v; idx = (idx + 1) % N; peak = Math.max(peak, Math.abs(v)); }
    for (let i = 0; i < n; i++) d[i] = d[i] / (peak || 1) * (i > n - 2000 ? (n - i) / 2000 : 1);
    this.ks.set(key, b); return b;
  }
  koto(t, f, vel) {
    const out = this.env(t, 0.003, vel * 0.5, 3, this.pan(rnd(-0.3, 0.3), this.music));
    const s = this.src(this.pluckBuf(f, "koto"), t); s.connect(this.chain(this.filt("lowpass", 3200), out));
    if (Math.random() < 0.15) { s.playbackRate.setValueAtTime(1, t + 0.25); s.playbackRate.linearRampToValueAtTime(1.0595, t + 0.45); }   // 押手：按弦把音推高半音，筝的味道
    this.send(out, 0.35);
  }
  shamisen(t, f, vel) {
    const out = this.env(t, 0.002, vel * 0.42, 1.5, this.pan(rnd(-0.2, 0.2), this.music));
    const peakF = this.filt("peaking", 2300, 2); peakF.gain.value = 6;   // 三味线"さわり"的嗡嗡亮音
    this.src(this.pluckBuf(f, "shamisen"), t).connect(this.chain(peakF, out));
    const click = this.env(t, 0.001, vel * 0.12, 0.02, out);   // 拨子打在皮上的一下
    this.src(this.white, t, { offset: Math.random() }).connect(this.chain(this.filt("highpass", 3000), click));
    this.send(out, 0.2);
  }
  musicbox(t, f, vel) {
    const out = this.env(t, 0.002, vel * 0.16, 1.8, this.pan(rnd(-0.4, 0.4), this.music));
    for (const [r, a] of [[1, 1], [3, 0.22], [5.4, 0.08]]) { const o = this.ctx.createOscillator(); o.frequency.value = f * r; const g = this.ctx.createGain(); g.gain.value = a; o.connect(g); g.connect(out); o.start(t); o.stop(t + 2); }
    this.send(out, 0.5);
  }
  flute(t, f, dur) {   // 尺八：正弦 + 气声（噪声过窄带通），起音先吹一口气，0.6 秒后加揉音
    const { ctx } = this, out = ctx.createGain(), p = this.pan(rnd(-0.2, 0.2), this.music);
    out.gain.setValueAtTime(0.0001, t); out.gain.linearRampToValueAtTime(0.1, t + 0.35); out.gain.setValueAtTime(0.1, t + dur - 0.6); out.gain.linearRampToValueAtTime(0.0001, t + dur); out.connect(p);
    const o = ctx.createOscillator(); o.frequency.value = f; o.frequency.setValueAtTime(f * 0.97, t); o.frequency.linearRampToValueAtTime(f, t + 0.3);
    const vib = ctx.createOscillator(), vg = ctx.createGain(); vib.frequency.value = 5; vg.gain.setValueAtTime(0, t); vg.gain.linearRampToValueAtTime(f * 0.012, t + 0.9); vib.connect(vg); vg.connect(o.frequency);
    o.connect(out); o.start(t); o.stop(t + dur); vib.start(t); vib.stop(t + dur);
    const breath = ctx.createGain(); breath.gain.setValueAtTime(0.4, t); breath.gain.linearRampToValueAtTime(0.12, t + 0.4); breath.connect(out);
    const s = this.src(this.white, t, { loop: true, offset: Math.random() }); s.connect(this.chain(this.filt("bandpass", f * 2, 8), this.filt("lowpass", 2500), breath)); s.stop(t + dur);
    this.send(out, 0.6);
  }
  bell(t, f = 1180, vel = 0.25) {   // 铃（佛具的"りん"）：几组不成倍数的泛音，每组两个微微走音，拍出"嗡——"
    const out = this.env(t, 0.002, vel, 4.5, this.pan(rnd(-0.3, 0.3), this.sfxBus));
    for (const [r, a] of [[1, 1], [2.71, 0.45], [5.15, 0.2]]) for (const det of [0, 1.6]) {
      const o = this.ctx.createOscillator(); o.frequency.value = f * r + det; const g = this.ctx.createGain(); g.gain.value = a * 0.5; o.connect(g); g.connect(out); o.start(t); o.stop(t + 5);
    }
    this.send(out, 0.4);
  }
  taiko(t, vel = 0.5) {
    const { ctx } = this, out = this.env(t, 0.002, vel, 0.55, this.music);
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(115, t); o.frequency.exponentialRampToValueAtTime(52, t + 0.18); o.connect(out); o.start(t); o.stop(t + 0.7);
    const thump = this.env(t, 0.001, vel * 0.6, 0.08, this.music); this.src(this.brown, t, { offset: Math.random() * 2 }).connect(this.chain(this.filt("lowpass", 260), thump));
    this.send(out, 0.25);
  }

  // ---- BGM ----
  setMusic(name, t) {
    if (this.m?.name === name) return;
    const cfg = MUSIC[name];
    for (const n of this.droneNodes) { n.gain.cancelScheduledValues(t); n.gain.setValueAtTime(n.gain.value, t); n.gain.linearRampToValueAtTime(0.0001, t + 2); n._stop(t + 2.1); }
    this.droneNodes = [];
    // 低音持续音：两个三角波，过低通，音量慢慢起伏（0.07 赫兹）
    for (const [i, m] of cfg.drone.entries()) {
      const o = this.ctx.createOscillator(); o.type = "triangle"; o.frequency.value = mtof(m); o.detune.value = i ? 4 : -3;
      const g = this.ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.035, t + 4);
      const lfo = this.ctx.createOscillator(), lg = this.ctx.createGain(); lfo.frequency.value = 0.07 + i * 0.03; lg.gain.value = 0.015; lfo.connect(lg); lg.connect(g.gain);
      o.connect(this.chain(this.filt("lowpass", 420), g)); g.connect(this.music);
      o.start(t); lfo.start(t); g._stop = (s) => { o.stop(s); lfo.stop(s); };
      this.droneNodes.push(g);
    }
    this.m = { name, cfg, next: t + 2.5, i: 0, deg: 2 + Math.floor(Math.random() * 3), len: 0, rest: 0 };
  }
  scheduleMusic(until) {
    const m = this.m; if (!m) return;
    const c = m.cfg, sc = SCALES[c.scale], eighth = 60 / c.bpm / 2;
    while (m.next < until) {
      const t = m.next;
      if (m.rest > 0) m.rest--;
      else {
        if (Math.random() < c.density) {
          m.deg += [-2, -1, -1, 0, 1, 1, 2][Math.floor(Math.random() * 7)];
          if (m.deg < 0) m.deg = 1; if (m.deg > 9) m.deg = 8;
          const note = c.root + 12 * Math.floor(m.deg / 5) + sc[m.deg % 5], vel = rnd(0.6, 1);
          this[c.lead](t, mtof(note), vel);
          if (Math.random() < 0.12) this[c.lead](t + (c.lead === "koto" ? 0.03 : 0), mtof(note - 12), vel * 0.6);   // 偶尔加低八度
        }
        if (++m.len >= 16 && Math.random() < 0.25) {   // 乐句结束：停 8~16 个八分音符，有时这时吹一声尺八、敲一下铃
          m.len = 0; m.rest = 6 + Math.floor(Math.random() * 8);
          if (Math.random() < c.flute) this.flute(t + eighth, mtof(c.root + 12 + sc[Math.floor(Math.random() * 5)]), m.rest * eighth * 0.8);
          if (Math.random() < c.bell) this.bell(t + eighth * 2, mtof(c.root + 36 + sc[0]) * 0.5, 0.08);
        }
      }
      if (c.taiko && m.rest === 0) { if (m.i % 8 === 0 && Math.random() < c.taiko) this.taiko(t, 0.35); else if (m.i % 8 === 5 && Math.random() < c.taiko * 0.4) this.taiko(t, 0.2); }
      m.i++; m.next += eighth;
    }
  }

  // ---- 环境声 ----
  setAmbience(list, t) {
    const key = list.join(",");
    if (this.ambKey === key) return;
    this.ambKey = key;
    for (const n of this.ambNodes) { n.gain.cancelScheduledValues(t); n.gain.setValueAtTime(n.gain.value, t); n.gain.linearRampToValueAtTime(0.0001, t + 1.5); n._stop?.(t + 1.6); }
    this.ambNodes = []; this.ambTicks = [];
    for (const k of list) this[`amb_${k}`]?.(t);
  }
  ambGain(t, v) { const g = this.ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(v, t + 1.5); g.connect(this.amb); this.ambNodes.push(g); return g; }
  loopNoise(t, buf, ...fx) { const s = this.src(buf, t, { loop: true, offset: Math.random() * 1.5 }); s.connect(this.chain(...fx)); return s; }
  amb_rain(t, inside = false) {
    const g = this.ambGain(t, inside ? 0.06 : 0.08);
    const s1 = this.loopNoise(t, this.white, this.filt("highpass", inside ? 200 : 600), this.filt("lowpass", inside ? 900 : 4000), g);
    const g2 = this.ambGain(t, inside ? 0.08 : 0.1), s2 = this.loopNoise(t, this.brown, this.filt("lowpass", 300), g2);   // 远处的雨声底
    g._stop = (s) => s1.stop(s); g2._stop = (s) => s2.stop(s);
    if (!inside) this.ambTicks.push({ next: t, tick: (tt) => {   // 屋檐滴水：随机的短"嗒"
      if (Math.random() < 0.5) { const e = this.env(tt, 0.001, rnd(0.04, 0.12), 0.04, this.pan(rnd(-0.8, 0.8), this.amb)); this.src(this.white, tt, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", rnd(2000, 5000), 6), e)); }
      return 0.07;
    } });
  }
  amb_rain_in(t) { this.amb_rain(t, true); }
  amb_wind_soft(t) {
    const g = this.ambGain(t, 0.16), f = this.filt("lowpass", 500, 0.7);
    const lfo = this.ctx.createOscillator(), lg = this.ctx.createGain(); lfo.frequency.value = 0.09; lg.gain.value = 260; lfo.connect(lg); lg.connect(f.frequency); lfo.start(t);
    const s = this.loopNoise(t, this.brown, f, g); g._stop = (st) => { s.stop(st); lfo.stop(st); };
  }
  amb_crowd(t, inside = false) {   // 人声嘈杂：几条窄带噪声放在元音共振峰上，音量每 0.2 秒随机变，像听不清的说话声
    const out = this.ambGain(t, inside ? 0.12 : 0.18), forms = [];
    for (const f of [420, 780, 1250, 2300]) {
      const g = this.ctx.createGain(); g.gain.value = 0; g.connect(out);
      const s = this.loopNoise(t, this.white, this.filt("bandpass", f, 5), g); forms.push({ g, s });
    }
    out._stop = (st) => forms.forEach((x) => x.s.stop(st));
    this.ambTicks.push({ next: t, tick: (tt) => { for (const x of forms) x.g.gain.setTargetAtTime(Math.random() < 0.6 ? rnd(0.2, 1) : 0.05, tt, 0.06); return rnd(0.12, 0.25); } });
    if (!inside) this.ambTicks.push({ next: t + 3, tick: (tt) => { if (Math.random() < 0.3) this.bell(tt, rnd(2200, 2600), 0.02); return rnd(4, 9); } });   // 远处偶尔的小铃
  }
  amb_crowd_in(t) { this.amb_crowd(t, true); }
  amb_room(t) { const g = this.ambGain(t, 0.08), s = this.loopNoise(t, this.brown, this.filt("lowpass", 180), g); g._stop = (st) => s.stop(st); }

  scheduleUntil(until) {
    this.scheduleMusic(until);
    for (const a of this.ambTicks) while (a.next < until) a.next += a.tick(a.next);
  }

  // ---- 音效 ----
  hyoshigi(t) {   // 拍子木：两块硬木对敲，"カン、カン"，原作换场的声音
    for (const [dt, v] of [[0, 0.9], [0.22, 1]]) {
      const tt = t + dt, out = this.env(tt, 0.001, v * 0.5, 0.09, this.sfxBus);
      this.src(this.white, tt, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", 2050, 9), out));
      const o = this.ctx.createOscillator(); o.frequency.value = 1150; const og = this.env(tt, 0.001, v * 0.3, 0.06, this.sfxBus); o.connect(og); o.start(tt); o.stop(tt + 0.2);
      this.send(out, 0.8); this.send(og, 0.6);
    }
  }
  slide(t, dur = 0.35) {   // 拉门滑过去
    const out = this.ctx.createGain(); out.gain.setValueAtTime(0.0001, t); out.gain.linearRampToValueAtTime(0.35, t + 0.05); out.gain.linearRampToValueAtTime(0.25, t + dur - 0.05); out.gain.linearRampToValueAtTime(0.0001, t + dur); out.connect(this.sfxBus);
    const s = this.src(this.white, t, { offset: Math.random() }); s.connect(this.chain(this.filt("bandpass", 650, 1.5), this.filt("lowpass", 1400), out)); s.stop(t + dur + 0.05);
    const thud = this.env(t + dur, 0.002, 0.4, 0.12, this.sfxBus); this.src(this.brown, t + dur, { offset: Math.random() }).connect(this.chain(this.filt("lowpass", 300), thud));
  }
  paper(t) {
    const out = this.env(t, 0.02, 0.22, 0.14, this.sfxBus), f = this.filt("bandpass", 3200, 1.2);
    f.frequency.setValueAtTime(3200, t); f.frequency.linearRampToValueAtTime(1500, t + 0.15);
    this.src(this.white, t, { offset: Math.random() }).connect(this.chain(f, out));
  }
  shutter(t) {
    for (const [dt, v] of [[0, 0.5], [0.07, 0.35]]) { const e = this.env(t + dt, 0.001, v, 0.025, this.sfxBus); this.src(this.white, t + dt, { offset: Math.random() }).connect(this.chain(this.filt("highpass", 1800), e)); }
    const o = this.ctx.createOscillator(); o.frequency.value = 180; const og = this.env(t, 0.001, 0.25, 0.05, this.sfxBus); o.connect(og); o.start(t); o.stop(t + 0.1);
  }
  // ---- 拔剑（退魔三拍）----
  unsheathe(t) {   // 抽剑：金属"铮——"，几条不成倍数的高频慢慢衰减，前面一下刀身擦过鞘口
    const out = this.env(t, 0.004, 0.2, 1.5, this.pan(0.1, this.sfxBus));
    for (const [f, a] of [[2150, 1], [3420, 0.6], [5230, 0.35], [7100, 0.2]]) { const o = this.ctx.createOscillator(); o.frequency.value = f * rnd(0.995, 1.005); const g = this.ctx.createGain(); g.gain.value = a * 0.4; o.connect(g); g.connect(out); o.start(t); o.stop(t + 1.7); }
    const sc = this.env(t - 0.2, 0.15, 0.18, 0.12, this.sfxBus), f = this.filt("bandpass", 2500, 2);
    f.frequency.setValueAtTime(2500, t - 0.2); f.frequency.linearRampToValueAtTime(6000, t);
    this.src(this.white, Math.max(0, t - 0.2), { offset: Math.random() }).connect(this.chain(f, sc));
    this.send(out, 0.6);
  }
  awaken(t) {   // 妖化：一记重太鼓 + 低音锯齿波慢慢涨起来又退掉
    const tk = this.env(t, 0.002, 0.8, 0.7, this.sfxBus), o = this.ctx.createOscillator();
    o.frequency.setValueAtTime(100, t); o.frequency.exponentialRampToValueAtTime(45, t + 0.25); o.connect(tk); o.start(t); o.stop(t + 0.9);
    const d = this.ctx.createGain(); d.gain.setValueAtTime(0.0001, t); d.gain.linearRampToValueAtTime(0.12, t + 0.8); d.gain.linearRampToValueAtTime(0.0001, t + 4.5); d.connect(this.sfxBus);
    for (const f of [55, 55.7]) { const s = this.ctx.createOscillator(); s.type = "sawtooth"; s.frequency.value = f; s.connect(this.chain(this.filt("lowpass", 280), d)); s.start(t); s.stop(t + 4.6); }
    this.send(tk, 0.5); this.bell(t + 0.05, 590, 0.12);
  }
  slash(t) {   // 横斩：一阵"嗖"（噪声带通从低扫到高）+ 末尾一声脆响
    const out = this.env(t - 0.12, 0.12, 0.55, 0.2, this.sfxBus), f = this.filt("bandpass", 500, 2);
    f.frequency.setValueAtTime(500, t - 0.12); f.frequency.exponentialRampToValueAtTime(3800, t + 0.1);
    this.src(this.white, Math.max(0, t - 0.12), { offset: Math.random() }).connect(this.chain(f, out));
    const cr = this.env(t, 0.001, 0.35, 0.06, this.sfxBus); this.src(this.white, t, { offset: Math.random() }).connect(this.chain(this.filt("highpass", 3000), cr));
    this.send(out, 0.5); this.send(cr, 0.7);
  }
  sheath(t) {   // 收剑：刀镡碰鞘口"咔、嗒"两下
    for (const [dt, v] of [[0, 0.35], [0.09, 0.5]]) {
      const tt = t + dt, e = this.env(tt, 0.001, v, 0.04, this.sfxBus);
      this.src(this.white, tt, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", 3000, 6), e));
      const o = this.ctx.createOscillator(); o.frequency.value = 1800; const og = this.env(tt, 0.001, v * 0.3, 0.05, this.sfxBus); o.connect(og); o.start(tt); o.stop(tt + 0.1);
    }
  }
  // ---- 物怪出没（docs/18）----
  sweep(t, buf, f0, f1, dur, peak, q = 2) {   // 一阵噪声，带通从 f0 扫到 f1（嗖、呼）
    const out = this.env(t, dur * 0.4, peak, dur * 0.6, this.sfxBus), f = this.filt("bandpass", f0, q);
    f.frequency.setValueAtTime(f0, t); f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    this.src(buf, t, { offset: Math.random() }).connect(this.chain(f, out)); return out;
  }
  scaleBell(t, n = 2, vel = 0.07) {   // 11-06 天秤上挂的小铃（用户："好像天秤没有响"）：细、短、高，几下错开，"叮铃"，不像佛具铃那样嗡很久
    for (let i = 0; i < n; i++) {
      const tt = t + i * rnd(0.07, 0.12), f = rnd(2500, 3300), out = this.env(tt, 0.001, vel * (1 - i * 0.18), 0.55, this.pan(rnd(-0.25, 0.25), this.sfxBus));
      for (const [r, a] of [[1, 1], [2.41, 0.35], [3.9, 0.15]]) { const o = this.ctx.createOscillator(); o.frequency.value = f * r; const g = this.ctx.createGain(); g.gain.value = a * 0.5; o.connect(g); g.connect(out); o.start(tt); o.stop(tt + 0.9); }
      this.send(out, 0.25);
    }
  }
  omen(t) {   // 预兆：铃两下，底下一层低音慢慢涨起来
    this.bell(t, 1320, 0.16); this.bell(t + 0.55, 1250, 0.12);
    const d = this.ctx.createGain(); d.gain.setValueAtTime(0.0001, t); d.gain.linearRampToValueAtTime(0.1, t + 1.6); d.gain.linearRampToValueAtTime(0.0001, t + 3.2); d.connect(this.sfxBus);
    for (const f of [62, 62.8]) { const o = this.ctx.createOscillator(); o.frequency.value = f; o.connect(d); o.start(t); o.stop(t + 3.3); }
  }
  biwa(t) {   // 琵琶（海座头）：几下低沉的拨弦，带"さわり"的嗡响，一下比一下慢，最后一下拖长
    [[0, 147, 0.7], [0.45, 110, 0.6], [0.8, 131, 0.55], [1.6, 98, 0.8], [2.5, 73.4, 0.9]].forEach(([d, f, v]) => {
      const tt = t + d, out = this.env(tt, 0.002, v * 0.45, 2.2, this.sfxBus);
      const peakF = this.filt("peaking", 1800, 2.5); peakF.gain.value = 8;
      this.src(this.pluckBuf(f, "shamisen"), tt).connect(this.chain(peakF, out));
      const click = this.env(tt, 0.001, v * 0.18, 0.03, out);   // 撥（バチ）打在弦上
      this.src(this.white, tt, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", 2400, 3), click));
      this.send(out, 0.45);
    });
  }
  nueCry(t, far = 0) {   // 鵺的叫声：像虎鸫（トラツグミ）夜里那种细长的口哨"ヒィ——……ヒョォ——"，一高一低，带一点颤；far 越大越远（更小、更多回响）
    const ctx = this.ctx, out = ctx.createGain(); out.gain.value = 0.42 * (1 - far * 0.6); out.connect(this.sfxBus); this.send(out, 0.5 + far * 0.4);
    [[0, 2480, 2380, 1.05], [1.55, 2150, 1980, 1.25]].forEach(([dt, f0, f1, dur]) => {
      const tt = t + dt, o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.setValueAtTime(f0 * 0.97, tt); o.frequency.linearRampToValueAtTime(f0, tt + 0.12); o.frequency.exponentialRampToValueAtTime(f1, tt + dur);
      const vib = ctx.createOscillator(), vg = ctx.createGain(); vib.frequency.value = 6.5; vg.gain.value = f0 * 0.006; vib.connect(vg); vg.connect(o.frequency); vib.start(tt); vib.stop(tt + dur + 0.1);
      g.gain.setValueAtTime(0.0001, tt); g.gain.exponentialRampToValueAtTime(0.5, tt + 0.18); g.gain.setValueAtTime(0.5, tt + dur * 0.55); g.gain.exponentialRampToValueAtTime(0.0001, tt + dur);
      const air = this.src(this.white, tt, { offset: Math.random() }), ag = this.env(tt, 0.15, 0.05, dur * 0.8, out);   // 一点气声
      air.connect(this.chain(this.filt("bandpass", f0, 9), ag));
      o.connect(g); g.connect(out); o.start(tt); o.stop(tt + dur + 0.05);
    });
  }
  appear(t) { this.send(this.sweep(t, this.brown, 160, 900, 0.9, 0.4, 1.2), 0.6); this.taiko(t + 0.85, 0.35); }   // 从墨里浮出来
  charge(t) { this.sweep(t, this.white, 400, 1200, 0.7, 0.08, 6); }   // 蓄力：一点尖细的嘶声
  lunge(t) { this.sweep(t, this.white, 300, 1600, 0.3, 0.3, 1.5); }   // 扑过来
  ofuda(t) { this.sweep(t, this.white, 1500, 4500, 0.14, 0.22, 1.5); this.paper(t + 0.02); }   // 札甩出去：纸片划过空气
  pin(t) {   // 钉中："啪"一下闷响 + 纸拍上去的脆声
    const e = this.env(t, 0.001, 0.55, 0.08, this.sfxBus); this.src(this.brown, t, { offset: Math.random() }).connect(this.chain(this.filt("lowpass", 600), e));
    const c = this.env(t, 0.001, 0.3, 0.03, this.sfxBus); this.src(this.white, t, { offset: Math.random() }).connect(this.chain(this.filt("highpass", 2500), c));
    this.send(e, 0.4);
  }
  kanji(t, i = 0) { this.bell(t, [880, 990, 1175][i % 3], 0.18); }   // 形 / 真 / 理 浮起来：一个比一个高
  guard(t) {   // 袖挡：布被撞了一下
    const e = this.env(t, 0.002, 0.45, 0.1, this.sfxBus); this.src(this.brown, t, { offset: Math.random() }).connect(this.chain(this.filt("lowpass", 420), e));
    this.sweep(t, this.white, 1800, 900, 0.12, 0.12, 2);
  }
  dodge(t) { this.sweep(t, this.white, 900, 500, 0.18, 0.12, 1.2); }   // 闪开：衣摆一甩
  jump(t) { this.sweep(t, this.white, 500, 1400, 0.22, 0.14, 1.2); }   // 跳起来：衣摆往上一兜
  land(t) { const e = this.env(t, 0.002, 0.3, 0.07, this.sfxBus); this.src(this.brown, t, { offset: Math.random() }).connect(this.chain(this.filt("lowpass", 380), e)); }   // 落地：一声闷的
  blink(t) { this.sweep(t, this.white, 2400, 6000, 0.12, 0.2, 2); this.paper(t + 0.01); this.paper(t + 0.05); }   // 瞬移：札纸一散
  blinkIn(t) { this.sweep(t, this.white, 5000, 1800, 0.16, 0.14, 2); this.bell(t + 0.02, 1660, 0.06); }   // 现身：纸片收回来
  seal(t) { this.sheath(t); this.bell(t + 0.1, 590, 0.14); }
  locked(t) {   // 形真理没齐按拔剑：刀镡磕在鞘口上一声，闷的，拔不出
    this.sheath(t); const e = this.env(t, 0.002, 0.35, 0.09, this.sfxBus); this.src(this.brown, t, { offset: Math.random() }).connect(this.chain(this.filt("lowpass", 300), e));
  }   // 形真理齐了：剑鞘"咔"一响
  vanish(t) { this.send(this.sweep(t, this.brown, 1600, 180, 1.8, 0.35, 0.8), 0.7); this.bell(t + 0.3, 1480, 0.12); }   // 化墨散掉
  release(t, n = 1) {   // 魂走了：铃一声一声往上走，很轻（小化猫是母猫一声、小的三声）
    const f = [988, 1175, 1319, 1568];
    for (let i = 0; i < n; i++) this.bell(t + 0.35 + i * 0.32, f[i % f.length], i ? 0.09 : 0.13);
  }
  burn(t) {   // 11-05 斩到怨念那团墨：一声"嗤"，像纸烧起来（高频噪声往下扫）
    this.send(this.sweep(t + 0.04, this.white, 6000, 1500, 0.7, 0.18, 1.2), 0.5); this.bell(t + 0.5, 1480, 0.08);
  }
  sheathStill(t) {   // 送：剑在鞘里轻轻一响，没出来
    const e = this.env(t, 0.001, 0.18, 0.05, this.sfxBus); this.src(this.white, t, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", 2600, 5), e));
  }
  okuri(t) {   // 送：一声低铃，一张札落地的纸声，过一会儿再一声高的
    this.bell(t + 0.15, 740, 0.14); this.paper(t + 1.7); this.bell(t + 2.2, 1175, 0.09);
  }
  retreat(t) { this.sweep(t, this.brown, 700, 120, 1.2, 0.3, 1); }   // 沉回墨里
  tick(t) { const e = this.env(t, 0.001, 0.15, 0.03, this.sfxBus); this.src(this.white, t, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", 4000, 4), e)); }
  step(t, floor, v = 1) {
    const p = this.pan(rnd(-0.1, 0.1), this.sfxBus), n = (buf, f, q, peak, d, type = "bandpass") => {
      const e = this.env(t, 0.003, peak * v, d, p); this.src(buf, t, { offset: Math.random() * 1.5, rate: rnd(0.9, 1.1) }).connect(this.chain(this.filt(type, f * rnd(0.9, 1.1), q), e));
    };
    if (floor === "tatami") { n(this.brown, 350, 0.7, 0.8, 0.07, "lowpass"); n(this.white, 2600, 1.5, 0.05, 0.05); }   // 软的闷响 + 草席沙沙
    else if (floor === "wood") {
      n(this.brown, 500, 0.8, 0.45, 0.06, "lowpass");
      const o = this.ctx.createOscillator(); o.frequency.value = rnd(170, 230); const e = this.env(t, 0.002, 0.18 * v, 0.07, p); o.connect(e); o.start(t); o.stop(t + 0.12);
      n(this.white, 1100, 3, 0.08, 0.03);
    } else if (floor === "gravel") { for (let i = 0; i < 4; i++) { const tt = t + i * 0.012; const e = this.env(tt, 0.001, rnd(0.06, 0.12) * v, 0.03, p); this.src(this.white, tt, { offset: Math.random() }).connect(this.chain(this.filt("bandpass", rnd(2500, 4500), 3), e)); } n(this.brown, 300, 0.7, 0.25, 0.05, "lowpass"); }
    else { n(this.brown, 260, 0.7, 0.35, 0.05, "lowpass"); n(this.white, 2200, 2, 0.1, 0.03); if (floor === "wet") n(this.white, 3500, 2, 0.12, 0.12); }   // 石板（雨里多一声水溅）
  }
}

// ---- 对外 ----
let eng = null, timer = null, scene = null;
const KEY = "mononoke_tour_mute";
let muted = false; try { muted = localStorage.getItem(KEY) === "1"; } catch {}

function now() { return eng.ctx.currentTime; }
function applyScene() {
  if (!eng || !scene) return;
  const { loc, zone } = scene, t = now() + 0.05;
  eng.setMusic(DARK.includes(`${loc}.${zone}`) ? "dark" : MUSIC[loc] ? loc : "map", t);
  eng.setAmbience(pick(AMBIENCE, loc, zone, ["room"]), t);
}

export const audio = {
  get muted() { return muted; },
  get ready() { return !!eng && eng.ctx.state === "running"; },
  /** 第一次用户操作时调：建 AudioContext、开始排 BGM。之后再调只是 resume */
  unlock() {
    if (!eng) {
      const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      eng = new Engine(new AC());
      eng.master.gain.value = muted ? 0 : 0.85;
      applyScene();
      timer = setInterval(() => { if (eng.ctx.state === "running") eng.scheduleUntil(now() + 0.4); }, 100);
      document.addEventListener("visibilitychange", () => (document.hidden ? eng.ctx.suspend() : eng.ctx.resume()));
    }
    if (eng.ctx.state !== "running") eng.ctx.resume();
  },
  /** 换地点 / 区块：BGM 只在地点（或明暗）变了时换，环境声按区块换，都淡入淡出 */
  setScene(loc, zone = "") { scene = { loc, zone }; applyScene(); },
  floorOf(loc, zone) { return pick(FLOOR, loc, zone, "tatami"); },
  toggle() {
    muted = !muted; try { localStorage.setItem(KEY, muted ? "1" : "0"); } catch {}
    if (eng) { const g = eng.master.gain, t = now(); g.cancelScheduledValues(t); g.setValueAtTime(g.value, t); g.linearRampToValueAtTime(muted ? 0 : 0.85, t + 0.3); }
    return muted;
  },
  play(name, ...args) { if (!eng || eng.ctx.state !== "running") return; eng[name]?.(now() + 0.01, ...args); },
};

/**
 * 离线录一段（验收用）：OfflineAudioContext 跑同一套引擎，events 是 [[秒, 方法名, ...参数]]，返回 16 位 WAV 的 base64
 * 例：await renderDemo("sakai", "omote", 30, [[3, "hyoshigi"], [5, "slide"]])
 */
export async function renderDemo(loc, zone, secs, events = []) {
  const ctx = new OfflineAudioContext(2, Math.floor(44100 * secs), 44100), e = new Engine(ctx);
  e.setMusic(DARK.includes(`${loc}.${zone}`) ? "dark" : MUSIC[loc] ? loc : "map", 0);
  e.setAmbience(pick(AMBIENCE, loc, zone, ["room"]), 0);
  e.scheduleUntil(secs);
  for (const [t, name, ...a] of events) e[name](t, ...a);
  const buf = await ctx.startRendering();
  const L = buf.getChannelData(0), R = buf.getChannelData(1), n = L.length, dv = new DataView(new ArrayBuffer(44 + n * 4));
  const w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); dv.setUint32(4, 36 + n * 4, true); w(8, "WAVEfmt "); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
  dv.setUint32(24, 44100, true); dv.setUint32(28, 44100 * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, "data"); dv.setUint32(40, n * 4, true);
  let peak = 0, sum = 0;
  for (let i = 0; i < n; i++) { for (const [c, ch] of [[0, L], [1, R]]) { const v = Math.max(-1, Math.min(1, ch[i])); dv.setInt16(44 + i * 4 + c * 2, v * 32767, true); peak = Math.max(peak, Math.abs(v)); sum += v * v; } }
  let bin = ""; const u8 = new Uint8Array(dv.buffer); for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode(...u8.subarray(i, i + 0x8000));
  return { wav: btoa(bin), peak, rms: Math.sqrt(sum / (n * 2)) };
}
