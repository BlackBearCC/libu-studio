# 阶段 B — Vision 抠图 + Despill + WebP 序列

**绝对不要用 ffmpeg chromakey**：liblib 绿幕色偏深(~#04AF41)且边缘有溢色，chromakey 会把白发一起吃掉。用 macOS Vision 前景分割。

**Vision 之后必做 despill**：Vision 只改 alpha，但**半透明边缘像素的 RGB 仍保留原始绿幕色**。放到非绿背景上看，头发丝、脚底阴影会有明显绿晕。必须再扫一遍 RGB，把"绿为主导"的像素的绿通道压下来。

```bash
# 1. 定位 ffmpeg（imageio_ffmpeg 自带）
FFMPEG=$(python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")

# 2. 首次使用时编译 bgrm（macOS Vision 封装，见同目录 bgrm.swift）
SKILL_DIR="$HOME/.claude/skills/libu-gen"
[[ -x "$SKILL_DIR/bgrm" ]] || swiftc -O "$SKILL_DIR/bgrm.swift" -o "$SKILL_DIR/bgrm"

# 3. 抽帧（24 fps, 5s = 121 帧）
rm -rf /tmp/q-raw /tmp/q-masked /tmp/q-despilled && mkdir -p /tmp/q-raw /tmp/q-masked /tmp/q-despilled
"$FFMPEG" -y -i ~/Downloads/<slug>-<name>.mp4 /tmp/q-raw/%04d.png

# 4. 并行 Vision 抠图（M 系列 Mac 约 20s / 120 帧）
cd /tmp/q-raw && ls *.png | xargs -P 4 -I {} "$SKILL_DIR/bgrm" /tmp/q-raw/{} /tmp/q-masked/{}
cd /

# 5. Despill：压绿通道到 max(R, B)。黄色/白色/肤色不受影响（因为它们的 G 不超过 max(R,B)）。
python3 <<'PY'
import numpy as np, glob, os
from PIL import Image
for f in sorted(glob.glob('/tmp/q-masked/*.png')):
    im = np.array(Image.open(f).convert('RGBA')).astype(np.int16)
    r, g, b, a = im[...,0], im[...,1], im[...,2], im[...,3]
    rb_max = np.maximum(r, b)
    mask = (a > 0) & (g > rb_max)
    im[...,1] = np.where(mask, rb_max, g)
    Image.fromarray(np.clip(im, 0, 255).astype(np.uint8), 'RGBA').save(
        f'/tmp/q-despilled/{os.path.basename(f)}')
PY

# 6. 转 WebP 到 lab 母本目录，从 0000 开始命名
#    (target 项目用的压缩版在阶段 D 走 0.5x 降采样)
LAB=<lab-root>/work/<slug>-anim/<name>
mkdir -p "$LAB/webp"
cd /tmp/q-despilled && N=$(ls *.png | wc -l) && for i in $(seq 1 $N); do
  "$FFMPEG" -y -i "$(printf "%04d.png" $i)" -c:v libwebp -quality 90 -preset drawing \
    "$LAB/webp/$(printf "%04d.webp" $((i-1)))" 2>/dev/null
done
ls "$LAB/webp" | wc -l   # 应该等于 121
```

**关键**：
- 帧命名从 `0000.webp` 起（不是 0001），消费端从 0 索引开始读
- Despill 必做，否则放到其他背景色（例如调试背景/合成到屏幕）会看到绿边
- 验证：`python3 -c "from PIL import Image; q=Image.open('$LAB/webp/0030.webp').convert('RGBA'); bg=Image.new('RGBA',q.size,(220,30,50,255)); bg.alpha_composite(q); bg.save('/tmp/check.png')"` 然后肉眼看头发丝 / 脚底有没有绿

## 阶段 B.1 — 碎毛/发丝被 Vision 丢了怎么办

Vision 对**细丝状前景**（chibi 角色的 ahoge 小尖、炸毛、碎发）有时会判为噪声并 alpha=0。现象：原视频里明明有那根飞出去的碎毛，抠图后不见了。

原理：这些细丝在原视频里是"白色被绿幕抗锯齿染成浅绿"（典型像素 `(182, 255, 196)`，`green_strength ≈ 60`），Vision 判成背景；但它们并不是纯绿，所以可以靠 **chroma rescue** 把它们捞回来——根据 `green_strength` 给出一个"连续 alpha"，和 Vision mask 取 max 合并。

把阶段 B 第 5 步的 despill 脚本**替换**为下面这个 hybrid 版本（Vision + chroma rescue + despill 一次做完）：

```python
import numpy as np, glob, os
from PIL import Image
GREEN_LO, GREEN_HI = 15, 90   # gs<LO → 不透明；gs>HI → 透明；之间线性过渡
for rf in sorted(glob.glob('/tmp/q-raw/*.png')):
    name = os.path.basename(rf)
    raw = np.array(Image.open(rf).convert('RGB')).astype(np.int16)
    vision_a = np.array(Image.open(f'/tmp/q-masked/{name}').convert('RGBA'))[..., 3]
    r, g, b = raw[..., 0], raw[..., 1], raw[..., 2]
    gs = g - np.maximum(r, b)  # green strength
    # chroma-based alpha: soft falloff rescues anti-aliased hair edges
    chroma_a = np.clip((GREEN_HI - gs) * 255 / (GREEN_HI - GREEN_LO), 0, 255).astype(np.uint8)
    # combine: Vision-guaranteed regions + chroma-rescued wisps
    final_a = np.maximum(vision_a, chroma_a)
    # despill: clamp green to max(r, b) where we're keeping the pixel
    rb_max = np.maximum(r, b)
    mask = (final_a > 0) & (g > rb_max)
    g2 = np.where(mask, rb_max, g)
    out = np.stack([r, g2, b, final_a], axis=-1).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(f'/tmp/q-despilled/{name}')
```

调参：
- 碎毛**还是没回来** → 降 `GREEN_HI`（比如 70）让判定阈放宽，或升 `GREEN_LO`（比如 25）让更多边缘像素保持高 alpha
- 背景**透不干净**（远处有绿色云雾） → 反向，把 `GREEN_HI` 升到 120

肉眼验证 3 倍放大头发区域：
```bash
python3 -c "from PIL import Image; q=Image.open('$LAB/webp/0000.webp').convert('RGBA'); bg=Image.new('RGBA',q.size,(220,30,50,255)); bg.alpha_composite(q); bg.crop((130,400,300,650)).resize((510,750),Image.NEAREST).save('/tmp/check_hair.png')"
```
