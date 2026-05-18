"""End-to-end test: insert minimal data → run export-manifest → verify shape."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_export_module():
    """`scripts/export-manifest.py` has a hyphen in its name, so we can't
    `import export-manifest`. Load it manually."""
    path = SCRIPTS / "export-manifest.py"
    spec = importlib.util.spec_from_file_location("export_manifest", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["export_manifest"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def export_mod():
    return _load_export_module()


@pytest.fixture
def populated_conn(conn, sample_character):
    """Add one shipped idle task + its main generation. Mirrors what the
    pipeline would create for a freshly-completed animation."""
    conn.execute(
        """INSERT INTO anim_tasks
           (name, character_slug, kind, status, created_at, lab_master_dir)
           VALUES ('idle_basic', ?, 'idle', 'shipped', '2026-05-18',
                   'work/example-mascot-anim/idle_basic/')""",
        (sample_character,),
    )
    task_id = conn.execute(
        "SELECT id FROM anim_tasks WHERE name='idle_basic'"
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO generations
           (task_id, stage, model, prompt,
            ref_single, source_url,
            resolution, aspect, duration_s, fps, frame_count, audio,
            credits_spent, status, chosen, ran_at)
           VALUES (?, 'a-alt', 'Seedance 1.5 Pro', 'a stable idle pose',
                   'first green-screen reference',
                   'https://example.invalid/v.mp4',
                   '720p', '3:4', 5, 24, 121, 0,
                   20, 'success', 1, '2026-05-18')""",
        (task_id,),
    )
    conn.execute(
        """INSERT INTO target_inject (task_id, anim_name, webp_subdir)
           VALUES (?, 'idle_basic', 'idle_basic')""",
        (task_id,),
    )
    conn.commit()
    return conn


def test_export_top_level_shape(export_mod, populated_conn, sample_character):
    manifest = export_mod.build_manifest(populated_conn, sample_character)
    assert manifest["version"] == 1
    assert manifest["character"] == sample_character
    assert "format" in manifest
    assert isinstance(manifest["animations"], list)
    assert len(manifest["animations"]) == 1


def test_export_animation_fields(export_mod, populated_conn, sample_character):
    manifest = export_mod.build_manifest(populated_conn, sample_character)
    anim = manifest["animations"][0]
    assert anim["name"] == "idle_basic"
    assert anim["model"] == "Seedance 1.5 Pro"
    # int columns must come out as int (not "5.0")
    assert anim["duration_s"] == 5
    assert isinstance(anim["duration_s"], int)
    assert anim["fps"] == 24
    assert anim["frame_count"] == 121
    assert anim["audio"] is False
    assert anim["reference_image"] == "first green-screen reference"
    assert anim["source_video_url"] == "https://example.invalid/v.mp4"
    # idle kind is the default, should NOT serialize
    assert "kind" not in anim


def test_export_attribute_biased_idle(export_mod, conn, sample_character):
    conn.execute(
        """INSERT INTO anim_tasks
           (name, character_slug, kind, status, created_at)
           VALUES ('idle_starving', ?, 'attribute_biased_idle', 'shipped', '2026-05-18')""",
        (sample_character,),
    )
    task_id = conn.execute(
        "SELECT id FROM anim_tasks WHERE name='idle_starving'"
    ).fetchone()[0]
    conn.execute(
        """INSERT INTO attribute_meta
           (task_id, attribute, level, bias_weight, loops)
           VALUES (?, 'hunger', 'starving', 0.7, 1)""",
        (task_id,),
    )
    conn.execute(
        """INSERT INTO generations
           (task_id, stage, model, prompt, status, chosen, ran_at)
           VALUES (?, 'a-alt', '可灵 3.0', 'p', 'success', 1, '2026-05-18')""",
        (task_id,),
    )
    conn.commit()

    manifest = export_mod.build_manifest(conn, sample_character)
    anim = manifest["animations"][0]
    assert anim["kind"] == "attribute_biased_idle"
    assert anim["attribute"] == "hunger"
    assert anim["level"] == "starving"
    assert anim["bias_weight"] == pytest.approx(0.7)
    assert anim["loops"] is True


def test_export_missing_character_errors(export_mod, conn):
    with pytest.raises(SystemExit):
        export_mod.build_manifest(conn, "nonexistent-slug")
