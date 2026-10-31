// 资源地址。开发时模型、泼溅从项目的 assets/ 读（Vite 的 /@fs），public/ 的贴图从站点根读；
// 打包发布（tools/build_site.py）时站点可能挂在子路径下（GitHub Pages 是 /strange_kitty/），
// assets/ 里用到的文件复制进站点的 game-assets/。
const BASE = import.meta.env.BASE_URL;   // 开发 "/"，发布 "/strange_kitty/"

// public/ 下的文件："/textures/x.png" 或 "textures/x.png" 都行
export const pub = (p) => BASE + p.replace(/^\//, "");

// assets/ 下的文件（"processed/x.glb"、"worldlabs/…/splat_500k.spz"）；以 / 开头的当 public 文件，http 开头的原样
export const asset = (u) =>
  /^https?:/.test(u) ? u : u.startsWith("/") ? pub(u) : import.meta.env.DEV ? `/@fs${ASSETS_DIR}/${u}` : `${BASE}game-assets/${u}`;
