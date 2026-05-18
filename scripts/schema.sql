-- libu-gen metadata store
-- Single source of truth for liblib.art animation tasks.
-- Files (mp4 / png / webp / intermediate frames) stay on disk under
-- work/<character>-anim/<task>/...; this DB only stores string paths + metadata.

PRAGMA foreign_keys = ON;

-- Characters registered for this lab. New character = one INSERT here
-- and one references/characters/<slug>.md in libu-gen skill.
CREATE TABLE IF NOT EXISTS characters (
  slug                  TEXT PRIMARY KEY,
  display_name          TEXT NOT NULL,
  inject_target_dir     TEXT NOT NULL,   -- relative path inside target project, e.g.
                                         -- assets/character-design/<slug>/anim/
  reference_doc         TEXT,            -- libu-gen reference path
  manifest_version      INTEGER NOT NULL DEFAULT 1,
  default_frame_format  TEXT,            -- top-level "format" of target manifest.json
  notes                 TEXT
);

-- One row per animation that ships (or shipped, or failed).
-- name is unique per character.
CREATE TABLE IF NOT EXISTS anim_tasks (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL,
  character_slug  TEXT NOT NULL REFERENCES characters(slug),
  kind            TEXT NOT NULL,    -- idle / state_triggered /
                                    -- attribute_biased_idle / attribute_transition
  status          TEXT NOT NULL DEFAULT 'wip',  -- wip / shipped / failed / archived
  created_at      TEXT NOT NULL,
  updated_at      TEXT,
  lab_master_dir  TEXT,             -- relative lab path, e.g. work/<slug>-anim/<task>/
  paired_with     TEXT,             -- sibling task name (enter ↔ exit, transition recovery)
  trigger_expr    TEXT,             -- Godot signal/method expression
                                    -- (state_triggered + attribute_transition both use this)
  path_summary    TEXT,             -- free-text pipeline summary, e.g.
                                    -- "image-refine (Seedream 5.0 Lite) + text-to-video (可灵 3.0)"
  notes           TEXT,
  UNIQUE(character_slug, name)
);

-- Attribute-driven animations (hunger-starving, mood-happy, ...).
-- Used for kind in (attribute_biased_idle, attribute_transition).
CREATE TABLE IF NOT EXISTS attribute_meta (
  task_id      INTEGER PRIMARY KEY REFERENCES anim_tasks(id) ON DELETE CASCADE,
  attribute    TEXT,                -- hunger / mood / ...
  level        TEXT,                -- for attribute_biased_idle: which level we play under
  from_level   TEXT,                -- for attribute_transition
  to_level     TEXT,                -- for attribute_transition
  bias_weight  REAL,                -- probability bias when in this level (0-1)
  loops        INTEGER              -- 0/1, loops in idle pool
);

-- Each liblib generation run (success or failed). Append-only.
-- chosen=1 means this generation produced the assets shipped for the task.
CREATE TABLE IF NOT EXISTS generations (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id               INTEGER NOT NULL REFERENCES anim_tasks(id) ON DELETE CASCADE,
  stage                 TEXT,        -- a-pre / a / a-alt
  model                 TEXT,        -- e.g. Seedance 1.5 Pro / 可灵 3.0 (首尾帧 mode)
  path                  TEXT,        -- text-to-video / image-refine / action-mimic
  prompt                TEXT,
  ref_single            TEXT,        -- target manifest field "reference_image"
  ref_first             TEXT,        -- target manifest field "reference_image_first"
  ref_last              TEXT,        -- target manifest field "reference_image_last"
  tail_frame_note       TEXT,        -- target manifest field "tail_frame"
  tail_frame_lock_note  TEXT,        -- target manifest field "tail_frame_lock"
  head_frame_lock_note  TEXT,        -- target manifest field "head_frame_lock"
  tail_locked_note      TEXT,        -- target manifest field "tail_locked"
  source_url            TEXT,        -- liblib mp4 / png download URL
  resolution            TEXT,
  aspect                TEXT,
  duration_s            REAL,
  fps                   INTEGER,
  frame_count           INTEGER,
  audio                 INTEGER,     -- 0/1
  credits_spent         INTEGER,
  credits_note          TEXT,
  queue_time_min        INTEGER,
  status                TEXT NOT NULL DEFAULT 'success',  -- success / failed / superseded
  chosen                INTEGER NOT NULL DEFAULT 0,
  ran_at                TEXT,
  notes                 TEXT
);

-- Multi-candidate output of a single generation (image-refine 4 imgs, etc).
-- For single-output generations (video), this can be left empty.
CREATE TABLE IF NOT EXISTS candidates (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  generation_id  INTEGER NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
  slot           INTEGER NOT NULL,  -- 1-based candidate index
  filename       TEXT,              -- liblib filename or local path
  chosen         INTEGER NOT NULL DEFAULT 0,
  notes          TEXT
);

-- How a task lands in the target project (Godot today, others later).
CREATE TABLE IF NOT EXISTS target_inject (
  task_id        INTEGER PRIMARY KEY REFERENCES anim_tasks(id) ON DELETE CASCADE,
  anim_name      TEXT,              -- name written into target manifest.json (often = task name)
  webp_subdir    TEXT,              -- relative to character.inject_target_dir
  inject_notes   TEXT
);

CREATE INDEX IF NOT EXISTS idx_generations_task ON generations(task_id);
CREATE INDEX IF NOT EXISTS idx_candidates_gen   ON candidates(generation_id);
