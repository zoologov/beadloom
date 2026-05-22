# ACTIVE: BDL-046 — VitePress portal: navigation + bilingual About

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Wave 1 (dev) — `site_about.py` ∥ `site_nav.py`
- **Coordinator:** main loop (multi-agent)
- **Parent:** `beadloom-ivts`
- **Blockers:** none

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-ivts.1 | dev (site_about) | ready |
| beadloom-ivts.2 | dev (site_nav) | ready |
| beadloom-ivts.3 | dev (site.py home/arch/docs-overview) | blocked ← 1,2 |
| beadloom-ivts.4 | dev (RU locale data) | blocked ← 2,3 |
| beadloom-ivts.5 | dev (config.mjs locales) | blocked ← 4 |
| beadloom-ivts.6 | test | blocked ← 1-5 |
| beadloom-ivts.7 | review | blocked ← 6 |
| beadloom-ivts.8 | dogfood (G6) | blocked ← 7 |
| beadloom-ivts.9 | tech-writer | blocked ← 8 |

## Waves

W1 `01∥02` → W2 `03` → W3 `04` → W4 `05` → test `06` → review `07` → dogfood `08` → docs `09`.

## Decisions / Notes

- Wave 1 beads touch **disjoint files** (new `site_about.py` vs edit `site_nav.py`). Run in parallel in the shared tree, but **subagents do NOT git commit** — the coordinator commits the wave once both finish (avoids the F4.4 parallel-commit / pre-commit-hook collision, UX #118).
- About = README generated (EN `/`, RU `/ru/`); only About bilingual (locales). Top nav empty; arch overview → `/architecture`.
- Dogfood (G6) = success criterion: verify on the **deployed** site, not just `docs:dev`.

## Progress Log

- 2026-06-02: docs approved (PRD/RFC/CONTEXT/PLAN), 9 beads + DAG created, coordinator activated, Wave 1 launching.
