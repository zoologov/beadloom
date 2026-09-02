# Work Item Routing

The work-item types, their flows and the documents each writes, derived from the composed
`/task-init` command.

**Source:** `src/beadloom/application/work_item_routing.py`

---

## Overview

`/task-init`'s routing table decides which documents a work item writes and which approval
gates it passes. This module reads that table out of the **composed** command rather than
restating it in Python, so a project layer that adds a type or moves one between flows
changes the check by the same act, and the command cannot state a route the check does not
police.

The join lives in `application` for the reason `doc-shape-requirements` states: the composed
command lives in `onboarding`, the check that reads a document lives in `doc_sync`, the two
are peer domains and neither may import the other.

## What is derived

| Fact | Read from |
|------|-----------|
| the types and their flows | the routing table's rows — a header whose first two columns are `Type` and `Flow` |
| the documents each type writes | the row's third cell, as the upper-case names it lists |
| the step that derives the axes | the first `##`/`###` heading whose body launches `subagent_type: explore` |
| the line the type decision is taken on | the routing table's header line |

`Routing.simplified_kinds` and `Routing.full_kinds` are the document kinds written by **only**
one route. A kind both routes write — `ACTIVE` — identifies neither and is in neither set,
which leaves exactly the evidence a check over a folder of documents has.

`Routing.explore_precedes_the_decision` is what makes "the type decision cannot be reached
without the explore step having run" checkable on the artifact rather than asserted about it.

## Honest skips

`Routing.notes` carries what the derivation could not do, the way `Composition.notes` does. A
command with no routing table, a command that launches no `explore` subagent, a role
population that ships no `explore` fragment, and a `flow.yml` that will not compose each
produce a note instead of an empty routing that would read as "no types are declared".

## Interfaces

| Name | Purpose |
|------|---------|
| `task_init_routing(*, config, project_root)` | The routing this project's composed `/task-init` declares |
| `read_routing(text)` | The same derivation over an already-composed text |
| `Routing` | The routes, the two line numbers and the notes |
| `Route` | One row: a type, its flow and the documents it writes |
| `SIMPLIFIED` / `FULL` | The two flow labels a cell is reduced to |
| `AXES_ROLE` | The role whose deliverable the type decision is made from |

## Tests

- `tests/acceptance/features/work_item_type.feature` — the scenarios.
- `tests/test_the_explore_role_is_composed_like_the_others.py` — the cases.
