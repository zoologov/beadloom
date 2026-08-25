# Intent Reader (component)

Internal building block of the application domain.

**Source:** `src/beadloom/application/intent_reader.py`

---

## Overview

Reads the TO-BE space's node declarations into the shape a context bundle
consumes. It is the adapter half of the intent `beadloom ctx` delivers; the
policy half is `context_oracle/intent.py`.

The join is not re-implemented here. `application/doc_spaces.py` already reads an
epic's *Related Files* declaration, was measured against the unscoped
alternative and rejected it, and stays the one reader of that section. This
component turns its per-epic answer into the per-node one a bundle needs, and
adds nothing to what it read.

## Why the split falls where it does

`context_oracle` is a domain and `application` is the layer above it, so a domain
reaching up for this read would be the wrong direction. The port types —
`IntentReading` and `DeclaredIntent` — are declared in the domain and the adapter
that fills them lives here, which is the direction `architecture-layers`
enforces and the same shape `infrastructure/doc_roots.py` uses to let `doc_sync`
resolve roots without importing `application`.

## Why the tracker is not read

`read_epic_intents` accepts bead statuses and this component passes none. Two
reasons, both measured:

- `bd close` writes only the local database, so the committed
  `.beads/issues.jsonl` export and the live tracker disagree on a branch. A bead
  status shown inside `ctx` would be confidently wrong exactly where the work is
  happening.
- The export is 2.7 MB and 15 ms to parse on this repository, paid on every cold
  bundle, for a fact that does not change which epic declared the node.

The surface makes no claim about bead status rather than a cheap wrong one.

## Cost

Reading the whole TO-BE space costs one open per epic directory: 61 epics and
25 ms measured on this repository, against a `build_context` that costs 8.5 ms.
It is paid on a cold bundle only — `compute_bundle_mtimes` folds the TO-BE tree
into the bundle cache's freshness inputs, so an edited `CONTEXT.md` invalidates
the bundles that carry it and an untouched tree serves from cache.

`--no-intent` exists for a caller that wants the old cost, and it reports
`not_checked` rather than an absence of intent.

## API

- `read_intent(project_root, *, known_refs) -> IntentReading` — the space read
  against the graph's own vocabulary. A backticked token that names no node is
  not a declaration.
- `read_node_intent(conn, project_root) -> IntentReading` — the one call a
  surface makes; resolves the vocabulary from the index first.

## Related

- `docs/domains/context-oracle/components/node-intent/DOC.md` — the policy.
- `docs/domains/application/components/doc-spaces/DOC.md` — the declaration join.
