import * as THREE from "three";
import { pub } from "../paths.js";
import { BURN, BURN_GLSL } from "./toon.js";

// 描边 + 和纸后期，一个合成 shader 做完：
//   pass 1  场景法线 + 深度 → normalRT（scene.overrideMaterial = MeshNormalMaterial）
//   pass 2  场景颜色 → colorRT
//   pass 3  全屏合成：深度跳变画粗外轮廓，法线跳变画细内线；再叠屏幕空间和纸、暗角、可选宽银幕黑边
// 描边色固定 canon 第 12 色 #322D48。和纸贴图按屏幕像素平铺，不跟镜头动。
export class PaperOutlinePost {
  constructor(renderer, scene, camera, { paper: paperFile = "textures/paper.png" } = {}) {   // 游览版传 paper.jpg（同一张纸纹，352 KB，png 是 850 KB）；探案版不传，照旧
    this.renderer = renderer; this.scene = scene; this.camera = camera;
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    this.normalRT = new THREE.WebGLRenderTarget(size.x, size.y, { depthTexture: new THREE.DepthTexture(size.x, size.y, THREE.UnsignedIntType) });
    this.colorRT = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType });
    this.normalMat = new THREE.MeshNormalMaterial();
    // 散华（toon.js BURN）：物怪那根圆柱里、地面以上、已经烧掉的部分不画法线，描边跟着一起没
    this.normalMat.onBeforeCompile = (sh) => {
      Object.assign(sh.uniforms, { uBurnOn: BURN.on, uBurnY: BURN.y, uBurnC: BURN.c, uBurnR: BURN.r, uBurnFloor: BURN.floor });
      sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vBurnW;")
        .replace("#include <project_vertex>", "#include <project_vertex>\nvBurnW = (modelMatrix * vec4(transformed, 1.0)).xyz;");
      // 法线材质的片元着色器里没有 <common>，声明直接放在 main 前面
      sh.fragmentShader = sh.fragmentShader.replace("void main() {", `varying vec3 vBurnW;\nuniform float uBurnOn, uBurnY, uBurnR, uBurnFloor; uniform vec2 uBurnC;\n${BURN_GLSL}\nvoid main() {\n  if (uBurnOn > 0.5 && vBurnW.y > uBurnFloor + 0.04 && length(vBurnW.xz - uBurnC) < uBurnR && burnD(vBurnW, uBurnY) < 0.0) discard;`);
    };
    const paper = new THREE.TextureLoader().load(pub(paperFile));
    paper.wrapS = paper.wrapT = THREE.RepeatWrapping;
    paper.colorSpace = THREE.NoColorSpace;

    this.quadMat = new THREE.ShaderMaterial({
      uniforms: {
        tColor: { value: this.colorRT.texture },
        tNormal: { value: this.normalRT.texture },
        tDepth: { value: this.normalRT.depthTexture },
        tPaper: { value: paper },
        uRes: { value: size },
        uNear: { value: camera.near }, uFar: { value: camera.far },
        uOutlineColor: { value: new THREE.Color("#322D48") },
        uPaperColor: { value: new THREE.Color("#F1E9DA") },
        uOutline: { value: 1 }, uPaper: { value: 1 }, uLetterbox: { value: 0 },
        uDepthThresh: { value: 0.012 },   // 相对深度差，超过算外轮廓
        uNormalThresh: { value: 0.72 },   // 法线夹角差，超过算内线
        uOuterWidth: { value: 1.6 },      // 外轮廓采样半径（像素）
        uInnerWidth: { value: 0.8 },
        uPaperScale: { value: 1.0 },      // 1 = 纸纹一像素对一像素
        uPaperStrength: { value: 0.15 },
        uTint: { value: new THREE.Color("#ffffff") }, uTintMix: { value: 0 },   // 整体调色（游览版雨夜：往藏青压一点）
        uRed: { value: new THREE.Color("#B42A47") }, uRedMix: { value: 0 },      // 妖化红描边：0 = 墨色，1 = 深红
        tMask: { value: null }, uUseMask: { value: 0 },                         // 有 maskLayer 时只在这层物体附近变红
        uReveal: { value: -1 }, uRevealC: { value: new THREE.Vector2(0.5, 0.5) },   // 上色：半径外压成灰（水墨），往外漫开；-1 = 关（笛小路家退魔后，docs/22）
      },
      vertexShader: /* glsl */ `
        varying vec2 vUv;
        void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
      `,
      fragmentShader: /* glsl */ `
        uniform sampler2D tColor, tNormal, tDepth, tPaper, tMask;
        uniform vec2 uRes;
        uniform float uNear, uFar, uDepthThresh, uNormalThresh, uOuterWidth, uInnerWidth, uPaperScale, uPaperStrength;
        uniform vec3 uOutlineColor, uPaperColor, uTint, uRed;
        uniform float uTintMix, uRedMix, uReveal;
        uniform vec2 uRevealC;
        uniform int uOutline, uPaper, uLetterbox, uUseMask;
        varying vec2 vUv;

        float linDepth(vec2 uv) {
          float z = texture2D(tDepth, uv).x * 2.0 - 1.0;
          return (2.0 * uNear * uFar) / (uFar + uNear - z * (uFar - uNear)) / uFar;   // 0..1
        }
        vec3 nrm(vec2 uv) { return texture2D(tNormal, uv).xyz * 2.0 - 1.0; }
        float isMesh(vec2 uv) { return step(0.05, dot(texture2D(tNormal, uv).xyz, vec3(1.0))); }   // 清屏是黑色（0），网格的法线颜色不会全黑

        void main() {
          vec3 col = texture2D(tColor, vUv).rgb;
          vec2 px = 1.0 / uRes;

          if (uOutline == 1) {
            // 外轮廓：Roberts cross 取深度差，按中心深度归一化，远处线不会变粗变脏
            vec2 o = px * uOuterWidth;
            float dc = linDepth(vUv);
            float d1 = abs(linDepth(vUv + vec2( o.x,  o.y)) - linDepth(vUv - vec2( o.x,  o.y)));
            float d2 = abs(linDepth(vUv + vec2( o.x, -o.y)) - linDepth(vUv - vec2( o.x, -o.y)));
            // 阈值按表面斜度放大：贴地平视时地板每个像素的深度差本来就大，不放大会整片地板被当成轮廓涂黑
            //（游览版积木走廊发现的）。nrm().z 是观察空间法线朝镜头的分量，背景处为 0 时按 0.15 算
            float facing = max(abs(nrm(vUv).z), 0.15);
            float th = uDepthThresh / facing;
            float dEdge = smoothstep(th * 0.6, th * 1.4, max(d1, d2) / max(dc, 1e-4));
            // 只在网格（灰盒、角色、道具）附近画线：四个采样点里有一个是网格才算，泼溅和泼溅之间不描边
            float mesh = max(max(isMesh(vUv + vec2(o.x, o.y)), isMesh(vUv - vec2(o.x, o.y))), max(isMesh(vUv + vec2(o.x, -o.y)), isMesh(vUv - vec2(o.x, -o.y))));
            dEdge *= max(mesh, isMesh(vUv));
            // 内线：法线差。背景处法线为 0，用深度 < 1 挡掉天空
            vec2 i = px * uInnerWidth;
            vec3 nc = nrm(vUv);
            float nd = 0.0;
            nd = max(nd, 1.0 - dot(nc, nrm(vUv + vec2(i.x, 0.0))));
            nd = max(nd, 1.0 - dot(nc, nrm(vUv - vec2(i.x, 0.0))));
            nd = max(nd, 1.0 - dot(nc, nrm(vUv + vec2(0.0, i.y))));
            nd = max(nd, 1.0 - dot(nc, nrm(vUv - vec2(0.0, i.y))));
            float nEdge = smoothstep(uNormalThresh * 0.7, uNormalThresh * 1.3, nd) * step(dc, 0.999) * 0.45 * max(isMesh(vUv), mesh);
            float edge = clamp(max(dEdge, nEdge), 0.0, 1.0);
            // 妖化红：有遮罩时只在遮罩物体（药郎）和它的外轮廓上变红，屋子的线还是墨色
            float mk = 1.0;
            if (uUseMask == 1) mk = max(max(texture2D(tMask, vUv).r, max(texture2D(tMask, vUv + vec2(o.x, o.y)).r, texture2D(tMask, vUv - vec2(o.x, o.y)).r)),
                                        max(texture2D(tMask, vUv + vec2(o.x, -o.y)).r, texture2D(tMask, vUv - vec2(o.x, -o.y)).r));
            col = mix(col, mix(uOutlineColor, uRed, uRedMix * mk), edge);
          }

          if (uReveal >= 0.0) {
            // 颜色从 uRevealC 往外一圈圈洇开：圈外是灰（带一点墨的紫调），圈边用纸纹抖一下，像墨洇在纸上
            vec2 d = (vUv - uRevealC) * vec2(uRes.x / uRes.y, 1.0);
            float edgeN = (texture2D(tPaper, vUv * 1.7).r - 0.5) * 0.22;
            float k = 1.0 - smoothstep(uReveal - 0.18, uReveal, length(d) + edgeN);
            float gray = dot(col, vec3(0.299, 0.587, 0.114));
            col = mix(vec3(gray) * vec3(0.97, 0.955, 1.0), col, k);
          }
          col = mix(col, col * uTint, uTintMix);

          if (uPaper == 1) {
            // 和纸：按屏幕像素平铺，不随镜头动。灰度 0.5 为中性，亮的地方往纸白提，暗的地方压暗
            vec2 puv = gl_FragCoord.xy / (1024.0 * uPaperScale);
            float g = texture2D(tPaper, puv).r - 0.5;
            col *= 1.0 + g * uPaperStrength * 2.0;
            col = mix(col, uPaperColor, max(g, 0.0) * uPaperStrength * 0.6);
            // 轻暗角
            vec2 q = vUv - 0.5;
            col *= 1.0 - dot(q, q) * 0.18;
          }

          if (uLetterbox == 1) {
            // 2.39:1 黑边（用描边色，不用纯黑）
            float barH = max(0.0, (1.0 - (uRes.x / uRes.y) / 2.39) * 0.5);
            if (vUv.y < barH || vUv.y > 1.0 - barH) col = uOutlineColor * 0.6;
          }

          gl_FragColor = vec4(col, 1.0);
          #include <colorspace_fragment>
        }
      `,
      depthTest: false, depthWrite: false,
    });
    this.exclude = [];   // 高斯泼溅（SplatMesh），不进法线通道
    this.spark = null;   // 设了 SparkRenderer 就让泼溅在描边通道里只写深度，挡住墙后的物体
    this.maskLayer = null;   // 设成图层号（游览版 3）：红描边只给开了这层的物体；null = 整屏（探案版）
    this.maskRT = null; this.maskMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.quadMat);
    this.quadScene = new THREE.Scene(); this.quadScene.add(this.quad);
    this.quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  }

  setFlags({ outline = true, paper = true, letterbox = false }) {
    this.quadMat.uniforms.uOutline.value = outline ? 1 : 0;
    this.quadMat.uniforms.uPaper.value = paper ? 1 : 0;
    this.quadMat.uniforms.uLetterbox.value = letterbox ? 1 : 0;
  }

  // 整体调色：col × tint 按 mix 混进去，0 = 关（探案版不用）
  setTint(color = "#ffffff", mix = 0) { this.quadMat.uniforms.uTint.value.set(color); this.quadMat.uniforms.uTintMix.value = mix; }

  // 上色漫开：r 是半径（屏幕高为 1），-1 关；cx / cy 是起点（0..1）
  setReveal(r, cx = 0.5, cy = 0.5) { this.quadMat.uniforms.uReveal.value = r; this.quadMat.uniforms.uRevealC.value.set(cx, cy); }

  // 描边色在墨色和红色之间混：0 = canon 第 12 色，1 = 深红（药郎妖化时用）。设了 maskLayer 只有那层物体变红
  setOutlineMix(t) { this.quadMat.uniforms.uRedMix.value = Math.max(0, Math.min(1, t)); }
  // 妖化描边换色（游览版设金色 #DCC67C）；不调就是默认深红（探案版）
  setAwakenColor(c) { this.quadMat.uniforms.uRed.value.set(c); }

  resize() {
    const size = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    this.normalRT.setSize(size.x, size.y); this.colorRT.setSize(size.x, size.y); this.maskRT?.setSize(size.x >> 1, size.y >> 1);
    this.quadMat.uniforms.uRes.value = size;
  }

  render() {
    const { renderer, scene, camera } = this;
    const bg = scene.background;
    scene.background = null;
    renderer.setRenderTarget(this.normalRT);
    renderer.setClearColor(0x000000, 1);
    renderer.clear();
    const spark = this.spark;
    if (spark) {
      // 1. 泼溅只写深度不写颜色：被泼溅墙挡住的灰盒、角色在下一步就过不了深度测试，不会被描边
      //    （只改材质的写入开关，不动泼溅的 visible / 位置，Spark 对那些很敏感）
      const hide = scene.children.filter((o) => o.visible && o !== spark && !this.exclude.includes(o));
      hide.forEach((o) => (o.visible = false));
      const m = spark.material, cw = m.colorWrite, dw = m.depthWrite, ac = renderer.autoClear;
      m.colorWrite = false; m.depthWrite = true; renderer.autoClear = false;
      renderer.render(scene, camera);
      m.colorWrite = cw; m.depthWrite = dw;
      hide.forEach((o) => (o.visible = true));
      // 2. 灰盒和角色的法线（泼溅这一遍不画）
      spark.visible = false;
      scene.overrideMaterial = this.normalMat;
      renderer.render(scene, camera);
      scene.overrideMaterial = null;
      spark.visible = true;
      renderer.autoClear = ac;
    } else {
      scene.overrideMaterial = this.normalMat;
      const hidden = this.exclude.filter((o) => o.visible); hidden.forEach((o) => (o.visible = false));
      renderer.render(scene, camera);
      hidden.forEach((o) => (o.visible = true));
      scene.overrideMaterial = null;
    }
    // 红描边遮罩（只在妖化、并且设了 maskLayer 时画）：只画那层物体，纯白，半分辨率
    const U = this.quadMat.uniforms, useMask = this.maskLayer !== null && U.uRedMix.value > 0;
    U.uUseMask.value = useMask ? 1 : 0;
    if (useMask) {
      if (!this.maskRT) { const s = renderer.getDrawingBufferSize(new THREE.Vector2()); this.maskRT = new THREE.WebGLRenderTarget(s.x >> 1, s.y >> 1); U.tMask.value = this.maskRT.texture; }
      const lm = camera.layers.mask; camera.layers.set(this.maskLayer);
      scene.overrideMaterial = this.maskMat; renderer.setRenderTarget(this.maskRT); renderer.setClearColor(0x000000, 1); renderer.clear();
      renderer.render(scene, camera); scene.overrideMaterial = null; camera.layers.mask = lm;
    }
    scene.background = bg;
    renderer.setRenderTarget(this.colorRT);
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    this.quadMat.uniforms.uNear.value = camera.near; this.quadMat.uniforms.uFar.value = camera.far;
    renderer.render(this.quadScene, this.quadCam);
  }
}
