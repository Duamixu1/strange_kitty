"""
药郎模型出精简版（11-05 游28 留下的"加载慢"，总指挥量的：本地 5.2 MB、线上 gzip 2.7 MB，首次进入最大的一个文件）。
不改动作、骨骼名、morph、弹簧骨，player.js / spring.json 不用动，只是文件小：

  1. 动作：平移、缩放通道里整段不变、又等于静止姿势的删掉（7468 条；代码只改骨头的旋转，不改位置和缩放，
     删了混合器照样回到静止姿势）。旋转通道一条不删：弹簧骨、上半身层（投札叠在走路上）、walk_layer 都直接改骨头旋转，
     某段动作里没有这根骨头的旋转轨道，混合器就不会每帧把它复位，代码上一帧写的值会留着（上半身层播完胳膊会停在投札的样子）。
  2. 一模一样的时间轴、数值数组共用一个 accessor（时间轴总共 44 种），所有动作数据收进两个 bufferView。
     原来每条通道各带一个 accessor + bufferView，glTF JSON 有 1.9 MB。
  3. 旋转关键帧存成 16 位整数（glTF 本身允许的 normalized SHORT，three.js 读的时候换回小数，误差 1/32767）。
  4. 关键帧精简：药郎的动作是逐帧烘焙的，前后两帧线性插值就能还原的关键帧删掉（旋转误差 ≤ --tol 度，默认 0.05°；平移 ≤ 0.1 毫米）。
  5. 头发妖化的两个 morph（每个顶点都在动，没法稀疏存）存成 16 位整数（KHR_mesh_quantization，three.js 支持）。
  6. 大贴图 2048 边 jpg 重新压（--tex 边长,质量），脸那张 --face 边长,质量。
网格的 draco 量化另跑 gltf-transform（见 docs/17 第十九节），本脚本只动动作和贴图，网格的 bufferView 原样拷过来。

  uv run --with numpy --with pillow tools/glb_lite_player.py <输入.glb> <输出.glb> [--tex 2048,62]
"""
import io, json, struct, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
CT = {5126: ("<f4", 4), 5122: ("<i2", 2), 5123: ("<u2", 2), 5121: ("u1", 1), 5120: ("i1", 1), 5125: ("<u4", 4)}
REST = {"translation": [0, 0, 0], "rotation": [0, 0, 0, 1], "scale": [1, 1, 1]}


def read_glb(path):
    b = Path(path).read_bytes(); jl = struct.unpack("<I", b[12:16])[0]; j = json.loads(b[20:20 + jl])
    o = 20 + jl; bl = struct.unpack("<I", b[o:o + 4])[0]; return j, b[o + 8:o + 8 + bl]


def write_glb(path, j, binb):
    js = json.dumps(j, separators=(",", ":"), ensure_ascii=False).encode(); js += b" " * (-len(js) % 4); binb = bytes(binb) + b"\0" * (-len(binb) % 4)
    total = 12 + 8 + len(js) + 8 + len(binb)
    Path(path).write_bytes(struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binb), 0x004E4942) + binb)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    tex = [int(x) for x in arg("--tex", "1024,80").split(",")]; face = [int(x) for x in arg("--face", "1024,75").split(",")]; tol = float(arg("--tol", "0.05"))
    j, binb = read_glb(src)
    A, BV = j["accessors"], j["bufferViews"]

    def data(i):
        a = A[i]; bv = BV[a["bufferView"]]; dt, sz = CT[a["componentType"]]; n = NC[a["type"]]
        o = bv.get("byteOffset", 0) + a.get("byteOffset", 0); arr = np.frombuffer(binb, dtype=dt, count=a["count"] * n, offset=o).reshape(a["count"], n)
        return arr.astype(np.float32) / 32767.0 if a.get("normalized") and a["componentType"] == 5122 else arr.astype(np.float32)

    anim_acc = {s[k] for an in j.get("animations", []) for s in an["samplers"] for k in ("input", "output")}
    # ---- 非动作部分：accessor、bufferView 原样留下（重新编号），字节拷过来 ----
    keep_acc = [i for i in range(len(A)) if i not in anim_acc]
    used_bv = {A[i]["bufferView"] for i in keep_acc if "bufferView" in A[i]} | {im["bufferView"] for im in j.get("images", []) if "bufferView" in im}
    used_bv |= {A[i]["sparse"][k]["bufferView"] for i in keep_acc if "sparse" in A[i] for k in ("indices", "values")}   # 身体的头发 morph 是稀疏存的
    for m in j["meshes"]:
        for p in m["primitives"]:
            d = p.get("extensions", {}).get("KHR_draco_mesh_compression")
            if d: used_bv.add(d["bufferView"])
    keep_bv = sorted(used_bv); bv_map = {o: n for n, o in enumerate(keep_bv)}; acc_map = {o: n for n, o in enumerate(keep_acc)}
    out = bytearray(); newBV = []
    big = max(range(len(j["images"])), key=lambda k: BV[j["images"][k]["bufferView"]]["byteLength"])
    for o in keep_bv:
        v = dict(BV[o]); raw = binb[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
        imgs = [k for k, im in enumerate(j["images"]) if im.get("bufferView") == o]
        if imgs:   # 贴图重新压：大的那张缩边 + 降质量，其他的只降质量
            k = imgs[0]; im = Image.open(io.BytesIO(raw)).convert("RGB"); size, q = (tex[0], tex[1]) if k == big else (face[0], face[1])
            if im.size[0] != size:   # 缩小以后描边、眼线会软，补一点锐化
                im = im.resize((size, size), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=int(arg("--sharp", "70")), threshold=2))
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=q, optimize=True); raw = buf.getvalue()
            print(f"贴图 {j['images'][k].get('name')}: {v['byteLength'] // 1024} KB → {len(raw) // 1024} KB（{size} 边，质量 {q}）")
        out += b"\0" * (-len(out) % 4); v["byteOffset"] = len(out); v["byteLength"] = len(raw); v["buffer"] = 0; out += raw; newBV.append(v)
    newA = []
    for i in keep_acc:
        a = dict(A[i])
        if "bufferView" in a: a["bufferView"] = bv_map[a["bufferView"]]
        if "sparse" in a:
            a["sparse"] = json.loads(json.dumps(a["sparse"]))
            for k in ("indices", "values"): a["sparse"][k]["bufferView"] = bv_map[a["sparse"][k]["bufferView"]]
        newA.append(a)
    for m in j["meshes"]:
        for p in m["primitives"]:
            p["attributes"] = {k: acc_map[v] for k, v in p["attributes"].items()}
            if "indices" in p: p["indices"] = acc_map[p["indices"]]
            if "targets" in p: p["targets"] = [{k: acc_map[v] for k, v in t.items()} for t in p["targets"]]
            d = p.get("extensions", {}).get("KHR_draco_mesh_compression")
            if d: d["bufferView"] = bv_map[d["bufferView"]]
    for s in j.get("skins", []):
        if "inverseBindMatrices" in s: s["inverseBindMatrices"] = acc_map[s["inverseBindMatrices"]]
    # morph 存 16 位：数值除以最大绝对值不行（normalized SHORT 只能表示 -1~1，没有比例），头发 morph 最大 0.16，直接按 -1~1 存，精度 1/32767
    mq = 0
    for m in j["meshes"]:
        for p in m["primitives"]:
            for t in p.get("targets", []):
                for k, ai in t.items():
                    a = newA[ai]
                    if "sparse" in a and "bufferView" not in a and a["componentType"] == 5126:   # 稀疏的：只换 values
                        sv = a["sparse"]["values"]; v = newBV[sv["bufferView"]]; n = a["sparse"]["count"] * 3
                        arr = np.frombuffer(out, dtype="<f4", count=n, offset=v["byteOffset"] + sv.get("byteOffset", 0)).copy()
                        if np.abs(arr).max() >= 1: continue
                        q = np.clip(np.round(arr * 32767), -32767, 32767).astype("<i2").tobytes()
                        out += b"\0" * (-len(out) % 4); newBV.append({"buffer": 0, "byteOffset": len(out), "byteLength": len(q)}); out += q
                        sv["bufferView"] = len(newBV) - 1; sv["byteOffset"] = 0; a["componentType"] = 5122; a["normalized"] = True
                        for kk in ("min", "max"):
                            if kk in a: a[kk] = [round(x * 32767) / 32767 for x in a[kk]]
                        v["dead"] = True; mq += 1; continue
                    if "bufferView" not in a or a["componentType"] != 5126 or a["count"] < 1000: continue
                    v = newBV[a["bufferView"]]; arr = np.frombuffer(out, dtype="<f4", count=a["count"] * 3, offset=v["byteOffset"] + a.get("byteOffset", 0)).copy()
                    if np.abs(arr).max() >= 1: continue
                    q = np.clip(np.round(arr * 32767), -32767, 32767).astype("<i2").tobytes()
                    out += b"\0" * (-len(out) % 4); newBV.append({"buffer": 0, "byteOffset": len(out), "byteLength": len(q)}); out += q
                    a.update({"bufferView": len(newBV) - 1, "byteOffset": 0, "componentType": 5122, "normalized": True,
                              "min": [round(x * 32767) / 32767 for x in a["min"]] if "min" in a else None, "max": [round(x * 32767) / 32767 for x in a["max"]] if "max" in a else None})
                    for kk in ("min", "max"):
                        if a[kk] is None: del a[kk]
                    v["dead"] = True; mq += 1
    if mq:
        for key in ("extensionsUsed", "extensionsRequired"): j[key] = sorted(set(j.get(key, [])) | {"KHR_mesh_quantization"})
        print(f"morph 存 16 位：{mq} 个")
    for im in j.get("images", []):
        if "bufferView" in im: im["bufferView"] = bv_map[im["bufferView"]]

    # ---- 动作：删通道、共用 accessor、旋转存 16 位 ----
    fl, sh = bytearray(), bytearray(); cache = {}; stats = {"删": 0, "留": 0}
    def put(arr, kind, quant):
        key = (kind, quant, arr.shape, np.round(arr, 6).tobytes())
        if key in cache: return cache[key]
        n = arr.shape[1]; t = {1: "SCALAR", 3: "VEC3", 4: "VEC4"}[n]
        if quant:
            q = np.clip(np.round(arr * 32767), -32767, 32767).astype("<i2"); sh.extend(b"\0" * (-len(sh) % 4)); off = len(sh); sh.extend(q.tobytes())
            a = {"bufferView": "S", "byteOffset": off, "componentType": 5122, "normalized": True, "count": len(arr), "type": t}
        else:
            off = len(fl); fl.extend(arr.astype("<f4").tobytes())
            a = {"bufferView": "F", "byteOffset": off, "componentType": 5126, "count": len(arr), "type": t}
        if kind == "input": a["min"] = [float(arr.min())]; a["max"] = [float(arr.max())]
        cache[key] = len(newA); newA.append(a); return cache[key]
    for an in j.get("animations", []):
        dur0 = max(float(data(s["input"]).max()) for s in an["samplers"])
        chans, samps = [], []
        for c in an["channels"]:
            s = an["samplers"][c["sampler"]]; path = c["target"]["path"]; outv = data(s["output"])
            if path in ("translation", "scale") and "--nodel" not in sys.argv:
                node = j["nodes"][c["target"]["node"]]
                if np.allclose(outv, outv[0], atol=1e-6) and np.allclose(outv[0], node.get(path, REST[path]), atol=1e-5):
                    stats["删"] += 1; continue
            stats["留"] += 1; inv = data(s["input"]); chain = j["nodes"][c["target"]["node"]].get("name", "").startswith("chain_")   # 弹簧链的旋转留小数：存 16 位以后下摆和腿的碰撞会翻到另一种稳定状态（量过差到 5~26 厘米）
            if path == "rotation": outv = outv / np.linalg.norm(outv, axis=1, keepdims=True)
            if path in ("rotation", "translation") and s.get("interpolation", "LINEAR") == "LINEAR" and len(inv) > 2:
                keep = reduce_keys(inv[:, 0], outv, path, tol); stats["帧前"] = stats.get("帧前", 0) + len(inv); stats["帧后"] = stats.get("帧后", 0) + len(keep)
                inv, outv = inv[keep], outv[keep]
            si = len(samps); samps.append({"input": put(inv, "input", False), "output": put(outv, "output", path == "rotation" and "--noquant" not in sys.argv and not chain),
                                           **({"interpolation": s["interpolation"]} if "interpolation" in s else {})})
            chans.append({"sampler": si, "target": c["target"]})
        an["channels"], an["samplers"] = chans, samps
        dur1 = max(float(data_new(newA, fl, a_i)) for a_i in {sm["input"] for sm in samps}) if samps else 0
        assert abs(dur1 - dur0) < 1e-4, (an["name"], dur0, dur1)   # 每段时长不变（播放代码按时长算节奏）
    for blob, tag in ((fl, "F"), (sh, "S")):
        out += b"\0" * (-len(out) % 4); newBV.append({"buffer": 0, "byteOffset": len(out), "byteLength": len(blob)}); out += blob; idx = len(newBV) - 1
        for a in newA:
            if a.get("bufferView") == tag: a["bufferView"] = idx
    # 换成 16 位以后旧的 float morph 那段字节不要了：重排一遍 bufferView
    alive = [k for k, v in enumerate(newBV) if not v.get("dead")]; remap = {o: n for n, o in enumerate(alive)}; out2 = bytearray(); BV2 = []
    for k in alive:
        v = dict(newBV[k]); raw = out[v["byteOffset"]:v["byteOffset"] + v["byteLength"]]; out2 += b"\0" * (-len(out2) % 4); v["byteOffset"] = len(out2); out2 += raw; BV2.append(v)
    for a in newA:
        if "bufferView" in a: a["bufferView"] = remap[a["bufferView"]]
        for k in ("indices", "values"):
            if "sparse" in a: a["sparse"][k]["bufferView"] = remap[a["sparse"][k]["bufferView"]]
    for m in j["meshes"]:
        for p in m["primitives"]:
            d = p.get("extensions", {}).get("KHR_draco_mesh_compression")
            if d: d["bufferView"] = remap[d["bufferView"]]
    for im in j.get("images", []): im["bufferView"] = remap[im["bufferView"]]
    out, newBV = out2, BV2
    j["accessors"], j["bufferViews"] = newA, newBV; j["buffers"] = [{"byteLength": len(out)}]
    write_glb(dst, j, out)
    print(f"动作通道：删 {stats['删']} 条，留 {stats['留']} 条；关键帧 {stats.get('帧前', 0)} → {stats.get('帧后', 0)}；动作 accessor {len(cache)} 个（原来 {len(anim_acc)}）")
    print(f"写出 {dst}  {Path(src).stat().st_size / 1e6:.2f} MB → {Path(dst).stat().st_size / 1e6:.2f} MB")


def reduce_keys(t, v, path, tol):
    """贪心：从上一个留下的关键帧往后伸，中间每一帧都能被两头线性插值还原（误差在 tol 内）就继续伸；返回留下的下标"""
    lim = np.radians(tol) if path == "rotation" else 1e-4
    keep = [0]; i = 0; n = len(t)
    while i < n - 1:
        j = i + 2
        while j < n:
            u = ((t[i + 1:j] - t[i]) / (t[j] - t[i]))[:, None]; m = v[i] * (1 - u) + v[j] * u
            if path == "rotation":
                if np.dot(v[i], v[j]) < 0: break
                m /= np.linalg.norm(m, axis=1, keepdims=True); err = 2 * np.arccos(np.clip(np.abs((m * v[i + 1:j]).sum(1)), 0, 1))
            else: err = np.linalg.norm(m - v[i + 1:j], axis=1)
            if err.max() > lim: break
            j += 1
        i = j - 1; keep.append(i)
    return keep


def data_new(A, fl, i):   # 新写进去的时间轴最大值
    a = A[i]; return a["max"][0]


if __name__ == "__main__":
    main()
