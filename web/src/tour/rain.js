import * as THREE from "three";

// 雨：区块写了 "weather": "rain" 时开。一堆斜线段在镜头周围的盒子里往下落，落到地面就回到顶上（按镜头位置取模，镜头走到哪雨跟到哪）。
// 不进描边通道（tour.js 把它放进 post.exclude），颜色是纸白半透明，像原作雨夜里一根根白线。
const N = 1600, BOX = 14, TOP = 9, SPEED = 9, LEN = 0.55, SLANT = 0.12;

export function createRain() {
  const pos = new Float32Array(N * 6);
  const seed = new Float32Array(N * 3);   // 每根雨丝在盒子里的初始 x、y、z（0..1）
  for (let i = 0; i < N * 3; i++) seed[i] = Math.random();
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.LineBasicMaterial({ color: "#F1E9DA", transparent: true, opacity: 0.38, depthWrite: false });
  const lines = new THREE.LineSegments(geo, mat);
  lines.frustumCulled = false; lines.visible = false; lines.renderOrder = 10;
  let t = 0;
  return {
    object: lines,
    set(on) { lines.visible = !!on; },
    update(dt, camera) {
      if (!lines.visible) return;
      t += dt;
      const c = camera.position, wrap = (v, o, s) => o + ((((v - o) % s) + s) % s);
      for (let i = 0; i < N; i++) {
        // 盒子以镜头为中心；y 随时间往下，取模回到顶上
        const x = wrap(seed[i * 3] * BOX, c.x - BOX / 2, BOX);
        const z = wrap(seed[i * 3 + 2] * BOX, c.z - BOX / 2, BOX);
        const y = TOP - ((seed[i * 3 + 1] * TOP + t * SPEED) % TOP);
        const k = i * 6;
        pos[k] = x; pos[k + 1] = y; pos[k + 2] = z;
        pos[k + 3] = x - SLANT * LEN; pos[k + 4] = y - LEN; pos[k + 5] = z;
      }
      geo.attributes.position.needsUpdate = true;
    },
  };
}
