# ACTIVE: BDL-046 — VitePress portal: navigation + bilingual About

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Dogfood round 2 — browser found 3 issues → fix beads 11(dev)/12(test)/13(review); BEAD-11 running
- **Review:** BEAD-07 = OK (closed); BEAD-10 fix (badge-link dead links) = done+deployed
- **Live dogfood findings (round 2):** (1) locale switcher translated the menu; (2) switcher 404'd on every page except /ru/; (3) docs-overview link wall reads poorly. Root cause for 1+2: VitePress `locales` is the wrong tool for curated About-only (global /x↔/ru/x mapping). FIX: drop locales, single EN sidebar, About bilingual via in-page cross-link (render_about rewrites README cross-links to /ru/↔/). #3: owner chose intro + section descriptions, no link wall.
- **Coordinator:** main loop (multi-agent)
- **Parent:** `beadloom-ivts`
- **Blockers:** none

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-ivts.1 | dev (site_about) | ✓ done (W1) |
| beadloom-ivts.2 | dev (site_nav) | ✓ done (W1) |
| beadloom-ivts.3 | dev (site.py home/arch/docs-overview) | ✓ done (W2) |
| beadloom-ivts.4 | dev (RU locale data) | in progress (W3) |
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
- 2026-06-02: W1 done + committed. site_about + site_nav shipped (47 tests, ruff/mypy clean). Doc-freshness gate: editing a domain README clears the synced stamp for ALL (README↔code) pairs under that ref → re-baseline the whole ref with `mark_synced_by_ref(conn, 'application', root)` then `sync-check` (no reindex) to fixpoint. W2 (BEAD-03 site.py) launched.
