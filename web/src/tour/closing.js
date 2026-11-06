// 结案札（11-06 第二版，用户："结案卡的设计很一般……形真理之前的线索册里都有了，可以用更有深度或者引人深思的信息，
//   然后设计的适合分享"）。整张卡画在 canvas 上（1080×1440，3:4，小红书 / Ins 竖图都放得下），屏幕上看到的就是存下来的图。
//   上半是退魔那一刻的画面（魂光升起时截的；上色的地点截上色以后），盖「退魔」印、贴一角物怪立绘；
//   图下一行是收尾（text.json end.<地点>）；左边一段判词（close.<地点>.verdict，药郎口吻：这一案说到底是人心里的什么），
//   再一句问（close.<地点>.question；11-06 用户不要对着"你"问、也不要标签，文案w 改成药郎口吻）；右边竖排案名、物怪、执念物；题眼（close.<地点>.tag）做一枚朱印最后落下；
//   底下一条是这个人自己这一趟：看过几处、観、拾遗、用了多久、日期、网址。
//   字走 i18n.js 的 tr()（界面字）；内容文案已经被 loadText 按语言合并过。非中日文时竖排改成转 90° 横写。
import { tr, LANG } from "./i18n.js";

export const CARD_W = 1080, CARD_H = 1440;
const PAPER = "#EFE6D2", INK = "#2A2018", RED = "#B42A47";
const SERIF = LANG === "ja" ? '"Hiragino Mincho ProN", "Yu Mincho", "Noto Serif JP", serif' : '"Songti SC", "STSong", "Noto Serif SC", "Hiragino Mincho ProN", serif';
const SANS = '-apple-system, "PingFang SC", "Hiragino Sans GB", sans-serif';
const CJK = /[぀-ヿ㐀-鿿]/;

/** 横排折行：按字宽折，标点不放行首 */
function wrap(c, text, maxW) {
  const out = []; let line = "";
  const units = CJK.test(text) ? [...text] : text.split(/(\s+)/);
  for (const u of units) {
    const t = line + u;
    if (c.measureText(t).width > maxW && line.trim()) {
      if (/^[，。、！？：；」』）]$/.test(u)) { out.push(t); line = ""; continue; }
      out.push(line.trimEnd()); line = u.trimStart();
    } else line = t;
  }
  if (line.trim()) out.push(line);
  return out;
}

/** 竖排一列（中日文一个字一格；别的语言转 90° 横写），返回占了多高 */
function vtext(c, text, x, y, size, color, gap = 1.08) {
  c.save(); c.fillStyle = color; c.font = `${size}px ${SERIF}`;
  if (CJK.test(text)) {
    c.textAlign = "center"; c.textBaseline = "top";
    let yy = y;
    for (const ch of text) {
      if (ch === " ") { yy += size * 0.4; continue; }
      if (/[·・]/.test(ch)) { c.fillText("・", x, yy - size * 0.1); yy += size * 0.8; continue; }
      c.fillText(ch, x, yy); yy += size * gap;
    }
    c.restore(); return yy - y;
  }
  c.translate(x, y); c.rotate(Math.PI / 2); c.textAlign = "left"; c.textBaseline = "middle";
  c.fillText(text, 0, 0); const w = c.measureText(text).width; c.restore(); return w;
}

/** 朱印：方块、双框、字竖排；rot 弧度 */
function seal(c, text, cx, cy, s, rot = 0, alpha = 0.9) {
  const ch = [...text].slice(0, 4), cols = ch.length > 2 ? 2 : 1, rows = Math.ceil(ch.length / cols);
  c.save(); c.translate(cx, cy); c.rotate(rot); c.globalAlpha = alpha;
  c.fillStyle = RED; c.fillRect(-s / 2, -s / 2, s, s);
  c.strokeStyle = PAPER; c.lineWidth = s * 0.03; c.strokeRect(-s / 2 + s * 0.07, -s / 2 + s * 0.07, s * 0.86, s * 0.86);
  c.fillStyle = PAPER; c.textAlign = "center"; c.textBaseline = "middle";
  const fs = (s * 0.72) / Math.max(rows, cols), cw = (s * 0.8) / cols, rh = (s * 0.8) / rows;
  c.font = `${CJK.test(text) ? fs : fs * 0.55}px ${SERIF}`;
  if (!CJK.test(text)) c.fillText(text, 0, 2);
  else ch.forEach((t, i) => { const col = cols - 1 - Math.floor(i / rows), row = i % rows; c.fillText(t, -s * 0.4 + cw * (col + 0.5), -s * 0.4 + rh * (row + 0.5) + 2); });
  // 印泥不匀：随机抠几个淡点
  let seed = text.length * 97 + 13; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  c.globalCompositeOperation = "destination-out";
  for (let i = 0; i < 40; i++) { c.globalAlpha = 0.15 + rnd() * 0.3; c.beginPath(); c.arc((rnd() - 0.5) * s, (rnd() - 0.5) * s, 1 + rnd() * s * 0.025, 0, 7); c.fill(); }
  c.restore();
}

/** 纸面：底色 + 细纤维 + 墨框 */
function paper(c) {
  c.fillStyle = PAPER; c.fillRect(0, 0, CARD_W, CARD_H);
  let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  c.save();
  for (let i = 0; i < 2200; i++) { c.globalAlpha = 0.04 + rnd() * 0.05; c.fillStyle = rnd() < 0.5 ? "#8A7350" : "#FFFFFF"; c.fillRect(rnd() * CARD_W, rnd() * CARD_H, 1 + rnd() * 2, 1 + rnd() * 2); }
  c.globalAlpha = 0.06; c.strokeStyle = "#8A7350"; c.lineWidth = 1;
  for (let i = 0; i < 90; i++) { const x = rnd() * CARD_W, y = rnd() * CARD_H, a = rnd() * 6.3, L = 10 + rnd() * 40; c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); c.stroke(); }
  c.restore();
  c.strokeStyle = INK; c.lineWidth = 4; c.strokeRect(26, 26, CARD_W - 52, CARD_H - 52);
  c.lineWidth = 1.2; c.strokeRect(38, 38, CARD_W - 76, CARD_H - 76);
}

/** 图按 cover 铺进框里 */
function cover(c, img, x, y, w, h) {
  const iw = img.width || img.naturalWidth, ih = img.height || img.naturalHeight; if (!iw || !ih) return;
  const s = Math.max(w / iw, h / ih), sw = w / s, sh = h / s;
  c.drawImage(img, (iw - sw) / 2, (ih - sh) / 2, sw, sh, x, y, w, h);
}

/**
 * 画结案札。d = { no, place, title, mononoke, item, end, verdict, question, tag, shot(canvas|null), portrait(img|null),
 *   stats: { looked, views:[n,m], finds:[n,m], minutes }, date, url, sealed(题眼印落了没) }
 */
export function drawCaseCard(cv, d) {
  cv.width = CARD_W; cv.height = CARD_H;
  const c = cv.getContext("2d");
  paper(c);
  const M = 64;
  // 抬头
  c.fillStyle = INK; c.globalAlpha = 0.75; c.font = `26px ${SERIF}`; c.textBaseline = "alphabetic"; c.textAlign = "left";
  c.fillText(tr("怪化猫 · 游览"), M, 96);
  c.globalAlpha = 1; c.fillStyle = RED; c.textAlign = "right";
  c.fillText(`${tr("结案札")} · ${tr(`第 ${d.no} 案`)}`, CARD_W - M, 96);
  // 画面
  const IX = M, IY = 122, IW = CARD_W - M * 2, IH = 660;
  c.save(); c.fillStyle = "#1c1814"; c.fillRect(IX, IY, IW, IH);
  if (d.shot) { c.filter = "saturate(.88) contrast(1.04)"; cover(c, d.shot, IX, IY, IW, IH); c.filter = "none"; }
  // 下沿压一层纸色，图跟纸接得软一点
  const g = c.createLinearGradient(0, IY + IH - 120, 0, IY + IH); g.addColorStop(0, "rgba(239,230,210,0)"); g.addColorStop(1, "rgba(239,230,210,.35)");
  c.fillStyle = g; c.fillRect(IX, IY + IH - 120, IW, 120);
  c.restore();
  c.strokeStyle = INK; c.lineWidth = 3; c.strokeRect(IX, IY, IW, IH);
  // 物怪立绘：贴在右下角，像夹进去的一张小像
  if (d.portrait) {
    const s = 210, px = IX + IW - s - 26, py = IY + IH - s - 26;
    c.save(); c.translate(px + s / 2, py + s / 2); c.rotate(0.045);
    c.fillStyle = PAPER; c.shadowColor = "rgba(0,0,0,.35)"; c.shadowBlur = 14; c.shadowOffsetY = 4; c.fillRect(-s / 2 - 10, -s / 2 - 10, s + 20, s + 44);
    c.shadowColor = "transparent"; cover(c, d.portrait, -s / 2, -s / 2, s, s);
    c.fillStyle = INK; c.font = `20px ${SERIF}`; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(d.mononoke, 0, s / 2 + 18);
    c.restore();
  }
  seal(c, tr("退魔"), IX + 82, IY + 82, 104, -0.1, 0.92);
  // 收尾、判词、一问：先按 k=1 排一遍看底在哪，放不下（英文长）就整体缩字再排，最多缩到 0.7
  const RX = CARD_W - M - 34, TY = IY + IH + 110, LW = RX - 140 - M, BOTTOM = CARD_H - 150 - 28;
  const layout = (k, draw) => {
    let y = IY + IH + 52 * k;
    c.textAlign = "left"; c.textBaseline = "alphabetic";
    c.fillStyle = INK; c.globalAlpha = 0.62; c.font = `${25 * k}px ${SERIF}`;
    for (const l of wrap(c, d.end ? `—— ${d.end}` : "", IW - 20).slice(0, 2)) { if (draw) c.fillText(l, M + 4, y); y += 38 * k; }
    c.globalAlpha = 1;
    y = Math.max(y + 34 * k, TY + 30 * k);
    c.fillStyle = INK; c.font = `${46 * k}px ${SERIF}`;
    for (const l of wrap(c, d.verdict || "", LW).slice(0, 4)) { if (draw) c.fillText(l, M, y + 40 * k); y += 70 * k; }
    y += 64 * k;   // 问句前不加标签（11-06 用户：不要"留一问""药郎问"，只留这一句）
    c.fillStyle = INK; c.globalAlpha = 0.85; c.font = `${34 * k}px ${SERIF}`;
    for (const l of wrap(c, d.question || "", LW - 160).slice(0, 3)) { if (draw) c.fillText(l, M, y + 22 * k); y += 52 * k; }   // 右下角留给题眼印
    c.globalAlpha = 1;
    return y;
  };
  let k = 1; while (k > 0.7 && layout(k, false) > BOTTOM) k -= 0.05;
  layout(k, true);
  // 右边竖排：案名、物怪 · 执念物（横写的语言：太长就缩到放得下）
  const room = BOTTOM - TY;
  const fit = (t, size) => { if (CJK.test(t)) return Math.min(size, room / Math.max(1, [...t].length * 1.08)); c.font = `${size}px ${SERIF}`; const w = c.measureText(t).width; return w > room ? size * room / w : size; };
  vtext(c, d.title, RX, TY, fit(d.title, 50), INK);
  const sub = `${d.mononoke} · ${d.item}`;
  vtext(c, sub, RX - 70, TY + 6, fit(sub, 26), RED, 1.12);
  c.strokeStyle = INK; c.globalAlpha = 0.25; c.lineWidth = 1; c.beginPath(); c.moveTo(RX - 112, TY - 10); c.lineTo(RX - 112, CARD_H - 180); c.stroke(); c.globalAlpha = 1;
  // 题眼印：最后落（sealed）
  if (d.sealed && d.tag) seal(c, d.tag, RX - 200, CARD_H - 245, CJK.test(d.tag) ? 116 : 128, 0.07);
  // 底栏：这一趟
  const FY = CARD_H - 150;
  c.strokeStyle = INK; c.lineWidth = 1.2; c.beginPath(); c.moveTo(M, FY); c.lineTo(CARD_W - M, FY); c.stroke();
  ["形", "真", "理"].forEach((t, i) => { const s = 38, x = M + i * (s + 8); c.fillStyle = RED; c.fillRect(x, FY + 26, s, s); c.fillStyle = PAPER; c.font = `26px ${SERIF}`; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(t, x + s / 2, FY + 26 + s / 2 + 1); });
  const st = d.stats || {}, parts = [];
  if (st.looked) parts.push(tr(`看过 ${st.looked} 处`));
  if (st.views) parts.push(tr(`観 ${st.views[0]} / ${st.views[1]}`));
  if (st.finds) parts.push(tr(`拾遗 ${st.finds[0]} / ${st.finds[1]}`));
  if (st.minutes) parts.push(tr(`用时 ${st.minutes} 分`));
  c.textAlign = "left"; c.textBaseline = "middle"; c.fillStyle = INK; c.globalAlpha = 0.8; c.font = `24px ${SANS}`;
  c.fillText(parts.join("  ·  "), M + 3 * 46 + 14, FY + 45);
  c.globalAlpha = 0.55; c.font = `21px ${SANS}`;
  c.fillText(`${tr(d.place)} · ${d.date}`, M, FY + 100);
  c.textAlign = "right"; c.fillText(d.url || "", CARD_W - M, FY + 100);
  c.globalAlpha = 1;
  return cv;
}
