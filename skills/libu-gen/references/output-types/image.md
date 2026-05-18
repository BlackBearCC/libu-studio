# Output type — Static image

Single image: portrait card, splash screen, dialogue cut-in, achievement
banner. Not animated. May or may not need transparency.

## When this applies

- Single PNG / WebP / JPG
- Animation not required (use [animation.md](animation.md) if it is)
- Could be portrait / scene / item card / banner

## Pipeline

```
liblib image-refine | text-to-image | image-edit
   →  (optional) Vision mask + despill
   →  PIL convert / resize / format
   →  lab.db  →  target inject
```

The decision tree differs from animation pipeline at one point: **whether you
need transparency**.

| Need | Background | Pipeline |
|---|---|---|
| Cut-out portrait (overlay on UI) | green screen | mask + despill (single-image variant) |
| Full scene / illustration | natural | skip mask, ship as RGB |
| Stylized card (UI frame around art) | flat color or transparent corners | depends — usually mask only the character region |

## Production paths

Use one of:

| Path | Model class | When |
|---|---|---|
| **text-to-image** | Seedream / Qwen-Image / 智能图片V2 | Pure-prompt generation, no references |
| **image-refine** | Seedream 5.0 Lite / Qwen-Edit / 图片编辑模型 | Have a draft, want it tweaked |
| **image-edit (inpaint)** | 图片编辑模型 | Need local change (mouth, eyes, background) |

See [models.md](../models.md) for the full model table.

## Register in lab.db

Single-image generations use `frame_count=1`, `duration_s=0`, and one of the
existing `kind`s (today, `idle` is the catch-all for non-animated assets).
This may grow a dedicated kind later — open an issue if it gets confusing.

```bash
$LAB_PY new $SLUG $NAME --kind idle --status shipped
$LAB_PY gen $SLUG $NAME \
  --stage a-pre \
  --path image-refine \
  --model "Seedream 5.0 Lite" \
  --prompt-file /tmp/prompt.txt \
  --resolution 1024x1024 --aspect 1:1 \
  --frame-count 1 --duration-s 0 --no-audio \
  --credits 4 \
  --chosen
$LAB_PY target $SLUG $NAME --webp-subdir <subdir>
$LAB_PY inject $SLUG $NAME --target-project $TGT
```

## Candidate handling

Image generations typically produce **4 candidates** per click. Record all
four under one `generations` row so the prompt's hit-rate is preserved:

```bash
GEN=<id from above>
$LAB_PY cand $SLUG $NAME --gen $GEN --slot 1 --filename "<sha1>.png" --chosen
$LAB_PY cand $SLUG $NAME --gen $GEN --slot 2 --filename "<sha2>.png"
$LAB_PY cand $SLUG $NAME --gen $GEN --slot 3 --filename "<sha3>.png"
$LAB_PY cand $SLUG $NAME --gen $GEN --slot 4 --filename "<sha4>.png"
```

## Mask + despill for one image (instead of a frame sequence)

The Python in [pipeline-mask-despill-webp.md](../pipeline-mask-despill-webp.md)
loops over `/tmp/q-raw/*.png` — for a single image, change the glob:

```python
from PIL import Image
import numpy as np
raw = np.array(Image.open("portrait-raw.png").convert("RGB")).astype(np.int16)
# ... same chroma rescue + despill logic, but write one output file
```

Or just run `bgrm` once then apply the hybrid despill script with a single-file glob.
