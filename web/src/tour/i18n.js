// 语言（11-06，用户："在地图那里加个设置入口，选中文、英文还是日文"）。文案w 做的。
//   - 选的语言存在 localStorage（mononoke_tour_lang），网址带 ?lang=en / ja / zh 也行（拍宣传图用）；默认中文。
//   - 内容文案：locations.js 的 loadText() 先读 text.json，再用 text.<语言>.json 逐键盖上去，缺的键留中文。
//   - 界面上写死在代码里的中文（提示条、按钮、加载页……）：不去改各个文件，这里在网页上查表换
//     （data/i18n/ui.<语言>.json，键是中文原文，{0}{1} 是变量，变量本身会再查一次表）。
//     新加的界面字没进表就照旧显示中文，不会坏；补表就行。
//   - 中文时这个文件什么都不做。
const KEY = "mononoke_tour_lang";
export const LANGS = [["zh", "中文"], ["en", "English"], ["ja", "日本語"]];

function readLang() {
  try {
    const q = new URLSearchParams(location.search).get("lang");
    if (q && LANGS.some(([id]) => id === q)) return q;
    const s = localStorage.getItem(KEY);
    if (s && LANGS.some(([id]) => id === s)) return s;
  } catch {}
  return "zh";
}
export const LANG = readLang();

export function setLang(id) {
  try { localStorage.setItem(KEY, id); } catch {}
  const u = new URL(location.href); u.searchParams.delete("lang");
  location.href = u.toString();
}

const DICTS = import.meta.glob("../data/i18n/ui.*.json", { eager: true, import: "default" });
const CJK = /[぀-ヿ一-鿿]/;
const exact = new Map(), pats = [];
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function compile(dict) {
  for (const [k, v] of Object.entries(dict || {})) {
    if (k.startsWith("_")) continue;
    if (!/\{\d\}/.test(k)) { exact.set(k, v); continue; }
    const order = [...k.matchAll(/\{(\d)\}/g)].map((m) => +m[1]);
    const re = new RegExp("^" + k.split(/\{\d\}/).map(esc).join("([\\s\\S]+?)") + "$");
    pats.push({ re, v, order, lit: k.replace(/\{\d\}/g, "").length });
  }
  pats.sort((a, b) => b.lit - a.lit);   // 字面越长越具体，先试
}

/** 查表翻一句；查不到原样返回。中文模式直接返回。 */
export function tr(s) {
  if (LANG === "zh" || !s || !CJK.test(s)) return s;
  const t = s.trim();
  let r = exact.get(t);
  if (r == null) for (const p of pats) {
    const m = t.match(p.re);
    if (m) { r = p.v.replace(/\{(\d)\}/g, (_, i) => tr(m[p.order.indexOf(+i) + 1])); break; }
  }
  if (r == null && t.includes(" · ")) {
    const parts = t.split(" · "), out = parts.map(tr);
    if (out.some((x, i) => x !== parts[i])) r = out.join(" · ");
  }
  return r == null ? s : s.replace(t, r);
}

const ATTRS = ["title", "aria-label", "alt", "placeholder", "data-p"];
function walk(n) {
  if (n.nodeType === 3) { if (n.parentElement?.closest("[data-noi18n]")) return; const v = tr(n.nodeValue); if (v !== n.nodeValue) n.nodeValue = v; return; }
  if (n.nodeType !== 1 || n.tagName === "SCRIPT" || n.tagName === "STYLE" || n.closest("[data-noi18n]")) return;
  for (const a of ATTRS) if (n.hasAttribute(a)) { const o = n.getAttribute(a), v = tr(o); if (v !== o) n.setAttribute(a, v); }
  for (const c of n.childNodes) walk(c);
}

/** 进页面就调一次：换掉已有的字，之后新出来的字（提示条、卡片、药箱）也跟着换 */
export function startI18n() {
  document.documentElement.lang = LANG === "zh" ? "zh-CN" : LANG;
  document.body.classList.add(`lang-${LANG}`);
  if (LANG === "zh") return;
  compile(DICTS[`../data/i18n/ui.${LANG}.json`]);
  walk(document.head.querySelector("title") || document.head); walk(document.body);
  new MutationObserver((ms) => {
    for (const m of ms) {
      if (m.type === "characterData") walk(m.target);
      else if (m.type === "attributes") walk(m.target);
      else m.addedNodes.forEach(walk);
    }
  }).observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
}

/** 总地图右上角的「设」：点开选语言，选了就重新载入 */
export function mountSettings(host) {
  const btn = document.createElement("button");
  btn.id = "setbtn"; btn.type = "button"; btn.textContent = "设"; btn.title = "设置";
  const panel = document.createElement("div");
  panel.id = "setpanel"; panel.className = "paper"; panel.setAttribute("role", "dialog");
  panel.innerHTML = `<div class="hd" data-noi18n>语言 · Language · 言語</div>` +
    LANGS.map(([id, name]) => `<button type="button" data-l="${id}" class="${id === LANG ? "on" : ""}" data-noi18n>${name}</button>`).join("");
  btn.addEventListener("click", (e) => { e.stopPropagation(); panel.classList.toggle("open"); });
  panel.addEventListener("click", (e) => { e.stopPropagation(); const l = e.target.closest("button")?.dataset.l; if (l && l !== LANG) setLang(l); else if (l) panel.classList.remove("open"); });
  addEventListener("click", () => panel.classList.remove("open"));
  addEventListener("keydown", (e) => { if (e.key === "Escape") panel.classList.remove("open"); });
  host.append(btn, panel);
}
