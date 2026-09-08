"""Step implementations for `features/gate_not_run.feature` (BDL-068 S6, #247).

Thin by design: every step writes a real pipeline on disk and runs the real
`beadloom ci` over a real project, because the finding is about what one
command's output says about itself. A double of the gate would report whatever
the double was told to report, and what the gate says is the whole finding.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.gate import run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/gate_not_run.feature")

#: The command this fixture's pipeline runs for the suite. Written with a flag
#: so a report that names the tool without the invocation is visibly short.
_SUITE_COMMAND = "uv run pytest --cov=alpha"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    project = tmp_path / "proj"
    (project / ".beadloom" / "_graph").mkdir(parents=True)
    generate_agents_md(project)
    return {"root": project}


def _write_workflow(root: Path, body: str) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(body, encoding="utf-8")


@given("a project whose pipeline runs the test suite")
def _pipeline_runs_the_suite(world: dict[str, Any]) -> None:
    _write_workflow(
        world["root"],
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: uv sync --extra dev\n"
        f"      - run: {_SUITE_COMMAND}\n",
    )


@given("a project whose pipeline runs no verification this report reads")
def _pipeline_runs_nothing_read(world: dict[str, Any]) -> None:
    _write_workflow(
        world["root"],
        "jobs:\n"
        "  publish:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: uv build\n",
    )


@given("a project whose workflow file cannot be parsed")
def _pipeline_unreadable(world: dict[str, Any]) -> None:
    _write_workflow(world["root"], "jobs: [this: is: not: a: mapping\n")


@when("the gate reports on that project")
def _run_the_gate(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", "rich"]
    )
    world["output"] = result.output
    world["exit_code"] = result.exit_code


@when("the gate reports a run that performs the suite itself")
def _run_the_gate_with_the_suite(world: dict[str, Any]) -> None:
    result = run_ci_gate(
        world["root"],
        fail_on=None,
        hub_exports=[],
        no_reindex=False,
        performed_elsewhere=("tests",),
    )
    assert result.coverage is not None
    world["not_performed"] = [item.duty for item in result.coverage.not_performed]


@then("the report names the test suite as not run by this gate")
def _names_the_suite(world: dict[str, Any]) -> None:
    assert "not run by this gate" in world["output"].lower()
    assert "the test suite" in world["output"]


@then("it names the command the pipeline runs for it")
def _names_the_command(world: dict[str, Any]) -> None:
    assert _SUITE_COMMAND in world["output"]


@then("the report does not name the test suite as not run")
def _does_not_name_the_suite(world: dict[str, Any]) -> None:
    assert "the test suite" not in world["not_performed"]


@then("the report names no verification as not run")
def _names_no_verification(world: dict[str, Any]) -> None:
    # The section is still printed, and says the population is empty. An absent
    # section and an empty one are the two answers this project keeps apart.
    assert "not run by this gate" in world["output"].lower()
    assert "the test suite" not in world["output"]
    assert "the type checker" not in world["output"]


@then("the report says the pipeline could not be read")
def _says_unread(world: dict[str, Any]) -> None:
    assert "could not be read" in world["output"]


@then("the verdict and the exit code are the ones the steps produced")
def _verdict_unchanged(world: dict[str, Any]) -> None:
    assert "PASS — gate clean" in world["output"]
    assert world["exit_code"] == 0
