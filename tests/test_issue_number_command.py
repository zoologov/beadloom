"""BDL-068 S6, `beadloom-0mdo.66` — the `issue-number` command surface.

Presentation and exit codes only. The allocation and the three legs are covered
by ``tests/test_issue_numbers.py`` and by the acceptance feature; what is tested
here is the contract a caller reads: the number on stdout, and an exit code that
distinguishes a finding from a refusal.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _declared(root: Path, body: str) -> Path:
    (root / "log.md").write_text(body, encoding="utf-8")
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "issue_log:\n  path: log.md\n  ledger: ledger\n", encoding="utf-8"
    )
    return root


def test_allocate_prints_the_number_it_took(tmp_path: Path) -> None:
    root = _declared(tmp_path, "7. an entry\n")
    result = CliRunner().invoke(
        main, ["issue-number", "allocate", "--holder", "a-bead", "--project", str(root)]
    )
    assert result.exit_code == 0, result.output
    assert "8" in result.output
    assert (root / "ledger" / "0008.md").is_file()


def test_allocate_json_carries_the_number_and_the_claim_path(tmp_path: Path) -> None:
    root = _declared(tmp_path, "7. an entry\n")
    result = CliRunner().invoke(
        main,
        ["issue-number", "allocate", "--holder", "a-bead", "--project", str(root), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["number"] == 8
    assert payload["holder"] == "a-bead"
    assert payload["claim"].endswith("0008.md")


def test_allocate_refuses_an_undeclared_project_and_names_the_config_key(
    tmp_path: Path,
) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["issue-number", "allocate", "--holder", "a-bead", "--project", str(tmp_path)]
    )
    assert result.exit_code == 2
    assert "issue_log" in result.output


def test_check_exits_1_on_a_duplicate_and_names_both_lines(tmp_path: Path) -> None:
    root = _declared(tmp_path, "187. the open one\n\n187. the closed one\n")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root)])
    assert result.exit_code == 1, result.output
    assert "187" in result.output
    assert "log.md:1" in result.output
    assert "log.md:3" in result.output


def test_check_exits_0_and_states_which_legs_read_nothing(tmp_path: Path) -> None:
    root = _declared(tmp_path, "7. an entry\n")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "ledger" in result.output.lower()


def test_check_on_an_undeclared_project_says_so_rather_than_passing_silently(
    tmp_path: Path,
) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["issue-number", "check", "--project", str(tmp_path), "--json"]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["declared"] is False
