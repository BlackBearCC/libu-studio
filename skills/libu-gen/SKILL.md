---
name: libu-gen
description: Use when generating a new animation asset (idle / state-triggered / attribute-driven transition) for any registered character via liblib.art — picks one of three production paths (image-refine / text-to-video / action-mimic), runs macOS Vision foreground mask + despill, exports a WebP frame sequence, and lands it into the target project's anim manifest.
---

# libu-gen

通过 liblib.art 生成角色动画素材的流水线：**liblib 出片（三选一路径）→ macOS Vision 抠图 → 绿色残留清理 (despill) → WebP 序列 → target 项目注入 + lab.db 入库**。

角色与目标项目由 lab `characters` 表注册。每个 contributor 在本地 clone 后自行 INSERT 角色行 + 在 `references/characters/<slug>.md` 写一份角色档案。详见 [README](../../README.md) 的 "Register a character" 段。

## 触发场景

- "给 <角色> 加个 XX 动作"、"做个 XX 的 idle 动画"
- "把第 N 张绿幕参考图改成 XX"（参考图洗版）
- "做个面板/状态切换打开关闭时的 enter/exit 配对动画" — **状态触发型**
- "做个 hunger 饿/濒死状态的 idle/transition" — **attribute 驱动型**
- 用户已有绿幕参考图在 liblib 账号里

## 必要准备

- 已登录 liblib.art（账号有积分；**积分按所选模型 + 分辨率算，跑前看 UI 底部那个数字为准**）
- Playwright MCP 可用（工具前缀 `mcp__plugin_playwright_playwright__*`），**默认 headless 后台运行**（plugin `.mcp.json` 已加 `--headless`）
- macOS 14+（用 `VNGenerateForegroundInstanceMaskRequest`）
- Python `imageio-ffmpeg` 已装（自带 ffmpeg 二进制）
- 目标角色已在 `<lab-root>/lab.db` 的 `characters` 表注册；缺则先 INSERT 一行 + 添加 `references/characters/<slug>.md`

## 三条路径决策

| 想做的事 | 走哪条 | reference |
|---|---|---|
| **有一段现成动作 demo**（自拍/找的视频/平台预设），想原样复刻 | **A — 动作模仿** | [path-a-action-mimic.md](references/path-a-action-mimic.md) |
| **自由创作新 idle**（脑子里有想法但没参考视频） | **A.alt — 文生视频** | [path-a-alt-text-to-video.md](references/path-a-alt-text-to-video.md) |
| **先把绿幕参考图洗一版再用** | **A.pre — 图生图** | [path-a-pre-image-refine.md](references/path-a-pre-image-refine.md) |

A.pre 是可选前置；A 或 A.alt 二选一拿到 mp4；阶段 B/C/D 是通用流水线。

## 流水线索引

按需读取对应 reference，**不要预先全部加载**：

| 用途 | reference |
|---|---|
| 选模型（图/视频/动作模仿三张清单 + 适用场景） | [models.md](references/models.md) |
| 阶段 A.pre — 图生图洗参考 | [path-a-pre-image-refine.md](references/path-a-pre-image-refine.md) |
| 阶段 A — 动作模仿 | [path-a-action-mimic.md](references/path-a-action-mimic.md) |
| 阶段 A.alt — 文生视频（含 prompt 三铁律） | [path-a-alt-text-to-video.md](references/path-a-alt-text-to-video.md) |
| 阶段 B — Vision 抠图 + despill + WebP | [pipeline-mask-despill-webp.md](references/pipeline-mask-despill-webp.md) |
| 阶段 C — target 项目（Godot）注入 | [target-inject-godot.md](references/target-inject-godot.md) |
| 阶段 D — 资产归档 + 压缩 + 入 lab.db | [archive-compress.md](references/archive-compress.md) |
| 状态触发动画（enter/loop/exit 配对） | [state-triggered.md](references/state-triggered.md) |
| **角色设定（写 prompt 前 mandatory 读）** | references/characters/<slug>.md |
| 常见坑 + 成本速查 | [troubleshooting.md](references/troubleshooting.md) |

## 通用铁律

1. **用户主导模型选择，skill 不锁定默认**。生成前必须把 **模型 + 分辨率 + 时长（如适用）+ 积分** 四项一起贴给用户确认才点生成。
2. **角色身份完全靠首尾帧参考图锚定**，prompt 里**禁止描述任何外观/五官/服装**。详见 path-a-alt-text-to-video.md 的"prompt 三铁律"。
3. **写 prompt 前必读 `references/characters/<slug>.md`**，对齐角色气质和硬约束词。
4. **每个 anim 跑完必须入 lab.db**：流程结束时通过脚本（见 archive-compress.md）登记 `generations` / `candidates` / `target_inject`。target 项目的 manifest.json 由 `<lab-root>/scripts/export-manifest.py` 自动重生成，**不要手动编辑 target 项目的 manifest.json**。

## 相关文件

- `bgrm.swift` / `bgrm` — macOS Vision 前景抠图 CLI（同目录；首次使用 `swiftc -O bgrm.swift -o bgrm` 编译）
- `<lab-root>/lab.db` — 元数据真相源
- `<lab-root>/scripts/export-manifest.py` — db → target manifest.json
