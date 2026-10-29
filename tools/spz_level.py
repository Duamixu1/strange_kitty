# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""把 World Labs 泼溅里"往远处下沉"的地面拉平：y' = y - (f(z) - f(0))，f(z) 是按碰撞网格实测的地面剖面（分段线性）。
只沿纵深剪切，墙保持竖直；每个高斯球的协方差按局部雅可比 J 变换 Σ' = J Σ Jᵀ，再分解回缩放和旋转。
坐标是文件原始坐标（y 向下、正前方 +z）。只支持 SPZ v2（旋转 3 字节）。
输出：<泼溅目录>/splat_<q>_level.spz 和 level.json（剖面，tools/walkmap.py 用它同步校平碰撞网格）。
用法：uv run tools/spz_level.py corridor_v3 [--q 500k] [--bin 0.25] [--xhalf 1.2] [--check]
  --check 只做一次 k=0 的编解码往返，检查误差"""
import argparse, gzip, json, struct, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from walkmap import load_glb   # noqa: E402

def read_spz(p):
    raw = gzip.decompress(p.read_bytes())
    magic, ver, n, shd, fb, fl, rs = struct.unpack_from("<IIIBBBB", raw, 0)
    if ver != 2 or shd != 0: sys.exit(f"只支持 v2、0 阶球谐（这是 v{ver}、{shd} 阶）")
    o = 16
    pos = np.frombuffer(raw, np.uint8, n * 9, o).reshape(n, 3, 3).astype(np.int32); o += n * 9
    alpha = np.frombuffer(raw, np.uint8, n, o); o += n
    color = np.frombuffer(raw, np.uint8, n * 3, o); o += n * 3
    scale = np.frombuffer(raw, np.uint8, n * 3, o).reshape(n, 3); o += n * 3
    rot = np.frombuffer(raw, np.uint8, n * 3, o).reshape(n, 3); o += n * 3
    v = pos[:, :, 0] | (pos[:, :, 1] << 8) | (pos[:, :, 2] << 16); v = np.where(v & 0x800000, v - 0x1000000, v)
    return dict(hdr=(magic, ver, n, shd, fb, fl, rs), P=v / (1 << fb), alpha=alpha, color=color, scale=scale, rot=rot)

def write_spz(p, d, P, scale, rot):
    magic, ver, n, shd, fb, fl, rs = d["hdr"]
    q = np.round(P * (1 << fb)).astype(np.int64); q = np.where(q < 0, q + (1 << 24), q).astype(np.uint32)
    pb = np.stack([q & 255, (q >> 8) & 255, (q >> 16) & 255], -1).astype(np.uint8)
    out = struct.pack("<IIIBBBB", *d["hdr"]) + pb.tobytes() + d["alpha"].tobytes() + d["color"].tobytes() + scale.astype(np.uint8).tobytes() + rot.astype(np.uint8).tobytes()
    p.write_bytes(gzip.compress(out, compresslevel=6))

def quat_to_mat(x, y, z, w):
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)

def mat_to_quat(R):
    # Shepperd，逐点
    t = np.trace(R, axis1=1, axis2=2); q = np.zeros((len(R), 4))
    m = t > 0; s = np.sqrt(np.maximum(t[m] + 1, 1e-12)) * 2
    q[m] = np.stack([(R[m, 2, 1] - R[m, 1, 2]) / s, (R[m, 0, 2] - R[m, 2, 0]) / s, (R[m, 1, 0] - R[m, 0, 1]) / s, s / 4], -1)
    for i, (a, b, c) in enumerate(((0, 1, 2), (1, 2, 0), (2, 0, 1))):
        mm = (~m) & (R[:, a, a] >= R[:, b, b]) & (R[:, a, a] >= R[:, c, c]); m = m | mm
        s = np.sqrt(np.maximum(1 + R[mm, a, a] - R[mm, b, b] - R[mm, c, c], 1e-12)) * 2
        qq = np.zeros((mm.sum(), 4)); qq[:, a] = s / 4
        qq[:, b] = (R[mm, b, a] + R[mm, a, b]) / s; qq[:, c] = (R[mm, c, a] + R[mm, a, c]) / s; qq[:, 3] = (R[mm, c, b] - R[mm, b, c]) / s
        q[mm] = qq
    q /= np.linalg.norm(q, axis=1, keepdims=True); q[q[:, 3] < 0] *= -1
    return q

def decode_cov(scale_b, rot_b):
    s = np.exp(scale_b.astype(np.float64) / 16 - 10)
    xyz = rot_b.astype(np.float64) / 127.5 - 1; w = np.sqrt(np.maximum(0, 1 - (xyz ** 2).sum(1)))
    R = quat_to_mat(xyz[:, 0], xyz[:, 1], xyz[:, 2], w)
    return R @ (s[:, :, None] ** 2 * np.transpose(R, (0, 2, 1)))

def encode_cov(S):
    lam, V = np.linalg.eigh(S)
    V[np.linalg.det(V) < 0, :, 0] *= -1
    q = mat_to_quat(V)
    sb = np.clip(np.round((np.log(np.sqrt(np.maximum(lam, 1e-20))) + 10) * 16), 0, 255)
    rb = np.clip(np.round((q[:, :3] + 1) * 127.5), 0, 255)
    return sb, rb

def floor_profile(V, F, bin_, xhalf):
    T = V[F]; c = T.mean(1); n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ny = np.abs(n[:, 1]) / (np.linalg.norm(n, axis=1) + 1e-12)
    sel = (ny > 0.85) & (np.abs(c[:, 0]) < xhalf)
    zs = np.arange(np.floor(c[sel, 2].min()), np.ceil(c[sel, 2].max()) + bin_, bin_); prof = []
    for z in zs:
        m = sel & (np.abs(c[:, 2] - z) < bin_)
        if m.sum() < 8: continue
        ys = c[m, 1]; prof.append((z, float(np.percentile(ys, 90))))   # y 向下：地面是 y 最大的那层
    prof = np.array(prof)
    k = np.ones(5) / 5; yp = np.convolve(np.pad(prof[:, 1], 2, mode="edge"), k, mode="valid")   # 平滑
    return prof[:, 0], yp

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--q", default="500k")
    ap.add_argument("--bin", type=float, default=0.25); ap.add_argument("--xhalf", type=float, default=1.2); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(); D = ROOT / "assets/worldlabs" / a.name
    d = read_spz(D / f"splat_{a.q}.spz"); P = d["P"]
    S = decode_cov(d["scale"], d["rot"])
    if a.check:
        sb, rb = encode_cov(S); S2 = decode_cov(sb, rb)
        rel = np.linalg.norm(S2 - S, axis=(1, 2)) / (np.linalg.norm(S, axis=(1, 2)) + 1e-20)
        print(f"往返误差：协方差相对误差 中位 {np.median(rel):.4f}，95% {np.percentile(rel, 95):.4f}；缩放字节不同 {(sb != d['scale']).mean():.1%}，旋转字节不同 {(rb != d['rot']).mean():.1%}")
        return
    V, F = load_glb(D / "collider.glb")
    zs, ys = floor_profile(V, F, a.bin, a.xhalf)
    f0 = float(np.interp(0.0, zs, ys))
    off = lambda z: np.interp(z, zs, ys) - f0           # 超出剖面范围按端点值平移
    slope = lambda z: np.interp(z, zs[:-1] + np.diff(zs) / 2, np.diff(ys) / np.diff(zs), left=0, right=0)
    P2 = P.copy(); P2[:, 1] = P[:, 1] - off(P[:, 2])
    J = np.tile(np.eye(3), (len(P), 1, 1)); J[:, 1, 2] = -slope(P[:, 2])
    S2 = J @ S @ np.transpose(J, (0, 2, 1))
    sb, rb = encode_cov(S2)
    out = D / f"splat_{a.q}_level.spz"; write_spz(out, d, P2, sb, rb)
    (D / "level.json").write_text(json.dumps({"_说明": "spz_level.py 写的地面剖面（原始坐标，y 向下）。y' = y - (interp(z, z, y) - f0)", "z": zs.round(4).tolist(), "y": ys.round(4).tolist(), "f0": round(f0, 4)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"地面剖面 {len(zs)} 段，z {zs[0]:.2f}..{zs[-1]:.2f}，原点地面 y={f0:.3f}，最大校正 {np.abs(ys - f0).max():.2f}（原始单位）→ {out.relative_to(ROOT)}，剖面 level.json")

if __name__ == "__main__":
    main()
