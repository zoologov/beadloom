"""Step implementations for the composed hooks that say when a check did not run.

BDL-083 S1a (``beadloom-7i09``). Thin: each step installs the hooks ``install-hooks``
writes, runs one of them as git would, and reads what it printed. The tools on the
hook's PATH are chosen per scenario (:mod:`tests.support.hook_runner`), because what
the hooks print depends on exactly that.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support.committed_project import commit_project, git
from tests.support.hook_runner import install_hooks, run_hook, tools
from tests.support.package_under_test import SHIPPED_FROM

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../services/cli-commands/composed_hooks.feature")

#: The widget spec the monorepo fixture's adopter staged, and the import that broke the layers.
_WIDGET_SPEC = "frontend/src/widgets/kpi-panel/ui/KpiPanel.spec.ts"
_APP_IMPORT = "import '@/app/styles'\n"

#: What uv prints when the command it is asked to run is not installed (uv 0.9, measured).
_UV_SPAWN_FAILURE = (
    "echo 'error: Failed to spawn: `ruff`' >&2\n"
    "echo '  Caused by: No such file or directory (os error 2)' >&2\n"
    "exit 2"
)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {"workdir": tmp_path, "root": None, "shims": {}, "run": None}


def _repository(workdir: Path) -> Path:
    root = workdir / "repo"
    root.mkdir()
    (root / ".beadloom").mkdir()
    (root / "README.md").write_text("a repository\n", encoding="utf-8")
    commit_project(root)
    return root


@given("a repository with the composed hooks installed")
def _a_repository(world: dict[str, Any]) -> None:
    world["root"] = _repository(world["workdir"])
    install_hooks(world["root"])


@given("the monorepo fixture as a repository with the blocking hooks installed")
def _the_monorepo(world: dict[str, Any]) -> None:
    # Copied from the checkout the package under test ships from, and not through
    # `tests.support.monorepo_fixture`: that module finds this repository's root when it
    # is imported, and `test_bead14_s4_binding` runs a copy of this suite that has none.
    # The fixture's one stored file name is a backend test this scenario does not read.
    root = world["workdir"] / "metrics-desk"
    shutil.copytree(SHIPPED_FROM / "tests" / "fixtures" / "monorepo", root)
    commit_project(root)
    world["root"] = root
    install_hooks(world["root"], "--mode", "block")


@given("a staged widget spec that imports the app layer")
def _a_layer_violation(world: dict[str, Any]) -> None:
    spec = world["root"] / _WIDGET_SPEC
    spec.write_text(_APP_IMPORT + spec.read_text(encoding="utf-8"), encoding="utf-8")
    git(world["root"], "add", _WIDGET_SPEC)


@given("a beadloom whose Gate exits 1 without printing a verdict")
def _a_crashing_gate(world: dict[str, Any]) -> None:
    world["shims"]["beadloom"] = "echo 'Traceback (most recent call last):' >&2\nexit 1"


@given("a staged Python file at the repository root")
def _a_root_python_file(world: dict[str, Any]) -> None:
    (world["root"] / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(world["root"], "add", "module.py")


@given("a staged Python file under a subfolder that holds its own pyproject.toml")
def _a_nested_python_file(world: dict[str, Any]) -> None:
    backend = world["root"] / "backend"
    (backend / "src").mkdir(parents=True)
    (backend / "pyproject.toml").write_text('[project]\nname = "backend"\n', encoding="utf-8")
    (backend / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(world["root"], "add", "backend")


@given("a uv that cannot find ruff")
def _uv_without_ruff(world: dict[str, Any]) -> None:
    world["shims"]["uv"] = _UV_SPAWN_FAILURE


@given("a uv that records where it was run")
def _uv_that_records(world: dict[str, Any]) -> None:
    log = world["workdir"] / "uv.log"
    world["uv_log"] = log
    world["shims"]["uv"] = f'echo "$(pwd) $*" >> "{log}"\nexit 0'


@when("the pre-push hook runs without beadloom on its PATH")
def _push_without_beadloom(world: dict[str, Any]) -> None:
    world["run"] = run_hook(world["root"], "pre-push", tools(world["workdir"]))


@when("the pre-push hook runs")
def _push(world: dict[str, Any]) -> None:
    path = tools(world["workdir"], shims=world["shims"])
    world["run"] = run_hook(world["root"], "pre-push", path)


@when("the pre-commit hook runs with beadloom on its PATH")
def _commit_with_beadloom(world: dict[str, Any]) -> None:
    path = tools(world["workdir"], beadloom=True, shims=world["shims"])
    world["run"] = run_hook(world["root"], "pre-commit", path)


@when("the pre-commit hook runs")
def _commit(world: dict[str, Any]) -> None:
    path = tools(world["workdir"], shims=world["shims"])
    world["run"] = run_hook(world["root"], "pre-commit", path)


def _said(world: dict[str, Any]) -> str:
    run = world["run"]
    return f"{run.stdout}{run.stderr}"


@then("the hook exits non-zero")
def _non_zero(world: dict[str, Any]) -> None:
    assert world["run"].returncode != 0, _said(world)


@then("the hook says the Gate did not run because beadloom is not on its PATH")
def _says_beadloom_missing(world: dict[str, Any]) -> None:
    said = _said(world)
    assert "Gate did not run" in said, said
    assert "not on the PATH" in said, said


@then("the hook says the Gate did not run")
def _says_not_run(world: dict[str, Any]) -> None:
    assert "the Gate did not run" in _said(world), _said(world)


@then("the hook says nothing about stale documentation")
def _no_stale_docs(world: dict[str, Any]) -> None:
    assert "stale" not in _said(world).lower(), _said(world)


@then("the hook names the fsd-layers violation of the widget's node")
def _names_the_violation(world: dict[str, Any]) -> None:
    said = _said(world)
    assert "fsd-layers" in said, said
    assert "widgets-kpi-panel" in said, said


@then("the hook blocks the commit for the architecture lint")
def _blocks_for_lint(world: dict[str, Any]) -> None:
    assert world["run"].returncode != 0, _said(world)
    assert "architecture lint" in _said(world), _said(world)


@then("the hook says ruff did not run and shows uv's own words")
def _says_ruff_not_run(world: dict[str, Any]) -> None:
    said = _said(world)
    assert "ruff did not run" in said, said
    assert "Failed to spawn" in said, said


@then("the hook does not report ruff lint violations")
def _no_violations(world: dict[str, Any]) -> None:
    assert "ruff lint violations" not in _said(world), _said(world)


@then("ruff ran in that subfolder over the file's path inside it")
def _ran_in_the_subfolder(world: dict[str, Any]) -> None:
    calls = world["uv_log"].read_text(encoding="utf-8").splitlines()
    backend = (world["root"] / "backend").resolve()
    assert f"{backend} run ruff check src/service.py" in calls, calls
