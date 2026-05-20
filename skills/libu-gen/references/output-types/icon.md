# Output type — Icon

For UI icons (app icon, emote badge, achievement medal, status indicator). A
single image plus a multi-size family, optionally packaged as `.ico` / `.icns`.

## When this applies

- Square asset, no animation
- Needs **multiple resolutions** ({16, 32, 64, 128, 256, 512, 1024})
- Often needs **transparent background** (use the same green-screen → mask
  pipeline as animations, just on a single frame)
- May need platform packaging (`.ico` for Windows, `.icns` for macOS, raw PNG
  set for web)

## Pipeline

```
liblib image-refine OR MiniMax image-01 direct API   →  (optional) Vision mask + despill
                                                      →  PIL resize family  →  ICO / ICNS pack
                                                      →  lab.db  →  target inject
```

### Step 1 — generate the source

Two routes — pick by use case:

**Route A — liblib via Playwright** (when you want to control model + 积分 in UI). Use `image-refine` (with reference) or any text-to-image model listed in [models.md](../models.md). Aim for **1024×1024 minimum** so downscales stay sharp.

**Route B — MiniMax image-01 direct API** (recommended for **batch icon families** — UI inventory items, achievement badges, status emotes). Skips the Playwright dance, costs ~$0.01 per image, returns a 1024×1024 URL within seconds. See [path-minimax-image01.md](../path-minimax-image01.md) for prompt iron rules (do NOT mention `sticker` / `die-cut` — model paints a white outer ring border) and shell template.

For a transparent icon, generate on a flat green-screen background — the same
pipeline as animation references. For an opaque flat-color background icon,
skip the mask stage. **MiniMax image-01** defaults to flat **pure white background** with no mask needed — perfect for icons that go on a white card / panel; if your target panel is dark, you'll need to mask out the white BG (PIL `getextrema` + threshold, not Vision — Vision is tuned for green).

Register in lab.db as a single-frame generation:

```bash
$LAB_PY new $SLUG $NAME --kind idle  # icons reuse the 'idle' kind for now
$LAB_PY gen $SLUG $NAME --stage a-pre --path image-refine \
  --model "Seedream 5.0 Lite" --prompt-file /tmp/icon.txt --chosen \
  --frame-count 1 --duration-s 0
```

### Step 2 — mask + despill (only if transparent)

Run a one-shot version of the Vision pipeline from
[pipeline-mask-despill-webp.md](../pipeline-mask-despill-webp.md), but skip
the `ffmpeg` frame extraction (you already have a PNG):

```bash
SKILL_DIR="$HOME/.claude/skills/libu-gen"
$SKILL_DIR/bgrm /path/to/icon-raw.png /path/to/icon-masked.png
# then apply hybrid despill to icon-masked.png (single-image variant of the
# Python script in pipeline-mask-despill-webp.md)
```

### Step 3 — resize family

```python
from PIL import Image
src = Image.open("icon-1024.png").convert("RGBA")
for sz in (16, 32, 64, 128, 256, 512, 1024):
    src.resize((sz, sz), Image.LANCZOS).save(f"icon-{sz}.png")
```

### Step 4 — platform packaging (optional)

- **Windows `.ico`** — multi-size .ico is just an indexed container:
  ```python
  src.save("icon.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
  ```
- **macOS `.icns`** — needs `iconutil`:
  ```bash
  mkdir icon.iconset
  cp icon-16.png  icon.iconset/icon_16x16.png
  cp icon-32.png  icon.iconset/icon_16x16@2x.png
  cp icon-32.png  icon.iconset/icon_32x32.png
  cp icon-64.png  icon.iconset/icon_32x32@2x.png
  cp icon-128.png icon.iconset/icon_128x128.png
  cp icon-256.png icon.iconset/icon_128x128@2x.png
  cp icon-256.png icon.iconset/icon_256x256.png
  cp icon-512.png icon.iconset/icon_256x256@2x.png
  cp icon-512.png icon.iconset/icon_512x512.png
  cp icon-1024.png icon.iconset/icon_512x512@2x.png
  iconutil -c icns icon.iconset
  ```
- **Web** — ship the raw PNG set; let `<link rel="icon" sizes="...">` do the picking.

### Step 5 — lab.db + target inject

Same as animations: `lab.py inject $SLUG $NAME --target-project $TGT`. The
icon's `target_inject.webp_subdir` becomes its destination directory inside
the target project — adapt if the target wants a flat `assets/icons/<name>.ico`
rather than a per-icon subdirectory (open a target-engine adapter issue if
this needs a schema column).

## Cost expectation

- ~4 credits per Seedream 5.0 Lite image, 4 candidates per run = ~16 credits
- No video model spend
- No frame-count multiplier
