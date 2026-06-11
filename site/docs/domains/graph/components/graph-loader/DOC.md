<!-- beadloom:badge-start -->
> ✅ **fresh**
> 
> last synced 2026-06-11T14:19:08.709748+00:00 · coverage 100% (`graph-loader`)
> 
> _Validation by Beadloom `doc_sync` — same source as `sync-check`._
<!-- beadloom:badge-end -->

# Graph Loader (component)

Internal building block of the graph domain.

**Source:** `src/beadloom/graph/loader.py`

---

## Overview

Parses the `.beadloom/_graph/*.yml` files (nodes + edges) and populates the
`nodes` / `edges` SQLite tables. Validates `ref_id` uniqueness and edge
integrity (every edge endpoint must resolve to a declared node). This is the
ingestion seam every other graph capability (lint, diff, ctx, snapshot) reads
from after reindex.

## Public surface

- `load_graph(...)` — parse the graph YAML and populate `nodes` / `edges` (and
  `foreign_edges` for `@repo:ref` cross-repo endpoints); returns a
  `GraphLoadResult` carrying `errors` + `warnings`.
- `parse_graph_file(path)` — parse one `*.yml` into a `ParsedFile`; raises
  `GraphParseError` on malformed YAML.
- `update_node_in_yaml(...)` — patch a node's fields back into its YAML file
  (used to write the `docs:` field after skeleton generation).
- `get_node_tags(conn, ref_id)` — the node's tag set (used by tag-matched rules).
- `GraphLoadResult` / `ParsedFile` / `ForeignEdge` / `GraphParseError` — the
  result + value types.
- `VALID_LIFECYCLES` — `{active, planned, deprecated, dead, external}`; an
  absent value defaults to `active`, an invalid one is recorded in
  `result.errors` and falls back to `active`.

## Collaborators

The ingestion seam every other graph capability reads after reindex — `lint`,
`diff`, `ctx`, `snapshot`, `federation`. It folds a GraphQL producer's exposed
surface in via `sdl.extract_surface` and derives `edges.contract_key`; it writes
through the infrastructure `db` layer.

> Component doc (BDL-051). Public surface verified against `loader.py`.
