#!/usr/bin/env python3
"""Export lab.db → target manifest.json for a given character.

Usage:
  python3 export-manifest.py <lab-db> <character-slug> [--out PATH]
                             [--print]    # write to stdout instead of file
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path


# Canonical key order for top-level + each animation entry, matching how the
# manifest.json is hand-written today. Keys not in the order list are appended
# at the end (rare).
TOP_ORDER = ["version", "character", "format", "animations"]
ANIM_ORDER = [
    "name", "kind",
    "attribute", "level", "from_level", "to_level", "bias_weight", "loops",
    "trigger", "paired_with",
    "created_at",
    "model", "path",
    "duration_s", "fps", "frame_count", "resolution", "aspect", "audio",
    "reference_image", "reference_image_first", "reference_image_last",
    "tail_frame", "tail_frame_lock", "head_frame_lock", "tail_locked",
    "prompt",
    "source_video_url",
    "lab_master",
    "credits_spent", "credits_note", "queue_time_min",
    "notes",
]


def order_dict(d, order):
    out = {}
    for k in order:
        if k in d:
            out[k] = d[k]
    for k in d:
        if k not in out:
            out[k] = d[k]
    return out


def i2b(v):
    if v is None:
        return None
    return bool(v)


def set_if(d, key, value):
    """Set d[key]=value only when value is not None."""
    if value is not None:
        d[key] = value


def set_numeric(d, key, value):
    """sqlite REAL columns yield float; collapse to int when value is integral
    so the exported JSON matches a hand-written manifest that used ints."""
    if value is None:
        return
    if isinstance(value, float) and value.is_integer():
        d[key] = int(value)
    else:
        d[key] = value


def build_manifest(conn, slug):
    cur = conn.cursor()
    char = cur.execute(
        """SELECT slug, manifest_version, default_frame_format, inject_target_dir
           FROM characters WHERE slug = ?""",
        (slug,),
    ).fetchone()
    if not char:
        sys.exit(f"character {slug} not found in db")
    _, version, frame_format, _ = char

    manifest = {
        "version": version,
        "character": slug,
        "format": frame_format,
        "animations": [],
    }

    tasks = cur.execute(
        """SELECT id, name, kind, created_at, lab_master_dir,
                  paired_with, trigger_expr, path_summary, notes
           FROM anim_tasks
           WHERE character_slug = ?
           ORDER BY id""",
        (slug,),
    ).fetchall()

    for (task_id, name, kind, created_at, lab_master,
         paired_with, trigger_expr, path_summary, t_notes) in tasks:
        anim = {"name": name}
        # kind only when not default 'idle' (sky_gaze had no kind in original)
        if kind and kind != "idle":
            anim["kind"] = kind

        # attribute_meta
        attr = cur.execute(
            """SELECT attribute, level, from_level, to_level, bias_weight, loops
               FROM attribute_meta WHERE task_id = ?""",
            (task_id,),
        ).fetchone()
        if attr:
            attribute, level, from_level, to_level, bias_weight, loops = attr
            set_if(anim, "attribute", attribute)
            set_if(anim, "level", level)
            set_if(anim, "from_level", from_level)
            set_if(anim, "to_level", to_level)
            set_if(anim, "bias_weight", bias_weight)
            if loops is not None:
                anim["loops"] = bool(loops)

        set_if(anim, "trigger", trigger_expr)
        set_if(anim, "paired_with", paired_with)

        set_if(anim, "created_at", created_at)

        # shipped generation (chosen=1)
        gen = cur.execute(
            """SELECT model, path, prompt,
                      ref_single, ref_first, ref_last,
                      tail_frame_note, tail_frame_lock_note,
                      head_frame_lock_note, tail_locked_note,
                      source_url, resolution, aspect,
                      duration_s, fps, frame_count, audio,
                      credits_spent, credits_note, queue_time_min
               FROM generations
               WHERE task_id = ? AND chosen = 1
               LIMIT 1""",
            (task_id,),
        ).fetchone()
        if gen:
            (model, gpath, prompt,
             ref_single, ref_first, ref_last,
             tail_frame_note, tail_frame_lock_note,
             head_frame_lock_note, tail_locked_note,
             source_url, resolution, aspect,
             duration_s, fps, frame_count, audio,
             credits_spent, credits_note, queue_time_min) = gen
            set_if(anim, "model", model)
            # path is the task-level summary, not the per-generation path
            set_if(anim, "path", path_summary)
            set_numeric(anim, "duration_s", duration_s)
            set_if(anim, "fps", fps)
            set_if(anim, "frame_count", frame_count)
            set_if(anim, "resolution", resolution)
            set_if(anim, "aspect", aspect)
            if audio is not None:
                anim["audio"] = bool(audio)
            set_if(anim, "reference_image", ref_single)
            set_if(anim, "reference_image_first", ref_first)
            set_if(anim, "reference_image_last", ref_last)
            set_if(anim, "tail_frame", tail_frame_note)
            set_if(anim, "tail_frame_lock", tail_frame_lock_note)
            set_if(anim, "head_frame_lock", head_frame_lock_note)
            set_if(anim, "tail_locked", tail_locked_note)
            set_if(anim, "prompt", prompt)
            set_if(anim, "source_video_url", source_url)
            set_numeric(anim, "credits_spent", credits_spent)
            set_if(anim, "credits_note", credits_note)
            set_numeric(anim, "queue_time_min", queue_time_min)

        # lab_master path stays relative to <lab-root>; consumers can prepend their
        # local clone path if needed.
        if lab_master:
            anim["lab_master"] = lab_master

        set_if(anim, "notes", t_notes)

        manifest["animations"].append(order_dict(anim, ANIM_ORDER))

    return order_dict(manifest, TOP_ORDER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("slug")
    ap.add_argument("--out", default=None)
    ap.add_argument("--print", action="store_true", help="write to stdout")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    manifest = build_manifest(conn, args.slug)
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

    if args.print or not args.out:
        sys.stdout.write(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
