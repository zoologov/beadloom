# beadloom:domain=application
# beadloom:feature=status
"""Status data-gathering — the read-side of the ``beadloom status`` command.

Pulls the index/coverage/health/trend counts and the per-node context-bundle
size metrics out of the SQLite index into a plain :class:`StatusData` value.
This is the application-layer logic the CLI ``status`` command renders (Rich or
JSON); the command keeps only presentation, this module owns the queries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@dataclass(frozen=True)
class StatusData:
    """Gathered index/health/coverage/trend state for the status display."""

    version: str | None
    last_reindex: str | None
    nodes_count: int
    edges_count: int
    docs_count: int
    chunks_count: int
    symbols_count: int
    stale_count: int
    isolated_count: int
    empty_summaries: int
    covered: int
    coverage_pct: float
    kind_rows: list[dict[str, object]] = field(default_factory=list)
    kind_covered: dict[str, int] = field(default_factory=dict)
    kind_total: dict[str, int] = field(default_factory=dict)
    trends: dict[str, str] = field(default_factory=dict)
    context_metrics: dict[str, object] = field(default_factory=dict)


def compute_context_metrics(
    conn: sqlite3.Connection,
    nodes_count: int,
    symbols_count: int,
) -> dict[str, object]:
    """Compute context bundle size metrics for the status display.

    Iterates over all nodes, builds context bundles, and measures their
    approximate token sizes using the chars/4 heuristic.
    """
    import sqlite3 as _sqlite3  # local import to satisfy TYPE_CHECKING usage

    from beadloom.context_oracle.builder import build_context, estimate_tokens

    ref_ids = [row[0] for row in conn.execute("SELECT ref_id FROM nodes").fetchall()]

    bundle_sizes: list[tuple[str, int]] = []
    for ref_id in ref_ids:
        try:
            bundle = build_context(conn, [ref_id], depth=1, max_nodes=10, max_chunks=5)
            bundle_text = json.dumps(bundle, ensure_ascii=False)
            tokens = estimate_tokens(bundle_text)
            bundle_sizes.append((ref_id, tokens))
        except (LookupError, _sqlite3.Error):
            continue

    if bundle_sizes:
        avg_tokens = sum(t for _, t in bundle_sizes) // len(bundle_sizes)
        largest_ref, largest_tokens = max(bundle_sizes, key=lambda x: x[1])
    else:
        avg_tokens = 0
        largest_ref = ""
        largest_tokens = 0

    return {
        "avg_bundle_tokens": avg_tokens,
        "largest_bundle_tokens": largest_tokens,
        "largest_bundle_ref_id": largest_ref,
        "total_symbols": symbols_count,
    }


def gather_status(conn: sqlite3.Connection, project_root: Path) -> StatusData:
    """Read the full status payload (counts, coverage, health, trends, metrics).

    ``project_root`` is accepted for symmetry with other application read APIs;
    every figure is computed from the already-opened index connection.
    """
    from beadloom.infrastructure.db import get_meta
    from beadloom.infrastructure.health import compute_trend, get_latest_snapshots

    nodes_count: int = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count: int = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    docs_count: int = conn.execute("SELECT count(*) FROM docs").fetchone()[0]
    chunks_count: int = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    symbols_count: int = conn.execute("SELECT count(*) FROM code_symbols").fetchone()[0]
    stale_count: int = conn.execute(
        "SELECT count(*) FROM sync_state WHERE status = 'stale'"
    ).fetchone()[0]

    # Per-kind breakdown.
    kind_rows = conn.execute(
        "SELECT kind, count(*) as cnt FROM nodes GROUP BY kind ORDER BY cnt DESC"
    ).fetchall()

    # Coverage: nodes with at least one doc linked.
    covered: int = conn.execute(
        "SELECT count(DISTINCT n.ref_id) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id"
    ).fetchone()[0]

    # Per-kind coverage.
    kind_coverage_rows = conn.execute(
        "SELECT n.kind, count(DISTINCT n.ref_id) as covered "
        "FROM nodes n JOIN docs d ON d.ref_id = n.ref_id GROUP BY n.kind"
    ).fetchall()
    kind_covered: dict[str, int] = {r["kind"]: r["covered"] for r in kind_coverage_rows}
    kind_total: dict[str, int] = {r["kind"]: r["cnt"] for r in kind_rows}

    # Isolated nodes count.
    isolated_count: int = conn.execute(
        "SELECT count(*) FROM nodes n "
        "LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id "
        "LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id "
        "WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL"
    ).fetchone()[0]

    # Empty summaries count.
    empty_summaries: int = conn.execute(
        "SELECT count(*) FROM nodes WHERE summary = '' OR summary IS NULL"
    ).fetchone()[0]

    last_reindex = get_meta(conn, "last_reindex_at", "never")
    version = get_meta(conn, "beadloom_version", "unknown")

    # Trend data.
    snapshots = get_latest_snapshots(conn, n=2)
    current = snapshots[0] if snapshots else None
    previous = snapshots[1] if len(snapshots) >= 2 else None
    trends = compute_trend(current, previous) if current and previous else {}

    # Context metrics: measure bundle sizes per node.
    context_metrics = compute_context_metrics(conn, nodes_count, symbols_count)

    coverage_pct = (covered / nodes_count * 100) if nodes_count > 0 else 0.0

    return StatusData(
        version=version,
        last_reindex=last_reindex,
        nodes_count=nodes_count,
        edges_count=edges_count,
        docs_count=docs_count,
        chunks_count=chunks_count,
        symbols_count=symbols_count,
        stale_count=stale_count,
        isolated_count=isolated_count,
        empty_summaries=empty_summaries,
        covered=covered,
        coverage_pct=coverage_pct,
        kind_rows=[{"kind": r["kind"], "cnt": r["cnt"]} for r in kind_rows],
        kind_covered=kind_covered,
        kind_total=kind_total,
        trends=trends,
        context_metrics=context_metrics,
    )
