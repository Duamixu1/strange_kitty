import * as THREE from "three";
import { makeToonMaterial } from "../style/toon.js";

// 手鞠物怪的实时占位模型：带纹样的球 + 几十根从球里长出来的彩线（管状曲线）+ 发光的核。
// unravel(t) 0→1 线长出来、核亮起来；collapse(t) 0→1 线缩回、球散掉。正式版换 Blender 渲的视频，这个接口不变。
const C = { paper: "#F1E9DA", coral: "#E6667A", crimson: "#B42A47", ochre: "#DCC67C", teal: "#49B3A6", wisteria: "#6A4C8C", navy: "#2A2A4E", lavender: "#D6D3EF", pink: "#E7A3B5" };

// model：配角与物怪线做的 assets/processed/temari.glb（半径 0.36、球心为原点、两极朝 ±Y，贴图自带纹样和描边）。
// 传了就用它当球体本体，没传（还没加载完或文件缺）就用下面代码拼的三层球。
export function buildTemari({ radius = 0.36, threads = 28, seed = 7, model = null } = {}) {
  const root = new THREE.Group();
  let s = seed; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;

  // 球：珊瑚底 + 麻叶（世界空间小周期），上半球再叠一层青海波的藏青带，像概念图的两段式
  const ball = new THREE.Mesh(new THREE.SphereGeometry(radius, 48, 32),
    makeToonMaterial({ color: C.coral, shadeColor: C.wisteria, shadeMix: 0.35, threshold: 0.3, pattern: { space: "world", tile: "asanoha", scale: 0.22, color: C.ochre, mix: 0.85 } }));
  const band = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.004, 48, 32, 0, Math.PI * 2, Math.PI * 0.42, Math.PI * 0.32),
    makeToonMaterial({ color: C.navy, shadeColor: C.wisteria, shadeMix: 0.3, threshold: 0.3, pattern: { space: "world", tile: "seigaiha", scale: 0.18, color: C.lavender, mix: 0.8 } }));
  const star = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.006, 48, 32, 0, Math.PI * 2, 0, Math.PI * 0.2),
    makeToonMaterial({ color: C.crimson, shadeColor: C.wisteria, shadeMix: 0.3, threshold: 0.3 }));
  const body = new THREE.Group();
  if (model) body.add(model.clone(true)); else body.add(ball, band, star);
  root.add(body);

  // 核：淡紫白的小球，unravel 时放大；用 MeshBasicMaterial 不受平涂阴影影响，像发光
  const core = new THREE.Mesh(new THREE.SphereGeometry(radius * 0.55, 24, 16), new THREE.MeshBasicMaterial({ color: C.lavender }));
  core.scale.setScalar(0.001); root.add(core);
  const eye = new THREE.Mesh(new THREE.SphereGeometry(radius * 0.16, 16, 12), new THREE.MeshBasicMaterial({ color: C.navy }));
  eye.position.set(0, 0, radius * 0.5); eye.scale.setScalar(0.001); core.add(eye);

  // 线：每根是一条从球面出发、往外卷的曲线，TubeGeometry 顺着路径生成，用 drawRange 控制"长出来多少"
  const colors = [C.coral, C.ochre, C.teal, C.wisteria, C.pink, C.crimson];
  const tubes = [];
  for (let i = 0; i < threads; i++) {
    const dir = new THREE.Vector3(rnd() - 0.5, rnd() * 0.8 - 0.2, rnd() - 0.5).normalize();
    const len = 1.6 + rnd() * 2.2;
    const pts = [dir.clone().multiplyScalar(radius * 0.8)];
    let p = dir.clone().multiplyScalar(radius), d = dir.clone();
    const swirl = new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize();
    for (let k = 1; k <= 8; k++) {
      d.applyAxisAngle(swirl, 0.55 + rnd() * 0.5).normalize();
      p = p.clone().addScaledVector(d, len / 8);
      p.y = Math.max(p.y, 0.05 - radius);   // 不钻进地面（root 放在球心高度）
      pts.push(p);
    }
    const curve = new THREE.CatmullRomCurve3(pts, false, "centripetal", 0.6);
    const geo = new THREE.TubeGeometry(curve, 48, 0.012 + rnd() * 0.012, 6, false);
    const mesh = new THREE.Mesh(geo, makeToonMaterial({ color: colors[i % colors.length], shadeColor: C.wisteria, shadeMix: 0.3, threshold: 0.2 }));
    mesh.geometry.setDrawRange(0, 0);
    mesh.frustumCulled = false;
    // 线头的"手"：先用淡紫白的小球占位
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), makeToonMaterial({ color: C.lavender, shadeColor: C.wisteria, shadeMix: 0.3 }));
    hand.visible = false; mesh.add(hand);
    tubes.push({ mesh, hand, curve, total: geo.index.count });
    root.add(mesh);
  }

  const api = {
    root, body, core,
    radius,
    /** 0→1：线长出来，核亮起来，球的纹样壳稍微胀开 */
    unravel(t) {
      t = THREE.MathUtils.clamp(t, 0, 1);
      for (let i = 0; i < tubes.length; i++) {
        const tb = tubes[i];
        const local = THREE.MathUtils.clamp((t - i / tubes.length * 0.35) / 0.65, 0, 1);   // 一根根先后长
        const e = 1 - Math.pow(1 - local, 3);
        tb.mesh.geometry.setDrawRange(0, Math.floor(tb.total * e / 6) * 6);
        tb.hand.visible = e > 0.02;
        tb.hand.position.copy(tb.curve.getPointAt(Math.max(0.001, e)));
        tb.hand.scale.setScalar(0.6 + e * 0.8);
      }
      core.scale.setScalar(Math.max(0.001, t)); eye.scale.setScalar(t > 0.6 ? (t - 0.6) / 0.4 : 0.001);
      body.scale.setScalar(1 + t * 0.15);
      body.rotation.y += 0.002 * t;
    },
    /** 0→1：线缩回、手消失，球和核一起缩没 */
    collapse(t) {
      t = THREE.MathUtils.clamp(t, 0, 1);
      for (const tb of tubes) {
        const e = 1 - t;
        tb.mesh.geometry.setDrawRange(0, Math.floor(tb.total * e / 6) * 6);
        tb.hand.visible = e > 0.05;
        tb.hand.position.copy(tb.curve.getPointAt(Math.max(0.001, e)));
      }
      const s = Math.max(0.001, 1 - t * t);
      body.scale.setScalar(s * 1.15); core.scale.setScalar(s);
    },
    /** 滚动：沿 -z 走，球绕 x 轴转 */
    roll(dz) { root.position.z += dz; body.rotation.x -= dz / radius; },
  };
  return api;
}
