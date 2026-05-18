# Output type — Video (mp4 direct)

Short or long-form video shipped as **mp4** straight from liblib, **no frame
extraction, no mask, no WebP sequence**. Use when the consumer wants a video
element (HTML5 `<video>`, Godot `VideoStreamPlayer`, Unity `VideoPlayer`, app
intro cut, marketing GIF source).

## When this applies vs animation

| Want | Output | Reference |
|---|---|---|
| Looping in-engine character idle / state animation | WebP frame sequence (alpha-keyed) | [animation.md](animation.md) |
| Plays once in a `<video>` element, optionally with audio | mp4 direct | this file |

Direct mp4 wins when:
- Background is **not** going to be keyed out (no green screen)
- Audio is welcome (Seedance 1.5 Pro syncs music/sfx)
- File is **large** (5+ seconds at 1080p) — frame sequence would blow asset
  budgets
- Target engine has a video element / texture (Godot, Unity, web)

## Pipeline

```
liblib text-to-video / action-mimic
   →  curl mp4 with Referer header
   →  (optional) trim / re-encode for size
   →  lab.db  →  target inject (copies mp4 instead of webp/)
```

No mask, no despill, no ffmpeg frame extraction.

## Step 1 — generate

Same as [path-a-alt-text-to-video.md](../path-a-alt-text-to-video.md) up to
the curl step. The three prompt iron rules still apply.

```bash
curl -sSL -H "Referer: https://www.liblib.art/" \
  -o ~/Downloads/<slug>-<name>.mp4 "<liblib mp4 URL>"
```

## Step 2 — (optional) trim / re-encode

If liblib outputs at 1080p but your target needs 720p / a different codec /
shorter clip:

```bash
FFMPEG=$(python3 -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
# trim to first 4 seconds, re-encode to H.264 baseline + AAC
"$FFMPEG" -y -i input.mp4 -t 4 -c:v libx264 -profile:v baseline -c:a aac out.mp4
```

> ⚠️ `imageio_ffmpeg`'s ffmpeg is `--disable-everything` stripped (webm/mjpeg
> only) — **it cannot transcode H.264**. For trim/re-encode, `brew install ffmpeg`
> first, or run the ops on a Linux box.

## Step 3 — register in lab.db

Video outputs reuse the existing schema, with these conventions:

- `target_inject.webp_subdir` repurposed as the relative directory inside the
  target project where the mp4 lands
- `generations.frame_count` = video's actual frame count (24 fps × duration)
  for reference; not consumed for inject
- `generations.audio` = 1 if Seedance synced music/sfx

```bash
$LAB_PY new $SLUG $NAME --kind state_triggered  # or idle, depending on usage
$LAB_PY gen $SLUG $NAME \
  --stage a-alt \
  --model "Seedance 1.5 Pro" \
  --prompt-file /tmp/prompt.txt \
  --source-url "https://images-wm.liblib.cloud/.../<sha>.mp4" \
  --resolution "1080p" --aspect "16:9" \
  --duration-s 5 --fps 24 --frame-count 121 --audio \
  --credits 20 \
  --chosen
$LAB_PY target $SLUG $NAME --webp-subdir <subdir>
```

## Step 4 — inject (copy mp4, not webp frames)

The current `lab.py inject` copies `<lab>/work/<slug>-anim/<name>/webp/*.webp`
to the target project. For mp4 outputs, **bypass `inject` and copy directly
for now** (this is a known gap — open an issue for a `--output-type video`
flag on inject):

```bash
LAB=<lab-root>
TGT=<target-project>
INJECT_DIR=$(sqlite3 $LAB/lab.db "SELECT inject_target_dir FROM characters WHERE slug='$SLUG';")
WEBP_SUBDIR=$(sqlite3 $LAB/lab.db "SELECT webp_subdir FROM target_inject t JOIN anim_tasks a ON t.task_id=a.id WHERE a.character_slug='$SLUG' AND a.name='$NAME';")
mkdir -p "$TGT/$INJECT_DIR/$WEBP_SUBDIR"
cp ~/Downloads/<slug>-$NAME.mp4 "$TGT/$INJECT_DIR/$WEBP_SUBDIR/$NAME.mp4"
$LAB_PY inject $SLUG  # no $NAME arg — only re-exports manifest.json, skips webp copy
```

## Cost expectation

- Seedance 1.5 Pro: ~20 credits per 5-second clip
- Seedance 2.0 Fast VIP / 可灵 3.0: 30-80 credits depending on resolution
- Action-mimic: per-platform pricing visible at UI bottom
