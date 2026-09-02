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

Four families of check read the same corpus and answer different questions:

| Family | Module | Checks |
|--------|--------|--------|
| Writing standard | `doc_sync.doc_quality` | `measurable-goal`, `decision-reason`, `risk-mitigation`, `pending-in-approved`, `unfilled-placeholder` |
| Structure | `doc_sync.doc_shape` | `missing-section`, `empty-section` |
| Axes | `doc_sync.axes_section` | `axes-without-a-seed`, `axis-without-a-scope-decision` |
| Route | `doc_sync.work_item_type` | `routed-without-axes`, `route-not-supported-by-the-axes` |

The section requirements the structural checks are held to are **derived** from the composed
`/templates` command, so a project that appends a section to its own template layer makes it
required by the same act and tells nothing else. The routes the route checks judge are derived
from the composed `/task-init` command by `application.work_item_routing`, for the same reason.

## Public surface

- `CHECK_NAMES` — every check, in report order. One list, so a summary counting findings per
  check cannot silently omit a family.
- `planning_report(paths, project_root=...)` — run everything over *paths*.
- `PlanningReport` — `quality`, `structure`, `routes`, `axes`, `axes_read`, and the derived
  `findings`, `applicable` and `checks_that_read_nothing`.

`applicable` is stated for all eleven checks rather than for the five that already had it,
because a check reported as `0 finding(s)` over a population of zero has verified nothing and
must not read as a pass. On this repository the two axes checks read **0** documents today, and
the Gate says so — `NOT CHECKED: axes-without-a-seed, axis-without-a-scope-decision` — because
no planning document carries an `## Axes` section yet.

The two ROUTE checks report a different population from every other check here: their unit is
the work-item FOLDER, so `applicable` carries `routes.work_items` for them. The document count
would overstate it by however many documents a work item holds. Measured on this repository:
`routed-without-axes` 12 findings over 12 work items, `route-not-supported-by-the-axes` 0 over
the same 12 — the second cannot fire until a work item carries axes, and it is verified red on
a fixture instead.

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
