// 视频用的声音素材：用游览版自己的声音引擎（web/src/tour/audio.js，全部现场合成）离线渲染成 WAV。
// 和 tools/tour_audio_render.mjs 的区别：这里音乐、环境声、音效分开渲染（剪辑时分轨混），所以要拿到 Engine 类本身——
// 把 audio.js 的源码取下来、末尾补一句 export，用 Blob URL 导入（不改游戏代码）。
// 用法：node promo/tools/render_audio.mjs <输出目录> <任务.json>
//   任务每条：{ name, secs, music?: "dark"|"sakai"|"wanya"|"ooku"|"map", amb?: ["rain", ...], events?: [[秒, "方法名", ...参数]] }
import { spawn } from "node:child_process";
import fs from "node:fs";
const [out, jobsFile] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsFile, "utf8"));
fs.mkdirSync(out, { recursive: true });
const PORT = 9362, prof = fs.mkdtempSync("/tmp/ra2-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, `--remote-debugging-port=${PORT}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await cdp("Page.enable");
await cdp("Page.navigate", { url: "http://[::1]:5173/kit_compare.html?mode=kit" });   // 只要同源页面，随便一个轻的
await sleep(2500);
const setup = await cdp("Runtime.evaluate", { awaitPromise: true, returnByValue: true, expression: `(async () => {
  const src = await (await fetch("/src/tour/audio.js")).text();
  const url = URL.createObjectURL(new Blob([src + "\\nexport { Engine };"], { type: "text/javascript" }));
  window.__A = await import(url);
  return Object.keys(window.__A).join(",");
})()` });
console.log("模块导出：", setup.result?.value ?? JSON.stringify(setup).slice(0, 300));
for (const J of jobs) {
  const r = await cdp("Runtime.evaluate", { awaitPromise: true, returnByValue: true, expression: `(async () => {
    const J = ${JSON.stringify(J)};
    const ctx = new OfflineAudioContext(2, Math.floor(44100 * J.secs), 44100), e = new __A.Engine(ctx);
    if (J.music) e.setMusic(J.music, 0);
    if (J.amb) e.setAmbience(J.amb, 0);
    e.scheduleUntil(J.secs);
    for (const [t, name, ...a] of (J.events || [])) e[name](t, ...a);
    const buf = await ctx.startRendering();
    const L = buf.getChannelData(0), R = buf.getChannelData(1), n = L.length, dv = new DataView(new ArrayBuffer(44 + n * 4));
    const w = (o, s) => [...s].forEach((c, i) => dv.setUint8(o + i, c.charCodeAt(0)));
    w(0, "RIFF"); dv.setUint32(4, 36 + n * 4, true); w(8, "WAVEfmt "); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 2, true);
    dv.setUint32(24, 44100, true); dv.setUint32(28, 44100 * 4, true); dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); w(36, "data"); dv.setUint32(40, n * 4, true);
    let peak = 0;
    for (let i = 0; i < n; i++) for (const [c, ch] of [[0, L], [1, R]]) { const v = Math.max(-1, Math.min(1, ch[i])); dv.setInt16(44 + i * 4 + c * 2, v * 32767, true); peak = Math.max(peak, Math.abs(v)); }
    let bin = ""; const u8 = new Uint8Array(dv.buffer); for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode(...u8.subarray(i, i + 0x8000));
    return { wav: btoa(bin), peak };
  })()` });
  const v = r.result?.value;
  if (!v?.wav) { console.log(J.name, "失败", JSON.stringify(r.exceptionDetails?.exception?.description ?? r).slice(0, 400)); continue; }
  fs.writeFileSync(`${out}/${J.name}.wav`, Buffer.from(v.wav, "base64"));
  console.log(J.name, "peak", v.peak.toFixed(3));
}
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
