# Work Item Type

The route a work item took, checked against the axes it was decided from: no axes on the
route that skips scope approval, and kept axes naming more nodes than that route holds.

**Source:** `src/beadloom/doc_sync/work_item_type.py`

---

## Specification

### Purpose

A work item's type is a claim about how far the change ranges. Until BDL-068 S1.5 the claim
was never checked: BDL-067 was routed `bug`, wrote one BRIEF, passed one approval gate and
became 28 beads, and re-deriving its axes afterwards showed the change ranging over four
graph nodes.

Two checks answer two questions about the route, and both take the WORK ITEM — a folder of
planning documents — as their unit, because a type is a property of the item and not of any
one document it holds.

| Check | Fires when |
|-------|-----------|
| `routed-without-axes` | a work item on the simplified route carries no `## Axes` section in any of its documents |
| `route-not-supported-by-the-axes` | a work item on the simplified route keeps axes naming more than one graph node |

### Why this is not `missing-section` a second time

Measured on this repository at `2a5c0d1`, `beadloom docs quality` reported `BRIEF documents
do not carry Axes (0/12)` and `RFC documents do not carry Axes (0/48)`. BDL-068 S1.4's
`missing-section` is peer-relative by design, so a section **no** peer keeps produces one
kind-level statement and zero document-level findings. `## Axes` was required by the template
and reported by nothing.

That policy is right for a convention an archive never adopted and wrong for the input to a
decision, so `routed-without-axes` is absolute. To keep one fault to one reporter, the
simplified route's `Axes` requirement is withdrawn from the peer-relative half of
`check_planning_sections` through its `absence_reported_elsewhere` argument. The requirement
itself stays, so a heading present with nothing under it is still `empty-section`'s finding —
withdrawing the requirement would have removed the emptiness check with it, which is a
coverage loss rather than a de-duplication.

### Why only the simplified route

The full route writes a PRD and an RFC and each passes an approval gate, so a mis-route meets
a person. The simplified route writes one BRIEF and passes one gate, on work that has already
been scoped. It is the route BDL-067 took.

### Why one node

`NODES_THE_SIMPLIFIED_ROUTE_HOLDS` is `1`, and the number is a property of the route's
documents rather than a threshold chosen for how many findings it produces: the route writes
one BRIEF and no RFC, so a change ranging over two nodes has no document in that route that
records the crossing. `beadloom impact src/beadloom/onboarding/scanner/bootstrap.py
--section` — BDL-067's own target — keeps rows naming four nodes.

### What decides the route

Nothing here. `simplified_kinds` arrives as an argument, derived from the composed
`/task-init` command by `beadloom.application.work_item_routing`, because `doc_sync` is a
peer domain of `onboarding` and may not import a template. An empty set means the routing
could not be derived: `_collect` keeps a folder only when one of its documents identifies the
route, so an empty set leaves an empty population and the report states zero rather than a clean
run over one. There is no early return for that case — one was written and a mutant showed it
could not be made to fail, so it was deleted.

### Population, reported separately

`WorkItemTypeReport.work_items` counts folders, not documents. The document count every other
planning check reports would overstate this population by however many documents a work item
carries, and `planning_report` publishes the folder count for these two checks alone.

## Interfaces

| Name | Purpose |
|------|---------|
| `check_work_item_types(documents, *, simplified_kinds)` | The two checks over `(path, text)` pairs |
| `WorkItemTypeReport` | `findings` and the `work_items` population entered |
| `WorkItem` | One folder: its key, the document that identifies its route, its kinds and its axes |
| `CHECK_NAMES` | The two check names, in report order |
| `NODES_THE_SIMPLIFIED_ROUTE_HOLDS` | How many nodes the simplified route can hold, with its reason |

## Tests

- `tests/acceptance/features/work_item_type.feature` — the scenarios.
- `tests/test_the_explore_role_is_composed_like_the_others.py` — the cases.
