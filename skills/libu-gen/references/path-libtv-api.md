# 阶段 A.libtv — LibTV OpenAPI（agent-im 直连，跳过 Playwright）

适用：不想 / 不能开 Playwright 跑 liblib.art 网页 UI 时（容器环境、headless 服务器、调度任务、想全后台不抢焦点），通过 LibTV 的 agent-im OpenAPI 把任务托管给 LibTV 平台的后端 Agent，自己只做 **上传 → 传话 → 取件** 三件事。

LibTV 平台同时为人类创作者和 Agent 设计；后端 Agent 自己负责挑模型、写 system prompt、编排工作流。**用户侧 Agent 只是搬运工**（详见 `references/orchestrator.md` 的"用户侧不做创作"约束）。

## 何时走 libtv API 而不是 Playwright

| 场景 | 走 libtv API ✓ | 走 Playwright（path-a.alt） |
|---|---|---|
| 容器 / 服务器，没有 Mac UI | ✓ | ✗（macOS only） |
| 用户明确说"全后台不切窗口"（[[feedback_no_focus_steal]]） | ✓ | ⚠️（headless 也行但 brittle） |
| 要复刻已有视频 / 短剧 / MV / 产品广告等复杂工作流 | ✓（后端编排远比 webui flow 强） | ✗ |
| 要用 `multi_camera_grid_9` / `story_beat_grid_4` 等场景化 tool_key | ✓ | ✗（webui 没暴露） |
| 想精确控制模型 + 分辨率 + 比例 + 时长（点选 UI） | ⚠️（后端自选） | ✓ |
| 没钱 / 想看 UI 底部"积分"再决定 | ✗（API 不实时回积分） | ✓ |
| 用户原话「跑 liblib」「打开 liblib 网页」 | ✗ | ✓ |

默认：**复杂创作 + 后台执行场景走 libtv API；想看 UI 控参 / 积分压价场景走 Playwright**。两者输出都是 mp4 URL，下游 B/C/D 流水线（mask → despill → WebP → 注入）完全一样。

## 必要准备

```bash
export LIBTV_ACCESS_KEY="sk-libtv-xxxxxxxxxxxx"
```

可选 `OPENAPI_IM_BASE` / `IM_BASE_URL`，默认 `https://im.liblib.tv`。

无需 pip 装包，纯 Python 标准库。脚本在本 skill 的 `scripts/libtv/` 下：`_common.py / create_session.py / query_session.py / upload_file.py / download_results.py / change_project.py`。所有命令示例都用 `${SKILL_DIR}/scripts/libtv/` 当占位符（实际就是这个 SKILL.md 所在目录的 `scripts/libtv/`）。

## 标准工作流（i2v 图生视频）

最常用的就是 **拿一张绿幕参考图 + 写动作 prompt → i2v 出 5s 视频**。流程：

### 1. 上传参考图 → 拿 OSS URL

```bash
python3 ${SKILL_DIR}/scripts/libtv/upload_file.py /path/to/poka_greenscreen.png
# → {"url": "https://libtv-res.liblib.art/claw/<projectUuid>/<uuid>.png"}
```

把返回的 `url` 记到一个 shell 变量里，下一步要带上。

### 2. create_session 传话

**重要**：i2v 模式必须在 prompt 文本里**明确**告诉后端 Agent "用 imageList 字段加载参考图 URL"，否则后端 Agent 经常忽略文中的 URL 引用，跑成 t2v 出来一个完全不同的角色（实测多次踩坑）。模板：

```bash
LIBTV_ACCESS_KEY=$KEY python3 ${SKILL_DIR}/scripts/libtv/create_session.py \
  "<动作描述>。参考图 URL（必须用 imageList 字段加载）：${REF_OSS_URL}" \
  > /tmp/session.json
SID=$(jq -r .sessionId /tmp/session.json)
```

不带 `--session-id` 就是新建会话；想在已有会话追加任务就加 `--session-id $SID`。同一会话内后端 Agent 共享上下文（适合连续微调）。

#### prompt 写法（i2v）

- **铁律 1-3 全部继承**（见 [path-a-alt-text-to-video.md](path-a-alt-text-to-video.md)）：不写时间戳 / 不描述外观 / 不描述次级部件运动
- **额外约束**：i2v 锁定首帧 = 参考图。所以 prompt 第一句应该写"参考图首帧 [当前姿态] → 0~0.5 秒变身为 [目标姿态] → 0.5~5 秒保持目标姿态做小幅 idle"，让模型有变身缓冲，不要试图直接出"全程目标姿态"——会让模型瞬变把脸搞糊
- **嘴部动作**：所有写 "嘴角微微上扬 / 偶尔嘴角动一下" 都会被模型过度演绎成嘴持续闪动（实测）。如果不需要说话 / 唱歌，**显式写"嘴巴始终闭合不要动"**
- **挂边 / 边缘截断构图**：模型默认把所有角色画全身。要做"角色被画面右边缘截断只露脸+肩+手"这种构图，必须**反复强调**"身体的躯干下部、腰、腿、脚都被画面右边缘截断在画面外不可见" + "身体一定要被画面右边缘截断只露脸+肩+手不要全身可见"——一次说不够

### 3. 轮询 query_session

```bash
LIBTV_ACCESS_KEY=$KEY python3 ${SKILL_DIR}/scripts/libtv/query_session.py $SID --after-seq 0
```

- 间隔 **8s** 一次
- 完成判定：messages 中出现 `role: assistant` 且 content 包含 mp4 URL（`https://libtv-res.liblib.art/...mp4` 或 `https://images-wm.liblib.cloud/...mp4`）
- 超时 3 分钟无结果 → 告知用户"生成时间较长，稍后通过项目画布链接查看"，停止轮询（**不要无限重试，烧积分**）
- 单次 query 失败可重试 1 次，连续 3 次失败停止

### 4. 下载 mp4（必带 Referer 防盗链）

LibTV CDN 用 Tengine 反盗链，curl 默认 403。**必须**带 Referer：

```bash
curl -sSL -H "Referer: https://www.liblib.art/" -o /path/to/output.mp4 "$MP4_URL"
```

或用 skill 自带的 `download_results.py`（自动从 session 取 URL）：

```bash
python3 ${SKILL_DIR}/scripts/libtv/download_results.py $SID \
  --output-dir ~/Documents/libu-studio/work/<series>/raw \
  --prefix <slug>-<name>
```

[[reference 见 feedback_liblib_cdn_referer]]

### 5. 落地 prompts log（强制，详见 [prompts-log.md](prompts-log.md)）

每次 gen 跑完，**不等用户提醒**，立刻 append 到 `~/Documents/ClawContent-Lab/work/<series>/_prompts_log.md`：prompt 全文 + 源 mp4 URL + 状态。这是用户既定流程的一部分（[[feedback_petclaw_doc_drift]] 校准 + 后续二次复用）。

## 上传 / 传话 / 取件铁律

继承 `/tmp/libtv-skills/skills/libtv-skill/SKILL.md` 的"用户侧不做创作"约束：

❌ **不要做**：
- 替用户扩写 / 润色 / 翻译 prompt（用户说"帮我推演分镜"就直接传"帮我推演分镜"）
- 自行拆解任务（如"生成 9 张分镜"拆成 9 次独立 create_session）
- 自行编排镜头描述 / 剧情推演 / 风格分析
- 在消息里塞自己编的 "超写实风格电影级光影 8K" 之类描述词

✅ **要做**：
- 上传本地文件 → 拿 OSS URL
- 把用户原描述 + OSS URL 原封不动发给 `create_session.py`
- 轮询结果 → 下载到本地 → 给用户报 mp4 URL + projectUrl

例外：**i2v 模式下必须显式写出"imageList 字段必须加载 URL"**——这不是创作，是补救后端 Agent 忽略文本 URL 引用的 bug。

## 工具场景速查（场景化 tool_key）

通过 `create_session.py` 的 prompt 文本提到对应能力，后端 Agent 会自动调用：

| 场景 | tool_key | 触发关键词 |
|---|---|---|
| 局部重绘 | `redraw` | "把 XX 改成 YY"、"局部重绘" |
| 擦除 | `erase` | "去掉 XX"、"擦掉" |
| 扩图 | `expand_image` | "扩展到 16:9"、"画面外延" |
| 九宫格多机位 | `multi_camera_grid_9` | "多机位"、"九宫格" |
| 四宫格剧情推演 | `story_beat_grid_4` | "剧情推演四宫格" |
| 25 宫格连贯分镜 | `continuous_storyboard_grid_25` | "25 宫格连贯分镜" |
| 角色脸三视图 | `character_face_turnaround_3view` | "角色脸三视图" |
| 产品三视图 | `product_turnaround_3view` | "产品三视图" |
| 角色三视图 | `character_turnaround_3view` | "角色三视图" |
| 画面推演 +3s | `frame_prediction_plus_3s` | "3 秒后" |
| 画面推演 -5s | `frame_prediction_minus_5s` | "5 秒前" |
| 电影级光影校正 | `cinematic_lighting_correction` | "光影校正" |

## 常见坑

- **i2v 拍出来角色完全变了**：99% 是后端 Agent 忽略了 imageList，跑成 t2v。修法见 prompt 写法那一节"imageList 字段必须加载"显式声明。
- **嘴巴一动一动**：删掉 prompt 里所有 "嘴角微微上扬 / 嘴动" 字眼，加 "嘴巴始终闭合不要动"
- **审核不合规**：`seedance asset 处理失败 审核不合规` 通常是参考图触发的（如二次元 JK 制服误判）。换一张参考图（如 PIL flip 另一侧的图）就行
- **CDN 403**：忘加 `Referer: https://www.liblib.art/` 了
- **超时 3 分钟没出**：复杂任务（短剧 / MV）就是会跑久，停轮询给用户 projectUrl 让他自己看
- **拿到的 mp4 是几个月前的老视频**：libtv API 不会，这是 Playwright 历史栏才会踩的坑（path-a.alt 里用 baseline-diff）。API 路径下 `query_session` 返回的就是当前会话的结果，不会串

## 相关

- 容器版完整 SKILL.md：`/tmp/libtv-skills/skills/libtv-skill/SKILL.md`（更详尽的 OpenAPI 描述）
- 后端 Agent 文档：https://docs.liblib.tv/agent
- 项目画布：`https://www.liblib.tv/canvas?projectId=<projectUuid>`
