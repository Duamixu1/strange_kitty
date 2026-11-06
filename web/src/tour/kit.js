import * as THREE from "three";
import { pub } from "../paths.js";
import { makeToonMaterial } from "../style/toon.js";

// 游览版积木（tools/kit_build.py 出的 GLB）：材质名 kit_<key>，这里按 key 换成卡通材质。
// 贴图在 public/textures/kit/（tools/kit_textures.py），UV 在 Blender 里已经按米排好，不用再设 repeat。
const C = { paper: "#F1E9DA", coral: "#E6667A", crimson: "#B42A47", ochre: "#DCC67C", green: "#59B86A", teal: "#49B3A6", blue: "#4F74BF", wisteria: "#6A4C8C", navy: "#2A2A4E", lavender: "#D6D3EF", pink: "#E7A3B5", ink: "#322D48", kogecha: "#573F33" };   // 第 13 色焦茶（10-29 加，万屋的木框），不用来描边
// tex：贴图文件；shadeMix：阴影层压多少（墙画、门画压得很轻，像画上去的，不像受光的墙）；double：薄片两面都画
const KIT = {
  mural_L: { tex: "mural_L.jpg", shadeMix: 0.1 }, mural_R: { tex: "mural_R.jpg", shadeMix: 0.1 },
  end_far: { tex: "end_far.jpg", shadeMix: 0.05 }, door_near: { tex: "door_near.jpg", shadeMix: 0.05 },
  carpet: { tex: "carpet.png" }, boards: { tex: "boards.png" }, andon: { tex: "andon.png", shadeMix: 0.15 },
  chochin: { tex: "chochin.png", shadeMix: 0.25 }, drape: { tex: "drape.png", double: true },
  paper: { double: true }, ochre: { double: true },
  // 平面图积木（docs/16）。木色、土壁先借色板色，万屋参考截图（游1）到了再定
  tatami: { tex: "tatami.png", shadeMix: 0.2 }, fusuma: { tex: "fusuma.png", shadeMix: 0.12 }, shoji: { tex: "shoji.png", shadeMix: 0.15 },
  udoor: { tex: "udoor.png", shadeMix: 0.12 }, sao: { tex: "sao.png", shadeMix: 0.15 }, goten: { tex: "goten.png", shadeMix: 0.1 },
  engawa: { tex: "engawa.png" }, earth: { tex: "earth.png" }, kakejiku: { tex: "kakejiku.png", shadeMix: 0.05 },
  tatami_side: { color: "green" }, wood: { color: "ochre" }, toko: { color: "ochre" }, frame: { color: "navy" },
  plaster: { color: "paper", pattern: { tile: "shippo", space: "world", scale: 0.7, color: "#D6D3EF", mix: 0.3 } },
  // 万屋（座敷童子，参考 assets/concept/ref/wanya/）。平面图里用 mat: wood=wood_dark, plaster=plaster_coral … 换
  // wood_dark：万屋的深褐木框（柱、长押、鸭居、柜台），用第 13 色焦茶
  wood_dark: { color: "kogecha" }, plaster_coral: { color: "coral" }, plaster_white: { color: "paper" }, frame_crimson: { color: "crimson" },
  stone: { tex: "stone.png", shadeMix: 0.2 }, koshiita: { tex: "koshiita.png", shadeMix: 0.2 },   // 门厅石地（纸白 + 墨点压成灰）、腰板
  goten_teal: { tex: "goten_teal.png", shadeMix: 0.1 }, glassdoor: { tex: "glassdoor.png", shadeMix: 0.08 }, fanlight: { tex: "fanlight.png", shadeMix: 0.03 },
  lattice: { tex: "lattice.png", shadeMix: 0.1 }, dais: { tex: "dais.png", shadeMix: 0.15 }, dais_side: { color: "teal" },
  byobu: { tex: "byobu.png", shadeMix: 0.08, double: true },
  // 万屋室内庭（参考帧 12）：拱桥、白砂、水、庭石
  deck: { tex: "deck.png", shadeMix: 0.2 }, gravel: { tex: "gravel.png", shadeMix: 0.15 }, rock: { color: "lavender" },
  water: { color: "blue", pattern: { tile: "seigaiha", space: "world", scale: 0.6, color: "#D6D3EF", mix: 0.45 } },
  // 万屋雨夜外景、黑影人群：屋顶藏青瓦（青海波当瓦纹），黑影是不受光的墨色剪影
  roof: { color: "navy", pattern: { tile: "seigaiha", space: "world", scale: 0.5, color: "#6A4C8C", mix: 0.4 }, double: true },
  kage: { color: "ink", shadeMix: 0 },
  // 万屋第二轮布置（10-30）：大座敷的火灯窗障子、花卉襖、莲花画带、畳边黑漆框
  katomado_shoji: { tex: "katomado_shoji.png", shadeMix: 0.1 }, fusuma_hana: { tex: "fusuma_hana.png", shadeMix: 0.1 },
  frieze_flower: { tex: "frieze_flower.png", shadeMix: 0.1 }, lacquer: { color: "ink", shadeMix: 0.2 },
  dou_sign: { tex: "dou_sign.png", shadeMix: 0.05 },
  ougi_wall: { tex: "ougi_wall.png", shadeMix: 0.05 },
  bijin_byobu: { tex: "bijin_byobu.jpg", shadeMix: 0.03 },
  // 坂井家（参考 assets/concept/ref/sakai/，图案全是程序画的，10-30）
  noren_kamon: { tex: "noren_kamon.png", shadeMix: 0.05, double: true }, fusuma_kamon: { tex: "fusuma_kamon.png", shadeMix: 0.1 },
  maku_sanshoku: { tex: "maku_sanshoku.png", shadeMix: 0.15 }, maku_green: { tex: "maku_green.png", shadeMix: 0.1 },
  chochin_kamon: { tex: "chochin_kamon.png", shadeMix: 0.15 }, itado: { tex: "itado.png", shadeMix: 0.15 },
  fusuma_nami: { tex: "fusuma_nami.png", shadeMix: 0.1 }, rug_tsuru: { tex: "rug_tsuru.png", shadeMix: 0.1 },
  zabuton_maru: { tex: "zabuton_maru.png", shadeMix: 0.1 }, floor_black: { tex: "floor_black.png", shadeMix: 0.2 },
  panels_color: { tex: "panels_color.png", shadeMix: 0.1 }, goten_blue: { tex: "goten_blue.png", shadeMix: 0.1 },
  wall_darkred: { tex: "wall_darkred.png", shadeMix: 0.15 }, lattice_red: { tex: "lattice_red.png", shadeMix: 0.15 },
  shiromuku: { tex: "shiromuku.png", shadeMix: 0.05 }, plaster_gray: { color: "lavender" },
  // 坂井家图片模型三张（10-31，scenes/25~27）
  fusuma_nami_img: { tex: "fusuma_nami_img.jpg", shadeMix: 0.08 }, rug_tsuru_img: { tex: "rug_tsuru_img.jpg", shadeMix: 0.08 },
  fusuma_ondori: { tex: "fusuma_ondori.jpg", shadeMix: 0.08 },   // 坂井家客间左墙雄鸡襖（scenes/24，10-31，40 积分）
  byobu_shoukaku: { tex: "byobu_shoukaku.jpg", shadeMix: 0.06, double: true },
  kutsunugi: { color: "paper", shadeMix: 0.25 },   // 坂井家玄关沓脱石（参考 04 那块浅色石阶），10-31
  wall_gray: { tex: "wall_gray.png", shadeMix: 0.15 }, earth_dark: { tex: "earth_dark.png", shadeMix: 0.2 }, goten_black: { tex: "goten_black.png", shadeMix: 0.1 },
  panels_ybg: { tex: "panels_ybg.png", shadeMix: 0.1 },
  gunkei: { tex: "gunkei.jpg", shadeMix: 0.03 },   // 大座敷天花的群鸡图（scenes/23，10-30 花 25 积分），整片铺   // 大座敷凸间后墙的美人画屏风（scenes/22，10-30 花 25 积分）
  bamboo: { color: "teal" }, bamboo_leaf: { color: "green", double: true },   // 竹丛，名字以 kit_bamboo 开头，镜头不撞它
  fanlight_lotus: { tex: "fanlight_lotus.png", shadeMix: 0.03 }, fanlight_star: { tex: "fanlight_star.png", shadeMix: 0.03 }, fanlight_crest: { tex: "fanlight_crest.png", shadeMix: 0.03 },
  plaster_teal: { color: "teal", pattern: { tile: "shippo", space: "world", scale: 0.45, color: "#D6D3EF", mix: 0.25 } },
};

// ---------- 整套换材质（游31，11-06） ----------
// 地点 JSON 写 "mat": "ink"，tour.js 进地点时调 setKitMat(loc.mat)，之后加载的积木（区块、act 小积木、拾遗）全换成这一套。
// ink：笛小路家（TV《鵺》）的水墨——墨、灰、和纸白，只留朱红一点。灰是墨和纸白按比例调的（inkGray），不另起新色。
//   有专门水墨版的（INK_MAP）换成 *_ink；其余带贴图的在浏览器里按亮度压成灰（朱红保留）；纯色的按亮度换成灰，深红/珊瑚归成朱红。
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const inkGray = (t) => { const a = hex(C.ink), b = hex(C.paper); return "#" + a.map((x, i) => Math.round(x + (b[i] - x) * t).toString(16).padStart(2, "0")).join(""); };
Object.assign(KIT, {
  wood_ink: { color: inkGray(0.08) }, frame_ink: { color: C.ink }, tatami_side_ink: { color: inkGray(0.6) },
  tatami_ink: { tex: "tatami_ink.png", shadeMix: 0.2 }, shoji_ink: { tex: "shoji_ink.png", shadeMix: 0.15 }, fusuma_ink: { tex: "fusuma_ink.png", shadeMix: 0.1 },
  plaster_ink: { tex: "plaster_ink.png", shadeMix: 0.25 }, kokabe_ink: { color: inkGray(0.82) }, engawa_ink: { tex: "engawa_ink.png", shadeMix: 0.2 },
  sao_ink: { tex: "sao_ink.png", shadeMix: 0.15 }, stone_ink: { tex: "stone_ink.png", shadeMix: 0.2 }, earth_ink: { tex: "earth_ink.png", shadeMix: 0.2 },
  gravel_ink: { tex: "gravel_ink.png", shadeMix: 0.15 }, roof_ink: { tex: "roof_ink.png", shadeMix: 0.2, double: true }, rock_ink: { color: inkGray(0.45) },
});
// 原 key（按前缀）→ 水墨 key。顺序有关：先匹配到的算
const INK_MAP = [
  [/^(wood|toko|lacquer|koshiita|itado|dais_side)/, "wood_ink"], [/^frame(?!_crimson)/, "frame_ink"], [/^tatami_side/, "tatami_side_ink"], [/^tatami/, "tatami_ink"],
  [/^(shoji|katomado_shoji|lattice$|glassdoor)/, "shoji_ink"], [/^(fusuma|udoor)/, "fusuma_ink"], [/^(plaster|wall_)/, "plaster_ink"],
  [/^(engawa|floor_black|boards|deck)/, "engawa_ink"], [/^(sao|goten)/, "sao_ink"], [/^(stone|kutsunugi)/, "stone_ink"], [/^earth/, "earth_ink"],
  [/^gravel/, "gravel_ink"], [/^roof/, "roof_ink"], [/^rock/, "rock_ink"],
];
// 笛小路家（游31）：fue_* 本身就是水墨的（ink 套里原样用），每个都有彩色版 fue_*_color（退魔后整片上色，参考 17）。
//   彩色版往原作结尾那种柔和的调子收：粉、淡黄绿、旧金（11-06 总指挥；贴图 kit_textures.py fue_soften 统一压过，纯色这里直接写）
//   贴图 tools/kit_textures.py fue_set；墨云襖、虎襖、源氏香纹墙是出的图（scenes/47~49，彩色版程序上色），墨溅、葡萄是程序画的；
//   雪庭全景天空 textures/kit/fue_sky.jpg / fue_sky_color.jpg（scenes/50，2:1 等距柱状，天空球由总指挥接）
const T = (f, m = 0.15, x = {}) => ({ tex: f, shadeMix: m, ...x });
Object.assign(KIT, {
  fue_wood: { color: inkGray(0.1) }, fue_wood_color: { color: "kogecha" }, fue_frame: { color: "ink" }, fue_frame_color: { color: "ink" },
  fue_plaster: T("plaster_ink.png", 0.25), fue_plaster_color: { color: "paper" }, fue_kokabe: { color: inkGray(0.86) }, fue_kokabe_color: { color: "paper" },
  fue_tsuiji: T("fue_tsuiji.png", 0.2), fue_tsuiji_color: T("fue_tsuiji_color.png", 0.2),
  fue_boards: T("fue_boards.png", 0.2), fue_boards_color: T("fue_boards_color.png", 0.2),
  fue_tatami: T("fue_tatami.png", 0.2), fue_tatami_color: T("fue_tatami_color.png", 0.2), fue_tatami_side: { color: inkGray(0.6) }, fue_tatami_side_color: { color: "#A9B57E" },
  fue_shoji: T("fue_shoji.png"), fue_shoji_color: T("fue_shoji_color.png"), fue_lattice: T("fue_lattice.png", 0.1), fue_lattice_color: T("fue_lattice_color.png", 0.1),
  fue_fusuma_bokuun: T("fue_fusuma_bokuun.jpg", 0.1), fue_fusuma_bokuun_color: T("fue_fusuma_bokuun_color.jpg", 0.1),   // scenes/47（11-06 出图）
  fue_fusuma_hane: T("fue_fusuma_hane.png", 0.1), fue_fusuma_hane_color: T("fue_fusuma_hane_color.png", 0.1),
  fue_fusuma_tora: T("fue_fusuma_tora.jpg", 0.1), fue_fusuma_tora_color: T("fue_fusuma_tora_color.jpg", 0.1),   // scenes/48
  fue_fusuma_plain: T("fue_fusuma_plain.png", 0.1), fue_fusuma_plain_color: T("fue_fusuma_plain_color.png", 0.1),
  fue_byobu_budou: T("fue_byobu_budou.png", 0.08, { double: true }), fue_byobu_budou_color: T("fue_byobu_budou_color.png", 0.08, { double: true }),
  fue_ceiling: T("fue_ceiling.png"), fue_ceiling_color: T("fue_ceiling_color.png"), fue_ceiling_hane: T("fue_ceiling_hane.png", 0.1), fue_ceiling_hane_color: T("fue_ceiling_hane_color.png", 0.1),
  fue_snow: T("fue_snow.png", 0.2), fue_snow_color: T("fue_snow_color.png", 0.2),
  fue_roof: T("roof_ink.png", 0.2, { double: true }), fue_roof_color: { color: "#7F7C98", pattern: { tile: "seigaiha", space: "world", scale: 0.5, color: "#9B97B3", mix: 0.35 }, double: true },
  fue_gate_roof: T("fue_gate_roof.png", 0.2, { double: true }), fue_gate_roof_color: T("fue_gate_roof_color.png", 0.2, { double: true }),
  fue_gate_door: T("fue_gate_door.png", 0.05), fue_gate_door_color: T("fue_gate_door_color.png", 0.05),
  fue_dais: T("fue_dais.png"), fue_dais_color: T("fue_dais_color.png"), fue_dais_edge: T("fue_dais_edge.png", 0.1), fue_dais_edge_color: T("fue_dais_edge_color.png", 0.1),
  fue_genji_wall: T("fue_genji_wall.jpg", 0.05), fue_genji_wall_color: T("fue_genji_wall_color.jpg", 0.05),   // scenes/49
  fue_kicho: T("fue_kicho.png", 0.1, { double: true }), fue_kicho_color: T("fue_kicho_color.png", 0.1, { double: true }),
  fue_lacquer: { color: "ink", shadeMix: 0.2 }, fue_lacquer_color: { color: "ink", shadeMix: 0.2 }, fue_censer: { color: inkGray(0.35) }, fue_censer_color: { color: "navy" },
  fue_genji_plate: { color: "ink", shadeMix: 0.05 }, fue_genji_plate_color: { color: "ink", shadeMix: 0.05 }, fue_genji_line: { color: "paper", shadeMix: 0.05 }, fue_genji_line_color: { color: "#C9B47A", shadeMix: 0.05 },
  fue_under: { color: "ink", shadeMix: 0 }, fue_under_color: { color: "ink", shadeMix: 0 },
  fue_tree: { color: inkGray(0.1) }, fue_tree_color: { color: "kogecha" }, fue_pine: { color: inkGray(0.3) }, fue_pine_color: { color: "#8FA37A" },
  fue_far: { color: inkGray(0.72), shadeMix: 0.05 }, fue_far_color: { color: "lavender", shadeMix: 0.05 },
  // 红色之间（参考 10）：退魔前后都是红的，彩色版就是同一张
  fue_aka_wall: T("fue_aka_wall.png", 0.2), fue_aka_fusuma: T("fue_aka_fusuma.png", 0.1), fue_aka_tatami: T("fue_aka_tatami.png", 0.2),
  fue_aka_ceiling: T("fue_aka_ceiling.png"), fue_aka_dais: T("fue_aka_dais.png"), fue_aka_dais_edge: T("fue_aka_dais_edge.png", 0.1),
  fue_aka_kicho: T("fue_aka_kicho.png", 0.1, { double: true }), fue_aka_wood: { color: "#5A2638" },
  // 游32 第二轮（文案线物件清单）：御簾、锦缎、墨溅墙、组香盘、苔、脚印、拾遗
  fue_misu: T("fue_misu.png", 0.1, { double: true }), fue_misu_color: T("fue_misu_color.png", 0.1, { double: true }),
  fue_kinran: T("fue_kinran.png", 0.15), fue_kinran_color: T("fue_kinran_color.png", 0.15),
  fue_hime: { color: inkGray(0.2), shadeMix: 0.05 }, fue_hime_color: { hide: true },   // 御簾后的瑠璃姫墨影，退魔后不见了
  fue_nishiki: { color: inkGray(0.82), shadeMix: 0.2 }, fue_nishiki_color: { color: "#C9B47A", shadeMix: 0.2 },
  fue_wall_hane: T("fue_wall_hane.png", 0.15), fue_wall_hane_color: T("fue_wall_hane_color.png", 0.15),
  fue_gold: { color: inkGray(0.7), shadeMix: 0.05 }, fue_gold_color: { color: "#C9B47A", shadeMix: 0.05 },
  fue_silver: { color: "paper", shadeMix: 0.05 }, fue_silver_color: { color: "lavender", shadeMix: 0.05 },
  fue_moss: { color: "#6E8A6A", shadeMix: 0.2 }, fue_moss_color: { color: "#9DB07A" },   // 参考 12：苔在水墨里也是绿的（压暗的萌葱），全场除了朱红唯一的点色
  fue_print: { color: inkGray(0.4), shadeMix: 0 }, fue_print_color: { color: "lavender", shadeMix: 0 },
  fue_geta: { color: inkGray(0.45) }, fue_geta_color: { color: "#C9B47A" }, fue_fuda: { color: inkGray(0.8) }, fue_fuda_color: { color: "#D8C99A" },
  fue_kuchiki: { color: "#2A2430" }, fue_kuchiki_color: { color: "#2A2430" },
  // 退魔后（参考 19）：原来的门藏起来、换成废墟；草、樱花、墙缝只在彩色时出来（hide：这一套里不显示）
  fue_gate_wood: { color: inkGray(0.1) }, fue_gate_wood_color: { hide: true }, fue_gate_roof_color: { hide: true },
  fue_ruin_wood: { hide: true }, fue_ruin_wood_color: { color: "kogecha" }, fue_ruin_roof: { hide: true }, fue_ruin_roof_color: T("fue_gate_roof_color.png", 0.2, { double: true }),
  fue_ruin_crack: { hide: true }, fue_ruin_crack_color: { color: "kogecha", shadeMix: 0 },
  fue_grass: { hide: true }, fue_grass_color: { color: "#A7B86F", double: true }, fue_sakura: { hide: true }, fue_sakura_color: { color: "pink" },
});
const MATSETS = { ink: { map: INK_MAP, shade: inkGray(0.35), gray: inkGray }, color: { shade: C.wisteria } };
let MAT = null, MATNAME = null;
export function setKitMat(name) { MAT = (name && MATSETS[name]) || null; MATNAME = MAT ? name : null; }
// 已经加载好的积木整套换（退魔后水墨 → 彩色）：await recolorKit(根节点, "color")，之后新加载的也会是这一套。
// 先把新一套材质都建好、等贴图全部下完，再一次性换上（11-06 总指挥：同步换的话新贴图没到，地板、天花会先黑一下）
export async function recolorKit(root, name) {
  setKitMat(name); const mats = new Map(), meshes = [];
  root.traverse((o) => {
    if (!o.isMesh || !o.userData.kitKey) return;
    const k = o.userData.kitKey; meshes.push(o);
    if (!mats.has(k)) mats.set(k, kitMaterial(k));
  });
  await Promise.all([...mats.values()].map((m) => m.userData.ready));
  for (const o of meshes) { o.material = mats.get(o.userData.kitKey); o.visible = !o.material.userData.hide; }
}

const texCache = new Map();
function tex(file, gray = null) {
  const id = gray ? `${file}#gray` : file;
  if (!texCache.has(id)) {
    let t, done; const ready = new Promise((r) => (done = () => r()));   // 下完（或失败）就 resolve，recolorKit 等它
    if (gray) {   // 按亮度压成墨—纸白之间的灰，红（朱红、深红、珊瑚）保留成朱红
      t = new THREE.Texture();
      new THREE.ImageLoader().load(pub(`textures/kit/${file}`), (img) => {
        const cv = document.createElement("canvas"); cv.width = img.width; cv.height = img.height;
        const g = cv.getContext("2d"); g.drawImage(img, 0, 0);
        const px = g.getImageData(0, 0, cv.width, cv.height), d = px.data, a = hex(C.ink), b = hex(C.paper), cr = hex(C.crimson);
        for (let i = 0; i < d.length; i += 4) {
          const r = d[i], gg = d[i + 1], bb = d[i + 2];
          if (r > gg + 70 && r > bb + 40) { d[i] = cr[0]; d[i + 1] = cr[1]; d[i + 2] = cr[2]; continue; }
          const L = Math.min(1, Math.max(0, ((0.299 * r + 0.587 * gg + 0.114 * bb) / 255 - 0.12) / 0.8));
          for (let k = 0; k < 3; k++) d[i + k] = a[k] + (b[k] - a[k]) * L;
        }
        g.putImageData(px, 0, 0); t.image = cv; t.needsUpdate = true; done();
      }, undefined, done);
    } else t = new THREE.TextureLoader().load(pub(`textures/kit/${file}`), done, undefined, done);
    t.userData.ready = ready;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    t.flipY = false;   // glTF 的 UV 原点在左上，和 GLTFLoader 自己加载的贴图一样不翻
    texCache.set(id, t);
  }
  return texCache.get(id);
}

// 纯色按亮度换灰；深红、珊瑚归成朱红（整套里唯一的点色）
function grayColor(c) {
  if (c === C.crimson || c === C.coral) return C.crimson;
  const [r, g, b] = hex(c); return MAT.gray(Math.min(1, Math.max(0, ((0.299 * r + 0.587 * g + 0.114 * b) / 255 - 0.12) / 0.8)));
}

export function kitMaterial(key) {
  const shade = MAT ? MAT.shade : C.wisteria;
  if (key.startsWith("bead_")) { const c = C[key.slice(5)]; return makeToonMaterial({ color: MATNAME === "ink" ? grayColor(c) : c, shadeColor: shade, shadeMix: 0.08, threshold: 0.35 }); }   // 天花串珠：仰视看到的都是背光面，阴影压得很轻
  let d = KIT[key] || {}, gray = false;
  if (MATNAME === "ink" && !key.startsWith("fue_")) {   // fue_* 本来就是水墨的，原样用
    const hit = MAT.map.find(([re]) => re.test(key));
    if (hit) d = KIT[hit[1]]; else gray = true;
  } else if (MATNAME === "color") {   // 彩色：有 _color 的换成 _color，水墨版 *_ink 换回原来的，别的原样
    if (KIT[key + "_color"]) d = KIT[key + "_color"];
    else if (key.endsWith("_ink") && KIT[key.slice(0, -4)]) d = KIT[key.slice(0, -4)];
  }
  let color = d.tex ? "#ffffff" : C[d.color] || d.color || C[key] || (d.hide ? "#000000" : "#ff00ff");   // 没登记的 key 是品红，一眼能看出漏了
  if (gray && !d.tex && color !== "#ff00ff") color = grayColor(color);
  const pattern = d.pattern && gray ? { ...d.pattern, color: grayColor(d.pattern.color.toUpperCase()) } : d.pattern || null;
  const m = makeToonMaterial({ map: d.tex ? tex(d.tex, gray) : null, color, shadeColor: shade, shadeMix: d.shadeMix ?? 0.3, threshold: 0.35, pattern });
  if (d.double) m.side = THREE.DoubleSide;
  m.userData.hide = !!d.hide;   // 这一套里不显示（笛小路家退魔前后的门、草、樱花）
  m.userData.ready = d.tex ? tex(d.tex, gray).userData.ready : Promise.resolve();
  return m;
}

// 加载一个积木场景 GLB，换好材质返回根节点
export async function loadKit(loader, url) {
  const gltf = await loader.loadAsync(url);
  const mats = new Map();
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    const key = (o.material?.name || o.name).replace(/^kit_/, "").replace(/\.\d+$/, "");
    if (!mats.has(key)) mats.set(key, kitMaterial(key));
    o.material = mats.get(key); o.userData.kitKey = key; o.visible = !o.material.userData.hide;
  });
  return gltf.scene;
}
