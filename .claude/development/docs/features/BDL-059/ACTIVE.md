# ACTIVE: BDL-059 — Code-health debt paydown (cohesion-driven)

> **Type:** epic
> **Parent bead:** beadloom-fm3u
> **Updated:** 2026-06-15

---

## Current focus

**S0 DONE** (#20) · **S1 DONE** (#21) · **S2 DONE** (#22). **S3 dev DONE** (`.9/.10/.11` closed): `rule_engine.py` 2249→`graph/rules/` (types/loader/evaluators/cycles + WHITE/GREY/BLACK #124, golden parity); `federation.py` 1000→`graph/federation/` (refs/export/reconcile/gate; `.10` done inline — subagent bash-blocked); `graph→application` layering inversion fixed (`resolve_scan_paths`→infra, `linter.lint` reindex-callback). All public import paths byte-stable; 4375 passed ×3 seeds; ci rc0. **domain-size-limit recalibrated 200→280** (owner decision: cohesion-driven in-domain split can't lower the count; `graph` 216 / `application` 251 are legit-large bounded contexts; documented in rules.yml — recalibration, NOT gaming). **Principle codified in flow**: dev+review roles (recalibration-vs-gaming) + `/coordinator` (autonomy + command-hygiene). **Next S3: `.12` test → `.13` review → `.14` tech-writer → PR.** Lessons: file-checkout integration + 3-way only the shared yml; re-baseline sync to fixpoint after integration (#133); recompose WITHOUT `--force` (#132) + cp live→vendored.

## Slice status

| Slice | Beads | State |
|-------|-------|-------|
| S0 principle | .1 dev, .2 review | ✓ done (#20) |
| S1 test-decouple | .3, .4 | ✓ done (#21) |
| S2 repo + N+1 | .5, .6, .7, .8 | ✓ done (#22) |
| S3 graph decomp | .9–.14 | dev ✓ (.9/.10/.11 closed) · .12 test → .13 review → .14 tw → PR |
| S4 services/app decomp | .15–.21 | blocked → S3 |
| S5 cache + types | .22–.24 | blocked → S4 |

## Plan notes

- Governing principle: cohesion-driven design (one nameable responsibility/module; split monsters by responsibility; never over-split; `domain-size-limit` is a consequence not a driver). Codified in S0.
- Behavior-preserving: no CLI/MCP/gate-verdict/graph-semantics change; golden-output tests for #123/#124/#128; `beadloom ci` rc 0 per slice.
- One PR per slice (`features/BDL-059-sN`); S3/S4 are heavy (real decomposition of monster modules) and use worktree-isolated parallel dev + merge-slot.
- Generated `site/` gitignored — do NOT re-commit.

## Progress log

- 2026-06-15 — PRD/RFC/CONTEXT/PLAN approved (RFC v2 cohesion-driven after owner pushback on metric-gaming). Epic + 24 beads created (beadloom-fm3u.1–.24), DAG S0→S1→S2→S3→S4→S5. Starting S0.
- 2026-06-16 — S3 dev wave integrated (file-checkout + 3-way on services.yml; `.10` federation done inline after subagent bash-block). `.9/.10/.11` closed; 5 commits on `features/BDL-059-s3`. Owner decided domain-size-limit **recalibrate 200→280** (vs gaming); codified recalibration-vs-gaming in dev/review roles + autonomy/command-hygiene in `/coordinator`. ci rc0, lint 0 violations, 4375×3 seeds. Permissions: `dontAsk` + destructive deny-net + broad allow + `/tmp` dirs. Next: `.12` test.
