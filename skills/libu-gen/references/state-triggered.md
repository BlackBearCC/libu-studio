# 状态触发动画：enter / loop / exit 配对

**与 idle 的区别**：idle 是 `_do_idle_action` 概率分支随机播放的循环/一次性站立小动作；**状态触发型**是 UI/逻辑状态切换（如专业形态面板 `opened` → `closed`）时按顺序播放的 **enter → (loop) → exit** 一组。两点关键差异：

1. **exit 视频必须用 enter 末帧作首帧** —— 先生成 enter，从输出 mp4 抽尾帧存为 png，再当 exit 的首帧。否则两段衔接位置/姿态对不上、切换瞬间闪一下。
2. **loop 默认不单独生成** —— enter 末帧本身就是"目标静态形态"，消费端用静帧 + sine wave/微抖动即可；除非需要循环呼吸/眨眼级别细节，否则不要烧额外积分。

## 首尾帧两种用法

| 用法 | 首帧 | 尾帧 | 典型场景 |
|---|---|---|---|
| **持久状态切换（enter/exit 配对）** | 站立参考图 | enter mp4 抽出的末帧 png | 面板 opened → closed、瘫坐 → 起身：进入末态是新姿态，要锚定准确收尾 |
| **一次性反应（self-contained transition）** | 站立参考图 | **同首帧** | hunger=hungry 摸肚子、hunger=full 拍肚子：5s 内做完反应回到站立，首尾相同保证播完无缝衔接 idle 调度，不留中间态污染 |

第二种用法很容易漏掉——尾帧 slot 不传或随便挑会让模型自由发挥末尾姿态，回 idle 时跳变。**一次性 transition 必须显式把首帧重新选作尾帧**。

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

## 属性等级触发（AttributeAnimDirector）

属性（如 hunger / mood / health）跌穿等级阈值时 `AttributeAnimDirector` 调起绑定的动画。每个 level 走两种范式之一，**互斥**：

| 范式 | 何时用 | 行为 |
|---|---|---|
| **state_mode（持续状态）** | 该 level 表达的是"角色现在处于某种持续姿态" — 例如 `hunger=starving` 瘫坐 | 进入：播 transition（站→坐，5s）→ 持久循环 loop_anim（idle_starving，loop=true），冻结 idle 调度 + walk。离开：播反向 transition（坐→站）→ 清空 mode → 恢复 idle 调度 |
| **one-shot transition（一次性反应）** | 该 level 表达的是"短暂反应" — 例如 `hunger=hungry` 摸肚子、`hunger=full` 拍肚子 | 进入：抢断式播一次 transition（5s）→ 立刻回普通 idle 调度。无持续状态、无 loop |

**判别标准**：「角色长期处于这个 level 时，看起来应该一直保持某动作还是只反应一下？」
- 一直保持 → state_mode（如瘫坐、撅嘴、蜷缩）
- 只反应一下 → one-shot（如摸肚子、打嗝、揉眼）

频繁切换"持续姿态"会让玩家以为状态在跳变 → 状态指示器要稳定；反过来"一次性反应"用 loop 表达会显得呆滞。

### director 配置 schema（hunger 实例）

```gdscript
const ATTRIBUTE_BINDINGS := {
    "hunger": {
        "default_level": "normal",
        "transitions": {                              # 跨界播一次
            "full":     "enter_full",                 # → full
            "hungry": {                               # → hungry（方向感知）
                "from_starving": "enter_hungry_from_starving",
                "default":       "enter_hungry_from_normal",
            },
            "starving": "enter_starving",             # → starving
        },
        "state_mode": {                               # 持续状态级，仅配真"状态"
            "starving": {"mode": &"sit", "loop_anim": &"idle_starving"},
        },
        # hungry / full 不在 state_mode 里 = 一次性反应
    },
}
```

`_apply_level()` 顺序：

```
pre-lock state_mode（如有）→ await play_state_transition → 
  state_mode != null: play_anim(loop_anim) 进持久循环
  state_mode == null: character.resume_idle_scheduling() 回普通调度
```

### 架构铁律（Phase 1 踩过的坑）

1. **必须 pre-lock state_mode 再播 transition**。否则 5s transition 播放期会被 behavior_system 的 PATROL 切换或 idle 调度抢断（看不到坐下过渡，直接跳到末状态）。`set_state_mode()` 内部立刻设标志 + 取消 idle timer + 清 walk flag。
2. **`play_state_transition()` 必须抢断 walking**。`_is_walking / _walk_stopping / velocity` 都得清，否则 walk_loop 的 await chain 会覆盖 transition 的 sprite。
3. **behavior_system._process 入口必须检查 `_state_mode != &""` 直接 return**。否则 PATROL/FOLLOW_MOUSE 会在 sit 期间起 walk。
4. **drag/fall 收尾必须查 state_mode**。`_end_drag` / 落地后 `play_anim("idle")` 默认回站立；sit 期间应回 `play_anim(_state_mode_anim)`。
5. **loop_anim 必须在 `_looping_anims` 列表里**才会 `set_animation_loop(true)`，否则播一次停在最后帧不循环。
6. **priming 阶段也要 await transition**。冷启动 hunger 已经在 starving 区间时，让用户看到 5s 坐下过渡，再进 loop —— 比直接 snap 到坐姿好得多。是否在 priming 播 transition 由 `is_prime` 参数控，cooldown 检查跳过。
7. **不要写 `biased_idle` 概率偏置 idle**（早期方案，废弃）—— 状态化场景下用 state_mode 表达，反应式用 one-shot transition。"30% 概率打断" 会冲淡 state 信号也冲淡 reaction 信号。

### 触发条件 & 测试路径

- 自然 decay 触发：写 `hunger.json` value 接近阈值（如 `value=30.5` 偏 hungry 一点），重启 Godot 等几秒 decay 跌过 30 触发 `enter_starving`
- 直接进入触发：写目标 level 区间值（如 `value=5` starving），priming 时 `is_prime=true` 同样 await 播 transition
- 反向触发：用 `tools/rpc-cli/index.cjs character.care.feed` 喂食 +75 hunger，可推过 hungry / full 边界看反向 transition

### offline floor 与 saved value（PetClaw 边界 bug）

`AttributeEngine.register()` 不该 clamp 低于 `offlineFloor` 的 saved value —— offline decay 保护只在"离线一段时间"语义有意义，玩家手动让 hunger 跌到 5 后退出立刻进来，应保持 5。Phase 1 已删 `offlineFloor` 字段及 clamp 逻辑（`src/character/attribute-engine.ts` / `presets.ts` / `level-system.ts`）。
