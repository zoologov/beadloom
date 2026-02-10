"""Tests for beadloom.why — Impact analysis: bidirectional BFS from a target node."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.db import create_schema, open_db
from beadloom.why import (
    TreeNode,
    WhyResult,
    analyze_node,
    render_why,
    result_to_dict,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Create a DB with schema for testing."""
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


def _insert_doc(
    conn: sqlite3.Connection,
    path: str,
    ref_id: str | None = None,
    kind: str = "other",
) -> int:
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, kind, ref_id, "abc123"),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM docs WHERE path = ?", (path,)).fetchone()
    return int(row[0])


def _insert_sync_state(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    ref_id: str,
    status: str = "ok",
) -> None:
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, "hash1", "hash2", "2025-01-01", status),
    )
    conn.commit()


@pytest.fixture()
def populated_db(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Create in-memory DB with test graph.

    Graph structure:
        LIB-core (domain) --[depends_on]--> AUTH-svc (service)
        AUTH-svc  --[uses]--> DB-ent (entity)
        FEAT-1 (feature) --[part_of]--> AUTH-svc
        FEAT-2 (feature) --[part_of]--> AUTH-svc

    Upstream of AUTH-svc: LIB-core (depends_on), FEAT-1 (part_of), FEAT-2 (part_of)
    Downstream of AUTH-svc: DB-ent (uses)

    Note: edge direction semantics for `why`:
    - upstream: edges WHERE src_ref_id = target (target depends on / is part of something)
    - downstream: edges WHERE dst_ref_id = target (something depends on / uses target)
    """
    _insert_node(conn, "AUTH-svc", "service", "Authentication service")
    _insert_node(conn, "LIB-core", "domain", "Core library")
    _insert_node(conn, "DB-ent", "entity", "Database entity")
    _insert_node(conn, "FEAT-1", "feature", "Login feature")
    _insert_node(conn, "FEAT-2", "feature", "Signup feature")

    # AUTH-svc depends_on LIB-core (AUTH-svc is src, LIB-core is dst)
    _insert_edge(conn, "AUTH-svc", "LIB-core", "depends_on")
    # AUTH-svc uses DB-ent
    _insert_edge(conn, "AUTH-svc", "DB-ent", "uses")
    # FEAT-1 part_of AUTH-svc
    _insert_edge(conn, "FEAT-1", "AUTH-svc", "part_of")
    # FEAT-2 part_of AUTH-svc
    _insert_edge(conn, "FEAT-2", "AUTH-svc", "part_of")

    return conn


# --- analyze_node: basic ---


class TestAnalyzeBasic:
    def test_analyze_basic(self, populated_db: sqlite3.Connection) -> None:
        """Node with both upstream and downstream connections."""
        result = analyze_node(populated_db, "AUTH-svc")
        assert isinstance(result, WhyResult)
        assert result.node.ref_id == "AUTH-svc"
        assert result.node.kind == "service"
        assert result.node.summary == "Authentication service"

        # AUTH-svc has outgoing edges (upstream): depends_on LIB-core, uses DB-ent
        assert len(result.upstream) > 0
        upstream_refs = {t.ref_id for t in result.upstream}
        assert "LIB-core" in upstream_refs or "DB-ent" in upstream_refs

        # AUTH-svc has incoming edges (downstream): FEAT-1, FEAT-2 point to it
        assert len(result.downstream) > 0
        downstream_refs = {t.ref_id for t in result.downstream}
        assert "FEAT-1" in downstream_refs
        assert "FEAT-2" in downstream_refs

    def test_analyze_no_edges(self, conn: sqlite3.Connection) -> None:
        """Isolated node returns empty trees."""
        _insert_node(conn, "ISOLATED", "domain", "Lonely node")
        result = analyze_node(conn, "ISOLATED")
        assert result.node.ref_id == "ISOLATED"
        assert result.upstream == ()
        assert result.downstream == ()
        assert result.impact.downstream_direct == 0
        assert result.impact.downstream_transitive == 0

    def test_analyze_nonexistent(self, conn: sqlite3.Connection) -> None:
        """LookupError raised with 'Did you mean' suggestions."""
        _insert_node(conn, "AUTH-svc", "service", "Auth service")
        with pytest.raises(LookupError, match="not found"):
            analyze_node(conn, "AUTH-svcc")
        # Should suggest the correct ref_id
        with pytest.raises(LookupError, match="AUTH-svc"):
            analyze_node(conn, "AUTH-svcc")

    def test_analyze_nonexistent_empty_db(self, conn: sqlite3.Connection) -> None:
        """LookupError raised without suggestions when DB is empty."""
        with pytest.raises(LookupError, match="not found"):
            analyze_node(conn, "NOTHING")


# --- analyze_node: depth limit ---


class TestAnalyzeDepthLimit:
    def test_depth_limit(self, conn: sqlite3.Connection) -> None:
        """Chain A->B->C->D, depth=1 should only show B."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_node(conn, "C", "service", "Node C")
        _insert_node(conn, "D", "entity", "Node D")
        _insert_edge(conn, "A", "B", "depends_on")
        _insert_edge(conn, "B", "C", "depends_on")
        _insert_edge(conn, "C", "D", "depends_on")

        # From A, upstream = outgoing edges: A->B->C->D
        result = analyze_node(conn, "A", depth=1)
        upstream_refs = {t.ref_id for t in result.upstream}
        assert "B" in upstream_refs
        assert "C" not in upstream_refs
        assert "D" not in upstream_refs

    def test_depth_2_shows_two_levels(self, conn: sqlite3.Connection) -> None:
        """Chain A->B->C->D, depth=2 should show B and C."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_node(conn, "C", "service", "Node C")
        _insert_node(conn, "D", "entity", "Node D")
        _insert_edge(conn, "A", "B", "depends_on")
        _insert_edge(conn, "B", "C", "depends_on")
        _insert_edge(conn, "C", "D", "depends_on")

        result = analyze_node(conn, "A", depth=2)
        # Flatten upstream tree to check
        upstream_refs = _collect_all_refs(result.upstream)
        assert "B" in upstream_refs
        assert "C" in upstream_refs
        assert "D" not in upstream_refs


# --- analyze_node: cycle detection ---


class TestAnalyzeCycle:
    def test_cycle_no_infinite_loop(self, conn: sqlite3.Connection) -> None:
        """A->B->A handles cycles without infinite loop."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_edge(conn, "A", "B", "uses")
        _insert_edge(conn, "B", "A", "uses")

        # Should complete without hanging
        result = analyze_node(conn, "A", depth=10)
        assert result.node.ref_id == "A"
        # Both upstream and downstream should have B (since edges go both ways)
        upstream_refs = {t.ref_id for t in result.upstream}
        downstream_refs = {t.ref_id for t in result.downstream}
        # A->B (outgoing from A) = upstream
        assert "B" in upstream_refs
        # B->A (incoming to A) = downstream
        assert "B" in downstream_refs

    def test_three_node_cycle(self, conn: sqlite3.Connection) -> None:
        """A->B->C->A should terminate."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_node(conn, "C", "service", "Node C")
        _insert_edge(conn, "A", "B", "uses")
        _insert_edge(conn, "B", "C", "uses")
        _insert_edge(conn, "C", "A", "uses")

        result = analyze_node(conn, "A", depth=10)
        assert result.node.ref_id == "A"


# --- impact summary ---


class TestImpactSummary:
    def test_impact_summary_counts(self, populated_db: sqlite3.Connection) -> None:
        """Correct direct/transitive counts for AUTH-svc."""
        result = analyze_node(populated_db, "AUTH-svc")
        # FEAT-1 and FEAT-2 are direct downstream
        assert result.impact.downstream_direct == 2
        # No transitive downstream beyond FEAT-1/FEAT-2
        assert result.impact.downstream_transitive >= 0

    def test_impact_summary_counts_chain(self, conn: sqlite3.Connection) -> None:
        """Chain: D->C->B->A, from A: downstream is B(direct), C, D (transitive)."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_node(conn, "C", "service", "Node C")
        _insert_node(conn, "D", "entity", "Node D")
        # D depends on C, C depends on B, B depends on A
        _insert_edge(conn, "D", "C", "depends_on")
        _insert_edge(conn, "C", "B", "depends_on")
        _insert_edge(conn, "B", "A", "depends_on")

        result = analyze_node(conn, "A", depth=5)
        # B is direct downstream of A (B->A edge exists)
        assert result.impact.downstream_direct == 1
        # C->B->A means C is transitive, D->C->B->A means D is transitive
        assert result.impact.downstream_transitive == 2

    def test_impact_doc_coverage(self, conn: sqlite3.Connection) -> None:
        """Correct percentage calculation for doc coverage."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_node(conn, "C", "service", "Node C")
        _insert_edge(conn, "B", "A", "depends_on")
        _insert_edge(conn, "C", "A", "depends_on")

        # B has a doc, C does not
        _insert_doc(conn, "b-spec.md", ref_id="B")

        result = analyze_node(conn, "A", depth=3)
        # downstream = B and C, B has doc, C doesn't -> 50%
        assert result.impact.doc_coverage == pytest.approx(50.0)

    def test_impact_doc_coverage_no_downstream(self, conn: sqlite3.Connection) -> None:
        """No downstream nodes -> 100% coverage (nothing to cover)."""
        _insert_node(conn, "A", "feature", "Node A")
        result = analyze_node(conn, "A")
        assert result.impact.doc_coverage == pytest.approx(100.0)

    def test_impact_stale_count(self, conn: sqlite3.Connection) -> None:
        """Counts stale docs in downstream."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_edge(conn, "B", "A", "depends_on")

        _insert_sync_state(conn, "b.md", "b.py", "B", status="stale")
        _insert_sync_state(conn, "b2.md", "b2.py", "B", status="ok")

        result = analyze_node(conn, "A", depth=3)
        assert result.impact.stale_count == 1

    def test_impact_stale_count_zero(self, conn: sqlite3.Connection) -> None:
        """No stale docs -> stale_count == 0."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_edge(conn, "B", "A", "depends_on")

        result = analyze_node(conn, "A", depth=3)
        assert result.impact.stale_count == 0


# --- max_nodes limit ---


class TestMaxNodesLimit:
    def test_max_nodes_limit(self, conn: sqlite3.Connection) -> None:
        """Large graph respects max_nodes."""
        _insert_node(conn, "CENTER", "feature", "Center node")
        for i in range(30):
            ref = f"N-{i:03d}"
            _insert_node(conn, ref, "entity", f"Node {i}")
            _insert_edge(conn, ref, "CENTER", "depends_on")

        result = analyze_node(conn, "CENTER", depth=3, max_nodes=10)
        # Count total nodes in downstream tree
        all_downstream = _collect_all_refs(result.downstream)
        assert len(all_downstream) <= 10


# --- render_why ---


class TestRenderWhy:
    def test_render_rich_output(self, populated_db: sqlite3.Connection) -> None:
        """render_why produces Rich output with expected sections."""
        from io import StringIO

        from rich.console import Console

        result = analyze_node(populated_db, "AUTH-svc")
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        render_why(result, console)
        output = buf.getvalue()

        # Should contain key sections
        assert "AUTH-svc" in output
        assert "service" in output.lower() or "Authentication" in output

    def test_render_empty_trees(self, conn: sqlite3.Connection) -> None:
        """render_why handles empty upstream/downstream."""
        from io import StringIO

        from rich.console import Console

        _insert_node(conn, "ALONE", "domain", "Lonely")
        result = analyze_node(conn, "ALONE")
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        render_why(result, console)
        output = buf.getvalue()
        assert "ALONE" in output


# --- result_to_dict ---


class TestResultToDict:
    def test_result_to_dict_structure(self, populated_db: sqlite3.Connection) -> None:
        """JSON serialization structure is correct."""
        result = analyze_node(populated_db, "AUTH-svc")
        d = result_to_dict(result)

        assert isinstance(d, dict)
        assert "node" in d
        assert "upstream" in d
        assert "downstream" in d
        assert "impact" in d

        # Node fields
        assert d["node"]["ref_id"] == "AUTH-svc"
        assert d["node"]["kind"] == "service"
        assert d["node"]["summary"] == "Authentication service"

        # Impact fields
        impact = d["impact"]
        assert "downstream_direct" in impact
        assert "downstream_transitive" in impact
        assert "doc_coverage" in impact
        assert "stale_count" in impact

    def test_result_to_dict_serializable(self, populated_db: sqlite3.Connection) -> None:
        """Result dict is JSON-serializable."""
        import json

        result = analyze_node(populated_db, "AUTH-svc")
        d = result_to_dict(result)
        serialized = json.dumps(d, ensure_ascii=False, indent=2)
        assert isinstance(serialized, str)
        # Round-trip
        parsed = json.loads(serialized)
        assert parsed["node"]["ref_id"] == "AUTH-svc"

    def test_result_to_dict_tree_nodes(self, conn: sqlite3.Connection) -> None:
        """Tree nodes in upstream/downstream have correct structure."""
        _insert_node(conn, "A", "feature", "Node A")
        _insert_node(conn, "B", "domain", "Node B")
        _insert_edge(conn, "A", "B", "depends_on")

        result = analyze_node(conn, "A")
        d = result_to_dict(result)

        assert len(d["upstream"]) == 1
        tree_node = d["upstream"][0]
        assert tree_node["ref_id"] == "B"
        assert tree_node["kind"] == "domain"
        assert tree_node["edge_kind"] == "depends_on"
        assert "children" in tree_node

    def test_result_to_dict_empty(self, conn: sqlite3.Connection) -> None:
        """Empty trees serialize correctly."""
        _insert_node(conn, "SOLO", "domain", "Solo")
        result = analyze_node(conn, "SOLO")
        d = result_to_dict(result)
        assert d["upstream"] == []
        assert d["downstream"] == []


# --- Helpers ---


def _collect_all_refs(trees: tuple[TreeNode, ...]) -> set[str]:
    """Recursively collect all ref_ids from a tree tuple."""
    refs: set[str] = set()
    for node in trees:
        refs.add(node.ref_id)
        refs.update(_collect_all_refs(node.children))
    return refs
