"""BDL-061.39: CI carries a PLATFORM dimension — and it cannot re-skip its way green.

WHY A SECOND DIMENSION AT ALL. BDL-061.38 added the locale dimension and priced
it honestly; BDL-061.42 then turned both rows green after fixing what they found
— 108 ASCII / 83 8-bit locale-attributable failures, one product call site that
could not write a git hook on a non-UTF-8 image, a federation export raising past
its own handler, a ``--help`` exiting 1. The dimension has therefore *paid*, in
defects, not in argument. Windows is the next axis, and the largest one left:
``src/`` contains **no** ``sys.platform`` or ``os.name`` branch anywhere, so the
product is either genuinely platform-neutral or has simply never been asked.

WHY THE LEG WAS NOT ADDED FIRST, which is the whole point of this bead. Six guard
tests carried ``skipif(sys.platform == "win32")``. A ``windows-latest`` leg added
while those marks stood would have SKIPPED all six on the one platform they name
and reported "passed" — the same shape as the vacuous symlink-loop test .36
repaired and the vacuous ``LC_ALL=C`` leg .38 measured. The marks were replaced
first (:mod:`tests.symlink_capability`, :mod:`tests.test_windows_dimension`), and
this file exists so they cannot come back by the CI door:

1. The leg is genuinely Windows (VACUOUS check) **and** this process can create a
   symbolic link (DEGRADED check). The second is the lock this bead is about: a
   Windows runner without ``SeCreateSymbolicLinkPrivilege`` would capability-skip
   exactly those six rows again, run ~6000 other tests and go green, and nobody
   would be told that the leg had stopped covering the thing it was bought for.
2. That probe script is EXECUTED by this suite, so the least-tested code in any
   repository — a shell script inside a YAML string — is covered, and it cannot
   drift from the workflow because the test reads the workflow.
3. The leg runs the WHOLE suite with extras byte-identical to the ``tests`` leg,
   so exactly one thing varies and a red leg is attributable to the platform.

EXPECT IT RED ON THE FIRST RUN, and read it the way .38's sentence says: *the
value is the delta between legs, never any leg's colour.* A red check with no
legend is ignored by the second week, so the legend is in ci.yml next to the job.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TEMPLATE = (
    REPO_ROOT
    / "src"
    / "beadloom"
    / "onboarding"
    / "templates"
    / "ai_techwriter"
    / "github-workflow.yml"
)

#: The job that carries the platform dimension.
WINDOWS_JOB = "tests-windows"

#: The leg it must differ from in exactly one respect.
BASELINE_JOB = "tests"


def _jobs(path: Path) -> dict[str, Any]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    jobs = doc["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _job(name: str, path: Path = CI) -> dict[str, Any]:
    jobs = _jobs(path)
    assert name in jobs, f"{path.name} declares no {name!r} job"
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    steps = job.get("steps", [])
    assert isinstance(steps, list)
    return [s for s in steps if isinstance(s, dict)]


def _step_with(job: dict[str, Any], needle: str) -> dict[str, Any]:
    matches = [s for s in _steps(job) if needle in str(s.get("run", ""))]
    assert len(matches) == 1, (
        f"expected exactly one step whose run contains {needle!r}, got {len(matches)}"
    )
    return matches[0]


def _env_of(step: dict[str, Any], job: dict[str, Any]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in (job.get("env"), step.get("env")):
        if isinstance(source, dict):
            merged.update({str(k): str(v) for k, v in source.items()})
    return merged


# --------------------------------------------------------------------------- #
# 1. The dimension exists, on the platform it claims
# --------------------------------------------------------------------------- #


def test_ci_declares_a_windows_leg() -> None:
    """The axis is the OPERATING SYSTEM, and it is not simulated."""
    assert _job(WINDOWS_JOB)["runs-on"] == "windows-latest"


def test_the_windows_leg_is_a_single_row_so_it_is_not_the_python_matrix_again() -> None:
    """One interpreter, on purpose — .38's reasoning, applied to this axis.

    Python 3.13 is the version the owner runs locally, so the ONLY difference
    from the known-green local suite is the operating system and a red leg is
    attributable to it. The version dimension is the ``tests`` matrix's job, and
    crossing the two would be four Windows legs for an ambiguous signal at twice
    the billing rate. A single row also means there is no ``fail-fast`` question:
    there is no sibling to cancel.
    """
    job = _job(WINDOWS_JOB)

    assert "strategy" not in job, (
        "a matrix here would fan out into several windows-latest legs; the leg "
        "is deliberately one row (see this test's docstring)"
    )
    setup = _step_with(job, "uv python install")
    assert "3.13" in str(setup["run"])


def test_the_windows_leg_runs_the_whole_suite() -> None:
    """A subset would narrow the dimension to the code we already suspect.

    Which is the exact mistake being corrected: .36's defect was invisible to the
    WHOLE suite, not to a small one. No ``--cov`` either — coverage is a property
    of the code, not of the platform, and the ``tests`` legs already enforce the
    floor; keeping it would add a second way for the leg to be red that has
    nothing to do with the dimension.
    """
    run = str(_step_with(_job(WINDOWS_JOB), "pytest")["run"])

    assert "pytest" in run
    for narrowing in (" -k", " -m ", "--cov", "tests/test_"):
        assert narrowing not in run, f"the leg is narrowed by {narrowing!r}: {run!r}"


def test_the_windows_leg_installs_the_same_extras_as_the_tests_leg() -> None:
    """ONLY the platform varies. Divergent extras would confound the signal.

    In particular the ``languages`` extra: the tree-sitter grammar wheels are the
    most platform-specific dependency in the project, so dropping them here to
    make the leg install cleanly would silently remove the language tests from
    the one platform they have never run on.
    """

    def install(job_name: str) -> str:
        return str(_step_with(_job(job_name), "uv sync")["run"]).strip()

    assert install(WINDOWS_JOB) == install(BASELINE_JOB)


def test_a_missing_grammar_fails_the_windows_leg_rather_than_skipping() -> None:
    """BDL-059 S1's guard, carried onto the new platform.

    Grammar wheels are built per platform; if a wheel is missing on Windows the
    language tests would SKIP and the leg would stay green while covering less
    than the leg it is compared against. The delta would then be an artifact of
    what installed rather than of the platform.
    """
    job = _job(WINDOWS_JOB)
    env = _env_of(_step_with(job, "pytest"), job)

    assert env.get("BEADLOOM_REQUIRE_LANGUAGE_GRAMMARS") == "1"


def test_the_windows_leg_can_actually_fail_the_pipeline() -> None:
    """No ``continue-on-error``: a check that cannot fail is theatre.

    This is the tempting "fix" the first time the leg is red — the leg is
    EXPECTED red on its first run — so it fails the suite instead of being left
    to a reviewer's memory.
    """
    job = _job(WINDOWS_JOB)

    assert job.get("continue-on-error") in (None, False)
    for step in _steps(job):
        assert step.get("continue-on-error") in (None, False), step.get("name")


def test_the_windows_leg_does_not_delay_the_ai_techwriter() -> None:
    """The wall-clock cost lands on the merge, not on the doc refresh.

    ``ai-techwriter`` runs on a self-hosted VPS and is gated on
    ``needs: [gate, tests, site-build]``. The Windows leg is the pipeline's new
    critical path (~2-3x the ubuntu legs, billed at 2x), and adding it to those
    needs would hold the doc refresh behind it for no benefit — the same
    decision .38 took for the locale legs.
    """
    needs = _job("ai-techwriter").get("needs", [])

    assert WINDOWS_JOB not in needs, needs


# --------------------------------------------------------------------------- #
# 2. The anti-vacuity probe — and it guards TWO ways of asserting nothing
# --------------------------------------------------------------------------- #


def test_the_probe_runs_before_the_suite() -> None:
    """A probe after the suite reports on a leg whose verdict is already cast."""
    steps = _steps(_job(WINDOWS_JOB))
    order = [i for i, s in enumerate(steps) if "run" in s]
    probe = next(i for i in order if "VACUOUS" in str(steps[i]["run"]))
    suite = next(i for i in order if "pytest" in str(steps[i]["run"]))

    assert probe < suite


def test_the_probe_step_runs_under_bash_not_pwsh() -> None:
    """Not a style point — the default shell on ``windows-latest`` is pwsh.

    ``uv run python - <<'PY'`` is a POSIX heredoc. pwsh does not implement one:
    it would parse ``<<'PY'`` as a redirection error and the step's behaviour
    would be neither the script nor a clean failure. ``shell: bash`` selects the
    Git-for-Windows bash that the image ships.
    """
    assert _step_with(_job(WINDOWS_JOB), "VACUOUS").get("shell") == "bash"


def _probe_script() -> str:
    """The heredoc body of ci.yml's 'Assert the leg is genuinely Windows' step."""
    run = str(_step_with(_job(WINDOWS_JOB), "VACUOUS")["run"])
    body = run.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    return textwrap.dedent(body)


def _run_probe(monkeypatch: pytest.MonkeyPatch, *, platform: str, sep: str) -> str | None:
    """Execute ci.yml's OWN script as the runner would see it.

    Returns the refusal message, or ``None`` when the probe accepted the leg.
    """
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(os, "sep", sep)
    try:
        # `exec` is the point rather than a shortcut: this runs the workflow's
        # script, not a copy of it, so the two cannot drift. The input is a file
        # in this repository, read from a fixed path.
        exec(compile(_probe_script(), "<ci.yml windows probe>", "exec"), {})  # noqa: S102
    except SystemExit as exit_:
        return str(exit_)
    return None


def test_probe_accepts_a_real_windows_runner_that_can_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The good case: Windows, and the symlink privilege is held.

    Run on a POSIX machine with the platform strings substituted — the symlink
    half is REAL here (this process can link), which is what makes the row a
    check of the script rather than of the substitution.
    """
    assert _run_probe(monkeypatch, platform="win32", sep="\\") is None


def test_probe_refuses_a_leg_that_is_not_windows_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VACUOUS: a ``runs-on`` typo, or a matrix row that quietly became ubuntu.

    Everything downstream would pass, and the leg would report a Windows verdict
    about Linux.
    """
    message = _run_probe(monkeypatch, platform="linux", sep="/")

    assert message is not None and "VACUOUS" in message


def test_probe_refuses_a_windows_runner_without_the_symlink_privilege(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DEGRADED, and this is the lock the bead is about.

    ``SeCreateSymbolicLinkPrivilege`` is not held by default outside Developer
    Mode. Without it the six capability-gated guard rows skip again — the leg
    runs ~6000 other tests, reports green, and has stopped covering the one
    thing it was bought for. WinError 1314 is injected because this machine will
    never raise it.
    """

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError(1314, "A required privilege is not held by the client")

    monkeypatch.setattr(os, "symlink", refuse)
    message = _run_probe(monkeypatch, platform="win32", sep="\\")

    assert message is not None and "DEGRADED" in message
    assert "1314" in message or "required privilege" in message


def test_probe_refuses_a_link_that_does_not_follow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The subtler degradation: a filesystem that "supports" links by copying.

    ``os.symlink`` returns, the file exists, and resolution lands on the copy
    rather than on the target — so the six rows would RUN and assert the wrong
    thing, which is worse than skipping.
    """

    def degrade(target: object, link: object, **kwargs: object) -> None:
        del target
        Path(str(link)).write_text("not a link\n", encoding="utf-8")

    monkeypatch.setattr(os, "symlink", degrade)
    message = _run_probe(monkeypatch, platform="win32", sep="\\")

    assert message is not None and "DEGRADED" in message


def test_the_probe_uses_a_temporary_directory_it_cleans_up(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """It must not leave a link behind that a later step in the job trips over.

    ``tempfile.tempdir`` is redirected at a directory only this test can see, so
    the assertion is deterministic rather than a race against whatever else is
    writing to the system temp directory.
    """
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    assert _run_probe(monkeypatch, platform="win32", sep="\\") is None
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- #
# 3. The lockout invariant — stated over this repo AND over what adopters get
# --------------------------------------------------------------------------- #


def test_the_windows_check_is_required() -> None:
    """A real check that gates nothing is advisory, which is .36's failure shape.

    The repo's own lockout guard (``test_required_contexts_match_ci_yml_check_runs``)
    derives the check-run names from ci.yml and asserts derived == required, so
    this is forced the moment the job exists — steps 3 and 4 of the bead land
    together. It is safe to land red: ``DEFAULT_STATUS_CHECK_CONTEXTS`` is a
    CONSTANT, and the live protection on ``main`` changes only when someone runs
    ``beadloom setup-branch-protection``. Do not run it until the leg is green.
    """
    from beadloom.onboarding.branch_protection import DEFAULT_STATUS_CHECK_CONTEXTS

    assert WINDOWS_JOB in DEFAULT_STATUS_CHECK_CONTEXTS


def test_the_vendored_template_runs_the_windows_leg_too() -> None:
    """.38 §5's lesson, which cost it a second commit.

    ``DEFAULT_STATUS_CHECK_CONTEXTS`` is not this repo's config — it is what
    ``beadloom setup-branch-protection`` PUTs in ANY repo, and a scaffolded
    repo's pipeline is the VENDORED TEMPLATE. A required context the template
    never produces leaves that adopter's ``main`` permanently unmergeable.
    """
    assert WINDOWS_JOB in _jobs(TEMPLATE), (
        f"the vendored template declares no {WINDOWS_JOB!r} job, but "
        "DEFAULT_STATUS_CHECK_CONTEXTS requires that check in every repo "
        "setup-branch-protection is run against -> adopter lockout"
    )


def test_the_template_tells_an_adopter_how_to_drop_the_platform_dimension() -> None:
    """The honest part of shipping this to someone else's Linux-only service.

    A non-UTF-8 container is the default deployment, so .38's locale rows are
    on-thesis for everyone. Windows is not: an adopter whose product only ever
    runs on Linux is being handed a required check they do not want. The cost is
    theirs to refuse, so the template says how — deleting the job alone would
    lock them out, and the two edits have to be named together.
    """
    windows_comment = _comment_above(TEMPLATE, f"  {WINDOWS_JOB}:")

    assert "--check" in windows_comment, windows_comment
    assert "setup-branch-protection" in windows_comment, windows_comment
    assert "DELETE THIS JOB" in windows_comment, windows_comment


def _comment_above(path: Path, key: str) -> str:
    """The contiguous block of comment lines immediately preceding *key*."""
    lines = path.read_text(encoding="utf-8").splitlines()
    index = lines.index(key)
    block: list[str] = []
    while index > 0 and lines[index - 1].lstrip().startswith("#"):
        index -= 1
        block.insert(0, lines[index])
    return "\n".join(block)
