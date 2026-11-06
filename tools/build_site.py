"""把游览版打成一个能直接发链接的静态网站（GitHub Pages）。

  python3 tools/build_site.py                 → web/dist/（站点挂在 /strange_kitty/ 下）
  python3 tools/build_site.py --base /        → 挂在域名根下（Cloudflare Pages 之类）
  python3 tools/build_site.py --publish       → 打包后推到 GitHub 的 gh-pages 分支（Pages 从这个分支发布）

做的事：
1. vite build，只打 tour.html（SITE=1 时 vite.config.js 只认这一个入口；探案版的 game.html 不发布）
2. 从地点 JSON、道具表、玩家模型默认值里收集用到的 assets/ 文件，复制进 dist/game-assets/
   （src/paths.js 的 asset() 发布时就读这里）
3. dist/index.html 改成跳转到 tour.html；加 .nojekyll
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB, ASSETS = ROOT / "web", ROOT / "assets"
DIST = WEB / "dist"
REPO_URL = "https://github.com/Duamixu1/strange_kitty.git"


def needed_assets():
    need = set(re.findall(r"processed/kusuriuri[\w./-]*\.glb", (WEB / "src/tour/player.js").read_text()))   # player.js 里写的药郎模型（含精简版）
    props = json.loads((WEB / "src/data/props.json").read_text())
    need |= {d["url"] for k, d in props.items() if not k.startswith("_")}
    need |= {f"processed/kit/{p.name}" for p in (ASSETS / "processed/kit").glob("*.glb")}   # 积木场景全带上（共约 10 MB）

    def walk(o):
        if isinstance(o, dict):
            if "splats" in o and isinstance(o["splats"], list):
                for S in o["splats"]:
                    need.add(f"worldlabs/{S['name']}/splat_{S.get('quality', '500k')}.spz")
                    if S.get("lite"): need.add(f"worldlabs/{S['name']}/splat_{S['lite']}.spz")   # 手机 / 慢网的轻量档（11-05）
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
        elif isinstance(o, str) and re.fullmatch(r"processed/[\w./-]+\.glb", o):
            need.add(o)
    for f in (WEB / "src/data/tour").glob("*.json"): walk(json.loads(f.read_text()))
    # 物怪出没（docs/18）：物怪模型写在 mononoke_fx.js 的 MONSTERS 里，不在地点 JSON；药箱的立绘在 processed/zukan/
    need |= set(re.findall(r"processed/[\w./-]+\.glb", (WEB / "src/tour/mononoke_fx.js").read_text()))
    need |= {f"processed/zukan/{p.name}" for p in (ASSETS / "processed/zukan").glob("*.jpg")}
    return sorted(need)


def optimize_textures():
    """11-06 手机加载慢（国内连 GitHub 每秒几十 KB，进そらりす丸要两三分钟）：只改 dist 里的副本，源文件不动。
    - 大 JPG：最长边压到 2048（天空球 2560），质量 72，变小才换
    - textures/kit 里的大 PNG（不透明）：另存一份 JPG（质量 78），小于原来六成才用；清单写进 tour.html 的 window.__TEX_JPG，kit.js 照清单读 JPG
    """
    def dims(f):
        o = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "hasAlpha", str(f)], capture_output=True, text=True).stdout
        g = lambda k: (re.search(k + r": (\S+)", o) or [None, ""])[1]
        return int(g("pixelWidth") or 0), int(g("pixelHeight") or 0), g("hasAlpha") == "yes"
    before = after = 0; jpg_list = []
    tex = DIST / "textures"
    for f in sorted(tex.rglob("*.jpg")):
        if f.stat().st_size < 150_000: continue
        w, h, _ = dims(f); cap = 2560 if "_sky" in f.name else 2048
        tmp = f.with_suffix(".tmp.jpg"); args = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "72"]
        if max(w, h) > cap: args += ["-Z", str(cap)]
        subprocess.run(args + [str(f), "--out", str(tmp)], capture_output=True)
        b0 = f.stat().st_size; before += b0
        if tmp.exists() and tmp.stat().st_size < b0 * 0.9: tmp.replace(f)
        else: tmp.unlink(missing_ok=True)
        after += f.stat().st_size
    for f in sorted((tex / "kit").glob("*.png")):
        if f.stat().st_size < 120_000: continue
        w, h, alpha = dims(f)
        if alpha: continue
        j = f.with_suffix(".jpg")
        if j.exists(): continue   # 同名 JPG 已经有了（别的用途），不碰
        args = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "78"] + (["-Z", "2048"] if max(w, h) > 2048 else [])
        subprocess.run(args + [str(f), "--out", str(j)], capture_output=True)
        b0 = f.stat().st_size; before += b0
        if j.exists() and j.stat().st_size < b0 * 0.6: jpg_list.append(f.name); after += j.stat().st_size
        else: j.unlink(missing_ok=True); after += b0
    page = DIST / "tour.html"; html = page.read_text()
    html = html.replace("window.__TEX_JPG = [];", "window.__TEX_JPG = " + json.dumps(jpg_list) + ";")
    page.write_text(html)
    print(f"贴图压缩：{before / 1e6:.1f} MB → {after / 1e6:.1f} MB（{len(jpg_list)} 张 PNG 换成 JPG）")


def build(base):
    env = dict(os.environ, SITE="1", SITE_BASE=base)
    subprocess.run(["npx", "vite", "build"], cwd=WEB, env=env, check=True)
    optimize_textures()
    out = DIST / "game-assets"
    total = 0
    for rel in needed_assets():
        src = ASSETS / rel
        if not src.exists(): sys.exit(f"缺文件：assets/{rel}")
        dst = out / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
        total += src.stat().st_size
    (DIST / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=tour.html"><a href="tour.html">进入怪化猫游览版</a>\n')
    (DIST / ".nojekyll").write_text("")
    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(f"→ {DIST}  模型和泼溅 {total / 1e6:.0f} MB，整个站点 {size / 1e6:.0f} MB")


def publish():
    """dist/ 整个作为 gh-pages 分支的唯一一次提交强推上去（不带历史，仓库不会越推越大）"""
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(DIST, tmp, dirs_exist_ok=True)
        run = lambda *a: subprocess.run(a, cwd=tmp, check=True)
        who = lambda k: subprocess.run(["git", "config", k], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        run("git", "init", "-q", "-b", "gh-pages")
        run("git", "config", "user.name", who("user.name")); run("git", "config", "user.email", who("user.email"))   # 作者跟主仓库一致
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", "发布怪化猫游览版")
        run("git", "push", "-f", REPO_URL, "gh-pages")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/strange_kitty/")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    build(a.base)
    if a.publish: publish()
