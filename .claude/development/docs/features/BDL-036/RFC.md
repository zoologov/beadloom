# RFC: BDL-036 — Phase 0: Foundation / Honesty Gate

> **Status:** Draft
> **Created:** 2026-05-30

---

## Overview

Make Beadloom pass its own `doctor` / `lint --strict` / `sync-check` honestly. Two tracks: (A) cheap, independent honesty fixes (#88/#92/#93/#94), and (B) the structural #91 god-package decouple via a new **application layer** (chosen approach), plus sync-check honesty (#89/#90), the YAML footgun (#86), and clean bootstrap (#71).

## Motivation

### Problem
See PRD. Re-verified live 2026-05-30: `lint --strict` exits 0 on 12 real violations (rules at `warn`); `doctor` reports false version + tool-count drift; silent/empty outputs in reindex + YAML loader.

### Solution
Split orchestration out of `infrastructure/`, restore the rules to `error`, and fix the diagnostic/silent-failure bugs — so "green" means green.

## Technical Context

### Constraints
- Python 3.10+, ruff + mypy --strict, pytest coverage ≥ 80%.
- Verify each claim live before fixing; `honest ≠ complete` — re-scope transparently if an issue proves deeper.
- This epic is the first real-code dogfood of the BDL-035 process (agents/* subagents).

### Affected Areas
`src/beadloom/infrastructure/` (split), `services/{cli,mcp_server}.py` + tests (import updates), `infrastructure/doctor.py` (#92/#93), `infrastructure/reindex.py` (#88/#94), `graph/loader.py` (#86), `doc_sync/engine.py` (#89/#90), `onboarding/` + rule templates (#71), `.beadloom/_graph/{services,rules}.yml` (layers + restore error).

## Proposed Solution

### #91 — Decouple via a new `application` layer (chosen: Split)

**Root cause:** `infrastructure/` conflates two layers — true domain-agnostic infra (`db.py`, config, git_activity, IO) and **orchestrators** (`reindex.py`, `doctor.py`, `debt_report.py`) that import domains. Orchestration is an upper layer misfiled as the lowest.

**Design — introduce a 4th layer:**
```
services → application → domains → infrastructure
  (cli/mcp/tui)  (reindex/doctor/debt)  (context-oracle/doc-sync/graph/onboarding)  (db/io/config)
```
- Create `src/beadloom/application/` and move the orchestrators (`reindex.py`, `doctor.py`, `debt_report.py`) there. Keep `infrastructure/` purely domain-agnostic (`db.py`, `git_activity.py`, config/IO).
- `application` may depend on domains + infrastructure (legal top-down); domains depend only on infrastructure. No more `infrastructure → domain` edges → all 12 violations vanish at the source.
- Update imports in `services/{cli,mcp_server}.py`, tests, and any cross-refs. Mechanical move (preserve module APIs) keeps most tests valid via import-path updates only.
- Graph: add `application` node + `layer-application` tag in `services.yml`; insert it into the `architecture-layers` rule (services → application → domains → infrastructure) in `rules.yml`.
- **Then restore** `no-dependency-cycles` + `architecture-layers` to `severity: error`; confirm `lint --strict` is genuinely clean (exit 0 with zero violations).

> **Risk control:** the move is the highest-risk change. Do it as the dedicated wave, after the cheap fixes are already green, with `bd merge-slot` serializing the landing. If any orchestrator turns out to be genuinely domain-agnostic (or vice versa), reclassify per evidence and note it.

### #92 — doctor version source
`_get_actual_version()` (`infrastructure/doctor.py:274-281`) returns `importlib.metadata.version("beadloom")` first (stale editable-install metadata). Make in-tree `__version__` the source of truth (or compare against it). (Moves with doctor.py into `application/`.)

### #93 — AGENTS.md MCP tool count
`generate_agents_md()` should enumerate MCP tools from the live registry so the count cannot drift (13 vs 14). Regenerate AGENTS.md; verify `doctor` MCP-tool check passes.

### #88 — incremental reindex "Nodes: 0"
`incremental_reindex` doesn't assign `result.nodes_loaded`/`edges_loaded` on the docs/code-only path → CLI prints default 0. Query live DB totals (as the `nothing_changed` branch already does at `cli.py:274-279`). Display-only fix; index is intact.

### #94 — narrow exceptions
`reindex.py:125,863,926` use `except Exception` for "table missing on first run". Narrow to `sqlite3.OperationalError` (+ verify it's a missing-table case); let other errors propagate.

### #86 — flow-style YAML edges → silent 0 nodes
Reproduce first (write a flow-style edge, reindex). Then in `graph/loader.py`: either correctly parse flow-style mappings (they are valid YAML — preferred) or raise a clear error naming the offending line. No silent 0-node result.

### #89/#90 — sync-check honesty + track markers
Investigate root cause in `doc_sync/engine.py`: why annotated+documented files report `untracked_files` (#89), and whether `<!-- beadloom:track=path -->` can be honored (#90a) or must be documented as unsupported (#90b). Deliver: sync-check reaches genuine 100% on a fully-annotated sample, OR an honest, evidence-backed re-scope if the fix is larger than Phase 0 warrants.

### #71 — clean bootstrap out-of-the-box
Once rules are `error`, a fresh `init --bootstrap` must pass `lint --strict`. Fix the bootstrap rule/classifier mismatch (feature-inside-service vs `feature-needs-domain`) so zero violations is the norm. Verify on a throwaway bootstrap.

### #96 — de-brittle tests (scoped)
Only where the #91 move breaks tests. A pure move + import-path update preserves most behavior; fix private-attr assertions only in touched modules (reindex/doctor/debt). Not a global rewrite.

### Changes

| File / Area | Change |
|-------------|--------|
| NEW `src/beadloom/application/` | move reindex.py, doctor.py, debt_report.py (orchestrators) |
| `infrastructure/` | keep domain-agnostic only (db, git_activity, config, IO) |
| `services/{cli,mcp_server}.py`, tests | update import paths |
| `infrastructure/doctor.py`→`application/` | #92 version source; #93 live MCP tool enumeration |
| `application/reindex.py` | #88 true totals; #94 narrow excepts |
| `graph/loader.py` | #86 flow-style YAML |
| `doc_sync/engine.py` | #89/#90 sync-check honesty |
| `onboarding/` + rule templates | #71 clean bootstrap |
| `.beadloom/_graph/{services,rules}.yml` | add application layer; restore cycles/layers to `error` |

### API Changes
Module locations change (`infrastructure.reindex` → `application.reindex` etc.). Public function signatures preserved where possible. Importers (cli, mcp_server, tests) updated. Log as API CHANGE for /review + /tech-writer.

## Alternatives Considered

- **Invert (protocols/registry):** cleanest DIP but adds DI scaffolding — overkill for a solo project now. Rejected.
- **Reclassify-only (graph 4th layer, no file move):** cheapest but dishonest — reindex.py and db.py stay in one dir, graph would misrepresent structure. Rejected (violates honesty principle — the whole point of this epic).

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Move breaks many imports/tests | High | Med | Mechanical move preserving APIs; run full pytest after; merge-slot serialize |
| #89/#90 deeper than Phase 0 | Med | Med | Time-box investigation; honest re-scope with evidence if so |
| Restoring `error` surfaces violations beyond the 12 | Low | Med | Run `lint --strict` iteratively during the move; fix as found |
| Circular dep just relocates (application↔domain) | Low | High | Verify with `beadloom doctor` + import direction after move |

## Open Questions

| # | Question | Decision |
|---|----------|----------|
| Q1 | #91 approach | Decided: **Split — new `application` layer** |
| Q2 | Layer name: `application` vs `orchestration` | Proposal: `application` (decide in CONTEXT) |
| Q3 | #89/#90 fixable within Phase 0? | Investigate first; honest re-scope if larger |
| Q4 | Execution: cheap fixes first, then #91? | Proposal: yes — Wave 1 cheap honesty fixes (fast green), Wave 2 #91 split, Wave 3 #86/#89/#90/#71 (detail in PLAN) |
