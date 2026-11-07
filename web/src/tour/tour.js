import * as THREE from "three";
import { asset, pub } from "../paths.js";
// Spark（泼溅渲染，压缩后约 1 MB，占程序包一大半）只有大奥用：进大奥时才 import，总地图、坂井家、万屋不用下它（11-05 用户："其他人打开特别慢"）
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { PaperOutlinePost } from "../style/post.js";
import { createCollision } from "../world/collision.js";
import { createPathfinder } from "../world/pathfind.js";
import { loadKit, kitReady, setKitMat, recolorKit } from "./kit.js";
import { loadPlayer, loadNpc, PLAYER_MODEL } from "./player.js";
import PROPS from "../data/props.json";
import { createGuide, loadCase } from "./guide.js";
import { FollowCam, buildCollider } from "./follow_cam.js";
import { SplatCam } from "./splat_cam.js";
import { swordShot } from "./sword_cam.js";
import { locationIds, loadLocation, loadText, loadMap, resolveZone } from "./locations.js";
import { fusumaWipe, prompt, toast, card, Tags, flash } from "./ui.js";
import { createRain } from "./rain.js";
import { createSnow } from "./snow.js";
import { audio } from "./audio.js";
import { loading, lastFail } from "./loading.js";
import { createEncounter, ROSTER } from "./encounter.js";
import { createMedbox } from "./medbox.js";
import { storyIntro, introSeen } from "./story_intro.js";
import { startI18n, mountSettings } from "./i18n.js";   // 语言设置（文案w）：总地图右上「设」选中文 / English / 日本語

// 游览版：药郎在原作地点里走走看看（docs/14_游览版方案.md）。
//   /tour.html                    绘卷总地图（现在是占位的横向长卷，游5 的图到了再换）
//   /tour.html?loc=<地点>          进地点，从 start 区块开始；&zone=<区块> 直接进某个区块
// 操作：点地面走过去，点"観"标签走过去看说明卡，点出口标签走过去换区块；WASD / 方向键也能走（跟着镜头方向）；按住 Shift 快走，按住 1 秒以上加速成跑；
//       拖动转镜头，滚轮拉远拉近，E 看说明卡 / 关卡片，P 拍照（存 PNG），F 换拍照滤镜（原色 / 夜色 / 雨 / 褪色），O 换拍照姿势（抱臂 / 回头），Esc 关卡片，M 回总地图。
// 调试：window.__tour；?auto=1 加载完按区块的验收机位和几个跟随角度拍图存到 assets/processed/shots/tour_*（无头 Chrome 用）
const params = new URLSearchParams(location.search);
// ?fresh=1：当第一次来的人玩（清掉案子进度、图鉴、教学卡这些本地记录），试玩引导用
if (params.has("fresh")) { try { Object.keys(localStorage).filter((k) => k.startsWith("mononoke_tour_")).forEach((k) => localStorage.removeItem(k)); } catch {} }
const locId = params.get("loc");
const status = document.getElementById("status");
startI18n();
// 手机、平板（手指是主要输入）：底部按钮栏代替键盘，说明换成手指的；?touch=1 在电脑上强开
const touch = matchMedia("(pointer: coarse)").matches || params.has("touch");
// 11-05 轻量档（用户："先优化一版加载的问题"）：手机（触屏）、省流量模式、浏览器估计网速低于 3 Mbps 时，泼溅读 lite（点数约一半，
//   每块 7.5 MB → 约 3.5 MB，场景线 tools/spz_thin.py）。?lite=1 / ?lite=0 强制
const conn = navigator.connection;
const LITE = params.get("lite") === "1" || (params.get("lite") !== "0" && (touch || !!conn?.saveData || (conn?.downlink ?? 10) < 3));
if (touch) document.body.classList.add("touch");
const assetUrl = asset;
// 声音：浏览器要用户先操作一次才能出声（手机上是第一次点屏幕）；右上角"音"键开关，记在本机
for (const ev of ["pointerdown", "pointerup", "touchend", "keydown"]) addEventListener(ev, () => audio.unlock(), { capture: true });
const sndBtn = document.getElementById("snd");
const showSnd = () => { sndBtn.textContent = audio.muted ? "静音" : "声音"; sndBtn.setAttribute("aria-pressed", String(!audio.muted)); sndBtn.classList.toggle("off", audio.muted); };
const toggleSnd = () => { audio.unlock(); audio.toggle(); showSnd(); };
showSnd();
sndBtn.addEventListener("click", (e) => { e.stopPropagation(); toggleSnd(); });
addEventListener("keydown", (e) => { if (e.code === "KeyB") toggleSnd(); });   // src/paths.js：开发读 ../assets，发布读站点里的 game-assets/

// 访问统计（GoatCounter）：页面按"/"（总地图）和"/地点/区块"报，玩家操作按事件报（拔剑、拍照、开说明卡）。
// 统计脚本是异步加载的，没到就先排队；开发时（localhost / 本机地址）不报。国内有些网络加载不到脚本，那部分就不计
const statQ = [];
const statOn = !/^(localhost|127\.|\[::1\]|::1$)/.test(location.hostname) && !params.has("selftest") && !params.has("auto");
function stat(path, title, event = false) {
  if (!statOn) return;
  const send = () => window.goatcounter.count({ path, title, event });
  if (window.goatcounter?.count) send(); else statQ.push(send);
}
if (statOn) { const t = setInterval(() => { if (window.goatcounter?.count) { clearInterval(t); statQ.splice(0).forEach((f) => f()); } }, 500); setTimeout(() => clearInterval(t), 30000); }
if (!locId) stat("/", "总地图");
// 下过的别再下（docs/23 C1）：发布版注册 Service Worker（public/sw.js），构建号变了浏览器会换新的；开发时不装
const swReady = !import.meta.env.DEV && "serviceWorker" in navigator && window.__BUILD ? navigator.serviceWorker.register(pub("sw.js") + "?v=" + window.__BUILD).catch(() => null) : Promise.resolve(null);
// 加载时长上报（docs/23 D）：到"准备好了"用了多少秒，分档报进访问统计 load/<地点>/<m 手机 | d 电脑>[c 公共部分来自缓存]/<档>，
//   在 duami.goatcounter.com 里看国内真实情况。顺手把这次用到的文件告诉 SW 存起来
function reportLoad(where, name) {
  const sec = performance.now() / 1000, bucket = sec < 10 ? "<10" : sec < 30 ? "10-30" : sec < 60 ? "30-60" : sec < 120 ? "60-120" : ">120";
  const res = performance.getEntriesByType("resource").filter((r) => r.name.startsWith(location.origin + pub("")));
  const cached = res.some((r) => /kusuriuri_v2/.test(r.name) && r.transferSize === 0 && r.decodedBodySize > 0);
  stat(`load/${where}/${touch ? "m" : "d"}${cached ? "c" : ""}/${bucket}`, `加载 ${name} · ${touch ? "手机" : "电脑"}${cached ? "（缓存）" : ""} · ${bucket} 秒（${sec.toFixed(0)}）`, true);
  swReady.then((reg) => reg && navigator.serviceWorker.ready.then((r) => r.active?.postMessage({ warm: res.map((r) => r.name) }))).catch(() => {});
}

// 加载失败：失败页上写出错在哪（哪个文件），也报一条访问统计事件（duami.goatcounter.com 里看 err/<地点>），手机上出错好查
function failed(where, e) {
  console.error(e);
  const detail = [e?.message || String(e), lastFail && lastFail !== e?.message ? lastFail : ""].filter(Boolean).join(" · ").slice(0, 220);
  status.textContent = "加载失败：" + detail;
  stat(`err/${where}`, `加载失败 · ${detail}`.slice(0, 200), true);
  loading.fail(where === "map" ? "总地图没加载出来" : "场景没加载出来", detail);
}
if (!locId) showMap().catch((e) => failed("map", e)); else startLocation(locId).catch((e) => failed(locId, e));

// ---------------------------------------------------------------- 总地图（占位）
// 总地图上每个地点的进度（guide.js 存的；没去过就不写）：形真理 2 / 3 · 観 6 / 8 · 物怪 1 / 5，本命退了写"已退魔"
function progressOf(id) {
  const cs = loadCase(id); let zk = []; try { zk = JSON.parse(localStorage.getItem("mononoke_tour_zukan") || "[]"); } catch {}
  const mons = ROSTER[id] || [], got = mons.filter((m) => zk.includes(m)).length, views = cs.seen.filter((k) => k.includes("/view:")).length;
  if (!cs.seen.length && !got) return "";
  const parts = [];
  if (cs.done) parts.push("已退魔"); else if (cs.chars.length || cs.intro) parts.push(`形真理 ${cs.chars.length} / 3`);
  parts.push(`観 ${views}${cs.totals?.views ? ` / ${cs.totals.views}` : ""}`);
  if (mons.length) parts.push(`物怪 ${got} / ${mons.length}`);
  return `<span class="prog">${parts.map((x) => `<i>${x}</i>`).join("")}</span>`;   // 一项一行，小屏上不跟隔壁地点的字叠在一起
}
async function showMap() {
  document.body.classList.add("map-mode");
  mountSettings(document.getElementById("map"));
  audio.setScene("map");
  const { real, test } = locationIds();
  loading.start("map", "绘卷"); loading.step("展开长卷…");
  const map = await loadMap();
  const texts = await loadText();
  // 缘起卡（story_intro.js）：第一次来先翻几张讲故事，翻的时候后台先下药郎和小物件；左上「缘起」能再看
  const warmUrls = [PLAYER_MODEL, ...Object.values(PROPS).map((d) => d.url)];
  const playIntro = () => { stat("/缘起", "缘起卡"); try { storyIntro(texts, warmUrls); } catch (e) { console.warn("缘起卡", e); } };   // 出错也不挡总地图
  if ((!introSeen() || params.get("intro") === "1") && !params.has("selftest") && !params.has("auto")) playIntro();
  const replay = document.createElement("button"); replay.className = "intro-btn"; replay.textContent = "缘起"; replay.title = "再看一遍故事介绍";
  replay.addEventListener("click", (e) => { e.stopPropagation(); playIntro(); });
  document.getElementById("map")?.appendChild(replay);   // 11-07 用户：总地图不要标题，长卷占满全屏；「缘起」浮在左上角
  const scroll = document.querySelector("#map .scroll"), paper = document.querySelector("#map .paper-roll");
  if (map) {
    // 长卷：图按窗口高度缩放，热区按图的像素比例换成百分比，图换成重画版也不用改
    const [W, H] = map.size;
    paper.style.aspectRatio = `${W} / ${H}`;
    const img = paper.querySelector("img");
    // 回到总地图时停在上次进的地点（没进过就停最左边）
    const LAST = "mononoke_tour_lastloc";
    const goLast = () => { let id = null; try { id = localStorage.getItem(LAST); } catch {} const P = map.places.find((q) => q.id === id); if (!P) return;
      scroll.scrollLeft = paper.offsetLeft + (P.label[0] / W) * paper.offsetWidth - scroll.clientWidth / 2; };
    paper.addEventListener("click", (e) => { const a = e.target.closest?.(".spot.open, .tag-name.open"); const id = a?.dataset.loc; if (id) try { localStorage.setItem(LAST, id); } catch {} }, true);
    img.addEventListener("load", () => { loading.done(); reportLoad("map", "总地图"); // 图出来时窗口可能还没排版（宽度 0），等长卷真有宽度了再定位一次；用户自己拖过就不再动
      let userMoved = false; scroll.addEventListener("pointerdown", () => (userMoved = true), { once: true });
      const ro = new ResizeObserver(() => { if (userMoved || !paper.offsetWidth) return; goLast(); ro.disconnect(); }); ro.observe(paper); }, { once: true });
    img.addEventListener("error", () => loading.fail("长卷图片没加载出来"), { once: true });
    // 用 fetch 下长卷图再显示（直接设 src 的话加载提示数不到字节，进度条不动）
    fetch(asset(map.image)).then((r) => r.blob()).then((b) => (img.src = URL.createObjectURL(b))).catch(() => (img.src = asset(map.image)));
    for (const P of map.places) {
      const open = P.open && real.includes(P.id);
      const [x0, y0, x1, y1] = P.rect, pct = (v, t) => `${(v / t) * 100}%`;
      const el = document.createElement(open ? "a" : "div");
      el.className = "spot" + (open ? " open" : " locked"); el.dataset.loc = P.id;
      Object.assign(el.style, { left: pct(x0, W), top: pct(y0, H), width: pct(x1 - x0, W), height: pct(y1 - y0, H) });
      if (open) el.href = `?loc=${P.id}`;
      const intro = texts[`loc.${P.id}`]?.body;
      el.title = open ? `${P.name} · ${P.sub}${intro ? "\n" + intro : ""}` : `${P.name}（未开放）`;
      paper.appendChild(el);
      const tag = document.createElement("div");
      tag.className = "tag-name" + (open ? " open" : ""); tag.dataset.loc = P.id;
      Object.assign(tag.style, { left: pct(P.label[0], W), top: pct(P.label[1], H) });
      tag.innerHTML = `<span class="name">${P.name}</span><span class="sub">${P.sub}</span>${open ? progressOf(P.id) : '<span class="seal">未开放</span>'}`;
      if (open) { tag.addEventListener("click", () => (location.href = `?loc=${P.id}`)); el.addEventListener("mouseenter", () => tag.classList.add("hover")); el.addEventListener("mouseleave", () => tag.classList.remove("hover")); }
      paper.appendChild(tag);
    }
  }
  // 拖着看、滚轮横着走
  let drag = null;
  scroll.addEventListener("pointerdown", (e) => { if (e.pointerType !== "touch") drag = { x: e.clientX, s: scroll.scrollLeft, moved: false }; });   // 手指用浏览器自己的横滑
  addEventListener("pointermove", (e) => { if (!drag) return; const dx = e.clientX - drag.x; if (Math.abs(dx) > 5) drag.moved = true; scroll.scrollLeft = drag.s - dx; });
  addEventListener("pointerup", () => setTimeout(() => (drag = null)));
  scroll.addEventListener("click", (e) => { if (drag?.moved) { e.preventDefault(); e.stopPropagation(); } }, true);
  scroll.addEventListener("wheel", (e) => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { e.preventDefault(); scroll.scrollLeft += e.deltaY; } }, { passive: false });
  // 不在地图上的地点（测试、示例）列在右下角；发布的站点不显示
  const extra = import.meta.env.DEV ? [...real.filter((id) => !map?.places.some((P) => P.id === id)), ...test] : [];
  document.querySelector("#map .tests").innerHTML = extra.length ? "测试：" + extra.map((id) => `<a href="?loc=${id}">${id}</a>`).join(" · ") : "";
  status.textContent = "";
}

// ---------------------------------------------------------------- 地点
function preloadFiles(urls) {
  for (const href of new Set(urls)) {
    const l = document.createElement("link");
    l.rel = "preload"; l.as = "fetch"; l.crossOrigin = "anonymous"; l.href = href;   // as=fetch + crossorigin，GLTFLoader 的 fetch 才能直接拿这份
    document.head.appendChild(l);
  }
}
async function startLocation(id) {
  const loc = await loadLocation(id);
  // 积木材质整套换（笛小路家 "mat": "ink" 水墨，docs/22）；?mat=ink 能在别的地点试，?mat= 空着是原样。
  // 地点写了 "recolor": "color" 的，本命退过魔以后换成那套（记在本机，下次进来直接是彩色）
  if (params.get("recolor")) loc.recolor = params.get("recolor");   // 试上色：?mat=ink&recolor=color，控制台 __tour.recolor()
  if (params.get("sky")) loc.sky = params.get("sky");   // 调试：?sky=名字 先拿别的图看天空球（找 textures/kit/名字.jpg）
  const COLOR_KEY = `mononoke_tour_color_${loc.id}`;
  let colored = false; try { colored = !!loc.recolor && localStorage.getItem(COLOR_KEY) === "1"; } catch {}
  setKitMat(params.get("mat") ?? (colored ? loc.recolor : loc.mat) ?? null);
  loading.start(id, loc.name, loc.splats?.length ? 1 : 0, LITE && loc.splats?.[0]?.lite ? 3.5 : undefined);   // 只等进门那块泼溅 loading.step("搭场景…");
  const texts = await loadText();
  document.title = `${loc.name} · 怪化猫游览`;
  // 进门前的铺垫（loading.js prelude）：每个地点第一次进来时翻几页故事，读的时候后台下场景；?prelude=1 每次都看
  {
    const PRE_KEY = `mononoke_prelude_${id}`, pages = texts[`prelude.${id}`];
    let seen = false; try { seen = localStorage.getItem(PRE_KEY) === "1"; } catch {}
    if (Array.isArray(pages) && pages.length && (!seen || params.get("prelude") === "1") && params.get("prelude") !== "0" && !params.has("selftest") && !params.has("auto")) {
      loading.prelude(pages.map((p, i) => ({ ...p, img: pub(`textures/prelude/${id}_${i + 1}.jpg`) })), loc.name);
      try { localStorage.setItem(PRE_KEY, "1"); } catch {}
    }
  }

  const scene = new THREE.Scene();
  const bgColor = new THREE.Color(loc.background || "#2A2A4E");
  scene.background = bgColor;
  // 天空球：区块或地点写 "sky": "fue_sky" → textures/kit/fue_sky.jpg（2:1 等距柱状）；上过色换 fue_sky_color.jpg。
  //   图没到 / 加载失败就还是纯色底；背景不进描边通道（post.js 渲染法线时会先把 background 拿掉）
  // 11-06：天空图也算进"这间准备好了"（prepZone 先下、enterZone 等它），不再进门以后才从纯色底换成天
  const skyTex = new Map(); let skyWant = null;
  const skyFile = (z) => { const name = z && "sky" in z ? z.sky : loc.sky; return name ? `${name}${colored ? "_color" : ""}.jpg` : null; };   // 区块写 "sky": null 就关掉
  function loadSky(file) {
    if (!skyTex.has(file)) skyTex.set(file, new Promise((r) => new THREE.TextureLoader().load(pub(`textures/kit/${file}`), (t) => {
      t.mapping = THREE.EquirectangularReflectionMapping; t.colorSpace = THREE.SRGBColorSpace; r(t);
    }, undefined, () => r(null))));
    return skyTex.get(file);
  }
  function setSky(z) {
    bgColor.set(z?.background || loc.background || "#2A2A4E"); scene.background = bgColor;
    skyWant = skyFile(z);
    if (!skyWant) return Promise.resolve();
    const file = skyWant;
    return loadSky(file).then((t) => { if (t && skyWant === file) scene.background = t; });
  }
  const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 200);
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  // 手机显存不够时浏览器会把画面收回（context lost）：报一条统计，提示刷新
  renderer.domElement.addEventListener("webglcontextlost", (ev) => { ev.preventDefault(); stat(`err/${locId || "map"}`, "画面被浏览器收回（显存不够）", true); toast("画面出错了，刷新一下就好"); });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(innerWidth, innerHeight);
  document.getElementById("stage").appendChild(renderer.domElement);
  scene.add(new THREE.DirectionalLight(0xffffff, 1));
  const post = new PaperOutlinePost(renderer, scene, camera, { paper: "textures/paper.jpg" });
  post.maskLayer = 3;   // 拔剑妖化的描边变色只给药郎（player.js 给药郎开了第 3 图层），屋子的线不跟着变
  post.setAwakenColor("#C9A23A");   // 妖化描边用金色（10-31 用户："不要用红色的勾边，改成金色"）。canon 赭金 #DCC67C 太浅，压在浅色墙前看不清，往深调成金；探案版不设，还是深红
  post.setFlags({ outline: true, paper: true, letterbox: false });
  const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath(pub("draco/")));

  // ---- 泼溅（地点级，进地点时一次加载完，之后不再动）----
  // Spark 的坑：运行中改泼溅的 visible / opacity / position、加 SplatEdit，整个泼溅系统会掉成 0 个点（探案版试过）。
  // 所以几个泼溅区块共用一个坐标系、一起加载，换区块只换镜头规则和可走范围，不增删泼溅。
  // 条目格式和 cameras.json 的 layout.splats 一样：原始帧 y 向下、沿 +z；绕 X 转 180°，再绕 Y 转 yawDeg，缩放，平移 position
  // 11-05 懒加载：五块泼溅（每块 7 MB）原来一起下、全下完才让进，慢网上要等 36 MB。现在先只下进门那块，进去以后其余几块
  //   一块接一块在后台下（按出口顺序），走进还没下完的房间时在拉门里等那一块；没开始下的，点进去就插队先下它。
  //   泼溅是"加进场景以后不再改"，后加的几块只是晚一点 new，加进去以后同样不动它（Spark 怕的是改 visible / opacity / 加 SplatEdit）。
  const splats = [], splatOf = new Map();   // splatOf：区块 id → { S, mesh, ready }
  const firstZone = params.get("zone") || loc.start;
  let Spark = null;
  const zoneOfSplat = (S) => S.zone || S.name.replace(/_v\d+$/, "");
  function addSplat(e) {
    if (e.mesh) return e.ready;
    const S = e.S, m = new Spark.SplatMesh({ url: asset(`worldlabs/${S.name}/splat_${(LITE && S.lite) || S.quality || "500k"}.spz`) });
    const yaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(S.yawDeg || 0));
    m.quaternion.copy(yaw.multiply(new THREE.Quaternion(1, 0, 0, 0)));
    m.scale.setScalar(S.scale); m.position.set(...S.position);
    m.frustumCulled = false;   // Spark 算的包围盒不对，镜头一偏整块被剔掉
    scene.add(m); splats.push(m); post.exclude.push(m);
    e.mesh = m; e.ready = Promise.resolve(m.initialized).then(() => { e.done = true; loading.splatDone(); }, (err) => { e.done = true; console.warn("泼溅加载失败", S.name, err); });
    return e.ready;
  }
  if (loc.splats?.length) {
    Spark = await import("@sparkjsdev/spark");
    const spark = new Spark.SparkRenderer({ renderer }); scene.add(spark); post.spark = spark;
    for (const S of loc.splats) splatOf.set(zoneOfSplat(S), { S, mesh: null, ready: null, done: false });
    if (!splatOf.has(firstZone)) splatOf.set(firstZone, splatOf.get(zoneOfSplat(loc.splats[0])));
    addSplat(splatOf.get(firstZone));
  }
  // 后台一块接一块下其余泼溅（进门那块好了才开始，不跟它抢网速）
  async function splatQueue() {
    for (const e of new Set(splatOf.values())) { if (!e.mesh) await addSplat(e); }
  }

  // 11-05：药郎、三件随身道具、进门区块的积木和配角同时开始下（原来一个下完才下下一个，慢网上光排队就多好几秒）。
  //   这里只发 <link rel=preload>，真正读文件的还是下面的 loader，拿的是同一份，不会多下
  {
    const z0 = loc.zones?.[firstZone] || {};
    // 11-06 地铁首次 14 秒：站台 11 个配角（3.9 MB）跟药郎抢网速，药郎拖到 12 秒才下完。配角不再预载，进场以后在后台下（attachNpcs）
    preloadFiles([PLAYER_MODEL, ...Object.values(PROPS).map((d) => d.url), z0.kit && `processed/kit/${z0.kit}.glb`].filter(Boolean).map((u) => assetUrl(u)));
  }
  status.textContent = `${loc.name} · 加载药郎…`; loading.step("请药郎出场…");
  const P = await loadPlayer(loader, assetUrl, { springs: params.get("spring") !== "0", props: params.get("props") !== "0", layer: params.get("layer") !== "0" });
  const player = P.group; scene.add(player);
  const follow = new FollowCam(camera, loc.camera || {}); follow.renderer = renderer;
  const splatCam = new SplatCam(camera);
  let cam = follow;   // 积木区块用跟随镜头；camera.mode 是 circle / rail 的泼溅区块用 SplatCam
  const rain = createRain(); scene.add(rain.object); post.exclude.push(rain.object);   // 雨丝不描边
  const snow = createSnow(); scene.add(snow.object); post.exclude.push(snow.object);   // 雪片也不描边（笛小路家门前、雪庭）
  const stand = () => { player.position.y = col.floorY(player.position.x, player.position.z) ?? 0; };   // 泼溅可走图带地面高度，积木的全平

  // ---- 区块 ----
  let Z = null, world = null, col = null, pf = null, path = null, arriveLock = false, busy = false, busyBy = "";
  let baseFov = 50;   // 区块定的 fov（横屏），竖屏时 fitFov 在它基础上放大
  let shotFov = null;   // 拾遗特写时暂存的区块 fov
  // A paper seal marks the reachable endpoint while the click route is active.
  const destination = new THREE.Mesh(new THREE.RingGeometry(0.13, 0.18, 32), new THREE.MeshBasicMaterial({ color: 0xffebb7, side: THREE.DoubleSide, depthWrite: false }));
  destination.rotation.x = -Math.PI / 2;
  destination.visible = false;
  scene.add(destination);
  const tags = new Tags((tid) => onTag(tid));
  const zoneCache = new Map(), npcCache = new Map(), findCache = new Map();   // findCache：拾遗小物件（guide.js，场景线的 find_*.glb）
  let npcsOn = [], findsOn = null;
  // 区块的积木（连贴图）和配角下好、建好，放进 zoneCache / npcCache；同一区块只下一次。
  // 11-05 用户："会卡在这里（换区块的拉门），然后等很久才进"：原来走到门口才开始下下一间，现在进一间以后就在后台把隔壁几间先下好（prefetchNext）
  const prepping = new Map();
  function prepZone(zoneId) {
    if (prepping.has(zoneId)) return prepping.get(zoneId);
    const z = loc.zones?.[zoneId] || {};
    const job = Promise.all([
      skyFile(z) && loadSky(skyFile(z)),   // 这间的天空图（没有就跳过）
      z.kit && !zoneCache.has(zoneId) && loadKit(loader, assetUrl(`processed/kit/${z.kit}.glb`)).then((g) => {
        g.traverse((o) => { if (o.isMesh && o.material.uniforms?.uCutout) o.material.uniforms.uCutout.value = 1; });   // 积木参与遮挡淡出
        if (z.offset) g.position.set(...z.offset);
        // 11-06 用户："进去之后还有很多装饰性的图都没有及时放上去"：贴图也下完才算这间好了（最多等 40 秒，网太慢就先进去）
        return kitReady(g, 40000).then(() => zoneCache.set(zoneId, g));
      }),
      // 配角不在这里下：等这间的积木和贴图到齐再下（attachNpcs / prefetchNext），不跟它们抢网速
      z.finds?.some((f) => f.kit) && !findCache.has(zoneId) && Promise.all(z.finds.filter((f) => f.kit).map((f) => loadKit(loader, assetUrl(`processed/kit/${f.kit}.glb`)).then((g) => { g.userData.find = f; return g; }).catch(() => null)))
        .then((list) => { const grp = new THREE.Group(); list.filter(Boolean).forEach((g) => grp.add(g)); findCache.set(zoneId, grp); }),
    ]).catch((e) => { prepping.delete(zoneId); throw e; });   // 失败了下次进门再试
    prepping.set(zoneId, job);
    return job;
  }
  // 配角：一间只下一次；网慢时不挡进门，下好再摆上（11-06 改，原来进门要等配角全下完、最多 6 秒，超时就不摆了）
  const npcJobs = new Map();
  function prepNpcs(zoneId) {
    if (npcJobs.has(zoneId)) return npcJobs.get(zoneId);
    const z = loc.zones?.[zoneId] || {};
    const job = !z.npcs?.length ? Promise.resolve([]) : Promise.all(z.npcs.map(async (d) => {
        // 模型还没做出来或网太慢：最多等 60 秒，不摆这一个
        const n = await Promise.race([loadNpc(loader, assetUrl, d), new Promise((_, no) => setTimeout(() => no(new Error("超时")), 60000))]).catch((e) => { console.warn("配角加载失败", d.model, e); return null; });
        if (n) {
          n.group.position.set(d.pos[0], 0, d.pos[1]); n.group.rotation.y = d.yaw || 0; n.pos = [...d.pos]; n.home = { pos: [...d.pos], yaw: d.yaw || 0 }; n.id = d.id; n.height = d.height; n.y = d.y || 0;   // y：坐在高台这类不算地面的东西上，比地面高多少（笛小路家瑠璃姫）
          if (d.patrol?.length) n.patrol = { pts: [d.pos, ...d.patrol], i: 0, dir: 1, speed: d.speed ?? 0.7, pause: d.pause ?? 3, hold: 0, yield: 0 };
        }
        return n;
      }));
    job.then((list) => npcCache.set(zoneId, list));
    npcJobs.set(zoneId, job);
    return job;
  }
  function placeNpcs(zoneId) {
    for (const n of npcsOn) scene.remove(n.group);
    npcsOn = colored ? [] : (npcCache.get(zoneId) || []).filter(Boolean);   // 上过色的地点（笛小路家）人都散了：原作里宅里的人早就死了，点香以后散去
    for (const n of npcsOn) { scene.add(n.group); n.group.position.y = (col.floorY(n.pos[0], n.pos[1]) ?? 0) + (n.y || 0); }
  }
  async function attachNpcs(zoneId) {
    if (!npcCache.has(zoneId)) await Promise.race([prepNpcs(zoneId), new Promise((r) => setTimeout(r, 1200))]);   // 本机 / 快网：进门时就摆好；慢网最多多等 1.2 秒
    if (npcCache.has(zoneId)) { placeNpcs(zoneId); return; }
    prepNpcs(zoneId).then(() => { if (Z?.id === zoneId) placeNpcs(zoneId); });
  }
  // 后台按出口顺序一间一间先下隔壁（不并发，免得跟眼前要用的抢网速）；出错不管，进门时 prepZone 会再试
  let prefetchChain = Promise.resolve();
  function prefetchNext(zoneId) {
    for (const e of loc.zones?.[zoneId]?.exits || []) prefetchChain = prefetchChain.then(() => prepZone(e.to)).then(() => prepNpcs(e.to)).catch(() => {});
  }
  async function enterZone(zoneId, arrive = null) {
    const sp = splatOf.get(zoneId);
    if (sp && !sp.done) await Promise.race([addSplat(sp), new Promise((r) => setTimeout(r, 120000))]);   // 这间的泼溅还没下完：在拉门里等它（没开始下的先插队）；最多等 2 分钟，网太慢就先让人进去
    const [z] = await Promise.all([resolveZone(loc, zoneId), prepZone(zoneId)]);
    enc.reset();   // 换区块：物怪直接收掉
    if (world) scene.remove(world);
    world = null;
    if (z.kit) { world = zoneCache.get(zoneId); scene.add(world); }
    // 配角站桩：区块的 npcs 列表（格式见 14 第三节），换区块时摘掉上一个区块的；药郎绕着走（挡住半径 0.45 米）
    for (const n of npcsOn) scene.remove(n.group);
    npcsOn = [];
    Z = z; col = createCollision(z.walk);
    if (z.npcs?.length) {   // 药郎绕着配角走；配角晚到也算（npcsOn 是活的）
      const base = col.canStand;
      col.canStand = (x, zz) => base(x, zz) && npcsOn.every((n) => (n.pos[0] - x) ** 2 + (n.pos[1] - zz) ** 2 > 0.45 * 0.45);
    }
    await attachNpcs(zoneId);
    if (findsOn) scene.remove(findsOn);
    findsOn = findCache.get(zoneId) || null;
    if (findsOn) { scene.add(findsOn); for (const g of findsOn.children) { const f = g.userData.find; g.position.set(f.pos[0], (col.floorY(f.pos[0], f.pos[1]) ?? 0) + (f.y || 0), f.pos[1]); g.rotation.y = f.yaw || 0; } }
    pf = createPathfinder(z.walk, col.canStand); path = null;
    let yaw = z.spawnYaw ?? 0, camYaw;
    if (!arrive && !z.spawn && z.stairs.length) arrive = { stair: 0 };
    if (arrive) {
      // 从楼梯口进来：站在门前往里走 0.6 米，背对门，镜头在门那边
      const s = z.stairs[arrive.stair], [fx, fz] = s.face;
      player.position.set(s.stand[0] - fx * 0.6, 0, s.stand[1] - fz * 0.6);
      yaw = Math.atan2(-fx, -fz); camYaw = Math.atan2(fx, fz);
      arriveLock = true; arriveT = 0;   // 先离开门口（或者转身朝门走），再回去才算要走
    } else {
      const c = z.spawn || [z.walk.x0 + z.walk.w * z.walk.cell / 2, z.walk.z0 + z.walk.h * z.walk.cell / 2];   // 都没有就站中间
      player.position.set(c[0], 0, c[1]);
      camYaw = yaw + Math.PI;
    }
    const near = col.nearestStand(player.position.x, player.position.z, 3); if (near) player.position.set(near.x, 0, near.z);
    player.rotation.y = yaw; stand();
    baseFov = z.camera?.fov ?? loc.camera?.fov ?? 50; camera.fov = baseFov; camera.updateProjectionMatrix();
    if (["circle", "rail"].includes(z.camera?.mode)) {
      cam = splatCam;
      cam.setZone({ canStand: col.canStand, yaw: camYaw, camera: z.camera });
      cam.updateCutout();
    } else {
      cam = follow;
      const W = z.walk, bounds = W ? [W.x0, W.z0, W.x0 + W.w * W.cell, W.z0 + W.h * W.cell] : null;
      cam.setZone({ canStand: col.canStand, ceiling: z.height, yaw: camYaw, bounds, collider: world ? buildCollider(world) : null, fixed: z.camera?.fixed || null });
      cam.dist = z.camera?.dist ?? loc.camera?.dist ?? 3.2;
      cam.pitch = z.camera?.pitch ?? loc.camera?.pitch ?? 0.2;
    }
    fitFov();
    cam.update(player, 0, true);
    tags.clear();
    for (const [n, p] of Object.entries(z.views)) tags.add(`view:${n}`, "view", "観", [p[0], (col.floorY(...p) ?? 0) + 1.7, p[1]], viewText(n).title);
    (z.exits || []).forEach((e, i) => { const s = z.stairs[e.stair]; // 双扇门各有一个通行格，共用一个路标；两边的实际门口仍然可以走。
      const sameDoor = s && z.exits.slice(0, i).some((prev) => {
        const other = z.stairs[prev.stair];
        return other && prev.to === e.to && prev.label === e.label && Math.hypot(s.door[0] - other.door[0], s.door[1] - other.door[1]) < 1.1;
      });
      if (s && !sameDoor) tags.add(`exit:${i}`, "exit", e.label || "出口", [s.door[0], 2.1, s.door[1]]); });
    // 天气：雨夜区块开雨丝，画面往藏青压一点；区块可以单独写 background
    const wet = z.weather === "rain";
    rain.set(wet); post.setTint(wet ? "#8C8CC8" : "#ffffff", wet ? 0.45 : 0);
    snow.set(z.weather === "snow" && !colored);   // 上过色就是春天了，雪停
    await Promise.race([setSky(z), new Promise((r) => setTimeout(r, 30000))]);
    status.textContent = `${loc.name} · ${z.name || zoneId}`;
    audio.setScene(loc.id, zoneId); floorSnd = audio.floorOf(loc.id, zoneId);
    stat(`/${loc.id}/${zoneId}`, `${loc.name} · ${z.name || zoneId}`);
    guide?.enterZone();   // 引导（guide.js）：门札、拾遗、本命
  }

  function setShot(c) {
    for (const k of [follow, splatCam]) k.shot = c ? { ...c, shot: true } : null;
    if (c?.fov) { shotFov ??= baseFov; baseFov = c.fov; fitFov(); }
    else if (!c && shotFov != null) { baseFov = shotFov; shotFov = null; fitFov(); }
  }

  function viewText(n) {
    const key = `${Z.textKey}.${n}`;
    const t = texts[key] || Z.texts?.[n] || {};
    return { place: `${loc.name} · ${Z.name || Z.id}`, title: t.title || `观景点 ${key}`, body: t.body || "（说明卡待写：文案线 text.json）" };
  }
  async function openView(n) {
    if (busy || enc.active) return;   // 物怪出没时不开说明卡
    stat(`说明卡/${Z.textKey}.${n}`, `说明卡 · ${viewText(n).title}`, true);
    busy = true; busyBy = `view:${n}`; path = null; pose = null;
    const p = Z.views[n]; player.rotation.y = Math.atan2(p[0] - player.position.x, p[1] - player.position.z) || player.rotation.y;
    P.play(Z.viewLook?.[n] === "up" ? "look" : "gaze", 0.4);   // 驻足看；高处的观景点（区块里写 viewLook: { "1": "up" }）抬头看
    prompt.set("");
    audio.play("bell");
    const shot = Z.camera?.fixed?.find((s) => String(s._view) === String(n) && s.look);
    if (shot) setShot({ ...shot, close: true });
    try { await card.open(viewText(n)); }
    finally { if (shot) setShot(null); }
    audio.play("paper");
    guide.onView(n);
    P.play("idle", 0.4); stillT = 0;
    busy = false;
  }
  async function takeExit(i) {
    const e = Z.exits[i]; if (!e || busy) return;
    busy = true; busyBy = `exit:${i}`; path = null; P.play("idle"); prompt.set("");
    audio.play("hyoshigi"); audio.play("slide");
    const wipeEl = document.getElementById("wipe");
    await fusumaWipe(async () => {
      const t = setTimeout(() => wipeEl.classList.add("wait"), 500);   // 隔壁还没下完：拉门上写一句，不让人以为卡死了
      try { await enterZone(e.to, { stair: e.arrive ?? 0 }); } catch (err) { console.error("换区块出错", err); } finally { clearTimeout(t); wipeEl.classList.remove("wait"); }
    }).finally(() => { busy = false; });   // 出错也要放开，不然人卡在原地走不动、门也不认
    prefetchNext(e.to);
  }
  function walkTo(x, z, then = null, tol = 0.3, label = "") {
    path = null;
    if (Z.npcs?.length) pf.invalidate();   // 配角可能刚加载进来，或巡到了新的位置
    const r = pf.routeTo([player.position.x, player.position.z], [x, z], tol);
    if (!r) { toast("过不去"); return; }
    const pts = r.pts.slice(1);
    if (!pts.length) { path = null; then && then(); return; }   // 点在药郎脚下：原来会留一条空路线，每帧报错把画面卡住（10-31 镜头诊断撞出来的）
    path = { pts, then, label, stalled: 0 };
    const [gx, gz] = pts.at(-1);
    destination.position.set(gx, (col.floorY(gx, gz) ?? 0) + 0.025, gz);
  }
  function onTag(tid) {
    if (busy || card.isOpen || guide.acting || guide.endOpen || enc.active || box?.isOpen) return;
    const [kind, n] = tid.split(":");
    if (kind === "view") { const p = Z.views[n]; walkTo(p[0], p[1], () => openView(n), 0.3, viewText(n).title); }
    if (kind === "find") {
      const f = Z.finds?.find((item) => String(item.id) === n);
      if (f) walkTo(...f.pos, () => guide.pickFind(f), 0.8, "拾遗");
    }
    // 出口：走到 stand 正上方（容差 0.1），保证进触发圈；原来 0.3 的容差会停在圈边上，触不触发看运气（场景线 10-29 查出来的）
    if (kind === "exit") { const s = Z.stairs[Z.exits[+n].stair]; arriveLock = false; walkTo(s.stand[0], s.stand[1], () => takeExit(+n), 0.1, Z.exits[+n].label); }
  }

  // ---- 输入 ----
  const keys = new Set();
  function act(code) {
    if (loading.holding) return;   // 铺垫页还开着：键盘留给翻页
    if (box?.key(code)) return;   // 药箱开着：方向键换格、Esc / I 关，别的键不管
    if (guide.endKey(code)) return;   // 结案卡开着（guide.js，11-06）：E 接着逛、N 去下一处
    if (enc.tutKey(code)) return;   // 物怪出没教学卡开着：翻页 / 跳过，别的键不管
    if (code === "KeyX" || (code === "Escape" && sword)) { if (!sword && enc.act("sword")) return; drawSword(); return; }   // 物怪出没时：形真理齐了才拔得出（encounter.js）
    if (code === "KeyI") { openBox(); return; }
    if (code === "KeyJ") { enc.act("throw"); return; }
    if (code === "KeyK") { enc.act("jump"); return; }   // 跳、瞬移只在物怪出没时有
    if (code === "KeyL") { enc.act("blink"); return; }
    if (code === "Space" && enc.active && !card.isOpen) { enc.act("dodge"); return; }
    if (code === "KeyE" || code === "Escape" || code === "Space") {
      if (card.isOpen) { card.close(); return; }
      if (code === "KeyE") { const v = nearView(); if (v) openView(v); else if (!busy && !enc.active && guide.act()) {} else if (touch) toast("走到観旁边再看"); }   // 没有観在旁边：问配角、捡拾遗（guide.js）
    }
    if (code === "KeyP") photo();
    if (code === "KeyF") setFilter(filterIdx + 1);
    if (code === "KeyO" && !busy && !card.isOpen) cyclePose();
    if (code === "KeyT" && !busy && !card.isOpen && !enc.active && !sword) guide.castScales();   // 放天秤指路（guide.js，11-06）
    if (code === "KeyM") location.href = pub("tour.html");
  }
  addEventListener("keydown", (e) => {
    if (e.code === "Space" && enc.active) e.preventDefault();
    if (e.code === "Tab" && box?.isOpen) e.preventDefault();   // 药箱里 Tab 翻案卷，不让浏览器跳焦点
    keys.add(e.code); act(e.code);
    if (/^(Arrow|Key[WASD])/.test(e.code)) path = null;
  });
  // 手机按钮栏：data-k 就是对应的键
  document.getElementById("prompt").addEventListener("click", () => act("KeyE"));   // 手机上提示条本身能点（只有 body.touch 时接收点击）
  // 手机摇杆（11-03）：左下区域按下的地方当摇杆中心，拖出去的方向 = 相对镜头的方向，推满 50 像素算推到底。
  // 只点一下没拖（< 10 像素、< 0.3 秒）当成点地面走，和右半屏一样
  const stick = { x: 0, y: 0, id: null };
  const stickEl = document.getElementById("stick"), stickBase = stickEl.querySelector(".base"), stickKnob = stickEl.querySelector(".knob");
  const STICK_R = 50;
  stickEl.addEventListener("pointerdown", (e) => {
    if (stick.id !== null) return;
    stick.id = e.pointerId; stick.cx = e.clientX; stick.cy = e.clientY; stick.t0 = performance.now(); stick.moved = false;
    stickEl.setPointerCapture(e.pointerId); stickEl.classList.add("on");
    Object.assign(stickBase.style, { left: `${e.clientX - 60}px`, top: `${e.clientY - 60}px`, bottom: "auto" });
  });
  stickEl.addEventListener("pointermove", (e) => {
    if (e.pointerId !== stick.id) return;
    let dx = e.clientX - stick.cx, dy = e.clientY - stick.cy; const d = Math.hypot(dx, dy);
    if (d > 10) stick.moved = true;
    if (d > STICK_R) { dx *= STICK_R / d; dy *= STICK_R / d; }
    stickKnob.style.transform = `translate(${dx}px, ${dy}px)`;
    stick.x = dx / STICK_R; stick.y = -dy / STICK_R;
    if (stick.moved) path = null;
  });
  const stickEnd = (e) => {
    if (e.pointerId !== stick.id) return;
    if (e.type === "pointerup" && !stick.moved && performance.now() - stick.t0 < 300 && !busy && !card.isOpen && !guide.endOpen) clickFloor(e.clientX, e.clientY);
    stick.id = null; stick.x = stick.y = 0; stickKnob.style.transform = ""; stickEl.classList.remove("on");
    Object.assign(stickBase.style, { left: "", top: "", bottom: "" });
  };
  stickEl.addEventListener("pointerup", stickEnd); stickEl.addEventListener("pointercancel", stickEnd);
  // 视角摇杆（只在手机上出现，tour.html 的 #look）：推的方向和幅度 → 每帧转镜头的速度，左右最快 2.4 弧度/秒、上下 1.2 弧度/秒，松手停
  const look = { x: 0, y: 0, id: null }, LOOK_R = 46;
  const lookEl = document.getElementById("look"), lookKnob = lookEl.querySelector(".knob");
  lookEl.addEventListener("pointerdown", (e) => {
    if (look.id !== null) return;
    e.stopPropagation(); look.id = e.pointerId; lookEl.setPointerCapture(e.pointerId); lookEl.classList.add("on");
    const r = lookEl.getBoundingClientRect(); look.cx = r.left + r.width / 2; look.cy = r.top + r.height / 2; lookMove(e);
  });
  function lookMove(e) {
    if (e.pointerId !== look.id) return;
    let dx = e.clientX - look.cx, dy = e.clientY - look.cy; const d = Math.hypot(dx, dy);
    if (d > LOOK_R) { dx *= LOOK_R / d; dy *= LOOK_R / d; }
    lookKnob.style.transform = `translate(${dx}px, ${dy}px)`;
    const k = Math.max(0, Math.min(1, (d - 6) / (LOOK_R - 6))) / (d || 1);   // 中间 6 像素是死区，手指放上去不动不转
    look.x = dx * k; look.y = dy * k;
  }
  lookEl.addEventListener("pointermove", lookMove);
  const lookEnd = (e) => { if (e.pointerId !== look.id) return; look.id = null; look.x = look.y = 0; lookKnob.style.transform = ""; lookEl.classList.remove("on"); };
  lookEl.addEventListener("pointerup", lookEnd); lookEl.addEventListener("pointercancel", lookEnd);
  document.querySelectorAll("#pad [data-k]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); act(b.dataset.k); }));
  addEventListener("keyup", (e) => keys.delete(e.code));
  document.getElementById("card").addEventListener("click", () => card.close());
  const canvas = renderer.domElement;
  // 手指：一指拖转镜头、点地面走（连点两下快走），两指捏合拉远拉近；鼠标照旧。两指放开以后这一下不算点
  let drag = null, pinch = null, lastTap = null;
  const fingers = new Map();
  const spread = () => { const [a, b] = [...fingers.values()]; return Math.hypot(a.x - b.x, a.y - b.y); };
  canvas.addEventListener("pointerdown", (e) => {
    fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (fingers.size === 2) { pinch = spread(); drag = null; return; }
    if (fingers.size === 1) drag = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false, touch: e.pointerType === "touch" };
  });
  // 拖动只认按下画布的那根手指（11-06 用户反馈手机上视角频繁切换、晃得头晕）：原来不分手指，
  // 左手推摇杆、右手搭在画面上时，摇杆那根手指每动一下都按两指之间几百像素的距离转镜头，推 50 像素镜头转了 122°
  addEventListener("pointermove", (e) => {
    if (fingers.has(e.pointerId)) fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch && fingers.size === 2) { const d = spread(); if (d > 10) { cam.zoomBy(pinch / d); pinch = d; } return; }
    if (!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) > (drag.touch ? 10 : 6)) drag.moved = true;
    if (drag.moved) { const k = drag.touch ? 1.4 : 1; cam.turn(dx * 0.005 * k, dy * 0.004 * k); drag.x = e.clientX; drag.y = e.clientY; }
  });
  const lift = (e) => {
    fingers.delete(e.pointerId);
    if (fingers.size < 2) pinch = null;
    if (drag && e.pointerId !== drag.id) return;   // 摇杆、按钮那根手指松开：不打断画布上的拖动，也不当成点地面
    if (e.type === "pointerup" && drag && !drag.moved && !busy && !card.isOpen && !guide.endOpen) {
      const now = performance.now(), dbl = lastTap && now - lastTap.t < 350 && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 40;
      lastTap = dbl ? null : { t: now, x: e.clientX, y: e.clientY };
      clickFloor(e.clientX, e.clientY, dbl);
    }
    drag = null;
  };
  addEventListener("pointerup", lift); addEventListener("pointercancel", lift);
  canvas.addEventListener("wheel", (e) => { e.preventDefault(); cam.zoomBy(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
  const ray = new THREE.Raycaster(), floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
  function clickFloor(x, y, fast = false) {
    ray.setFromCamera(new THREE.Vector2((x / innerWidth) * 2 - 1, -(y / innerHeight) * 2 + 1), camera);
    if (!ray.ray.intersectPlane(floor, hit)) return;
    const s = pf.snapPoint(hit.x, hit.z, 0.8);
    if (!s) { path = null; toast("过不去"); return; }
    arriveLock = false; walkTo(s[0], s[1]);
    if (path) path.fast = fast;   // 连点两下：快走过去
  }

  // ---- 每帧 ----
  function nearView() {
    let best = null, bd = 1.1;
    for (const [n, p] of Object.entries(Z.views)) { const d = Math.hypot(p[0] - player.position.x, p[1] - player.position.z); if (d < bd) { bd = d; best = n; } }
    // 11-05：観已经看过、旁边又有能做的事 / 拾遗 / 配角（大奥空房的壁橱就挨着観）：E 先给那样，不再一直开同一张卡
    if (best && guide?.state.seen.includes(`${Z.id}/view:${best}`) && guide.nearOther()) return null;
    return best;
  }
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  // 转身：先快后慢地收过去（剩下的角度每秒收掉约 99.9%，最快 rate 弧度/秒、最慢 1 弧度/秒），不再匀速一下拧过去；
  // 要去的朝向同时告诉药郎，头先看过去（walk_layer.js）。10-31 以前是匀速 12 弧度/秒，180° 转身 0.26 秒，看着像机器
  function turnToward(yaw, rate, dt) {
    if (params.get("turn") === "old") { const d = wrap(yaw - player.rotation.y); player.rotation.y = wrap(player.rotation.y + Math.sign(d) * Math.min(Math.abs(d), rate * dt)); return; }   // 对比用：10-31 以前的匀速转身
    const d = wrap(yaw - player.rotation.y), step = Math.min(Math.abs(d), Math.min(rate * dt, Math.max(Math.abs(d) * (1 - Math.exp(-7 * dt)), dt)));
    player.rotation.y = wrap(player.rotation.y + Math.sign(d) * step); P.setFacing?.(yaw);
  }
  let curSpeed = 0, shiftT = 0;   // 当前移动速度（米/秒）、Shift 按住多久
  // 按住方向键时镜头切了（进出固定机位、轨道换侧），"前"还按切之前的画面算，直到换键或松开；
  // 不然一切镜头"前"就变了，药郎被带回原来的范围，镜头又切回去，来回闪（10-31）
  let moveLock = null;
  function move(dt) {
    if (busy || card.isOpen || enc.holding || box?.isOpen || guide.endOpen) return;   // 结案卡开着也不走；察觉、投札、闪避、袖挡的时候、药箱开着时脚下不走
    const k = (a, b) => keys.has(a) || keys.has(b);
    const sm = Math.min(1, Math.hypot(stick.x, stick.y)), stickOn = sm > 0.15;   // 手机摇杆推了多少（0~1）
    const sig = ["KeyW", "ArrowUp", "KeyS", "ArrowDown", "KeyA", "ArrowLeft", "KeyD", "ArrowRight"].filter((c) => keys.has(c)).join() + (stickOn ? "|stick" : "");
    if (!sig || !moveLock || moveLock.sig !== sig || moveLock.cam !== cam) moveLock = sig ? { sig, cam, cuts: cam.cuts, f: cam.forward.clone() } : null;
    else if (moveLock.cuts === cam.cuts) moveLock.f.copy(cam.forward);   // 没切镜头：照常跟着镜头（边走边拖镜头会转弯）
    const f = moveLock ? moveLock.f : cam.forward, r = new THREE.Vector3(-f.z, 0, f.x);
    const v = new THREE.Vector3();
    if (k("KeyW", "ArrowUp")) v.add(f); if (k("KeyS", "ArrowDown")) v.sub(f);
    if (k("KeyD", "ArrowRight")) v.add(r); if (k("KeyA", "ArrowLeft")) v.sub(r);
    if (stickOn) v.addScaledVector(f, stick.y).addScaledVector(r, stick.x);
    // 走 1.0 米/秒；按住 Shift 快走 1.8 米/秒，按住超过 1 秒加速成跑 2.85 米/秒（run_k，10-31 角色线做的，第二版实测 2.833）。
    // 速度慢慢加上去（每秒最多加 2.5 米/秒），换步态按当前速度，不是一按就跳；播放倍率按实际速度算，脚不打滑。松开往下减得快
    const fast = keys.has("ShiftLeft") || keys.has("ShiftRight") || !!path?.fast || sm > 0.92;   // 摇杆推到底 = 按住 Shift
    shiftT = fast ? shiftT + dt : 0;
    const want = fast ? (shiftT > 1 ? 2.85 : 1.8) : 1.0;
    curSpeed = Math.max(curSpeed, 0.6);
    curSpeed += THREE.MathUtils.clamp(want - curSpeed, -6 * dt, 2.5 * dt);
    const mps = curSpeed, gait = mps > 2.55 ? "sprint" : mps > 1.3 ? "run" : "walk", speed = mps * dt;   // 跑 run_k 本身 2.833 米/秒，切过去那一刻倍率 0.9，再低就像慢动作
    if (!v.lengthSq() && path) {
      const [tx, tz] = path.pts[0];
      const dx = tx - player.position.x, dz = tz - player.position.z, d = Math.hypot(dx, dz);
      if (d < 0.06) { path.pts.shift(); if (!path.pts.length) { const t = path.then; path = null; P.play("idle"); stillT = 0; t && t(); } return; }
      v.set(dx / d, 0, dz / d);
      if (d < speed) { player.position.x = tx; player.position.z = tz; stand(); turnToward(Math.atan2(dx, dz), 12, dt); P.play(gait); P.setMoveSpeed(mps); return; }
    }
    if (!v.lengthSq()) { curSpeed = 0; idleTick(dt); return; }
    pose = null; stillT = 0;
    v.normalize();
    turnToward(Math.atan2(v.x, v.z), 12, dt);
    const nx = player.position.x + v.x * speed, nz = player.position.z + v.z * speed;
    const ox = player.position.x, oz = player.position.z;
    if (col.canStand(nx, player.position.z)) player.position.x = nx;
    if (col.canStand(player.position.x, nz)) player.position.z = nz;
    if (path) {
      path.stalled = Math.hypot(player.position.x - ox, player.position.z - oz) < speed * 0.05 ? path.stalled + dt : 0;
      if (path.stalled > 0.65) { path = null; toast("过不去"); }
    }
    stand();
    P.play(gait); P.setMoveSpeed(mps);
  }
  // 配角：巡逻的沿折线来回走（到头停 pause 秒，药郎靠近 1.1 米就停下转身看他）；站桩的偶尔换姿势（player.js 的 idles）。
  // 挡路用的 n.pos 跟着走，药郎的碰撞每帧读它，所以两人不会穿过去
  function npcTick(n, dt) {
    const P2 = n.patrol;
    if (!P2) { n.update(dt, "idle"); return; }
    const gp = n.group.position, dPlayer = Math.hypot(player.position.x - gp.x, player.position.z - gp.z);
    if (dPlayer < 1.1) P2.yield = 2;
    if (P2.yield > 0) {
      P2.yield -= dt;
      const want = Math.atan2(player.position.x - gp.x, player.position.z - gp.z), d = wrap(want - n.group.rotation.y);
      n.group.rotation.y += Math.sign(d) * Math.min(Math.abs(d), 4 * dt);
      n.update(dt, "idle"); return;
    }
    if (P2.hold > 0) { P2.hold -= dt; n.update(dt, "idle"); return; }
    const tgt = P2.pts[P2.i + P2.dir] ? P2.pts[P2.i + P2.dir] : null;
    if (!tgt) { P2.dir *= -1; P2.hold = P2.pause; n.update(dt, "idle"); return; }
    const dx = tgt[0] - gp.x, dz = tgt[1] - gp.z, dist = Math.hypot(dx, dz), step = P2.speed * dt;
    if (dist <= step) { gp.x = tgt[0]; gp.z = tgt[1]; P2.i += P2.dir; if (!P2.pts[P2.i + P2.dir]) { P2.dir *= -1; P2.hold = P2.pause; } }
    else { gp.x += dx / dist * step; gp.z += dz / dist * step; }
    const d = wrap(Math.atan2(dx, dz) - n.group.rotation.y);
    n.group.rotation.y += Math.sign(d) * Math.min(Math.abs(d), 5 * dt);
    gp.y = col.floorY(gp.x, gp.z) ?? 0;
    n.pos[0] = gp.x; n.pos[1] = gp.z;
    n.update(dt, "walk");
  }
  // 站着：拍照姿势保持；站久了（15 秒）偶尔抱臂一下（idle_alt，一次性，播完回待机），之后冷却 30 秒
  let pose = null, stillT = 0;
  function idleTick(dt) {
    if (pose) return;
    stillT += dt;
    if (stillT > 15 && P.currentName === "idle_k") { P.play("idle_alt", 0.4); stillT = -30; return; }
    if (P.currentName !== "idle2_k") P.play("idle");
  }
  // 拍照姿势：O 依次切 抱臂 → 回头 → 不摆。回头要背对镜头站（朝镜头看的方向），药郎从左肩上回望
  const POSES = [null, ["photo_fold", "抱臂"], ["photo_back", "回头"]];
  function cyclePose() {
    const i = (POSES.findIndex((p) => (p ? p[0] : null) === pose) + 1) % POSES.length;
    path = null; pose = POSES[i] ? POSES[i][0] : null;
    if (pose === "photo_back") { const f = cam.forward; player.rotation.y = Math.atan2(f.x, f.z); }
    P.play(pose || "idle", 0.3); P.resetSprings(); stillT = 0;
    audio.play("tick");
    toast(pose ? `姿势：${POSES[i][1]}（${touch ? "" : "O 切换，"}走动就取消）` : "姿势：不摆");
  }
  // 拔剑（10-31 加进游览版）：探案版结局的退魔三拍 exorcise_k，X 键 / 手机"拔剑"钮。约 10 秒：
  // 1.25 秒抽剑，3.08 秒妖化（描边变金、换表情）到 8.21 秒，5.1 秒横斩，7.9 秒收剑；剑只在这段里出现（data/props.json）。
  // 药郎先转向镜头；播的时候不能走（busy），镜头照常拖，可以拍照；再按 X 或 Esc 收手
  // 物怪出没（encounter.js）用 opts：face 转向物怪；short 第二次以后的 3 秒短版（不带运镜）；onSlash 横斩那一下（物怪化墨）；onEnd(砍到没有)。
  // 短版：角色线的 exorcise_short_k 到了就播它（出手帧在 EXO_SHORT，到了按 17 里写的改）；没到先拿 exorcise_k 从 4.3 秒（已经妖化、横斩前）1.6 倍速播
  const AWAKEN = { from: 3.08, to: 8.21, fade: 0.15 }, SLASH = 5.1;
  const EXO_SHORT = { unsheathe: 0.42, slash: 1.67, sheath: 2.4, awaken: [0.75, 2.58] }, EXO_FALLBACK = { from: 4.3, speed: 1.6 };   // 短版节奏点：角色线 17 第十五节
  let sword = false, swordTimers = [], swordFace = 0, swordOpts = {}, swordT = 0, swordSlashed = false, swordAwoke = false;
  const awakenMix = (t, A = AWAKEN) => Math.max(0, Math.min(1, (t - (A.from - A.fade)) / A.fade, ((A.to + A.fade) - t) / A.fade));
  function drawSword(opts = {}) {
    if (sword) { endSword(); return; }
    if (busy || card.isOpen) return;
    stat("拔剑", `拔剑 · ${loc.name}`, true);
    sword = true; busy = true; path = null; pose = null; stillT = 0; prompt.set(""); swordOpts = opts; swordT = 0; swordSlashed = false; swordAwoke = false;
    const f = cam.forward; swordFace = opts.face ?? Math.atan2(-f.x, -f.z);   // 转向镜头：平滑转过去（一下拧 180° 下摆弹簧骨甩开，像白布摊了一地，翻车集 008）
    let sfx = [[1.25, "unsheathe"], [3.08, "awaken"], [SLASH, "slash"], [7.9, "sheath"]];
    if (opts.short && P.has("exorcise_short")) { P.play("exorcise_short", 0.2); sfx = [[EXO_SHORT.unsheathe, "unsheathe"], [EXO_SHORT.awaken[0], "awaken"], [EXO_SHORT.slash, "slash"], [EXO_SHORT.sheath, "sheath"]]; }
    else if (opts.short) { const F = EXO_FALLBACK; P.play("exorcise", 0.2, F); sfx = [[0, "unsheathe"], [0.1, "awaken"], ...sfx.slice(2).map(([t, n]) => [(t - F.from) / F.speed, n])]; }
    else P.play("exorcise", 0.25);   // 不重置弹簧骨：重置那一帧下摆回到绑定姿势，像白布摊了一地（翻车集 008）
    putDownChest();
    audio.play("hyoshigi");
    swordTimers = sfx.map(([t, n]) => setTimeout(() => sword && audio.play(n), t * 1000));
  }
  function endSword() {
    swordTimers.forEach(clearTimeout); swordTimers = [];
    if (/^exorcise/.test(P.currentName)) P.play("idle", 0.4);
    sword = false; busy = false; post.setOutlineMix(0); stillT = 0; fitFov();   // fitFov：把运镜改过的 fov 复位
    pickUpChest();
    const o = swordOpts; swordOpts = {}; o.onEnd?.(swordSlashed);
  }
  // 药箱：原作药郎退魔前先把药箱放下。拔剑时把药箱从背上摘下，立在他右后方的地上（保持背着时的朝向），收剑后挂回去。
  // 不放下的话横斩转身时药箱从侧面甩出来压着袖子和头发（翻车集 008）
  let chestSaved = null;
  function putDownChest() {
    const c = P.props.find((p) => p.id === "medicine_chest"); if (!c || chestSaved) return;
    const o = c.prop; chestSaved = { parent: o.parent, pos: o.position.clone(), quat: o.quaternion.clone(), scale: o.scale.clone() };
    player.updateMatrixWorld(true); scene.attach(o);
    const yaw = swordFace, fx = Math.sin(yaw), fz = Math.cos(yaw);   // 按转向镜头之后的朝向放（药郎是慢慢转过去的）
    o.rotateOnWorldAxis(new THREE.Vector3(0, 1, 0), yaw - player.rotation.y);
    const box = new THREE.Box3().setFromObject(o), ctr = box.getCenter(new THREE.Vector3());
    const tx = player.position.x - fz * 0.75 - fx * 0.35, tz = player.position.z + fx * 0.75 - fz * 0.35;   // 右手边 0.75 米、往后 0.35 米
    o.position.x += tx - ctr.x; o.position.z += tz - ctr.z; o.position.y += player.position.y - box.min.y;
  }
  function pickUpChest() {
    const c = P.props.find((p) => p.id === "medicine_chest"); if (!c || !chestSaved) return;
    const o = c.prop, s = chestSaved; s.parent.add(o); o.position.copy(s.pos); o.quaternion.copy(s.quat); o.scale.copy(s.scale); chestSaved = null;
  }
  function swordTick(dt) {
    if (!sword) return;
    swordT += dt;
    if (swordT < 1.2) turnToward(swordFace, 6, dt);
    if (!/^exorcise/.test(P.currentName)) { endSword(); return; }   // 播完自己回了待机
    const short = P.currentName === "exorcise_short_k";
    post.setOutlineMix(short ? awakenMix(P.time, { from: EXO_SHORT.awaken[0], to: EXO_SHORT.awaken[1], fade: 0.15 }) : awakenMix(P.time));
    // 妖化那一刻告诉物怪（怨念开始被抽出来，docs/19 第十节）：给它到横斩还剩几秒（短版的占位是 1.6 倍速，按实际播放时间算）
    const awT = short ? EXO_SHORT.awaken[0] : AWAKEN.from, slT = short ? EXO_SHORT.slash : SLASH;
    if (!swordAwoke && P.time >= awT) { swordAwoke = true; swordOpts.onAwaken?.(Math.max(0.3, (slT - P.time) / (!short && swordOpts.short ? EXO_FALLBACK.speed : 1)) * 0.9); }
    if (!swordSlashed && P.time >= slT) { swordSlashed = true; swordOpts.onSlash?.(); }
  }

  // ---- 物怪出没（encounter.js，docs/18）----
  let shakeT = 0;
  // 本命退魔后整片上色（docs/22：原作《鵺》结尾画面从水墨变彩色）：材质先全换成彩色，后期把画面压灰，再从中间往外一圈圈洇开
  let reveal = null;
  let exoShot = null;   // 本命魂光升起时截的一帧（结案札用）
  function recolor() {
    if (!loc.recolor || colored) return;
    colored = true; try { localStorage.setItem(COLOR_KEY, "1"); } catch {}
    const roots = [...new Set([...zoneCache.values(), scene])].filter(Boolean);
    reveal = { t: -99 };   // 换材质这几百毫秒先占住（recoloring() 为真，执念物卡等着）
    // 等新一套贴图下好再换（recolorKit 返回 promise；没下好就换会黑一下），换的那一帧把画面压灰，再洇开
    Promise.all(roots.map((r) => recolorKit(r, loc.recolor))).then(() => {
      for (const r of roots) r.traverse((o) => { if (o.isMesh && o.material.uniforms?.uCutout) o.material.uniforms.uCutout.value = 1; });
      post.setReveal(0.05, 0.5, 0.42); reveal = { t: 0 };
      for (const n of npcsOn) scene.remove(n.group); npcsOn = [];   // 宅里的人跟着香散了
      snow.set(false); setSky(Z); audio.play("release", 3);
    });
  }
  const enc = createEncounter({
    scene, camera, player, P, audio, loc, texts, touch, mode: params.get("mononoke"), loader, assetUrl,
    noRandom: ["selftest", "auto", "walktest"].some((k) => params.has(k)) && !params.has("mononoke"),   // 自测、自动拍图不随机出
    zone: () => Z, col: () => col, cam: () => cam,
    free: () => !busy && !card.isOpen && !sword && !box?.isOpen,
    onSoul: (id) => { if (id === loc.case?.mononoke) exoShot = composePhoto(FILTERS[0]); },   // 结案札的画面：魂光升起那一刻（guide.js / closing.js）
    onRelease: (id) => { if (id === loc.case?.mononoke || id === loc.recolorOn) recolor(); },   // 本命魂走完（掉卡之前）：有 recolor 的地点上色
    recoloring: () => !!reveal,
    onCollect: (id) => { boxBtn.classList.add("new"); toast(touch ? "收进药箱了 · 点右上「箱」看" : "收进药箱了 · 按 I 打开", 3200); },
    // 引导（guide.js，docs/19）：看过两处才随机出；本命不随机出；第一次随机出哪只；本命退了盖印
    randomOk: () => guide.randomOk(), allowRandom: (id) => guide.allowRandom(id), firstRandom: () => guide.firstRandom(), onDone: (id) => guide.onExorcised(id),
    stopWalk: () => { path = null; },
    turnToward, stat: (p, t) => stat(p, t, true),
    shake: (s) => { shakeT = Math.max(shakeT, s); },
    // 屋里暗一点：往紫灰压；雨夜区块本来就压着藍调，在那上面再加一点
    gloom: (g) => { const wet = Z?.weather === "rain"; post.setTint(wet ? "#8C8CC8" : "#5A5480", wet ? 0.45 + 0.25 * g : 0.5 * g); },   // g = 0 时和区块原来的调色一样
    drawSword,
    // 现在按着的方向（按镜头算的世界 yaw），没按是 null：瞬移往这边
    moveYaw: () => {
      const f = cam.forward, v = new THREE.Vector3(), r = new THREE.Vector3(-f.z, 0, f.x), k = (a, b) => keys.has(a) || keys.has(b);
      if (k("KeyW", "ArrowUp")) v.add(f); if (k("KeyS", "ArrowDown")) v.sub(f);
      if (k("KeyD", "ArrowRight")) v.add(r); if (k("KeyA", "ArrowLeft")) v.sub(r);
      if (Math.hypot(stick.x, stick.y) > 0.15) v.addScaledVector(f, stick.y).addScaledVector(r, stick.x);
      return v.lengthSq() > 1e-4 ? Math.atan2(v.x, v.z) : null;
    },
    // 跟随镜头（不在固定机位、手没在拖）的 yaw，和往某个 yaw 慢慢转（时间常数约 0.7 秒）；泼溅区块的轨道镜头不转
    camYaw: () => (cam === follow && !follow.fixedOn && !drag ? follow.yaw : null),
    nudgeCam: (y, dt) => { follow.yaw += wrap(y - follow.yaw) * (1 - Math.exp(-1.4 * dt)); },
  });
  // 引导与探索（guide.js，docs/19）
  let mapPlaces = []; loadMap().then((m) => { const { real } = locationIds(); mapPlaces = (m?.places || []).filter((p) => p.open && real.includes(p.id)).map((p) => ({ id: p.id, name: p.name })); }).catch(() => {});
  const guide = createGuide({
    loc, texts, player, P, scene, camera, audio, enc, tags, col: () => col, loader, assetUrl, touch, tex: (f) => pub(`textures/kit/${f}`),
    noOutline: (o) => post.exclude.push(o),
    followCam: () => cam === follow && !follow.fixedOn,   // 放天秤：跟随镜头会转到药郎身后（perform），扫描房间的环绕 / 固定机位不转
    // act 的临时机位 { pos: [x,y,z], look: [x,y,z] }；拾遗特写另带 close: true（不往药郎身上挪看点）和 fov（收窄，关掉时复位）
    shot: setShot,
    findObj: (f) => findsOn?.children.find((g) => g.userData.find === f) || null,   // 拾遗小物件的网格（特写对准它的包围盒）
    // 镜头射线：from 往 to 方向，碰到墙、柱子（跟随镜头的碰撞网格）返回距离，没碰到或没有碰撞网格返回 null
    camRay: (from, to) => {
      if (cam !== follow || !follow.bvh) return null;
      const d = to.clone().sub(from), len = d.length(), r = new THREE.Ray(from.clone(), d.normalize());
      return follow.bvh.raycastFirst(r, THREE.DoubleSide, 0.06, len)?.distance ?? null;
    },
    loadKit: (kit) => loadKit(loader, assetUrl(`processed/kit/${kit}.glb`)), shake: (s) => { shakeT = Math.max(shakeT, s); },   // act 的小积木、镜头一抖（docs/20）
    // 动作播完就回待机；有场景演出时，等演出也结束再让玩家离开。
    perform: async (clip, sec, yaw, effect) => {
      busy = true; busyBy = `perform:${clip}`; path = null; prompt.set("");
      if (yaw != null) { player.rotation.y = yaw; camAim = cam.shot ? null : yaw + Math.PI; }
      P.play(clip, 0.25, { from: 0.01 });
      const animation = new Promise((done) => setTimeout(() => { P.play("idle", 0.4); stillT = 0; done(); }, sec * 1000));
      try { await Promise.all([animation, effect?.()]); }
      finally { busy = false; }
    },
    route: (a, b, tol) => { if (Z.npcs?.length) pf.invalidate(); return pf.routeTo(a, b, tol)?.pts || null; },
    zone: () => Z, npcs: () => npcsOn, free: () => !busy && !card.isOpen && !sword && !box?.isOpen && !enc.active,
    snap: () => (loc.recolor ? null : exoShot) || composePhoto(FILTERS[0]),   // 上色的地点截上色以后的
    places: () => mapPlaces, go: (id) => { location.href = pub("tour.html") + (id ? `?loc=${id}` : ""); },   // 结案卡"去下一处"：总地图上开着的地点按长卷顺序
    stat: (p, t) => stat(p, t, true),
    allViews: async () => Object.fromEntries(await Promise.all(Object.keys(loc.zones || {}).map(async (id) => [id, Object.keys((await resolveZone(loc, id)).views || {})]))),
  });
  const mkBtn = document.getElementById("mkbtn");
  const showMk = () => { mkBtn.classList.toggle("off", !enc.on); mkBtn.setAttribute("aria-pressed", String(enc.on)); mkBtn.title = `物怪出没：${enc.on ? "开" : "关"}`; };
  showMk();
  // 药箱（medbox.js）：斩过的物怪和执念物。物怪出没时、说明卡开着时不开
  const boxBtn = document.getElementById("boxbtn");
  var box = createMedbox({ entries: () => enc.entries(), asset, audio, book: (el) => guide.mountBook(el), onOpen: () => { boxBtn.classList.remove("new"); keys.clear(); if (path) { path = null; P.play("idle"); } } });
  function openBox() {
    if (box.isOpen) { box.close(); return; }
    if (enc.active) { toast("物怪还在，先别开箱"); return; }
    if (busy || sword || card.isOpen) return;
    box.open();
  }
  boxBtn.addEventListener("click", (e) => { e.stopPropagation(); openBox(); });
  mkBtn.addEventListener("click", (e) => { e.stopPropagation(); enc.toggle(); showMk(); audio.play("tick"); toast(`物怪出没：${enc.on ? "开（逛着逛着偶尔会出来）" : "关"}`); });

  let exitsOff = false;   // 自动拍图时关掉：药郎被摆到出口旁边拍验收机位，会被自动传走，下一张拍成别的区块
  let arriveT = 0;
  function checkExits(dt, walked, fromX, fromZ) {
    arriveT += dt;
    if (!walked || busy || !Z.exits || exitsOff) return;
    let near = false;
    Z.exits.forEach((e, i) => {
      const s = Z.stairs[e.stair]; if (!s) return;
      const d = Math.hypot(s.stand[0] - player.position.x, s.stand[1] - player.position.z);
      if (d < 0.9) near = true;
      // 11-05 用户："有的时候走出房间就回不去了"：进门站在门前 0.6 米，原来要先走出 0.9 米再回来门才认；
      // 一进门就转身往回走的话一直在圈里，门永远不触发。改成：进来 0.8 秒以后，正在走、而且面朝这扇门走过去，也解锁
      if (arriveLock && arriveT > 0.8 && d < 0.9) {
        // 以走近门的实际位移为准；转身动画追上方向之前，也应当能原路返回。
        const before = Math.hypot(s.stand[0] - fromX, s.stand[1] - fromZ);
        if (before - d > walked * 0.5) arriveLock = false;
      }
      if (d < 0.45 && !arriveLock) takeExit(i);   // 到达点在门前 0.6 米，比触发圈远，不会一进来就被传回去
    });
    if (!near) arriveLock = false;
  }
  function updatePrompt() {
    if (busy || card.isOpen) return;
    if (enc.active || guide.acting || guide.endOpen) { prompt.set(""); return; }   // 正在做 act（合掌、开柜子……）：提示条收着
    if (path?.label) { prompt.set(`前往 · ${path.label}`); return; }
    const v = nearView();
    prompt.set(v ? `${touch ? "点这里看" : "E 看看"} · ${viewText(v).title}` : guide.promptText(touch));
  }

  // ---- 拍照：去掉界面，按当前滤镜合成，存 PNG ----
  // 滤镜预览：画布走 CSS filter，夜色的藍调、雨丝在 #fx 层；存图时在 2D 画布上用同样的 filter 重画一遍，再叠藍调和雨丝
  const FILTERS = [
    { id: "none", name: "原色", css: "none" },
    { id: "night", name: "夜色", css: "brightness(.72) saturate(.8) contrast(1.08)", tint: "rgba(42, 42, 78, .35)" },
    { id: "rain", name: "雨", css: "saturate(.85) brightness(.92)", rain: true },
    { id: "faded", name: "褪色", css: "sepia(.35) saturate(.7) contrast(.9) brightness(1.04)" },
  ];
  let filterIdx = 0;
  const fxEl = document.getElementById("fx");
  function setFilter(i, quiet = false) {
    filterIdx = (i + FILTERS.length) % FILTERS.length;
    const f = FILTERS[filterIdx];
    renderer.domElement.style.filter = f.css === "none" ? "" : f.css;
    fxEl.className = f.id;
    if (!quiet) { audio.play("tick"); toast(`滤镜：${f.name}${touch ? "" : "（F 切换）"}`); }
  }
  function composePhoto(f = FILTERS[filterIdx], seal = null) {
    post.render();
    const src = renderer.domElement, c = document.createElement("canvas");
    c.width = src.width; c.height = src.height;
    const ctx = c.getContext("2d");
    ctx.filter = f.css; ctx.drawImage(src, 0, 0); ctx.filter = "none";
    if (f.tint) { ctx.globalCompositeOperation = "multiply"; ctx.fillStyle = f.tint; ctx.fillRect(0, 0, c.width, c.height); ctx.globalCompositeOperation = "source-over"; }
    if (f.rain) {
      // 雨丝：固定种子，同一个画面拍两次一样
      let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      ctx.strokeStyle = "rgba(241, 233, 218, .35)"; ctx.lineWidth = Math.max(1, c.width / 1280);
      ctx.beginPath();
      for (let i = 0; i < 520; i++) {
        const x = rnd() * c.width * 1.2, y = rnd() * c.height, L = (0.04 + rnd() * 0.06) * c.height;
        ctx.moveTo(x, y); ctx.lineTo(x - L * 0.25, y + L);
      }
      ctx.stroke();
    }
    if (seal) {   // 拍照点（guide.js）：右下角盖一枚朱印，地点名竖排
      const u = c.height / 800, s = 64 * u, x = c.width - s - 28 * u, y = c.height - s - 28 * u, ch = [...seal].slice(0, 3);
      ctx.save(); ctx.globalAlpha = 0.88; ctx.fillStyle = "#B42A47"; ctx.fillRect(x, y, s, s);
      ctx.fillStyle = "#F1E9DA"; ctx.font = `${Math.round((s * 0.8) / ch.length)}px "Hiragino Mincho ProN", "Songti SC", serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ch.forEach((t, i) => ctx.fillText(t, x + s / 2, y + (s * (i + 0.5)) / ch.length + 1));
      ctx.strokeStyle = "#F1E9DA"; ctx.lineWidth = 2 * u; ctx.strokeRect(x + 4 * u, y + 4 * u, s - 8 * u, s - 8 * u); ctx.restore();
    }
    return c;
  }
  function photo() {
    stat("拍照", `拍照 · ${loc.name}`, true);
    audio.play("shutter");
    const seal = guide.onPhoto(), shot = composePhoto(undefined, seal), url = shot.toDataURL("image/png");
    if (seal) setTimeout(() => toast("好位置 · 照片盖了印", 2400), 300);
    flash();
    if (touch && navigator.canShare) {
      // 手机：弹系统分享，能直接存进相册；不支持分享文件的退回下载
      shot.toBlob((b) => {
        const f = new File([b], `怪化猫游览_${loc.name}.png`, { type: "image/png" });
        if (navigator.canShare({ files: [f] })) navigator.share({ files: [f] }).catch(() => {}); else download();
      }, "image/png");
      return;
    }
    download();
    function download() {
    const a = document.createElement("a");
    const t = new Date(), pad = (n) => String(n).padStart(2, "0");
    a.download = `怪化猫游览_${loc.name}_${FILTERS[filterIdx].id === "none" ? "" : FILTERS[filterIdx].name + "_"}${t.getFullYear()}${pad(t.getMonth() + 1)}${pad(t.getDate())}_${pad(t.getHours())}${pad(t.getMinutes())}${pad(t.getSeconds())}.png`;
    a.href = url; a.click();
    toast("拍好了，存在下载文件夹");
    }
  }

  // 脚步声：按走过的距离数步子，一步的长度随速度变（走 1 米/秒约 0.6 米一步，跑约 0.9 米）。
  // 地面按区块定（audio.js 的 FLOOR）；坂井家玄关土间比地板低，踩在土间上换成石头声
  let floorSnd = "tatami", stepAcc = 0;
  function footsteps(d, dt) {
    if (d < 1e-4 || dt <= 0) { stepAcc = Math.min(stepAcc, 0.3); return; }
    stepAcc += d;
    const v = d / dt, stride = 0.42 + 0.17 * Math.min(v, 3);
    if (stepAcc >= stride) { stepAcc -= stride; audio.play("step", player.position.y < -0.1 ? "stone" : floorSnd, Math.min(1, 0.6 + v * 0.2)); }
  }

  const clock = new THREE.Clock(), tv = new THREE.Vector3();
  let camAim = null;   // act 时跟随镜头要转到的 yaw（guide 的 perform）
  function frame(dt = Math.min(clock.getDelta(), 0.1)) {
    if (camAim != null) { if (cam !== follow || follow.fixedOn || drag) camAim = null; else { const d = wrap(camAim - follow.yaw); follow.yaw += d * (1 - Math.exp(-2.5 * dt)); if (Math.abs(d) < 0.01) camAim = null; } }
    swordTick(dt);
    if (Z) {
      const x0 = player.position.x, z0 = player.position.z;
      move(dt);
      const walked = Math.hypot(player.position.x - x0, player.position.z - z0);
      enc.update(dt); guide.update(dt);
      footsteps(walked, dt);
      checkExits(dt, walked, x0, z0);   // 走进门才转场，战斗瞬移、后撤落到门前时仍留在这间。
      updatePrompt();
    }
    P.update(dt);
    for (const n of npcsOn) npcTick(n, dt);
    if (look.x || look.y) cam.turn(look.x * 2.4 * dt, look.y * 1.2 * dt);   // 视角摇杆：往右推镜头往右转，往上推往上看
    cam.update(enc.camTarget(), dt, enc.takeCamSnap());   // 物怪出没时镜头看药郎和物怪之间（偏药郎）
    if (sword) { fitFov(); if (!swordOpts.short) swordShot(camera, cam, player, P.time); }   // 拔剑运镜（sword_cam.js）：每帧从跟随镜头的结果上叠，fov 先复位再乘；短版不带运镜
    sea(dt);
    if (shakeT > 0) { shakeT -= dt; const a = 0.06 * Math.min(1, shakeT / 0.12); camera.position.x += (Math.random() - 0.5) * a; camera.position.y += (Math.random() - 0.5) * a; camera.updateMatrixWorld(); }   // 袖挡、钉中：镜头一震
    rain.update(dt, camera); snow.update(dt, camera);
    if (reveal && reveal.t > -99) {   // 退魔后上色：颜色从画面中间往外洇开，4.5 秒铺满
      reveal.t += dt; const k = Math.min(1, reveal.t / 4.5);
      post.setReveal(k >= 1 ? -1 : 0.05 + 1.7 * k * k, 0.5, 0.42); if (k >= 1) reveal = null;
    }
    destination.visible = !!path && !busy && !enc.active;
    post.render();
    tags.update(camera, innerWidth, innerHeight, tv);
  }
  // 海和船摇（そらりす丸，地点写 "sway": 幅度倍数）：网格名（kit 的 kit_sol_sea）或材质名带 sol_sea 的海面贴图慢慢流、波纹晃；镜头随船轻轻左右倾、上下起伏。
  //   镜头控制器每帧会重算朝向（跟随）或不动（固定机位），所以上一帧加的倾斜先确认还在、在的话先扣掉再加这一帧的，不会越叠越歪
  let seaT = 0, seaScan = 0, seaMats = [], pondMeshes = [], swayPrev = { roll: 0, y: 0, q: null };
  let glazeMat = null;
  function glazePond(o) {
    if (o.userData.glaze) return;
    if (!glazeMat) {
      const c = document.createElement("canvas"); c.width = c.height = 256; const g = c.getContext("2d");
      g.fillStyle = "rgba(140,200,225,0.14)"; g.fillRect(0, 0, 256, 256);
      g.filter = "blur(5px)"; g.strokeStyle = "rgba(235,248,255,0.30)";
      // 45° 的斜反光，左右各画一份，一格一格拼起来是连着的（不露格子缝）
      for (const [x, w] of [[30, 9], [58, 3], [150, 12], [178, 4]]) for (const d of [-256, 0, 256]) { g.lineWidth = w; g.beginPath(); g.moveTo(x + d, 256); g.lineTo(x + d + 256, 0); g.stroke(); }
      const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace;
      glazeMat = new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
    }
    const m = new THREE.Mesh(o.geometry, glazeMat); m.position.y = 0.01; m.renderOrder = 2; m.name = "pond_glaze";
    o.add(m); post.exclude.push(m); o.userData.glaze = m;
  }
  function sea(dt) {
    seaT += dt;
    if ((seaScan -= dt) <= 0) {   // 一秒找一次（换区块、退魔换材质都会变）
      seaScan = 1; const set = new Set();
      // 中庭漩涡池（sol_uzu / sol_pool）：11-06 用户说"没看见水池"——深色漩涡纹像块地毯。说明卡写"水却一点不动"，所以纹样不流，
      // 只在上面盖一层不描边的水光（淡青、几道斜的反光），看得出是一池静水
      pondMeshes = [];
      scene.traverse((o) => { if (!o.isMesh || !o.visible || !o.material?.uniforms?.uUvOff) return; const n = `${o.name}|${o.material.name || ""}`; if (/sol_sea/.test(n)) set.add(o.material); else if (/sol_uzu|sol_pool/.test(n)) pondMeshes.push(o); });
      seaMats = [...set];
    }
    for (const m of seaMats) { m.uniforms.uUvOff.value.set(seaT * 0.05, Math.sin(seaT * 0.4) * 0.03); m.uniforms.uWave.value.set(0.035, 1.6, seaT * 1.1); }
    for (const o of pondMeshes) glazePond(o);
    const amp = loc.sway || 0; if (!amp) return;
    if (swayPrev.q && camera.quaternion.equals(swayPrev.q)) { camera.rotateZ(-swayPrev.roll); camera.position.y -= swayPrev.y; }
    const roll = Math.sin(seaT * 0.55) * 0.012 * amp + Math.sin(seaT * 0.21) * 0.006 * amp, y = Math.sin(seaT * 0.8) * 0.035 * amp;
    camera.rotateZ(roll); camera.position.y += y; camera.updateMatrixWorld();
    swayPrev = { roll, y, q: camera.quaternion.clone() };
  }
  // 竖屏手机：区块的 fov 是按横屏定的，竖着横向只剩一条缝。窄于 1.2:1 时放大竖向 fov，让横向视野和 1.2:1 时一样，最多 75°
  function fitFov() {
    const a = innerWidth / innerHeight, t = Math.tan(THREE.MathUtils.degToRad(baseFov) / 2);
    camera.fov = a >= 1.2 ? baseFov : Math.min(75, THREE.MathUtils.radToDeg(2 * Math.atan(t * 1.2 / a)));
    camera.updateProjectionMatrix();
  }
  addEventListener("resize", () => { camera.aspect = innerWidth / innerHeight; fitFov(); renderer.setSize(innerWidth, innerHeight); post.resize(); });

  loading.step("布置房间…");
  await enterZone(params.get("zone") || loc.start);
  renderer.setAnimationLoop(() => frame());
  // 加载提示：泼溅（大奥）也要等下完，不然一进去房间是空的；最多等 2 分钟，网太慢就先让人进去
  // 11-05（翻车集 016）：泼溅刚下完还没排好序、衣服弹簧骨还在从绑定姿势往下落，加载提示一撤就看见空房间和炸开的衣摆。
  //   在提示底下先跑一会儿：至少 30 帧、泼溅地点至少 1.2 秒（后台标签页不出帧，最多等 3 秒）
  await Promise.race([(async () => {
    const t0 = performance.now();
    for (let n = 0; n < 30 || performance.now() - t0 < (splatOf.size ? 1200 : 300); n++) await new Promise((r) => requestAnimationFrame(r));
  })(), new Promise((r) => setTimeout(r, 3000))]);
  loading.done();   // 进门那块泼溅 enterZone 里已经等过了
  reportLoad(id, loc.name);
  if (splatOf.size) splatQueue();
  prefetchNext(Z.id);
  // 进去以后再在后台下这个地点的物怪（0.4~0.8 MB），不拖慢首次加载；11-05 再往后排：等隔壁几间先下好（物怪要看过两处才出，不急），
  //   慢网上原来两样一起下，刚进门就去隔壁要多等一两秒
  if (enc.on) prefetchChain.then(() => enc.preload()).catch(() => {});
  if (!["selftest", "auto", "walktest"].some((k) => params.has(k))) guide.intro(loading.holding);   // 第一次进有案子的地点：一张小卡交代

  async function save(name) {
    frame(1 / 60);
    const data = renderer.domElement.toDataURL("image/jpeg", 0.92);
    return (await fetch("/__shot", { method: "POST", body: JSON.stringify({ name, data }) })).json();
  }
  window.__tour = { recolor: () => recolor(), loc, audio, get zone() { return Z; }, get col() { return col; }, player, P, get cam() { return cam; }, splats, setFilter, composePhoto, cyclePose, get pose() { return pose; }, enc, camera, scene, renderer, post, enterZone, walkTo, openView, takeExit, keys, save, step: (n = 1, dt = 1 / 60) => { for (let i = 0; i < n; i++) frame(dt); }, card, tags, guide, get npcs() { return npcsOn; }, get box() { return box; } };
  if (params.get("auto")) autoShots();
  if (params.get("selftest")) selfTest();
  if (params.get("walktest")) walkTest();

  // ?walktest=1：走路随动层的验收录像。外景里直走 5.5 米、左拐 90° 再走 3 米、停下站 1.5 秒，
  // 镜头在药郎左前方 3/4 侧面跟拍（背面会被药箱挡住上身），机位方向慢慢跟着他的朝向转（时间常数 0.8 秒），
  // 不用跟随镜头，免得镜头自己的平滑把身体的倾斜抵掉。每 1/24 秒存一帧 walktest_<tag>_NNN.jpg。
  // &layer=0&turn=old 是改之前的样子（没有随动层、匀速转身），tag 自动变成 old。用 tools/walk_video.sh 跑并合成视频
  async function walkTest() {
    const tag = params.get("sprint") ? "sprint" : params.get("layer") === "0" ? "old" : "new";   // &sprint=1：一直按着 Shift，快走 1 秒后加速成跑
    renderer.setAnimationLoop(null); status.style.display = "none"; tags.clear();
    if (loc.zones.soto) await enterZone("soto");
    player.position.set(2.5, 0, 11.0); player.rotation.y = Math.PI / 2; stand(); P.play("idle"); P.resetSprings();
    for (let i = 0; i < 60; i++) frame(1 / 60);
    const off = new THREE.Vector3(), look = new THREE.Vector3();
    let n = 0, camYaw = player.rotation.y;
    const shoot = async () => {
      camYaw += wrap(player.rotation.y - camYaw) * (1 - Math.exp(-(1 / 24) / 0.8));
      off.set(1.7, 1.3, 2.6).applyAxisAngle(new THREE.Vector3(0, 1, 0), camYaw);
      camera.position.copy(player.position).add(off); camera.lookAt(look.set(player.position.x, 1.0, player.position.z)); camera.updateMatrixWorld();
      post.render();
      const data = renderer.domElement.toDataURL("image/jpeg", 0.9);
      await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `walktest_${tag}_${String(n++).padStart(3, "0")}`, data }) });
    };
    if (params.get("sprint")) keys.add("ShiftLeft");
    path = { pts: [[8.0, 11.0], [8.0, 8.0]], then: null };
    let tail = 36;
    while (path || tail-- > 0) { frame(1 / 48); frame(1 / 48); await shoot(); }
    document.title = "WALKTEST DONE";
  }

  // ?selftest=1：不靠鼠标，把"走到观景点 → 开卡 → 关卡 → 走进出口 → 拉门转场到另一头"跑一遍，结果打到控制台（无头 Chrome 的日志里看）
  async function selfTest() {
    const log = (ok, msg) => console.log(`[selftest] ${ok ? "OK " : "FAIL"} ${msg}`);
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    renderer.setAnimationLoop(null);
    const run = (sec) => { for (let i = 0; i < sec * 60; i++) frame(1 / 60); };
    const v = Object.keys(Z.views)[0];
    if (v) {
      onTag(`view:${v}`); run(12);
      const p = Z.views[v], d = Math.hypot(p[0] - player.position.x, p[1] - player.position.z);
      log(d < 0.4, `走到观景点 ${v}，离点 ${d.toFixed(2)} 米`);
      log(card.isOpen, `说明卡打开：${document.querySelector("#card .title").textContent}`);
      run(1); log(["gaze_k", "look_up_k"].includes(P.currentName), `开卡时药郎驻足看（${P.currentName}）`);
      await save(`tour_${loc.id}_动作_驻足看`);
      card.close(); await wait(50); run(0.5); guide.closeEnding("stay");   // 斩的是本命：结案卡（还没弹的也算）关掉再往下测 log(!card.isOpen && P.currentName === "idle_k", `说明卡关掉，回待机（${P.currentName}）`);
    }
    if (Z.exits?.length) {
      const from = Z.id, e = Z.exits[0];
      onTag("exit:0"); for (let i = 0; i < 20 * 60 && !busy; i++) frame(1 / 60);
      log(busy, `走到出口 0（${e.label}）触发转场`);
      // 等转场真正结束（第一次进带配角的区块要先加载模型，可能超过 1 秒），最多等 8 秒
      for (let t = 0; t < 8000 && busy; t += 200) await wait(200);
      run(0.2);
      const s = Z.stairs[e.arrive ?? 0], d = Math.hypot(s.stand[0] - player.position.x, s.stand[1] - player.position.z);
      log(Z.id === e.to && d < 1.0, `转到 ${from} → ${Z.id}，离到达口 ${d.toFixed(2)} 米`);
      run(1); log(!busy && Z.id === e.to, "到了以后没有立刻又被传回去");
      // 11-05 用户："有的时候走出房间就回不去了"：一进门就转身按住方向键往回走（没先走出门口 0.9 米），要能回去
      { const back = Z.id, door = Z.stairs[e.arrive ?? 0], f = cam.forward, tgt = Math.atan2(door.stand[0] - player.position.x, door.stand[1] - player.position.z);
        const camYawNow = Math.atan2(f.x, f.z), dk = Math.cos(tgt - camYawNow) > 0.7 ? "KeyW" : Math.cos(tgt - camYawNow) < -0.7 ? "KeyS" : Math.sin(tgt - camYawNow) > 0 ? "KeyA" : "KeyD";
        keys.add(dk); for (let i = 0; i < 60 * 4 && !busy; i++) frame(1 / 60); keys.delete(dk);
        for (let t = 0; t < 8000 && busy; t += 200) await wait(200); run(0.3);
        log(Z.id === from, `一进门就转身往回走（按住 ${dk}），回到 ${from}（现在 ${Z.id}）`);
        if (Z.id !== back) { await enterZone(back, { stair: e.arrive ?? 0 }); run(1); } }
    }
    const lit = [];
    for (let i = 0; i < 10; i++) { keys.add("KeyW"); run(0.5); keys.delete("KeyW"); lit.push(col.canStand(player.position.x, player.position.z)); }
    log(lit.every(Boolean), "按住 W 走 5 秒，一直在可走区域里");
    // 四种滤镜各合成一张存到 shots，看滤镜有没有生效
    for (const f of FILTERS) {
      const data = composePhoto(f).toDataURL("image/jpeg", 0.9);
      const r = await (await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `tour_${loc.id}_滤镜_${f.name}`, data }) })).json();
      log(r.ok, `滤镜 ${f.name} 合成存图`);
    }
    // 配角巡逻：找第一个有巡逻配角的区块，进去跑 6 秒，看配角挪没挪
    const pz = Object.keys(loc.zones).find((k) => loc.zones[k].npcs?.some((d) => d.patrol));
    if (pz) {
      await enterZone(pz); run(0.1);
      const n = npcsOn.find((x) => x.patrol), p0 = n.group.position.clone();
      // 药郎放到离整条巡逻路线都超过 2 米、又离路线最近的可走格子（直接往旁边挪几米可能被墙拉回来，贴着配角，它就一直在让路）
      const segD = (x, z) => Math.min(...n.patrol.pts.slice(1).map((b, k) => { const a = n.patrol.pts[k], vx = b[0] - a[0], vz = b[1] - a[1], L = vx * vx + vz * vz || 1, t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (z - a[1]) * vz) / L)); return Math.hypot(x - a[0] - t * vx, z - a[1] - t * vz); }));
      const W2 = Z.walk; let best = null;
      for (let j = 0; j < W2.h; j += 2) for (let i = 0; i < W2.w; i += 2) {
        const x = W2.x0 + (i + 0.5) * W2.cell, z = W2.z0 + (j + 0.5) * W2.cell;
        if (!col.canStand(x, z)) continue;
        const d = segD(x, z); if (d > 2 && (!best || d < best.d)) best = { x, z, d };
      }
      if (best) { player.position.set(best.x, 0, best.z); stand(); }
      // 记 6 秒里离起点最远走了多远（只比首尾会撞上"走过去又走回来"的时刻）
      let moved = 0;
      for (let k = 0; k < 60; k++) { run(0.1); moved = Math.max(moved, p0.distanceTo(n.group.position)); }
      log(moved > 0.3, `配角巡逻：${pz} 里的配角 6 秒内最远离开起点 ${moved.toFixed(2)} 米`);
    }
    // 拔剑：X 一下，4 秒时应在妖化（描边红），10 秒后回待机
    for (let t = 0; t < 8000 && busy; t += 200) await wait(200);   // 前面按住 W 走的那段可能正好走进门、转场还没完
    await enterZone(loc.start); run(1);
    act("KeyX"); run(4);
    const red = post.quadMat.uniforms.uRedMix.value;
    const chestDown = P.props.find((p) => p.id === "medicine_chest")?.prop.parent === scene;
    log(P.currentName === "exorcise_k" && red > 0.9 && chestDown !== false, `拔剑：4 秒时在退魔三拍里、描边变红、药箱放在地上（${P.currentName}，红 ${red.toFixed(2)}，药箱在地上 ${chestDown}）`);
    await save(`tour_${loc.id}_动作_拔剑`);
    run(7); log(!sword && P.currentName === "idle_k" && post.quadMat.uniforms.uRedMix.value < 0.01 && !!P.props.find((p) => p.id === "medicine_chest")?.prop.parent !== scene, `拔剑播完回待机、药箱挂回背上、描边回墨色（${P.currentName}）`);
    // 物怪出没（docs/18）：在出发区块叫出一只（没标出生点就在镜头前方找空地），蓄力时闪避、落地时投札，钉齐三张后拔剑：
    // 第一次完整退魔、第二次短版，看消散、掉卡；第三次什么都不按，60 秒后应自己退走
    await enc.preload();   // 用角色线的物怪模型测（不是占位墨影）
    for (const round of [1, 2, 3]) {
      await enterZone(loc.start); run(1);
      if (round === 1) try { localStorage.removeItem("mononoke_tour_exo"); localStorage.removeItem("mononoke_tour_tut"); } catch {}   // 教学卡"只教一次"也清（文案w 11-06 报：同一浏览器第二次跑会误报）
      if (!enc.start(true, enc.rosterAll[0])) { log(false, "物怪出没：找不到出生点"); break; }   // 原作那只（有案子的地点随机不出它，这里点名叫）
      for (let i = 0; i < 600 && enc.state !== "fight" && !enc.tutorial; i++) frame(1 / 60);
      if (round === 1) {   // 第一次遭遇：现身后停住弹教学卡，停着的时候物怪不动；空格关卡再开打
        const T0 = enc.debug.T; run(1); const no = () => document.querySelector("#mktut .no")?.textContent;
        const frozen = enc.tutorial && enc.debug.T === T0 && no() === "1 / 6";
        act("ArrowRight"); const p2 = no() === "2 / 6" && document.querySelector("#mktut .key")?.textContent === "J";
        act("KeyX"); const need = document.querySelector("#mk .need.show") === null && !sword;   // 卡开着按 X 不该亮"还差"、不拔剑
        for (let i = 0; i < 4; i++) act("ArrowRight"); const last = document.querySelector("#mktut .next")?.textContent === "开打";
        act("Space"); for (let i = 0; i < 10; i++) frame(1 / 60);
        log(frozen && p2 && need && last && !enc.tutorial && enc.state === "fight", `物怪出没第 1 次：现身后停住弹教学卡，一页一个键翻到 6 / 6，开打（${enc.state}）`);
        act("KeyX"); log(!!document.querySelector("#mk .need.show") && enc.state === "fight" && !sword, "形真理没齐按 X：中间亮三格提示，剑没拔");
      }
      for (let i = 0; i < 600 && enc.state !== "fight"; i++) frame(1 / 60);
      if (round === 3) { run(62); log(enc.state === "idle" && !enc.monster, `物怪出没第 3 次：不理它，60 秒后自己退走（${enc.state}）`); break; }
      // 第 2 次：蓄力时按 K 跳（不按空格），开打 1.5 秒按一次 L 瞬移
      let dodged = 0, maxY = 0, guards = 0, blinkD = -1;
      for (let i = 0; i < 60 * 55 && enc.state === "fight"; i++) {
        const d = enc.debug;
        if (d.sub === "charge" && d.subT > 0.55 && d.subT <= 0.57) { act(round === 2 ? "KeyK" : "Space"); dodged++; }
        if (round === 2 && i === 90) { const p0 = player.position.clone(); act("KeyL"); run(0.6); blinkD = Math.hypot(player.position.x - p0.x, player.position.z - p0.z); }
        if (round === 2) maxY = Math.max(maxY, player.position.y - (col.floorY(player.position.x, player.position.z) ?? 0));
        if (d.sub === "land" && i % 10 === 0) act("KeyJ");
        const g0 = P.currentName; frame(1 / 60); if (round === 2 && g0 !== "guard_k" && P.currentName === "guard_k") guards++;
      }
      if (round === 2) log(maxY > 0.6 && guards === 0 && blinkD > 1.5 && player.visible, `物怪出没第 2 次：K 跳 ${dodged} 次（最高 ${maxY.toFixed(2)} 米，被撞 ${guards} 次）、L 瞬移 ${blinkD.toFixed(2)} 米`);
      log(enc.state === "sealed" && enc.pins === 3 && !!enc.monster?.real, `物怪出没第 ${round} 次：钉齐三张（${enc.monster?.real ? "原作模型" : "墨影"}，${enc.pins} 张，闪避 ${dodged} 次，${enc.debug.fightT} 秒）`);
      run(0.8); if (round === 1) await save(`tour_${loc.id}_物怪_札阵`);
      act("KeyX"); const anim = P.currentName; let grudge = false, cut = false, vis = true, burned = false, burnShot = false;
      for (let i = 0; i < 60 * 23 && (enc.state !== "idle" || enc.cardPending); i++) { frame(1 / 60); grudge ||= !!enc.fx.grudge; cut ||= enc.fx.grudge?.cut >= 0; burned ||= !!enc.fx.burn || enc.monster?.id === "umibozu";   // 海坊主是沉回海里，不烧
        if (round === 1 && !burnShot && enc.fx.burn?.t > 1.0) { burnShot = true; await save(`tour_${loc.id}_物怪_散华`); } if (enc.state === "vanish") vis &&= !!enc.monster?.group.visible || enc.monster?.id === "umibozu"; }   // 退魔 10 秒 + 魂走 3~4 秒
      log(anim === (round === 1 ? "exorcise_k" : "exorcise_short_k") && grudge && cut && vis && burned && enc.state === "idle" && card.isOpen && !sword, `物怪出没第 ${round} 次：${anim} 退魔，斩的是抽出来的怨念团（抽出 ${grudge}、劈开 ${cut}、本体没被砍没 ${vis}、散华 ${burned}），掉执念物卡（${document.querySelector("#card .title")?.textContent}）`);
      card.close(); await wait(50); run(0.5); guide.closeEnding("stay");   // 斩的是本命：结案卡（还没弹的也算）关掉再往下测
    }
    // 送（docs/19 第十节）：没有怨的那几只，形真理齐了剑不出鞘，X 改成送它走（坂井家小化猫、万屋青座敷；大奥没有）
    const okuriId = { sakai: "bakeneko_ko", wanya: "zashiki_ao" }[loc.id];
    if (okuriId) {
      await enc.preload(okuriId); await enterZone(loc.start); run(1);
      if (enc.start(true, okuriId)) {
        for (let i = 0; i < 900 && enc.state !== "fight"; i++) frame(1 / 60);
        for (let i = 0; i < 60 * 55 && enc.state === "fight"; i++) { const d = enc.debug; if (d.sub === "charge" && d.subT > 0.55 && d.subT <= 0.57) act("Space"); if (d.sub === "land" && i % 10 === 0) act("KeyJ"); frame(1 / 60); }
        run(0.8); const btn = document.querySelector("#pad .b-sword")?.textContent;
        act("KeyX"); const st0 = enc.state; let drew = false;
        for (let i = 0; i < 60 * 12 && enc.state !== "idle"; i++) { frame(1 / 60); drew ||= sword; }
        log(btn === "送" && st0 === "okuri" && !drew && enc.state === "idle" && card.isOpen, `送：${okuriId} 形真理齐了钮写「${btn}」，按 X 剑没出鞘（${st0}），送走、掉卡（${document.querySelector("#card .title")?.textContent}）`);
        card.close(); await wait(50); run(0.5); guide.closeEnding("stay");   // 斩的是本命：结案卡（还没弹的也算）关掉再往下测
      } else log(false, `送：${okuriId} 找不到出生点`);
    }
    // 引导与探索（guide.js，docs/19）：有案子的地点（坂井家）走一遍——凑字、提示一档档加、门札、本命现身
    if (guide.hasCase) {
      guide.reset(); const S0 = () => guide.state; const C = loc.case;
      // 本命之前随机不出它，第一次随机出 firstRandom
      log(!guide.allowRandom(C.mononoke) && guide.firstRandom() === C.firstRandom, `引导：本命 ${C.mononoke} 不随机出，第一次随机出 ${C.firstRandom}`);
      // 提示：进玄关（有没看的観）站着不动，40 / 90 / 150 秒各加一档
      const hz = loc.zones.genkan ? "genkan" : Object.keys(loc.zones).find((k) => k !== loc.start) || loc.start;   // 有没看的観的区块
      await enterZone(hz); run(0.5); guide.quiet = 0;
      // 计时直接拨到每档前一点再走一秒（真跑 150 秒，扫描房间的大奥会把 GPU 跑崩）
      guide.quiet = 39.5; run(1); const h1 = guide.hintLv; guide.quiet = 89.5; run(1); const h2 = guide.hintLv; guide.quiet = 149.5; run(1); const h3 = guide.hintLv, ptxt = document.getElementById("prompt").textContent;
      log(h1 === 1 && h2 === 2 && h3 === 3 && !!ptxt, `引导：${loc.zones[hz].name}站着不动，提示 40 秒第 ${h1} 档、90 秒第 ${h2} 档、150 秒第 ${h3} 档（${ptxt}）${h3 === 3 ? "" : `［busy ${busy}(${busyBy}) 卡 ${card.isOpen} 剑 ${!!sword} 箱 ${!!box?.isOpen} 物怪 ${enc.active}/${enc.state} 结案 ${guide.endOpen} 做 ${guide.acting}］`}`);
      const fuda = [...document.querySelectorAll(".tag.exit")].map((e) => (e.classList.contains("fuda") ? "札" : e.classList.contains("dim") ? "暗" : "-") + e.textContent);
      log(fuda.some((t) => t.startsWith("札")), `引导：${loc.zones[hz].name}的门札（${fuda.join(" ")}）`);
      // 放天秤（11-06）：按 T 沿路立起一串天秤指向要找的东西，6 秒多以后收掉，歇 8 秒
      { for (let t = 0; t < 8000 && busy; t += 200) await wait(200);
        const st = enterZone(loc.start).then(() => run(0.5)); await st; run(9);   // 前面第二档提示自动放过一次：等它收掉、歇完
        const tgt = guide.target(), far = !tgt || Math.hypot(tgt.pos[0] - player.position.x, tgt.pos[1] - player.position.z) >= 1.2;   // 就在脚边时不立天秤、只说一句
        act("KeyT"); run(1.5); const n1 = guide.cast, cd = guide.castCd > 0; run(8); const n2 = guide.cast;
        for (let t = 0; t < 3000 && busy; t += 100) await wait(100);   // 抬手那 0.9 秒按真时间算：等它做完，后面开说明卡才不被挡
        log(cd && (far ? n1 >= 1 && n2 === 0 : n1 === 0), `放天秤：按 T ${far ? `立起 ${n1} 只、7 秒后收掉（剩 ${n2}）` : "目标就在脚边，只响铃说一句"}、进入冷却`); }
      // 先后：理的线索先凑齐（真还没亮），理不亮、格子写"等"；真亮了理接着亮
      const li = C.clues.find((c) => c.after);
      if (li) { li.need.forEach((k) => guide.mark(k)); run(0.2); const held = !S0().chars.includes(li.char) && (S0().held || []).includes(li.char) && document.querySelector(`#case .k[data-c="${li.char}"]`)?.dataset.p === "等";
        log(held, `引导：${li.char}的线索先齐了、${li.after}还没亮时${li.char}不亮，格子写"等"`); }
      // 凑字：need 里的観看过、配角的话听到（配角没文案时直接记）；三样齐了天秤停、三格全亮
      for (const cl of C.clues) for (const k of cl.need) {
        const [z, w] = k.split("/"), [kind, id] = w.split(":");
        if (Z.id !== z) { await enterZone(z); run(0.3); }
        if (kind === "view") { openView(id); await wait(30); card.close(); await wait(30); run(0.3); }
        else if (kind === "npc" && texts[`npc.${loc.id}.${id}`] && npcsOn.some((x) => x.id === id)) { const n = npcsOn.find((x) => x.id === id); player.position.set(n.pos[0] + 0.8, player.position.y, n.pos[1]); n.said = -1; for (let i = 0; i < 4; i++) { guide.act(); run(0.2); } }
        else if (kind === "act") {   // 能"做"的事：站到那儿按 E，等效果放完、那句话浮完记下（docs/20）
          const a = Z.acts?.find((x) => x.id === id);
          if (a) { player.position.set(a.pos[0], player.position.y, a.pos[1]); run(0.1); const lbl = guide.promptText(false); guide.act(); for (let i = 0; i < 80 && !guide.state.seen.includes(k); i++) { run(0.1); await wait(100); }
            log(guide.state.seen.includes(k), `引导：${Z.name} 按 E「${lbl}」（${[].concat(a.fx || "incense").join("+")}），做完记下 ${k}`); }
          else guide.mark(k);
        }
        else guide.mark(k);
      }
      const lit = [...document.querySelectorAll("#case .k.got")].map((e) => e.textContent).join("");
      box.openBook(); await wait(60);
      const bk = document.querySelector("#medbox .book"), rooms = bk?.querySelectorAll(".C-room").length, litN = bk?.querySelectorAll(".C-node.lit").length, lines = bk?.querySelectorAll(".C-svg path").length, sw = bk?.querySelector(".C-sword")?.textContent;
      box.close();
      log(rooms === Object.keys(loc.case.plan?.rooms || {}).length && litN === 3 && lines > 0 && /可出鞘/.test(sw || ""), `引导：药箱案卷（宅图）翻得开：${rooms} 间房、亮 ${litN} 张札、${lines} 条线、剑「${sw}」`);
      log(S0().chars.length === 3 && S0().ready && lit === "形真理", `引导：凑齐线索，三格亮了（${lit}）`);
      // 本命：走进本命那间，2.5 秒后现身（大奥 bossReturn：从别的房间回到主廊）
      enc.reset(); if (C.bossReturn && Z.id === C.boss) { await enterZone(Object.keys(loc.zones).find((k) => k !== C.boss)); run(0.5); }
      await enterZone(C.boss); run(5);
      const boss = enc.current, bst = enc.state;
      log(boss === C.mononoke && ["omen", "appear", "fight"].includes(bst) || enc.tutorial, `引导：形真理齐了进${loc.zones[C.boss].name}，本命现身（${boss}，${bst}）${boss === C.mononoke && ["omen", "appear", "fight"].includes(bst) ? "" : `［ready ${guide.state.ready} done ${guide.state.done} busy ${busy}(${busyBy}) 卡 ${card.isOpen} 箱 ${!!box?.isOpen} 剑 ${!!sword} 区块 ${Z.id} 结案 ${guide.endOpen}］`}`);
      // 结案札（11-06 第二版）：本命退了 2.2 秒后弹一张画好的竖版札（1080×1440），第一下 E 落印，第二下 E 接着逛关掉
      enc.reset(); guide.onExorcised(C.mononoke); await wait(2600);
      if (C.closeAt) {   // 笛小路家：退完不马上结案，要先出去（guide.js outWait）；没出去时不弹，出去 5 秒后弹
        const waitOk = guide.state.outWait && !guide.endOpen, lit = document.querySelector(".tag.exit.fuda")?.textContent;
        await enterZone(C.closeAt[0]); run(0.5); const early = guide.endOpen; await wait(5400);
        log(waitOk && !early && !guide.state.outWait, `引导：本命退了先不结案，出口金札「${lit || ""}」往外指，走到${loc.zones[C.closeAt[0]].name}看一会儿再弹结案札`);
      }
      for (let t = 0; t < 3000 && !guide.endOpen; t += 100) await wait(100);
      const cv = document.querySelector("#case-end canvas"), d = guide.endCard || {}, nextBtn = document.querySelector("#case-end button.main")?.textContent.replace(/[EN]$/, "");
      const opened = guide.endOpen; act("KeyE"); const sealed = !!d.sealed; act("KeyE"); await wait(50);
      log(opened && cv?.width === 1080 && cv?.height === 1440 && !!d.shot && !!d.portrait && !!d.title && sealed && !guide.endOpen && !!nextBtn,
        `结案札：退魔后弹出（${cv?.width}×${cv?.height}，画面 ${!!d.shot}、立绘 ${!!d.portrait}）、判词「${(d.verdict || "").slice(0, 12)}…」、一问「${(d.question || "").slice(0, 10)}…」、印「${d.tag || ""}」、钮「${nextBtn}」、E 落印再 E 关掉`);
      guide.reset(); run(0.5);
    }
    // 药箱：前面退过的物怪收进去了。I 打开只有箱子；回车拉开那格出卡（有立绘）；Esc 先收卡、再关箱子；开着时人不走、物怪不出
    {
      const got = enc.entries().filter((e) => e.got);
      act("KeyI"); const opened = box.isOpen && !box.cardOpen, cnt = document.querySelector("#medbox .mb-count").textContent, first = box.selected?.id;
      act("Enter"); await wait(300); const img = document.querySelector("#medbox .tr-img img"), card1 = box.cardOpen;
      act("Escape"); const back = box.isOpen && !box.cardOpen;
      act("Escape");
      log(opened && got.length > 0 && cnt === `已收 ${got.length} / ${enc.entries().length}` && first === got[0].id && card1 && img?.naturalWidth > 0 && back && !box.isOpen,
        `药箱：开（只有箱子）、${cnt}、回车拉开 ${first} 出卡（立绘 ${img?.naturalWidth || 0} 像素）、Esc 收卡、Esc 关`);
    }
    // 这个地点能出的每一只（11-04 加到三~五只）：指定出场，等到缠斗，查是原作模型、身高对、动作在播，存一张图
    for (const id of enc.rosterAll) {
      await enc.preload(id); await enterZone(loc.start); run(0.5);
      if (!enc.start(true, id)) { log(false, `物怪 ${id}：找不到出生点`); continue; }
      for (let i = 0; i < 600 && enc.state !== "fight"; i++) frame(1 / 60);
      run(1.5);
      const m = enc.monster, box = new THREE.Box3().setFromObject(m.group), h = box.max.y - box.min.y;
      log(m?.real && m.id === id && enc.state === "fight" && h > 0.4 && h < 2.6 && !!m.clip, `物怪 ${id}（${enc.current}）：原作模型、缠斗中，高 ${h.toFixed(2)} 米，动作 ${m.clip}${m.swarm ? "，一群" : ""}`);
      await save(`tour_${loc.id}_物怪_${id}`);
      enc.reset(); run(0.3);
    }
    // 拍照姿势：先回到出发区块的出生点（前面按 W 可能走到墙角，镜头被挤到头顶），
    // O 切两次（抱臂、回头），各等 1 秒让下摆停下来再存图；再切一次回不摆
    await enterZone(loc.start); run(1);
    for (const want of ["pose_fold_k", "pose_back_k"]) {
      cyclePose(); run(1);
      log(P.currentName === want, `拍照姿势 ${want}（当前 ${P.currentName}）`);
      await save(`tour_${loc.id}_动作_${want}`);
    }
    cyclePose(); run(0.3); log(pose === null && P.currentName === "idle_k", "姿势切回不摆");
    document.title = "SELFTEST DONE";
    renderer.setAnimationLoop(() => frame());
  }

  // ?auto=1：每个区块拍几张：区块自带的验收机位（walk 文件里的 shots），再从出生点按四个方向的跟随镜头各拍一张
  async function autoShots() {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    status.style.display = "none";
    const slow = loc.splats?.length > 0;   // 泼溅要等加载和排序
    exitsOff = true;
    await wait(slow ? 9000 : 1500);
    for (const zid of Object.keys(loc.zones)) {
      await enterZone(zid); await wait(slow ? 2000 : 600);
      for (const [k, yaw] of [["后", 0], ["右", Math.PI / 2], ["前", Math.PI], ["左", -Math.PI / 2]]) {
        cam.yaw = player.rotation.y + Math.PI + yaw; cam.cur = null; cam.off = { yaw: 0, pitch: 0 }; cam.inited = false;
        for (let i = 0; i < 60; i++) frame(1 / 60);   // 跑一秒让镜头躲墙的偏转稳下来
        await wait(slow ? 1500 : 300);
        await save(`tour_${loc.id}_${zid}_跟随${k}`);
      }
      // 药郎站到每个观景点上，用这个区块真实的镜头规则拍一张（泼溅区块的安全圈 / 轨道就靠这几张验）
      for (const [n, p] of Object.entries(Z.views)) {
        player.position.set(p[0], 0, p[1]); stand();
        cam.inited = false; cam.cur = null;
        for (let i = 0; i < 90; i++) frame(1 / 60);
        await wait(slow ? 1500 : 300);
        await save(`tour_${loc.id}_${zid}_观景点${n}`);
      }
      for (const s of Z.walk.shots || []) {
        player.position.set(s.player[0], 0, s.player[1]); stand(); player.rotation.y = s.player[2] || 0;   // stand：坂井家玄关土间低 0.36 米，不贴地会飘
        renderer.setAnimationLoop(null);
        P.play("idle"); for (let i = 0; i < 40; i++) P.update(1 / 60);   // 一小步一小步推：一次推 0.5 秒弹簧骨会甩飞，姿势像蹲着侧身
        camera.position.set(...s.cam); camera.lookAt(...s.look); camera.updateMatrixWorld();
        cam.updateCutout(player); post.render(); await wait(200);
        const data = renderer.domElement.toDataURL("image/jpeg", 0.92);
        await fetch("/__shot", { method: "POST", body: JSON.stringify({ name: `tour_${loc.id}_${zid}_${s.name}`, data }) });
        renderer.setAnimationLoop(() => frame());
      }
    }
    document.title = "DONE";
    await save(`tour_${loc.id}__done`);   // 收工标记：tools/tour_shots.sh 等到这个文件才停，然后删掉它
  }
}
