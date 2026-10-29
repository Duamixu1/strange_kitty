import * as THREE from "three";

// 机位调度：读 cameras.json 的 zones，按类型摆相机。
//   fixed    固定位置 + 注视点
//   dolly    沿某轴跟随角色，落后 followOffset，始终朝 lookDirection
//   anchored 挂在某个物体（NPC、天秤）的局部坐标上，用于覆盖层
// 区由外面（game.js 按角色所在区域）决定，这里只负责"切"和"每帧更新"。切区时调用 onTransition 做擦除。
//
// 玩家转视角（look）：鼠标拖动在固定 / 轨道机位上"原地转头"，滚轮拉近拉远。机位本身不动：
// 泼溅场景镜头一出房间就穿帮、贴墙就糊，所以只转方向不挪位置。切区时自动回正，覆盖层（对话、看壁画）不受影响。
const UP = new THREE.Vector3(0, 1, 0);
// 默认上限；每个区可以在 cameras.json 里用 look: { yaw, pitchUp, pitchDown } 覆盖（走廊窄，转多了贴墙糊成一片）
export const LOOK_LIMIT = { yaw: 0.85, pitchUp: 0.35, pitchDown: 0.4, zoomMin: 0.7, zoomMax: 1.6 };
export class CameraDirector {
  constructor(camera, cams, { onTransition } = {}) {
    this.camera = camera; this.cams = cams; this.zones = cams.zones;
    this.onTransition = onTransition;
    this.current = null; this.overlay = null; this.anchors = {};
    camera.fov = cams.fov; camera.near = cams.near; camera.far = cams.far; camera.updateProjectionMatrix();
    this._tmp = new THREE.Vector3(); this._tmp2 = new THREE.Vector3(); this._tmp3 = new THREE.Vector3(); this._tmp4 = new THREE.Vector3();
    this.look = { yaw: 0, pitch: 0, zoom: 1 };
  }
  /** 拖动：dx、dy 是弧度增量（向右拖 dx>0 视线往右，向上拖 dy<0 视线往上） */
  get lookLimit() { return { ...LOOK_LIMIT, ...(this.zones[this.current]?.look || {}) }; }
  turn(dx, dy) {
    const L = this.look, M = this.lookLimit;
    L.yaw = THREE.MathUtils.clamp(L.yaw - dx, -M.yaw, M.yaw);
    L.pitch = THREE.MathUtils.clamp(L.pitch - dy, -M.pitchDown, M.pitchUp);
  }
  zoomBy(factor) { this.look.zoom = THREE.MathUtils.clamp(this.look.zoom * factor, LOOK_LIMIT.zoomMin, LOOK_LIMIT.zoomMax); }
  resetLook() { this.look.yaw = 0; this.look.pitch = 0; this.look.zoom = 1; }
  /** 当前区能不能转视角：固定和轨道机位可以，覆盖层和过场不行 */
  get canLook() { return !this.manual && !this.overlay && ["fixed", "dolly"].includes(this.zones[this.current]?.type); }
  // 朝 target 看，再叠上玩家转的角度
  _lookWithOffset(cam, target) {
    const L = this.look;
    if (!L.yaw && !L.pitch) { cam.lookAt(target); return; }
    const dir = this._tmp3.copy(target).sub(cam.position);
    const dist = dir.length(); dir.normalize();
    dir.applyAxisAngle(UP, L.yaw);
    const right = this._tmp4.crossVectors(dir, UP).normalize();
    dir.applyAxisAngle(right, L.pitch);
    cam.lookAt(this._tmp4.copy(cam.position).addScaledVector(dir, dist));
  }
  registerAnchor(name, object3d) { this.anchors[name] = object3d; }

  /** 切主区。immediate 不做擦除（开场用）。 */
  async setZone(id, { immediate = false } = {}) {
    if (id === this.current) return;
    const apply = () => { this.current = id; this.resetLook(); this.apply(id, null); };
    if (immediate || !this.onTransition) apply();
    else await this.onTransition(apply);
  }
  /** 覆盖层机位（看壁画、对话），退出时回主区。anchorObj 可以临时指定锚点物体。 */
  pushOverlay(id, anchorObj = null) { this.overlay = { id, anchorObj }; }
  popOverlay() { this.overlay = null; }

  apply(id, player) {
    const z = this.zones[id]; if (!z) return;
    const cam = this.camera;
    const looking = !this.overlay && (z.type === "fixed" || z.type === "dolly");   // 只有主机位吃玩家转的角度
    const fov = (z.fov || this.cams.fov) / (looking ? this.look.zoom : 1);
    if (cam.fov !== fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
    if (z.type === "fixed") {
      cam.position.set(...z.position);
      if (looking) this._lookWithOffset(cam, this._tmp.set(...z.lookAt)); else cam.lookAt(...z.lookAt);
    } else if (z.type === "dolly" && player) {
      const p = player.position;
      const along = THREE.MathUtils.clamp(p.z + z.followOffset, z.range[0], z.range[1]);
      cam.position.set(z.x, z.height, along);
      this._tmp.set(...z.lookDirection).normalize().add(cam.position);
      if (looking) this._lookWithOffset(cam, this._tmp); else cam.lookAt(this._tmp);
    } else if (z.type === "anchored") {
      const a = (this.overlay && this.overlay.anchorObj) || this.anchors[z.anchor]; if (!a) return;
      a.updateWorldMatrix(true, false);
      const o = (z.perAnchor && z.perAnchor[a.name]) || {};   // 个别 NPC 背后有泼溅虚影时单独给偏移
      cam.position.copy(this._tmp.set(...(o.offset || z.offset)).applyMatrix4(a.matrixWorld));
      cam.lookAt(this._tmp2.set(...(o.lookAtOffset || z.lookAtOffset)).applyMatrix4(a.matrixWorld));
    }
  }
  update(player) {
    if (this.manual) return;                       // 过场自己摆相机
    if (this.overlay) this.apply(this.overlay.id, player);
    else if (this.current) this.apply(this.current, player);
  }
}
