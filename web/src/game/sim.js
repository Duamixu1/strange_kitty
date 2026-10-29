// 整局推演：用逻辑层 + 真实可走栅格（src/data/walkmap.json，场景线用 collider.glb 预算）走一遍路线，
// 算每步的路程、时间、天秤响铃、"一直在晃"的时间，以及每一步按 E 时附近有没有别的交互在抢。
// 移动规则同 game.js：步速 1.6 m/s，可站 = 栅格可站且离每个 NPC ≥ 0.45 米；交互 = 半径内最近的那个（graybox.js 的 interact 表）。
// 每一步从当前位置沿栅格寻最短路，走到"按 E 正好触发目标"的第一个格子就停（玩家看到提示就按）。
// 运行：cd web && node src/game/sim.js            推荐路线 + 新手弯路
//      node src/game/sim.js --old                 旧的天秤参数（半径 8、无回差、催全部可发现线索）对比
import { readFileSync } from "node:fs";
import { createGame } from "./logic.js";
import { createCollision } from "../world/collision.js";

const here = new URL(".", import.meta.url);
const J = (p) => JSON.parse(readFileSync(new URL(p, here), "utf8"));
const script = J("../data/script.json"), clues = J("../data/clues.json"), cams = J("../world/cameras.json");
const walkmap = J("../data/walkmap.json");
const col = createCollision(walkmap);
const OLD = process.argv.includes("--old");
if (OLD) clues.scale = { radius: 8, ringSteps: [0.33, 0.66, 0.9] };

const SPEED = 1.6, NPC_BLOCK = 0.45;
const CPS = 7, LINE_GAP = 0.6;   // 阅读：每秒 7 字 + 每句推进 0.6 秒
const WEIGH = 8;                 // 开天秤、放两件、看结果，秒
const L = cams.layout, npc = cams.npc_positions, clu = clues.clues;

// ---- 交互表：照抄 graybox.js 的 interact ----
const cy = L.courtyard;
const INTERACT = [
  { id: "gate", kind: "gate", p: [L.gate.interact[0], L.gate.interact[2]], r: 1.6 },
  { id: "E1", kind: "clue", p: [clu.E1.position[0], clu.E1.position[2]], r: 1.3 },
  { id: "E2", kind: "clue", p: [L.mural_kata.position[0] + 1.0, L.mural_kata.position[2]], r: 1.6 },
  { id: "E4", kind: "clue", p: [clu.E4.position[0], clu.E4.position[2]], r: 1.5 },
  { id: "E5", kind: "clue", p: [cy.well[0] + Math.sign(cy.door[0] - cy.well[0]) * 1.1, cy.well[2]], r: 1.4 },
  { id: "E6a", kind: "clue", p: [clu.E6a.position[0], clu.E6a.position[2]], r: 1.3 },
  { id: "E6b", kind: "clue", p: [clu.E6b.position[0], clu.E6b.position[2]], r: 1.4 },
  ...Object.entries(npc).map(([id, n]) => ({ id, kind: "npc", p: [n.position[0], n.position[2]], r: 1.6 })),
];
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
/** 站在 q 按 E 会触发什么（同 game.js 的 nearest()），以及半径内还有哪些在抢 */
function nearestAt(g, q) {
  const inR = [];
  for (const it of INTERACT) {
    if (it.kind === "gate" && g.state.gateOpened) continue;
    if (it.kind !== "gate" && !g.state.gateOpened) continue;
    if (it.kind === "clue" && g.state.has[it.id]) continue;
    const d = dist(it.p, q);
    if (d <= it.r) inR.push({ id: it.id, d });
  }
  inR.sort((a, b) => a.d - b.d);
  return { hit: inR[0] ? inR[0].id : null, others: inR.slice(1).map((o) => o.id) };
}

// ---- 栅格寻路（8 邻接 Dijkstra，NPC 0.45 米内不可站）----
const { cell, x0, z0, w, h } = walkmap;
const cx = (i) => x0 + (i + 0.5) * cell, cz = (j) => z0 + (j + 0.5) * cell;
const blocked = new Uint8Array(w * h);
for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
  const x = cx(i), z = cz(j);
  let ok = col.canStand(x, z);
  if (ok) for (const n of Object.values(npc)) if (Math.hypot(x - n.position[0], z - n.position[2]) < NPC_BLOCK) ok = false;
  blocked[j * w + i] = ok ? 0 : 1;
}
const toCell = ([x, z]) => [Math.floor((x - x0) / cell), Math.floor((z - z0) / cell)];
function snap(p) {   // 起点不在可站格上时就近拉回
  const [i, j] = toCell(p);
  if (i >= 0 && j >= 0 && i < w && j < h && !blocked[j * w + i]) return [i, j];
  let best = null, bd = Infinity;
  for (let dj = -10; dj <= 10; dj++) for (let di = -10; di <= 10; di++) {
    const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= w || b >= h || blocked[b * w + a]) continue;
    const d = di * di + dj * dj; if (d < bd) { bd = d; best = [a, b]; }
  }
  return best;
}
/** 从 start 出发，找最近的满足 goal(x,z) 的格子，返回折线点列 */
function route(start, goal) {
  const s = snap(start); if (!s) return null;
  const N = w * h, D = new Float64Array(N).fill(Infinity), prev = new Int32Array(N).fill(-1);
  const heap = [];   // 简单二叉堆 [d, idx]
  const push = (d, k) => { heap.push([d, k]); let c = heap.length - 1; while (c > 0) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
  const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
  const k0 = s[1] * w + s[0]; D[k0] = 0; push(0, k0);
  const nb = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2]];
  while (heap.length) {
    const [d, k] = pop(); if (d > D[k]) continue;
    const i = k % w, j = (k / w) | 0;
    if (goal(cx(i), cz(j))) {
      const pts = []; for (let c = k; c !== -1; c = prev[c]) pts.push([cx(c % w), cz((c / w) | 0)]);
      return { pts: pts.reverse(), len: d * cell };
    }
    for (const [di, dj, cst] of nb) {
      const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= w || b >= h) continue;
      const kk = b * w + a; if (blocked[kk]) continue;
      if (di && dj && (blocked[j * w + a] || blocked[b * w + i])) continue;   // 不切墙角
      const nd = d + cst; if (nd < D[kk]) { D[kk] = nd; prev[kk] = k; push(nd, kk); }
    }
  }
  return null;
}

const readTime = (lines) => lines.reduce((s, l) => s + l.length / CPS + LINE_GAP, 0);

function run(name, steps) {
  const g = createGame(script, clues);
  let pos = [L.gate.start[0], L.gate.start[2]], T = 0, walked = 0, rings = 0, wobble = 0, near = 0, wrong = 0;
  const rows = [], problems = [];
  for (const st of steps) {
    const t0 = T, w0 = walked, r0 = rings; let note = "", crowd = "";
    // 走：to 是交互 id（走到按 E 正好触发它）或 { area: [x, z] }（逛到某点）
    if (st.to) {
      const goal = typeof st.to === "string"
        ? (x, z) => nearestAt(g, [x, z]).hit === st.to
        : (x, z) => dist([x, z], st.to) < 0.3;
      const rt = route(pos, goal);
      if (!rt) { problems.push(`${st.label}：走不到`); rows.push({ 步骤: st.label, 路程m: "-", 用时s: "-", 响铃: 0, 备注: "走不到！" }); continue; }
      for (let i = 0; i + 1 < rt.pts.length; i++) {
        const a = rt.pts[i], b = rt.pts[i + 1], d = dist(a, b), dt = d / SPEED;
        const s = OLD ? oldSignal(g, b) : g.scaleSignal([b[0], 0, b[1]], npc);
        T += dt; walked += d;
        if (s.stepUp) rings++;
        if (s.amplitude > 0) wobble += dt;
        if (s.amplitude > 0.66) near += dt;
      }
      pos = rt.pts[rt.pts.length - 1];
      if (typeof st.to === "string") { const n = nearestAt(g, pos); if (n.others.length) crowd = n.others.join("、"); }
    }
    if (st.do) {
      const [kind, id] = st.do.split(":");
      if (kind === "talk") { const r = g.talk(id); T += readTime(r.lines); note = `${r.lines.length} 句${r.gained ? " 得 " + r.gained : ""}`; }
      else if (kind === "interact") {
        let r = g.interact(id);
        if (!r.ok && r.talkFirst) { const t = g.talk(r.talkFirst); T += readTime([...r.lines, ...t.lines]); r = g.interact(id); note = "先和歌山说话 → "; }
        T += readTime(r.lines);
        if (r.ok && script.evidence[id]) T += readTime([script.evidence[id].desc]);
        note += r.ok ? `得 ${id}` : `拒：${(r.lines[0] || "").slice(0, 8)}`;
      } else if (kind === "weigh") {
        const [l, r] = id.split("+"); const pl = g.put(l), pr = g.put(r); const res = g.weigh();
        T += WEIGH + readTime(res.lines || (res.line ? [res.line] : []));
        if (res.result === "wrong") wrong++;
        note = res.result === "balanced" ? `亮 ${res.lights}` : res.result === "wrong" ? "错" : `放不上：${pl.reason || pr.reason}`;
      }
    }
    rows.push({ 步骤: st.label, 路程m: (walked - w0).toFixed(1), 用时s: (T - t0).toFixed(0), 响铃: rings - r0, 半径内还有: crowd, 备注: note });
  }
  console.log(`\n== ${name}${OLD ? "（旧参数）" : ""}  总路程 ${walked.toFixed(0)} m，总用时 ${(T / 60).toFixed(1)} 分钟，响铃 ${rings} 次，天秤在晃 ${(wobble / T * 100).toFixed(0)}% 的时间，贴近(>0.66) ${near.toFixed(0)} 秒，放错 ${wrong} 次`);
  console.table(rows);
  if (problems.length) console.log("问题：" + problems.join("；"));
  return { T, walked, rings };
}

/** 旧规则：催全部可发现的线索，不分字、不回差 */
function oldSignal(g, p) {
  let best = null;
  for (const id of g.availableClues()) {
    if ((id === "E6b" && g.state.has.E6a) || (id === "E6a" && g.state.has.E6b)) continue;
    const c = clu[id]; const q = c.position ? [c.position[0], c.position[2]] : [npc[c.npc].position[0], npc[c.npc].position[2]];
    const d = dist(p, q); if (!best || d < best.distance) best = { distance: d };
  }
  if (!best) return { amplitude: 0, stepUp: false };
  const amplitude = Math.max(0, Math.min(1, 1 - best.distance / clues.scale.radius));
  let ring = 0; clues.scale.ringSteps.forEach((s, i) => { if (amplitude >= s) ring = i + 1; });
  const stepUp = ring > g.state.lastRing; g.state.lastRing = ring;
  return { amplitude, stepUp };
}

/** 女中房最里面的一个可站点（检查能不能从两个女中之间穿过去） */
const M = L.rooms.maids;
const maidsBack = (() => { for (let x = M.x[1] - 0.4; x > M.x[0]; x -= 0.1) { const p = col.nearestStand(x, (M.z[0] + M.z[1]) / 2, 0.6); if (p) return [p.x, p.z]; } return null; })();

const recommended = [
  { label: "推门", to: "gate", do: "interact:gate" },
  { label: "拾彩线 E1", to: "E1", do: "interact:E1" },
  { label: "看壁画 E2", to: "E2", do: "interact:E2" },
  { label: "称 形", do: "weigh:E1+E2" },
  { label: "女中房：阿龟 E3", to: "kame", do: "talk:kame" },
  { label: "女中房：阿浅证言", to: "asa", do: "talk:asa" },
  { label: "歌山房：歌山", to: "utayama", do: "talk:utayama" },
  { label: "翻簿子 E4", to: "E4", do: "interact:E4" },
  { label: "称 真", do: "weigh:E3+E4" },
  { label: "中庭：捞井 E5", to: "E5", do: "interact:E5" },
  { label: "空房：抽屉 E6b", to: "E6b", do: "interact:E6b" },
  { label: "空房：线轴 E6a", to: "E6a", do: "interact:E6a" },
  { label: "称 理", do: "weigh:E5+E6a" },
];
const novice = [
  { label: "推门", to: "gate", do: "interact:gate" },
  { label: "先逛到走廊尽头（没拾线）", to: [0, L.corridor.z[0] + 0.8] },
  { label: "空房：开抽屉 E6b（提前）", to: "E6b", do: "interact:E6b" },
  { label: "中庭：试捞井（被拒）", to: "E5", do: "interact:E5" },
  { label: "回头拾彩线 E1", to: "E1", do: "interact:E1" },
  { label: "看壁画 E2", to: "E2", do: "interact:E2" },
  { label: "称 形", do: "weigh:E1+E2" },
  { label: "女中房：阿浅", to: "asa", do: "talk:asa" },
  { label: "女中房：往里逛（从两人中间穿过）", to: maidsBack },
  { label: "女中房：阿龟 E3", to: "kame", do: "talk:kame" },
  { label: "称错一次 E3+E6b", do: "weigh:E3+E6b" },
  { label: "歌山房：直奔文机（talkFirst）", to: "E4", do: "interact:E4" },
  { label: "称 真", do: "weigh:E3+E4" },
  { label: "中庭：捞井 E5", to: "E5", do: "interact:E5" },
  { label: "再问阿浅（提示空房）", to: "asa", do: "talk:asa" },
  { label: "空房：线轴 E6a", to: "E6a", do: "interact:E6a" },
  { label: "称 理", do: "weigh:E5+E6b" },
];
run("推荐路线", recommended);
run("新手弯路", novice);
