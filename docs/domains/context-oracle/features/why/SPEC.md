# Why (Impact Analysis)

Bidirectional BFS impact analysis for an architecture graph node -- shows upstream dependencies and downstream dependents with aggregated impact metrics.

Source: `src/beadloom/context_oracle/why.py`

## Specification

### Purpose

Given a `ref_id`, the `why` feature answers: "What does this node depend on, what depends on it, and what is the blast radius of a change?" It builds two trees (upstream and downstream) via BFS traversal of the edges table, then computes impact metrics including documentation coverage and stale-doc count for the downstream subgraph.

### Data Structures

#### NodeInfo (frozen dataclass)

Basic information about the analyzed node.

| Field | Type | Description |
|-------|------|-------------|
| `ref_id` | `str` | Node identifier |
| `kind` | `str` | Node kind (domain, feature, service, entity, adr) |
| `summary` | `str` | Node summary text |

#### TreeNode (frozen dataclass)

Recursive tree structure representing one node in the upstream or downstream tree.

| Field | Type | Description |
|-------|------|-------------|
| `ref_id` | `str` | Node identifier |
| `kind` | `str` | Node kind |
| `summary` | `str` | Node summary |
| `edge_kind` | `str` | Edge type connecting this node to its parent in the tree |
| `children` | `tuple[TreeNode, ...]` | Child nodes (default `()`) |

#### ImpactSummary (frozen dataclass)

Aggregated impact metrics computed from the downstream tree.

| Field | Type | Description |
|-------|------|-------------|
| `downstream_direct` | `int` | Number of direct dependents (depth 0 in `_count_tree_nodes`) |
| `downstream_transitive` | `int` | Number of transitive dependents (depth > 0) |
| `doc_coverage` | `float` | Percentage (0--100) of downstream nodes with at least one document |
| `stale_count` | `int` | Number of stale `sync_state` entries for downstream nodes |

#### WhyResult (frozen dataclass)

Complete result of the impact analysis.

| Field | Type | Description |
|-------|------|-------------|
| `node` | `NodeInfo` | The analyzed node |
| `upstream` | `tuple[TreeNode, ...]` | Upstream dependency tree (top-level children) |
| `downstream` | `tuple[TreeNode, ...]` | Downstream dependent tree (top-level children) |
| `impact` | `ImpactSummary` | Aggregated impact metrics |

### Core Algorithm: `analyze_node`

```python
def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
) -> WhyResult
```

Steps:

1. **Validate node existence.** Query `nodes` table for `ref_id`. If not found, call `suggest_ref_id(conn, ref_id)` and raise `LookupError` with the message `'"<ref_id>" not found. Did you mean: <suggestions>?'`.
2. **Build upstream tree.** Call `_build_tree(conn, ref_id, "upstream", depth, max_nodes)`. Upstream follows outgoing edges (`src_ref_id = current` in the `edges` table) -- these are the things the node depends on.
3. **Build downstream tree.** Call `_build_tree(conn, ref_id, "downstream", depth, max_nodes)`. Downstream follows incoming edges (`dst_ref_id = current`) -- these are the things that depend on the node.
4. **Count direct vs. transitive.** Apply `_count_tree_nodes(downstream)` to partition dependents by tree depth.
5. **Collect downstream refs.** Apply `_collect_all_refs(downstream)` to get all `ref_id` values in the downstream tree.
6. **Compute doc coverage.** `_compute_doc_coverage(conn, downstream_refs)` returns the percentage of downstream nodes with at least one row in the `docs` table. Returns `100.0` if the set is empty.
7. **Count stale docs.** `_count_stale_docs(conn, downstream_refs)` counts rows in `sync_state` where `status = 'stale'` for any downstream `ref_id`.
8. **Assemble and return** `WhyResult`.

### Tree Construction: `_build_tree`

```python
def _build_tree(
    conn: sqlite3.Connection,
    start_ref_id: str,
    direction: str,       # "upstream" | "downstream"
    depth: int,
    max_nodes: int,
) -> tuple[TreeNode, ...]
```

Algorithm (BFS with parent tracking):

1. Initialize `visited = {start_ref_id}` and `node_count = 0`.
2. Seed the BFS queue with immediate neighbors of `start_ref_id` (via `_get_neighbors`).
3. For each unvisited neighbor within `max_nodes` limit: add to queue at depth 1, record in `children_map[start_ref_id]`, cache node info.
4. Process the queue level by level. For each dequeued node at `current_depth < depth` and `node_count < max_nodes`: expand neighbors, add unvisited ones to queue at `current_depth + 1`, record in `children_map[current_id]`.
5. Build a recursive `TreeNode` structure from `children_map` starting at `start_ref_id`.
6. Return the top-level children (the start node itself is NOT included in the tree).

### Direction Semantics

| Direction | SQL Query | Meaning |
|-----------|-----------|---------|
| `upstream` | `SELECT dst_ref_id, kind FROM edges WHERE src_ref_id = ?` | Outgoing edges: what this node depends on |
| `downstream` | `SELECT src_ref_id, kind FROM edges WHERE dst_ref_id = ?` | Incoming edges: what depends on this node |

### Node Counting: `_count_tree_nodes`

```python
def _count_tree_nodes(trees: tuple[TreeNode, ...], depth: int = 0) -> tuple[int, int]
```

Recursive traversal of the tree. At the initial call (`depth=0`), top-level nodes count as "direct". All deeper nodes count as "transitive". Returns `(direct_count, transitive_count)`.

### Doc Coverage: `_compute_doc_coverage`

```python
def _compute_doc_coverage(conn: sqlite3.Connection, downstream_refs: set[str]) -> float
```

Queries `COUNT(DISTINCT ref_id) FROM docs WHERE ref_id IN (...)`. Returns `covered / total * 100`. Returns `100.0` for an empty set (vacuous truth -- a node with no dependents has no undocumented dependents).

### Stale Doc Count: `_count_stale_docs`

```python
def _count_stale_docs(conn: sqlite3.Connection, downstream_refs: set[str]) -> int
```

Queries `COUNT(*) FROM sync_state WHERE ref_id IN (...) AND status = 'stale'`. Returns `0` for an empty set.

### Rendering: `render_why`

```python
def render_why(result: WhyResult, console: Console) -> None
```

Rich terminal output consisting of:

1. **Header Panel** (`border_style="blue"`): `ref_id (kind)` and summary.
2. **Upstream Tree** (`Tree` with cyan label `"Upstream (dependencies)"`): Each node rendered as `[bold]ref_id[/] (kind) [dim]--[edge_kind]--[/] summary`. If empty, prints `"No upstream dependencies."`.
3. **Downstream Tree** (`Tree` with green label `"Downstream (dependents)"`): Same format. If empty, prints `"No downstream dependents."`.
4. **Impact Summary Panel** (`border_style="yellow"`): Direct dependents, transitive dependents, doc coverage percentage, stale docs count.

### JSON Serialization: `result_to_dict`

```python
def result_to_dict(result: WhyResult) -> dict[str, object]
```

Converts a `WhyResult` to a JSON-serializable dict with structure:

```json
{
  "node": { "ref_id": "...", "kind": "...", "summary": "..." },
  "upstream": [
    {
      "ref_id": "...", "kind": "...", "summary": "...",
      "edge_kind": "...",
      "children": [ ... ]
    }
  ],
  "downstream": [ ... ],
  "impact": {
    "downstream_direct": 5,
    "downstream_transitive": 12,
    "doc_coverage": 80.0,
    "stale_count": 2
  }
}
```

### CLI Integration

```
beadloom why REF_ID [--depth N] [--json] [--project DIR]
```

- Default `--depth 3`.
- Without `--json`: calls `render_why` for Rich output.
- With `--json`: calls `result_to_dict` and prints JSON.

### MCP Integration

The `why` MCP tool accepts `ref_id` and optional `depth`, returns the dict from `result_to_dict`.

## API

### Public Functions

```python
def analyze_node(
    conn: sqlite3.Connection,
    ref_id: str,
    depth: int = 3,
    max_nodes: int = 50,
) -> WhyResult
```

Perform bidirectional BFS impact analysis. Raises `LookupError` with Levenshtein suggestions if `ref_id` not found.

```python
def render_why(result: WhyResult, console: Console) -> None
```

Render a `WhyResult` to the terminal using Rich panels and trees.

```python
def result_to_dict(result: WhyResult) -> dict[str, object]
```

Serialize a `WhyResult` to a JSON-compatible dictionary.

### Public Classes

```python
@dataclass(frozen=True)
class NodeInfo:
    ref_id: str
    kind: str
    summary: str

@dataclass(frozen=True)
class TreeNode:
    ref_id: str
    kind: str
    summary: str
    edge_kind: str
    children: tuple[TreeNode, ...] = ()

@dataclass(frozen=True)
class ImpactSummary:
    downstream_direct: int
    downstream_transitive: int
    doc_coverage: float
    stale_count: int

@dataclass(frozen=True)
class WhyResult:
    node: NodeInfo
    upstream: tuple[TreeNode, ...]
    downstream: tuple[TreeNode, ...]
    impact: ImpactSummary
```

### Private Functions

```python
def _build_tree(conn, start_ref_id, direction, depth, max_nodes) -> tuple[TreeNode, ...]
def _get_neighbors(conn, ref_id, direction) -> list[tuple[str, str]]
def _cache_node(conn, ref_id, cache) -> None
def _count_tree_nodes(trees, depth=0) -> tuple[int, int]
def _collect_all_refs(trees) -> set[str]
def _compute_doc_coverage(conn, downstream_refs) -> float
def _count_stale_docs(conn, downstream_refs) -> int
def _render_tree(tree_nodes, parent) -> None
def _tree_node_to_dict(tnode) -> dict[str, object]
```

## Invariants

- The start node is never included in the upstream or downstream trees (it is always in the `visited` set from the beginning).
- BFS does not cycle: a `visited` set prevents re-traversal.
- Each ref_id appears at most once across the entire tree for a given direction.
- `max_nodes` is a hard cap per direction, enforced during BFS expansion.
- If `ref_id` does not exist in `nodes`, `LookupError` is raised before any traversal.
- `doc_coverage` is `100.0` when there are no downstream nodes (vacuous truth).
- All dataclasses are frozen (immutable after construction).

## Constraints

- Default depth is 3 and default `max_nodes` is 50 per direction. These are independent limits -- BFS stops when either is reached.
- The upstream and downstream traversals are fully independent: they do not share `visited` sets or node counts.
- `_get_neighbors` issues one SQL query per node per BFS step. For large graphs, this results in O(nodes_visited) queries per direction.
- `_compute_doc_coverage` and `_count_stale_docs` use dynamic SQL with `IN (...)` placeholders. The number of placeholders equals the size of the downstream ref set (up to `max_nodes`).
- Levenshtein suggestions on `LookupError` rely on `suggest_ref_id` from `beadloom.context_oracle.builder`, which loads all ref_ids into memory.

## Testing

Tests are located in `tests/test_why.py`. Key scenarios:

- **Basic analysis**: Create a small graph, call `analyze_node`, verify `WhyResult` structure, upstream and downstream trees, and impact counts.
- **Unknown ref_id**: Verify `LookupError` is raised with suggestion text.
- **Depth limit**: Verify that nodes beyond `depth` are not included in the tree.
- **Max nodes limit**: Verify that BFS stops after `max_nodes` per direction.
- **No dependents**: Verify that a leaf node returns empty downstream tree and `doc_coverage = 100.0`.
- **Cycle handling**: Create a graph with cycles, verify BFS completes without infinite loop.
- **Doc coverage calculation**: Set up nodes with and without docs, verify percentage.
- **Stale count**: Insert stale sync_state rows, verify count in impact summary.
- **`result_to_dict` round-trip**: Verify JSON-serializable output matches expected structure.
- **`render_why` smoke test**: Call with a mock console, verify no exceptions.
