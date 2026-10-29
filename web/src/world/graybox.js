import * as THREE from "three";
import { makeToonMaterial } from "../style/toon.js";

// 灰盒场景：按 cameras.json 的 layout 用方块拼走廊、三间房、中庭、井、壁画、门，颜色只用色板。
// 返回：可走区域矩形、可交互点（线索、NPC、门）、可按需隐藏的物体。以后换成正式场景只要保持这些接口。
const C = { paper: "#F1E9DA", coral: "#E6667A", crimson: "#B42A47", ochre: "#DCC67C", green: "#59B86A", teal: "#49B3A6", blue: "#4F74BF", wisteria: "#6A4C8C", navy: "#2A2A4E", lavender: "#D6D3EF", pink: "#E7A3B5", ink: "#322D48" };
// 灰盒各颜色默认铺什么纹样（世界空间，scale 单位米）。正式场景按 docs/02 的纹样规则来，这里先看效果。
const PATTERN_BY_COLOR = {
  [C.green]: { tile: "seigaiha", scale: 1.6, color: C.paper, mix: 0.7 },
  [C.coral]: { tile: "asanoha", scale: 1.2, color: C.pink, mix: 0.8 },
  [C.paper]: { tile: "shippo", scale: 1.4, color: C.lavender, mix: 0.6 },
  [C.ochre]: { tile: "ichimatsu", scale: 0.9, color: C.crimson, mix: 0.12 },
  [C.wisteria]: { tile: "asanoha", scale: 0.8, color: C.lavender, mix: 0.45 },
  [C.navy]: { tile: "seigaiha", scale: 1.0, color: C.lavender, mix: 0.5 },
  [C.teal]: { tile: "ichimatsu", scale: 0.3, color: C.paper, mix: 0.5 },
  [C.lavender]: { tile: "shippo", scale: 1.0, color: C.paper, mix: 0.4 },
};
const mat = (color, pattern = PATTERN_BY_COLOR[color]) => makeToonMaterial({ color, shadeColor: C.wisteria, shadeMix: 0.3, threshold: 0.35, pattern: pattern ? { space: "world", ...pattern } : null });
const box = (w, h, d, color) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color));

export function buildGraybox(scene, cams, clues) {
  const L = cams.layout, H = L.corridor.ceiling;
  const g = new THREE.Group(); scene.add(g);
  const put = (m, x, y, z) => { m.position.set(x, y, z); g.add(m); return m; };
  const [cx0, cx1] = L.corridor.x, [cz0, cz1] = L.corridor.z;
  const cw = cx1 - cx0, cl = cz1 - cz0, cmz = (cz0 + cz1) / 2;

  const splatList = L.splats || (L.splat ? [{ ...L.splat, for: "corridor" }] : []);
  const splatFor = new Set(splatList.map((s) => s.for));
  const splat = splatFor.has("corridor");   // 走廊是 World Labs 泼溅时，灰盒只建门、房间和中庭
  const hasSplat = (room) => splatFor.has(room);   // 某间房有泼溅时，不建它的地面、墙和家具
  if (!splat) {
  // 走廊地面 + 地毯 + 两侧细边
  put(box(cw, 0.1, cl, C.green), 0, -0.05, cmz);
  put(box(1.6, 0.02, cl, C.coral), 0, 0.011, cmz);
  put(box(0.08, 0.025, cl, C.crimson), -0.84, 0.012, cmz); put(box(0.08, 0.025, cl, C.crimson), 0.84, 0.012, cmz);
  // 天花
  put(box(cw, 0.1, cl, C.navy), 0, H + 0.05, cmz);
  // 尽头墙 + 红白扇
  put(box(cw, H, 0.2, C.paper), 0, H / 2, cz0 - 0.1);
  put(new THREE.Mesh(new THREE.CircleGeometry(1.1, 32), mat(C.crimson)), 0, 1.7, cz0 + 0.02);
  put(new THREE.Mesh(new THREE.CircleGeometry(0.7, 32), mat(C.paper)), 0, 1.7, cz0 + 0.04);
  // 门口墙（门两侧）和门（两扇紫色，推开后移走）
  put(box((cw - 1.8) / 2, H, 0.2, C.paper), cx0 + (cw - 1.8) / 4, H / 2, cz1 + 0.1);
  put(box((cw - 1.8) / 2, H, 0.2, C.paper), cx1 - (cw - 1.8) / 4, H / 2, cz1 + 0.1);
  put(box(cw, H - 2.4, 0.2, C.paper), 0, H - (H - 2.4) / 2, cz1 + 0.1);
  }
  const gate = new THREE.Group();
  if (!splat) {   // 泼溅的近端本身画着木门，不再叠灰盒门
    gate.add(put(box(0.9, 2.4, 0.12, C.wisteria), -0.45, 1.2, cz1 + 0.1));
    gate.add(put(box(0.9, 2.4, 0.12, C.wisteria), 0.45, 1.2, cz1 + 0.1));
  }
  g.add(gate);
  // 门外一小块地（泼溅模式开场在门内，不需要）
  if (!splat) put(box(cw, 0.1, 4, C.ochre), 0, -0.05, cz1 + 2);

  // 墙：按门洞切段。左墙只有中庭一个门洞，右墙三个
  function wallWithDoors(x, doorsZ, color) {
    const edges = [cz0, ...doorsZ.flatMap((z) => [z - 0.9, z + 0.9]).sort((a, b) => a - b), cz1];
    for (let i = 0; i < edges.length; i += 2) {
      const a = edges[i], b = edges[i + 1]; if (b - a < 0.01) continue;
      put(box(0.2, H, b - a, color), x, H / 2, (a + b) / 2);
    }
    for (const z of doorsZ) put(box(0.2, H - 2.2, 1.8, color), x, H - (H - 2.2) / 2, z);   // 门楣
  }
  const rooms = L.rooms, cy = L.courtyard;
  let mural = null;
  if (!splat) {
  wallWithDoors(cx1, Object.values(rooms).map((r) => r.door[2]), C.paper);
  wallWithDoors(cx0, [cy.door[2]], C.paper);
  }
  // 壁画（左墙上，形线索 E2）：有泼溅时也要摆，位置是泼溅里画出来的墙面，facing 是朝走廊里的法线
  {
    const M = L.mural_kata, [w, h] = M.size || [3.2, 2.2], f = M.facing || [1, 0, 0];
    mural = new THREE.Group(); mural.position.set(...M.position); mural.rotation.y = Math.atan2(f[0], f[2]); g.add(mural);
    // 拓画贴图（场景线 scenes/19_壁画_踢鞠童女.png 缩成 2048×1434，比例对上板子 10:7）：不受光，四周照常描一圈边，像画框
    const tex = new THREE.TextureLoader().load("/textures/mural_kata.jpg"); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    mural.add(new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex })));
  }
  // 走廊两侧行灯和紫幔
  if (!splat) for (let z = cz1 - 2; z > cz0 + 1; z -= 3) {
    for (const x of [cx0 + 0.3, cx1 - 0.3]) { put(box(0.4, 0.7, 0.4, C.teal), x, 0.55, z); put(box(0.5, 0.2, 0.5, C.wisteria), x, 0.1, z); }
    put(box(0.12, H, 0.12, C.wisteria), cx0 + 0.15, H / 2, z - 1.5); put(box(0.12, H, 0.12, C.wisteria), cx1 - 0.15, H / 2, z - 1.5);
    for (const x of [-1.2, -0.4, 0.4, 1.2]) put(box(0.25, 0.4, 0.25, C.crimson), x, H - 0.3, z);
  }

  // 房间：地面（畳色）+ 三面墙 + 天花
  function room(r, floorColor, key) {
    if (hasSplat(key)) return;
    const [x0, x1] = r.x, [z0, z1] = r.z, w = x1 - x0, d = z1 - z0, mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
    const right = r.door[0] > 0;                       // 门在走廊右墙（+x）还是左墙（-x）
    const nearX = right ? x0 : x1, farX = right ? x1 : x0, out = right ? 1 : -1;
    put(box(w, 0.1, d, floorColor), mx, -0.05, mz);
    if (splat) {   // 靠走廊一侧的墙，留门洞（没泼溅时这面墙由走廊的 wallWithDoors 建）
      const dz = r.door[2];
      put(box(0.2, H, dz - 0.9 - z0, C.paper), nearX - 0.1 * out, H / 2, (z0 + dz - 0.9) / 2);
      put(box(0.2, H, z1 - (dz + 0.9), C.paper), nearX - 0.1 * out, H / 2, (dz + 0.9 + z1) / 2);
      put(box(0.2, H - 2.2, 1.8, C.paper), nearX - 0.1 * out, H - (H - 2.2) / 2, dz);
    }
    put(box(w, 0.1, d, C.navy), mx, H + 0.05, mz);
    put(box(0.2, H, d, C.paper), farX + 0.1 * out, H / 2, mz);
    put(box(w, H, 0.2, C.paper), mx, H / 2, z0 - 0.1);
    put(box(w, H, 0.2, C.paper), mx, H / 2, z1 + 0.1);
    put(box(0.3, 2.5, 0.3, C.wisteria), farX - 0.3 * out, 1.25, z0 + 0.3);
  }
  room(rooms.maids, C.ochre, "maids"); room(rooms.utayama, C.ochre, "utayama"); room(rooms.yuki, C.lavender, "yuki");
  // 房间里的东西：女中房两张矮桌，歌山房书桌 + 簿子，阿雪房空的，角落线轴和一个抽屉柜
  if (!hasSplat("maids")) { const m = rooms.maids; put(box(1.0, 0.3, 0.6, C.crimson), m.x[0] + 1.5, 0.15, m.z[1] - 0.8); put(box(1.0, 0.3, 0.6, C.crimson), m.x[0] + 4, 0.15, m.z[0] + 0.8); }
  // 房间道具：房间有泼溅时，文机、线轴、抽屉柜都画在泼溅里（线索坐标就是按全景图反算的家具位置），灰盒不再摆
  const clu = clues.clues;   // 注意别和上面走廊长度 cl 重名
  let ledger = null, spool = null;
  if (!hasSplat("utayama")) {
    const desk = put(box(1.4, 0.7, 0.7, C.navy), clu.E4.position[0], 0.35, clu.E4.position[2]);
    ledger = put(box(0.4, 0.06, 0.3, C.ochre), desk.position.x - 0.2, 0.73, desk.position.z);
  }
  if (!hasSplat("yuki")) {
    spool = put(new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.16, 12), mat(C.coral)), ...clu.E6a.position); spool.position.y = 0.08;
    const drawer = put(box(0.9, 0.6, 0.5, C.navy), clu.E6b.position[0], 0.3, clu.E6b.position[2]);
    put(box(0.3, 0.05, 0.05, C.ochre), drawer.position.x, 0.4, drawer.position.z + 0.26);
  }

  // 中庭：绿地 + 井 + 四周矮墙，天空开着
  if (!hasSplat("courtyard")) {
    const [x0, x1] = cy.x, [z0, z1] = cy.z, w = x1 - x0, d = z1 - z0, mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
    put(box(w, 0.1, d, C.green), mx, -0.05, mz);
    put(box(0.2, 1.0, d, C.paper), x0 - 0.1, 0.5, mz); put(box(w, 1.0, 0.2, C.paper), mx, 0.5, z0 - 0.1); put(box(w, 1.0, 0.2, C.paper), mx, 0.5, z1 + 0.1);
    if (z0 < cz0) put(box(0.2, 1.0, cz0 - z0, C.paper), x1 + 0.1, 0.5, (z0 + cz0) / 2);   // 伸出走廊尽头的那一段，靠走廊一侧补一道矮墙
    put(new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 0.9, 20), mat(C.navy)), cy.well[0], 0.45, cy.well[2]);
    put(new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.05, 20), mat(C.ink)), cy.well[0], 0.93, cy.well[2]);
    put(box(0.12, 2.2, 0.12, C.wisteria), cy.well[0] - 0.8, 1.1, cy.well[2]); put(box(0.12, 2.2, 0.12, C.wisteria), cy.well[0] + 0.8, 1.1, cy.well[2]);
    put(box(1.8, 0.1, 1.0, C.crimson), cy.well[0], 2.2, cy.well[2]);
    for (const [x, z] of [[x0 + 1, z0 + 1], [x1 - 1, z1 - 1], [x0 + 1.5, z1 - 1.5]]) put(new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 8), mat(C.teal)), x, 0.8, z);
  }

  // 走廊地上的彩线（E1）：从线索点拖到尽头方向
  const e1 = clues.clues.E1.position;
  const thread = put(box(0.05, 0.02, 2.4, C.coral), e1[0], 0.03, e1[2] - 1.2);

  // NPC 占位：圆柱身体 + 球头，颜色区分
  const npcColor = { asa: C.wisteria, kame: C.pink, utayama: C.navy };
  const npcs = {};
  for (const [id, n] of Object.entries(cams.npc_positions)) {
    const grp = new THREE.Group();
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.28, 1.25, 14), mat(npcColor[id])); body.position.y = 0.62;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.17, 14, 10), mat(C.lavender)); head.position.y = 1.45;
    const hair = new THREE.Mesh(new THREE.SphereGeometry(0.19, 14, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat(C.ink)); hair.position.y = 1.47;
    grp.add(body, head, hair);
    grp.position.set(...n.position);
    grp.lookAt(grp.position.x + n.facing[0], grp.position.y, grp.position.z + n.facing[2]);
    grp.name = id; g.add(grp); npcs[id] = grp;
  }

  // 可走区域：走廊（门开后含门口）、房间、中庭，门洞各一小块连通
  const rect = (x0, x1, z0, z1) => ({ x0, x1, z0, z1 });
  const pad = 0.3;
  const walk = {
    gate: splat ? rect(cx0 + pad, cx1 - pad, cz0 + pad, cz1 - 0.3) : rect(cx0 + pad, cx1 - pad, cz1 + 0.4, cz1 + 3.2),   // 泼溅模式开场就在门内，整条走廊可走
    corridor: rect(cx0 + pad, cx1 - pad, cz0 + pad, cz1 - 0.1),
    doors: [],
    rooms: [],
  };
  for (const r of [...Object.values(rooms), cy]) {
    walk.rooms.push(rect(r.x[0] + pad, r.x[1] - pad, r.z[0] + pad, r.z[1] - pad));
    // 门洞矩形要和走廊可走区重叠（走廊可走区比墙窄），朝走廊那边多伸 1.3 米
    const inward = r.door[0] > 0 ? [r.door[0] - 1.3, r.door[0] + 0.6] : [r.door[0] - 0.6, r.door[0] + 1.3];
    walk.doors.push(rect(inward[0], inward[1], r.door[2] - 0.75, r.door[2] + 0.75));
  }

  // 可交互点
  const interact = [
    { id: "gate", kind: "gate", position: L.gate.interact || [0, 0, cz1 + 0.6], radius: 1.6, label: "open_door" },
    { id: "E1", kind: "clue", position: e1, radius: 1.3, label: "pick", mesh: thread },
    { id: "E2", kind: "clue", position: [L.mural_kata.position[0] + 1.0, 0, L.mural_kata.position[2]], radius: 1.6, label: "interact", overlay: "Z1a_mural" },
    { id: "E4", kind: "clue", position: [clu.E4.position[0], 0, clu.E4.position[2]], radius: 1.5, label: "interact", mesh: ledger },
    { id: "E5", kind: "clue", position: [cy.well[0] + Math.sign(cy.door[0] - cy.well[0]) * 1.1, 0, cy.well[2]], radius: 1.4, label: "interact" },   // 井朝门的一侧（井 +z 那边是井屋顶，站不进去）
    { id: "E6a", kind: "clue", position: [clu.E6a.position[0], 0, clu.E6a.position[2]], radius: 1.3, label: "pick", mesh: spool },
    { id: "E6b", kind: "clue", position: [clu.E6b.position[0], 0, clu.E6b.position[2]], radius: 1.4, label: "interact" },
    ...Object.keys(npcs).map((id) => ({ id, kind: "npc", position: cams.npc_positions[id].position, radius: 1.6, label: "talk", object: npcs[id] })),
  ];

  // 区域判定：角色在哪个矩形里就是哪个区
  const zoneRects = [
    ["Z2_maids_room", rooms.maids], ["Z2a_utayama_room", rooms.utayama], ["Z2b_yuki_room", rooms.yuki], ["Z3_courtyard", cy],
  ].map(([zone, r]) => ({ zone, x0: r.x[0], x1: r.x[1], z0: r.z[0], z1: r.z[1] }));

  return { group: g, gate, walk, interact, npcs, zoneRects, mural };
}

export function inRect(p, r) { return p.x >= r.x0 && p.x <= r.x1 && p.z >= r.z0 && p.z <= r.z1; }
