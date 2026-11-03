// 首次加载提示（10-31 用户："手机和电脑初次加载时间都很长，做一个简单轻量的提示说明"）。
// 提示层本身写在 tour.html 里（静态 HTML + CSS，没有图片），打开网页就显示，不用等 3.6 MB 的程序下完；
// 程序跑起来以后由这里接手：进度条和百分比、轮播操作小提示，加载完淡出。
// 文案不出现"下载"和 MB（11-03 用户：说下载很奇怪，会让人有抵触心理，只说进度）。
// 进度怎么算：普通文件（模型、贴图、走路图）包一层 fetch 数实际收到的字节；泼溅（.spz，Spark 可能在后台线程里下，数不到）
// 每块 initialized 以后按它的大小一次加上，所以 fetch 那边跳过 .spz，不重复算。
// 估计总量是 10-31 实测 fetch 收到的字节（解压后，不含已经下完的程序本体）；总地图就是那张长卷图；泼溅按文件大小。
const EST_MB = { map: 1.2, ooku: 6.1, wanya: 7.0, sakai: 6.6 };
const SPLAT_MB = 7.45;   // 大奥每块泼溅 7.2~7.8 MB

const $ = (s) => document.querySelector(s);
const el = $("#loading");
let got = 0, splatGot = 0, total = 0, timer = null, done = false;

function render() {
  if (done || !el) return;
  const mb = (got / 1e6) + splatGot;
  const p = Math.min(0.97, mb / Math.max(total, 0.1));
  el.querySelector(".bar i").style.width = `${(p * 100).toFixed(1)}%`;
  el.querySelector(".mb").textContent = `${Math.round(p * 100)}%`;
}

// fetch 包一层数字节（只在加载期间；加载完换回原来的 fetch）
const rawFetch = window.fetch.bind(window);
function countingFetch(input, init) {
  return rawFetch(input, init).then((res) => {
    const url = typeof input === "string" ? input : input.url || "";
    if (done || !res.body || /\.spz(\?|$)/.test(url)) return res;
    const counter = new TransformStream({ transform(chunk, ctl) { got += chunk.byteLength; ctl.enqueue(chunk); } });
    return new Response(res.body.pipeThrough(counter), { status: res.status, statusText: res.statusText, headers: res.headers });
  });
}

export const loading = {
  /** 开始：kind = "map" 或地点 id，name = 显示的名字，splats = 这个地点有几块泼溅 */
  start(kind, name, splats = 0) {
    if (!el) return;
    total = (EST_MB[kind] ?? 5) + splats * SPLAT_MB;
    el.querySelector(".where").textContent = kind === "map" ? "正在展开绘卷" : `正在进入「${name}」`;
    el.querySelector(".big").textContent = total > 15 ? "这里有实景扫描的房间，第一次进入会久一点，请多等一会儿。" : "";
    el.classList.add("counting");
    window.fetch = countingFetch;
    render(); timer = setInterval(render, 250);
  },
  /** 一块泼溅加载完 */
  splatDone() { splatGot += SPLAT_MB; render(); },
  /** 当前步骤（"加载药郎…"之类），显示在进度条下面 */
  step(text) { const s = el?.querySelector(".step"); if (s) s.textContent = text; },
  /** 加载完：进度条走满，淡出 */
  done() {
    if (done || !el) return;
    window.__loadMB = +(got / 1e6).toFixed(2);   // 调试：这次实际数到多少（不含泼溅），用来校准 EST_MB
    el.querySelector(".bar i").style.width = "100%";
    done = true; clearInterval(timer); window.fetch = rawFetch;
    el.classList.add("out"); setTimeout(() => el.remove(), 600);
  },
  /** 出错：提示换网络或刷新 */
  fail(msg) {
    if (!el) return;
    done = true; clearInterval(timer); window.fetch = rawFetch;
    el.classList.add("failed");
    el.querySelector(".where").textContent = "加载失败";
    el.querySelector(".big").textContent = `${msg}。可以刷新再试一次，或者换个网络。`;
  },
};
