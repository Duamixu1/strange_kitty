import * as THREE from "three";
import CFG from "./data/spring.json";

// 弹簧骨：驱动 blender_layers.py 生成的骨链（下摆、大袖、长发）。
// 每节骨头只管自己的"尾巴"（子骨头的位置）：带惯性的位置积分 + 回到绑定形状的力 + 重力，
// 长度固定，再被腿、躯干的胶囊推开，最后把骨头转向尾巴。做法和 VRM 的 SpringBone 一样。
// 每帧在 mixer.update 之后调用 update(dt)；截图定格时调用 settle() 让它先静止下来。
const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3(), _v3 = new THREE.Vector3();
const _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion();

function closestOnSegment(p, a, b, out) {
  const ab = _v3.subVectors(b, a); const t = Math.max(0, Math.min(1, _v1.subVectors(p, a).dot(ab) / Math.max(ab.lengthSq(), 1e-9)));
  return out.copy(a).addScaledVector(ab, t);
}

export class SpringBones {
  constructor(root) {
    this.root = root;
    root.updateMatrixWorld(true);
    const bones = {}; root.traverse((o) => { if (o.isBone) bones[o.name] = o; });
    // 碰撞体
    this.colliders = {};
    for (const [name, c] of Object.entries(CFG.colliders)) {
      if (c.type === "box") {                     // 盒子：挂在某个节点（挂点或骨头）上，min/max 是节点自己坐标里的范围
        const node = root.getObjectByName(c.node); if (!node) continue;
        this.colliders[name] = { box: true, node, min: new THREE.Vector3(...c.min), max: new THREE.Vector3(...c.max), inv: new THREE.Matrix4(), scale: 1 };
        continue;
      }
      if (!bones[c.from] || !bones[c.to]) continue;
      this.colliders[name] = { a: bones[c.from], b: bones[c.to], r: c.r, pa: new THREE.Vector3(), pb: new THREE.Vector3() };
    }
    // 骨链：chain_<组>_<名>_<序号>，末端 chain_<组>_<名>_end
    const chains = {};
    for (const [name, b] of Object.entries(bones)) {
      const m = /^chain_(hem|sleeve|hair)_(.+)_(\d+)$/.exec(name);
      if (!m) continue;
      const key = `${m[1]}_${m[2]}`;
      (chains[key] ||= { group: m[1], joints: [] }).joints.push({ bone: b, idx: +m[3] });
    }
    this.chains = Object.values(chains);
    for (const ch of this.chains) {
      ch.joints.sort((x, y) => x.idx - y.idx);
      ch.cfg = CFG.groups[ch.group];
      ch.cols = {};   // 每组自己的碰撞半径（加载时校准）
      for (const j of ch.joints) {
        const tail = j.bone.children.find((c) => c.isBone);
        j.tailBone = tail;
        j.axis = tail.position.clone().normalize();          // 骨头本地空间里指向尾巴的方向
        j.rest = j.bone.quaternion.clone();
        j.len = tail.getWorldPosition(_v1).distanceTo(j.bone.getWorldPosition(_v2));
        j.cur = tail.getWorldPosition(new THREE.Vector3()); j.prev = j.cur.clone();
      }
    }
    this.calibrate();
    this.count = this.chains.reduce((n, c) => n + c.joints.length, 0);
  }

  // 绑定姿势下，给每一节单独算它允许的碰撞体半径：离腿远的关节用配置里的完整半径，
  // 静止时就贴着腿的那几节才收小（留 5 毫米），免得一节贴腿把整条腿的半径都压没了
  calibrate() {
    this.updateColliders();
    this.radii = {};
    for (const ch of this.chains) {
      const cfg = ch.cfg;
      for (const j of ch.joints) {
        j.radii = {};
        j.boxes = {};
        for (const cn of cfg.colliders) {
          const c = this.colliders[cn]; if (!c) continue;
          if (c.box) {   // 盒子：静止时关节已经贴着或在里面，就把离它最近的那一面让开到关节外面
            const lo = c.min.clone(), hi = c.max.clone();
            const q = j.cur.clone().applyMatrix4(c.inv); const m = cfg.hit / c.scale + 0.003;
            const inside = [0, 1, 2].every((k) => q.getComponent(k) > lo.getComponent(k) - m && q.getComponent(k) < hi.getComponent(k) + m);
            if (inside) {
              const pens = [0, 1, 2].flatMap((k) => [[q.getComponent(k) - (lo.getComponent(k) - m), k, "lo"], [(hi.getComponent(k) + m) - q.getComponent(k), k, "hi"]]);
              const [, k, side] = pens.sort((x, y) => x[0] - y[0])[0];
              if (side === "lo") lo.setComponent(k, q.getComponent(k) + m); else hi.setComponent(k, q.getComponent(k) - m);
            }
            j.boxes[cn] = { lo, hi };
            continue;
          }
          const d = j.cur.distanceTo(closestOnSegment(j.cur, c.pa, c.pb, _v2));
          j.radii[cn] = Math.max(Math.min(c.r, d - cfg.hit - 0.005), 0.0);
          const g = (this.radii[ch.group] ||= {});
          g[cn] = Math.min(g[cn] ?? Infinity, j.radii[cn]);   // 只用来打印看最小值
        }
      }
    }
  }

  updateColliders() {
    for (const c of Object.values(this.colliders)) {
      if (c.box) { c.inv.copy(c.node.matrixWorld).invert(); c.scale = c.node.getWorldScale(_v1).x; continue; }
      c.a.getWorldPosition(c.pa); c.b.getWorldPosition(c.pb);
    }
  }

  update(dt) {
    dt = Math.min(dt, 1 / 30);
    this.root.updateMatrixWorld(true);
    this.updateColliders();
    for (const ch of this.chains) {
      const cfg = ch.cfg;
      for (const j of ch.joints) {
        const radii = j.radii;
        const b = j.bone;
        b.parent.getWorldQuaternion(_q1);
        const head = b.getWorldPosition(_v1).clone();
        // 绑定形状在世界里的方向
        const restDir = _v2.copy(j.axis).applyQuaternion(j.rest).applyQuaternion(_q1);
        const next = j.cur.clone()
          .addScaledVector(_v3.subVectors(j.cur, j.prev), 1 - cfg.drag)
          .addScaledVector(restDir, cfg.stiffness * dt)
          .add(new THREE.Vector3(0, -cfg.gravity * dt, 0));
        next.sub(head).setLength(j.len).add(head);
        for (const [cn, r] of Object.entries(radii)) {
          if (r <= 0) continue;
          const c = this.colliders[cn]; const p = closestOnSegment(next, c.pa, c.pb, new THREE.Vector3());
          const d = next.distanceTo(p), min = r + cfg.hit;
          if (d < min) { next.sub(p).setLength(min).add(p); next.sub(head).setLength(j.len).add(head); }
        }
        for (const [cn, bx] of Object.entries(j.boxes)) {
          const c = this.colliders[cn]; const q = next.clone().applyMatrix4(c.inv); const m = cfg.hit / c.scale;
          const pens = [0, 1, 2].flatMap((k) => [[q.getComponent(k) - (bx.lo.getComponent(k) - m), k, -1], [(bx.hi.getComponent(k) + m) - q.getComponent(k), k, 1]]);
          if (pens.every((x) => x[0] > 0)) {        // 在盒子里：从穿进去最浅的那一面推出去
            const [, k, dir] = pens.sort((x, y) => x[0] - y[0])[0];
            q.setComponent(k, dir < 0 ? bx.lo.getComponent(k) - m : bx.hi.getComponent(k) + m);
            next.copy(q.applyMatrix4(c.node.matrixWorld)); next.sub(head).setLength(j.len).add(head);
          }
        }
        j.prev.copy(j.cur); j.cur.copy(next);
        // 骨头转向尾巴
        const to = next.clone().sub(head).normalize().applyQuaternion(_q2.copy(_q1).invert());
        const from = _v2.copy(j.axis).applyQuaternion(j.rest);
        b.quaternion.setFromUnitVectors(from, to).multiply(j.rest);
        b.updateMatrixWorld(true);
      }
    }
  }

  // 定格截图前让骨链静止下来
  settle(steps = 120) { for (let i = 0; i < steps; i++) this.update(1 / 60); }

  // 跳动作时把速度清零，免得被甩飞
  reset() { for (const ch of this.chains) for (const j of ch.joints) j.prev.copy(j.cur); }
}
