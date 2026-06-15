# ACTIVE: BDL-058 — Release 2.1.0

> **Type:** chore
> **Branch:** features/BDL-058
> **Bead:** beadloom-eo9v
> **Updated:** 2026-06-15

---

## Current focus

Edits done; `beadloom ci` rc 0, pytest 4316, version 2.1.0. Next: commit → PR → merge → GitHub Release `v2.1.0` → delete `archive/BDL-051-docs` tag.

## Progress log

- 2026-06-15 — Release 2.1.0 prep on `features/BDL-058`: version bump (×3), CHANGELOG `[2.1.0]`, ROADMAP currency (v2.1.0 entry + P3 reword + docs-debt resolved), BDL-UX currency (closed #121/#130/#131; logged #132/#133; tallies 133/23/87), 3 doc nits (closes #131), version-fact hygiene (multi-agent guide title/intro neutralized + ignore historical refs; snapshot-label example de-versioned). `beadloom ci` green, 4316 tests pass, ruff/mypy clean.
- Post-merge TODO: GitHub Release `v2.1.0` (→ PyPI via pypi-publish.yml) + confirm deploy-site; `git tag -d archive/BDL-051-docs` (salvage source consumed).
