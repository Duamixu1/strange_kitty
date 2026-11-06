"""把做游戏过程中的图片素材按用途分组，每组拼一张缩略总览图。

用法：uv run --with pillow tools/asset_sheets.py
输出：promo/素材总览/<组号>_<组名>.jpg，以及 promo/素材总览/清单.json（每组的文件列表）
分组定义在 GROUPS 里；改了分组重跑即可。
"""
import glob, json, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "promo", "素材总览")
SC = "assets/concept/scenes/"
SH = "assets/processed/shots/"
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"

GROUPS = [
    ("01", "角色造型_药郎与道具", [
        SC + "01_药贩子三视图.png", SC + "11_药贩子_建模三视图.png",
        "assets/concept/props/sword.png", "assets/concept/props/medicine_chest.png",
        "assets/concept/props/scale.png", SC + "09_退魔之剑.png", SC + "10_药箱与天秤.png",
        SH + "chars_对比_2D_vs_Tripo.jpg", "assets/tripo_raw/kusuriuri_v1_preview.jpg",
        "assets/tripo_raw/kusuriuri_v2_preview.webp",
    ]),
    ("02", "角色造型_配角", [
        SC + "16_阿浅_建模三视图.png", SC + "17_阿龟_建模三视图.png", SC + "18_歌山_建模三视图.png",
        SC + "28_志乃_建模三视图.png", SC + "29_久代_建模三视图.png", SC + "30_徳次_建模三视图.png",
        SC + "31_加世_建模三视图.png", SC + "32_坂井伊行_建模三视图.png", SC + "33_小田島_建模三视图.png",
        SC + "_lineup_npc.jpg", SH + "npc14_六人检查.jpg", SH + "npc_身高对比.png",
    ]),
    ("03", "角色造型_物怪", [
        SC + "07_手鞠_本体.png", SC + "08_手鞠_散线.png",
        SC + "35_化猫_建模三视图.png", SC + "36_座敷童子_建模三视图.png", SC + "37_唐伞_建模三视图.png",
        SC + "38_无面_建模三视图.png", SC + "39_火鼠_建模三视图.png", SC + "40_海坊主_建模三视图.png",
        SC + "41_鵺_建模三视图.png", SH + "物怪_十一只_正侧面_身高.jpg",
    ] + sorted(glob.glob(os.path.join(ROOT, "assets/processed/zukan/*.jpg")))),
    ("04", "画风_色板纹样贴图", [
        "assets/concept/00_色板.png", "assets/concept/patterns_preview.png",
        SC + "19_壁画_踢鞠童女.png", SC + "22_大座敷_美人画屏风.png", SC + "23_大座敷_群鸡图天花.png",
        SC + "24_坂井家_雄鸡襖.png", SC + "25_坂井家_浪涛襖.png", SC + "26_坂井家_鹤纹地毯.png",
        SC + "27_坂井家_松鹤屏风.png", SC + "12_证物图标.png", SH + "游31_水墨贴图一套.jpg",
        SH + "游31_水墨材质_坂井家对比.jpg",
    ]),
    ("05", "场景_设定图全景和地图", [
        SC + "02_走廊全景.png", SC + "06_走廊_360全景_fixed.png", SC + "13_女中房_360全景_fixed.png",
        SC + "14_歌山房_360全景.png", SC + "15_阿雪空房_360全景.png", SC + "16_中庭_360全景_fixed.png",
        "assets/worldlabs/对比_v1_v2_v3.jpg", "assets/worldlabs/walkmap.png",
        SC + "20_总地图长卷.png", SH + "tour_总地图_重画版.png", SH + "kitview_map_diorama_0_长卷.jpg",
        SH + "map_大奥门_前后对比.jpg",
    ]),
    ("06", "修改前后_角色和动作", [
        SH + "layer_对比_分层骨链.jpg", SH + "walk2_对比_修前修后.jpg", SH + "walk2_下摆跟腿_对比.jpg",
        SH + "walk2_上身连带_对比_走.jpg", SH + "run2_对比_跑和快走.jpg", SH + "exorcise_挥剑_修前修后.jpg",
        SH + "exorcise_第二轮_头发和横斩.jpg", SH + "tour_拔剑_代码修前修后.jpg",
        SH + "tokuji_后脑勺推平_前后.jpg", SH + "药郎帽子_纹样排除_前后.jpg", SH + "oda_走路_改前改后.jpg",
        SH + "药郎_抬头看_收小对比.jpg", SH + "物怪_客间光晕_前后.jpg", SH + "temari_对比_概念图.jpg",
    ]),
    ("07", "修改前后_场景和镜头", [
        SH + "room_对比_全景图.jpg", SH + "kitcmp_对比_积木vs泼溅.jpg", SH + "corr_对比_三种走廊镜头.jpg",
        SH + "look_对比_房间与走廊.jpg", SH + "tour_镜头俯角_改前改后.jpg", SH + "wanya2_门前_对比.jpg",
        SH + "wanya3_门前外观_对比.jpg", SH + "wanya2_大座敷_对比.jpg", SH + "sakai1_对比.jpg",
        SH + "sakai4_大图案_对比.jpg", SH + "sakai7_客间大座敷_对比.jpg", SH + "游28_大奥lite对比_总览.jpg",
        SH + "游30_井_0前.jpg", SH + "游30_井_3后.jpg",
    ]),
    ("08", "翻车集", sorted(glob.glob(os.path.join(ROOT, "promo/翻车集/*.jpg")) +
                          glob.glob(os.path.join(ROOT, "promo/翻车集/*.webp")))),
    ("09", "实景_坂井家", [
        SH + "tour_sakai_omote_门楼正面.jpg", SH + "tour_sakai_omote_斜看门楼.jpg",
        SH + "tour_sakai_genkan_进门看里面.jpg", SH + "tour_sakai_rouka_廊下深处.jpg",
        SH + "tour_sakai_kyakuma_雄鸡襖.jpg", SH + "tour_sakai_ozashiki_正面.jpg",
        SH + "tour_sakai_misshitsu_正面.jpg", SH + "tour_sakai_daidokoro_厨房.jpg",
        SH + "tour_sakai_daidokoro_古井.jpg", SH + "游29b_后院_坟前特写.jpg",
        SH + "游29b_厨房_捕鼠夹特写.jpg", SH + "kitview_sakai_omote_0_俯视可走.jpg",
    ]),
    ("10", "实景_万屋", [
        SH + "tour_wanya_soto_正面.jpg", SH + "tour_wanya_soto_拱桥.jpg", SH + "tour_wanya_soto_回望街对面.jpg",
        SH + "tour_wanya_genkan_门厅全景.jpg", SH + "tour_wanya_genkan_回望玻璃门.jpg",
        SH + "tour_wanya_rouka_八角厅.jpg", SH + "tour_wanya_rouka_火灯窗.jpg",
        SH + "tour_wanya_niwa_拱桥.jpg", SH + "tour_wanya_niwa_桥上.jpg",
        SH + "tour_wanya_ozashiki_正面看高台.jpg", SH + "tour_wanya_ozashiki_仰望群鸡图.jpg",
        SH + "游29w_门前_湿草鞋.jpg", SH + "游29w_室内庭_地藏特写.jpg", SH + "游29w_长廊_小手印.jpg",
    ]),
    ("11", "实景_大奥", [
        SH + "tour_ooku_corridor_观景点1.jpg", SH + "tour_ooku_corridor_观景点2.jpg",
        SH + "tour_ooku_maids_观景点1.jpg", SH + "tour_ooku_utayama_观景点1.jpg",
        SH + "tour_ooku_yuki_观景点1.jpg", SH + "tour_ooku_courtyard_观景点1.jpg",
        SH + "游29o_主廊_唐伞撑开.jpg", SH + "游29o_女中房_纸鹤.jpg", SH + "游29o_主廊_发簪.jpg",
        SH + "游29o_空房_壁橱打开.jpg", SH + "游29o_中庭_井口站位.jpg", SH + "final_四间房加中庭.jpg",
    ]),
    ("12", "实景_笛小路家_制作中", [
        SH + "游31_笛小路家_水墨总览.jpg", SH + "游31_笛小路家_退魔后彩色总览.jpg",
        SH + "游31_笛小路家_五区块俯视.jpg",
        SH + "kitview_fue_niwa_ink_2_外廊上看雪庭.jpg", SH + "kitview_fue_niwa_color_2_外廊上看雪庭.jpg",
        SH + "kitview_fue_kou_ink_1_香之间正面.jpg", SH + "kitview_fue_kou_color_1_香之间正面.jpg",
        SH + "kitview_fue_oku_ink_3_红色之间.jpg", SH + "kitview_fue_oku_color_3_红色之间.jpg",
        SH + "kitview_fue_mon_ink_1_门.jpg",
    ]),
    ("13", "动作和退魔过程", [
        SH + "药郎_妖化_时间轴.jpg", SH + "tour_拔剑_四个时刻.jpg", SH + "tour_拔剑_第二轮_运镜全程.jpg",
        SH + "游29_斩怨_1怨念抽出.jpg", SH + "游29_斩怨_2斩的是墨团.jpg", SH + "游29_斩怨_3本体褪成浅色.jpg",
        SH + "游29_送_1放札.jpg", SH + "游29_送_2母猫来接.jpg", SH + "物怪_小化猫_魂走.jpg",
        SH + "药郎_送okuri_k.jpg", SH + "小化猫_三段待机_第四版.jpg", SH + "tourpose_对比_游览版动作.jpg",
        SH + "tour_sakai_物怪_bakeneko.jpg", SH + "tour_wanya_物怪_zashiki.jpg",
        SH + "tour_ooku_物怪_karakasa.jpg", SH + "tour_ooku_物怪_札阵.jpg",
    ]),
    ("14", "拍照滤镜和姿势", [
        SH + "tour_wanya_滤镜_原色.jpg", SH + "tour_wanya_滤镜_夜色.jpg", SH + "tour_wanya_滤镜_雨.jpg",
        SH + "tour_wanya_滤镜_褪色.jpg", SH + "tour_sakai_动作_pose_fold_k.jpg",
        SH + "tour_sakai_动作_pose_back_k.jpg", SH + "tour_ooku_动作_驻足看.jpg", SH + "tour_ooku_动作_拔剑.jpg",
    ]),
    ("15", "界面_药箱宅图手机", [
        SH + "游29b_案卷宅图_全齐.jpg", SH + "游29b_案卷宅图_手机.jpg", SH + "游30_宅图_wanya.jpg",
        SH + "游30_冒话_阿浅.jpg", SH + "tour_手机_横屏.jpg", SH + "tour_手机_竖屏.jpg",
        SH + "tour_加载提示_电脑.jpg", SH + "tour_加载提示_手机.jpg",
        "promo/raw/title_cards/B_sakai.png", "promo/raw/title_cards/B_wanya.png",
        "promo/raw/title_cards/B_ooku.png", "promo/raw/网站截图.png",
    ]),
]


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def sheet(title, files, cell=420, cols=4):
    items = [f for f in files if os.path.exists(f)]
    rows = (len(items) + cols - 1) // cols
    pad, lab, head = 12, 46, 70
    W = cols * (cell + pad) + pad
    H = head + rows * (cell * 3 // 4 + lab + pad) + pad
    im = Image.new("RGB", (W, H), (242, 234, 218))
    d = ImageDraw.Draw(im)
    d.text((pad, 16), title, fill=(50, 45, 72), font=font(34))
    f = font(17)
    ch = cell * 3 // 4
    for i, p in enumerate(items):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = head + r * (ch + lab + pad)
        try:
            t = Image.open(p).convert("RGB")
            t.thumbnail((cell, ch))
            im.paste(t, (x + (cell - t.width) // 2, y + (ch - t.height) // 2))
        except Exception as e:  # noqa
            d.text((x, y), f"读不出：{e}", fill=(160, 0, 0), font=f)
        name = f"{i + 1:02d} " + os.path.basename(p)
        while d.textlength(name, font=f) > cell and len(name) > 6:
            name = name[:-2]
        d.text((x, y + ch + 6), name, fill=(50, 45, 72), font=f)
    return im, items


def main():
    os.chdir(ROOT)
    os.makedirs(OUT, exist_ok=True)
    manifest = {}
    for num, name, files in GROUPS:
        files = [os.path.relpath(f, ROOT) if os.path.isabs(f) else f for f in files]
        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            print(f"[{num}] 缺：", *missing, sep="\n  ", file=sys.stderr)
        im, items = sheet(f"{num} {name}（{len(files) - len(missing)} 张）", files)
        im.save(os.path.join(OUT, f"{num}_{name}.jpg"), quality=82)
        manifest[f"{num}_{name}"] = items
        print(num, name, len(items))
    with open(os.path.join(OUT, "清单.json"), "w") as fp:
        json.dump(manifest, fp, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
