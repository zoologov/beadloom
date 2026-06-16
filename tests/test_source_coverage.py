"""Tests for check_source_coverage — untracked file detection via nodes.source dirs."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync.engine import check_source_coverage
from beadloom.infrastructure.db import create_schema, open_db

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


def _insert_node(
    conn: sqlite3.Connection,
    ref_id: str,
    source: str | None,
    *,
    kind: str = "domain",
    summary: str = "test node",
) -> None:
    """Insert a node with optional source field."""
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, summary, source),
    )
    conn.commit()


def _insert_doc(
    conn: sqlite3.Connection,
    path: str,
    ref_id: str,
    *,
    kind: str = "domain",
    doc_hash: str = "dochash",
) -> None:
    """Insert a doc entry linked to a ref_id."""
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, ?)",
        (path, kind, ref_id, doc_hash),
    )
    conn.commit()


def _insert_sync_state(
    conn: sqlite3.Connection,
    doc_path: str,
    code_path: str,
    ref_id: str,
) -> None:
    """Insert a sync_state entry for a tracked code file."""
    conn.execute(
        "INSERT INTO sync_state "
        "(doc_path, code_path, ref_id, code_hash_at_sync, doc_hash_at_sync, "
        "synced_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (doc_path, code_path, ref_id, "hash1", "hash2", "2025-01-01", "ok"),
    )
    conn.commit()


def _insert_code_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    ref_id: str,
    *,
    symbol_name: str = "some_func",
    kind: str = "function",
) -> None:
    """Insert a code_symbol annotated with a given ref_id."""
    annotations = json.dumps({"domain": ref_id})
    conn.execute(
        "INSERT INTO code_symbols "
        "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, kind, 1, 10, annotations, "filehash"),
    )
    conn.commit()


class TestSourceCoverageAllTracked:
    """Node with source dir where all files are tracked -> empty result."""

    def test_all_files_tracked_via_sync_state(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via sync_state
        _insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_files_tracked_via_code_symbols(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        # Setup: node with source dir
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")

        # Track via code_symbols (annotated with ref_id)
        _insert_code_symbol(conn, "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageUntracked:
    """Node with new untracked file -> detected."""

    def test_untracked_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Create two files on disk
        (project / "src" / "mymodule" / "handler.py").write_text("def handler(): pass\n")
        (project / "src" / "mymodule" / "new_feature.py").write_text("def new(): pass\n")

        # Only track handler.py
        _insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mymod"
        assert results[0]["doc_path"] == "mymodule.md"
        assert "src/mymodule/new_feature.py" in results[0]["untracked_files"]

    def test_untracked_file_relative_path(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Untracked files should be reported as relative paths."""
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "utils.py").write_text("X = 1\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        # Path should be relative, not absolute
        for path in results[0]["untracked_files"]:
            assert not path.startswith("/")


class TestSourceCoverageExclusions:
    """Exclusions work: __init__.py, conftest.py, __main__.py are ignored."""

    def test_init_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        # Only excluded files on disk
        (project / "src" / "mymodule" / "__init__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_conftest_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "conftest.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_main_excluded(self, conn: sqlite3.Connection, project: Path) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_all_exclusions_combined(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "__init__.py").write_text("")
        (project / "src" / "mymodule" / "conftest.py").write_text("")
        (project / "src" / "mymodule" / "__main__.py").write_text("")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_excluded_files_ignored_but_real_file_detected(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/mymodule/handler.py")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/nonexistent/")
        _insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


class TestSourceCoverageMultipleNodes:
    """Multiple nodes with mixed results."""

    def test_mixed_results(self, conn: sqlite3.Connection, project: Path) -> None:
        # Node 1: all tracked (no gaps)
        _insert_node(conn, "mod-a", "src/mod_a/")
        _insert_doc(conn, "mod_a.md", "mod-a")
        (project / "src" / "mod_a").mkdir(parents=True)
        (project / "src" / "mod_a" / "tracked.py").write_text("x = 1\n")
        _insert_sync_state(conn, "mod_a.md", "src/mod_a/tracked.py", "mod-a")

        # Node 2: has untracked file
        _insert_node(conn, "mod-b", "src/mod_b/")
        _insert_doc(conn, "mod_b.md", "mod-b")
        (project / "src" / "mod_b").mkdir(parents=True)
        (project / "src" / "mod_b" / "tracked.py").write_text("y = 1\n")
        (project / "src" / "mod_b" / "untracked.py").write_text("z = 1\n")
        _insert_sync_state(conn, "mod_b.md", "src/mod_b/tracked.py", "mod-b")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert results[0]["ref_id"] == "mod-b"
        assert "src/mod_b/untracked.py" in results[0]["untracked_files"]

    def test_node_without_doc_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with source dir but no linked doc -> skipped."""
        _insert_node(conn, "mymod", "src/mymodule/")
        # No doc inserted for this node

        (project / "src" / "mymodule" / "code.py").write_text("x = 1\n")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_node_with_null_source_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Node with NULL source -> skipped."""
        _insert_node(conn, "mymod", None)
        _insert_doc(conn, "mymodule.md", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []


def _insert_edge(
    conn: sqlite3.Connection,
    src_ref_id: str,
    dst_ref_id: str,
    kind: str = "part_of",
) -> None:
    """Insert an edge between two nodes."""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src_ref_id, dst_ref_id, kind),
    )
    conn.commit()


class TestSourceCoverageHierarchy:
    """Hierarchy-aware coverage: child part_of edges are considered."""

    def test_child_feature_tracked_via_hierarchy(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File annotated to child feature (part_of parent) should NOT be
        flagged as untracked for parent domain."""
        # Parent node owns the source directory
        _insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        _insert_doc(conn, "infrastructure.md", "infrastructure")

        # Child node is part_of parent
        _insert_node(conn, "doctor", None, kind="feature")
        _insert_edge(conn, "doctor", "infrastructure", "part_of")

        # Create file on disk inside parent's source dir
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )

        # File annotated to the *child* ref_id, not the parent
        _insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")

        results = check_source_coverage(conn, project)
        # Should be empty: child annotation covers the file
        assert results == []

    def test_truly_untracked_not_hidden_by_hierarchy(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File NOT annotated to any child feature should still be flagged."""
        _insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        _insert_doc(conn, "infrastructure.md", "infrastructure")

        _insert_node(conn, "doctor", None, kind="feature")
        _insert_edge(conn, "doctor", "infrastructure", "part_of")

        # Two files on disk
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )
        (project / "src" / "mymodule" / "orphan.py").write_text(
            "def orphan(): pass\n"
        )

        # Only doctor.py is annotated to the child feature
        _insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "handler.py").write_text(
            "def handler(): pass\n"
        )

        # Track directly via sync_state on the parent
        _insert_sync_state(conn, "mymodule.md", "src/mymodule/handler.py", "mymod")

        results = check_source_coverage(conn, project)
        assert results == []

    def test_multiple_children_all_counted(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """Multiple child features — files from different children all counted."""
        _insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        _insert_doc(conn, "infrastructure.md", "infrastructure")

        # Two child features
        _insert_node(conn, "doctor", None, kind="feature")
        _insert_edge(conn, "doctor", "infrastructure", "part_of")

        _insert_node(conn, "linter", None, kind="feature")
        _insert_edge(conn, "linter", "infrastructure", "part_of")

        # Files on disk
        (project / "src" / "mymodule" / "doctor.py").write_text(
            "def run_doctor(): pass\n"
        )
        (project / "src" / "mymodule" / "linter.py").write_text(
            "def run_lint(): pass\n"
        )

        # Each file annotated to its respective child feature
        _insert_code_symbol(conn, "src/mymodule/doctor.py", "doctor")
        _insert_code_symbol(
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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "config.py").write_text(
            "# beadloom:feature=mymod\nSETTINGS = {}\n"
        )

        results = check_source_coverage(conn, project)
        assert results == []

    def test_annotation_to_other_node_still_untracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A file annotated to a DIFFERENT node is still untracked here."""
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "data.py").write_text("X = 1\nY = 2\n")

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/data.py" in results[0]["untracked_files"]

    def test_annotation_to_child_feature_tracks(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """File annotated to a child feature (part_of parent) is tracked."""
        _insert_node(conn, "infrastructure", "src/mymodule/", kind="domain")
        _insert_doc(conn, "infrastructure.md", "infrastructure")
        _insert_node(conn, "doctor", None, kind="feature")
        _insert_edge(conn, "doctor", "infrastructure", "part_of")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

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
        _insert_node(conn, "mymod", "src/mymodule/")
        _insert_doc(conn, "mymodule.md", "mymod")

        (project / "src" / "mymodule" / "constants.py").write_text("X = 1\n")
        # No doc file written on disk.

        results = check_source_coverage(conn, project)
        assert len(results) == 1
        assert "src/mymodule/constants.py" in results[0]["untracked_files"]


# --- Golden / N+1-regression scaffolding (#123) --------------------------- #


def _legacy_check_source_coverage(
    conn: sqlite3.Connection, project_root: Path
) -> list[dict[str, object]]:
    """The pre-refactor per-node algorithm, frozen as the golden oracle.

    Mirrors the original ~5N-query implementation (per-node sync/docs lookup,
    per-node sync_state + edges + child sync_state, per-ref_id
    ``annotations LIKE '%"ref_id"%'``). The refactored set-based version MUST
    return structurally-identical results to this for any fixture.
    """
    from beadloom.doc_sync.engine import (
        _COVERAGE_EXCLUDE,
        _file_annotation_ref_ids,
        _tracked_paths_from_doc,
    )

    node_rows = conn.execute(
        "SELECT ref_id, source FROM nodes "
        "WHERE source IS NOT NULL AND source LIKE '%/'"
    ).fetchall()
    if not node_rows:
        return []

    results: list[dict[str, object]] = []
    for node in node_rows:
        ref_id = node["ref_id"]
        source = node["source"]
        source_dir = project_root / source
        if not source_dir.is_dir():
            continue

        doc_row = conn.execute(
            "SELECT doc_path FROM sync_state WHERE ref_id = ? LIMIT 1", (ref_id,)
        ).fetchone()
        if doc_row is None:
            doc_row = conn.execute(
                "SELECT path AS doc_path FROM docs WHERE ref_id = ? LIMIT 1",
                (ref_id,),
            ).fetchone()
        if doc_row is None:
            continue
        doc_path = doc_row["doc_path"]

        disk_files: set[str] = set()
        for py_file in source_dir.glob("*.py"):
            if py_file.name in _COVERAGE_EXCLUDE:
                continue
            disk_files.add(str(py_file.relative_to(project_root)))
        if not disk_files:
            continue

        tracked: set[str] = set()
        for r in conn.execute(
            "SELECT code_path FROM sync_state WHERE ref_id = ?", (ref_id,)
        ).fetchall():
            tracked.add(r["code_path"])

        child_rows = conn.execute(
            "SELECT src_ref_id FROM edges WHERE dst_ref_id = ? AND kind = 'part_of'",
            (ref_id,),
        ).fetchall()
        child_ref_ids = [r["src_ref_id"] for r in child_rows]
        for child_id in child_ref_ids:
            for r in conn.execute(
                "SELECT code_path FROM sync_state WHERE ref_id = ?", (child_id,)
            ).fetchall():
                tracked.add(r["code_path"])

        all_ref_ids = [ref_id, *child_ref_ids]
        for rid in all_ref_ids:
            for r in conn.execute(
                "SELECT file_path FROM code_symbols WHERE annotations LIKE ?",
                (f'%"{rid}"%',),
            ).fetchall():
                tracked.add(r["file_path"])

        owned_ref_ids = set(all_ref_ids)
        tracked |= _tracked_paths_from_doc(project_root / "docs" / doc_path, project_root)
        for disk_file in disk_files:
            if disk_file in tracked:
                continue
            if _file_annotation_ref_ids(project_root / disk_file) & owned_ref_ids:
                tracked.add(disk_file)

        untracked = sorted(disk_files - tracked)
        if untracked:
            results.append(
                {"ref_id": ref_id, "doc_path": doc_path, "untracked_files": untracked}
            )
    return results


def _build_rich_fixture(conn: sqlite3.Connection, project: Path) -> None:
    """A multi-node / multi-child / multi-annotation coverage scenario.

    Exercises every tracking signal at once so the golden assertion is a
    meaningful equivalence check, not a trivial empty-vs-empty.
    """
    # Domain A: parent dir, one child feature, mixed tracking signals.
    _insert_node(conn, "dom-a", "src/dom_a/", kind="domain")
    _insert_doc(conn, "dom_a.md", "dom-a")
    _insert_node(conn, "feat-a", None, kind="feature")
    _insert_edge(conn, "feat-a", "dom-a", "part_of")
    (project / "src" / "dom_a").mkdir(parents=True)
    (project / "src" / "dom_a" / "via_sync.py").write_text("a = 1\n")
    (project / "src" / "dom_a" / "via_symbol.py").write_text("def f(): pass\n")
    (project / "src" / "dom_a" / "via_child.py").write_text("def g(): pass\n")
    (project / "src" / "dom_a" / "via_annotation.py").write_text(
        "# beadloom:domain=dom-a\nK = 1\n"
    )
    (project / "src" / "dom_a" / "orphan_a.py").write_text("z = 9\n")
    _insert_sync_state(conn, "dom_a.md", "src/dom_a/via_sync.py", "dom-a")
    _insert_code_symbol(conn, "src/dom_a/via_symbol.py", "dom-a")
    _insert_code_symbol(conn, "src/dom_a/via_child.py", "feat-a", symbol_name="g")

    # Domain B: fully tracked, no gaps.
    _insert_node(conn, "dom-b", "src/dom_b/", kind="domain")
    _insert_doc(conn, "dom_b.md", "dom-b")
    (project / "src" / "dom_b").mkdir(parents=True)
    (project / "src" / "dom_b" / "ok.py").write_text("def ok(): pass\n")
    _insert_code_symbol(conn, "src/dom_b/ok.py", "dom-b", symbol_name="ok")

    # Domain C: source dir absent on disk -> skipped.
    _insert_node(conn, "dom-c", "src/missing_c/", kind="domain")
    _insert_doc(conn, "dom_c.md", "dom-c")

    # Domain D: no linked doc -> skipped despite an untracked file.
    _insert_node(conn, "dom-d", "src/dom_d/", kind="domain")
    (project / "src" / "dom_d").mkdir(parents=True)
    (project / "src" / "dom_d" / "stray.py").write_text("q = 1\n")


class TestSourceCoverageGoldenParity:
    """#123: the set-based rewrite is byte/structure-identical to the legacy
    per-node algorithm, and drops the non-indexable code_symbols ``LIKE``."""

    def test_refactor_matches_legacy_on_rich_fixture(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        _build_rich_fixture(conn, project)
        golden = _legacy_check_source_coverage(conn, project)
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
