"""把一间 World Labs 房间泼溅摆进走廊布局，并把全景图上的家具位置换算成游戏坐标。
用法：
  python3 tools/room_place.py <泼溅名> --side right|left --door-z -11.0 [--stub 1.0] [--door-raw -0.75] [--scale 1.08]
                              [--pt 名字:u,v ...]
  --side      房间在走廊右侧（+x）还是左侧（-x）；走廊墙在 x=±3
  --door-z    房间门（也是房间中心）在走廊上的 z
  --stub      门墙外留多长的入口过道（米），过道外的脑补走廊用 spz_clip.py 裁掉
  --door-raw  门那面墙在泼溅原始坐标里的 z（用碰撞网格按 z 切片看墙宽突变的地方，女中房和阿雪空房都是 -0.75）
  --scale     不填就用 world.json 的 metric_scale_factor；泼溅还没生成时可以借别的房间的数先算
  --pt        全景图上某件东西落地点的位置，u、v 是 0 到 1 的比例（u=0.5 正前，0.25 左，0.75 右；v=0.5 地平线）
输出：cameras.json 里 splats 用的一条、rooms 用的矩形、spz_clip 的 --zmin、每个 --pt 的游戏坐标。
换算：相机在全景图原点，高度 = 地面。注意 world.json 的 ground_plane_offset 不可靠（女中房偏 0.17、歌山房偏 0.35），
要用 --floor 传实测值：读 splat_500k.spz，取房间内（z>-0.5、|x|<1.2、不透明）点的 y 直方图里最低处最密的那一层。
落地点俯角 θ=(v-0.5)·180°，距离 d=h/tanθ，方位 φ=(u-0.5)·360°。
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORRIDOR_WALL = 3.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name"); ap.add_argument("--side", choices=["right", "left"], required=True)
    ap.add_argument("--door-z", type=float, required=True); ap.add_argument("--stub", type=float, default=1.0)
    ap.add_argument("--door-raw", type=float, default=-0.75); ap.add_argument("--scale", type=float)
    ap.add_argument("--floor", type=float, help="ground_plane_offset，不填读 world.json")
    ap.add_argument("--half-width-raw", type=float, default=1.6, help="房间半宽（原始单位），用来给 rooms 矩形")
    ap.add_argument("--back-raw", type=float, default=1.6, help="里墙的原始 z")
    ap.add_argument("--pt", nargs="*", default=[])
    a = ap.parse_args()
    wj = ROOT / f"assets/worldlabs/{a.name}/world.json"
    sm = json.loads(wj.read_text())["assets"]["splats"]["semantics_metadata"] if wj.exists() else {}
    s = a.scale or sm["metric_scale_factor"]; h = a.floor if a.floor is not None else sm["ground_plane_offset"]
    sign = 1 if a.side == "right" else -1
    door_wall_x = sign * (CORRIDOR_WALL + a.stub)
    cx = door_wall_x - sign * s * a.door_raw            # 原始 z 映射到世界 x：x = cx + sign*s*z_raw
    cz = a.door_z
    yaw = -90 if a.side == "right" else 90
    def world(xr, zr): return (round(cx + sign * s * zr, 2), round(cz + sign * s * xr, 2))   # 右侧：原始 +x → 世界 +z；左侧反过来
    zmin = a.door_raw - a.stub / s
    back_x = cx + sign * s * a.back_raw
    xs = sorted([sign * CORRIDOR_WALL, round(back_x, 2)])
    hw = a.half_width_raw * s
    print(json.dumps({"splat": {"name": a.name, "quality": "500k_clipped", "scale": round(s, 4), "for": "?", "position": [round(cx, 3), round(h * s, 3), cz], "yawDeg": yaw},
                      "room": {"x": xs, "z": [round(cz - hw, 2), round(cz + hw, 2)], "door": [sign * CORRIDOR_WALL, 0, cz]},
                      "spz_clip_zmin": round(zmin, 3), "camera_height": round(h * s, 2)}, ensure_ascii=False))
    for spec in a.pt:
        name, uv = spec.split(":"); u, v = map(float, uv.split(","))
        phi = math.radians((u - 0.5) * 360); theta = math.radians((v - 0.5) * 180)
        d = h / math.tan(theta)
        xr, zr = d * math.sin(phi), d * math.cos(phi)
        print(f"{name}: 原始 ({xr:.2f}, {zr:.2f}) → 世界 {world(xr, zr)}")

if __name__ == "__main__":
    main()
