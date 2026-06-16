"""Tests for beadloom.infrastructure.repository — centralized graph-index reads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.infrastructure import repository as repo

if TYPE_CHECKING:
    import sqlite3


def _seed(conn: sqlite3.Connection) -> None:
    """Insert a small fixed graph: 1 domain + 2 children, edges, docs, sync, symbols."""
    conn.executemany(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        [
            ("dom", "domain", "A domain", "src/dom/"),
            ("feat", "feature", "A feature", "src/dom/feat.py"),
            ("comp", "component", "A component", None),
        ],
    )
    conn.executemany(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        [
            ("feat", "dom", "part_of"),
            ("comp", "dom", "part_of"),
            ("feat", "comp", "depends_on"),
        ],
    )
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        ("docs/dom.md", "domain", "dom", "h1"),
    )
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("docs/dom.md", "src/dom/feat.py", "feat", "x", "y", "now", "stale"),
    )
    conn.execute(
        "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, "
        "line_end, file_hash) VALUES (?, ?, ?, ?, ?, ?)",
        ("src/dom/feat.py", "do_thing", "function", 10, 20, "fh"),
    )
    conn.commit()


class TestNodeReads:
    def test_get_all_nodes_ordered(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        nodes = repo.get_all_nodes(schema_db)
        # ordered by kind, ref_id
        assert [(n.ref_id, n.kind, n.summary) for n in nodes] == [
            ("comp", "component", "A component"),
            ("dom", "domain", "A domain"),
            ("feat", "feature", "A feature"),
        ]

    def test_get_node(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        node = repo.get_node(schema_db, "dom")
        assert node is not None
        assert node.ref_id == "dom"
        assert node.kind == "domain"
        assert node.summary == "A domain"

    def test_get_node_missing(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.get_node(schema_db, "nope") is None

    def test_get_node_with_source(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        node = repo.get_node_with_source(schema_db, "feat")
        assert node is not None
        assert node.source == "src/dom/feat.py"

    def test_get_node_with_source_missing(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.get_node_with_source(schema_db, "nope") is None

    def test_get_nodes_by_kind(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        domains = repo.get_nodes_by_kind(schema_db, "domain")
        assert [n.ref_id for n in domains] == ["dom"]

    def test_get_source_paths(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        paths = repo.get_source_paths(schema_db)
        assert set(paths) == {"src/dom/", "src/dom/feat.py"}

    def test_get_node_sources(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        mapping = repo.get_node_sources(schema_db)
        assert mapping == {"dom": "src/dom/", "feat": "src/dom/feat.py"}


class TestEdgeReads:
    def test_get_all_edges_ordered(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        edges = repo.get_all_edges(schema_db)
        assert ("feat", "dom", "part_of") in {
            (e.src_ref_id, e.dst_ref_id, e.kind) for e in edges
        }
        # ordered by src_ref_id
        assert edges == sorted(edges, key=lambda e: e.src_ref_id)

    def test_get_part_of_children(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        children = repo.get_part_of_children(schema_db, "dom")
        assert {c.ref_id for c in children} == {"feat", "comp"}

    def test_get_outgoing_edges(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        out = repo.get_outgoing_edges(schema_db, "feat")
        assert {(e.dst_ref_id, e.kind) for e in out} == {
            ("dom", "part_of"),
            ("comp", "depends_on"),
        }

    def test_get_incoming_edges(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        inc = repo.get_incoming_edges(schema_db, "dom")
        assert {(e.src_ref_id, e.kind) for e in inc} == {
            ("feat", "part_of"),
            ("comp", "part_of"),
        }

    def test_count_edges_touching(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.count_edges_touching(schema_db, "dom") == 2


class TestDocReads:
    def test_get_doc_ref_ids(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.get_doc_ref_ids(schema_db) == {"dom"}

    def test_count_docs(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.count_docs(schema_db) == 1

    def test_count_docs_for_ref(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        assert repo.count_docs_for_ref(schema_db, "dom") == 1
        assert repo.count_docs_for_ref(schema_db, "feat") == 0

    def test_get_docs_for_ref(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        docs = repo.get_docs_for_ref(schema_db, "dom")
        assert docs == [("docs/dom.md", "domain")]


class TestSyncReads:
    def test_get_stale_pairs_for_ref(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        stale = repo.get_stale_pairs_for_ref(schema_db, "feat")
        assert stale == [("docs/dom.md", "src/dom/feat.py")]


class TestSymbolReads:
    def test_get_symbols_for_source(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        syms = repo.get_symbols_for_source(schema_db, "src/dom/feat.py")
        assert [(s.symbol_name, s.kind, s.line_start) for s in syms] == [
            ("do_thing", "function", 10)
        ]

    def test_get_symbols_for_source_dir_prefix(
        self, schema_db: sqlite3.Connection
    ) -> None:
        _seed(schema_db)
        # A directory source ("src/dom/") matches files beneath it.
        syms = repo.get_symbols_for_source(schema_db, "src/dom/")
        assert {s.symbol_name for s in syms} == {"do_thing"}


class TestSearchFallback:
    def test_search_nodes_like(self, schema_db: sqlite3.Connection) -> None:
        _seed(schema_db)
        results = repo.search_nodes_like(schema_db, "feat", limit=10)
        assert [n.ref_id for n in results] == ["feat"]
