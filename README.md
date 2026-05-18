# ClawContent-Lab

> ⚠️ **Platform: macOS 14+ only.** The foreground-mask backend uses Apple's
> `VNGenerateForegroundInstanceMaskRequest` via a small Swift CLI; there is
> currently no portable fallback. Linux / Windows users can still consume the
> data model (`lab.db` + `scripts/`) but cannot run the mask + despill stage.
> Cross-platform mask backends are welcome contributions — see
> [CONTRIBUTING](./CONTRIBUTING.md) (TODO).

An open-source **libu** content generation toolkit, driven by AI coding agents
(Claude Code / Codex / OpenClaw). Use it to manage end-to-end character
animation pipelines built on top of [liblib.art](https://www.liblib.art/):

- Generate per-character idle / state-triggered / attribute-driven animations
- Pipeline: liblib (image-refine ▸ text-to-video ▸ action-mimic) → macOS Vision
  foreground mask → green-spill cleanup → WebP frame sequence → target project
  injection
- Local SQLite (`lab.db`) is the single source of truth for animation metadata;
  the consuming project's `manifest.json` is generated from it
- Per-character profiles, prompt history, generation candidates, credit costs,
  and target-project injection rules are all version-controllable as SQL dumps

> **No assets, no credentials.** The `lab.db` SQLite file, every kind of media
> file (mp4 / png / webp / mp3 / ...), and the contents of `work/` and
> `imports/` are kept out of git on purpose. Each contributor's character
> profiles under `skills/libu-gen/references/characters/` are also ignored —
> only the `example.md` template is shipped.

## Layout

```
ClawContent-Lab/
├── scripts/
│   ├── schema.sql                  # SQLite schema for lab.db
│   ├── migrate-from-existing.py    # one-shot import from a hand-written manifest.json
│   ├── export-manifest.py          # lab.db → target project manifest.json
│   └── verify-roundtrip.py         # field-level diff helper
└── skills/
    └── libu-gen/                   # Claude Code skill (copy to ~/.claude/skills/)
        ├── SKILL.md                # entry point (decision tree + reference index)
        ├── bgrm.swift              # macOS Vision foreground-mask CLI source
        └── references/
            ├── models.md
            ├── path-a-pre-image-refine.md
            ├── path-a-action-mimic.md
            ├── path-a-alt-text-to-video.md
            ├── pipeline-mask-despill-webp.md
            ├── target-inject-godot.md
            ├── archive-compress.md
            ├── state-triggered.md
            ├── troubleshooting.md
            └── characters/
                └── example.md      # per-character profile template
```

## Quick start

### 1. Clone

```bash
git clone https://github.com/BlackBearCC/ClawContent-Lab.git
cd ClawContent-Lab
```

### 2. Create your `lab.db`

```bash
sqlite3 lab.db < scripts/schema.sql
```

### 3. Register a character

Copy the template and fill it in for your character:

```bash
cp skills/libu-gen/references/characters/example.md \
   skills/libu-gen/references/characters/<your-slug>.md
$EDITOR skills/libu-gen/references/characters/<your-slug>.md
```

Then insert a `characters` row pointing at your target project:

```sql
INSERT INTO characters
  (slug, display_name, inject_target_dir, reference_doc,
   manifest_version, default_frame_format)
VALUES ('<your-slug>', '<Display Name>',
        'path/to/target/project/anim/',     -- relative inside your target repo
        'references/characters/<your-slug>.md',
        1,
        'WebP frame sequence, 0000-based, 24 fps default');
```

### 4. Install the agent skill (Claude Code)

```bash
cp -R skills/libu-gen ~/.claude/skills/
# first-time only — compile macOS Vision helper
swiftc -O ~/.claude/skills/libu-gen/bgrm.swift -o ~/.claude/skills/libu-gen/bgrm
```

Then in a new Claude Code session, ask: *"make a new idle animation for
\<your-slug\>"* — the skill loads its decision tree from `SKILL.md` and walks
you through the three production paths.

### 5. Optional — bootstrap from an existing hand-written `manifest.json`

If you already maintain a manifest by hand and want to switch to `lab.db` as
the source of truth, run:

```bash
python3 scripts/migrate-from-existing.py <consuming-project-root> <lab-root>
python3 scripts/verify-roundtrip.py \
  <consuming-project-root>/path/to/manifest.json \
  <(python3 scripts/export-manifest.py lab.db <your-slug> --print)
```

The diff must come out empty before you trust the import.

## Requirements

- **macOS 14+** (uses `VNGenerateForegroundInstanceMaskRequest` for foreground masking)
- **Python 3.10+** with `imageio_ffmpeg`, `Pillow`, `numpy`
- An AI coding agent that supports skills (Claude Code primarily; Codex / OpenClaw also welcome)
- Optional: Playwright MCP for browser-driven liblib.art automation
- A liblib.art account with credits

## Adding a new target engine

`target-inject-godot.md` is the only target-specific reference today. To
support another engine, add `target-inject-<engine>.md` describing how
characters are wired in that engine, and link it from `SKILL.md`'s pipeline
index. The DB schema is engine-agnostic — only `characters.inject_target_dir`
and the per-task `target_inject` row are consumed by `export-manifest.py`.

## License

[MIT](./LICENSE)
