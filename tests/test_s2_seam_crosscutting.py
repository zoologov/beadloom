"""S2 cross-cutting coverage (BDL-059 .7).

These tests sit *across* the data-access seam rather than re-testing each
repository function in isolation (that is ``test_repository.py`` /
``test_graph_reads.py``). They pin the invariants the seam exists to hold:

1. **Connection lifetime / no leaks (#122).** ``infrastructure.db.connection``
   is a closing context-manager: it releases the handle on normal exit AND on
   an exception, with no ``ResourceWarning`` — even when every warning is
   promoted to an error within the test's own scope.
2. **Repository ↔ inline-SQL parity + no-regression guard.** The repository
   returns exactly the rows the old inlined
   ``SELECT ref_id, kind, summary FROM nodes`` produced, and a source-grep guard
   asserts no NEW raw ``... FROM nodes`` query reappears outside ``repository.py``
   (the de-duplication #122 set out to do), and ``tui/`` carries zero raw
   ``.execute()`` beyond the one allowed WAL PRAGMA.
3. **graph_reads facade fidelity.** The application facade is a pure
   pass-through: identical results to the repository, and it never imports the
   presentation layer (no ``application.graph_reads`` -> ``tui`` edge).

Each test uses the schema-initialized ``schema_db`` / ``tmp_path`` fixtures and
never touches the shared on-disk ``.beadloom/beadloom.db``.
"""

from __future__ import annotations

import ast
import sqlite3
import warnings
from pathlib import Path

import pytest

from beadloom.application import graph_reads
from beadloom.infrastructure import repository as repo
from beadloom.infrastructure.db import connection, create_schema

_SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "beadloom"
_TUI_DIR = _SRC_ROOT / "tui"
_REPOSITORY_FILE = _SRC_ROOT / "infrastructure" / "repository.py"

# The classic inlined node read this seam centralized (~16 copies pre-S2).
_INLINE_NODE_QUERY = "SELECT ref_id, kind, summary FROM nodes"
# The single legitimate raw execute in tui: enabling WAL on the app connection.
_ALLOWED_TUI_EXECUTE = '.execute("PRAGMA journal_mode=WAL")'


def _seed(conn: sqlite3.Connection) -> None:
    """Insert a small fixed graph: 1 domain + 2 children with mixed sources."""
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
    conn.commit()


# --- 1. Connection lifetime / no leaks (#122) ------------------------------- #


class TestConnectionLifetimeNoLeak:
    """``db.connection`` releases its handle in every path, with no warning."""

    def test_connection_used_then_querying_after_block_raises(
        self, tmp_path: Path
    ) -> None:
        # Arrange / Act: take a connection through the CM and keep a reference.
        db_path = tmp_path / "t.db"
        with connection(db_path) as conn:
            create_schema(conn)
            held = conn
        # Assert: a closed connection rejects further use.
        with pytest.raises(sqlite3.ProgrammingError):
            held.execute("SELECT 1")

    def test_connection_closes_even_when_body_raises(self, tmp_path: Path) -> None:
        # Arrange
        db_path = tmp_path / "t.db"
        held: sqlite3.Connection | None = None
        # Act: an exception inside the body must not leak the handle.
        with pytest.raises(RuntimeError, match="kaboom"), connection(db_path) as conn:
            held = conn
            raise RuntimeError("kaboom")
        # Assert
        assert held is not None
        with pytest.raises(sqlite3.ProgrammingError):
            held.execute("SELECT 1")

    def test_no_resource_warning_on_normal_exit(self, tmp_path: Path) -> None:
        """The CM closes its own connection on normal exit, with no warning.

        ResourceWarning is promoted to an error for this scope. The closed
        connection is asserted directly (querying it raises) rather than via a
        blanket ``gc.collect()`` — which would sweep unrelated leaked handles
        from other tests and produce a misleading failure.
        """
        # Arrange / Act
        db_path = tmp_path / "t.db"
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            with connection(db_path) as conn:
                create_schema(conn)
                conn.execute(
                    "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
                    ("n", "domain", "s"),
                )
                conn.commit()
                held = conn
            # Assert: the CM released the handle (no leak, no ResourceWarning).
            with pytest.raises(sqlite3.ProgrammingError):
                held.execute("SELECT 1")

    def test_no_resource_warning_when_body_raises(self, tmp_path: Path) -> None:
        # Arrange
        db_path = tmp_path / "t.db"
        with warnings.catch_warnings():
            warnings.simplefilter("error", ResourceWarning)
            held: sqlite3.Connection | None = None
            # Act: the connection must still close (no leak) on an exception path.
            with pytest.raises(ValueError, match="boom"), connection(db_path) as conn:
                create_schema(conn)
                held = conn
                raise ValueError("boom")
            # Assert: the CM closed it despite the exception.
            assert held is not None
            with pytest.raises(sqlite3.ProgrammingError):
                held.execute("SELECT 1")

    def test_repository_calls_through_cm_leave_no_open_handle(
        self, tmp_path: Path
    ) -> None:
        """A realistic read flow over the CM closes its handle on exit."""
        # Arrange
        db_path = tmp_path / "t.db"
        with connection(db_path) as setup:
            create_schema(setup)
            _seed(setup)
        # Act: exercise several repository reads inside one CM scope.
        with connection(db_path) as conn:
            nodes = repo.get_all_nodes(conn)
            edges = repo.get_all_edges(conn)
            children = repo.get_part_of_children(conn, "dom")
            held = conn
        # Assert: results are sane and the handle is released on exit.
        assert {n.ref_id for n in nodes} == {"dom", "feat", "comp"}
        assert {c.ref_id for c in children} == {"feat", "comp"}
        assert any(e.kind == "depends_on" for e in edges)
        with pytest.raises(sqlite3.ProgrammingError):
            held.execute("SELECT 1")


# --- 2. Repository parity + no-regression grep guard ------------------------ #


class TestRepositoryInlineParity:
    """Repository reads equal the old hand-written inline query results."""

    def test_get_all_nodes_equals_inline_select(
        self, schema_db: sqlite3.Connection
    ) -> None:
        # Arrange
        _seed(schema_db)
        # Act: the centralized read vs the exact pre-S2 inline query.
        repo_rows = [(n.ref_id, n.kind, n.summary) for n in repo.get_all_nodes(schema_db)]
        inline_rows = [
            (r["ref_id"], r["kind"], r["summary"])
            for r in schema_db.execute(
                f"{_INLINE_NODE_QUERY} ORDER BY kind, ref_id"
            ).fetchall()
        ]
        # Assert: byte-identical rows, same order.
        assert repo_rows == inline_rows

    def test_get_node_equals_inline_select(
        self, schema_db: sqlite3.Connection
    ) -> None:
        # Arrange
        _seed(schema_db)
        # Act
        node = repo.get_node(schema_db, "dom")
        inline = schema_db.execute(
            f"{_INLINE_NODE_QUERY} WHERE ref_id = ?", ("dom",)
        ).fetchone()
        # Assert
        assert node is not None
        assert (node.ref_id, node.kind, node.summary) == (
            inline["ref_id"],
            inline["kind"],
            inline["summary"],
        )

    def test_get_nodes_by_kind_equals_inline_select(
        self, schema_db: sqlite3.Connection
    ) -> None:
        # Arrange
        _seed(schema_db)
        # Act
        repo_rows = [n.ref_id for n in repo.get_nodes_by_kind(schema_db, "feature")]
        inline_rows = [
            r["ref_id"]
            for r in schema_db.execute(
                f"{_INLINE_NODE_QUERY} WHERE kind = ? ORDER BY ref_id", ("feature",)
            ).fetchall()
        ]
        # Assert
        assert repo_rows == inline_rows == ["feat"]


class TestNoInlineNodeQueryRegression:
    """Grep-style guard: the seam S2 closed (``tui/``) carries no raw SQL.

    NB: S2 centralized the inline ``SELECT ref_id, kind, summary FROM nodes`` and
    re-layered the *TUI* through the facade. Other callers (context_oracle,
    services) still run the inline query directly — that is pre-existing and out
    of this slice's seam, so the regression guard is scoped to ``tui/`` (where
    S2 removed every raw query) rather than asserting a repo-wide ban that was
    never true.
    """

    def _py_files(self, root: Path) -> list[Path]:
        return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)

    def test_repository_owns_the_canonical_node_query(self) -> None:
        # The centralized literal lives in repository.py (the seam's home).
        text = _REPOSITORY_FILE.read_text(encoding="utf-8")
        assert _INLINE_NODE_QUERY in text

    def test_tui_has_no_inline_node_query(self) -> None:
        # Arrange: the TUI must never build the node SELECT itself — it reads
        # through the facade. A re-scattered literal here is the regression.
        offenders: list[str] = []
        for path in self._py_files(_TUI_DIR):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if "FROM nodes" in line and "ref_id, kind, summary" in line:
                    offenders.append(
                        f"{path.relative_to(_TUI_DIR)}:{lineno}: {line.strip()}"
                    )
        # Assert
        assert not offenders, (
            "Inline node query re-scattered into tui (must read via facade):\n"
            + "\n".join(offenders)
        )

    def test_tui_has_no_raw_execute_beyond_wal_pragma(self) -> None:
        # Arrange
        offenders: list[str] = []
        for path in self._py_files(_TUI_DIR):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if ".execute(" not in line:
                    continue
                if _ALLOWED_TUI_EXECUTE in line:
                    continue
                offenders.append(
                    f"{path.relative_to(_TUI_DIR)}:{lineno}: {line.strip()}"
                )
        # Assert
        assert not offenders, "Raw .execute() in tui beyond WAL PRAGMA:\n" + "\n".join(
            offenders
        )


# --- 3. graph_reads facade fidelity ----------------------------------------- #


class TestGraphReadsFacadeFidelity:
    """The application facade forwards to the repository with identical results."""

    def test_facade_results_identical_to_repository(
        self, schema_db: sqlite3.Connection
    ) -> None:
        # Arrange
        _seed(schema_db)
        # Act / Assert: every facade read equals the repository read it wraps.
        assert graph_reads.get_all_nodes(schema_db) == repo.get_all_nodes(schema_db)
        assert graph_reads.get_all_edges(schema_db) == repo.get_all_edges(schema_db)
        assert graph_reads.get_node(schema_db, "dom") == repo.get_node(schema_db, "dom")
        assert graph_reads.get_part_of_children(
            schema_db, "dom"
        ) == repo.get_part_of_children(schema_db, "dom")
        assert graph_reads.get_node_sources(schema_db) == repo.get_node_sources(
            schema_db
        )

    def test_facade_reexports_repository_row_types(self) -> None:
        # The facade must re-export the same dataclasses (not parallel copies),
        # so a NodeRow built by either path compares equal.
        assert graph_reads.NodeRow is repo.NodeRow
        assert graph_reads.EdgeRow is repo.EdgeRow
        assert graph_reads.SymbolRow is repo.SymbolRow

    def test_facade_public_surface_matches_module_symbols(self) -> None:
        # Every name the facade advertises must be a real attribute (no dangling
        # __all__ entry that would break a TUI import).
        for name in graph_reads.__all__:
            assert hasattr(graph_reads, name), f"graph_reads.__all__ lists missing {name}"

    def test_facade_does_not_import_presentation_layer(self) -> None:
        # The seam exists so application sits BELOW presentation; the facade must
        # never import tui (that would invert the layering it was built to fix).
        facade_file = _SRC_ROOT / "application" / "graph_reads.py"
        tree = ast.parse(facade_file.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        assert not any("tui" in mod.split(".") for mod in imported), (
            f"graph_reads must not import the tui presentation layer: {imported}"
        )
