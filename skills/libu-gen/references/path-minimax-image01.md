# 阶段 A.minimax — MiniMax image-01 直连 API（icon 批量主力）

适用：批量出 UI icon / inventory item icon / achievement badge / status emote 等"统一风格、白底、1024×1024"的成套图标。比走 liblib Playwright 快很多（每张几秒），定价透明（每张 ≈ $0.01），prompt 直接 POST 不用人值班看 UI。

不适用：要透明 PNG / 要绿幕 / 要复杂构图 / 想挂用户 LoRA → 走 liblib（image-01 默认出白底，且不能挂 LoRA）。

## 必要准备

```bash
export MINIMAX_API_KEY="$(cat ~/.config/minimax/api_key)"   # 或任何你存 key 的地方
```

无需脚本，直接 `curl` 或 `python3 -c 'import urllib'` 即可。

## 端点

```
POST https://api.minimaxi.com/v1/image_generation
Authorization: Bearer $MINIMAX_API_KEY
Content-Type: application/json
```

请求 body：

```json
{
  "model": "image-01",
  "prompt": "<风模板 + 单个 icon 描述>",
  "aspect_ratio": "1:1",
  "n": 1,
  "response_format": "url"
}
```

响应：

```json
{ "data": { "image_urls": ["https://.../xxx.jpg"] }, ... }
```

URL 有效期约 1 小时，**必须立即下载**到本地。

## Prompt 三铁律（image-01 专属）

**铁律 1 — 禁词 `sticker` / `die-cut` / `peel-back edge`**。一旦出现，模型自动把目标画一个白色 die-cut 外圈贴纸边框，无法用 chromakey / Vision mask 清掉（白外圈和白底融在一起）。

实测：写 "chibi cartoon **sticker** style" → 出来一颗药丸外面一圈 2px 白边圆角矩形像剪下来的贴纸，废。改成 "chibi cartoon **illustration** style" → 干净。

**铁律 2 — 禁词 `pixel art` / `8-bit` / `voxel` / `minecraft`**。即使你写 "NOT pixel art"，"pixel" 这个词仍然有概率触发像素化输出（minecraft 砖块脸）。**直接不出现这些词**，正向用 `2D hand-drawn watercolor illustration` 或 `bold black ink outline cartoon` 覆盖。

**铁律 3 — 显式声明背景**："on a clean pure white empty canvas" + "isolated centered"。模型默认会加场景（草地 / 木桌 / 货架），icon 必须强调 "isolated" + "centered" + "pure white background"。

## 风模板（PetClaw 风，已经过线上验证）

`$STYLE` 一次写好复用：

```bash
STYLE="Vibrant cheerful 2D hand-drawn watercolor illustration with bold black ink outline, kawaii chibi cartoon style, eye-catching memorable game inventory item icon. Object isolated centered on a clean pure white empty canvas. NOT pixel art, NOT minecraft, NOT photorealistic. 1:1 square composition."
```

调用模板：

```bash
gen() {
  local name="$1" prompt="$2"
  echo "[$name]"
  local url=$(curl -sS -X POST "https://api.minimaxi.com/v1/image_generation" \
    -H "Authorization: Bearer $MINIMAX_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c '
import json, sys
print(json.dumps({
  "model":"image-01",
  "prompt":sys.argv[1],
  "aspect_ratio":"1:1",
  "n":1,
  "response_format":"url"
}))' "$prompt")" \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
print(d["data"]["image_urls"][0] if d.get("data") else "ERR")')
  [[ "$url" == ERR* || -z "$url" ]] && { echo "  FAIL"; return; }
  curl -sS -o "$OUT/${name}.jpg" "$url"
  echo "  $(stat -f%z "$OUT/${name}.jpg") B"
}

# 使用：
OUT=/tmp/icons_out
mkdir -p "$OUT"
gen heart_potion "A single chubby red heart-shaped potion bottle with a cork stopper. $STYLE"
gen gold_ticket "A single golden boarding-pass ticket with a tiny rocket icon on it. $STYLE"
```

## 单个 icon 描述写法（在 `$STYLE` 之前）

模板：`A single <object> <key visual attrs>, <subtle accent>.`

**好例子**（已上线 PetClaw inventory）：
- `A single chubby cute oval pill capsule, half bright sky blue and half sunny yellow, with a tiny calming wave symbol on it, soft glow aura around it, kawaii friendly.`
- `A single elegant cream envelope with a glowing lighthouse wax seal, faint wisps of fog curling around the edges, soft warm light.`
- `A single neatly folded fluffy bath towel in pastel turquoise with playful stripes, a tiny luggage tag tied to it, soft watercolor texture.`

**踩坑例子**：
- ❌ `An achievement sticker with...` → die-cut 白边
- ❌ `Pixel art cute cat...` → minecraft 脸
- ❌ `A medicine bottle on a wooden shelf` → 出货架 + 砍价签 + 完整商店场景
- ❌ `8-bit retro RPG potion` → 像素化

## 流水线步骤总览

```
1. 选 $STYLE 模板 + 写 n 张 prompt 草稿
2. 用户确认 prompt 列表（批量 cost 透明: n × $0.01）
3. 串行 gen()，落本地 jpg
4. （可选）PIL 缩 family / mask 白底 / ICO 打包
5. ★ append _prompts_log.md ★  ← 强制
6. （可选）lab.py gen 入 db
7. 报告用户：本地路径 + 弃用 / 完工清单
```

## 后处理

image-01 输出 1024×1024 jpg / 默认白底。

- **要透明 alpha**：因为是白底不是绿底，**不能用 Vision** （Vision 抠的是 fg/bg 语义分割，对纯白底反而无效）。改用 PIL 阈值：
  ```python
  from PIL import Image, ImageChops
  im = Image.open(src).convert("RGBA")
  px = im.load()
  for y in range(im.height):
    for x in range(im.width):
      r,g,b,a = px[x,y]
      if r > 240 and g > 240 and b > 240:
        px[x,y] = (r, g, b, 0)
  im.save(dst)
  ```
  注意：物体本身的高光也可能 >240，会被误抠出空洞。要避免就让 prompt 加 "no white highlights on the object body, use cream / off-white where highlights are needed"。

- **要白底直接用**：跳过 mask，直接 PIL `Image.LANCZOS` 缩出 family（同 [icon.md](output-types/icon.md) Step 3 起步）。

## 落地 prompts log（强制，每次必跑）

批量 icon 一跑就是 20-30 张，**结束后必须**一次性 append 进 `~/Documents/ClawContent-Lab/work/<slug>-icons/_prompts_log.md`。批量场景特别容易忽略这一步——20 张 prompt 都是手写微调的，丢了下次同主题从零试错。schema 见 [prompts-log.md](prompts-log.md)。

推荐 batch 跑完用一个 here-doc 一次性 append（不要每张追加一次造成 race / 顺序乱）：

```bash
cat >> ~/Documents/ClawContent-Lab/work/$SLUG-icons/_prompts_log.md <<'EOF'

## Batch <YYYY-MM-DD>: <主题>，n=20

**通用规格**: MiniMax image-01 / 1024×1024 / 1:1 / 白底 / ≈ $0.01/张
**$STYLE 模板版本**: v3 (去 sticker + 显式 NOT pixel)

### 完工列表
- `heart_potion` — A single chubby red heart-shaped potion bottle... | URL `https://.../xxx.jpg` | ✅
- `gold_ticket` — A single golden boarding-pass... | URL `...` | ✅
- `nebula_pouch` — ... | URL `...` | ⚠️ 出了草地背景，重跑加 "isolated on pure white"
...

### 踩坑 / 弃用 prompt
- v1 `... sticker style ...` → 白 die-cut 外圈，废
- v1 `... pixel cute cat ...` → minecraft 砖块脸，废
EOF
```

**铁律**：不要把每张图的 URL / prompt 只留在 shell history 里就关 terminal。

## 成本 & 速度

| 项 | 数值 |
|---|---|
| 单张定价 | ≈ $0.01 |
| 单张耗时 | 3-8 秒 |
| 并发上限 | 5 并发（超了 429） |
| 推荐策略 | 串行 `for name in $LIST; do gen ...; done`，简单可控 |

20 个 icon 跑完 < 3 分钟 / $0.20。比 liblib Seedream 5.0 Lite (~4 积分/张 × 4 candidates) 便宜且无人值守。

## lab.db 入库

跑完每个 icon 一行：

```bash
$LAB_PY new $SLUG $NAME --kind idle
$LAB_PY gen $SLUG $NAME --stage a-minimax --path text-to-image \
  --model "image-01" --prompt-file /tmp/prompts/$NAME.txt --chosen \
  --frame-count 1 --duration-s 0 --credits 0.01
```

**`--stage a-minimax`** 是新的 stage 值，对应本路径。`--path text-to-image`。

## 相关

- 官方文档：https://platform.minimaxi.com/document/image-generation
- 风模板的演进史（v1 含 sticker 出白圈 → v2 去 sticker → v3 加 NOT pixel）：见 `~/Documents/ClawContent-Lab/work/<slug>-icons/_prompts_log.md`
- 输出类型流程：[icon.md](output-types/icon.md) Step 2 起步（PIL 缩 family）
- 视频 / 动画 icon 不用本路径，请走 liblib (path-a / path-a.alt) 或 LibTV ([path-libtv-api.md](path-libtv-api.md))
