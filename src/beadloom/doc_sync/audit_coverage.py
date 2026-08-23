"""Per-fact coverage of a documentation audit: what it did NOT check.

An audit reports the mentions it judged.  Measured on this repo (BDL-UX #173),
that report read ``13 mention(s) fresh`` over a declared list of NINE facts, and
all thirteen were restatements of ONE of them — so a green ``docs-audit`` meant
"one fact of nine was checked" and printed as a clean bill of health.

This module answers the question the finding count cannot: for every fact the
project declares, was anything checked, and if not, why not.  The distinction it
exists to draw is between the docs being SILENT about a fact and the audit being
BLIND to it — the same equation as ``sync-check``'s ``unverified`` and the
linter's dead-rule report: *unverifiable is not clean*.
"""

# beadloom:feature=docs-audit

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from beadloom.doc_sync.scanner import unreadable_reason

if TYPE_CHECKING:
    from beadloom.doc_sync.audit import AuditFinding, Fact

#: At least one mention of the fact was compared against ground truth.  This is
#: about being CHECKED, not about being right: a stale mention is coverage.
COVERAGE_VERIFIED = "verified"

#: No document states the fact.  There was nothing to check — not a defect, but
#: not a verification either, and it must never be counted as one.
COVERAGE_NOT_COVERED = "not_covered"

#: The scanner cannot read a claim of this fact at all (see
#: :func:`beadloom.doc_sync.scanner.unreadable_reason`).  The fact is
#: structurally unverifiable: it appears in the declared list, and no document
#: — right or wrong — could move it.
COVERAGE_UNREADABLE = "unreadable"


@dataclass(frozen=True)
class FactCoverage:
    """How much of one declared fact the audit was actually able to check.

    Attributes
    ----------
    fact:
        The declared ground-truth fact.
    mentions:
        How many documentation mentions were judged against it.
    status:
        ``verified`` / ``not_covered`` / ``unreadable``.
    reason:
        For ``unreadable``, the scanner's own statement of the limit.
        ``None`` otherwise.
    """

    fact: Fact
    mentions: int
    status: str
    reason: str | None = None

    @property
    def verified(self) -> bool:
        """True when something was actually compared for this fact."""
        return self.status == COVERAGE_VERIFIED


def assess_coverage(
    facts: dict[str, Fact], findings: list[AuditFinding]
) -> dict[str, FactCoverage]:
    """Report, for every declared fact, whether the audit checked anything.

    A mention dropped by a ``docs_audit.ignore`` rule is not a finding and so
    does not count as coverage — deliberately.  A suppression that hides the
    only mention of a fact leaves that fact unchecked, and counting it as
    covered would read as coverage the run does not have (the lesson that
    retired three dead ignore entries in BDL-061.44).
    """
    judged = Counter(finding.mention.fact_name for finding in findings)

    coverage: dict[str, FactCoverage] = {}
    for name, fact in facts.items():
        count = judged.get(name, 0)
        if count:
            coverage[name] = FactCoverage(fact, count, COVERAGE_VERIFIED)
            continue
        reason = unreadable_reason(name, fact.value)
        coverage[name] = FactCoverage(
            fact,
            0,
            COVERAGE_UNREADABLE if reason else COVERAGE_NOT_COVERED,
            reason,
        )
    return coverage
