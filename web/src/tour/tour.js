import * as THREE from "three";
import { SparkRenderer, SplatMesh } from "@sparkjsdev/spark";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { PaperOutlinePost } from "../style/post.js";
import { createCollision } from "../world/collision.js";
import { createPathfinder } from "../world/pathfind.js";
import { loadKit } from "./kit.js";
import { loadPlayer, loadNpc } from "./player.js";
import { FollowCam, buildCollider } from "./follow_cam.js";
import { SplatCam } from "./splat_cam.js";
import { locationIds, loadLocation, loadText, loadMap, resolveZone } from "./locations.js";
import { fusumaWipe, prompt, toast, card, Tags, flash } from "./ui.js";
import { createRain } from "./rain.js";

// 游览版：药郎在原作地点里走走看看（docs/14_游览版方案.md）。
//   /tour.html                    绘卷总地图（现在是占位的横向长卷，游5 的图到了再换）
//   /tour.html?loc=<地点>          进地点，从 start 区块开始；&zone=<区块> 直接进某个区块
// 操作：点地面走过去，点"観"标签走过去看说明卡，点出口标签走过去换区块；WASD / 方向键也能走（跟着镜头方向）；按住 Shift 快走，按住 1 秒以上加速成跑；
//       拖动转镜头，滚轮拉远拉近，E 看说明卡 / 关卡片，P 拍照（存 PNG），F 换拍照滤镜（原色 / 夜色 / 雨 / 褪色），O 换拍照姿势（抱臂 / 回头），Esc 关卡片，M 回总地图。
// 调试：window.__tour；?auto=1 加载完按区块的验收机位和几个跟随角度拍图存到 assets/processed/shots/tour_*（无头 Chrome 用）
const params = new URLSearchParams(location.search);
const locId = params.get("loc");
const status = document.getElementById("status");
const assetUrl = (u) => (/^(https?:)?\//.test(u) ? u : `/@fs${ASSETS_DIR}/${u}`);

if (!locId) showMap().catch((e) => { console.error(e); status.textContent = "总地图加载失败：" + e.message; }); else startLocation(locId).catch((e) => { console.error(e); status.textContent = "加载失败：" + e.message; });

// ---------------------------------------------------------------- 总地图（占位）
async function showMap() {
  document.body.classList.add("map-mode");
  const { real, test } = locationIds();
  const map = await loadMap();
  const texts = await loadText();
  const scroll = document.querySelector("#map .scroll"), paper = document.querySelector("#map .paper-roll");
  if (map) {
    // 长卷：图按窗口高度缩放，热区按图的像素比例换成百分比，图换成重画版也不用改
    const [W, H] = map.size;
    paper.style.aspectRatio = `${W} / ${H}`;
    paper.querySelector("img").src = map.image;
    for (const P of map.places) {
      const open = P.open && real.includes(P.id);
      const [x0, y0, x1, y1] = P.rect, pct = (v, t) => `${(v / t) * 100}%`;
      const el = document.createElement(open ? "a" : "div");
      el.className = "spot" + (open ? " open" : " locked");
      Object.assign(el.style, { left: pct(x0, W), top: pct(y0, H), width: pct(x1 - x0, W), height: pct(y1 - y0, H) });
      if (open) el.href = `?loc=${P.id}`;
      const intro = texts[`loc.${P.id}`]?.body;
      el.title = open ? `${P.name} · ${P.sub}${intro ? "\n" + intro : ""}` : `${P.name}（未开放）`;
      paper.appendChild(el);
      const tag = document.createElement("div");
      tag.className = "tag-name" + (open ? " open" : "");
      Object.assign(tag.style, { left: pct(P.label[0], W), top: pct(P.label[1], H) });
      tag.innerHTML = `<span class="name">${P.name}</span><span class="sub">${P.sub}</span>${open ? "" : '<span class="seal">未开放</span>'}`;
      if (open) { tag.addEventListener("click", () => (location.href = `?loc=${P.id}`)); el.addEventListener("mouseenter", () => tag.classList.add("hover")); el.addEventListener("mouseleave", () => tag.classList.remove("hover")); }
      paper.appendChild(tag);
    }
  }
  // 拖着看、滚轮横着走
  let drag = null;
  scroll.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, s: scroll.scrollLeft, moved: false }; });
  addEventListener("pointermove", (e) => { if (!drag) return; const dx = e.clientX - drag.x; if (Math.abs(dx) > 5) drag.moved = true; scroll.scrollLeft = drag.s - dx; });
  addEventListener("pointerup", () => setTimeout(() => (drag = null)));
  scroll.addEventListener("click", (e) => { if (drag?.moved) { e.preventDefault(); e.stopPropagation(); } }, true);
  scroll.addEventListener("wheel", (e) => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); scroll.scrollLeft += e.deltaY; } }, { passive: false });
  // 不在地图上的地点（测试、示例）列在右下角
  const extra = [...real.filter((id) => !map?.places.some((P) => P.id === id)), ...test];
  document.querySelector("#map .tests").innerHTML = extra.length ? "测试：" + extra.map((id) => `<a href="?loc=${id}">${id}</a>`).join(" · ") : "";
  status.textContent = "";
}

// ---------------------------------------------------------------- 地点
async function startLocation(id) {
  const loc = await loadLocation(id);
  const texts = await loadText();
  document.title = `${loc.name} · 怪化猫游览`;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(loc.background || "#2A2A4E");
  const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 200);
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(innerWidth, innerHeight);
  document.getElementById("stage").appendChild(renderer.domElement);
  scene.add(new THREE.DirectionalLight(0xffffff, 1));
  const post = new PaperOutlinePost(renderer, scene, camera);
  post.setFlags({ outline: true, paper: true, letterbox: false });
  const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));

  // ---- 泼溅（地点级，进地点时一次加载完，之后不再动）----
  // Spark 的坑：运行中改泼溅的 visible / opacity / position、加 SplatEdit，整个泼溅系统会掉成 0 个点（探案版试过）。
  // 所以几个泼溅区块共用一个坐标系、一起加载，换区块只换镜头规则和可走范围，不增删泼溅。
  // 条目格式和 cameras.json 的 layout.splats 一样：原始帧 y 向下、沿 +z；绕 X 转 180°，再绕 Y 转 yawDeg，缩放，平移 position
  const splats = [];
  if (loc.splats?.length) {
    const spark = new SparkRenderer({ renderer }); scene.add(spark);
    for (const S of loc.splats) {
      const m = new SplatMesh({ url: `/@fs${ASSETS_DIR}/worldlabs/${S.name}/splat_${S.quality || "500k"}.spz` });
      const yaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(S.yawDeg || 0));
      m.quaternion.copy(yaw.multiply(new THREE.Quaternion(1, 0, 0, 0)));
      m.scale.setScalar(S.scale); m.position.set(...S.position);
      m.frustumCulled = false;   // Spark 算的包围盒不对，镜头一偏整块被剔掉
      scene.add(m); splats.push(m);
    }
    post.exclude.push(...splats); post.spark = spark;
  }

  status.textContent = `${loc.name} · 加载药郎…`;
  const P = await loadPlayer(loader, assetUrl, { springs: params.get("spring") !== "0", props: params.get("props") !== "0", layer: params.get("layer") !== "0" });
  const player = P.group; scene.add(player);
  const follow = new FollowCam(camera, loc.camera || {}); follow.renderer = renderer;
  const splatCam = new SplatCam(camera);
  let cam = follow;   // 积木区块用跟随镜头；camera.mode 是 circle / rail 的泼溅区块用 SplatCam
  const rain = createRain(); scene.add(rain.object); post.exclude.push(rain.object);   // 雨丝不描边
  const stand = () => { player.position.y = col.floorY(player.position.x, player.position.z) ?? 0; };   // 泼溅可走图带地面高度，积木的全平

  // ---- 区块 ----
  let Z = null, world = null, col = null, pf = null, path = null, arriveLock = false, busy = false;
  const tags = new Tags((tid) => onTag(tid));
  const zoneCache = new Map(), npcCache = new Map();
  let npcsOn = [];
  async function enterZone(zoneId, arrive = null) {
    const z = await resolveZone(loc, zoneId);
    if (world) scene.remove(world);
    world = null;
    if (z.kit && !zoneCache.has(zoneId)) {
      const g = await loadKit(loader, assetUrl(`processed/kit/${z.kit}.glb`));
      g.traverse((o) => { if (o.isMesh && o.material.uniforms?.uCutout) o.material.uniforms.uCutout.value = 1; });   // 积木参与遮挡淡出
      if (z.offset) g.position.set(...z.offset);
      zoneCache.set(zoneId, g);
    }
    if (z.kit) { world = zoneCache.get(zoneId); scene.add(world); }
    // 配角站桩：区块的 npcs 列表（格式见 14 第三节），换区块时摘掉上一个区块的；药郎绕着走（挡住半径 0.45 米）
    for (const n of npcsOn) scene.remove(n.group);
    npcsOn = [];
    if (z.npcs?.length) {
      if (!npcCache.has(zoneId)) npcCache.set(zoneId, await Promise.all(z.npcs.map(async (d) => {
        const n = await loadNpc(loader, assetUrl, d).catch((e) => { console.warn("配角加载失败", d.model, e); return null; });
        if (n) {
          n.group.position.set(d.pos[0], 0, d.pos[1]); n.group.rotation.y = d.yaw || 0; n.pos = [...d.pos]; n.home = { pos: [...d.pos], yaw: d.yaw || 0 };
          if (d.patrol?.length) n.patrol = { pts: [d.pos, ...d.patrol], i: 0, dir: 1, speed: d.speed ?? 0.7, pause: d.pause ?? 3, hold: 0, yield: 0 };
        }
        return n;
      })));
      npcsOn = npcCache.get(zoneId).filter(Boolean);
      for (const n of npcsOn) scene.add(n.group);
    }
    Z = z; col = createCollision(z.walk);
    if (npcsOn.length) {
      const base = col.canStand;
      col.canStand = (x, zz) => base(x, zz) && npcsOn.every((n) => (n.pos[0] - x) ** 2 + (n.pos[1] - zz) ** 2 > 0.45 * 0.45);
    }
    for (const n of npcsOn) n.group.position.y = col.floorY(n.pos[0], n.pos[1]) ?? 0;
    pf = createPathfinder(z.walk, col.canStand); path = null;
    let yaw = z.spawnYaw ?? 0, camYaw;
    if (!arrive && !z.spawn && z.stairs.length) arrive = { stair: 0 };
    if (arrive) {
      // 从楼梯口进来：站在门前往里走 0.6 米，背对门，镜头在门那边
      const s = z.stairs[arrive.stair], [fx, fz] = s.face;
      player.position.set(s.stand[0] - fx * 0.6, 0, s.stand[1] - fz * 0.6);
      yaw = Math.atan2(-fx, -fz); camYaw = Math.atan2(fx, fz);
      arriveLock = true;   // 先离开门口，再回去才算要走
    } else {
      const c = z.spawn || [z.walk.x0 + z.walk.w * z.walk.cell / 2, z.walk.z0 + z.walk.h * z.walk.cell / 2];   // 都没有就站中间
      player.position.set(c[0], 0, c[1]);
      camYaw = yaw + Math.PI;
    }
    const near = col.nearestStand(player.position.x, player.position.z, 3); if (near) player.position.set(near.x, 0, near.z);
    player.rotation.y = yaw; stand();
    camera.fov = z.camera?.fov ?? loc.camera?.fov ?? 50; camera.updateProjectionMatrix();
    if (["circle", "rail"].includes(z.camera?.mode)) {
      cam = splatCam;
      cam.setZone({ canStand: col.canStand, yaw: camYaw, camera: z.camera });
    } else {
      cam = follow;
      const W = z.walk, bounds = W ? [W.x0, W.z0, W.x0 + W.w * W.cell, W.z0 + W.h * W.cell] : null;
      cam.setZone({ canStand: col.canStand, ceiling: z.height, yaw: camYaw, bounds, collider: world ? buildCollider(world) : null, fixed: z.camera?.fixed || null });
      if (z.camera) Object.assign(cam, z.camera);
    }
    cam.update(player, 0, true);
    tags.clear();
    for (const [n, p] of Object.entries(z.views)) tags.add(`view:${n}`, "view", "観", [p[0], 1.9, p[1]]);
    (z.exits || []).forEach((e, i) => { const s = z.stairs[e.stair]; if (s) tags.add(`exit:${i}`, "exit", e.label || "出口", [s.door[0], 2.1, s.door[1]]); });
    // 天气：雨夜区块开雨丝，画面往藏青压一点；区块可以单独写 background
    const wet = z.weather === "rain";
    rain.set(wet); post.setTint(wet ? "#8C8CC8" : "#ffffff", wet ? 0.45 : 0);
    scene.background.set(z.background || loc.background || "#2A2A4E");
    status.textContent = `${loc.name} · ${z.name || zoneId}`;
  }

  function viewText(n) {
    const key = `${Z.textKey}.${n}`;
    const t = texts[key] || Z.texts?.[n] || {};
    return { place: `${loc.name} · ${Z.name || Z.id}`, title: t.title || `观景点 ${key}`, body: t.body || "（说明卡待写：文案线 text.json）" };
  }
  async function openView(n) {
    if (busy) return;
    busy = true; path = null; pose = null;
    const p = Z.views[n]; player.rotation.y = Math.atan2(p[0] - player.position.x, p[1] - player.position.z) || player.rotation.y;
    P.play(Z.viewLook?.[n] === "up" ? "look" : "gaze", 0.4);   // 驻足看；高处的观景点（区块里写 viewLook: { "1": "up" }）抬头看
    prompt.set("");
    await card.open(viewText(n));
    P.play("idle", 0.4); stillT = 0;
    busy = false;
  }
  async function takeExit(i) {
    const e = Z.exits[i]; if (!e || busy) return;
    busy = true; path = null; P.play("idle"); prompt.set("");
    await fusumaWipe(() => enterZone(e.to, { stair: e.arrive ?? 0 }));
    busy = false;
  }
  function walkTo(x, z, then = null, tol = 0.3) {
    const r = pf.routeTo([player.position.x, player.position.z], [x, z], tol);
    if (!r) { toast("过不去"); return; }
    path = { pts: r.pts.slice(1), then };
  }
  function onTag(tid) {
    if (busy || card.isOpen) return;
    const [kind, n] = tid.split(":");
    if (kind === "view") { const p = Z.views[n]; walkTo(p[0], p[1], () => openView(n)); }
    // 出口：走到 stand 正上方（容差 0.1），保证进触发圈；原来 0.3 的容差会停在圈边上，触不触发看运气（场景线 10-29 查出来的）
    if (kind === "exit") { const s = Z.stairs[Z.exits[+n].stair]; arriveLock = false; walkTo(s.stand[0], s.stand[1], null, 0.1); }
  }

  // ---- 输入 ----
  const keys = new Set();
  addEventListener("keydown", (e) => {
    keys.add(e.code);
    if (e.code === "KeyE" || e.code === "Escape" || e.code === "Space") {
      if (card.isOpen) { card.close(); return; }
      if (e.code === "KeyE") { const v = nearView(); if (v) openView(v); }
    }
    if (e.code === "KeyP") photo();
    if (e.code === "KeyF") setFilter(filterIdx + 1);
    if (e.code === "KeyO" && !busy && !card.isOpen) cyclePose();
    if (e.code === "KeyM") location.href = "/tour.html";
    if (/^(Arrow|Key[WASD])/.test(e.code)) path = null;
  });
  addEventListener("keyup", (e) => keys.delete(e.code));
  document.getElementById("card").addEventListener("click", () => card.close());
  const canvas = renderer.domElement;
  let drag = null;
  canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, moved: false }; });
  addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) > 6) drag.moved = true;
    if (drag.moved) { cam.turn(dx * 0.005, dy * 0.004); drag.x = e.clientX; drag.y = e.clientY; }
  });
  addEventListener("pointerup", (e) => {
    if (drag && !drag.moved && !busy && !card.isOpen) clickFloor(e.clientX, e.clientY);
    drag = null;
  });
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); cam.zoomBy(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
  const ray = new THREE.Raycaster(), floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
  function clickFloor(x, y) {
    ray.setFromCamera(new THREE.Vector2((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1), camera);
    if (!ray.ray.intersectPlane(floor, hit)) return;
    const s = pf.snapPoint(hit.x, hit.z, 0.8); if (!s) return;
    arriveLock = false; walkTo(s[0], s[1]);
  }

  // ---- 每帧 ----
  function nearView() {
    let best = null, bd = 1.1;
    for (const [n, p] of Object.entries(Z.views)) { const d = Math.hypot(p[0] - player.position.x, p[1] - player.position.z); if (d < bd) { bd = d; best = n; } }
    return best;
  }
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  // 转身：先快后慢地收过去（剩下的角度每秒收掉约 99.9%，最快 rate 弧度/秒、最慢 1 弧度/秒），不再匀速一下拧过去；
  // 要去的朝向同时告诉药郎，头先看过去（walk_layer.js）。10-31 以前是匀速 12 弧度/秒，180° 转身 0.26 秒，看着像机器
  function turnToward(yaw, rate, dt) {
    if (params.get("turn") === "old") { const d = wrap(yaw - player.rotation.y); player.rotation.y = wrap(player.rotation.y + Math.sign(d) * Math.min(Math.abs(d), rate * dt)); return; }   // 对比用：10-31 以前的匀速转身
    const d = wrap(yaw - player.rotation.y), step = Math.min(Math.abs(d), Math.min(rate * dt, Math.max(Math.abs(d) * (1 - Math.exp(-7 * dt)), dt)));
    player.rotation.y = wrap(player.rotation.y + Math.sign(d) * step); P.setFacing?.(yaw);
  }
  let curSpeed = 0, shiftT = 0;   // 当前移动速度（米/秒）、Shift 按住多久
  function move(dt) {
    if (busy || card.isOpen) return;
    const f = cam.forward, r = new THREE.Vector3(-f.z, 0, f.x);
    const k = (a, b) => keys.has(a) || keys.has(b);
    const v = new THREE.Vector3();
    if (k("KeyW", "ArrowUp")) v.add(f); if (k("KeyS", "ArrowDown")) v.sub(f);
    if (k("KeyD", "ArrowRight")) v.add(r); if (k("KeyA", "ArrowLeft")) v.sub(r);
    // 走 1.0 米/秒；按住 Shift 快走 1.8 米/秒，按住超过 1 秒加速成跑 2.85 米/秒（run_k，10-31 角色线做的，第二版实测 2.833）。
    // 速度慢慢加上去（每秒最多加 2.5 米/秒），换步态按当前速度，不是一按就跳；播放倍率按实际速度算，脚不打滑。松开往下减得快
    const fast = keys.has("ShiftLeft") || keys.has("ShiftRight");
    shiftT = fast ? shiftT + dt : 0;
    const want = fast ? (shiftT > 1 ? 2.85 : 1.8) : 1.0;
    curSpeed = Math.max(curSpeed, 0.6);
    curSpeed += THREE.MathUtils.clamp(want - curSpeed, -6 * dt, 2.5 * dt);
    const mps = curSpeed, gait = mps > 2.55 ? "sprint" : mps > 1.3 ? "run" : "walk", speed = mps * dt;   // 跑 run_k 本身 2.833 米/秒，切过去那一刻倍率 0.9，再低就像慢动作
    if (!v.lengthSq() && path) {
      const [tx, tz] = path.pts[0];
      const dx = tx - player.position.x, dz = tz - player.position.z, d = Math.hypot(dx, dz);
      if (d < 0.06) { path.pts.shift(); if (!path.pts.length) { const t = path.then; path = null; P.play("idle"); stillT = 0; t && t(); } return; }
      v.set(dx / d, 0, dz / d);
      if (d < speed) { player.position.x = tx; player.position.z = tz; stand(); turnToward(Math.atan2(dx, dz), 12, dt); P.play(gait); P.setMoveSpeed(mps); return; }
    }
    if (!v.lengthSq()) { curSpeed = 0; idleTick(dt); return; }
    pose = null; stillT = 0;
    v.normalize();
    turnToward(Math.atan2(v.x, v.z), 12, dt);
    const nx = player.position.x + v.x * speed, nz = player.position.z + v.z * speed;
    if (col.canStand(nx, player.position.z)) player.position.x = nx;
    if (col.canStand(player.position.x, nz)) player.position.z = nz;
    stand();
    P.play(gait); P.setMoveSpeed(mps);
  }
  // 配角：巡逻的沿折线来回走（到头停 pause 秒，药郎靠近 1.1 米就停下转身看他）；站桩的偶尔换姿势（player.js 的 idles）。
  // 挡路用的 n.pos 跟着走，药郎的碰撞每帧读它，所以两人不会穿过去
  function npcTick(n, dt) {
    const P2 = n.patrol;
    if (!P2) { n.update(dt, "idle"); return; }
    const gp = n.group.position, dPlayer = Math.hypot(player.position.x - gp.x, player.position.z - gp.z);
    if (dPlayer < 1.1) P2.yield = 2;
    if (P2.yield > 0) {
      P2.yield -= dt;
      const want = Math.atan2(player.position.x - gp.x, player.position.z - gp.z), d = wrap(want - n.group.rotation.y);
      n.group.rotation.y += Math.sign(d) * Math.min(Math.abs(d), 4 * dt);
      n.update(dt, "idle"); return;
    }
    if (P2.hold > 0) { P2.hold -= dt; n.update(dt, "idle"); return; }
    const tgt = P2.pts[P2.i + P2.dir] ? P2.pts[P2.i + P2.dir] : null;
    if (!tgt) { P2.dir *= -1; P2.hold = P2.pause; n.update(dt, "idle"); return; }
    const dx = tgt[0] - gp.x, dz = tgt[1] - gp.z, dist = Math.hypot(dx, dz), step = P2.speed * dt;
    if (dist <= step) { gp.x = tgt[0]; gp.z = tgt[1]; P2.i += P2.dir; if (!P2.pts[P2.i + P2.dir]) { P2.dir *= -1; P2.hold = P2.pause; } }
    else { gp.x += dx / dist * step; gp.z += dz / dist * step; }
    const d = wrap(Math.atan2(dx, dz) - n.group.rotation.y);
    n.group.rotation.y += Math.sign(d) * Math.min(Math.abs(d), 5 * dt);
    gp.y = col.floorY(gp.x, gp.z) ?? 0;
    n.pos[0] = gp.x; n.pos[1] = gp.z;
    n.update(dt, "walk");
  }
  // 站着：拍照姿势保持；站久了（15 秒）偶尔抱臂一下（idle_alt，一次性，播完回待机），之后冷却 30 秒
  let pose = null, stillT = 0;
  function idleTick(dt) {
    if (pose) return;
    stillT += dt;
    if (stillT > 15 && P.currentName === "idle_k") { P.play("idle_alt", 0.4); stillT = -30; return; }
    if (P.currentName !== "idle2_k") P.play("idle");
  }
  // 拍照姿势：O 依次切 抱臂 → 回头 → 不摆。回头要背对镜头站（朝镜头看的方向），药郎从左肩上回望
  const POSES = [null, ["photo_fold", "抱臂"], ["photo_back", "回头"]];
  function cyclePose() {
    const i = (POSES.findIndex((p) => (p ? p[0] : null) === pose) + 1) % POSES.length;
    path = null; pose = POSES[i] ? POSES[i][0] : null;
    if (pose === "photo_back") { const f = cam.forward; player.rotation.y = Math.atan2(f.x, f.z); }
    P.play(pose || "idle", 0.3); P.resetSprings(); stillT = 0;
    toast(pose ? `姿势：${POSES[i][1]}（O 切换，走动就取消）` : "姿势：不摆");
  }
  let exitsOff = false;   // 自动拍图时关掉：药郎被摆到出口旁边拍验收机位，会被自动传走，下一张拍成别的区块
  function checkExits() {
    if (busy || !Z.exits || exitsOff) return;
    let near = false;
    Z.exits.forEach((e, i) => {
      const s = Z.stairs[e.stair]; if (!s) return;
      const d = Math.hypot(s.stand[0] - player.position.x, s.stand[1] - player.position.z);
      if (d < 0.9) near = true;
      if (d < 0.45 && !arriveLock) takeExit(i);   // 到达点在门前 0.6 米，比触发圈远，不会一进来就被传回去
    });
    if (!near) arriveLock = false;
  }
  function updatePrompt() {
    if (busy || card.isOpen) return;
    const v = nearView();
    prompt.set(v ? `E 看看 · ${viewText(v).title}` : "");
  }

  // ---- 拍照：去掉界面，按当前滤镜合成，存 PNG ----
  // 滤镜预览：画布走 CSS filter，夜色的藍调、雨丝在 #fx 层；存图时在 2D 画布上用同样的 filter 重画一遍，再叠藍调和雨丝
  const FILTERS = [
    { id: "none", name: "原色", css: "none" },
    { id: "night", name: "夜色", css: "brightness(.72) saturate(.8) contrast(1.08)", tint: "rgba(42, 42, 78, .35)" },
    { id: "rain", name: "雨", css: "saturate(.85) brightness(.92)", rain: true },
    { id: "faded", name: "褪色", css: "sepia(.35) saturate(.7) contrast(.9) brightness(1.04)" },
  ];
  let filterIdx = 0;
  const fxEl = document.getElementById("fx");
  function setFilter(i, quiet = false) {
    filterIdx = (i + FILTERS.length) % FILTERS.length;
    const f = FILTERS[filterIdx];
    renderer.domElement.style.filter = f.css === "none" ? "" : f.css;
    fxEl.className = f.id;
    if (!quiet) toast(`滤镜：${f.name}（F 切换）`);
  }
  function composePhoto(f = FILTERS[filterIdx]) {
    post.render();
    const src = renderer.domElement, c = document.createElement("canvas");
    c.width = src.width; c.height = src.height;
    const ctx = c.getContext("2d");
    ctx.filter = f.css; ctx.drawImage(src, 0, 0); ctx.filter = "none";
    if (f.tint) { ctx.globalCompositeOperation = "multiply"; ctx.fillStyle = f.tint; ctx.fillRect(0, 0, c.width, c.height); ctx.globalCompositeOperation = "source-over"; }
    if (f.rain) {
      // 雨丝：固定种子，同一个画面拍两次一样
      let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      ctx.strokeStyle = "rgba(241, 233, 218, .35)"; ctx.lineWidth = Math.max(1, c.width / 1280);
      ctx.beginPath();
      for (let i = 0; i < 520; i++) {
        const x = rnd() * c.width * 1.2, y = rnd() * c.height, L = (0.04 + rnd() * 0.06) * c.height;
        ctx.moveTo(x, y); ctx.lineTo(x - L * 0.25, y + L);
      }
      ctx.stroke();
    }
    return c;
  }
  function photo() {
    const url = composePhoto().toDataURL("image/png");
    flash();
    const a = document.createElement("a");
    const t = new Date(), pad = (n) => String(n).padStart(2, "0");
    a.download = `怪化猫游览_${loc.name}_${FILTERS[filterIdx].id === "none" ? "" : FILTERS[filterIdx].name + "_"}${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}_${pad(t.getHours())}${pad(t.getMinutes())}${pad(t.getSeconds())}.png`;
    a.href = url; a.click();
    toast("拍好了，存在下载文件夹");
  }

  const clock = new THREE.Clock(), tv = new THREE.Vector3();
  function frame(dt = Math.min(clock.getDelta(), 0.1)) {
    if (Z) { move(dt); checkExits(); updatePrompt(); }
    P.update(dt);
    for (const n of npcsOn) npcTick(n, dt);
    cam.update(player, dt);
    rain.update(dt, camera);
    post.render();
    tags.update(camera, innerWidth, innerHeight, tv);
  }
  addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); post.resize(); });

  await enterZone(params.get("zone") || loc.start);
  renderer.setAnimationLoop(() => frame());

  async function save(name) {
    frame(1 / 60);
    const data = renderer.domElement.toDataURL("image/jpeg", 0.92);
    return (await fetch("/__shot", { method: "POST", body: JSON.stringify({ name, data }) })).json();
  }
  window.__tour = { loc, get zone() { return Z; }, player, P, get cam() { return cam; }, splats, setFilter, composePhoto, cyclePose, get pose() { return pose; }, camera, scene, renderer, post, enterZone, walkTo, openView, takeExit, keys, save, step: (n = 1, dt = 1 / 60) => { for (let i = 0; i < n; i++) frame(dt); }, card, tags };
  if (params.get("auto")) autoShots();
  if (params.get("selftest")) selfTest();
  if (params.get("walktest")) walkTest();

  // ?walktest=1：走路随动层的验收录像。外景里直走 5.5 米、左拐 90° 再走 3 米、停下站 1.5 秒，
  // 镜头在药郎左前方 3/4 侧面跟拍（背面会被药箱挡住上身），机位方向慢慢跟着他的朝向转（时间常数 0.8 秒），
  // 不用跟随镜头，免得镜头自己的平滑把身体的倾斜抵掉。每 1/24 秒存一帧 walktest_<tag>_NNN.jpg。
  // &layer=0&turn=old 是改之前的样子（没有随动层、匀速转身），tag 自动变成 old。用 tools/walk_video.sh 跑并合成视频
  async function walkTest() {
    const tag = params.get("sprint") ? "sprint" : params.get("layer") === "0" ? "old" : "new";   // &sprint=1：一直按着 Shift，快走 1 秒后加速成跑
    renderer.setAnimationLoop(null); status.style.display = "none"; tags.clear();
    if (loc.zones.soto) await enterZone("soto");
    player.position.set(2.5, 0, 11.0); player.rotation.y = Math.PI / 2; stand(); P.play("idle"); P.resetSprings();
    for (let i = 0; i < 60; i++) frame(1 / 60);
    const off = new THREE.Vector3(), look = new THREE.Vector3();
    let n = 0, camYaw = player.rotation.y;
    const shoot = async () => {
      camYaw += wrap(player.rotation.y - camYaw) * (1 - Math.exp(-(1 / 24) / 0.8));
      off.set(1.7, 1.3, 2.6).applyAxisAngle(new THREE.Vector3(0, 1, 0), camYaw);
      camera.position.copy(player.position).add(off); camera.lookAt(look.set(player.position.x, 1.0, player.position.z)); camera.updateMatrixWorld();
      post.render();
      const data = renderer.domElement.toDataURL("image/jpeg", 0.9);
      await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `walktest_${tag}_${String(n++).padStart(3, "0")}`, data }) });
    };
    if (params.get("sprint")) keys.add("ShiftLeft");
    path = { pts: [[8.0, 11.0], [8.0, 8.0]], then: null };
    let tail = 36;
    while (path || tail-- > 0) { frame(1 / 48); frame(1 / 48); await shoot(); }
    document.title = "WALKTEST DONE";
  }

  // ?selftest=1：不靠鼠标，把"走到观景点 → 开卡 → 关卡 → 走进出口 → 拉门转场到另一头"跑一遍，结果打到控制台（无头 Chrome 的日志里看）
  async function selfTest() {
    const log = (ok, msg) => console.log(`[selftest] ${ok ? "OK " : "FAIL"} ${msg}`);
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    renderer.setAnimationLoop(null);
    const run = (sec) => { for (let i = 0; i < sec * 60; i++) frame(1 / 60); };
    const v = Object.keys(Z.views)[0];
    if (v) {
      onTag(`view:${v}`); run(12);
      const p = Z.views[v], d = Math.hypot(p[0] - player.position.x, p[1] - player.position.z);
      log(d < 0.4, `走到观景点 ${v}，离点 ${d.toFixed(2)} 米`);
      log(card.isOpen, `说明卡打开：${document.querySelector("#card .title").textContent}`);
      run(1); log(["gaze_k", "look_up_k"].includes(P.currentName), `开卡时药郎驻足看（${P.currentName}）`);
      await save(`tour_${loc.id}_动作_驻足看`);
      card.close(); await wait(50); run(0.5); log(!card.isOpen && P.currentName === "idle_k", `说明卡关掉，回待机（${P.currentName}）`);
    }
    if (Z.exits?.length) {
      const from = Z.id, e = Z.exits[0];
      onTag("exit:0"); for (let i = 0; i < 20 * 60 && !busy; i++) frame(1 / 60);
      log(busy, `走到出口 0（${e.label}）触发转场`);
      // 等转场真正结束（第一次进带配角的区块要先加载模型，可能超过 1 秒），最多等 8 秒
      for (let t = 0; t < 8000 && busy; t += 200) await wait(200);
      run(0.2);
      const s = Z.stairs[e.arrive ?? 0], d = Math.hypot(s.stand[0] - player.position.x, s.stand[1] - player.position.z);
      log(Z.id === e.to && d < 1.0, `转到 ${from} → ${Z.id}，离到达口 ${d.toFixed(2)} 米`);
      run(1); log(!busy && Z.id === e.to, "到了以后没有立刻又被传回去");
    }
    const lit = [];
    for (let i = 0; i < 10; i++) { keys.add("KeyW"); run(0.5); keys.delete("KeyW"); lit.push(col.canStand(player.position.x, player.position.z)); }
    log(lit.every(Boolean), "按住 W 走 5 秒，一直在可走区域里");
    // 四种滤镜各合成一张存到 shots，看滤镜有没有生效
    for (const f of FILTERS) {
      const data = composePhoto(f).toDataURL("image/jpeg", 0.9);
      const r = await (await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `tour_${loc.id}_滤镜_${f.name}`, data }) })).json();
      log(r.ok, `滤镜 ${f.name} 合成存图`);
    }
    // 配角巡逻：找第一个有巡逻配角的区块，进去跑 6 秒，看配角挪没挪
    const pz = Object.keys(loc.zones).find((k) => loc.zones[k].npcs?.some((d) => d.patrol));
    if (pz) {
      await enterZone(pz); run(0.1);
      const n = npcsOn.find((x) => x.patrol), p0 = n.group.position.clone();
      // 药郎放到离整条巡逻路线都超过 2 米、又离路线最近的可走格子（直接往旁边挪几米可能被墙拉回来，贴着配角，它就一直在让路）
      const segD = (x, z) => Math.min(...n.patrol.pts.slice(1).map((b, k) => { const a = n.patrol.pts[k], vx = b[0] - a[0], vz = b[1] - a[1], L = vx * vx + vz * vz || 1, t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (z - a[1]) * vz) / L)); return Math.hypot(x - a[0] - t * vx, z - a[1] - t * vz); }));
      const W2 = Z.walk; let best = null;
      for (let j = 0; j < W2.h; j += 2) for (let i = 0; i < W2.w; i += 2) {
        const x = W2.x0 + (i + 0.5) * W2.cell, z = W2.z0 + (j + 0.5) * W2.cell;
        if (!col.canStand(x, z)) continue;
        const d = segD(x, z); if (d > 2 && (!best || d < best.d)) best = { x, z, d };
      }
      if (best) player.position.set(best.x, 0, best.z);
      // 记 6 秒里离起点最远走了多远（只比首尾会撞上"走过去又走回来"的时刻）
      let moved = 0;
      for (let k = 0; k < 60; k++) { run(0.1); moved = Math.max(moved, p0.distanceTo(n.group.position)); }
      log(moved > 0.3, `配角巡逻：${pz} 里的配角 6 秒内最远离开起点 ${moved.toFixed(2)} 米`);
    }
    // 拍照姿势：先回到出发区块的出生点（前面按 W 可能走到墙角，镜头被挤到头顶），
    // O 切两次（抱臂、回头），各等 1 秒让下摆停下来再存图；再切一次回不摆
    await enterZone(loc.start); run(1);
    for (const want of ["pose_fold_k", "pose_back_k"]) {
      cyclePose(); run(1);
      log(P.currentName === want, `拍照姿势 ${want}（当前 ${P.currentName}）`);
      await save(`tour_${loc.id}_动作_${want}`);
    }
    cyclePose(); run(0.3); log(pose === null && P.currentName === "idle_k", "姿势切回不摆");
    document.title = "SELFTEST DONE";
    renderer.setAnimationLoop(() => frame());
  }

  // ?auto=1：每个区块拍几张：区块自带的验收机位（walk 文件里的 shots），再从出生点按四个方向的跟随镜头各拍一张
  async function autoShots() {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    status.style.display = "none";
    const slow = loc.splats?.length > 0;   // 泼溅要等加载和排序
    exitsOff = true;
    await wait(slow ? 9000 : 1500);
    for (const zid of Object.keys(loc.zones)) {
      await enterZone(zid); await wait(slow ? 2000 : 600);
      for (const [k, yaw] of [["后", 0], ["右", Math.PI / 2], ["前", Math.PI], ["左", -Math.PI / 2]]) {
        cam.yaw = player.rotation.y + Math.PI + yaw; cam.cur = null; cam.off = { yaw: 0, pitch: 0 }; cam.inited = false;
        for (let i = 0; i < 60; i++) frame(1 / 60);   // 跑一秒让镜头躲墙的偏转稳下来
        await wait(slow ? 1500 : 300);
        await save(`tour_${loc.id}_${zid}_跟随${k}`);
      }
      // 药郎站到每个观景点上，用这个区块真实的镜头规则拍一张（泼溅区块的安全圈 / 轨道就靠这几张验）
      for (const [n, p] of Object.entries(Z.views)) {
        player.position.set(p[0], 0, p[1]); stand();
        cam.inited = false; cam.cur = null;
        for (let i = 0; i < 90; i++) frame(1 / 60);
        await wait(slow ? 1500 : 300);
        await save(`tour_${loc.id}_${zid}_观景点${n}`);
      }
      for (const s of Z.walk.shots || []) {
        player.position.set(s.player[0], 0, s.player[1]); player.rotation.y = s.player[2] || 0;
        renderer.setAnimationLoop(null);
        P.play("idle"); for (let i = 0; i < 40; i++) P.update(1 / 60);   // 一小步一小步推：一次推 0.5 秒弹簧骨会甩飞，姿势像蹲着侧身
        camera.position.set(...s.cam); camera.lookAt(...s.look); camera.updateMatrixWorld();
        cam.updateCutout(player); post.render(); await wait(200);
        const data = renderer.domElement.toDataURL("image/jpeg", 0.92);
        await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `tour_${loc.id}_${zid}_${s.name}`, data }) });
        renderer.setAnimationLoop(() => frame());
      }
    }
    document.title = "DONE";
    await save(`tour_${loc.id}__done`);   // 收工标记：tools/tour_shots.sh 等到这个文件才停，然后删掉它
  }
}
