// 游览版视频素材录制：无头 Chrome（Metal）打开 tour.html，按镜头表一条条摆药郎、走路、按键、运镜，逐帧截图。
// 用法：node promo/tools/record_tour.mjs <镜头表.json> [--only 名字,名字] [--probe]
//   --probe：每条只拍开头、中间、结尾三张（看构图用），存到 promo/raw/tour_v3/_probe/
//   正式：每条存 30 fps 的帧到 promo/raw/tour_v3/<名字>/f_0000.jpg，再用 frames_to_clip 合成 <名字>.mp4
// 镜头表每条：
//   { name, loc, zone, dur, player: [x, z, yaw], fov?, ui?: false, cutout?: true,
//     cam: "game" | { keys: [[秒, [x,y,z], [x,y,z] | "player"], ...] }   （keys 之间 smoothstep 插值）
//     events: [[秒, "walk", x, z] | [秒, "run", x, z] | [秒, "key", "KeyX"] | [秒, "view", n] | [秒, "anim", 名字] | [秒, "yaw", 弧度]
//              | [秒, "follow", { yaw, pitch, dist }]（改跟随镜头参数） | [秒, "hold"/"release", 键名]
//              | 手机：[秒, "drag", 选择器或 [x,y], dx, dy, 按住秒数]（手指按下、0.25 秒拖到偏移处、按住、松开；摇杆用）| [秒, "tap", 选择器或 [x,y]] }
//   mobile: true 的条用手机横屏（844×390，2 倍像素，触屏 + coarse 指针），保留按钮栏和摇杆，手指位置画一个半透明圆点
// 时间按游戏帧推（每帧 2 个 1/60 秒），和真实时间无关，所以慢机器上也不会掉帧。泼溅地点每帧多等一点，给 Spark 排序。
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const listFile = args[0];
const only = args.includes("--only") ? args[args.indexOf("--only") + 1].split(",") : null;
const probe = args.includes("--probe");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const OUT = path.join(ROOT, "promo/raw/tour_v3");
const FPS = 30, W = 1920, H = 1080, PORT = 9351;
const MW = 844, MH = 390;
const shots = JSON.parse(fs.readFileSync(listFile, "utf8")).filter((s) => !s.name.startsWith("_") && (!only || only.includes(s.name)));

const prof = fs.mkdtempSync("/tmp/rt-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, `--remote-debugging-port=${PORT}`, `--window-size=${W},${H}`, "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 40; i++) { try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result?.value; };
const shot = async (f) => { const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 90 }); fs.writeFileSync(f, Buffer.from(r.data, "base64")); };
await cdp("Page.enable");
async function setMode(mobile) {
  await cdp("Emulation.setDeviceMetricsOverride", mobile ? { width: MW, height: MH, deviceScaleFactor: 2, mobile: true } : { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: !!mobile, maxTouchPoints: 5 });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "pointer", value: mobile ? "coarse" : "fine" }] });
}
// 手指：id → [x, y]；每次触摸事件都要带上所有按着的手指
const fingers = new Map();
const touchSend = (type) => cdp("Input.dispatchTouchEvent", { type, touchPoints: [...fingers].map(([i, [x, y]]) => ({ x, y, id: i })) });
const where = async (t) => (Array.isArray(t) ? t : ev(`(() => { const r = document.querySelector(${JSON.stringify(t)}).getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`));

// 页面里的辅助：藏界面、摆人、插值运镜
const HELPERS = `(() => {
  const T = __tour;
  T.renderer.setAnimationLoop(null);
  const css = document.createElement("style");
  css.textContent = window.__rtMobile ? "#help,#tags,#status,#toast,#loading,#map,#fx{display:none!important}" : "#help,#tags,#prompt,#status,#snd,#pad,#toast,#loading,#map,#fx{display:none!important}";
  if (window.__rtMobile) {   // 手指圆点：录屏里看得见按在哪
    const dots = new Map();
    const dot = () => { const d = document.createElement("div"); Object.assign(d.style, { position: "fixed", width: "46px", height: "46px", margin: "-23px 0 0 -23px", borderRadius: "50%", background: "rgba(241,233,218,.45)", border: "2px solid rgba(50,45,72,.7)", pointerEvents: "none", zIndex: 99999 }); document.body.appendChild(d); return d; };
    addEventListener("pointerdown", (e) => { const d = dot(); dots.set(e.pointerId, d); d.style.left = e.clientX + "px"; d.style.top = e.clientY + "px"; }, true);
    addEventListener("pointermove", (e) => { const d = dots.get(e.pointerId); if (d) { d.style.left = e.clientX + "px"; d.style.top = e.clientY + "px"; } }, true);
    for (const t of ["pointerup", "pointercancel"]) addEventListener(t, (e) => { dots.get(e.pointerId)?.remove(); dots.delete(e.pointerId); }, true);
  }
  document.head.appendChild(css);
  const V = T.camera.position.constructor;
  const ss = (x) => x * x * (3 - 2 * x);
  window.__rt = {
    place(x, z, yaw) { T.player.position.x = x; T.player.position.z = z; T.player.position.y = T.col.floorY(x, z) ?? 0; T.player.rotation.y = yaw; },
    camAt(keys, t) {
      let i = 0; while (i < keys.length - 2 && t > keys[i + 1][0]) i++;
      const [t0, p0, l0] = keys[i], [t1, p1, l1] = keys[Math.min(i + 1, keys.length - 1)];
      const u = t1 > t0 ? ss(Math.max(0, Math.min(1, (t - t0) / (t1 - t0)))) : 0;
      const P = T.player.position, pl = (l) => (l === "player" ? [P.x, P.y + 1.25, P.z] : l);
      const a = pl(l0), b = pl(l1);
      T.camera.position.set(...p0.map((v, k) => v + (p1[k] - v) * u));
      T.camera.lookAt(new V(...a.map((v, k) => v + (b[k] - v) * u)));
      T.camera.updateMatrixWorld();
    },
    cutout(on) { T.scene.traverse((o) => { const u = o.material?.uniforms?.uCutout; if (u) u.value = on ? 1 : 0; }); },
  };
  return 1;
})()`;

let curLoc = null, curZone = null, curMobile = null;
fs.mkdirSync(path.join(OUT, "_probe"), { recursive: true });
for (const S of shots) {
  const splat = S.loc === "ooku";
  if (!!S.mobile !== curMobile) { await setMode(!!S.mobile); curMobile = !!S.mobile; curLoc = null; }
  if (S.loc !== curLoc) {
    await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${S.loc}&zone=${S.zone}` });
    for (let i = 0; i < 180; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
    if (splat) await ev("Promise.all(__tour.splats.map((m) => m.initialized))");
    await sleep(splat ? 6000 : 2500);
    await ev(`window.__rtMobile = ${!!S.mobile}`);
    await ev(HELPERS);
    curLoc = S.loc; curZone = S.zone;
  }
  if (S.zone !== curZone) { await ev(`__tour.enterZone(${JSON.stringify(S.zone)}).then(() => 1)`); curZone = S.zone; await sleep(500); }
  await ev(`document.getElementById("card").style.visibility = ${S.ui ? '"visible"' : '"hidden"'}`);
  const [px, pz, pyaw] = S.player;
  await ev(`(() => { const T = __tour; T.keys.clear(); __rt.place(${px}, ${pz}, ${pyaw}); T.P.play("idle", 0); __rt.cutout(${S.cutout ?? false}); ${S.fov ? `T.camera.fov = ${S.fov}; T.camera.updateProjectionMatrix();` : ""} T.step(${S.settle ?? 45}); return 1; })()`);
  if (splat) await sleep(1500);
  const n = Math.round(S.dur * FPS);
  const evs = (S.events || []).slice().sort((a, b) => a[0] - b[0]);
  const dir = path.join(OUT, S.name);
  if (!probe) { fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true }); }
  const probeAt = new Set([0, Math.floor(n / 2), n - 1]);
  let ei = 0;
  const drags = [];   // 进行中的拖动：{ id, x0, y0, dx, dy, t0, hold }
  for (let f = 0; f < n; f++) {
    const t = f / FPS;
    for (const d of drags.slice()) {   // 推进拖动：0.25 秒拖到位，按住到 t0 + hold 松开
      const u = Math.min(1, (t - d.t0) / 0.25);
      fingers.set(d.id, [d.x0 + d.dx * u, d.y0 + d.dy * u]);
      if (t >= d.t0 + d.hold) { fingers.delete(d.id); drags.splice(drags.indexOf(d), 1); await touchSend("touchEnd"); }
      else await touchSend("touchMove");
    }
    while (ei < evs.length && evs[ei][0] <= t + 1e-6) {
      const [, kind, ...a] = evs[ei++];
      if (kind === "walk" || kind === "run") await ev(`(() => { __tour.walkTo(${a[0]}, ${a[1]}, null, 0.15); ${kind === "run" ? '__tour.keys.add("ShiftLeft");' : ""} return 1; })()`);
      if (kind === "key") await ev(`(() => { window.dispatchEvent(new KeyboardEvent("keydown", { code: ${JSON.stringify(a[0])} })); window.dispatchEvent(new KeyboardEvent("keyup", { code: ${JSON.stringify(a[0])} })); return 1; })()`);
      if (kind === "hold") await ev(`(__tour.keys.add(${JSON.stringify(a[0])}), 1)`);
      if (kind === "release") await ev(`(__tour.keys.delete(${JSON.stringify(a[0])}), 1)`);
      if (kind === "view") await ev(`(__tour.openView(${a[0]}), 1)`);
      if (kind === "anim") await ev(`(__tour.P.play(${JSON.stringify(a[0])}, 0.4), 1)`);
      if (kind === "drag") { const [x0, y0] = await where(a[0]); const d = { id: 10 + drags.length + f % 7, x0, y0, dx: a[1], dy: a[2], t0: t, hold: a[3] }; fingers.set(d.id, [x0, y0]); await touchSend("touchStart"); drags.push(d); }
      if (kind === "tap") { const [x, y] = await where(a[0]); fingers.set(99, [x, y]); await touchSend("touchStart"); await ev("(__tour.step(2), 1)"); fingers.delete(99); await touchSend("touchEnd"); }
      if (kind === "follow") await ev(`(Object.assign(__tour.cam, ${JSON.stringify(a[0])}), 1)`);
      if (kind === "yaw") await ev(`(__tour.player.rotation.y = ${a[0]}, 1)`);
    }
    const camExpr = S.cam && S.cam !== "game" ? `__rt.camAt(${JSON.stringify(S.cam.keys)}, ${t}); __tour.post.render();` : "";
    await ev(`(() => { __tour.step(2); ${camExpr} return 1; })()`);
    if (splat) await sleep(25);
    if (probe) { if (probeAt.has(f)) await shot(path.join(OUT, "_probe", `${S.name}_${f}.jpg`)); }
    else await shot(path.join(dir, `f_${String(f).padStart(4, "0")}.jpg`));
  }
  console.log(S.name, probe ? "probe" : `${n} 帧`);
  if (!probe) {
    const ff = execFileSync("uv", ["run", "--with", "imageio-ffmpeg", "python", "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"]).toString().trim();
    execFileSync(ff, ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", path.join(dir, "f_%04d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", path.join(OUT, `${S.name}.mp4`)]);
  }
}
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
