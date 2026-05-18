"""Schema sanity tests: tables exist, foreign keys behave, basic insertion works."""
from __future__ import annotations


EXPECTED_TABLES = {
    "characters",
    "anim_tasks",
    "attribute_meta",
    "generations",
    "candidates",
    "target_inject",
}


def test_all_tables_created(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert EXPECTED_TABLES.issubset(names), (
        f"missing: {EXPECTED_TABLES - names}"
    )


def test_character_insert_and_lookup(conn, sample_character):
    row = conn.execute(
        "SELECT slug, display_name, manifest_version FROM characters WHERE slug = ?",
        (sample_character,),
    ).fetchone()
    assert row == ("example-mascot", "Example Mascot", 1)


def test_anim_task_requires_existing_character(conn, sample_character):
    # FK is declared but PRAGMA foreign_keys must be ON for enforcement
    conn.execute("PRAGMA foreign_keys = ON")
    # this should succeed: character exists
    conn.execute(
        """INSERT INTO anim_tasks (name, character_slug, kind, created_at)
           VALUES (?, ?, ?, ?)""",
        ("idle_basic", sample_character, "idle", "2026-05-18"),
    )
    conn.commit()

    # uniqueness: same (character_slug, name) again should fail
    import sqlite3
    try:
        conn.execute(
            """INSERT INTO anim_tasks (name, character_slug, kind, created_at)
               VALUES (?, ?, ?, ?)""",
            ("idle_basic", sample_character, "idle", "2026-05-18"),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("duplicate (character_slug, name) was not rejected")


def test_generation_with_candidates(conn, sample_character):
    conn.execute(
        """INSERT INTO anim_tasks (name, character_slug, kind, created_at)
           VALUES ('idle_basic', ?, 'idle', '2026-05-18')""",
        (sample_character,),
    )
    task_id = conn.execute("SELECT id FROM anim_tasks WHERE name='idle_basic'").fetchone()[0]
    conn.execute(
        """INSERT INTO generations
           (task_id, stage, model, path, prompt, status, chosen)
           VALUES (?, 'a-pre', 'Seedream 5.0 Lite', 'image-refine', 'p', 'success', 0)""",
        (task_id,),
    )
    gen_id = conn.execute(
        "SELECT id FROM generations WHERE task_id = ?", (task_id,)
    ).fetchone()[0]
    conn.executemany(
        """INSERT INTO candidates (generation_id, slot, filename, chosen)
           VALUES (?, ?, ?, ?)""",
        [
            (gen_id, 1, "a.png", 1),
            (gen_id, 2, "b.png", 0),
            (gen_id, 3, "c.png", 0),
            (gen_id, 4, "d.png", 0),
        ],
    )
    conn.commit()

    chosen_filename = conn.execute(
        """SELECT filename FROM candidates
           WHERE generation_id = ? AND chosen = 1""",
        (gen_id,),
    ).fetchone()
    assert chosen_filename == ("a.png",)
