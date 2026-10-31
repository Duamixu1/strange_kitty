// 手机触屏测试：无头 Chrome 模拟手机（默认横屏 844×390，W=390 H=844 竖屏），发真实触摸事件：点地面走、一指拖转镜头、两指捏合、连点快走、按钮栏、点観开卡关卡；打印 JSON 结果，截图存到第二个参数的目录。用法：node tools/tour_touchtest.mjs <地点> <目录>
import { spawn } from "node:child_process";
import fs from "node:fs";
const [loc = "wanya", out = "."] = process.argv.slice(2);
const prof = fs.mkdtempSync("/tmp/tt-");
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--user-data-dir=${prof}`, "--remote-debugging-port=9333", `--window-size=${process.env.W||844},${process.env.H||390}`, "--enable-gpu", "--use-angle=metal", "--ignore-gpu-blocklist", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 30; i++) { try { const l = await (await fetch("http://127.0.0.1:9333/json")).json(); const p = l.find((t) => t.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(300); }
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (pend.has(d.id)) { pend.get(d.id)(d.result ?? d); pend.delete(d.id); } };
const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result?.value;
await cdp("Emulation.setDeviceMetricsOverride", { width: +(process.env.W||844), height: +(process.env.H||390), deviceScaleFactor: 2, mobile: true });
await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
await cdp("Emulation.setEmulatedMedia", { features: [{ name: "pointer", value: "coarse" }] });
await cdp("Page.enable");
await cdp("Page.navigate", { url: `${process.env.BASE || "http://[::1]:5173/tour.html"}?loc=${loc}` });
for (let i = 0; i < 90; i++) { await sleep(1000); if (await ev("!!(window.__tour && __tour.zone)")) break; }
await sleep(2500);
const shot = async (name) => { const r = await cdp("Page.captureScreenshot", { format: "jpeg", quality: 80 }); fs.writeFileSync(`${out}/${name}.jpg`, Buffer.from(r.data, "base64")); };
const touch = (type, pts) => cdp("Input.dispatchTouchEvent", { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
const res = {}; const innerW = +(process.env.W||844);
res.touchClass = await ev("document.body.classList.contains('touch')");
const pos = () => ev("[__tour.player.position.x, __tour.player.position.z].map(v=>+v.toFixed(2))");
const dist = () => ev("+(__tour.cam.cur ?? __tour.cam.dist).toFixed(2)");
res.cam0 = await ev("[...__tour.camera.position.toArray().map(v=>+v.toFixed(2)), +__tour.camera.fov.toFixed(1), __tour.cam.fixedOn ? \"fixed\" : \"follow\", +(__tour.cam.cur??0).toFixed(2)]"); await shot(`touch_${loc}_0`);
// 1. 点地面：点画面下方偏左
res.p0 = await pos();
// 声音：记下 audio.play 被调了哪些（开发服务器上 import 到的是同一个模块实例）
await ev(`(() => { const A = __tour.audio; window.__snd = []; const p = A.play; A.play = (n, ...a) => { __snd.push(n + (a[0] ? ":" + a[0] : "")); return p(n, ...a); }; return true; })()`);
// 找药郎前方 1.5~4 米一个能站的点，投到屏幕上点它
const tp = await ev(`(()=>{const T=__tour,p=T.player.position,f=T.cam.forward;for(const r of [3,2.5,2,1.5,4])for(const a of [0,.4,-.4,.8,-.8]){const x=p.x+(f.x*Math.cos(a)-f.z*Math.sin(a))*r,z=p.z+(f.z*Math.cos(a)+f.x*Math.sin(a))*r;if(!T.col.canStand(x,z))continue;const v=new p.constructor(x,p.y,z).project(T.camera);const sx=(v.x+1)/2*innerWidth,sy=(1-v.y)/2*innerHeight;if(sx>20&&sx<innerWidth-110&&sy>60&&sy<innerHeight-20)return [sx,sy];}return null})()`);
res.tapAt = tp;
if (tp) { await touch("touchStart", [tp]); await sleep(60); await touch("touchEnd", []); }
await sleep(2500); res.p1 = await pos(); res.walked = Math.hypot(res.p1[0] - res.p0[0], res.p1[1] - res.p0[1]);
// 2. 一指拖：转镜头
res.yaw0 = await ev("+__tour.cam.yaw.toFixed(3)");
await touch("touchStart", [[innerW/2, 200]]); for (let k = 1; k <= 8; k++) { await touch("touchMove", [[innerW/2 - 80 + k * 20, 200]]); await sleep(16); } await touch("touchEnd", []);
await sleep(300); res.yaw1 = await ev("+__tour.cam.yaw.toFixed(3)"); res.p2 = await pos(); res.dragNoWalk = Math.hypot(res.p2[0] - res.p1[0], res.p2[1] - res.p1[1]) < 0.05;
// 3. 两指捏合：拉近
res.d0 = await ev("+__tour.cam.dist.toFixed(2)");
await touch("touchStart", [[innerW/2-120, 200], [innerW/2+120, 200]]); for (let k = 1; k <= 8; k++) { await touch("touchMove", [[innerW/2-120 + k * 10, 200], [innerW/2+120 - k * 10, 200]]); await sleep(16); } await touch("touchEnd", []);
await sleep(300); res.d1 = await ev("+__tour.cam.dist.toFixed(2)"); res.p3 = await pos(); res.pinchNoWalk = Math.hypot(res.p3[0] - res.p2[0], res.p3[1] - res.p2[1]) < 0.05;
await shot(`touch_${loc}_1`);
// 4. 连点两下：快走
const tp2 = await ev(`(()=>{const T=__tour,p=T.player.position,f=T.cam.forward;for(const r of [5,4.5,4,3.5,3])for(const a of [0,.3,-.3,.6,-.6]){const x=p.x+(f.x*Math.cos(a)-f.z*Math.sin(a))*r,z=p.z+(f.z*Math.cos(a)+f.x*Math.sin(a))*r;if(!T.col.canStand(x,z))continue;const v=new p.constructor(x,p.y,z).project(T.camera);const sx=(v.x+1)/2*innerWidth,sy=(1-v.y)/2*innerHeight;if(sx>20&&sx<innerWidth-110&&sy>60&&sy<innerHeight-20)return [sx,sy];}return null})()`);
res.tap2At = tp2;
if (tp2) { await touch("touchStart", [tp2]); await sleep(40); await touch("touchEnd", []); await sleep(120); await touch("touchStart", [tp2]); await sleep(40); await touch("touchEnd", []); }
await sleep(900); res.speedNow = await ev("(()=>{const a=__tour.player.position.clone();return new Promise(r=>setTimeout(()=>r(+(a.distanceTo(__tour.player.position)/0.5).toFixed(2)),500))})()");
await sleep(2500);
// 5. 按钮：滤镜、姿势
const btn = async (k) => { const r = await ev(`(()=>{const b=document.querySelector('#pad [data-k=${k}]').getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]})()`); await touch("touchStart", [r]); await sleep(50); await touch("touchEnd", []); await sleep(500); };
await btn("KeyF"); res.filter = await ev("__tour.renderer.domElement.style.filter || 'none'");
await btn("KeyO"); await sleep(800); res.pose = await ev("__tour.pose");
await shot(`touch_${loc}_2`);
// 6. 観标签：点了走过去开卡
const tag = await ev("(()=>{const t=[...document.querySelectorAll('.tag.view')].find(e=>{const b=e.getBoundingClientRect();return b.x>0&&b.x<844&&b.y>0&&b.y<330&&e.style.display!=='none'});if(!t)return null;const b=t.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]})()");
res.tag = tag;
if (tag) { await touch("touchStart", [tag]); await sleep(50); await touch("touchEnd", []); for (let i = 0; i < 20 && !(await ev("__tour.card.isOpen")); i++) await sleep(500); res.cardOpen = await ev("__tour.card.isOpen"); await sleep(600); await shot(`touch_${loc}_3_card`); await touch("touchStart", [[422, 250]]); await sleep(50); await touch("touchEnd", []); await sleep(600); res.cardClosed = !(await ev("__tour.card.isOpen")); }
res.audioReady = await ev("__tour.audio.ready");
res.sounds = await ev("(() => { const c = {}; for (const n of window.__snd || []) c[n] = (c[n] || 0) + 1; return c; })()");
res.errors = await ev("window.__errs || []");
console.log(JSON.stringify(res));
ws.close(); chrome.kill(); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {}
