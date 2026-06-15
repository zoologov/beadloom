# PLAN: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Status:** Approved
> **Created:** 2026-06-15
> **Type:** epic
> **PRD:** ./PRD.md · **RFC:** ./RFC.md · **CONTEXT:** ./CONTEXT.md

---

## Bead DAG (created only after this PLAN is Approved)

Parent: **BDL-059 [epic]** — Code-health debt paydown (cohesion-driven). Six slices, one green PR each, sequenced S0→S1→S2→S3→S4→S5. Within a slice: dev(s) → test → review → tech-writer (where docs change). The slice-review gates the next slice's first dev.

### S0 — Codify cohesion-driven principle
- **.1 [dev]** Add the cohesion-driven principle to CORE `dev` + `review` roles (`onboarding/templates/roles/core/{dev,review}.md.txt`); recompose adapters (`setup-agentic-flow`); drift-guard green. (Peer to DDD/TDD/TBD.)
- **.2 [review]** ← .1

### S1 — Test decoupling + hygiene (#129d + #129a-f) — keystone
- **.3 [dev]** Decouple the ~90 production-internal test couplings (TUI read-only props, `Doctor`) — leave test-internal fixture helpers; db `yield`/`finally` fixtures (kill ResourceWarnings); add `pytest-randomly`; tree-sitter grammar CI guard. (TDD; behavior change limited to adding read-only accessors.)
- **.4 [review]** ← .3, .2

### S2 — Data-access seam + N+1 (#122 + #123)
- **.5 [dev]** Connection context-manager (no bare `open_db`) + `infrastructure/repository.py` (centralize the 16× repeated queries) + route `tui/` through application/repository (no direct `.execute()`).
- **.6 [dev]** Rewrite `doc_sync/engine.py::check_source_coverage` (single CTE/JOIN, drop non-indexable `LIKE`) — golden-output test pins identical results.
- **.7 [test]** ← .5, .6 — golden coverage + repository + ResourceWarning-clean + TUI smoke.
- **.8 [review]** ← .7, .4

### S3 — Decompose `graph/` + layering + cycles (#125-graph + #124 + layering)
- **.9 [dev]** Extract `graph/rule_engine.py` → `rules/` package by responsibility (`types`/`loader`/`evaluators`/`cycles`/`__init__`); stable re-exports; new graph node(s).
- **.10 [dev]** Extract `graph/federation.py` → `federation/` package (`refs`/`export`/`reconcile`); `contracts.py` stays in `graph`.
- **.11 [dev]** Fix the `graph`→`application.reindex` layering inversion (no lazy-import workaround) + WHITE/GREY/BLACK cycle detection (golden-output equivalent).
- **.12 [test]** ← .9, .10, .11 — golden cycles, `lint --strict` clean, no `domain-size-limit` warning on `graph`, import-boundary clean.
- **.13 [review]** ← .12, .8
- **.14 [tech-writer]** ← .13 — `docs/architecture.md` + domain READMEs/SPECs for the new `rules`/`federation` structure.

### S4 — Decompose `services`/`application`/`onboarding` monsters (#126 + big files)
- **.15 [dev]** `services/cli.py` → `services/commands/` package (per command group) + thin Click wiring; `cli:status` business logic → `application/status.py` (own node).
- **.16 [dev]** `application/reindex.py` → `application/reindex/` package (`full`/`incremental`/`fingerprint`/`__init__`).
- **.17 [dev]** `onboarding/scanner.py` → `onboarding/scanner/` package (`detect`/`classify`/`bootstrap`/`interactive`).
- **.18 [dev]** Split `application/debt_report.py` (collection/scoring/formatting) + `application/site_dashboard.py` (data/render).
- **.19 [test]** ← .15–.18 — behavior parity (CLI output, status, reindex, debt, dashboard), golden checks.
- **.20 [review]** ← .19, .13
- **.21 [tech-writer]** ← .20 — docs for the new `commands`/`status`/`reindex`/`scanner` structure.

### S5 — Cache + types tail (#128 + #127)
- **.22 [dev]** Wire `context_oracle/builder.py::build_context` through `SqliteCache` (golden bundle parity) + TypedDict/dataclasses for onboarding `Any` (`doc_generator`/`scanner`/`config_reader`) + narrow `git_activity.py` `except`.
- **.23 [test]** ← .22 — golden bundle + cache hit/miss + type-narrowing regressions.
- **.24 [review]** ← .23, .20

## Dependencies / waves

```
S0:  .1 → .2
S1:  (.2) → .3 → .4
S2:  (.4) → [.5 ∥ .6] → .7 → .8
S3:  (.8) → [.9 ∥ .10 ∥ .11] → .12 → .13 → .14
S4:  (.13) → [.15 ∥ .16 ∥ .17 ∥ .18] → .19 → .20 → .21
S5:  (.20) → .22 → .23 → .24
```

- Within-slice parallel dev beads (`.5∥.6`, `.9∥.10∥.11`, `.15∥.16∥.17∥.18`) run via **worktree isolation**; integrate by file-checkout, serialized through `bd merge-slot`. Beware shared-file overlap (e.g. `cli.py` in S4 — coordinate).
- One PR per slice → `main`, green-gated, merged in order.

## Critical path

`S0 → S1 → S2 → S3 (graph decomposition) → S4 (services/app decomposition) → S5`. S3 + S4 are the heavy slices (real cohesion decomposition of the monster modules).

## Notes

- Parent is **`epic`-type** (enables `bd swarm` for the 24-bead DAG).
- Behavior-preserving throughout; golden-output tests for #123/#124/#128; `beadloom ci` rc 0 per slice.
- Cohesion-driven becomes a permanent flow principle from S0; review enforces both "no monster" AND "no over-split".
- Pure internal refactor → likely no version bump (or a PATCH after S5).
- Scope is large by design (owner: maximal code quality) — slices are independently valuable; the epic can pause between them.
