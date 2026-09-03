"""`beadloom rooms` — the rooms a project declares, and the one you are in.

The command exists so a completion checklist can name rooms without listing
them: what it prints follows the declaration, so a leg added to a workflow is
covered by the same act that added it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _declaring_project(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        "requires-python = \">=3.10\"\n"
        "classifiers = [\n"
        '  "Programming Language :: Python :: 3.10",\n'
        '  "Programming Language :: Python :: 3.11",\n'
        "]\n",
        encoding="utf-8",
    )
    workflows = root / ".github" / "workflows"
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


class TestTheHumanReport:
    def test_it_names_the_room_this_run_is_in(self, tmp_path: Path) -> None:
        import platform

        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert outcome.exit_code == 0
        assert platform.system() in outcome.stdout

    def test_it_names_every_declared_leg_and_where_it_was_declared(
        self, tmp_path: Path
    ) -> None:
        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert "os=ubuntu-latest python=3.10" in outcome.stdout
        assert ".github/workflows/ci.yml: tests" in outcome.stdout

    def test_it_names_the_unresolved_population(self, tmp_path: Path) -> None:
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True, exist_ok=True)
        (workflows / "ci.yml").write_text(
            "jobs:\n  publish:\n    runs-on: [self-hosted, publisher]\n",
            encoding="utf-8",
        )
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert "unresolved" in outcome.stdout.lower()
        assert "self-hosted+publisher" in outcome.stdout

    def test_a_supported_interpreter_no_leg_enters_is_named(
        self, tmp_path: Path
    ) -> None:
        _declaring_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "classifiers = [\n"
            '  "Programming Language :: Python :: 3.10",\n'
            '  "Programming Language :: Python :: 3.11",\n'
            '  "Programming Language :: Python :: 3.13",\n'
            "]\n",
            encoding="utf-8",
        )
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert "3.13" in outcome.stdout
        assert "no leg" in outcome.stdout

    def test_it_does_not_call_a_room_naming_verdict_stronger(
        self, tmp_path: Path
    ) -> None:
        """The command reports; it never grades. An adjective here would be the
        defect, since a louder word is exactly what a room is not."""
        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert outcome.exit_code == 0
        lowered = outcome.stdout.lower()
        assert "declared room" in lowered
        for word in ("stronger", "safer", "more reliable", "trustworthy"):
            assert word not in lowered


class TestTheMachineReport:
    def test_json_carries_the_current_room_and_every_comparison(
        self, tmp_path: Path
    ) -> None:
        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(tmp_path), "--json"]
        )
        payload = json.loads(outcome.stdout)
        assert payload["current"]["os"]
        assert len(payload["declared"]) == 2
        assert payload["supported"] == ["3.10", "3.11"]

    def test_a_dimension_prints_its_distinct_values_one_per_line(
        self, tmp_path: Path
    ) -> None:
        """The form a completion checklist loops over instead of a literal list."""
        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(tmp_path), "--dimension", "python"]
        )
        assert outcome.exit_code == 0
        assert outcome.stdout.split() == ["3.10", "3.11"]

    def test_a_dimension_no_declared_room_carries_is_refused_not_answered_empty(
        self, tmp_path: Path
    ) -> None:
        """An empty answer would read as "this project has no such axis", which
        is the clean list an agent trusts and stops at."""
        _declaring_project(tmp_path)
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(tmp_path), "--dimension", "os-version"]
        )
        assert outcome.exit_code == 2
        assert "os" in outcome.stderr
        assert "python" in outcome.stderr


class TestAProjectThatDeclaresNothing:
    def test_it_says_so_rather_than_printing_an_empty_list(
        self, tmp_path: Path
    ) -> None:
        outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path)])
        assert outcome.exit_code == 0
        assert "declares no room" in outcome.stdout

    def test_a_dimension_over_no_declared_room_is_refused(self, tmp_path: Path) -> None:
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(tmp_path), "--dimension", "python"]
        )
        assert outcome.exit_code == 2
        assert "declares no room" in outcome.stderr


class TestTheCommandOverThisRepository:
    def test_it_lists_the_interpreters_this_project_supports(self) -> None:
        from pathlib import Path as _Path

        root = _Path(__file__).resolve().parents[1]
        outcome = CliRunner().invoke(
            main, ["rooms", "--project", str(root), "--dimension", "python"]
        )
        assert outcome.exit_code == 0
        assert outcome.stdout.split() == ["3.10", "3.11", "3.12", "3.13"]
