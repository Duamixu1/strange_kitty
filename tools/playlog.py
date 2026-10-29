# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""看游玩记录：assets/processed/playlogs/<开始时间>.json（游戏页面自动存，见 web/src/game/playlog.js）。
用法：uv run tools/playlog.py            最新一份
     uv run tools/playlog.py 20261029-001210
输出：终端里打印摘要和时间线，同目录存 <id>_路线.png（俯视图：灰色是可走区域，线是走过的路，颜色从蓝到红表示先后，
     圆点是点击的落点，红叉是点了走不过去，三角是按 E / 点击互动的位置）和 <id>_摘要.md。"""
import json, sys, base64
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "assets/processed/playlogs"
ZONE_NAME = {"Z0_gate": "门口", "Z1_corridor": "长廊", "Z2_maids_room": "女中的房间", "Z2a_utayama_room": "歌山的房间", "Z2b_yuki_room": "空房", "Z3_courtyard": "中庭"}

def load(arg):
    files = sorted(LOGS.glob("*.json"))
    if not files: sys.exit(f"{LOGS} 里还没有记录")
    f = next((p for p in files if p.stem == arg), None) if arg else files[-1]
    if not f: sys.exit(f"没找到 {arg}")
    return f, json.loads(f.read_text(encoding="utf-8"))

def fmt(t): return f"{int(t // 60)}:{int(t % 60):02d}"

def summarize(d):
    ev = d["events"]; dur = d["meta"].get("duration") or (ev[-1]["t"] if ev else 0)
    c = Counter(e["type"] for e in ev)
    lines = [f"# 游玩记录 {d['id']}", "", f"总时长 {fmt(dur)}，页面 {d['meta'].get('w')}×{d['meta'].get('h')}，地址参数 `{d['meta'].get('url') or '无'}`", ""]
    # 每个区待了多久
    zt = defaultdict(float); last = None
    for e in ev:
        if e["type"] == "pos":
            if last: zt[last["z"]] += e["t"] - last["t"]
            last = e
    # 怎么走的
    mv = Counter(e.get("mv") for e in ev if e["type"] == "pos")
    clicks = [e for e in ev if e["type"] == "click"]
    blocked = [e for e in clicks if e.get("blocked")]
    keys_down = Counter(e["k"] for e in ev if e["type"] == "key" and e.get("down"))
    looks = [e for e in ev if e["type"] == "look"]
    stuck = [e for e in ev if e["type"] == "path_end" and e.get("why") == "stuck"]
    lines += ["## 一眼看", "",
              "| 项 | 数 |", "|---|---|",
              f"| 走路时间：点击 / 键盘 / 站着 | {mv['click'] * 0.5:.0f} 秒 / {mv['key'] * 0.5:.0f} 秒 / {mv[None] * 0.5:.0f} 秒 |",
              f"| 点击次数（其中走不过去） | {len(clicks)}（{len(blocked)}） |",
              f"| 寻路途中被卡住 | {len(stuck)} |",
              f"| 拖动转视角 | {len(looks)} 次 |",
              f"| 进出房间 | {c['door']} 次 |",
              f"| 拿到证物 | {c['gain']} 件 |",
              f"| 天秤：打开 / 称 / 称错 | {sum(1 for e in ev if e['type'] == 'panel' and e.get('open'))} / {c['weigh']} / {sum(1 for e in ev if e['type'] == 'weigh' and e.get('result') == 'wrong')} |",
              f"| 弹出提示 | {c['hint']} 次 |",
              f"| 最常按的键 | {'、'.join(f'{k}×{n}' for k, n in keys_down.most_common(5)) or '无'} |", ""]
    lines += ["## 各处停留", "", "| 区 | 时间 |", "|---|---|"] + [f"| {ZONE_NAME.get(z, z)} | {fmt(t)} |" for z, t in sorted(zt.items(), key=lambda kv: -kv[1])] + [""]
    # 卡住的地方：两次"进展"（拿证物、亮字、说话、进房间）之间超过 40 秒
    prog = [e for e in ev if e["type"] in ("gain", "talk", "door", "weigh", "interact")]
    gaps = []
    prev = 0.0
    for e in prog + [{"t": dur, "type": "end"}]:
        if e["t"] - prev > 40:
            where = [p for p in ev if p["type"] == "pos" and prev <= p["t"] <= e["t"]]
            zones = Counter(ZONE_NAME.get(p["z"], p["z"]) for p in where).most_common(2)
            hints = [h["id"] for h in ev if h["type"] == "hint" and prev <= h["t"] <= e["t"]]
            gaps.append(f"| {fmt(prev)} → {fmt(e['t'])} | {e['t'] - prev:.0f} 秒 | {'、'.join(z for z, _ in zones)} | {'、'.join(hints) or ''} |")
        prev = e["t"]
    if gaps: lines += ["## 没进展的时段（超过 40 秒）", "", "| 时间 | 长度 | 主要在哪 | 弹了什么提示 |", "|---|---|---|---|"] + gaps + [""]
    # 时间线
    lines += ["## 时间线", ""]
    for e in ev:
        t = e["type"]
        if t in ("pos", "key", "zoom"): continue
        s = {"click": lambda e: "点" + (f"「{e['on']}」" if e.get("on") else f"地面 {e.get('floor')}") + ("，走不过去" if e.get("blocked") else f"，路长 {e.get('len')} 米" if e.get("len") else "（就在跟前）"),
             "path_end": lambda e: {"arrived": "走到了", "keys": "按方向键打断了自动走", "stuck": "自动走被卡住", "panel": "打开天秤打断了自动走"}.get(e["why"], "停下：" + e["why"]),
             "door": lambda e: ("进" if e["enter"] else "出") + ZONE_NAME.get({"maids": "Z2_maids_room", "utayama": "Z2a_utayama_room", "yuki": "Z2b_yuki_room", "courtyard": "Z3_courtyard"}[e["room"]], e["room"]),
             "zone": lambda e: "镜头区 → " + ZONE_NAME.get(e["z"], e["z"]),
             "interact": lambda e: f"互动 {e['id']}（{'点击' if e['by'] == 'click' else '按键'}）",
             "talk": lambda e: f"和 {e['id']} 说话 {e['lines']} 句" + (f"，得到 {e['gained']}" if e.get("gained") else ""),
             "gain": lambda e: f"得到 {e['id']}",
             "say": lambda e: f"台词：{e['first']}…",
             "panel": lambda e: "打开天秤" if e["open"] else "关上天秤",
             "put": lambda e: f"放 {e['id']}" + ("" if e["ok"] else f"（没放上：{e.get('reason')}）"),
             "weigh": lambda e: f"称：{e['result']}" + (f"，亮 {e['lights']}" if e.get("lights") else ""),
             "hint": lambda e: f"提示 {e['id']}（第 {e['level']} 级）",
             "look": lambda e: f"拖动视角 {e['from']} → {e['to']}",
             "look_reset": lambda e: "视角回正",
             "sword": lambda e: "拔剑过场", "ending": lambda e: f"结局 {e.get('ending')}，称错 {e.get('wrong')} 次"}.get(t, lambda e: t)(e)
        lines.append(f"- {fmt(e['t'])} {s}")
    return "\n".join(lines) + "\n"

def draw(d, out):
    wm = json.loads((ROOT / "web/src/data/walkmap.json").read_text(encoding="utf-8"))
    cell, x0, z0, w, h, rows = wm["cell"], wm["x0"], wm["z0"], wm["w"], wm["h"], wm["rows"]
    S = 5   # 每格 5 像素
    im = Image.new("RGB", (w * S, h * S), "#F1E9DA"); dr = ImageDraw.Draw(im)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "1": dr.rectangle([i * S, j * S, i * S + S - 1, j * S + S - 1], fill="#D8D2C4")
    P = lambda x, z: ((x - x0) / cell * S, (z - z0) / cell * S)
    try: font = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 18)
    except OSError: font = ImageFont.load_default()
    cams = json.loads((ROOT / "web/src/world/cameras.json").read_text(encoding="utf-8"))
    for key, r in {**cams["layout"]["rooms"], "courtyard": cams["layout"]["courtyard"]}.items():
        cx, cz = (r["x"][0] + r["x"][1]) / 2, (r["z"][0] + r["z"][1]) / 2
        dr.text(P(cx - 1, cz), {"maids": "女中房", "utayama": "歌山房", "yuki": "空房", "courtyard": "中庭"}[key], fill="#6A4C8C", font=font)
    for n, v in cams["npc_positions"].items():
        x, y = P(v["position"][0], v["position"][2]); dr.ellipse([x - 6, y - 6, x + 6, y + 6], outline="#6A4C8C", width=2)
    pos = [e for e in d["events"] if e["type"] == "pos"]
    T = max((e["t"] for e in pos), default=1) or 1
    for a, b in zip(pos, pos[1:]):
        if abs(a["p"][0] - b["p"][0]) + abs(a["p"][1] - b["p"][1]) > 2.5: continue   # 门转场的瞬移不连线
        k = b["t"] / T; col = (int(60 + 180 * k), int(90 * (1 - k)), int(200 * (1 - k)))
        dr.line([P(*a["p"]), P(*b["p"])], fill=col, width=3)
    for e in d["events"]:
        if e["type"] == "click" and e.get("floor"):
            x, y = P(*e["floor"])
            if e.get("blocked"): dr.line([x - 6, y - 6, x + 6, y + 6], fill="#B42A47", width=3); dr.line([x - 6, y + 6, x + 6, y - 6], fill="#B42A47", width=3)
            else: dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill="#49B3A6")
        if e["type"] == "interact":
            x, y = P(*e["p"]); dr.polygon([(x, y - 7), (x - 6, y + 5), (x + 6, y + 5)], fill="#E6667A" if e["by"] == "click" else "#2A2A4E")
    im.save(out)

def main():
    f, d = load(sys.argv[1] if len(sys.argv) > 1 else None)
    md = summarize(d)
    (f.parent / f"{f.stem}_摘要.md").write_text(md, encoding="utf-8")
    draw(d, f.parent / f"{f.stem}_路线.png")
    print(md)
    print(f"→ {f.parent / (f.stem + '_摘要.md')}\n→ {f.parent / (f.stem + '_路线.png')}")

if __name__ == "__main__":
    main()
