"""The nightly mutation job, and the lockout it must not cause (BDL-068 S3.1).

Q3 was left open with its decision rule stated and was answered by a
measurement: 3 989 mutants over `src/beadloom/graph/rules/` take 54 min 55 s on
a 10-core Apple-silicon machine with six workers, against the ~16-28
runner-minute budget that withdrew `tests-windows`. So the job is scheduled, and
a scheduled job produces no check-run on a pull request — which is exactly how a
required status-check context makes `main` unmergeable.

These tests read the workflow as data. None of them proves the job runs; the
first scheduled run is what does that.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
MUTATION = WORKFLOWS / "mutation.yml"

#: PyYAML reads the workflow key `on` as the boolean True (the Norway problem's
#: cousin). Named here so the tests read as the workflow does.
_ON = True


def _workflow() -> dict[object, object]:
    data = yaml.safe_load(MUTATION.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _triggers() -> dict[str, object]:
    """The workflow's `on:` block, which PyYAML hands back under the key True."""
    triggers = _workflow()[_ON]
    assert isinstance(triggers, dict)
    return triggers


def _job() -> dict[str, object]:
    jobs = _workflow()["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["mutation"]
    assert isinstance(job, dict)
    return job


def _steps_text() -> str:
    steps = _job()["steps"]
    assert isinstance(steps, list)
    return "\n".join(str(step.get("run", "")) for step in steps)


class TestTheJobIsScheduledRatherThanPerPullRequest:
    def test_it_runs_on_a_schedule(self) -> None:
        assert "schedule" in _triggers()

    def test_it_does_not_run_on_a_pull_request(self) -> None:
        """Measured at 55 minutes against a ~4-minute pipeline: a leg this long
        is not a cost so much as the critical path."""
        assert "pull_request" not in _triggers()

    def test_it_can_be_dispatched_by_hand(self) -> None:
        """A nightly with no manual trigger cannot be run when it matters."""
        assert "workflow_dispatch" in _triggers()


class TestItCannotLockTheTrunk:
    def test_the_job_is_not_a_required_status_check(self) -> None:
        """A scheduled workflow reports no check-run on a PR. Requiring its
        context under `strict: true` makes every PR — and `main` — unmergeable,
        which is the trap `DEFAULT_STATUS_CHECK_CONTEXTS` already documents for
        the withdrawn Windows leg."""
        from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

        jobs = _workflow()["jobs"]
        assert isinstance(jobs, dict)
        for name in jobs:
            assert str(name) not in DEFAULT_STATUS_CHECK_CONTEXTS


class TestTheVerdictIsTheProductsAndNotTheRunners:
    def test_the_runner_is_not_the_verdict(self) -> None:
        """`mutmut run` exits non-zero whenever a mutant survives, which is a
        normal outcome. Letting it decide would make the job's verdict "no
        survivors at all", which no suite has."""
        assert "mutmut run" in _steps_text()
        assert "mutmut run --max-children 4 || true" in _steps_text()

    def test_the_score_is_produced_by_the_command(self) -> None:
        text = _steps_text()
        assert "beadloom mutation" in text
        assert "--stats mutants/mutmut-cicd-stats.json" in text

    def test_the_job_stays_answerable_only_for_the_slice_it_ran(self) -> None:
        assert "--only src/beadloom/graph/rules/" in _steps_text()

    def test_the_score_is_held_to_a_floor(self) -> None:
        """A job that cannot fail reports nothing, which is the defect this
        whole slice exists to detect."""
        assert "--min-score" in _steps_text()


class TestTheRunnerStaysOffEveryOtherLeg:
    def test_only_this_workflow_installs_the_mutation_extra(self) -> None:
        """Tool-agnosticism as a property of the pipeline: no leg an adopter
        would copy installs a mutation runner."""
        others = {
            path.name: path.read_text(encoding="utf-8")
            for path in WORKFLOWS.glob("*.yml")
            if path != MUTATION
        }
        for name, text in others.items():
            assert "--extra mutation" not in text, name
            assert "mutmut" not in text, name

    def test_this_workflow_installs_it(self) -> None:
        assert "--extra mutation" in _steps_text()
