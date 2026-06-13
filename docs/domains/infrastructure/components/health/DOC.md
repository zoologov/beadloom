# Health (component)

Internal building block of the infrastructure domain.

**Source:** `src/beadloom/infrastructure/health.py`

---

## Overview

Computes and persists health snapshots (node/edge/doc counts, coverage %, stale
+ isolated counts) and derives trend indicators across snapshots — the honest,
point-in-time picture of project health that the rest of the tooling reports
against. (The Rich rendering of the `beadloom status` dashboard lives in the
CLI `status` command, which calls these functions; this module only computes
and persists the figures.)

## Public surface

- `take_snapshot(conn)` — compute current index stats and persist them to
  `health_snapshots`; returns a `HealthSnapshot`.
- `get_latest_snapshots(conn, n=2)` — recent snapshots for trend comparison.
- `compute_trend(current, previous)` — per-metric trend indicators
  (arrows + deltas) between two snapshots.
- `HealthSnapshot` — frozen dataclass: `taken_at`, `nodes_count`,
  `edges_count`, `docs_count`, `coverage_pct`, `stale_count`, `isolated_count`.

## Collaborators

`reindex` (application layer) calls `take_snapshot` after each index; the CLI
`status` command and the metrics dashboard read the persisted series for trends.
Snapshots persist across reindexes.

> Component doc (BDL-051). Public surface verified against `health.py`.
