# ACTIVE: BDL-054 — Release 2.0.0 prep

> **Last updated:** 2026-06-14

---

## Current Focus

- **Phase:** all beads done (.1 dev, .2 tech-writer, .3 review PASS). Committing + opening release PR.
- **Branch:** `features/BDL-054` (one branch, one PR → release).
- **Parent:** `beadloom-uvpp`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-uvpp.1 | dev — release mechanics (version/badges/CHANGELOG/ROADMAP) | ✓ done |
| beadloom-uvpp.2 | tech-writer — README en/ru + architecture + getting-started (→VitePress) | ✓ done |
| beadloom-uvpp.3 | review — release readiness (badges/en≡ru/docs/version/VitePress) | ✓ done (PASS) |

## Waves

W1 .1 dev → .2 tech-writer → .3 review → ONE PR → merge → coordinator cuts GitHub Release v2.0.0 (→ pypi-publish + deploy-site).

## Key decisions (from BRIEF)

- Version **2.0.0** (semver MAJOR — breaking: ai_techwriter path, coverage-lint=error, vendoring retired + capability leap). `__version__` in src/beadloom/__init__.py.
- ty migration DEFERRED (beta + lower accuracy); keep `mypy --strict`.
- Public docs feed VitePress (`beadloom docs site`); en ≡ ru.
- Tests badge fix: tests.yml → ci.yml (retired in BDL-050).

## Progress Log

- 2026-06-14: BRIEF approved; chore `beadloom-uvpp` + 3 beads; branch `features/BDL-054`. W1 (.1 dev) launched.
