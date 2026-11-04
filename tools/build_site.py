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
    need = {"processed/kusuriuri_v2_posed_layered.glb"}                       # player.js 默认模型
    props = json.loads((WEB / "src/data/props.json").read_text())
    need |= {d["url"] for k, d in props.items() if not k.startswith("_")}
    need |= {f"processed/kit/{p.name}" for p in (ASSETS / "processed/kit").glob("*.glb")}   # 积木场景全带上（共约 10 MB）

    def walk(o):
        if isinstance(o, dict):
            if "splats" in o and isinstance(o["splats"], list):
                for S in o["splats"]: need.add(f"worldlabs/{S['name']}/splat_{S.get('quality', '500k')}.spz")
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


def build(base):
    env = dict(os.environ, SITE="1", SITE_BASE=base)
    subprocess.run(["npx", "vite", "build"], cwd=WEB, env=env, check=True)
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
