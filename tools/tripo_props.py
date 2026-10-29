# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""
道具单图生成模型：assets/concept/props/<id>.png → Tripo image-to-model → assets/tripo_raw/props/<id>.glb
图先用 tools/props_crop.py 从概念图里抠出来。进度存 assets/tripo_props_state.json，断了重跑接着来。

  uv run tools/tripo_props.py                 三个都跑
  uv run tools/tripo_props.py --only sword    只跑一个
  uv run tools/tripo_props.py --only sword --redo   重出（旧文件挪到 _旧版）
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tripo_gen import Tripo, TripoError, load_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "assets/tripo_props_state.json"
SRC = ROOT / "assets/concept/props"
OUT = ROOT / "assets/tripo_raw/props"
PROPS = ["sword", "medicine_chest", "scale"]
PAYLOAD = {"model": "v3.1-20260211", "texture": True, "pbr": False, "texture_quality": "detailed",
           "texture_alignment": "original_image"}


def log(pid, msg): print(f"[props] {time.strftime('%H:%M:%S')} {pid:<15} {msg}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", nargs="*")
    p.add_argument("--redo", action="store_true")
    a = p.parse_args()
    ids = a.only or PROPS
    api = Tripo(load_key())
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    bal0 = api.balance()["balance"]; print(f"[props] 余额 {bal0}")
    OUT.mkdir(parents=True, exist_ok=True)

    def one(pid):
        st = state.setdefault(pid, {})
        dest = OUT / f"{pid}.glb"
        if a.redo and dest.exists():
            old = OUT / "_旧版" / f"{pid}_{time.strftime('%m%d%H%M%S')}.glb"; old.parent.mkdir(exist_ok=True); dest.replace(old)
            st.pop("model_task", None)
        if dest.exists():
            log(pid, "已有，跳过"); return 0
        if not st.get("model_task"):
            tok = api.upload(SRC / f"{pid}.png")
            st["model_task"] = api.create("/generation/image-to-model", {"input": tok, **PAYLOAD})
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            log(pid, f"已提交 {st['model_task']}")
        t = api.wait(st["model_task"], pid, "生成")
        api.download(t["output"]["model_url"], dest)
        if t["output"].get("rendered_image_url"):
            api.download(t["output"]["rendered_image_url"], OUT / f"{pid}_preview.webp")
        log(pid, f"完成，扣 {t.get('credits_consumed', '?')} 积分 → {dest.relative_to(ROOT)} ({dest.stat().st_size/1e6:.0f} MB)")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, ids))
    bal1 = api.balance()["balance"]
    print(f"[props] 余额 {bal1}，本次共花 {bal0 - bal1}")


if __name__ == "__main__":
    try: main()
    except TripoError as e: sys.exit(f"[props] 出错：{e}")
