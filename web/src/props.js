import * as THREE from "three";
import PROPS from "./data/props.json";

// 按挂点名把道具挂到角色身上。道具 GLB 的原点和朝向在 Blender 里已经对好挂点，这里只做三件事：
// 找挂点、换材质（交给调用方的 dress 回调，和角色共用平涂/原色两套）、按动作和时间开关显示。
export async function attachProps(model, loader, assetUrl, dress) {
  const attached = [];
  for (const [id, d] of Object.entries(PROPS)) {
    if (id.startsWith("_")) continue;
    const socket = model.getObjectByName(d.socket);
    if (!socket) continue;                       // 这个模型没有这个挂点（比如 v1），跳过
    const gltf = await loader.loadAsync(assetUrl(d.url));
    const prop = gltf.scene;
    prop.name = `prop_${id}`;
    prop.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; dress(o); } });
    socket.add(prop);
    attached.push({ id, prop, show: d.show || null });
  }
  return {
    list: attached,
    // 每帧调用：clip = 当前动作名，t = 当前动作播到第几秒
    update(clip, t) {
      for (const p of attached) {
        if (!p.show) { p.prop.visible = true; continue; }
        const w = p.show[clip];
        p.prop.visible = !!w && t >= w[0] && t <= w[1];
      }
    },
  };
}
