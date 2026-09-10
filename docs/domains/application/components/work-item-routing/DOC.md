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
| the types and their flows | the rows of every table whose own header row leads with `Type` and `Flow` |
| the documents each type writes | the row's third cell, as the upper-case names it lists |
| the step that derives the axes | the first `##`/`###` heading whose body launches `subagent_type: explore` |
| the line the type decision is taken on | the first routing table's header line |

## Where a routing table starts and stops

A routing table is a **table** whose own **header row** names the routing columns, and it ends
where its rows stop. Both halves are read through `doc-sync`'s `markdown-tables` component,
which is the one place in this project that decides where a markdown table begins.

This reader is the third of that boundary. BDL-UX #213 (`doc-quality`) and #244
(`axes-section`) were one sentence found hours apart in one slice — a section holding two
tables read as one — and BDL-UX #259 is the same sentence here. It fired no instance, because
the reader discarded a row whose second cell named neither `simplified` nor `full`, and that
vocabulary guard is what #213 measured as insufficient. Measured over this repository: of 5 122
table rows in 456 markdown files, the guard admits 27, and 17 of the 27 belong to other tables
in other documents.

A document states **more than one** routing table when its project layer adds one, so the
routes are the union of them all with each table's rows judged against its own header — the
rule `axes-section` already follows for a section that holds one table per slice. The line the
type decision is taken on is the first of them.

`Routing.shared_kinds` is the third face of the same computation: the document kinds **every**
route writes, taken as an intersection. On this project it answers `ACTIVE`, and `beadloom
waves` spends it — a document no route can avoid is one every bead of a work item writes and no
bead's code owns, which is the shared medium BDL-UX #257 named. An empty routing answers the
empty set rather than the vacuous intersection over nothing.

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

A **row a routing table states and this derivation cannot read as a route** — one naming
neither flow, or one too narrow to state a document set — is named in `notes` with its line
number rather than dropped. The omission is the worse of the two failure directions: the type's
document kinds leave `Routing.simplified_kinds`, so every work item of that type falls out of
the population `check_work_item_types` judges and the report reads as a clean run over a
smaller corpus.

## Interfaces

| Name | Purpose |
|------|---------|
| `task_init_routing(*, config, project_root)` | The routing this project's composed `/task-init` declares |
| `read_routing(text)` | The same derivation over an already-composed text |
| `Routing` | The routes, the two line numbers and the notes |
| `Routing.shared_kinds` | The document kinds every route writes — what `beadloom waves` reads as its focus document |
| `Route` | One row: a type, its flow and the documents it writes |
| `SIMPLIFIED` / `FULL` | The two flow labels a cell is reduced to |
| `AXES_ROLE` | The role whose deliverable the type decision is made from |

## Tests

- `tests/acceptance/features/work_item_type.feature` — the scenarios.
- `tests/acceptance/features/work_item_routing.feature` — the table boundary's scenarios.
- `tests/test_the_explore_role_is_composed_like_the_others.py` — the cases.
- `tests/test_the_routing_table_is_one_table.py` — the boundary, and the regression set that
  states no route this reader reads today disappears.
