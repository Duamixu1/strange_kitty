// 帧耗时：无头 Chrome 打开 tour.html?loc=<地点>，每个区块按住 W 走 3 秒（真渲染），量每帧镜头更新、整帧的耗时，
// 再查药郎在不在画面里（胸口投影到屏幕上）。用法：node tools/tour_perf.mjs <地点>
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "wanya"] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/pf-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9336", "--window-size=1600,900", "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9336/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result?.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${loc}` });
for (let i = 0; i < 120; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(2000);
const out = await ev(`(async () => {
  const T = __tour; T.renderer.setAnimationLoop(null);
  const zones = Object.keys(T.loc.zones || {}).length ? Object.keys(T.loc.zones) : T.loc.zones.map((z) => z.id);
  const cam0 = T.cam, res = [];
  const vis = () => { const p = T.player.position, v = new p.constructor(p.x, p.y + 1.0, p.z).project(T.camera), h = new p.constructor(p.x, p.y + 1.7, p.z).project(T.camera); return Math.abs(v.x) < 0.95 && v.y > -0.95 && v.y < 0.95 && v.z < 1 && h.y > -0.9; };
  for (const zid of zones) {
    await T.enterZone(zid); T.step(3);
    const startVis = vis();
    let camMs = 0, frameMs = 0, n = 0, hidden = 0;
    const c = T.cam, up = c.update.bind(c);
    c.update = (...a) => { const t0 = performance.now(); up(...a); camMs += performance.now() - t0; };
    T.keys.add("KeyW");
    for (let f = 0; f < 180; f++) { const t0 = performance.now(); T.step(1); T.renderer.getContext().finish(); frameMs += performance.now() - t0; n++; if (!vis()) hidden++; if (f === 90) { T.keys.delete("KeyW"); T.keys.add("KeyD"); } }
    T.keys.clear(); c.update = up;
    res.push({ zone: zid, frameMs: +(frameMs / n).toFixed(1), camMs: +(camMs / n).toFixed(2), startVis, hiddenFrames: hidden });
  }
  return res;
})()`);
for (const r of out || []) console.log(`${loc}.${r.zone}  每帧 ${r.frameMs} ms（镜头 ${r.camMs} ms）  进区块时看得见药郎 ${r.startVis}  走动中看不见 ${r.hiddenFrames}/180 帧`);
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
