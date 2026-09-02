# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-02
> **Phase:** Development

---

## Current Bead

**Bead:** `beadloom-0mdo.1` — lift the three AST derivations out of `tests/` into a production package
**Goal:** the derivations that answer *who else writes this, who else calls this, how many
branches does this have* become importable by production code, without weakening the tests
that currently hold them.
**Done when:** no derivation logic remains in `tests/`; each test still fails on the shape it
was written to catch, verified against the evasion spellings those modules already carry; a
derivation with no test that fails on a fifth body is reported rather than lifted.

## Progress

- [x] PRD approved (2026-09-02)
- [x] RFC approved — six slices, three alternatives rejected with reasons
- [x] CONTEXT + PLAN approved — Q1, Q2, Q4, Q5 decided; Q3 left open with its decision rule
- [x] Beads created: epic `beadloom-0mdo`, nine S1 beads, five slice placeholders, DAG wired
- [ ] S1 — `impact` + `## Axes` + `Explore`
- [ ] S2 — the review's independence
- [ ] S3 — what we measure with
- [ ] S4 — the guards' surface
- [ ] S5 — the tracker adapters
- [ ] S6 — the flow's documents and roles

## Results

| Bead | Status | Details |
|------|--------|---------|
| `beadloom-0mdo.1` | Pending | S1 dev — lift the derivations |
| `beadloom-0mdo.2` | Pending | blocked by `.1` — `beadloom impact` |
| `beadloom-0mdo.3` | Pending | blocked by `.1` — retroactive validation against BDL-067 |
| `beadloom-0mdo.4` | Pending | blocked by `.2` — `## Axes` required section |
| `beadloom-0mdo.5` | Pending | blocked by `.2` — the `Explore` role |
| `beadloom-0mdo.6` | Pending | blocked by `.4` — the commit-scope check |
| `beadloom-0mdo.7` | Pending | blocked by `.3`, `.5`, `.6` — test |
| `beadloom-0mdo.8` | Pending | blocked by `.7` — review |
| `beadloom-0mdo.9` | Pending | blocked by `.8` — tech-writer |
| `beadloom-0mdo.10` .. `.14` | Pending | S2–S6, ordered by dependency; their beads are created when the preceding slice's review closes |

## Notes

**The structural decision this epic is run under.** Beads are created per slice, not for the
epic. Writing 24 beads now would mean writing 20 of them before the first slice has taught
anything — which is the plan BDL-067 wrote blind, five times larger. The re-plan rule is
expressed as structure rather than as discipline.

**The decisions taken at planning, so they are not re-litigated per bead.**

- Q1 — the axes are DERIVED by `beadloom impact`; the document records the derivation's output
  and the human's scope decision; the bead's `refs:` is generated from the document. A
  disagreement between the three is a finding. One computation, two renderings, one check.
- Q2 — the commit-scope check compares against the WORK ITEM's axes, not the bead's. A bead may
  narrow freely inside what the human approved; leaving the work item's axes is the re-plan
  trigger.
- Q4 — External `bd` findings are answered by deriving our own call sites, not by a wrapper.
- Q5 — `Explore` is a role file composed by `role-composer`, not a mode. A mode has no protocol
  file, and that is why the one `Explore` run in BDL-067 returned a trace of the defect and
  nothing about axes.
- Q3 stays open with its decision rule stated: the mutation job runs per PR if it fits under
  the budget that withdrew `tests-windows`, nightly otherwise — measured in S3 before the job
  is added.

**The one bead that can invalidate the epic's premise, on purpose.** `.3` runs the lifted
derivations against the tree as it stood at BDL-067's first dev bead and asks whether they
would have listed both graph writers and four entry points of `init`. The answer is recorded
whichever way it comes out, and a *no* rewrites `.2`'s acceptance before any later slice
consumes it.

**Branch.** `features/BDL-068` is stacked on `features/BDL-067`, because S1 lifts three
derivations that exist only there. PR #58 is open, green and unmerged; this branch is rebased
onto `main` once it lands.
