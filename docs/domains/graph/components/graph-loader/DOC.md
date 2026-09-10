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

### `source:` is resolved against disk at load time

A node's `source` is STAT'ed as it is loaded (BDL-061.50):

- a **directory written without a trailing slash** is normalised to carry one. A
  directory source is a covering prefix everywhere it is consumed — ownership,
  the sync-pair fallback, symbol counts, module-coverage — and each of those
  reads a slash-less value as a lone file path, so the node owned **nothing**:
  no `depends_on` edge, no sync pair, no symbol count, no coverage, silently.
  Beadloom's own graph happens to use trailing slashes on all its sourced nodes,
  which is precisely why the defect could only ever be an adopter's.
- a **file** source is never widened into a directory: the path is stat'ed, not
  guessed.
- a source that names **no path at all** is a declaration that owns nothing, and
  it is reported as a `GraphLoadResult` warning naming the `ref_id` — surfaced
  by `beadloom reindex` — instead of turning into an empty node nobody
  questions.

## Public surface

- `load_graph(...)` — parse the graph YAML and populate `nodes` / `edges` (and
  `foreign_edges` for `@repo:ref` cross-repo endpoints); returns a
  `GraphLoadResult` carrying `errors` + `warnings`.
- `parse_graph_file(path)` — parse one `*.yml` into a `ParsedFile`; raises
  `GraphParseError` on malformed YAML, on a top-level value that is not a
  mapping, and — since BDL-069 — on a file that will not DECODE. `read_text` sat
  outside the `try`, so a graph file that is not UTF-8 left `load_graph` as a raw
  `UnicodeDecodeError` instead of as an entry in `result.errors`.
- `update_node_in_yaml(...)` — patch a node's fields back into its YAML file
  (used to write the `docs:` field after skeleton generation).
- `NOT_A_GRAPH_FILE` — `{"rules.yml"}`, the name every reader of
  `.beadloom/_graph/` skips. Declared here, in the domain that owns the graph
  file format and also reads `rules.yml` (`graph/linter.py`), and re-exported by
  `onboarding.graph_files` for the readers that go through the skip policy. The
  direction is what makes one constant possible: `onboarding` may import `graph`
  and the reverse is a cycle.
- `get_node_tags(conn, ref_id)` — the node's tag set (used by tag-matched rules).
- `GraphLoadResult` / `ParsedFile` / `ForeignEdge` / `GraphParseError` — the
  result + value types.
- `VALID_LIFECYCLES` — `{active, planned, deprecated, dead, external}`; an
  absent value defaults to `active`, an invalid one is recorded in
  `result.errors` and falls back to `active`.

## The skip policy, and why this module restates it

BDL-069 measured that `load_graph` and `update_node_in_yaml` both read
`.beadloom/_graph/` for NODES, which puts them in the population of
`onboarding.graph_files.each_graph_file` — and neither reaches it. The structural
reason is the same for both: `onboarding` already imports `graph`, so importing
that policy here would be a dependency cycle, which `no-dependency-cycles`
refuses at error severity. So the three guards are restated in each body, and the
duplication is filed as `beadloom-4axf`, which closes it by moving the policy
into a layer every reader may import.

`load_graph` would keep an exemption even then, and it is the more interesting
one: it must REPORT a file it cannot parse rather than pass over it. A graph file
that will not parse is recorded in `result.errors` naming the file and the line,
which is what stops a broken graph from loading as a silently smaller one
(BDL-UX #86). Skipping is the right answer for a reader whose caller is `init`
and the wrong one here.

## Collaborators

The ingestion seam every other graph capability reads after reindex — `lint`,
`diff`, `ctx`, `snapshot`, `federation`. It folds a GraphQL producer's exposed
surface in via `sdl.extract_surface` and derives `edges.contract_key`; it writes
through the infrastructure `db` layer.

> Component doc (BDL-051). Public surface verified against `loader.py`.
