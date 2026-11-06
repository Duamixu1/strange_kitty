import * as THREE from "three";

// 雪：区块写了 "weather": "snow" 时开（笛小路家门前、雪庭，docs/22）。做法同 rain.js：镜头周围一个盒子里的点往下飘，
// 落到底回到顶上，按镜头位置取模，镜头走到哪雪跟到哪。每片左右轻轻晃，大小不一，近大远小。
// 不进描边通道（tour.js 放进 post.exclude），纸白、边缘柔，像原作里一团团的雪片。
const N = 900, BOX = 16, TOP = 8, SPEED = 0.55;

function flakeTex() {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, "rgba(255,252,244,1)"); gr.addColorStop(0.45, "rgba(250,246,236,.85)"); gr.addColorStop(1, "rgba(250,246,236,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export function createSnow() {
  const pos = new Float32Array(N * 3), seed = new Float32Array(N * 4);   // x、y、z（0..1）和晃动的相位
  for (let i = 0; i < N * 4; i++) seed[i] = Math.random();
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({ map: flakeTex(), size: 0.11, sizeAttenuation: true, transparent: true, opacity: 0.9, depthWrite: false });
  const pts = new THREE.Points(geo, mat);
  pts.frustumCulled = false; pts.visible = false; pts.renderOrder = 10;
  let t = 0;
  return {
    object: pts,
    get on() { return pts.visible; },
    set(on) { pts.visible = !!on; },
    update(dt, camera) {
      if (!pts.visible) return;
      t += dt;
      const c = camera.position, wrap = (v, o, s) => o + ((((v - o) % s) + s) % s);
      for (let i = 0; i < N; i++) {
        const ph = seed[i * 4 + 3] * 6.28, sp = SPEED * (0.6 + seed[i * 4 + 3] * 0.8);   // 每片落得快慢不一
        const x = wrap(seed[i * 4] * BOX + Math.sin(t * 0.9 + ph) * 0.25, c.x - BOX / 2, BOX);
        const z = wrap(seed[i * 4 + 2] * BOX + Math.cos(t * 0.7 + ph) * 0.2, c.z - BOX / 2, BOX);
        const y = TOP - ((seed[i * 4 + 1] * TOP + t * sp) % TOP) - 0.5;
        pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
      }
      geo.attributes.position.needsUpdate = true;
    },
  };
}
