# Snapshot

Architecture snapshot store for the graph domain.

**Source:** `src/beadloom/graph/snapshot.py`

---

## Specification

### Purpose

Persist point-in-time snapshots of the architecture graph and compare them over
time. `snapshot save` records the current node and edge state; `snapshot list`
shows the stored snapshots; `snapshot compare` diffs two of them. This lets
drift be reviewed independently of git history.

### How it works

`save_snapshot` reads the `nodes`, `edges`, and `code_symbols` tables, serialises
the node and edge data to JSON, and stores it in `graph_snapshots` with a node
count, edge count, and symbol count. `compare_snapshots` loads two stored states
and computes a `SnapshotDiff` of added, removed, and changed nodes plus added and
removed edges; its `has_changes` property is True when any difference exists.

## Invariants

- A saved snapshot is an immutable record of the graph at save time.
- Comparison is keyed by `ref_id` and edge identity, so it is order-independent
  and deterministic.
- Comparing against an unknown snapshot id raises `ValueError`.

## API

Module `src/beadloom/graph/snapshot.py`:

- `SnapshotInfo` — metadata: `id`, `label`, `created_at`, `node_count`,
  `edge_count`, `symbols_count`.
- `SnapshotDiff` — diff result: `old_id`, `new_id`, `added_nodes`,
  `removed_nodes`, `changed_nodes`, `added_edges`, `removed_edges`, and the
  `has_changes` property.
- `save_snapshot(conn, label=None) -> int` — store the current graph; returns
  the new snapshot id.
- `list_snapshots(conn) -> list[SnapshotInfo]` — list stored snapshots.
- `compare_snapshots(conn, old_id, new_id) -> SnapshotDiff` — diff two
  snapshots (raises `ValueError` on a missing id).

## Testing

Tests: `tests/test_snapshot.py`, `tests/test_cli_snapshot.py`
