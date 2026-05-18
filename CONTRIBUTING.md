# Contributing to libu-studio

Thanks for considering a contribution! libu-studio is a young project; almost
any improvement is welcome — code, docs, character profiles, target-engine
adapters, or just bug reports.

## TL;DR

1. Fork + clone
2. `sqlite3 lab.db < scripts/schema.sql` to spin up a local DB
3. `pip install -r requirements-dev.txt` (when present — for now just stdlib +
   `Pillow`, `numpy`, `imageio-ffmpeg`, `pytest`)
4. `pytest tests/` should be green before you push
5. Open a PR against `main` with a Conventional Commit-style title

## Development setup

### Required tools

- **Python 3.10+** (stdlib `sqlite3`, plus `Pillow numpy imageio-ffmpeg pytest`)
- **macOS 14+** if you want to run the foreground-mask backend (Apple Vision)
- **`gh` CLI** if you plan to script GitHub operations from CI

### Repo layout

See [`README.md`](./README.md) for the canonical layout. In short:

- `scripts/` — Python tools that operate on `lab.db`
- `skills/libu-gen/` — Claude Code skill (entry point + references)
- `tests/` — pytest suite covering schema and export logic
- `.github/` — workflows, issue & PR templates

### Local test loop

```bash
pytest tests/                       # full suite
pytest tests/test_export.py -k field_round_trip   # one test
ruff check scripts/ tests/          # lint (matches CI)
```

`tests/` uses an in-memory SQLite, so it's hermetic — no `lab.db` is read or
written. New scripts should follow the same pattern (accept a connection or a
path so tests can inject a fixture DB).

## What we'd love help with

- **`lab.py` CLI subcommands** — `new / gen / choose / inject / status / show
  / dump` are the immediate next milestone (track in
  [issues](https://github.com/BlackBearCC/libu-studio/issues))
- **A cross-platform mask backend** — today we only support Apple Vision via
  `bgrm.swift`. A pure-Python or `onnx` rembg port would let Linux/Windows
  users participate
- **Target-engine adapters** — currently only Godot. Unity, Cocos Creator,
  Spine, or even browser/Canvas adapters welcome. See "Adding a new target
  engine" in `README.md` for the convention
- **Character profiles** — character profiles under
  `skills/libu-gen/references/characters/*.md` are intentionally
  per-contributor (gitignored) — but `example.md` is shipped as a template and
  PRs that improve the template are welcome
- **Localization** — SKILL.md and references are written in Chinese today;
  English / Japanese translations welcome under
  `skills/libu-gen/references/i18n/<lang>/` (TBD)

## Commit message style

Conventional Commits:

```
feat(lab-cli): add 'gen' subcommand
fix(export): collapse REAL columns with integral values to int
docs(readme): clarify macOS platform requirement
chore(ci): pin ruff to 0.6
```

Common scopes: `lab-cli`, `export`, `migrate`, `skill`, `ci`, `tests`, `docs`,
`readme`, `gitignore`. Use lowercase. Keep the subject under 70 chars.

If a commit touches the SKILL.md trigger phrasing or any reference file's
filename, mention that in the body so downstream forks can update their
copies in `~/.claude/skills/libu-gen/`.

## Pull request checklist

Before requesting review:

- [ ] `pytest tests/` passes
- [ ] `ruff check scripts/ tests/` is clean
- [ ] No new credentials, tokens, cookies, or env values added (search your
      diff for `gho_`, `ghs_`, `pat_`, `Bearer `, `cookie:`)
- [ ] No new hard-coded local paths (`~/Documents/...`, `/Users/...`,
      `C:\Users\...`) — use placeholders documented in `archive-compress.md`
- [ ] If you added a new field to the schema, you also updated
      `export-manifest.py` and added a test
- [ ] If you added or moved a reference file, you updated the index in
      `skills/libu-gen/SKILL.md`

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`:

- **Bug report** — something broke
- **Feature request** — a new pipeline path / output type / model adapter
- **New target engine** — proposal to add e.g. Unity / Cocos / Spine support

For anything sensitive (potential credential leak, security advisory), see
[`SECURITY.md`](./SECURITY.md) instead of opening a public issue.

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/)
v2.1. Be kind, assume good faith. A formal `CODE_OF_CONDUCT.md` will be added
when the contributor base grows; until then, reach out to the maintainer if
you experience or witness behavior that violates that spirit.
