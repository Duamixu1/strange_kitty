import * as THREE from "three";
import { buildTemari } from "../world/temari.js";

// 拔剑过场（实时占位版）。四个镜头，总长约 14 秒，Space / Esc 跳过。
// 正式版换成 Blender 渲的视频时，只换 runSwordCutscene 的实现，调用方不动。
//   1  手鞠从走廊尽头沿地毯滚到药贩子面前（镜头在药贩子身后低角度）
//   2  线散开、核亮起（镜头贴近球）
//   3  字卡"形、真、理，齐了"，接药贩子挥刀（镜头正面低角度）
//   4  白闪，线缩回，球散掉，淡出
const $ = (s) => document.querySelector(s);
const ease = (t) => t * t * (3 - 2 * t);
const SLASH_AT = 123 / 24;   // 横斩那一帧（tools/poses/kusuriuri_v2.json 的 exorcise_k）

export function runSwordCutscene({ scene, camera, director, player, play, hud, script, cams, temariModel = null }) {
  const night = $("#night"), flash = $("#flash"), text = $("#cut-text");
  const zone = player.position.clone();
  const czMin = cams && cams.layout ? cams.layout.corridor.z[0] : -24;
  const standZ = Math.max(czMin + 5, Math.min(-8, zone.z));   // 药贩子站的位置：走廊里，面对尽头，离尽头至少 5 米
  player.position.set(0, 0, standZ); player.rotation.y = Math.PI; player.visible = true;
  play("idle");
  const temari = buildTemari({ model: temariModel });
  const rollFrom = Math.max(standZ - 12, czMin + 1.2);
  temari.root.position.set(0, temari.radius, rollFrom);
  scene.add(temari.root);
  director.manual = true;
  document.body.classList.add("cutscene");
  text.textContent = script.kusuriuri.all_three;

  const shots = [
    { dur: 3.2, enter() { camera.fov = 36; camera.updateProjectionMatrix(); night.style.opacity = 0.3; },
      update(t) {
        const z0 = rollFrom, z1 = standZ - 3.2;
        const z = THREE.MathUtils.lerp(z0, z1, ease(t));
        temari.roll(z - temari.root.position.z);
        camera.position.set(1.5, 1.25, standZ + 5.2); camera.lookAt(-0.2, 0.55, standZ - 6);
      } },
    { dur: 3.0, enter() { camera.fov = 34; camera.updateProjectionMatrix(); night.style.opacity = 0.42; if (hud) hud.ring(2); },
      update(t) {
        temari.unravel(t);
        const p = temari.root.position;
        camera.position.set(p.x + 2.3 - t * 0.6, p.y + 0.7 + t * 0.5, p.z + 2.0 + t * 0.6); camera.lookAt(p.x, p.y + 0.3, p.z);
      } },
    // 退魔三拍（手 K exorcise_k，24 帧/秒）：1.25 秒抽剑、3.2 秒妖化、4.6 秒蓄力、5.1 秒横斩、7.9 秒起收剑
    // 这一镜从抽剑播到横斩前一刻，下一镜的白闪正好落在横斩上
    { dur: SLASH_AT, enter() { play("slash"); text.classList.add("show"); camera.fov = 34; camera.updateProjectionMatrix(); setTimeout(() => { text.classList.remove("show"); if (hud) hud.ring(3); }, 1400); },
      update(t) {
        camera.position.set(1.9, 1.0, standZ - 3.4); camera.lookAt(0, 1.15, standZ);
      } },
    { dur: 3.0, enter() { flash.style.opacity = 1; setTimeout(() => (flash.style.opacity = 0), 180); },
      update(t) { temari.collapse(t); night.style.opacity = 0.42 + t * 0.58;
        camera.position.set(1.5, 1.25, standZ + 5.2); camera.lookAt(-0.2, 0.55, standZ - 6); } },
  ];

  let i = -1, t0 = 0, done = false, resolve;
  const promise = new Promise((r) => (resolve = r));
  const skip = (e) => { if (e.code === "Space" || e.code === "Escape") finish(); };
  addEventListener("keydown", skip);
  function next(now) { i++; if (i >= shots.length) return finish(); t0 = now; shots[i].enter(); }
  function finish() {
    if (done) return; done = true;
    removeEventListener("keydown", skip);
    scene.remove(temari.root);
    director.manual = false;
    document.body.classList.remove("cutscene");
    text.classList.remove("show"); night.style.opacity = 0; flash.style.opacity = 0;
    play("idle");
    resolve();
  }
  // 调用方每帧调 update(performance.now())，promise 在过场结束或跳过时 resolve
  return {
    promise,
    get active() { return !done; },
    update(now) {
      if (done) return;
      if (i < 0) return next(now);
      const t = (now - t0) / 1000 / shots[i].dur;
      if (t >= 1) { shots[i].update(1); return next(now); }
      shots[i].update(t);
    },
  };
}
