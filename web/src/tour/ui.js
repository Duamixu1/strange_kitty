// 游览版的界面层（DOM）：拉门转场、底部提示、说明卡、观景点和出口的地面标签、拍照闪光。
// 探案版的 ui/overlay.js 冻结不改，这里只取用得上的几样重写。元素都在 tour.html 里。
const $ = (s) => document.querySelector(s);

export function fusumaWipe(midCallback, duration = 700) {
  const el = $("#wipe");
  el.style.transition = "none"; el.style.transform = "translateX(-100%)";
  void el.offsetWidth;
  el.style.transition = `transform ${duration / 2}ms ease-in`; el.style.transform = "translateX(0)";
  return new Promise((resolve) => {
    setTimeout(async () => {
      await (midCallback && midCallback());
      el.style.transition = `transform ${duration / 2}ms ease-out`; el.style.transform = "translateX(100%)";
      setTimeout(resolve, duration / 2);
    }, duration / 2);
  });
}

export const prompt = {
  set(text) { const el = $("#prompt"); el.textContent = text || ""; el.classList.toggle("show", !!text); },
};

export function toast(text, ms = 1800) {
  const el = $("#toast"); el.textContent = text; el.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), ms);
}

/** 说明卡：标题 + 一两句。open 返回一个 promise，关掉时 resolve */
export const card = {
  get isOpen() { return $("#card").classList.contains("show"); },
  open({ title, body, place }) {
    const el = $("#card");
    el.querySelector(".place").textContent = place || "";
    el.querySelector(".title").textContent = title || "";
    el.querySelector(".body").textContent = body || "";
    el.classList.add("show");
    return new Promise((r) => (this._resolve = r));
  },
  close() { $("#card").classList.remove("show"); this._resolve && this._resolve(); this._resolve = null; },
};

/** 地面上的标签（观景点"観"、出口"上楼"）：每帧按 3D 位置投影到屏幕，可以点 */
export class Tags {
  constructor(onClick) { this.root = $("#tags"); this.items = []; this.onClick = onClick; }
  clear() { this.root.innerHTML = ""; this.items = []; }
  add(id, kind, label, pos, title = label) {
    const el = document.createElement("button");
    el.type = "button"; el.title = title; el.setAttribute("aria-label", title);
    el.className = `tag ${kind}`; el.textContent = label;
    el.addEventListener("pointerdown", (e) => e.stopPropagation());
    el.addEventListener("click", (e) => { e.stopPropagation(); this.onClick(id); });
    this.root.appendChild(el);
    this.items.push({ id, el, pos });
  }
  update(camera, w, h, v) {
    for (const it of this.items) {
      v.set(...it.pos).project(camera);
      const hide = v.z < -1 || v.z > 1 || Math.abs(v.x) > 1.1 || Math.abs(v.y) > 1.1;
      it.el.style.display = hide ? "none" : "";
      if (!hide) {
        // 贴边时把整枚标签留在屏幕内；百分比取标签本身的宽高，不用逐帧测量 DOM。
        const x = (v.x * 0.5 + 0.5) * w, y = (-v.y * 0.5 + 0.5) * h;
        it.el.style.transform = `translate(clamp(4px, calc(${x}px - 50%), calc(${w - 4}px - 100%)), clamp(4px, calc(${y}px - 100%), calc(${h - 4}px - 100%)))`;
      }
    }
  }
}

export function flash() {
  const el = $("#flash"); el.classList.remove("go"); void el.offsetWidth; el.classList.add("go");
}
