"""The Gate's doctor line does not call a run with warnings clean.

* The Gate's doctor step prints ``N check(s) clean`` where *N* counts every
  check, warnings included. On the untouched repo that line read
  ``20 check(s) clean`` over 10 OK, 9 WARNING and 1 INFO that says verbatim
  "command count not verified".

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

import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.doctor import Severity, run_checks
from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.two_component_project import indexed_project


class TestTheDoctorSummaryCountsWarningsAsClean:
    """The Gate's doctor line reports how many checks RAN, under the word "clean"."""

    def test_the_fixture_really_does_produce_a_doctor_warning(self, tmp_path: Path) -> None:
        """This class's non-vacuity guard: without a warning the next test proves nothing."""
        # Arrange
        project = indexed_project(tmp_path)
        (project / "docs" / "orphan.md").write_text("# Orphan\n\nNo node owns me.\n")
        reindex(project)

        # Act
        conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
        conn.row_factory = sqlite3.Row
        try:
            checks = run_checks(conn, project_root=project)
        finally:
            conn.close()

        # Assert
        assert [c for c in checks if c.severity is Severity.WARNING]

    # FIXED in BDL-061.46 (BDL-UX #174, third item): the summary counts the
    # CHECKS that ran and reports their severities, so it can no longer rise
    # while the tree shrinks and can no longer call a warning clean.
    def test_the_doctor_step_does_not_call_a_warning_clean(self, tmp_path: Path) -> None:
        # Arrange
        project = indexed_project(tmp_path)
        (project / "docs" / "orphan.md").write_text("# Orphan\n\nNo node owns me.\n")

        # Act
        result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
        doctor_step = next(s for s in result.steps if s.name == "doctor")

        # Assert
        assert "clean" not in doctor_step.summary, (
            "a run with warnings is not clean; the summary must count what passed, "
            f"not what ran — got {doctor_step.summary!r}"
        )
