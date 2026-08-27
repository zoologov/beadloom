# Node Intent (component)

Internal building block of the context-oracle domain.

**Source:** `src/beadloom/context_oracle/intent.py`

---

## Overview

Decides which recorded intent a node's context bundle carries.
`beadloom ctx <ref-id>` is step 4 of BEFORE ANY WORK, so it is the one moment an
agent is guaranteed to ask about a node; until this component existed it was
answered
with reality alone — the node's AS-IS documentation, its symbols, its edges —
and never with the reason the code is there.

The component is pure policy: it takes a reading of the TO-BE space and the
focus ref ids, and returns the `intent` section of the bundle. It opens no file
and runs no query, which is why it can live in the domain while the adapter that
reads the space lives one layer up in `application/intent_reader.py`.

## Which intent belongs to a node

The epics that **declared** it, and nothing else. `beadloom-mr2l.17` measured the
alternative before building the join this component reads: scanning an epic's
documents for backticked tokens that happen to be ref ids attributed the node
`status` to nine epics whose prose merely used the English word. The *Related
Files* section is a declaration, so it is what is read.

Only the **focus** ref ids are looked up. A bundle's traversal reaches up to
twenty nodes and the question was asked about one or two of them; looking up the
whole subgraph would spend the budget on nodes nobody named.

## Three answers, and why two of them are not one

| `status` | What it means |
|---|---|
| `declared` | At least one epic's declaration names this node. The epics are listed. |
| `none_declared` | The TO-BE space was read and nothing in it declares this node. |
| `not_checked` | Nobody read the space, or there was nothing in it to read. `reason` says which. |

`none_declared` is the common case — this repository holds 84 nodes and only
fifteen of them are declared by any epic — so it carries `epics_read` and
`epics_declaring_nodes`. That turns it from a claim into a measurement: an empty
answer over 62 epics and an empty answer over none are the same sentence about
two different worlds. The epic count moves whenever a planning directory is
added, which is why the answer carries it instead of the reader assuming one.

Collapsing `none_declared` into `not_checked` would re-earn what this epic spent
two slices on (BDL-UX #174, #175). An absence with a stated reason is a decision;
an absence without one is a gap; neither is evidence that no intent exists.

The four reasons are `intent_space_not_read` (the caller opted out, or the
caller has no project root to read from), `no_intent_documents` (the TO-BE space
is empty), `no_epic_declares_any_node` (documents were read and not one declares
anything — the same vacuity `SpacesReport.relation_checked` reports) and
`doc_roots_config_error` (the configuration did not resolve, so an empty read
would not be an honest answer).

## The cap, and why nothing is dropped by it

A node can be named by many epics over years, and a bundle has a budget it
exists to respect. At most `MAX_DECLARATIONS` (5) declarations carry their
document and line; the rest keep their names in `also_declared_by`. A cap that
truncated silently would be the same defect at a smaller scale.

Order is descending **natural** key — digit runs compare numerically, so
`ORD-31` sorts above `ORD-4` where plain string order puts it below. A tracker
allocates numbers in sequence, so the highest-numbered epic is usually the most
recent statement of intent. It is a heuristic, it is stated as one, and it is
the other reason the truncated epics keep their names.

## What is deliberately not here

The bundle **points** at the intent document and its line; it does not paste the
intent. A `ctx` bundle on this repository is already ~157 KB, and inlining a PRD
would spend the budget the pointer costs 90 bytes to avoid.

No bead status is claimed. `bd close` writes only the local database, so the
committed tracker export and the live tracker disagree on a branch, and a status
shown here would be confidently wrong exactly where the work is happening.

## Related

- `docs/domains/application/components/intent-reader/DOC.md` — the adapter.
- `docs/domains/application/components/doc-spaces/DOC.md` — the declaration join.
- `docs/domains/context-oracle/components/context-builder/DOC.md` — the bundle.
