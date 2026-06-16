---
name: libu-gen
description: Use when generating a new animation, icon, image, or video asset for any registered character via liblib.art / LibTV CLI (`libtv`) / MiniMax image-01 direct API — picks one of five production paths (image-refine / text-to-video Playwright / action-mimic / libtv-cli / minimax-image01), runs macOS Vision foreground mask + despill, exports a WebP frame sequence or icon family, lands it into the target project, and auto-appends each prompt to the series prompts log.
---

# libu-gen

通过 liblib.art / LibTV 生成角色动画素材的流水线：**出片（四选一路径）→ macOS Vision 抠图 → 绿色残留清理 (despill) → WebP 序列 → target 项目注入 + lab.db 入库 + prompts log 自动追加**。

角色与目标项目由 lab `characters` 表注册。每个 contributor 在本地 clone 后自行 INSERT 角色行 + 在 `references/characters/<slug>.md` 写一份角色档案。详见 [README](../../README.md) 的 "Register a character" 段。

## 触发场景

- "给 <角色> 加个 XX 动作"、"做个 XX 的 idle 动画"
- "把第 N 张绿幕参考图改成 XX"（参考图洗版）
- "做个面板/状态切换打开关闭时的 enter/exit 配对动画" — **状态触发型**
- "做个 hunger 饿/濒死状态的 idle/transition" — **attribute 驱动型**
- 用户已有绿幕参考图在 liblib 账号里

## 必要准备

- 已登录 liblib.art（账号有积分；**积分按所选模型 + 分辨率算，跑前看 UI 底部那个数字为准**）—— Playwright 路径必备
- 已安装并登录官方 `libtv` CLI（`~/.libtv/libtv`，凭据 `~/.libtv/credentials.json`，`libtv login web/phone`）—— LibTV CLI 路径必备（容器 / headless / 后台）。远程机拷 `credentials.json` 即可，旧 `LIBTV_ACCESS_KEY` 已废
- `MINIMAX_API_KEY=...` 环境变量 —— MiniMax image-01 icon 批量路径必备
- Playwright MCP 可用（工具前缀 `mcp__plugin_playwright_playwright__*`），**默认 headless 后台运行**（plugin `.mcp.json` 已加 `--headless`）—— Playwright 路径必备
- macOS 14+（用 `VNGenerateForegroundInstanceMaskRequest`）
- Python `imageio-ffmpeg` 已装（自带 ffmpeg 二进制）
- 目标角色已在 `<lab-root>/lab.db` 的 `characters` 表注册；缺则先 INSERT 一行 + 添加 `references/characters/<slug>.md`

## 五条路径决策

| 想做的事 | 走哪条 | reference |
|---|---|---|
| **有一段现成动作 demo**（自拍/找的视频/平台预设），想原样复刻 | **A — 动作模仿** | [path-a-action-mimic.md](references/path-a-action-mimic.md) |
| **自由创作新 idle**（脑子里有想法但没参考视频），人值班看 UI 控参数 | **A.alt — 文生视频（Playwright）** | [path-a-alt-text-to-video.md](references/path-a-alt-text-to-video.md) |
| **先把绿幕参考图洗一版再用** | **A.pre — 图生图** | [path-a-pre-image-refine.md](references/path-a-pre-image-refine.md) |
| **后台 / 容器 / headless / 复杂工作流（短剧/MV/分镜）/ 用户要求全后台不抢焦点** | **A.libtv — LibTV CLI** | [path-libtv-api.md](references/path-libtv-api.md) |
| **批量出 UI icon / inventory item / badge（统一风格成套白底图）** | **A.minimax — MiniMax image-01 直连 API** | [path-minimax-image01.md](references/path-minimax-image01.md) |

A.pre 是可选前置；A / A.alt / A.libtv 三选一拿到 mp4；批量 icon 走 A.minimax；阶段 B/C/D 是通用流水线。

**Playwright vs LibTV CLI 默认选择**：用户原话"打开 liblib"、"我看下"、"控积分" → Playwright；用户原话"全后台不切窗口"、"容器里跑"、"复刻一段视频" → LibTV CLI（`libtv` 命令行）。两边都能出 mp4，下游流水线一模一样。**MiniMax image-01 走 A.minimax**：只用于 icon 批量场景（动画 / 视频用不上）。

## 输出类型决策（先选这个）

| 想做什么 | 走哪份 |
|---|---|
| **角色动画**（idle / state-triggered / attribute-driven 等，WebP 帧序列，常用） | [output-types/animation.md](references/output-types/animation.md) |
| **图标**（UI icon / emote / badge，单图 + 多尺寸 family，可选 ICO/ICNS 打包） | [output-types/icon.md](references/output-types/icon.md) |
| **静态图片**（portrait / splash / card / cut-in） | [output-types/image.md](references/output-types/image.md) |
| **mp4 视频**（直接拿 mp4 不抠图，HTML5/Godot VideoStream 类用） | [output-types/video.md](references/output-types/video.md) |

输出类型决定了 post-processing 流程；下面的"流水线索引"是 animation 默认拆解，icon/image/video 走各自精简版本。

## 流水线索引

按需读取对应 reference，**不要预先全部加载**：

| 用途 | reference |
|---|---|
| 选模型（图/视频/动作模仿三张清单 + 适用场景） | [models.md](references/models.md) |
| 阶段 A.pre — 图生图洗参考 | [path-a-pre-image-refine.md](references/path-a-pre-image-refine.md) |
| 阶段 A — 动作模仿 | [path-a-action-mimic.md](references/path-a-action-mimic.md) |
| 阶段 A.alt — 文生视频（Playwright，含 prompt 三铁律） | [path-a-alt-text-to-video.md](references/path-a-alt-text-to-video.md) |
| 阶段 A.libtv — LibTV CLI（官方 `libtv` 命令行，i2v / 复杂编排） | [path-libtv-api.md](references/path-libtv-api.md) |
| 阶段 A.minimax — MiniMax image-01 直连 API（icon 批量主力） | [path-minimax-image01.md](references/path-minimax-image01.md) |
| **每次 gen 完强制追加 prompts log（用户不用提醒）** | [prompts-log.md](references/prompts-log.md) |
| 阶段 B — Vision 抠图 + despill + WebP | [pipeline-mask-despill-webp.md](references/pipeline-mask-despill-webp.md) |
| 阶段 C — target 项目（Godot）注入 | [target-inject-godot.md](references/target-inject-godot.md) |
| 阶段 D — 资产归档 + 压缩 + 入 lab.db | [archive-compress.md](references/archive-compress.md) |
| 状态触发动画（enter/loop/exit 配对） | [state-triggered.md](references/state-triggered.md) |
| **角色设定（写 prompt 前 mandatory 读）** | references/characters/<slug>.md |
| 常见坑 + 成本速查 | [troubleshooting.md](references/troubleshooting.md) |
| **全自动模式设计**（默认 interactive；orchestrator 在建） | [orchestrator.md](references/orchestrator.md) |

## 通用铁律

1. **用户主导模型选择，skill 不锁定默认**。生成前必须把 **模型 + 分辨率 + 时长（如适用）+ 积分** 四项一起贴给用户确认才点生成。
2. **角色身份完全靠首尾帧参考图锚定**，prompt 里**禁止描述任何外观/五官/服装**。详见 path-a-alt-text-to-video.md 的"prompt 三铁律"。
3. **写 prompt 前必读 `references/characters/<slug>.md`**，对齐角色气质和硬约束词。
4. **每个 anim 跑完必须用 `lab.py` 入 lab.db**：用 `lab.py new / gen / choose / target / inject` 五步登记 + 落地（详见 [archive-compress.md](references/archive-compress.md) D.3）。**不要手动编辑 target 项目的 manifest.json**——lab.db 是单一真相源，target manifest 由 `lab.py inject` 自动重生成。
5. **生成前 verify "无配音"模式**（仅 Playwright 路径）。UI 底部规格栏（`<模型名> 无配音|<时长>` 那一行）必须显示「无配音」，否则可能：(a) mp4 带 audio track 干扰后处理（多 4 MB / 静音也得 strip），(b) 翻倍扣分。每段生成前 verify 一次，UI 默认偶发回到「有配音」。LibTV CLI 路径用 `--set enableSound=off` 控制，不用管这条。
6. **每次 gen 跑完必须 append `_prompts_log.md`**，用户不用提醒。位置 `~/Documents/ClawContent-Lab/work/<series>/_prompts_log.md`，schema 见 [prompts-log.md](references/prompts-log.md)。漏写 = 下次同主题 prompt 工程从零试错。这是流水线的内置最后一步，不是可选项。

## 相关文件

- `bgrm.swift` / `bgrm` — macOS Vision 前景抠图 CLI（同目录；首次使用 `swiftc -O bgrm.swift -o bgrm` 编译）
- LibTV 出片走官方 `libtv` CLI（`~/.libtv/libtv`），安装 / 登录 / i2v 命令见 [path-libtv-api.md](references/path-libtv-api.md)。旧的 `scripts/libtv/*.py` OpenAPI 客户端已随 LibTV 官方下线删除
- `<lab-root>/lab.db` — 元数据真相源
- `<lab-root>/scripts/export-manifest.py` — db → target manifest.json
- `~/Documents/ClawContent-Lab/work/<series>/_prompts_log.md` — 每次 gen 追加的 prompt 笔记本
