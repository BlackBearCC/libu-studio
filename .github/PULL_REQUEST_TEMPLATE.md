# <Short summary>

## What this PR does

<!-- 1-3 bullets. The "why" matters more than the "what" — the diff shows
     the what. -->

## How I tested it

<!-- Did `pytest tests/` pass? Did you run an end-to-end pipeline against
     a real character profile? -->

```
pytest tests/
ruff check scripts/ tests/
```

## Checklist

- [ ] `pytest tests/` passes
- [ ] `ruff check scripts/ tests/` is clean
- [ ] No credentials, tokens, cookies, or env values in the diff
      (search for `gho_`, `ghs_`, `pat_`, `Bearer `, `cookie:`)
- [ ] No new hard-coded local paths (`~/Documents/...`, `/Users/...`, `C:\Users\...`)
- [ ] Schema change? — `export-manifest.py` and tests updated
- [ ] New reference file? — `SKILL.md` index updated
- [ ] User-facing string change? — touched both `SKILL.md` *and* the
      `~/.claude/skills/libu-gen/` consumer copy (for your own dev machine,
      not part of this repo)

## Screenshots / before-after

<!-- Optional but loved for output-type / character profile PRs. -->
