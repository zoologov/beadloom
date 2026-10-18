"""Every format of `beadloom ci` states the reason a report derived after the steps is absent.

BDL-083 S1 fix 1 (``beadloom-4m0w``, S1R Major 1). A room census or a coverage report that
raised is absent from the result and carried as a reason beside it; the rich and JSON
formats are read end to end by the acceptance scenarios, and this file holds the GitHub
annotations and the empty case to the same sentence.
"""

from __future__ import annotations

from beadloom.application.gate import GateResult, GateStep
from beadloom.services.commands.federation import _format_gate_github, _format_gate_json

_ROOM = "the room census raised LookupError: injected fault"
_COVERAGE = "the coverage report raised LookupError: injected fault"


def _result(**reasons: str) -> GateResult:
    return GateResult(steps=[GateStep("lint", summary="3 rules, 0 violations")], **reasons)


def test_the_github_notices_carry_both_reasons() -> None:
    out = _format_gate_github(_result(room_reason=_ROOM, coverage_reason=_COVERAGE))

    assert f"::notice::room not stated: {_ROOM}" in out.splitlines()
    assert f"::notice::not run by this gate: no claim — {_COVERAGE}" in out.splitlines()


def test_a_result_with_no_report_and_no_reason_states_nothing() -> None:
    """Nothing asked is not the same answer as a report that raised."""
    out = _format_gate_github(_result())

    assert "room" not in out
    assert "not run by this gate" not in out
    assert "room" not in _format_gate_json(_result())
