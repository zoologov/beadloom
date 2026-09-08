"""The gate says which verifications no step of it performed (BDL-UX #247).

`beadloom ci` does not run the test suite, and until this file existed it never
said so, while the pre-push hook it backs is described as "the full `beadloom
ci`". Two measurements in one slice: a document change reddened two tests under
a green gate, and a docs wave spilled a code span past a line under a gate that
returned rc 0 over that tree twice, after which all six test legs went red on
one assertion that reproduces locally in 0.07 s.

The half this file pins is the CHEAP one: the statement. Whether the hook should
also run the suite is a separate decision, recorded on the bead.

Two properties, and the second is the one that keeps the first from rotting:

1. the claim names the duty and the command the project's own pipeline runs for
   it, so a reader can act on it;
2. the claim is derived from the RUN'S STEP LIST, so a suite step added to the
   gate later removes the line by the same act.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.application.gate_coverage import derive_gate_coverage
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

_SUITE = "uv run pytest --cov=alpha --cov-fail-under=80"


def _clean_project(project_root: Path) -> None:
    """A project whose every gate step passes (no rules => no lint violations)."""
    (project_root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(project_root)


def _workflow(project_root: Path, body: str, name: str = "ci.yml") -> None:
    workflows = project_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / name).write_text(body, encoding="utf-8")


def _pipeline_with(project_root: Path, *commands: str, job: str = "tests") -> None:
    steps = "".join(f"      - run: {command}\n" for command in commands)
    _workflow(
        project_root,
        f"jobs:\n  {job}:\n    runs-on: ubuntu-latest\n    steps:\n{steps}",
    )


class TestWhatTheGateDidNotPerform:
    def test_the_suite_the_pipeline_runs_is_named_with_its_command(
        self, tmp_path: Path
    ) -> None:
        _pipeline_with(tmp_path, "uv sync --extra dev", _SUITE)
        coverage = derive_gate_coverage(tmp_path, performed=("lint", "doctor"))
        named = {item.duty: item for item in coverage.not_performed}
        assert "the test suite" in named
        assert named["the test suite"].command == _SUITE
        assert named["the test suite"].source == ".github/workflows/ci.yml: tests"

    def test_the_style_linter_and_the_type_checker_are_named_too(
        self, tmp_path: Path
    ) -> None:
        _pipeline_with(
            tmp_path, "uv run ruff check src/ tests/", "uv run mypy src/", _SUITE
        )
        coverage = derive_gate_coverage(tmp_path, performed=("lint",))
        assert [item.duty for item in coverage.not_performed] == [
            "the test suite",
            "the style linter",
            "the type checker",
        ]

    def test_the_architecture_lint_step_is_not_read_as_the_style_linter(
        self, tmp_path: Path
    ) -> None:
        # The gate's own step is called `lint` and checks the architecture
        # boundaries, not the source style. A reader who takes [PASS] lint for
        # ruff is exactly the confusion this line exists to end, so the step
        # name must not silence the ruff claim.
        _pipeline_with(tmp_path, "uv run ruff check src/")
        coverage = derive_gate_coverage(tmp_path, performed=("lint",))
        assert [item.duty for item in coverage.not_performed] == ["the style linter"]

    def test_a_verification_a_step_of_this_run_performs_is_not_claimed(
        self, tmp_path: Path
    ) -> None:
        # The anti-staleness property: the answer is a function of the step
        # list, so a suite step added to the gate later removes the line.
        _pipeline_with(tmp_path, _SUITE)
        for step_name in ("tests", "pytest", "test-suite", "suite"):
            coverage = derive_gate_coverage(tmp_path, performed=("lint", step_name))
            assert coverage.not_performed == (), step_name

    def test_a_command_behind_a_runner_prefix_is_still_recognised(
        self, tmp_path: Path
    ) -> None:
        _pipeline_with(tmp_path, "python -m pytest -q", "poetry run mypy src")
        coverage = derive_gate_coverage(tmp_path, performed=())
        assert [item.duty for item in coverage.not_performed] == [
            "the test suite",
            "the type checker",
        ]

    def test_a_pipeline_running_none_of_them_is_not_claimed_about(
        self, tmp_path: Path
    ) -> None:
        # An adopter whose suite runs under a name this report does not read is
        # told the population is empty, not that nothing is missing.
        _pipeline_with(tmp_path, "go test ./...", job="build")
        coverage = derive_gate_coverage(tmp_path, performed=("lint",))
        assert coverage.not_performed == ()
        assert coverage.declared == ()

    def test_a_workflow_that_cannot_be_parsed_is_reported_unread(
        self, tmp_path: Path
    ) -> None:
        _workflow(tmp_path, "jobs: [this: is: not: a: mapping\n")
        coverage = derive_gate_coverage(tmp_path, performed=())
        assert coverage.not_performed == ()
        assert len(coverage.unresolved) == 1
        assert coverage.unresolved[0].source == ".github/workflows/ci.yml"

    def test_a_project_with_no_pipeline_says_so_rather_than_nothing(
        self, tmp_path: Path
    ) -> None:
        coverage = derive_gate_coverage(tmp_path, performed=("lint",))
        assert coverage.not_performed == ()
        assert coverage.inspected == 0


class TestTheGateSaysIt:
    def test_the_result_carries_the_coverage(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.coverage is not None
        assert [item.duty for item in result.coverage.not_performed] == [
            "the test suite"
        ]

    def test_a_caller_that_runs_the_suite_itself_is_not_contradicted(
        self, tmp_path: Path
    ) -> None:
        # `complete_bead` runs the suite beside the gate. One run must not say
        # the suite was not run while the same run ran it.
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        result = run_ci_gate(
            tmp_path,
            fail_on=None,
            hub_exports=[],
            no_reindex=False,
            performed_elsewhere=("tests",),
        )
        assert result.coverage is not None
        assert result.coverage.not_performed == ()

    def test_the_human_report_names_the_suite_under_the_verdict(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        out = CliRunner().invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "rich"]
        )
        assert out.exit_code == 0
        assert "PASS — gate clean" in out.output
        assert "Not run by this gate:" in out.output
        assert f"the test suite — `{_SUITE}`" in out.output
        assert ".github/workflows/ci.yml: tests" in out.output

    def test_the_json_report_carries_it_structurally(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        out = CliRunner().invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "json"]
        )
        payload = json.loads(out.stdout)
        assert payload["not_run"]["not_performed"] == [
            {
                "duty": "the test suite",
                "command": _SUITE,
                "source": ".github/workflows/ci.yml: tests",
            }
        ]

    def test_the_github_report_annotates_it_as_a_notice(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        out = CliRunner().invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "github"]
        )
        assert "::notice::not run by this gate: the test suite" in out.output

    def test_naming_what_was_not_run_changes_no_verdict(self, tmp_path: Path) -> None:
        # A guard, and it is meant to stay green: the line is a qualification of
        # the verdict, never a step with a status of its own.
        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.ok
        assert all(step.name != "tests" for step in result.steps)


class TestTheToolAnAgentClosesABeadOn:
    """`complete_bead` runs the suite beside the gate, so it says a different thing."""

    def test_a_gate_only_run_says_the_suite_was_not_run(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        from beadloom.services.bd_seam import BdResult
        from beadloom.services.mcp_server import handle_complete_bead

        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        with patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, "", "")
            result = handle_complete_bead(tmp_path, bead="bd-1", run_tests=False)

        assert result["not_run"] == ["the test suite"]

    def test_a_run_that_ran_the_suite_does_not_report_it_as_not_run(
        self, tmp_path: Path
    ) -> None:
        from unittest.mock import patch

        from beadloom.services.bd_seam import BdResult
        from beadloom.services.mcp_server import handle_complete_bead

        _clean_project(tmp_path)
        _pipeline_with(tmp_path, _SUITE)
        with patch("beadloom.services.mcp_server.run_bd") as run_bd, patch(
            "beadloom.services.mcp_server._run_test_suite", return_value=(True, "ok")
        ):
            run_bd.return_value = BdResult(0, "", "")
            result = handle_complete_bead(tmp_path, bead="bd-1", run_tests=True)

        assert result["not_run"] == []
