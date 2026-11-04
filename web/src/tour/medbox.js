// 药箱（docs/18 第九节 6，11-04 用户在五版方案里选了"药箱"）：药郎背的那只箱子，一格一格的小抽屉，斩下的执念物收进去。
//   4×3 十二格：十一只物怪各一格（按坂井家 / 万屋 / 大奥排），最后一格固定放天秤。收过的抽屉贴竖写的签条（执念物名）。
//   打开时只有一只大箱子（11-04 用户改的）；点一格收过的抽屉，抽屉拉出来，上面弹一张卡：立绘、执念物、形真理、
//   物卡那两句、魂走那句；点卡右上的叉回到箱子，再点箱子的叉关掉。没收的签条空白，点了只抖一下。
//   新收的、还没打开看过的那格签条上点一个朱点。I 键或右上"箱"钮开关；← → ↑ ↓ 换格，回车 / 空格 / E 打开那格，
//   Esc 先关卡、再关箱子。
//   立绘是游览版里用原作模型渲染的静态图（assets/processed/zukan/<id>.jpg），不用为了看册子把十一只模型都下下来。
const SEEN = "mononoke_tour_boxseen";
const ls = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

export function createMedbox({ entries, asset, audio, onOpen, onClose }) {
  const root = document.getElementById("medbox");
  const grid = root.querySelector(".mb-grid"), tray = root.querySelector(".mb-tray"), count = root.querySelector(".mb-count");
  let open = false, cardOn = false, list = [], sel = -1;
  const seen = () => { try { return new Set(JSON.parse(ls.get(SEEN) || "[]")); } catch { return new Set(); } };
  const markSeen = (id) => { const s = seen(); if (!s.has(id)) { s.add(id); ls.set(SEEN, JSON.stringify([...s])); } };

  function draw() {
    list = entries();
    const s = seen();
    count.textContent = `已收 ${list.filter((e) => e.got).length} / ${list.length}`;
    grid.innerHTML = list.map((e, i) => `<button class="mb-dr${e.got ? "" : " empty"}" data-i="${i}" aria-label="${e.got ? e.itemTitle : "空抽屉"}">`
      + `<span class="lbl">${e.got ? e.itemTitle : ""}</span>${e.got && !s.has(e.id) ? `<span class="new"></span>` : ""}<span class="ring"></span></button>`).join("")
      + `<div class="mb-dr scale">天秤</div>`;
  }
  // 选中一格（方向键走到的那格描金边）；不开卡
  function pick(i) {
    sel = i;
    grid.querySelectorAll(".mb-dr").forEach((d) => d.classList.toggle("sel", +d.dataset.i === i));
  }
  // 拉开一格：收过的出卡，没收的抖一下
  function pull(i) {
    pick(i); const e = list[i]; if (!e) return;
    const d = grid.querySelector(`.mb-dr[data-i="${i}"]`);
    if (!e.got) { d.classList.remove("shake"); void d.offsetWidth; d.classList.add("shake"); audio?.play("tick"); return; }
    grid.querySelectorAll(".mb-dr").forEach((x) => x.classList.toggle("on", x === d));
    markSeen(e.id); d.querySelector(".new")?.remove();
    tray.innerHTML = `<button class="tr-x" aria-label="收回抽屉">×</button>`
      + `<div class="tr-img"><img src="${asset(`processed/zukan/${e.id}.jpg`)}" alt="${e.name}"><span class="tr-tag">${e.itemTitle}</span></div>`
      + `<h3>${e.name}</h3><div class="meta">${e.place} · 执念物「${e.itemTitle}」</div>`
      + `<div class="row"><b>形</b>${e.katachi}</div><div class="row"><b>真</b>${e.makoto}</div><div class="row"><b>理</b>${e.kotowari}</div>`
      + `<div class="body">${e.itemBody}</div><div class="after">${e.after}</div>`;
    tray.scrollTop = 0;
    cardOn = true; root.classList.add("card"); audio?.play("paper");
  }
  function closeCard() {
    if (!cardOn) return;
    cardOn = false; root.classList.remove("card");
    grid.querySelectorAll(".mb-dr.on").forEach((x) => x.classList.remove("on"));
    audio?.play("tick");
  }
  function openBox(focusId) {
    if (open) return;
    open = true; cardOn = false; root.classList.remove("card"); draw();
    const want = focusId ? list.findIndex((e) => e.id === focusId) : -1, firstGot = list.findIndex((e) => e.got);
    pick(want >= 0 ? want : firstGot >= 0 ? firstGot : 0);
    root.classList.add("show"); document.body.classList.add("medbox-open");
    audio?.play("tick"); onOpen?.();
  }
  function closeBox() {
    if (!open) return;
    open = false; cardOn = false; root.classList.remove("show", "card"); document.body.classList.remove("medbox-open");
    audio?.play("tick"); onClose?.();
  }
  grid.addEventListener("click", (ev) => { const d = ev.target.closest(".mb-dr"); if (d?.dataset.i) pull(+d.dataset.i); });
  root.querySelector(".mb-x").addEventListener("click", closeBox);
  tray.addEventListener("click", (ev) => { if (ev.target.closest(".tr-x")) closeCard(); });
  root.addEventListener("pointerdown", (ev) => {
    ev.stopPropagation();
    if (ev.target === root) cardOn ? closeCard() : closeBox();   // 点空地：有卡先收卡，没卡关箱子
  });

  return {
    get isOpen() { return open; },
    get cardOpen() { return cardOn; },
    open: openBox, close: closeBox,
    toggle(focusId) { open ? closeBox() : openBox(focusId); },
    /** 开着的时候吃掉按键；返回 true = 用掉了 */
    key(code) {
      if (!open) return false;
      if (code === "Escape") { cardOn ? closeCard() : closeBox(); return true; }
      if (code === "KeyI") { closeBox(); return true; }
      if (code === "Enter" || code === "Space" || code === "KeyE") { cardOn ? closeCard() : pull(sel); return true; }
      const n = list.length, mv = { ArrowLeft: -1, KeyA: -1, ArrowRight: 1, KeyD: 1, ArrowUp: -4, KeyW: -4, ArrowDown: 4, KeyS: 4 }[code];
      if (mv) {
        if (cardOn) {   // 卡开着：左右翻到上 / 下一只收过的
          const step = mv > 0 ? 1 : -1;
          for (let j = sel + step; j >= 0 && j < n; j += step) if (list[j].got) { pull(j); break; }
        } else { const j = sel + mv; if (j >= 0 && j < n) { pick(j); audio?.play("tick"); } }
      }
      return true;
    },
    /** 自测用 */
    get selected() { return list[sel]; },
  };
}
