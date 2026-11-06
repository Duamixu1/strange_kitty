// 缘起手册的插图（11-06 第三版，文案w）。用户："插图要符合怪化猫每集的美术设计，但保持轻量"，点名了五种画风：
//   浮世绘、目黑雅叙园（路人脸涂黑配旋转的花）/ 克里姆特 / 能、屏风画、表现主义 / 黑白水墨 / 大正摩登、毕加索式造型。
// 一页一种，对上一篇：
//   yorozu  第 1 页  座敷童子：雨里的万屋门面、唐破风、红拱桥，桥上的路人脸涂黑，头上一朵花慢慢转
//   sumi    第 2 页  鵺：黑白水墨，墨云墨点，雪，一张白面浮在墨团里，只有角上一枚朱印是颜色
//   klimt   第 3 页  海坊主：金底螺旋、眼形、马赛克方块，深蓝海上金线浪，正中立着退魔剑
//   noh     第 4 页  のっぺらぼう：红白条的富士鹤屏风折成锯齿，表现主义的黑色折线，三张能面压着形真理三印
//   taisho  第 5 页  化猫（地铁）：做旧的米灰纸，黑大理石拱、芥黄红顶的电车，一张毕加索式半侧半正的女人脸和一只黑猫
// 全是内联 SVG（每张几 KB），不下图片；纹样、滤镜都在 DEFS 里定义一次，几张画共用。
// viewBox 300×220；每张画自己铺满底色、外加一道墨框，像手册里贴的一张版画。

const C = {
  paper: "#F1E9DA", ink: "#322D48", coral: "#E6667A", red: "#B42A47", gold: "#DCC67C", gold2: "#C9A23A", teal: "#49B3A6",
  fuji: "#6A4C8C", lav: "#D6D3EF", navy: "#1F2A55", mustard: "#D9A93A", wine: "#7A1F2B", green: "#8DBE8A", sumi: "#2B2B2B",
};
const S = (w = 2.5) => `stroke="${C.ink}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;
const r1 = (n) => Math.round(n * 10) / 10;

// 小工具：伪随机（每次画面一样）、螺旋线
let seed = 7;
const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280);
const spiral = (cx, cy, r, turns = 2.2) => {
  let d = "";
  for (let i = 0; i <= 28; i++) { const t = i / 28, a = t * turns * Math.PI * 2, rr = r * t; d += `${i ? "L" : "M"}${r1(cx + Math.cos(a) * rr)} ${r1(cy + Math.sin(a) * rr)}`; }
  return d;
};
const frame = `<rect x="1.5" y="1.5" width="297" height="217" fill="none" ${S(3)}/>`;

export const DEFS = `<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
  <pattern id="si-sgh" width="24" height="12" patternUnits="userSpaceOnUse"><rect width="24" height="12" fill="${C.teal}"/>${[11, 7.5, 4].map((r) => `<path d="M${12 - r} 12 A${r} ${r} 0 0 1 ${12 + r} 12 M${-r} 6 A${r} ${r} 0 0 1 ${r} 6 M${24 - r} 6 A${r} ${r} 0 0 1 ${24 + r} 6" fill="none" stroke="${C.paper}" stroke-width="1.1"/>`).join("")}</pattern>
  <pattern id="si-washi" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".7" fill="${C.ink}" opacity=".09"/><circle cx="7" cy="7" r=".5" fill="${C.ink}" opacity=".07"/></pattern>
  <pattern id="si-rain" width="14" height="22" patternUnits="userSpaceOnUse"><line x1="10" y1="0" x2="6" y2="12" stroke="#fff" stroke-width=".9" opacity=".75"/></pattern>
  <pattern id="si-stripe" width="16" height="10" patternUnits="userSpaceOnUse"><rect width="8" height="10" fill="${C.red}"/><rect x="8" width="8" height="10" fill="${C.paper}"/></pattern>
  <pattern id="si-check" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="12" height="12" fill="${C.paper}"/><rect width="6" height="6" fill="${C.sumi}"/><rect x="6" y="6" width="6" height="6" fill="${C.sumi}"/></pattern>
  <pattern id="si-mosaic" width="18" height="18" patternUnits="userSpaceOnUse"><rect width="18" height="18" fill="${C.gold}"/><rect x="2" y="2" width="5" height="7" fill="${C.sumi}" opacity=".75"/><rect x="10" y="9" width="6" height="4" fill="${C.paper}"/><rect x="9" y="2" width="3" height="3" fill="${C.red}"/></pattern>
  <linearGradient id="si-goldg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EBCB6A"/><stop offset="1" stop-color="#B98A2C"/></linearGradient>
  <filter id="si-blur6" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
  <filter id="si-blur2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.6"/></filter>
</defs></svg>`;

// 头上转的花（万屋的路人）：六瓣，SMIL 转，轻
const flower = (x, y, r, cols, dur) => `<g>${Array.from({ length: 6 }, (_, k) => { const a = (k / 6) * Math.PI * 2; return `<ellipse cx="${r1(x + Math.cos(a) * r * 0.62)}" cy="${r1(y + Math.sin(a) * r * 0.62)}" rx="${r1(r * 0.42)}" ry="${r1(r * 0.26)}" transform="rotate(${r1((a * 180) / Math.PI)} ${r1(x + Math.cos(a) * r * 0.62)} ${r1(y + Math.sin(a) * r * 0.62)})" fill="${cols[k % cols.length]}" ${S(1)}/>`; }).join("")}<circle cx="${x}" cy="${y}" r="${r1(r * 0.22)}" fill="${C.gold}" ${S(1)}/><animateTransform attributeName="transform" type="rotate" from="0 ${x} ${y}" to="360 ${x} ${y}" dur="${dur}s" repeatCount="indefinite"/></g>`;
// 涂黑脸的路人：和服梯形身子 + 黑脸 + 头上的花
const walker = (x, y, kimono, sash, flowerCols, dur) => `
  <path d="M${x - 11} ${y + 38} L${x - 7} ${y + 8} Q${x} ${y + 3} ${x + 7} ${y + 8} L${x + 11} ${y + 38} Z" fill="${kimono}" ${S(1.8)}/>
  <rect x="${x - 8}" y="${y + 18}" width="16" height="5" fill="${sash}" ${S(1.2)}/>
  <circle cx="${x}" cy="${y}" r="6.5" fill="${C.sumi}" ${S(1.5)}/>${flower(x, y - 15, 11, flowerCols, dur)}`;

const yorozu = () => `
  <rect width="300" height="220" fill="#DAD3C4"/><rect width="300" height="220" fill="url(#si-washi)"/>
  <path d="M40 58 L150 26 L260 58 Z" fill="#4A4C5C" ${S(2)}/>
  <rect x="62" y="56" width="176" height="24" fill="#5A4636" ${S(2)}/>
  ${Array.from({ length: 9 }, (_, k) => `<rect x="${70 + k * 19}" y="61" width="12" height="13" fill="#F3EBDD" ${S(1)}/>`).join("")}
  ${Array.from({ length: 8 }, (_, k) => `<circle cx="${80 + k * 20}" cy="86" r="4.5" fill="${C.red}" ${S(1)}/>`).join("")}
  <rect x="70" y="80" width="160" height="78" fill="#F3EBDD" ${S(2)}/>
  ${[90, 210].map((x) => `<rect x="${x - 9}" y="94" width="18" height="34" fill="${C.teal}" ${S(1.5)}/><circle cx="${x}" cy="104" r="6" fill="none" stroke="${C.paper}" stroke-width="1.5"/>`).join("")}
  <path d="M112 112 Q150 80 188 112 L188 118 L112 118 Z" fill="#4A4C5C" ${S(2)}/>
  <rect x="132" y="118" width="36" height="40" fill="${C.red}" ${S(2)}/><circle cx="150" cy="134" r="9" fill="${C.paper}" ${S(1.5)}/><text x="150" y="138.5" text-anchor="middle" font-size="12" fill="${C.ink}" font-family="Hiragino Mincho ProN, Songti SC, serif">同</text>
  <rect x="0" y="176" width="300" height="44" fill="url(#si-sgh)"/>
  <path d="M30 188 Q150 128 270 188" fill="none" stroke="#D2483A" stroke-width="8" stroke-linecap="round"/><path d="M30 176 Q150 116 270 176" fill="none" stroke="#D2483A" stroke-width="3"/>
  ${[60, 100, 140, 180, 220].map((x) => { const y = 188 - 60 * (1 - ((x - 150) / 120) ** 2); return `<line x1="${x}" y1="${r1(y - 12)}" x2="${x}" y2="${r1(y)}" stroke="#D2483A" stroke-width="3"/>`; }).join("")}
  ${walker(78, 128, C.fuji, C.gold, [C.coral, C.paper, C.teal], 7)}${walker(108, 121, C.teal, C.red, [C.gold, C.coral, C.lav], 9)}${walker(218, 126, C.coral, C.ink, [C.lav, C.gold, C.paper], 8)}
  <rect width="300" height="220" fill="url(#si-rain)" opacity=".55"/>${frame}`;

const sumi = () => { seed = 11; return `
  <rect width="300" height="220" fill="#E6E3DC"/><rect width="300" height="220" fill="url(#si-washi)"/>
  <g filter="url(#si-blur6)" fill="${C.sumi}">
    <ellipse cx="60" cy="34" rx="70" ry="20" opacity=".5"/><ellipse cx="258" cy="58" rx="56" ry="16" opacity=".4"/>
    <ellipse cx="176" cy="96" rx="80" ry="58" opacity=".85"/><ellipse cx="226" cy="140" rx="46" ry="30" opacity=".6"/>
  </g>
  <g filter="url(#si-blur2)" fill="${C.sumi}">${Array.from({ length: 18 }, () => `<circle cx="${r1(20 + rnd() * 260)}" cy="${r1(20 + rnd() * 160)}" r="${r1(1 + rnd() * 4)}" opacity=".7"/>`).join("")}</g>
  <path d="M0 176 Q80 166 150 172 T300 168 L300 220 L0 220 Z" fill="#F4F2EC"/>
  <path d="M30 104 L104 104 L112 112 L22 112 Z" fill="${C.sumi}"/><path d="M28 112 L106 112" stroke="${C.sumi}" stroke-width="3"/>
  <rect x="38" y="112" width="7" height="64" fill="${C.sumi}"/><rect x="88" y="112" width="7" height="64" fill="${C.sumi}"/><rect x="38" y="128" width="57" height="5" fill="${C.sumi}" opacity=".8"/>
  <path d="M22 104 L112 104" stroke="#F4F2EC" stroke-width="3"/>
  <g filter="url(#si-blur2)">${Array.from({ length: 14 }, (_, k) => { const a = (k / 14) * Math.PI * 2, x = 176 + Math.cos(a) * 34, y = 96 + Math.sin(a) * 42; return `<path d="M176 96 L${r1(x)} ${r1(y)} L${r1(176 + Math.cos(a + 0.2) * 52)} ${r1(96 + Math.sin(a + 0.2) * 60)}" stroke="${C.sumi}" stroke-width="7" fill="none" stroke-linecap="round"/>`; }).join("")}</g>
  <path d="M152 70 Q176 56 200 70 Q206 100 196 120 Q176 138 156 120 Q146 100 152 70 Z" fill="#F4F2EC" ${S(2)}/>
  <path d="M158 88 q8 -7 15 -2 q-8 6 -15 2 Z M180 86 q7 -5 15 2 q-8 4 -15 -2 Z" fill="${C.sumi}"/><circle cx="166" cy="87" r="1.3" fill="#F4F2EC"/><circle cx="187" cy="87" r="1.3" fill="#F4F2EC"/>
  <path d="M168 114 q8 3 16 0" fill="none" stroke="${C.sumi}" stroke-width="2"/><path d="M160 76 q6 -4 12 -2 M182 74 q6 -2 12 2" fill="none" ${S(1.5)}/>
  <path d="M214 150 C246 140 262 160 250 176 C240 190 258 204 276 194" fill="none" stroke="${C.sumi}" stroke-width="6" stroke-linecap="round"/>
  ${Array.from({ length: 26 }, () => `<circle cx="${r1(rnd() * 300)}" cy="${r1(rnd() * 220)}" r="${r1(0.8 + rnd() * 1.8)}" fill="#fff" opacity=".9"/>`).join("")}
  <rect x="254" y="22" width="24" height="24" fill="${C.red}"/><rect x="258" y="26" width="16" height="16" fill="none" stroke="${C.paper}" stroke-width="1.2"/>${frame}`; };

const klimt = () => { seed = 3; return `
  <rect width="300" height="220" fill="url(#si-goldg)"/><rect width="300" height="220" fill="url(#si-mosaic)" opacity=".22"/>
  ${[0, 1, 2, 3, 4, 5, 6].map((i) => `<path d="${spiral(24 + i * 42, 34, 13)}" fill="none" stroke="${C.sumi}" stroke-width="1.8"/><path d="${spiral(45 + i * 42, 112, 11)}" fill="none" stroke="${C.sumi}" stroke-width="1.6" opacity=".85"/>`).join("")}
  ${[[40, 76], [96, 70], [208, 72], [262, 78]].map(([x, y]) => `<ellipse cx="${x}" cy="${y}" rx="9" ry="5" fill="${C.paper}" ${S(1.3)}/><circle cx="${x}" cy="${y}" r="2.6" fill="${C.sumi}"/>`).join("")}
  ${[[16, 120, C.sumi], [70, 132, C.red], [118, 60, C.paper], [186, 128, C.teal], [236, 120, C.sumi], [278, 132, C.red]].map(([x, y, c]) => `<rect x="${x}" y="${y}" width="9" height="13" fill="${c}" ${S(1)}/>`).join("")}
  <rect x="0" y="152" width="300" height="68" fill="${C.navy}"/>
  ${[160, 176, 192, 208].map((y, k) => `<path d="M0 ${y} ${Array.from({ length: 8 }, (_, i) => `Q${i * 40 + 20 + (k % 2) * 10} ${y - 10} ${i * 40 + 40} ${y}`).join(" ")}" fill="none" stroke="${C.gold}" stroke-width="2.2"/>`).join("")}
  <circle cx="150" cy="104" r="62" fill="none" stroke="${C.paper}" stroke-width="1.2" opacity=".7"/><circle cx="150" cy="104" r="52" fill="none" stroke="${C.sumi}" stroke-width="1" opacity=".6" stroke-dasharray="2 5"/>
  <rect x="142" y="82" width="16" height="122" rx="3" fill="${C.fuji}" ${S(2.4)}/>${[100, 130, 160, 190].map((y) => `<path d="${spiral(150, y, 5, 1.6)}" fill="none" stroke="${C.gold}" stroke-width="1.3"/>`).join("")}
  <ellipse cx="150" cy="82" rx="22" ry="7" fill="${C.gold}" ${S(2.4)}/>
  <rect x="143" y="42" width="14" height="38" fill="${C.paper}" ${S(2.4)}/><path d="M143 48 L157 58 M157 48 L143 58 M143 62 L157 72 M157 62 L143 72" ${S(1.6)}/>
  <circle cx="150" cy="32" r="12" fill="${C.red}" ${S(2.4)}/><circle cx="146" cy="30" r="1.8" fill="${C.ink}"/><circle cx="154" cy="30" r="1.8" fill="${C.ink}"/><path d="M145 37 Q150 34 155 37" fill="none" ${S(1.6)}/>
  <path d="M157 54 C176 62 184 78 180 100" fill="none" stroke="${C.red}" stroke-width="4" stroke-linecap="round"/>${frame}`; };

const mask = (x, y, tint, ch) => `
  <ellipse cx="${x}" cy="${y}" rx="24" ry="31" fill="${tint}" ${S(2)}/>
  <path d="M${x - 15} ${y - 14} q6 -5 11 0 M${x + 4} ${y - 14} q6 -5 11 0" fill="none" ${S(1.6)}/>
  <path d="M${x - 14} ${y - 4} q5 -4 10 0 q-5 3 -10 0 Z M${x + 4} ${y - 4} q5 -4 10 0 q-5 3 -10 0 Z" fill="${C.sumi}"/>
  <path d="M${x - 5} ${y + 15} q5 3 10 0 q-5 -2 -10 0 Z" fill="${C.red}"/>
  <rect x="${x - 11}" y="${y + 36}" width="22" height="22" fill="${C.red}" ${S(1.5)}/><text x="${x}" y="${y + 53}" text-anchor="middle" font-size="16" fill="${C.paper}" font-family="Hiragino Mincho ProN, Songti SC, serif">${ch}</text>`;
const noh = () => `
  <rect width="300" height="220" fill="#B9372F"/><rect width="300" height="220" fill="url(#si-washi)"/>
  ${[0, 1, 2, 3, 4, 5].map((k) => { const x0 = k * 50, sk = k % 2 ? 10 : -10; return `<path d="M${x0} ${30 + sk} L${x0 + 50} ${30 - sk} L${x0 + 50} ${168 - sk} L${x0} ${168 + sk} Z" fill="url(#si-stripe)" ${S(2)}/><path d="M${x0} ${30 + sk} L${x0 + 50} ${30 - sk} L${x0 + 50} ${168 - sk} L${x0} ${168 + sk} Z" fill="${k % 2 ? "#000" : "#fff"}" opacity=".12"/>`; }).join("")}
  <path d="M70 120 L130 62 L190 120 Z" fill="#F3EEE6" ${S(2)}/><path d="M112 80 L130 62 L148 80 L140 76 L130 86 L120 76 Z" fill="#fff" ${S(1.2)}/>
  <path d="M206 70 q14 -12 30 -4 q-10 2 -14 10 q16 -2 26 8 q-18 -2 -30 4 Z" fill="#fff" ${S(1.5)}/><circle cx="208" cy="69" r="2.2" fill="${C.red}"/>
  <path d="M0 18 L40 30 L70 8 L110 28 L150 4 L196 26 L232 6 L270 24 L300 10" fill="none" stroke="${C.sumi}" stroke-width="4"/>
  <path d="M0 200 L36 186 L60 206 L104 182 L140 204 L180 184 L222 206 L262 186 L300 202" fill="none" stroke="${C.sumi}" stroke-width="4"/>
  ${mask(80, 128, "#F6F2EA", "形")}${mask(150, 118, "#E2DDF0", "真")}${mask(220, 128, "#F4DEDE", "理")}${frame}`;

const taisho = () => { seed = 5; return `
  <rect width="300" height="220" fill="#CDBFA6"/><rect width="300" height="220" fill="url(#si-washi)"/>
  ${Array.from({ length: 14 }, () => { const x = rnd() * 300, y = rnd() * 220; return `<line x1="${r1(x)}" y1="${r1(y)}" x2="${r1(x + 10 + rnd() * 30)}" y2="${r1(y + rnd() * 6 - 3)}" stroke="${C.ink}" stroke-width=".6" opacity=".25"/>`; }).join("")}
  <path d="M120 150 L120 70 A90 64 0 0 1 300 70 L300 150 Z" fill="${C.sumi}"/><path d="M128 150 L128 72 A82 58 0 0 1 292 72 L292 150" fill="none" stroke="#EDE6D8" stroke-width="5"/>
  <rect x="150" y="104" width="150" height="46" fill="${C.mustard}" ${S(2)}/><rect x="150" y="96" width="150" height="10" fill="${C.wine}" ${S(2)}/>
  ${[162, 196, 230, 264].map((x) => `<rect x="${x}" y="112" width="24" height="18" fill="${C.sumi}" stroke="${C.gold}" stroke-width="1.5"/>`).join("")}
  <rect x="0" y="150" width="300" height="70" fill="url(#si-check)"/><rect x="0" y="150" width="300" height="70" fill="#CDBFA6" opacity=".35"/><line x1="0" y1="150" x2="300" y2="150" ${S(2)}/>
  <rect x="18" y="22" width="104" height="140" fill="${C.paper}" ${S(2.5)}/>
  <path d="M32 150 L46 64 L70 40 L96 54 L108 150 Z" fill="${C.coral}" ${S(2)}/>
  <path d="M70 40 L96 54 L108 150 L70 150 Z" fill="${C.teal}" ${S(2)}/>
  <path d="M34 150 Q22 100 34 62 Q46 30 78 30 Q106 32 112 62 L102 66 Q94 44 72 46 Q50 50 46 84 Q42 116 52 150 Z" fill="#F7F4EE" ${S(2)}/><path d="M38 92 Q36 120 44 146 M46 70 Q40 100 46 130" fill="none" stroke="${C.lav}" stroke-width="1.5"/>
  <ellipse cx="58" cy="86" rx="9" ry="6" fill="#fff" ${S(1.6)}/><circle cx="58" cy="86" r="3" fill="${C.sumi}"/>
  <path d="M84 78 l12 4 l-12 4 Z" fill="${C.sumi}"/><path d="M70 92 L64 112 L74 112" fill="none" ${S(1.8)}/><path d="M60 124 q8 5 16 0" fill="none" stroke="${C.red}" stroke-width="3"/>
  <path d="M40 162 L40 136 L48 126 L54 136 L66 136 L72 126 L80 136 L80 162 Z" fill="${C.sumi}" ${S(1.5)}/><circle cx="52" cy="142" r="2" fill="${C.gold}"/><circle cx="68" cy="142" r="2" fill="${C.gold}"/>
  <path d="M80 158 q22 -4 18 -24" fill="none" stroke="${C.sumi}" stroke-width="4" stroke-linecap="round"/>${frame}`; };

export const ART = { yorozu: yorozu(), sumi: sumi(), klimt: klimt(), noh: noh(), taisho: taisho() };
// 旧名字（第二版 intro.cards 里写的 art）照样能用
Object.assign(ART, { box: ART.yorozu, ghost: ART.sumi, sword: ART.klimt, seals: ART.noh, scroll: ART.taisho });
export const ORDER = ["yorozu", "sumi", "klimt", "noh", "taisho"];
export const svg = (name) => `<svg viewBox="0 0 300 220" aria-hidden="true">${ART[name] || ""}</svg>`;
