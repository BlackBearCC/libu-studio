# 状态触发动画：enter / loop / exit 配对

**与 idle 的区别**：idle 是 `_do_idle_action` 概率分支随机播放的循环/一次性站立小动作；**状态触发型**是 UI/逻辑状态切换（如专业形态面板 `opened` → `closed`）时按顺序播放的 **enter → (loop) → exit** 一组。两点关键差异：

1. **exit 视频必须用 enter 末帧作首帧** —— 先生成 enter，从输出 mp4 抽尾帧存为 png，再当 exit 的首帧。否则两段衔接位置/姿态对不上、切换瞬间闪一下。
2. **loop 默认不单独生成** —— enter 末帧本身就是"目标静态形态"，消费端用静帧 + sine wave/微抖动即可；除非需要循环呼吸/眨眼级别细节，否则不要烧额外积分。

## 取 enter 末帧作 png

**首选** —— Mac 上有正经 ffmpeg（`brew install ffmpeg` 装的那个）：
```bash
ffmpeg -ss 4.95 -i ~/Downloads/<slug>-<name>_enter.mp4 -frames:v 1 ~/Downloads/<slug>-<name>_tail.png
```

**Fallback —— Mac 没 ffmpeg / 不想装时，用 chrome 内置 H.264 decoder**（通过已连接的 playwright/CDP 页面跑）：

```js
const fs = require('fs');
const buf = fs.readFileSync(mp4Path);
const b64 = buf.toString("base64");
const { dataUrl } = await page.evaluate(async (b64In) => {
  const bin = atob(b64In);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  const blob = new Blob([arr], { type: "video/mp4" });
  const url = URL.createObjectURL(blob);
  const v = document.createElement("video");
  v.muted = true; v.src = url;
  document.body.appendChild(v);
  await new Promise(r => v.addEventListener("loadedmetadata", r, { once: true }));
  return new Promise((resolve) => {
    v.addEventListener("seeked", () => {
      const c = document.createElement("canvas");
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d").drawImage(v, 0, 0);
      resolve({ dataUrl: c.toDataURL("image/png") });
    }, { once: true });
    v.currentTime = (v.duration || 5) - 0.05;  // seek 到末尾倒数 0.05s
  });
}, b64);
fs.writeFileSync(pngPath, Buffer.from(dataUrl.split(",")[1], "base64"));
```

**为什么必须走 base64 → Blob 这条弯路**：
- `imageio_ffmpeg` 自带的 ffmpeg 是 `--disable-everything` stripped 构建（playwright/imageio 内部用），**解不了 mp4**，碰到就抛 "could not find codec parameters"。它只支持 webm / mjpeg。
- cross-origin mp4 直接 `<video src=cloudURL>` → canvas 染污 → `toDataURL` 抛 SecurityError。**必须**先把 mp4 读成本地 Buffer → atob → Uint8Array → Blob → object URL，让 video 来源变 same-origin 后才能画 canvas。

## enter / exit prompt 句式（"藏到屏幕下面"为例）

- **enter（下沉）**：起初角色完整站立在画面正中。接着身体匀速从画面正中向下沉，依次裙摆/腰/胸/脖子/下巴/嘴/眼睛/额头被画面下沿吃掉，**最后只剩头顶一小撮白发和呆毛露在画面正中央底部**。保持该状态到视频结束。镜头完全固定不动，纯绿色背景不变。
- **exit（上升）**：角色起始状态：身体藏在画面下方画外，**只有头顶一小撮白发和呆毛露在画面正中央底部**。接着身体匀速从画面底部往上升起，依次额头/眼睛/嘴巴/下巴/脖子/红领带/肩膀/裙摆/最后整个身体连脚一起回到画面正中央，恢复正面站立姿态。最后保持站姿直到视频结束。镜头完全固定不动，纯绿色背景不变。

铁律（不写时间戳 / 不描述外观 / 不描述次级部件运动）继续适用，见 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md)。

## Godot 侧（与 idle 的差异）

**不**走 `_do_idle_action` 概率分支。改在 `character_controller.gd` 监听状态信号（如 `superpower_panel.opened` / `closed`），分别 `_play_oneshot("<name>_enter")` / `_play_oneshot("<name>_exit")`。中间静态期用尾帧 + Godot tween 做轻微浮动（不要循环播视频，浪费 GPU 还出 codec 解码热路径）。

> ⚠️ 状态触发动画必须 freeze + `_play_oneshot`，单 `play_anim` 会被 `_do_idle_action` / `behavior.play_anim("idle")` 打断（曾踩过）。

## 属性等级触发（attribute_biased_idle / attribute_transition）

- `attribute_biased_idle`：当 attribute（如 hunger）处于某 level（如 starving）时，idle 概率池里这条权重提到 `bias_weight`（如 0.70）。在 `_do_idle_action` 之前先查 attribute level，命中则按 bias 选这条。
- `attribute_transition`：跨界时（hungry→starving / starving→hungry）由 `AttributeAnimDirector` 抢断式播 `play_state_transition()`。首末帧锁死到对应 `idle_<level>` 的首/末帧，保证无缝衔接。
- ⚠️ **状态指示器原则**：starving 这种 state_mode 一直保持到 level 变化，不要加 sit/stand cycle "显得活泼"——会冲淡状态信号。
