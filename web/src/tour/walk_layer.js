import * as THREE from "three";

// 走路的"随动层"（10-31，用户说药郎上半身僵、走得机械，要飘逸随意）。
// 走路动作本身（walk2_k，角色线 tools/walk_gen.py）只管一个周期里的摆动；这里管跟玩家怎么走有关、动作文件里做不出来的：
//   拐弯往里侧倾（速度 × 转向角速度），头稳住不跟着歪；
//   加速上身往前压（起步、冲刺），停步上身往前送一下再回正（阻尼弹簧，有余摆）；
//   头先转向要去的方向，身子后跟上。
// 都是在角色自己的坐标系里转（前 +z、上 +y），换算到骨头父节点空间再叠到动作之上，动作每帧会重写骨头，所以叠加不会累积；
// 没被动作打帧的骨头靠 restore() 先撤回上一帧叠的量。下摆、袖子、头发是弹簧骨，在这之后算，会跟着这层再甩一下。
const BONES = { s1: "Spine01", s2: "Spine02", head: "Head" };
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const clamp = THREE.MathUtils.clamp;

// 阻尼弹簧：w0 角频率（越大越快跟上），zeta 阻尼比（< 1 有余摆）
class Spring {
  constructor(w0, zeta) { this.w0 = w0; this.zeta = zeta; this.x = 0; this.v = 0; }
  step(target, dt) {
    const a = this.w0 * this.w0 * (target - this.x) - 2 * this.zeta * this.w0 * this.v;
    this.v += a * dt; this.x += this.v * dt; return this.x;
  }
  reset() { this.x = this.v = 0; }
}

export class WalkLayer {
  constructor(model, group) {
    this.group = group;
    this.b = {};
    for (const [k, n] of Object.entries(BONES)) this.b[k] = model.getObjectByName(n) || null;
    this.saved = new Map();
    this.target = null;   // 要转去的朝向（tour.js 每帧给），没有就当已经对准
    this.pitch = new Spring(8, 0.45);   // 前后：停步往前送，有余摆
    this.roll = new Spring(6, 0.7);     // 左右：拐弯内倾
    this.look = new Spring(9, 0.85);    // 头先转
    this.v = 0; this.acc = 0; this.w = 0;
    this.prev = null;
    this._q = new THREE.Quaternion(); this._p = new THREE.Quaternion(); this._g = new THREE.Quaternion(); this._e = new THREE.Euler();
  }
  reset() { this.prev = null; this.pitch.reset(); this.roll.reset(); this.look.reset(); this.v = this.acc = this.w = 0; }

  /** mixer.update 之前调：撤回上一帧叠上去的量（被动作重写的骨头无所谓） */
  restore() { for (const [bone, q] of this.saved) bone.quaternion.copy(q); this.saved.clear(); }

  /** mixer.update 之后、弹簧骨之前调 */
  apply(dt) {
    if (!(dt > 0)) return;
    const g = this.group, yaw = g.rotation.y;
    if (!this.prev || this.prev.pos.distanceTo(g.position) > 1) { this.reset(); this.prev = { pos: g.position.clone(), yaw }; return; }   // 换区块瞬移
    // 速度、加速度、转向角速度，各自低通一下（每帧的数值有锯齿）
    const k = (tau) => 1 - Math.exp(-dt / tau);
    const dx = g.position.x - this.prev.pos.x, dz = g.position.z - this.prev.pos.z;
    const v = Math.hypot(dx, dz) / dt, v0 = this.v;
    this.v += (v - this.v) * k(0.1);
    this.acc += ((this.v - v0) / dt - this.acc) * k(0.12);
    this.w += (wrap(yaw - this.prev.yaw) / dt - this.w) * k(0.08);
    this.prev.pos.copy(g.position); this.prev.yaw = yaw;

    // 目标量（弧度）。加速和减速都往前：加速是往前压着发力（冲刺 2.5 米/秒² 约 3°），停步是身子惯性往前送（约 5°），弹簧再回正。
    // 10-31 第一版加速时是往后拖，冲刺时整个人后仰，用户说跑得不帅，改成往前。走着时整体再前倾一点
    const pitchT = clamp(Math.abs(this.acc) * 0.022, 0, 0.09) + Math.min(this.v, 2) * 0.015;
    // 拐弯内倾：向心加速度 v·ω 越大倾得越多，最多约 7°。ω > 0 是往左转，左是 +x，往 +x 倒要绕 z 轴转负角
    const rollT = clamp(-this.v * this.w * 0.05, -0.12, 0.12);
    // 头先看过去：还差多少度没转过去，头先转一半，最多约 25°；站着不动时回正
    const lookT = this.target === null || this.v < 0.05 ? 0 : clamp(wrap(this.target - yaw) * 0.5, -0.45, 0.45);
    const pitch = this.pitch.step(pitchT, dt), roll = this.roll.step(rollT, dt), look = this.look.step(lookT, dt);

    // 上身两节平分；头：转向看过去，同时抵掉大半的侧倾和前倾，视线保持水平
    this.add(this.b.s1, pitch * 0.5, 0, roll * 0.55);
    this.add(this.b.s2, pitch * 0.5, look * 0.25, roll * 0.45);
    this.add(this.b.head, -pitch * 0.6, look * 0.75, -roll * 0.75);
  }

  // 在角色坐标系里绕 x（前倾为正）、y（左转为正）、z 转，叠到骨头上：local' = P⁻¹ · (G·R·G⁻¹) · P · local
  add(bone, rx, ry, rz) {
    if (!bone || (!rx && !ry && !rz)) return;
    if (!this.saved.has(bone)) this.saved.set(bone, bone.quaternion.clone());
    bone.parent.updateWorldMatrix(true, false);
    const P = bone.parent.getWorldQuaternion(this._p), G = this.group.getWorldQuaternion(this._g);
    const R = this._q.setFromEuler(this._e.set(rx, ry, rz, "YXZ"));
    R.premultiply(G).multiply(G.clone().invert());                  // 角色系 → 世界系
    R.premultiply(P.clone().invert()).multiply(P);                   // 世界系 → 父节点系
    bone.quaternion.premultiply(R);
  }
}
