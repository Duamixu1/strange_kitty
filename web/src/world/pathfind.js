// 点击移动用的寻路：在可走栅格上做 8 邻接 Dijkstra（不切墙角），再拉直成折线。
// canStand(x, z) 由调用方给（游戏里 = 碰撞栅格 + NPC 阻挡 + 推门前的门口限制），栅格范围取 walkmap 的范围。
// 用法：
//   const pf = createPathfinder(walkmap, canStand);
//   pf.invalidate()                         可站规则变了（推开门）时调用，下次寻路重建栅格
//   pf.route([x, z], (x, z) => bool)        找最近的满足条件的格子，返回 { pts: [[x,z],...], len } 或 null
//   pf.routeTo([x, z], [gx, gz], tol)       走到离 [gx,gz] tol 米以内
export function createPathfinder(map, canStand) {
  const { cell, x0, z0, w, h } = map;
  const cx = (i) => x0 + (i + 0.5) * cell, cz = (j) => z0 + (j + 0.5) * cell;
  let blocked = null;
  function build() {
    blocked = new Uint8Array(w * h);
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) blocked[j * w + i] = canStand(cx(i), cz(j)) ? 0 : 1;
  }
  const free = (i, j) => i >= 0 && j >= 0 && i < w && j < h && !blocked[j * w + i];
  function snap(x, z, maxCells = 12) {
    const i = Math.floor((x - x0) / cell), j = Math.floor((z - z0) / cell);
    if (free(i, j)) return [i, j];
    let best = null, bd = Infinity;
    for (let dj = -maxCells; dj <= maxCells; dj++) for (let di = -maxCells; di <= maxCells; di++) {
      if (!free(i + di, j + dj)) continue;
      const d = di * di + dj * dj; if (d < bd) { bd = d; best = [i + di, j + dj]; }
    }
    return best;
  }
  // 两点之间直线上每 0.05 米都可站，就能直接走过去（拉直用）
  function clear(a, b) {
    const n = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05);
    for (let k = 1; k < n; k++) {
      const t = k / n, x = a[0] + (b[0] - a[0]) * t, z = a[1] + (b[1] - a[1]) * t;
      if (!free(Math.floor((x - x0) / cell), Math.floor((z - z0) / cell))) return false;
    }
    return true;
  }
  function smooth(pts) {
    if (pts.length < 3) return pts;
    const out = [pts[0]]; let k = 0;
    while (k < pts.length - 1) {
      let far = k + 1;
      for (let m = pts.length - 1; m > k + 1; m--) if (clear(pts[k], pts[m])) { far = m; break; }
      out.push(pts[far]); k = far;
    }
    return out;
  }
  function route(start, goal) {
    if (!blocked) build();
    const s = snap(start[0], start[1]); if (!s) return null;
    const N = w * h, D = new Float64Array(N).fill(Infinity), prev = new Int32Array(N).fill(-1);
    const heap = [];
    const push = (d, k) => { heap.push([d, k]); let c = heap.length - 1; while (c > 0) { const p = (c - 1) >> 1; if (heap[p][0] <= heap[c][0]) break; [heap[p], heap[c]] = [heap[c], heap[p]]; c = p; } };
    const pop = () => { const top = heap[0], last = heap.pop(); if (heap.length) { heap[0] = last; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < heap.length && heap[l][0] < heap[m][0]) m = l; if (r < heap.length && heap[r][0] < heap[m][0]) m = r; if (m === c) break; [heap[m], heap[c]] = [heap[c], heap[m]]; c = m; } } return top; };
    const k0 = s[1] * w + s[0]; D[k0] = 0; push(0, k0);
    const nb = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2]];
    while (heap.length) {
      const [d, k] = pop(); if (d > D[k]) continue;
      const i = k % w, j = (k / w) | 0;
      if (goal(cx(i), cz(j))) {
        const pts = []; for (let c = k; c !== -1; c = prev[c]) pts.push([cx(c % w), cz((c / w) | 0)]);
        pts.reverse(); pts[0] = [start[0], start[1]];
        return { pts: smooth(pts), len: d * cell };
      }
      for (const [di, dj, c] of nb) {
        const a = i + di, b = j + dj; if (!free(a, b)) continue;
        if (di && dj && (!free(a, j) || !free(i, b))) continue;
        const kk = b * w + a, nd = d + c;
        if (nd < D[kk]) { D[kk] = nd; prev[kk] = k; push(nd, kk); }
      }
    }
    return null;
  }
  return {
    invalidate() { blocked = null; },
    route,
    routeTo(start, g, tol = 0.15) { return route(start, (x, z) => Math.hypot(x - g[0], z - g[1]) <= tol); },
    /** [x,z] 附近最近的可走格中心，找不到返回 null */
    snapPoint(x, z, maxM = 1.5) { if (!blocked) build(); const c = snap(x, z, Math.ceil(maxM / cell)); return c && [cx(c[0]), cz(c[1])]; },
  };
}
