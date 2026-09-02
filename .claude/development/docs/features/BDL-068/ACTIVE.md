# ACTIVE: BDL-068 — The flow's rules are advice; make them instruments

> **Last updated:** 2026-09-02
> **Phase:** Development

---

## Current Bead

**Bead:** none — `.1`, `.3`, `.2` and `.4` closed. `bd ready` lists `.6` (the commit-scope
check, unblocked by `.4`) and `.5` (the `Explore` role); they may run beside each other.

**The bead just closed.** `beadloom-0mdo.4` — `## Axes` as a required section, reported by
`doc-quality` when absent or empty
**Goal:** make the section a work item declares its axes in a requirement the flow enforces,
derived from the template that carries it rather than from a list in code.
**The premise did not hold, and that is the first thing this bead measured.**
`doc_templates.required_sections` derives over the `docs` artifact kind, whose kinds are graph
NODE documents; BRIEF and RFC have no template in that family at all, and `missing_sections` is
a sync-check reason over paired node documents rather than a `doc-quality` finding. So the
derivation was EXTENDED to the planning skeletons — fenced blocks inside the composed
`/templates` command — and `doc_shape`'s peer policy was extracted into one function used over
both corpora, rather than a second mechanism built beside either.

## Progress

- [x] PRD approved (2026-09-02)
- [x] RFC approved — six slices, three alternatives rejected with reasons
- [x] CONTEXT + PLAN approved — Q1, Q2, Q4, Q5 decided; Q3 left open with its decision rule
- [x] Beads created: epic `beadloom-0mdo`, nine S1 beads, five slice placeholders, DAG wired
- [x] S1.1 — the three derivations lifted into `application/source_derivation/` (dev)
- [x] S1.3 — the derivations validated against BDL-067 retroactively; the answer is partial
- [x] S1.2 — `beadloom impact`, seed derived and named, unresolved population as a field (dev)
- [x] S1.4 — `## Axes` required by the template that carries it; nine checks behind one
      composition; `beadloom axes` generates the bead `refs:` from the document (dev)
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
| `beadloom-0mdo.2` | Done | `beadloom impact <path\|symbol>` in `src/beadloom/application/impact/` (six modules by responsibility, a `feature` node with a SPEC) plus `services/commands/impact.py`, human and `--json`. The seed is DERIVED under the rule `reaches-an-effect-sink` — a name the target reaches transitively whose own body performs a declared effect directly — and the answer names the seed, the rule and the effect. Measured at `af26750d`, macOS, foreground, through `git archive` with no argument naming a commit point: `bootstrap.py` → seed `write_yaml_atomic`, co-writers 6 including `bootstrap_project` and `import_docs`; `setup.py` → 7 seeds including it and none of the first-hop names, `init` 4 branches, exits `{return, sys.exit(0)}`. A target no rule finds a sink for reports `co_writers.resolved = false` with the reason, never an empty list. Eight kinds in the unresolved population. 9 scenarios (red before the code existed) + 20 cases; every case demonstrated red by eight mutants — forward closure frozen at the first hop → 8, seeds taken from what reaches a sink → 12, an absent seed rendered as empty → 2, the population dropped → 7, the effect conjunction turned into a disjunction → 3, `ends_the_branch` reduced to `Return \| Raise` → 3, the boundary claiming an index it did not read → 2, `PUTS_BYTES_ON_DISK` added to the effect table → 2. Green on the tree, macOS: 7905 passed, `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. |
| `beadloom-0mdo.3` | Done | measured at `af26750d` (the parent of `acf4066`, 2026-08-31), macOS, foreground, the lifted package imported from `430d9ae` and pointed at a detached worktree. Seeded with the commit point `write_yaml_atomic` the derivations list 2 writers (`bootstrap_project`, `import_docs`) and 4 branches of `init`; seeded with `bootstrap_project`, the function that bead was changing, they list 0 writers and 3 branches — the number the epic carried throughout. Both facts were in reach on the day and neither is reached from the function under change, so the premise survives as a conditional and the condition is now S1.2's hardest criterion. Second measurement: the seed is derivable from the target under `SERIALISES_YAML` (2 candidates from `bootstrap.py`) and unreachable under `PUTS_BYTES_ON_DISK`, which does not contain the commit point at all. Kept as 8 cases in `tests/test_the_seed_decides_what_impact_reports.py`, each demonstrated red. |
| `beadloom-0mdo.4` | Done | `## Axes` in the BRIEF and RFC skeletons, required by the same act that adds it: `required_sections_by_document_kind` runs `doc_templates`' own heading extraction over the composed `/templates` command's fenced blocks. `doc_shape`'s peer-majority policy extracted into `peer_section_shape` and used over both corpora; `check_planning_sections` reports `missing-section` (peer-relative) and `empty-section` (not). `doc_sync/axes_section.py` holds the section's grammar — `axes-without-a-seed`, `axis-without-a-scope-decision` — and `application/impact/section.py` renders one from an `ImpactAnswer` using that grammar, so the writer and the reader are one shape. `application/planning_report.py` is now the ONE composition of all nine checks behind the gate step and `beadloom docs quality`. New CLI: `beadloom impact --section` and `beadloom axes <document> [--refs]`. Measured on this repository, foreground, no pipe: `missing-section` 102 over 256 read, `empty-section` 0 over 256, 17 kind-level conventions including `BRIEF Axes (0/12)` and `RFC Axes (0/48)`; the 767 findings a non-peer-relative policy would give is why the peer one was chosen. `empty-section` was 155 until a defect the run exposed — a section whose content lives in its subsections read as empty — was fixed by propagating content up the heading depth. 9 scenarios + 29 cases, every case demonstrated red by eleven mutants. Green on the tree, macOS: 7944 passed (baseline 7905), `ruff` and `mypy --strict` clean, `beadloom ci` rc 0. Green in a clean room over 33 files, with the pre-existing sync-baseline failure reproduced at HEAD alone. |
| `beadloom-0mdo.5` | Pending | blocked by `.2` — the `Explore` role |
| `beadloom-0mdo.6` | Pending | unblocked by `.4` — the commit-scope check. It reads the WORK ITEM's declared axes through `beadloom.doc_sync.axes_section.read_axes_section`; the grammar and the `refs:` generation are in place |
| `beadloom-0mdo.7` | Pending | blocked by `.3`, `.5`, `.6` — test |
| `beadloom-0mdo.8` | Pending | blocked by `.7` — review |
| `beadloom-0mdo.9` | Pending | blocked by `.8` — tech-writer |
| `beadloom-0mdo.10` .. `.14` | Pending | S2–S6, ordered by dependency; their beads are created when the preceding slice's review closes |

## Notes

**Handed up by `.4`, not fixed by it.** Requiring the planning templates' sections reports
**102** documents on this repository's archive: old RFCs with no `## Overview`, old PRDs with
no `## Impact`. Every one is a true departure from the shape its peers keep, every check is
`warn`, and the Gate stays rc 0 on them. Whether the archive is revised or the corpus is scoped
by `doc_quality.paths` is an owner's decision rather than a dev bead's, and it is stated here so
the number is not discovered later as a surprise.

**The two axes checks read 0 documents today**, and the Gate says so rather than reporting them
clean (`NOT CHECKED: axes-without-a-seed, axis-without-a-scope-decision`). No planning document
in this repository carries an `## Axes` section yet. BDL-068's own RFC deliberately does NOT get
one from this bead: an epic is not an `impact` target, its axes span six slices and several
runs, and a guessed table is exactly what `.6` would then measure every commit against.


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

**Why the seed rule is stated over two effects and not three.** `serialises-yaml` and
`reads-a-yaml-directory` are declared; `PUTS_BYTES_ON_DISK` is deliberately excluded, and the
exclusion is a check rather than a comment. Beyond `.3`'s finding that it does not contain this
product's own commit point, it is not a sound predicate ALONE, because `open` also READS —
measured at `af26750d` it gives `bootstrap.py` four seeds none of which is the commit point,
and `setup.py` nineteen seeds and 65 co-writers, most of them readers. `.1` handed its
narrowing to `.7` and nothing in `impact` is built on top of it. The synthetic tree in
`tests/test_impact_derives_the_seed_it_answers_from.py` reproduces the finding in miniature —
its sink writes through `os.fdopen(...).write` and `Path.replace`, exactly as
`write_yaml_atomic` does — so that case runs on every leg rather than only where the history is
in the checkout.

**Still open, and still nobody's bead.** BDL-068's RFC carries Q1–Q5 as `Pending` while CONTEXT
records four of them as decided, and the Gate warns `pending-in-approved` on all five. `.3`
raised it and `.2` did not repair it either: two documents disagreeing about whether a decision
was taken is this epic's own class, inside this epic, and which document wins is the
coordinator's call rather than a dev bead's.

**Branch.** `features/BDL-068`. PR #58 landed on `main` as `a4738b7`, so the three lifted
derivations are no longer stacked on an open branch.
