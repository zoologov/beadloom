# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-02
> **Phase:** Development

---

## Current Bead

**Bead:** none — `.1` and `.3` closed; `.2` (`beadloom impact`) is unblocked and runs against
the acceptance `.3` rewrote.

**The bead just closed.** `beadloom-0mdo.3` — validate the derivations against BDL-067
retroactively, before anything consumes them
**Goal:** answer, from a measurement rather than from an argument, whether the lifted
derivations would have listed both writers of graph nodes and four entry points of `init` on
the tree BDL-067's first dev bead started from.
**The answer: partial, and the partial half is the seed.** Recorded in PLAN.md under S1.3 with
the commit, the room and the command; S1.2's acceptance rewritten before `.2` starts.

## Progress

- [x] PRD approved (2026-09-02)
- [x] RFC approved — six slices, three alternatives rejected with reasons
- [x] CONTEXT + PLAN approved — Q1, Q2, Q4, Q5 decided; Q3 left open with its decision rule
- [x] Beads created: epic `beadloom-0mdo`, nine S1 beads, five slice placeholders, DAG wired
- [x] S1.1 — the three derivations lifted into `application/source_derivation/` (dev)
- [x] S1.3 — the derivations validated against BDL-067 retroactively; the answer is partial
- [ ] S1 — `impact` + `## Axes` + `Explore`
- [ ] S2 — the review's independence
- [ ] S3 — what we measure with
- [ ] S4 — the guards' surface
- [ ] S5 — the tracker adapters
- [ ] S6 — the flow's documents and roles

## Results

| Bead | Status | Details |
|------|--------|---------|
| `beadloom-0mdo.1` | Done | the three derivations lifted into `src/beadloom/application/source_derivation/` (six modules by responsibility, a `component` node with a DOC). The tests keep their assertions and supply the seeds; measured with `git diff --numstat`, the five affected test modules shrink by 329 lines net (466 deleted, 137 added) and the package is 716 lines. Each lifted shape is demonstrated capable of failing by mutating it and running the suite: reader verbs narrowed → 5 red, the call vocabulary narrowed to attribute calls → 1 red, the writer payload half removed → 4 red, the reachability fixpoint frozen → 13 red, the terminator reduced to `Return \| Raise` → 2 red, the bypass sweep made blind → 1 red. One derivation REFUSED and reported: the prose sibling-reference scanner, which passes 27/27 with its finding computation replaced by `[]`. Green on the tree, macOS: 7867 passed, `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.2` | Pending | blocked by `.1` — `beadloom impact` |
| `beadloom-0mdo.3` | Done | measured at `af26750d` (the parent of `acf4066`, 2026-08-31), macOS, foreground, the lifted package imported from `430d9ae` and pointed at a detached worktree. Seeded with the commit point `write_yaml_atomic` the derivations list 2 writers (`bootstrap_project`, `import_docs`) and 4 branches of `init`; seeded with `bootstrap_project`, the function that bead was changing, they list 0 writers and 3 branches — the number the epic carried throughout. Both facts were in reach on the day and neither is reached from the function under change, so the premise survives as a conditional and the condition is now S1.2's hardest criterion. Second measurement: the seed is derivable from the target under `SERIALISES_YAML` (2 candidates from `bootstrap.py`) and unreachable under `PUTS_BYTES_ON_DISK`, which does not contain the commit point at all. Kept as 8 cases in `tests/test_the_seed_decides_what_impact_reports.py`, each demonstrated red. |
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

**The bead that could invalidate the epic's premise, and partly did.** `.3` ran the lifted
derivations against the tree as it stood at BDL-067's first dev bead. Both facts the epic
claims an axes artifact would have surfaced are inside the derivations' reach on that tree —
and only under a seed BDL-067 did not choose until its own fifteenth bead. Seeded from the
function the first dev bead was changing, the same derivations report three branches and no
writers, confidently and cleanly. So the premise holds as a conditional, the condition is seed
derivation, and `.2`'s acceptance was rewritten to make it the load-bearing criterion rather
than an implementation detail. The measurement was not softened into a pass and the derivation
was not repaired to make it come out yes; a repair would have measured the repair.

**A second measurement `.3` did not go looking for.** `PUTS_BYTES_ON_DISK` — the lifted
shape for *this body puts bytes on disk* — does not contain `write_yaml_atomic`, the product's
own single commit point, because that function writes through `os.fdopen(...).write` and
`Path.replace` while the shape spells `write_text`, `write_bytes` and `open`. A shape stated
over three spellings walking past the thing it exists to protect is this epic's own defect
class, found inside this epic's own instrument. Left unrepaired on purpose and handed to `.7`,
which already owns the other half of the same gap.

**Three counts this epic's own planning commit broke.** `409e977` added four planning
documents and a PRD carrying fourteen scenario references, and left three hand-maintained
literals in the suite at their BDL-067 values: TO-BE documents (199), scenario references in
PRD/BRIEF (36) and WORKING documents (57). The branch was Gate-green and suite-red at the same
time for that whole interval, because `beadloom ci` does not run pytest. Corrected in `.1`
with the reason recorded beside each literal; the class is `mr2l.72` and S6 owns it.

**Branch.** `features/BDL-068`. PR #58 landed on `main` as `a4738b7`, so the three lifted
derivations are no longer stacked on an open branch.
