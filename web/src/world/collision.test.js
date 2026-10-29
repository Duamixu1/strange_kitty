// 运行：cd web && node --test src/world/collision.test.js
// 可走图由 tools/walkmap.py 生成；布局（cameras.json layout）或泼溅变了要重跑脚本，再跑这个测试
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { canStand, floorY, nearestStand, walkmap } from "./collision.js";

const here = new URL(".", import.meta.url);
const cams = JSON.parse(readFileSync(new URL("./cameras.json", here), "utf8"));
const clues = JSON.parse(readFileSync(new URL("../data/clues.json", here), "utf8"));
const L = cams.layout;

test("开场点能站", () => {
  const s = L.gate.start;
  assert.ok(canStand(s[0], s[2]), `开场点 ${s} 不可站`);
});

test("走廊外面、墙外不能站", () => {
  assert.equal(canStand(0, 5), false);       // 门外
  assert.equal(canStand(0, -30), false);     // 远远超出
  assert.equal(canStand(-2.9, -8), false);   // 走廊左墙上
});

test("每间房的中部和门口都能站，并且和开场点连通", () => {
  const rooms = { ...L.rooms, courtyard: L.courtyard };
  for (const [name, r] of Object.entries(rooms)) {
    const d = r.door; const sgn = d[0] > 0 ? 1 : -1;
    assert.ok(canStand(d[0], d[2]), `${name} 门口 ${d} 不可站`);
    const cx = (r.x[0] + r.x[1]) / 2, cz = (r.z[0] + r.z[1]) / 2;
    assert.ok(nearestStand(cx, cz, 1.2), `${name} 中部 (${cx}, ${cz}) 附近 1.2 米没有可站点`);
    assert.ok(canStand(d[0] - sgn * 1.2, d[2]) || nearestStand(d[0] - sgn * 1.2, d[2], 0.6), `${name} 门内侧走廊不可站`);
  }
});

test("NPC 和线索都能走到交互半径以内", () => {
  for (const [id, n] of Object.entries(cams.npc_positions)) {
    const p = n.position;
    assert.ok(nearestStand(p[0], p[2], 1.5), `NPC ${id} @ ${p} 周围 1.5 米内没有可站点`);
  }
  // 交互点和半径照 graybox.js 的 interact 表：墙上的壁画 E2 交互点在墙往里 1 米、半径 1.6；井 E5 在井前 1 米
  const special = {
    E2: [L.mural_kata.position[0] + 1.0, L.mural_kata.position[2], 1.6],
    E5: [L.courtyard.well[0], L.courtyard.well[2] + 1.0, 1.4],
  };
  for (const [id, c] of Object.entries(clues.clues || clues)) {
    if (!c || !Array.isArray(c.position)) continue;
    const [x, z, r] = special[id] || [c.position[0], c.position[2], 1.3];
    assert.ok(nearestStand(x, z, r), `线索 ${id} 交互点 (${x}, ${z}) 周围 ${r} 米内没有可站点`);
  }
});

test("地面高度：房间约 0，走廊门口略高", () => {
  const g = L.gate.start;
  const fg = floorY(g[0], g[2]);
  assert.ok(fg !== null && Math.abs(fg) < 0.6, `开场点地面 ${fg}`);
  for (const [name, r] of Object.entries(L.rooms)) {
    const f = floorY(...(() => { const p = nearestStand((r.x[0] + r.x[1]) / 2, (r.z[0] + r.z[1]) / 2, 1.2); return [p.x, p.z]; })());
    assert.ok(f !== null && Math.abs(f) < 0.15, `${name} 房间地面 ${f}，应该接近 0`);
  }
});

test("栅格自洽", () => {
  assert.equal(walkmap.rows.length, walkmap.h);
  assert.ok(walkmap.rows.every((r) => r.length === walkmap.w));
});
