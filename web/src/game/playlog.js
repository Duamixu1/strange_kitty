// 游玩记录：把按键、点击、拖动视角、位置、换区、互动、对话、天秤、提示都记下来，
// 每 5 秒和关页面时发给开发服务器的 /__playlog，存成 assets/processed/playlogs/<开始时间>.json。
// 看记录：cd mononoke-game && uv run tools/playlog.py（默认最新一份，出摘要和一张俯视路线图）。
// ?log=0 关掉。线上构建没有这个接口，发不出去就算了，不影响游戏。
export function createPlaylog({ enabled = true, meta = {} } = {}) {
  const t0 = performance.now();
  const d = new Date(), pad = (n) => String(n).padStart(2, "0");
  const id = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  const events = [];
  let dirty = false, sent = 0;
  const now = () => Math.round(performance.now() - t0) / 1000;
  function ev(type, data = {}) {
    if (!enabled) return;
    events.push({ t: now(), type, ...data });
    dirty = true;
  }
  const body = () => JSON.stringify({ id, meta: { ...meta, started: d.toISOString(), duration: now() }, events });
  async function flush() {
    if (!enabled || !dirty) return;
    dirty = false;
    try { await fetch("/__playlog", { method: "POST", body: body(), keepalive: true }); sent++; } catch { dirty = true; }
  }
  if (enabled) {
    setInterval(flush, 5000);
    const final = () => { if (dirty && navigator.sendBeacon) { navigator.sendBeacon("/__playlog", new Blob([body()], { type: "application/json" })); dirty = false; } };
    addEventListener("pagehide", final);
    document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") final(); });
  }
  return { id, ev, flush, events, get sent() { return sent; } };
}
