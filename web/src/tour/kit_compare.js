import * as THREE from "three";
import { SparkRenderer, SplatMesh } from "@sparkjsdev/spark";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { makeToonMaterial } from "../style/toon.js";
import { PaperOutlinePost } from "../style/post.js";
import { attachProps } from "../props.js";
import { loadKit } from "./kit.js";
import cams from "../world/cameras.json";

// 游览版第一步风险试验：大奥走廊的积木版和泼溅版，同一套着色、描边、和纸后期，药郎站同一个位置，四个机位对比。
//   /kit_compare.html?mode=kit     积木版（assets/processed/kit/ooku_corridor_kit.glb，tools/kit_build.py）
//   /kit_compare.html?mode=splat   泼溅版（cameras.json 里的 corridor_v3）
//   &shot=1..4 选机位；按 1 到 4 切，拖动环视，S 存当前画面到 assets/processed/shots/
// 截图脚本用 window.__cmp：shot(i)、step(n)、save(name)
const params = new URLSearchParams(location.search);
const mode = params.get("mode") === "splat" ? "splat" : "kit";
const status = document.getElementById("status");

const scene = new THREE.Scene();
scene.background = new THREE.Color("#F1E9DA");
const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 120);
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
scene.add(new THREE.DirectionalLight(0xffffff, 1));
const post = new PaperOutlinePost(renderer, scene, camera);
post.setFlags({ outline: true, paper: true, letterbox: false });

const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath("/draco/"));
const assetUrl = (u) => (/^(https?:)?\//.test(u) ? u : `/@fs${ASSETS_DIR}/${u}`);
const loading = [];

// ---- 场景 ----
if (mode === "splat") {
  const spark = new SparkRenderer({ renderer }); scene.add(spark);
  const S = cams.layout.splats.find((s) => (s.for || "corridor") === "corridor");
  const m = new SplatMesh({ url: `/@fs${ASSETS_DIR}/worldlabs/${S.name}/splat_${S.quality || "500k"}.spz` });
  const yaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(S.yawDeg || 0));
  m.quaternion.copy(yaw.multiply(new THREE.Quaternion(1, 0, 0, 0)));
  m.scale.setScalar(S.scale); m.position.set(...S.position); m.frustumCulled = false;
  scene.add(m); post.exclude.push(m); post.spark = spark;
  loading.push(m.initialized || Promise.resolve());
} else {
  loading.push(loadKit(loader, assetUrl("processed/kit/ooku_corridor_kit.glb")).then((g) => scene.add(g)));
}

// ---- 药郎（和 game.js 同一个模型、同一套角色纹样） ----
const CHAR_PATTERNS = [
  { color: "#E6667A", tile: "asanoha", patColor: "#F1E9DA", mix: 0.9 },
  { color: "#B42A47", tile: "asanoha", patColor: "#E7A3B5", mix: 0.8 },
  { color: "#2A2A4E", tile: "seigaiha", patColor: "#D6D3EF", mix: 0.85 },
  { color: "#DCC67C", tile: "shippo", patColor: "#B42A47", mix: 0.6 },
  { color: "#49B3A6", tile: "ichimatsu", patColor: "#F1E9DA", mix: 0.5 },
  { color: "#F1E9DA" }, { color: "#D6D3EF" }, { color: "#6A4C8C" }, { color: "#E7A3B5" }, { color: "#4F74BF" }, { color: "#59B86A" }, { color: "#322D48" },
];
const toonFor = (o, pattern) => {
  const map = o.material.map || null; if (map) map.colorSpace = THREE.SRGBColorSpace;
  o.material = makeToonMaterial({ map, color: map ? "#ffffff" : o.material.color.clone(), shadeColor: "#6A4C8C", shadeMix: 0.35, threshold: 0.42, pattern });
};
const player = new THREE.Group(); scene.add(player);
let mixer = null;
loading.push(loader.loadAsync(assetUrl("processed/kusuriuri_v2_posed_layered.glb")).then(async (gltf) => {
  const m = gltf.scene;
  m.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; toonFor(o, { space: "screen", scale: 120, byPalette: CHAR_PATTERNS }); } });
  const box = new THREE.Box3().setFromObject(m), s = 1.7 / (box.max.y - box.min.y);
  m.scale.setScalar(s); m.position.set(-(box.min.x + box.max.x) / 2 * s, -box.min.y * s, -(box.min.z + box.max.z) / 2 * s);
  player.add(m);
  const idle = gltf.animations.find((c) => /idle_k/.test(c.name)) || gltf.animations.find((c) => /idle/.test(c.name));
  if (idle) { mixer = new THREE.AnimationMixer(m); mixer.clipAction(idle).play(); mixer.setTime(0.5); }   // 定在待机的同一帧，两版姿势一样
  await attachProps(m, loader, assetUrl, (o) => toonFor(o, null)).catch(() => {});
}));

// ---- 四个机位（游览版方案第六节） ----
const SHOTS = [
  { name: "1_入口一点透视", cam: [0, 1.5, -1.9], look: [0, 2.1, -13], player: [0.55, 0, -4.8], yaw: 0.45 },
  { name: "2_药郎正侧面", cam: [2.0, 1.25, -6.4], look: [-0.4, 1.05, -6.4], player: [-0.4, 0, -6.4], yaw: Math.PI },
  { name: "3_贴近左墙0.8米", cam: [-1.7, 1.5, -3.9], look: [-1.1, 1.3, -9], player: [-0.8, 0, -6.6], yaw: 0.35 },
  { name: "4_回头看门口", cam: [0.3, 1.6, -8.6], look: [0, 1.7, 0], player: [0, 0, -5.4], yaw: 0 },
];
let cur = 0, lookYaw = 0, lookPitch = 0;
function shot(i) {
  cur = i; lookYaw = lookPitch = 0;
  const S = SHOTS[i];
  player.position.set(...S.player); player.rotation.y = S.yaw;
  applyCam();
  status.textContent = `${mode === "kit" ? "积木版" : "泼溅版"} · 机位 ${S.name}（1~4 切机位，拖动环视，S 存图）`;
}
function applyCam() {
  const S = SHOTS[cur];
  camera.position.set(...S.cam); camera.lookAt(...S.look);
  camera.rotateOnWorldAxis(new THREE.Vector3(0, 1, 0), lookYaw); camera.rotateX(lookPitch);
}

let drag = null;
renderer.domElement.addEventListener("pointerdown", (e) => (drag = { x: e.clientX, y: e.clientY }));
addEventListener("pointerup", () => (drag = null));
addEventListener("pointermove", (e) => {
  if (!drag) return;
  lookYaw -= (e.clientX - drag.x) * 0.004; lookPitch = Math.max(-1, Math.min(1, lookPitch - (e.clientY - drag.y) * 0.004));
  drag = { x: e.clientX, y: e.clientY }; applyCam();
});
addEventListener("keydown", (e) => {
  if (/^Digit[1-4]$/.test(e.code)) shot(+e.code.slice(5) - 1);
  if (e.code === "KeyS") save();
});
addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); post.resize(); });

function frame() { post.render(); }
async function save(name = `kitcmp_${mode}_${SHOTS[cur].name}`) {
  frame();
  const data = renderer.domElement.toDataURL("image/jpeg", 0.92);
  return (await fetch("/__shot", { method: "POST", body: JSON.stringify({ name, data }) })).json();
}
window.__cmp = { mode, shots: SHOTS, shot, save, step: (n = 1) => { for (let i = 0; i < n; i++) frame(); }, camera, scene, renderer, post, ready: Promise.all(loading) };

shot(Math.max(0, Math.min(3, (+params.get("shot") || 1) - 1)));
Promise.all(loading).then(() => { status.textContent += " · 已加载"; window.__cmp.loaded = true; if (params.get("auto")) autoShots(); }).catch((e) => (status.textContent = "加载失败：" + e.message));
renderer.setAnimationLoop(frame);

// ?auto=1：加载完依次拍四个机位存图（给无头 Chrome 用，内置浏览器 WebGL 被禁时走这条），拍完把标题改成 DONE
async function autoShots() {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  status.style.display = "none";
  await wait(mode === "splat" ? 6000 : 2500);   // 贴图、泼溅排序要一会
  for (let i = 0; i < SHOTS.length; i++) { shot(i); await wait(mode === "splat" ? 2500 : 800); await save(); }
  document.title = "DONE";
}
