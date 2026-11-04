import * as THREE from "three";
import { makeToonMaterial } from "../style/toon.js";
import { SpringBones } from "../spring.js";
import { attachProps } from "../props.js";
import { WalkLayer } from "./walk_layer.js";

// 药郎：和探案版同一个模型、同一套角色纹样（game.js 那份冻结了，这里复制一份）。
// 动作和触发时机见 docs/17_游览版动作.md（角色线，游6）：站着 idle、走 walk、开说明卡 gaze（高处的观景点 look）、
// 站久了偶尔 idle_alt（抱臂一下）、拍照姿势 photo_fold / photo_back。一次性动作播完自动回 idle。
const CHAR_PATTERNS = [
  { color: "#E6667A", tile: "asanoha", patColor: "#F1E9DA", mix: 0.9 },
  { color: "#B42A47", tile: "asanoha", patColor: "#E7A3B5", mix: 0.8 },
  { color: "#2A2A4E", tile: "seigaiha", patColor: "#D6D3EF", mix: 0.85 },
  { color: "#DCC67C", tile: "shippo", patColor: "#B42A47", mix: 0.6 },
  { color: "#49B3A6", tile: "ichimatsu", patColor: "#F1E9DA", mix: 0.5 },
  { color: "#F1E9DA" }, { color: "#D6D3EF" }, { color: "#6A4C8C" }, { color: "#E7A3B5" }, { color: "#4F74BF" }, { color: "#59B86A" }, { color: "#322D48" },
];
const ALIAS = { exorcise: ["exorcise_k"], exorcise_short: ["exorcise_short_k"], idle: ["idle_k", "idle"], walk: ["walk2_k", "walk_k", "walk"], run: ["walk_fast_k", "walk2_k", "walk_k"], sprint: ["run_k", "walk_fast_k", "walk2_k"], gaze: ["gaze_k", "idle_k"], look: ["look_up_k", "idle_k"],
  idle_alt: ["idle2_k"], turn: ["turn_k"], photo_fold: ["pose_fold_k"], photo_back: ["pose_back_k"] };
const LOOPING = new Set(["ready_k", "idle_k", "idle", "walk_k", "walk", "walk2_k", "walk_fast_k", "run_k", "gaze_k", "pose_fold_k", "pose_back_k"]);
// 走路动作本身的地面速度（米/秒，支撑脚往后蹬的速度，角色线在 Blender 里量的，1.7 米身高）。
// 播放倍率 = 实际移动速度 ÷ 这个值，脚才不打滑。walk2_k / walk_fast_k 是 10-30 角色线用腿 IK 算的（一步 0.6 / 0.71 米），
// walk_k 是探案版的旧走路（步子小、支撑脚还往前蹭），只在没有新动作的模型上兜底。
const CLIP_SPEED = { walk2_k: 0.962, walk_fast_k: 1.774, run_k: 2.829, walk_k: 0.3 };   // 10-31 角色线重量（tools/walk_measure.py，按绑定姿势 1.7 米算）；腿改按三维长度算后重做

export async function loadPlayer(loader, assetUrl, { model = "processed/kusuriuri_v2_posed_layered.glb", springs = true, props = true, layer: useLayer = true } = {}) {
  const group = new THREE.Group();
  const toonFor = (o, pattern) => {
    const map = o.material.map || null; if (map) map.colorSpace = THREE.SRGBColorSpace;
    o.material = makeToonMaterial({ map, color: map ? "#ffffff" : o.material.color.clone(), shadeColor: "#6A4C8C", shadeMix: 0.35, threshold: 0.42, pattern });
  };
  const gltf = await loader.loadAsync(assetUrl(model));
  const m = gltf.scene;
  m.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; toonFor(o, { space: "screen", scale: 120, byPalette: CHAR_PATTERNS, maxY: 0.91 }); } });   // maxY：帽子（身体网格绑定高度 0.91 以上，头发最高 0.89）不铺纹样
  const box = new THREE.Box3().setFromObject(m), s = 1.7 / (box.max.y - box.min.y);
  m.scale.setScalar(s); m.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
  group.add(m); group.updateMatrixWorld(true);
  m.traverse((o) => o.layers.enable(3));   // 第 3 图层：妖化红描边只给药郎（post.js 的 maskLayer）
  const mixer = new THREE.AnimationMixer(m), actions = {};
  for (const clip of gltf.animations) actions[clip.name.replace(/^preset:(biped:)?/, "").replace(/\|.*$/, "").toLowerCase()] = mixer.clipAction(clip);
  let current = null, currentName = null;
  let idleOverride = null;   // 物怪出没时"待机"换成戒备 ready_k（setIdle）
  const resolve = (name) => (name === "idle" && idleOverride && actions[idleOverride] ? idleOverride : null) || (ALIAS[name] || [name]).find((k) => actions[k]) || null;
  // speed：播放倍率；from：从第几秒开始（物怪出没的占位动作用，角色线的新动作到了就不用）
  function play(name, fade = 0.2, { speed = 1, from = 0 } = {}) {
    const key = resolve(name); if (!key) return;
    const a = actions[key]; if (a === current && speed === 1 && !from) return;
    if (current && current !== a) current.fadeOut(fade);
    a.reset(); a.timeScale = speed; a.time = from;
    if (LOOPING.has(key)) a.setLoop(THREE.LoopRepeat, Infinity); else { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }
    a.fadeIn(fade).play(); current = a; currentName = key;
  }
  mixer.addEventListener("finished", (e) => { if (e.action === current) play("idle", 0.4); });   // 抬头看、抱臂一下这类一次性动作播完回待机
  play("idle");
  const sb = springs ? new SpringBones(m) : null;
  const pr = props ? await attachProps(m, loader, assetUrl, (o) => toonFor(o, null)).catch(() => null) : null;
  pr?.list.forEach((p) => { if (p.id !== "medicine_chest") p.prop.traverse((o) => o.layers.enable(3)); });   // 剑也跟着妖化变红（药箱拔剑时放在地上，不变红）
  const layer = useLayer ? new WalkLayer(m, group) : { restore() {}, apply() {}, reset() {}, target: null };   // 拐弯内倾、起停余摆、头先转（walk_layer.js）；?layer=0 关掉对比
  // 上半身层（物怪出没，docs/18）：投札、袖挡这类动作只取 Spine01 往上的骨头（不含下摆、袖子、头发的弹簧骨）的转动，
  // 叠在当前的全身动作上播，走路时腿照走。另开一个 mixer 算出上半身的姿势，再和全身动作的结果按权重插值，
  // 头尾各 fade 秒淡入淡出；腰那两节只叠一部分，转身不会从腰上折断
  const upperW = new Map();
  m.getObjectByName("Spine01")?.traverse((o) => { if (o.isBone && !o.name.startsWith("chain_")) upperW.set(o, o.name === "Spine01" ? 0.5 : o.name === "Spine02" ? 0.8 : 1); });
  const upperNames = new Set([...upperW.keys()].map((o) => o.name));
  const upperMixer = new THREE.AnimationMixer(m), upperClips = {}, upperA = new Map(), _q = new THREE.Quaternion();
  let upper = null;
  function upperClip(key) {
    if (!upperClips[key]) { const c = actions[key].getClip(); upperClips[key] = new THREE.AnimationClip(`${key}_upper`, c.duration, c.tracks.filter((t) => t.name.endsWith(".quaternion") && upperNames.has(t.name.split(".")[0]))); }
    return upperClips[key];
  }
  function applyUpper(dt) {
    if (!upper) return;
    for (const b of upperW.keys()) upperA.set(b, b.quaternion.clone());
    upperMixer.update(dt);
    const a = upper.a, dur = a.getClip().duration / Math.abs(a.timeScale || 1), t = a.time / Math.abs(a.timeScale || 1);
    const w = Math.max(0, Math.min(1, t / upper.fade, (dur - t) / upper.fade));
    for (const [b, k] of upperW) { _q.copy(b.quaternion); b.quaternion.copy(upperA.get(b)).slerp(_q, w * k); }
    if (a.time >= a.getClip().duration - 1e-4) { a.stop(); upper = null; }
  }
  let last = new THREE.Vector3();
  return {
    group, play, get currentName() { return currentName; }, get time() { return current ? current.time : 0; }, props: pr ? pr.list : [],
    /** 模型里有没有这个动作（别名也算）；duration 是它的秒数 */
    has(name) { return !!resolve(name); },
    /** 换"待机"用哪个动作（null = 默认 idle_k）；正在待机就顺手切过去 */
    setIdle(clip) { const was = currentName === resolve("idle"); idleOverride = clip; if (was) play("idle", 0.3); },
    duration(name) { const k = resolve(name); return k ? actions[k].getClip().duration : 0; },
    /** 上半身层播一个一次性动作（只取上半身轨道）；speed 播放倍率，fade 淡入淡出秒数 */
    playUpper(name, { speed = 1, fade = 0.12 } = {}) {
      const key = resolve(name); if (!key) return false;
      if (upper) upper.a.stop();
      const a = upperMixer.clipAction(upperClip(key));
      a.reset(); a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; a.timeScale = speed; a.play();
      upper = { a, key, fade }; return true;
    },
    get upperName() { return upper ? upper.key : null; },
    get upperTime() { return upper ? upper.a.time : 0; },
    /** 右手（札从这里飞出去）：有挂点用挂点，没有用手骨 */
    hand: m.getObjectByName("socket_R_Hand") || m.getObjectByName("R_Hand") || m,
    /** 走路时每帧调：按实际移动速度（米/秒）调走路动作的播放倍率，倍率限在 0.5 到 3 之间 */
    setMoveSpeed(v) {
      if (!current || !CLIP_SPEED[currentName]) return;
      current.timeScale = Math.min(3, Math.max(0.5, v / CLIP_SPEED[currentName]));
    },
    /** 要转去的朝向（弧度），头会先看过去 */
    setFacing(yaw) { layer.target = yaw; },
    resetSprings() { layer.reset(); if (sb && sb.count) { group.updateMatrixWorld(true); sb.reset(); } },   // 切拍照姿势时下摆、长发会甩，先归位
    update(dt) {
      layer.restore();
      mixer.update(dt);
      applyUpper(dt);
      layer.apply(dt);
      if (pr && currentName) pr.update(currentName, current.time);
      if (sb && sb.count) {
        group.updateMatrixWorld(true);
        if (last.distanceToSquared(group.position) > 1) sb.reset();   // 瞬移（换区块）时不让下摆甩出去
        sb.update(dt);
      }
      last.copy(group.position);
    },
  };
}

// 配角（游览版不对话）：和药郎同一套平涂 + 角色纹样，身高按包围盒归一，待机起点错开。
// 让画面活一点（游15）：
//   idles: ["bow_k", "look_k", ...]  站着时每隔 gap 秒（默认 8~16 秒随机）播其中一个一次性动作，播完回待机；模型里没有的名字跳过
//   patrol: [[x, z], ...]            沿这条折线来回走，到头停 pause 秒（默认 3）；speed 米/秒（默认 0.7），播 walk_k / walk2_k（没有就待机滑过去）
//   药郎走到 1.1 米以内，巡逻的配角停下来转身看他，走开 2 秒后再接着走
export async function loadNpc(loader, assetUrl, { model, height = 1.5, clip = "idle", idles = [], gap = [8, 16] }) {
  const gltf = await loader.loadAsync(assetUrl(model));
  const m = gltf.scene;
  m.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = false;
    const map = o.material.map || null; if (map) map.colorSpace = THREE.SRGBColorSpace;
    o.material = makeToonMaterial({ map, color: map ? "#ffffff" : o.material.color.clone(), shadeColor: "#6A4C8C", shadeMix: 0.35, threshold: 0.42, pattern: { space: "screen", scale: 120, byPalette: CHAR_PATTERNS } });
  });
  const box = new THREE.Box3().setFromObject(m), s = height / (box.max.y - box.min.y);
  m.scale.setScalar(s); m.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
  const group = new THREE.Group(); group.add(m);
  const clips = Object.fromEntries(gltf.animations.map((a) => [a.name.replace(/\|.*$/, "").toLowerCase(), a]));
  const find = (...names) => names.map((n) => clips[n] || Object.values(clips).find((c) => c.name.toLowerCase().includes(n))).find(Boolean);
  const idleClip = find(clip, "idle_k", "idle"), walkClip = find("walk2_k", "walk_k", "walk");
  const extra = idles.map((n) => clips[n]).filter(Boolean);
  if (!idleClip) return { group, update() {}, play() {}, hasWalk: false };
  const mixer = new THREE.AnimationMixer(m);
  let cur = mixer.clipAction(idleClip); cur.play(); cur.time = Math.random() * idleClip.duration;
  function play(c, once = false) {
    const a = mixer.clipAction(c); if (a === cur) return;
    cur.fadeOut(0.35); a.reset();
    if (once) { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; } else a.setLoop(THREE.LoopRepeat, Infinity);
    a.fadeIn(0.35).play(); cur = a;
  }
  mixer.addEventListener("finished", (e) => { if (e.action === cur) play(idleClip); });
  let wait = gap[0] + Math.random() * (gap[1] - gap[0]);
  return {
    group, hasWalk: !!walkClip,
    // mode: "idle" 站着（会偶尔换姿势）、"walk" 走
    update(dt, mode = "idle") {
      if (mode === "walk") { if (walkClip) play(walkClip); wait = gap[0]; }
      else {
        if (walkClip && cur.getClip() === walkClip) play(idleClip);
        if (extra.length && cur.getClip() === idleClip && (wait -= dt) <= 0) {
          play(extra[Math.floor(Math.random() * extra.length)], true);
          wait = gap[0] + Math.random() * (gap[1] - gap[0]);
        }
      }
      mixer.update(dt);
    },
  };
}
