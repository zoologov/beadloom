# Planning Report (component)

One composition of every check that reads a planning document.

**Source:** `src/beadloom/application/planning_report.py`

---

## Overview

Before BDL-068 S1.4 the `docs-quality` gate step and the `beadloom docs quality` command each
assembled the run themselves: find the documents, derive the placeholder vocabulary, call the
checks. Two assemblies of one report can disagree about what was checked, and BDL-068 exists to
remove that class of defect. The assembly now lives here, once, and both surfaces render what
it returns.

Three families of check read the same corpus and answer different questions:

| Family | Module | Checks |
|--------|--------|--------|
| Writing standard | `doc_sync.doc_quality` | `measurable-goal`, `decision-reason`, `risk-mitigation`, `pending-in-approved`, `unfilled-placeholder` |
| Structure | `doc_sync.doc_shape` | `missing-section`, `empty-section` |
| Axes | `doc_sync.axes_section` | `axes-without-a-seed`, `axis-without-a-scope-decision` |

The section requirements the structural checks are held to are **derived** from the composed
`/templates` command, so a project that appends a section to its own template layer makes it
required by the same act and tells nothing else.

## Public surface

- `CHECK_NAMES` — every check, in report order. One list, so a summary counting findings per
  check cannot silently omit a family.
- `planning_report(paths, project_root=...)` — run everything over *paths*.
- `PlanningReport` — `quality`, `structure`, `axes`, `axes_read`, and the derived `findings`,
  `applicable` and `checks_that_read_nothing`.

`applicable` is stated for all nine checks rather than for the five that already had it,
because a check reported as `0 finding(s)` over a population of zero has verified nothing and
must not read as a pass. On this repository the two axes checks read **0** documents today, and
the Gate says so — `NOT CHECKED: axes-without-a-seed, axis-without-a-scope-decision` — because
no planning document carries an `## Axes` section yet.

## What it deliberately does not merge

`quality` and `structure` are kept apart rather than collapsed into one count. `quality` carries
the applicability the writing checks report and the documents nobody could decode; `structure`
carries the conventions and the document kinds no template describes. A single number over both
would say "clean" about populations neither entered — the equation BDL-UX #173, #174 and #175
all turn on.

## The double read, stated

The texts are read here for the structural checks and again inside `check_documents`, which owns
the decode-failure reporting. A document nobody could read is *unverified* and says so there;
duplicating that judgement to save one read would be a second answer to one question.
