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
Since S1 fix 5 (``beadloom-ba9w.18``) the room is the gate's own census, read off the
result with its reason, so the boundary is crossed once per call rather than twice.
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

    from beadloom.application.rooms import RoomCensus

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
    *,
    coverage: GateCoverage | None = None,
    coverage_reason: str | None = None,
    room: RoomCensus | None = None,
    room_reason: str | None = None,
) -> GateResult:
    step = GateStep("lint", passed=True, summary="clean")
    return GateResult(
        steps=[step],
        coverage=coverage,
        coverage_reason=coverage_reason,
        room=room,
        room_reason=room_reason,
    )


def _red(*, coverage_reason: str | None = None, room_reason: str | None = None) -> GateResult:
    step = GateStep("lint", passed=False, findings=[{"why": "boom"}])
    return GateResult(steps=[step], coverage_reason=coverage_reason, room_reason=room_reason)


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


class TestTheRoomIsTheOneTheGateTook:
    """S1R second pass Minor 1 (``beadloom-ba9w.18``): one census per call, the gate's.

    Fix 4 put the tool's own census under the boundary, beside the census the gate had
    just taken, so one call derived the room twice and the MCP room could differ from
    the room the gate's JSON reported for the same run. The verdict now reads
    ``gate.room`` and ``gate.room_reason``, and no second census is taken.
    """

    _RAISED = "the room census raised _InjectedFaultError: injected fault"

    def test_the_verdict_states_the_gate_s_census_and_takes_none_of_its_own(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        census = rooms.take_census(project)
        monkeypatch.setattr(rooms, "take_census", _raises)

        verdict = _complete(project, _green(room=census))

        assert verdict["status"] == "PASS"
        assert verdict["room"] == {
            "current": rooms.room_line(census.current),
            "declared": len(census.comparisons),
            "entered": len(census.entered),
            "not_entered": [c.room.label for c in census.not_entered],
        }

    def test_a_census_that_raised_in_the_gate_is_its_reason_and_the_pass_stands(
        self, project: Path
    ) -> None:
        verdict = _complete(project, _green(room_reason=self._RAISED))

        assert verdict["status"] == "PASS"
        assert verdict["room"] == {"reason": self._RAISED}

    def test_a_census_that_raised_leaves_the_refusal_and_its_findings(
        self, project: Path
    ) -> None:
        verdict = _complete(project, _red(room_reason=self._RAISED))

        assert verdict["status"] == "FAIL"
        assert verdict["findings"] == [{"why": "boom"}]
        assert verdict["room"] == {"reason": self._RAISED}

    def test_a_gate_that_took_no_census_is_said_to_have_taken_none(
        self, project: Path
    ) -> None:
        verdict = _complete(project, _green())

        assert verdict["room"] == {"reason": "the gate took no room census"}
