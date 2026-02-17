"""Tests for beadloom.graph.snapshot — Architecture snapshot storage."""

from __future__ import annotations

import json
import sqlite3

import pytest

from beadloom.graph.snapshot import (
    SnapshotDiff,
    SnapshotInfo,
    compare_snapshots,
    list_snapshots,
    save_snapshot,
)
from beadloom.infrastructure.db import create_schema


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """Create an in-memory DB with full schema."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    create_schema(db)
    return db


@pytest.fixture()
def populated_conn(conn: sqlite3.Connection) -> sqlite3.Connection:
    """DB with sample nodes, edges, and symbols."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("auth-login", "feature", "User authentication"),
    )
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        ("user-service", "service", "User management"),
    )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("auth-login", "user-service", "uses"),
    )
    conn.execute(
        "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("auth.py", "login", "function", 1, 10, "abc123"),
    )
    conn.execute(
        "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("user.py", "UserService", "class", 1, 50, "def456"),
    )
    conn.commit()
    return conn


class TestSaveSnapshot:
    def test_save_returns_id(self, populated_conn: sqlite3.Connection) -> None:
        """save_snapshot returns a positive integer snapshot_id."""
        snap_id = save_snapshot(populated_conn)
        assert isinstance(snap_id, int)
        assert snap_id > 0

    def test_save_with_label(self, populated_conn: sqlite3.Connection) -> None:
        """save_snapshot stores the label."""
        snap_id = save_snapshot(populated_conn, label="v1.6.0")
        row = populated_conn.execute(
            "SELECT label FROM graph_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        assert row["label"] == "v1.6.0"

    def test_save_without_label(self, populated_conn: sqlite3.Connection) -> None:
        """save_snapshot stores NULL label when none given."""
        snap_id = save_snapshot(populated_conn)
        row = populated_conn.execute(
            "SELECT label FROM graph_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        assert row["label"] is None

    def test_save_captures_nodes_json(self, populated_conn: sqlite3.Connection) -> None:
        """Saved snapshot contains all nodes as JSON."""
        snap_id = save_snapshot(populated_conn)
        row = populated_conn.execute(
            "SELECT nodes_json FROM graph_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        nodes = json.loads(row["nodes_json"])
        assert len(nodes) == 2
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"auth-login", "user-service"}

    def test_save_captures_edges_json(self, populated_conn: sqlite3.Connection) -> None:
        """Saved snapshot contains all edges as JSON."""
        snap_id = save_snapshot(populated_conn)
        row = populated_conn.execute(
            "SELECT edges_json FROM graph_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        edges = json.loads(row["edges_json"])
        assert len(edges) == 1
        assert edges[0]["src_ref_id"] == "auth-login"
        assert edges[0]["dst_ref_id"] == "user-service"
        assert edges[0]["kind"] == "uses"

    def test_save_captures_symbols_count(self, populated_conn: sqlite3.Connection) -> None:
        """Saved snapshot records correct symbols count."""
        snap_id = save_snapshot(populated_conn)
        row = populated_conn.execute(
            "SELECT symbols_count FROM graph_snapshots WHERE id = ?", (snap_id,)
        ).fetchone()
        assert row["symbols_count"] == 2

    def test_save_empty_db(self, conn: sqlite3.Connection) -> None:
        """save_snapshot works on an empty database."""
        snap_id = save_snapshot(conn)
        row = conn.execute(
            "SELECT nodes_json, edges_json, symbols_count FROM graph_snapshots WHERE id = ?",
            (snap_id,),
        ).fetchone()
        assert json.loads(row["nodes_json"]) == []
        assert json.loads(row["edges_json"]) == []
        assert row["symbols_count"] == 0

    def test_save_multiple_snapshots(self, populated_conn: sqlite3.Connection) -> None:
        """Multiple snapshots get distinct IDs."""
        id1 = save_snapshot(populated_conn, label="first")
        id2 = save_snapshot(populated_conn, label="second")
        assert id1 != id2
        assert id2 > id1


class TestListSnapshots:
    def test_list_empty(self, conn: sqlite3.Connection) -> None:
        """list_snapshots returns empty list when no snapshots exist."""
        result = list_snapshots(conn)
        assert result == []

    def test_list_returns_snapshot_info(self, populated_conn: sqlite3.Connection) -> None:
        """list_snapshots returns SnapshotInfo objects."""
        save_snapshot(populated_conn, label="test-snap")
        result = list_snapshots(populated_conn)
        assert len(result) == 1
        snap = result[0]
        assert isinstance(snap, SnapshotInfo)
        assert snap.label == "test-snap"
        assert snap.node_count == 2
        assert snap.edge_count == 1
        assert snap.symbols_count == 2
        assert snap.created_at  # non-empty

    def test_list_ordered_by_created_at(self, populated_conn: sqlite3.Connection) -> None:
        """list_snapshots returns snapshots ordered by creation time (newest first)."""
        save_snapshot(populated_conn, label="first")
        save_snapshot(populated_conn, label="second")
        result = list_snapshots(populated_conn)
        assert len(result) == 2
        assert result[0].label == "second"
        assert result[1].label == "first"

    def test_list_multiple(self, populated_conn: sqlite3.Connection) -> None:
        """list_snapshots returns all saved snapshots."""
        for i in range(3):
            save_snapshot(populated_conn, label=f"snap-{i}")
        result = list_snapshots(populated_conn)
        assert len(result) == 3


class TestCompareSnapshots:
    def test_compare_no_changes(self, populated_conn: sqlite3.Connection) -> None:
        """Comparing identical snapshots returns empty diff."""
        id1 = save_snapshot(populated_conn, label="before")
        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert isinstance(diff, SnapshotDiff)
        assert diff.added_nodes == []
        assert diff.removed_nodes == []
        assert diff.changed_nodes == []
        assert diff.added_edges == []
        assert diff.removed_edges == []
        assert not diff.has_changes

    def test_compare_added_node(self, populated_conn: sqlite3.Connection) -> None:
        """Adding a node between snapshots is detected."""
        id1 = save_snapshot(populated_conn, label="before")

        # Add a node
        populated_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("billing", "domain", "Billing domain"),
        )
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert diff.has_changes
        assert len(diff.added_nodes) == 1
        assert diff.added_nodes[0]["ref_id"] == "billing"

    def test_compare_removed_node(self, populated_conn: sqlite3.Connection) -> None:
        """Removing a node between snapshots is detected."""
        id1 = save_snapshot(populated_conn, label="before")

        # Remove a node (and its edges due to CASCADE)
        populated_conn.execute("DELETE FROM edges WHERE src_ref_id = ?", ("auth-login",))
        populated_conn.execute("DELETE FROM nodes WHERE ref_id = ?", ("auth-login",))
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert diff.has_changes
        assert len(diff.removed_nodes) == 1
        assert diff.removed_nodes[0]["ref_id"] == "auth-login"

    def test_compare_changed_node(self, populated_conn: sqlite3.Connection) -> None:
        """Changing a node's summary between snapshots is detected."""
        id1 = save_snapshot(populated_conn, label="before")

        # Change summary
        populated_conn.execute(
            "UPDATE nodes SET summary = ? WHERE ref_id = ?",
            ("Updated auth flow", "auth-login"),
        )
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert diff.has_changes
        assert len(diff.changed_nodes) == 1
        changed = diff.changed_nodes[0]
        assert changed["ref_id"] == "auth-login"
        assert changed["old_summary"] == "User authentication"
        assert changed["new_summary"] == "Updated auth flow"

    def test_compare_added_edge(self, populated_conn: sqlite3.Connection) -> None:
        """Adding an edge between snapshots is detected."""
        id1 = save_snapshot(populated_conn, label="before")

        populated_conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            ("user-service", "auth-login", "depends_on"),
        )
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert diff.has_changes
        assert len(diff.added_edges) == 1
        assert diff.added_edges[0]["src_ref_id"] == "user-service"

    def test_compare_removed_edge(self, populated_conn: sqlite3.Connection) -> None:
        """Removing an edge between snapshots is detected."""
        id1 = save_snapshot(populated_conn, label="before")

        populated_conn.execute(
            "DELETE FROM edges WHERE src_ref_id = ? AND dst_ref_id = ?",
            ("auth-login", "user-service"),
        )
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")
        diff = compare_snapshots(populated_conn, id1, id2)
        assert diff.has_changes
        assert len(diff.removed_edges) == 1
        assert diff.removed_edges[0]["src_ref_id"] == "auth-login"

    def test_compare_nonexistent_snapshot(self, conn: sqlite3.Connection) -> None:
        """Comparing with a nonexistent snapshot raises ValueError."""
        snap_id = save_snapshot(conn)
        with pytest.raises(ValueError, match="not found"):
            compare_snapshots(conn, snap_id, 9999)

    def test_compare_reversed_ids(self, populated_conn: sqlite3.Connection) -> None:
        """Comparing in reversed order swaps added/removed."""
        id1 = save_snapshot(populated_conn, label="before")

        populated_conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("billing", "domain", "Billing domain"),
        )
        populated_conn.commit()

        id2 = save_snapshot(populated_conn, label="after")

        # Forward: billing is added
        diff_fwd = compare_snapshots(populated_conn, id1, id2)
        assert len(diff_fwd.added_nodes) == 1

        # Reverse: billing is removed
        diff_rev = compare_snapshots(populated_conn, id2, id1)
        assert len(diff_rev.removed_nodes) == 1
        assert diff_rev.removed_nodes[0]["ref_id"] == "billing"
