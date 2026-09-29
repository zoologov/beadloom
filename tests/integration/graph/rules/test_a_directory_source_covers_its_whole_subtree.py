"""A directory ``source`` covers its whole subtree for ``module_coverage``, and nothing outside it.

BDL-051 Slice 3b: a directory source covers nested subtrees (``tui/screens/*``,
``tui/widgets/*``), does not over-cover siblings outside the directory, and nested
or overlapping directory sources both count.

Split out of ``tests/test_bead15_s3b_coverage.py`` by node (BDL-074 E1).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rule_engine import (
    ModuleCoverageRule,
    evaluate_module_coverage_rules,
)
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture()
def mem_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    yield conn
    conn.close()


def _insert_symbol(
    conn: sqlite3.Connection,
    file_path: str,
    symbol_name: str,
    annotations: dict[str, str],
) -> None:
    conn.execute(
        "INSERT INTO code_symbols"
        " (file_path, symbol_name, kind, line_start, line_end, annotations, file_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_path, symbol_name, "function", 1, 10, json.dumps(annotations), "h"),
    )


def _mc_rule(
    *,
    exempt: tuple[str, ...] = (),
    severity: str = "error",
) -> ModuleCoverageRule:
    return ModuleCoverageRule(
        name="module-coverage",
        description="every src module must be a node or exempt",
        source_root="src/beadloom/",
        min_symbols=1,
        exempt=exempt,
        severity=severity,
    )


class TestDirSourceCoverageDepth:
    """A directory `source` covers its whole subtree (deeply), but not outside it."""

    def test_dir_source_covers_deeply_nested_modules(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ (dir source) covers BOTH tui/screens/* and tui/widgets/* — nested depth."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        for path in (
            "src/beadloom/tui/screens/main_screen.py",
            "src/beadloom/tui/widgets/status_bar.py",
            "src/beadloom/tui/app.py",
        ):
            _insert_symbol(mem_db, path, "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/screens/main_screen.py" not in flagged
        assert "src/beadloom/tui/widgets/status_bar.py" not in flagged
        assert "src/beadloom/tui/app.py" not in flagged

    def test_dir_source_does_not_over_cover_siblings_outside(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """tui/ does NOT cover a sibling under a different dir (e.g. graph/), nor a prefix-twin.

        Guards against a naive ``startswith`` that would let ``tui/`` cover a
        sibling directory whose name merely starts with ``tui`` (``tui_extra/``).
        """
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/outside.py", "fn", {"domain": "graph"})
        _insert_symbol(mem_db, "src/beadloom/tui_extra/twin.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/outside.py" in flagged
        assert "src/beadloom/tui_extra/twin.py" in flagged

    def test_file_source_node_covers_only_its_own_file(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A file-source node covers ONLY its file, not a sibling in the same dir."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("graph-loader", "component", "loader", "src/beadloom/graph/loader.py"),
        )
        _insert_symbol(mem_db, "src/beadloom/graph/loader.py", "fn", {})
        _insert_symbol(mem_db, "src/beadloom/graph/sibling.py", "fn", {"domain": "graph"})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/graph/loader.py" not in flagged
        assert "src/beadloom/graph/sibling.py" in flagged

    def test_overlapping_nested_dir_sources_both_cover(
        self, mem_db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        """A nested dir source inside an outer dir source: modules under either are covered."""
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui", "service", "tui", "src/beadloom/tui/"),
        )
        mem_db.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            ("tui-widgets", "component", "widgets", "src/beadloom/tui/widgets/"),
        )
        _insert_symbol(mem_db, "src/beadloom/tui/widgets/deep/inner.py", "fn", {})
        flagged = {
            v.file_path
            for v in evaluate_module_coverage_rules(mem_db, [_mc_rule()], project_root=tmp_path)
        }
        assert "src/beadloom/tui/widgets/deep/inner.py" not in flagged
