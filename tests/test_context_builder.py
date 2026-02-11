"""Tests for beadloom.context_builder — BFS subgraph + context bundle assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.context_builder import (
    bfs_subgraph,
    build_context,
    collect_chunks,
    suggest_ref_id,
)
from beadloom.db import create_schema, open_db

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Create an in-memory-like DB with schema."""
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


def _insert_chunk(
    conn: sqlite3.Connection,
    doc_id: int,
    chunk_index: int,
    heading: str,
    section: str,
    content: str,
    node_ref_id: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO chunks (doc_id, chunk_index, heading, section, content, node_ref_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (doc_id, chunk_index, heading, section, content, node_ref_id),
    )
    conn.commit()


# --- suggest_ref_id ---


class TestSuggestRefId:
    def test_exact_match(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "PROJ-123", "feature", "Feature")
        result = suggest_ref_id(conn, "PROJ-123")
        assert result == []

    def test_suggestions(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "PROJ-123", "feature", "Feature 123")
        _insert_node(conn, "PROJ-124", "feature", "Feature 124")
        _insert_node(conn, "PROJ-132", "feature", "Feature 132")
        _insert_node(conn, "TOTALLY-DIFFERENT", "domain", "Other")
        result = suggest_ref_id(conn, "PROJ-125")
        # Should suggest close matches
        assert len(result) > 0
        assert "PROJ-123" in result or "PROJ-124" in result

    def test_empty_db(self, conn: sqlite3.Connection) -> None:
        result = suggest_ref_id(conn, "anything")
        assert result == []

    def test_max_suggestions(self, conn: sqlite3.Connection) -> None:
        for i in range(20):
            _insert_node(conn, f"N-{i:03d}", "feature", f"Node {i}")
        result = suggest_ref_id(conn, "N-000")
        assert len(result) <= 5

    def test_prefix_match_short_input(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "mcp-server", "service", "MCP Server")
        result = suggest_ref_id(conn, "mcp")
        assert result == ["mcp-server"]

    def test_prefix_match_case_insensitive(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "mcp-server", "service", "MCP Server")
        result = suggest_ref_id(conn, "MCP")
        assert result == ["mcp-server"]

    def test_reverse_prefix_match(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "mcp", "domain", "MCP domain")
        result = suggest_ref_id(conn, "mcp-server-v2")
        assert "mcp" in result

    def test_prefix_and_levenshtein_combined(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "mcp-server", "service", "MCP Server")
        _insert_node(conn, "mcq", "domain", "MCQ domain")
        result = suggest_ref_id(conn, "mcp")
        assert result[0] == "mcp-server"  # prefix match first
        assert "mcq" in result  # levenshtein match also present

    def test_prefix_match_no_false_positives(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "xyz-server", "service", "XYZ Server")
        result = suggest_ref_id(conn, "abc")
        assert result == []


# --- bfs_subgraph ---


class TestBfsSubgraph:
    def test_single_node_no_edges(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "Node A")
        nodes, edges = bfs_subgraph(conn, ["A"], depth=2, max_nodes=20)
        assert len(nodes) == 1
        assert nodes[0]["ref_id"] == "A"
        assert edges == []

    def test_outgoing_edges(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "Feature A")
        _insert_node(conn, "B", "domain", "Domain B")
        _insert_edge(conn, "A", "B", "part_of")
        nodes, edges = bfs_subgraph(conn, ["A"], depth=1, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"A", "B"}
        assert len(edges) == 1

    def test_incoming_edges(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "Feature A")
        _insert_node(conn, "B", "domain", "Domain B")
        _insert_edge(conn, "B", "A", "part_of")
        nodes, _edges = bfs_subgraph(conn, ["A"], depth=1, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"A", "B"}

    def test_depth_limit(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        _insert_node(conn, "C", "service", "C")
        _insert_edge(conn, "A", "B", "part_of")
        _insert_edge(conn, "B", "C", "uses")

        # depth=1 should NOT reach C
        nodes, _ = bfs_subgraph(conn, ["A"], depth=1, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert "C" not in ref_ids

        # depth=2 should reach C
        nodes, _ = bfs_subgraph(conn, ["A"], depth=2, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert "C" in ref_ids

    def test_max_nodes_limit(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "A")
        for i in range(10):
            _insert_node(conn, f"N{i}", "entity", f"Node {i}")
            _insert_edge(conn, "A", f"N{i}", "touches_entity")

        nodes, _ = bfs_subgraph(conn, ["A"], depth=1, max_nodes=5)
        assert len(nodes) <= 5

    def test_edge_priority_ordering(self, conn: sqlite3.Connection) -> None:
        """part_of edges should be explored before touches_code."""
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        _insert_node(conn, "C", "entity", "C")
        _insert_edge(conn, "A", "C", "touches_code")
        _insert_edge(conn, "A", "B", "part_of")

        nodes, _ = bfs_subgraph(conn, ["A"], depth=1, max_nodes=3)
        ref_ids = {n["ref_id"] for n in nodes}
        # Both should be reached within limit of 3 (A + B + C)
        assert "B" in ref_ids

    def test_multiple_focus_nodes(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "feature", "B")
        _insert_node(conn, "C", "domain", "C")
        _insert_edge(conn, "A", "C", "part_of")
        _insert_edge(conn, "B", "C", "part_of")

        nodes, _ = bfs_subgraph(conn, ["A", "B"], depth=1, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"A", "B", "C"}

    def test_cycle_handling(self, conn: sqlite3.Connection) -> None:
        """BFS should not loop on cycles."""
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        _insert_edge(conn, "A", "B", "uses")
        _insert_edge(conn, "B", "A", "uses")

        nodes, _ = bfs_subgraph(conn, ["A"], depth=5, max_nodes=20)
        ref_ids = {n["ref_id"] for n in nodes}
        assert ref_ids == {"A", "B"}

    def test_no_duplicates(self, conn: sqlite3.Connection) -> None:
        """Nodes should not be duplicated even if reachable via multiple paths."""
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        _insert_node(conn, "C", "service", "C")
        _insert_edge(conn, "A", "B", "part_of")
        _insert_edge(conn, "A", "C", "uses")
        _insert_edge(conn, "B", "C", "uses")

        nodes, _ = bfs_subgraph(conn, ["A"], depth=2, max_nodes=20)
        ref_ids = [n["ref_id"] for n in nodes]
        assert len(ref_ids) == len(set(ref_ids))


# --- collect_chunks ---


class TestCollectChunks:
    def test_basic_collection(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        doc_id = _insert_doc(conn, "spec.md", ref_id="F1")
        _insert_chunk(conn, doc_id, 0, "Overview", "spec", "Content here")

        chunks = collect_chunks(conn, {"F1"}, max_chunks=10)
        assert len(chunks) == 1
        assert chunks[0]["heading"] == "Overview"

    def test_section_priority_ordering(self, conn: sqlite3.Connection) -> None:
        """spec chunks should come before 'other' chunks."""
        _insert_node(conn, "F1", "feature", "Feature 1")
        doc_id = _insert_doc(conn, "doc.md", ref_id="F1")
        _insert_chunk(conn, doc_id, 0, "Tests", "tests", "Test content")
        _insert_chunk(conn, doc_id, 1, "Spec", "spec", "Spec content")
        _insert_chunk(conn, doc_id, 2, "Other", "other", "Other content")

        chunks = collect_chunks(conn, {"F1"}, max_chunks=10)
        sections = [c["section"] for c in chunks]
        assert sections.index("spec") < sections.index("tests")
        assert sections.index("tests") < sections.index("other")

    def test_max_chunks_limit(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        doc_id = _insert_doc(conn, "big.md", ref_id="F1")
        for i in range(20):
            _insert_chunk(conn, doc_id, i, f"Heading {i}", "other", f"Content {i}")

        chunks = collect_chunks(conn, {"F1"}, max_chunks=5)
        assert len(chunks) == 5

    def test_no_matching_docs(self, conn: sqlite3.Connection) -> None:
        chunks = collect_chunks(conn, {"nonexistent"}, max_chunks=10)
        assert chunks == []

    def test_multiple_ref_ids(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "F1", "feature", "Feature 1")
        _insert_node(conn, "F2", "feature", "Feature 2")
        doc1 = _insert_doc(conn, "spec1.md", ref_id="F1")
        doc2 = _insert_doc(conn, "spec2.md", ref_id="F2")
        _insert_chunk(conn, doc1, 0, "H1", "spec", "Content 1")
        _insert_chunk(conn, doc2, 0, "H2", "spec", "Content 2")

        chunks = collect_chunks(conn, {"F1", "F2"}, max_chunks=10)
        assert len(chunks) == 2


# --- build_context ---


class TestBuildContext:
    def _setup_graph(self, conn: sqlite3.Connection) -> None:
        """Set up a minimal graph with docs and code."""
        _insert_node(conn, "PROJ-1", "feature", "Track filtering")
        _insert_node(conn, "routing", "domain", "Routing domain")
        _insert_node(conn, "api-gw", "service", "API Gateway")
        _insert_edge(conn, "PROJ-1", "routing", "part_of")
        _insert_edge(conn, "PROJ-1", "api-gw", "uses")

        doc_id = _insert_doc(conn, "spec.md", ref_id="PROJ-1", kind="feature")
        _insert_chunk(conn, doc_id, 0, "Business rules", "spec", "Must filter by date.")

        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "src/api.py",
                "list_tracks",
                "function",
                10,
                80,
                '{"feature": "PROJ-1"}',
                "hash123",
            ),
        )
        conn.commit()

    def test_bundle_structure(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        assert bundle["version"] == 2
        assert "focus" in bundle
        assert "graph" in bundle
        assert "text_chunks" in bundle
        assert "code_symbols" in bundle
        assert "sync_status" in bundle
        assert "constraints" in bundle
        assert "warning" in bundle

    def test_focus_field(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        focus = bundle["focus"]
        assert focus["ref_id"] == "PROJ-1"
        assert focus["kind"] == "feature"
        assert focus["summary"] == "Track filtering"

    def test_graph_nodes_and_edges(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        graph = bundle["graph"]
        node_ids = {n["ref_id"] for n in graph["nodes"]}
        assert "PROJ-1" in node_ids
        assert "routing" in node_ids
        assert len(graph["edges"]) >= 1

    def test_text_chunks_included(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        chunks = bundle["text_chunks"]
        assert len(chunks) >= 1
        assert chunks[0]["heading"] == "Business rules"

    def test_code_symbols_included(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        symbols = bundle["code_symbols"]
        assert len(symbols) >= 1
        assert symbols[0]["symbol_name"] == "list_tracks"

    def test_sync_status_default(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        assert bundle["sync_status"]["stale_docs"] == []

    def test_warning_null_by_default(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        bundle = build_context(conn, ["PROJ-1"])
        assert bundle["warning"] is None

    def test_ref_id_not_found_raises(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(LookupError, match="not found"):
            build_context(conn, ["NONEXISTENT"])

    def test_ref_id_not_found_with_suggestion(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "PROJ-123", "feature", "Feature")
        with pytest.raises(LookupError, match="PROJ-123"):
            build_context(conn, ["PROJ-124"])

    def test_multiple_focus_nodes(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        bundle = build_context(conn, ["A", "B"])
        # Focus should be first ref_id
        assert bundle["focus"]["ref_id"] == "A"
        node_ids = {n["ref_id"] for n in bundle["graph"]["nodes"]}
        assert "A" in node_ids
        assert "B" in node_ids

    def test_stale_sync_state(self, conn: sqlite3.Connection) -> None:
        self._setup_graph(conn)
        conn.execute(
            "INSERT INTO sync_state "
            "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
            "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spec.md", "src/api.py", "PROJ-1", "old", "old", "2025-01-01", "stale"),
        )
        conn.commit()
        bundle = build_context(conn, ["PROJ-1"])
        assert len(bundle["sync_status"]["stale_docs"]) >= 1

    def test_depth_parameter(self, conn: sqlite3.Connection) -> None:
        _insert_node(conn, "A", "feature", "A")
        _insert_node(conn, "B", "domain", "B")
        _insert_node(conn, "C", "service", "C")
        _insert_edge(conn, "A", "B", "part_of")
        _insert_edge(conn, "B", "C", "uses")

        bundle_d1 = build_context(conn, ["A"], depth=1)
        bundle_d2 = build_context(conn, ["A"], depth=2)
        nodes_d1 = {n["ref_id"] for n in bundle_d1["graph"]["nodes"]}
        nodes_d2 = {n["ref_id"] for n in bundle_d2["graph"]["nodes"]}
        assert "C" not in nodes_d1
        assert "C" in nodes_d2

    def test_stale_index_warning(self, conn: sqlite3.Connection, tmp_path: Path) -> None:
        """If last_reindex_at is set, warning should be null (no staleness check without files)."""
        self._setup_graph(conn)
        from beadloom.db import set_meta

        set_meta(conn, "last_reindex_at", "2025-01-01T00:00:00+00:00")
        bundle = build_context(conn, ["PROJ-1"])
        # Without actual file mtime check, warning should be None
        assert bundle["warning"] is None
