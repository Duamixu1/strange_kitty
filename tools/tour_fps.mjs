// 实际帧率：无头 Chrome 按真实循环跑（不停自动渲染），2 倍像素大窗口，按一下键开声音，按住 W 走，
// 记 requestAnimationFrame 间隔的中位数、95%、超过 50 毫秒的帧数。用法：node tools/tour_fps.mjs <地点> [区块] [宽] [高]
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "wanya", zone = "", W = "1800", H = "1000"] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/fps-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9337", `--window-size=${W},${H}`, "--force-device-scale-factor=2", "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "--autoplay-policy=no-user-gesture-required", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9337/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result?.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${loc}${zone ? "&zone=" + zone : ""}` });
for (let i = 0; i < 120; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(3000);
await cdp("Input.dispatchKeyEvent", { type: "keyDown", code: "KeyQ", key: "q" }); await cdp("Input.dispatchKeyEvent", { type: "keyUp", code: "KeyQ", key: "q" });
const r = await ev(`new Promise((res) => {
  const T = __tour, d = [], t0 = performance.now(); let last = t0;
  T.keys.add("KeyW");
  const tick = (now) => { d.push(now - last); last = now; if (now - t0 < 6000) requestAnimationFrame(tick); else { T.keys.clear(); d.sort((a, b) => a - b); res({ n: d.length, p50: d[d.length >> 1], p95: d[Math.floor(d.length * 0.95)], max: d[d.length - 1], long: d.filter((x) => x > 50).length, audio: T.audio.ready, px: [T.renderer.domElement.width, T.renderer.domElement.height] }); } };
  requestAnimationFrame(tick);
})`);
console.log(`${loc}${zone ? "." + zone : ""}  ${r.px.join("×")} 像素  ${r.n} 帧/6 秒  中位 ${r.p50.toFixed(1)} ms  95% ${r.p95.toFixed(1)} ms  最长 ${r.max.toFixed(0)} ms  超 50ms ${r.long} 帧  声音 ${r.audio}`);
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
