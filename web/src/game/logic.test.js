// 运行：cd web && node --test src/game/logic.test.js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createGame } from "./logic.js";

const here = new URL(".", import.meta.url);
const script = JSON.parse(readFileSync(new URL("../data/script.json", here), "utf8"));
const clues = JSON.parse(readFileSync(new URL("../data/clues.json", here), "utf8"));
const cams = JSON.parse(readFileSync(new URL("../world/cameras.json", here), "utf8"));
const npcPos = cams.npc_positions;

function playToMakoto(g) {
  g.interact("gate");
  g.interact("E1"); g.interact("E2");
  g.put("E1"); g.put("E2");
  assert.equal(g.weigh().lights, "kata");
  g.talk("kame");
  g.talk("utayama"); g.interact("E4");
  g.put("E3"); g.put("E4");
  assert.equal(g.weigh().lights, "makoto");
}

test("完整通关 结局 A", () => {
  const g = createGame(script, clues);
  assert.equal(g.nextStep(), "open_gate");
  playToMakoto(g);
  assert.equal(g.nextStep(), "fish_well_E5");
  assert.ok(g.interact("E5").ok);
  g.interact("E6a");
  g.put("E5"); g.put("E6a");
  const r = g.weigh();
  assert.equal(r.lights, "kotowari"); assert.equal(r.ending, "A"); assert.ok(r.allThree);
  assert.equal(g.state.phase, "sword");
  assert.equal(g.nextStep(), "watch_sword");
  g.finishSword();
  assert.equal(g.endingCard().card, script.endings.A.card);
  assert.equal(g.endingCard().other, null, "没拿 E6b 就不提另一件");
});

test("结局 B 且两件都拿时结果卡提另一件", () => {
  const g = createGame(script, clues);
  playToMakoto(g);
  g.interact("E5"); g.interact("E6a"); g.interact("E6b");
  g.put("E5"); g.put("E6b");
  assert.equal(g.weigh().ending, "B");
  g.finishSword();
  assert.equal(g.endingCard().other, script.endings.B.other);
});

test("井在前两字亮之前捞不了", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  const r = g.interact("E5");
  assert.equal(r.ok, false); assert.equal(r.lines[0], script.kusuriuri.well_before);
  assert.ok(!g.state.has.E5);
});

test("放错回弹、不扣证物、计数", () => {
  const g = createGame(script, clues);
  g.interact("gate"); g.interact("E1"); g.talk("kame");          // 有 E1 和 E3，都是左盘
  assert.equal(g.put("E1").ok, true);
  assert.equal(g.put("E3").ok, false, "左盘已满");
  g.takeBack("left"); g.put("E3");
  g.interact("E2"); g.put("E2");                                 // E3 + E2 是错的
  const r = g.weigh();
  assert.equal(r.result, "wrong"); assert.equal(g.state.counters.wrongPairs, 1);
  assert.ok(g.state.has.E3 && g.state.has.E2);
  assert.deepEqual(g.state.pans, { left: null, right: null });
});

test("已亮的字对应证物不能再放", () => {
  const g = createGame(script, clues);
  g.interact("gate"); g.interact("E1"); g.interact("E2"); g.put("E1"); g.put("E2"); g.weigh();
  assert.equal(g.put("E1").reason, "already_lit");
});

test("天秤指向最近的可发现线索，井在条件满足前不算", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  let s = g.scaleSignal([0, 0, -3], npcPos);
  assert.equal(s.target, "E1");
  assert.ok(s.amplitude > 0.5);
  s = g.scaleSignal([-7, 0, -12.8], npcPos);     // 站在井边，但井还不可发现
  assert.notEqual(s.target, "E5");
  g.interact("E1"); g.interact("E2"); g.put("E1"); g.put("E2"); g.weigh();
  g.talk("kame"); g.talk("utayama"); g.interact("E4"); g.put("E3"); g.put("E4"); g.weigh();
  s = g.scaleSignal([-7, 0, -12.8], npcPos);
  assert.equal(s.target, "E5");
});

test("天秤档位只在变近时报 stepUp", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  const far = g.scaleSignal([0, 0, 6], npcPos);     // 离 E1（z=-3）约 9 米，超出半径
  assert.equal(far.ring, 0);
  const near = g.scaleSignal([0.6, 0, -4.5], npcPos);
  assert.ok(near.ring >= 3 && near.stepUp);
  const again = g.scaleSignal([0.6, 0, -4.5], npcPos);
  assert.equal(again.stepUp, false);
});

test("阿浅的话随进度变化", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  let t = g.talk("asa");
  assert.deepEqual(t.lines, [...script.npc.asa.first, ...script.npc.asa.testimony]);
  t = g.talk("asa");
  assert.deepEqual(t.lines, script.npc.asa.testimony);
  playToMakoto(g);
  assert.deepEqual(g.talk("asa").lines, script.npc.asa.hint_room);
  g.interact("E6b");
  assert.deepEqual(g.talk("asa").lines, script.npc.asa.after_e6);
});

test("阿龟第一次说话就给 E3，之后只剩一句", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  const t = g.talk("kame");
  assert.equal(t.gained, "E3");
  assert.deepEqual(g.talk("kame").lines, script.npc.kame.after_e3);
});

test("歌山：先见面才能翻簿子，翻完有后话", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  assert.equal(g.interact("E4").ok, false);
  g.talk("utayama");
  assert.equal(g.interact("E4").ok, true);
  assert.deepEqual(g.talk("utayama").lines, script.npc.utayama.after_e4);
});

test("nextStep 推荐路线覆盖全部状态", () => {
  const g = createGame(script, clues);
  const seen = [g.nextStep()];
  g.interact("gate"); seen.push(g.nextStep());
  g.interact("E1"); seen.push(g.nextStep());
  g.interact("E2"); seen.push(g.nextStep());
  g.put("E1"); g.put("E2"); g.weigh(); seen.push(g.nextStep());
  g.talk("kame"); seen.push(g.nextStep());
  g.talk("utayama"); seen.push(g.nextStep());
  g.interact("E4"); seen.push(g.nextStep());
  g.put("E3"); g.put("E4"); g.weigh(); seen.push(g.nextStep());
  g.interact("E5"); seen.push(g.nextStep());
  g.talk("asa"); seen.push(g.nextStep());
  g.interact("E6a"); seen.push(g.nextStep());
  g.put("E5"); g.put("E6a"); g.weigh(); seen.push(g.nextStep());
  g.finishSword(); seen.push(g.nextStep());
  assert.deepEqual(seen, ["open_gate", "pick_E1", "look_mural_E2", "weigh_E1_E2", "talk_kame_E3", "talk_utayama",
    "read_ledger_E4", "weigh_E3_E4", "fish_well_E5", "talk_asa_hint", "search_yuki_room", "weigh_E5_E6", "watch_sword", "save_card"]);
});

// ---- 2026-10-28 节奏推演后加的规则 ----

test("推门前天秤不响", () => {
  const g = createGame(script, clues);
  const s = g.scaleSignal([0, 0, -2.4], npcPos);
  assert.equal(s.target, null); assert.equal(s.amplitude, 0);
});

test("天秤只催当前这个字的线索，同一个字先左盘后右盘", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  assert.deepEqual(g.scaleTargets(), ["E1"], "形：先催彩线");
  g.interact("E1");
  assert.deepEqual(g.scaleTargets(), ["E2"]);
  // 站在阿雪房门口：E6b 很近，但现在在找形，天秤不理它
  assert.equal(g.scaleSignal([3, 0, -11], npcPos).target, "E2");
  g.interact("E2"); g.put("E1"); g.put("E2"); g.weigh();
  assert.deepEqual(g.scaleTargets(), ["E3"], "真：先催阿龟（人证）");
  g.talk("kame");
  assert.deepEqual(g.scaleTargets(), ["@utayama"], "簿子要先见歌山才可发现：天秤指向歌山本人");
  assert.equal(g.scaleSignal([-6, 0, -7.8], npcPos).target, "@utayama");
  g.talk("utayama");
  assert.deepEqual(g.scaleTargets(), ["E4"]);
  g.interact("E4"); g.put("E3"); g.put("E4"); g.weigh();
  assert.deepEqual(g.scaleTargets(), ["E5"], "理：先催井，不催空房里的两件");
  g.interact("E5");
  assert.deepEqual(g.scaleTargets().sort(), ["E6a", "E6b"]);
  g.interact("E6b");
  assert.deepEqual(g.scaleTargets(), [], "拿了一件候选就不再催另一件");
});

test("档位回差：在门槛附近来回不重复响铃", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  const r = clues.scale.radius, step1 = clues.scale.ringSteps[0];
  const dAt = (amp) => r * (1 - amp);           // 振幅对应的距离
  const e1 = clues.clues.E1.position;
  const at = (d) => g.scaleSignal([e1[0], 0, e1[2] + d], npcPos);
  assert.equal(at(dAt(step1) + 0.05).ring, 0);
  assert.ok(at(dAt(step1) - 0.05).stepUp, "过线：响");
  assert.equal(at(dAt(step1) + 0.05).ring, 1, "退回线外一点点：还在 1 档");
  assert.equal(at(dAt(step1) - 0.05).stepUp, false, "再进来：不响");
  assert.equal(at(dAt(step1 - clues.scale.hysteresis) + 0.1).ring, 0, "退得够远才降档");
});

test("没见歌山就翻簿子：返回 talkFirst 让界面先触发对话", () => {
  const g = createGame(script, clues);
  g.interact("gate");
  const r = g.interact("E4");
  assert.equal(r.ok, false); assert.equal(r.talkFirst, "utayama");
  g.talk("utayama");
  assert.ok(g.interact("E4").ok);
});

test("提示延时：教学步短、探索步长", () => {
  const g = createGame(script, clues);
  assert.deepEqual(g.hintDelay("pick_E1"), { first: 45, more: 90 });
  assert.deepEqual(g.hintDelay("fish_well_E5"), { first: 90, more: 150 });
  assert.deepEqual(g.hintDelay(), { first: 45, more: 90 }, "默认用当前 nextStep（open_gate）");
});
