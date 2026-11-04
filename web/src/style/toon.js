import * as THREE from "three";
import { pub } from "../paths.js";

// 2 阶平涂材质：固有色 + 一层阴影色，没有高光、没有真实光照衰减。
// 阴影色不是把固有色压暗，而是往 canon 里的"藤紫"(#6A4C8C) 偏一点，像赛璐珞的阴影层。
// 只认场景里的第一盏平行光（取 uLightDir）。支持蒙皮（SkinnedMesh 自动走骨骼变形）和形态键（药郎妖化的 awaken_hair / awaken_eyes / awaken_mouth，three 按网格自动开关）。
//
// 纹样（pattern）：
//   { tile: "asanoha"|"ichimatsu"|"seigaiha"|"shippo", space: "screen"|"world", scale, color, mix }
//     screen：按屏幕像素铺，不跟物体动（原作人物身上纹样"透出来"的做法），scale 是一个周期多少 CSS 像素
//     world：按世界坐标三平面投影，跟着表面走（地面、墙），scale 是一个周期多少米
//   { space, byPalette: [{ color, tile, patColor, mix }, ...] }
//     按贴图颜色最接近哪个色板色来决定铺哪种纹样，给 Tripo 烘好贴图的角色用；没列出的颜色不铺
//   maxY：网格自己坐标里（绑定姿势，不跟动作动）高于这个高度的地方不铺纹样。药郎的帽子用（10-31 用户说帽子"有点透"：
//     帽子的深色被归到藏青、铺了按屏幕走的纹样，药郎一动纹样不动，看着像透过帽子看到后面）
// setPatternsEnabled(false) 全局关掉，方便对比。

export const PATTERN_NAMES = ["asanoha", "ichimatsu", "seigaiha", "shippo"];   // 麻叶、市松、青海波、七宝（tools/patterns.py --set mononoke）
const PATTERN_ASPECT = { asanoha: 0.8662, ichimatsu: 1, seigaiha: 0.5, shippo: 1 };   // 高/宽，和 tools/patterns.py 输出一致   // 高/宽，和 tools/patterns.py 输出一致
const ENABLED = { value: 1 };
const PIXEL_RATIO = { value: Math.min(devicePixelRatio || 1, 2) };
let textures = null;
function patternTextures() {
  if (textures) return textures;
  const loader = new THREE.TextureLoader();
  textures = PATTERN_NAMES.map((n) => {
    const t = loader.load(pub(`textures/patterns/${n}.png`));
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.NoColorSpace; t.anisotropy = 4;
    return t;
  });
  return textures;
}
// 遮挡淡出（游览版跟随镜头用）：镜头和角色之间挡着的柱子、行灯，在角色周围一个椭圆里按网点抖动镂空，
// 平涂风格里看着像淡出。全局一份，每帧由镜头更新；只对 uCutout=1 的材质（游览版积木）生效，探案版不受影响。
//   center 屏幕像素（设备像素，左下原点），radius 像素（横向；纵向 ×1.7），depth 角色胸口的观察深度（米），0 = 关
export const CUTOUT = { center: { value: new THREE.Vector2() }, radius: { value: 0 }, depth: { value: 0 } };
export function setPatternsEnabled(v) { ENABLED.value = v ? 1 : 0; }
export function patternsEnabled() { return ENABLED.value === 1; }
const lin = (c) => new THREE.Color(c).convertSRGBToLinear();
const MAXPAL = 12;

export function makeToonMaterial({ map = null, color = "#ffffff", shadeColor = "#6A4C8C", shadeMix = 0.35, threshold = 0.4, softness = 0.02, pattern = null } = {}) {
  const tex = patternTextures();
  const pal = { n: 0, color: [], tile: [], patColor: [], mix: [] };
  if (pattern && pattern.byPalette) {
    for (const e of pattern.byPalette.slice(0, MAXPAL)) {
      pal.color.push(lin(e.color)); pal.tile.push(e.tile ? PATTERN_NAMES.indexOf(e.tile) : -1);
      pal.patColor.push(lin(e.patColor || "#F1E9DA")); pal.mix.push(e.mix ?? 0.4);
    }
    pal.n = pal.color.length;
  }
  while (pal.color.length < MAXPAL) { pal.color.push(new THREE.Color(0, 0, 0)); pal.tile.push(-1); pal.patColor.push(new THREE.Color(0, 0, 0)); pal.mix.push(0); }
  const p = pattern || {};
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      map: { value: map },
      uHasMap: { value: map ? 1 : 0 },
      uColor: { value: new THREE.Color(color) },
      uShade: { value: new THREE.Color(shadeColor) },
      uShadeMix: { value: shadeMix },
      uThreshold: { value: threshold },
      uSoft: { value: softness },
      uLightDir: { value: new THREE.Vector3(-1.5, 3, 2.5).normalize() },
      tPat0: { value: tex[0] }, tPat1: { value: tex[1] }, tPat2: { value: tex[2] }, tPat3: { value: tex[3] },
      uPatAspect: { value: new THREE.Vector4(...PATTERN_NAMES.map((n) => PATTERN_ASPECT[n])) },
      uPatEnabled: ENABLED,
      uPixelRatio: PIXEL_RATIO,
      uPatTile: { value: p.tile ? PATTERN_NAMES.indexOf(p.tile) : -1 },
      uPatSpace: { value: p.space === "world" ? 1 : 0 },
      uPatScale: { value: p.scale ?? (p.space === "world" ? 1.0 : 96) },
      uPatColor: { value: lin(p.color || "#F1E9DA") },
      uPatMix: { value: p.mix ?? 0.4 }, uPatMaxY: { value: p.maxY ?? 1e6 },
      uPalN: { value: pal.n },
      uPalColor: { value: pal.color }, uPalTile: { value: pal.tile }, uPalPatColor: { value: pal.patColor }, uPalMix: { value: pal.mix },
      uRim: { value: 0 }, uRimColor: { value: new THREE.Color("#F6E3B4") },   // 边缘透光：默认关；暗场景里的黑物怪用（encounter.js）
      uCutout: { value: 0 }, uCutCenter: CUTOUT.center, uCutRadius: CUTOUT.radius, uCutDepth: CUTOUT.depth,
    },
    vertexShader: /* glsl */ `
      #include <common>
      #include <morphtarget_pars_vertex>
      #include <skinning_pars_vertex>
      varying vec2 vUv;
      varying vec3 vNormalW;
      varying vec3 vWorldPos;
      varying float vViewZ;
      varying float vObjY;
      void main() {
        vUv = uv; vObjY = position.y;
        #include <morphinstance_vertex>
        #include <beginnormal_vertex>
        #include <morphnormal_vertex>
        #include <skinbase_vertex>
        #include <skinnormal_vertex>
        vNormalW = normalize(mat3(modelMatrix) * objectNormal);
        #include <begin_vertex>
        #include <morphtarget_vertex>
        #include <skinning_vertex>
        vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
        #include <project_vertex>
        vViewZ = -mvPosition.z;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D map;
      uniform int uHasMap;
      uniform vec3 uColor, uShade, uLightDir;
      uniform float uShadeMix, uThreshold, uSoft;
      uniform sampler2D tPat0, tPat1, tPat2, tPat3;
      uniform vec4 uPatAspect;
      uniform int uPatEnabled, uPatTile, uPatSpace, uPalN;
      uniform float uPixelRatio, uPatScale, uPatMix, uPatMaxY;
      uniform vec3 uPatColor;
      uniform vec3 uPalColor[${MAXPAL}];
      uniform int uPalTile[${MAXPAL}];
      uniform vec3 uPalPatColor[${MAXPAL}];
      uniform float uPalMix[${MAXPAL}];
      varying vec2 vUv;
      varying vec3 vNormalW;
      varying vec3 vWorldPos;
      varying float vViewZ;
      varying float vObjY;
      uniform int uCutout;
      uniform float uRim;
      uniform vec3 uRimColor;
      uniform vec2 uCutCenter;
      uniform float uCutRadius, uCutDepth;

      // 4×4 有序抖动阈值 0..1（bayer2 递归一层）
      float bayer2(vec2 a) { a = floor(a); return fract(a.x / 2.0 + a.y * a.y * 0.75); }
      float bayer4(vec2 a) { return bayer2(0.5 * a) * 0.25 + bayer2(a); }

      float tileAt(int t, vec2 uv) {
        if (t == 0) { uv.y /= uPatAspect.x; return texture2D(tPat0, uv).r; }
        if (t == 1) { uv.y /= uPatAspect.y; return texture2D(tPat1, uv).r; }
        if (t == 2) { uv.y /= uPatAspect.z; return texture2D(tPat2, uv).r; }
        uv.y /= uPatAspect.w; return texture2D(tPat3, uv).r;
      }
      // 纹样遮罩：屏幕空间直接按像素铺；世界空间三平面投影，按法线权重混合三个方向
      float patternMask(int t) {
        if (t < 0) return 0.0;
        if (uPatSpace == 0) return tileAt(t, gl_FragCoord.xy / (uPatScale * uPixelRatio));
        vec3 n = abs(normalize(vNormalW)); n = pow(n, vec3(4.0)); n /= (n.x + n.y + n.z);
        vec3 p = vWorldPos / uPatScale;
        return tileAt(t, p.zy) * n.x + tileAt(t, p.xz) * n.y + tileAt(t, p.xy) * n.z;
      }

      void main() {
        // 遮挡淡出：角色周围椭圆里、比角色离镜头近 0.35 米以上、离地 15 厘米以上（不挖地板）的片元按网点镂空
        if (uCutout == 1 && uCutDepth > 0.0 && vWorldPos.y > 0.15 && vViewZ < uCutDepth - 0.35) {
          vec2 q = gl_FragCoord.xy - uCutCenter; q.y /= 1.7;
          float a = 1.0 - smoothstep(0.55, 1.0, length(q) / uCutRadius);
          if (bayer4(gl_FragCoord.xy / 2.0) < a * 0.9) discard;
        }
        vec3 base = uColor;
        if (uHasMap == 1) base *= texture2D(map, vUv).rgb;   // sRGB 贴图由 WebGL2 硬件解成线性
        if (uPatEnabled == 1 && vObjY < uPatMaxY) {
          if (uPalN > 0) {
            // 按最接近的色板色选纹样。分类用低一级 mip 的模糊采样，否则 Tripo 贴图的噪点会让纹样碎成雪花
            vec3 cls = uHasMap == 1 ? uColor * texture2D(map, vUv, 3.0).rgb : uColor;
            int best = -1; float bd = 1e9;
            for (int i = 0; i < ${MAXPAL}; i++) {
              if (i >= uPalN) break;
              vec3 d = cls - uPalColor[i]; float dd = dot(d, d);
              if (dd < bd) { bd = dd; best = i; }
            }
            for (int i = 0; i < ${MAXPAL}; i++) {
              if (i == best) { float m = patternMask(uPalTile[i]); base = mix(base, uPalPatColor[i], m * uPalMix[i]); }
            }
          } else if (uPatTile >= 0) {
            base = mix(base, uPatColor, patternMask(uPatTile) * uPatMix);
          }
        }
        float ndl = dot(normalize(vNormalW), normalize(uLightDir));
        float lit = smoothstep(uThreshold - uSoft, uThreshold + uSoft, ndl);
        // 阴影层：固有色和阴影色相乘再和固有色混合，保留纹样，只是整体偏紫偏暗
        vec3 shaded = mix(base, base * uShade * 1.6, uShadeMix);
        vec3 c = mix(shaded, base, lit);
        if (uRim > 0.0) {   // 侧对镜头的那圈（菲涅尔）从里往外慢慢亮起来，像身上透出一层光（硬切的细边用户嫌生硬，11-04 改）
          float fres = 1.0 - abs(dot(normalize(vNormalW), normalize(cameraPosition - vWorldPos)));
          c = mix(c, uRimColor, pow(smoothstep(0.2, 1.0, fres), 1.6) * uRim);
        }
        gl_FragColor = vec4(c, 1.0);
      }
    `,
  });
  mat.toonParams = mat.uniforms;
  return mat;
}
