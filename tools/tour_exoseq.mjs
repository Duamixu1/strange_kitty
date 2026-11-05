// 退魔收场逐时刻截图（11-05，docs/19 第十节"斩与送"）：无头 Chrome 打开 tour.html?loc=<地点>&zone=<区块>，叫出指定物怪，
// 自动闪避、投札钉齐三张，按 X，然后在给的几个时刻各拍一张，最后拼一张总览。
// 用法：node tools/tour_exoseq.mjs <地点> <区块> <物怪 id> <输出前缀> [秒,秒,...] [full]
//   full：清掉"退过魔"的记录，拔剑走完整 10 秒版（默认短版）
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "sakai", zone = "ozashiki", mon = "bakeneko", out = "/tmp/exo", times = "0.5,1.5,2.5,3.5,4.5,6", full] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/ex-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9343", "--window-size=1280,800", "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9343/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) console.log("ERR", JSON.stringify(r.exceptionDetails).slice(0, 400)); return r.result?.value; };
await cdp("Page.enable");
await cdp("Page.navigate", { url: `http://[::1]:5173/tour.html?loc=${loc}&zone=${zone}&mononoke=off` });
for (let i = 0; i < 120; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(3000);
const res = await ev(`(async()=>{const T=__tour,E=T.enc;T.renderer.setAnimationLoop(null);
  localStorage.setItem("mononoke_tour_tut","1"); ${full ? 'localStorage.removeItem("mononoke_tour_exo");' : 'localStorage.setItem("mononoke_tour_exo","1");'}
  for (const s of ["#help","#tags"]) { const e=document.querySelector(s); if (e) e.style.display="none"; }
  T.card.close(); await E.preload("${mon}"); if (!E.start(true,"${mon}")) return "找不到出生点";
  for (let i=0;i<900&&E.state!=="fight";i++) T.step(1);
  for (let i=0;i<3600&&E.state==="fight";i++){const d=E.debug; if(d.sub==="charge"&&d.subT>0.55&&d.subT<=0.57)E.act("dodge"); if(d.sub==="land"&&i%10===0)E.act("throw"); T.step(1);}
  T.step(40); const r=E.state+" 钉 "+E.pins+" 钮「"+(document.querySelector("#pad .b-sword")?.textContent)+"」";
  window.dispatchEvent(new KeyboardEvent("keydown",{code:"KeyX"})); window.dispatchEvent(new KeyboardEvent("keyup",{code:"KeyX"})); T.step(1,0);
  return r;})()`);
console.log(mon, res);
const shot = async (f) => { const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 82 }); fs.writeFileSync(f, Buffer.from(r.data, "base64")); };
let t = 0; const files = [];
for (const at of times.split(",").map(Number)) {
  const n = Math.max(0, Math.round((at - t) * 60)); t += n / 60;
  const st = await ev(`(()=>{const T=__tour;for(let i=0;i<${n};i++)T.step(1);return T.enc.state+" "+T.P.currentName})()`);
  const f = `${out}_${at}s.jpg`; await shot(f); files.push(f); console.log(at, st);
}
const end = await ev(`(()=>{const T=__tour;for(let i=0;i<900&&T.enc.state!=="idle";i++)T.step(1);return T.enc.state+" 卡："+(T.card.isOpen?document.querySelector("#card .title")?.textContent:"没开")})()`);
console.log("结束", end);
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
