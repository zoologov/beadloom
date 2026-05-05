"""Tests for beadloom.application.site_metrics_history (BDL-041 F4.4 BEAD-03).

The metrics-history store is an additive append-log of honest metric points
``{ts, lint_violations, debt_score, coverage_pct, sync_pct, nodes, edges,
symbols}`` persisted to ``.beadloom/metrics_history.json``. Trends on the
dashboard come *only* from these real recorded points — never an interpolated
or fabricated one. Timestamps are injected (never ``now()`` inside the store)
so the series is deterministic in tests.

These tests assert: append/read round-trips, the series is sorted by ts, no
fabrication (read returns exactly what was appended), idempotent dedup of an
identical ts, and a structural backfill from ``graph_snapshots`` so the trend
isn't empty on day one.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.application.site_metrics_history import (
    MetricsPoint,
    append_metrics_point,
    backfill_structural_history,
    history_path,
    read_history,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / ".beadloom").mkdir(parents=True)
    return project


def _point(ts: str, **over: float) -> MetricsPoint:
    base: dict[str, float] = {
        "lint_violations": 0,
        "debt_score": 0.0,
        "coverage_pct": 0.0,
        "sync_pct": 100.0,
        "nodes": 0,
        "edges": 0,
        "symbols": 0,
    }
    base.update(over)
    return MetricsPoint(
        ts=ts,
        lint_violations=int(base["lint_violations"]),
        debt_score=float(base["debt_score"]),
        coverage_pct=float(base["coverage_pct"]),
        sync_pct=float(base["sync_pct"]),
        nodes=int(base["nodes"]),
        edges=int(base["edges"]),
        symbols=int(base["symbols"]),
    )


# ---------------------------------------------------------------------------
# Append / read round-trip
# ---------------------------------------------------------------------------


def test_read_empty_returns_empty_list(tmp_path: Path) -> None:
    project = _project(tmp_path)
    assert read_history(project) == []


def test_append_then_read_round_trips(tmp_path: Path) -> None:
    project = _project(tmp_path)
    point = _point("2026-06-01T00:00:00+00:00", lint_violations=3, debt_score=12.5)
    append_metrics_point(project, point)
    series = read_history(project)
    assert series == [point]


def test_history_written_under_dot_beadloom(tmp_path: Path) -> None:
    project = _project(tmp_path)
    append_metrics_point(project, _point("2026-06-01T00:00:00+00:00"))
    assert history_path(project) == project / ".beadloom" / "metrics_history.json"
    assert history_path(project).exists()


# ---------------------------------------------------------------------------
# Honest: only recorded points, sorted by ts, no fabrication
# ---------------------------------------------------------------------------


def test_series_sorted_by_ts(tmp_path: Path) -> None:
    project = _project(tmp_path)
    append_metrics_point(project, _point("2026-06-03T00:00:00+00:00", nodes=3))
    append_metrics_point(project, _point("2026-06-01T00:00:00+00:00", nodes=1))
    append_metrics_point(project, _point("2026-06-02T00:00:00+00:00", nodes=2))
    series = read_history(project)
    assert [p.ts for p in series] == [
        "2026-06-01T00:00:00+00:00",
        "2026-06-02T00:00:00+00:00",
        "2026-06-03T00:00:00+00:00",
    ]
    # No interpolation/fabrication: exactly the three recorded points.
    assert [p.nodes for p in series] == [1, 2, 3]


def test_no_fabricated_points_between_recorded(tmp_path: Path) -> None:
    project = _project(tmp_path)
    append_metrics_point(project, _point("2026-01-01T00:00:00+00:00"))
    append_metrics_point(project, _point("2026-12-01T00:00:00+00:00"))
    # A 11-month gap must NOT be filled in — exactly two real points.
    assert len(read_history(project)) == 2


def test_duplicate_ts_is_idempotent_overwrite(tmp_path: Path) -> None:
    project = _project(tmp_path)
    ts = "2026-06-01T00:00:00+00:00"
    append_metrics_point(project, _point(ts, lint_violations=5))
    append_metrics_point(project, _point(ts, lint_violations=2))
    series = read_history(project)
    # Same ts collapses to one point (the latest value) — a re-run of the same
    # build must not double-count the series.
    assert len(series) == 1
    assert series[0].lint_violations == 2


# ---------------------------------------------------------------------------
# Determinism: injected ts, byte-stable JSON store
# ---------------------------------------------------------------------------


def test_store_json_is_deterministic_sorted(tmp_path: Path) -> None:
    project = _project(tmp_path)
    append_metrics_point(project, _point("2026-06-02T00:00:00+00:00", nodes=2))
    append_metrics_point(project, _point("2026-06-01T00:00:00+00:00", nodes=1))
    raw = history_path(project).read_text(encoding="utf-8")
    parsed = json.loads(raw)
    # Stored sorted by ts and each object key-sorted -> byte stable.
    assert [pt["ts"] for pt in parsed] == [
        "2026-06-01T00:00:00+00:00",
        "2026-06-02T00:00:00+00:00",
    ]
    assert raw == json.dumps(parsed, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_append_uses_injected_ts_not_now(tmp_path: Path) -> None:
    project = _project(tmp_path)
    point = _point("1999-01-01T00:00:00+00:00")
    append_metrics_point(project, point)
    assert read_history(project)[0].ts == "1999-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Backfill structural counts from graph_snapshots
# ---------------------------------------------------------------------------


def _snapshot(
    conn: sqlite3.Connection,
    *,
    created_at: str,
    nodes: int,
    edges: int,
    symbols: int,
) -> None:
    nodes_json = json.dumps([{"ref_id": f"n{i}"} for i in range(nodes)])
    edges_json = json.dumps([{"src_ref_id": f"e{i}"} for i in range(edges)])
    conn.execute(
        "INSERT INTO graph_snapshots "
        "(label, created_at, nodes_json, edges_json, symbols_count) "
        "VALUES (?, ?, ?, ?, ?)",
        (None, created_at, nodes_json, edges_json, symbols),
    )
    conn.commit()


def _conn(project: Path) -> sqlite3.Connection:
    from beadloom.infrastructure.db import create_schema, open_db

    conn = open_db(project / ".beadloom" / "beadloom.db")
    create_schema(conn)
    return conn


def test_backfill_seeds_structural_points_from_snapshots(tmp_path: Path) -> None:
    project = _project(tmp_path)
    conn = _conn(project)
    try:
        _snapshot(conn, created_at="2026-05-01 10:00:00", nodes=5, edges=4, symbols=20)
        _snapshot(conn, created_at="2026-05-02 10:00:00", nodes=6, edges=5, symbols=25)
        backfill_structural_history(conn, project)
    finally:
        conn.close()
    series = read_history(project)
    # One point per snapshot, structural counts present, sorted by ts.
    assert len(series) == 2
    assert [p.nodes for p in series] == [5, 6]
    assert [p.edges for p in series] == [4, 5]
    assert [p.symbols for p in series] == [20, 25]


def test_backfill_does_not_overwrite_existing_recorded_point(tmp_path: Path) -> None:
    project = _project(tmp_path)
    # A real recorded point (full metrics) already exists for this ts.
    ts = "2026-05-01T10:00:00+00:00"
    append_metrics_point(project, _point(ts, nodes=99, lint_violations=7))
    conn = _conn(project)
    try:
        # A snapshot mapping to the SAME ts (snapshot stores 'YYYY-MM-DD HH:MM:SS').
        _snapshot(conn, created_at="2026-05-01 10:00:00", nodes=5, edges=4, symbols=20)
        backfill_structural_history(conn, project)
    finally:
        conn.close()
    series = read_history(project)
    assert len(series) == 1
    # The richer recorded point is preserved; backfill never clobbers real data.
    assert series[0].nodes == 99
    assert series[0].lint_violations == 7


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    project = _project(tmp_path)
    conn = _conn(project)
    try:
        _snapshot(conn, created_at="2026-05-01 10:00:00", nodes=5, edges=4, symbols=20)
        backfill_structural_history(conn, project)
        backfill_structural_history(conn, project)
    finally:
        conn.close()
    assert len(read_history(project)) == 1
