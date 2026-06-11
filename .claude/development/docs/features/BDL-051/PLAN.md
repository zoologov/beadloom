# PLAN: BDL-051 (EPIC) — Beadloom governs itself

> **Status:** Approved
> **Created:** 2026-06-11
> **PRD/RFC/CONTEXT:** ./PRD.md · ./RFC.md · ./CONTEXT.md

---

## Beads (described — NOT created until this PLAN is Approved)

Parent: `BDL-051` (epic). Four slices, each a trunk-based PR (dev → test → review), + one epic tech-writer.

| Bead | Role | Title | Depends on |
|------|------|-------|------------|
| **S1 — feature definition + sprawl lint** | | | |
| .1 | dev | `docs/guides/architecture-model.md` (Domain vs Feature def) + `unregistered-feature-candidate` lint in `rule_engine` + `rules.yml` (per-domain files with `domain=`/no-`feature=`/≥N symbols, warn) | — |
| .2 | test | lint unit tests (synthetic graph + flags real onboarding candidates; warn-only; N threshold) | .1 |
| .3 | review | S1 quality/honesty (lint not a false-fail; def is clear) | .2 |
| **S2 — ai_agents domain + retire vendoring** | | | |
| .4 | dev | move `tools/ai_techwriter` → `src/beadloom/ai_agents/ai_techwriter/` + annotations + `services.yml` nodes (ai_agents domain, ai-techwriter feature) + SPEC; update imports + `ci.yml`/`.gitlab-ci.yml`/templates invocation → `beadloom.ai_agents.ai_techwriter`; retire `HARNESS_MODULES`/`*.py.txt`/`sync_vendored_harness`/drift-guard; recipe+provisioner → package-data; `ai_agents` boundary rule | .3 |
| .5 | test | move-regression tests (harness behavior unchanged; scaffold emits installed-module workflow; recipe as package-data; boundary rule) | .4 |
| .6 | review | S2 (no BDL-049/050 regression; vendoring cleanly retired; boundaries) | .5 |
| **S3a — taxonomy + coverage-lint** (EXPANDED 2026-06-11) | | | |
| .7 | dev | add `component` node kind (rule_engine VALID_NODE_KINDS + services.yml); replace sprawl-lint with COVERAGE-lint (every src module = node OR explicit exempt); exempt mechanism in rules.yml (<N symbols AND not-CLI AND internal) | .3 |
| .8 | test | coverage-lint (flags unclassified module; exempt honored; component kind valid) | .7 |
| .9 | review | S3a (taxonomy + coverage-lint correctness, exempt not a silent escape) | .8 |
| **S3b — classify ALL ~80 modules** | | | |
| .14 | dev | classify every src module → feature/component/exempt; create nodes (services.yml + annotations) + SPEC/DOC skeletons; coverage-lint clean | .9 |
| .15 | test | nodes/sync-check/coverage-lint clean across all 7 domains | .14 |
| .16 | review | classification correctness; no shadow code; each exempt justified | .15 |
| **S4 — process-tools ACTIVE-table fix + adoption** | | | |
| .10 | dev | `checkpoint`/`complete_bead` maintain the `ACTIVE.md` bead-status table (tolerant parser, best-effort) in `mcp_server.py`; wire coordinator adoption note | .3 |
| .11 | test | ACTIVE-table update tests (flip row on done/in-progress; fallback when unparseable; bd/gate mocked) | .10 |
| .12 | review | S4 (fail-safe; correct-by-construction ACTIVE) | .11 |
| **epic close** | | | |
| .13 | tech-writer | guides + CHANGELOG + ROADMAP + fill the new SPEC/DOC skeletons + renumber speed → BDL-052 (re-label stub `beadloom-parl`) | .6,.12,.16 |

## Dependencies / DAG

```
.1→.2→.3 ─┬─> .4→.5→.6 ─┐
          ├─> .7→.8→.9 ─┼─> .13 (tech-writer)
          └─> .10→.11→.12 ┘
```
S1 gates all (the lint + definition underpin S2/S3). S2/S3/S4 are independent after S1 (different files: ai_agents/ vs onboarding+services.yml vs mcp_server.py) but run as **sequential PRs** (trunk-based, one merge at a time) — order S2 → S3 → S4.

## Waves (trunk-based: one slice-PR at a time)

- **W1 (S1):** .1 dev → .2 test → .3 review → PR → merge.
- **W2 (S2):** .4 dev → .5 test → .6 review → PR (dogfoods the live agent on the new path) → merge.
- **W3 (S3):** .7 dev → .8 test → .9 review → PR → merge.
- **W4 (S4):** .10 dev → .11 test → .12 review → PR → merge.
- **W5:** .13 tech-writer → PR → merge → close epic.

Each slice-PR green on `ci.yml` (gate + tests + site-build + ai-techwriter) before merge; `main` green by construction.

## Acceptance (maps to goals)

- **G1** ← .1 (def). **G2** ← .1/.2 (lint). **G3** ← .7/.8 (re-model + audit).
- **G4** ← .4 (ai_agents move + graph). **G5** ← .4/.5 (no regression + boundaries + retire vendoring).
- **G6** ← .10 (adoption). **G7** ← .10/.11 (ACTIVE-table fix). **G8** ← .13 (docs + renumber).
