# strange_kitty：怪化猫二创小游戏

> 非官方同人作品（fan game），免费，不用于商业用途。《モノノ怪》的角色和世界观版权归原作方所有。本仓库不包含原片画面和官方素材：美术参考图、模型、场景都是自己生成和制作的。

这个游戏取材自剧场版《モノノ怪 唐傘》的特别预告。玩家扮演药贩子，在大奥里四处查看、收集证物，再用天秤配对，找出手鞠物怪的「形・真・理」。

## 运行

```bash
npm install --prefix web
npm run dev --prefix web
```

然后打开 http://localhost:5173/game.html。直接进某个房间：`?at=maids`、`utayama`、`yuki`、`courtyard`、`corridor`。

**操作**
- WASD 或鼠标点击：移动
- E 或回车：查看、对话
- Tab：天秤
- N：纹样开关

## 目录

| 目录 | 内容 |
|---|---|
| `web/` | Three.js + Vite 游戏和查看器（`game.html`、`character.html`） |
| `web/src/data/` | 台词、证物、可走栅格 |
| `assets/processed/` | 游戏里用的模型：药贩子、阿浅、阿龟、歌山、手鞠和道具 |
| `assets/worldlabs/` | World Labs 生成的场景泼溅（走廊、女中房、歌山房、阿雪空房、中庭） |
| `assets/concept/` | 色板、三视图、全景图等概念图 |
| `docs/` | 设定、玩法、文字、待办 |
| `tools/` | Blender、Tripo、World Labs 的处理脚本 |
| `promo/` | 样片和配乐 |

## 制作工具

Tripo（建模）、Blender（绑骨和动作）、World Labs（场景）、Three.js 与 Spark（渲染）
