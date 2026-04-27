# ACTIVE: BDL-040 — F4: Living Knowledge Base + Visual Landscape (VitePress)

> **Last updated:** 2026-06-02

---

## Current Focus

- **Phase:** Ready to start (Wave 1)
- **Epic bead:** `beadloom-83f` (swarm `beadloom-a8v`)
- **Next bead:** `beadloom-83f.1` — BEAD-01 dev: site generator core + scaffold + architecture pages
- **Blockers:** none

## Bead Map (epic `beadloom-83f`)

| Bead | Role | P | Status | Depends |
|------|------|---|--------|---------|
| .1 generator core + scaffold + architecture pages (G1+B/intra) | dev | P0 | open (READY) | — |
| .2 Showcase A — metrics dashboard (G2) | dev | P0 | open | .1 |
| .3 Showcase B — 🌟 landscape map (G4) | dev | P0 | open | .1 |
| .4 Showcase C — published validated docs + badges (G5) | dev | P0 | open | .1 |
| .5 dogfood — build Beadloom's own site (G6) | dev | P1 | open | .2,.3,.4 |
| .6 test — determinism + no-docs-mutation + honest metrics + coverage | test | P0 | open | .1–.5 |
| .7 review | review | P0 | open | .6 |
| .8 tech-writer (guide + SPEC + CHANGELOG + STRATEGY F4.2/F4.3) | tech-writer | P1 | open | .7 |

## Waves

- **Wave 1 (solo dev):** .1 — generator core + scaffold + architecture pages (foundation).
- **Wave 2 (dev, sequential — shared site.py/cli.py):** .2 (dashboard), .3 (map), .4 (validated docs).
- **Wave 3 (solo dev):** .5 — dogfood (build Beadloom's own site; merge-slot to land).
- **Wave 4 (test):** .6.
- **Wave 5 (review):** .7 → fix cycle if ISSUES.
- **Wave 6 (tech-writer):** .8.

## Progress Log

- 2026-06-02 — `/task-init` complete: PRD / RFC / CONTEXT / PLAN approved (PRD+RFC revised to the "showcase of 3 Beadloom products" framing — dashboard / interactive architecture / published validated docs); epic `beadloom-83f` + 8 sub-beads created; DAG wired; swarm `beadloom-a8v` (6 waves); `bd ready` confirms .1 unblocked.
- 2026-06-02 — BEAD-02 done (Showcase A — metrics dashboard). New `application/site_dashboard.py`: `build_dashboard_data` (deterministic JSON-safe dict) + `render_dashboard_md` + `serialize_dashboard_data`. Honest by construction — lint via `graph/linter.lint`, debt via `debt_report.compute_debt_score`+`compute_debt_trend`+`format_debt_json`, docs via read-only `sync_state` coverage/freshness, doctor via `doctor.run_checks`, federated rollup via the `federate` JSON verbatim. Wired into `generate_site` → emits `dashboard.md` + `dashboard.data.json` under `--out`. 15 tests (`tests/test_site_dashboard.py`) assert dashboard==gate equality, determinism, sorted-keys, out-dir-only. Full suite 2993 green; ruff/mypy clean; `beadloom ci` exit 0. application README re-attested to sync fixpoint.

## Notes / Reminders

- **Beadloom produces, VitePress renders** — no LLM (F4.1 deferred), no SaaS, static site only.
- **Honest by construction** — dashboard numbers AND doc badges from the SAME code paths as `lint`/`doctor`/`debt-report`/`sync-check`/`doc_sync`.
- **NEVER mutate source `docs/`** — Showcase C injects badges only into the COPY under `site/docs/`; authored prose untouched; no AI prose-rewriting.
- **Separate out-dir** (`site/`), build output gitignored; generated MD/config reproducible.
- **Determinism** — identical graph → byte-identical tree (sorted, no wall-clock in diffed output).
- **Map = Mermaid** thin slice (clickable); Cytoscape/D3 = follow-up. No schema bump.
- **Anonymization (binding):** landscape-map dogfood uses committed anonymized fixtures; never the gitignored scratch; `git grep` before commit.
- `site.py`/`cli.py` shared by .1–.5 → Wave 2 sequential (conflict-safe). Re-run sync-check to fixpoint after `mark_synced` (F4.1 invariant).
