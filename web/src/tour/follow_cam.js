import * as THREE from "three";
import { MeshBVH } from "three-mesh-bvh";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { CUTOUT } from "../style/toon.js";

// 积木区块的跟随镜头：绕药郎转（拖动转方向和俯仰、滚轮拉远拉近），镜头不穿墙、不顶天花：
// 有碰撞网格（setCollider，积木区块都有）时，从药郎胸口往镜头方向打一条射线，碰到真实的墙、柱、天花就停在前面 0.25 米；
// 水池、碎石、拱桥栏杆这些矮东西不挡（10-30 以前用可走格子判断，矮东西也算墙，镜头被逼到头顶往下俯拍）。
// 没有碰撞网格时退回按可走格子逐步试。镜头也不出平面图的范围（外景没有墙的那几边）。
// 镜头和药郎之间挡着的柱子、家具交给着色器的遮挡淡出（toon.js 的 CUTOUT），这里每帧把药郎的屏幕位置和深度传过去。
// 固定机位：区块 camera.fixed 列的矩形（格式和泼溅区块一样 { rect: [x0, x1, z0, z1], pos: [x, y, z], look: [x, y, z] }），
// 药郎走进矩形就直接切到那个机位（像原作切镜头，不滑过去），走出来再切回跟随。look 不写就看药郎。
// 被挡时试的偏转角（弧度）和抬高量
const CAND_YAW = [0, 0.35, -0.35, 0.7, -0.7, 1.05, -1.05, 1.4, -1.4];
const CAND_PITCH = [0, 0.15, 0.3];   // 自动抬高最多 0.3 弧度（约 17°），宁可拉近也不俯拍
const MAX_PITCH = 0.9;               // 俯角上限（约 52°），手动拖也不超过

export class FollowCam {
  constructor(camera, { yaw = Math.PI, pitch = 0.2, dist = 3.2, minDist = 0.9, maxDist = 5, target = 1.45, fov = 50 } = {}) {   // 俯角 0.2（约 11°）、看胸口偏上：接近平视，10-30 用户嫌 0.32 往下看太多
    this.camera = camera;
    this.yaw = yaw; this.pitch = pitch; this.dist = dist;   // yaw：镜头在药郎的哪个方向（0 = 在 +z 那边）
    this.minDist = minDist; this.maxDist = maxDist; this.targetH = target;
    this.canStand = () => true; this.ceiling = 2.7; this.bounds = null; this.bvh = null; this.fixed = null; this.fixedOn = null;
    this._ray = new THREE.Ray();
    this.cur = null;     // 实际镜头距离（被墙挡住时比 dist 短）
    this.off = { yaw: 0, pitch: 0 };   // 被墙逼出来的偏转和抬高（自动，不挡了会回到 0）
    camera.fov = fov; camera.updateProjectionMatrix();
    this._t = new THREE.Vector3(); this._p = new THREE.Vector3(); this._v = new THREE.Vector3();
  }
  setZone({ canStand, ceiling, yaw, bounds = null, collider = null, fixed = null }) {
    this.canStand = canStand; this.ceiling = ceiling; this.bounds = bounds; this.bvh = collider; this.fixed = fixed; this.fixedOn = null;
    if (yaw !== undefined) this.yaw = yaw;
    this.cur = null; this.off = { yaw: 0, pitch: 0 };
  }
  turn(dx, dy) {
    this.yaw -= dx;
    this.pitch = THREE.MathUtils.clamp(this.pitch + dy, -0.15, MAX_PITCH);
  }
  zoomBy(f) { this.dist = THREE.MathUtils.clamp(this.dist * f, this.minDist, this.maxDist); }
  /** 镜头水平朝向（给 WASD 用）：从镜头看向药郎的方向 */
  get forward() {
    if (this.fixedOn) { const d = this.camera.getWorldDirection(this._v.clone()); d.y = 0; return d.lengthSq() > 1e-6 ? d.normalize() : new THREE.Vector3(0, 0, -1); }   // 固定机位：按画面方向走
    const y = this.viewYaw; return new THREE.Vector3(-Math.sin(y), 0, -Math.cos(y));
  }

  /** 镜头实际所在的水平方向（玩家设的 yaw + 被墙逼出来的偏转） */
  get viewYaw() { return this.yaw + this.off.yaw; }

  // 从 t 沿 (yaw, pitch) 往外，镜头最远能放多远：有碰撞网格打射线，没有就水平投影每 5 厘米查一次可走格子；
  // 高度不超过天花下 0.2 米，水平位置不出平面图范围
  reach(t, yaw, pitch, want) {
    const cp = Math.cos(pitch), sp = Math.sin(pitch), hx = Math.sin(yaw), hz = Math.cos(yaw);
    let d = want;
    if (sp > 0.01) d = Math.min(d, (this.ceiling - 0.2 - t.y) / sp);
    if (this.bounds) {
      const [x0, z0, x1, z1] = this.bounds, inside = (s) => { const x = t.x + hx * s * cp, z = t.z + hz * s * cp; return x > x0 && x < x1 && z > z0 && z < z1; };
      while (d > 0.3 && !inside(d)) d -= 0.05;
    }
    if (this.bvh) {
      this._ray.origin.copy(t); this._ray.direction.set(hx * cp, sp, hz * cp);
      const hit = this.bvh.raycastFirst(this._ray, THREE.DoubleSide, 0, d + 0.25);
      if (hit) d = Math.min(d, hit.distance - 0.25);
      return Math.max(0.3, d);
    }
    for (let s = 0.05; s <= d; s += 0.05) {
      const hd = s * cp;
      if (!this.canStand(t.x + hx * hd, t.z + hz * hd)) return Math.max(0.3, s - 0.1);
    }
    return Math.max(0.3, d);
  }

  update(player, dt, snap = false) {
    const t = this._t.set(player.position.x, player.position.y + this.targetH, player.position.z);
    const f = (this.fixed || []).find(({ rect: [x0, x1, z0, z1] }) => t.x >= x0 && t.x <= x1 && t.z >= z0 && t.z <= z1);
    if (f) {
      this.fixedOn = f;
      this.camera.position.set(...f.pos);
      if (f.look) this.camera.lookAt(...f.look); else this.camera.lookAt(t);
      this.camera.updateMatrixWorld();
      this.updateCutout(player);
      return;
    }
    if (this.fixedOn) { this.fixedOn = null; snap = true; }   // 从固定机位走出来：直接切回跟随，不从固定机位滑过来
    // 被挡时怎么躲：先往左右偏（窄廊下里自然变成顺着廊下看），再抬高俯视，最后才拉近。
    // 每帧试一圈"偏转 × 抬高"，代价 = 偏离玩家设定的角度 + 离想要的距离差多少 + 和上一帧选的差多少（防抖），取最小的
    const prev = this.off, want = this.dist;
    let best = null;
    for (const dy of CAND_YAW) for (const dp of CAND_PITCH) {
      const pitch = Math.min(this.pitch + dp, MAX_PITCH);
      const r = this.reach(t, this.yaw + dy, pitch, want);
      const cost = Math.abs(dy) + dp * 4 + (want - r) * 2.5 + (r < 0.7 ? 3 : 0) + (Math.abs(dy - prev.yaw) + Math.abs(dp - prev.pitch)) * 0.5;
      if (!best || cost < best.cost) best = { cost, dy, dp };
    }
    const k = snap || this.cur === null ? 1 : 1 - Math.exp(-5 * dt);
    this.off = { yaw: prev.yaw + (best.dy - prev.yaw) * k, pitch: prev.pitch + (best.dp - prev.pitch) * k };
    const yaw = this.yaw + this.off.yaw, pitch = Math.min(this.pitch + this.off.pitch, MAX_PITCH);
    const allowed = this.reach(t, yaw, pitch, want);
    // 拉远时慢慢退，被挡时立刻贴上来（不让镜头穿进墙里哪怕一帧）
    if (this.cur === null || snap) this.cur = allowed;
    else this.cur = allowed < this.cur ? allowed : this.cur + (allowed - this.cur) * (1 - Math.exp(-4 * dt));
    const cp = Math.cos(pitch);
    this.camera.position.copy(t).addScaledVector(this._v.set(Math.sin(yaw) * cp, Math.sin(pitch), Math.cos(yaw) * cp), this.cur);
    this.camera.lookAt(t);
    this.camera.updateMatrixWorld();
    this.updateCutout(player);
  }

  // 遮挡淡出参数：药郎胸口在屏幕上的位置（设备像素）、半径（按身高在屏幕上的大小）、观察深度
  updateCutout(player, renderer = this.renderer) {
    if (!renderer) return;
    const size = renderer.getDrawingBufferSize(this._sz || (this._sz = new THREE.Vector2()));
    const chest = this._p.set(player.position.x, player.position.y + 1.0, player.position.z);
    const depth = -chest.clone().applyMatrix4(this.camera.matrixWorldInverse).z;
    const ndc = chest.project(this.camera);
    CUTOUT.center.value.set((ndc.x * 0.5 + 0.5) * size.x, (ndc.y * 0.5 + 0.5) * size.y);
    // 1 米在这个深度上占多少像素 → 横向半径约 0.55 米
    const pxPerM = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2) * Math.max(depth, 0.1));
    CUTOUT.radius.value = 0.55 * pxPerM;
    CUTOUT.depth.value = depth > 0.5 ? depth : 0;
  }
}

// 不挡镜头的积木（场景线 10-30 给的清单，按 GLB 网格名）：吊绳和细栏杆、吊着的提灯、串珠、紫幔、竹丛。
// 这些又细又悬空，挡镜头会让镜头一跳一跳；被它们挡住视线的交给遮挡淡出
const NO_CAM_BLOCK = /^kit_(ink|chochin|bead_|drape|bamboo)/;

// 积木区块的碰撞网格：把场景里所有网格（含世界变换）合成一个只有位置的几何体，建 BVH 给镜头打射线。每个区块建一次，缓存在 root.userData
export function buildCollider(root) {
  if (root.userData.camCollider) return root.userData.camCollider;
  root.updateMatrixWorld(true);
  const geos = [];
  root.traverse((o) => {
    if (!o.isMesh || !o.geometry?.attributes.position || NO_CAM_BLOCK.test(o.name)) return;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", o.geometry.attributes.position.clone());
    if (o.geometry.index) g.setIndex(o.geometry.index.clone());
    g.applyMatrix4(o.matrixWorld);
    geos.push(g);
  });
  const merged = geos.length ? mergeGeometries(geos.map((g) => (g.index ? g.toNonIndexed() : g)), false) : null;
  root.userData.camCollider = merged ? new MeshBVH(merged) : null;
  return root.userData.camCollider;
}
