/**
 * 玩法逻辑层：状态机、天秤引导、配对、提示。纯函数，不依赖 Three.js。
 * 数据来自 web/src/data/script.json（文字）和 web/src/data/clues.json（线索位置与条件）。
 * 规格见 docs/07_玩法逻辑与攻略.md。
 *
 * 用法：
 *   const g = createGame(script, clues);
 *   g.talk('kame') → { lines, gained }
 *   g.interact('E1') → { ok, lines }
 *   g.put('E1'); g.put('E2'); g.weigh() → { result:'balanced', lights:'kata', line }
 *   g.scaleSignal([x,y,z]) → { target, distance, amplitude, ring }
 *   g.nextStep() → 'pick_E1' 等提示 id（攻略和防卡关用）
 */

export const THREE = ["kata", "makoto", "kotowari"];

export function initialState() {
  return {
    phase: "play",            // play | sword | ending
    zone: "Z0_gate",
    gateOpened: false,
    scaleIntro: false,        // 药贩子说过 scale_first
    met: { asa: false, kame: false, utayama: false },
    has: {},                  // 证物 id → true
    lit: { kata: false, makoto: false, kotowari: false },
    pans: { left: null, right: null },
    ending: null,             // 'A' | 'B'
    lastRing: 0,              // 天秤上一次响的档位
    counters: { wrongPairs: 0, talks: 0 },
    log: [],                  // 事件记录，调试和攻略统计用
  };
}

function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

export function createGame(script, cluesData, state = initialState()) {
  const clues = cluesData.clues;
  const scaleCfg = cluesData.scale;
  const log = (type, data) => state.log.push({ type, ...data });

  function litCount() { return THREE.filter((k) => state.lit[k]).length; }

  function available(id) {
    const c = clues[id];
    if (!c || state.has[id]) return false;
    return c.requires.every((p) => Boolean(getPath(state, p)));
  }

  function availableClues() { return Object.keys(clues).filter(available); }

  function cluePosition(id, npcPositions) {
    if (id.startsWith("@")) { const n = npcPositions && npcPositions[id.slice(1)]; return n ? n.position : null; }   // "@utayama" = 指向这个人
    const c = clues[id];
    if (c.position) return c.position;
    if (c.npc && npcPositions && npcPositions[c.npc]) return npcPositions[c.npc].position;
    return null;
  }

  /** 当前在找哪个字：形 → 真 → 理 */
  function currentChar() { return THREE.find((k) => !state.lit[k]) || null; }

  /**
   * 天秤现在催的线索：只催当前这个字的、可发现且未拿到的线索；同一个字里先催左盘（痕迹 / 人证 / 本体），再催右盘。
   * 推门前不催。拿了理的一件候选后不再催另一件。
   */
  function scaleTargets() {
    const ch = currentChar();
    if (!state.gateOpened || !ch) return [];
    const ids = availableClues().filter((id) => script.evidence[id] && script.evidence[id].for === ch)
      .filter((id) => !((id === "E6b" && state.has.E6a) || (id === "E6a" && state.has.E6b)));
    const left = ids.filter((id) => script.evidence[id].pan === "left");
    if (ids.length) return left.length ? left : ids;
    // 这个字剩下的线索只差"见过某人"才解锁（簿子要先见歌山）：天秤指向那个人，不让这一段安静
    const gate = [];
    for (const [id, c] of Object.entries(clues)) {
      if (state.has[id] || !script.evidence[id] || script.evidence[id].for !== ch) continue;
      const unmet = c.requires.filter((r) => !getPath(state, r));
      if (unmet.length && unmet.every((r) => r.startsWith("met."))) for (const r of unmet) gate.push("@" + r.slice(4));
    }
    return [...new Set(gate)];
  }

  /** 天秤：指向 scaleTargets 里最近的一个。覆盖层打开时调用方自己不调它。 */
  function scaleSignal(pos, npcPositions) {
    let best = null;
    for (const id of scaleTargets()) {
      const p = cluePosition(id, npcPositions);
      if (!p) continue;
      const d = Math.hypot(p[0] - pos[0], p[2] - pos[2]);   // 只算水平距离
      if (!best || d < best.distance) best = { target: id, distance: d };
    }
    if (!best) { state.lastRing = 0; return { target: null, distance: Infinity, amplitude: 0, ring: 0, stepUp: false }; }
    const amplitude = Math.max(0, Math.min(1, 1 - best.distance / scaleCfg.radius));
    // 档位：往上走一过线就升；往下走要低过线一段（回差）才降，免得在门槛附近来回响铃
    const hys = scaleCfg.hysteresis || 0;
    let ring = 0;
    scaleCfg.ringSteps.forEach((s, i) => { if (amplitude >= s - (state.lastRing > i ? hys : 0)) ring = i + 1; });
    const stepUp = ring > state.lastRing;        // 刚进入更近一档，UI 在这一帧响铃
    state.lastRing = ring;
    return { ...best, amplitude, ring, stepUp };
  }

  function gain(id) {
    if (state.has[id]) return false;
    state.has[id] = true;
    log("gain", { id });
    return true;
  }

  /** 对话：按状态选 script.npc[id] 里的哪一段，返回台词并推进状态。 */
  function talk(npc) {
    const n = script.npc[npc];
    if (!n) return { lines: [], gained: null };
    state.counters.talks++;
    const lines = [];
    let gained = null;
    if (!state.met[npc]) { state.met[npc] = true; lines.push(...n.first); log("meet", { npc }); }
    if (npc === "asa") {
      if (state.has.E6a || state.has.E6b) lines.push(...n.after_e6);
      else if (state.lit.makoto) lines.push(...n.hint_room);
      else lines.push(...n.testimony);
    } else if (npc === "kame") {
      if (!state.has.E3) { lines.push(...n.testimony, ...n.give_e3); gain("E3"); gained = "E3"; }
      else lines.push(...n.after_e3);
    } else if (npc === "utayama") {
      if (state.has.E4) lines.push(...n.after_e4);
      // 没拿簿子时只有 first 那两句；第二次来重复 first 的第二句，提醒簿子在桌上
      else if (lines.length === 0) lines.push(n.first[1]);
    }
    return { lines, gained };
  }

  /**
   * 互动：target 是线索 id（E1 拾起、E2 看壁画、E4 翻簿子、E5 捞井、E6a 拾线轴、E6b 开抽屉）或 'gate'。
   * 返回 ok=false 时附带药贩子的拒绝台词（比如井前“还不是时候”）。
   */
  function interact(target) {
    const k = script.kusuriuri;
    if (target === "gate") {
      if (!state.gateOpened) { state.gateOpened = true; state.zone = "Z1_corridor"; log("gate", {}); return { ok: true, lines: [k.gate] }; }
      return { ok: true, lines: [] };
    }
    if (!clues[target]) return { ok: false, lines: [] };
    if (target === "E5" && !(state.lit.kata && state.lit.makoto)) return { ok: false, lines: [k.well_before] };
    // 文机和歌山挨得近：没见过她就翻簿子，让调用方先触发和她的对话（talkFirst），不用玩家自己找她
    if (target === "E4" && !state.met.utayama) return { ok: false, lines: k.ledger_before ? [k.ledger_before] : [], talkFirst: "utayama" };
    if (!available(target)) return { ok: false, lines: [] };
    const lines = [];
    if (!state.scaleIntro) { state.scaleIntro = true; lines.push(k.scale_first); }
    gain(target);
    return { ok: true, lines, gained: target };
  }

  // ---------- 天秤配对 ----------
  function put(id) {
    const e = script.evidence[id];
    if (!e || !state.has[id]) return { ok: false, reason: "not_owned" };
    if (state.lit[e.for]) return { ok: false, reason: "already_lit" };   // 已亮的字对应的证物不能再放
    if (state.pans[e.pan]) return { ok: false, reason: "pan_full" };
    state.pans[e.pan] = id;
    return { ok: true };
  }

  function takeBack(pan) {
    const id = state.pans[pan];
    state.pans[pan] = null;
    return id;
  }

  function weigh() {
    const { left, right } = state.pans;
    if (!left || !right) return { result: "incomplete" };
    const pair = script.pairs.find((p) => p.left === left && p.right === right);
    state.pans = { left: null, right: null };
    if (!pair) {
      state.counters.wrongPairs++;
      log("wrong", { left, right });
      return { result: "wrong", line: script.kusuriuri.wrong };
    }
    state.lit[pair.lights] = true;
    if (pair.ending) state.ending = pair.ending;
    log("lit", { which: pair.lights, left, right });
    const lines = [pair.line, script.kusuriuri[pair.lights]];
    if (litCount() === 3) { state.phase = "sword"; lines.push(script.kusuriuri.all_three); }
    return { result: "balanced", lights: pair.lights, ending: pair.ending || null, lines, allThree: litCount() === 3 };
  }

  function finishSword() { if (state.phase === "sword") state.phase = "ending"; return state.phase; }

  function endingCard() {
    if (!state.ending) return null;
    const e = script.endings[state.ending];
    const other = state.ending === "A" ? "E6b" : "E6a";
    return { card: e.card, lines: e.lines, other: state.has[other] ? e.other : null };
  }

  /** 下一步提示 id：攻略生成和防卡关都用它。顺序就是推荐路线。 */
  function nextStep() {
    if (state.phase === "sword") return "watch_sword";
    if (state.phase === "ending") return "save_card";
    if (!state.gateOpened) return "open_gate";
    if (!state.lit.kata) {
      if (!state.has.E1) return "pick_E1";
      if (!state.has.E2) return "look_mural_E2";
      return "weigh_E1_E2";
    }
    if (!state.lit.makoto) {
      if (!state.has.E3) return "talk_kame_E3";
      if (!state.met.utayama) return "talk_utayama";
      if (!state.has.E4) return "read_ledger_E4";
      return "weigh_E3_E4";
    }
    if (!state.lit.kotowari) {
      if (!state.has.E5) return "fish_well_E5";
      if (!state.has.E6a && !state.has.E6b) return state.met.asa ? "search_yuki_room" : "talk_asa_hint";
      return "weigh_E5_E6";
    }
    return "done";
  }

  /** 防卡关提示的等待秒数：教学性的前几步和"该开天秤了"的步骤等得短一些。 */
  function hintDelay(id = nextStep()) {
    const quick = ["open_gate", "pick_E1", "look_mural_E2", "weigh_E1_E2", "weigh_E3_E4", "weigh_E5_E6"];
    return quick.includes(id) ? { first: 45, more: 90 } : { first: 90, more: 150 };
  }

  return {
    state, availableClues, available, currentChar, scaleTargets, scaleSignal, talk, interact, put, takeBack, weigh,
    finishSword, endingCard, nextStep, hintDelay, litCount,
  };
}
