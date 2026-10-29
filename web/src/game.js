import * as THREE from "three";
import { SparkRenderer, SplatMesh } from "@sparkjsdev/spark";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { makeToonMaterial, setPatternsEnabled, patternsEnabled } from "./style/toon.js";
import { PaperOutlinePost } from "./style/post.js";
import { createGame } from "./game/logic.js";
import { buildGraybox, inRect } from "./world/graybox.js";
import { CameraDirector } from "./world/camera_director.js";
import { Dialogue, ScaleHud, ScalePanel, Prompt, fusumaWipe, toast, endingCard } from "./ui/overlay.js";
import { runSwordCutscene } from "./game/cutscene.js";
import { SpringBones } from "./spring.js";
import { attachProps } from "./props.js";
import { canStandP, nearestStand, walkmap } from "./world/collision.js";
import { createPathfinder } from "./world/pathfind.js";
import { createPlaylog } from "./game/playlog.js";
import { RoomCard, HoverTip } from "./ui/overlay.js";
import script from "./data/script.json";
import clues from "./data/clues.json";
import cams from "./world/cameras.json";

// 灰盒游戏台：走廊 + 房间是方块，药贩子是 Tripo 轻量模型，逻辑走 logic.js，界面和机位按 cameras.json。
// 操作：鼠标点地面走过去、点人和东西走过去自动互动、点门口进出房间；也可以 WASD / 方向键走（跟着镜头方向）。
// 按住拖动转视角、滚轮拉近、双击或 R 回正，E 互动/说话，Tab 开天秤，对话里空格/点击推进。?nopost=1 关后期，?log=0 不记游玩记录。
const params = new URLSearchParams(location.search);
const status = document.getElementById("status");
// 游玩记录（src/game/playlog.js）：存到 assets/processed/playlogs/，用 tools/playlog.py 看
const plog = createPlaylog({ enabled: params.get("log") !== "0", meta: { url: location.search, w: innerWidth, h: innerHeight } });

const scene = new THREE.Scene();
scene.background = new THREE.Color("#F1E9DA");
const camera = new THREE.PerspectiveCamera(28, innerWidth / innerHeight, 0.1, 120);
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.getElementById("stage").appendChild(renderer.domElement);
const light = new THREE.DirectionalLight(0xffffff, 1); light.position.set(-1.5, 3, 2.5); scene.add(light);

const world = buildGraybox(scene, cams, clues);
// World Labs 泼溅（走廊一块、房间各一块）。原始帧 y 向下、正前方沿 +z；绕 X 转 180° 变成 y 向上、正前方沿 -z，
// 再绕 Y 转 yawDeg 对准房间朝向，缩放，最后平移到 layout 里写的位置
const splats = [];
const onlySplats = params.get("splats");   // 调试：?splats=corridor,maids 只加载这几块；?splats=none 一块都不加载
const splatList = (cams.layout.splats || (cams.layout.splat ? [cams.layout.splat] : []))
  .filter((S) => !onlySplats || onlySplats.split(",").includes(S.for || "corridor"));
let spark = null;
if (splatList.length) { spark = new SparkRenderer({ renderer }); scene.add(spark); }
for (const S of splatList) {
  const m = new SplatMesh({ url: `/@fs${ASSETS_DIR}/worldlabs/${S.name}/splat_${S.quality || "500k"}.spz` });
  const flip = new THREE.Quaternion(1, 0, 0, 0);
  const yaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(S.yawDeg || 0));
  m.quaternion.copy(yaw.multiply(flip));
  m.scale.setScalar(S.scale);
  m.frustumCulled = false;   // Spark 算的包围盒不对，镜头一偏泼溅整个被剔掉，画面只剩背景色
  m.position.set(...S.position);
  m.userData.for = S.for || "corridor";
  // 房间泼溅门外那截脑补走廊已经用 tools/spz_clip.py 在文件层面裁掉（quality 指向裁过的文件）。
  // 注意：不要在运行时改泼溅的 visible / opacity / position，也不要挂 SplatEdit：Spark 会把可见点数算成 0，整个泼溅系统停摆（都试过）。
  scene.add(m); splats.push(m);
}
const splat = splats[0] || null;
const game = createGame(script, clues);
const dialogue = new Dialogue();
const prompt = new Prompt();
const director = new CameraDirector(camera, cams, { onTransition: (apply) => fusumaWipe(apply) });
for (const [id, obj] of Object.entries(world.npcs)) director.registerAnchor(id, obj);
const hud = new ScaleHud(script, { onOpen: () => panel.toggle() });
const panel = new ScalePanel(script, game, { dialogue, hud, onAllThree: startSword, onBalanced: () => progressed() });
const post = new PaperOutlinePost(renderer, scene, camera);
post.setFlags({ outline: true, paper: true, letterbox: true });
post.exclude.push(...splats);
post.spark = spark;   // 描边通道里让泼溅写深度，墙后的灰盒和角色不会透出描边
const usePost = params.get("nopost") !== "1";

// 角色纹样：按贴图颜色最接近哪个色板色来铺，屏幕空间（原作"纹样贴在屏幕上"的做法）。scale 是一个周期多少 CSS 像素
const CHAR_PATTERNS = [
  { color: "#E6667A", tile: "asanoha", patColor: "#F1E9DA", mix: 0.9 },
  { color: "#B42A47", tile: "asanoha", patColor: "#E7A3B5", mix: 0.8 },
  { color: "#2A2A4E", tile: "seigaiha", patColor: "#D6D3EF", mix: 0.85 },
  { color: "#DCC67C", tile: "shippo", patColor: "#B42A47", mix: 0.6 },
  { color: "#49B3A6", tile: "ichimatsu", patColor: "#F1E9DA", mix: 0.5 },
  { color: "#F1E9DA" }, { color: "#D6D3EF" }, { color: "#6A4C8C" }, { color: "#E7A3B5" }, { color: "#4F74BF" }, { color: "#59B86A" }, { color: "#322D48" },
];

// ---- 角色 ----
const player = new THREE.Group(); player.position.set(...(cams.layout.gate.start || [0, 0, cams.layout.gate.position[2] + 2.2])); scene.add(player);
let mixer = null, actions = {}, current = null, currentName = null, springs = null, props = null;
// 动作名：手 K 版叫 idle_k / walk_k / exorcise_k，Tripo 预设叫 idle / walk / slash，哪个有用哪个
const ALIAS = { idle: ["idle_k", "idle"], walk: ["walk_k", "walk"], slash: ["exorcise_k", "slash"] };
const LOOPING = new Set(["idle_k", "idle", "walk_k", "walk"]);
function play(name) {
  const key = (ALIAS[name] || [name]).find((k) => actions[k]) || name;
  const a = actions[key]; if (!a || a === current) return;
  if (current) current.fadeOut(0.2);
  a.reset();
  if (LOOPING.has(key)) a.setLoop(THREE.LoopRepeat, Infinity); else { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }   // 退魔三拍这类一次性动作停在最后一帧
  a.fadeIn(0.2).play(); current = a; currentName = key;
}
// 药贩子 v2 分层版：下摆、大袖、长发挂了骨链，由弹簧骨驱动（药郎模型线，src/spring.js + data/spring.json）；
// 剑、药箱、天秤按模型里的挂点挂上（src/props.js + data/props.json），剑只在退魔三拍里出现。?spring=0 / ?props=0 关掉
const modelParam = params.get("model") || "processed/kusuriuri_v2_posed_layered.glb";
const modelLoader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
const assetUrl = (u) => (/^(https?:)?\//.test(u) ? u : `/@fs${ASSETS_DIR}/${u}`);
const toonFor = (o, pattern) => {
  const map = o.material.map || null; if (map) map.colorSpace = THREE.SRGBColorSpace;
  const color = map ? "#ffffff" : o.material.color.clone();   // 没贴图的（刀身）用材质本身的颜色
  o.material = makeToonMaterial({ map, color, shadeColor: "#6A4C8C", shadeMix: 0.35, threshold: 0.42, pattern });
};
modelLoader.load(assetUrl(modelParam), (gltf) => {
  const m = gltf.scene;
  m.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; toonFor(o, { space: "screen", scale: 120, byPalette: CHAR_PATTERNS }); } });
  const box = new THREE.Box3().setFromObject(m), h = box.max.y - box.min.y, s = 1.7 / h;
  m.scale.setScalar(s); m.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
  player.add(m);
  player.updateMatrixWorld(true);
  if (params.get("spring") !== "0") { springs = new SpringBones(m); if (!springs.count) springs = null; }
  if (gltf.animations.length) {
    mixer = new THREE.AnimationMixer(m);
    for (const clip of gltf.animations) {
      const name = clip.name.replace(/^preset:(biped:)?/, "").replace(/\|.*$/, "").toLowerCase();
      actions[name] = mixer.clipAction(clip);
    }
    play("idle");
  }
  if (params.get("props") !== "0") {
    attachProps(m, modelLoader, assetUrl, (o) => toonFor(o, null)).then((p) => { props = p; }).catch((err) => console.error("道具加载失败", err));
  }
  status.textContent = `${script.title.name}`;
}, undefined, (e) => { status.textContent = "模型加载失败：" + e.message; });
// 手鞠物怪本体（配角与物怪线，tools/temari_build.py 程序画的贴图，自带纹样和描边，所以卡通材质不再叠纹样）
let temariModel = null;
modelLoader.load(assetUrl("processed/temari.glb"), (gltf) => {
  temariModel = gltf.scene;
  temariModel.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; toonFor(o, null); } });
}, undefined, () => {});   // 没有这个文件就用 temari.js 里代码拼的球
// 配角三人（配角与物怪线，待办第 37 项）：Tripo 多视图 + 绑骨 + 手 K 待机 idle_k，替掉 graybox 里的圆柱占位。
// 身高按包围盒（含发饰和冠）归一：药郎的 1.7 含高帽、眼睛只在 1.41 米，所以女中比他矮一头，歌山在两人之间
const NPC_MODELS = { asa: ["processed/asa_posed.glb", 1.46], kame: ["processed/kame_posed.glb", 1.42], utayama: ["processed/utayama_posed.glb", 1.57] };
const npcMixers = [];
for (const [id, [file, height]] of Object.entries(NPC_MODELS)) {
  const grp = world.npcs[id]; if (!grp) continue;
  modelLoader.load(assetUrl(file), (gltf) => {
    const m = gltf.scene;
    m.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; toonFor(o, { space: "screen", scale: 120, byPalette: CHAR_PATTERNS }); } });
    const box = new THREE.Box3().setFromObject(m), s = height / (box.max.y - box.min.y);
    m.scale.setScalar(s); m.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
    for (const c of grp.children) c.visible = false;   // 圆柱占位
    grp.add(m);
    const clip = gltf.animations.find((c) => /idle/i.test(c.name));
    if (clip) { const mx = new THREE.AnimationMixer(m), a = mx.clipAction(clip); a.play(); a.time = Math.random() * clip.duration; npcMixers.push(mx); }   // 起点错开，三人不同步
  }, undefined, () => {});   // 没有文件就留着圆柱
}

// 妖化：退魔三拍里药郎的表情 3.08 秒切入、8.21 秒切回（药郎模型线第 43 项），这段时间描边变红，前后各 0.15 秒渐变
const AWAKEN = { clip: "exorcise_k", from: 3.08, to: 8.21, fade: 0.15 };
function awakenMix(clip, t) {
  if (clip !== AWAKEN.clip) return 0;
  if (t < AWAKEN.from - AWAKEN.fade || t > AWAKEN.to + AWAKEN.fade) return 0;
  return Math.min(1, (t - (AWAKEN.from - AWAKEN.fade)) / AWAKEN.fade, ((AWAKEN.to + AWAKEN.fade) - t) / AWAKEN.fade);
}

// ---- 输入与移动 ----
const keys = new Set();
const LOGGED_KEYS = new Set(["KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "KeyE", "Enter", "Tab", "Space", "Escape", "KeyR", "KeyN"]);
addEventListener("keydown", (e) => {
  if (e.repeat) return;
  if (LOGGED_KEYS.has(e.code)) plog.ev("key", { k: e.code, down: 1 });
  hud.ensureAudio();
  if (dialogue.open) { if (["Space", "KeyE", "Enter"].includes(e.code)) { e.preventDefault(); dialogue.advance(); } return; }
  if (panel.open) { if (e.code === "Tab" || e.code === "Escape") { e.preventDefault(); panel.close(); } return; }
  if (game.state.phase !== "play") return;
  if (e.code === "KeyN") { setPatternsEnabled(!patternsEnabled()); return; }
  if (e.code === "KeyR") { director.resetLook(); return; }
  if (e.code === "Tab") { e.preventDefault(); panel.show(); return; }
  if (e.code === "KeyE" || e.code === "Enter") { e.preventDefault(); doInteract(); return; }
  keys.add(e.code);
});
addEventListener("keyup", (e) => { if (LOGGED_KEYS.has(e.code) && keys.has(e.code)) plog.ev("key", { k: e.code, down: 0 }); keys.delete(e.code); });
addEventListener("blur", () => keys.clear());

// 鼠标：按下后移动不到 6 像素就松开 = 点一下（走过去 / 互动）；拖动超过 6 像素 = 原地转头看四周。
// 滚轮拉近拉远；双击或按 R 回正。切进别的区会自动回正。对话框开着时点画面任意处 = 下一句
const canvas = renderer.domElement;
const hoverTip = new HoverTip();
let drag = null, mouse = null;
const canLookNow = () => director.canLook && !dialogue.open && !panel.open && !cutscene;
const canClickNow = () => !dialogue.open && !panel.open && !cutscene && !busy && !doorBusy && game.state.phase === "play";
canvas.addEventListener("contextmenu", (e) => e.preventDefault());
canvas.addEventListener("pointerdown", (e) => {
  hud.ensureAudio();
  if (dialogue.open) { dialogue.advance(); return; }
  drag = { x0: e.clientX, y0: e.clientY, x: e.clientX, y: e.clientY, id: e.pointerId, t: performance.now(), moved: false, button: e.button, look0: { ...director.look } };
  try { canvas.setPointerCapture(e.pointerId); } catch {}
});
canvas.addEventListener("pointermove", (e) => {
  mouse = { x: e.clientX, y: e.clientY };
  if (!drag || e.pointerId !== drag.id) return;
  if (!drag.moved && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) > 6) { drag.moved = true; canvas.style.cursor = "grabbing"; hoverTip.set(null); }
  if (!drag.moved || !canLookNow()) return;
  const k = 0.0035 * (camera.fov / 40);   // 拉近时转得慢一点
  director.turn((e.clientX - drag.x) * k, (e.clientY - drag.y) * k);
  drag.x = e.clientX; drag.y = e.clientY;
});
canvas.addEventListener("pointerleave", () => { mouse = null; hoverTip.set(null); });
const endDrag = (e) => {
  if (!drag || e.pointerId !== drag.id) return;
  const d = drag; drag = null; canvas.style.cursor = "";
  if (d.moved) { plog.ev("look", { from: [d.look0.yaw, d.look0.pitch].map((v) => +v.toFixed(2)), to: [director.look.yaw, director.look.pitch].map((v) => +v.toFixed(2)), zone: director.current }); return; }
  if (e.type === "pointerup" && d.button === 0) onClick(e.clientX, e.clientY);
};
canvas.addEventListener("pointerup", endDrag);
canvas.addEventListener("pointercancel", endDrag);
canvas.addEventListener("wheel", (e) => { if (!canLookNow()) return; e.preventDefault(); director.zoomBy(e.deltaY > 0 ? 0.92 : 1 / 0.92); plog.ev("zoom", { z: +director.look.zoom.toFixed(2) }); }, { passive: false });
canvas.addEventListener("dblclick", () => { director.resetLook(); plog.ev("look_reset", {}); });

const walkRects = () => [game.state.gateOpened ? world.walk.corridor : null, world.walk.gate, ...world.walk.doors, ...world.walk.rooms].filter(Boolean);
// 可走区域：场景线用各泼溅的 collider.glb 预算的 0.1 米栅格（src/world/collision.js，已扣身体半径，门洞挖通）。
// 推门前只能在门口这一小段走；没有泼溅的调试模式（?splats=none）退回灰盒的矩形。
// 不跟碰撞图的地面高度走：文机这类矮家具在图里也算"可站"（高 0.39 米），跟着走会踩上桌面。
const useWalkmap = splats.length > 0;
function canStand(p) {
  if (!game.state.gateOpened && p.z < cams.layout.gate.start[2] - 1.6) return false;
  for (const n of Object.values(cams.npc_positions)) if (Math.hypot(p.x - n.position[0], p.z - n.position[2]) < 0.45) return false;   // NPC 站在空地上，不让药郎穿过去
  return useWalkmap ? canStandP(p) : walkRects().some((r) => inRect(p, r));
}
// 药郎模型线补的三个动作（待办第 42 项）：站着超过 8 秒播一次抱臂 idle2_k（10 秒，播完回 idle_k）；
// 站着时往反方向（差 60° 以上）起步，先边转边播碎步 turn_k，转到差 15° 以内再走；看壁画前抬头 look_up_k（见 doInteract）
const wrapAngle = (a) => Math.atan2(Math.sin(a), Math.cos(a));
function turnToward(yaw, rate, dt) {
  const diff = wrapAngle(yaw - player.rotation.y);
  player.rotation.y = wrapAngle(player.rotation.y + Math.sign(diff) * Math.min(Math.abs(diff), rate * dt));
  return Math.abs(diff);
}
let stillTime = 0, busy = false, faceYaw = null;   // busy：交互前的一小段动作（抬头看壁画），这时不听方向键
let doorBusy = false;   // 进出房间的拉门转场中
// 点击移动：autoPath = { pts, i, goal, target, tol, lastMoveT, lastPos }。按方向键会取消
let autoPath = null;
const pathfinder = createPathfinder(walkmap, (x, z) => canStand({ x, z }));
const keyMoving = () => ["KeyW", "KeyA", "KeyS", "KeyD", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].some((k) => keys.has(k));
// 方向键跟着镜头走：W 是"往屏幕里面走"，D 是"往屏幕右边走"。按住方向键期间锁住起步时的镜头方向，
// 走进别的房间、镜头换了角度也不会突然变向；松开再按才用新镜头的方向
let moveBasis = null;
function cameraBasis() {
  const f = new THREE.Vector3(); camera.getWorldDirection(f); f.y = 0;
  if (f.lengthSq() < 1e-4) f.set(0, 0, -1);
  f.normalize();
  return { f, r: new THREE.Vector3(-f.z, 0, f.x) };
}
function move(dt) {
  if (cutscene) return;                              // 过场里动作由过场控制
  if (busy) { if (faceYaw !== null) turnToward(faceYaw, 8, dt); return; }
  if (doorBusy) return;
  if (dialogue.open || panel.open || game.state.phase !== "play") { stillTime = 0; play("idle"); return; }
  if (autoPath) {
    if (keyMoving()) cancelPath("keys");
    else { followPath(dt); return; }
  }
  const ix = (keys.has("KeyD") || keys.has("ArrowRight") ? 1 : 0) - (keys.has("KeyA") || keys.has("ArrowLeft") ? 1 : 0);
  const iz = (keys.has("KeyW") || keys.has("ArrowUp") ? 1 : 0) - (keys.has("KeyS") || keys.has("ArrowDown") ? 1 : 0);
  if (!ix && !iz) moveBasis = null;
  else if (!moveBasis) moveBasis = cameraBasis();
  const d = moveBasis ? moveBasis.f.clone().multiplyScalar(iz).addScaledVector(moveBasis.r, ix) : new THREE.Vector3();
  if (d.lengthSq() === 0) {
    stillTime += dt;
    if (currentName === "idle2_k") { if (current.time >= current.getClip().duration - 0.05) { stillTime = 0; play("idle"); } return; }
    if (stillTime > 8 && actions.idle2_k) { play("idle2_k"); return; }
    play("idle"); return;
  }
  stillTime = 0;
  const yaw = Math.atan2(d.x, d.z), walking = currentName === "walk_k" || currentName === "walk";
  if (!walking && currentName !== "turn_k" && Math.abs(wrapAngle(yaw - player.rotation.y)) > Math.PI / 3 && actions.turn_k) play("turn_k");
  if (currentName === "turn_k") { if (turnToward(yaw, 7, dt) > 0.26) return; }
  else turnToward(yaw, 14, dt);
  d.normalize().multiplyScalar(1.6 * dt);
  const p = player.position, nx = p.clone().add(new THREE.Vector3(d.x, 0, 0)), nz = p.clone().add(new THREE.Vector3(0, 0, d.z));
  if (canStand(nx)) p.x = nx.x;
  if (canStand(nz)) p.z = nz.z;
  play("walk");
}

// ---- 区域与机位 ----
// 门洞：走廊是喇叭口，门口那面画出来的墙比房门靠里（女中房门口的墙在 x≈0.9，房门在 x=3）。
// 药郎一走出走廊的墙线就切进房间机位，不在画墙后面多走一两米。墙线用碰撞图在门两侧各 1.2 米处量
const ROOM_ZONE = { maids: "Z2_maids_room", utayama: "Z2a_utayama_room", yuki: "Z2b_yuki_room", courtyard: "Z3_courtyard" };
const doorways = [];
if (useWalkmap) {
  const wallX = (z, side) => { let x = 0; while (Math.abs(x) < 3.2 && canStandP({ x, z })) x += 0.05 * side; return Math.abs(x); };
  const rooms = { ...cams.layout.rooms, courtyard: cams.layout.courtyard };
  for (const [key, r] of Object.entries(rooms)) {
    if (!r || !r.door || !ROOM_ZONE[key]) continue;
    const side = r.door[0] > 0 ? 1 : -1, dz = r.door[2];
    // 门的前后两半各用自己那一侧的走廊墙线（女中房门口一侧是喇叭口，两边宽窄差近 1 米）；
    // 门在走廊尽头时，尽头外那一侧没有走廊（量出来是 0），借用另一侧
    let near = wallX(dz + 1.2, side), far = wallX(dz - 1.2, side);
    if (near < 0.3) near = far;
    if (far < 0.3) far = near;
    for (const [w, z0, z1] of [[near, dz, dz + 0.75], [far, dz - 0.75, dz]]) {
      const xs = [side * Math.max(0.6, w - 0.1), r.door[0]].sort((a, b) => a - b);
      doorways.push({ zone: ROOM_ZONE[key], x0: xs[0], x1: xs[1], z0, z1 });
    }
  }
}
function zoneFor(p) {
  for (const r of doorways) if (inRect(p, r)) return r.zone;
  for (const r of world.zoneRects) if (inRect(p, r)) return r.zone;
  return game.state.gateOpened ? "Z1_corridor" : "Z0_gate";
}
director.setZone("Z0_gate", { immediate: true });

// 进出房间：房间机位在门墙内往里看，人站在门口时在镜头背后看不见。所以进门是一次"门转场"：
// 拉门擦过去的同时把人放到门墙内 entryDepth 米处、面朝里；在房间里走回门墙内 exitDepth 米以内，再擦一次放回走廊门外
const ROOMS = {};
for (const [key, zone] of Object.entries(ROOM_ZONE)) {
  const r = key === "courtyard" ? cams.layout.courtyard : cams.layout.rooms[key]; if (!r) continue;
  const side = r.door[0] > 0 ? 1 : -1, doorZ = r.door[2];
  const sp = (cams.layout.splats || []).find((S) => S.for === key);
  const wallX = sp && sp.clipZmin != null ? sp.position[0] + (sp.yawDeg < 0 ? 1 : -1) * sp.scale * sp.clipZmin : r.door[0];
  const inner = doorways.filter((d) => d.zone === zone).reduce((m, d) => Math.min(m, Math.abs(d.x0), Math.abs(d.x1)), Math.abs(r.door[0]));
  ROOMS[key] = {
    key, zone, side, doorZ, wallX,
    entry: [wallX + side * (r.entryDepth || 2.2), doorZ],
    exitX: wallX + side * (r.exitDepth || 1.2),
    out: [side * Math.max(0.3, inner - 0.45), doorZ],
  };
}
const roomOfZone = (z) => Object.values(ROOMS).find((R) => R.zone === z) || null;
const roomCard = new RoomCard();
const seenRooms = new Set();
function standAt(pt) {
  const q = (useWalkmap ? nearestStand(pt[0], pt[1], 1.2) : null) || { x: pt[0], z: pt[1] };
  player.position.set(q.x, 0, q.z);
  if (springs) springs.reset();
}
async function doorTransition(R, entering) {
  doorBusy = true; play("idle");
  plog.ev("door", { room: R.key, enter: entering ? 1 : 0, from: [player.position.x, player.position.z].map((v) => +v.toFixed(2)) });
  await fusumaWipe(() => {
    standAt(entering ? R.entry : R.out);
    player.rotation.y = (entering ? R.side : -R.side) > 0 ? Math.PI / 2 : -Math.PI / 2;
    const z = entering ? R.zone : "Z1_corridor";
    currentZone = z; director.current = z; director.resetLook(); director.apply(z, player);
    moveBasis = null;
  });
  doorBusy = false;
  if (entering) { roomCard.show(script.rooms[R.key], !seenRooms.has(R.key)); seenRooms.add(R.key); progressed(); }
  plog.ev("zone", { z: currentZone });
  if (autoPath) replan();
}
// 调试：?at=yuki / maids / utayama / courtyard / corridor 打开就推开门、站进那间房的门内（不播对话）
{
  const at = params.get("at");
  if (at) {
    game.interact("gate"); world.gate.visible = false;
    const r = at === "courtyard" ? cams.layout.courtyard : cams.layout.rooms[at];
    if (r) { const out = r.door[0] > 0 ? 1 : -1; player.position.set(r.door[0] + out * 1.6, 0, r.door[2]); player.rotation.y = out > 0 ? Math.PI / 2 : -Math.PI / 2; }
    else player.position.set(0, 0, -5);
    const ok = splats.length ? nearestStand(player.position.x, player.position.z, 1.5) : null;   // 落点贴到最近的可站格
    if (ok) player.position.set(ok.x, 0, ok.z);
  }
}

// ---- 交互 ----
function nearest() {
  let best = null;
  for (const it of world.interact) {
    if (it.kind === "gate" && game.state.gateOpened) continue;
    if (it.kind !== "gate" && !game.state.gateOpened) continue;   // 门没推开之前只认推门
    if (it.kind === "clue" && game.state.has[it.id]) continue;
    const d = Math.hypot(it.position[0] - player.position.x, it.position[2] - player.position.z);
    if (d <= it.radius && (!best || d < best.d)) best = { it, d };
  }
  return best && best.it;
}
// ---- 点击移动 ----
// 每个可点的东西在屏幕上是一段竖线（脚到头），鼠标离这段线 46 像素以内就算指着它
const CLICK_SPAN = { npc: [0, 1.5], gate: [0.3, 2.0] };
const CLICK_AT = { E2: () => cams.layout.mural_kata.position, E5: () => cams.layout.courtyard.well };
const areaOf = (x, z) => { for (const r of world.zoneRects) if (inRect({ x, z }, r)) return r.zone; return "corridor"; };
function clickTargets() {
  const here = roomOfZone(currentZone) ? currentZone : "corridor";
  const out = [];
  for (const it of world.interact) {
    if (it.kind === "gate" && game.state.gateOpened) continue;
    if (it.kind !== "gate" && !game.state.gateOpened) continue;
    if (it.kind === "clue" && game.state.has[it.id]) continue;
    const at = CLICK_AT[it.id] ? CLICK_AT[it.id]() : it.position;
    if (it.kind !== "gate" && areaOf(at[0], at[2]) !== here) continue;
    const span = CLICK_SPAN[it.kind] || (it.id === "E2" ? [-0.5, 0.5] : [0, 0.6]);
    const y0 = it.id === "E2" ? at[1] : 0;
    const label = it.kind === "npc" ? `${script.ui.talk} · ${script.npc[it.id].name}` : script.ui[it.label];
    out.push({ it, label, a: [at[0], y0 + span[0], at[2]], b: [at[0], y0 + span[1], at[2]] });
  }
  if (game.state.gateOpened) {
    for (const R of Object.values(ROOMS)) {
      if (here === "corridor") out.push({ door: R, enter: true, label: `${script.ui.enter} · ${script.rooms[R.key]}`, a: [R.side * 2.6, 0.2, R.doorZ], b: [R.side * 2.6, 2.0, R.doorZ] });
      else if (R.zone === here) out.push({ door: R, enter: false, label: `${script.ui.leave} · ${script.rooms.corridor}`, a: [R.wallX + R.side * 0.3, 0.2, R.doorZ], b: [R.wallX + R.side * 0.3, 2.0, R.doorZ] });
    }
  }
  return out;
}
const _pa = new THREE.Vector3(), _pb = new THREE.Vector3();
function toScreen(v, out) {
  v.project(camera);
  const r = canvas.getBoundingClientRect();
  out.x = r.left + (v.x + 1) / 2 * r.width; out.y = r.top + (1 - v.y) / 2 * r.height; out.front = v.z < 1;
  return out;
}
function pickTarget(mx, my) {
  let best = null;
  for (const t of clickTargets()) {
    const A = toScreen(_pa.set(...t.a), {}), B = toScreen(_pb.set(...t.b), {});
    if (!A.front || !B.front) continue;
    const vx = B.x - A.x, vy = B.y - A.y, L2 = vx * vx + vy * vy || 1;
    const u = Math.max(0, Math.min(1, ((mx - A.x) * vx + (my - A.y) * vy) / L2));
    const d = Math.hypot(mx - (A.x + vx * u), my - (A.y + vy * u));
    if (d < 46 && (!best || d < best.d)) best = { ...t, d };
  }
  return best;
}
// 画面上下的宽银幕黑边里点了不算
function inLetterbox(my) {
  const r = canvas.getBoundingClientRect(), barH = Math.max(0, (1 - (r.width / r.height) / 2.39) * 0.5) * r.height;
  return my < r.top + barH || my > r.bottom - barH;
}
const raycaster = new THREE.Raycaster(), floorPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
function floorPoint(mx, my) {
  const r = canvas.getBoundingClientRect();
  raycaster.setFromCamera({ x: (mx - r.left) / r.width * 2 - 1, y: -((my - r.top) / r.height * 2 - 1) }, camera);
  const hit = new THREE.Vector3();
  return raycaster.ray.intersectPlane(floorPlane, hit) ? hit : null;
}
// 目的地的小圈：珊瑚色，走到了淡出；点到走不了的地方闪一下深红
const pathMarker = new THREE.Mesh(new THREE.RingGeometry(0.16, 0.24, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: "#E6667A", transparent: true, depthWrite: false }));
pathMarker.position.y = 0.02; pathMarker.visible = false; pathMarker.renderOrder = 5; scene.add(pathMarker);
post.exclude.push(pathMarker);
function markAt(x, z, ok) { pathMarker.position.set(x, 0.02, z); pathMarker.material.color.set(ok ? "#E6667A" : "#B42A47"); pathMarker.material.opacity = 1; pathMarker.visible = true; }

function onClick(mx, my) {
  if (!canClickNow() || inLetterbox(my)) return;
  const t = pickTarget(mx, my);
  if (t && t.it) {
    const it = t.it, at = it.position;
    if (Math.hypot(at[0] - player.position.x, at[2] - player.position.z) <= it.radius && nearest() === it) {   // 已经在跟前，直接互动
      plog.ev("click", { on: it.id, how: "here" }); doInteract(it); return;
    }
    const tol = Math.max(0.3, it.radius - 0.3);
    startPath((x, z) => Math.hypot(x - at[0], z - at[2]) <= tol, { kind: "interact", it, tol }, [at[0], at[2]], { on: it.id });
    return;
  }
  if (t && t.door) { goDoor(t.door, t.enter, "click"); return; }
  const hit = floorPoint(mx, my);
  if (!hit) return;
  const snapPt = pathfinder.snapPoint(hit.x, hit.z, 1.2);
  if (!snapPt) { markAt(hit.x, hit.z, false); toast(script.ui.walk_blocked, 900); plog.ev("click", { floor: [hit.x, hit.z].map((v) => +v.toFixed(2)), blocked: 1 }); return; }
  startPath((x, z) => Math.hypot(x - snapPt[0], z - snapPt[1]) <= 0.15, null, snapPt, { floor: [hit.x, hit.z].map((v) => +v.toFixed(2)) });
}
function goDoor(R, enter, how) {
  if (!canClickNow()) return;
  const goal = enter ? R.entry : [R.exitX - R.side * 0.4, R.doorZ];
  startPath((x, z) => Math.hypot(x - goal[0], z - goal[1]) <= 0.3, { kind: "door", R, enter }, goal, { on: (enter ? "enter_" : "leave_") + R.key, how });
}
// 门牌：走廊里离门 5.5 米以内，在门的位置挂一个小牌子；门在画面外时贴在画面边上、带箭头。
// 房间里镜头背对门，底部挂"回到长廊"。点牌子 = 走过去进门 / 出门
const doorTagBox = document.getElementById("door-tags");
const doorTags = {};
function doorTag(key, text) {
  if (!doorTags[key]) {
    const b = document.createElement("button"); b.className = "door-tag paper"; b.dataset.key = key;
    b.addEventListener("pointerdown", (e) => e.stopPropagation());
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      if (key === "out") { const R = roomOfZone(currentZone); if (R) goDoor(R, false, "tag"); }
      else goDoor(ROOMS[key], true, "tag");
    });
    doorTagBox.appendChild(b); doorTags[key] = b;
  }
  const b = doorTags[key]; if (b.dataset.text !== text) { b.dataset.text = text; b.innerHTML = text; }
  return b;
}
const _tv = new THREE.Vector3();
function updateDoorTags() {
  const show = new Set();
  const ok = game.state.gateOpened && !cutscene && !dialogue.open && !panel.open && game.state.phase === "play" && !director.overlay;
  const rect = canvas.getBoundingClientRect(), barH = Math.max(0, (1 - (rect.width / rect.height) / 2.39) * 0.5) * rect.height;
  const top = rect.top + barH + 10, bottom = rect.bottom - barH - 44, left = rect.left + 12, right = rect.right - 12;
  const inRoom = roomOfZone(currentZone);
  if (ok && inRoom) {
    const b = doorTag("out", `↓ ${script.ui.leave}${script.rooms.corridor}`);
    b.style.transform = `translate(${Math.round(left + 8)}px, ${Math.round(bottom)}px)`;   // 左下角，不和中间的"E 说话"提示叠在一起
    show.add("out");
  } else if (ok) {
    for (const R of Object.values(ROOMS)) {
      const d = Math.hypot(R.side * 2.6 - player.position.x, R.doorZ - player.position.z);
      if (d > 5.5) continue;
      _tv.set(R.side * 2.4, 1.7, R.doorZ).applyMatrix4(camera.matrixWorldInverse);
      const behind = _tv.z > -0.2;
      _tv.set(R.side * 2.4, 1.7, R.doorZ).project(camera);
      let x = rect.left + (_tv.x + 1) / 2 * rect.width, y = rect.top + (1 - _tv.y) / 2 * rect.height;
      if (behind) { x = R.side > 0 ? right : left; y = bottom; }
      const b = doorTag(R.key, "");
      const w = b.offsetWidth || 120;
      const clampedL = x - w / 2 < left, clampedR = x + w / 2 > right, clampedB = y > bottom;
      const arrow = clampedL ? "← " : clampedR ? "" : clampedB ? "↓ " : "";
      b.innerHTML = `${arrow}${script.ui.enter} · ${script.rooms[R.key]}${clampedR ? " →" : ""}`;
      x = Math.min(Math.max(x - w / 2, left), right - w); y = Math.min(Math.max(y, top), bottom);
      b.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
      b.style.opacity = d > 4.5 ? String(Math.max(0.35, 1 - (d - 4.5))) : "1";
      show.add(R.key);
    }
  }
  for (const [k, b] of Object.entries(doorTags)) b.classList.toggle("show", show.has(k));
}
function startPath(goalFn, target, goalPt, logData) {
  const r = pathfinder.route([player.position.x, player.position.z], goalFn);
  if (!r) { markAt(goalPt[0], goalPt[1], false); toast(script.ui.walk_blocked, 900); plog.ev("click", { ...logData, blocked: 1 }); return; }
  autoPath = { pts: r.pts, i: 1, goalFn, goalPt, target, lastPos: player.position.clone(), stuckT: 0 };
  moveBasis = null;
  markAt(goalPt[0], goalPt[1], true);
  plog.ev("click", { ...logData, len: +r.len.toFixed(1) });
}
function replan() {
  const P = autoPath; if (!P) return;
  const r = pathfinder.route([player.position.x, player.position.z], P.goalFn);
  if (!r) { cancelPath("replan_fail"); return; }
  P.pts = r.pts; P.i = 1; P.stuckT = 0;
}
function cancelPath(why) { if (!autoPath) return; plog.ev("path_end", { why }); autoPath = null; }
async function arrive() {
  const P = autoPath; autoPath = null;
  plog.ev("path_end", { why: "arrived" });
  play("idle");
  const t = P.target;
  if (t && t.kind === "interact") {
    const at = t.it.position;
    player.rotation.y = Math.atan2(at[0] - player.position.x, at[2] - player.position.z);
    doInteract(t.it);
  }
}
function followPath(dt) {
  const P = autoPath;
  if (P.i >= P.pts.length) { arrive(); return; }
  const [tx, tz] = P.pts[P.i], p = player.position;
  const dx = tx - p.x, dz = tz - p.z, dist = Math.hypot(dx, dz);
  if (dist < 0.12) { P.i++; if (P.i >= P.pts.length) arrive(); return; }
  turnToward(Math.atan2(dx, dz), 12, dt);
  const step = Math.min(dist, 1.6 * dt);
  const nx = p.clone(), nz = p.clone(); nx.x += dx / dist * step; nz.z += dz / dist * step;
  if (canStand(nx)) p.x = nx.x;
  if (canStand(nz)) p.z = nz.z;
  play("walk"); stillTime = 0;
  P.stuckT += dt;
  if (P.stuckT > 0.8) {   // 0.8 秒没走出 10 厘米：被挡住了，重新找一次路，再不行就停
    if (P.lastPos.distanceTo(p) < 0.1) { if (P.replanned) { cancelPath("stuck"); play("idle"); return; } P.replanned = true; replan(); }
    P.stuckT = 0; P.lastPos.copy(p);
  }
}
// 鼠标指着能点的东西时，光标变成手、旁边浮一行字
function updateHover() {
  if (!mouse || drag?.moved || !canClickNow() || inLetterbox(mouse.y)) { hoverTip.set(null); if (!drag) canvas.style.cursor = ""; return; }
  const t = pickTarget(mouse.x, mouse.y);
  hoverTip.set(t ? t.label : null, mouse.x, mouse.y);
  canvas.style.cursor = t ? "pointer" : "";
}

let lastProgress = performance.now(), hintLevel = 0;
function progressed() { lastProgress = performance.now(); hintLevel = 0; hud.showHint(""); }

// 和 NPC 说话：镜头切到对话机位，说完回原机位
async function talkTo(id) {
  director.pushOverlay("Z4_dialogue", world.npcs[id]);
  const r = game.talk(id);
  plog.ev("talk", { id, lines: r.lines.length, gained: r.gained || null });
  await dialogue.say(script.npc[id].name, r.lines);
  director.popOverlay();
  if (r.gained) gained(r.gained);
  progressed();
}

// 交互前先做的一小段动作：转向目标、播一次性动作，hold 秒后再切镜头
const GLANCE = { E2: { clip: "look_up_k", at: cams.layout.mural_kata.position, hold: 1.2 } };
async function doInteract(forced = null) {
  if (busy || doorBusy) return;
  const it = forced || nearest(); if (!it) return;
  plog.ev("interact", { id: it.id, kind: it.kind, by: forced ? "click" : "key", p: [player.position.x, player.position.z].map((v) => +v.toFixed(2)) });
  const gl = GLANCE[it.id];
  if (gl && actions[gl.clip]) {
    busy = true; faceYaw = Math.atan2(gl.at[0] - player.position.x, gl.at[2] - player.position.z);
    play(gl.clip);
    await new Promise((r) => setTimeout(r, gl.hold * 1000));
    busy = false; faceYaw = null;
  }
  if (it.kind === "npc") { await talkTo(it.id); return; }
  if (it.kind === "gate") {
    const r = game.interact("gate");
    world.gate.visible = false;
    pathfinder.invalidate();   // 推开门以后整条走廊才算可走
    await dialogue.say(null, r.lines);
    progressed();
    return;
  }
  // 线索
  if (it.overlay) director.pushOverlay(it.overlay);
  let r = game.interact(it.id);
  if (!r.ok && r.talkFirst) {
    // 文机和歌山挨着：没见过她就翻簿子时，先说一句、自动和她对话，说完再拿簿子（玩法线 docs/07 第八节）
    director.popOverlay();
    await dialogue.say(null, r.lines);
    await talkTo(r.talkFirst);
    if (it.overlay) director.pushOverlay(it.overlay);
    r = game.interact(it.id);
  }
  if (!r.ok) { await dialogue.say(null, r.lines); director.popOverlay(); return; }
  if (it.mesh) it.mesh.visible = false;
  gained(it.id);
  await dialogue.say(null, [...r.lines, script.evidence[it.id].desc]);
  director.popOverlay();
  progressed();
}
function gained(id) { plog.ev("gain", { id }); toast(`${script.ui.gained}：${script.evidence[id].name}`, 2200, id); }

let cutscene = null;
async function startSword() {
  prompt.set("");
  plog.ev("sword", {}); cancelPath("sword");
  cutscene = runSwordCutscene({ scene, camera, director, player, play, hud, script, cams, temariModel });
  await cutscene.promise;
  cutscene = null;
  game.finishSword();
  endingCard(script, game.endingCard(), game.state.lit);
  plog.ev("ending", { ending: game.state.ending, wrong: game.state.counters.wrongPairs }); plog.flush();
}

// ---- 防卡关提示 ----
function hintTick() {
  if (game.state.phase !== "play" || dialogue.open || panel.open) return;
  const idle = (performance.now() - lastProgress) / 1000;
  const id = game.nextStep(), text = script.hints[id];
  const { first, more } = game.hintDelay(id);   // 教学步 45 / 90 秒，探索步 90 / 150 秒（logic.js）
  if (idle > more && hintLevel < 2) { hintLevel = 2; hud.showHint(text ? text + " " + script.ui.hint_more : ""); plog.ev("hint", { id, level: 2 }); }
  else if (idle > first && hintLevel < 1) { hintLevel = 1; hud.showHint(text || ""); plog.ev("hint", { id, level: 1 }); }
}

// 记录天秤和对话（包一层，不改界面层）
{
  const _put = game.put, _weigh = game.weigh, _show = panel.show.bind(panel), _close = panel.close.bind(panel), _say = dialogue.say.bind(dialogue);
  game.put = (id) => { const r = _put(id); plog.ev("put", { id, ok: r.ok ? 1 : 0, reason: r.reason }); return r; };
  game.weigh = () => { const r = _weigh(); plog.ev("weigh", { result: r.result, lights: r.lights || null, ending: r.ending || null }); return r; };
  panel.show = () => { plog.ev("panel", { open: 1 }); cancelPath("panel"); return _show(); };
  panel.close = () => { if (panel.open) plog.ev("panel", { open: 0 }); return _close(); };
  dialogue.say = (name, lines) => { if (lines && lines.length) plog.ev("say", { name: name || null, n: lines.length, first: String(lines[0]).slice(0, 24) }); return _say(name, lines); };
}

addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); post.resize(); });
window.__game = { plog, onClick, pickTarget, clickTargets, get autoPath() { return autoPath; }, ROOMS, game, player, camera, director, dialogue, panel, world, splat, spark, play, get springs() { return springs; }, get props() { return props; }, get temariModel() { return temariModel; }, get mixer() { return mixer; }, get current() { return current; }, awakenMix, doorways, zoneFor, interact: doInteract, renderer, scene, post, setPatterns: setPatternsEnabled, startSword, keys, step: frame, get currentName() { return currentName; },
  // 把 3D 画面存到 assets/processed/shots/<name>.jpg（开发服务器的 /__shot 接口）
  async shot(name) { const r = await fetch("/__shot", { method: "POST", body: JSON.stringify({ name, data: renderer.domElement.toDataURL("image/jpeg", 0.92) }) }); return r.json(); } };

// 关于 Spark 的排序：它回读 GPU 深度靠定时器轮询，页面在后台（浏览器面板隐藏）时定时器被限到 1 秒甚至 1 分钟一次，
// 一次排序要几秒到几分钟，期间活跃点数是 0、泼溅整块不画。这不是故障，页面可见时排序只要几毫秒。
// 不要加"排序卡住就复位"的看门狗：复位会打断进行中的回读，结果永远是 0。

const clock = new THREE.Clock();
const lastPlayerPos = new THREE.Vector3().copy(player.position);
let currentZone = null, sampleT = 0;
// 一帧：浏览器面板隐藏时 rAF 不跑，验收时用 __game.step(dt) 手动推帧（配合 __game.keys 模拟按键）
function frame(dt) {
  move(dt);
  if (mixer) mixer.update(dt);
  for (const mx of npcMixers) mx.update(dt);
  if (springs) {
    if (lastPlayerPos.distanceToSquared(player.position) > 1) springs.reset();   // 瞬移（?at=、过场摆位）时不让下摆甩出去
    springs.update(dt);
  }
  lastPlayerPos.copy(player.position);
  if (props) props.update(currentName, current ? current.time : 0);
  post.setOutlineMix(awakenMix(currentName, current ? current.time : 0));
  if (cutscene) cutscene.update(performance.now());
  const z = zoneFor(player.position);
  if (!director.overlay && !doorBusy && !cutscene) {
    const inRoom = roomOfZone(currentZone), toRoom = roomOfZone(z);
    if (!inRoom && toRoom) doorTransition(toRoom, true);                                   // 从走廊跨进门洞 → 进房间
    else if (inRoom && (player.position.x - inRoom.exitX) * inRoom.side < 0 && Math.abs(player.position.z - inRoom.doorZ) < 1.0) doorTransition(inRoom, false);   // 走回门口 → 出房间
    else if (!inRoom && z !== currentZone) {
      currentZone = z; director.setZone(z); plog.ev("zone", { z });
      if (z === "Z1_corridor" && !seenRooms.has("corridor")) { seenRooms.add("corridor"); roomCard.show(script.rooms.corridor, true); }
    }
  }
  sampleT += dt;
  if (sampleT >= 0.5) {
    sampleT = 0;
    plog.ev("pos", { p: [player.position.x, player.position.z].map((v) => +v.toFixed(2)), r: +player.rotation.y.toFixed(2), z: currentZone, mv: autoPath ? "click" : keyMoving() ? "key" : null, look: director.look.yaw || director.look.pitch || director.look.zoom !== 1 ? [director.look.yaw, director.look.pitch, director.look.zoom].map((v) => +v.toFixed(2)) : undefined });
  }
  director.update(player);
  if (!cutscene) player.visible = !(director.overlay && cams.zones[director.overlay.id].hidePlayer);
  updateHover();
  updateDoorTags();
  if (pathMarker.visible) { pathMarker.material.opacity = Math.max(0, pathMarker.material.opacity - (autoPath ? 0 : dt * 1.5)); if (pathMarker.material.opacity <= 0) pathMarker.visible = false; }
  const it = nearest();
  prompt.set(it && !busy && !dialogue.open && !panel.open && game.state.phase === "play" ? `E　${it.kind === "npc" ? script.ui.talk + " · " + script.npc[it.id].name : script.ui[it.label]}` : "");
  const signal = dialogue.open || panel.open ? null : game.scaleSignal([player.position.x, 0, player.position.z], cams.npc_positions);
  hud.update(signal, dt);
  hintTick();
  if (usePost) post.render(); else renderer.render(scene, camera);
}
renderer.setAnimationLoop(() => frame(Math.min(clock.getDelta(), 0.1)));
