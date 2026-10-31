// 镜头跳变诊断：无头 Chrome 打开 tour.html?loc=<地点>，停掉自动渲染循环，每个区块用固定步长逐帧跑：
//   点地面随机走（寻路）、按住 W 走（中途换 A / D、偶尔拖镜头）、原地拖一圈。
// 每帧记镜头位置和朝向；一帧里位置跳超过 0.15 米或朝向转超过 6°（60 帧/秒下）记一次"跳"，同时记当时的原因线索
// （固定机位进出、撞墙拉近距离 cur 变化、躲墙偏转 off 变化）。用法：node tools/tour_camjump.mjs <地点> [种子]
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "sakai", seed = "1"] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/cj-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9335", "--window-size=1280,720", "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9335/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 500)); return r.result?.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${loc}` });
for (let i = 0; i < 120; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(2000);
const out = await ev(`(async () => {
  const T = __tour; T.renderer.setAnimationLoop(null); T.post.render = () => {};
  let s = ${+seed} * 9301 + 49297; const R = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const zones = Object.keys(T.loc.zones || {}).length ? Object.keys(T.loc.zones) : T.loc.zones.map((z) => z.id);
  const report = [];
  const camState = () => { const c = T.cam; return { cuts: c.cuts ?? 0, cur: c.cur != null ? +c.cur.toFixed(2) : null, off: c.off ? +c.off.yaw.toFixed(2) : null }; };
  for (const zid of zones) {
    await T.enterZone(zid); T.step(5);
    const Z = T.zone, W = Z.walk, pts = [];
    for (let k = 0; k < 4000 && pts.length < 60; k++) { const x = W.x0 + R() * W.w * W.cell, z = W.z0 + R() * W.h * W.cell; if (T.col.canStand(x, z)) pts.push([x, z]); }
    const ev = { zone: zid, jumps: [], frames: 0 };
    const pd = new T.camera.position.constructor(), dir = pd.clone(), d2 = pd.clone();
    let prev = null, prevDir = null, prevSt = null, phase = "";
    const sample = () => {
      T.step(1); ev.frames++;
      const p = T.camera.position.clone(); T.camera.getWorldDirection(d2);
      const st = camState();
      if (prev) {
        const dp = p.distanceTo(prev), da = Math.acos(Math.min(1, d2.dot(prevDir))) * 180 / Math.PI;
        if (dp > 0.15 || da > 6) ev.jumps.push({ phase, dp: +dp.toFixed(2), da: +da.toFixed(1), from: prevSt, to: st, pl: [+T.player.position.x.toFixed(2), +T.player.position.z.toFixed(2)] });
      }
      prev = p; prevDir = d2.clone(); prevSt = st;
    };
    // 1. 点地面走
    for (let k = 0; k < 6 && pts.length; k++) {
      phase = "tap" + k; const [x, z] = pts[Math.floor(R() * pts.length)];
      T.walkTo(x, z); let still = 0, lp = T.player.position.clone();
      for (let f = 0; f < 900 && still < 20; f++) { sample(); still = T.player.position.distanceTo(lp) < 1e-4 ? still + 1 : 0; lp.copy(T.player.position); }
    }
    // 2. 按住 W 走，中途换方向、拖镜头
    for (let k = 0; k < 4; k++) {
      phase = "W" + k; T.keys.clear(); T.keys.add("KeyW"); if (R() < 0.5) T.keys.add(R() < 0.5 ? "KeyA" : "KeyD");
      const turnRate = (R() - 0.5) * 0.03;
      for (let f = 0; f < 240; f++) { if (f % 60 < 20) T.cam.turn(turnRate, 0); sample(); }
      T.keys.clear();
    }
    // 3. 原地拖一圈
    phase = "spin"; for (let f = 0; f < 200; f++) { T.cam.turn(0.032, 0); sample(); }
    report.push(ev);
  }
  return report;
})()`);
for (const z of out || []) {
  const by = {}; for (const j of z.jumps) { const k = (j.from.cuts !== j.to.cuts ? "切镜头" : j.from.cur !== null && Math.abs(j.to.cur - j.from.cur) > 0.1 ? "撞墙拉近" : "其他"); by[k] = (by[k] || 0) + 1; }
  const hard = z.jumps.filter((j) => j.from.cuts === j.to.cuts && (j.dp > 0.6 || j.da > 6)).length;   // 硬跳：不是有意切镜头，却一帧跳 0.6 米以上或转 6° 以上，就是用户看到的"闪"
  console.log(`${loc}.${z.zone}  帧 ${z.frames}  跳 ${z.jumps.length}  硬跳 ${hard}`, JSON.stringify(by));
  if (process.env.V) for (const j of z.jumps.slice(0, +process.env.V)) console.log("   ", JSON.stringify(j));
}
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
