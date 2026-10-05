"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/integration/doc_sync/issue_numbers/test_issue_numbers.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import re

from beadloom.doc_sync.issue_numbers import (
    DUPLICATE_NUMBER,
    UNCLAIMED_NUMBER,
    UNWRITTEN_CLAIM,
    check_issue_numbers,
    declared_log,
    read_log_numbers,
)
from tests.support.repository_root import REPO_ROOT

CHECKS = (DUPLICATE_NUMBER, UNWRITTEN_CLAIM, UNCLAIMED_NUMBER)

#: How this log heads an entry, open or struck through when closed. Written apart
#: from the module's grammar and narrower than it, so the grammar is measured
#: against a reader it shares no code with.
_ENTRY_HEADING_RE = re.compile(r"^(\d+)\. (?:~~)?\[\d{4}-\d{2}-\d{2}\]", re.MULTILINE)


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
    """Every entry heading the log writes is an entry the grammar reads.

    A grammar that matched nothing would report zero findings and mean nothing,
    and one that matched a sliver would report a clean list over the sliver —
    BDL-UX #267's class, a verdict over 2% of the log read as a verdict over all
    of it. This used to be guarded by ``entries > 200``, a literal that a
    legitimate trim of the log broke: on 2026-10-05 the log was cut to its open
    entries and holds 110. The expectation is now derived from the log itself,
    by a reader deliberately simpler than the grammar — the log's own heading
    convention, ``N. [YYYY-MM-DD]`` or ``N. ~~[YYYY-MM-DD]`` at column 0 — so
    the guard bites on ONE missed heading at any size and no trim moves it.
    """
    log = declared_log(REPO_ROOT).log.read_text(encoding="utf-8")
    headings = [int(number) for number in _ENTRY_HEADING_RE.findall(log)]
    assert headings, "no dated entry heading in the log: the oracle, not the grammar, is wrong"

    report = check_issue_numbers(REPO_ROOT)
    read = read_log_numbers(log).defined
    assert sorted(set(headings) - read) == [], "the entry grammar stopped matching this log"
    assert report.entries >= len(headings), "the verdict counts fewer entries than the log heads"
    assert set(CHECKS) == {DUPLICATE_NUMBER, UNWRITTEN_CLAIM, UNCLAIMED_NUMBER}


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
