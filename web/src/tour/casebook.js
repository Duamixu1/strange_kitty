// 案卷·宅图（11-05，用户在 web/case_drafts.html 五版里选了 C"宅图"，文案线细化）：药箱里翻开的线索册。
//   左边是这个地点的俯视平面（地点 JSON 的 case.plan：5 列 × 6 行的格子表），去过的房间铺游戏里那块积木贴图，没去过的是褪色的襖、贴"未至"；
//   查到的东西在它的房间底部钉一颗钉子（观 / 人 / 掌 / 拾），形真理的钉子用彩线连到右边的三张札（朱形、青真、金理），
//   亮了实线、没亮虚线，最新那条上有一颗光点往札走；理和真之间一条依赖线（"先要知道真" / "已通"）。
//   门画在两间房公共边的中点，门后还有没查到的线索就贴一张闪动的小札。房间查完盖"查毕"，差一两样挂"余 N"，药郎在哪间放紫色"药"。
//   底下是摘记页签（形 / 真 / 理 / 见闻 / 拾遗），选一个页签，图上别的钉子和线调暗；点钉子跳到它那条，点札切到那个字。
//   手机（窄于 700 像素）右栏挪到图下面、札横排，连线往下走。
// 数据：guide.js 的 bookData() 给（进度、摘记、出处）；画法照草稿页搬过来。
const CC = { 形: "#B42A47", 真: "#4F74BF", 理: "#C9A23A" };
const KIND = { view: "观", npc: "人", act: "掌", find: "拾" };
const ONE = new Set(["rug_tsuru_img.jpg", "shiromuku.png", "fusuma.png"]);   // 整幅画，只铺一张，不平铺

/**
 * el：要画进去的元素（药箱的卡里）；get()：每次画都重新取数据 → {
 *   name, mononoke, plan: { compass: 右上那行字（万屋 "↑ 楼上　↓ 门前"）, rooms: { id: [列, 行, 跨列, 跨行, 贴图, "tall"/"small"] }, deco: [[列, 行, 跨列, 跨行, 贴图, 名字]], cols, rows },
 *   edges: [[外, 里]], roomName: { id: 名 }, here, newest,
 *   clues: [{ c, line, hold, st: lit/held/none, items: [{ k, room, src, note, kind, got }] }],
 *   seen: [...同上（只有拿到的）], finds: [...（全部，got 标出拿没拿到）], roomItems: { id: { total, got } }, visited: Set, tex: (文件名) => url }
 */
export function mountCasebook(el, get) {
  let tab = null, sel = null;
  const draw = () => {
    const m = get();
    el.innerHTML = render(m);
    after(m);
  };
  function render(m) {
    const P = m.plan, known = new Set([...m.visited, ...m.edges.filter(([a, b]) => m.visited.has(a) || m.visited.has(b)).flat()]);
    const all = [...m.clues.flatMap((c) => c.items.filter((i) => i.got).map((i) => ({ ...i, c: c.c }))), ...m.seen, ...m.finds.filter((f) => f.got)];
    const lit = m.clues.filter((c) => c.st === "lit").length;
    const T = tab || m.clues.find((c) => c.items.some((i) => i.k === m.newest))?.c || (m.finds.some((f) => f.k === m.newest) ? "拾遗" : m.seen.length ? "见闻" : m.clues[0]?.c);
    tab = T;
    const rooms = Object.entries(P.rooms).map(([id, [x, y, w, h, tex, cls]]) => {
      const v = m.visited.has(id), ri = m.roomItems[id] || { total: 0, got: 0 }, left = ri.total - ri.got;
      const pins = all.filter((p) => p.room === id).map((p) => {
        const dim = p.c ? T !== p.c : p.kind === "find" ? T !== "拾遗" : T !== "见闻";
        return `<button class="C-pin${p.c ? " k" : p.kind === "find" ? " f" : ""}${dim ? " dim" : ""}${sel === p.k ? " sel" : ""}" data-k="${p.k}" ${p.c ? `data-c="${p.c}" style="--pc:${CC[p.c]}"` : ""} title="${p.src}"><span>${KIND[p.kind] || "观"}</span></button>`;
      }).join("");
      const t = v ? tex : "fusuma.png";
      return `<div class="C-room ${v ? "v" : "un"} ${cls || ""}" data-room="${id}" style="grid-column:${x}/span ${w};grid-row:${y}/span ${h}">
        <div class="tex${ONE.has(t) ? " one" : ""}" style="background-image:url(${m.tex(t)})"></div>
        <span class="nm">${known.has(id) ? m.roomName[id] || id : ""}</span>
        ${v ? "" : `<span class="slip">未至</span>`}
        ${v && ri.total && !left ? `<span class="C-stamp">查毕</span>` : v && left && left <= 2 && ri.got ? `<span class="C-left">余 ${left}</span>` : ""}
        ${m.here === id ? `<span class="C-here">药</span>` : ""}
        <div class="C-pins">${pins}</div></div>`;
    }).join("") + (P.deco || []).map(([x, y, w, h, tex, nm]) => `<div class="C-deco" style="grid-column:${x}/span ${w};grid-row:${y}/span ${h}"><div class="tex" style="background-image:url(${m.tex(tex)})"></div><span>${nm}</span></div>`).join("");
    const nodes = m.clues.map((c) => `<button class="C-node ${c.st}${T === c.c ? " on" : ""}" data-node="${c.c}" style="--cc:${CC[c.c]}">${c.c}<span class="n">${c.items.filter((i) => i.got).length} / ${c.items.length}</span></button>`).join("");
    const sword = `<div class="C-sword${lit === 3 ? " on" : ""}"><svg viewBox="0 0 26 96"><g fill="none" stroke="currentColor" stroke-width="2"><path d="M13 4 L17 12 L17 62 L9 62 L9 12 Z"/><path d="M3 64 H23"/><path d="M11 66 H15 V90 H11 Z"/></g>${lit === 3 ? "" : `<path d="M4 70 L22 84 M22 70 L4 84" stroke="currentColor" stroke-width="1.5"/>`}</svg>${m.done ? "已退魔" : lit === 3 ? "可出鞘" : "未出鞘"}</div>`;
    const fgot = m.finds.filter((f) => f.got).length;
    const tabs = [["见闻", `见闻 ${m.seen.length}`], ...(m.finds.length ? [["拾遗", `拾遗 ${fgot}/${m.finds.length}`]] : [])];
    const empty = (t = "……") => `<li class="un"><span class="ic"></span><small>　</small><span>${t}</span></li>`;
    const li = (i, c) => i.got
      ? `<li class="${sel === i.k ? "sel" : ""}"><span class="ic${c ? "" : i.kind === "find" ? " f" : " s"}" ${c ? `style="--pc:${CC[c]}"` : ""}>${KIND[i.kind] || "观"}</span><small>${m.roomName[i.room] || i.room} · ${i.src}</small><span>${i.note}</span></li>`
      : empty();
    let body;
    const cl = m.clues.find((c) => c.c === T);
    if (cl) body = `<div class="ln ${cl.st}">${cl.st === "lit" ? cl.line : cl.st === "held" ? `线索齐了，但还说不通：${cl.hold}` : "还没查到"}</div><ul>${cl.items.map((i) => li(i, cl.c)).join("")}</ul>`;
    else if (T === "见闻") body = `<ul>${m.seen.map((i) => li(i)).join("") || empty("还没有")}</ul>`;
    else body = `<ul>${m.finds.map((i) => li(i)).join("")}</ul>`;
    return `<div class="C-wrap"><div class="C-plan" style="--rows:${P.rows || 6};grid-template-columns:repeat(${P.cols || 5},minmax(0,1fr))"><span class="hd">${m.name}<small>${m.mononoke} · 形、真、理 ${lit} / 3</small></span><span class="compass">${P.compass || "↑ 深处　↓ 门前"}</span>${rooms}</div>
      <div class="C-side"><span class="hd">札</span>${nodes}${sword}</div><svg class="C-svg"></svg></div>
      <div class="C-legend"><span><i style="background:${CC.形}"></i>形</span><span><i style="background:${CC.真}"></i>真</span><span><i style="background:${CC.理}"></i>理</span>
        <span>观　看过的観</span><span>人　配角的话</span><span>掌　做过的事</span><span>拾　拾遗</span><span>门上发光的小札　门后还有没查的</span></div>
      <div class="C-notes"><div class="C-tabs">${cl ? `<b style="color:${CC[cl.c]}">${cl.c}</b>` : ""}${tabs.map(([k, t]) => `<button data-tab="${k}" class="${k === T ? "on" : ""}">${t}</button>`).join("")}</div><div class="C-body">${body}</div></div>`;
  }
  function after(m) {
    const wrap = el.querySelector(".C-wrap"), svg = el.querySelector(".C-svg"); if (!wrap) return;
    const R = wrap.getBoundingClientRect(); if (!R.width) return;
    const box = (e) => { const r = e.getBoundingClientRect(); return { l: r.left - R.left, t: r.top - R.top, r: r.right - R.left, b: r.bottom - R.top, cx: r.left - R.left + r.width / 2, cy: r.top - R.top + r.height / 2 }; };
    const roomEl = (id) => el.querySelector(`.C-room[data-room="${id}"]`);
    const side = box(el.querySelector(".C-side")), vertical = side.t > box(el.querySelector(".C-plan")).t + 20;
    const below = (id, seen = new Set()) => { if (seen.has(id)) return []; seen.add(id); return [id, ...m.edges.filter(([a]) => a === id).flatMap(([, b]) => below(b, seen))]; };
    let out = "";
    for (const [a, b] of m.edges) {
      const ea = roomEl(a), eb = roomEl(b); if (!ea || !eb) continue;
      const A = box(ea), B = box(eb);
      const ox = [Math.max(A.l, B.l), Math.min(A.r, B.r)], oy = [Math.max(A.t, B.t), Math.min(A.b, B.b)];
      let x, y, horiz;
      if (ox[1] - ox[0] > 8) { x = (ox[0] + ox[1]) / 2; y = A.b < B.t ? (A.b + B.t) / 2 : (B.b + A.t) / 2; horiz = true; }
      else { y = (oy[0] + oy[1]) / 2; x = A.r < B.l ? (A.r + B.l) / 2 : (B.r + A.l) / 2; horiz = false; }
      const open = m.visited.has(a) || m.visited.has(b);
      const inner = below(b);
      const pending = open && (m.clues.some((c) => c.items.some((i) => inner.includes(i.room) && !i.got)) || inner.some((r) => m.visited.has(r) && m.roomItems[r] && m.roomItems[r].got < m.roomItems[r].total));
      const w = horiz ? 22 : 13, h = horiz ? 13 : 22;
      out += `<rect x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" fill="${open ? "#F1E9DA" : "#E8DCC4"}" stroke="#322D48" stroke-width="1.5"/>`;
      if (pending) out += `<g><rect x="${x - 4}" y="${y - 9}" width="8" height="18" fill="#F1E9DA" stroke="#B42A47" stroke-width="1.5"><animate attributeName="stroke-opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></rect><line x1="${x}" y1="${y - 5}" x2="${x}" y2="${y + 5}" stroke="#B42A47" stroke-width="1.5"/><circle cx="${x}" cy="${y}" r="13" fill="none" stroke="#C9A23A" stroke-width="2" opacity=".6"><animate attributeName="r" values="9;14;9" dur="1.6s" repeatCount="indefinite"/></circle></g>`;
    }
    const path = (x1, y1, x2, y2) => vertical ? `M${x1} ${y1} C${x1} ${(y1 + y2) / 2} ${x2} ${y1 + 40} ${x2} ${y2}` : `M${x1} ${y1} C${(x1 + x2) / 2} ${y1 - 24} ${x2 - 70} ${y2} ${x2} ${y2}`;
    const st = Object.fromEntries(m.clues.map((c) => [c.c, c.st]));
    for (const p of el.querySelectorAll(".C-pin[data-c]")) {
      const c = p.dataset.c, ne = el.querySelector(`.C-node[data-node="${c}"]`); if (!ne) continue;
      const n = box(ne), q = box(p), s = st[c];
      const d = path(q.cx, q.cy, vertical ? n.cx : n.l, vertical ? n.t : n.cy);
      const dim = tab && tab !== c;
      out += `<path class="th${dim ? " dim" : ""}" d="${d}" stroke="#322D48" stroke-width="${s === "lit" ? 5 : 3.5}" opacity="${dim ? 0.08 : 0.35}"/>`;
      out += `<path class="th${dim ? " dim" : ""}" d="${d}" stroke="${CC[c]}" stroke-width="${s === "lit" ? 2.6 : 2}" ${s === "lit" ? "" : `stroke-dasharray="6 5"`}/>`;
      if (p.dataset.k === m.newest && !dim) out += `<circle r="4.5" fill="#fff8e0" stroke="${CC[c]}" stroke-width="2"><animateMotion dur="2.4s" repeatCount="indefinite" path="${d}"/></circle>`;
    }
    // 依赖：有 after 的字（理）→ 它要等的字（真）
    for (const c of m.clues.filter((x) => x.after)) {
      const nr = el.querySelector(`.C-node[data-node="${c.c}"]`), nzE = el.querySelector(`.C-node[data-node="${c.after}"]`); if (!nr || !nzE) continue;
      if (c.st === "none" && !c.items.some((i) => i.got)) continue;
      const a = box(nr), z = box(nzE), ok = st[c.after] === "lit", col = ok ? "#C9A23A" : "#E6667A";
      if (vertical) out += `<path d="M${a.cx} ${a.b + 6} C${a.cx} ${a.b + 22} ${z.cx} ${z.b + 22} ${z.cx} ${z.b + 6}" fill="none" stroke="${col}" stroke-width="2" ${ok ? "" : `stroke-dasharray="4 4"`}/>`;
      else {
        const x = z.r + 8;
        out += `<path d="M${a.r + 2} ${a.cy} C${x + 14} ${a.cy} ${x + 14} ${z.cy} ${z.r + 2} ${z.cy}" fill="none" stroke="${col}" stroke-width="2" ${ok ? "" : `stroke-dasharray="4 4"`}/>`;
        out += `<text x="${x + 16}" y="${(a.cy + z.cy) / 2}" fill="${col}" font-size="11" letter-spacing="2" style="writing-mode:vertical-rl" text-anchor="middle">${ok ? "已通" : `先要知道${c.after}`}</text>`;
      }
    }
    svg.setAttribute("viewBox", `0 0 ${R.width} ${R.height}`);
    svg.innerHTML = out;
    el.querySelectorAll(".C-pin").forEach((p) => p.addEventListener("click", (e) => {
      e.stopPropagation(); const k = p.dataset.k; sel = k;
      tab = p.dataset.c || (m.finds.some((f) => f.k === k) ? "拾遗" : "见闻"); draw();
    }));
    el.querySelectorAll(".C-node").forEach((n) => n.addEventListener("click", (e) => { e.stopPropagation(); tab = n.dataset.node; sel = null; draw(); }));
    el.querySelectorAll(".C-tabs button").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); tab = b.dataset.tab; sel = null; draw(); }));
  }
  const onResize = () => { if (el.isConnected) draw(); else removeEventListener("resize", onResize); };
  addEventListener("resize", onResize);
  // 卡刚显示出来时布局可能还没算好：下一帧再量一次连线
  draw(); requestAnimationFrame(() => el.isConnected && draw());
  return { draw, get tab() { return tab; } };
}
