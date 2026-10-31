import * as THREE from "three";

// 拔剑运镜（10-31 用户："挥剑的时候可以有一个缩放，整个镜头可以有一个运镜"）。
// 跟随镜头算完这一帧以后再叠一层：以药郎胸口为中心推拉、绕着他转、压低机位、变焦（fov）、震动。
// 不改跟随镜头自己的状态（yaw、dist 都是玩家的），下一帧它照常从玩家设定的角度算，所以拔剑结束自然回到原位，拔剑时拖镜头也照常有效。
// 时间按 exorcise_k 的秒数走，和 tour.js 的音效节奏点对齐：1.25 抽剑、3.08 妖化、5.1 横斩、7.9 收剑。
//   秒, 距离倍数, 绕转（度，正 = 镜头往药郎右手那边绕）, 机位（度，负 = 压低往上看）, fov 倍数（< 1 = 推上去）
const KEYS = [
  [0.0, 1.0, 0, 0, 1.0],
  [1.25, 0.9, 4, 0, 0.97],     // 抽剑：慢慢推近
  [3.0, 0.84, 8, -1, 0.95],
  [3.36, 0.8, 9, -4, 0.8],     // 妖化：镜头猛地一收（变焦推上去）
  [4.5, 0.76, 14, -6, 0.82],   // 定住：慢慢绕、慢慢压低
  [5.02, 0.7, 20, -9, 0.84],   // 蓄势：越推越近，低机位往上看
  [5.2, 0.86, 17, -6, 1.04],   // 横斩：一下拉开、变广角
  [6.4, 0.8, 15, -5, 0.96],
  [7.9, 0.88, 10, -3, 1.0],    // 收剑
  [9.6, 1.0, 0, 0, 1.0],       // 慢慢回到玩家原来的镜头
];
// 震动：秒、持续、幅度（度）
const SHAKES = [[3.08, 0.4, 0.5], [5.1, 0.35, 0.9]];

const smooth = (x) => x * x * (3 - 2 * x);
function at(t) {
  if (t <= KEYS[0][0]) return KEYS[0].slice(1);
  for (let i = 0; i < KEYS.length - 1; i++) {
    const a = KEYS[i], b = KEYS[i + 1];
    if (t <= b[0]) { const u = smooth((t - a[0]) / (b[0] - a[0])); return a.slice(1).map((v, k) => v + (b[k + 1] - v) * u); }
  }
  return KEYS[KEYS.length - 1].slice(1);
}

const _t = new THREE.Vector3(), _e = new THREE.Euler();
/** cam：当前镜头控制器（FollowCam 时按它的角度和防穿墙重算位置；固定机位、泼溅区块只变焦和震动）。t：exorcise_k 播到第几秒 */
export function swordShot(camera, cam, player, t) {
  const [kd, dyaw, dpitch, kf] = at(t);
  if (cam.reach && !cam.fixedOn && cam.cur !== null) {
    _t.set(player.position.x, player.position.y + cam.targetH, player.position.z);
    const yaw = cam.yaw + cam.off.yaw + THREE.MathUtils.degToRad(dyaw);
    const pitch = Math.max(-0.1, cam.pitch + cam.off.pitch + THREE.MathUtils.degToRad(dpitch));
    const d = Math.min(cam.cur * kd, cam.reach(_t, yaw, pitch, cam.cur * kd));   // 绕过去那边有墙就贴近一点，不穿墙
    const cp = Math.cos(pitch);
    camera.position.copy(_t).add(new THREE.Vector3(Math.sin(yaw) * cp, Math.sin(pitch), Math.cos(yaw) * cp).multiplyScalar(d));
    camera.lookAt(_t);
  }
  camera.fov *= kf; camera.updateProjectionMatrix();
  for (const [s, dur, amp] of SHAKES) {
    const u = (t - s) / dur; if (u < 0 || u > 1) continue;
    const a = THREE.MathUtils.degToRad(amp) * (1 - u) ** 2;
    _e.set(a * Math.sin(t * 73), a * Math.sin(t * 59 + 1.3), a * 0.5 * Math.sin(t * 41 + 2.1));
    camera.quaternion.multiply(new THREE.Quaternion().setFromEuler(_e));
  }
  camera.updateMatrixWorld();
}
