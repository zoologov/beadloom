"""The three reports `run_ci_gate` derives after its steps run outside the step boundary.

BDL-083 S1e (``beadloom-ba9w.13``, BDL-UX #318; RFC D1) put every Gate step inside
``run_bounded``, so a step that raises becomes an ``ERROR`` step and the rest still run.
The room census, the verification coverage and the ownership report are derived after
the steps, from the finished result, and are not steps: the bead's own completion note
says they are not bounded, and leaves the ruling to the S1 review. This file records
that behaviour as it is, measured on 2026-10-18: an exception in any of the three leaves
``run_ci_gate`` as a traceback, and the verdict of steps that all ran is lost with it.

It pins the current behaviour, not a decision. When the review rules that these reports
are bounded too, these are the tests to invert. The pre-push hook already reads a run
that printed no verdict as "the Gate did not run" and refuses the push, so the push is
not waved through either way; what is lost is the verdict.
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

    from beadloom.application.guards.contract import ClaimedBead


class _NoClaims:
    """A tracker that answers, with no bead claimed, so the ownership report is derived."""

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        return ()


class _InjectedFaultError(LookupError):
    """The exception the tests raise, so no other failure can pass for it."""


def _raises(*_args: object, **_kwargs: object) -> object:
    raise _InjectedFaultError("injected fault")


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(root)
    reindex(root)
    return root


@pytest.mark.parametrize(
    "derivation", ["take_census", "derive_gate_coverage", "derive_gate_ownership"]
)
def test_a_report_derived_after_the_steps_that_raises_escapes_the_gate(
    project: Path, monkeypatch: pytest.MonkeyPatch, derivation: str
) -> None:
    monkeypatch.setattr(gate, derivation, _raises)

    with pytest.raises(_InjectedFaultError):
        run_ci_gate(project, fail_on=None, hub_exports=[], no_reindex=True, tracker=_NoClaims())


def test_the_same_project_gives_a_verdict_when_no_report_raises(project: Path) -> None:
    """The baseline: without it, the escape above could be any failure of the run."""
    result = run_ci_gate(
        project, fail_on=None, hub_exports=[], no_reindex=True, tracker=_NoClaims()
    )

    assert result.crashed == []
