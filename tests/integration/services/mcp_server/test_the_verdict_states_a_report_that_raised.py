"""``complete_bead`` names a report that raised instead of reading as "nothing to say".

BDL-083 S1 fix 4 (``beadloom-ba9w.17``; BDL-UX #318's class; RFC D1). S1 fix 1 derived
the Gate's post-step reports under ``gate_boundary.derive_bounded`` and carried the
reason a report is absent on the result. The MCP tool read two of those reports on its
own account and dropped the reason both times:

* ``not_run`` was built from the coverage report alone, so a coverage report that
  raised gave ``[]`` — the same answer as "this run skipped nothing";
* the tool took its own room census with no boundary, so an exception there ended the
  call with a traceback and the verdict of a gate that had run was lost.

Both now go through the one boundary fix 1 added. ``not_run`` keeps its type, a list of
names, and a sibling ``not_run_reason`` says why it is empty when the report raised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from beadloom.application import rooms
from beadloom.application.gate import GateResult, GateStep
from beadloom.application.gate_coverage import GateCoverage
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.bd_seam import BdResult
from beadloom.services.mcp_server import handle_complete_bead

if TYPE_CHECKING:
    from pathlib import Path

_REASON = "the coverage report raised LookupError: injected fault"


class _InjectedFaultError(LookupError):
    """The exception the tests raise, so no other failure can pass for it."""


def _raises(*_args: object, **_kwargs: object) -> object:
    raise _InjectedFaultError("injected fault")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(tmp_path)
    return tmp_path


def _complete(project: Path, gate: GateResult) -> dict[str, object]:
    with (
        patch("beadloom.services.mcp_server.run_ci_gate", return_value=gate),
        patch("beadloom.services.mcp_server.run_bd") as run_bd,
    ):
        run_bd.return_value = BdResult(0, "", "")
        return handle_complete_bead(project, bead="bd-1", run_tests=False)


def _green(
    *, coverage: GateCoverage | None = None, coverage_reason: str | None = None
) -> GateResult:
    step = GateStep("lint", passed=True, summary="clean")
    return GateResult(steps=[step], coverage=coverage, coverage_reason=coverage_reason)


def _red(*, coverage_reason: str | None = None) -> GateResult:
    step = GateStep("lint", passed=False, findings=[{"why": "boom"}])
    return GateResult(steps=[step], coverage_reason=coverage_reason)


class TestNotRunNamesTheCoverageReportThatRaised:
    def test_a_pass_carries_the_reason_beside_the_empty_list(self, project: Path) -> None:
        verdict = _complete(project, _green(coverage_reason=_REASON))

        assert verdict["status"] == "PASS"
        assert verdict["not_run"] == []
        assert verdict["not_run_reason"] == _REASON

    def test_a_refusal_carries_it_too(self, project: Path) -> None:
        verdict = _complete(project, _red(coverage_reason=_REASON))

        assert verdict["status"] == "FAIL"
        assert verdict["not_run"] == []
        assert verdict["not_run_reason"] == _REASON

    def test_a_derived_report_gives_no_reason(self, project: Path) -> None:
        verdict = _complete(project, _green(coverage=GateCoverage(performed=("lint",))))

        assert verdict["not_run"] == []
        assert verdict["not_run_reason"] is None


class TestTheRoomCensusIsTakenInsideTheBoundary:
    def test_a_census_that_raises_is_a_reason_and_the_pass_stands(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rooms, "take_census", _raises)

        verdict = _complete(project, _green())

        assert verdict["status"] == "PASS"
        assert verdict["room"] == {
            "reason": "the room census raised _InjectedFaultError: injected fault"
        }

    def test_a_census_that_raises_leaves_the_refusal_and_its_findings(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rooms, "take_census", _raises)

        verdict = _complete(project, _red())

        assert verdict["status"] == "FAIL"
        assert verdict["findings"] == [{"why": "boom"}]
        assert verdict["room"] == {
            "reason": "the room census raised _InjectedFaultError: injected fault"
        }

    def test_a_census_that_answers_is_stated_without_a_reason(self, project: Path) -> None:
        verdict = _complete(project, _green())

        room = verdict["room"]
        assert isinstance(room, dict)
        assert room["current"]
        assert "reason" not in room
