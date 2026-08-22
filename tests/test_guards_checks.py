"""The two shipped guards, each proved to FAIL on the condition it guards (BDL-061 S1)."""

from __future__ import annotations

from beadloom.application.guards.checks import BUILTIN_GUARDS
from beadloom.application.guards.contract import (
    ClaimedBead,
    GuardProbes,
    GuardRequest,
)


class _Tracker:
    def __init__(self, beads: tuple[ClaimedBead, ...] | None) -> None:
        self._beads = beads

    def claimed_beads(self) -> tuple[ClaimedBead, ...] | None:
        return self._beads


class _Workspace:
    def __init__(self, branch: str | None) -> None:
        self._branch = branch

    def current_branch(self) -> str | None:
        return self._branch


def _request(tmp_path, *, beads=None, branch=None, context=None, options=None):
    return GuardRequest(
        project_root=tmp_path,
        context=context or {},
        probes=GuardProbes(tracker=_Tracker(beads), workspace=_Workspace(branch)),
        options=options or {},
    )


class TestBeadClaimed:
    guard = "bead-claimed"

    def test_fails_when_no_bead_is_in_progress(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(
            _request(tmp_path, beads=(), context={"path": "src/app.py"})
        )
        assert finding.satisfied is False
        assert finding.skipped_because is None
        assert "src/app.py" in finding.why
        assert "claim" in finding.remediation

    def test_passes_when_a_bead_is_in_progress(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(
            _request(tmp_path, beads=(ClaimedBead(id="bd-1", title="x"),))
        )
        assert finding.satisfied is True
        assert "bd-1" in finding.why

    def test_skips_with_a_reason_when_the_tracker_is_unavailable(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, beads=None))
        assert finding.skipped_because
        assert "tracker" in finding.skipped_because

    def test_always_names_what_it_did_not_check(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, beads=()))
        assert finding.not_covered

    def test_missing_path_is_named_as_not_covered(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, beads=()))
        assert any("path" in item for item in finding.not_covered)


class TestWorkingBranch:
    guard = "working-branch"

    def test_fails_on_the_trunk(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, branch="main"))
        assert finding.satisfied is False
        assert "main" in finding.why

    def test_passes_on_a_feature_branch(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(
            _request(tmp_path, branch="features/BDL-061")
        )
        assert finding.satisfied is True

    def test_trunk_name_is_configurable(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(
            _request(tmp_path, branch="trunk", options={"trunk": "trunk"})
        )
        assert finding.satisfied is False

    def test_skips_with_a_reason_outside_a_branch(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, branch=None))
        assert finding.skipped_because
        assert "branch" in finding.skipped_because

    def test_always_names_what_it_did_not_check(self, tmp_path) -> None:
        finding = BUILTIN_GUARDS[self.guard].check(_request(tmp_path, branch="main"))
        assert finding.not_covered


def test_every_builtin_guard_declares_its_name_and_summary() -> None:
    """The summary is load-bearing: the evaluator prints it as ``not_covered``."""
    assert BUILTIN_GUARDS
    for name, guard in BUILTIN_GUARDS.items():
        assert guard.name == name
        assert guard.summary.strip()
