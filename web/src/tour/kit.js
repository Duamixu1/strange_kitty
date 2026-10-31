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

const texCache = new Map();
function tex(file) {
  if (!texCache.has(file)) {
    const t = new THREE.TextureLoader().load(pub(`textures/kit/${file}`));
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
    t.flipY = false;   // glTF 的 UV 原点在左上，和 GLTFLoader 自己加载的贴图一样不翻
    texCache.set(file, t);
  }
  return texCache.get(file);
}

export function kitMaterial(key) {
  if (key.startsWith("bead_")) return makeToonMaterial({ color: C[key.slice(5)], shadeColor: C.wisteria, shadeMix: 0.08, threshold: 0.35 });   // 天花串珠：仰视看到的都是背光面，阴影压得很轻
  const d = KIT[key] || {};
  const color = d.tex ? "#ffffff" : C[d.color || key] || "#ff00ff";   // 没登记的 key 是品红，一眼能看出漏了
  const m = makeToonMaterial({ map: d.tex ? tex(d.tex) : null, color, shadeColor: C.wisteria, shadeMix: d.shadeMix ?? 0.3, threshold: 0.35, pattern: d.pattern || null });
  if (d.double) m.side = THREE.DoubleSide;
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
    o.material = mats.get(key);
  });
  return gltf.scene;
}
