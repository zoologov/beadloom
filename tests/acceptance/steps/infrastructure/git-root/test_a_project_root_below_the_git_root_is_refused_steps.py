"""Steps of `infrastructure/git-root/a_project_root_below_the_git_root_is_refused.feature`.

BDL-083 S2e (``beadloom-7pd6``), BDL-UX #325. Real git repositories built in the test's
directory and the real commands through the command line: the nested layout is the monorepo
fixture committed one folder below the repository's root, the control is the same fixture
committed at its own root. Nothing between the repository and the verdict is mocked.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main
from tests.support.committed_project import commit_project
from tests.support.shipped_monorepo import (
    shipped_monorepo_below_its_git_root,
    shipped_monorepo_checkout,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../infrastructure/git-root/a_project_root_below_the_git_root_is_refused.feature")

#: The documented pair whose code file the scenarios change: the monorepo fixture's backend.
_CHANGED_CODE = "backend/src/application/__init__.py"
_CHANGED_DOC = "backend/README.md"


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _reindexed(root: Path) -> Path:
    result = CliRunner().invoke(main, ["reindex", "--project", str(root)])
    assert result.exit_code == 0, result.output
    return root


@given("a git repository whose code sits one folder below its root, with no .beadloom")
def _plain_nested(tmp_path: Path, state: dict[str, Any]) -> None:
    repository = tmp_path / "repository"
    package = repository / "app" / "src" / "app"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("def greet() -> str:\n    return 'hi'\n")
    commit_project(repository)
    state["root"] = repository / "app"
    state["git_root"] = repository


@given("the monorepo fixture committed one folder below its git root, indexed")
def _nested_monorepo(tmp_path: Path, state: dict[str, Any]) -> None:
    root = shipped_monorepo_below_its_git_root(tmp_path)
    state["root"] = _reindexed(root)
    state["git_root"] = root.parent


@given("the monorepo fixture committed at its own git root, indexed")
def _monorepo(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = _reindexed(shipped_monorepo_checkout(tmp_path))


@given("a code file of a documented pair changed since HEAD")
def _changed(state: dict[str, Any]) -> None:
    code = state["root"] / _CHANGED_CODE
    code.write_text(code.read_text(encoding="utf-8") + "\nCHANGED = True\n", encoding="utf-8")


def _run(state: dict[str, Any], *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    state["exit_code"] = result.exit_code
    state["output"] = result.output


@when("init runs non-interactively in that folder")
def _init(state: dict[str, Any]) -> None:
    _run(state, "init", "--yes")


@when("doctor runs in the project root")
def _doctor(state: dict[str, Any]) -> None:
    _run(state, "doctor")


@when("sync-check runs against HEAD in the project root")
def _since(state: dict[str, Any]) -> None:
    _run(state, "sync-check", "--since", "HEAD")


@then("the command exits 1")
def _exit_1(state: dict[str, Any]) -> None:
    assert state["exit_code"] == 1, state["output"]


@then("the command exits 0")
def _exit_0(state: dict[str, Any]) -> None:
    assert state["exit_code"] == 0, state["output"]


@then("the command exits 2")
def _exit_2(state: dict[str, Any]) -> None:
    assert state["exit_code"] == 2, state["output"]


@then("the output says the git root is above the project root and names both paths")
def _named(state: dict[str, Any]) -> None:
    output = " ".join(state["output"].split())

    assert "the git root is above the project root" in output, output
    assert str(state["git_root"].resolve()) in output, output
    assert str(state["root"].resolve()) in output, output


@then("the folder holds no .beadloom")
def _nothing_written(state: dict[str, Any]) -> None:
    assert not (state["root"] / ".beadloom").exists()


@then("no pair is reported fresh")
def _no_fresh_pair(state: dict[str, Any]) -> None:
    assert "[ok]" not in state["output"], state["output"]


@then("doctor says no git root is above the project root")
def _root_ok(state: dict[str, Any]) -> None:
    assert "[ok] No git root above the project root." in state["output"], state["output"]


@then("the changed pair is reported stale")
def _stale(state: dict[str, Any]) -> None:
    lines = [line for line in state["output"].splitlines() if _CHANGED_CODE in line]

    assert any("[stale]" in line and _CHANGED_DOC in line for line in lines), state["output"]
