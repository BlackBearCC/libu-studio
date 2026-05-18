#!/usr/bin/env python3
"""Example migrator: hand-written manifest.json → fresh lab.db.

> ⚠️ **This script encodes ONE specific historical migration** (a poka-v4
> consuming-project layout under apps/godot-pet/...). Hard-coded paths and
> candidate file names below were copied from a particular project's prompts
> log. **Do NOT run this against your own project unmodified** — read it as a
> template and adapt:
>
>   1. Change the `manifest_path` construction to your project's layout
>   2. Change the inserted `characters` row (slug / inject_target_dir / etc.)
>   3. Remove or rewrite the special-cased a-pre image-refine generation
>      block at the bottom (it embeds prompts and candidate SHAs literal)
>
> A future revision may turn this into a parameterized importer; for now
> treat it as a worked example of how to walk a manifest.json into the schema.

Usage:
  python3 migrate-from-existing.py <project-root> <lab-root> [--out lab.db]

Writes:
  <lab-root>/lab.db  (or --out path)

The script is destructive: it drops and recreates all tables.
"""
import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent / "schema.sql"


def b2i(v):
    if v is None:
        return None
    return 1 if v else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root", help="path to the character's consuming project")
    ap.add_argument("lab_root", help="path to libu-studio repo")
    ap.add_argument("--out", default=None, help="output lab.db path (default <lab>/lab.db)")
    args = ap.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    lab_root = Path(args.lab_root).expanduser().resolve()
    out = Path(args.out).expanduser().resolve() if args.out else (lab_root / "lab.db")

    # NOTE: layout is hard-coded for this example migration. Adapt for your project.
    manifest_path = (
        project_root
        / "apps/godot-pet/assets/character-design/poka-v4/anim/manifest.json"
    )
    if not manifest_path.exists():
        sys.exit(f"manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if out.exists():
        out.unlink()

    conn = sqlite3.connect(out)
    conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
    cur = conn.cursor()

    # ---- characters ----
    cur.execute(
        """INSERT INTO characters
           (slug, display_name, inject_target_dir, reference_doc,
            manifest_version, default_frame_format, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            manifest["character"],
            "poka-v4",
            "apps/godot-pet/assets/character-design/poka-v4/anim/",
            "references/characters/poka-v4.md",
            manifest.get("version", 1),
            manifest.get("format"),
            None,
        ),
    )

    now = dt.date.today().isoformat()

    for anim in manifest["animations"]:
        name = anim["name"]
        kind = anim.get("kind", "idle")
        created_at = anim.get("created_at")
        lab_master = anim.get("lab_master")
        # strip the historical "petclaw-lab/" prefix if present so it's relative
        # to the lab root; adapt to whatever prefix your source manifest uses.
        if lab_master and lab_master.startswith("petclaw-lab/"):
            lab_master = lab_master[len("petclaw-lab/"):]

        cur.execute(
            """INSERT INTO anim_tasks
               (name, character_slug, kind, status, created_at, updated_at,
                lab_master_dir, paired_with, trigger_expr, path_summary, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                manifest["character"],
                kind,
                "shipped",
                created_at,
                now,
                lab_master,
                anim.get("paired_with"),
                anim.get("trigger"),
                anim.get("path"),
                anim.get("notes"),
            ),
        )
        task_id = cur.lastrowid

        # attribute_meta for attribute_biased_idle / attribute_transition
        if kind in ("attribute_biased_idle", "attribute_transition"):
            cur.execute(
                """INSERT INTO attribute_meta
                   (task_id, attribute, level, from_level, to_level, bias_weight, loops)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    anim.get("attribute"),
                    anim.get("level"),
                    anim.get("from_level"),
                    anim.get("to_level"),
                    anim.get("bias_weight"),
                    b2i(anim.get("loops")) if "loops" in anim else None,
                ),
            )

        # target_inject (anim_name defaults to task name; subdir convention matches)
        cur.execute(
            """INSERT INTO target_inject
               (task_id, anim_name, webp_subdir, inject_notes)
               VALUES (?, ?, ?, ?)""",
            (task_id, name, name, None),
        )

        # main generation (the video that shipped) — chosen=1
        cur.execute(
            """INSERT INTO generations
               (task_id, stage, model, path, prompt,
                ref_single, ref_first, ref_last,
                tail_frame_note, tail_frame_lock_note,
                head_frame_lock_note, tail_locked_note,
                source_url, resolution, aspect,
                duration_s, fps, frame_count, audio,
                credits_spent, credits_note, queue_time_min,
                status, chosen, ran_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                infer_stage(anim),
                anim.get("model"),
                # main video generation's pipeline path. For idle_starving,
                # manifest.path is the composite summary, not this leg's path.
                # Set null here; the composite goes in anim_tasks.path_summary.
                None,
                anim.get("prompt"),
                anim.get("reference_image"),
                anim.get("reference_image_first"),
                anim.get("reference_image_last"),
                anim.get("tail_frame"),
                anim.get("tail_frame_lock"),
                anim.get("head_frame_lock"),
                anim.get("tail_locked"),
                anim.get("source_video_url"),
                anim.get("resolution"),
                anim.get("aspect"),
                anim.get("duration_s"),
                anim.get("fps"),
                anim.get("frame_count"),
                b2i(anim.get("audio")) if "audio" in anim else None,
                anim.get("credits_spent"),
                anim.get("credits_note"),
                anim.get("queue_time_min"),
                "success",
                1,
                created_at,
                None,
            ),
        )

    # ---- idle_starving's a-pre image-refine generation (from _prompts_log.md task 1) ----
    cur.execute("SELECT id FROM anim_tasks WHERE name = ?", ("idle_starving",))
    row = cur.fetchone()
    if row:
        idle_starving_id = row[0]
        cur.execute(
            """INSERT INTO generations
               (task_id, stage, model, path, prompt,
                ref_single,
                aspect,
                credits_spent, credits_note,
                status, chosen, ran_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                idle_starving_id,
                "a-pre",
                "Seedream 5.0 Lite",
                "image-refine",
                "保持角色和构图不变，把姿势改为坐在地上："
                "双腿向前自然伸出，上半身懒洋洋地前倾，"
                "双手垂在膝盖或地上，半眯眼漫不经心没什么表情。纯绿色背景不变。",
                "liblib 账户图库 id 019c385a1a3a5e3a (人物大小居中绿幕站立)",
                "3:4",
                16,
                "5820 → 5804",
                "success",
                0,
                "2026-05-18",
                "图生图洗瘫坐参考图。4 张候选，用户选 cand_1。",
            ),
        )
        gen_id = cur.lastrowid
        candidates = [
            (1, "b57ae794ea0c267830319b6eda6c02cdf66fdf0e631b0516743456ed55c5648d.png", 1,
             "用户选定 (人物居中懒洋洋坐姿)。落到 work/poka-anim/idle_starving/ref_seated.png"),
            (2, "73667636583ae5f1002bf146c18783e6bc0d9f9893640902cb562fcb1f68d8f2.png", 0, None),
            (3, "687a33c6e9342260922490093c2a1b4dc5d5ad1e15ad66a1609c4de183628bc1.png", 0, None),
            (4, "5cb04e34e3f568237a06449011c778b064b6fb28de99bb4ed5cd2f4ba67c6791.png", 0, None),
        ]
        cur.executemany(
            """INSERT INTO candidates (generation_id, slot, filename, chosen, notes)
               VALUES (?, ?, ?, ?, ?)""",
            [(gen_id, slot, fn, chosen, notes) for (slot, fn, chosen, notes) in candidates],
        )

    conn.commit()

    # quick sanity print
    print(f"OK  → {out}")
    for tbl in (
        "characters", "anim_tasks", "attribute_meta",
        "generations", "candidates", "target_inject",
    ):
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:18s} {n}")
    conn.close()


def infer_stage(anim):
    """Map manifest anim → main generation stage tag.

    Rules:
      - explicit anim['path'] containing 'action-mimic' → 'a'
      - 'text-to-video' (or absent path with a video model) → 'a-alt'
      - 'image-refine' only → 'a-pre' (no shipped anim case today)
    """
    p = (anim.get("path") or "").lower()
    if "action-mimic" in p or "action_mimic" in p:
        return "a"
    if "text-to-video" in p or "text_to_video" in p or not p:
        return "a-alt"
    if "image-refine" in p or "image_refine" in p:
        return "a-pre"
    return "a-alt"


if __name__ == "__main__":
    main()
