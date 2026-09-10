"""BDL-068 S6, `beadloom-0mdo.66` — the issue log's number allocator.

The acceptance scenarios in ``tests/acceptance/features/issue_numbers.feature``
carry the behaviour. These are the edges underneath it: the entry grammar's
boundaries, the states in which a leg reads nothing, and this repository's own
log, which is the only corpus of 236 hand-written entries available to check the
grammar against.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from beadloom.doc_sync.issue_numbers import (
    DUPLICATE_NUMBER,
    UNCLAIMED_NUMBER,
    UNWRITTEN_CLAIM,
    allocate_number,
    check_issue_numbers,
    read_claims,
    read_log_numbers,
    resolve_issue_log,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _declared(root: Path, body: str) -> Path:
    log = root / "log.md"
    log.write_text(body, encoding="utf-8")
    (root / ".beadloom").mkdir(exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "issue_log:\n  path: log.md\n  ledger: ledger\n", encoding="utf-8"
    )
    return root


# ---------------------------------------------------------------------------
# The entry grammar
# ---------------------------------------------------------------------------


def test_a_numbered_line_inside_a_fence_is_not_an_entry() -> None:
    """The log's own template block is fenced and numbered; it defines nothing."""
    numbers = read_log_numbers(
        "## Template\n\n```markdown\n1. [YYYY-MM-DD] Short description\n```\n\n7. a real entry\n"
    )
    assert [entry.number for entry in numbers.entries] == [7]


def test_an_indented_ordered_list_item_is_not_an_entry() -> None:
    """Entries inline their own sub-lists; a sub-item is not a second entry."""
    numbers = read_log_numbers("7. an entry\n\n    1. a point the entry makes\n")
    assert [entry.number for entry in numbers.entries] == [7]


def test_a_number_stated_only_in_a_heading_is_mentioned_and_not_defined() -> None:
    """The two populations answer different questions and are kept apart."""
    numbers = read_log_numbers("7. an entry\n\n### Import extraction depth — #159 (2026-08-20)\n")
    assert numbers.defined == frozenset({7})
    assert 159 in numbers.mentioned
    assert numbers.highest == 159


def test_a_foreign_trackers_number_is_not_read_as_this_logs() -> None:
    """Found by dogfooding the allocator on this repository's own log.

    The first real allocation returned **#32164**, because
    ``anthropics/claude-code#32163`` is a reference to another project's tracker
    and the mention population read it as a number in use here. That is BDL-UX
    #253's class in a second place: a token attributed to a named subject, read
    as a claim about ours.
    """
    numbers = read_log_numbers(
        "7. an entry\n\n    upstream carries it: anthropics/claude-code#32163\n"
    )
    assert numbers.mentioned == frozenset()
    assert numbers.highest == 7


def test_an_unattributed_number_still_counts_and_only_costs_a_number() -> None:
    """The safe direction, stated because it is a deliberate imprecision.

    ``PR #59`` names no repository, so this reader cannot tell it from an entry
    reference and counts it. The consequence is a floor one higher than it needs
    to be — a wasted number, never a collision — which is the direction to err in.
    """
    numbers = read_log_numbers("7. an entry\n\n    landed as PR #59\n")
    assert numbers.mentioned == frozenset({59})


def test_a_gap_below_the_highest_is_unaccounted_rather_than_free() -> None:
    numbers = read_log_numbers("1. one\n\n4. four\n")
    assert numbers.unaccounted == (2, 3)


def test_an_entry_line_carries_the_line_it_was_defined_at() -> None:
    numbers = read_log_numbers("## Open\n\n7. the seventh\n")
    assert numbers.entries[0].line == 3
    assert numbers.entries[0].title.startswith("the seventh")


# ---------------------------------------------------------------------------
# The allocation
# ---------------------------------------------------------------------------


def test_allocation_refuses_a_project_that_declares_no_log(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text("languages:\n- .py\n", encoding="utf-8")
    with pytest.raises(ValueError, match="issue_log"):
        allocate_number(tmp_path, holder="a-bead")


def test_allocation_creates_the_ledger_and_names_its_holder(tmp_path: Path) -> None:
    root = _declared(tmp_path, "7. an entry\n")
    claim = allocate_number(root, holder="beadloom-0mdo.66")
    assert claim.number == 8
    assert claim.path.name == "0008.md"
    assert read_claims(root / "ledger")[0].holder == "beadloom-0mdo.66"


def test_allocation_skips_a_number_already_claimed_by_a_file(tmp_path: Path) -> None:
    """The ledger is consulted, not just the log: a claim not yet written up holds."""
    root = _declared(tmp_path, "7. an entry\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    assert allocate_number(root, holder="a-bead").number == 9


def test_a_claim_whose_body_is_unreadable_still_holds_its_number(tmp_path: Path) -> None:
    root = _declared(tmp_path, "7. an entry\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_bytes(b"\xff\xfe not utf-8")
    claims = read_claims(root / "ledger")
    assert [claim.number for claim in claims] == [8]
    assert claims[0].holder == ""


# ---------------------------------------------------------------------------
# What each leg can and cannot read
# ---------------------------------------------------------------------------


def test_before_the_first_allocation_two_legs_read_nothing_and_say_so(tmp_path: Path) -> None:
    """An empty ledger has no floor, so `unclaimed` and `unwritten` enter no number."""
    root = _declared(tmp_path, "7. an entry\n\n8. another\n")
    report = check_issue_numbers(root)
    assert report.floor is None
    assert report.not_verified is True
    assert report.passed is True


def test_a_declared_log_that_is_missing_is_reported_rather_than_read_as_clean(
    tmp_path: Path,
) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text(
        "issue_log:\n  path: absent.md\n  ledger: ledger\n", encoding="utf-8"
    )
    report = check_issue_numbers(tmp_path)
    assert report.declared is True
    assert report.log_missing is True
    assert report.not_verified is True


def test_an_entry_below_the_floor_is_not_required_to_have_been_allocated(
    tmp_path: Path,
) -> None:
    """The floor is the ledger's own first claim, so history is not retro-required."""
    root = _declared(tmp_path, "7. an entry\n\n8. another\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    report = check_issue_numbers(root)
    assert report.floor == 8
    assert report.findings == ()


def test_a_config_block_missing_the_ledger_key_declares_nothing(tmp_path: Path) -> None:
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "config.yml").write_text(
        "issue_log:\n  path: log.md\n", encoding="utf-8"
    )
    assert resolve_issue_log(tmp_path) is None
    assert check_issue_numbers(tmp_path).declared is False


# ---------------------------------------------------------------------------
# This repository's own log
# ---------------------------------------------------------------------------


def test_this_repositorys_issue_log_carries_no_number_finding() -> None:
    """The invariant, not a literal.

    ``beadloom-mr2l.72`` filed the hand-maintained population literal as its own
    defect, so this asserts the property the check exists for and no count. It
    bites the day an entry is hand-appended past the ledger's floor, a number is
    claimed and never written up, or two entries share a number -- which is the
    state this repository was in until #187 was repaired on 2026-09-09.
    """
    report = check_issue_numbers(REPO_ROOT)
    assert report.declared is True, "this repository declares its own issue log"
    assert [(f.check, f.number) for f in report.findings] == []


def test_this_repositorys_log_is_read_by_the_grammar_it_is_written_in() -> None:
    """A grammar that matched nothing would report zero findings and mean nothing."""
    report = check_issue_numbers(REPO_ROOT)
    assert report.entries > 200, "the entry grammar stopped matching this log"
    assert set(CHECKS) == {DUPLICATE_NUMBER, UNWRITTEN_CLAIM, UNCLAIMED_NUMBER}


CHECKS = (DUPLICATE_NUMBER, UNWRITTEN_CLAIM, UNCLAIMED_NUMBER)


# ---------------------------------------------------------------------------
# beadloom-l9ee — the population `unclaimed-number` could not reach
# ---------------------------------------------------------------------------


def test_entries_below_the_floor_are_counted_as_the_population_no_leg_judged(
    tmp_path: Path,
) -> None:
    """The skip above is deliberate; the silence about it was not.

    ``_ledger_findings`` passes over every entry below the floor, so a report
    stating ``240 entr(ies)`` beside ``No duplicate, unwritten or unclaimed
    number`` describes a leg that entered five of them. CONTEXT's constraint is
    that the unresolved population is part of every answer.
    """
    root = _declared(tmp_path, "5. old\n\n6. older\n\n7. also old\n\n8. the first allocated\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    report = check_issue_numbers(root)
    assert report.floor == 8
    assert report.entries == 4
    assert report.entries_below_floor == 3
    assert report.findings == (), "an unreached population is coverage, not a finding"


def test_a_ledger_covering_the_whole_log_leaves_nothing_to_qualify(tmp_path: Path) -> None:
    """The sentence must be absent when it would be noise, or it trains a skip."""
    root = _declared(tmp_path, "8. the only entry\n")
    (root / "ledger").mkdir()
    (root / "ledger" / "0008.md").write_text("# 8\n", encoding="utf-8")
    report = check_issue_numbers(root)
    assert report.entries_below_floor == 0


def test_with_no_floor_at_all_the_count_is_zero_because_not_verified_carries_it(
    tmp_path: Path,
) -> None:
    """Two statements of one fact are two things that can disagree.

    Before a project's first allocation there is no floor for an entry to be
    below, and :attr:`IssueNumberReport.not_verified` already says both ledger
    legs entered no number. This count stays 0 so the empty case has one home.
    """
    root = _declared(tmp_path, "7. an entry\n\n8. another\n")
    report = check_issue_numbers(root)
    assert report.floor is None
    assert report.not_verified is True
    assert report.entries_below_floor == 0


def test_this_repositorys_log_is_mostly_older_than_its_own_ledger() -> None:
    """The property, not the literal — the same rule the corpus tests above follow.

    This repository adopted the allocator on 2026-09-09 with 240 entries already
    written, so `unclaimed-number` reaches the handful at or above the floor and
    no more. A report that did not say so would read as a clean bill over the
    whole log.
    """
    report = check_issue_numbers(REPO_ROOT)
    assert report.floor is not None, "this repository has allocated at least one number"
    assert report.entries_below_floor > 0, "the log predates its ledger"
    assert report.entries_below_floor < report.entries
