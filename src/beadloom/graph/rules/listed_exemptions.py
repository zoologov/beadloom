# beadloom:domain=graph
# beadloom:feature=rule-engine
"""What a listed exemption does: which entry excuses a subject, and which entries stopped.

The suite rules (``test_binding``, ``scenario_binding``) excuse named test
files, feature files and nodes, each list held in a
:class:`~beadloom.graph.rules.types.ListedExemption`. This module answers the
two questions every such rule asks of its exemption list, and owns nothing
else: the rules decide what is a finding, this decides what an exemption does
about it. It mirrors
:mod:`.exemptions`, which answers the same two questions for ``forbid_import``'s
from/to entries; the matching differs (a list of paths or node ids rather than a
pair of globs), the promise does not:

* an ENTRY that excuses nothing is reported by name — DEAD, "delete it". An
  entry is judged on its own, not with the rest of its list, so a file listed as
  not yet split is reported the run after it moves to its node's folder;
* an exemption past the date its ``until`` leads with, while still excusing
  something, is reported once with the count — EXPIRED. Expiry is a finding and
  never a time bomb: nothing reappears at ``error`` because a day passed.
"""

from __future__ import annotations

from collections import Counter
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from beadloom.graph.rules.exemptions import EXPIRED_EXEMPTION_HINT
from beadloom.graph.rules.types import liveness_finding
from beadloom.infrastructure.exit_condition import deadline_passed, exit_condition_deadline

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from beadloom.graph.rules.types import ListedExemption, Violation

#: One entry of one exemption: the exemption's index and the entry's text.
EntryKey = tuple[int, str]


class ExemptionLedger:
    """The exemptions of one rule leg, and how many subjects each entry has excused so far.

    *by_path* decides the matching: a path entry is an ``fnmatch`` glob over a
    repository-relative path, a node entry names one ``ref_id`` exactly.
    """

    def __init__(self, exemptions: Sequence[ListedExemption], *, by_path: bool) -> None:
        self.exemptions = tuple(exemptions)
        self._by_path = by_path
        self._used: Counter[EntryKey] = Counter()

    def excuse(self, subject: str) -> bool:
        """Whether an entry excuses *subject*; the first that does is counted."""
        for index, exemption in enumerate(self.exemptions):
            for entry in exemption.entries:
                if self._covers(entry, subject):
                    self._used[(index, entry)] += 1
                    return True
        return False

    def _covers(self, entry: str, subject: str) -> bool:
        return fnmatchcase(subject, entry) if self._by_path else subject == entry

    @property
    def excused(self) -> int:
        """How many subjects the entries excused in this run."""
        return sum(self._used.values())

    def stale_findings(
        self,
        *,
        rule_name: str,
        rule_description: str,
        subject: str,
        today: date | None = None,
    ) -> list[Violation]:
        """One finding per dead entry and one per expired exemption.

        *subject* names what an entry excuses, as a finding says it (``test
        file``, ``feature file``, ``node``).
        """
        findings: list[Violation] = []
        for index, exemption in enumerate(self.exemptions):
            excused = 0
            for entry in exemption.entries:
                count = self._used[(index, entry)]
                excused += count
                if count == 0:
                    findings.append(
                        _dead(rule_name, rule_description, subject, entry, exemption.until)
                    )
            if excused and deadline_passed(exemption.until, today=today):
                findings.append(_expired(rule_name, rule_description, subject, exemption, excused))
        return findings


def _dead(
    rule_name: str, rule_description: str, subject: str, entry: str, until: str
) -> Violation:
    return liveness_finding(
        rule_name=rule_name,
        rule_description=rule_description,
        message=(
            f"Rule '{rule_name}': the exemption entry `{entry}` excuses no {subject} — "
            f"nothing it names is a finding any more. Its exit condition ({until}) is "
            f"met; delete the entry"
        ),
        remediation=(
            f"delete `{entry}` from the rule's `exempt` list — an entry that excuses "
            f"nothing hides how much of the population is really exempt"
        ),
    )


def _expired(
    rule_name: str,
    rule_description: str,
    subject: str,
    exemption: ListedExemption,
    excused: int,
) -> Violation:
    deadline = exit_condition_deadline(exemption.until)
    plural = subject if excused == 1 else f"{subject}s"
    return liveness_finding(
        rule_name=rule_name,
        rule_description=rule_description,
        message=(
            f"Rule '{rule_name}': the exemption ({exemption.reason}) expired on "
            f"{deadline} and is still excusing {excused} {plural}"
        ),
        remediation=EXPIRED_EXEMPTION_HINT,
    )
