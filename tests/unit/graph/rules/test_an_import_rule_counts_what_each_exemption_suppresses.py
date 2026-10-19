"""One ``forbid_import`` rule judged over the imports it is handed.

``evaluate_one_import_rule`` is pure over its arguments: the import rows, and the two
population sizes the dead-glob finding quotes. These cases pin what its findings say, the
numbers in them above all, because a count that is off by one reads exactly like a correct
one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import ImportBoundaryRule, ImportExemption
from beadloom.graph.rules.evaluators import evaluate_one_import_rule

if TYPE_CHECKING:
    from beadloom.graph.rules import Violation

#: A deadline behind every clock this suite runs under.
LONG_PAST = "2000-01-01 when the adapter moves"

#: Three import rows from two files, naming three distinct targets.
IMPORTS = [
    ("src/app/ui/panel.py", 3, "app.store.rows"),
    ("src/app/ui/panel.py", 4, "app.store.cache"),
    ("src/app/ui/menu.py", 7, "app.logic.plan"),
]


def _rule(**kwargs: object) -> ImportBoundaryRule:
    defaults: dict[str, object] = {
        "name": "ui-reads-no-store",
        "description": "the UI never reads the store directly",
        "from_glob": "src/app/ui/*",
        "to_glob": "app/store/*",
    }
    defaults.update(kwargs)
    return ImportBoundaryRule(**defaults)  # type: ignore[arg-type]  # kwargs typed by the test


def _evaluate(
    rule: ImportBoundaryRule, imports: list[tuple[str, int, str]] = IMPORTS
) -> list[Violation]:
    return evaluate_one_import_rule(rule, imports, file_count=2, target_count=3)


class TestAnExpiredExemption:
    @pytest.mark.parametrize(
        ("imports", "stated"),
        [
            pytest.param(IMPORTS[:1], "suppressing 1 crossing", id="one crossing"),
            pytest.param(IMPORTS, "suppressing 2 crossings", id="two crossings"),
        ],
    )
    def test_it_states_how_many_crossings_it_still_suppresses(
        self, imports: list[tuple[str, int, str]], stated: str
    ) -> None:
        rule = _rule(exempt=(ImportExemption(to_glob="app/store/*", until=LONG_PAST),))

        (expired,) = _evaluate(rule, imports)

        assert expired.message.endswith(stated)

    def test_each_exemption_counts_only_the_crossings_it_excused(self) -> None:
        rule = _rule(
            exempt=(
                ImportExemption(to_glob="app/store/rows", until=LONG_PAST),
                ImportExemption(to_glob="app/store/cache", until=LONG_PAST),
            )
        )

        findings = _evaluate(rule)

        assert [f.message.rsplit(" and is still ", 1)[1] for f in findings] == [
            "suppressing 1 crossing",
            "suppressing 1 crossing",
        ]

    def test_a_live_exemption_is_not_reported(self) -> None:
        rule = _rule(exempt=(ImportExemption(to_glob="app/store/*", until="2999-12-31"),))

        findings = _evaluate(rule)

        assert findings == []


class TestACrossing:
    def test_its_finding_carries_the_description_of_its_rule(self) -> None:
        crossing = _evaluate(_rule())[0]

        assert crossing.rule_description == "the UI never reads the store directly"


class TestAGlobThatMatchesNothing:
    def test_a_dead_to_glob_is_the_only_side_named(self) -> None:
        (dead,) = _evaluate(_rule(to_glob="app.nowhere.*"))

        assert dead.severity == "warn"
        assert "`to` glob 'app.nowhere.*'" in dead.message
        assert "`from` glob" not in dead.message

    def test_a_to_glob_that_can_match_is_live_with_nothing_to_ban(self) -> None:
        """BDL-083 D2: matchable and unmatched is a live rule, at info — never dead."""
        (live,) = _evaluate(_rule(to_glob="app/nowhere/*"))

        assert (live.rule_type, live.severity) == ("nothing_to_ban", "info")
        assert "`to` glob 'app/nowhere/*' matches 0 of 3 indexed import paths" in live.message

    def test_a_to_glob_naming_a_source_root_looks_dead_and_says_it_is_an_inference(
        self,
    ) -> None:
        """S1R second pass Minor 2 (``beadloom-ba9w.18``): the headline makes the reason's claim.

        The source root is inferred from the index, and the reason says an importable
        package of that name would still fire the rule. A headline of "cannot fire" and a
        lead-in of "can match none" asserted what the reason hedges. The level stays
        ``warn``: the inference holds on every multi-module project it was measured on,
        where the glob is a file path written for a module and the rule checks nothing.
        """
        (dead,) = evaluate_one_import_rule(
            _rule(to_glob="src/app/store/*"),
            IMPORTS[2:],
            file_count=1,
            target_count=1,
            roots=frozenset({"src"}),
        )

        assert dead.severity == "warn"
        assert dead.message.startswith("Rule 'ui-reads-no-store' looks unable to fire: ")
        assert "and looks unmatchable: it begins with 'src'" in dead.message
        assert "cannot fire" not in dead.message
        assert "can match none" not in dead.message

    def test_a_dead_from_glob_keeps_the_certain_headline_beside_an_inferred_to_glob(
        self,
    ) -> None:
        (dead,) = evaluate_one_import_rule(
            _rule(from_glob="src/app/cli/*", to_glob="src/app/store/*"),
            IMPORTS,
            file_count=2,
            target_count=3,
            roots=frozenset({"src"}),
        )

        assert dead.message.startswith("Rule 'ui-reads-no-store' cannot fire: ")
        assert "and looks unmatchable: it begins with 'src'" in dead.message

    def test_a_dotted_to_glob_can_match_none_and_cannot_fire(self) -> None:
        (dead,) = _evaluate(_rule(to_glob="app.store.*"))

        assert dead.message.startswith("Rule 'ui-reads-no-store' cannot fire: ")
        assert "and can match none: it holds a '.'" in dead.message

    def test_a_dead_from_glob_is_the_only_side_named(self) -> None:
        (dead,) = _evaluate(_rule(from_glob="src/app/cli/*"))

        assert "`from` glob 'src/app/cli/*'" in dead.message
        assert "`to` glob" not in dead.message

    def test_the_finding_quotes_both_population_sizes_it_was_handed(self) -> None:
        (dead,) = _evaluate(_rule(from_glob="src/app/cli/*", to_glob="app/nowhere/*"))

        assert "matches 0 of 2 indexed source files" in dead.message
        assert "matches 0 of 3 indexed import paths" in dead.message
