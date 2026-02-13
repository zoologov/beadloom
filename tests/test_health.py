"""Tests for beadloom.health — snapshots, trends, dashboard data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.infrastructure.db import create_schema, open_db
from beadloom.infrastructure.health import (
    HealthSnapshot,
    compute_trend,
    get_latest_snapshots,
    take_snapshot,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a DB with schema."""
    db_path = tmp_path / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


def _insert_node(conn: sqlite3.Connection, ref_id: str, kind: str, summary: str) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        (ref_id, kind, summary),
    )
    conn.commit()


def _insert_edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )
    conn.commit()


def _insert_doc(conn: sqlite3.Connection, path: str, ref_id: str) -> None:
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, "other", ref_id, "abc123"),
    )
    conn.commit()


class TestTakeSnapshot:
    def test_empty_db(self, conn: sqlite3.Connection) -> None:
        snapshot = take_snapshot(conn)
        assert snapshot.nodes_count == 0
        assert snapshot.edges_count == 0
        assert snapshot.docs_count == 0
        assert snapshot.coverage_pct == 0.0
        assert snapshot.stale_count == 0
        assert snapshot.isolated_count == 0
        assert snapshot.taken_at != ""

    def test_with_data(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        _insert_node(conn, "D1", "domain", "Domain 1")
        _insert_edge(conn, "F1", "D1", "part_of")
        _insert_doc(conn, "spec.md", "F1")

        snapshot = take_snapshot(conn)
        assert snapshot.nodes_count == 2
        assert snapshot.edges_count == 1
        assert snapshot.docs_count == 1
        assert snapshot.coverage_pct == 50.0  # 1/2 nodes covered
        assert snapshot.isolated_count == 0

    def test_persists_to_db(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature")
        take_snapshot(conn)

        row = conn.execute("SELECT * FROM health_snapshots").fetchone()
        assert row is not None
        assert row["nodes_count"] == 1

    def test_isolated_nodes(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        _insert_node(conn, "F2", "feature", "Feature 2")
        # F1 and F2 have no edges — both isolated.
        snapshot = take_snapshot(conn)
        assert snapshot.isolated_count == 2

    def test_stale_docs(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, "
            "doc_hash_at_sync, synced_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("doc.md", "code.py", "F1", "h1", "h2", "2025-01-01", "stale"),
        )
        conn.commit()
        snapshot = take_snapshot(conn)
        assert snapshot.stale_count == 1


class TestGetLatestSnapshots:
    def test_empty(self, conn: sqlite3.Connection) -> None:
        snapshots = get_latest_snapshots(conn)
        assert snapshots == []

    def test_single(self, conn: sqlite3.Connection) -> None:
        take_snapshot(conn)
        snapshots = get_latest_snapshots(conn)
        assert len(snapshots) == 1

    def test_multiple(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        take_snapshot(conn)
        _insert_node(conn, "F2", "feature", "Feature 2")
        take_snapshot(conn)

        snapshots = get_latest_snapshots(conn, n=2)
        assert len(snapshots) == 2
        # Most recent first.
        assert snapshots[0].nodes_count == 2
        assert snapshots[1].nodes_count == 1

    def test_limit(self, conn: sqlite3.Connection) -> None:
        for _i in range(5):
            take_snapshot(conn)
        snapshots = get_latest_snapshots(conn, n=3)
        assert len(snapshots) == 3


class TestComputeTrend:
    def test_no_previous(self) -> None:
        current = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=2,
        )
        trends = compute_trend(current, None)
        assert trends == {}

    def test_no_change(self) -> None:
        snap = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=2,
        )
        trends = compute_trend(snap, snap)
        assert trends == {}

    def test_coverage_improved(self) -> None:
        prev = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=2,
        )
        curr = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=50.0,
            stale_count=1,
            isolated_count=2,
        )
        trends = compute_trend(curr, prev)
        assert "coverage_pct" in trends
        assert "▲" in trends["coverage_pct"]
        assert "+20%" in trends["coverage_pct"]

    def test_stale_increased(self) -> None:
        prev = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=2,
        )
        curr = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=3,
            isolated_count=2,
        )
        trends = compute_trend(curr, prev)
        # Stale increase is bad — should show down arrow.
        assert "▼" in trends["stale_count"]

    def test_isolated_decreased(self) -> None:
        prev = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=5,
        )
        curr = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=1,
            isolated_count=2,
        )
        trends = compute_trend(curr, prev)
        # Isolated decrease is good — should show up arrow.
        assert "▲" in trends["isolated_count"]

    def test_nodes_changed(self) -> None:
        prev = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=0,
            isolated_count=0,
        )
        curr = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=15,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=0,
            isolated_count=0,
        )
        trends = compute_trend(curr, prev)
        assert trends["nodes_count"] == "+5"

    def test_small_coverage_change_ignored(self) -> None:
        prev = HealthSnapshot(
            taken_at="2025-01-01",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.0,
            stale_count=0,
            isolated_count=0,
        )
        curr = HealthSnapshot(
            taken_at="2025-01-02",
            nodes_count=10,
            edges_count=5,
            docs_count=3,
            coverage_pct=30.3,
            stale_count=0,
            isolated_count=0,
        )
        trends = compute_trend(curr, prev)
        assert "coverage_pct" not in trends
