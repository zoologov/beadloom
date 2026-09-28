"""Tests for beadloom.application.graph_reads — the TUI read facade.

The facade is the seam that lets ``tui`` read the graph index without importing
``infrastructure`` directly (the ``tui-no-direct-infra`` boundary). It delegates
to ``infrastructure.repository`` and returns the same typed rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.application import graph_reads

if TYPE_CHECKING:
    import sqlite3


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        [
            ("dom", "domain", "A domain", "src/dom/"),
            ("feat", "feature", "A feature", "src/dom/feat.py"),
        ],
    )
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        ("feat", "dom", "part_of"),
    )
    conn.commit()


def test_get_all_nodes(schema_db: sqlite3.Connection) -> None:
    _seed(schema_db)
    nodes = graph_reads.get_all_nodes(schema_db)
    assert {n.ref_id for n in nodes} == {"dom", "feat"}


def test_get_node(schema_db: sqlite3.Connection) -> None:
    _seed(schema_db)
    node = graph_reads.get_node(schema_db, "dom")
    assert node is not None and node.kind == "domain"


def test_get_all_edges(schema_db: sqlite3.Connection) -> None:
    _seed(schema_db)
    edges = graph_reads.get_all_edges(schema_db)
    assert ("feat", "dom", "part_of") in {
        (e.src_ref_id, e.dst_ref_id, e.kind) for e in edges
    }


def test_count_docs(schema_db: sqlite3.Connection) -> None:
    _seed(schema_db)
    assert graph_reads.count_docs(schema_db) == 0
