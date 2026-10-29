// 真实可走区域：由 tools/walkmap.py 从各块泼溅的 collider.glb 预算成 0.1 米栅格（src/data/walkmap.json，别手改，改布局后重跑脚本）。
// 用法：import { canStand, floorY, nearestStand } from "./world/collision.js";
//   canStand(x, z)        这个点能不能站。已经扣掉 0.25 米身体半径，直接拿角色脚下坐标查
//   canStandP(p)          同上，传 {x, z}
//   floorY(x, z)          这一格泼溅地面的真实高度（米）。走廊泼溅的地面是斜的：门口 +0.2，尽头 -1.9；房间约 0。没有地面返回 null
//   nearestStand(x, z, r) 半径 r 米内最近的可站点 {x, z}，用于 ?at= 传送或卡住时拉回；找不到返回 null
//   walkmap               原始栅格，调试用
import walkmap from "../data/walkmap.json" with { type: "json" };

export function createCollision(map) {
  const { cell, x0, z0, w, h, rows } = map;
  let floor = null;
  if (map.floor) {
    const bin = typeof atob === "function" ? atob(map.floor) : Buffer.from(map.floor, "base64").toString("binary");
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    floor = new Int16Array(bytes.buffer);
  }
  const idx = (x, z) => {
    const i = Math.floor((x - x0) / cell), j = Math.floor((z - z0) / cell);
    return i < 0 || j < 0 || i >= w || j >= h ? null : [i, j];
  };
  function canStand(x, z) {
    const c = idx(x, z);
    return !!c && rows[c[1]].charCodeAt(c[0]) === 49; // '1'
  }
  function floorY(x, z) {
    const c = idx(x, z);
    if (!c || !floor) return null;
    const v = floor[c[1] * w + c[0]];
    return v === -32768 ? null : v / 100;
  }
  function nearestStand(x, z, r = 1.0) {
    if (canStand(x, z)) return { x, z };
    const n = Math.ceil(r / cell); let best = null, bd = Infinity;
    const ci = Math.floor((x - x0) / cell), cj = Math.floor((z - z0) / cell);
    for (let dj = -n; dj <= n; dj++) for (let di = -n; di <= n; di++) {
      const i = ci + di, j = cj + dj;
      if (i < 0 || j < 0 || i >= w || j >= h || rows[j].charCodeAt(i) !== 49) continue;
      const px = x0 + (i + 0.5) * cell, pz = z0 + (j + 0.5) * cell, d = (px - x) ** 2 + (pz - z) ** 2;
      if (d < bd && d <= r * r) { bd = d; best = { x: px, z: pz }; }
    }
    return best;
  }
  return { canStand, canStandP: (p) => canStand(p.x, p.z), floorY, nearestStand, walkmap: map };
}

const C = createCollision(walkmap);
export const { canStand, canStandP, floorY, nearestStand } = C;
export { walkmap };
