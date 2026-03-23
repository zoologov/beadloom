"""Tests for lifecycle-aware rule evaluation (BEAD-02, BDL-037 Principle 8).

``planned`` and ``deprecated`` edges represent intent that is not yet (or no
longer) live reality, so they must NOT count as live cycle / layer violations.
``active`` edges behave exactly as before (no regression).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    CycleRule,
    LayerDef,
    LayerRule,
    evaluate_cycle_rules,
    evaluate_layer_rules,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    conn = open_db(db_path)
    create_schema(conn)
    yield conn  # type: ignore[misc]
    conn.close()


def _node(conn: sqlite3.Connection, ref_id: str, kind: str = "domain") -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
        (ref_id, kind, f"{ref_id} node"),
    )


def _edge(
    conn: sqlite3.Connection,
    src: str,
    dst: str,
    kind: str = "depends_on",
    lifecycle: str = "active",
) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) VALUES (?, ?, ?, ?)",
        (src, dst, kind, lifecycle),
    )


def _tag(conn: sqlite3.Connection, ref_id: str, tag: str) -> None:
    import json

    conn.execute(
        "UPDATE nodes SET extra = ? WHERE ref_id = ?",
        (json.dumps({"tags": [tag]}), ref_id),
    )


# ---------------------------------------------------------------------------
# Cycle rules
# ---------------------------------------------------------------------------


class TestCycleLifecycle:
    def test_active_cycle_still_detected(self, db_conn: sqlite3.Connection) -> None:
        """No regression: an all-active cycle is still a violation."""
        _node(db_conn, "a")
        _node(db_conn, "b")
        _edge(db_conn, "a", "b")
        _edge(db_conn, "b", "a")
        db_conn.commit()
        rule = CycleRule(name="no-cycles", description="", edge_kind="depends_on")
        violations = evaluate_cycle_rules(db_conn, [rule])
        assert len(violations) == 1

    def test_planned_edge_breaks_cycle(self, db_conn: sqlite3.Connection) -> None:
        """A planned edge is not live, so the cycle is not a violation."""
        _node(db_conn, "a")
        _node(db_conn, "b")
        _edge(db_conn, "a", "b", lifecycle="active")
        _edge(db_conn, "b", "a", lifecycle="planned")
        db_conn.commit()
        rule = CycleRule(name="no-cycles", description="", edge_kind="depends_on")
        violations = evaluate_cycle_rules(db_conn, [rule])
        assert violations == []

    def test_deprecated_edge_breaks_cycle(self, db_conn: sqlite3.Connection) -> None:
        _node(db_conn, "a")
        _node(db_conn, "b")
        _edge(db_conn, "a", "b", lifecycle="deprecated")
        _edge(db_conn, "b", "a", lifecycle="active")
        db_conn.commit()
        rule = CycleRule(name="no-cycles", description="", edge_kind="depends_on")
        violations = evaluate_cycle_rules(db_conn, [rule])
        assert violations == []

    def test_dead_edge_breaks_cycle(self, db_conn: sqlite3.Connection) -> None:
        _node(db_conn, "a")
        _node(db_conn, "b")
        _edge(db_conn, "a", "b", lifecycle="active")
        _edge(db_conn, "b", "a", lifecycle="dead")
        db_conn.commit()
        rule = CycleRule(name="no-cycles", description="", edge_kind="depends_on")
        violations = evaluate_cycle_rules(db_conn, [rule])
        assert violations == []


# ---------------------------------------------------------------------------
# Layer rules
# ---------------------------------------------------------------------------


def _layer_rule() -> LayerRule:
    return LayerRule(
        name="layers",
        description="top-down only",
        layers=(LayerDef(name="upper", tag="upper"), LayerDef(name="lower", tag="lower")),
        enforce="top-down",
        edge_kind="depends_on",
    )


class TestLayerLifecycle:
    def test_active_layer_violation_detected(self, db_conn: sqlite3.Connection) -> None:
        """No regression: a live reverse-layer edge is still a violation."""
        _node(db_conn, "low")
        _node(db_conn, "up")
        _tag(db_conn, "low", "lower")
        _tag(db_conn, "up", "upper")
        _edge(db_conn, "low", "up", lifecycle="active")
        db_conn.commit()
        violations = evaluate_layer_rules(db_conn, [_layer_rule()])
        assert len(violations) == 1

    def test_planned_layer_edge_not_violation(self, db_conn: sqlite3.Connection) -> None:
        _node(db_conn, "low")
        _node(db_conn, "up")
        _tag(db_conn, "low", "lower")
        _tag(db_conn, "up", "upper")
        _edge(db_conn, "low", "up", lifecycle="planned")
        db_conn.commit()
        violations = evaluate_layer_rules(db_conn, [_layer_rule()])
        assert violations == []

    def test_deprecated_layer_edge_not_violation(self, db_conn: sqlite3.Connection) -> None:
        _node(db_conn, "low")
        _node(db_conn, "up")
        _tag(db_conn, "low", "lower")
        _tag(db_conn, "up", "upper")
        _edge(db_conn, "low", "up", lifecycle="deprecated")
        db_conn.commit()
        violations = evaluate_layer_rules(db_conn, [_layer_rule()])
        assert violations == []
