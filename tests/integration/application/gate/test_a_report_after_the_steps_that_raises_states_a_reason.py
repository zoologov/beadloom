"""A report `run_ci_gate` derives after its steps that raises becomes a stated reason.

BDL-083 S1e (``beadloom-ba9w.13``, BDL-UX #318; RFC D1) put every Gate step inside
``run_bounded``. The room census, the verification coverage and the ownership report
are derived after the steps, from the finished result, and until S1 fix 1
(``beadloom-4m0w``, S1R Major 1) they ran outside any boundary: an exception in one of
them left ``run_ci_gate`` as a traceback, and the verdict of steps that all ran was
lost with it (measured on 2026-10-18 by this file's earlier, strict form).

Each report is now derived under the boundary. One that raises is absent, and the run
says why in a sentence naming the exception class and message; the steps, their
verdict and the exit code are the ones they would have been.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.application import gate
from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.onboarding.scanner import generate_agents_md

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.application.gate import GateResult
    from beadloom.application.guards.contract import ClaimedBead


class _NoClaims:
    """A tracker that answers, with no bead claimed, so the ownership report is derived."""

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        return ()


class _InjectedFaultError(LookupError):
    """The exception the tests raise, so no other failure can pass for it."""


def _raises(*_args: object, **_kwargs: object) -> object:
    raise _InjectedFaultError("injected fault")


def _room_reason(result: GateResult) -> str | None:
    return result.room_reason if result.room is None else None


def _coverage_reason(result: GateResult) -> str | None:
    return result.coverage_reason if result.coverage is None else None


def _ownership_reason(result: GateResult) -> str | None:
    ownership = result.ownership
    return ownership.reason if ownership is not None and not ownership.owners else None


#: Each derivation, the name its report is stated under, and how the reason is read back.
_REPORTS = [
    pytest.param("take_census", "room census", _room_reason, id="room"),
    pytest.param("derive_gate_coverage", "coverage report", _coverage_reason, id="coverage"),
    pytest.param("derive_gate_ownership", "ownership report", _ownership_reason, id="ownership"),
]


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(root)
    reindex(root)
    return root


def _run(project: Path) -> GateResult:
    return run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=True, tracker=_NoClaims())


@pytest.mark.parametrize(("derivation", "report", "reason_of"), _REPORTS)
def test_a_report_derived_after_the_steps_that_raises_states_its_reason(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    derivation: str,
    report: str,
    reason_of: object,
) -> None:
    monkeypatch.setattr(gate, derivation, _raises)

    result = _run(project)

    assert callable(reason_of)
    assert reason_of(result) == f"the {report} raised _InjectedFaultError: injected fault"


@pytest.mark.parametrize(("derivation", "report", "reason_of"), _REPORTS)
def test_the_steps_verdict_is_the_one_they_gave_without_the_fault(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    derivation: str,
    report: str,
    reason_of: object,
) -> None:
    baseline = _run(project)
    monkeypatch.setattr(gate, derivation, _raises)

    result = _run(project)

    assert result.ok is baseline.ok is True
    assert [(s.name, s.status, s.summary) for s in result.steps] == [
        (s.name, s.status, s.summary) for s in baseline.steps
    ]
    assert result.crashed == []


def test_the_reports_that_did_not_raise_are_still_derived(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One report raising takes nothing from the other two."""
    monkeypatch.setattr(gate, "derive_gate_coverage", _raises)

    result = _run(project)

    assert result.room is not None
    assert result.room_reason is None
    assert result.ownership is not None
    assert result.ownership.reason is None


def test_the_same_project_states_no_reason_when_no_report_raises(project: Path) -> None:
    """The baseline: without it, a reason above could be any failure of the run."""
    result = _run(project)

    assert result.crashed == []
    assert result.room is not None
    assert result.coverage is not None
    assert result.room_reason is None
    assert result.coverage_reason is None
