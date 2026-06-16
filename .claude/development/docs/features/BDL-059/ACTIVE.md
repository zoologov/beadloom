# ACTIVE: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Type:** epic
> **Parent bead:** beadloom-fm3u
> **Updated:** 2026-06-15

---

## Current focus

**S0 DONE** (#20 merged) · **S1 DONE** (#21 merged) · **S2 DONE** (`.5`–`.8` closed; PR pending) — data-access seam (`connection()` CM + `infrastructure/repository.py` + `application/graph_reads.py` facade, TUI re-layered) + de-N+1 `check_source_coverage` (json_each, golden parity). Review PASS, behavior-preserving, 4372 passed under seeds, ci rc0. Follow-ups: `beadloom-2qwb` (centralize remaining same-layer node-reads), `beadloom-g0c5` (test_tui GC leak). **Next: S3 (`.9`∥`.10`∥`.11`) — decompose `graph/` (rules/+federation/) + layering fix + WHITE/GREY/BLACK cycles** (heavy slice — pause before it per owner). Lessons: recompose WITHOUT `--force` (#132); after worktree integration re-baseline sync + document new modules in domain README (#105); verify refactors under multiple `--randomly-seed`s.

## Slice status

| Slice | Beads | State |
|-------|-------|-------|
| S0 principle | .1 dev, .2 review | in progress |
| S1 test-decouple | .3, .4 | blocked → S0 |
| S2 repo + N+1 | .5, .6, .7, .8 | blocked → S1 |
| S3 graph decomp | .9–.14 | blocked → S2 |
| S4 services/app decomp | .15–.21 | blocked → S3 |
| S5 cache + types | .22–.24 | blocked → S4 |

## Plan notes

- Governing principle: cohesion-driven design (one nameable responsibility/module; split monsters by responsibility; never over-split; `domain-size-limit` is a consequence not a driver). Codified in S0.
- Behavior-preserving: no CLI/MCP/gate-verdict/graph-semantics change; golden-output tests for #123/#124/#128; `beadloom ci` rc 0 per slice.
- One PR per slice (`features/BDL-059-sN`); S3/S4 are heavy (real decomposition of monster modules) and use worktree-isolated parallel dev + merge-slot.
- Generated `site/` gitignored — do NOT re-commit.

## Progress log

- 2026-06-15 — PRD/RFC/CONTEXT/PLAN approved (RFC v2 cohesion-driven after owner pushback on metric-gaming). Epic + 24 beads created (beadloom-fm3u.1–.24), DAG S0→S1→S2→S3→S4→S5. Starting S0.
