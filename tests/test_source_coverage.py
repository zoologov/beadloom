"""Tests for check_source_coverage — untracked file detection via nodes.source dirs."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import check_source_coverage
from beadloom.infrastructure.db import create_schema, open_db
from tests.support.source_coverage_rows import (
    insert_code_symbol,
    insert_doc,
    insert_edge,
    insert_node,
    insert_sync_state,
    legacy_check_source_coverage,
)

if TYPE_CHECKING:
    import sqlite3
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project directory with docs/ and src/ for coverage tests."""
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / "src" / "mymodule").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> sqlite3.Connection:
    db_path = project / ".beadloom" / "test.db"
    c = open_db(db_path)
    create_schema(c)
    return c


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


class TestSourceCoverageAllTracked:
    """Node with source dir where all files are tracked -> empty result."""

    def test_all_files_tracked_via_sync_state(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via sync_state
        insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_files_tracked_via_code_symbols(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via code_symbols (annotated with ref_id)
        insert_code_symbol(conn, "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageUntracked:
    """Node with new untracked file -> detected."""

    def test_untracked_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Create two files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "src" / "mymodule" / "new_feature.py").write_text("def new(): pass\n")

        # Only track handler.py
        insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mymod"
        assert results[0]["doc_path"] == "mymodule.md"
        assert "src/mymodule/new_feature.py" in results[0]["untracked_files"]

    def test_untracked_file_relative_path(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Untracked files should be reported as relative paths."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "utils.py").write_text("X = 1\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        # Path should be relative, not absolute
        for path in results[0]["untracked_files"]:
            assert not path.startswith("/")


class TestSourceCoverageExclusions:
    """Exclusions work: __init__.py, conftest.py, __main__.py are ignored."""

    def test_init_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Only excluded files on disk
        (project / "src" / "mymodule" / "__init__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_conftest_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "conftest.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_main_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_exclusions_combined(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__init__.py").write_text("")
        (project / "src" / "mymodule" / "conftest.py").write_text("")
        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_excluded_files_ignored_but_real_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__init__.py").write_text("")
        (project / "src" / "mymodule" / "real_code.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/real_code.py" in results[0]["untracked_files"]
        # Excluded files should NOT appear
        untracked = results[0]["untracked_files"]
        assert all("__init__" not in f for f in untracked)


class TestSourceCoverageFileSource:
    """Node with file source (not dir, doesn't end in /) -> skipped."""

    def test_file_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Source points to a single file, not a directory
        insert_node(conn, "mymod", "src/mymodule/handler.py")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "src" / "mymodule" / "untracked.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageNoNodes:
    """No nodes -> empty result."""

    def test_empty_db(self, conn: sqlite3.Connection, project: Path) -> None:
        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageMissingDir:
    """Source directory doesn't exist on disk -> skipped gracefully."""

    def test_nonexistent_dir_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/nonexistent/")
        insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageMultipleNodes:
    """Multiple nodes with mixed results."""

    def test_mixed_results(self, conn: sqlite3.Connection, project: Path) -> None:
        # Node 1: all tracked (no gaps)
        insert_node(conn, "mod-a", "src/mod_a/")
        insert_doc(conn, "mod_a.md", "mod-a")
        (project / "src" / "mod_a").mkdir(parents=True)
        (project / "src" / "mod_a" / "tracked.py").write_text("x = 1\n")
        insert_sync_state(conn, "mod_a.md", "src/mod_a/tracked.py", "mod-a")

        # Node 2: has untracked file
        insert_node(conn, "mod-b", "src/mod_b/")
        insert_doc(conn, "mod_b.md", "mod-b")
        (project / "src" / "mod_b").mkdir(parents=True)
        (project / "src" / "mod_b" / "tracked.py").write_text("y = 1\n")
        (project / "src" / "mod_b" / "untracked.py").write_text("z = 1\n")
        insert_sync_state(conn, "mod_b.md", "src/mod_b/tracked.py", "mod-b")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mod-b"
        assert "src/mod_b/untracked.py" in results[0]["untracked_files"]

    def test_node_without_doc_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with source dir but no linked doc -> skipped."""
        insert_node(conn, "mymod", "src/mymodule/")
        # No doc inserted for this node

        (project / "src" / "mymodule" / "code.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_node_with_null_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with NULL source -> skipped."""
        insert_node(conn, "mymod", None)
        insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageHierarchy:
    """Hierarchy-aware coverage: child part_of edges are considered."""

    def test_child_feature_tracked_via_hierarchy(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File annotated to child feature (part_of parent) should NOT be
        flagged as untracked for parent domain."""
        # Parent node owns the source directory
        insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        insert_doc(conn, "infrastructure.md", "infrastructure")

        # Child node is part_of parent
        insert_node(conn, "doctor", None, kind="feature")
        insert_edge(conn, "doctor", "infrastructure", "part_of")

        # Create file on disk inside parent's source dir
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )

        # File annotated to the *child* ref_id, not the parent
        insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")

        results = check_source_coverage(conn, project)
        # Should be empty: child annotation covers the file
        assert results == []

    def test_truly_untracked_not_hidden_by_hierarchy(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File NOT annotated to any child feature should still be flagged."""
        insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        insert_doc(conn, "infrastructure.md", "infrastructure")

        insert_node(conn, "doctor", None, kind="feature")
        insert_edge(conn, "doctor", "infrastructure", "part_of")

        # Two files on disk
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )
        (project / "src" / "mymodule" / "orphan.py").write_text(
            "def orphan(): pass\n"
        )

        # Only doctor.py is annotated to the child feature
        insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "infrastructure"
        assert "src/mymodule/orphan.py" in results[0]["untracked_files"]
        # doctor.py should NOT be in untracked
        assert "src/mymodule/doctor.py" not in results[0]["untracked_files"]

    def test_no_children_works_as_before(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with no part_of children still works — no regression."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "handler.py").write_text(
            "def handler(): pass\n"
        )

        # Track directly via sync_state on the parent
        insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_multiple_children_all_counted(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Multiple child features — files from different children all counted."""
        insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        insert_doc(conn, "infrastructure.md", "infrastructure")

        # Two child features
        insert_node(conn, "doctor", None, kind="feature")
        insert_edge(conn, "doctor", "infrastructure", "part_of")

        insert_node(conn, "linter", None, kind="feature")
        insert_edge(conn, "linter", "infrastructure", "part_of")

        # Files on disk
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )
        (project / "src" / "mymodule" / "linter.py").write_text(
            "def run_lint(): pass\n"
        )

        # Each file annotated to its respective child feature
        insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")
        insert_code_symbol(
            conn, "src/mymodule/linter.py", "linter", symbol_name="run_lint"
        )

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageFileAnnotation:
    """#89: file-level beadloom annotation tracks symbol-less files.

    A file with a module-level ``# beadloom:domain=X`` comment but NO
    extractable top-level symbol (e.g. a pure constants/config module)
    produces zero ``code_symbols`` rows and would otherwise be reported as
    untracked. The annotation is the explicit ownership signal and must
    count as tracked.
    """

    def test_symbolless_annotated_file_is_tracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Pure-constants file: annotated, but tree-sitter extracts no symbol,
        # so it never lands in code_symbols.
        (project / "src" / "mymodule" / "constants.py").write_text(
            "# beadloom:domain=mymod\n\nMAX_SIZE = 100\nNAME = 'broker'\n"
        )

        results = check_source_coverage(conn, project)
        assert results == [], (
            f"Annotated symbol-less file should be tracked, got: {results}"
        )

    def test_feature_annotation_also_tracks(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A ``# beadloom:feature=X`` annotation also counts as tracking."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "config.py").write_text(
            "# beadloom:feature=mymod\nSETTINGS = {}\n"
        )

        results = check_source_coverage(conn, project)
        assert results == []

    def test_annotation_to_other_node_still_untracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A file annotated to a DIFFERENT node is still untracked here."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "constants.py").write_text(
            "# beadloom:domain=somewhere-else\nVALUE = 1\n"
        )

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/constants.py" in results[0]["untracked_files"]

    def test_unannotated_symbolless_file_still_untracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A symbol-less file with NO annotation remains untracked (honest)."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "data.py").write_text("X = 1\nY = 2\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/data.py" in results[0]["untracked_files"]

    def test_annotation_to_child_feature_tracks(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File annotated to a child feature (part_of parent) is tracked."""
        insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        insert_doc(conn, "infrastructure.md", "infrastructure")
        insert_node(conn, "doctor", None, kind="feature")
        insert_edge(conn, "doctor", "infrastructure", "part_of")

        # Symbol-less file annotated to the child feature.
        (project / "src" / "mymodule" / "doctor_constants.py").write_text(
            "# beadloom:feature=doctor\nDEFAULT = 5\n"
        )

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageTrackMarker:
    """#90: ``<!-- beadloom:track=path -->`` doc markers bind files to docs."""

    def test_track_marker_makes_file_tracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        # Symbol-less, UNannotated file on disk.
        (project / "src" / "mymodule" / "constants.py").write_text("X = 1\n")

        # Doc on disk explicitly binds the file via a track marker.
        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\n"
            "<!-- beadloom:track=src/mymodule/constants.py -->\n"
            "Describes constants.\n"
        )

        results = check_source_coverage(conn, project)
        assert results == [], (
            f"File bound via track marker should be tracked, got: {results}"
        )

    def test_track_marker_only_covers_listed_files(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "constants.py").write_text("X = 1\n")
        (project / "src" / "mymodule" / "other.py").write_text("Y = 2\n")

        (project / "docs" / "mymodule.md").write_text(
            "# My Module\n\n"
            "<!-- beadloom:track=src/mymodule/constants.py -->\n"
        )

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        untracked = results[0]["untracked_files"]
        assert "src/mymodule/other.py" in untracked
        assert "src/mymodule/constants.py" not in untracked

    def test_no_marker_no_doc_file_unchanged(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Missing doc file on disk must not crash; behaves as before."""
        insert_node(conn, "mymod", "src/mymodule/")
        insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "constants.py").write_text("X = 1\n")
        # No doc file written on disk.

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/constants.py" in results[0]["untracked_files"]


# --- Golden / N+1-regression scaffolding (#123) --------------------------- #


def _build_rich_fixture(conn: sqlite3.Connection, project: Path) -> None:
    """A multi-node / multi-child / multi-annotation coverage scenario.

    Exercises every tracking signal at once so the golden assertion is a
    meaningful equivalence check, not a trivial empty-vs-empty.
    """
    # Domain A: parent dir, one child feature, mixed tracking signals.
    insert_node(conn, "dom-a", "src/dom_a/", kind="domain")
    insert_doc(conn, "dom_a.md", "dom-a")
    insert_node(conn, "feat-a", None, kind="feature")
    insert_edge(conn, "feat-a", "dom-a", "part_of")
    (project / "src" / "dom_a").mkdir(parents=True)
    (project / "src" / "dom_a" / "via_sync.py").write_text("a = 1\n")
    (project / "src" / "dom_a" / "via_symbol.py").write_text("def f(): pass\n")
    (project / "src" / "dom_a" / "via_child.py").write_text("def g(): pass\n")
    (project / "src" / "dom_a" / "via_annotation.py").write_text(
        "# beadloom:domain=dom-a\nK = 1\n"
    )
    (project / "src" / "dom_a" / "orphan_a.py").write_text("z = 9\n")
    insert_sync_state(conn, "dom_a.md", "src/dom_a/via_sync.py", "dom-a")
    insert_code_symbol(conn, "src/dom_a/via_symbol.py", "dom-a")
    insert_code_symbol(conn, "src/dom_a/via_child.py", "feat-a", symbol_name="g")

    # Domain B: fully tracked, no gaps.
    insert_node(conn, "dom-b", "src/dom_b/", kind="domain")
    insert_doc(conn, "dom_b.md", "dom-b")
    (project / "src" / "dom_b").mkdir(parents=True)
    (project / "src" / "dom_b" / "ok.py").write_text("def ok(): pass\n")
    insert_code_symbol(conn, "src/dom_b/ok.py", "dom-b", symbol_name="ok")

    # Domain C: source dir absent on disk -> skipped.
    insert_node(conn, "dom-c", "src/missing_c/", kind="domain")
    insert_doc(conn, "dom_c.md", "dom-c")

    # Domain D: no linked doc -> skipped despite an untracked file.
    insert_node(conn, "dom-d", "src/dom_d/", kind="domain")
    (project / "src" / "dom_d").mkdir(parents=True)
    (project / "src" / "dom_d" / "stray.py").write_text("q = 1\n")


class TestSourceCoverageGoldenParity:
    """#123: the set-based rewrite is byte/structure-identical to the legacy
    per-node algorithm, and drops the non-indexable code_symbols ``LIKE``."""

    def test_refactor_matches_legacy_on_rich_fixture(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _build_rich_fixture(conn, project)
        golden = legacy_check_source_coverage(conn, project)
        actual = check_source_coverage(conn, project)
        assert actual == golden
        # Sanity: the fixture is non-trivial (dom-a has real gaps).
        assert any(r["ref_id"] == "dom-a" for r in actual)
        dom_a = next(r for r in actual if r["ref_id"] == "dom-a")
        assert dom_a["untracked_files"] == ["src/dom_a/orphan_a.py"]

    def test_no_substring_like_against_code_symbols(self) -> None:
        """Guards the perf intent: no ``annotations LIKE '%...%'`` substring
        scan survives in the refactored coverage path (uses json_each)."""
        import ast
        import inspect
        import textwrap

        from beadloom.doc_sync import engine

        def _executed_sql(fn: object) -> str:
            """Concatenate only the SQL string literals passed to conn.execute,
            ignoring docstrings/comments that may mention 'LIKE' as prose."""
            tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))  # type: ignore[arg-type]
            sql: list[str] = []
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "execute"
                    and node.args
                ):
                    sql.append(ast.unparse(node.args[0]))
            return " ".join(sql)

        # The code_symbols annotation lookup must be JSON-parse driven.
        sym_sql = _executed_sql(engine._symbol_paths_by_ref_id)
        assert "json_each" in sym_sql
        assert "LIKE" not in sym_sql
        # No per-ref_id substring scan in any prefetch query (old
        # `annotations LIKE ?` is gone).
        cov_sql = _executed_sql(engine.check_source_coverage)
        assert "LIKE ?" not in cov_sql + sym_sql
