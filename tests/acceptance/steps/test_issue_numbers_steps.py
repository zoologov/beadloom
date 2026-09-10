"""Step implementations for BDL-068 S6 — the issue log's number allocator.

Thin by design: every step arranges a real log on disk and calls the real
allocator or the real check. Nothing is doubled, because a scenario that passes
against a double proves the double.

The concurrency scenario runs two OS processes rather than two threads. The
guarantee under test is ``os.open(O_CREAT | O_EXCL)``, which is the
filesystem's, and two threads in one interpreter would exercise the GIL
instead of it.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.doc_sync.issue_numbers import (
    DUPLICATE_NUMBER,
    UNCLAIMED_NUMBER,
    UNWRITTEN_CLAIM,
    allocate_number,
    check_issue_numbers,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/issue_numbers.feature")


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _project(root: Path, log_body: str, *, declare: bool = True) -> Path:
    """A project root carrying an issue log and the config that declares it."""
    log = root / ".claude" / "development" / "Issues.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(log_body, encoding="utf-8")
    (root / ".beadloom").mkdir(exist_ok=True)
    if declare:
        (root / ".beadloom" / "config.yml").write_text(
            "issue_log:\n"
            "  path: .claude/development/Issues.md\n"
            "  ledger: .claude/development/issues\n",
            encoding="utf-8",
        )
    else:
        (root / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------


@given("an issue log whose highest number is 261")
def _log_at_261(world: dict[str, Any], tmp_path: Path) -> None:
    world["root"] = _project(tmp_path, "## Open Issues\n\n261. [2026-09-09] an entry\n")


@given("an issue log that states 159 in a consolidated heading and in no entry")
def _log_with_heading_only(world: dict[str, Any], tmp_path: Path) -> None:
    world["root"] = _project(
        tmp_path,
        "## Open Issues\n\n"
        "158. [2026-08-20] an entry\n\n"
        "## Closed Issues\n\n"
        "### Import extraction depth — #159 (2026-08-20)\n",
    )


@given("an issue log in which two entries are both numbered 187")
def _log_with_duplicate(world: dict[str, Any], tmp_path: Path) -> None:
    world["root"] = _project(
        tmp_path,
        "## Open Issues\n\n"
        "187. [2026-08-25] the open one\n\n"
        "## Closed Issues\n\n"
        "187. [2026-08-23] the closed one\n",
    )


@given("a ledger holding a claim for 262 and a log with no entry numbered 262")
def _claim_without_entry(world: dict[str, Any], tmp_path: Path) -> None:
    root = _project(tmp_path, "## Open Issues\n\n261. [2026-09-09] an entry\n")
    ledger = root / ".claude" / "development" / "issues"
    ledger.mkdir(parents=True)
    (ledger / "0262.md").write_text("# 262\n\n**Holder:** some-bead\n", encoding="utf-8")
    world["root"] = root


@given("a ledger whose floor is 262 and a log entry numbered 263 that no claim holds")
def _entry_without_claim(world: dict[str, Any], tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "## Open Issues\n\n262. [2026-09-09] the claimed one\n\n263. [2026-09-09] the bypass\n",
    )
    ledger = root / ".claude" / "development" / "issues"
    ledger.mkdir(parents=True)
    (ledger / "0262.md").write_text("# 262\n\n**Holder:** some-bead\n", encoding="utf-8")
    world["root"] = root


@given("a project that declares no issue log")
def _no_log(world: dict[str, Any], tmp_path: Path) -> None:
    world["root"] = _project(tmp_path, "## Open Issues\n", declare=False)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

_RACE = textwrap.dedent(
    """
    import sys
    from pathlib import Path
    from beadloom.doc_sync.issue_numbers import allocate_number
    claim = allocate_number(Path(sys.argv[1]), holder="racer")
    sys.stdout.write(str(claim.number))
    """
)


@when("two writers allocate a number without either seeing the other")
def _two_writers(world: dict[str, Any]) -> None:
    root = world["root"]
    runs = [
        subprocess.Popen(  # noqa: S603 - fixed argv, no shell, test-local script
            [sys.executable, "-c", _RACE, str(root)],
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        for _ in range(2)
    ]
    world["numbers"] = [int(run.communicate()[0]) for run in runs]


@when("a number is allocated")
def _allocate_one(world: dict[str, Any]) -> None:
    world["claim"] = allocate_number(world["root"], holder="a-bead")


@when("the issue numbers are checked")
def _check(world: dict[str, Any]) -> None:
    world["report"] = check_issue_numbers(world["root"])


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------


@then("the two writers hold different numbers")
def _different(world: dict[str, Any]) -> None:
    first, second = world["numbers"]
    assert first != second, f"both writers received {first}"
    assert {first, second} == {262, 263}


@then("each number has a claim file of its own")
def _claim_files(world: dict[str, Any]) -> None:
    ledger = world["root"] / ".claude" / "development" / "issues"
    held = sorted(p.name for p in ledger.glob("*.md"))
    assert held == ["0262.md", "0263.md"], held


@then("the allocated number is not 159")
def _not_159(world: dict[str, Any]) -> None:
    assert world["claim"].number != 159
    assert world["claim"].number == 160


@then("187 is reported as defined twice")
def _duplicate_reported(world: dict[str, Any]) -> None:
    findings = [f for f in world["report"].findings if f.check == DUPLICATE_NUMBER]
    assert [f.number for f in findings] == [187], world["report"].findings


@then("262 is reported as claimed and unwritten")
def _unwritten_reported(world: dict[str, Any]) -> None:
    findings = [f for f in world["report"].findings if f.check == UNWRITTEN_CLAIM]
    assert [f.number for f in findings] == [262], world["report"].findings


@then("263 is reported as unclaimed")
def _unclaimed_reported(world: dict[str, Any]) -> None:
    findings = [f for f in world["report"].findings if f.check == UNCLAIMED_NUMBER]
    assert [f.number for f in findings] == [263], world["report"].findings


@then("the check reports that no issue log is declared")
def _undeclared(world: dict[str, Any]) -> None:
    assert world["report"].declared is False


@then("the check reports no finding")
def _no_findings(world: dict[str, Any]) -> None:
    assert world["report"].findings == ()


# ---------------------------------------------------------------------------
# beadloom-l9ee — the population one leg could not reach
# ---------------------------------------------------------------------------


@given("a ledger whose floor is 262 and a log holding 3 entries below it")
def _log_older_than_its_ledger(world: dict[str, Any], tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "## Open Issues\n\n"
        "259. [2026-09-01] written before the allocator existed\n\n"
        "260. [2026-09-02] and this one\n\n"
        "261. [2026-09-03] and this one\n\n"
        "262. [2026-09-09] the first allocated entry\n",
    )
    ledger = root / ".claude" / "development" / "issues"
    ledger.mkdir(parents=True)
    (ledger / "0262.md").write_text("# 262\n\n**Holder:** some-bead\n", encoding="utf-8")
    world["root"] = root


@given("a ledger whose floor is the log's own first entry")
def _ledger_covering_the_whole_log(world: dict[str, Any], tmp_path: Path) -> None:
    root = _project(tmp_path, "## Open Issues\n\n262. [2026-09-09] the only entry\n")
    ledger = root / ".claude" / "development" / "issues"
    ledger.mkdir(parents=True)
    (ledger / "0262.md").write_text("# 262\n\n**Holder:** some-bead\n", encoding="utf-8")
    world["root"] = root


@then("the verdict names 3 entries as below the floor and judged by no leg")
def _three_below_the_floor(world: dict[str, Any]) -> None:
    report = world["report"]
    assert report.entries_below_floor == 3, report
    assert report.findings == (), "the qualification is coverage, not a finding"


@then("the verdict names no entry as below the floor")
def _none_below_the_floor(world: dict[str, Any]) -> None:
    assert world["report"].entries_below_floor == 0, world["report"]
