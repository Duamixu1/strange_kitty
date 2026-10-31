import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { makeToonMaterial } from "./style/toon.js";
import { PaperOutlinePost } from "./style/post.js";
import { attachProps } from "./props.js";
import { SpringBones } from "./spring.js";

// 角色画风样片：把 Tripo 轻量模型套上 2 阶平涂，再走一遍"描边 + 和纸"后期。
// 模型默认读 ../assets/processed/kusuriuri_v1_lite.glb，?model= 可换（相对 assets/ 的路径或完整 URL）。
// 模型里带动画的话，按 5 到 9 切动作，一次性动作播完回 idle。
// 模型里有挂点（socket_*）的话，按 src/data/props.json 自动挂剑、药箱、天秤；?props=0 不挂。
// 模型里有骨链（chain_*，下摆、大袖、长发）的话，用弹簧骨驱动，参数在 src/data/spring.json；按 J 开关，?spring=0 不开。
const params = new URLSearchParams(location.search);
const modelParam = params.get("model") || "processed/kusuriuri_v1_lite.glb";
const assetUrl = (p) => (/^(https?:)?\//.test(p) ? p : `/@fs${ASSETS_DIR}/${p}`);
const modelUrl = assetUrl(modelParam);
const status = document.getElementById("status");
const animHud = document.getElementById("anims");

const PAPER = "#F1E9DA";
const HEIGHT = 1.7;
const scene = new THREE.Scene();
scene.background = new THREE.Color(PAPER);
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.05, 50);
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

// 光：一盏主光，从镜头左上前方打；平涂阶数靠阈值，不靠光强
const key = new THREE.DirectionalLight(0xffffff, 1);
key.position.set(-1.5, 3, 2.5);
scene.add(key);

// 地面：一块地毯红圆片，让描边有个"地"可落，也方便看脚底
const ground = new THREE.Mesh(
  new THREE.CircleGeometry(1.1, 48).rotateX(-Math.PI / 2),
  makeToonMaterial({ color: "#E6667A", shadeColor: "#B42A47" }),
);
scene.add(ground);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.9, 0);

const presets = {
  Digit1: { pos: [0, 1.0, 4.6], target: [0, 0.88, 0] },        // 全身正面
  Digit2: { pos: [0.25, 1.52, 1.05], target: [0, 1.47, 0] },   // 脸
  Digit3: { pos: [0, 1.0, -4.6], target: [0, 0.88, 0] },       // 背面
  Digit4: { pos: [2.6, 1.3, 3.6], target: [0, 0.88, 0] },      // 斜侧
  DigitC: { pos: [0, 1.2, 2.1], target: [0, 1.0, 0] },         // 上半身正面（只给 ?auto 的 views=C 用）
  DigitD: { pos: [1.5, 1.2, 1.5], target: [0, 1.0, 0] },       // 上半身斜侧
  DigitT: { pos: [0, 3.0, 0.35], target: [0, 1.0, 0] },        // 俯视（看前臂朝向）
  DigitF: { pos: [0.7, 0.3, 1.3], target: [0, 0.12, 0] },       // 脚边（看脚底落地、下摆穿地）
  DigitS: { pos: [-4.2, 0.95, 0], target: [0, 0.85, 0] },       // 正侧面（角色朝 +z，镜头在他右手边）
  DigitH: { pos: [-1.1, 0.75, 0.25], target: [-0.2, 0.75, 0] },   // 右手和右袖近景（从角色右边看）
  DigitK: { pos: [-1.6, 0.3, 0.25], target: [0, 0.12, 0.25] },     // 脚边正侧面近景（看脚落地滑不滑，配 &follow=0）
  DigitB: { pos: [0.25, 1.52, -1.05], target: [0, 1.47, 0] },     // 后脑勺近景（查双面头）
  DigitX: { pos: [-1.2, 1.45, 0], target: [0, 1.4, 0] },          // 头部正侧面近景（看后脑勺剪影）
  DigitU: { pos: [-0.45, 0.25, 0.35], target: [-0.25, 0.7, 0] },   // 右袖从下往上看
  DigitL: { pos: [4.2, 0.95, 0], target: [0, 0.85, 0] },          // 左正侧面（看剑从身前横过时离左袖多远）
  DigitV: { pos: [0, 2.4, 1.6], target: [0, 1.0, 0.3] },          // 前上方俯看（看剑在身前多远）
};
function applyPreset(k) {
  const p = presets[k]; if (!p) return;
  camera.position.set(...p.pos); controls.target.set(...p.target); controls.update();
}
applyPreset("Digit1");

const post = new PaperOutlinePost(renderer, scene, camera);
const flags = { toon: true, outline: true, paper: true, letterbox: false, twos: false, spring: true };  // twos = 一拍二：动画按 12 帧/秒定帧
let plainMaterials = null, toonMaterials = null, model = null, props = null, springs = null;

// ---- 动画 ----
const ANIM_KEYS = ["Digit5", "Digit6", "Digit7", "Digit8", "Digit9", "Digit0", "Minus", "Equal", "BracketLeft", "BracketRight", "Backslash"];
const ONE_SHOT = new Set(["turn", "look_around", "slash", "agree", "bow", "cast_a_spell", "hurt", "greet_01", "greet_02"]);
let mixer = null, actions = {}, clipNames = [], current = null, currentName = null;
function clipKey(name) { return name.replace(/^preset:(biped:)?/, "").replace(/\|.*$/, "").toLowerCase(); }
// 一次性动作：Tripo 预设里列出的几个，以及手 K 的 *_k 里除了待机、走路、驻足看、拍照姿势这些循环动作之外的全部
function isOneShot(name) { return ONE_SHOT.has(name) || (name.endsWith("_k") && !/^(idle|walk|gaze|pose_)/.test(name)); }
function play(name, { once = isOneShot(name) } = {}) {
  const next = actions[name]; if (!next) return;
  if (current && current !== next) current.fadeOut(0.25);
  next.reset();
  next.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
  next.clampWhenFinished = once;
  next.fadeIn(current ? 0.25 : 0).play();
  current = next; currentName = name;
  if (springs) springs.reset();
  status.textContent = `动作 ${name}${once ? "（一次）" : ""}`;
}

// Tripo 的 animate_in_place 会把髋骨的水平位移冻在某个终点（walk 整条偏 1.4 个单位），
// 这里把每个剪辑里髋骨位置轨道"整体偏离静止位超过 0.2"的分量归回静止位，小幅上下起伏保留。
function fixRootDrift(root, clips) {
  const rest = new Map();
  root.traverse((o) => { if (o.isBone) rest.set(o.name, o.position.clone()); });
  for (const clip of clips) {
    for (const t of clip.tracks) {
      if (!t.name.endsWith(".position")) continue;
      const bone = t.name.slice(0, -".position".length);
      const r = rest.get(bone); if (!r) continue;
      const v = t.values, n = v.length / 3, rv = [r.x, r.y, r.z];
      for (let c = 0; c < 3; c++) {
        let dev = 0;
        for (let i = 0; i < n; i++) dev = Math.max(dev, Math.abs(v[i * 3 + c] - rv[c]));
        if (dev > 0.2) for (let i = 0; i < n; i++) v[i * 3 + c] = rv[c];
      }
    }
  }
}

addEventListener("keydown", (e) => {
  if (presets[e.code]) applyPreset(e.code);
  if (e.code === "KeyO") flags.outline = !flags.outline;
  if (e.code === "KeyP") flags.paper = !flags.paper;
  if (e.code === "KeyL") flags.letterbox = !flags.letterbox;
  if (e.code === "KeyT") { flags.toon = !flags.toon; swapMaterials(); }
  if (e.code === "KeyJ") { flags.spring = !flags.spring; status.textContent = `弹簧骨 ${flags.spring ? "开" : "关"}`; return; }
  if (e.code === "KeyK") { flags.twos = !flags.twos; status.textContent = `一拍二 ${flags.twos ? "开" : "关"}`; return; }
  const slot = ANIM_KEYS.indexOf(e.code);
  const m = slot >= 0 && clipNames[slot];
  if (m) play(clipNames[slot]);
  post.setFlags(flags);
  if (!m) status.textContent = `平涂 ${flags.toon ? "开" : "关"} · 描边 ${flags.outline ? "开" : "关"} · 和纸 ${flags.paper ? "开" : "关"}`;
});
function swapMaterials() {
  if (!model) return;
  model.traverse((o) => { if (o.isMesh) o.material = (flags.toon ? toonMaterials : plainMaterials).get(o); });
}

// 给一个网格建平涂 / 原色两套材质。没有贴图的（比如生成的刀身）用材质本身的颜色。
// 妖化的形态键：style/toon.js 自己支持了（总指挥 10-28 加的），这里不用再补
function dress(o) {
  const map = o.material.map || null;
  if (map) { map.colorSpace = THREE.SRGBColorSpace; map.anisotropy = 4; }
  const color = map ? "#ffffff" : o.material.color.clone();
  plainMaterials.set(o, new THREE.MeshBasicMaterial({ map, color }));
  toonMaterials.set(o, makeToonMaterial({ map, color, shadeColor: "#6A4C8C", shadeMix: 0.35, threshold: 0.42 }));
  o.material = (flags.toon ? toonMaterials : plainMaterials).get(o);
}

const draco = new DRACOLoader().setDecoderPath("/draco/");
const loader = new GLTFLoader().setDRACOLoader(draco);
loader.load(modelUrl, (gltf) => {
  model = gltf.scene;
  plainMaterials = new Map(); toonMaterials = new Map();
  let tris = 0;
  model.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = false;  // 蒙皮模型的包围盒不随动作更新，关掉以免被裁掉
    tris += o.geometry.index ? o.geometry.index.count / 3 : o.geometry.attributes.position.count / 3;
    dress(o);
  });
  // 统一身高：Tripo 导入的模型尺寸不定，按包围盒缩到 1.7 米、脚底落地
  const box = new THREE.Box3().setFromObject(model);
  const h = box.max.y - box.min.y;
  const s = HEIGHT / h;
  model.scale.setScalar(s);
  model.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
  scene.add(model);
  model.updateMatrixWorld(true);
  if (params.get("spring") !== "0") {
    springs = new SpringBones(model);
    if (!springs.count) springs = null;
  }

  if (gltf.animations.length) {
    fixRootDrift(model, gltf.animations);
    mixer = new THREE.AnimationMixer(model);
    for (const clip of gltf.animations) {
      const name = clipKey(clip.name);
      actions[name] = mixer.clipAction(clip);
      clipNames.push(name);
    }
    mixer.addEventListener("finished", () => { const back = actions.idle_k ? "idle_k" : actions.idle ? "idle" : null; if (back) play(back); });
    animHud.textContent = clipNames.map((n, i) => `${(ANIM_KEYS[i] || "?").replace("Digit", "").replace("Minus", "-").replace("Equal", "=").replace("BracketLeft", "[").replace("BracketRight", "]").replace("Backslash", "\\")}=${n}`).join(" ") + " · K 一拍二";
    play(actions.idle_k ? "idle_k" : actions.idle ? "idle" : clipNames[0]);
  }
  status.textContent = `已加载 · ${Math.round(tris / 1000)}k 面 · ${gltf.animations.length} 个动作 · 原高 ${h.toFixed(2)}` + (springs ? ` · 骨链 ${springs.chains.length} 条` : "");
  if (params.get("props") !== "0") {
    attachProps(model, loader, assetUrl, dress).then((p) => {
      props = p;
      if (p.list.length) status.textContent += ` · 道具 ${p.list.map((x) => x.id).join("、")}`;
    }).catch((err) => { console.error(err); status.textContent += " · 道具加载失败"; });
  }
}, undefined, (err) => { status.textContent = "加载失败：" + err.message; console.error(err); });

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); post.resize();
});

// 调试接口：截图脚本可以直接摆相机、切开关、切动作、定格到某一秒
window.__viewer = {
  camera, controls, flags, post, get mixer() { return mixer; }, get clips() { return clipNames; }, get props() { return props; },
  setPose(x, y, z, tx, ty, tz) { camera.position.set(x, y, z); controls.target.set(tx, ty, tz); controls.update(); },
  preset: applyPreset, play,
  setFlags(f) { Object.assign(flags, f); swapMaterials(); post.setFlags(flags); },
  // 定格到某一秒：跳过交叉淡入，直接只保留当前动作，截图用
  seek(t) { if (!current) return; mixer.stopAllAction(); current.reset().setEffectiveWeight(1).play(); current.paused = true; current.time = t; mixer.update(0); if (springs && flags.spring) { springs.reset(); springs.settle(); } },
  get springs() { return springs; },
  resume() { if (current) current.paused = false; },
};

// ?auto=动作:秒,动作:秒&views=1,3,4&prefix=名字：加载完按顺序定格、按机位（1 正面 2 脸 3 背面 4 斜侧 C 上半身正面 D 上半身斜侧 T 俯视 F 脚边 S 正侧面 H 右手右袖近景 U 右袖仰视 K 脚边侧面近景 B 后脑勺近景 X 头部正侧面 L 左正侧面 V 前上方俯看）拍，
// 存到 assets/processed/shots/<prefix>_<动作>_<秒>_<机位>.jpg，拍完标题改成 DONE。给无头 Chrome 用（tools/char_shots.sh）
if (params.get("auto")) {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  (async () => {
    while (!mixer || (params.get("props") !== "0" && !props)) await wait(200);
    await wait(800);
    const views = (params.get("views") || "1,4").split(",");
    // &move=米/秒：走路动作边播边往前走（模拟游戏里），弹簧骨真的跑起来不定格，先走 1.2 秒热身再拍第 t 秒；
    // 地上铺一条每 25 厘米一道墨线的地带，支撑脚相对墨线不动就是不滑；镜头跟着身体平移
    const move = +params.get("move") || 0, z0 = model.position.z, follow = params.get("follow") !== "0";
    let camDz = null;   // &follow=0：镜头只在拍第一张时对准身体，之后不动，脚踩的墨线在画面里该一动不动
    if (move) {
      autoSim = true;
      const strip = new THREE.Group();
      strip.add(new THREE.Mesh(new THREE.PlaneGeometry(1.6, 16).rotateX(-Math.PI / 2).translate(0, 0.002, 6), makeToonMaterial({ color: "#D6D3EF", shadeColor: "#6A4C8C" })));
      for (let z = -2; z <= 14; z += 0.25) { const m = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.004, z % 1 === 0 ? 0.03 : 0.012), makeToonMaterial({ color: "#322D48" })); m.position.set(0, 0.004, z); strip.add(m); }
      scene.add(strip);
    }
    for (const item of params.get("auto").split(",")) {
      const [clip, t] = item.split(":");
      if (move) {
        play(clip, { once: false }); mixer.stopAllAction(); current.reset().setEffectiveWeight(1).play();
        model.position.z = z0; model.updateMatrixWorld(true); if (springs) springs.reset();
        const dt = 1 / 60, T = 1.2 + (+t || 0);
        for (let tt = 0; tt < T - 1e-6; tt += dt) {
          mixer.update(dt); model.position.z += move * dt; model.updateMatrixWorld(true);
          if (springs && flags.spring) springs.update(dt);
          if (props) props.update(currentName, current.time);
        }
      } else { play(clip); window.__viewer.seek(+t || 0); }
      for (const v of views) {
        applyPreset("Digit" + v);
        if (move) { if (follow || camDz === null) camDz = model.position.z - z0; camera.position.z += camDz; controls.target.z += camDz; controls.update(); }
        post.render();
        const name = `${params.get("prefix") || "char"}_${clip}_${t || 0}_${v}`;
        await fetch("/__shot", { method: "POST", body: JSON.stringify({ name, data: renderer.domElement.toDataURL("image/jpeg", 0.9) }) });
      }
    }
    document.title = "DONE";
  })();
}

const clock = new THREE.Clock();
let twosAcc = 0, autoSim = false;   // autoSim：?auto&move 自己推帧，渲染循环不再更新动画和弹簧骨
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.1);
  if (mixer && !autoSim) {
    if (flags.twos) { twosAcc += dt; if (twosAcc >= 1 / 12) { mixer.update(twosAcc); if (springs && flags.spring) springs.update(twosAcc); twosAcc = 0; } }
    else { mixer.update(dt); if (springs && flags.spring) springs.update(dt); }
  }
  if (props && !autoSim) props.update(currentName, current ? current.time : 0);
  controls.update();
  post.render();
});
