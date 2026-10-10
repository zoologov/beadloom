# ACTIVE: BDL-081 — Release 9.0.0

> **Last updated:** 2026-10-10
> **Phase:** Completed

---

## Current Bead

**Bead:** none — shipped. PR #99 (`ee9341c7`, 2026-10-10); Release `v9.0.0`; PyPI publish green; the harness on the downloaded wheel: 24 of 24 checks hold; the published portal carries the brand.
**Goal:** 9.0.0 published, verified on the downloaded wheel, documented by the measurement.
**Done when:** every PRD goal's *Done when* holds; the harness passes on the PyPI wheel; close-out by the template.

## Progress

- [x] PRD approved; RFC approved; CONTEXT and PLAN approved (delegated, 2026-10-10)
- [x] R1, R2 landed
- [x] D1, V1 landed
- [x] R passed
- [x] PR merged, Release v9.0.0, published, verified, close-out (2026-10-10)

## Results

| Bead | Role | Status | Note |
|---|---|---|---|
| `beadloom-qfk9` | R1 | ✓ done (commit `74cf3816`; 9.0.0 in 17 checked places; `[9.0.0]` Breaking ×5 verbatim by the measurement, Upgrading 7 steps; `ci` red only on D1's pairs and the README paragraph) | the bump; `[9.0.0]` Breaking first |
| `beadloom-ehts` | R2 | ✓ done | the leftover `other/` page retired on upgrade |
| `beadloom-d7qq` | D1 | ✓ done | the docs read |
| `beadloom-3iu5` | V1 | ✓ done (commit `55a3d2f0`; `languages` extra; site alias ×2, portal steiger/brand/footer, FSD init/preset/rules/lint, npm assets + lint:fsd; 8.0.0 → exit 4 with 10–12 new failures, the tree's wheel → 0 (25/25 with Node 22); SKIPPED status for npm checks without Node, named under the verdict) | the harness |
| `beadloom-g0a0` | R | ✓ done — REVIEW PASSED after the fix cycle (2 majors fixed at `e72fae07`; harness 25/25 on the tree's wheel; `ci` rc 0 on a fresh index) | review, bead id only |
| `beadloom-1ov1` | P | ✓ done (PR #99 merged `ee9341c7`; Release v9.0.0; pypi-publish 38076191181 green; harness on the PyPI wheel 24/24; portal published with the brand) | PR, release, publish, verify, close-out |

## Notes

- 2026-10-10: /task-init done; the measured diff in `axes.md`; the owner's eight rulings in PRD.md.
