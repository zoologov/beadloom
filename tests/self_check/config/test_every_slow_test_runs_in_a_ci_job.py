"""The suite's ``slow`` tests run in a CI job, so none of them is a phantom.

BDL-076 B3 (``beadloom-hmqn``). ``tests/conftest.py`` skips every ``slow`` test
unless ``BEADLOOM_RUN_SLOW=1``, and the ``tests`` job does not set it. A slow test
that no job runs is a check that exists only in the file that declares it. The
``site-adopters`` job is where they run: it asks for the marker, sets the switch,
and installs the browser the fixtures' Playwright suite needs.

``beadloom-ujzb.20``, an owner ruling of 2026-10-01: the job builds six portals
and runs the browser suite on each, so it no longer runs on every pull request.
It has its own workflow, ``site-adopters.yml``, started by a pull request that
changes what it tests (a ``paths:`` filter), weekly on the default branch, and
by hand. The filter is held here to what the job reads: every slow test file,
every conftest above one, and every support module they import, transitively,
read from the files themselves - so a new support module a slow test imports
fails this check until the filter names it.

``beadloom-ujzb.24``, the re-review's finding m6: the product code those tests RUN
was a hand list, and it missed ``application/reindex``, the ``init`` command and what
they reach. It is now traced: the beadloom half of the build every slow test makes is
run on every adopter fixture in a fresh interpreter, and every ``src/beadloom`` file
entered on the way must be named by the filter (``tests/support/slow_test_trace.py``
says how, and what it cannot see).
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
from functools import cache
from typing import Any

from tests.support.ci_workflows import (
    ADVISORY_JOBS,
    ADVISORY_WORKFLOWS,
    GH_CI,
    GH_SITE_ADOPTERS,
    WORKFLOWS_DIR,
    jobs_of,
    load_yaml,
)
from tests.support.repository_root import REPO_ROOT, TESTS_ROOT

#: Where the beadloom half of the build every slow test makes is written.
_ADOPTER_PORTALS = "tests/support/adopter_portals.py"
_ADOPT = "adopt"
#: The helper every slow test and support module runs a beadloom command through.
_BEADLOOM_CALL = "_beadloom"
#: The command each step of ``adopt`` runs, and the module of the CLI that holds it.
_COMMAND_MODULES = {
    "init": "src/beadloom/services/commands/setup.py",
    "reindex": "src/beadloom/services/commands/index_ops.py",
    "docs": "src/beadloom/services/commands/docs.py",
}

_JOB = "site-adopters"
_SWITCH = "BEADLOOM_RUN_SLOW"
#: A module marked slow as a whole, on a line of its own.
_SLOW_MARK = re.compile(r"^pytestmark = pytest\.mark\.slow$", re.MULTILINE)
_SUPPORT_PACKAGE = "tests.support"

#: PyYAML reads the workflow key `on` as the boolean True.
_ON = True


def _steps(job: str) -> list[dict[str, Any]]:
    return [step for step in jobs_of(GH_SITE_ADOPTERS)[job]["steps"] if isinstance(step, dict)]


def _slow_step() -> dict[str, Any]:
    (step,) = [s for s in _steps(_JOB) if "pytest" in str(s.get("run", ""))]
    return step


def _triggers() -> dict[str, Any]:
    triggers = load_yaml(GH_SITE_ADOPTERS)[_ON]  # type: ignore[index]
    assert isinstance(triggers, dict)
    return triggers


def _paths() -> list[str]:
    paths = _triggers()["pull_request"]["paths"]
    assert isinstance(paths, list)
    return [str(path) for path in paths]


def _matches(pattern: str, path: str) -> bool:
    """GitHub's path-filter glob: ``**`` crosses ``/``, ``*`` does not."""
    regex = "".join(
        ".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part)
        for part in re.split(r"(\*\*|\*)", pattern)
    )
    return re.fullmatch(regex, path) is not None


def _slow_test_files() -> list[str]:
    return sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in TESTS_ROOT.rglob("test_*.py")
        if _SLOW_MARK.search(path.read_text(encoding="utf-8"))
    )


def _support_imports(path: str) -> set[str]:
    """The ``tests/support`` modules *path* imports, as repository paths."""
    tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
            if node.module == _SUPPORT_PACKAGE:
                names = [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        for name in names:
            if name.startswith(_SUPPORT_PACKAGE + "."):
                found.add(name.replace(".", "/") + ".py")
    return {module for module in found if (REPO_ROOT / module).is_file()}


@cache
def _what_the_slow_tests_read() -> frozenset[str]:
    """Every slow test, each conftest above it, and every support module they reach."""
    files: set[str] = set()
    for test in _slow_test_files():
        files.add(test)
        folder = (REPO_ROOT / test).parent
        while folder != TESTS_ROOT.parent:
            conftest = folder / "conftest.py"
            if conftest.is_file():
                files.add(conftest.relative_to(REPO_ROOT).as_posix())
            folder = folder.parent
    pending = sorted(files)
    while pending:
        for module in _support_imports(pending.pop()):
            if module not in files:
                files.add(module)
                pending.append(module)
    return frozenset(files)


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
    assert GH_SITE_ADOPTERS in ADVISORY_WORKFLOWS


def test_no_other_job_turns_the_slow_tests_on() -> None:
    """One job owns the slow tests, so a second one is a decision, not a copy."""
    turning_on = sorted(
        f"{workflow.name}:{name}"
        for workflow in sorted(WORKFLOWS_DIR.glob("*.yml"))
        for name, job in jobs_of(workflow).items()
        if isinstance(job, dict)
        for step in job.get("steps", [])
        if isinstance(step, dict) and _SWITCH in (step.get("env") or {})
    )

    assert turning_on == [f"{GH_SITE_ADOPTERS.name}:{_JOB}"]


def test_the_suite_holds_slow_tests_for_the_job_to_run() -> None:
    """The job is not a runner of nothing: at least the adopter fixtures are slow tests."""
    assert len([path for path in _slow_test_files() if path.startswith("tests/integration/")]) >= 3


# -- when it runs: not on every pull request (owner ruling, 2026-10-01) ---------


def test_the_job_is_not_in_the_pipeline_every_pull_request_runs() -> None:
    assert _JOB not in jobs_of(GH_CI)


def test_a_pull_request_starts_it_only_through_a_paths_filter() -> None:
    """Without ``paths:`` - or with only ``paths-ignore:`` - every pull request runs it."""
    pull_request = _triggers()["pull_request"]
    assert isinstance(pull_request, dict)
    assert _paths()
    assert "paths-ignore" not in pull_request
    assert not [path for path in _paths() if path.startswith("!")]
    assert not [path for path in _paths() if _matches(path, "README.md")]


def test_no_job_of_the_workflow_runs_unconditionally_elsewhere() -> None:
    """The workflow's only events are the filtered pull request, the schedule and a hand."""
    assert set(_triggers()) == {"pull_request", "schedule", "workflow_dispatch"}


def test_it_runs_weekly_and_by_hand() -> None:
    schedule = _triggers()["schedule"]
    assert isinstance(schedule, list)
    (entry,) = schedule
    fields = str(entry["cron"]).split()
    assert fields[2:4] == ["*", "*"]
    assert fields[4] != "*"
    assert "workflow_dispatch" in _triggers()


def test_the_filter_names_every_file_the_slow_tests_read() -> None:
    patterns = _paths()
    unfiltered = sorted(
        path
        for path in _what_the_slow_tests_read()
        if not any(_matches(pattern, path) for pattern in patterns)
    )
    assert unfiltered == []


def test_the_filter_names_the_code_and_fixtures_the_portals_are_built_from() -> None:
    for path in (
        "src/beadloom/application/site/generate.py",
        "src/beadloom/site_scaffold/package.json",
        "src/beadloom/onboarding/__init__.py",
        "src/beadloom/graph/__init__.py",
        "src/beadloom/context_oracle/__init__.py",
        "src/beadloom/services/commands/docs.py",
        "pyproject.toml",
        "uv.lock",
        GH_SITE_ADOPTERS.relative_to(REPO_ROOT).as_posix(),
    ):
        assert (REPO_ROOT / path).is_file(), path
        assert any(_matches(pattern, path) for pattern in _paths()), path
    fixtures = sorted((TESTS_ROOT / "fixtures" / "site").rglob("*"))
    assert fixtures
    fixture = next(path for path in fixtures if path.is_file()).relative_to(REPO_ROOT).as_posix()
    assert any(_matches(pattern, fixture) for pattern in _paths())


def test_every_pattern_of_the_filter_names_something_that_exists() -> None:
    """A folder renamed under a pattern would leave the job unstarted, silently."""
    tracked = [
        path.relative_to(REPO_ROOT).as_posix()
        for root in ("src", "tests", ".github")
        for path in (REPO_ROOT / root).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ] + ["pyproject.toml", "uv.lock"]
    dead = [pattern for pattern in _paths() if not any(_matches(pattern, p) for p in tracked)]
    assert dead == []


# -- the product code the slow tests run (the re-review's m6, beadloom-ujzb.24) ---


@cache
def _product_code_the_slow_tests_run() -> frozenset[str]:
    """Every ``src/beadloom`` file the slow tests' beadloom steps enter, traced afresh."""
    with tempfile.TemporaryDirectory() as workdir:
        traced = subprocess.run(  # noqa: S603 - this interpreter, a module of this suite
            [sys.executable, "-m", "tests.support.slow_test_trace", workdir],
            cwd=workdir,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
    assert traced.returncode == 0, traced.stderr[-4000:]
    return frozenset(traced.stdout.split())


def _beadloom_commands(path: str, function: str | None = None) -> set[str]:
    """The first word of every ``_beadloom(...)`` call in *path*, or in its *function*."""
    tree: ast.AST = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
    if function is not None:
        (tree,) = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == function
        ]
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == _BEADLOOM_CALL
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }


def test_the_trace_runs_every_command_the_slow_tests_run() -> None:
    """A slow test running a command the trace does not would leave its code unnamed."""
    run_by_the_slow_tests = set().union(
        *(_beadloom_commands(path) for path in sorted(_what_the_slow_tests_read()))
    )
    traced = _beadloom_commands(_ADOPTER_PORTALS, _ADOPT)

    assert run_by_the_slow_tests
    assert run_by_the_slow_tests <= traced
    assert traced == set(_COMMAND_MODULES)


def test_the_trace_entered_each_command_it_ran() -> None:
    """A trace that recorded nothing would make the next check pass on nothing."""
    entered = _product_code_the_slow_tests_run()

    assert set(_COMMAND_MODULES.values()) <= entered
    assert "src/beadloom/application/reindex/full.py" in entered


def test_the_filter_names_the_product_code_the_slow_tests_run() -> None:
    patterns = _paths()
    unfiltered = sorted(
        path
        for path in _product_code_the_slow_tests_run()
        if not any(_matches(pattern, path) for pattern in patterns)
    )
    assert unfiltered == []
