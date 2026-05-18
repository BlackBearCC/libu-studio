"""Integration tests for lab.py CLI subcommands.

Tests invoke lab.py as a subprocess to exercise the actual argparse plumbing.
Each test gets a fresh on-disk lab.db in a tmp_path (the CLI requires a real
file because subcommands open the DB themselves).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LAB = REPO_ROOT / "scripts" / "lab.py"
SCHEMA = REPO_ROOT / "scripts" / "schema.sql"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db = tmp_path / "lab.db"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.execute(
        """INSERT INTO characters
           (slug, display_name, inject_target_dir, manifest_version, default_frame_format)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "example-mascot",
            "Example Mascot",
            "assets/characters/example-mascot/anim/",
            1,
            "WebP frame sequence, 0000-based, 24 fps default",
        ),
    )
    conn.commit()
    conn.close()
    return db


def run(*args: str, db: Path, check: bool = True) -> subprocess.CompletedProcess:
    """Invoke lab.py with --db pointing at the fixture DB."""
    cmd = [sys.executable, str(LAB), "--db", str(db), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def test_new_creates_task(db_path: Path):
    proc = run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    assert "created anim_task" in proc.stdout
    # idempotency / collision detection
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    assert "already exists" in (excinfo.value.stderr or "")


def test_new_rejects_unknown_character(db_path: Path):
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        run("new", "nobody", "idle_basic", "--kind", "idle", db=db_path)
    assert "not registered" in (excinfo.value.stderr or "")


def test_gen_and_choose_lifecycle(db_path: Path):
    run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    # first generation: failed run
    run(
        "gen", "example-mascot", "idle_basic",
        "--stage", "a-alt",
        "--model", "Seedance 1.5 Pro",
        "--prompt", "first try",
        "--status", "failed",
        db=db_path,
    )
    # second generation: shipped
    run(
        "gen", "example-mascot", "idle_basic",
        "--stage", "a-alt",
        "--model", "Seedance 1.5 Pro",
        "--prompt", "second try",
        "--chosen",
        db=db_path,
    )

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT id, status, chosen FROM generations
           WHERE task_id = (SELECT id FROM anim_tasks WHERE name='idle_basic')
           ORDER BY id"""
    ).fetchall()
    assert rows[0][1:] == ("failed", 0)
    assert rows[1][1:] == ("success", 1)
    conn.close()


def test_attribute_upsert(db_path: Path):
    run("new", "example-mascot", "idle_starving",
        "--kind", "attribute_biased_idle", db=db_path)
    run(
        "attribute", "example-mascot", "idle_starving",
        "--attribute", "hunger",
        "--level", "starving",
        "--bias-weight", "0.7",
        "--loops",
        db=db_path,
    )
    # second call: idempotent upsert
    run(
        "attribute", "example-mascot", "idle_starving",
        "--attribute", "hunger",
        "--level", "starving",
        "--bias-weight", "0.6",     # changed
        db=db_path,
    )
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        """SELECT bias_weight, loops FROM attribute_meta
           WHERE task_id = (SELECT id FROM anim_tasks WHERE name='idle_starving')"""
    ).fetchone()
    assert row[0] == pytest.approx(0.6)
    # loops was set to NULL on the second call (no --loops flag given)
    # — but with BooleanOptionalAction default=None, absence of flag means None,
    #   and the upsert writes None. Document this.
    assert row[1] is None
    conn.close()


def test_inject_writes_manifest(db_path: Path, tmp_path: Path):
    run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    run(
        "gen", "example-mascot", "idle_basic",
        "--stage", "a-alt",
        "--model", "Seedance 1.5 Pro",
        "--prompt", "p",
        "--source-url", "https://example.invalid/v.mp4",
        "--resolution", "720p",
        "--duration-s", "5",
        "--fps", "24",
        "--frame-count", "121",
        "--audio", "--no-audio",   # last one wins -> False
        "--credits", "20",
        "--chosen",
        db=db_path,
    )
    run("target", "example-mascot", "idle_basic", db=db_path)

    target_root = tmp_path / "fake_project"
    target_root.mkdir()
    run(
        "inject", "example-mascot",
        "--target-project", str(target_root),
        db=db_path,
    )
    manifest_path = target_root / "assets/characters/example-mascot/anim/manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["character"] == "example-mascot"
    assert data["animations"][0]["name"] == "idle_basic"
    assert data["animations"][0]["duration_s"] == 5
    assert data["animations"][0]["credits_spent"] == 20


def test_status_lists_tasks(db_path: Path):
    run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    run("new", "example-mascot", "yawn", "--kind", "idle", db=db_path)
    proc = run("status", db=db_path)
    assert "idle_basic" in proc.stdout
    assert "yawn" in proc.stdout


def test_dump_writes_sql(db_path: Path):
    run("new", "example-mascot", "idle_basic", "--kind", "idle", db=db_path)
    proc = run("dump", db=db_path)
    dump_path = db_path.parent / "lab.dump.sql"
    assert dump_path.exists(), proc.stdout + proc.stderr
    text = dump_path.read_text(encoding="utf-8")
    assert "CREATE TABLE" in text
    assert "example-mascot" in text
