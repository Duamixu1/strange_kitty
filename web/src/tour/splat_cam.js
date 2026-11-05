import * as THREE from "three";
import { CUTOUT } from "../style/toon.js";
import { frameLook } from "./follow_cam.js";

// 泼溅区块的镜头（游览版方案第二节第 4 小节）：泼溅只在全景拍摄点附近看着清楚，贴墙就糊，所以镜头不跟着药郎贴墙走。
// 接口和 FollowCam 一样（setZone / turn / zoomBy / forward / update / updateCutout），tour.js 按区块的 camera.mode 换着用。
//   circle  安全圈：镜头只在拍摄点周围半径 r 的圈里滑（再扣掉离墙 margin 米的地方），转头对着药郎。
//           想要的位置 = 药郎身后 dist 米（拖动改方向），超出圈就收回圈里，离药郎太近就沿圈往反方向让开。
//   rail    轨道：镜头在线段 a→b 上滑，停在离药郎 back 米远的地方（走廊这种窄长空间）。
//   fixed   在 camera.fixed 里列的矩形里，镜头直接放在给定机位（安全圈照不到的角落）；任何模式都可以带 fixed。
// 高度 h（默认 1.5 米，低于这个泼溅地面的虚影多），看药郎胸口。
export class SplatCam {
  constructor(camera) {
    this.camera = camera;
    this.yaw = Math.PI; this.pitch = 0.12; this.dist = 3.0; this.minDist = 1.2; this.maxDist = 5;
    this.cfg = {}; this.canStand = () => true;
    this.pos = new THREE.Vector3(); this.look = new THREE.Vector3(); this.inited = false;
    this.fixedOn = null; this.flip = false; this.side = 0; this.cutT = 99; this.cuts = 0;
    this._t = new THREE.Vector3(); this._d = new THREE.Vector3();
  }
  setZone({ canStand, yaw, camera = {} }) {
    this.canStand = canStand; this.cfg = camera;
    if (yaw !== undefined) this.yaw = yaw;
    if (camera.dist) this.dist = camera.dist;
    if (camera.fov) { this.camera.fov = camera.fov; this.camera.updateProjectionMatrix(); }
    this.inited = false; this.margin = camera.margin ?? 1.2; this.fixedOn = null; this.flip = false; this.side = 0; this.cutT = 99;
    this._clearCache = new Map();
  }
  turn(dx, dy) { this.yaw -= dx; this.pitch = THREE.MathUtils.clamp(this.pitch + dy, -0.2, 0.7); }
  zoomBy(f) { this.dist = THREE.MathUtils.clamp(this.dist * f, this.minDist, this.maxDist); }
  get viewYaw() { const d = this._d.subVectors(this.look, this.pos); return Math.atan2(-d.x, -d.z); }
  /** 镜头水平朝向（给 WASD 用）：从镜头看向药郎的方向 */
  get forward() { const d = this._d.subVectors(this.look, this.pos); d.y = 0; return d.lengthSq() > 1e-6 ? d.normalize() : new THREE.Vector3(0, 0, -1); }

  // 离墙够不够远：以这点为圆心、margin 为半径，八个方向都还在可走区域里（结果按 10 厘米格子缓存）
  clear(x, z) {
    const key = `${Math.round(x * 10)},${Math.round(z * 10)}`;
    if (this._clearCache.has(key)) return this._clearCache.get(key);
    let ok = this.canStand(x, z);
    for (let k = 0; ok && k < 8; k++) { const a = k * Math.PI / 4; ok = this.canStand(x + Math.cos(a) * this.margin, z + Math.sin(a) * this.margin); }
    this._clearCache.set(key, ok);
    return ok;
  }
  // 从 p 往 c 收，直到离墙够远（收到 c 还不够就停在 c：拍摄点本身总是最清楚的地方）。p、c 是 Vector2，y 分量是 z
  pullToClear(p, c) {
    for (let s = 0; s <= 1.0001; s += 0.05) {
      const x = p.x + (c.x - p.x) * s, z = p.y + (c.y - p.y) * s;
      if (this.clear(x, z)) return new THREE.Vector2(x, z);
    }
    return c.clone();
  }

  // 算镜头该在哪。不改状态：hold 为真时沿用当前固定机位 / 轨道这一侧（刚切过镜头不许再切），返回值带上算出来的 fixed、flip
  target(player, hold = false) {
    const C = this.cfg, h = C.h ?? 1.5, t = this._t.set(player.position.x, player.position.y + 1.2, player.position.z);
    // 固定机位：药郎在某个矩形里就用那个机位（进出缓冲 0.35 米，update 里直接切，不滑过去）
    const inRect = ({ rect: [x0, x1, z0, z1] }, m) => t.x >= x0 - m && t.x <= x1 + m && t.z >= z0 - m && t.z <= z1 + m;
    // shot：做 act 时临时换的机位（guide.js 的 act.cam，docs/20），有就压过下面的固定机位
    const f = this.shot || (hold ? this.fixedOn : this.fixedOn && inRect(this.fixedOn, 0.35) ? this.fixedOn : (C.fixed || []).find((r) => inRect(r, 0)) || null);
    if (f) {   // 看点往药郎身上挪到他在画面里（follow_cam.js 的 frameLook；算完把镜头放回原处，update 里再平滑过去）
      const pos = new THREE.Vector3(...f.pos), cp = this.camera.position.clone(), cq = this.camera.quaternion.clone();
      const look = frameLook(this.camera, pos, f.look ? new THREE.Vector3(...f.look) : t.clone(), player);
      this.camera.position.copy(cp); this.camera.quaternion.copy(cq); this.camera.updateMatrixWorld();
      return { pos, look, fixed: f, flip: this.flip, side: this.side };
    }
    let flip = this.flip, side = this.side;
    const want = new THREE.Vector2(t.x + Math.sin(this.yaw) * this.dist, t.z + Math.cos(this.yaw) * this.dist);
    let p;
    if (C.mode === "rail") {
      const a = new THREE.Vector2(...C.a), b = new THREE.Vector2(...C.b), ab = b.clone().sub(a), L2 = ab.lengthSq();
      // 轨道上离药郎 back 米、并且在"想要的那一侧"的点：先投影药郎，再沿轨道往镜头那边退
      const proj = THREE.MathUtils.clamp(new THREE.Vector2(t.x, t.z).sub(a).dot(ab) / L2, 0, 1);
      // 镜头在药郎的哪一侧（按拖的方向）：拖到和轨道差不多垂直的时候不换（|cos| < 0.35 的死区），免得转镜头时来回换侧
      const cosA = new THREE.Vector2(want.x - t.x, want.y - t.z).normalize().dot(ab.clone().normalize());
      if (!side || (!hold && Math.abs(cosA) > 0.35)) side = Math.sign(cosA) || -1;
      const L = Math.sqrt(L2), back = (C.back ?? this.dist) / L, minS = this.minDist / L;
      // 这一侧退不够（药郎站在轨道端头附近）：换到另一侧，从前面回头拍。换过去以后要这一侧能退 minS + 0.6 米才换回来（防来回换）；
      // 换侧在 update 里是直接切镜头，不从药郎身上扫过去
      const room = (sd) => Math.abs(THREE.MathUtils.clamp(proj + sd * back, 0, 1) - proj);
      if (!hold) { if (!flip && room(side) < minS) flip = true; else if (flip && room(side) >= minS + 0.6 / L) flip = false; }
      const s = THREE.MathUtils.clamp(proj + (flip ? -side : side) * back, 0, 1);
      p = a.clone().addScaledVector(ab, s);
    } else {
      const c = new THREE.Vector2(...(C.center || [0, 0])), r = C.r ?? 1.5;
      p = want.clone();
      if (p.distanceTo(c) > r) p = c.clone().add(p.sub(c).setLength(r));
      // 离药郎太近（药郎走到拍摄点上了）：沿药郎 → 镜头的方向推到圈边上
      const tp = new THREE.Vector2(t.x, t.z);
      if (p.distanceTo(tp) < this.minDist) {
        const dir = p.clone().sub(tp); if (dir.lengthSq() < 1e-6) dir.set(Math.sin(this.yaw), Math.cos(this.yaw));
        p = c.clone().add(dir.setLength(r));
      }
      p = this.pullToClear(p, c);
    }
    const pos = new THREE.Vector3(p.x, h, p.y);
    const look = t.clone(); look.y += C.lookUp ?? 0;
    pos.y = h + Math.sin(this.pitch) * 0.6;   // 上下拖只让镜头高低动一点，不离开清楚的高度带
    return { pos, look, fixed: null, flip, side };
  }

  update(player, dt, snap = false) {
    let { pos, look, fixed, flip, side } = this.target(player);
    // 镜头切换（进出固定机位、轨道换侧）：直接切；切一次以后 0.6 秒内不再切（按原来的机位 / 原来那一侧重算）
    this.cutT += dt;
    if (!this.side) this.side = side;
    if (fixed !== this.fixedOn || flip !== this.flip || side !== this.side) {
      if (this.cutT < 0.6 && this.inited && !snap) ({ pos, look } = this.target(player, true));
      else { this.fixedOn = fixed; this.flip = flip; this.side = side; this.cutT = 0; this.cuts++; snap = snap || this.inited; }
    }
    const k = snap || !this.inited ? 1 : 1 - Math.exp(-4 * dt);
    this.pos.lerp(pos, k); this.look.lerp(look, k); this.inited = true;
    if (k === 1) { this.pos.copy(pos); this.look.copy(look); }
    this.camera.position.copy(this.pos); this.camera.lookAt(this.look); this.camera.updateMatrixWorld();
  }
  updateCutout() { CUTOUT.depth.value = 0; }   // 泼溅区块没有积木柱子，关掉遮挡淡出
}
