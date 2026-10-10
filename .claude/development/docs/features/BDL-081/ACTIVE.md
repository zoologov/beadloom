# ACTIVE: BDL-081 — Release 9.0.0

> **Last updated:** 2026-10-10
> **Phase:** Development

---

## Current Bead

**Bead:** R `beadloom-g0a0` reviewing on its own worktree of `60351530`; D1's follow-up landed `60351530`; V1 landed `55a3d2f0`, D1 `66980c74`; R1 landed `74cf3816`, R2 `74b0e509`. Then R; P.
**Goal:** 9.0.0 published, verified on the downloaded wheel, documented by the measurement.
**Done when:** every PRD goal's *Done when* holds; the harness passes on the PyPI wheel; close-out by the template.

## Progress

- [x] PRD approved; RFC approved; CONTEXT and PLAN approved (delegated, 2026-10-10)
- [x] R1, R2 landed
- [x] D1, V1 landed
- [ ] R passed
- [ ] PR merged, Release v9.0.0, published, verified, close-out

## Results

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-qfk9` | R1 | ✓ done (commit `74cf3816`; 9.0.0 in 17 checked places; `[9.0.0]` Breaking ×5 verbatim by the measurement, Upgrading 7 steps; `ci` red only on D1's pairs and the README paragraph) | the bump; `[9.0.0]` Breaking first |
| `beadloom-ehts` | R2 | ✓ done | the leftover `other/` page retired on upgrade |
| `beadloom-d7qq` | D1 | ✓ done | the docs read |
| `beadloom-3iu5` | V1 | ✓ done (commit `55a3d2f0`; `languages` extra; site alias ×2, portal steiger/brand/footer, FSD init/preset/rules/lint, npm assets + lint:fsd; 8.0.0 → exit 4 with 10–12 new failures, the tree's wheel → 0 (25/25 with Node 22); SKIPPED status for npm checks without Node, named under the verdict) | the harness |
| `beadloom-g0a0` | R | in progress | review, bead id only |
| `beadloom-1ov1` | P | blocked | PR, release, publish, verify, close-out |

## Notes

- 2026-10-10: /task-init done; the measured diff in `axes.md`; the owner's eight rulings in PRD.md.
