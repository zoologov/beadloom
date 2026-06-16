# beadloom:domain=application
# beadloom:feature=debt-report
"""Debt trend tracking — compare the current score against the last snapshot.

Recomputes a structural debt score from a stored ``graph_snapshots`` row (only
nodes/edges are captured there) and produces per-category deltas vs the current
report, so the report can show movement over time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application.debt_report.config import load_debt_weights
from beadloom.application.debt_report.models import (
    DebtReport,
    DebtTrend,
    DebtWeights,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _compute_snapshot_debt(
    snapshot_nodes: list[dict[str, str]],
    snapshot_edges: list[dict[str, str]],
    snapshot_symbols_count: int,
    weights: DebtWeights,
) -> tuple[float, dict[str, float]]:
    """Compute a debt score from snapshot data.

    Uses only structural data available in the snapshot: nodes and edges.
    Computes the complexity category (high fan-out) from edges and
    approximates undocumented nodes (all nodes in snapshot are assumed
    undocumented, since docs table is not captured in snapshots).

    Returns (total_score, per_category_scores).
    """
    # Count high fan-out from snapshot edges
    edge_counts: dict[str, int] = {}
    for edge in snapshot_edges:
        src = edge.get("src_ref_id", "")
        if src:
            edge_counts[src] = edge_counts.get(src, 0) + 1

    high_fan_out = sum(
        1 for cnt in edge_counts.values() if cnt > weights.high_fan_out_threshold
    )

    # Complexity category score from snapshot
    complexity_score = float(high_fan_out) * weights.high_fan_out

    # Undocumented: snapshot doesn't store docs, so we count all nodes as
    # potentially undocumented. To avoid misleading trend data, we set
    # doc-related categories to 0 (not computable from snapshot).
    # Rule violations and test gaps are also not computable from snapshot.
    category_scores = {
        "rule_violations": 0.0,
        "doc_gaps": 0.0,
        "complexity": complexity_score,
        "test_gaps": 0.0,
        "meta_doc_staleness": 0.0,
    }
    total = sum(category_scores.values())
    return min(100.0, total), category_scores


def compute_debt_trend(
    conn: sqlite3.Connection,
    current_report: DebtReport,
    project_root: Path,
    weights: DebtWeights | None = None,
) -> DebtTrend | None:
    """Compare current debt score against the last snapshot.

    Returns ``None`` if no previous snapshot exists.
    Recomputes the debt score from the snapshot's structural data to get
    an accurate trend comparison for the complexity category.

    For categories not stored in snapshots (rules, docs, tests), the
    trend compares against the category scores from the snapshot's
    recomputed structural debt.

    Args:
        conn: Database connection.
        current_report: The current debt report.
        project_root: Project root directory.
        weights: Optional debt weights override.

    Returns:
        A :class:`DebtTrend` or ``None`` if no snapshot exists.
    """
    import json

    from beadloom.graph.snapshot import list_snapshots

    if weights is None:
        weights = load_debt_weights(project_root)

    snapshots = list_snapshots(conn)
    if not snapshots:
        return None

    # Use the most recent snapshot
    latest = snapshots[0]

    # Load snapshot data
    row = conn.execute(
        "SELECT nodes_json, edges_json, symbols_count, label, created_at "
        "FROM graph_snapshots WHERE id = ?",
        (latest.id,),
    ).fetchone()
    if row is None:
        return None

    snapshot_nodes: list[dict[str, str]] = json.loads(row["nodes_json"])
    snapshot_edges: list[dict[str, str]] = json.loads(row["edges_json"])
    symbols_count: int = row["symbols_count"]
    snapshot_label: str = row["label"] or ""
    snapshot_date: str = row["created_at"]

    # Build the display string: prefer label, fallback to date
    snapshot_display = f"{snapshot_date} [{snapshot_label}]" if snapshot_label else snapshot_date

    # Compute debt from snapshot structural data
    prev_total, prev_categories = _compute_snapshot_debt(
        snapshot_nodes, snapshot_edges, symbols_count, weights,
    )

    # Build per-category deltas
    current_categories: dict[str, float] = {
        cat.name: cat.score for cat in current_report.categories
    }
    category_deltas: dict[str, float] = {}
    for cat_name in (
        "rule_violations", "doc_gaps", "complexity", "test_gaps",
        "meta_doc_staleness",
    ):
        current_val = current_categories.get(cat_name, 0.0)
        prev_val = prev_categories.get(cat_name, 0.0)
        category_deltas[cat_name] = current_val - prev_val

    delta = current_report.debt_score - prev_total

    return DebtTrend(
        previous_snapshot=snapshot_display,
        previous_score=prev_total,
        delta=delta,
        category_deltas=category_deltas,
    )
