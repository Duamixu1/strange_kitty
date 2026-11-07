// 怪化猫游览 · Service Worker（docs/23 第二节 C1，11-06）
// 下过的别再下：程序（assets/，文件名带 hash）、模型（game-assets/）、贴图（textures/）、draco、图标存进 Cache API。
// GitHub Pages 的缓存只给 10 分钟，过了每个文件都要回源问一遍"变没变"，国内到 GitHub 一次往返几百毫秒，60 个文件光问就十几秒；
// 这里按发布时生成的 manifest.json（每个文件的内容 hash）判新旧：hash 没变直接从缓存给，不碰网络；变了才重下。
// 页面（tour.html）、manifest 本身走网络。带 Range 的请求（泼溅库分段下）和别的域名不管。
// 注册：tour.js 在发布版里 register("sw.js?v=<构建号>")，构建号变了浏览器会装新的 SW，新 SW 第一次启动重新取 manifest。
const CACHE = "mononoke-tour-v2";   // 11-07 v1→v2：v1 里可能存着浏览器 HTTP 缓存给的旧文件（见下面 fresh），换个名字整个清掉重下
const BASE = new URL(self.registration.scope).pathname;   // "/strange_kitty/"
const V = new URL(self.location.href).searchParams.get("v") || "0";
const TRACKED = /^(game-assets|textures|draco|icons)\//;
let manifestP = null;
// 重下时绕过浏览器 HTTP 缓存（no-cache = 先问服务器）：GitHub Pages 给 10 分钟 max-age，刚发布完直接 fetch 会拿到浏览器缓存里的旧文件，
// 再按新 hash 存进来，以后就一直给旧的（11-07 实测：长卷去金霞后线上仍显示金霞）
const fresh = (u) => fetch(u, { cache: "no-cache" });
// 存进缓存时只留 content-type：服务器给的是 gzip 过的，body 到这里已经解开了，连 content-encoding / content-length 一起存进去，
// 下次取出来浏览器会再解一遍，模型就读坏了（11-06 本机测出来：第二处卡住不进）
const keep = (headers, hash) => { const h = new Headers(); const ct = headers.get("content-type"); if (ct) h.set("content-type", ct); if (hash) h.set("x-hash", hash); return h; };
function manifest() {
  if (!manifestP) manifestP = (async () => {
    const c = await caches.open(CACHE), key = BASE + "manifest.json?v=" + V;
    const hit = await c.match(key); if (hit) return hit.json();   // 这个构建的清单拿过了
    try {
      const r = await fetch(key, { cache: "no-store" });
      if (r.ok) { await c.put(key, r.clone()); for (const k of await c.keys()) if (k.url.includes("manifest.json?v=") && k.url !== new URL(key, self.location.href).href) c.delete(k); return r.json(); }
    } catch {}
    const any = (await c.keys()).find((k) => k.url.includes("manifest.json?v="));   // 网不通：拿上一版清单凑合
    return any ? (await c.match(any)).json() : {};
  })().catch(() => (manifestP = null, {}));
  return manifestP;
}
self.addEventListener("install", (e) => { self.skipWaiting(); e.waitUntil(manifest()); });
self.addEventListener("activate", (e) => { e.waitUntil((async () => { for (const k of await caches.keys()) if (k.startsWith("mononoke-tour-") && k !== CACHE) await caches.delete(k); await self.clients.claim(); })()); });
self.addEventListener("fetch", (e) => {
  const req = e.request; if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url); if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) return;
  const rel = url.pathname.slice(BASE.length), hashed = rel.startsWith("assets/");
  if (!hashed && !TRACKED.test(rel)) return;
  e.respondWith((async () => {
    const c = await caches.open(CACHE), key = url.origin + url.pathname;
    const hit = await c.match(key);
    const want = hashed ? null : (await manifest())[rel] || null;
    if (hit && (hashed || (want && hit.headers.get("x-hash") === want))) return hit;
    let res;
    try { res = hashed ? await fetch(req) : await fresh(req.url); } catch (err) { if (hit) return hit; throw err; }   // 断网：有旧的先给旧的
    if (res.ok && res.type === "basic" && (hashed || want)) {
      e.waitUntil(c.put(key, new Response(res.clone().body, { status: 200, headers: keep(res.headers, want) })).catch(() => {}));
    }
    return res;
  })());
});
// 页面加载完发来这次用到的文件清单：刚下过的还在浏览器缓存里，顺手存进 Cache（SW 刚装好时前面几个文件没经过它）
self.addEventListener("message", (e) => {
  const urls = e.data?.warm; if (!Array.isArray(urls)) return;
  e.waitUntil((async () => {
    const c = await caches.open(CACHE), m = await manifest();
    for (const u of urls) {
      try {
        const url = new URL(u, self.location.href); if (url.origin !== self.location.origin || !url.pathname.startsWith(BASE)) continue;
        const rel = url.pathname.slice(BASE.length), hashed = rel.startsWith("assets/"), want = hashed ? null : m[rel];
        if (!hashed && !want) continue;
        const key = url.origin + url.pathname, hit = await c.match(key);
        if (hit && (hashed || hit.headers.get("x-hash") === want)) continue;
        const r = await (hashed ? fetch(key) : fresh(key)); if (!r.ok || r.type !== "basic") continue;
        await c.put(key, new Response(r.body, { status: 200, headers: keep(r.headers, want) }));
      } catch {}
    }
  })());
});
