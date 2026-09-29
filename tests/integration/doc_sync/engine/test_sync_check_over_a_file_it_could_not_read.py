"""``sync-check`` does not report a pair fresh over a file it could not read.

* ``sync-check`` reports ``status: ok`` for a pair whose code file — or whose
  doc — no longer exists, because ``_file_hash`` returns ``None`` for a missing
  file and both comparisons are guarded by the truthiness of that hash. Deleting
  a documented feature's whole ``SPEC.md`` from this repo left ``beadloom ci``
  at exit 0 with every step PASS.

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

from beadloom.doc_sync.engine import check_sync

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.two_component_project import ALPHA_CLEAN, indexed_project


def _pair_status(project: Path, *, code_suffix: str) -> list[str]:
    """Statuses reported for every pair whose code path ends with *code_suffix*."""
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        return [
            str(row["status"])
            for row in check_sync(conn, project)
            if str(row.get("code_path") or "").endswith(code_suffix)
        ]
    finally:
        conn.close()


class TestSyncCheckOverAFileItCouldNotRead:
    """``_file_hash`` returns ``None`` for a missing file, and ``None`` reads as "unchanged"."""

    def test_a_pair_whose_code_changed_is_reported_stale(self, tmp_path: Path) -> None:
        """The freshness comparison works — this class's non-vacuity guard."""
        # Arrange
        project = indexed_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").write_text(
            ALPHA_CLEAN + "\n\ndef added() -> int:\n    return 3\n", encoding="utf-8"
        )

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert statuses and all(s == "stale" for s in statuses), (
            f"a changed code file must make its pair stale — got {statuses}"
        )

    # FIXED in BDL-061.46/.47 (BDL-UX #174): the code side reads ``missing`` too.
    def test_a_pair_whose_code_file_was_deleted_is_not_reported_fresh(
        self, tmp_path: Path
    ) -> None:
        # Arrange
        project = indexed_project(tmp_path)
        (project / "src" / "app" / "alpha" / "service.py").unlink()

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert "ok" not in statuses, (
            "a file that is not there was not checked, and must not be called fresh"
        )

    # FIXED in BDL-061.46/.47 (BDL-UX #174): a pair whose doc file is gone is
    # reported ``missing`` — a failure, not an absence.
    def test_a_pair_whose_doc_was_deleted_is_not_reported_fresh(self, tmp_path: Path) -> None:
        # Arrange
        project = indexed_project(tmp_path)
        (project / "docs" / "components" / "alpha.md").unlink()

        # Act
        statuses = _pair_status(project, code_suffix="alpha/service.py")

        # Assert
        assert "ok" not in statuses, "a doc that is not there cannot be fresh against anything"
