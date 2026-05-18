# Security Policy

## Supported versions

libu-studio is pre-1.0; only `main` is supported. Pin to a commit if you need
stability.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security-sensitive reports.**

Use one of:

1. **GitHub Security Advisories** (preferred):
   <https://github.com/BlackBearCC/libu-studio/security/advisories/new>
2. Email the maintainer (see GitHub profile)

We will acknowledge within **7 days** and aim to publish a fix or mitigation
within **30 days** for confirmed vulnerabilities.

## What counts as a vulnerability here

This is a content-generation toolchain, not a server. The realistic threat
model is small. Reportable issues include:

- **Credential leaks in shipped code or `lab.dump.sql` examples** — anything
  resembling `gho_*`, `ghs_*`, `pat_*`, `Bearer <token>`, liblib session
  cookies, browser local storage dumps
- **Arbitrary file overwrite** — a script that writes outside its declared
  output directory based on attacker-controlled input (manifest path, slug,
  filename)
- **Command injection** — anywhere a shell command interpolates a value from
  the manifest or DB without quoting
- **Path traversal** in `lab.db` lookups (e.g. a `..`-bearing `inject_target_dir`
  causing writes outside the target project)
- **Insecure download** — fetching from a URL stored in the DB without
  validating the host

## Out of scope

- The repo intentionally has no auth surface and runs entirely local
- liblib.art account abuse / token theft is a liblib.art concern, not ours
- macOS sandbox bypasses in `bgrm.swift` (Apple Vision is sandboxed by the OS)
- Bugs in upstream Python deps (`Pillow`, `numpy`, `imageio_ffmpeg`) —
  please report those upstream

## Safe disclosure

If you confirm a vulnerability and want it cited, we will credit you in the
fix commit and the published advisory. Coordinated disclosure with downstream
forks: we will give you the embargo window you request, up to 90 days.
