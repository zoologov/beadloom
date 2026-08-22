"""Guard probes at the boundary: every way a tool declines to answer (BDL-061 S1).

The happy paths run against the **real** ``git`` and ``bd`` in
``tests/test_guards_cli.py::TestRealProbes``. What is stubbed here is only the
failure surface of those two tools, which cannot be provoked reliably from a real
binary: bd missing, bd exiting non-zero, bd printing something that is not the
expected JSON, git raising at the process boundary.

Standing rule 4 applies and is stated rather than implied: **these tests prove
the contract of the ``bd`` seam, not bd's own behaviour.** What they do prove is
the property everything else rests on — a probe that cannot answer returns
``None``, which makes the guard *skip with a reason*. Any of these paths
returning ``()`` instead would report "no bead is claimed" and turn a broken tool
into a false violation; returning a bead would be a false pass.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.models import GuardOutcome
from beadloom.services import bd_seam, guard_probes
from beadloom.services.bd_seam import BdResult, BdUnavailableError
from beadloom.services.guard_probes import build_probes


@pytest.fixture()
def bd_project(tmp_path):
    """A project that looks like it uses bd, so the tracker actually queries it."""
    (tmp_path / ".beads").mkdir()
    return tmp_path


def _bd_returns(monkeypatch, result) -> None:
    """Stub the bd seam — the IO boundary, not the unit under test."""

    def fake_run_bd(_args, *, cwd=None):  # signature parity with run_bd
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(bd_seam, "run_bd", fake_run_bd)


class TestTrackerDeclinesToAnswer:
    @pytest.mark.parametrize(
        ("label", "result"),
        [
            ("bd not installed", BdUnavailableError("no bd on PATH")),
            ("bd exited non-zero", BdResult(returncode=2, stdout="", stderr="boom")),
            ("bd printed junk", BdResult(returncode=0, stdout="not json", stderr="")),
            ("bd printed an object", BdResult(returncode=0, stdout='{"id": "x"}', stderr="")),
        ],
    )
    def test_an_unanswerable_tracker_reports_none_not_an_empty_result(
        self, bd_project, monkeypatch, label, result
    ) -> None:
        _bd_returns(monkeypatch, result)

        assert build_probes(bd_project).tracker.claimed_beads() is None, label

    @pytest.mark.parametrize(
        ("label", "result"),
        [
            ("bd not installed", BdUnavailableError("no bd on PATH")),
            ("bd exited non-zero", BdResult(returncode=2, stdout="", stderr="boom")),
            ("bd printed junk", BdResult(returncode=0, stdout="not json", stderr="")),
        ],
    )
    def test_a_broken_tracker_skips_the_guard_instead_of_failing_it(
        self, bd_project, monkeypatch, label, result
    ) -> None:
        """A tool that is down must not read as "the developer did not claim a bead"."""
        _bd_returns(monkeypatch, result)

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=bd_project,
            context={"path": "src/app.py"},
            probes=build_probes(bd_project),
        )

        assert verdict.outcome is GuardOutcome.SKIP, label
        assert verdict.exit_code == 0

    def test_an_empty_tracker_result_is_a_violation_not_a_skip(
        self, bd_project, monkeypatch
    ) -> None:
        """The other side of the same coin: bd answering "nothing claimed" must bite."""
        _bd_returns(monkeypatch, BdResult(returncode=0, stdout="[]", stderr=""))

        verdict = evaluate_guard(
            "bead-claimed",
            project_root=bd_project,
            context={"path": "src/app.py"},
            probes=build_probes(bd_project),
        )

        assert verdict.outcome is GuardOutcome.WARN

    def test_only_in_progress_beads_count_as_claimed(self, bd_project, monkeypatch) -> None:
        _bd_returns(
            monkeypatch,
            BdResult(
                returncode=0,
                stdout=json.dumps(
                    [
                        {"id": "bd-1", "status": "open", "title": "not started"},
                        {"id": "bd-2", "status": "in_progress", "title": "claimed"},
                        {"id": "bd-3", "status": "closed", "title": "done"},
                        {"status": "in_progress", "title": "no id at all"},
                        "not even a mapping",
                    ]
                ),
                stderr="",
            ),
        )

        claimed = build_probes(bd_project).tracker.claimed_beads()

        assert [bead.id for bead in claimed] == ["bd-2"]

    def test_a_project_without_beads_is_never_queried(self, tmp_path, monkeypatch) -> None:
        """Invoking bd in an unrelated repo could initialise state there (dev decision 7)."""

        def explode(_args, *, cwd=None):  # signature parity with run_bd
            msg = "bd was invoked in a project that does not use it"
            raise AssertionError(msg)

        monkeypatch.setattr(bd_seam, "run_bd", explode)

        assert build_probes(tmp_path).tracker.claimed_beads() is None


class TestWorkspaceDeclinesToAnswer:
    @pytest.mark.parametrize(
        "error",
        [OSError("git is gone"), subprocess.TimeoutExpired(cmd="git", timeout=10)],
    )
    def test_a_git_failure_at_the_process_boundary_reports_no_branch(
        self, tmp_path, monkeypatch, error
    ) -> None:
        def explode(*_args, **_kwargs):
            raise error

        monkeypatch.setattr(guard_probes.subprocess, "run", explode)

        assert build_probes(tmp_path).workspace.current_branch() is None

    def test_a_detached_head_prints_nothing_and_reads_as_no_branch(
        self, tmp_path, monkeypatch
    ) -> None:
        """``git branch --show-current`` is silent on a detached HEAD — not an error."""
        monkeypatch.setattr(
            guard_probes.subprocess,
            "run",
            lambda *_a, **_k: subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout="\n", stderr=""
            ),
        )

        assert build_probes(tmp_path).workspace.current_branch() is None

    def test_an_unknown_branch_skips_the_guard_rather_than_assuming_the_trunk(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setattr(
            guard_probes.subprocess,
            "run",
            lambda *_a, **_k: subprocess.CompletedProcess(
                args=["git"], returncode=128, stdout="", stderr="not a repository"
            ),
        )

        verdict = evaluate_guard(
            "working-branch", project_root=tmp_path, probes=build_probes(tmp_path)
        )

        assert verdict.outcome is GuardOutcome.SKIP
        assert verdict.why.strip()
