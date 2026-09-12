"""BDL-068 S6, `beadloom-0mdo.66` — the `issue-number` command surface.

Presentation and exit codes only. The allocation and the three legs are covered
by ``tests/test_issue_numbers.py`` and by the acceptance feature; what is tested
here is the contract a caller reads: the number on stdout, and an exit code that
distinguishes a finding from a refusal.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
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


# ---------------------------------------------------------------------------
# beadloom-l9ee — the verdict states the population one leg could not reach
# ---------------------------------------------------------------------------


def test_check_names_the_entries_below_the_floor_that_no_leg_judged(tmp_path: Path) -> None:
    """A clean list is trusted and stopped at, so the clean list says what it covers."""
    root = _declared(tmp_path, "5. old\n\n6. older\n\n7. also old\n\n8. the first allocated\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "3 of 4" in result.output
    assert "floor 8" in result.output
    assert "unclaimed-number" in result.output


def test_check_says_nothing_about_the_floor_when_the_ledger_covers_the_whole_log(
    tmp_path: Path,
) -> None:
    """NOT VERIFIED RED, and the reason is that it cannot be.

    The sentence it forbids did not exist before the commit that added it, so
    this assertion passed vacuously beforehand. It is kept because it is the
    only thing that bites if the qualification is later emitted
    unconditionally, which would train a reader to skip the line it is there to
    make them read.
    """
    root = _declared(tmp_path, "8. the only entry\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "below floor" not in result.output


def test_check_names_the_unaccounted_numbers_rather_than_only_counting_them(
    tmp_path: Path,
) -> None:
    """A count is not actionable; the number is the thing a reader goes and looks for."""
    root = _declared(tmp_path, "5. an entry\n\n8. a later entry\n")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root)])
    assert result.exit_code == 0, result.output
    assert "#6" in result.output
    assert "#7" in result.output


def test_check_json_carries_the_unreached_population(tmp_path: Path) -> None:
    root = _declared(tmp_path, "5. old\n\n6. older\n\n7. also old\n\n8. the first allocated\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(root), "--json"])
    assert json.loads(result.stdout)["entries_below_floor"] == 3


# ---------------------------------------------------------------------------
# The three surfaces of one declaration — BDL-069, `beadloom-rqma.8`
# ---------------------------------------------------------------------------


def _misdeclared(root: Path) -> Path:
    """A project that opted in and misspelled one key: `ledger:` written `ledgr:`."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "log.md").write_text("7. an entry\n", encoding="utf-8")
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "issue_log:\n  path: log.md\n  ledgr: ledger\n", encoding="utf-8"
    )
    return root


def test_allocate_tells_a_misdeclaration_from_an_opt_out(tmp_path: Path) -> None:
    """BDL-UX #270 on the command a person types, not on the Gate leg beside it.

    Both surfaces answer "did this project declare a log?" and they gave two
    answers: the Gate named the key while `allocate` printed, byte for byte, the
    sentence a project that wrote nothing gets. The assertion holds the two
    outputs against each other rather than against a literal, so rewording
    either one cannot pass it.
    """
    opted_out = tmp_path / "opted-out"
    opted_out.mkdir()
    (opted_out / ".beadloom").mkdir()
    (opted_out / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    misdeclared = _misdeclared(tmp_path / "misdeclared")

    runner = CliRunner()
    absent = runner.invoke(
        main, ["issue-number", "allocate", "--holder", "a-bead", "--project", str(opted_out)]
    )
    refused = runner.invoke(
        main, ["issue-number", "allocate", "--holder", "a-bead", "--project", str(misdeclared)]
    )
    assert absent.exit_code == 2
    assert refused.exit_code == 2
    assert refused.output != absent.output
    assert "`ledger:`" in refused.output
    assert "`ledgr:`" in refused.output


def test_check_reports_a_declaration_it_could_not_use_rather_than_a_clean_log(
    tmp_path: Path,
) -> None:
    """The third surface #270's own `Command:` line names.

    It never printed the opt-out's sentence, so it was not the byte-identical
    shape the entry measured — it printed `No duplicate, unwritten or unclaimed
    number.` and exited 0, a CLEAN verdict over a log it never opened. A green
    over a population of zero is the same false green one surface along, and the
    refusal it needs is already on the report the Gate renders.
    """
    result = CliRunner().invoke(
        main, ["issue-number", "check", "--project", str(_misdeclared(tmp_path))]
    )
    assert result.exit_code == 1, result.output
    assert "No duplicate, unwritten or unclaimed number." not in result.output
    assert "`ledger:`" in result.output
    assert "`ledgr:`" in result.output


def test_check_still_reports_an_opt_out_as_an_opt_out(tmp_path: Path) -> None:
    """The constraint the fix must not break: declaring nothing is not a finding."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["issue-number", "check", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "No issue log is declared" in result.output


# ---------------------------------------------------------------------------
# A config nobody could read — BDL-069, `beadloom-rqma.9`
# ---------------------------------------------------------------------------

#: The two shapes that reach `read_declaration`'s ``UNREADABLE`` state. The
#: second parses cleanly, so a fix aimed at the YAML parser alone leaves it
#: live — which is why both are parameters of the same test rather than one
#: test and a sentence about the other.
_UNREADABLE_CONFIGS = [
    pytest.param("issue_log:\n  - [unclosed\n", id="does-not-parse"),
    pytest.param("- one\n- two\n", id="top-level-is-a-list"),
]


def _unreadable(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(body, encoding="utf-8")
    return root


def _opted_out(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("body", _UNREADABLE_CONFIGS)
def test_check_says_the_declaration_is_unknown_over_a_config_it_could_not_read(
    tmp_path: Path, body: str
) -> None:
    """The false green this bead exists to remove.

    `check` printed the opt-out's sentence over a config nobody read, at exit 0
    — a positive assertion about a declaration that was never seen. The refusal
    was already on the report and no reader consumed it. Held against the
    opt-out's own output rather than against a literal, so rewording either
    sentence cannot pass this.
    """
    runner = CliRunner()
    unreadable = runner.invoke(
        main, ["issue-number", "check", "--project", str(_unreadable(tmp_path / "u", body))]
    )
    absent = runner.invoke(
        main, ["issue-number", "check", "--project", str(_opted_out(tmp_path / "o"))]
    )
    assert unreadable.exit_code == 0, unreadable.output
    assert unreadable.output != absent.output
    assert "unknown" in unreadable.output
    assert "No issue log is declared" not in unreadable.output
    assert "repair .beadloom/config.yml" in unreadable.output


@pytest.mark.parametrize("body", _UNREADABLE_CONFIGS)
def test_check_json_carries_undetermined_rather_than_a_false_declared(
    tmp_path: Path, body: str
) -> None:
    """A machine acts on this payload, so `"declared": false` was the worse half.

    It stated an opt-out beside the refusal that contradicts it, and carried no
    key saying which of the two to believe.
    """
    result = CliRunner().invoke(
        main,
        [
            "issue-number",
            "check",
            "--project",
            str(_unreadable(tmp_path, body)),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["undetermined"] is True
    assert payload["declared"] is None
    assert payload["refusals"], payload


def test_check_json_tells_an_opt_out_from_an_unread_config(tmp_path: Path) -> None:
    """The other side of the constraint: a project that declared nothing still reads as one."""
    result = CliRunner().invoke(
        main,
        ["issue-number", "check", "--project", str(_opted_out(tmp_path)), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["undetermined"] is False
    assert payload["declared"] is False
    assert payload["refusals"] == []
