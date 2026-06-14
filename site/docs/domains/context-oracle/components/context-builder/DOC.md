<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-14T12:30:18.610981+00:00 · coverage 100% (`context-builder`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Context Builder (component)

Internal building block of the context-oracle domain.

**Source:** `src/beadloom/context_oracle/builder.py`

---

## Overview

Assembles a context bundle for a node via a bounded BFS subgraph traversal of
the graph, gathering the node, its neighbors, the attributed code symbols, and
the relevant docs into one structured bundle. This is the machinery behind
`ctx` / `prime` — the read-only context surface AI agents consume.

## Public surface

- `build_context(conn, ref_ids, *, depth=2, max_nodes=20, max_chunks=10)` —
  build a full versioned context bundle for the focus ref_ids; raises
  `LookupError` if any focus ref_id is unknown.
- `bfs_subgraph(conn, focus_ref_ids, depth=2, max_nodes=20)` — the bounded
  bidirectional BFS that expands neighbors by edge priority; returns
  `(nodes, edges)`.
- `collect_chunks(conn, ref_ids, max_chunks=10)` — gather doc text chunks for
  the subgraph, ordered by section priority.
- `suggest_ref_id(conn, ref_id)` — up to 5 prefix-/Levenshtein-matched
  suggestions for a missing ref_id.
- `estimate_tokens(text)` — the chars/4 token-count heuristic used to size
  bundles.
- `DEFAULT_DEPTH` / `DEFAULT_MAX_NODES` / `DEFAULT_MAX_CHUNKS` — traversal
  defaults (`2` / `20` / `10`).

## Collaborators

Reads `nodes` / `edges` / `chunks` / `code_symbols` / `sync_state` (populated by
the graph-loader, doc-indexer, and code-indexer) plus the architecture `rules`.
It is the engine behind the `ctx` / `prime` surfaces and feeds the `cache`
feature; the full bundle shape and the BFS / chunk-priority tables live in the
[context-oracle README](../../README.md).

> Component doc (BDL-051). Public surface verified against `builder.py`.
