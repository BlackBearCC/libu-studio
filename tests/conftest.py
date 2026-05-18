"""Shared pytest fixtures for libu-studio tests.

Tests are hermetic: every test gets a fresh in-memory SQLite DB with the
schema applied. We never touch a real lab.db on disk.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

# Allow `import export_manifest` etc. from scripts/ in tests.
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def schema_sql() -> str:
    return (SCRIPTS / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def conn(schema_sql: str):
    """Fresh in-memory SQLite with schema applied. Closed after the test."""
    c = sqlite3.connect(":memory:")
    c.executescript(schema_sql)
    yield c
    c.close()


@pytest.fixture
def sample_character(conn):
    """Insert one example-character row and return its slug."""
    conn.execute(
        """INSERT INTO characters
           (slug, display_name, inject_target_dir, reference_doc,
            manifest_version, default_frame_format)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "example-mascot",
            "Example Mascot",
            "assets/characters/example-mascot/anim/",
            "references/characters/example-mascot.md",
            1,
            "WebP frame sequence, 0000-based, 24 fps default",
        ),
    )
    conn.commit()
    return "example-mascot"
