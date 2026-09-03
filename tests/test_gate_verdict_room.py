"""The Gate's verdict carries the room it was taken in, and says nothing louder.

Two halves, and the second is the one that is easy to lose. A verdict that names
its room is ANSWERABLE -- a reader can see which of the declared rooms the run
entered. It is not a stronger verdict, and this file fails if the room ever
changes a status, an exit code or a finding count.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.application.gate import run_ci_gate
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _clean_project(project_root: Path) -> None:
    """A project whose every gate step passes (no rules => no lint violations)."""
    (project_root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(project_root)


def _declare_a_leg(project_root: Path) -> None:
    workflows = project_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    strategy:\n"
        "      matrix:\n"
        '        python-version: ["3.10", "3.11"]\n',
        encoding="utf-8",
    )


class TestTheVerdictCarriesItsRoom:
    def test_the_result_names_the_room_the_run_was_taken_in(
        self, tmp_path: Path
    ) -> None:
        import platform

        _clean_project(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.room is not None
        assert result.room.current.dimensions["os"] == platform.system()

    def test_the_result_names_the_declared_rooms_it_did_not_enter(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.room is not None
        assert len(result.room.comparisons) == 2

    def test_the_human_report_prints_the_room(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        runner = CliRunner()
        outcome = runner.invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "rich"]
        )
        assert "Room:" in outcome.stdout
        assert "not entered" in outcome.stdout

    def test_the_json_report_carries_the_room(self, tmp_path: Path) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        runner = CliRunner()
        outcome = runner.invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "json"]
        )
        payload = json.loads(outcome.stdout)
        assert payload["room"]["current"]["os"]
        assert len(payload["room"]["not_entered"]) == 2

    def test_the_github_report_carries_the_room_as_a_notice(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        runner = CliRunner()
        outcome = runner.invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "github"]
        )
        assert "::notice::room" in outcome.stdout


class TestNamingTheRoomIsNotAStrongerVerdict:
    """The room may never change what the Gate decided, only what it says."""

    def test_a_passing_gate_still_passes_and_carries_no_extra_finding(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.ok is True
        assert result.findings == []
        assert result.room is not None
        assert result.room.not_entered != ()

    def test_the_room_is_not_a_step(self, tmp_path: Path) -> None:
        """A step has a status, and a status is a claim the room does not make."""
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        result = run_ci_gate(tmp_path, fail_on=None, hub_exports=[], no_reindex=False)
        assert result.room is not None
        assert [s.name for s in result.steps if "room" in s.name] == []

    def test_a_failing_gate_still_exits_one_with_its_room_named(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        graph_dir = tmp_path / ".beadloom" / "_graph"
        (graph_dir / "rules.yml").write_text(
            "rules:\n"
            "  - name: nonexistent-domain-needs-parent\n"
            "    require: {}\n"
            "    description: domain nonexistent-domain\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        outcome = runner.invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "rich"]
        )
        assert outcome.exit_code == 1
        assert "FAIL — gate blocked" in outcome.stdout
        assert "Room:" in outcome.stdout

    def test_a_project_declaring_no_leg_gets_a_room_and_no_leg_claim(
        self, tmp_path: Path
    ) -> None:
        _clean_project(tmp_path)
        runner = CliRunner()
        outcome = runner.invoke(
            main, ["ci", "--project", str(tmp_path), "--format", "rich"]
        )
        assert outcome.exit_code == 0
        assert "Room:" in outcome.stdout
        assert "declares no room" in outcome.stdout


class TestTheRefusingGateAlsoNamesItsRoom:
    """`complete_bead` is the verdict an agent closes a bead on."""

    def test_a_pass_carries_the_room_it_was_taken_in(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.bd_seam import BdResult
        from beadloom.services.mcp_server import handle_complete_bead

        _clean_project(tmp_path)
        green = GateResult(steps=[GateStep("lint", passed=True, summary="clean")])
        with patch(
            "beadloom.services.mcp_server.run_ci_gate", return_value=green
        ), patch("beadloom.services.mcp_server.run_bd") as run_bd:
            run_bd.return_value = BdResult(0, "next: bd-2\n", "")
            result = handle_complete_bead(tmp_path, bead="bd-1", run_tests=False)

        assert result["status"] == "PASS"
        assert result["room"]["current"]

    def test_a_refusal_carries_it_too(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        from beadloom.application.gate import GateResult, GateStep
        from beadloom.services.mcp_server import handle_complete_bead

        _clean_project(tmp_path)
        _declare_a_leg(tmp_path)
        red = GateResult(
            steps=[GateStep("lint", passed=False, findings=[{"why": "boom"}])]
        )
        with patch("beadloom.services.mcp_server.run_ci_gate", return_value=red), patch(
            "beadloom.services.mcp_server.run_bd"
        ):
            result = handle_complete_bead(tmp_path, bead="bd-1", run_tests=False)

        assert result["status"] == "FAIL"
        assert result["room"]["declared"] == 2
        assert result["room"]["entered"] <= result["room"]["declared"]
