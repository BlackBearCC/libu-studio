# Output type — Animation (WebP frame sequence)

The default and most-developed output type. Alpha-keyed WebP frames for
in-engine playback. This is the form the original SKILL.md was built around.

## When this applies

- In-engine character animation (idle / state-triggered / attribute-driven)
- Requires transparency (alpha background)
- Plays via a sprite-sheet or frame-by-frame renderer (Godot
  `AnimatedSprite2D`, Unity SpriteRenderer w/ flipbook, web `<canvas>`)
- Typical scope: 5 seconds @ 24 fps = 121 frames

## Pipeline

This is the full path described across SKILL.md and the path-a-*.md / pipeline
references. Quick map:

| Stage | Reference |
|---|---|
| 1. Pick production path | SKILL.md "三条路径决策" |
| 2.a Image-refine reference image (optional) | [path-a-pre-image-refine.md](../path-a-pre-image-refine.md) |
| 2.b Action-mimic from a demo video | [path-a-action-mimic.md](../path-a-action-mimic.md) |
| 2.c Text-to-video from prompt | [path-a-alt-text-to-video.md](../path-a-alt-text-to-video.md) |
| 3. Vision mask + chroma rescue + despill + WebP encode | [pipeline-mask-despill-webp.md](../pipeline-mask-despill-webp.md) |
| 4. Target inject (Godot today) | [target-inject-godot.md](../target-inject-godot.md) |
| 5. Archive + compress + lab.db | [archive-compress.md](../archive-compress.md) |

## State-triggered subtype

Enter / loop / exit pairs (panel open → close, status change) have extra
constraints — see [state-triggered.md](../state-triggered.md).

## Attribute-driven subtype

Animations whose probability or transition is driven by character attributes
(hunger, mood) live under `kind = attribute_biased_idle` or
`attribute_transition` — same WebP pipeline, plus the `attribute_meta` row.

## Cost expectation

- Per shipped animation: typically **20 credits** (Seedance 1.5 Pro), can run
  to **30-80** for 可灵 3.0 / Seedance 2.0 VIP
- A.pre image-refine adds **~16 credits** if you wash a reference first
- New 可灵 3.0 accounts get 4 free runs

## Why this is the "main" output type

The animation pipeline catches almost every edge case that simpler outputs
ignore: scenes that need transparency, alpha-band hair, green-spill removal,
sub-frame transitions, attribute-driven probability mixing. Most production
paths and references were built for this output; icons / static images / mp4
are simpler subsets.
