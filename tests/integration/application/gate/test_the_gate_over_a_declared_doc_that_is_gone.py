"""The Gate reacts to a declared document that is gone as it reacts to a real violation.

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

import json
from typing import TYPE_CHECKING

from beadloom.application.gate import run_ci_gate

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import GateStep
from tests.support.two_component_project import ALPHA_CROSSING, indexed_project


def _gate(project: Path) -> tuple[bool, list[str]]:
    """Run the whole Gate and return ``(ok, [finding text, ...])``.

    Deliberately NOT the step summaries: a count that silently moves from
    ``275 pair(s) fresh`` to ``264 pair(s) fresh`` inside a PASS line is the
    defect, not the report of it. What a reader can act on is the verdict and
    the findings.
    """
    result = run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False)
    return result.ok, [json.dumps(f, sort_keys=True, default=str) for f in result.findings]


def _steps(project: Path) -> list[GateStep]:
    """Run the whole Gate and return its steps."""
    return run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=False).steps


class TestTheGateOverADeclaredDocThatIsGone:
    """A node declares ``docs:``; deleting the file it names changes no verdict."""

    def test_the_gate_reacts_to_a_real_boundary_violation(self, tmp_path: Path) -> None:
        """The Gate's verdict moves on this fixture — this class's non-vacuity guard."""
        # Arrange
        clean = indexed_project(tmp_path / "clean")
        crossing = indexed_project(tmp_path / "crossing", alpha_source=ALPHA_CROSSING)

        # Act — compare the lint STEP rather than the whole verdict: a freshly
        # built fixture has never been sync-baselined, which is a property of the
        # fixture and not of the thing under test
        clean_lint = next(s for s in _steps(clean) if s.name == "lint")
        crossing_lint = next(s for s in _steps(crossing) if s.name == "lint")

        # Assert
        assert clean_lint.passed is True, f"clean fixture: {clean_lint.summary}"
        assert crossing_lint.passed is False, "a real crossing must fail lint in the Gate"

    # FIXED in BDL-061.46/.47 (BDL-UX #174): the DECLARATION outlives the file,
    # so deleting the doc fails the Gate by name instead of shrinking a count.
    def test_deleting_a_declared_doc_is_reported_by_the_gate(self, tmp_path: Path) -> None:
        # Arrange
        project = indexed_project(tmp_path)
        # The untouched fixture must not FAIL. It does carry warnings — it is not
        # a git repo and its index was just built, so its pairs are honestly
        # `unverified` rather than fresh (BDL-UX #175); that is the fix, not a
        # regression, and the assertion is about errors.
        before_ok, before_findings = _gate(project)
        assert before_ok is True
        assert not [f for f in before_findings if '"severity": "error"' in f]
        (project / "docs" / "components" / "alpha.md").unlink()

        # Act
        ok, findings = _gate(project)

        # Assert
        assert ok is False or any("alpha.md" in f for f in findings), (
            "a node declares this doc and the file is gone: the Gate must fail or name "
            f"it — got ok={ok} with {len(findings)} finding(s)"
        )
