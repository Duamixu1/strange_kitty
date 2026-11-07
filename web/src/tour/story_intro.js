import { asset, pub } from "../paths.js";

import { ORDER, DEFS, svg } from "./story_art.js";
import "./story_intro.css";
import { LANG } from "./i18n.js";

// 毛笔字体（11-07 用户："正文用刘建毛草，其他你决定"）：中文正文刘建毛草（草书）、标题和按钮志莽行书、日文祐字肅、英文 Cormorant 斜体。
// 只含手册用到的字的小 woff2（tools/intro_fonts.py 生成，改了 intro.cards 的字要重跑），按当前语言只下需要的那一两个。
const FONT_FILES = { zh: [["IntroZhBody", "intro_zh_body"], ["IntroZhTitle", "intro_zh_title"]], ja: [["IntroJa", "intro_ja"]], en: [["IntroEn", "intro_en", "italic"]] };
let fontsAsked = false;
function loadFonts() {
  if (fontsAsked || typeof FontFace === "undefined") return; fontsAsked = true;
  for (const [family, file, style] of FONT_FILES[LANG] || FONT_FILES.zh) {
    new FontFace(family, `url(${pub(`fonts/${file}.woff2`)}) format("woff2")`, { display: "swap", style: style || "normal" })
      .load().then((f) => document.fonts.add(f)).catch(() => {});   // 下不来就用原来的宋体
  }
}

const SEEN = "mononoke_tour_intro";
const DRAFT = [
  { k: "怪化猫 · 游览", t: "他只是个卖药的\n他到的地方\n总有奇怪的事发生", art: "yorozu" },
  { k: "物怪", t: "怨　执　舍不得\n这些念头遇见了妖\n就会变成物怪", art: "sumi" },
  { k: "退魔剑", t: "药郎的药箱里有一把剑\n在等待答案", art: "klimt" },
  { k: "形 · 真 · 理", t: "它是什么　出过什么事\n为何不走\n三样齐了　剑才出鞘", art: "noh" },
  { k: "启程", t: "雨还在下\n但故事已经开始了", go: "展开长卷", art: "taisho" },
];

function artImg(name) {
  const path = pub(`textures/intro/intro_${name}`);
  return `<img src="${path}.webp" srcset="${path}.webp 680w, ${path}_1600.webp 1600w"
    sizes="(orientation: landscape) 58vw, 92vh" alt="" data-art="${name}" draggable="false" decoding="async">`;
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
  loadFonts();
  const cards = texts?.["intro.cards"]?.length ? texts["intro.cards"] : DRAFT;
  const n = cards.length;
  const el = document.createElement("dialog"); el.id = "story-intro";
  el.setAttribute("aria-label", "缘起");
  const pages = cards.map((c, k) => `<section class="si-page" data-art="${esc(c.art)}" style="z-index:${n - k}">
      <div class="si-art"><div class="si-print">${artImg(c.art || ORDER[k % ORDER.length])}</div></div>
      <div class="si-copy">
        <div class="si-verse"><h2 class="si-k">${esc(c.k)}</h2>
        <p class="si-t">${esc(c.t)}</p></div>${c.b ? `<p class="si-b">${esc(c.b)}</p>` : ""}
        ${k === n - 1 ? `<button class="si-go">${esc(c.go || "展开长卷")}</button>` : ""}
      </div></section>`).join("");
  el.innerHTML = `${DEFS}<div class="si-book" tabindex="-1" autofocus>${pages}</div>
    <div class="si-series"><span aria-hidden="true">❀</span>缘起</div>
    <button class="si-skip">跳过<small>Esc</small></button>
    <footer class="si-footer"><p class="si-plain" aria-hidden="true"></p>
      <div class="si-nav"><button class="si-prev" aria-label="上一张">‹</button>
        <span class="si-no" aria-live="polite"></span>
        <button class="si-next" aria-label="下一张">›</button></div></footer>`;
  document.body.appendChild(el);
  el.showModal();
  el.querySelectorAll(".si-art img").forEach((im) => im.addEventListener("error", () => { im.outerHTML = svg(im.dataset.art); }, { once: true }));   // 图片挂了用 SVG 顶上
  const $ = (s) => el.querySelector(s), all = [...el.querySelectorAll(".si-page")];
  warm(warmUrls.filter((u) => typeof u === "string").map((u) => asset(u)));
  // 底栏原来写"正在备行李 n / m"，11-07 用户说"这里可以换成正文，因为草书确实看不明白"：改成这一页诗句的宋体版（英文本来就好认，不重复）
  const plain = (c) => (LANG === "en" ? "" : String(c?.t || "").replace(/\n+/g, "　"));
  let i = 0;
  return new Promise((resolve) => {
    function show(k) {
      i = Math.max(0, Math.min(n - 1, k));
      all.forEach((p, j) => {
        p.classList.toggle("gone", j < i);
        p.inert = j !== i;
      });
      $(".si-no").textContent = `${i + 1} / ${n}`;
      $(".si-plain").textContent = plain(cards[i]);
      $(".si-prev").disabled = i === 0;
      $(".si-next").disabled = i === n - 1;
    }
    function close() {
      try { localStorage.setItem(SEEN, "1"); } catch {}
      removeEventListener("keydown", onKey, true);
      el.classList.remove("show"); setTimeout(() => { el.close(); el.remove(); }, 450); resolve();
    }
    const next = () => (i === n - 1 ? close() : show(i + 1));
    function onKey(e) {
      if (["Enter", "Space"].includes(e.code) && e.target.closest?.("button")) return;
      if (["ArrowRight", "Space", "Enter", "KeyD"].includes(e.code)) next();
      else if (["ArrowLeft", "KeyA"].includes(e.code)) show(i - 1);
      else if (e.code === "Escape") close();
      else return;
      e.preventDefault(); e.stopPropagation();
    }
    addEventListener("keydown", onKey, true);
    $(".si-prev").addEventListener("click", () => show(i - 1));
    $(".si-next").addEventListener("click", () => show(i + 1));
    el.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
    $(".si-go")?.addEventListener("click", (e) => { e.stopPropagation(); close(); });
    $(".si-skip").addEventListener("click", (e) => { e.stopPropagation(); close(); });
    let down = null;
    $(".si-book").addEventListener("pointercancel", () => { down = null; });
    $(".si-book").addEventListener("pointerdown", (e) => { down = { x: e.clientX }; });
    $(".si-book").addEventListener("pointerup", (e) => {
      if (!down || e.target.closest(".si-go")) return; const dx = e.clientX - down.x; down = null;
      if (Math.abs(dx) > 40) return dx < 0 ? next() : show(i - 1);   // 左右划
      const r = $(".si-book").getBoundingClientRect();
      e.clientX - r.left < r.width * 0.25 ? show(i - 1) : (i === n - 1 ? null : next());   // 最后一页点纸面不关，点按钮才走
    });
    show(0); setTimeout(() => el.classList.add("show"), 30);   // 不用 rAF：页面在后台时 rAF 不跑，会一直透明
  });
}
