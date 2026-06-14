# ACTIVE: BDL-052 (EPIC) — Usable doc-flow + role configurator

> **Last updated:** 2026-06-14

---

## Current Focus

- **Phase:** S1+S2 committed. S1+S2+S3 committed. S4/S5/S6 dev running IN PARALLEL (worktree-isolated).
- **Branch:** `features/BDL-052` (one branch; commit per slice; ONE PR at the end).
- **Coordinator:** main loop (multi-agent; independent dev beads run in parallel).
- **Parent:** `beadloom-3m2d`

## Beads

| Bead | Role | Status |
|------|------|--------|
| beadloom-3m2d.1 | dev — S1 pre-push Gate hook + coordinator loop + parallelism | ✓ done |
| beadloom-3m2d.2 | test — S1 | ✓ done |
| beadloom-3m2d.3 | review — S1 | ✓ done (PASS; 1 minor→.19) |
| beadloom-3m2d.4 | dev — S2 CORE roles (restore+modernize) | ✓ done |
| beadloom-3m2d.5 | test — S2 | ✓ done |
| beadloom-3m2d.6 | review — S2 | ✓ done (PASS; conftest nit fixed) |
| beadloom-3m2d.7 | dev — S3 configurator (flow.yml + ddd/fsd + overlays + adapters) | ✓ done (impl; +47 tests; ci rc0) |
| beadloom-3m2d.8 | test — S3 | ✓ done |
| beadloom-3m2d.9 | review — S3 | ✓ done (PASS; orphaned-adapter minor→followup/.19) |
| beadloom-3m2d.10 | dev — S4 symbol-scope | in progress (parallel worktree) |
| beadloom-3m2d.11 | test — S4 | blocked ← 10 |
| beadloom-3m2d.12 | review — S4 | blocked ← 11 |
| beadloom-3m2d.13 | dev — S5 CI parallel+cache | in progress (parallel worktree) |
| beadloom-3m2d.14 | test — S5 | blocked ← 13 |
| beadloom-3m2d.15 | review — S5 | blocked ← 14 |
| beadloom-3m2d.16 | dev — S6 active-sync --stage | in progress (parallel worktree) |
| beadloom-3m2d.17 | test — S6 | blocked ← 16 |
| beadloom-3m2d.18 | review — S6 | blocked ← 17 |
| beadloom-3m2d.19 | tech-writer — epic close | blocked ← 3,6,9,12,15,18 |

## Waves (one branch; commit per slice; ONE PR at the end)

W1 S1(.1→.2→.3) → W2 S2(.4→.5→.6) → W3 S3(.7→.8→.9) → W4 S4(.10–.12) → W5 S5(.13–.15) → W6 S6(.16–.18) → W7 tech-writer(.19) → ONE PR → merge → close. S4/S5/S6 independent after S1 (dev beads parallelizable).

## Key decisions (from PRD/RFC + owner discussion)

- Hard invariant: no code in main without current docs — deterministic **Gate** (pre-push hook + CI required check). NOT non-blocking.
- Local-primary: flow on the user's own agent (Claude Code / Cursor); tech-writer authors docs locally (no local Goose+Qwen). CI Goose+Qwen = unchanged fallback + speed (parallel+cache).
- **Role configurator:** CORE (restored+modernized from 1.9.0) + OVERLAYS — architecture **ddd + fsd (peers)** + stack (python/fastapi/javascript/typescript/vuejs) + TOOL adapters (claude/cursor), via `.beadloom/flow.yml` + drift-guard.
- Symbol-scope (changed-symbol ∩ doc-ref; conservative fallback). Explicit parallelism in the coordinator.

## Progress Log

- 2026-06-14: PRD/RFC(+Addendum)/CONTEXT/PLAN approved; epic `beadloom-3m2d` + 19 beads + DAG; branch `features/BDL-052`. W1 (S1) launched (.1 dev). Owner additions folded: restore lost agent rules (point 2), role configurator core+overlays (point 3), FSD first-class with DDD, explicit parallelism (point 1).
- 2026-06-14: BEAD-07 (S3 dev) implemented. `.beadloom/flow.yml` + `flow_config.py` (FlowConfig, strict validation, resolve/detect-stack); overlays under `onboarding/templates/roles/` (core/{4 roles} extracted from S2; architecture/{ddd,fsd} at parity + annotation vocab; stack/{python,fastapi,javascript,typescript,vuejs}); `role_composer.compose_role` (CORE+arch+sorted-stack, deterministic); `role_adapters.generate_adapters` (.claude/agents/* + .cursor/agents/* + .cursor/rules orchestrator); `setup-agentic-flow --tool/--stack/--architecture`; drift-guard (live .claude/agents/* == compose(ddd,python), catches hand-edit + CORE-change); config-check covers flow.yml + composed drift. 3 new modules classified (features part_of onboarding) + SPEC docs (coverage-lint 0). +47 tests; suite 4129 green; ruff+mypy clean; `beadloom ci` rc 0. NOT committed — hand to .8 (test).
