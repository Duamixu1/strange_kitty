import * as THREE from "three";
import { clone as cloneSkinned } from "three/addons/utils/SkeletonUtils.js";
import { makeToonMaterial } from "../style/toon.js";

// 物怪出没的特效和占位物怪（docs/18，总指挥）。都是程序生成，不用贴图文件：
//   札：纸条 + 红框 + 墨字，飞出去带几张残影，钉中时啪地贴在物怪身上、抖一下
//   札阵：形真理齐了，一圈札绕着物怪转，连成一条红线，结印时收紧
//   墨溅：钉中时溅一小把墨点；消散：物怪化成墨滴往上飘散
//   字：形 / 真 / 理 在物怪头上浮起来，下面一句话（DOM，tour.html 的 #mk）
// 物怪本体：角色线按原作做的三只（docs/17 第十五节：化猫 bakeneko、唐伞 karakasa、座敷童子 zashiki），loadMonster 加载；
// 模型还没下完（或者加载失败）先用占位的墨影：一团会变形的墨色剪影，前面一张纸面具，身后拖几节墨尾。
// 两种接口一样：group、center()、play(状态)、stretch / glow / squash / fade / hover、update(dt)、resetTrail()、dispose()

const INK = new THREE.Color("#221C33"), PAPER = "#F1E9DA", VERMILION = "#B42A47";
const rnd = (a, b) => a + Math.random() * (b - a);

function canvasTex(w, h, draw) {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// 魂光的贴图：暖白的一团，外圈一道淡金的环（退魔后执念散了、魂走了）
const SOUL_TEX = () => canvasTex(128, 128, (g, w) => {
  const r = w / 2, gr = g.createRadialGradient(r, r, 0, r, r, r);
  gr.addColorStop(0, "rgba(255,250,235,1)"); gr.addColorStop(0.25, "rgba(255,240,205,.85)"); gr.addColorStop(0.55, "rgba(235,200,120,.25)"); gr.addColorStop(1, "rgba(235,200,120,0)");
  g.fillStyle = gr; g.fillRect(0, 0, w, w);
  g.strokeStyle = "rgba(201,162,58,.9)"; g.lineWidth = 3; g.beginPath(); g.arc(r, r, r * 0.6, 0, Math.PI * 2); g.stroke();   // 金环：浅色墙前也看得出
  g.strokeStyle = "rgba(201,162,58,.35)"; g.lineWidth = 2; g.beginPath(); g.arc(r, r, r * 0.8, 0, Math.PI * 2); g.stroke();
});

// 光晕：物怪身后一团很淡的暖光，暗区块里把黑色的身形托出来（encounter.js 的 RIM_ZONES）
export const HALO_TEX = () => canvasTex(128, 128, (g, w) => {
  const r = w / 2, gr = g.createRadialGradient(r, r, 0, r, r, r);
  // 到七成半径就淡没了：贴片外圈要是还有一点亮，碰到地板会被切出一条直边，看着像个方块
  gr.addColorStop(0, "rgba(255,236,196,.75)"); gr.addColorStop(0.3, "rgba(250,226,180,.45)"); gr.addColorStop(0.55, "rgba(246,220,170,.14)"); gr.addColorStop(0.72, "rgba(246,220,170,0)"); gr.addColorStop(1, "rgba(246,220,170,0)");
  g.fillStyle = gr; g.fillRect(0, 0, w, w);
});

// 札的贴图：和纸底、朱红双框、中间一列墨写的"字"（抽象的笔画，不写真字）、下面一个朱印
const OFUDA_TEX = () => canvasTex(64, 192, (g, w, h) => {
  g.fillStyle = PAPER; g.fillRect(0, 0, w, h);
  g.strokeStyle = VERMILION; g.lineWidth = 3; g.strokeRect(4, 4, w - 8, h - 8); g.lineWidth = 1.5; g.strokeRect(9, 9, w - 18, h - 18);
  g.strokeStyle = "#2A2A4E"; g.lineWidth = 4; g.lineCap = "round";
  let seed = 3; const r = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let y = 22; y < 140; y += 18) { g.beginPath(); g.moveTo(20 + r() * 6, y); g.quadraticCurveTo(32, y + 4 + r() * 6, 44 - r() * 6, y + 10); g.stroke(); }
  g.fillStyle = VERMILION; g.beginPath(); g.arc(32, 162, 9, 0, Math.PI * 2); g.fill();
});

// 面具：三个地点三种（按原作物怪的印象，角色线的模型到了就不用）
const MASKS = {
  // 化猫：白脸、两只尖耳、细长的红眼
  cat: (g, w, h) => {
    g.fillStyle = PAPER; g.beginPath(); g.moveTo(w * 0.14, h * 0.05); g.lineTo(w * 0.36, h * 0.3); g.lineTo(w * 0.64, h * 0.3); g.lineTo(w * 0.86, h * 0.05); g.lineTo(w * 0.92, h * 0.6); g.quadraticCurveTo(w * 0.5, h * 1.02, w * 0.08, h * 0.6); g.closePath(); g.fill();
    g.fillStyle = VERMILION; for (const x of [0.33, 0.67]) { g.beginPath(); g.ellipse(w * x, h * 0.52, w * 0.1, h * 0.035, x < 0.5 ? 0.25 : -0.25, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = "#2A2A4E"; for (const x of [0.33, 0.67]) { g.beginPath(); g.ellipse(w * x, h * 0.52, w * 0.018, h * 0.03, 0, 0, Math.PI * 2); g.fill(); }
  },
  // 座敷童子：齐刘海的黑发、白脸、两个红点眼、一点红嘴
  child: (g, w, h) => {
    g.fillStyle = PAPER; g.beginPath(); g.ellipse(w * 0.5, h * 0.55, w * 0.38, h * 0.42, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#14101F"; g.beginPath(); g.moveTo(w * 0.08, h * 0.62); g.quadraticCurveTo(w * 0.05, h * 0.05, w * 0.5, h * 0.06); g.quadraticCurveTo(w * 0.95, h * 0.05, w * 0.92, h * 0.62); g.lineTo(w * 0.86, h * 0.62); g.lineTo(w * 0.86, h * 0.4); g.lineTo(w * 0.14, h * 0.4); g.lineTo(w * 0.14, h * 0.62); g.closePath(); g.fill();
    g.fillStyle = VERMILION; for (const x of [0.36, 0.64]) { g.beginPath(); g.arc(w * x, h * 0.55, w * 0.045, 0, Math.PI * 2); g.fill(); }
    g.beginPath(); g.ellipse(w * 0.5, h * 0.78, w * 0.05, h * 0.02, 0, 0, Math.PI * 2); g.fill();
  },
  // 唐伞：伞面的竹骨、正中一只大眼、底下吐一截红舌头
  umbrella: (g, w, h) => {
    g.fillStyle = "#E9DCC4"; g.beginPath(); g.moveTo(w * 0.5, h * 0.02); g.lineTo(w * 0.96, h * 0.92); g.quadraticCurveTo(w * 0.5, h * 0.8, w * 0.04, h * 0.92); g.closePath(); g.fill();
    g.strokeStyle = "rgba(42,42,78,.45)"; g.lineWidth = 2; for (const x of [0.2, 0.35, 0.65, 0.8]) { g.beginPath(); g.moveTo(w * 0.5, h * 0.03); g.lineTo(w * x, h * 0.88); g.stroke(); }
    g.fillStyle = "#fff"; g.beginPath(); g.ellipse(w * 0.5, h * 0.5, w * 0.17, h * 0.1, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = VERMILION; g.beginPath(); g.arc(w * 0.5, h * 0.5, w * 0.08, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#14101F"; g.beginPath(); g.arc(w * 0.5, h * 0.5, w * 0.035, 0, Math.PI * 2); g.fill();
    g.fillStyle = VERMILION; g.beginPath(); g.moveTo(w * 0.44, h * 0.78); g.quadraticCurveTo(w * 0.5, h * 1.0, w * 0.58, h * 0.95); g.lineTo(w * 0.56, h * 0.78); g.closePath(); g.fill();
  },
};

// 面具的外形（和上面画的轮廓一致，画布坐标 0~1、y 向下）：网格按这个形状建，描边沿着面具边走，不会描出一个方框
const MASK_SHAPES = {
  cat: [[0.14, 0.05], [0.36, 0.3], [0.64, 0.3], [0.86, 0.05], [0.92, 0.6], [0.8, 0.84], [0.5, 0.97], [0.2, 0.84], [0.08, 0.6]],
  child: Array.from({ length: 28 }, (_, i) => { const a = (i / 28) * Math.PI * 2; return [0.5 + Math.cos(a) * 0.44, 0.52 + Math.sin(a) * 0.47]; }),
  umbrella: [[0.5, 0.02], [0.96, 0.92], [0.6, 0.86], [0.56, 0.98], [0.47, 0.92], [0.04, 0.92]],
};
function maskGeometry(kind, w, h) {
  const pts = (MASK_SHAPES[kind] || MASK_SHAPES.cat).map(([x, y]) => new THREE.Vector2(x, 1 - y));
  const g = new THREE.ShapeGeometry(new THREE.Shape(pts));   // ShapeGeometry 的 uv 就是形状坐标（0~1），正好对上画布
  g.translate(-0.5, -0.5, 0); g.scale(w, h, 1); return g;
}

// 墨色材质：上面稍亮、边上暗，glow 时边缘泛朱红（蓄力）
function inkMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { uInk: { value: INK.clone() }, uGlow: { value: 0 }, uGlowColor: { value: new THREE.Color(VERMILION) }, uAlpha: { value: 1 } },
    vertexShader: `varying vec3 vN; varying vec3 vV; varying float vY;
      void main() { vec4 wp = modelMatrix * vec4(position, 1.0); vN = normalize(mat3(modelMatrix) * normal); vV = normalize(cameraPosition - wp.xyz); vY = normal.y; gl_Position = projectionMatrix * viewMatrix * wp; }`,
    fragmentShader: `uniform vec3 uInk; uniform float uGlow; uniform vec3 uGlowColor; uniform float uAlpha; varying vec3 vN; varying vec3 vV; varying float vY;
      void main() { float rim = pow(1.0 - max(dot(normalize(vN), vV), 0.0), 2.0);
        vec3 c = uInk * (0.85 + 0.35 * smoothstep(-0.2, 1.0, vY)) * (1.0 - 0.35 * rim);
        c = mix(c, uGlowColor, uGlow * rim * 1.2);
        gl_FragColor = vec4(c, uAlpha);
        #include <colorspace_fragment>
      }`,
    transparent: true,
  });
}

/** 占位物怪（墨影）。kind：cat / child / umbrella；离地 hover 米 */
export function makeInkMonster(kind = "cat", { hover = 1.15 } = {}) {
  const group = new THREE.Group();
  const body = new THREE.Group(); body.position.y = hover; group.add(body);
  const geo = new THREE.IcosahedronGeometry(0.34, 3), base = geo.attributes.position.array.slice();
  const mat = inkMaterial();
  const blob = new THREE.Mesh(geo, mat); blob.frustumCulled = false; body.add(blob);
  const maskTex = canvasTex(128, 160, MASKS[kind] || MASKS.cat);
  const mask = new THREE.Mesh(maskGeometry(kind, 0.36, 0.44), new THREE.MeshBasicMaterial({ map: maskTex, transparent: true, alphaTest: 0.4, side: THREE.DoubleSide }));
  mask.position.set(0, 0.04, 0.4); mask.rotation.x = -0.08; body.add(mask);   // 墨团表面翻涌最多鼓出 12%（0.38 米），面具放在外面，不然被盖住只剩一条边
  // 墨尾：几节越来越小的墨球，跟着身体过去的位置走
  const tail = [], hist = [];
  for (let i = 0; i < 6; i++) { const t = new THREE.Mesh(new THREE.IcosahedronGeometry(0.16 * (1 - i * 0.13), 1), mat); t.frustumCulled = false; group.add(t); tail.push(t); }
  let time = Math.random() * 10;
  const _v = new THREE.Vector3();
  const M = {
    group, kind, glow: 0, stretch: 0, squash: 0, fade: 1, hover,
    /** 身体中心的世界坐标（札往这里飞） */
    center(out = new THREE.Vector3()) { return body.getWorldPosition(out); },
    radius: 0.34,
    update(dt) {
      time += dt;
      // 表面慢慢翻涌（CPU 改顶点，描边通道看到的是同一个形状）
      const p = geo.attributes.position.array;
      for (let i = 0; i < p.length; i += 3) {
        const x = base[i], y = base[i + 1], z = base[i + 2];
        const n = 1 + 0.07 * Math.sin(x * 7 + time * 3.1) * Math.sin(y * 6 + time * 2.3) + 0.05 * Math.sin(z * 9 - time * 4) + (y < 0 ? 0.18 * -y * (0.6 + 0.4 * Math.sin(x * 11 + time * 5)) : 0);   // 底下拖成墨裙
        p[i] = x * n; p[i + 1] = y * n * (y < 0 ? 1.35 : 1); p[i + 2] = z * n;
      }
      geo.attributes.position.needsUpdate = true; geo.computeVertexNormals();
      // 扑：顺着前后拉长；被钉 / 落地：压扁一下；悬浮上下飘
      const s = this.fade, st = 1 + this.stretch, sq = 1 - this.squash * 0.35;
      body.scale.set(s / Math.sqrt(st) * (1 + this.squash * 0.2), s * sq / Math.sqrt(st), s * st);
      body.position.y = this.hover + Math.sin(time * 1.7) * 0.06 * (1 - this.squash);
      mat.uniforms.uGlow.value = this.glow;
      mask.material.opacity = Math.min(1, s * 1.5);
      // 墨尾：每 1/30 秒记一次身体位置，第 i 节落后 i+1 格
      group.updateMatrixWorld(true); const c = body.getWorldPosition(_v);
      if (!hist.length || (M._acc = (M._acc || 0) + dt) > 1 / 30) { M._acc = 0; hist.unshift(c.clone()); if (hist.length > 20) hist.pop(); }
      tail.forEach((t, i) => {
        const h = hist[Math.min(hist.length - 1, (i + 1) * 2)] || c;
        t.position.copy(group.worldToLocal(_v.copy(h))); t.position.y -= 0.12 + i * 0.05;
        t.scale.setScalar(s * (1 + Math.sin(time * 3 + i) * 0.1));
      });
    },
    play() {},
    resetTrail() { hist.length = 0; },
    dispose() { geo.dispose(); mat.dispose(); maskTex.dispose(); tail.forEach((t) => t.geometry.dispose()); mask.geometry.dispose(); mask.material.dispose(); },
  };
  M.update(0);
  return M;
}

// 物怪模型（角色线，动作名都一样：idle_k 飘着 / 站着、appear_k 浮上来、charge_k 蓄力、lunge_k 扑、hit_k 被钉、vanish_k 消散，都朝 +Z）。
// h 身高（米，代码缩放）；yaw 模型不朝 +Z 时转多少；mask 模型没下完时墨影用哪张面具；speed 动作倍速；count > 1 是一群（小化猫：一次三只，各钉一张）。
// 11-04 角色线交了四只新的、三只变体（docs/18 第九节）
export const MONSTERS = {
  bakeneko: { file: "processed/bakeneko_posed.glb", h: 1.15, mask: "cat" },
  bakeneko_shiro: { file: "processed/bakeneko_shiro_posed.glb", h: 1.15, mask: "cat" },
  bakeneko_ko: { file: "processed/bakeneko_posed.glb", h: 1.15 * 0.55, mask: "cat", speed: 1.4, count: 3 },
  nue: { file: "processed/nue_posed.glb", h: 1.35, mask: "cat" },
  umibozu: { file: "processed/umibozu_posed.glb", h: 2.2, mask: "umbrella" },
  zashiki: { file: "processed/zashiki_posed.glb", h: 1.1, mask: "child" },   // 模型本身量出来 1.0 米，按角色线建议放到 1.1
  zashiki_ao: { file: "processed/zashiki_ao_posed.glb", h: 1.1, mask: "child" },
  noppera: { file: "processed/noppera_posed.glb", h: 1.85, mask: "child" },
  karakasa: { file: "processed/karakasa_posed.glb", h: 1.3, mask: "umbrella" },
  karakasa_kuro: { file: "processed/karakasa_kuro_posed.glb", h: 1.3, mask: "umbrella" },
  hinezumi: { file: "processed/hinezumi_posed.glb", h: 1.0, mask: "cat" },
  kitten_guide: { file: "processed/bakeneko_posed.glb", h: 1.15 * 0.55, mask: "cat" },   // 引导（guide.js）：90 秒没找到东西，一只小化猫跑过去领路（不是物怪，不进图鉴）
};
const ONCE = new Set(["appear_k", "hit_k", "vanish_k", "charge_k", "lunge_k", "look_back_k"]);

/** 加载按原作做的物怪（id 见 MONSTERS）。接口和墨影一样，扑、蓄力、浮上来这些交给模型自己的动作，
 *  代码只管：squash（被钉压一下）、fade（消散、退走时缩没）、hover 低于 0 时整只往地下沉（退走、海坊主消散） */
export async function loadMonster(loader, assetUrl, id) {
  const cfg = MONSTERS[id] || MONSTERS.bakeneko;
  const gltf = await loader.loadAsync(assetUrl(cfg.file));
  if (!(cfg.count > 1)) return buildMonster(gltf.scene, gltf.animations, id, cfg);
  const scenes = Array.from({ length: cfg.count }, (_, i) => (i ? cloneSkinned(gltf.scene) : gltf.scene));   // 先从原样的场景克隆，再各自换材质
  const cats = scenes.map((sc) => buildMonster(sc, gltf.animations, id, cfg));
  return makeSwarm(cats, id);
}

function buildMonster(m, animations, id, cfg) {
  const group = new THREE.Group(), inner = new THREE.Group();
  m.traverse((o) => {
    if (!o.isMesh) return;
    o.frustumCulled = false;
    const map = o.material.map || null; if (map) map.colorSpace = THREE.SRGBColorSpace;
    o.material = makeToonMaterial({ map, color: map ? "#ffffff" : o.material.color.clone(), shadeColor: "#2A2440", shadeMix: 0.45, threshold: 0.45 });
  });
  if (cfg.yaw) m.rotation.y += cfg.yaw;
  inner.add(m); group.add(inner);
  const box0 = new THREE.Box3().setFromObject(m), k = cfg.h / Math.max(0.01, box0.max.y - box0.min.y);
  if (Math.abs(k - 1) > 0.03) m.scale.multiplyScalar(k);
  const box = new THREE.Box3().setFromObject(m), height = box.max.y - box.min.y;
  const mixer = new THREE.AnimationMixer(m), clips = Object.fromEntries(animations.map((c) => [c.name.replace(/\|.*$/, "").toLowerCase(), c]));
  const bones = {}; m.traverse((o) => { if (o.isBone) bones[o.name] = o; });
  mixer.timeScale = cfg.speed || 1;
  let cur = null;
  const M = {
    group, id, kind: cfg.mask, glow: 0, stretch: 0, squash: 0, fade: 1, hover: 1.15, height, radius: Math.max(0.25, (box.max.x - box.min.x) * 0.4), real: true,
    center(out = new THREE.Vector3()) { return inner.localToWorld(out.set(0, height * 0.55, 0)); },
    /** state：idle / appear / charge / lunge / hit / vanish */
    play(state, fade = 0.12, at = 0) {   // at：从第几秒开始（一群里各只错开）
      const c = clips[`${state}_k`]; if (!c) return;
      const a = mixer.clipAction(c); if (a === cur && !ONCE.has(c.name)) return;
      if (cur && cur !== a) cur.fadeOut(fade);
      a.reset(); if (ONCE.has(`${state}_k`)) { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; } else a.setLoop(THREE.LoopRepeat, Infinity);
      a.fadeIn(fade).play(); if (at) a.time = at % c.duration; cur = a;
    },
    /** 叠在动作上的姿势（一群里每只的性子）：{ neck, head: [x, y, z] 弧度, tail: 每节加的 [x, y, z], sway: [幅度, 频率] 尾巴自己摆 } */
    pose: null, poseT: Math.random() * 10,
    idleName: "idle", idleFade: 0.2,   // 一次性动作播完回哪段待机（小化猫每只不一样）
    bones,
    get clip() { return cur?.getClip().name; },
    has(state) { return !!clips[`${state}_k`]; },
    update(dt) {
      if (this.posed) for (const [b, q] of this.posed) b.quaternion.copy(q);   // 先还原上一帧加之前的样子：动作里没打关键帧的骨头不会被 mixer 覆盖，不还原就会一帧一帧越加越歪
      mixer.update(dt);
      if (this.pose) applyPose(this, dt);
      const s = Math.max(0.001, this.fade), sq = 1 - this.squash * 0.18;
      inner.scale.set(s * (1 + this.squash * 0.1), s * sq, s * (1 + this.squash * 0.1));
      inner.position.y = Math.min(0, this.hover);   // 退走：沉到地下
    },
    resetTrail() {},
    dispose() { mixer.stopAllAction(); m.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); o.material.dispose(); } }); },
  };
  // 一次性的动作播完回飘着（扑完落地、被钉完）
  mixer.addEventListener("finished", (e) => { if (e.action === cur && e.action.getClip().name !== "vanish_k") M.play(M.idleName, M.idleFade); });
  M.play("idle");
  return M;
}

const _q = new THREE.Quaternion(), _e = new THREE.Euler();
function applyPose(M, dt) {
  const P = M.pose, B = M.bones; M.poseT += dt;
  M.posed ||= new Map();
  const add = (b, r) => { if (!b || !r) return; if (!M.posed.has(b)) M.posed.set(b, b.quaternion.clone()); b.quaternion.multiply(_q.setFromEuler(_e.set(r[0], r[1], r[2]))); };
  for (const [b, q] of M.posed) q.copy(b.quaternion);   // 记下 mixer 给的（加之前的）
  add(B.neck, P.neck); add(B.head, P.head);
  const sw = P.sway ? Math.sin(M.poseT * P.sway[1] * Math.PI * 2) * P.sway[0] : 0;
  for (let k = 0; k < 5; k++) { const b = B[`tail${k}`]; if (!b) break; add(b, P.tail); if (sw) add(b, [0, sw * (0.4 + k * 0.15), 0]); }
}

/** 一群（小化猫）：三只排成三角一起绕、一起扑；札每次打"当前那只"，钉中的那只定住发抖，换下一只。
 *  对外和一只一样（encounter.js 不用管是一群），多一个 onPin()（钉中以后调）和 reset()（重新出场）。
 *  11-04 用户说"三位的动作太一致了，没有个性"：每只大小、朝向、动作快慢和起点都错开，一起扑时后两只晚一点跟上；
 *  待机各播各的（角色线做的，第三版都站着）：老大歪头看人、尾巴竖着摇；老二回头舔肩背、转回来看人一眼；老三最小、往后缩着发抖、偶尔回头 */
const KITTENS = [   // idle：角色线 11-04 做的各自待机（bakeneko_posed.glb，第四版三只都站着，11-04 老二、老三往两边拉开免得叠在一起；sit = 坐姿，进出蓄力 / 被钉淡 0.35 秒，现在没有坐着的了）
  { pos: [0, 0.42], yaw: 0.22, scale: 1.05, speed: 1.0, at: 0, delay: 0, idle: "idle_curious" },
  { pos: [-0.8, -0.08], yaw: -0.12, scale: 1.0, speed: 1.15, at: 1.2, delay: 0.07, idle: "idle_groom" },   // 站着回头舔肩背
  { pos: [0.74, -0.3], yaw: -0.5, scale: 0.86, speed: 0.9, at: 0.6, delay: 0.14, idle: "idle_sit" },   // 名字没改，第三版是站着往后缩、发抖
];
function makeSwarm(cats, id) {
  const group = new THREE.Group();
  cats.forEach((c, i) => {
    const K = KITTENS[i % KITTENS.length];
    c.group.position.set(K.pos[0], 0, K.pos[1]); c.group.rotation.y = K.yaw; c.group.scale.setScalar(K.scale);
    c.K = K; c.wait = null; group.add(c.group);
    // 有了自己的待机就用它（脑袋、耳朵、尾巴都打了关键帧，不再叠姿势）；文件里还没有的话退回原来的 idle_k
    if (c.has(K.idle)) { c.idleName = K.idle; c.idleFade = K.sit ? 0.35 : 0.2; }
  });
  const pinned = new Set(); let target = 0;
  const S = {
    group, id, kind: "cat", glow: 0, stretch: 0, squash: 0, fade: 1, hover: 1.15, height: cats[0].height, radius: 0.85, real: true, swarm: true, cats,
    get target() { return target; },
    center(out = new THREE.Vector3()) { return cats[target].center(out); },
    // 一起动的时候不是同一帧：后两只晚 0.07 / 0.14 秒跟上；循环的待机各从不同的地方开始
    play(state, fade) {
      cats.forEach((c, i) => {
        if (pinned.has(i) && state !== "vanish" && state !== "appear") return;
        const f = c.K.sit ? Math.max(fade ?? 0.12, 0.35) : fade;
        if (state === "idle") c.play(c.idleName, f, c.K.at); else if (c.K.delay) c.wait = { state, fade: f, t: c.K.delay }; else c.play(state, f);
      });
    },
    onPin() {
      pinned.add(target); cats[target].wait = null; cats[target].play("hit", cats[target].K.sit ? 0.35 : 0.12);
      for (let k = 1; k <= cats.length; k++) { const n = (target + k) % cats.length; if (!pinned.has(n)) { target = n; break; } }
    },
    reset() { pinned.clear(); target = 0; cats.forEach((c) => { c.wait = null; c.play(c.idleName, 0.12, c.K.at); }); },
    get clip() { return cats[target].clip; },
    update(dt) {
      cats.forEach((c, i) => {
        const p = pinned.has(i);
        if (c.wait && (c.wait.t -= dt) <= 0) { c.play(c.wait.state, c.wait.fade); c.wait = null; }
        c.fade = this.fade; c.hover = this.hover; c.glow = this.glow;
        c.squash = p ? 0.25 + Math.sin(performance.now() * 0.03 + i) * 0.06 : this.squash;   // 钉住的那只缩着打颤
        c.update((p ? 0.15 : c.K.speed) * dt);
      });
    },
    resetTrail() {},
    dispose() { cats.forEach((c) => c.dispose()); },
  };
  return S;
}

/** 特效管理：札、札阵、墨点、字。update(dt) 每帧调；clear() 遭遇结束时清掉 */
export class MononokeFx {
  constructor(scene, camera) {
    this.scene = scene; this.camera = camera;
    this.tex = OFUDA_TEX();
    this.ofudaGeo = new THREE.PlaneGeometry(0.075, 0.22);
    this.inkMat = new THREE.MeshBasicMaterial({ color: INK, transparent: true });
    this.dropGeo = new THREE.IcosahedronGeometry(0.035, 1);
    this.flying = []; this.pinned = []; this.drops = []; this.papers = []; this.lights = []; this.ring = null;
    this.goldMat = new THREE.MeshBasicMaterial({ color: "#E8C15A", transparent: true });
    this.grudge = null; this.cuts = []; this.drip = null;
    this.root = new THREE.Group(); scene.add(this.root);
    this.mk = document.getElementById("mk");
  }
  ofudaMesh() {
    const m = new THREE.Mesh(this.ofudaGeo, new THREE.MeshBasicMaterial({ map: this.tex, side: THREE.DoubleSide, transparent: true }));
    m.frustumCulled = false; return m;
  }
  /** 投一张札：from 世界坐标，target() 每帧给目标点（物怪会动，札稍微追一点），willHit 决定钉中还是擦过去；到了调 onArrive(hit) */
  throw(from, target, willHit, onArrive, { speed = 13, delay = 0 } = {}) {
    const m = this.ofudaMesh(); m.position.copy(from); m.visible = delay <= 0; this.root.add(m);
    const ghosts = [0.5, 0.3, 0.15].map((a) => { const g = this.ofudaMesh(); g.material.opacity = a; g.visible = false; this.root.add(g); return g; });
    const t0 = target(new THREE.Vector3()), side = new THREE.Vector3().subVectors(t0, from).cross(new THREE.Vector3(0, 1, 0)).normalize();
    // 擦过去的：瞄准点往旁边偏 0.6~0.9 米，飞过去以后再飘一会儿掉地上
    const miss = willHit ? null : side.multiplyScalar((Math.random() < 0.5 ? -1 : 1) * rnd(0.6, 0.9)).add(new THREE.Vector3(0, rnd(-0.1, 0.3), 0));
    this.flying.push({ m, ghosts, hist: [], target, miss, willHit, onArrive, speed, delay, t: 0, spin: rnd(10, 16), vel: null, fall: 0 });
  }
  /** 札钉在物怪身上：挂到物怪的 group 下面，跟着它动；啪地放大一下 */
  pin(monster, world) {
    const m = this.ofudaMesh(); monster.group.add(m);
    const local = monster.group.worldToLocal(world.clone());
    m.position.copy(local); m.lookAt(monster.group.localToWorld(local.clone().multiplyScalar(2).setY(local.y))); m.rotateZ(rnd(-0.6, 0.6));
    this.pinned.push({ m, t: 0 }); return m;
  }
  /** 一把墨点：n 个，从 pos 往外溅，有重力，落地前缩没 */
  splat(pos, n = 14, { up = 1.5, spread = 2.2, rise = false, mat = null } = {}) {
    for (let i = 0; i < n; i++) {
      const d = new THREE.Mesh(this.dropGeo, mat || this.inkMat); d.position.copy(pos); d.frustumCulled = false;
      const s = rnd(0.6, 1.8); d.scale.setScalar(s); this.root.add(d);
      const v = new THREE.Vector3(rnd(-1, 1), rnd(0.2, 1) * up, rnd(-1, 1)).normalize().multiplyScalar(rnd(0.5, 1) * spread);
      this.drops.push({ d, v, life: rnd(0.5, 0.9) * (rise ? 2.2 : 1), t: 0, s, rise });
    }
  }
  /** 一把札纸：n 张从 pos 往外散开、翻着飘落（瞬移消失 / 现身）；inward 时从外面收拢到 pos */
  paper(pos, n = 10, { inward = false } = {}) {
    for (let i = 0; i < n; i++) {
      const m = this.ofudaMesh(); m.scale.setScalar(1.5); this.root.add(m);
      const a = rnd(0, Math.PI * 2), r = rnd(0.6, 1.2), y = rnd(-0.5, 0.6);
      const off = new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r);
      m.position.copy(pos); if (inward) m.position.add(off);
      m.rotation.set(rnd(0, 6), rnd(0, 6), rnd(0, 6));
      this.papers.push({ m, from: m.position.clone(), to: inward ? pos.clone().add(off.multiplyScalar(0.05)) : pos.clone().add(off), t: 0, life: inward ? 0.22 : rnd(0.7, 1), inward, spin: new THREE.Vector3(rnd(-9, 9), rnd(-9, 9), rnd(-9, 9)) });
    }
  }
  /** 魂光：退魔以后从 pos 升起来、慢慢飘走淡掉。list 每项 { size, delay, follow }：follow 是另一团的下标，
   *  先往它那边靠再一起往上（小化猫跟着母猫走）。返回全部飘完要多少秒 */
  souls(pos, list) {
    this.soulTex ||= SOUL_TEX();
    const made = list.map((o, i) => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.soulTex, transparent: true, depthWrite: false, opacity: 0 }));   // 不用叠加：叠在浅色墙、天上会看不见
      sp.position.copy(pos).add(new THREE.Vector3(rnd(-0.25, 0.25), rnd(-0.1, 0.15), rnd(-0.25, 0.25)));
      if (o.offset) sp.position.add(o.offset);
      sp.scale.setScalar(0.01); sp.frustumCulled = false; this.root.add(sp);
      return { sp, size: o.size || 0.35, delay: o.delay || 0, follow: o.follow, t: 0, life: o.life || 3.2, seed: rnd(0, 6), vel: new THREE.Vector3(0, o.rise ?? 0.45, 0) };
    });
    made.forEach((m) => { if (m.follow != null) m.lead = made[m.follow]; });
    this.lights.push(...made);
    return Math.max(...made.map((m) => m.delay + m.life));
  }
  // ---- 11-05 退魔收场（docs/19 第十节）：剑斩的是缠在它身上的怨念，不是它本身 ----
  /** 怨念剥离：一团有面具的墨影从物怪身上被抽出来，dur 秒里浮到它头上方、越长越大；它本身由 encounter.js 褪色 */
  peel(monster, dur = 1.4) {
    this.clearGrudge();
    const h = monster.height || 1, c = monster.center(new THREE.Vector3());
    const g = makeInkMonster(monster.kind || "cat", { hover: 0 });
    g.group.position.copy(c); g.fade = 0.05; g.glow = 0.5; this.root.add(g.group);
    this.grudge = { g, from: c.clone(), to: c.clone().add(new THREE.Vector3(0, h * 0.45 + 0.5, 0)), t: 0, dur: Math.max(0.35, dur), size: Math.min(1.8, Math.max(0.85, h * 0.8)), cut: -1, monster, acc: 0 };
    this.splat(c, 16, { up: 1, spread: 0.5, rise: true });
  }
  /** 横斩劈中那团墨：一道金光横着闪过，墨被压扁、烧成金色火星和墨点散掉 */
  cutGrudge() {
    const G = this.grudge; if (!G) return;
    G.cut = 0;
    const at = G.g.center(new THREE.Vector3());
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 0.035), new THREE.MeshBasicMaterial({ color: "#FFF1C4", transparent: true, depthTest: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
    m.position.copy(at); m.quaternion.copy(this.camera.quaternion); m.rotateZ(rnd(-0.35, -0.15)); m.scale.set(0.01, 1, 1); m.renderOrder = 10; m.frustumCulled = false;
    this.root.add(m); this.cuts.push({ m, t: 0, len: G.size * 1.8 });
    this.splat(at, 26, { up: 1, spread: 1.3, rise: true, mat: this.goldMat });
    this.splat(at, 18, { up: 0.6, spread: 1.6 });
  }
  /** 钉在它身上的札散成纸片落下（斩完 / 送走：它已经不用再被钉着了） */
  unpin() { const w = new THREE.Vector3(); for (const p of this.pinned) { p.m.getWorldPosition(w); p.m.parent?.remove(p.m); this.paper(w, 3); } this.pinned = []; }
  clearGrudge() { if (this.grudge) { this.root.remove(this.grudge.g.group); this.grudge.g.dispose(); this.grudge = null; } }
  /** 送：墨像水一样从它身上往下滴干净，dur 秒 */
  dripOff(monster, dur = 1.8) { this.drip = { monster, t: 0, dur, acc: 0 }; }
  /** 送：一张札从 from（药郎指尖）飘落到 floorY，0.35 秒、轻晃两下，落地后平躺、过一会儿淡掉 */
  dropFuda(from, floorY) {
    const m = this.ofudaMesh(); m.position.copy(from); this.root.add(m);
    this.falling = { m, from: from.clone(), floorY, t: 0 };
  }
  /** 送：札阵落到地上摊平，红线换成金色，慢慢转着 */
  ringToFloor(floorY) { if (this.ring) { this.ring.floor = 0; this.ring.floorY = floorY; this.ring.line.material.color.set("#E8C15A"); } }
  /** 札阵：count 张札绕着 center() 转，红线连起来；tighten 0→1 收紧 */
  makeRing(monster, count = 8) {
    this.clearRing();
    const g = new THREE.Group(), cards = [];
    for (let i = 0; i < count; i++) { const m = this.ofudaMesh(); g.add(m); cards.push(m); }
    const lineGeo = new THREE.BufferGeometry().setFromPoints(Array.from({ length: count + 1 }, () => new THREE.Vector3()));
    const line = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: VERMILION, transparent: true, opacity: 0.85 }));
    line.frustumCulled = false; g.add(line);
    this.root.add(g);
    this.ring = { g, cards, line, monster, t: 0, tighten: 0, count };
  }
  clearRing() { if (this.ring) { this.root.remove(this.ring.g); this.ring.line.geometry.dispose(); this.ring = null; } }
  /** 字浮起来：char 在物怪头上，line 在屏幕下方（字幕那样），ms 毫秒后淡掉 */
  kanji(char, line, world, ms = 2600) {
    if (!this.mk) return;
    if (line) this.mk.querySelectorAll(".line").forEach((o) => o.remove());   // 下面那句话同时只留一句：钉得快时上一句还没淡掉
    const k = document.createElement("div"); k.className = "kanji"; k.textContent = char; this.mk.appendChild(k);
    const l = document.createElement("div"); l.className = "line"; l.textContent = line || ""; if (line) this.mk.appendChild(l);
    const item = { k, l, world: world.clone(), t: 0, ms };
    (this.words ||= []).push(item);
    requestAnimationFrame(() => { k.classList.add("show"); l.classList.add("show"); });
    setTimeout(() => { k.classList.remove("show"); l.classList.remove("show"); setTimeout(() => { k.remove(); l.remove(); this.words = this.words.filter((w) => w !== item); }, 500); }, ms);
  }
  update(dt) {
    const tmp = new THREE.Vector3();
    for (const f of this.flying.slice()) {
      if (f.delay > 0) { f.delay -= dt; if (f.delay <= 0) f.m.visible = true; else continue; }
      f.t += dt;
      const tgt = f.target(new THREE.Vector3()); if (f.miss) tgt.add(f.miss);
      if (f.vel && f.passed) {
        // 擦过去以后：往前飘，慢慢往下掉、翻着转，0.7 秒后淡掉
        f.vel.y -= 4 * dt; f.vel.multiplyScalar(1 - 1.5 * dt); f.m.position.addScaledVector(f.vel, dt); f.m.rotation.x += 8 * dt;
        f.fall += dt; f.m.material.opacity = Math.max(0, 1 - f.fall / 0.7);
        if (f.fall > 0.7) { this.kill(f); }
      } else {
        const to = tgt.clone().sub(f.m.position), d = to.length(), step = f.speed * dt;
        f.vel = to.clone().normalize().multiplyScalar(f.speed);
        if (d <= step + 0.02) {
          f.m.position.copy(tgt);
          if (f.willHit) { this.kill(f); f.onArrive?.(true, tgt.clone()); continue; }
          f.passed = true; f.onArrive?.(false, tgt.clone());
        } else f.m.position.addScaledVector(to, step / d);
        // 札面朝着飞的方向转（像飞镖那样转着走）
        f.m.lookAt(tmp.copy(f.m.position).add(f.vel)); f.m.rotateX(Math.PI / 2); f.m.rotateY(f.t * f.spin);
      }
      f.hist.unshift(f.m.position.clone()); if (f.hist.length > 7) f.hist.pop();
      f.ghosts.forEach((g, i) => { const h = f.hist[(i + 1) * 2]; g.visible = !!h && f.m.visible; if (h) { g.position.copy(h); g.quaternion.copy(f.m.quaternion); } });
    }
    for (const p of this.pinned) { p.t += dt; const s = p.t < 0.25 ? 1 + 0.6 * Math.sin((p.t / 0.25) * Math.PI) * (1 - p.t / 0.25) : 1; p.m.scale.setScalar(s); }
    for (const d of this.drops.slice()) {
      d.t += dt; const k = d.t / d.life;
      if (d.rise) { d.v.y += 1.2 * dt; d.v.x *= 1 - dt; d.v.z *= 1 - dt; } else d.v.y -= 6 * dt;
      d.d.position.addScaledVector(d.v, dt); d.d.scale.setScalar(d.s * Math.max(0, 1 - k * k));
      if (k >= 1) { this.root.remove(d.d); this.drops.splice(this.drops.indexOf(d), 1); }
    }
    for (const p of this.papers.slice()) {
      // 散的：0.25 秒冲到外面，再慢慢往下飘、淡掉；收的：0.22 秒收到中间，越收越小
      p.t += dt; const k = Math.min(1, p.t / p.life);
      if (p.inward) { p.m.position.lerpVectors(p.from, p.to, k * k); p.m.scale.setScalar(1.5 * (1 - k * 0.8)); }
      else { const e = 1 - Math.pow(1 - Math.min(1, p.t / 0.25), 3); p.m.position.lerpVectors(p.from, p.to, e); p.m.position.y -= Math.max(0, p.t - 0.25) * 0.5; p.m.material.opacity = 1 - k; }
      p.m.rotation.x += p.spin.x * dt; p.m.rotation.y += p.spin.y * dt; p.m.rotation.z += p.spin.z * dt;
      if (k >= 1) { this.root.remove(p.m); this.papers.splice(this.papers.indexOf(p), 1); }
    }
    for (const m of this.lights.slice()) {
      m.t += dt; const t = m.t - m.delay; if (t < 0) continue;
      const k = t / m.life, a = k < 0.15 ? k / 0.15 : k > 0.7 ? Math.max(0, 1 - (k - 0.7) / 0.3) : 1;
      m.sp.material.opacity = a * 0.95; m.sp.scale.setScalar(m.size * (0.6 + 0.4 * Math.min(1, t / 0.4)) * (1 + 0.06 * Math.sin(t * 5 + m.seed)));
      if (m.lead) {   // 跟着领头那团：水平方向往它身后 0.25 米靠拢，高度比它低一点
        const tx = m.lead.sp.position.x + Math.sin(m.seed) * 0.25, tz = m.lead.sp.position.z + Math.cos(m.seed) * 0.25, ty = m.lead.sp.position.y - 0.15 - 0.1 * Math.sin(m.seed);
        const kk = 1 - Math.exp(-2.2 * dt); m.sp.position.x += (tx - m.sp.position.x) * kk; m.sp.position.z += (tz - m.sp.position.z) * kk; m.sp.position.y += (ty - m.sp.position.y) * kk;
      } else {
        m.sp.position.addScaledVector(m.vel, dt); m.sp.position.x += Math.sin(t * 1.3 + m.seed) * 0.12 * dt; m.sp.position.z += Math.cos(t * 1.1 + m.seed) * 0.12 * dt;
        m.vel.y += 0.15 * dt;   // 越飘越快一点
      }
      if (k >= 1) { this.root.remove(m.sp); m.sp.material.dispose(); this.lights.splice(this.lights.indexOf(m), 1); }
    }
    const G = this.grudge;
    if (G) {
      G.g.group.rotation.y = Math.atan2(this.camera.position.x - G.g.group.position.x, this.camera.position.z - G.g.group.position.z);   // 面具朝镜头
      if (G.cut < 0) {
        G.t += dt; const k = Math.min(1, G.t / G.dur), e = 1 - Math.pow(1 - k, 3);
        G.g.group.position.lerpVectors(G.from, G.to, e); G.g.fade = 0.05 + (G.size - 0.05) * e; G.g.glow = 0.35 + 0.25 * Math.sin(G.t * 9);
        // 抽出来的路上：墨点从它身上往上被吸过去
        if (k < 1 && (G.acc += dt) > 0.05) { G.acc = 0; this.splat(G.monster.center(tmp), 2, { up: 1, spread: 0.35, rise: true }); }
      } else {
        G.cut += dt; const k = Math.min(1, G.cut / 0.55);
        G.g.squash = Math.min(1, G.cut / 0.08); G.g.glow = 1; G.g.fade = G.size * (1 - k * k);
        if (k >= 1) this.clearGrudge();
      }
      this.grudge?.g.update(dt);
    }
    for (const c of this.cuts.slice()) {
      c.t += dt; const k = c.t / 0.45;
      c.m.scale.x = c.len * Math.min(1, c.t / 0.07); c.m.material.opacity = k < 0.3 ? 1 : Math.max(0, 1 - (k - 0.3) / 0.7);
      if (k >= 1) { this.root.remove(c.m); c.m.geometry.dispose(); c.m.material.dispose(); this.cuts.splice(this.cuts.indexOf(c), 1); }
    }
    if (this.falling) {
      const F = this.falling; F.t += dt; const k = Math.min(1, F.t / 0.35);
      F.m.position.set(F.from.x + Math.sin(k * Math.PI * 2) * 0.06, F.from.y + (F.floorY + 0.01 - F.from.y) * k * k, F.from.z);
      F.m.rotation.set(-Math.PI / 2 * k, 0, Math.sin(k * Math.PI * 2) * 0.5 * (1 - k));
      if (F.t > 3) F.m.material.opacity = Math.max(0, 1 - (F.t - 3) / 0.6);
      if (F.t > 3.6) { this.root.remove(F.m); this.falling = null; }
    }
    if (this.drip) {
      const D = this.drip; D.t += dt;
      if ((D.acc += dt) > 0.045) {
        D.acc = 0; const c = D.monster.center(tmp), r = (D.monster.radius || 0.3) * 0.8;
        this.splat(c.add(new THREE.Vector3(rnd(-r, r), rnd(-0.2, 0.25), rnd(-r, r))), 1, { up: 0.05, spread: 0.12 });
      }
      if (D.t > D.dur) this.drip = null;
    }
    const R = this.ring;
    if (R) {
      R.t += dt; const c = R.monster.center(tmp);
      if (R.floor != null) R.floor = Math.min(1, R.floor + dt / 0.9);
      const fk = R.floor == null ? 0 : 1 - Math.pow(1 - R.floor, 3);   // 送：0.9 秒落到地上、转慢、圈放大
      const rad = (0.95 - 0.35 * R.tighten) * (1 - fk) + 0.85 * fk, pts = [];
      R.cards.forEach((m, i) => {
        const a = R.t * (0.9 + R.tighten * 2) * (1 - fk * 0.85) + (i / R.count) * Math.PI * 2, y0 = c.y + Math.sin(R.t * 2 + i) * 0.06;
        const y = y0 + ((R.floorY ?? c.y) + 0.02 - y0) * fk;
        m.position.set(c.x + Math.cos(a) * rad, y, c.z + Math.sin(a) * rad);
        if (fk > 0.6) { m.rotation.set(-Math.PI / 2, 0, -a); } else m.lookAt(c.x, y, c.z);
        pts.push(m.position.clone());
      });
      pts.push(pts[0]); R.line.geometry.setFromPoints(pts);
    }
    if (this.words?.length && this.mk) {
      for (const w of this.words) {
        w.t += dt; tmp.copy(w.world); tmp.y += 0.5 + w.t * 0.25; tmp.project(this.camera);
        w.k.style.transform = `translate(${(tmp.x * 0.5 + 0.5) * innerWidth}px, ${(-tmp.y * 0.5 + 0.5) * innerHeight}px) translate(-50%, -50%)`;
      }
    }
  }
  kill(f) { this.root.remove(f.m); f.ghosts.forEach((g) => this.root.remove(g)); this.flying.splice(this.flying.indexOf(f), 1); }
  clear() {
    for (const f of this.flying.slice()) this.kill(f);
    for (const p of this.pinned) p.m.parent?.remove(p.m); this.pinned = [];
    for (const d of this.drops) this.root.remove(d.d); this.drops = [];
    for (const p of this.papers) this.root.remove(p.m); this.papers = [];
    for (const m of this.lights) { this.root.remove(m.sp); m.sp.material.dispose(); } this.lights = [];
    this.clearRing(); this.clearGrudge(); this.drip = null;
    if (this.falling) { this.root.remove(this.falling.m); this.falling = null; }
    for (const c of this.cuts) this.root.remove(c.m); this.cuts = [];
  }
}
