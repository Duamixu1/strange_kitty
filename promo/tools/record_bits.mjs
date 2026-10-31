// 快剪用的几段过程镜头：无头 Chrome 录屏，和 record_game.mjs 同一套做法（CDP screencast → frames → frames_to_mp4.py）。
//   node promo/tools/record_bits.mjs <输出目录> shader|code
// shader：character.html 里药郎从"Tripo 原始着色"开始，依次打开平涂、描边、和纸，最后横斩
// code：  game.js 在一个代码编辑器样式的页面里往下滚（页面由本脚本现生成，代码高亮用 cdnjs 的 highlight.js）
// doc <md 文件> <起行> <止行>：把一段 Markdown（分工表、待办表）渲染成文档页，慢慢往下滚
// url <网址>：打开网页（比如 GitHub 仓库页），停一会儿再慢慢往下滚
import { spawn } from "node:child_process";
import fs from "node:fs"; import path from "node:path"; import os from "node:os";

const OUT = path.resolve(process.argv[2]); const MODE = process.argv[3];
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const W = 1920, H = 1080, PORT = 9335;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
fs.mkdirSync(path.join(OUT, "frames"), { recursive: true });
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "bits-"));
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`,
  `--window-size=${W},${H + 87}`, "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "--hide-scrollbars", "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
let u; for (let i = 0; i < 50 && !u; i++) { try { u = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === "page")?.webSocketDebuggerUrl; } catch {} await sleep(200); }
const ws = new WebSocket(u); await new Promise((r) => (ws.onopen = r));
let seq = 0; const pend = new Map(); const frames = [], markers = []; let n = 0;
ws.onmessage = (m) => { const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) { pend.get(d.id)(d.result); pend.delete(d.id); }
  else if (d.method === "Page.screencastFrame") { send("Page.screencastFrameAck", { sessionId: d.params.sessionId });
    const f = `${String(n++).padStart(6, "0")}.jpg`; fs.writeFileSync(path.join(OUT, "frames", f), Buffer.from(d.params.data, "base64")); frames.push({ f, t: d.params.metadata.timestamp }); } };
const send = (method, params = {}) => new Promise((r) => { const id = ++seq; pend.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.value;
const key = async (code, k) => { await send("Input.dispatchKeyEvent", { type: "keyDown", code, key: k || code }); await sleep(50); await send("Input.dispatchKeyEvent", { type: "keyUp", code, key: k || code }); };
const mark = (name) => markers.push({ name, t: Date.now() / 1000 });
const rec = () => send("Page.startScreencast", { format: "jpeg", quality: 90, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
await send("Page.enable");

if (MODE === "shader") {
  await send("Page.navigate", { url: "http://[::1]:5173/character.html?model=processed/kusuriuri_v2_posed_layered.glb" });
  for (let i = 0; i < 300; i++) { if (await js(`!!document.getElementById('status') && !document.getElementById('status').textContent.includes('加载')`)) break; await sleep(200); }
  await sleep(3000);
  await js(`document.getElementById('hud').style.display='none'; document.querySelectorAll('#anim-hud,.anim-hud').forEach(e=>e.style.display='none')`);
  await key("Digit2", "2"); await key("KeyT", "t"); await key("KeyO", "o"); await key("KeyP", "p");
  await sleep(1200);
  await rec(); await sleep(400);
  mark("raw"); await sleep(1100);
  await key("KeyT", "t"); mark("toon"); await sleep(1000);
  await key("KeyO", "o"); mark("outline"); await sleep(1000);
  await key("KeyP", "p"); mark("paper"); await sleep(1200);
  const slot = await js(`(()=>{const t=document.getElementById('anims')?.textContent||''; const m=t.match(/([0-9=\\-\\[\\]\\\\])=([^ ]*(slash|exorcise)[^ ]*)/); return m?m[1]:null;})()`);
  console.log("横斩键", slot, await js(`document.getElementById('anims')?.textContent`));
  if (slot) { await key("Digit4", "4"); await key(`Digit${slot}`, slot); mark("slash"); await sleep(5500); }
} else if (MODE === "doc" || MODE === "url") {
  let target;
  if (MODE === "doc") {
    const [mdPath, a, b] = process.argv.slice(4);
    const md = fs.readFileSync(path.resolve(mdPath), "utf8").split("\n").slice(+a - 1, +b).join("\n").replace(/\]\(#local_[^)]*\)/g, "]()");
    const html = `<!doctype html><meta charset=utf-8><script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>body{margin:0;background:#f6f3ec;font:24px/1.7 -apple-system,"PingFang SC",sans-serif;color:#2b2838;overflow:hidden}
#doc{max-width:1640px;margin:0 auto;padding:60px 80px;will-change:transform}
h1,h2,h3{font-family:"Songti SC",serif;color:#322D48} h3{font-size:34px;border-bottom:2px solid #E6667A;padding-bottom:6px}
table{border-collapse:collapse;width:100%;font-size:20px;background:#fff} th,td{border:1px solid #d9d2c3;padding:10px 14px;vertical-align:top} th{background:#efe6d6}
code{background:#efe6d6;padding:1px 6px;border-radius:4px;font-size:.9em} a{color:#B42A47;text-decoration:none}</style>
<div id=doc></div><script>document.getElementById('doc').innerHTML=marked.parse(${JSON.stringify(md)});</script>`;
    target = "file://" + path.join(OUT, "doc.html"); fs.writeFileSync(path.join(OUT, "doc.html"), html);
  } else target = process.argv[4];
  await send("Page.navigate", { url: target }); await sleep(MODE === "url" ? 6000 : 2500);
  await rec(); await sleep(300); mark("scroll"); await sleep(1500);
  await js(`new Promise(r=>{const t0=performance.now(), D=6000, Y=${MODE === "url" ? 700 : 900}; const y0=scrollY; const el=document.getElementById('doc');
    (function f(t){const u=Math.min(1,(t-t0)/D); const e=u<.5?2*u*u:1-(-2*u+2)**2/2; if(el) el.style.transform='translateY('+(-Y*e)+'px)'; else scrollTo(0,y0+Y*e); u<1?requestAnimationFrame(f):r();})(t0);})`);
  await sleep(1200);
} else if (MODE === "code") {
  const src = fs.readFileSync(path.join(ROOT, "web/src/game.js"), "utf8").split("\n").slice(160, 330).join("\n");
  const esc = src.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const html = `<!doctype html><meta charset=utf-8><link rel=stylesheet href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>body{margin:0;background:#1e2127;font:22px/1.55 Menlo,monospace;overflow:hidden}
.tabs{height:46px;background:#21252b;display:flex;align-items:flex-end;padding-left:16px}
.tab{background:#282c34;color:#d7dae0;font:16px -apple-system,sans-serif;padding:12px 22px;border-radius:6px 6px 0 0}
.tab.dim{background:none;color:#7f848e}
#wrap{position:absolute;top:46px;bottom:0;left:0;right:0;overflow:hidden;background:#282c34}
#code{display:flex;padding:18px 0;will-change:transform}
.ln{color:#495162;text-align:right;padding:0 24px 0 18px;user-select:none;white-space:pre}
pre{margin:0} code.hljs{background:none;padding:0}</style>
<div class=tabs><div class=tab>game.js</div><div class="tab dim">logic.js</div><div class="tab dim">cameras.json</div></div>
<div id=wrap><div id=code><div class=ln>${src.split("\n").map((_, i) => i + 161).join("\n")}</div><pre><code class="language-javascript">${esc}</code></pre></div></div>
<script>hljs.highlightAll();</script>`;
  const f = path.join(OUT, "code.html"); fs.writeFileSync(f, html);
  await send("Page.navigate", { url: "file://" + f }); await sleep(2500);
  await rec(); await sleep(300); mark("scroll");
  await js(`new Promise(r=>{const el=document.getElementById('code'); const t0=performance.now(); const D=3200, Y=1500;
    (function f(t){const u=Math.min(1,(t-t0)/D); const e=u<.5?2*u*u:1-(-2*u+2)**2/2; el.style.transform='translateY('+(-Y*e)+'px)'; u<1?requestAnimationFrame(f):r();})(t0);})`);
  await sleep(500);
}
await send("Page.stopScreencast"); await sleep(300);
fs.writeFileSync(path.join(OUT, "frames.json"), JSON.stringify(frames));
fs.writeFileSync(path.join(OUT, "markers.json"), JSON.stringify(markers));
console.log(MODE, "帧数", frames.length);
ws.close(); chrome.kill(); await sleep(800); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {} process.exit(0);
