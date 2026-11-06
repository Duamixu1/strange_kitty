// 11-06 用户："可以在首页，进入地图前放一些文字的闪卡或者是介绍，方便用户对这个故事有个基本的了解，并且方便之后的内容先加载"。
// 11-06 第二版（文案w）：用户说"有点普通，最好不要太多字，可以有一些浮世绘风格的简笔画，点击翻页（像翻手册），尽量简单、加载快"。
//   一本竖着的小手册：每页一幅浮世绘味的简笔画（内联 SVG，不下图片）+ 一句话（+ 可选一行小字）；
//   点一下，这页沿左边书脊翻过去；点左边四分之一往回翻。画用游览版那套色（纸、墨、朱、赭金、青、藤紫）。
// 翻的时候后台把各地点都要用的东西（药郎模型、药箱小物件、长卷图）先下进浏览器缓存，进地点时就快。
// 看过记在本机；总地图左上「缘起」能再看。字读 text.json 的 intro.cards（文案w：{k 竖排标题, t 一句, b? 小字, art? 画, go? 最后一页按钮}），没有就用这里的底稿。
// 键：→ / 空格 / 回车 下一页，← 上一页，Esc 跳过；手机点页面右边下一页、左边四分之一上一页，左右划也行。
import { asset } from "../paths.js";

const SEEN = "mononoke_tour_intro";
const DRAFT = [
  { k: "怪化猫 · 游览", t: "跟着卖药郎，去出过事的地方。", b: "大奥 · 万屋 · 坂井家", art: "yorozu" },
  { k: "物怪", t: "放不下的念头缠上了妖，就成了物怪。", art: "sumi" },
  { k: "退魔剑", t: "药箱里有把剑，不是想拔就能拔。", art: "klimt" },
  { k: "形 · 真 · 理", t: "查清这三样，剑才出鞘。", b: "它是什么 · 出过什么事 · 为什么不走", art: "noh" },
  { k: "启程", t: "长卷上亮着的地方，都进得去。", go: "展开长卷", art: "taisho" },
];

import { ART, ORDER, DEFS, svg } from "./story_art.js";   // 插图（第三版：每页一种原作画风），见 story_art.js

function css() {
  if (document.getElementById("story-intro-css")) return;
  const s = document.createElement("style"); s.id = "story-intro-css";
  s.textContent = `
  #story-intro { position: fixed; inset: 0; z-index: 60; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; padding: 16px;
    background: var(--navy); font-family: "Songti SC", "Noto Serif CJK SC", "Hiragino Mincho ProN", serif; color: var(--ink); opacity: 0; transition: opacity .45s; }
  body.lang-ja #story-intro { font-family: "Hiragino Mincho ProN", "Yu Mincho", serif; }
  #story-intro.show { opacity: 1; }
  #story-intro .si-book { position: relative; width: min(340px, 80vw, 56vh); aspect-ratio: 3 / 4; perspective: 1400px; }
  #story-intro .si-book::before, #story-intro .si-book::after { content: ""; position: absolute; inset: 0; background: #E2D7C2; border: 2px solid var(--ink); }
  #story-intro .si-book::before { transform: translate(5px, 5px); } #story-intro .si-book::after { transform: translate(10px, 10px); background: #D3C7AF; z-index: -1; }
  #story-intro .si-page { position: absolute; inset: 0; z-index: 1; box-sizing: border-box; padding: 26px 22px 40px; background: var(--paper) linear-gradient(90deg, rgba(50,45,72,.13), rgba(50,45,72,0) 16px);
    border: 2px solid var(--ink); display: flex; flex-direction: column; align-items: center; cursor: pointer; user-select: none; -webkit-tap-highlight-color: transparent;
    transform-origin: left center; transition: transform .75s cubic-bezier(.35,.6,.25,1), opacity .75s; backface-visibility: hidden; }
  #story-intro .si-page.gone { transform: rotateY(-165deg); opacity: 0; pointer-events: none; }
  #story-intro .si-k { position: absolute; right: 14px; top: 16px; writing-mode: vertical-rl; font-size: 15px; letter-spacing: .35em; color: var(--crimson);
    border-left: 1.5px solid rgba(50,45,72,.3); padding-left: 6px; max-height: 46%; overflow: hidden; }
  #story-intro .si-art { width: 96%; margin: 14px 22px 0 0; flex: 1 1 auto; min-height: 0; display: flex; align-items: center; }
  #story-intro .si-art svg { width: 100%; height: auto; max-height: 100%; display: block; box-shadow: 2px 3px 0 rgba(50,45,72,.25); }
  #story-intro .si-t { font-size: clamp(15px, 2.6vh, 18px); line-height: 1.6; text-align: center; margin: 10px 4px 0; letter-spacing: .04em; text-wrap: balance; }
  #story-intro .si-b { font-size: 12px; opacity: .6; margin-top: 6px; letter-spacing: .08em; text-align: center; text-wrap: balance; }
  #story-intro .si-no { position: absolute; left: 0; right: 0; bottom: 12px; text-align: center; font-size: 12px; letter-spacing: .3em; opacity: .45; }
  #story-intro .si-go { margin-top: 12px; border: 2px solid var(--ink); background: var(--crimson); color: var(--paper); font: inherit; font-size: 14px; letter-spacing: .2em; padding: 6px 18px; cursor: pointer; box-shadow: 2px 2px 0 var(--ink); }
  #story-intro .si-hint { color: var(--paper); opacity: .55; font: 12px -apple-system, "PingFang SC", sans-serif; letter-spacing: .15em; transition: opacity .4s; }
  #story-intro .si-hint.off { opacity: 0; }
  #story-intro .si-skip { position: fixed; top: 16px; right: 18px; background: transparent; border: 1px solid rgba(241,233,218,.4); color: var(--paper); opacity: .7; font: 13px -apple-system, "PingFang SC", sans-serif; letter-spacing: .1em; padding: 6px 14px; cursor: pointer; }
  #story-intro .si-load { position: fixed; bottom: 16px; left: 0; right: 0; text-align: center; color: var(--paper); opacity: .4; font: 12px -apple-system, "PingFang SC", sans-serif; letter-spacing: .15em; }
  `;
  document.head.appendChild(s);
}

/** 后台先下的东西（进浏览器缓存；进地点时 GLTFLoader 再取就快了） */
function warm(urls) {
  const list = [...new Set(urls.filter(Boolean))];
  let n = 0; const done = () => ++n;
  return { total: list.length, get done() { return n; }, all: Promise.all(list.map((u) => fetch(u, { priority: "low" }).then((r) => r.blob()).catch(() => null).finally(done))) };
}

export const introSeen = () => { try { return localStorage.getItem(SEEN) === "1"; } catch { return true; } };

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

/** 放缘起手册；关掉时 resolve。warmUrls：翻页时顺手先下的文件（相对资源路径） */
export function storyIntro(texts, warmUrls = []) {
  css();
  const cards = texts?.["intro.cards"]?.length ? texts["intro.cards"] : DRAFT;
  const n = cards.length;
  const el = document.createElement("div"); el.id = "story-intro";
  const defs = DEFS;   // 纹样、滤镜（几张画共用）
  const pages = cards.map((c, k) => `<div class="si-page" data-i="${k}" style="z-index:${n - k + 1}">
      <div class="si-k">${esc(c.k)}</div><div class="si-art">${svg(c.art || ORDER[k % ORDER.length])}</div>
      <div class="si-t">${esc(c.t)}</div>${c.b ? `<div class="si-b">${esc(c.b)}</div>` : ""}
      ${k === n - 1 ? `<button class="si-go">${esc(c.go || "展开长卷")}</button>` : ""}<div class="si-no">${k + 1} / ${n}</div></div>`).join("");
  el.innerHTML = `${defs}<div class="si-book">${pages}</div><div class="si-hint">点一下翻页</div><button class="si-skip">跳过 Esc</button><div class="si-load"></div>`;
  document.body.appendChild(el);
  const $ = (s) => el.querySelector(s), all = [...el.querySelectorAll(".si-page")];
  const w = warm(warmUrls.filter((u) => typeof u === "string").map((u) => asset(u)));
  const loadTick = setInterval(() => { $(".si-load").textContent = w.done >= w.total ? "行李备好了" : `正在备行李 ${w.done} / ${w.total}`; }, 300);
  let i = 0;
  return new Promise((resolve) => {
    const show = (k) => { i = Math.max(0, Math.min(n - 1, k)); all.forEach((p, j) => p.classList.toggle("gone", j < i)); if (i > 0) $(".si-hint").classList.add("off"); };
    function close() {
      try { localStorage.setItem(SEEN, "1"); } catch {}
      removeEventListener("keydown", onKey, true); clearInterval(loadTick);
      el.classList.remove("show"); setTimeout(() => el.remove(), 450); resolve();
    }
    const next = () => (i === n - 1 ? close() : show(i + 1));
    function onKey(e) {
      if (["ArrowRight", "Space", "Enter", "KeyD"].includes(e.code)) next();
      else if (["ArrowLeft", "KeyA"].includes(e.code)) show(i - 1);
      else if (e.code === "Escape") close();
      else return;
      e.preventDefault(); e.stopPropagation();
    }
    addEventListener("keydown", onKey, true);
    $(".si-go")?.addEventListener("click", (e) => { e.stopPropagation(); close(); });
    $(".si-skip").addEventListener("click", (e) => { e.stopPropagation(); close(); });
    let down = null;
    $(".si-book").addEventListener("pointerdown", (e) => { down = { x: e.clientX, t: Date.now() }; });
    $(".si-book").addEventListener("pointerup", (e) => {
      if (!down || e.target.closest(".si-go")) return; const dx = e.clientX - down.x; down = null;
      if (Math.abs(dx) > 40) return dx < 0 ? next() : show(i - 1);   // 左右划
      const r = $(".si-book").getBoundingClientRect();
      e.clientX - r.left < r.width * 0.25 ? show(i - 1) : (i === n - 1 ? null : next());   // 最后一页点纸面不关，点按钮才走
    });
    show(0); setTimeout(() => el.classList.add("show"), 30);   // 不用 rAF：页面在后台时 rAF 不跑，会一直透明
  });
}
