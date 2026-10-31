// 探案版实机录屏：无头 Chrome（Metal）打开 game.html，脚本自动从推门玩到结果卡，CDP screencast 逐帧存图 + 镜头时间点。
// 用法：dev 服务器先开着（[::1]:5173），然后
//   node promo/tools/record_game.mjs <输出目录> [--ending a|b] [--probe]
// --probe 只玩不录，打印每一步目标在屏幕上的位置，用来调脚本。
// 输出：<目录>/frames/*.jpg、frames.json（每帧时间戳）、markers.json（镜头名 → 时间）。
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const OUT = path.resolve(process.argv[2] || "rec");
const ENDING = process.argv.includes("--ending") ? process.argv[process.argv.indexOf("--ending") + 1] : "a";
const PROBE = process.argv.includes("--probe");
const W = 1920, H = 1080, PORT = 9333;
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

fs.mkdirSync(path.join(OUT, "frames"), { recursive: true });
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "rec-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, `--window-size=${W},${H + 87}`,
  "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
process.on("exit", () => { try { chrome.kill(); } catch {} });

let ws, seq = 0;
const pending = new Map(), handlers = {};
async function connect() {
  for (let i = 0; i < 50; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const p = l.find((t) => t.type === "page"); if (p) return p.webSocketDebuggerUrl; } catch {}
    await sleep(200);
  }
  throw new Error("chrome 没起来");
}
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
async function js(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
}
async function waitFor(expr, ms = 30000, label = expr) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { if (await js(expr)) return true; await sleep(100); }
  throw new Error("等太久：" + label);
}

// ---- 录帧 ----
const frames = [], markers = [];
let frameN = 0;
handlers["Page.screencastFrame"] = (p) => {
  send("Page.screencastFrameAck", { sessionId: p.sessionId });
  if (PROBE) return;
  const f = `${String(frameN++).padStart(6, "0")}.jpg`;
  fs.writeFileSync(path.join(OUT, "frames", f), Buffer.from(p.data, "base64"));
  frames.push({ f, t: p.metadata.timestamp });
};
const mark = (name) => { markers.push({ name, t: Date.now() / 1000 }); console.log(`[${(Date.now() / 1000).toFixed(1)}] ▶ ${name}`); };

// ---- 鼠标：页面里画一个假光标（无头截图没有系统光标），移动时平滑插值 ----
let mx = W * 0.5, my = H * 0.62;
async function moveTo(x, y, ms = 600) {
  const n = Math.max(6, Math.round(ms / 25)), x0 = mx, y0 = my;
  for (let i = 1; i <= n; i++) {
    const u = i / n, e = u < 0.5 ? 2 * u * u : 1 - (-2 * u + 2) ** 2 / 2;
    mx = x0 + (x - x0) * e; my = y0 + (y - y0) * e;
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: mx, y: my });
    await js(`(()=>{const c=document.getElementById('__cur'); if(c){c.style.left=${mx}+'px'; c.style.top=${my}+'px';}})()`);
    await sleep(ms / n);
  }
}
async function click(x, y, ms) {
  await moveTo(x, y, ms);
  await sleep(150);
  await js(`document.getElementById('__cur')?.classList.add('down')`);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(70);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  setTimeout(() => js(`document.getElementById('__cur')?.classList.remove('down')`).catch(() => {}), 160);
}
const KEYS = { Space: [" ", 32], KeyE: ["e", 69], Tab: ["Tab", 9], Enter: ["Enter", 13] };
async function key(code) {
  const [k, vk] = KEYS[code];
  await send("Input.dispatchKeyEvent", { type: "keyDown", code, key: k, windowsVirtualKeyCode: vk });
  await sleep(60);
  await send("Input.dispatchKeyEvent", { type: "keyUp", code, key: k, windowsVirtualKeyCode: vk });
}

// ---- 游戏里的东西 → 屏幕坐标 ----
// 返回 {x,y,on}：on = 在画面里；door 用 R.key，线索 / 人 / 门用 it.id
const where = (sel) => js(`(()=>{const g=__game, V=g.camera.position.constructor;
  const t=g.clickTargets().find(t=>${sel}); if(!t) return null;
  const v=new V((t.a[0]+t.b[0])/2,(t.a[1]+t.b[1])/2,(t.a[2]+t.b[2])/2).project(g.camera);
  const r=g.renderer.domElement.getBoundingClientRect();
  const x=r.left+(v.x+1)/2*r.width, y=r.top+(1-v.y)/2*r.height;
  return {x,y,on:v.z<1&&x>40&&x<r.width-40&&y>r.height*0.14&&y<r.height*0.86};})()`);
const idle = `(__game.autoPath==null && !document.querySelector('#dialogue.show') && !document.querySelector('#scale-panel.show'))`;

// 对话：每句按字数停一会儿再按空格，直到对话框收起
async function talkThrough(maxLines = 12) {
  await waitFor(`!!document.querySelector('#dialogue.show')`, 20000, "对话框");
  for (let i = 0; i < maxLines; i++) {
    const t = await js(`document.querySelector('#dialogue.show .text')?.textContent || ''`);
    if (!t) break;
    await sleep(Math.min(4200, 1100 + t.length * 85));
    await key("Space");
    await sleep(250);
    if (!(await js(`!!document.querySelector('#dialogue.show')`))) break;
  }
  await sleep(400);
}

async function clickThing(sel, label) {
  const p = await where(sel);
  console.log(`  点 ${label}:`, p && { x: Math.round(p.x), y: Math.round(p.y), on: p.on });
  if (!p) throw new Error("找不到 " + label);
  if (!p.on) {
    // 在画面外：直接调游戏里的寻路（和点门牌 / 点东西一样的效果）
    console.log(`  ${label} 在画面外，改用门牌 / 直接寻路`);
    await js(`(()=>{const g=__game; const t=g.clickTargets().find(t=>${sel}); const v=new g.camera.position.constructor((t.a[0]+t.b[0])/2,(t.a[1]+t.b[1])/2,(t.a[2]+t.b[2])/2).project(g.camera);})()`);
    const tag = await js(`(()=>{for(const el of document.querySelectorAll('#door-tags > *')){ if(el.textContent.includes(${JSON.stringify(label)})&&el.offsetParent){const r=el.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};}} return null;})()`);
    if (tag) { await click(tag.x, tag.y); return; }
    throw new Error(label + " 不在画面里，也没有门牌");
  }
  await click(p.x, p.y);
}
const door = (key, enter) => `t.door&&t.door.key===${JSON.stringify(key)}&&t.enter===${enter}`;
const item = (id) => `t.it&&t.it.id===${JSON.stringify(id)}`;

async function enterRoom(key, name) {
  await clickThing(door(key, true), name);
  await waitFor(`__game.currentName!=null && ${idle}`, 30000, "走进 " + name);
  await sleep(2200);   // 拉门转场 + 房名卡
}
// 出门：游戏里点"回到长廊"的目的地在门槛里面，传送到走廊后寻路又会把人带回房间（探案版的 bug，没改游戏代码）。
// 所以出了门就按住 ↑ 一下，打断寻路，药郎停在走廊门口。
async function leaveRoom(key) {
  await clickThing(door(key, false), "长廊");
  await waitFor(`__game.zoneFor(__game.player.position)==='Z1_corridor'`, 30000, "走到走廊");
  await send("Input.dispatchKeyEvent", { type: "keyDown", code: "ArrowUp", key: "ArrowUp", windowsVirtualKeyCode: 38 });
  const t0 = Date.now();
  while (Date.now() - t0 < 5000 && (await js(`!!__game.autoPath`))) await sleep(16);
  await send("Input.dispatchKeyEvent", { type: "keyUp", code: "ArrowUp", key: "ArrowUp", windowsVirtualKeyCode: 38 });
  await waitFor(idle, 10000, "出门");
  await sleep(1400);
}
async function getClue(id, name, lines = 12) {
  await clickThing(item(id), name);
  await talkThrough(lines);
  await sleep(500);
}
async function weigh(a, b, hoverBetween = false) {
  await key("Tab");
  await waitFor(`!!document.querySelector('#scale-panel.show')`, 5000, "天秤面板");
  await sleep(900);
  const btn = (id) => js(`(()=>{for(const b of document.querySelectorAll('#scale-panel .item')){ if(b.querySelector('img').src.endsWith('/${id}.png')){const r=b.getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};}} return null;})()`);
  const pa = await btn(a); await click(pa.x, pa.y, 700); await sleep(800);
  if (hoverBetween) {   // 理：在两件之间犹豫一下
    const p1 = await btn("E6a"), p2 = await btn("E6b");
    await moveTo(p1.x, p1.y, 700); await sleep(900); await moveTo(p2.x, p2.y, 700); await sleep(900);
  }
  const pb = await btn(b); await click(pb.x, pb.y, 700);
  await sleep(1500);
}

// ================= 主流程 =================
ws = new WebSocket(await connect());
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) { const p = pending.get(d.id); pending.delete(d.id); d.error ? p.rej(new Error(d.error.message)) : p.res(d.result); }
  else if (d.method && handlers[d.method]) handlers[d.method](d.params);
};
await send("Page.enable"); await send("Runtime.enable");
await send("Page.navigate", { url: `http://[::1]:5173/game.html?log=0` });
await waitFor(`!!window.__game && document.getElementById('status')?.textContent && !document.getElementById('status').textContent.includes('加载')`, 120000, "游戏加载");
console.log("加载完，等泼溅排序", await js(`JSON.stringify([innerWidth, innerHeight, __game.renderer.domElement.width, __game.renderer.domElement.height])`));
await sleep(9000);
// 录屏用：藏掉左上角的操作说明，加一个假光标
await js(`(()=>{const s=document.createElement('style'); s.textContent='#hud{display:none!important} #__cur{position:fixed;z-index:99999;pointer-events:none;width:30px;height:30px;margin:-2px 0 0 -3px;transition:transform .12s} #__cur.down{transform:scale(.82)}'; document.head.appendChild(s);
  const c=document.createElement('div'); c.id='__cur'; c.innerHTML='<svg viewBox="0 0 24 24" width="30" height="30"><path d="M3 2 L3 19 L7.6 14.8 L10.6 21.6 L13.6 20.3 L10.7 13.6 L17 13.6 Z" fill="#F1E9DA" stroke="#322D48" stroke-width="1.6" stroke-linejoin="round"/></svg>'; c.style.left='${mx}px'; c.style.top='${my}px'; document.body.appendChild(c);})()`);

if (!PROBE) await send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
await sleep(800);

try {
  // 1 推门
  mark("01_推门");
  await sleep(2500);
  await clickThing(`t.it&&t.it.kind==='gate'`, "门");
  await talkThrough();
  await sleep(1500);

  // 2 规则：打开天秤，三个字暗着
  mark("02_天秤空");
  await key("Tab"); await sleep(2800); await key("Tab"); await sleep(800);

  // 3 形
  mark("03_形");
  await getClue("E2", "拓画");
  await getClue("E1", "彩线");
  await weigh("E1", "E2");
  await talkThrough();
  await sleep(800);

  // 4 天秤晃：走向女中房门口
  mark("04_天秤晃");
  await enterRoom("maids", "女中的房间");

  // 5 真
  mark("05_真");
  await getClue("kame", "阿龟");   // 和阿龟说话拿家书（npc 的 it.id 就是 kame）
  await leaveRoom("maids");
  await enterRoom("utayama", "歌山的房间");
  await getClue("E4", "登记簿", 20);
  await weigh("E3", "E4");
  await talkThrough();
  await leaveRoom("utayama");

  // 6 理
  mark("06_理");
  await enterRoom("courtyard", "中庭");
  await getClue("E5", "井");
  await leaveRoom("courtyard");
  await enterRoom("yuki", "空房");
  await getClue("E6a", "木线轴");
  await getClue("E6b", "回信");
  mark("06b_理_天秤");
  await weigh("E5", ENDING === "b" ? "E6b" : "E6a", true);
  await talkThrough();

  // 7 拔剑
  mark("07_拔剑");
  await waitFor(`!!document.querySelector('#ending.show')`, 90000, "结果卡");
  mark("08_结果卡");
  await sleep(1500);
  const sv = await js(`(()=>{const r=document.querySelector('#ending .save').getBoundingClientRect(); return {x:r.left+r.width/2,y:r.top+r.height/2};})()`);
  await moveTo(sv.x, sv.y, 900); await sleep(3500);
  mark("end");
} catch (e) {
  console.error("出错：", e.message);
  mark("error");
  const shot = await send("Page.captureScreenshot", { format: "jpeg", quality: 80 });
  fs.writeFileSync(path.join(OUT, "error.jpg"), Buffer.from(shot.data, "base64"));
  console.error(await js(`JSON.stringify({auto:!!__game.autoPath, name:__game.currentName, dlg:document.querySelector('#dialogue').className, panel:document.querySelector('#scale-panel').className, tags:[...document.querySelectorAll('#door-tags > *')].map(e=>[e.textContent,e.className,e.offsetParent?1:0]), p:[__game.player.position.x,__game.player.position.z]})`).catch(e=>e.message));
}
if (!PROBE) await send("Page.stopScreencast");
await sleep(500);
fs.writeFileSync(path.join(OUT, "frames.json"), JSON.stringify(frames));
fs.writeFileSync(path.join(OUT, "markers.json"), JSON.stringify(markers, null, 1));
console.log(`帧数 ${frames.length}，时长 ${frames.length ? (frames.at(-1).t - frames[0].t).toFixed(1) : 0}s`);
ws.close(); chrome.kill(); fs.rmSync(prof, { recursive: true, force: true });
process.exit(0);
