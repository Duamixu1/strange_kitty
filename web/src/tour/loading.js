// 首次加载提示（10-31 用户："手机和电脑初次加载时间都很长，做一个简单轻量的提示说明"）。
// 提示层本身写在 tour.html 里（静态 HTML + CSS，没有图片），打开网页就显示，不用等 3.6 MB 的程序下完；
// 程序跑起来以后由这里接手：进度条和百分比、轮播操作小提示，加载完淡出。
// 文案不出现"下载"和 MB（11-03 用户：说下载很奇怪，会让人有抵触心理，只说进度）。
// 进度怎么算：普通文件（模型、贴图、走路图）包一层 fetch 数实际收到的字节；泼溅（.spz，Spark 可能在后台线程里下，数不到）
// 每块 initialized 以后按它的大小一次加上，所以 fetch 那边跳过 .spz，不重复算。
// 估计总量是 10-31 实测 fetch 收到的字节（解压后，不含已经下完的程序本体）；总地图就是那张长卷图；泼溅按文件大小。
const EST_MB = { map: 1.2, ooku: 6.1, wanya: 7.0, sakai: 6.6, fuenokouji: 7.5, solaris: 6.5, subway: 6.5, prison: 6.5 };
const SPLAT_MB = 7.45;   // 大奥每块泼溅 7.2~7.8 MB

const $ = (s) => document.querySelector(s);
const el = $("#loading");
let got = 0, splatGot = 0, total = 0, timer = null, done = false, splatMB = SPLAT_MB;
// 11-06 进门前的铺垫（用户："进去花了两三分钟……前期做一个比较长的故事背景铺垫，配不需要精度那么高的图，让人一边读、后台一边加载"）：
//   第一次进一个地点，加载卡换成几页故事（prelude.<地点>，文案线写；图是游戏里自己拍的小图 textures/prelude/<地点>_<n>.jpg）。
//   点一下翻一页；场景好了以后不自己消失，等看的人点「进入」（读完最后一页、或者随时点底下的「直接进入」）
let pre = null;   // { pages, i, ready, name, box }
function preRender() {
  if (!pre) return;
  const { pages, i, ready, name, box } = pre, pg = pages[i], last = i === pages.length - 1;
  box.querySelector("img").src = pg.img; box.querySelector("img").style.visibility = "hidden";
  box.querySelector(".pt").textContent = pg.title || ""; box.querySelector(".pb").textContent = pg.body || "";
  box.querySelector(".pd").textContent = pages.map((_, k) => (k === i ? "●" : "○")).join(" ");
  const go = box.querySelector(".pgo"), skip = box.querySelector(".pskip");
  if (!last) { go.textContent = "接着读 →"; go.disabled = false; }
  else if (ready) { go.textContent = `进入「${name}」`; go.disabled = false; }
  else { go.textContent = "还在准备…"; go.disabled = true; }
  skip.style.display = ready && !last ? "" : "none";
  el.classList.toggle("pre-ready", !!ready);
}
function preEnter() {
  if (!pre) return;
  pre = null; el.classList.add("out"); setTimeout(() => el.remove(), 600);
}

function render() {
  if (done || !el) return;
  const mb = (got / 1e6) + splatGot;
  const p = Math.min(0.97, mb / Math.max(total, 0.1));
  el.querySelector(".bar i").style.width = `${(p * 100).toFixed(1)}%`;
  el.querySelector(".mb").textContent = `${Math.round(p * 100)}%`;
}

// fetch 包一层数字节（只在加载期间；加载完换回原来的 fetch）
const rawFetch = window.fetch.bind(window);
// 11-06 手机上进そらりす丸"加载失败"：手机网一抖，一个文件没下来整个地点就进不去。下载失败（断网、5xx）隔一会儿自动再试两次；
// 记下最后一个失败的文件，失败页上写出来（也报给访问统计），下次好查
const urlOf = (input) => (typeof input === "string" ? input : input?.url || "");
export let lastFail = "";
async function retryFetch(input, init) {
  for (let i = 0; ; i++) {
    try {
      const res = await rawFetch(input, init);
      if (res.status >= 500 && i < 2) throw new Error(`HTTP ${res.status}`);
      if (!res.ok) lastFail = `${res.status} ${urlOf(input).replace(/^.*\/strange_kitty\//, "")}`;
      return res;
    } catch (e) {
      if (i >= 2 || init?.signal?.aborted) { lastFail = `${e.message} ${urlOf(input).replace(/^.*\/strange_kitty\//, "")}`; throw e; }
      await new Promise((r) => setTimeout(r, 700 * (i + 1)));
    }
  }
}
window.fetch = retryFetch;
function countingFetch(input, init) {
  return retryFetch(input, init).then((res) => {
    const url = typeof input === "string" ? input : input.url || "";
    if (done || !res.body || /\.spz(\?|$)/.test(url)) return res;
    const counter = new TransformStream({ transform(chunk, ctl) { got += chunk.byteLength; ctl.enqueue(chunk); } });
    return new Response(res.body.pipeThrough(counter), { status: res.status, statusText: res.statusText, headers: res.headers });
  });
}

export const loading = {
  /** 开始：kind = "map" 或地点 id，name = 显示的名字，splats = 这个地点有几块泼溅 */
  start(kind, name, splats = 0, mb = SPLAT_MB) {   // mb：每块泼溅多大（轻量档 lite 约 3.5）
    if (!el) return;
    splatMB = mb; total = (EST_MB[kind] ?? 5) + splats * splatMB;
    el.querySelector(".where").textContent = kind === "map" ? "正在展开绘卷" : `正在进入「${name}」`;
    el.querySelector(".big").textContent = total > 15 ? "这里有实景扫描的房间，第一次进入会久一点，请多等一会儿。" : "";
    el.classList.add("counting");
    window.fetch = countingFetch;
    render(); timer = setInterval(render, 250);
  },
  /** 一块泼溅加载完 */
  splatDone() { splatGot += splatMB; render(); },
  /** 当前步骤（"加载药郎…"之类），显示在进度条下面 */
  step(text) { const s = el?.querySelector(".step"); if (s) s.textContent = text; },
  /** 加载完：进度条走满，淡出 */
  /** 进门前的铺垫：pages = [{ title, body, img }]，name = 地点名。加载完以后等人点「进入」才撤 */
  prelude(pages, name) {
    if (!el || !pages?.length) return;
    const box = document.createElement("div"); box.className = "pre";
    box.innerHTML = '<div class="pimg"><img alt=""></div><div class="pt"></div><div class="pb"></div><div class="pnav"><span class="pd"></span><button class="pgo"></button></div><button class="pskip">直接进入</button>';
    box.querySelector("img").addEventListener("load", (e) => { e.target.style.visibility = ""; });
    box.querySelector("img").addEventListener("error", (e) => { e.target.parentNode.style.display = "none"; });
    const next = () => { if (!pre) return; if (pre.i < pre.pages.length - 1) { pre.i++; preRender(); } else if (pre.ready) preEnter(); };
    box.querySelector(".pgo").addEventListener("click", (e) => { e.stopPropagation(); next(); });
    box.querySelector(".pskip").addEventListener("click", (e) => { e.stopPropagation(); preEnter(); });
    box.addEventListener("click", next);   // 点图或字也能翻
    addEventListener("keydown", (e) => { if (pre && (e.code === "Space" || e.code === "Enter" || e.code === "ArrowRight")) { e.preventDefault(); next(); } });
    for (const p of pages) { const im = new Image(); im.src = p.img; }   // 几张小图先下好
    el.querySelector(".card").insertBefore(box, el.querySelector(".bar"));
    el.classList.add("has-pre");
    pre = { pages, i: 0, ready: false, name, box }; preRender();
  },
  /** 铺垫还开着（加载卡还没撤）：tour.js 这时不接键盘 */
  get holding() { return !!pre; },
  done() {
    if (done || !el) return;
    window.__loadMB = +(got / 1e6).toFixed(2);   // 调试：这次实际数到多少（不含泼溅），用来校准 EST_MB
    el.querySelector(".bar i").style.width = "100%";
    done = true; clearInterval(timer); window.fetch = retryFetch;
    if (pre) { pre.ready = true; el.querySelector(".mb").textContent = "100%"; el.querySelector(".step").textContent = "准备好了"; preRender(); return; }
    el.classList.add("out"); setTimeout(() => el.remove(), 600);
  },
  /** 出错：提示换网络或刷新 */
  fail(msg, detail = "") {
    if (!el) return;
    done = true; clearInterval(timer); window.fetch = retryFetch;
    el.classList.add("failed");
    el.querySelector(".where").textContent = "加载失败";
    el.querySelector(".big").textContent = `${msg}。可以再试一次，或者换个网络。`;
    if (!el.querySelector(".err")) {
      const d = document.createElement("div"); d.className = "err"; d.textContent = detail;
      d.style.cssText = "font: 11px/1.5 ui-monospace, Menlo, monospace; opacity: .6; margin-top: 10px; word-break: break-all;";
      const b = document.createElement("button"); b.textContent = "再试一次"; b.onclick = () => location.reload();
      b.style.cssText = "margin-top: 14px; padding: 8px 22px; font: 14px serif; color: #fff; background: #A23B3B; border: 0; border-radius: 3px;";
      el.querySelector(".big").after(d, b);
    }
  },
};
