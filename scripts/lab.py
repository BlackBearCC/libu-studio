#!/usr/bin/env python3
"""lab.py — single-binary CLI for managing lab.db (libu-studio metadata).

Replaces hand-rolled `sqlite3 'INSERT INTO ...'` snippets in SKILL.md stage D
with declarative subcommands. Every write is a small, idempotent operation,
and `lab.py inject` re-exports the consuming project's manifest.json so the
sqlite DB stays the single source of truth.

Usage:
    lab.py [--db PATH] <subcommand> [args]

Run `lab.py <subcommand> --help` for per-command flags.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DB = Path.cwd() / "lab.db"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def open_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        sys.exit(
            f"lab.db not found at {path}\n"
            f"Initialize with: sqlite3 {path} < {SCRIPT_DIR}/schema.sql"
        )
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_task_id(conn: sqlite3.Connection, slug: str, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM anim_tasks WHERE character_slug = ? AND name = ?",
        (slug, name),
    ).fetchone()
    if row is None:
        sys.exit(f"no anim_task: slug={slug!r} name={name!r}  (try `lab.py new` first)")
    return row[0]


def require_character(conn: sqlite3.Connection, slug: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM characters WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        sys.exit(
            f"character {slug!r} not registered. INSERT a row into characters first."
        )


def load_text(value: str | None, path: str | None) -> str | None:
    """Choose between a literal --foo or a file at --foo-file."""
    if path:
        return Path(path).expanduser().read_text(encoding="utf-8")
    return value


def tristate(v: bool | None) -> int | None:
    """argparse BooleanOptionalAction → SQLite 0/1/NULL.

    None (flag not given) → NULL, True → 1, False → 0.
    """
    if v is None:
        return None
    return 1 if v else 0


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_new(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    require_character(conn, args.slug)

    existing = conn.execute(
        "SELECT id FROM anim_tasks WHERE character_slug = ? AND name = ?",
        (args.slug, args.name),
    ).fetchone()
    if existing:
        sys.exit(f"anim_task already exists: slug={args.slug} name={args.name} id={existing[0]}")

    conn.execute(
        """INSERT INTO anim_tasks
           (name, character_slug, kind, status, created_at, lab_master_dir,
            paired_with, trigger_expr, path_summary, notes)
           VALUES (?, ?, ?, ?, COALESCE(?, date('now')), ?, ?, ?, ?, ?)""",
        (
            args.name,
            args.slug,
            args.kind,
            args.status,
            args.created_at,
            args.lab_master_dir,
            args.paired_with,
            args.trigger,
            args.path_summary,
            args.notes,
        ),
    )
    task_id = conn.execute(
        "SELECT id FROM anim_tasks WHERE character_slug = ? AND name = ?",
        (args.slug, args.name),
    ).fetchone()[0]
    conn.commit()
    print(f"created anim_task id={task_id} slug={args.slug} name={args.name}")


def cmd_gen(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)

    prompt = load_text(args.prompt, args.prompt_file)

    if args.chosen:
        # uncheck other chosen generations on the same task
        conn.execute(
            "UPDATE generations SET chosen = 0 WHERE task_id = ? AND chosen = 1",
            (task_id,),
        )

    conn.execute(
        """INSERT INTO generations
           (task_id, stage, model, path, prompt,
            ref_single, ref_first, ref_last,
            tail_frame_note, tail_frame_lock_note,
            head_frame_lock_note, tail_locked_note,
            source_url, resolution, aspect,
            duration_s, fps, frame_count, audio,
            credits_spent, credits_note, queue_time_min,
            status, chosen, ran_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, ?, ?,
                   ?, ?, ?, ?, ?, COALESCE(?, date('now')), ?)""",
        (
            task_id,
            args.stage,
            args.model,
            args.path,
            prompt,
            args.ref_single,
            args.ref_first,
            args.ref_last,
            args.tail_frame_note,
            args.tail_frame_lock_note,
            args.head_frame_lock_note,
            args.tail_locked_note,
            args.source_url,
            args.resolution,
            args.aspect,
            args.duration_s,
            args.fps,
            args.frame_count,
            tristate(args.audio),
            args.credits,
            args.credits_note,
            args.queue_time_min,
            args.status,
            1 if args.chosen else 0,
            args.ran_at,
            args.notes,
        ),
    )
    gen_id = conn.execute(
        "SELECT MAX(id) FROM generations WHERE task_id = ?", (task_id,)
    ).fetchone()[0]
    conn.commit()
    print(f"created generation id={gen_id} task_id={task_id} stage={args.stage} chosen={int(args.chosen)}")


def cmd_cand(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)
    # sanity: generation belongs to task
    row = conn.execute(
        "SELECT id FROM generations WHERE id = ? AND task_id = ?",
        (args.gen, task_id),
    ).fetchone()
    if row is None:
        sys.exit(f"generation {args.gen} doesn't belong to task {args.slug}/{args.name}")

    if args.chosen:
        conn.execute(
            "UPDATE candidates SET chosen = 0 WHERE generation_id = ? AND chosen = 1",
            (args.gen,),
        )

    conn.execute(
        """INSERT INTO candidates (generation_id, slot, filename, chosen, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (
            args.gen,
            args.slot,
            args.filename,
            1 if args.chosen else 0,
            args.notes,
        ),
    )
    conn.commit()
    print(f"added candidate slot={args.slot} to generation {args.gen}")


def cmd_choose(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)

    if args.gen is not None:
        # validate generation belongs to task
        row = conn.execute(
            "SELECT id FROM generations WHERE id = ? AND task_id = ?",
            (args.gen, task_id),
        ).fetchone()
        if row is None:
            sys.exit(f"generation {args.gen} doesn't belong to task {args.slug}/{args.name}")
        conn.execute("UPDATE generations SET chosen = 0 WHERE task_id = ?", (task_id,))
        conn.execute("UPDATE generations SET chosen = 1 WHERE id = ?", (args.gen,))
        print(f"chose generation {args.gen} for task {args.slug}/{args.name}")

    if args.cand is not None:
        # cand requires a generation context
        if args.gen is None:
            sys.exit("--cand requires --gen to disambiguate which generation's candidate to choose")
        conn.execute(
            "UPDATE candidates SET chosen = 0 WHERE generation_id = ?",
            (args.gen,),
        )
        result = conn.execute(
            "UPDATE candidates SET chosen = 1 WHERE generation_id = ? AND slot = ?",
            (args.gen, args.cand),
        )
        if result.rowcount == 0:
            sys.exit(f"no candidate slot={args.cand} on generation {args.gen}")
        print(f"chose candidate slot={args.cand} on generation {args.gen}")

    conn.commit()


def cmd_attribute(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)
    conn.execute(
        """INSERT INTO attribute_meta
           (task_id, attribute, level, from_level, to_level, bias_weight, loops)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(task_id) DO UPDATE SET
             attribute=excluded.attribute,
             level=excluded.level,
             from_level=excluded.from_level,
             to_level=excluded.to_level,
             bias_weight=excluded.bias_weight,
             loops=excluded.loops""",
        (
            task_id,
            args.attribute,
            args.level,
            args.from_level,
            args.to_level,
            args.bias_weight,
            tristate(args.loops),
        ),
    )
    conn.commit()
    print(f"upserted attribute_meta for task {args.slug}/{args.name}")


def cmd_target(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)
    conn.execute(
        """INSERT INTO target_inject
           (task_id, anim_name, webp_subdir, inject_notes)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(task_id) DO UPDATE SET
             anim_name=COALESCE(excluded.anim_name, target_inject.anim_name),
             webp_subdir=COALESCE(excluded.webp_subdir, target_inject.webp_subdir),
             inject_notes=COALESCE(excluded.inject_notes, target_inject.inject_notes)""",
        (
            task_id,
            args.anim_name or args.name,
            args.webp_subdir or args.name,
            args.notes,
        ),
    )
    conn.commit()
    print(f"upserted target_inject for task {args.slug}/{args.name}")


def cmd_inject(args: argparse.Namespace) -> None:
    """Re-export manifest.json + optionally rsync webp into target project."""
    conn = open_db(args.db)
    require_character(conn, args.slug)

    inject_target_dir = conn.execute(
        "SELECT inject_target_dir FROM characters WHERE slug = ?",
        (args.slug,),
    ).fetchone()[0]

    if not args.target_project:
        sys.exit(
            "missing --target-project <path>. lab.py stays generic about where "
            "the consuming project lives; pass its root via flag or LIBU_TARGET_PROJECT env."
        )
    target_root = Path(args.target_project).expanduser().resolve()
    if not target_root.is_dir():
        sys.exit(f"--target-project {target_root} is not a directory")

    manifest_path = target_root / inject_target_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Build manifest via export-manifest.py (loaded as a module)
    spec = importlib.util.spec_from_file_location(
        "export_manifest", SCRIPT_DIR / "export-manifest.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    manifest = mod.build_manifest(conn, args.slug)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {manifest_path}")

    # Optional: rsync webp directory for the named task only
    if args.name:
        task_id = get_task_id(conn, args.slug, args.name)
        ti = conn.execute(
            "SELECT webp_subdir FROM target_inject WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if ti is None:
            sys.exit(f"no target_inject row for task {args.slug}/{args.name}")
        webp_subdir = ti[0] or args.name

        lab_root = (args.lab_root or args.db.parent).resolve()
        src = lab_root / "work" / f"{args.slug}-anim" / args.name / "webp"
        dst = target_root / inject_target_dir / webp_subdir
        if not src.is_dir():
            sys.exit(f"lab webp dir missing: {src}")

        dst.mkdir(parents=True, exist_ok=True)
        # plain shutil copy — predictable, no rsync dependency
        for webp in sorted(src.glob("*.webp")):
            shutil.copy2(webp, dst / webp.name)
        n = len(list(dst.glob("*.webp")))
        print(f"copied {n} webp frames → {dst}")


def cmd_status(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    q = """
        SELECT t.character_slug, t.name, t.kind, t.status, t.created_at,
               g.id AS gen_id, g.model, g.credits_spent
        FROM anim_tasks t
        LEFT JOIN generations g ON g.task_id = t.id AND g.chosen = 1
        WHERE 1=1
    """
    params: list[Any] = []
    if args.slug:
        q += " AND t.character_slug = ?"
        params.append(args.slug)
    if args.kind:
        q += " AND t.kind = ?"
        params.append(args.kind)
    q += " ORDER BY t.character_slug, t.id"

    rows = conn.execute(q, params).fetchall()
    if not rows:
        print("(no matching anim_tasks)")
        return
    print(f"{'slug':<18} {'name':<32} {'kind':<22} {'status':<10} {'created':<12} {'gen':<5} {'credits':<8} model")
    print("-" * 130)
    for slug, name, kind, status, created, gen_id, model, credits in rows:
        print(
            f"{slug:<18} {name:<32} {kind:<22} {status:<10} {created or '':<12} "
            f"{str(gen_id or '-'):<5} {str(credits or '-'):<8} {model or ''}"
        )


def cmd_show(args: argparse.Namespace) -> None:
    conn = open_db(args.db)
    task_id = get_task_id(conn, args.slug, args.name)

    task = conn.execute(
        "SELECT * FROM anim_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    cols = [d[0] for d in conn.execute("SELECT * FROM anim_tasks WHERE id = ?", (task_id,)).description]
    print("=== anim_task ===")
    for k, v in zip(cols, task, strict=True):
        if v is not None:
            print(f"  {k}: {v}")

    am = conn.execute(
        "SELECT attribute, level, from_level, to_level, bias_weight, loops FROM attribute_meta WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if am:
        print("=== attribute_meta ===")
        print(f"  attribute={am[0]} level={am[1]} from={am[2]} to={am[3]} bias={am[4]} loops={am[5]}")

    ti = conn.execute(
        "SELECT anim_name, webp_subdir, inject_notes FROM target_inject WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if ti:
        print("=== target_inject ===")
        print(f"  anim_name={ti[0]} webp_subdir={ti[1]} notes={ti[2] or ''}")

    print("=== generations ===")
    for gen in conn.execute(
        """SELECT id, stage, model, path, status, chosen, credits_spent, source_url
           FROM generations WHERE task_id = ? ORDER BY id""",
        (task_id,),
    ).fetchall():
        gid, stage, model, path, status, chosen, credits, src = gen
        marker = "★" if chosen else " "
        print(f"  {marker} id={gid} stage={stage:<6} model={model or '-'} path={path or '-'} status={status} credits={credits or '-'}")
        if src:
            print(f"      url={src}")
        cands = conn.execute(
            "SELECT slot, filename, chosen FROM candidates WHERE generation_id = ? ORDER BY slot",
            (gid,),
        ).fetchall()
        for slot, fn, c in cands:
            cm = "★" if c else " "
            print(f"      {cm} cand_{slot}: {fn}")


def cmd_dump(args: argparse.Namespace) -> None:
    """Write `lab.dump.sql` next to lab.db using sqlite3 .dump.

    Defaults to <db-dir>/lab.dump.sql so CI / dev workflows can `cat` it for diffs.
    """
    out = args.out or args.db.with_name("lab.dump.sql")
    cmd = ["sqlite3", str(args.db), ".dump"]
    with open(out, "w", encoding="utf-8") as f:
        rc = subprocess.run(cmd, stdout=f, check=False).returncode
    if rc != 0:
        sys.exit(f"sqlite3 .dump exited {rc}")
    print(f"wrote {out}")


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("slug", help="character slug (must exist in characters table)")
    p.add_argument("name", help="anim_task name (unique per character)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"path to lab.db (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--lab-root",
        type=Path,
        default=None,
        help="lab repo root (defaults to dirname of --db); used for resolving work/ paths",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # new
    p_new = sub.add_parser("new", help="create an anim_task row")
    add_common(p_new)
    p_new.add_argument("--kind", required=True,
                       choices=["idle", "state_triggered", "attribute_biased_idle", "attribute_transition"])
    p_new.add_argument("--status", default="wip")
    p_new.add_argument("--created-at", default=None, help="YYYY-MM-DD (default: today)")
    p_new.add_argument("--lab-master-dir", default=None)
    p_new.add_argument("--paired-with", default=None)
    p_new.add_argument("--trigger", default=None, help="trigger_expr column")
    p_new.add_argument("--path-summary", default=None)
    p_new.add_argument("--notes", default=None)
    p_new.set_defaults(func=cmd_new)

    # gen
    p_gen = sub.add_parser("gen", help="record a generation run")
    add_common(p_gen)
    p_gen.add_argument("--stage", required=True, choices=["a-pre", "a", "a-alt"])
    p_gen.add_argument("--model")
    p_gen.add_argument("--path", help="image-refine / text-to-video / action-mimic")
    p_gen.add_argument("--prompt")
    p_gen.add_argument("--prompt-file")
    p_gen.add_argument("--ref-single")
    p_gen.add_argument("--ref-first")
    p_gen.add_argument("--ref-last")
    p_gen.add_argument("--tail-frame-note")
    p_gen.add_argument("--tail-frame-lock-note")
    p_gen.add_argument("--head-frame-lock-note")
    p_gen.add_argument("--tail-locked-note")
    p_gen.add_argument("--source-url")
    p_gen.add_argument("--resolution")
    p_gen.add_argument("--aspect")
    p_gen.add_argument("--duration-s", type=float)
    p_gen.add_argument("--fps", type=int)
    p_gen.add_argument("--frame-count", type=int)
    p_gen.add_argument("--audio", default=None, action=argparse.BooleanOptionalAction)
    p_gen.add_argument("--credits", type=int, dest="credits")
    p_gen.add_argument("--credits-note")
    p_gen.add_argument("--queue-time-min", type=int)
    p_gen.add_argument("--status", default="success",
                       choices=["success", "failed", "superseded"])
    p_gen.add_argument("--chosen", action="store_true",
                       help="mark as the shipped generation (auto-unchose siblings)")
    p_gen.add_argument("--ran-at", default=None)
    p_gen.add_argument("--notes", default=None)
    p_gen.set_defaults(func=cmd_gen)

    # cand
    p_cand = sub.add_parser("cand", help="add a candidate row under a generation")
    add_common(p_cand)
    p_cand.add_argument("--gen", type=int, required=True, help="generation id")
    p_cand.add_argument("--slot", type=int, required=True)
    p_cand.add_argument("--filename", required=True)
    p_cand.add_argument("--chosen", action="store_true")
    p_cand.add_argument("--notes")
    p_cand.set_defaults(func=cmd_cand)

    # choose
    p_choose = sub.add_parser("choose", help="mark a generation / candidate as chosen=1")
    add_common(p_choose)
    p_choose.add_argument("--gen", type=int, help="generation id to mark chosen")
    p_choose.add_argument("--cand", type=int, help="candidate slot (requires --gen)")
    p_choose.set_defaults(func=cmd_choose)

    # attribute
    p_attr = sub.add_parser("attribute", help="upsert attribute_meta for a task")
    add_common(p_attr)
    p_attr.add_argument("--attribute")
    p_attr.add_argument("--level")
    p_attr.add_argument("--from-level")
    p_attr.add_argument("--to-level")
    p_attr.add_argument("--bias-weight", type=float)
    p_attr.add_argument("--loops", default=None, action=argparse.BooleanOptionalAction)
    p_attr.set_defaults(func=cmd_attribute)

    # target
    p_tgt = sub.add_parser("target", help="upsert target_inject for a task")
    add_common(p_tgt)
    p_tgt.add_argument("--anim-name", help="defaults to task name")
    p_tgt.add_argument("--webp-subdir", help="defaults to task name")
    p_tgt.add_argument("--notes")
    p_tgt.set_defaults(func=cmd_target)

    # inject
    p_inj = sub.add_parser("inject", help="re-export target manifest.json and copy webp")
    p_inj.add_argument("slug")
    p_inj.add_argument("name", nargs="?", default=None,
                       help="if given, also copy that task's webp into target project")
    p_inj.add_argument("--target-project", required=True, help="root of consuming project")
    p_inj.set_defaults(func=cmd_inject)

    # status
    p_st = sub.add_parser("status", help="list anim_tasks")
    p_st.add_argument("--slug")
    p_st.add_argument("--kind")
    p_st.set_defaults(func=cmd_status)

    # show
    p_show = sub.add_parser("show", help="show one anim_task with all generations")
    add_common(p_show)
    p_show.set_defaults(func=cmd_show)

    # dump
    p_dump = sub.add_parser("dump", help="write lab.dump.sql alongside lab.db")
    p_dump.add_argument("--out", type=Path, help="output path (default: <db-dir>/lab.dump.sql)")
    p_dump.set_defaults(func=cmd_dump)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
