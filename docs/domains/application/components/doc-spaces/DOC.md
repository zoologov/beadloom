# Doc Spaces (component)

Internal building block of the application domain.

**Source:** `src/beadloom/application/doc_spaces.py`

---

## Overview

Makes the claim *"the intent recorded in TO-BE is reflected in AS-IS"* checkable.
It is a relation between two artifacts rather than a flag on one: nothing here
marks a planning document "done", because that document stays the record of what
was intended and a different document is what gets updated.

It lives in `application` because the answer joins three readers no single domain
owns — the graph (which nodes exist and which have documentation), the tracker
(which beads closed) and the space vocabulary in `infrastructure/doc_roots.py`.

## The join, and why it is a declaration

An epic's `CONTEXT.md` (or a task's `BRIEF.md`) carries a *Related Files* section
naming the graph nodes the work touches. The relation is read from that section
and from nothing else.

Scanning a whole document for backticked tokens that happen to be ref ids was
measured first and rejected: on this repository it attributed the node `status`
to nine epics whose documents merely used the English word. That is the
false-positive class BDL-UX #169 and #190 already record against the audit
scanner.

An epic that declares no node is therefore **unresolved** — counted in its own
bucket and reported, never silently counted as clean. So is an epic whose
planning document carries no *Related Files* heading at all. Filtering those
out was the first implementation: on this repository it removed 34 of 57 epics
from the denominator and the report then read *16 of 23*, which looks like
coverage of two thirds where the real figure is under a third.

## What is checked, and what is not

One leg: an epic with at least one closed bead that declares node *X*, where *X*
has no AS-IS document at all. Intent was recorded, the work finished, and reality
was never written down.

There is deliberately no second leg on staleness. `sync-check` already holds
every AS-IS document against its code and names the stale ones; a second check
saying the same thing from another angle would double one finding.

The WORKING declaration is audited two ways, neither inferred from an absence:

- `working_exemption_inert` — declared kinds that no document uses, so the
  exemption excused nothing.
- `working_declaration_contradicted` — the graph declares a WORKING document as
  a node's documentation, so one artifact says it describes the code while
  another says it must not be held against it.

## Public surface

- `check_spaces(project_root, *, spaces, known_refs, documented_refs, declared_doc_paths, beads_by_epic)`
  — the pure core. Every graph and tracker fact arrives as an argument, so the
  relation can be exercised against a project that is not this one.
- `spaces_report(conn, project_root, *, beads)` — the same over a live index.
- `graph_facts(conn)` — `(known_refs, documented_refs, declared_doc_paths)`.
- `beads_by_epic(records)` — group tracker records by the epic key their title
  names.
- `read_epic_intents(...)`, `EpicIntent`, `SpaceFinding`, `SpacesReport`.
- `FINDING_NO_AS_IS`, `FINDING_WORKING_CONTRADICTED`, `FINDING_WORKING_INERT`,
  `FINDING_CONFIG`.

`SpacesReport.relation_checked` is false when nothing was related. A relation
check over an empty population reports nothing and reads exactly like one that
found no problem, so the report says which of the two it is.

## Collaborators

- `services/commands/docs.py` — `beadloom docs spaces`.
- `application/gate.py` — the `doc-spaces` step, which reports and never blocks.
- `services/bd_seam.py` supplies the tracker records the service layer converts
  with `beads_by_epic`.

> Component doc (BDL-061 S5). Public surface verified against `doc_spaces.py`.
