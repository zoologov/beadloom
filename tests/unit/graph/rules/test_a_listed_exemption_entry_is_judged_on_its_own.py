"""What a listed exemption does: which entry excuses a subject, and which entries stopped.

The ledger behind the suite rules' ``exempt`` lists (``listed_exemptions``). Each entry is
counted on its own, a dead entry is reported by name, and an exemption past its deadline
is reported once with the number of subjects it still excuses. Every case here is pure:
the ledger reads no file, no index and no clock except the ``today`` it is handed.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import EXPIRED_EXEMPTION_HINT, ListedExemption
from beadloom.graph.rules.listed_exemptions import ExemptionLedger

if TYPE_CHECKING:
    from beadloom.graph.rules import Violation

RULE_NAME = "features-live-in-their-folder"
RULE_DESCRIPTION = "a feature file lives in the folder of its node"
SUBJECT = "feature file"
PAST = "2020-01-31 once the files move"
TODAY = date(2024, 6, 1)


def _exemption(*entries: str, until: str = PAST) -> ListedExemption:
    return ListedExemption(entries=entries, reason="the move is pending", until=until)


def _stale(ledger: ExemptionLedger, *, today: date = TODAY) -> list[Violation]:
    return ledger.stale_findings(
        rule_name=RULE_NAME, rule_description=RULE_DESCRIPTION, subject=SUBJECT, today=today
    )


class TestAPathEntryIsAGlob:
    def test_a_glob_entry_excuses_a_path_it_matches(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/old/*.feature")], by_path=True)

        excused = ledger.excuse("specs/old/billing.feature")

        assert excused is True

    def test_a_node_entry_excuses_only_the_identical_id(self) -> None:
        ledger = ExemptionLedger([_exemption("bill*")], by_path=False)

        excused = ledger.excuse("billing")

        assert excused is False


class TestTheCountOfExcusedSubjects:
    def test_one_entry_counts_every_subject_it_excuses(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/old/*.feature")], by_path=True)
        ledger.excuse("specs/old/a.feature")
        ledger.excuse("specs/old/b.feature")

        excused = ledger.excused

        assert excused == 2


class TestAnExpiredExemption:
    @pytest.mark.parametrize(
        ("entries", "subjects", "stated"),
        [
            pytest.param(("specs/old/*.feature",), ("specs/old/a.feature",), "1 feature file"),
            pytest.param(
                ("specs/old/*.feature",),
                ("specs/old/a.feature", "specs/old/b.feature"),
                "2 feature files",
                id="one entry, two subjects",
            ),
            pytest.param(
                ("specs/a.feature", "specs/b.feature"),
                ("specs/a.feature", "specs/b.feature"),
                "2 feature files",
                id="two entries, one subject each",
            ),
        ],
    )
    def test_it_states_how_many_subjects_its_entries_still_excuse(
        self, entries: tuple[str, ...], subjects: tuple[str, ...], stated: str
    ) -> None:
        ledger = ExemptionLedger([_exemption(*entries)], by_path=True)
        for subject in subjects:
            ledger.excuse(subject)

        (expired,) = _stale(ledger)

        assert expired.message.endswith(f"still excusing {stated}")

    def test_its_finding_names_the_rule_it_belongs_to(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/a.feature")], by_path=True)
        ledger.excuse("specs/a.feature")

        (expired,) = _stale(ledger)

        assert (expired.rule_name, expired.rule_description) == (RULE_NAME, RULE_DESCRIPTION)
        assert expired.message.startswith(f"Rule '{RULE_NAME}': the exemption")

    def test_its_finding_carries_the_expired_exemption_hint(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/a.feature")], by_path=True)
        ledger.excuse("specs/a.feature")

        (expired,) = _stale(ledger)

        assert expired.remediation == EXPIRED_EXEMPTION_HINT

    def test_it_is_judged_against_the_day_it_is_handed(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/a.feature")], by_path=True)
        ledger.excuse("specs/a.feature")

        findings = _stale(ledger, today=date(2020, 1, 30))

        assert findings == []


class TestADeadEntry:
    def test_its_finding_names_the_entry_the_subject_and_the_exit_condition(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/gone.feature")], by_path=True)

        (dead,) = _stale(ledger)

        assert dead.message == (
            f"Rule '{RULE_NAME}': the exemption entry `specs/gone.feature` excuses no "
            f"feature file — nothing it names is a finding any more. Its exit condition "
            f"({PAST}) is met; delete the entry"
        )

    def test_its_finding_carries_the_rule_description(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/gone.feature")], by_path=True)

        (dead,) = _stale(ledger)

        assert dead.rule_description == RULE_DESCRIPTION

    def test_its_remedy_is_to_delete_the_entry_it_names(self) -> None:
        ledger = ExemptionLedger([_exemption("specs/gone.feature")], by_path=True)

        (dead,) = _stale(ledger)

        assert dead.remediation is not None
        assert dead.remediation.startswith("delete `specs/gone.feature` from the rule's `exempt`")
