# Character profiles

Each character used by `libu-gen` ships with one Markdown profile in this
directory, named `<slug>.md`. The profile defines visual identity, personality,
existing animation vocabulary, and any attribute-driven systems.

**Profiles are per-user data and are not committed to git** — only this README
and `example.md` are versioned. To register a new character:

1. `cp example.md <your-slug>.md`
2. Fill in the template
3. `INSERT INTO characters (...) VALUES (...);` into `lab.db` so
   `export-manifest.py` knows where to inject WebP frames

See `../../../README.md` (repo root) for the full quick-start.
