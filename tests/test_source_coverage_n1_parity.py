"""N+1-rewrite parity edge cases for ``check_source_coverage`` (BDL-059 .7, #123).

``test_source_coverage.py`` already pins the happy paths, one rich golden
fixture, and an AST guard that the ``code_symbols`` lookup is ``json_each``-driven
(no substring ``LIKE``). This module adds the *edge-case* fixtures the S2 brief
calls out, each asserting the set-based rewrite is structurally identical to the
frozen legacy per-node oracle:

- a node carrying children + symbol annotations + a doc reachable via **both**
  ``sync_state`` and the ``docs`` table (the sync_state-precedence branch);
- a node with **no** linked doc (skipped, even with on-disk gaps);
- a **removed symbol** (annotation gone) re-surfacing the file as untracked.

It reuses the legacy oracle and the insert helpers from
``test_source_coverage`` so the equivalence check stays single-sourced.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

import pytest

from beadloom.doc_sync import engine
from beadloom.doc_sync.engine import check_source_coverage

from .test_source_coverage import (
    _insert_code_symbol,
    _insert_doc,
    _insert_edge,
    _insert_node,
    _insert_sync_state,
    _legacy_check_source_coverage,
)

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "docs").mkdir(parents=True)
    (proj / ".beadloom").mkdir(parents=True)
    return proj


@pytest.fixture()
def conn(project: Path) -> Iterator[sqlite3.Connection]:
    from beadloom.infrastructure.db import create_schema, open_db

    db_path = project / ".beadloom" / "test.db"
    c = open_db(db_path)
    create_schema(c)
    try:
        yield c
    finally:
        c.close()


def _assert_parity(conn: sqlite3.Connection, project: Path) -> list[dict[str, object]]:
    """Run both implementations and assert structural identity; return actual."""
    golden = _legacy_check_source_coverage(conn, project)
    actual = check_source_coverage(conn, project)
    assert actual == golden
    return actual


class TestN1ParityEdgeCases:
    def test_node_with_children_annotations_and_doc_via_both_sources(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A parent with a child, a symbol annotation, AND a doc linked via both
        ``sync_state`` and ``docs`` — exercises the sync_state-precedence branch
        of ``_doc_paths_by_ref_id`` together with the hierarchy fan-out."""
        # Arrange
        (project / "src" / "mod").mkdir(parents=True)
        _insert_node(conn, "parent", "src/mod/", kind="domain")
        _insert_doc(conn, "parent.md", "parent")  # docs-table doc
        _insert_node(conn, "child", None, kind="feature")
        _insert_edge(conn, "child", "parent", "part_of")

        (project / "src" / "mod" / "via_sync.py").write_text("a = 1\n")
        (project / "src" / "mod" / "via_child_symbol.py").write_text("def g(): pass\n")
        (project / "src" / "mod" / "orphan.py").write_text("z = 9\n")

        # Doc reachable via BOTH sync_state (precedence) and docs table.
        _insert_sync_state(conn, "parent.md", "src/mod/via_sync.py", "parent")
        # File tracked through the child via a code_symbol annotation.
        _insert_code_symbol(conn, "src/mod/via_child_symbol.py", "child", symbol_name="g")

        # Act / Assert: identical structure, and only the orphan is a gap.
        actual = _assert_parity(conn, project)
        assert len(actual) == 1
        assert actual[0]["ref_id"] == "parent"
        assert actual[0]["untracked_files"] == ["src/mod/orphan.py"]

    def test_node_with_no_doc_is_skipped(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A node with a source dir + on-disk gaps but NO linked doc (neither
        sync_state nor docs) is skipped — both implementations agree."""
        # Arrange
        (project / "src" / "nodoc").mkdir(parents=True)
        _insert_node(conn, "nodoc", "src/nodoc/", kind="domain")
        (project / "src" / "nodoc" / "stray.py").write_text("q = 1\n")

        # Act / Assert
        actual = _assert_parity(conn, project)
        assert actual == []

    def test_removed_symbol_resurfaces_file_as_untracked(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """When a symbol's annotation is removed, its file becomes untracked
        again — the set-based path tracks the deletion exactly like the legacy
        per-node ``LIKE`` did."""
        # Arrange: file initially tracked via a code_symbol annotation.
        (project / "src" / "mod").mkdir(parents=True)
        _insert_node(conn, "mod", "src/mod/", kind="domain")
        _insert_doc(conn, "mod.md", "mod")
        (project / "src" / "mod" / "feature.py").write_text("def f(): pass\n")
        _insert_code_symbol(conn, "src/mod/feature.py", "mod", symbol_name="f")

        # Sanity: tracked, no gap, parity holds.
        assert _assert_parity(conn, project) == []

        # Act: symbol removed (e.g. file deleted from disk then re-added, or the
        # function renamed away) — drop the code_symbols row.
        conn.execute("DELETE FROM code_symbols WHERE file_path = ?", ("src/mod/feature.py",))
        conn.commit()

        # Assert: the file resurfaces as untracked, identically in both paths.
        actual = _assert_parity(conn, project)
        assert len(actual) == 1
        assert actual[0]["ref_id"] == "mod"
        assert "src/mod/feature.py" in actual[0]["untracked_files"]

    def test_symbol_annotation_with_null_value_is_tolerated(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A code_symbol whose annotation has a JSON ``null`` value must not crash
        the json_each fan-out (the ``rid is None`` guard) and stays parity-clean.

        ``json_each`` yields the NULL value for ``{"domain": null}``; the prefetch
        skips it, so the file is NOT tracked through that annotation — identical
        to the legacy substring scan, which never matched a quoted ref_id there.
        """
        # Arrange
        (project / "src" / "mod").mkdir(parents=True)
        _insert_node(conn, "mod", "src/mod/", kind="domain")
        _insert_doc(conn, "mod.md", "mod")
        (project / "src" / "mod" / "weird.py").write_text("def w(): pass\n")
        # Annotation object with a JSON null value -> json_each emits a NULL.
        conn.execute(
            "INSERT INTO code_symbols "
            "(file_path, symbol_name, kind, line_start, line_end, annotations, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("src/mod/weird.py", "w", "function", 1, 5, '{"domain": null}', "fh"),
        )
        conn.commit()

        # Act / Assert: no crash; the null-valued annotation does not track it.
        actual = _assert_parity(conn, project)
        assert len(actual) == 1
        assert "src/mod/weird.py" in actual[0]["untracked_files"]

    def test_doc_via_docs_table_only_no_sync_state(
        self, conn: sqlite3.Connection, project: Path
    ) -> None:
        """A node whose only doc link is in the ``docs`` table (no sync_state row
        at all) — exercises the docs-fallback branch of ``_doc_paths_by_ref_id``."""
        # Arrange
        (project / "src" / "docsonly").mkdir(parents=True)
        _insert_node(conn, "docsonly", "src/docsonly/", kind="domain")
        _insert_doc(conn, "docsonly.md", "docsonly")
        (project / "src" / "docsonly" / "gap.py").write_text("x = 1\n")

        # Act / Assert
        actual = _assert_parity(conn, project)
        assert len(actual) == 1
        assert actual[0]["doc_path"] == "docsonly.md"
        assert "src/docsonly/gap.py" in actual[0]["untracked_files"]


def _executed_sql(fn: object) -> str:
    """Concatenate only the SQL string literals passed to ``conn.execute`` in
    *fn*, ignoring docstrings/comments that may mention 'LIKE' as prose."""
    import ast
    import textwrap

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


class TestNoSubstringLikeInNewPath:
    """The de-N+1 path must not reintroduce a non-indexable ``LIKE '%...%'``."""

    def test_symbol_prefetch_query_is_json_each_not_like(self) -> None:
        # Only the actual SQL passed to conn.execute is inspected (prose in the
        # docstring mentioning LIKE/json_each is excluded).
        sym_sql = _executed_sql(engine._symbol_paths_by_ref_id)
        assert "json_each" in sym_sql
        assert "LIKE" not in sym_sql

    def test_coverage_prefetch_queries_carry_no_substring_like(self) -> None:
        # None of the per-ref_id prefetch SQL nor the orchestration reintroduces
        # a substring `LIKE ?` (the old `annotations LIKE '%"ref_id"%'` scan).
        combined = " ".join(
            _executed_sql(fn)
            for fn in (
                engine.check_source_coverage,
                engine._symbol_paths_by_ref_id,
                engine._sync_paths_by_ref_id,
                engine._children_by_parent,
                engine._doc_paths_by_ref_id,
            )
        )
        assert "LIKE ?" not in combined
