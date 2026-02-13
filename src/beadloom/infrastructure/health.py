"""Health metrics: snapshots, trend computation, and Rich dashboard."""

# beadloom:domain=infrastructure

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


@dataclass(frozen=True)
class HealthSnapshot:
    """Point-in-time health metrics."""

    taken_at: str
    nodes_count: int
    edges_count: int
    docs_count: int
    coverage_pct: float
    stale_count: int
    isolated_count: int


def take_snapshot(conn: sqlite3.Connection) -> HealthSnapshot:
    """Compute current health metrics and persist to health_snapshots table."""
    nodes_count: int = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
    edges_count: int = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
    docs_count: int = conn.execute("SELECT count(*) FROM docs").fetchone()[0]

    covered: int = conn.execute(
        "SELECT count(DISTINCT n.ref_id) FROM nodes n JOIN docs d ON d.ref_id = n.ref_id"
    ).fetchone()[0]
    coverage_pct = (covered / nodes_count * 100) if nodes_count > 0 else 0.0

    stale_count: int = conn.execute(
        "SELECT count(*) FROM sync_state WHERE status = 'stale'"
    ).fetchone()[0]

    isolated_count: int = conn.execute(
        "SELECT count(*) FROM nodes n "
        "LEFT JOIN edges e1 ON e1.src_ref_id = n.ref_id "
        "LEFT JOIN edges e2 ON e2.dst_ref_id = n.ref_id "
        "WHERE e1.src_ref_id IS NULL AND e2.dst_ref_id IS NULL"
    ).fetchone()[0]

    taken_at = datetime.now(tz=timezone.utc).isoformat()

    snapshot = HealthSnapshot(
        taken_at=taken_at,
        nodes_count=nodes_count,
        edges_count=edges_count,
        docs_count=docs_count,
        coverage_pct=coverage_pct,
        stale_count=stale_count,
        isolated_count=isolated_count,
    )

    conn.execute(
        "INSERT INTO health_snapshots "
        "(taken_at, nodes_count, edges_count, docs_count, coverage_pct, "
        "stale_count, isolated_count, extra) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            snapshot.taken_at,
            snapshot.nodes_count,
            snapshot.edges_count,
            snapshot.docs_count,
            snapshot.coverage_pct,
            snapshot.stale_count,
            snapshot.isolated_count,
            json.dumps({}),
        ),
    )
    conn.commit()

    return snapshot


def get_latest_snapshots(conn: sqlite3.Connection, n: int = 2) -> list[HealthSnapshot]:
    """Get the N most recent snapshots for trend comparison."""
    rows = conn.execute(
        "SELECT taken_at, nodes_count, edges_count, docs_count, "
        "coverage_pct, stale_count, isolated_count "
        "FROM health_snapshots ORDER BY id DESC LIMIT ?",
        (n,),
    ).fetchall()

    return [
        HealthSnapshot(
            taken_at=r["taken_at"],
            nodes_count=r["nodes_count"],
            edges_count=r["edges_count"],
            docs_count=r["docs_count"],
            coverage_pct=r["coverage_pct"],
            stale_count=r["stale_count"],
            isolated_count=r["isolated_count"],
        )
        for r in rows
    ]


def compute_trend(
    current: HealthSnapshot,
    previous: HealthSnapshot | None,
) -> dict[str, str]:
    """Compute trend indicators between two snapshots.

    Returns a dict mapping metric names to trend strings like "▲ +8%" or "▼ +1".
    For metrics where increase is bad (stale, isolated), arrows are inverted.
    """
    if previous is None:
        return {}

    trends: dict[str, str] = {}

    # Coverage: increase is good
    cov_delta = current.coverage_pct - previous.coverage_pct
    if abs(cov_delta) >= 0.5:
        arrow = "▲" if cov_delta > 0 else "▼"
        trends["coverage_pct"] = f"{arrow} {cov_delta:+.0f}%"

    # Stale: increase is bad
    stale_delta = current.stale_count - previous.stale_count
    if stale_delta != 0:
        arrow = "▼" if stale_delta > 0 else "▲"
        trends["stale_count"] = f"{arrow} {stale_delta:+d} since last reindex"

    # Isolated: decrease is good
    iso_delta = current.isolated_count - previous.isolated_count
    if iso_delta != 0:
        arrow = "▼" if iso_delta > 0 else "▲"
        trends["isolated_count"] = f"{arrow} {iso_delta:+d} since last reindex"

    # Nodes
    nodes_delta = current.nodes_count - previous.nodes_count
    if nodes_delta != 0:
        trends["nodes_count"] = f"{nodes_delta:+d}"

    # Edges
    edges_delta = current.edges_count - previous.edges_count
    if edges_delta != 0:
        trends["edges_count"] = f"{edges_delta:+d}"

    # Docs
    docs_delta = current.docs_count - previous.docs_count
    if docs_delta != 0:
        trends["docs_count"] = f"{docs_delta:+d}"

    return trends
