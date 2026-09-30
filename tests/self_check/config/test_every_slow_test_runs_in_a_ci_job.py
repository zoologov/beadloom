"""The suite's ``slow`` tests run in a CI job, so none of them is a phantom.

BDL-076 B3 (``beadloom-hmqn``). ``tests/conftest.py`` skips every ``slow`` test
unless ``BEADLOOM_RUN_SLOW=1``, and the ``tests`` job does not set it. A slow test
that no job runs is a check that exists only in the file that declares it. The
``site-adopters`` job is where they run: it asks for the marker, sets the switch,
and installs the browser the fixtures' Playwright suite needs.
"""

from __future__ import annotations

from typing import Any

from tests.support.ci_workflows import ADVISORY_JOBS, GH_CI, jobs_of
from tests.support.repository_root import TESTS_ROOT

_JOB = "site-adopters"
_SWITCH = "BEADLOOM_RUN_SLOW"


def _steps(job: str) -> list[dict[str, Any]]:
    return [step for step in jobs_of(GH_CI)[job]["steps"] if isinstance(step, dict)]


def _slow_step() -> dict[str, Any]:
    (step,) = [s for s in _steps(_JOB) if "pytest" in str(s.get("run", ""))]
    return step


def test_the_adopters_job_runs_pytest_on_the_slow_marker() -> None:
    run = str(_slow_step()["run"]).split()

    assert run[run.index("-m") + 1] == "slow"


def test_the_adopters_job_turns_the_slow_tests_on() -> None:
    assert _slow_step()["env"][_SWITCH] == "1"


def test_the_adopters_job_runs_the_whole_suite_not_a_folder_of_it() -> None:
    """A path argument would leave a slow test written elsewhere unrun."""
    run = str(_slow_step()["run"])

    assert "tests/" not in run


def test_the_adopters_job_installs_the_browser_before_the_slow_tests() -> None:
    names = [str(step.get("run", "")) for step in _steps(_JOB)]
    install = next(i for i, run in enumerate(names) if "install --with-deps chromium" in run)

    assert install < names.index(str(_slow_step()["run"]))


def test_the_adopters_job_is_advisory() -> None:
    assert _JOB in ADVISORY_JOBS


def test_no_other_job_turns_the_slow_tests_on() -> None:
    """One job owns the slow tests, so a second one is a decision, not a copy."""
    turning_on = sorted(
        name
        for name, job in jobs_of(GH_CI).items()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict) and _SWITCH in (step.get("env") or {})
    )

    assert turning_on == [_JOB]


def test_the_suite_holds_slow_tests_for_the_job_to_run() -> None:
    """The job is not a runner of nothing: at least the adopter fixtures are slow tests."""
    slow = [
        path
        for path in (TESTS_ROOT / "integration").rglob("test_*.py")
        if "pytestmark = pytest.mark.slow" in path.read_text(encoding="utf-8")
    ]

    assert len(slow) >= 3
