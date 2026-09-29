"""``lint --no-reindex`` answers about the index, and says nothing about the tree.

* ``lint --no-reindex`` — the read-only form #147 introduced — answers about the
  INDEX and says nothing about the tree. With a real violation on disk and no
  reindex it printed ``12 rules, 0 violations`` at exit 0, silently.

Tests that assert a gap carry ``xfail(strict=True)``: the gap is recorded as an
executable statement, and the day it is fixed the marker fails the suite rather
than letting the finding be quietly forgotten. Each class also carries at least
one PASSING test using the same fixture, so an xfail can never be an artefact of
a broken helper (TESTS MUST BITE).

Split out of ``tests/test_s2_false_green_residue.py`` by node (BDL-074 E1). Every gap
below was measured on a clean-room copy of this repository at 004487a before it
was written down.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.graph.linter import lint as run_lint
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.two_component_project import ALPHA_CROSSING, indexed_project


class TestReadOnlyLintOverAStaleIndex:
    """#147's read-only form is a new way to lint a graph that is not the code."""

    def test_read_only_lint_leaves_the_index_file_byte_identical(self, tmp_path: Path) -> None:
        """The load-bearing half of #147, plus the one qualification it carries."""
        # Arrange
        project = indexed_project(tmp_path)
        db = project / ".beadloom" / "beadloom.db"
        for sidecar in ("-wal", "-shm"):
            db.with_name(db.name + sidecar).unlink(missing_ok=True)
        before_bytes = db.read_bytes()
        before_files = {p.name for p in (project / ".beadloom").iterdir()}

        # Act
        run_lint(project)

        # Assert
        assert db.read_bytes() == before_bytes
        new_files = {p.name for p in (project / ".beadloom").iterdir()} - before_files
        assert all(n.endswith(("-wal", "-shm")) for n in new_files), (
            "a read-only lint may leave SQLite's own sidecars behind (measured: it does, "
            f"on a WAL index) but nothing else — got {sorted(new_files)}"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FINDING S2/.6-6: `lint --no-reindex` reports on the INDEX and never says the "
            "index predates the tree. Measured on this repo: with a real "
            "tui -> infrastructure import on disk and no reindex it printed "
            "'12 rules, 0 violations' at exit 0, silent on stdout and stderr, while plain "
            "`lint --strict` on the same tree exited 1. file_index already holds a sha256 "
            "per path, so the answer is one query away."
        ),
    )
    def test_read_only_lint_over_a_stale_index_does_not_report_clean(self, tmp_path: Path) -> None:
        # Arrange — index the clean tree, then introduce a crossing WITHOUT reindexing
        project = indexed_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            ALPHA_CROSSING, encoding="utf-8"
        )

        # Act — --format json, never a line count: piped output changes shape (#148)
        runner = CliRunner()
        invocation = runner.invoke(
            main,
            ["lint", "--no-reindex", "--strict", "--format", "json", "--project", str(project)],
        )
        payload = json.loads(invocation.stdout)
        crossings = [v for v in payload["violations"] if v["rule_type"] == "forbid_import"]
        said_stale = "stale" in (invocation.stdout + invocation.stderr).lower()

        # Assert
        assert crossings or said_stale, (
            "an index older than the working tree cannot answer for the working tree: "
            "the read-only lint must report the crossing or say the index predates the "
            f"code — got exit {invocation.exit_code}, {payload['summary']}, and no "
            "staleness signal on either stream"
        )
