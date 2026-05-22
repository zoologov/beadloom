# PLAN: BDL-046 — VitePress portal: navigation + bilingual About

> **Status:** Approved
> **Created:** 2026-06-02
> **CONTEXT:** ./CONTEXT.md

---

## Beads (DAG)

Parent: `[epic] BDL-046 — VitePress portal: navigation + bilingual About`

| Bead | Role | Title | Depends on |
|------|------|-------|-----------|
| BEAD-01 | dev | `site_about.py` — README→About transform + link rebasing | — |
| BEAD-02 | dev | `site_nav.py` — ordered sidebar, flatten Dashboard/Landscape, About + Getting Started, `/architecture` link, Documentation overview + expanded, empty top nav | — |
| BEAD-03 | dev | `site.py` — emit About home (EN `/index.md`, RU `/ru/index.md`), move arch overview → `/architecture.md`, docs overview `/docs/index.md` | BEAD-01, BEAD-02 |
| BEAD-04 | dev | `site_nav.py` + `site.py` — RU locale: `navRu`/`sidebarRu` (About-only RU + EN-section links) | BEAD-02, BEAD-03 |
| BEAD-05 | dev | `config.mjs` — `locales` block (EN root + RU), import `navRu`/`sidebarRu` | BEAD-04 |
| BEAD-06 | test | Tests: site_about (rebasing cases), site_nav (order/flatten/locale), site (home/arch-move/docs-overview/ru) | BEAD-05 |
| BEAD-07 | review | Code review (read-only): correctness, purity/determinism, link-safety, mypy/ruff | BEAD-06 |
| BEAD-08 | dogfood | Generate + build + deploy own portal; verify in browser (G6): About landing, exact menu, no top nav + theme toggle, docs-overview tree, EN↔RU switch; log UX | BEAD-07 |
| BEAD-09 | tech-writer | VitePress guide (new IA + bilingual-About) + CHANGELOG + STRATEGY note | BEAD-08 |

## Waves

```
Wave 1 (dev):     BEAD-01 ∥ BEAD-02        (independent: about-transform, nav builders)
Wave 2 (dev):     BEAD-03                  (home/arch-move/docs-overview — needs 01+02)
Wave 3 (dev):     BEAD-04                  (RU locale data — needs 02+03)
Wave 4 (dev):     BEAD-05                  (config.mjs locales wiring — needs 04)
Test wave:        BEAD-06                  (after all dev)
Review wave:      BEAD-07                  (after test)  ── ISSUES → fix beads → re-run
Dogfood wave:     BEAD-08                  (after review OK; the success criterion)
Docs wave:        BEAD-09                  (after dogfood)
```

## Critical path

BEAD-01/02 → 03 → 04 → 05 → 06 → 07 → 08 → 09

## Parallelism

- Wave 1: BEAD-01 and BEAD-02 run in parallel (different modules: `site_about.py` vs `site_nav.py`). To avoid the F4.4 shared-tree pre-commit collision (UX #118), run them with **worktree isolation** or sequentially; merges serialized via `bd merge-slot`.
- BEAD-03/04/05 are a serial chain (each builds on the prior).

## Acceptance (epic-level)

- [ ] G1 menu order exact; Dashboard + Landscape flat; Architecture collapsed; Documentation expanded + Overview-led.
- [ ] G2 About (README) is the landing `/`; arch overview at `/architecture`.
- [ ] G3 `/docs/` is intro + grouped tree.
- [ ] G4 no top nav; theme toggle works.
- [ ] G5 About switches EN↔RU via locale switcher.
- [ ] G6 verified on the deployed site.
- [ ] G7 docs/CHANGELOG/STRATEGY updated.
- [ ] Gates green: pytest, ruff, mypy, `beadloom ci` (reindex/lint/sync-check/doctor); anonymization clean.

## Notes

- `dogfood` bead uses `subagent_type: dev` (build + browser verification is dev-side); or run inline by the coordinator if a subagent is build-blocked.
- No DB migration; regeneration idempotent.
