# 阶段 D — 资产归档 + 压缩 + 入 lab.db

## D.1 双轨存放：lab 留原片 / 项目用压缩版

`<lab-root>` 指本地 clone 的 libu-studio 根，`<target-project>` 指 character 消费方仓库根。

- **`<lab-root>/work/<slug>-anim/<name>/`**：完整母本档案，不压缩，方便回溯/重生成
  - `<name>.mp4` — liblib 下载的原始 mp4
  - `raw/*.png` — ffmpeg 抽出来的 121 帧原始 PNG (RGB, 含绿幕)
  - `masked/*.png` — bgrm Vision 抠图后 PNG (RGBA, 边缘有绿溢色)
  - `despilled/*.png` — hybrid despill 之后 PNG (RGBA, 干净, 原分辨率 ~828×1108)
  - `webp/*.webp` — **原分辨率 q90 的 WebP** (=镜像 despilled, 但 WebP 容器)
- **`<inject_target_dir>/<name>/`**（从 lab.db characters 表查）：项目实际加载的 WebP 帧序列
  - **每个动画文件夹必须 ≤ 5 MB**
  - 默认走 **0.5× 降采样 + WebP q90 preset drawing**（414×554, 121 帧, ~3-5 MB）
  - 视觉对比: 3 倍放大才看出边缘抗锯齿差异, runtime 显示尺寸下肉眼无差
  - GPU 显存占用减半, 是双赢

## D.2 压缩流水线（接在阶段 B 后面跑）

```bash
PY=/usr/local/bin/python3.12
FFMPEG=$($PY -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
SCALE=0.5  # 调这里可调到 0.66 / 0.75 等; 5MB 不够时降 SCALE
Q=90

SLUG=<your-slug>     # e.g. poka-v4
ANIM=<name>
LAB_ROOT=<lab-root>          # local clone of libu-studio
TARGET_PROJECT=<target-project>  # local clone of the character's consuming project
LAB=$LAB_ROOT/work/$SLUG-anim/$ANIM
TGT_REL=$(sqlite3 $LAB_ROOT/lab.db \
  "SELECT inject_target_dir FROM characters WHERE slug='$SLUG';")
OUT=$TARGET_PROJECT/$TGT_REL$ANIM

# 1. lab/webp/ 用原分辨率 q90 (lab 母本)
rm -f $LAB/webp/*.webp
cd $LAB/despilled
for i in $(seq 1 $(ls *.png | wc -l | tr -d ' ')); do
  "$FFMPEG" -y -i "$(printf "%04d.png" $i)" -c:v libwebp -quality $Q -preset drawing \
    "$LAB/webp/$(printf "%04d.webp" $((i-1)))" 2>/dev/null
done

# 2. 项目 OUT 走 0.5× 降采样
RESIZED=/tmp/rs_$ANIM
rm -rf $RESIZED && mkdir -p $RESIZED
$PY - <<PY
from PIL import Image
import glob, os
for f in sorted(glob.glob("$LAB/despilled/*.png")):
    im = Image.open(f).convert("RGBA")
    nw, nh = int(im.width * $SCALE), int(im.height * $SCALE)
    im.resize((nw, nh), Image.LANCZOS).save(f"$RESIZED/" + os.path.basename(f))
PY
mkdir -p $OUT
rm -f $OUT/*.webp
cd $RESIZED
for i in $(seq 1 $(ls *.png | wc -l | tr -d ' ')); do
  "$FFMPEG" -y -i "$(printf "%04d.png" $i)" -c:v libwebp -quality $Q -preset drawing \
    "$OUT/$(printf "%04d.webp" $((i-1)))" 2>/dev/null
done
du -sh $OUT  # 验证 ≤ 5MB
```

如果 5MB 不够（动画细节多/121 帧太重），按这个顺序调：

1. SCALE 0.5 → 0.66 → 0.75（每多 0.16, 体积大约 ×1.5）
2. Q 90 → 80 → 70（每降 10, 体积大约 -15%）
3. 极端情况降 FPS 24→12（**注意**: 改了要同步改 `_anim_config[<name>].fps`）

## D.3 落 lab.db（替代手抄 manifest.json）

> 当前未做完 `lab.py` CLI 前，临时用 sqlite3 直接 INSERT；Step 3 完成后切到 `lab.py gen/choose/inject`。

```bash
DB=<lab-root>/lab.db
SLUG=<your-slug>     # e.g. poka-v4
NAME=<name>
KIND=idle  # idle / state_triggered / attribute_biased_idle / attribute_transition

# 1. anim_tasks 行
sqlite3 "$DB" "INSERT INTO anim_tasks
  (name, character_slug, kind, status, created_at, lab_master_dir, paired_with, trigger_expr, path_summary, notes)
  VALUES ('$NAME', '$SLUG', '$KIND', 'shipped', date('now'),
          'work/$SLUG-anim/$NAME/', NULL, NULL, NULL, NULL);"

# 2. attribute_meta 行（仅 attribute_biased_idle / attribute_transition）
# sqlite3 "$DB" "INSERT INTO attribute_meta (task_id, attribute, level, ...) VALUES (...);"

# 3. main generation 行（chosen=1）
sqlite3 "$DB" "INSERT INTO generations
  (task_id, stage, model, prompt, ref_first, ref_last,
   source_url, resolution, aspect, duration_s, fps, frame_count, audio,
   credits_spent, credits_note, status, chosen, ran_at)
  VALUES ((SELECT id FROM anim_tasks WHERE name='$NAME' AND character_slug='$SLUG'),
          'a-alt', '<model>', '<prompt>', '<ref_first>', '<ref_last>',
          '<source_url>', '414x554', '3:4', 5, 24, 121, 0,
          <credits>, '<credits_note>', 'success', 1, date('now'));"

# 4. target_inject
sqlite3 "$DB" "INSERT INTO target_inject (task_id, anim_name, webp_subdir)
  VALUES ((SELECT id FROM anim_tasks WHERE name='$NAME' AND character_slug='$SLUG'),
          '$NAME', '$NAME');"

# 5. (A.pre 走过的话) 加 a-pre generation + candidates 表
# 详见 character 的 idle_starving 历史记录 SELECT * FROM generations WHERE stage='a-pre';

# 6. 重新生成主仓 manifest.json
TGT_REL=$(sqlite3 "$DB" "SELECT inject_target_dir FROM characters WHERE slug='$SLUG';")
python3 <lab-root>/scripts/export-manifest.py \
  "$DB" $SLUG --out <target-project>/${TGT_REL}manifest.json

# 7. 校验 round-trip 零差异（可选）
python3 <lab-root>/scripts/verify-roundtrip.py \
  <target-project>/${TGT_REL}manifest.json /tmp/check.json  # 视情况
```

**必填字段（不允许缩写或省略）**：`prompt` / `source_url` / `ref_first`（或 `ref_single`）/ `credits_spent` —— manifest 是这条动画唯一的"完整 reproducible 档案"。

**关键参考图**（A.pre 洗出来的、用户从 4 张候选挑定的那张）必须留两份：
- `~/Downloads/<slug>-<anim>-ref.png` — 工作副本，方便后续重传到 liblib 图库
- `<lab-root>/work/<slug>-anim/<anim>/ref_*.png` — 永久 lab 副本

不仅"图标图片"（指 A.pre 洗的姿态参考图）要存, 视频生成的 mp4 也要存到 `lab/<name>.mp4`（不能只指望 liblib CDN URL —— images-wm.liblib.cloud 是带 30 天-1年 不等的 TTL，老了会 404）。

## D.4 commit checklist

**target 项目侧**（character 消费方仓库；以 Godot 项目布局为例）：
```bash
cd <target-project>
git add <inject_target_dir><name>/                # 压缩 WebP
git add <inject_target_dir>manifest.json          # 由 export-manifest.py 重生成
git add <path-to>/character_controller.gd         # _anim_config + 钩子
git add <path-to>/attribute_anim_director.gd      # (新功能时)
git add <path-to>/main.gd                         # wiring
```

**lab 仓侧**（libu-studio 本地 clone；多数文件被 `.gitignore` 排除，按需 commit 元数据）：
```bash
cd <lab-root>
# work/ 默认被 .gitignore 排除（mp4/png/webp/中间帧不入开源仓），如有需要 PR 公开样例可单独豁免
git add skills/libu-gen/references/characters/<your-slug>.md   # 角色档案
# lab.db / lab.dump.sql 也被 .gitignore 排除，由 contributor 本地保留
```
