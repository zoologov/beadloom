# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What a ``forbid_import`` exemption is doing: what it swallows, and whether it has run out.

An exemption baselines a pre-existing crossing instead of narrowing the rule that
catches it. That is only honest while the exemption stays *visible*, and there
are exactly two ways it can stop being visible:

* it swallows a real crossing and nobody says so — the run reports
  ``0 violations`` and the reader has no way to tell "nothing crossed" from
  "what crossed was excused" (A GREEN COUNT IS NOT A CHECKED COUNT);
* its stated exit condition passes and nobody notices — ``until`` was required to
  be a non-empty string and nothing more, so an entry dated 1999 suppressed
  exactly as well as one dated next week (review ``.7`` MAJOR 2 / BDL-061.49).

This module closes both, and owns nothing else: :mod:`.evaluators` decides what
crosses a boundary, this decides what an exemption does about it.

**Every exemption is visible, whatever it does.** The two findings below are
mutually exclusive and exhaustive over the ways an entry can be stale — an
exemption that suppresses nothing is DEAD (reported, "delete it"), and one that
suppresses something past its deadline is EXPIRED (reported, with the count it is
still excusing). An entry that is neither is reported by count, on every run. A
blanket ``from: "*" / to: "*"`` entry therefore cannot hide either: it either
suppresses crossings (counted) or suppresses none (dead).

**Expiry is a finding, never a time bomb.** A crossing does NOT reappear at
``error`` severity because a calendar day passed: a build that reddens with no
commit behind it is the failure mode BDL-061.48 rejected for inert rules, in its
harsher form. A project that wants a hard deadline has ``--fail-on-warn``.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from beadloom.graph.rules.types import (
    MATCHING_FORM_HINT,
    ImportBoundaryRule,
    ImportExemption,
    Violation,
    exit_condition_deadline,
    liveness_finding,
    matches_import_target,
)

if TYPE_CHECKING:
    import sqlite3

#: What to do about an entry whose stated exit condition has passed. It offers
#: both honest moves — retire it, or re-date it — because "delete it" alone is
#: advice nobody can take when the crossing is still there.
EXPIRED_EXEMPTION_HINT = (
    "Fix the crossing and delete the exemption, or replace `until:` with a new "
    "date and the reason the exemption still holds. An exit condition that has "
    "passed is a decision nobody has revisited, not a licence that renews itself."
)


@dataclass(frozen=True)
class SuppressedCrossing:
    """One import that broke a boundary rule and was excused by a named exemption.

    Carried in the lint result so the suppressed *count* can be audited rather
    than trusted: a reader who sees "3 crossings suppressed" can ask which three.
    """

    rule_name: str
    file_path: str
    line_number: int
    import_path: str
    exemption_from: str
    exemption_to: str
    until: str
    expired: bool

    def to_dict(self) -> dict[str, object]:
        """JSON-ready mapping for ``lint --format json``."""
        return {
            "rule_name": self.rule_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "import_path": self.import_path,
            "exemption_from": self.exemption_from,
            "exemption_to": self.exemption_to,
            "until": self.until,
            "expired": self.expired,
        }


def exemption_covers(exemption: ImportExemption, file_path: str, target_as_path: str) -> bool:
    """True when *exemption* excuses this crossing, in the rule's own two vocabularies."""
    return fnmatch.fnmatch(file_path, exemption.from_glob) and matches_import_target(
        target_as_path, exemption.to_glob
    )


def exemption_index_for(
    rule: ImportBoundaryRule, file_path: str, target_as_path: str
) -> int | None:
    """The index of the first exemption covering this crossing, if any."""
    for index, exemption in enumerate(rule.exempt):
        if exemption_covers(exemption, file_path, target_as_path):
            return index
    return None


def is_expired(exemption: ImportExemption, *, today: date | None = None) -> bool:
    """True when this entry names a deadline and that day is behind us.

    The deadline names the last day the exemption covers, so ``until`` equal to
    today is still live: an exit condition is an intent, and reading it one day
    early would make every entry expire before its author's own deadline.
    """
    deadline = exit_condition_deadline(exemption.until)
    return deadline is not None and deadline < (today or date.today())


def stale_exemption_findings(
    rule: ImportBoundaryRule,
    suppressed_per_exemption: dict[int, int],
    *,
    today: date | None = None,
) -> list[Violation]:
    """One finding per exemption that has stopped earning its place — at most one each.

    *suppressed_per_exemption* maps the index of each exemption to the number of
    crossings it excused in this run, which is knowable only from the scan the
    rule evaluation already performs.
    """
    findings: list[Violation] = []
    for index, exemption in enumerate(rule.exempt):
        count = suppressed_per_exemption.get(index, 0)
        if count == 0:
            findings.append(_dead_finding(rule, exemption))
        elif is_expired(exemption, today=today):
            findings.append(_expired_finding(rule, exemption, count))
    return findings


def _dead_finding(rule: ImportBoundaryRule, exemption: ImportExemption) -> Violation:
    """Report an exemption that suppressed nothing — its exit condition firing."""
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"Rule '{rule.name}': the exemption for imports of '{exemption.to_glob}' "
            f"from '{exemption.from_glob}' suppresses nothing — no such crossing is left "
            f"in the code. Its exit condition ({exemption.until}) is met; delete it"
        ),
        remediation=MATCHING_FORM_HINT,
    )


def _expired_finding(
    rule: ImportBoundaryRule, exemption: ImportExemption, suppressed: int
) -> Violation:
    """Report an exemption still excusing crossings past the date it gave itself."""
    deadline = exit_condition_deadline(exemption.until)
    crossings = "crossing" if suppressed == 1 else "crossings"
    return liveness_finding(
        rule_name=rule.name,
        rule_description=rule.description,
        message=(
            f"Rule '{rule.name}': the exemption for imports of '{exemption.to_glob}' "
            f"from '{exemption.from_glob}' expired on {deadline} and is still "
            f"suppressing {suppressed} {crossings}"
        ),
        remediation=EXPIRED_EXEMPTION_HINT,
    )


def suppressed_crossings(
    conn: sqlite3.Connection,
    rules: list[ImportBoundaryRule],
    *,
    today: date | None = None,
) -> list[SuppressedCrossing]:
    """Every crossing an exemption excused, in a deterministic order.

    A second, read-only pass over the same imports :func:`evaluate_import_boundary_rules`
    reads — the same shape :func:`~beadloom.graph.rules.liveness.inert_rule_names`
    has: the count belongs on the *result* rather than among the violations, and a
    caller that only wants the number must not have to evaluate every rule to get
    it. The matching itself is not duplicated; both passes ask
    :func:`exemption_covers`.
    """
    if not rules:
        return []

    imports = sorted(
        (str(row[0]), int(row[1]), str(row[2]))
        for row in conn.execute("SELECT file_path, line_number, import_path FROM code_imports")
    )

    found: list[SuppressedCrossing] = []
    for rule in rules:
        for file_path, line_number, import_path in imports:
            target_as_path = import_path.replace(".", "/")
            if not (
                fnmatch.fnmatch(file_path, rule.from_glob)
                and matches_import_target(target_as_path, rule.to_glob)
            ):
                continue
            index = exemption_index_for(rule, file_path, target_as_path)
            if index is None:
                continue
            exemption = rule.exempt[index]
            found.append(
                SuppressedCrossing(
                    rule_name=rule.name,
                    file_path=file_path,
                    line_number=line_number,
                    import_path=import_path,
                    exemption_from=exemption.from_glob,
                    exemption_to=exemption.to_glob,
                    until=exemption.until,
                    expired=is_expired(exemption, today=today),
                )
            )
    return found
