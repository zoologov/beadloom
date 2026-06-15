# ACTIVE: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Type:** epic
> **Parent bead:** beadloom-fm3u
> **Updated:** 2026-06-15

---

## Current focus

**S0 DONE** (PR #20 merged, `68e53ff`) — cohesion-driven principle in CORE roles. **S1 DONE** (PR pending) — `.3`+`.4` closed: ~112 prod-internal test couplings decoupled to read-only accessors/observable behavior (review PASS, behavior-preserving), db yield/finally fixtures (ResourceWarnings 64→0), pytest-randomly, grammar-guard (fails-not-skips); 4317 passed, ci rc0. **Next: S2 (`.5`∥`.6`) — repository seam + N+1.** Recompose lesson: `setup-agentic-flow` WITHOUT `--force` (#132); re-vendor snapshots by copying live→vendored.

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
