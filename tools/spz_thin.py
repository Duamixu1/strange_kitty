# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""给高斯泼溅 .spz 出一份手机用的瘦身版（lite）：按视觉重要性留点，不均匀抽。
重要性 = 不透明度 × 投影面积（最大两轴缩放之积）。做法：
  1. 先扔掉几乎看不见的点（alpha < --amin）；
  2. 空间分格（体素 5 cm），每个格子按自己的点数等比例留（至少 1 个，墙面大色块不出洞），格子里按重要性从高到低留（--mode strat，默认）；
     --mode global 是另一种：每格保底一个后全局按重要性补——11-05 试过，大点全留、细点全丢，屏风花纹糊成一片，不用；
  3. 可选：被删得多的格子把留下的点放大一点（--grow，默认 1 不放大）。
点数自动二分，让文件 ≤ --target 字节。保持原文件的点顺序（压缩率更好）。
用法：uv run tools/spz_thin.py <房间名> [--q 500k_clipped] [--target 3450000] [--voxel 0.06]
  输出 assets/worldlabs/<房间名>/splat_<q>_lite.spz
也可以直接给路径：uv run tools/spz_thin.py <输入.spz> --out <输出.spz>
读写法同 spz_clip.py（SPZ v2/v3，gzip 包 16 字节头 + 各属性数组）。"""
import argparse, gzip, struct, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MAGIC = 0x5053474E


def read_spz(path):
    raw = gzip.decompress(Path(path).read_bytes())
    hdr = struct.unpack_from("<IIIBBBB", raw, 0)
    magic, version, n, sh_deg, frac_bits = hdr[:5]
    if magic != MAGIC: sys.exit(f"不是 SPZ 文件（magic {magic:#x}）")
    rot_bytes = 3 if version == 2 else 4
    sh_dim = (sh_deg + 1) ** 2 - 1
    sizes = [("pos", 9), ("alpha", 1), ("color", 3), ("scale", 3), ("rot", rot_bytes), ("sh", sh_dim * 3)]
    off = 16; parts = {}
    for name, per in sizes:
        parts[name] = np.frombuffer(raw, np.uint8, n * per, off).reshape(n, per) if per else np.zeros((n, 0), np.uint8)
        off += n * per
    if off != len(raw): print(f"提示：文件还有 {len(raw) - off} 字节没对上（版本 {version}），按已知布局继续")
    b = parts["pos"].reshape(n, 3, 3).astype(np.int32)
    v = b[:, :, 0] | (b[:, :, 1] << 8) | (b[:, :, 2] << 16)
    v = np.where(v & 0x800000, v - 0x1000000, v)
    return hdr, parts, v / (1 << frac_bits)


def write_spz(path, hdr, parts, keep, scale_u8=None):
    magic, version, n, sh_deg, frac_bits, flags, reserved = hdr
    m = int(keep.sum())
    out = bytearray(struct.pack("<IIIBBBB", magic, version, m, sh_deg, frac_bits, flags, reserved))
    for name in ("pos", "alpha", "color", "scale", "rot", "sh"):
        arr = scale_u8 if (name == "scale" and scale_u8 is not None) else parts[name]
        out += np.ascontiguousarray(arr[keep]).tobytes()
    data = gzip.compress(bytes(out), compresslevel=9)
    Path(path).write_bytes(data)
    return len(data)


def plan(parts, P, m, voxel, amin, grow, mode="strat"):
    """返回 (keep 布尔数组, 新 scale u8)。"""
    n = len(P)
    a = parts["alpha"][:, 0].astype(np.float64) / 255.0
    ls = parts["scale"].astype(np.float64) / 16.0 - 10.0          # ln(缩放)
    ss = np.sort(ls, axis=1)
    area = np.exp(ss[:, 2] + ss[:, 1])                              # 最大两轴之积 ∝ 投影面积
    score = a * area
    alive = a >= amin
    # 体素编号
    q = np.floor((P - P.min(0)) / voxel).astype(np.int64)
    dims = q.max(0) + 1
    vid = (q[:, 0] * dims[1] + q[:, 1]) * dims[2] + q[:, 2]
    # 按 (体素, -重要性) 排序，每个体素第一个就是保底点
    order = np.lexsort((-score, vid))
    order = order[alive[order]]
    first = np.ones(len(order), bool); first[1:] = vid[order][1:] != vid[order][:-1]
    floor_idx = order[first]
    keep = np.zeros(n, bool)
    if mode == "strat":
        # 分层：每个体素按自己的点数等比例留（至少 1 个），格子里按重要性从高到低留；比例二分到总数 = m
        ov = vid[order]
        start = np.searchsorted(ov, ov, side="left")
        rank = np.arange(len(order)) - start
        cnt = np.bincount(np.unique(ov, return_inverse=True)[1])[np.unique(ov, return_inverse=True)[1]]
        lo, hi = 0.0, 1.0
        for _ in range(30):
            fr = (lo + hi) / 2
            k = int((rank < np.maximum(1, np.round(fr * cnt))).sum())
            if k > m: hi = fr
            else: lo = fr
        sel = rank < np.maximum(1, np.round(lo * cnt))
        keep[order[sel]] = True
    elif len(floor_idx) >= m:   # 体素太细，保底点就超额了：只在保底点里按重要性挑
        keep[floor_idx[np.argsort(-score[floor_idx])[:m]]] = True
    else:
        keep[floor_idx] = True
        rest = np.where(alive & ~keep)[0]
        need = m - len(floor_idx)
        keep[rest[np.argsort(-score[rest])[:need]]] = True
    # 覆盖补偿：每个体素 全部覆盖 / 留下覆盖，按面积比放大留下的点（线性缩放取平方根），封顶 grow
    _, inv = np.unique(vid, return_inverse=True)
    tot = np.bincount(inv, weights=score * alive)
    kept = np.bincount(inv, weights=score * keep)
    ratio = np.where(kept > 0, tot / np.maximum(kept, 1e-30), 1.0)
    f = np.clip(np.sqrt(ratio[inv]), 1.0, grow)
    new_scale = parts["scale"].astype(np.float64) + 16.0 * np.log(f)[:, None]
    new_scale = np.clip(np.round(new_scale), 0, 255).astype(np.uint8)
    return keep, new_scale, f


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src", help="房间名（assets/worldlabs/<名>）或 .spz 路径")
    p.add_argument("--q", default=None, help="原 quality 名，如 500k_clipped / 500k_level")
    p.add_argument("--out")
    p.add_argument("--target", type=int, default=3_450_000, help="输出文件上限（字节）")
    p.add_argument("--voxel", type=float, default=0.05, help="保底体素边长（文件原始单位）")
    p.add_argument("--amin", type=float, default=0.02, help="不透明度低于这个直接扔")
    p.add_argument("--mode", default="strat", choices=["strat", "global"], help="strat：每格等比例留；global：每格保底一个后全局按重要性补")
    p.add_argument("--grow", type=float, default=1.0, help="补偿放大封顶倍数（1 = 不放大；11-05 试过 1.15，更糊且没换来更少的洞）")
    a = p.parse_args()
    if a.src.endswith(".spz"):
        src = Path(a.src); dst = Path(a.out) if a.out else src.with_name(src.stem + "_lite.spz")
    else:
        if not a.q: sys.exit("给房间名时要带 --q")
        d = ROOT / "assets" / "worldlabs" / a.src
        src = d / f"splat_{a.q}.spz"; dst = Path(a.out) if a.out else d / f"splat_{a.q}_lite.spz"
    hdr, parts, P = read_spz(src)
    n = hdr[2]
    src_size = src.stat().st_size
    # 二分点数，让文件刚好落在 target 以内
    lo, hi = 1000, n
    m = min(n, int(n * a.target / src_size * 0.95))
    best = None
    for _ in range(8):
        keep, sc, f = plan(parts, P, m, a.voxel, a.amin, a.grow, a.mode)
        size = write_spz(dst, hdr, parts, keep, sc)
        if size <= a.target:
            best = (m, size, f[keep]); lo = m
        else:
            hi = m
        if hi - lo < n * 0.005: break
        m = (lo + hi) // 2 if best else int(m * a.target / size * 0.98)
    if best is None: sys.exit("压不到目标大小")
    if best[0] != m:   # 最后一次不是最佳那次，重写一遍
        keep, sc, f = plan(parts, P, best[0], a.voxel, a.amin, a.grow, a.mode)
        write_spz(dst, hdr, parts, keep, sc)
    m, size, fk = best
    print(f"{src.parent.name}/{src.name}: {n} → {m} 点（{m / n:.0%}），{src_size / 1e6:.2f} → {size / 1e6:.2f} MB，"
          f"放大了的点 {np.mean(fk > 1.001):.0%}（平均 ×{fk.mean():.3f}）→ {dst.relative_to(ROOT) if dst.is_relative_to(ROOT) else dst}")


if __name__ == "__main__":
    main()
