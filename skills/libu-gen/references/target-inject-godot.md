# 阶段 C — target 项目注入（Godot）

> 本 reference 描述 Godot 项目（当前唯一注册的 target）。其他引擎/项目按需新增。
> 当前 character 的 target 路径从 `characters.inject_target_dir` 查（lab.db）。

编辑 `apps/godot-pet/scripts/character/character_controller.gd`（character `poka-v4` 的情况；其他角色按 inject_target_dir 找对应 controller）。

## 1. 加 `_anim_config` 条目

```gdscript
"<name>": {
    "frames_dir": "res://assets/character-design/<slug>/anim/<name>",
    "frame_count": 121,   # 与阶段 B 末尾 ls 数一致
    "fps": 24.0,
},
```

## 2. 在 `_do_idle_action` 加概率分支（仅 kind=idle）

参考 character 文档里"现行 idle 概率分配"那一节（在 references/characters/<slug>.md）。新动作默认 **7%**。

```gdscript
elif roll < 0.XX:   # 在 blink 分支前插一条，XX = 上一段阈值 + 0.07
    print("[Character] Idle action: <name>")
    await _play_oneshot("<name>")
```

同时把 blink 分支的概率阈值往后推 0.07（看现行 `"blink" if roll < 0.NN else "blink_2"` 那行）。

## 3. 循环/单次

单次一次性动作（yawn/stretch/question 那类）**不要**加进 `_looping_anims`。
要循环的子动画（像 `yawn_loop`）才加进去。

## 4. 状态触发型 / 属性驱动型不走概率分支

详见 [state-triggered.md](state-triggered.md)。状态触发型由 main.gd / `AttributeAnimDirector` 监听信号 → 直接 `_play_oneshot(<name>)` 或 `play_state_transition()`。

## 5. 验证

让用户打开 Godot 编辑器跑 main.tscn，看 console：
```
[Character] Animation '<name>': 121/121 frames (from 0), 24.0 FPS, loop=false
```
若 loaded < total，帧缺或路径错。

## 6. 不要手动改 manifest.json

target 项目的 `manifest.json` 由 lab 脚本生成。阶段 D 跑完 `lab.db` 入库后，执行：

```bash
python3 ~/Documents/petclaw-lab/scripts/export-manifest.py \
  ~/Documents/petclaw-lab/lab.db <slug> \
  --out <inject_target_dir>/manifest.json
```

详见 [archive-compress.md](archive-compress.md)。
