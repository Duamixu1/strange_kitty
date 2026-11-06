import * as THREE from "three";
import { toast, card, flash } from "./ui.js";
import { makeInkMonster, loadMonster, MononokeFx, MONSTERS, HALO_TEX } from "./mononoke_fx.js";

// 物怪出没（docs/18_物怪出没方案.md，11-03 用户拍板）：游览时偶尔来一段的小插曲，没有血条、不会输。
//   预兆（天秤抖、铃响、屋里暗一点，药郎停下察觉）→ 现身（物怪从墨里浮出来）→ 缠斗（绕着飘、蓄力 0.8 秒扑过来；
//   闪避躲开，没闪开药郎用袖挡退两步；趁它扑空落地投札最容易钉中）→ 三张札钉中依次浮出 形 / 真 / 理 → 札阵围住，
//   拔剑键亮 → 退魔（第一次完整 10 秒，之后 3 秒短版）→ 化墨散掉，掉一张执念物卡收进图鉴。
//   60 秒没打完或者药郎跑远了，物怪自己沉回墨里。打完或退走以后冷却 2~3 分钟；同时最多一只；菜单"怪"钮能关。
// 出生点：区块里写 mononoke: [[x, z], ...]（场景线标在地方够大、镜头转得开的地方），没有就不在这个区块出。
//   ?mononoke=any 不看出生点，在药郎前方自己找一块空地（开发用）；?mononoke=now 进来 3 秒就出一只；?mononoke=<id>（noppera、nue……）3 秒后出指定那只。
// 全按 dt 推（不用 setTimeout），自测里一帧一帧推也对得上。
// 动作：角色线的新动作（docs/17 新的一节）到了就用，没有的先拿现成的顶上（PLACEHOLDER），动作名和出手时间一换就行。

const COOL = [120, 180], FIRST = [40, 80], LIMIT = 60, RETRY = 20;
const KANJI = ["形", "真", "理"];
// 投札：动作名、出手（札离手）的秒数、是不是只带上半身（边走边投）。第三张固定撒一扇
const THROWS = {
  flick: { clip: "ofuda_flick_k", release: 0.33, upper: true },   // 出手时间是角色线量的（17 第十五节）
  spin: { clip: "ofuda_spin_k", release: 0.5, upper: false },
  fan: { clip: "ofuda_fan_k", release: 0.5, upper: false, fan: true },
};
const PLACEHOLDER = { throw: { clip: "reach_k", release: 0.35, speed: 1.6, upper: true }, sense: "scale_look_k" };
// 跳（K）和瞬移（L），只在缠斗里用（11-04 你定的）。时间点是秒：up 离地、down 落地；out 人消失、in 在新位置现身。
// 时间点是角色线 11-04 交的 jump_k / blink_k（docs/17 第十七节）；模型里没有这两段时跳用 ready 姿势、瞬移用 dodge_back_k 占位
const JUMP = { clip: "jump_k", dur: 0.75, up: 0.17, down: 0.54, h: 0.7 };
const BLINK = { clip: "blink_k", out: 0.15, in: 0.25, dist: [2.4, 2, 1.6] };
// okuri：没有怨、只是在等在想的（小化猫等人喂、白化猫想回家、青座敷想有人找他玩）——形真理齐了剑不出鞘，X 改成"送"它走（11-05 用户说
//   X 斩小猫"像把猫杀了，很可怕"，docs/19 第十节）。其余的照旧拔剑，但斩的是从它身上抽出来的那团怨念（墨），它本身褪成淡光走掉，不再播消散。
// 物怪：id → 默认名字、执念物（占位，text.json 的 mononoke.<text 或 id> 写了就用那边的）。模型和身高在 mononoke_fx.js 的 MONSTERS。
// 11-04：每个地点从原来一只加到三~五只（角色线的四只新物怪、三只变体），出哪只随机抽，见 choose()
const MONO = {
  bakeneko: { name: "化猫", item: "猫铃", text: "sakai" },
  bakeneko_shiro: { name: "白化猫", item: "白猫的项圈", okuri: true },
  bakeneko_ko: { name: "小化猫", item: "三只小铃", okuri: true },
  nue: { name: "鵺", item: "黑羽" },
  umibozu: { name: "海坊主", item: "断了的念珠", zones: ["sakai/omote", "wanya/soto"] },   // 只在外景（坂井家门前、万屋雨夜门前）：2.2 米在屋里顶到天花板
  zashiki: { name: "座敷童子", item: "红手鞠", text: "wanya" },
  zashiki_ao: { name: "青座敷", item: "青手鞠", okuri: true },
  noppera: { name: "无面", item: "白漆面" },
  karakasa: { name: "唐伞", item: "破纸伞", text: "ooku" },
  karakasa_kuro: { name: "黑唐伞", item: "黑伞骨", charge: 0.72 },   // 蓄力短一成（角色线建议）
  hinezumi: { name: "火鼠", item: "焦了的鼠皮" },
};
export const ROSTER = {   // 每个地点能出哪些；第一只是原作那只，这个地点第一次遭遇一定是它
  sakai: ["bakeneko", "bakeneko_shiro", "bakeneko_ko", "nue", "umibozu"],
  wanya: ["zashiki", "zashiki_ao", "noppera", "umibozu"],
  ooku: ["karakasa", "karakasa_kuro", "hinezumi"],
  fuenokouji: ["nue", "noppera", "bakeneko_shiro"],   // 笛小路家（docs/22）：本命鵺；打完以后随机出无面（"每个人看见的样子不一样"）、白化猫（雪）
};
const LEGACY = { sakai: "bakeneko", wanya: "zashiki", ooku: "karakasa" };
const LOC_NAME = { sakai: "坂井家", wanya: "万屋", ooku: "大奥", fuenokouji: "笛小路家" };   // 11-04 以前图鉴记的是地点
const SINK = new Set(["umibozu"]);   // 消散是沉回去，墨往下散
// 地板、墙都暗的区块：物怪边缘透一层暖光、身后托一团淡光晕，不然黑猫和地板分不开（11-04 用户截图：坂井家客间；
// 先做的硬勾边用户嫌生硬，改成光）。其他区块不加
const RIM_ZONES = new Set(["sakai/kyakuma"]);
const STORE = { on: "mononoke_tour_mk", exo: "mononoke_tour_exo", zukan: "mononoke_tour_zukan", tut: "mononoke_tour_tut", okuri: "mononoke_tour_okuri" };
const ls = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
const rnd = (a, b) => a + Math.random() * (b - a);
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

/**
 * ctx（tour.js 给）：scene camera player P audio loc texts touch mode("any" / "now" / null)
 *   zone() col() free()（没在走剧情、没开卡、没拔剑）stopWalk() turnToward(yaw, rate, dt) gloom(0~1) shake(秒)
 *   drawSword({ short, face, onSlash, onEnd }) stat(path, title)
 */
export function createEncounter(ctx) {
  const { player, P, audio } = ctx;
  const fx = new MononokeFx(ctx.scene, ctx.camera);
  const ink = document.getElementById("mkink");
  let on = ls.get(STORE.on) !== "0";
  const pinned = MONO[ctx.mode] ? ctx.mode : null;   // ?mononoke=<id>：试玩指定那只，进来 3 秒就出
  let st = "idle", T = 0, wait = ctx.mode === "now" || pinned ? 3 : rnd(...FIRST);
  let flipCD = 0, mon = null, sub = "orbit", subT = 0, pins = 0, fightT = 0, orbitA = 0, orbitC = 0, orbitDir = 1, nextCharge = 0;
  let lungeFrom = new THREE.Vector3(), lungeTo = new THREE.Vector3(), hold = 0, inv = 0, dodgeCD = 0, throwCD = 0;
  let tutOpen = false, camSnap = false, air = null, blinkS = null, jumpCD = 0, blinkCD = 0;
  let slide = null, pendingThrow = null, omenAt = null, gloom = 0, retreatWhy = "";
  const proxy = new THREE.Object3D(), tmp = new THREE.Vector3();
  // 物怪模型：进地点以后在后台加载下一只要出的（preload），打完不扔、下次接着用；没下完先用墨影
  const cache = {}, loading = {};
  const load = (id) => { if (!loading[id] && ctx.loader) loading[id] = loadMonster(ctx.loader, ctx.assetUrl, id).then((m) => { m.cached = true; return (cache[id] = m); }).catch((e) => { console.warn("物怪模型加载失败，用墨影", id, e); return null; }); return loading[id] || Promise.resolve(null); };
  const roster = () => ROSTER[ctx.loc.id] || ROSTER.sakai;
  const zukan = () => { let z = []; try { z = JSON.parse(ls.get(STORE.zukan) || "[]"); } catch {} return [...new Set(z.map((x) => LEGACY[x] || x))]; };
  const fits = (id) => !MONO[id].zones || MONO[id].zones.includes(`${ctx.loc.id}/${ctx.zone()?.id}`);
  // 下一只出哪只：这个地点的原作那只还没退过就先出它；之后没收进图鉴的权重 3、收过的 1，不连着出同一只
  let cur = null, nextId = null, lastId = null;
  // 11-05（docs/19）：有案子的地点，原作那只是"本命"，形真理查齐了才在指定区块出（startBoss），随机不出它；第一次随机出 firstRandom（坂井家小化猫）
  const allow = (id) => ctx.allowRandom?.(id) ?? true;
  function choose() {
    const r0 = roster(), r = r0.filter(allow), z = zukan(), fr = ctx.firstRandom?.();
    if (fr) { if (r.includes(fr) && !z.includes(fr)) return fr; } else if (r.includes(r0[0]) && !z.includes(r0[0])) return r0[0];
    let pool = r.filter((id) => id !== lastId); if (!pool.length) pool = r.length ? r : r0;
    const w = pool.map((id) => (z.includes(id) ? 1 : 3));
    let x = Math.random() * w.reduce((a, b) => a + b, 0);
    for (let i = 0; i < pool.length; i++) if ((x -= w[i]) < 0) return pool[i];
    return pool[0];
  }
  /** 进地点 / 自测：在后台下好下一只（传 id 就下那只） */
  const preload = (id) => { id ||= pinned; if (!id) nextId ||= choose(); return Promise.all([load(id || nextId), load(roster()[0])]).then(([m]) => m); };
  // 字：这个地点的本命（case.mononoke）用地点那份（鵺在笛小路家读 mononoke.fuenokouji，在坂井家随机出时读 mononoke.nue）
  const textKey = () => { const d = MONO[cur] || MONO.bakeneko; return ctx.loc.case?.mononoke === cur && ctx.texts[`mononoke.${ctx.loc.id}`] ? ctx.loc.id : d.text || cur; };
  const M = () => { const d = MONO[cur] || MONO.bakeneko; return { ...d, kind: MONSTERS[cur]?.mask || "cat", ...(ctx.texts[`mononoke.${textKey()}`] || {}) }; };
  const has = (clip) => P.has(clip);
  const yawTo = (p) => Math.atan2(p.x - player.position.x, p.z - player.position.z);
  const floorAt = (x, z) => ctx.col()?.floorY(x, z) ?? 0;
  const setState = (s) => {
    st = s; T = 0; document.body.classList.toggle("encounter", ["appear", "fight", "sealed"].includes(s)); document.body.classList.toggle("mk-ready", s === "sealed");
    const b = document.querySelector("#pad .b-sword"); if (b) b.textContent = s === "sealed" && M().okuri ? "送" : "拔剑";   // 手机：没有怨的那几只，钮上写"送"
  };
  // 褪色：物怪本体（toon 材质的 uPale）0 = 原样，1 = 一团浅色的光
  let pale = 0, paleTo = 0;
  const setPale = (v) => { pale = v; mon?.group.traverse((o) => { if (o.isMesh && o.material.uniforms?.uPale) o.material.uniforms.uPale.value = v; }); };

  // ---- 出生点：区块的 mononoke 列表里，离药郎 2.5~7 米、尽量在他前面的一个；any 模式在前方 3.5 米附近找空地 ----
  function pickSpawn(any = !!ctx.mode) {
    const Z = ctx.zone(), col = ctx.col(); if (!Z || !col) return null;
    const f = ctx.cam().forward, px = player.position.x, pz = player.position.z, face = Math.atan2(f.x, f.z);   // "前方"按镜头看的方向：物怪出在画面里、面具朝着镜头
    const score = ([x, z]) => { const d = Math.hypot(x - px, z - pz); if (d < 2.5 || d > 7) return -1; return 2 + Math.cos(wrap(Math.atan2(x - px, z - pz) - face)) - Math.abs(d - 3.5) * 0.3; };
    let pts = (Z.mononoke || []).map((p) => [p[0], p[1]]);
    if (!pts.length && any) {
      for (let i = 0; i < 16; i++) { const a = face + (i % 2 ? 1 : -1) * Math.ceil(i / 2) * (Math.PI / 8); for (const d of [3.5, 3, 4.2, 2.6]) pts.push([px + Math.sin(a) * d, pz + Math.cos(a) * d]); }
      pts = pts.filter(([x, z]) => [0, 1, 2, 3, 4, 5].every((k) => col.canStand(x + Math.sin(k) * 0.6, z + Math.cos(k) * 0.6)));
    }
    pts = pts.filter(([x, z]) => col.canStand(x, z)).map((p) => [p, score(p)]).filter(([, s]) => s >= 0).sort((a, b) => b[1] - a[1]);
    return pts.length ? pts[0][0] : null;
  }

  function start(any, want, at) {
    if (st !== "idle" || !ctx.free()) return false;
    const sp = at && ctx.col()?.canStand(at[0], at[1]) ? at : pickSpawn(any); if (!sp) return false;
    // 出哪只：指定的 > 排好的下一只（这个区块能出、模型下好了）> 别的下好了的 > 原作那只（没下好就是墨影）
    nextId ||= choose();
    cur = want || pinned || [nextId, ...roster()].find((id) => allow(id) && fits(id) && cache[id]) || roster().find((id) => allow(id) && fits(id)) || roster()[0];
    lastId = cur; nextId = choose(); load(nextId);   // 趁冷却在后台下好下一只
    const m = M();
    mon = cache[cur] || makeInkMonster(m.kind);
    mon.reset?.();
    const glow = RIM_ZONES.has(`${ctx.loc.id}/${ctx.zone()?.id}`);
    mon.group.traverse((o) => { if (o.isMesh && o.material.uniforms?.uRim) o.material.uniforms.uRim.value = glow ? 0.75 : 0; });
    clearHalo(); if (glow) addHalo();
    pale = paleTo = 0; setPale(0);
    mon.group.position.set(sp[0], floorAt(sp[0], sp[1]), sp[1]); mon.hover = mon.real ? 1.15 : -0.5; mon.fade = mon.real ? 1 : 0; mon.squash = mon.glow = mon.stretch = 0; mon.group.visible = false;
    ctx.scene.add(mon.group);
    pins = 0; fightT = 0; hold = 0; inv = 0; pendingThrow = null; slide = null; sub = "orbit"; subT = 0; land(); blinkCD = 0;
    omenAt = player.position.clone();
    ctx.stopWalk();
    setState("omen");
    P.play(has("sense_k") ? "sense_k" : PLACEHOLDER.sense, 0.3); hold = 1.5;
    audio.play("omen"); audio.play("scaleBell", 4, 0.1);   // 天秤上的小铃跟着抖响
    ctx.stat(`物怪/${ctx.loc.id}/${cur}`, `物怪出没 · ${m.name}`);
    return true;
  }

  function appear() {
    setState("appear");
    mon.group.visible = true; mon.resetTrail(); mon.play("appear");
    P.setIdle("ready_k");   // 缠斗时站着是戒备姿势
    fx.splat(tmp.copy(mon.group.position).setY(mon.group.position.y + 0.1), 18, { up: 0.6, spread: 1.4 });
    audio.play("appear");
    if (!ctx.camSaved && ctx.cam().dist) { ctx.camSaved = ctx.cam().dist; ctx.cam().dist = Math.min(ctx.cam().maxDist ?? 99, ctx.cam().dist * 1.2); }   // 镜头稍微拉开，人和物怪都进画面
    orbitA = Math.atan2(mon.group.position.x - player.position.x, mon.group.position.z - player.position.z);
    const cf = ctx.cam().forward; orbitC = Math.atan2(cf.x, cf.z);   // 绕圈的范围按现身那一刻镜头看的方向定下来，之后不跟镜头（镜头会转去过肩，跟着就互相追着转）
    if (ls.get(STORE.tut) === "1") toast(ctx.touch ? `${M().name}现身 · 点「札」投札，「闪」「跳」「瞬」躲开` : `${M().name}现身 · J 投札 · 空格闪避 · K 跳 · L 瞬移`, 3600);   // 第一次不弹，教学卡讲
  }

  // 光晕：每只（一群的话每只小猫）身后一张淡光贴片，每帧挪到"物怪背后、离镜头远一点"的位置，被身体挡住的地方不画，就只在轮廓外透出来
  let halos = [], haloTex = null;
  const haloAt = new THREE.Vector3(), haloDir = new THREE.Vector3();
  function addHalo() {
    haloTex ||= HALO_TEX();
    const h = mon.height || 1, tg = mon.swarm ? mon.group.children.slice() : [mon.group];
    halos = tg.map((o) => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, transparent: true, depthWrite: false, opacity: 0 }));
      sp.scale.setScalar(h * 1.5);   // 亮的部分半径约 0.55 个身高，和中心一样高：碰不到地板 sp.frustumCulled = false; ctx.scene.add(sp);
      return { sp, o, h };
    });
  }
  function clearHalo() { for (const x of halos) { ctx.scene.remove(x.sp); x.sp.material.dispose(); } halos = []; }
  function updateHalo() {
    const show = mon.group.visible && ["appear", "fight", "sealed", "exorcise", "vanish", "okuri", "release"].includes(st);
    for (const x of halos) {
      x.o.getWorldPosition(haloAt); haloAt.y += x.h * 0.58;
      haloDir.subVectors(haloAt, ctx.camera.position).normalize();
      x.sp.position.copy(haloAt).addScaledVector(haloDir, x.h * 0.3);
      x.sp.material.opacity = show ? Math.min(1, mon.fade) * 0.85 : 0;
    }
  }
  function end(why) {
    clearHalo();
    if (tutOpen) tutClose(true);
    needEl?.classList.remove("show");
    land(); fx.clear();
    if (mon) { setPale(0); ctx.scene.remove(mon.group); if (!mon.cached) mon.dispose(); mon = null; }
    pale = paleTo = 0;
    if (ctx.camSaved) { ctx.cam().dist = ctx.camSaved; ctx.camSaved = null; }
    setState("idle"); wait = why === "cancel" ? 60 : rnd(...COOL);
    P.setIdle(null);
    if (why === "done" && has("settle_k")) P.play("settle_k", 0.3); else P.play("idle", 0.4);   // 打完收势：低头、整一下袖子
  }

  // ---- 玩家的操作 ----
  function throwOfuda() {
    if (!["fight"].includes(st) || hold > 0 || throwCD > 0 || !mon) return;
    const kind = pins === 2 ? "fan" : Math.random() < 0.6 ? "flick" : "spin";
    let T0 = THROWS[kind], clip = T0.clip, speed = 1, upper = T0.upper, release = T0.release;
    if (!has(clip)) { const ph = PLACEHOLDER.throw; clip = ph.clip; speed = ph.speed; upper = ph.upper; release = ph.release / speed; }
    ctx.stopWalk();
    if (upper) P.playUpper(clip, { speed }); else { P.play(clip, 0.12, { speed }); hold = P.duration(clip) / speed; }
    pendingThrow = { t: release, fan: !!T0.fan, face: yawTo(mon.group.position) };
    throwCD = 0.55;
  }
  function release(fan) {
    if (!mon) return;
    const from = P.hand.getWorldPosition(new THREE.Vector3());
    // 中不中：扑空刚落地 / 被钉住那一下一定中；蓄力时一半；飘着的时候它会躲
    const p = sub === "land" || sub === "hit" ? 1 : sub === "charge" ? 0.5 : 0.22, hit = Math.random() < p && pins < 3;
    audio.play("ofuda");
    const target = (v) => mon ? mon.center(v) : v.copy(from);
    const count = fan ? 5 : 1;
    for (let i = 0; i < count; i++) {
      const main = i === Math.floor(count / 2);
      const spread = (i - (count - 1) / 2) * 0.35, side = new THREE.Vector3();
      const tf = fan && !main ? (v) => { target(v); side.set(Math.cos(player.rotation.y), 0, -Math.sin(player.rotation.y)).multiplyScalar(spread); return v.add(side); } : target;
      fx.throw(from, tf, main ? hit : false, main ? (ok, at) => onArrive(ok, at) : null, { delay: fan ? Math.abs(spread) * 0.08 : 0 });
    }
  }
  function onArrive(ok, at) {
    if (!mon || st !== "fight") return;
    if (!ok) { if (sub === "orbit") { orbitDir *= -1; mon.squash = 0.3; } return; }   // 擦过去：飘着的时候它往另一边一闪
    pins++;
    fx.pin(mon, at); fx.splat(at, 12); mon.onPin?.();   // 一群的：钉中的那只定住，下一张打下一只
    mon.squash = 1; sub = "hit"; subT = 0; mon.play("hit");
    audio.play("pin"); audio.play("kanji", pins - 1);
    const m = M(), lines = [m.katachi, m.makoto, m.kotowari];
    fx.kanji(KANJI[pins - 1], lines[pins - 1] || (pins === 1 ? `形：${m.name}` : ""), mon.center(new THREE.Vector3()));
    ctx.shake(0.12);
  }
  function dodge() {
    if (st !== "fight" || dodgeCD > 0 || (hold > 0 && !pendingThrow)) return;
    const away = mon ? yawTo(mon.group.position) + Math.PI : player.rotation.y + Math.PI;
    // 物怪在蓄力、扑过来时往旁边闪（离它扑的线远），其他时候往后撤；动作没有的先只做位移
    const kind = sub === "charge" || sub === "lunge" ? (Math.random() < 0.5 ? "L" : "R") : "back";
    const clip = kind === "back" ? "dodge_back_k" : kind === "L" ? "dodge_left_k" : "dodge_right_k";
    const dir = kind === "back" ? away : yawTo(mon.group.position) + (kind === "L" ? Math.PI / 2 : -Math.PI / 2);
    player.rotation.y = yawTo(mon.group.position);
    if (has(clip)) P.play(clip, 0.08); else P.play("idle", 0.1);
    slide = { dir, dist: 0.6, t: -0.08, dur: 0.32 };   // 角色线给的：0.08~0.4 秒挪 0.6 米
    hold = has(clip) ? P.duration(clip) : 0.42; inv = 0.5; dodgeCD = 0.7; pendingThrow = null;
    audio.play("dodge");
  }
  // 跳：原地跳起 0.7 米、往后飘 0.3 米，离地到落地之间不会被扑中（物怪从脚下扑过去）
  function jump() {
    if (st !== "fight" || air || blinkS || jumpCD > 0 || (hold > 0 && !pendingThrow)) return;
    const real = has(JUMP.clip), dur = real ? P.duration(JUMP.clip) : JUMP.dur;
    const face = yawTo(mon.group.position);
    player.rotation.y = face;
    P.play(real ? JUMP.clip : "idle", 0.06);
    air = { t: 0 };
    slide = { dir: face + Math.PI, dist: 0.3, t: -JUMP.up, dur: JUMP.down - JUMP.up };
    hold = dur; inv = JUMP.down + 0.05; jumpCD = 0.9; pendingThrow = null;
    audio.play("jump");
  }
  // 瞬移：化成一把札纸散掉，在 2.4 米外（按着方向键就往那边，不按就往物怪的侧面）现身；冷却 3 秒
  function blink() {
    if (st !== "fight" || air || blinkS || (hold > 0 && !pendingThrow)) return;
    if (blinkCD > 0) { toast(`瞬移还要 ${Math.ceil(blinkCD)} 秒`, 900); return; }
    const to = blinkTarget(); if (!to) { toast("这里太窄，瞬移不开", 1200); return; }
    const real = has(BLINK.clip);
    player.rotation.y = yawTo(mon.group.position);
    P.play(real ? BLINK.clip : "dodge_back_k", 0.06);
    blinkS = { t: 0, to, real, out: real ? BLINK.out : 0.1, in: real ? BLINK.in : 0.3, gone: false, back: false };
    hold = real ? P.duration(BLINK.clip) : 0.55; inv = blinkS.in + 0.25; blinkCD = 3; pendingThrow = null; slide = null;
    audio.play("blink");
  }
  function blinkTarget() {
    const col = ctx.col(), mp = mon.group.position, px = player.position.x, pz = player.position.z;
    const toM = yawTo(mp), side = Math.random() < 0.5 ? 1 : -1, want = ctx.moveYaw?.();
    const dirs = want != null ? [want, want + 0.5, want - 0.5] : [];
    dirs.push(toM + side * Math.PI / 2, toM - side * Math.PI / 2, toM + side * 2.2, toM - side * 2.2, toM + Math.PI);
    // 能去的点里挑：按着的方向优先，其次落在画面里的（固定机位远景时别瞬移到画面外），再按顺序
    let best = null, bs = -1;
    dirs.forEach((a, i) => { for (const d of BLINK.dist) {
      const x = px + Math.sin(a) * d, z = pz + Math.cos(a) * d, dm = Math.hypot(x - mp.x, z - mp.z);
      if (dm < 1.4 || dm > 7) continue;
      // 一路上都要站得住：不穿墙瞬移到隔壁屋
      let ok = true; for (let s = 0.3; s <= d && ok; s += 0.3) ok = col.canStand(px + Math.sin(a) * s, pz + Math.cos(a) * s);
      if (!ok || ![0, 1, 2, 3, 4, 5].every((k) => col.canStand(x + Math.sin(k) * 0.3, z + Math.cos(k) * 0.3))) continue;
      const y = floorAt(x, z), v = tmp.set(x, y + 0.9, z).project(ctx.camera), inView = v.z < 1 && Math.abs(v.x) < 0.7 && Math.abs(v.y) < 0.8;
      const sc = (want != null && i < 3 ? 10 : 0) + (inView ? 5 : 0) + d - i * 0.1;
      if (sc > bs) { bs = sc; best = new THREE.Vector3(x, y, z); }
      break;   // 这个方向最远能去的就是它
    } });
    return best;
  }
  // 遭遇收掉时：人落回地上、现出来
  function land() {
    if (air || blinkS) { player.visible = true; player.position.y = floorAt(player.position.x, player.position.z); }
    air = null; blinkS = null;
  }
  const chest = (p) => tmp.set(p.x, p.y + 1.1, p.z);
  // 第一次遭遇的教学卡（11-04 用户定的）：物怪现身后整个遭遇停住，一页讲一个键，左右翻（1 / 6），最后一页"开打"；只教一次。
  // 翻页：← → / A D / 点箭头；空格、回车、E 下一页；Esc 或"跳过"直接开打
  const TUT = [
    { key: null, name: "斩物怪，先知道它的形、真、理", line: "投札钉中它三次，三个字就齐了" },
    { key: ["J", "札"], name: "投札", line: "钉中一张，浮出一个字", tip: "它扑空落地那一下，最好钉" },
    { key: ["空格", "闪"], name: "闪避", line: "它发红发抖，就要扑过来了" },
    { key: ["K", "跳"], name: "跳", line: "人在空中，它扑不到" },
    { key: ["L", "瞬"], name: "瞬移", line: "化成札纸，闪到两米外", tip: "3 秒才能再用一次" },
    { key: ["X", "拔剑"], name: "拔剑", line: "形、真、理齐了，剑才拔得出来" },
  ];
  let tutEl = null, tutPage = 0;
  function tutorial() {
    tutOpen = true; tutPage = 0; document.body.classList.add("mk-tut");
    if (!tutEl) {
      tutEl = document.createElement("div"); tutEl.id = "mktut";
      tutEl.innerHTML = `<div class="box paper"><div class="place">物怪出没 · 第一次</div><button class="skip">跳过</button>
        <div class="key"></div><div class="name"></div><div class="line"></div><div class="tip"></div>
        <div class="nav"><button class="prev" aria-label="上一页">‹</button><span class="no"></span><button class="next" aria-label="下一页">›</button></div></div>`;
      document.body.appendChild(tutEl);
      tutEl.addEventListener("pointerdown", (e) => e.stopPropagation());
      tutEl.querySelector(".prev").onclick = () => tutGo(-1);
      tutEl.querySelector(".next").onclick = () => tutGo(1);
      tutEl.querySelector(".skip").onclick = () => tutClose();
    }
    tutShow(); tutEl.classList.add("show");
  }
  function tutShow() {
    const p = TUT[tutPage], q = (c) => tutEl.querySelector(c), last = tutPage === TUT.length - 1;
    q(".key").textContent = p.key ? p.key[ctx.touch ? 1 : 0] : "形 真 理";
    q(".key").className = `key${p.key ? "" : " intro"}${p.key && !ctx.touch && p.key[0].length > 1 ? " wide" : ""}`;
    q(".name").textContent = p.name; q(".line").textContent = p.line; q(".tip").textContent = p.tip || "";
    q(".no").textContent = `${tutPage + 1} / ${TUT.length}`;
    q(".prev").disabled = tutPage === 0;
    q(".next").textContent = last ? "开打" : "›"; q(".next").classList.toggle("go", last);
  }
  function tutGo(d) {
    if (tutPage + d >= TUT.length) { tutClose(); return; }
    tutPage = Math.max(0, tutPage + d); tutShow(); audio.play("tick");
  }
  function tutClose(keep) {
    tutEl?.classList.remove("show"); document.body.classList.remove("mk-tut");
    if (!tutOpen) return;
    tutOpen = false; if (keep) return;   // 遭遇被收掉了（换区块）：下次还教
    ls.set(STORE.tut, "1");
    if (st === "appear") { setState("fight"); sub = "orbit"; subT = 0; nextCharge = rnd(1.8, 2.8); }
  }
  function tutKey(code) {
    if (!tutOpen) return false;
    if (code === "ArrowRight" || code === "KeyD" || code === "Space" || code === "Enter" || code === "KeyE") tutGo(1);
    else if (code === "ArrowLeft" || code === "KeyA") tutGo(-1);
    else if (code === "Escape") tutClose();
    return true;   // 卡开着时别的键都不管
  }
  // 形真理没齐就按 X：屏幕中间亮出三格，齐了的红、没齐的空着，抖一下，"咔"一声拔不出
  const needEl = (() => {
    const mk = document.getElementById("mk"); if (!mk) return null;
    const d = document.createElement("div"); d.className = "need";
    d.innerHTML = `<div>${KANJI.map((c) => `<span class="k">${c}</span>`).join("")}</div><div class="t"></div>`;
    mk.appendChild(d); return d;
  })();
  let needT = null;
  function needHint() {
    if (!needEl) { toast(`形、真、理还差 ${3 - pins} 样，剑拔不出来`); return; }
    needEl.querySelectorAll(".k").forEach((e, i) => e.classList.toggle("got", i < pins));
    needEl.querySelector(".t").textContent = pins ? `还差 ${3 - pins} 样，剑拔不出来 · 先投札钉中它` : "形、真、理一样都不知道，剑拔不出来 · 先投札钉中它";
    needEl.classList.remove("show"); void needEl.offsetWidth; needEl.classList.add("show");
    clearTimeout(needT); needT = setTimeout(() => needEl.classList.remove("show"), 2000);
    audio.play("locked"); ctx.shake(0.1);
  }
  function guard() {
    const back = yawTo(mon.group.position) + Math.PI;
    player.rotation.y = yawTo(mon.group.position);
    if (has("guard_k")) P.play("guard_k", 0.08); else P.play("idle", 0.1);
    slide = { dir: back, dist: 0.35, t: -0.05, dur: 0.35 };   // 角色线给的：0.05~0.4 秒往后 0.35 米（退多了会顶到镜头那边的墙，镜头挤到头发里）
    hold = has("guard_k") ? P.duration("guard_k") : 0.6; inv = 0.8; pendingThrow = null;
    audio.play("guard"); ctx.shake(0.25);
  }
  function exorcise() {
    if (st !== "sealed") return false;
    if (M().okuri) return okuri();
    const first = ls.get(STORE.exo) !== "1";
    setState("exorcise");
    ctx.drawSword({
      short: !first, face: yawTo(mon.group.position),
      onAwaken: (dur) => { fx.peel(mon, dur); paleTo = 0.55; mon.play("idle", 0.4); },   // 妖化那一刻：怨念从它身上被抽出来
      onSlash: vanish,
      onEnd: (didSlash) => {
        if (!didSlash) { setState("sealed"); return; }   // 砍下去之前就收手了：札阵还在，再按一次
        if (first) ls.set(STORE.exo, "1");
        letGo();
      },
    });
    return true;
  }
  // 横斩：斩的是浮在它头上的那团怨念（fx.cutGrudge），它本身不播消散，褪成浅色、安静下来，等收剑以后化成魂光走
  function vanish() {
    setState("vanish");
    fx.clearRing(); flash(); fx.cutGrudge(); fx.unpin(); paleTo = 1;
    mon.squash = 0; mon.glow = 0; mon.play("idle", 0.5);
    fx.splat(mon.center(new THREE.Vector3()), 10, SINK.has(cur) ? { up: 0.3, spread: 1.2 } : { up: 1, spread: 0.8, rise: true });
    audio.play("burn");
  }
  // 送（没有怨的）：剑不出鞘。药郎结印、把一张札放到地上，札阵落地变成一圈金线，墨从它身上滴干净，它褪成浅色，化成魂光走
  function okuri() {
    setState("okuri");
    ctx.stopWalk(); player.rotation.y = yawTo(mon.group.position);
    if (has("okuri_k")) { P.play("okuri_k", 0.2); hold = P.duration("okuri_k"); }
    else { P.play(has("seal_k") ? "seal_k" : "idle", 0.2, { from: 0.01 }); hold = 3; okuriSettle = 1.3; }   // from：札阵齐了那下刚播过 seal_k，还没播完时要从头再来一遍
    audio.play("sheathStill"); audio.play("okuri");
    if (ls.get(STORE.okuri) !== "1") { ls.set(STORE.okuri, "1"); toast("剑没有动 · 它身上没有怨", 3000); }
    // okuri_k（角色线 11-05，docs/17 第十八节）：1.92 秒札离手（札阵这时落地），2.3~3.25 秒往后退 0.2 米由代码给
    okuriDrop = has("okuri_k") ? 1.92 : 0.2;
    if (has("okuri_k")) slide = { dir: player.rotation.y + Math.PI, dist: 0.2, t: -2.3, dur: 0.95, linear: true };
    fx.dripOff(mon, 1.9); mon.play("idle", 0.4);
    ctx.stat(`物怪/${ctx.loc.id}/${cur}/送`, `送 · ${M().name}`);
    return true;
  }
  let okuriSettle = 0, okuriDrop = 0;
  // 退魔以后不是一下就完：执念散了，魂光从它消散的地方升起来、慢慢飘走，铃响，底下一句余韵（text.json 的 after），
  // 再掉执念物卡。11-04 用户说"小猫那么可爱，斩杀它很心疼"：小化猫是先亮起一团大的（母猫），三团小的跟上去一起走
  let relDur = 0, relLine = false;
  function letGo() {
    setState("release"); relLine = false;
    fx.clearRing();
    const c = mon.center(new THREE.Vector3()), p = mon.group.position, at = new THREE.Vector3(p.x, Math.max(p.y + 0.6, c.y), p.z);
    const list = mon.swarm
      ? [{ size: 0.85, rise: 0.2, offset: new THREE.Vector3(0, 0.35, 0), life: 4.2 }, ...[0, 1, 2].map((i) => ({ size: 0.4, delay: 0.7 + i * 0.3, follow: 0, life: 4.2 - 0.7 - i * 0.3 + 0.2 }))]
      : [{ size: 0.7, delay: 0.1, life: 3.4, rise: 0.3 }];   // 升得慢一点，屋里也能在画面里多停一会儿
    relDur = fx.souls(at, list);
    audio.play("release", mon.swarm ? 4 : 1);
  }
  async function dropCard() {
    const m = M(), z = zukan();
    ctx.stat(`物怪/${ctx.loc.id}/${cur}/${m.okuri ? "送走" : "退魔"}`, `${m.okuri ? "送走" : "退魔"} · ${m.name}`);
    const fresh = !z.includes(cur);
    if (fresh) { z.push(cur); ls.set(STORE.zukan, JSON.stringify(z)); }
    await card.open({ place: `执念物 · 收进药箱 ${z.length} / ${Object.keys(MONO).length}`, title: m.itemTitle || m.item, body: m.itemBody || `${m.name}留下的东西。（说明待文案线写：text.json 的 mononoke.${m.text || cur}）` });
    if (fresh) ctx.onCollect?.(cur);   // 药箱（medbox.js）：新收的那格亮一下、提示怎么打开
    ctx.onDone?.(cur);   // 引导（guide.js）：本命退了，地点盖"退魔"
  }


  // ---- 每帧 ----
  let cardIn = 0;   // 上色时晚几秒再掉执念物卡
  function update(dt) {
    if (tutOpen) return;   // 教学卡开着：整个遭遇停住
    if (cardIn > 0 && (cardIn -= dt) <= 0) dropCard();
    T += dt; hold = Math.max(0, hold - dt); inv = Math.max(0, inv - dt); dodgeCD = Math.max(0, dodgeCD - dt); throwCD = Math.max(0, throwCD - dt); jumpCD = Math.max(0, jumpCD - dt); blinkCD = Math.max(0, blinkCD - dt);
    document.body.classList.toggle("blink-cd", blinkCD > 0);
    const g = st === "idle" || st === "release" ? 0 : st === "omen" ? Math.min(1, T / 1.5) : st === "vanish" ? Math.max(0, 1 - T / 1.5) : 1;   // 魂走的时候屋里亮回来
    gloom += (g - gloom) * (1 - Math.exp(-4 * dt));
    ctx.gloom(gloom); if (ink) ink.style.opacity = (gloom * 0.85).toFixed(3);
    if (st === "idle") {
      if (!on || ctx.noRandom || !ctx.free() || !ctx.zone()) return;
      if (ctx.randomOk && !ctx.randomOk() && !ctx.mode) return;   // 11-05：至少看过两处再出，别一进门还没逛就被打断
      if (!(ctx.zone().mononoke?.length || ctx.mode)) return;
      if ((wait -= dt) <= 0) { if (!start()) wait = RETRY; }
      return;
    }
    if (slide) {
      // 闪避 / 被撞退：在 dur 秒里沿 dir 滑出 dist 米（先快后慢），撞墙就停
      const k0 = Math.max(0, Math.min(1, slide.t / slide.dur)); slide.t += dt; const k1 = Math.max(0, Math.min(1, slide.t / slide.dur));   // t 从负数起：动作开头那几帧先不挪
      const e = slide.linear ? (k) => k : (k) => 1 - (1 - k) * (1 - k), d = (e(k1) - e(k0)) * slide.dist;   // linear：送的后退半步要匀速，脚才不打滑
      const nx = player.position.x + Math.sin(slide.dir) * d, nz = player.position.z + Math.cos(slide.dir) * d, col = ctx.col();
      if (col.canStand(nx, player.position.z)) player.position.x = nx;
      if (col.canStand(player.position.x, nz)) player.position.z = nz;
      player.position.y = floorAt(player.position.x, player.position.z);
      if (k1 >= 1) slide = null;
    }
    if (air) {
      // 抛物线抬人：up~down 之间离地，最高 h 米
      air.t += dt; const k = (air.t - JUMP.up) / (JUMP.down - JUMP.up);
      player.position.y = floorAt(player.position.x, player.position.z) + (k > 0 && k < 1 ? 4 * k * (1 - k) * JUMP.h : 0);
      if (air.t >= JUMP.down) { air = null; audio.play("land"); fx.splat(tmp.copy(player.position).setY(player.position.y + 0.05), 6, { up: 0.3, spread: 0.8 }); }
    }
    if (blinkS) {
      const b = blinkS; b.t += dt;
      if (!b.gone && b.t >= b.out) { b.gone = true; fx.paper(chest(player.position), 16); fx.splat(tmp.copy(player.position).setY(player.position.y + 0.8), 14, { up: 1, spread: 0.9, rise: true }); player.visible = false; }
      if (b.gone && !b.back && b.t >= b.in) {
        b.back = true; camSnap = true; player.position.copy(b.to); if (mon) player.rotation.y = yawTo(mon.group.position); player.visible = true;
        fx.paper(chest(player.position), 10, { inward: true }); fx.splat(tmp.copy(player.position).setY(player.position.y + 0.1), 8, { up: 0.4, spread: 0.9 }); audio.play("blinkIn");
        if (!b.real) P.play("idle", 0.12);
      }
      if (b.back && b.t >= b.in + 0.05) blinkS = null;
    }
    if (pendingThrow) {
      ctx.turnToward(pendingThrow.face = mon ? yawTo(mon.group.position) : pendingThrow.face, 14, dt);
      if ((pendingThrow.t -= dt) <= 0) { const f = pendingThrow.fan; pendingThrow = null; release(f); }
    }
    fx.update(dt);
    if (mon && pale !== paleTo) { const v = pale + (paleTo - pale) * Math.min(1, dt * (paleTo > 0.9 ? 1.6 : 0.9)); setPale(Math.abs(paleTo - v) < 0.004 ? paleTo : v); }
    // 天秤抖（预兆和缠斗时一直微微抖，札钉齐了停）
    const scale = P.props.find((p) => p.id === "scale")?.prop;
    if (scale && (st === "omen" || st === "fight")) scale.rotation.z = Math.sin(T * 38) * 0.12 * (st === "omen" ? 1 : 0.4);   // 平时天秤归 guide.js 管（朝没找的东西倾）
    if (!mon) return;
    if (halos.length) updateHalo();
    const mp = mon.group.position, toP = Math.hypot(player.position.x - mp.x, player.position.z - mp.z);
    mon.group.rotation.y = Math.atan2(player.position.x - mp.x, player.position.z - mp.z);
    // 过肩镜头：镜头慢慢转到"物怪 → 药郎"这条线后面偏 35°（靠现在镜头那一侧），人不挡物怪；玩家自己拖镜头时 tour.js 不转
    if (["appear", "fight", "sealed"].includes(st)) {
      const back = Math.atan2(player.position.x - mp.x, player.position.z - mp.z), cur = ctx.camYaw();
      if (cur !== null) { const side = wrap(cur - back) >= 0 ? 1 : -1; ctx.nudgeCam(back + side * 0.6, dt); }
    }
    switch (st) {
      case "omen":
        if (T > 1.5 && omenAt.distanceTo(player.position) > 2.5) { audio.play("retreat"); toast("天秤不抖了"); end("cancel"); return; }   // 预兆时走开了：不出现
        if (T > 3) appear();
        break;
      case "appear": {
        const k = Math.min(1, T / 1.2);
        mon.hover = -0.5 + 1.65 * (1 - (1 - k) * (1 - k)); mon.fade = k;
        if (T > 0.4) ctx.turnToward(yawTo(mp), 6, dt);
        if (T > 1.2) {
          if (ls.get(STORE.tut) !== "1") { tutorial(); break; }   // 第一次遭遇：物怪浮出来以后先停下，讲一遍按键
          setState("fight"); sub = "orbit"; subT = 0; nextCharge = rnd(1.5, 2.5);
        }
        break;
      }
      case "fight":
        fightT += dt;
        if (fightT > LIMIT || toP > 9) { retreatWhy = toP > 9 ? "far" : "time"; setState("retreat"); audio.play("retreat"); fx.clear(); if (mon.real) mon.hover = 0; break; }
        fightTick(dt, mp, toP);
        break;
      case "sealed":
        // 札阵收紧，物怪被钉在原地打颤；等拔剑
        if (fx.ring) fx.ring.tighten = Math.min(1, fx.ring.tighten + dt * 0.8);
        mon.squash = 0.4 + Math.sin(T * 30) * 0.08; mon.glow = 0.2; mon.hover += (0.9 - mon.hover) * (1 - Math.exp(-3 * dt));
        break;
      case "vanish":
        if (SINK.has(cur) && mon.real) {   // 海坊主：沉回去（往地下降），墨往下散
          mon.fade = Math.max(0, 1 - T / 1.6); mon.hover = Math.min(0, mon.hover) - dt * 1.4;
          if (T > 0.1 && T < 1.1 && Math.random() < dt * 30) fx.splat(tmp.copy(mon.group.position).setY(mon.group.position.y + 0.3), 3, { up: 0.2, spread: 1.2 });
        } else {
          mon.squash = 0; mon.hover += (0.9 - mon.hover) * (1 - Math.exp(-2 * dt));   // 斩完：它还在，褪成浅色、不再打颤，静静浮着
        }
        if (SINK.has(cur) && mon.real && T > 1.3 && mon.group.visible) { mon.group.visible = false; }
        break;
      case "exorcise": mon.squash *= 1 - Math.min(1, dt * 2); break;   // 等 drawSword 的 onAwaken / onSlash；怨念抽走的时候它慢慢不抖了
      case "okuri":
        if (okuriDrop && T >= okuriDrop) {   // 札离手：从右手指尖（R_Fingers_1）飘落到地上，札阵跟着落地亮成一圈
          okuriDrop = 0; const fy = floorAt(mon.group.position.x, mon.group.position.z), b = player.getObjectByName("R_Fingers_1");
          if (b) fx.dropFuda(b.getWorldPosition(new THREE.Vector3()), floorAt(player.position.x, player.position.z));
          fx.ringToFloor(fy);
        }
        if (T > 0.3) paleTo = 1;
        if (T > 1.2 && fx.pinned.length) fx.unpin();   // 墨滴得差不多了，钉着的札也落下来
        mon.squash *= 1 - Math.min(1, dt * 2); mon.glow = 0; mon.hover += (0.9 - mon.hover) * (1 - Math.exp(-2 * dt));
        if (okuriSettle && T > okuriSettle) { okuriSettle = 0; if (has("settle_k")) P.play("settle_k", 0.3); }
        if (T > 2.6) letGo();
        break;
      case "release":
        mon.fade = Math.max(0, mon.fade - dt * 0.8); mon.hover += dt * 0.25; if (mon.fade <= 0) mon.group.visible = false;   // 褪成光的它慢慢缩没、往上飘，魂光同时升起
        if (!relLine && T > 0.8) { relLine = true; const m = M(); fx.kanji("", m.after || "执念散了。它走了。", mon.group.position.clone().setY(mon.group.position.y + 1.2), 3200); }
        if (T > Math.max(3.4, relDur - 0.3)) { const id = cur; end("done"); ctx.onRelease?.(id); cardIn = ctx.recoloring?.() ? 4.2 : 0; if (!cardIn) dropCard(); return; }   // 要上色的地点等颜色洇满再掉卡
        break;
      case "retreat":
        mon.hover -= dt * 1.2; mon.fade = Math.max(0, 1 - T / 1.2);
        if (T > 1.3) { toast(retreatWhy === "far" ? `${M().name}沉回墨里了` : `${M().name}沉回墨里，走了`); end("retreat"); return; }
        break;
    }
    mon?.update(dt);
  }

  // 缠斗里物怪的动作：orbit 绕着飘 → charge 蓄力 0.8 秒 → lunge 扑 0.42 秒 → land 扑空落地 1.5 秒（最好钉；挨撞袖挡完还来得及投）→ orbit；
  // 被钉中 hit 0.6 秒；第三张钉中以后进 sealed
  function fightTick(dt, mp, toP) {
    subT += dt;
    const CH = MONO[cur]?.charge || 0.8;
    mon.glow += ((sub === "charge" ? Math.min(1, subT / CH) : 0) - mon.glow) * Math.min(1, dt * 12);
    mon.stretch += ((sub === "lunge" ? 0.7 : sub === "charge" ? -0.15 : 0) - mon.stretch) * Math.min(1, dt * 14);
    mon.squash = Math.max(0, mon.squash - dt * 2.2);
    const col = ctx.col();
    if (sub === "orbit") {
      // 绕着药郎飘，半径 2.6 米，只在现身时镜头前方左右各 60° 里来回（绕到镜头边上只看见一团黑、面具也背过去了）；
      // 要去的点站不住（墙里、屋外）就掉头
      const rel = wrap(orbitA - orbitC);
      if (Math.abs(rel) > 1.05) { orbitDir = -Math.sign(rel); orbitA -= rel - Math.sign(rel) * 1.05; }
      orbitA += orbitDir * 0.55 * dt; flipCD -= dt;
      // 窄的地方（大奥走廊）：要去的点站不住先缩半径，缩到 1.6 米还不行才掉头，掉头之间隔 0.6 秒（原来每帧掉头，卡在原地抖、一直不扑）
      let R = 2.8, tx, tz;
      for (; R >= 1.6; R -= 0.4) { tx = player.position.x + Math.sin(orbitA) * R; tz = player.position.z + Math.cos(orbitA) * R; if (col.canStand(tx, tz)) break; }
      if (R < 1.6 && flipCD <= 0) { orbitDir *= -1; flipCD = 0.6; }
      const k = 1 - Math.exp(-2.5 * dt);
      mp.x += (tx - mp.x) * k; mp.z += (tz - mp.z) * k; mp.y += (floorAt(mp.x, mp.z) - mp.y) * k;
      mon.hover += (1.15 - mon.hover) * k;
      // 正挡在药郎和镜头一条线上时先不扑（人挡住它）
      if (subT > nextCharge && toP < 4.5 && (Math.abs(rel) > 0.35 || subT > nextCharge + 2.5)) {   // 等太久就不管角度了
        sub = "charge"; subT = 0; audio.play("charge"); mon.play("charge");
        // 蓄力一开始就瞄好：扑向药郎这时的位置，停在他跟前 0.6 米（没闪开就撞上）；不穿过去，不然落在镜头和人之间把人挡住。
        // 蓄力时（物怪发红、抖）闪开，它就扑空
        const dx = player.position.x - mp.x, dz = player.position.z - mp.z, d = Math.hypot(dx, dz) || 1;
        lungeTo.set(player.position.x - dx / d * 0.6, mp.y, player.position.z - dz / d * 0.6);
      }
    } else if (sub === "charge") {
      mp.x += Math.sin(subT * 60) * 0.004;   // 抖一下
      if (subT > CH) {
        sub = "lunge"; subT = 0; audio.play("lunge"); mon.play("lunge");
        lungeFrom.copy(mp);
      }
    } else if (sub === "lunge") {
      const k = Math.min(1, subT / 0.42), e = k * k * (3 - 2 * k);
      mp.lerpVectors(lungeFrom, lungeTo, e); mon.hover += (0.8 - mon.hover) * Math.min(1, dt * 10);
      // 扑的路上离药郎 0.75 米以内、他又没在闪：撞上，袖挡
      if (inv <= 0 && Math.hypot(player.position.x - mp.x, player.position.z - mp.z) < 0.75) guard();
      if (k >= 1) { sub = "land"; subT = 0; mon.squash = 1; fx.splat(tmp.copy(mp).setY(mp.y + 0.2), 8, { up: 0.5, spread: 1 }); }
    } else if (sub === "land") {
      mon.hover += (0.55 - mon.hover) * Math.min(1, dt * 8);
      if (subT > 1.5) { sub = "orbit"; subT = 0; nextCharge = rnd(2.2, 3.8); orbitA = Math.atan2(mp.x - player.position.x, mp.z - player.position.z); }
    } else if (sub === "hit") {
      if (subT > 0.6) {
        if (pins >= 3) {
          setState("sealed"); fx.makeRing(mon); audio.play("seal");
          if (has("seal_k")) { P.play("seal_k", 0.15); hold = P.duration("seal_k"); }
          toast(M().okuri ? (ctx.touch ? "形、真、理齐了 · 它身上没有怨 · 点「送」送它走" : "形、真、理齐了 · 它身上没有怨 · 按 X 送它走")
            : ctx.touch ? "形、真、理齐了 · 点「拔剑」退魔" : "形、真、理齐了 · 按 X 拔剑", 4000);
        } else { sub = "orbit"; subT = 0; nextCharge = rnd(1.8, 3); orbitA = Math.atan2(mp.x - player.position.x, mp.z - player.position.z); }
      }
    }
  }

  return {
    get state() { return st; }, get tutorial() { return tutOpen; }, get tutPage() { return tutPage; }, tutKey, get debug() { return { st, T: +T.toFixed(2), sub, subT: +subT.toFixed(2), pins, hold: +hold.toFixed(2), slide: !!slide, fightT: +fightT.toFixed(1), inv: +inv.toFixed(2), air: !!air, blink: !!blinkS, blinkCD: +blinkCD.toFixed(2), throwCD: +throwCD.toFixed(2), pending: !!pendingThrow }; }, get sub() { return sub; }, get pins() { return pins; }, get monster() { return mon; }, get on() { return on; }, fx,
    /** 正在遭遇（预兆到消散） */
    get active() { return st !== "idle"; },
    /** 掉执念物卡之前那几秒（上色的地点等颜色洇满）：状态已经回 idle，卡还没出 */
    get cardPending() { return cardIn > 0; },
    preload,
    /** 药郎现在能不能自己走（察觉、投札、闪避、袖挡、结印的时候不能） */
    get holding() { return tutOpen || (st === "omen" ? hold > 0 : hold > 0 || !!slide); },
    /** 镜头看哪：遭遇时看药郎和物怪之间偏药郎那边（0.35） */
    camTarget() {
      if (!mon || !["appear", "fight", "sealed", "vanish", "okuri"].includes(st)) return player;
      const fy = floorAt(player.position.x, player.position.z);   // 跳起来时镜头不跟着上下
      proxy.position.set(player.position.x, fy, player.position.z).lerp(tmp.copy(mon.group.position).setY(fy), 0.35); proxy.rotation.copy(player.rotation);
      return proxy;
    },
    update,
    /** 瞬移现身那一帧：镜头直接切过去（取一次就清掉） */
    takeCamSnap() { const s = camSnap; camSnap = false; return s; },
    /** 按键：throw / dodge / jump / blink / sword；返回 true 表示遭遇把这个键用掉了 */
    act(what) {
      if (st === "idle") return false;
      if (tutOpen) return true;
      if (what === "throw") { throwOfuda(); return true; }
      if (what === "dodge") { dodge(); return st !== "idle"; }
      if (what === "jump") { jump(); return true; }
      if (what === "blink") { blink(); return true; }
      if (what === "sword") {
        if (st === "sealed") return exorcise();
        if (st === "fight" || st === "appear" || st === "omen") { needHint(); return true; }
      }
      return false;
    },
    /** 马上出一只（自测、调试）；any = 区块没标出生点也在前方找空地 */
    start: (any = false, id) => start(any || undefined, id),
    /** 本命（guide.js）：模型没下好先下、返回 false 等下次；at 是区块的 bossAt（站不住就按出生点挑）。"怪"开关关着也出 */
    startBoss(id, at) { if (!cache[id]) { load(id); return false; } return start(false, id, at); },
    /** 这个地点能出哪些（自测逐只过一遍） */
    /** 药箱要的：十一只按地点排好，每只的名字、地点、执念物和那几句字，got = 收过 */
    entries() {
      const z = zukan(), seen = new Set(), out = [];
      for (const loc of Object.keys(ROSTER)) for (const id of ROSTER[loc]) {
        if (seen.has(id)) continue; seen.add(id);
        const d = MONO[id], t = ctx.texts[`mononoke.${d.text || id}`] || {};
        const places = Object.keys(ROSTER).filter((l) => ROSTER[l].includes(id)).map((l) => LOC_NAME[l]).join(" · ");
        out.push({ id, got: z.includes(id), place: places, name: t.name || d.name, itemTitle: t.itemTitle || d.item, itemBody: t.itemBody || "", katachi: t.katachi || "", makoto: t.makoto || "", kotowari: t.kotowari || "", after: t.after || "" });
      }
      return out;
    },
    get roster() { return roster().filter(fits); }, get rosterAll() { return roster(); }, get current() { return cur; },
    /** 换区块、离开：直接收掉，不算冷却 */
    reset() { if (st !== "idle") { end("cancel"); wait = rnd(...FIRST) / 2; } },
    toggle() { on = !on; ls.set(STORE.on, on ? "1" : "0"); if (!on) this.reset(); return on; },
  };
}
