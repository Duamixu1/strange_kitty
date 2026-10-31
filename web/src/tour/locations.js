// 地点数据：web/src/data/tour/<地点>.json（场景线填），格式见 docs/14_游览版方案.md 第三节。
// 测试用的地点放 src/tour/fixtures/（总指挥自己的，不进正式地图）。
// 区块的可走格子、出生点、观景点、楼梯口来自场景线 kit_build.py 出的 <积木名>_walk.json；
// 地点 JSON 里同名字段可以覆盖（测试夹具就靠这个，不用 walk 文件也能跑）。
const LOCS = import.meta.glob("../data/tour/*.json");
const FIXTURES = import.meta.glob("./fixtures/*.json");
const WALKS = import.meta.glob("../data/tour/*_walk.json");
const TEXTS = import.meta.glob("../data/tour/text.json");
const LEGACY_WALK = import.meta.glob("../data/walkmap.json");   // 探案版的大奥可走图（只读），测试夹具用；正式地点由场景线复制成 data/tour/<名>_walk.json

const base = (p) => p.split("/").pop().replace(/\.json$/, "");
const imp = async (loader) => (await loader()).default;

/** 能进的地点 id 列表（正式 + 测试夹具，去掉 *_walk 和 text） */
export function locationIds() {
  const ids = Object.keys(LOCS).map(base).filter((n) => !n.endsWith("_walk") && n !== "text" && n !== "map");
  return { real: ids, test: Object.keys(FIXTURES).map(base) };
}

export async function loadLocation(id) {
  const key = Object.keys(LOCS).find((p) => base(p) === id) || Object.keys(FIXTURES).find((p) => base(p) === id);
  if (!key) throw new Error(`没有这个地点：${id}`);
  return imp(LOCS[key] || FIXTURES[key]);
}

/** 绘卷总地图的图和热区（场景线 data/tour/map.json）；没有就返回 null */
export async function loadMap() {
  const k = Object.keys(LOCS).find((p) => base(p) === "map");
  return k ? imp(LOCS[k]) : null;
}

export async function loadText() {
  const k = Object.keys(TEXTS)[0];
  return k ? imp(TEXTS[k]) : {};
}

// 把一个矩形 [x0, x1, z0, z1] 变成可走格子（测试夹具用；正式区块用 kit_build 出的 walk 文件）
function rectWalk([x0, x1, z0, z1], cell = 0.1) {
  const w = Math.round((x1 - x0) / cell), h = Math.round((z1 - z0) / cell);
  return { cell, x0, z0, w, h, rows: Array.from({ length: h }, () => "1".repeat(w)) };
}

// 只留矩形 [x0, x1, z0, z1] 里的可走格子：几个泼溅区块共用一张可走图时，各区块只能在自己那块走，进出都走出口转场
function clipWalk(walk, [x0, x1, z0, z1]) {
  const rows = walk.rows.map((row, j) => {
    const z = walk.z0 + (j + 0.5) * walk.cell;
    if (z < z0 || z > z1) return "0".repeat(row.length);
    return Array.from(row, (ch, i) => { const x = walk.x0 + (i + 0.5) * walk.cell; return x >= x0 && x <= x1 ? ch : "0"; }).join("");
  });
  return { ...walk, rows };
}

/** 区块数据合成：walk 文件 + 地点 JSON 里的覆盖 */
export async function resolveZone(loc, zoneId) {
  const Z = loc.zones[zoneId];
  if (!Z) throw new Error(`地点 ${loc.id} 没有区块 ${zoneId}`);
  let walk = {};
  const walkName = Z.walk || (Z.kit && !Z.walkRect ? Z.kit : null);   // 泼溅区块用 walk 指定可走图，积木区块默认和 kit 同名
  if (walkName === "walkmap") walk = await imp(Object.values(LEGACY_WALK)[0]);
  else if (walkName) {
    const k = Object.keys(WALKS).find((p) => base(p) === `${walkName}_walk`);
    if (!k) throw new Error(`缺 ${walkName}_walk.json（场景线生成）`);
    walk = await imp(WALKS[k]);
  }
  if (Z.walkRect) walk = { ...rectWalk(Z.walkRect), height: Z.height };
  if (Z.walkClip) walk = clipWalk(walk, Z.walkClip);
  return {
    id: zoneId, ...Z,
    walk,
    height: Z.height ?? walk.height ?? 2.7,
    spawn: Z.spawn ?? walk.spawn ?? null,   // 没有出生点（楼上这种只能从楼梯进的区块）：进来时站到第一个楼梯口
    views: Z.views ?? walk.views ?? {},
    stairs: Z.stairs ?? walk.stairs ?? [],
    textKey: Z.textKey ?? Z.kit ?? zoneId,   // 说明卡按 <textKey>.<数字> 找
  };
}
