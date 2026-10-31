// 离线录声音样本：无头 Chrome 打开开发服务器，调 audio.js 的 renderDemo 录成 WAV。用法：node tools/tour_audio_render.mjs <目录> '[["名字","地点","区块",秒数,[[秒,"音效名",参数]]]]'
import { spawn } from "node:child_process";
import fs from "node:fs";
const out = process.argv[2];
const prof = fs.mkdtempSync("/tmp/ra-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9334", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9334/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await cdp("Page.enable");
await cdp("Page.navigate", { url: "http://[::1]:5173/tour.html" });
await sleep(3000);
const jobs = JSON.parse(process.argv[3]);
for (const [name, loc, zone, secs, events] of jobs) {
  const r = await cdp("Runtime.evaluate", { expression: `import("/src/tour/audio.js").then(m => m.renderDemo(${JSON.stringify(loc)}, ${JSON.stringify(zone)}, ${secs}, ${JSON.stringify(events)}))`, awaitPromise: true, returnByValue: true });
  const v = r.result?.value;
  if (!v) { console.log(name, "FAIL", JSON.stringify(r).slice(0, 400)); continue; }
  fs.writeFileSync(`${out}/${name}.wav`, Buffer.from(v.wav, "base64"));
  console.log(name, "peak", v.peak.toFixed(3), "rms", v.rms.toFixed(4));
}
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
