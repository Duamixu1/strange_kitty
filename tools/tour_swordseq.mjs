// 拔剑逐帧：无头 Chrome 打开 tour.html?loc=<地点>&zone=<区块>，按 X，正面每 1/15 秒存一帧（拼视频用），
// 每 0.4 秒再从侧面（镜头绕到药郎右边 90°）存一帧（看挥剑轨迹、穿模）。用法：node tools/tour_swordseq.mjs <地点> <区块> <输出目录>
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "wanya", zone = "ozashiki", out = "."] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/sq-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9341", "--window-size=720,720", "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9341/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 300)); return r.result?.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${loc}&zone=${zone}` });
for (let i = 0; i < 120; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(3000);
await ev(`(()=>{const T=__tour;T.renderer.setAnimationLoop(null);document.querySelector("#help").style.display="none";document.querySelector("#tags").style.display="none";T.cam.dist=3.2;T.step(60);window.dispatchEvent(new KeyboardEvent("keydown",{code:"KeyX"}));T.step(1,0);return 1})()`);
const shot = async (f) => { const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 80 }); fs.writeFileSync(f, Buffer.from(r.data, "base64")); };
const pad = (n) => String(n).padStart(3, "0");
for (let k = 0; k <= 150; k++) {
  await shot(`${out}/front_${pad(k)}.jpg`);
  if (k % 6 === 0) {   // 0.4 秒一次侧面
    await ev(`(()=>{const T=__tour;T._y=T.cam.yaw;T.cam.yaw+=Math.PI/2;T.step(1,0);return 1})()`);
    await shot(`${out}/side_${pad(k / 6)}.jpg`);
    await ev(`(()=>{const T=__tour;T.cam.yaw=T._y;T.step(1,0);return 1})()`);
  }
  await ev(`__tour.step(4)`);   // 4 帧 = 1/15 秒
}
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
