import * as THREE from "three";
import { toast, card, prompt } from "./ui.js";
import { HALO_TEX, loadMonster } from "./mononoke_fx.js";
import { mountCasebook } from "./casebook.js";
import { drawCaseCard } from "./closing.js";
import { loadNpc } from "./player.js";

// 引导与探索（11-05，docs/19_引导与探索方案.md）：给目标、不给路线。
//   每个地点一个小案子：查出这里物怪的形、真、理（地点 JSON 的 case）。线索散在観点、配角的话里，先找哪个都行；
//   三样齐了，原作那只（本命）才在指定区块现身（case.boss）。没写 case 的地点只有通用的那几样（门札、查毕、冒话、拾遗、拍照点）。
// 引导全用游戏里的东西，不出箭头和任务列表：
//   天秤朝区块里还没找的东西倾，越近晃得越快；门框贴札（隔壁还有东西没查）、查完的门札褪色；
//   一个区块里多久没找到新东西，提示一档档往上加：40 秒那边亮一下、响一声铃；90 秒一团小光飘过去停在那儿；150 秒提示条直接写一句。
//   配角走近冒一句（纸条），按 E 依次说下一句；区块查完盖"查毕"；拾遗（finds）走近才看得见；拍照点（photo）站上去拍照钮闪、照片带落款印。
// 进度存在浏览器本地（localStorage，mononoke_tour_case_<地点>），总地图读它显示进度。
//
// 地点 JSON：
//   "case": { "mononoke": "bakeneko", "boss": "ozashiki", "firstRandom": "bakeneko_ko", "npcNames": { "kayo": "加世" },
//             "clues": [{ "char": "形", "need": ["daidokoro/view:1", "daidokoro/npc:kayo"] }, ...] }
//   区块：finds: [{ id, pos: [x, z], y }]，photo: [{ pos: [x, z], r, yaw }]，bossAt: [x, z]
//         acts: [{ id, pos, face, r, anim, fx, at, props, cam }]（cam：做的时候临时换的机位 { pos, look }）（能"做"的事，格式见下面 FX 那段；docs/20）
//   case.bossReturn：本命那间是起点（大奥主廊），刚进地点那一下不出，要从别的房间回来才出；也不浮 pre
// 文案（text.json）：case.<地点> { title, hook }；act.<地点>.<id> { label, line, src(案卷里写的出处，可省) }；ready.<地点>（形真理齐了浮的那句，可省）；npc.<地点>.<配角 id> { lines: [...], clue: 下标 }；hint.<地点>.<形|真|理>；find.<地点>.<id> { title, body }
const KEY = (loc) => `mononoke_tour_case_${loc}`;
const CHARS = ["形", "真", "理"];
const HINT = [40, 90, 150];   // 秒：一档档往上加
const ls = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const SCALE_SIDE = 0.3;   // 天秤从腰前往右胯外挪多少米

/** 读某个地点的进度（总地图也用） */
export function loadCase(locId) {
  let s = null; try { s = JSON.parse(ls.get(KEY(locId)) || "null"); } catch {}
  return Object.assign({ seen: [], chars: [], ready: false, done: false, intro: false, zones: {}, totals: null }, s || {});
}

/**
 * ctx（tour.js 给）：loc texts player P scene camera audio enc stat
 *   zone() → 当前区块（resolveZone 的结果，带 id views exits stairs finds photo）
 *   npcs() → 当前区块的配角（有 id、group、pos、height）
 *   free() → 没在走剧情、没开卡、没拔剑、没物怪
 *   tags → 地面标签（出口贴札用）
 *   allViews() → Promise<{ 区块: [観名...] }>（算总数，总地图用）
 */
export function createGuide(ctx) {
  const { loc, texts, player, P, audio } = ctx;
  const C = loc.case || null;
  const S = loadCase(loc.id);
  const save = () => ls.set(KEY(loc.id), JSON.stringify(S));
  const has = (k) => S.seen.includes(k);
  const zid = () => ctx.zone()?.id;
  const names = { ...(C?.npcNames || {}) };
  const npcText = (id) => texts[`npc.${loc.id}.${id}`] || null;
  let quiet = 0, hintLv = 0, hintAt = null;

  // ---- 区块里"要找的东西"：観、带话的配角（有线索的那句要听到）、拾遗 ----
  function itemsOf(Z = ctx.zone()) {
    if (!Z) return [];
    const out = [];
    for (const [n, p] of Object.entries(Z.views || {})) out.push({ key: `${Z.id}/view:${n}`, pos: p, kind: "view" });
    for (const n of ctx.npcs()) if (n.id && npcText(n.id)) out.push({ key: `${Z.id}/npc:${n.id}`, pos: n.pos, kind: "npc", npc: n });
    for (const f of Z.finds || []) out.push({ key: `${Z.id}/find:${f.id}`, pos: f.pos, kind: "find", find: f });
    for (const a of Z.acts || []) out.push({ key: `${Z.id}/act:${a.id}`, pos: a.pos, kind: "act", act: a });   // 11-05 第二轮：坟前合掌这类"做一下"的互动
    return out;
  }
  const left = () => itemsOf().filter((it) => !has(it.key));
  // 区块"查完"：记下这个区块有哪些东西（总地图、门札要用），全看过就盖查毕
  function noteZone() {
    const Z = ctx.zone(); if (!Z) return;
    S.zones[Z.id] = itemsOf(Z).map((it) => it.key); save();
  }
  const zoneDone = (id) => { const l = S.zones[id]; return !!l && l.every(has); };

  // ---- 界面：右上三格（有案子的地点）、查毕印、冒话纸条、领路的小光 ----
  const hud = document.createElement("div"); hud.id = "case";
  if (C) { hud.innerHTML = CHARS.map((c) => `<span class="k" data-c="${c}">${c}</span>`).join(""); document.body.appendChild(hud); }
  // 没亮的字下面写查到几样（1 / 2）；先凑齐但要等前一个字的，写"等"
  const paintHud = () => hud.querySelectorAll(".k").forEach((e) => {
    const c = e.dataset.c, cl = C?.clues?.find((x) => x.char === c), got = S.chars.includes(c);
    const n = cl ? cl.need.filter(has).length : 0;
    e.classList.toggle("got", got); e.classList.toggle("part", !got && n > 0);
    e.dataset.p = got || !n ? "" : (S.held || []).includes(c) ? "等" : `${n}/${cl.need.length}`;
  });
  paintHud();
  const stampEl = document.createElement("div"); stampEl.id = "stamp"; document.body.appendChild(stampEl);
  function stamp(text) { stampEl.textContent = text; stampEl.classList.remove("go"); void stampEl.offsetWidth; stampEl.classList.add("go"); audio.play("pin"); }
  // ---- 结案札（11-06 用户："形真理了之后，有个最后结束性的说明吗？"；第二版："设计很一般……形真理之前的线索册里都有了，
  //   可以用更有深度或者引人深思的信息，然后设计的适合分享"）----
  //   本命退了、执念物卡关掉、「退魔」印盖完以后弹：一张画好的竖版札（closing.js：退魔那一刻的画面、判词、留一问、这一趟的足迹），
  //   题眼朱印晚 0.9 秒落下。钮：存图 / 分享（S）、接着逛（E / Esc）、去下一处（N；总地图上还没退魔的下一处，都退了就回总地图）
  const endEl = document.createElement("div"); endEl.id = "case-end"; document.body.appendChild(endEl);
  let endOpen = false, endTimers = [], endNext = null, endPending = 0, endCv = null, endData = null, endGen = 0;
  const free0 = ctx.free; ctx.free = () => !endOpen && free0();   // 结案札开着：不冒话、不提示、不放天秤
  if (C && !S.began) { S.began = Date.now(); save(); }   // 用时：第一次进这个地点算起
  function nextPlace() {
    const list = ctx.places?.() || [], i = list.findIndex((p) => p.id === loc.id);
    for (let k = 1; k <= list.length; k++) { const p = list[(i + k + list.length) % list.length]; if (p.id !== loc.id && !loadCase(p.id).done) return p; }
    return null;
  }
  const loadImg = (url) => new Promise((ok) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = url; setTimeout(() => ok(null), 2500); });
  async function openEnding() {
    if (!C || endOpen) return;
    const gen = ++endGen;
    const m = texts[`mononoke.${loc.id}`] || {}, cs = texts[`case.${loc.id}`] || {}, cl = texts[`close.${loc.id}`] || {};
    const views = S.seen.filter((k) => k.includes("/view:")).length, finds = S.seen.filter((k) => k.includes("/find:")).length, T = S.totals || {};
    const places = ctx.places?.() || [], no = Math.max(1, places.findIndex((p) => p.id === loc.id) + 1), mins = S.began ? Math.round((Date.now() - S.began) / 60000) : 0;
    const now = new Date(), pad = (n) => String(n).padStart(2, "0");
    endNext = nextPlace();
    endData = {
      no, place: loc.name, title: cs.title || loc.name, mononoke: m.name || "", item: m.itemTitle || "",
      end: texts[`end.${loc.id}`] || m.after || "", verdict: cl.verdict || m.after || "", question: cl.question || "", tag: cl.tag || "",
      shot: ctx.snap?.() || null, portrait: await loadImg(ctx.assetUrl(`processed/zukan/${C.mononoke}.jpg`)),
      stats: { looked: S.seen.length, views: T.views ? [views, T.views] : null, finds: T.finds ? [finds, T.finds] : null, minutes: mins > 0 && mins < 600 ? mins : 0 },
      date: `${now.getFullYear()}.${pad(now.getMonth() + 1)}.${pad(now.getDate())}`, url: "duamixu1.github.io/strange_kitty", sealed: false,
    };
    if (gen !== endGen) return;   // 等立绘的时候被关了（自测）
    const canShare = !!(ctx.touch && navigator.canShare && navigator.share);
    endEl.innerHTML = `<div class="ce-card"><canvas></canvas></div><div class="ce-btns">`
      + `<button data-a="save">${canShare ? "分享" : "存图"}<kbd>S</kbd></button><button data-a="stay">接着逛<kbd>E</kbd></button>`
      + `<button class="main" data-a="next">${endNext ? `去下一处 · ${endNext.name}` : "回总地图"}<kbd>N</kbd></button></div>`;
    endCv = drawCaseCard(endEl.querySelector("canvas"), endData);
    endEl.querySelectorAll("button").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); b.dataset.a === "save" ? saveEnding() : closeEnding(b.dataset.a); }));
    endEl.addEventListener("pointerdown", (e) => e.stopPropagation());
    endOpen = true; endEl.classList.add("show"); audio.play("paper");
    endTimers.push(setTimeout(sealEnding, 900));
    ctx.stat(`结案/${loc.id}`, `结案 · ${loc.name}`);
  }
  function sealEnding() { if (!endData || endData.sealed) return; endData.sealed = true; drawCaseCard(endCv, endData); if (endData.tag) audio.play("pin"); endEl.classList.add("sealed"); }
  function showAllEnding() { endTimers.forEach(clearTimeout); endTimers = []; sealEnding(); }
  async function saveEnding() {
    showAllEnding();
    const blob = await new Promise((ok) => endCv.toBlob(ok, "image/png")), name = `结案札_${loc.name}.png`;
    ctx.stat(`结案/${loc.id}/存图`, `结案札存图 · ${loc.name}`);
    try {
      const file = new File([blob], name, { type: "image/png" });
      if (ctx.touch && navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], title: endData.title }); return; }
    } catch (e) { if (e?.name === "AbortError") return; }
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast("结案札存好了", 2200);
  }
  function closeEnding(a) {
    clearTimeout(endPending); endGen++;   // 还没弹出来的也取消（自测斩完本命接着测别的）
    if (!endOpen) return;
    showAllEnding(); endOpen = false; endEl.classList.remove("show", "sealed");
    if (a === "next") { ctx.stat(`结案/${loc.id}/下一处`, endNext ? `去 ${endNext.name}` : "回总地图"); ctx.go?.(endNext?.id || null); return; }
    setTimeout(() => toast(ctx.touch ? "接着逛 · 想走了点右上「地图」" : "接着逛 · 想走了按 M 回总地图", 3600), 300);
  }
  // 结案札开着时的按键：S 存图；E / Esc / 空格 = 接着逛；N / Enter = 去下一处；印还没落先按一下落印
  function endKey(code) {
    if (!endOpen) return false;
    if (["KeyE", "Escape", "Space", "KeyN", "Enter", "KeyS"].includes(code) && !endData?.sealed) { showAllEnding(); return true; }
    if (code === "KeyS") saveEnding();
    else if (code === "KeyE" || code === "Escape" || code === "Space") closeEnding("stay");
    else if (code === "KeyN" || code === "Enter") closeEnding("next");
    return code !== "KeyM";   // 开着时别的键都不管（M 回总地图照旧）
  }
  const bark = document.createElement("div"); bark.id = "bark"; bark.className = "paper"; document.body.appendChild(bark);
  let barkOn = null, barkT = 0;
  function say(n, i) {
    const t = npcText(n.id); if (!t) return;
    const line = t.lines?.[i]; if (!line) return;
    barkOn = n; barkT = 4; bark.innerHTML = `<b>${names[n.id] || t.name || ""}</b>${line}`; bark.classList.add("show");
    audio.play("paper");
    n.said = i;
    if (i === (t.clue ?? 0) || !t.lines[i + 1]) mark(`${zid()}/npc:${n.id}`);
  }
  // 领路的小光（90 秒那档）：从药郎身边飘到要找的东西那儿，停在上面一闪一闪
  const haloTex = HALO_TEX();
  // 光点、墨影这些半透明贴片放一个组里，不进描边通道（不然描边把贴片画成一个个小方框）
  const fxRoot = new THREE.Group(); ctx.scene.add(fxRoot); ctx.noOutline?.(fxRoot);
  const wisp = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, opacity: 0, color: "#FFF4D6" }));
  wisp.scale.setScalar(0.6); wisp.visible = false; fxRoot.add(wisp);
  let wispTo = null, wispT = 0;
  const glint = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, opacity: 0, color: "#FFE9B0" }));
  glint.scale.setScalar(1.2); glint.visible = false; fxRoot.add(glint);
  let glintT = 0;
  // 领路的小化猫（角色线 run_k / look_back_k）：从药郎前面一点出发，顺着可走的路跑到那样东西旁边，停下回头看一眼，坐一会儿，淡掉。
  // 模型没下好就用上面那团小光
  let kit = null, kitRun = null;
  const kitLoad = ctx.loader ? loadMonster(ctx.loader, ctx.assetUrl, "kitten_guide").then((m) => { kit = m; m.group.visible = false; ctx.scene.add(m.group); m.group.traverse((o) => { if (o.isMesh && o.material.uniforms?.uPale) o.material.uniforms.uPale.value = 0.45; }); }).catch(() => {}) : null;
  function kittenTo(it) {
    if (!kit || !ctx.route) return false;
    // 起点：镜头看过去药郎前方 1.6 米左右（要在画面里），从那儿顺着可走的路跑过去
    const f = new THREE.Vector3(); ctx.camera.getWorldDirection(f); f.y = 0; f.normalize();
    const col = ctx.col(); let from = null;
    for (const d of [1.6, 1.2, 2.2, 0.9]) for (const a of [0, 0.5, -0.5, 1, -1]) {
      if (from) break; const c = Math.cos(a), sn = Math.sin(a), x = player.position.x + (f.x * c - f.z * sn) * d, z = player.position.z + (f.x * sn + f.z * c) * d;
      if (col?.canStand(x, z)) from = [x, z];
    }
    from ||= [player.position.x, player.position.z];
    const pts = ctx.route(from, [it.pos[0], it.pos[1]], 0.7);
    if (!pts || pts.length < 2) return false;
    kitRun = { pts, k: 1, t: 0, phase: "run", wait: 0 };
    const p = kitRun.pts[0]; kit.group.position.set(p[0], ctx.col()?.floorY(p[0], p[1]) ?? 0, p[1]); kit.fade = 0.01; kit.hover = 0; kit.group.visible = true; kit.play("run", 0.1);
    return true;
  }
  function kitTick(dt) {
    if (!kitRun || !kit) return;
    const R = kitRun; R.t += dt; kit.update(dt);
    if (R.phase === "run") {
      kit.fade = Math.min(1, kit.fade + dt * 3);
      const tgt = R.pts[R.k], g = kit.group.position, dx = tgt[0] - g.x, dz = tgt[1] - g.z, d = Math.hypot(dx, dz), step = 1.32 * dt;   // run_k 在 0.55 倍大小时脚不打滑的速度（角色线 11-05）
      kit.group.rotation.y = Math.atan2(dx, dz);
      if (d <= step) { g.x = tgt[0]; g.z = tgt[1]; if (++R.k >= R.pts.length) {
          // look_back_k 往它自己的左后方回头约 110°：身子转到让回过来的脸正对镜头
          R.phase = "look"; R.wait = 1.3; kit.group.rotation.y = Math.atan2(ctx.camera.position.x - g.x, ctx.camera.position.z - g.z) - 1.92; kit.play(kit.has("look_back") ? "look_back" : "idle", 0.2);
        } }
      else { g.x += (dx / d) * step; g.z += (dz / d) * step; }
      g.y = ctx.col()?.floorY(g.x, g.z) ?? g.y;
      if (R.t > 15) R.phase = "fade";
    } else if (R.phase === "look") { if ((R.wait -= dt) <= 0) { R.phase = "stay"; R.wait = 4; kit.play("idle", 0.3); } }
    else if (R.phase === "stay") { if ((R.wait -= dt) <= 0) R.phase = "fade"; }
    else { kit.fade -= dt * 1.5; if (kit.fade <= 0) { kit.group.visible = false; kitRun = null; } }
  }

  // ---- 记下找到一样东西；凑线索 ----
  function mark(k) {
    if (has(k)) return false;
    S.seen.push(k); S.last = k; if (C?.clues?.some((cl) => cl.need.includes(k))) S.lastClue = k; save();
    quiet = 0; hintLv = 0; clearHints();
    ctx.stat(`探索/${loc.id}/${k}`, `探索 · ${k}`);
    checkClues();
    const Z = ctx.zone();
    if (Z && S.zones[Z.id] && zoneDone(Z.id) && !S.stamped?.includes(Z.id)) {
      (S.stamped ||= []).push(Z.id); save();
      setTimeout(() => stamp("查毕"), 600);
      ctx.stat(`查毕/${loc.id}/${Z.id}`, `查毕 · ${Z.name || Z.id}`);
    }
    decorateExits();
    return true;
  }
  function checkClues() {
    if (!C) return;
    const m = texts[`mononoke.${loc.id}`] || {}, lines = { 形: m.katachi, 真: m.makoto, 理: m.kotowari };
    let shown = 0;
    for (const cl of C.clues || []) {
      if (S.chars.includes(cl.char) || !cl.need.every(has)) continue;
      // 11-05 第二轮（用户："我先进的大座敷……整体的逻辑要注意"）：理那句"她死在那里"要先知道真；先凑齐的字等着，弹一句往前一个字那边引
      if (cl.after && !S.chars.includes(cl.after)) {
        if (!(S.held ||= []).includes(cl.char)) { S.held.push(cl.char); save(); setTimeout(() => toast(texts[`hold.${loc.id}.${cl.char}`] || `这件事还连着别的，先去查「${cl.after}」`, 4200), 400); }
        continue;
      }
      S.chars.push(cl.char); S.held = (S.held || []).filter((c) => c !== cl.char); save();
      setTimeout(() => showChar(cl.char, lines[cl.char]), shown++ * 4000);   // 真亮了、等着的理接着亮：一个一个来
      ctx.stat(`线索/${loc.id}/${cl.char}`, `线索 · ${cl.char}`);
      if (!S.bookTold) { S.bookTold = true; save(); setTimeout(() => toast(ctx.touch ? "记进药箱的案卷了 · 点「箱」翻看" : "记进药箱的案卷了 · I 打开药箱翻看", 3600), 4200); }
    }
    paintHud();
    if (!S.ready && S.chars.length >= 3) {
      S.ready = true; save();
      const bz = loc.zones?.[C.boss]?.name || C.boss, here = zid() === C.boss;
      // 就站在本命那间里凑齐的（万屋最后一样常是大座敷里志乃的话）：不用出去再进来，提示完它就在这儿现身
      const t = here ? `形、真、理都查到了 · 铃声就在这间里` : texts[`ready.${loc.id}`] || `形、真、理都查到了 · 铃声是从${bz}那边来的`;
      setTimeout(() => { audio.play("omen"); audio.play("scaleBell", 5, 0.11); jolt = 1.6; toast(t, 5000); decorateExits(); if (here && zid() === C.boss && bossWait < 0) bossWait = 2.5; }, 3200);
      ctx.stat(`线索/${loc.id}/齐`, "形真理齐了");
    }
  }
  const charEl = document.createElement("div"); charEl.id = "clue"; document.body.appendChild(charEl);
  function showChar(c, line) {
    charEl.innerHTML = `<div class="c">${c}</div>${line ? `<div class="l paper">${line}</div>` : ""}`;
    charEl.classList.remove("show"); void charEl.offsetWidth; charEl.classList.add("show");
    audio.play("kanji", CHARS.indexOf(c));
    clearTimeout(showChar._t); showChar._t = setTimeout(() => charEl.classList.remove("show"), 3800);
  }

  // ---- 门札：隔壁没去过 / 没查完贴札；查完的褪色；本命那间在形真理齐了以后贴朱红的、一跳一跳 ----
  // 11-06 用户："笛小路家斩完物怪之后可以引导用户出到外面，看到彩色的景色之后再显示结案札"。
  //   case 写 closeAt（区块 id 列表）：本命不在这些区块里退的，退完不弹结案札，记 S.outWait，出口里往外走的那一个亮金札、
  //   别的压暗，浮一句往外走；走进 closeAt 的区块，停几秒让人看颜色，再弹
  function outNext() {
    if (!C?.closeAt) return null;
    const goal = new Set(C.closeAt), q = [[zid(), null]], seen = new Set([zid()]);
    while (q.length) {
      const [z, first] = q.shift();
      if (first && goal.has(z)) return first;
      for (const e of loc.zones?.[z]?.exits || []) if (!seen.has(e.to)) { seen.add(e.to); q.push([e.to, first || e.to]); }
    }
    return null;
  }
  const OUT_LINE = () => texts[`out.${loc.id}`] || "香散了。到外面去看看。";
  function decorateExits() {
    const Z = ctx.zone(); if (!Z) return;
    const out = S.outWait ? outNext() : null;
    (Z.exits || []).forEach((e, i) => {
      const it = ctx.tags.items.find((t) => t.id === `exit:${i}`); if (!it) return;
      if (S.outWait) { const go = e.to === out; it.el.classList.toggle("fuda", go); it.el.classList.toggle("boss", false); it.el.classList.toggle("dim", !go); return; }
      const boss = C && S.ready && !S.done && e.to === C.boss;
      const open = boss || !zoneDone(e.to);   // 没去过的也算没查完
      it.el.classList.toggle("fuda", !!open && !boss); it.el.classList.toggle("boss", !!boss); it.el.classList.toggle("dim", !open);
    });
  }

  // ---- 提示一档档往上加 ----
  function target() {
    // 先找跟还没凑齐的字有关的，再找别的；同样的话挑近的
    const L = left(); if (!L.length) return null;
    const want = new Set(C ? (C.clues || []).filter((cl) => !S.chars.includes(cl.char)).flatMap((cl) => cl.need) : []);
    const px = player.position.x, pz = player.position.z;
    L.sort((a, b) => (want.has(b.key) - want.has(a.key)) || (Math.hypot(a.pos[0] - px, a.pos[1] - pz) - Math.hypot(b.pos[0] - px, b.pos[1] - pz)));
    return L[0];
  }
  function clearHints() { wispTo = null; wisp.visible = false; glint.visible = false; if (kitRun) kitRun.phase = "fade"; if (hintAt) { prompt.set(""); hintAt = null; } }
  const at3 = (it, y = 1.3) => new THREE.Vector3(it.pos[0], (ctx.col()?.floorY(it.pos[0], it.pos[1]) ?? 0) + (it.kind === "find" ? 0.35 : y), it.pos[1]);
  function hint(lv, it) {
    if (lv === 1) { glint.position.copy(at3(it)); glint.visible = true; glintT = 0; audio.play("bell"); ctx.stat(`提示/${loc.id}/1`, "提示 · 亮一下"); }
    if (lv === 2 && castScales(true)) { ctx.stat(`提示/${loc.id}/2`, "提示 · 天秤自己指"); return; }   // 11-06：第二档改成天秤（小化猫领路留着当后备）
    if (lv === 2 && kittenTo(it)) { ctx.stat(`提示/${loc.id}/2`, "提示 · 小化猫领路"); return; }
    if (lv === 2) { wisp.position.copy(player.position).setY(player.position.y + 1.2); wisp.visible = true; wispTo = at3(it, 1.1); wispT = 0; ctx.stat(`提示/${loc.id}/2`, "提示 · 小光领路"); }
    if (lv === 3) {
      const cl = C?.clues?.find((c) => !S.chars.includes(c.char) && c.need.includes(it.key));
      const zn = (k) => loc.zones?.[k.split("/")[0]]?.name;
      const t = (cl && texts[`hint.${loc.id}.${cl.char}`]) || (it.kind === "find" ? "这里好像还掉着什么" : it.kind === "npc" ? `${names[it.npc?.id] || "那个人"}好像有话要说` : `${zn(it.key) || "这里"}还有一处没看`);
      hintAt = t; prompt.set(t); setTimeout(() => { if (hintAt === t) { prompt.set(""); hintAt = null; } }, 6000);
      ctx.stat(`提示/${loc.id}/3`, "提示 · 直接说");
    }
  }

  // ---- 能"做"的事（acts）、拾遗、拍照点 ----
  const actNear = (r) => !acting && (ctx.zone()?.acts || []).find((a) => !has(`${zid()}/act:${a.id}`) && Math.hypot(a.pos[0] - player.position.x, a.pos[1] - player.position.z) < (r ?? a.r ?? 1.0));
  const actText = (a) => texts[`act.${loc.id}.${a.id}`] || {};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // 11-05 docs/20：act 可以写 anim（药郎的动作）、fx（效果，可以几样一起）、at（效果的位置）、props（摆在旁边、会动的小积木）。
  //   fx：incense 线香 + 一小团魂光（坂井家坟前，默认）/ steps 头顶一串小脚步 + 镜头一抖 + 廊下尽头小黑影一闪 / pinwheel 风车转起来
  //       peek 井水里浮起几样东西的影子 / open 拉开拉门、里面的东西露出来 / kasa 收着的伞自己撑开半圈又合上
  //   props：[{ kit, pos: [x, z], y, yaw, move: kasa|slide|spin, dist, show: "after" }]，加载法跟拾遗一样（processed/kit/<kit>.glb）
  const DEF_LINE = { incense: "坟很小，小得不像是给人立的。", steps: "头顶的楼板上，有一串很轻的脚步跑过去。", pinwheel: "没有风，风车自己转了起来。",
    peek: "井水晃了一下，底下有东西浮上来，又沉下去了。", open: "柜子里是湿的。", kasa: "伞自己撑开了半圈，又慢慢合上。" };
  const DEF_SEC = { steps: 3.4, peek: 3.6, open: 3.0, kasa: 3.2, biwa: 7.2, fuda: 3.2, utsuro: 3.4 };
  const tweens = [];
  const tween = (dur, fn, delay = 0) => new Promise((done) => tweens.push({ t: -delay, dur, fn, done }));
  function tweenTick(dt) { for (const w of tweens.slice()) { w.t += dt; if (w.t < 0) continue; const k = Math.min(1, w.t / w.dur); w.fn(k); if (k >= 1) { tweens.splice(tweens.indexOf(w), 1); w.done(); } } }
  const ease = (k) => k * k * (3 - 2 * k);
  async function doAct(a) {
    if (acting) return; acting = true;
    const t = actText(a), face = a.face || a.pos, fxs = [].concat(a.fx || "incense");
    const anim = a.anim && P.has(a.anim) ? a.anim : P.has("seal_k") ? "seal_k" : "nod_k";
    if (a.cam) ctx.shot?.(a.cam);
    ctx.perform(anim, a.sec || Math.max(2.8, ...fxs.map((f) => DEF_SEC[f] || 0)), Math.atan2(face[0] - player.position.x, face[1] - player.position.z));
    await sleep(700);
    await Promise.all(fxs.map((f) => FX[f]?.(a, face)));   // 几样效果一起放，都放到该浮那句话的时候
    showLine(t.line || DEF_LINE[fxs[0]] || "……"); audio.play("release", 1);
    await sleep(3600);   // 那句看完，再记线索（字要浮起来的话不跟这句抢）
    if (a.cam) ctx.shot?.(null);
    mark(`${zid()}/act:${a.id}`); acting = false;
  }
  const floorAt = (x, z) => ctx.col()?.floorY(x, z) ?? 0;
  const at3v = (v, dy = 0) => v.length === 3 ? new THREE.Vector3(v[0], v[1] + dy, v[2]) : new THREE.Vector3(v[0], floorAt(v[0], v[1]) + dy, v[1]);
  const propsOf = (a) => (propsOn?.items || []).filter((it) => it.a === a);
  // 池里浮起的人（听琵琶）：配角模型换成幽蓝半透明、不受光的材质；第一次用时才下，下过留着
  const ghosts = new Map();
  function ghostOf(a) {
    const model = a.ghost || "processed/asa_posed_lite.glb";
    if (!ghosts.has(model)) ghosts.set(model, ctx.loader ? loadNpc(ctx.loader, ctx.assetUrl, { model, height: a.ghostH || 1.45 }).then((n) => {
      const mats = [];
      n.group.traverse((o) => {
        if (!o.isMesh) return;
        const m = new THREE.MeshBasicMaterial({ map: o.material.uniforms?.map?.value || o.material.map || null, color: "#9CC2EC", transparent: true, opacity: 0, depthWrite: true });
        o.material = m; o.renderOrder = 3; mats.push(m);
      });
      return { n, mats };
    }).catch(() => null) : Promise.resolve(null));
    return ghosts.get(model);
  }
  const FX = {
    async incense(a, face) {   // 坂井家坟前合掌（原来那套）
      const fy = floorAt(face[0], face[1]);
      audio.play("bell");
      for (let i = 0; i < 10; i++) motes.push({ sp: mote(0x9a948c, 0.12), at: new THREE.Vector3(face[0] + (Math.random() - 0.5) * 0.08, fy + 0.25, face[1] + (Math.random() - 0.5) * 0.08), t: -i * 0.25, life: 2.6, rise: 0.35, drift: 0.12 });
      motes.push({ sp: mote(0xFFF1CF, 0.4), at: new THREE.Vector3(face[0], fy + 0.35, face[1]), t: -0.6, life: 4, rise: 0.3, drift: 0.05, soul: true });
      await sleep(1200);
    },
    async steps(a) {   // 头顶一串小脚步：从一头跑到另一头，声音一下一下挪过去；镜头一抖；前面一个小黑影钻进襖里
      const n = 7;
      for (let i = 0; i < n; i++) setTimeout(() => { audio.play("step", "wood", 0.35 + 0.25 * Math.sin((i / (n - 1)) * Math.PI)); }, i * 190);
      setTimeout(() => ctx.shake?.(0.14), 500);
      await sleep(1300);
      if (a.at) {
        const p = at3v(a.at, 0.6), sp = inkSprite("child", 0.7, 1.2); sp.material.color.set("#050308"); sp.position.copy(p); fxRoot.add(sp);
        // 从走廊中间跑向 at 那扇襖、钻进去没了（at 写在门边 / 墙边）：方向取 at 偏离药郎视线的那一侧
        const look = new THREE.Vector3().subVectors(p, player.position).setY(0), fwd = new THREE.Vector3(Math.sin(player.rotation.y), 0, Math.cos(player.rotation.y));
        let dir = look.clone().addScaledVector(fwd, -look.dot(fwd));
        if (dir.lengthSq() < 0.04) dir = new THREE.Vector3(fwd.z, 0, -fwd.x); dir.normalize();
        audio.play("dodge");
        tween(0.9, (k) => { sp.position.copy(p).addScaledVector(dir, -1.0 + ease(k) * 1.1); sp.material.opacity = Math.min(1, Math.sin(k * Math.PI) * 1.6); }).then(() => { fxRoot.remove(sp); sp.material.dispose(); });
      }
      await sleep(600);
    },
    async pinwheel(a) {   // 风车：没有风，自己转起来，转快了再慢慢停
      audio.play("bell", 1660, 0.08);
      for (const it of propsOf(a).filter((x) => x.p.move === "spin")) {
        const g = it.g, dur = 4.2; let lk = 0;   // 转速：一秒里涨到最快（一秒转两圈），再慢慢停
        tween(dur, (k) => { const v = k < 0.25 ? k / 0.25 : (1 - (k - 0.25) / 0.75) ** 2; g.rotation.z += v * 12.5 * (k - lk) * dur; lk = k; });
        const c = g.getWorldPosition(new THREE.Vector3());
        for (let i = 0; i < 5; i++) motes.push({ sp: mote(0xFFE3C0, 0.14), at: c.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.3, 0, (Math.random() - 0.5) * 0.3)), t: -0.3 - i * 0.35, life: 2.4, rise: 0.25, drift: 0.1 });
      }
      await sleep(1400);
    },
    async peek(a, face) {   // 往井里看：井水面上一样一样浮起梳子、信、小人偶的影子，一晃就散
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 0.6);
      audio.play("bell", 740, 0.12);
      ["comb", "letter", "doll"].forEach((kind, i) => {
        // 从水面一路浮到井沿上面一点（镜头多半比井沿低，只在水面上会被井沿挡住）
        const sp = inkSprite(kind, 0.42, 0.42), o = new THREE.Vector3((i - 1) * 0.2, 0.15, (Math.random() - 0.5) * 0.12); sp.material.color.set("#EEF4FA"); fxRoot.add(sp);
        tween(2.4, (k) => { sp.position.copy(p).add(o).add(new THREE.Vector3(Math.sin(k * 6 + i) * 0.03, ease(k) * 0.5, 0)); sp.material.opacity = Math.sin(k * Math.PI) * 0.95; }, i * 0.55).then(() => { fxRoot.remove(sp); sp.material.dispose(); });
        motes.push({ sp: mote(0xCFE2FF, 0.3), at: p.clone().add(o), t: -i * 0.55, life: 2.4, rise: 0.22, drift: 0.02 });
      });
      await sleep(2000);
    },
    async open(a) {   // 打开柜子：拉门滑开，里面那排东西露出来
      audio.play("slide", 0.7);
      for (const it of propsOf(a)) {
        if (it.p.move === "slide") { const from = it.g.position.clone(), to = from.clone().add(slideVec(it.p)); tween(0.8, (k) => it.g.position.lerpVectors(from, to, ease(k))); }
        if (it.p.show === "after") { it.g.visible = true; it.g.scale.setScalar(0.001); tween(0.5, (k) => it.g.scale.setScalar(0.85 + 0.15 * ease(k)), 0.5); }
      }
      await sleep(1400);
    },
    // ---- そらりす丸（11-06）----
    async biwa(a, face) {   // 听琵琶：池边响起琵琶，池水里浮起一个女孩，晃一晃就沉回去（海座头是源慧的分身）
      // 11-06 用户：先是"没看见女孩"，换成大一号的模糊贴图又说"太抽象太简陋，像个 icon"。改用真人模型（a.ghost，默认借大奥阿浅的模型），
      // 去掉描边、染成半透明幽蓝，从水下一点点浮出来、在水面上站一会儿（播待机），再沉回去；act 带机位隔池对着拍（solaris.json）
      audio.play("biwa");
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 0.1);
      const gp = ghostOf(a);
      await sleep(900);
      for (let i = 0; i < 5; i++) motes.push({ sp: mote(0xCFE2F4, 0.5 + i * 0.3), at: p.clone().add(new THREE.Vector3(0, 0.22, 0)), t: -i * 0.5, life: 2.0, rise: 0.02, drift: 0 });
      const g = await Promise.race([gp, sleep(2500).then(() => null)]);
      if (g) {
        const { n, mats } = g, root = n.group; root.position.copy(p); root.position.y = p.y - 1.5;
        const cp = a.cam?.pos ? new THREE.Vector3(...a.cam.pos) : ctx.camera.position; root.rotation.y = Math.atan2(cp.x - p.x, cp.z - p.z);   // 朝着镜头，脸看得见
        fxRoot.add(root); let lk = 0;
        await tween(5.2, (k) => {
          n.update((k - lk) * 5.2); lk = k;
          const up = ease(Math.min(1, k / 0.35)), down = k > 0.8 ? ease((k - 0.8) / 0.2) : 0;
          root.position.y = p.y - 1.5 + up * 1.45 - down * 1.2 + Math.sin(k * 7) * 0.02;
          const o = Math.min(1, k / 0.2) * (1 - down) * 0.75; for (const m of mats) m.opacity = o;
        });
        fxRoot.remove(root);
      } else {   // 模型没下来：退回原来的影子
        const sp = inkSprite("child", 0.75, 1.25); sp.material.color.set("#DCE8F2"); fxRoot.add(sp);
        await tween(4, (k) => { sp.position.copy(p).add(new THREE.Vector3(0, 0.3 + ease(k) * 0.5, 0)); sp.material.opacity = Math.sin(k * Math.PI) * 0.85; });
        fxRoot.remove(sp); sp.material.dispose();
      }
      for (let i = 0; i < 8; i++) motes.push({ sp: mote(0xBFD8F0, 0.18), at: p.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.9, 0.3, (Math.random() - 0.5) * 0.9)), t: -i * 0.2, life: 2.2, rise: 0.25, drift: 0.04 });
      await sleep(600);
    },
    async fuda(a, face) {   // 札墙：墙上的札一齐翻动，几张从墙上掀起来，朝 a.to（那扇门，源慧的房间）飘过去
      const p = at3v(a.at || face, 0), to = a.to ? at3v(a.to, 1.2) : p.clone().add(new THREE.Vector3(1.5, 0, 0));
      for (let i = 0; i < 4; i++) setTimeout(() => audio.play("paper"), i * 160);
      ctx.shake?.(0.06);
      for (let i = 0; i < 6; i++) {
        const sp = inkSprite("letter", 0.16, 0.32); sp.material.color.set("#F3EAD6"); fxRoot.add(sp);
        const from = p.clone().add(new THREE.Vector3(0, (Math.random() - 0.5) * 0.8, (Math.random() - 0.5) * 1.4));
        tween(1.6, (k) => { sp.position.lerpVectors(from, to, ease(k)).add(new THREE.Vector3(0, Math.sin(k * 9 + i) * 0.08, 0)); sp.material.opacity = Math.sin(k * Math.PI) * 0.95; }, 0.2 + i * 0.12).then(() => { fxRoot.remove(sp); sp.material.dispose(); });
      }
      await sleep(2200);
    },
    async utsuro(a, face) {   // 看虚舟：封板的缝里吐出一口冷气，里面空空的，只有一点青光升起来又散了
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 0.4);
      audio.play("slide", 0.9); await sleep(600);
      audio.play("bell", 620, 0.1);
      for (let i = 0; i < 12; i++) motes.push({ sp: mote(0x6E7F90, 0.35), at: p.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.6, 0, (Math.random() - 0.5) * 0.6)), t: -i * 0.12, life: 2.4, rise: 0.25, drift: 0.2 });
      motes.push({ sp: mote(0xCFE6FF, 0.5), at: p.clone().add(new THREE.Vector3(0, 0.3, 0)), t: -0.8, life: 3, rise: 0.35, drift: 0.05, soul: true });
      await sleep(1800);
    },
    // ---- 地铁（11-06）----
    async senro(a, face) {   // 看铁轨：枕木上那块暗色旧印子慢慢渗出来，旁边一串小小的猫脚印一个个亮起、往南走远
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 0.02);
      audio.play("bell", 520, 0.1);
      const stain = inkSprite("doll", 0.7, 0.45); stain.material.color.set("#3A1418"); stain.position.copy(p).add(new THREE.Vector3(0, 0.03, 0)); fxRoot.add(stain);
      tween(1.6, (k) => { stain.material.opacity = 0.75 * ease(k); }).then(() => sleep(2600)).then(() => tween(0.8, (k) => { stain.material.opacity = 0.75 * (1 - k); })).then(() => { fxRoot.remove(stain); stain.material.dispose(); });
      for (let i = 0; i < 7; i++) {   // 猫脚印：左右交替，往 +z（南）走远
        const sp = inkSprite("child", 0.09, 0.09); sp.material.color.set("#1A1622"); fxRoot.add(sp);
        sp.position.copy(p).add(new THREE.Vector3((i % 2 ? 0.08 : -0.08) + 0.4, 0.04, 0.3 + i * 0.32));
        tween(0.3, (k) => { sp.material.opacity = 0.8 * k; }, 0.9 + i * 0.25).then(() => sleep(2400 - i * 200)).then(() => tween(0.6, (k) => { sp.material.opacity = 0.8 * (1 - k); })).then(() => { fxRoot.remove(sp); sp.material.dispose(); });
      }
      await sleep(2400);
    },
    async shinbun(a, face) {   // 看报：报纸被一阵风掀开一角，左下角那一小块慢慢浮起来、发着冷光，又落回去
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 1.0);
      audio.play("paper"); setTimeout(() => audio.play("paper"), 260);
      const sp = inkSprite("letter", 0.3, 0.24); sp.material.color.set("#F3EEDF"); fxRoot.add(sp);
      tween(2.6, (k) => { sp.position.copy(p).add(new THREE.Vector3(0, 0.05 + Math.sin(k * Math.PI) * 0.35, 0)); sp.material.opacity = Math.sin(k * Math.PI) * 0.95; }).then(() => { fxRoot.remove(sp); sp.material.dispose(); });
      motes.push({ sp: mote(0xDDE6F2, 0.3), at: p.clone().add(new THREE.Vector3(0, 0.25, 0)), t: -0.4, life: 2.4, rise: 0.1, drift: 0.02 });
      await sleep(2000);
    },
    // ---- 牢房（11-06）----
    async door(a, face) {   // 推牢门：格子门吱呀一声自己让开半扇——锁从来没挂上；门缝里漏出一线白光，一点光尘往外飘
      const p = at3v(a.at || face, a.at?.length === 3 ? 0 : 1.0);
      audio.play("slide", 1.4); setTimeout(() => audio.play("slide", 0.6), 500);
      for (const it of propsOf(a)) if (it.p.move === "slide") { const from = it.g.position.clone(), to = from.clone().add(slideVec(it.p)); tween(1.2, (k) => it.g.position.lerpVectors(from, to, ease(k))); }
      await sleep(700);
      for (let i = 0; i < 8; i++) motes.push({ sp: mote(0xF4EEDC, 0.16), at: p.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.3, (Math.random() - 0.5) * 0.8, (Math.random() - 0.5) * 0.3)), t: -i * 0.18, life: 2.6, rise: 0.08, drift: 0.25 });
      motes.push({ sp: mote(0xFFF6E0, 0.7), at: p.clone(), t: -0.2, life: 2.8, rise: 0.02, drift: 0.02, soul: true });
      await sleep(1600);
    },
    async kasa(a) {   // 收着的伞"啪"地撑开半圈，停一停，又慢慢合上
      const ks = propsOf(a).filter((x) => x.p.move === "kasa");
      await sleep(400);
      audio.play("jump"); audio.play("paper");
      for (const it of ks) {
        const g = it.g, open = it.p.open ?? 0.7;
        tween(0.28, (k) => g.scale.set(0.2 + (open - 0.2) * ease(k), 1, 0.2 + (open - 0.2) * ease(k)))
          .then(() => sleep(1100)).then(() => tween(2.2, (k) => g.scale.set(open - (open - 0.2) * ease(k), 1, open - (open - 0.2) * ease(k))));
      }
      await sleep(1000);
    },
  };
  const slideVec = (p) => new THREE.Vector3(p.dist ?? 0.5, 0, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), p.yaw || 0);
  // 墨影（小黑影、井里的影子）：程序画在 canvas 上，边缘糊一点
  const inkTex = {};
  function inkSprite(kind, w, h) {
    if (!inkTex[kind]) {
      const c = document.createElement("canvas"); c.width = 128; c.height = 128; const g = c.getContext("2d");
      g.filter = "blur(3px)"; g.fillStyle = "#fff"; g.strokeStyle = "#fff"; g.lineWidth = 6;
      if (kind === "child") { g.beginPath(); g.arc(64, 30, 17, 0, 7); g.fill(); g.beginPath(); g.moveTo(44, 50); g.lineTo(84, 50); g.lineTo(96, 120); g.lineTo(32, 120); g.closePath(); g.fill(); }
      else if (kind === "comb") { g.beginPath(); g.ellipse(64, 60, 46, 22, 0, Math.PI, 0); g.fill(); for (let x = 22; x <= 106; x += 9) g.fillRect(x, 58, 4, 26); }
      else if (kind === "letter") { g.fillRect(28, 30, 72, 70); g.globalCompositeOperation = "destination-out"; for (let y = 44; y < 92; y += 12) g.fillRect(38, y, 52, 3); }
      else { g.beginPath(); g.arc(64, 34, 20, 0, 7); g.fill(); g.beginPath(); g.ellipse(64, 86, 26, 36, 0, 0, 7); g.fill(); }
      inkTex[kind] = new THREE.CanvasTexture(c);
    }
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: inkTex[kind], color: "#1A1622", transparent: true, depthWrite: false, opacity: 0 }));
    sp.scale.set(w, h, 1); return sp;
  }
  // 区块里 act 的小积木：进区块摆上（同一区块只下一次），按做没做过摆成"之前"或"之后"的样子
  const propCache = new Map(); let propsOn = null;
  async function mountProps() {
    const Z = ctx.zone(); if (propsOn) { ctx.scene.remove(propsOn.grp); propsOn = null; }
    const list = (Z?.acts || []).flatMap((a) => (a.props || []).map((p) => ({ a, p })));
    if (!list.length || !ctx.loadKit) return;
    if (!propCache.has(Z.id)) propCache.set(Z.id, Promise.all(list.map(({ a, p }) => ctx.loadKit(p.kit).then((g) => ({ a, p, g })).catch(() => null)))
      .then((l) => { const grp = new THREE.Group(), items = l.filter(Boolean); items.forEach((i) => grp.add(i.g)); return { grp, items }; }));
    const o = await propCache.get(Z.id); if (ctx.zone()?.id !== Z.id) return;
    propsOn = o; ctx.scene.add(o.grp);
    for (const { a, p, g } of o.items) {
      const done = has(`${Z.id}/act:${a.id}`);
      g.position.set(p.pos[0], floorAt(p.pos[0], p.pos[1]) + (p.y || 0), p.pos[1]); g.rotation.set(0, p.yaw || 0, 0); g.scale.setScalar(1);
      if (p.move === "kasa") g.scale.set(0.2, 1, 0.2);
      if (p.move === "slide" && done) g.position.add(slideVec(p));
      g.visible = p.show !== "after" || done;
    }
  }
  let acting = false;
  const motes = [];
  function mote(color, size) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, opacity: 0, color })); sp.scale.setScalar(size); fxRoot.add(sp); return sp; }
  function moteTick(dt) {
    for (const m of motes.slice()) {
      m.t += dt; if (m.t < 0) continue; const k = m.t / m.life;
      m.sp.position.copy(m.at).add(new THREE.Vector3(Math.sin(m.t * 1.7 + m.life) * m.drift, m.t * m.rise, Math.cos(m.t * 1.3) * m.drift));
      m.sp.material.opacity = (k < 0.2 ? k / 0.2 : 1 - (k - 0.2) / 0.8) * (m.soul ? 0.95 : 0.5); m.sp.scale.setScalar(m.size || (m.soul ? 0.4 : 0.12) * (1 + k * (m.soul ? 0.2 : 2)));
      if (k >= 1) { fxRoot.remove(m.sp); m.sp.material.dispose(); motes.splice(motes.indexOf(m), 1); }
    }
  }
  function showLine(line) {
    charEl.innerHTML = `<div class="l paper">${line}</div>`;
    charEl.classList.remove("show"); void charEl.offsetWidth; charEl.classList.add("show");
    clearTimeout(showChar._t); showChar._t = setTimeout(() => charEl.classList.remove("show"), 3800);
  }
  const findNear = (r = 1.1) => (ctx.zone()?.finds || []).find((f) => !has(`${zid()}/find:${f.id}`) && Math.hypot(f.pos[0] - player.position.x, f.pos[1] - player.position.z) < r);
  const photoAt = () => (ctx.zone()?.photo || []).findIndex((p) => Math.hypot(p.pos[0] - player.position.x, p.pos[1] - player.position.z) < (p.r || 0.8));
  const npcNear = (r = 2) => { let best = null, bd = r; for (const n of ctx.npcs()) { if (!n.id || !npcText(n.id)) continue; const d = Math.hypot(n.pos[0] - player.position.x, n.pos[1] - player.position.z); if (d < bd) { bd = d; best = n; } } return best; };
  let findTags = [];
  function addFindTags() {
    findTags = [];
    for (const f of ctx.zone()?.finds || []) {
      if (has(`${zid()}/find:${f.id}`)) continue;
      const id = `find:${f.id}`; ctx.tags.add(id, "find", "拾", [f.pos[0], (f.y ?? 0) + 0.5, f.pos[1]]);
      findTags.push({ f, it: ctx.tags.items.at(-1) });
    }
  }
  async function pickUp(f) {
    const t = texts[`find.${loc.id}.${f.id}`] || { title: "拾遗", body: "（文案待写：text.json find." + loc.id + "." + f.id + "）" };
    const all = Object.values(loc.zones || {}).reduce((a, z) => a + (z.finds?.length || 0), 0);
    mark(`${zid()}/find:${f.id}`);
    const got = S.seen.filter((k) => k.includes("/find:")).length;
    findTags.find((x) => x.f === f)?.it.el.remove();
    audio.play("bell");
    const cs = closeShot(f);
    ctx.shot?.(cs);
    player.rotation.y = Math.atan2(cs.look[0] - player.position.x, cs.look[2] - player.position.z) || player.rotation.y;   // 药郎转过去看着它
    P.play("gaze", 0.4);
    await card.open({ place: `拾遗 · ${loc.name} ${got} / ${all}`, title: t.title, body: t.body });
    ctx.shot?.(null); P.play("idle", 0.4);
    audio.play("paper");
  }
  // 拾遗特写（11-06 用户："这里其实可以给特写"）：对准小物件的包围盒，从当前镜头那一侧斜着拍，稍微俯看。
  // 镜头不能穿进柱子、墙（ctx.camRay 打碰撞网格），药郎不能挡在镜头和物件之间；说明卡盖住下半屏，所以把物件放在画面上方
  const CLOSE_FOV = 34;
  function closeShot(f) {
    const g = ctx.findObj?.(f), c = new THREE.Vector3(), size = new THREE.Vector3();
    if (g) { const b = new THREE.Box3().setFromObject(g); if (!b.isEmpty()) { b.getCenter(c); b.getSize(size); } }
    if (!size.lengthSq()) { c.copy(at3v(f.pos, (f.y || 0) + 0.15)); size.set(0.3, 0.3, 0.3); }
    const r = THREE.MathUtils.clamp(Math.max(size.x, size.y, size.z) / 2, 0.12, 0.6), half = THREE.MathUtils.degToRad(CLOSE_FOV / 2);
    const want = THREE.MathUtils.clamp(r / Math.tan(half) * 1.8, 0.6, 1.6);
    const pitch = c.y < 1.0 ? 0.5 : 0.2;   // 地上、柱脚的东西多往下看一点
    const cam = ctx.camera.position, base = Math.atan2(cam.x - c.x, cam.z - c.z), P0 = player.position;
    let best = null;
    for (const da of [0.55, -0.55, 0.95, -0.95, 0, 1.35, -1.35, 1.8, -1.8, Math.PI]) {
      const a = base + da, dir = new THREE.Vector3(Math.sin(a) * Math.cos(pitch), Math.sin(pitch), Math.cos(a) * Math.cos(pitch));
      let d = want;
      const hit = ctx.camRay?.(c, c.clone().addScaledVector(dir, want + 0.15));
      if (hit != null) { if (hit < 0.55) continue; d = Math.min(d, hit - 0.15); }
      const pos = c.clone().addScaledVector(dir, d);
      // 药郎挡不挡：镜头到物件这段（水平）离他身体轴线多近，在那个位置上这段线有多高
      const sx = pos.x - c.x, sz = pos.z - c.z, L2 = sx * sx + sz * sz || 1e-6;
      const s = THREE.MathUtils.clamp(((P0.x - c.x) * sx + (P0.z - c.z) * sz) / L2, 0, 1);
      const near = Math.hypot(c.x + sx * s - P0.x, c.z + sz * s - P0.z), yAt = c.y + (pos.y - c.y) * s - P0.y;
      if (near < 0.35 && yAt < 1.8) continue;
      best = { pos, d }; break;
    }
    if (!best) best = { pos: c.clone().add(new THREE.Vector3(Math.sin(base) * 0.9, 0.6, Math.cos(base) * 0.9)), d: 1 };
    // 看点往下挪：物件落在画面上方约 1/3 处，避开说明卡
    const look = c.clone(); look.y -= best.d * Math.tan(half) * 0.42 / Math.cos(pitch);
    return { pos: best.pos.toArray(), look: look.toArray(), fov: CLOSE_FOV, close: true };
  }

  // ---- 放天秤（11-06，用户："它作为线索的作用比较弱"）：照原作，药郎把天秤放出去，沿着走得通的路一只接一只立起来，
  //   都朝下一只歪，最后一只指着要找的东西；铃声从近到远一个个响过去，6 秒后淡掉。指谁：这间里先找跟没亮的字有关的；
  //   这间查完了指还有东西没查的那扇门；形真理齐了指本命那间的门。T / 「秤」放，歇 8 秒；第二档提示也是它（auto，不做动作）
  const CAST_CD = 8, CAST_LIFE = 6;
  let castCd = 0; const cast = [];
  function castTarget() {
    const it = left().length ? target() : null;
    if (it) return { pos: it.pos, what: "here" };
    const Z = ctx.zone(); if (!Z) return null;
    const ex = (Z.exits || []).map((e) => ({ e, s: Z.stairs?.[e.stair] })).filter((x) => x.s);
    const pick = (C && S.ready && !S.done && ex.find((x) => x.e.to === C.boss)) || ex.find((x) => !zoneDone(x.e.to));
    return pick ? { pos: pick.s.stand, what: pick.e.to === C?.boss && S.ready ? "boss" : "door" } : null;
  }
  function castScales(auto = false) {
    const scaleProp = P.props.find((p) => p.id === "scale")?.prop;
    if (!scaleProp || (!auto && castCd > 0)) return false;
    const tg = castTarget();
    if (!tg) { if (!auto) toast("天秤一动不动 · 这一带没有要找的了", 2600); return false; }
    const from = [player.position.x, player.position.z];
    let pts = ctx.route?.(from, [tg.pos[0], tg.pos[1]], 0.6);
    if (!pts || pts.length < 2) pts = [from, [tg.pos[0], tg.pos[1]]];
    // 沿路每隔 1.1 米一只，最多 5 只；最后一只停在离目标 0.6 米处
    const seg = []; let total = 0;
    for (let i = 1; i < pts.length; i++) { const L = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(L); total += L; }
    const at = (d) => { let k = 0; while (k < seg.length - 1 && d > seg[k]) { d -= seg[k]; k++; } const t = seg[k] ? Math.min(1, d / seg[k]) : 0; return [pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t]; };
    // 从药郎前方 1.4 米起（近了会和他叠在一起），每隔约 1.2 米一只，最多 5 只；最后一只停在离目标 0.6 米处
    if (tg.what === "here" && total < 1.2) {   // 就在脚边（提示条已经能按 E）：不放了，铃一响、说一句
      audio.play("scaleBell", 2, 0.07); toast(ctx.touch ? "天秤指着跟前 · 点提示条看看" : "天秤指着跟前 · 按 E 看看", 2600);
      if (!auto) castCd = 2; return true;
    }
    const near = total < 2.2;   // 就在跟前：只在那样东西正上方立一只
    const end = Math.max(0.6, total - 0.6), first = Math.min(1.4, end), n = near ? 1 : Math.max(1, Math.min(5, Math.round((end - first) / 1.2) + 1));
    const spots = near ? [[tg.pos[0], tg.pos[1]]] : Array.from({ length: n }, (_, i) => at(n === 1 ? end : first + (end - first) * (i / (n - 1))));
    clearCast();
    // 天秤模型自己的坐标就是端正的（横梁沿 X 摊开、秤盘往下垂）：正面朝镜头立着，横梁才看得清；
    //   往下一只在画面哪一侧就往哪侧歪（绕自身 Z），一路直直往里走时只微微晃。
    //   自己放的：镜头会转到药郎身后、朝第一只看（perform 的 camAim），所以按那个方向摆正面
    const f = new THREE.Vector3(); ctx.camera.getWorldDirection(f);
    if (!auto && ctx.followCam?.()) f.set(spots[0][0] - player.position.x, 0, spots[0][1] - player.position.z);
    f.y = 0; if (f.lengthSq() < 1e-6) ctx.camera.getWorldDirection(f).setY(0); f.normalize();
    const yaw = Math.atan2(-f.x, -f.z), right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
    spots.forEach((p, i) => {
      const nx = i < n - 1 ? spots[i + 1] : tg.pos, d = new THREE.Vector3(nx[0] - p[0], 0, nx[1] - p[1]);
      const lat = d.lengthSq() > 1e-6 ? d.normalize().dot(right) : 0;
      const g = scaleProp.clone(true); g.position.set(0, 0, 0); g.rotation.set(0, 0, 0); g.scale.setScalar(2.6);
      const tilter = new THREE.Group(), holder = new THREE.Group(); tilter.add(g); holder.add(tilter); ctx.scene.add(holder);
      // 身后衬一团淡淡的暖光（不进描边），屋里花样多的地方也看得出一只只
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, opacity: 0, color: "#FFF1CF" })); halo.scale.setScalar(0.9); fxRoot.add(halo);
      holder.updateMatrixWorld(true);
      const c = new THREE.Box3().setFromObject(g).getCenter(new THREE.Vector3()); g.position.sub(c);   // 绕天秤中心歪
      holder.position.set(p[0], floorAt(p[0], p[1]) + (near ? 1.7 : 1.3), p[1]);
      holder.rotation.y = yaw;
      tilter.scale.setScalar(0.001);
      halo.position.copy(holder.position).addScaledVector(f, 0.15);
      cast.push({ holder, g: tilter, halo, t: -i * 0.35 - (auto ? 0 : 0.5), i, rang: false, axis: "z", tilt: -0.5 * lat });
    });
    if (!auto) {
      castCd = CAST_CD; document.body.classList.add("cast-cd");
      ctx.perform(P.has("reach_k") ? "reach_k" : "nod_k", 0.9, Math.atan2(spots[0][0] - player.position.x, spots[0][1] - player.position.z));
      audio.play("paper");
    }
    if (!auto) quiet = 0;   // 自己放的才重新计时；第二档自动放的不清零，不然第三档要再等 150 秒
    ctx.stat(`天秤/${loc.id}/${auto ? "auto" : "T"}`, auto ? "天秤 · 自己指" : "天秤 · 放出");
    return true;
  }
  function clearCast() { for (const c of cast) { ctx.scene.remove(c.holder); fxRoot.remove(c.halo); c.halo.material.dispose(); } cast.length = 0; }
  function castTick(dt) {
    if (castCd > 0 && (castCd -= dt) <= 0) document.body.classList.remove("cast-cd");
    for (const c of cast) {
      c.t += dt; if (c.t < 0) continue;
      const k = c.t, grow = Math.min(1, k / 0.25), fade = k > CAST_LIFE ? Math.max(0, 1 - (k - CAST_LIFE) / 0.6) : 1;
      if (!c.rang) { c.rang = true; audio.play("scaleBell", 1, 0.06 + c.i * 0.008); }
      c.g.scale.setScalar(Math.max(0.001, grow * fade));
      c.halo.material.opacity = 0.55 * grow * fade * (0.85 + 0.15 * Math.sin(k * 3 + c.i));
      c.g.rotation[c.axis] = c.tilt * Math.min(1, k / 0.6) + Math.sin(k * 5 + c.i) * 0.05;   // 立起来以后往下一只那边歪，微微晃
    }
    if (cast.length && cast.every((c) => c.t > CAST_LIFE + 0.6)) clearCast();
  }

  // ---- 本命：形真理齐了、走进 boss 区块，2.5 秒后它在那儿现身（"怪"开关关着也出：这是故事） ----
  let bossWait = -1, entered = 0;
  let jolt = 0; const rung = new Map();   // 天秤：齐了那一下猛抖；这次进区块已经为哪样东西响过

  const G = {
    get state() { return S; }, get hasCase() { return !!C; },
    /** 进区块（tags 建好以后调） */
    enterZone() {
      quiet = 0; hintLv = 0; clearHints(); barkOn = null; bark.classList.remove("show"); rung.clear(); clearCast();
      for (const n of ctx.npcs()) n.said = -1;
      noteZone(); addFindTags(); decorateExits(); mountProps();
      entered++;
      // bossReturn（大奥：本命那间是起点）：刚进这个地点那一下不出，要从别的房间回来才出
      if (C && S.ready && !S.done && zid() === C.boss && !(C.bossReturn && entered === 1)) bossWait = 2.5;
      // 形真理没齐就先进了本命那间：上方浮一句，告诉人这里以后会出事、现在还没到时候（起点就是本命那间的不浮）
      if (C && !S.ready && zid() === C.boss && !C.bossReturn) { const t = texts[`pre.${loc.id}.${zid()}`]; setTimeout(() => toast(t || "远处的铃响了一下，又停了。", 3600), 900); }
      document.body.classList.toggle("zone-done", zoneDone(zid()));
      if (S.outWait) {
        if (C.closeAt.includes(zid())) { S.outWait = false; save(); decorateExits(); clearTimeout(endPending); endPending = setTimeout(openEnding, 5000); }   // 先看一会儿颜色
        else setTimeout(() => S.outWait && toast(OUT_LINE(), 3000), 900);
      }
    },
    /** 第一次进这个地点：一张小卡交代案子 */
    async intro() {
      if (!C || S.intro) return;
      S.intro = true; save();
      const t = texts[`case.${loc.id}`] || { title: "这里出了物怪", hook: "要斩物怪，先得知道它的形、真、理。到处看看，问问这家的人。" };
      await card.open({ place: loc.name, title: t.title, body: t.hook });
      toast("右上角三格：查到一样亮一格", 3600);
      setTimeout(() => toast(ctx.touch ? "不知道往哪走：点「秤」放天秤，它会指路" : "不知道往哪走：按 T 放天秤，它会指路", 4200), 4000);
    },
    onView(n) { mark(`${zid()}/view:${n}`); },
    /** E：没有観在旁边时，问配角 / 捡拾遗。用掉了返回 true */
    act() {
      const a = actNear(); if (a) { doAct(a); return true; }
      const f = findNear(); if (f) { pickUp(f); return true; }
      const n = npcNear(); if (n) { const t = npcText(n.id); say(n, Math.min((t.lines?.length || 1) - 1, (n.said ?? -1) + 1)); return true; }
      return false;
    },
    /** 旁边有没有能做的事、拾遗、配角（観看过以后 E 让给它们） */
    nearOther() { return !!(actNear() || findNear() || npcNear(1.6)); },
    /** 提示条：配角、拾遗、拍照点（没有観在旁边时 tour.js 问这里） */
    promptText(touch) {
      if (hintAt) return hintAt;
      const a = actNear(); if (a) return `${touch ? "点这里" : "E"} ${actText(a).label || "看看"}`;
      const f = findNear(); if (f) return `${touch ? "点这里" : "E"} 拾起来看看`;
      const n = npcNear(1.6); if (n) return `${touch ? "点这里" : "E"} 搭话 · ${names[n.id] || npcText(n.id)?.name || ""}`;
      if (photoAt() >= 0) return `好位置 · ${touch ? "点拍照" : "P 拍照"}`;
      return "";
    },
    /** 拍照：站在拍照点上，记一笔，返回落款（照片右下角盖的印） */
    onPhoto() {
      const i = photoAt(); if (i < 0) return null;
      mark(`${zid()}/photo:${i}`);
      return loc.name;
    },
    /** 物怪出没能不能随机出：至少看过两处；本命没退之前不随机出它 */
    randomOk() { return S.seen.length >= 2 && (!C || S.chars.length >= 1); },   // 有案子的地点：至少查到一个字（知道这家出了什么）再随机出
    allowRandom(id) { return !C || S.done || id !== C.mononoke; },
    firstRandom() { return C && !S.done ? C.firstRandom : null; },
    /** 退魔 / 送走以后（encounter 调） */
    onExorcised(id) {
      if (!C || id !== C.mononoke || S.done) return;
      S.done = true; save(); decorateExits();
      setTimeout(() => stamp("退魔"), 400);
      ctx.stat(`本命/${loc.id}`, `本命 · ${loc.name}`);
      if (C.closeAt && !C.closeAt.includes(zid())) {   // 要出去看了颜色再结案
        S.outWait = true; save(); decorateExits();
        endPending = setTimeout(() => toast(OUT_LINE(), 4200), 9000);   // 执念物卡（上色洇满后掉）大致看完了再说
        return;
      }
      endPending = setTimeout(openEnding, 2200);   // 「退魔」印盖完再弹结案卡
    },
    update(dt) {
      const free = ctx.free();
      // 冒话：走近 2 米冒第一句（每进一次区块一次），说完 4 秒收起；纸条跟着头顶
      if (free) { const n = npcNear(); if (n && (n.said ?? -1) < 0) say(n, 0); }
      if (barkOn) {
        barkT -= dt;
        const v = new THREE.Vector3(barkOn.group.position.x, barkOn.group.position.y + (barkOn.height || 1.6) + 0.25, barkOn.group.position.z).project(ctx.camera);
        const off = v.z > 1 || Math.abs(v.x) > 1.05 || Math.abs(v.y) > 1.05;
        bark.style.transform = `translate(${(v.x * 0.5 + 0.5) * innerWidth}px, ${(-v.y * 0.5 + 0.5) * innerHeight}px) translate(-50%, -100%)`;
        // 11-05：转到画面外先藏着（扫描房间的环绕镜头常一下转开），转回来还在；4 秒到了才收
        if (barkT <= 0) { bark.classList.remove("show"); barkOn = null; } else bark.classList.toggle("show", !off);
      }
      // 拾遗：走近 2.5 米才露出"拾"字
      for (const { f, it } of findTags) { const d = Math.hypot(f.pos[0] - player.position.x, f.pos[1] - player.position.z); it.el.classList.toggle("near", d < 2.5); }
      document.body.classList.toggle("photo-spot", free && photoAt() >= 0);
      // 天秤：朝还没找的东西倾，越近晃得越快；区块查完就停
      const scale = P.props.find((p) => p.id === "scale")?.prop;
      // 11-06（用户："看不到天秤的晃动"）：天秤原来挂在腰正前方，跟随镜头在身后，身子整个挡住它。
      //   第一帧把它往右胯外挪（在腰挂点自己的坐标里算一次，之后跟着腰动），从身后、斜后方都看得见
      if (scale && !scale.userData.side) {
        scale.userData.side = true;
        player.updateMatrixWorld(true);
        const yaw = player.rotation.y, right = new THREE.Vector3(-Math.cos(yaw), 0, Math.sin(yaw)), back = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
        const w = scale.getWorldPosition(new THREE.Vector3()).addScaledVector(right, SCALE_SIDE).addScaledVector(back, 0.06);
        scale.position.copy(scale.parent.worldToLocal(w));
        scale.scale.multiplyScalar(1.25);   // 本身只有巴掌大、颜色深，挂在胯边再放大一点才看得出倾
      }
      const it = left().length ? target() : null;
      if (scale && !ctx.enc.active) {
        let rz = 0;
        if (it) {
          const a = Math.atan2(it.pos[0] - player.position.x, it.pos[1] - player.position.z), side = Math.sin(wrap(a - player.rotation.y));
          const d = Math.hypot(it.pos[0] - player.position.x, it.pos[1] - player.position.z), near = Math.max(0, 1 - d / 7);
          G._t = (G._t || 0) + dt * (2 + near * 8);
          rz = -side * 0.42 + Math.sin(G._t) * (0.05 + near * 0.09);
        }
        // 形真理齐了：剧烈抖一阵（docs/19 第三节）
        if (jolt > 0) { jolt -= dt; rz = Math.sin(jolt * 40) * 0.22 * Math.min(1, jolt / 0.6); scale.rotation.z = rz; }
        else scale.rotation.z += (rz - scale.rotation.z) * Math.min(1, dt * 4);
        // 11-06 天秤会响（用户："好像天秤没有响"）：走进那样东西 3 米内叮铃一声，再走近到 1.3 米轻响一下；每样东西每次进区块各一次
        if (it) {
          const d = Math.hypot(it.pos[0] - player.position.x, it.pos[1] - player.position.z), lv = d < 1.3 ? 2 : d < 3 ? 1 : 0, was = rung.get(it.key) || 0;
          if (lv > was && free) { rung.set(it.key, lv); audio.play("scaleBell", lv === 1 ? 2 : 1, lv === 1 ? 0.07 : 0.045); }
        }
      }
      // 本命
      if (bossWait >= 0 && free && !ctx.enc.active) { if ((bossWait -= dt) < 0) { const Z = ctx.zone(); if (!ctx.enc.startBoss(C.mononoke, Z.bossAt)) bossWait = 1; } }
      // 提示：只在能自由走的时候计时；区块没东西了不提示
      if (glint.visible) { glintT += dt; glint.material.opacity = Math.max(0, Math.sin(Math.min(1, glintT / 1.6) * Math.PI)) * 0.9; if (glintT > 1.6) glint.visible = false; }
      if (wispTo) {
        wispT += dt; wisp.position.lerp(wispTo, 1 - Math.exp(-1.2 * dt)); wisp.position.y += Math.sin(wispT * 3) * 0.002;
        wisp.material.opacity = Math.min(0.95, wispT) * (0.75 + 0.25 * Math.sin(wispT * 5)); if (wispT > 12) { wisp.visible = false; wispTo = null; }
      }
      kitTick(dt); moteTick(dt); tweenTick(dt); castTick(dt);
      if (!free || !it) return;
      quiet += dt;
      if (hintLv < 3 && quiet >= HINT[hintLv]) { hintLv++; hint(hintLv, it); }
    },
    /** 案卷·宅图（casebook.js）：药箱里翻开，画进 el。没有 case.plan 的地点退回下面的文字版 */
    mountBook(el) {
      if (!C?.plan) { el.innerHTML = G.book(); return null; }
      return mountCasebook(el, () => G.bookData());
    },
    bookData() {
      const notes = texts[`note.${loc.id}`] || {}, m = texts[`mononoke.${loc.id}`] || {}, lines = { 形: m.katachi, 真: m.makoto, 理: m.kotowari };
      const kindOf = (k) => k.split("/")[1].split(":")[0];
      const roomName = Object.fromEntries(Object.entries(loc.zones || {}).map(([id, z]) => [id, z.name || id]));
      const src = (k) => {
        const [z, w] = k.split("/"), [kind, id] = w.split(":");
        if (kind === "view") return (texts[`${loc.id}_${z}.${id}`] || {}).title || `${roomName[z]}的観`;
        if (kind === "npc") return names[id] || npcText(id)?.name || id;
        if (kind === "find") return (texts[`find.${loc.id}.${id}`] || {}).title || "拾遗";
        if (kind === "act") return actText({ id }).src || (id === "grave" ? "坟前合掌" : actText({ id }).label || "做过的事");
        return k;
      };
      const noteOf = (k) => { if (notes[k]) return notes[k]; const [, w] = k.split("/"), [kind, id] = w.split(":"); if (kind === "npc") { const t = npcText(id); return t?.lines?.[t.clue ?? 0] || ""; } if (kind === "find") return (texts[`find.${loc.id}.${id}`] || {}).body || ""; return src(k); };
      const item = (k) => ({ k, room: k.split("/")[0], src: src(k), note: noteOf(k), kind: kindOf(k), got: has(k) });
      const used = new Set(C.clues.flatMap((c) => c.need));
      const clues = C.clues.map((cl) => ({ c: cl.char, after: cl.after, line: lines[cl.char] || "", hold: texts[`hold.${loc.id}.${cl.char}`] || "", items: cl.need.map(item),
        st: S.chars.includes(cl.char) ? "lit" : (S.held || []).includes(cl.char) ? "held" : "none" }));
      const seen = S.seen.filter((k) => !used.has(k) && !/\/(find|photo):/.test(k)).map(item);
      const finds = Object.entries(loc.zones || {}).flatMap(([z, Z]) => (Z.finds || []).map((f) => item(`${z}/find:${f.id}`)));
      const visited = new Set(Object.keys(S.zones));
      const roomItems = Object.fromEntries(Object.entries(S.zones).map(([z, l]) => [z, { total: l.length, got: l.filter(has).length }]));
      // 门：从起点按出口一层层往里走，外 → 里
      const edges = [], depth = { [loc.start]: 0 }, q = [loc.start];
      while (q.length) { const a = q.shift(); for (const e of loc.zones?.[a]?.exits || []) { if (depth[e.to] == null) { depth[e.to] = depth[a] + 1; q.push(e.to); edges.push([a, e.to]); } } }
      return { name: loc.name, mononoke: m.name || "", plan: C.plan, edges, roomName, here: zid(), newest: S.lastClue || S.last, clues, seen, finds, roomItems, visited, done: S.done, tex: (f) => ctx.tex(f) };
    },
    /** 药箱里的"案卷"（11-05 第二轮，用户："线索也可以收进药箱，让整个线索的逻辑更完整"）：
     *  形 / 真 / 理三段，每段列查到的出处和一句摘记（text.json note.<地点>），亮了的字写出那句；没查到的留空行；
     *  后面是"见闻"（其他看过的観、说过话的配角）和"拾遗"。摘记没写的，観用卡的标题、配角用他说的那句、拾遗用标题 */
    book() {
      const notes = texts[`note.${loc.id}`] || {}, m = texts[`mononoke.${loc.id}`] || {}, lines = { 形: m.katachi, 真: m.makoto, 理: m.kotowari };
      const zn = (k) => loc.zones?.[k.split("/")[0]]?.name || k.split("/")[0];
      const src = (k) => {
        const [z, w] = k.split("/"), [kind, id] = w.split(":");
        if (kind === "view") return (texts[`${loc.id}_${z}.${id}`] || {}).title || `${zn(k)}的観`;
        if (kind === "npc") return names[id] || npcText(id)?.name || id;
        if (kind === "find") return (texts[`find.${loc.id}.${id}`] || {}).title || "拾遗";
        if (kind === "act") return `${zn(k)} · ${actText({ id }).label || "看看"}`;
        return k;
      };
      const fallback = (k) => { const [, w] = k.split("/"), [kind, id] = w.split(":"); const t = kind === "npc" ? npcText(id) : null; return t ? t.lines?.[t.clue ?? 0] || "" : ""; };
      const row = (k) => has(k) ? `<li><b>${src(k)}</b>${notes[k] || fallback(k)}</li>` : `<li class="un">……</li>`;
      const used = new Set();
      let h = `<h3>${loc.name} · 案卷</h3>`;
      if (C) {
        h += `<div class="meta">${S.done ? "已退魔" : S.ready ? "形、真、理都查到了" : `形、真、理 ${S.chars.length} / 3`}</div>`;
        for (const cl of C.clues || []) {
          cl.need.forEach((k) => used.add(k));
          const lit = S.chars.includes(cl.char);
          h += `<div class="case-sec${lit ? " lit" : ""}"><div class="row"><b>${cl.char}</b>${lit ? lines[cl.char] || "" : (S.held || []).includes(cl.char) ? "线索齐了，但还说不通，先去查别的" : "还没查到"}</div><ul>${cl.need.map(row).join("")}</ul></div>`;
        }
      }
      const other = S.seen.filter((k) => !used.has(k) && !k.includes("/find:") && !k.includes("/photo:"));
      if (other.length) h += `<div class="case-sec"><div class="row"><b>闻</b>见闻</div><ul>${other.map(row).join("")}</ul></div>`;
      const finds = S.seen.filter((k) => k.includes("/find:"));
      const all = Object.values(loc.zones || {}).reduce((a, z) => a + (z.finds?.length || 0), 0);
      if (all) h += `<div class="case-sec"><div class="row"><b>拾</b>拾遗 ${finds.length} / ${all}</div><ul>${finds.map((k) => { const t = texts[`find.${loc.id}.${k.split(":")[1]}`] || {}; return `<li><b>${t.title || "拾遗"}</b>${t.body || ""}</li>`; }).join("") || '<li class="un">……</li>'}</ul></div>`;
      return h;
    },
    /** 自测、调试 */
    get kitten() { return kitRun ? { phase: kitRun.phase, at: kit.group.position.toArray().map((v) => +v.toFixed(2)), n: kitRun.pts.length } : kit ? "ready" : "not loaded"; },
    get kitObj() { return kit; },
    /** T / 「秤」：放天秤指路 */
    castScales: () => castScales(false), get endOpen() { return endOpen; }, get endCard() { return endData; }, endKey, openEnding, closeEnding, get cast() { return cast.length; }, get castCd() { return castCd; },
    get acting() { return acting; },
    get quiet() { return quiet; }, set quiet(v) { quiet = v; }, get hintLv() { return hintLv; }, mark, itemsOf, left, target,
    reset() { try { localStorage.removeItem(KEY(loc.id)); } catch {} const t = S.totals; for (const k of Object.keys(S)) delete S[k]; Object.assign(S, loadCase(loc.id), { totals: t }); paintHud(); noteZone(); decorateExits(); },
  };
  // 总地图要的总数：观景点按区块数，算一次存下来
  ctx.allViews?.().then((v) => { S.totals = { views: Object.values(v).reduce((a, l) => a + l.length, 0), finds: Object.values(loc.zones || {}).reduce((a, z) => a + (z.finds?.length || 0), 0) }; save(); }).catch(() => {});
  return G;
}
