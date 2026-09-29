"""`test_binding` — a test file bound to no node, and a node with no bound test file.

BDL-074 C3. The binding C1 records (a test file's node, from the mirror of its
path or a node's `tests:` list) is judged here in both directions. Every leg is
proved to report, the exemptions are proved to excuse only what they name and to
report themselves once they excuse nothing, and every run states its population:
how many files and nodes it judged, and how many it could not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SUITE_POPULATION_RULE_TYPE,
    TEST_BINDING_RULE_TYPE,
    ListedExemption,
    NodeMatcher,
    TestBindingRule,
    evaluate_all,
    evaluate_test_binding_rules,
    inert_rule_names,
    is_advisory,
    load_rules,
)
from beadloom.graph.rules.liveness import inert_rules
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode, write_rules

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Violation


def _rule(**kwargs: object) -> TestBindingRule:
    defaults: dict[str, object] = {
        "name": "test-binding",
        "description": "a test file binds to a node",
        "files": "tests/**",
    }
    defaults.update(kwargs)
    return TestBindingRule(**defaults)  # type: ignore[arg-type]  # kwargs typed by the test


def _index() -> SuiteIndex:
    return SuiteIndex(
        nodes=[
            SuiteNode("ledger", kind="domain"),
            SuiteNode("billing", part_of=("ledger",)),
            SuiteNode("invoicing", part_of=("ledger",)),
            SuiteNode("tax-table", kind="component", part_of=("invoicing",)),
        ],
        files=[
            SuiteFile("tests/unit/ledger/test_billing.py", ref_id="billing"),
            SuiteFile("tests/unit/ledger/invoicing/test_tax_table.py", ref_id="tax-table"),
            SuiteFile("tests/test_loose.py", placement="unplaced", kind=None),
            SuiteFile("tests/unit/vault/test_vault.py", placement="unowned"),
            SuiteFile(
                "tests/acceptance/steps/test_billing_steps.py",
                placement="other_kind",
                kind="acceptance",
            ),
        ],
    )


def _evaluate(
    tmp_path: Path, rule: TestBindingRule, index: SuiteIndex | None = None
) -> list[Violation]:
    conn = (index or _index()).build(tmp_path)
    try:
        return evaluate_test_binding_rules(conn, [rule])
    finally:
        conn.close()


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


def _population(violations: list[Violation]) -> str:
    return "\n".join(v.message for v in _of_type(violations, SUITE_POPULATION_RULE_TYPE))


class TestATestFileBoundToNoNode:
    def test_an_unplaced_and_an_unowned_file_are_each_reported_by_path(
        self, tmp_path: Path
    ) -> None:
        # Act
        violations = _evaluate(tmp_path, _rule())

        # Assert
        reported = sorted(v.file_path or "" for v in _of_type(violations, TEST_BINDING_RULE_TYPE))
        assert reported == ["tests/test_loose.py", "tests/unit/vault/test_vault.py"]

    def test_the_finding_names_the_placement_that_left_it_unbound(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule())

        messages = {v.file_path: v.message for v in _of_type(violations, TEST_BINDING_RULE_TYPE)}
        assert "unplaced" in messages["tests/test_loose.py"]
        assert "unowned" in messages["tests/unit/vault/test_vault.py"]

    def test_an_acceptance_step_file_is_outside_the_judged_population(
        self, tmp_path: Path
    ) -> None:
        """An acceptance step file binds through its scenarios' tags, not its path."""
        violations = _evaluate(tmp_path, _rule())

        paths = {v.file_path for v in violations}
        assert "tests/acceptance/steps/test_billing_steps.py" not in paths
        assert "4 of 5 indexed test file(s)" in _population(violations)
        assert "1 acceptance step file(s)" in _population(violations)

    def test_the_files_glob_narrows_the_population(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(files="tests/unit/**"))

        reported = [v.file_path for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == ["tests/unit/vault/test_vault.py"]

    def test_the_finding_carries_the_rule_severity(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(severity="error"))

        assert {v.severity for v in _of_type(violations, TEST_BINDING_RULE_TYPE)} == {"error"}


def _suite_of_every_kind(*extra: SuiteFile) -> SuiteIndex:
    """One file of each placement, two acceptance step files and three self-checks."""
    return SuiteIndex(
        nodes=[SuiteNode("ledger", kind="domain"), SuiteNode("billing", part_of=("ledger",))],
        files=[
            SuiteFile("tests/unit/ledger/test_billing.py", ref_id="billing"),
            SuiteFile("tests/test_loose.py", placement="unplaced", kind=None),
            *(
                SuiteFile(
                    f"tests/acceptance/steps/test_{name}_steps.py",
                    placement="other_kind",
                    kind="acceptance",
                )
                for name in ("billing", "refunds")
            ),
            *(
                SuiteFile(
                    f"tests/self_check/docs/test_{name}.py",
                    placement="other_kind",
                    kind="self_check",
                )
                for name in ("readme", "spec", "changelog")
            ),
            *extra,
        ],
    )


class TestThePopulationNamesEveryKindItDoesNotJudge:
    """BDL-074 F1: no file is filed under a phrase that is true of only some of them.

    The rule once said "174 bind by other means" of 73 acceptance step files and
    101 self-checks. The first bind through their scenarios' tags; the second bind
    to nothing, by design. One phrase over both was true of neither.
    """

    def test_acceptance_and_self_check_are_each_counted_by_their_kind(
        self, tmp_path: Path
    ) -> None:
        # Act
        population = _population(_evaluate(tmp_path, _rule(), _suite_of_every_kind()))

        # Assert
        assert "judged 2 of 7 indexed test file(s)" in population
        assert "2 acceptance step file(s)" in population
        assert "3 self-check file(s)" in population
        assert "by other means" not in population

    def test_a_self_check_is_stated_as_bound_to_no_node_by_design(self, tmp_path: Path) -> None:
        population = _population(_evaluate(tmp_path, _rule(), _suite_of_every_kind()))

        assert (
            "3 self-check file(s) — the project's checks of its own files and "
            "configuration, bound to no node by design: a sanctioned outcome, not a gap"
        ) in population

    def test_acceptance_names_the_scenario_rule_that_judges_its_tags(self, tmp_path: Path) -> None:
        conn = _suite_of_every_kind().build(tmp_path)
        try:
            violations = evaluate_test_binding_rules(
                conn, [_rule()], scenario_rules=("scenarios-in-their-folder",)
            )
        finally:
            conn.close()

        assert (
            "2 acceptance step file(s) — the scenarios they run bind through their "
            "@node: tags, judged by `scenarios-in-their-folder`"
        ) in _population(violations)

    def test_acceptance_says_so_when_no_scenario_rule_judges_its_tags(
        self, tmp_path: Path
    ) -> None:
        population = _population(_evaluate(tmp_path, _rule(), _suite_of_every_kind()))

        assert "judged by no `scenario_binding` rule of this project" in population

    def test_the_scenario_rule_is_named_when_both_are_declared_together(
        self, tmp_path: Path
    ) -> None:
        """The name reaches the line through the one dispatch lint runs, not by hand."""
        rules = load_rules(
            write_rules(
                tmp_path,
                "  - name: tb\n"
                "    test_binding: { files: 'tests/**' }\n"
                "  - name: scenarios-in-their-folder\n"
                "    scenario_binding: { features: 'tests/acceptance/**/*.feature' }\n",
            )
        )
        conn = _suite_of_every_kind().build(tmp_path)
        try:
            violations = evaluate_all(conn, rules, project_root=tmp_path)
        finally:
            conn.close()

        stated = [
            v.message
            for v in _of_type(violations, SUITE_POPULATION_RULE_TYPE)
            if v.rule_name == "tb"
        ]
        assert len(stated) == 1
        assert "judged by `scenarios-in-their-folder`" in stated[0]

    def test_the_kind_is_the_one_the_index_recorded_not_the_folder(self, tmp_path: Path) -> None:
        """A file's kind is read from the index, so no folder name is assumed here."""
        index = _suite_of_every_kind(
            SuiteFile(
                "tests/self_check/docs/test_recorded_as_acceptance.py",
                placement="other_kind",
                kind="acceptance",
            )
        )

        population = _population(_evaluate(tmp_path, _rule(), index))

        assert "3 acceptance step file(s)" in population
        assert "3 self-check file(s)" in population

    def test_a_kind_the_rule_has_no_statement_for_is_still_named(self, tmp_path: Path) -> None:
        index = _suite_of_every_kind(
            SuiteFile("tests/smoke/test_boot.py", placement="other_kind", kind="smoke")
        )

        population = _population(_evaluate(tmp_path, _rule(), index))

        assert "1 smoke file(s) — bound to no node, and not judged by this rule" in population

    def test_a_kind_the_suite_does_not_hold_is_not_mentioned(self, tmp_path: Path) -> None:
        population = _population(_evaluate(tmp_path, _rule()))

        assert "self-check" not in population

    def test_the_excuses_are_counted_by_the_exemptions_that_made_them(
        self, tmp_path: Path
    ) -> None:
        index = _suite_of_every_kind(
            SuiteFile("tests/test_other_loose.py", placement="unplaced", kind=None)
        )
        rule = _rule(
            exempt_files=(
                ListedExemption(entries=("tests/test_loose.py",), reason="mixed", until="split"),
                ListedExemption(
                    entries=("tests/test_other_loose.py",), reason="written late", until="placed"
                ),
            )
        )

        population = _population(_evaluate(tmp_path, rule, index))

        assert "2 bound to none — 2 excused by 2 exemption(s), 0 reported" in population


class TestANodeWithNoBoundTestFile:
    def test_a_node_of_the_configured_kind_with_no_bound_file_is_reported(
        self, tmp_path: Path
    ) -> None:
        violations = _evaluate(
            tmp_path, _rule(files=None, for_matcher=NodeMatcher(kind="feature"))
        )

        reported = [v.from_ref_id for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == []  # billing is bound; invoicing is covered through tax-table

    def test_a_file_bound_to_a_part_counts_for_its_container(self, tmp_path: Path) -> None:
        index = _index()
        index.files = [f for f in index.files if f.ref_id != "billing"]

        violations = _evaluate(
            tmp_path, _rule(files=None, for_matcher=NodeMatcher(kind="feature")), index
        )

        reported = [v.from_ref_id for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == ["billing"]

    def test_the_finding_says_an_unbound_file_may_test_the_node(self, tmp_path: Path) -> None:
        """While a file binds to no node, 'no bound test' is not 'untested'."""
        index = _index()
        index.files = [f for f in index.files if f.ref_id != "billing"]

        violations = _evaluate(
            tmp_path, _rule(files=None, for_matcher=NodeMatcher(kind="feature")), index
        )

        (finding,) = _of_type(violations, TEST_BINDING_RULE_TYPE)
        assert "2 test file(s) bind to no node" in finding.message

    def test_the_node_population_is_stated(self, tmp_path: Path) -> None:
        index = _index()
        index.files = [f for f in index.files if f.ref_id != "billing"]

        violations = _evaluate(
            tmp_path, _rule(files=None, for_matcher=NodeMatcher(kind="feature")), index
        )

        population = _population(violations)
        assert "2 node(s) (kind=feature)" in population
        assert "1 with a bound test file, 1 without" in population


class TestExemptions:
    def test_an_exempt_file_is_not_reported_and_is_counted(self, tmp_path: Path) -> None:
        rule = _rule(
            exempt_files=(
                ListedExemption(entries=("tests/test_loose.py",), reason="mixed", until="split"),
            )
        )

        violations = _evaluate(tmp_path, rule)

        reported = [v.file_path for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == ["tests/unit/vault/test_vault.py"]
        assert "1 excused by 1 exemption(s)" in _population(violations)

    def test_an_exempt_node_is_not_reported(self, tmp_path: Path) -> None:
        index = _index()
        index.files = [f for f in index.files if f.ref_id != "billing"]
        rule = _rule(
            files=None,
            for_matcher=NodeMatcher(kind="feature"),
            exempt_nodes=(ListedExemption(entries=("billing",), reason="r", until="u"),),
        )

        violations = _evaluate(tmp_path, rule, index)

        assert _of_type(violations, TEST_BINDING_RULE_TYPE) == []

    def test_an_entry_that_excuses_nothing_is_reported_by_name(self, tmp_path: Path) -> None:
        """A path that moved to its node's folder is the exit condition firing."""
        rule = _rule(
            exempt_files=(
                ListedExemption(
                    entries=("tests/test_loose.py", "tests/test_moved_away.py"),
                    reason="mixed",
                    until="split",
                ),
            )
        )

        violations = _evaluate(tmp_path, rule)

        dead = _of_type(violations, LIVENESS_RULE_TYPE)
        assert len(dead) == 1
        assert "tests/test_moved_away.py" in dead[0].message
        assert dead[0].severity == "warn"

    def test_an_expired_entry_still_excusing_is_reported(self, tmp_path: Path) -> None:
        rule = _rule(
            exempt_files=(
                ListedExemption(
                    entries=("tests/test_loose.py",), reason="mixed", until="1999-01-01"
                ),
            )
        )

        violations = _evaluate(tmp_path, rule)

        (expired,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert "expired on 1999-01-01" in expired.message
        assert "1 test file" in expired.message


class TestPopulationAndLiveness:
    def test_the_population_is_advisory_and_always_stated(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule())

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert population.severity == "warn"
        assert is_advisory(population)

    def test_a_for_matcher_selecting_nothing_is_reported_and_counted_inert(
        self, tmp_path: Path
    ) -> None:
        rule = _rule(files=None, for_matcher=NodeMatcher(kind="adr"))
        conn = _index().build(tmp_path)
        try:
            violations = evaluate_all(conn, [rule], project_root=tmp_path)
            inert = inert_rule_names(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()

        liveness = _of_type(violations, LIVENESS_RULE_TYPE)
        assert len(liveness) == 1
        assert "selects no node" in liveness[0].message
        assert inert == {"test-binding"}

    def test_an_index_with_no_test_file_stands_the_file_leg_down(self, tmp_path: Path) -> None:
        index = SuiteIndex(nodes=[SuiteNode("ledger", kind="domain")])
        conn = index.build(tmp_path)
        try:
            violations = evaluate_all(conn, [_rule()], project_root=tmp_path)
            inert = inert_rule_names(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        (liveness,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert "no indexed test file" in liveness.message
        assert inert == {"test-binding"}

    def test_a_live_rule_is_not_counted_inert(self, tmp_path: Path) -> None:
        conn = _index().build(tmp_path)
        try:
            inert = inert_rule_names(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert inert == set()


class TestTheRuleIsDeclaredInRulesYml:
    def test_both_legs_and_both_exemption_kinds_parse(self, tmp_path: Path) -> None:
        path = write_rules(
            tmp_path,
            "  - name: tb\n"
            "    test_binding:\n"
            "      for: { kind: feature }\n"
            "      files: 'tests/**'\n"
            "      exempt:\n"
            "        - files: ['tests/test_a.py', 'tests/test_b.py']\n"
            "          reason: mixed\n"
            "          until: split by node\n"
            "        - nodes: [billing]\n"
            "          reason: no code of its own\n"
            "          until: it gains code\n",
        )

        (rule,) = load_rules(path)

        assert isinstance(rule, TestBindingRule)
        assert rule.for_matcher == NodeMatcher(kind="feature")
        assert rule.files == "tests/**"
        assert rule.exempt_files[0].entries == ("tests/test_a.py", "tests/test_b.py")
        assert rule.exempt_nodes[0].entries == ("billing",)
        assert rule.severity == "warn"

    @pytest.mark.parametrize(
        ("block", "complaint"),
        [
            ("{}", "names neither"),
            ("{ files: 'tests/**', exempt: [{ files: [a], until: x }] }", "reason"),
            ("{ files: 'tests/**', exempt: [{ files: [a], reason: x }] }", "until"),
            ("{ files: 'tests/**', exempt: [{ reason: x, until: y }] }", "exactly one"),
            (
                "{ files: 'tests/**', exempt: [{ files: [a], nodes: [b], reason: x, until: y }] }",
                "exactly one",
            ),
            ("{ files: 'tests/**', exempt: [{ nodes: [b], reason: x, until: y }] }", "for"),
        ],
    )
    def test_a_rule_that_cannot_mean_anything_is_refused(
        self, tmp_path: Path, block: str, complaint: str
    ) -> None:
        path = write_rules(tmp_path, f"  - name: tb\n    test_binding: {block}\n")

        with pytest.raises(ValueError, match=complaint):
            load_rules(path)


def test_the_rule_survives_being_written_to_the_index() -> None:
    from beadloom.application.reindex.rules_loader import _serialize_rule

    rule = _rule(
        for_matcher=NodeMatcher(kind="feature"),
        exempt_files=(ListedExemption(entries=("tests/test_a.py",), reason="r", until="u"),),
    )

    rule_type, payload = _serialize_rule(rule)

    assert rule_type == "test_binding"
    assert payload["files"] == "tests/**"
    assert payload["for"] == {"kind": "feature"}
    assert payload["exempt"] == [{"files": ["tests/test_a.py"], "reason": "r", "until": "u"}]


_FILE_REMEDIATION = (
    "place it where its path mirrors the code it tests, or name it in the "
    "`tests:` list of the node it belongs to; a file that cannot be placed yet "
    "is exempted by path, with a reason and an exit condition"
)
_NO_TABLE_REMEDIATION = (
    "reindex so the test files are recorded, or point `files:` / `for:` at "
    "what the project has — a leg that judges nothing reads exactly like one "
    "that found nothing wrong"
)


def _node_rule(**kwargs: object) -> TestBindingRule:
    """A rule with only the node leg, over the `feature` nodes of the fixture."""
    return _rule(files=None, for_matcher=NodeMatcher(kind="feature"), **kwargs)


def _index_without_billing_tests() -> SuiteIndex:
    index = _index()
    index.files = [f for f in index.files if f.ref_id != "billing"]
    return index


class TestAFindingCarriesItsRuleAndItsRemedy:
    """A finding is read on its own, away from the rule that made it."""

    def test_a_file_finding_carries_the_description_of_its_rule(self, tmp_path: Path) -> None:
        # Act
        violations = _evaluate(tmp_path, _rule(files="tests/unit/**"))

        # Assert
        (finding,) = _of_type(violations, TEST_BINDING_RULE_TYPE)
        assert finding.rule_description == "a test file binds to a node"

    def test_a_file_finding_says_how_to_place_the_file(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(files="tests/unit/**"))

        (finding,) = _of_type(violations, TEST_BINDING_RULE_TYPE)
        assert finding.remediation == _FILE_REMEDIATION

    def test_a_node_finding_says_how_to_place_a_test_of_that_node(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _node_rule(), _index_without_billing_tests())

        (finding,) = _of_type(violations, TEST_BINDING_RULE_TYPE)
        assert finding.remediation == (
            "place a test of `billing` where its path mirrors the node's code, or name "
            "the file in the node's `tests:` list; a node that is not tested yet is "
            "exempted by name, with a reason and an exit condition"
        )

    def test_the_population_carries_the_description_of_its_rule(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule())

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert population.rule_description == "a test file binds to a node"


class TestAnExemptionIsMatchedTheWayItsLegNamesThings:
    def test_a_file_entry_is_a_glob_over_the_path(self, tmp_path: Path) -> None:
        # Arrange
        rule = _rule(
            files="tests/unit/**",
            exempt_files=(
                ListedExemption(entries=("tests/unit/vault/*",), reason="r", until="u"),
            ),
        )

        # Act
        violations = _evaluate(tmp_path, rule)

        # Assert
        assert _of_type(violations, TEST_BINDING_RULE_TYPE) == []

    def test_a_node_entry_names_one_node_exactly_and_is_no_glob(self, tmp_path: Path) -> None:
        rule = _node_rule(
            exempt_nodes=(ListedExemption(entries=("bill*",), reason="r", until="u"),),
        )

        violations = _evaluate(tmp_path, rule, _index_without_billing_tests())

        reported = [v.from_ref_id for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == ["billing"]

    def test_a_dead_file_entry_carries_the_description_of_its_rule(self, tmp_path: Path) -> None:
        rule = _rule(
            exempt_files=(
                ListedExemption(entries=("tests/test_moved_away.py",), reason="r", until="u"),
            )
        )

        violations = _evaluate(tmp_path, rule)

        (dead,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert dead.rule_description == "a test file binds to a node"

    def test_a_dead_node_entry_names_its_rule_and_what_it_excuses(self, tmp_path: Path) -> None:
        rule = _node_rule(
            exempt_nodes=(ListedExemption(entries=("vault",), reason="r", until="u"),),
        )

        violations = _evaluate(tmp_path, rule)

        (dead,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert (dead.rule_name, dead.rule_description) == (
            "test-binding",
            "a test file binds to a node",
        )
        assert dead.message.startswith(
            "Rule 'test-binding': the exemption entry `vault` excuses no node — "
        )


class TestThePopulationSentenceCountsEachPart:
    def test_a_file_leg_with_no_other_kind_ends_at_its_reported_count(
        self, tmp_path: Path
    ) -> None:
        """Five files, three under `tests/unit/`: two bound, one unbound, nothing else."""
        # Act
        population = _population(_evaluate(tmp_path, _rule(files="tests/unit/**")))

        # Assert
        assert population == (
            "test files: judged 3 of 5 indexed test file(s) matching `tests/unit/**` "
            "(2 outside the glob): 2 bound to a node, 1 bound to none — "
            "0 excused by 0 exemption(s), 1 reported"
        )

    def test_the_bound_count_is_the_judged_files_less_the_unbound(self, tmp_path: Path) -> None:
        population = _population(_evaluate(tmp_path, _rule()))

        assert "judged 4 of 5" in population
        assert ": 2 bound to a node, 2 bound to none — " in population

    def test_an_excused_node_is_taken_off_the_reported_count(self, tmp_path: Path) -> None:
        rule = _node_rule(
            exempt_nodes=(ListedExemption(entries=("billing",), reason="r", until="u"),),
        )

        population = _population(_evaluate(tmp_path, rule, _index_without_billing_tests()))

        assert "1 without — 1 excused by an exemption, 0 reported;" in population

    def test_two_legs_are_stated_in_one_line_separated_by_a_semicolon(
        self, tmp_path: Path
    ) -> None:
        rule = _rule(files="tests/unit/**", for_matcher=NodeMatcher(kind="feature"))

        population = _population(_evaluate(tmp_path, rule))

        assert "1 reported; nodes: judged 2 node(s) (kind=feature)" in population

    def test_every_scenario_rule_is_named_separated_by_a_comma(self, tmp_path: Path) -> None:
        conn = _suite_of_every_kind().build(tmp_path)
        try:
            violations = evaluate_test_binding_rules(
                conn, [_rule()], scenario_rules=("in-their-folder", "tagged-by-node")
            )
        finally:
            conn.close()

        assert "judged by `in-their-folder`, `tagged-by-node`, recognised" in _population(
            violations
        )

    def test_no_scenario_rule_is_stated_between_the_tags_and_the_recognition(
        self, tmp_path: Path
    ) -> None:
        population = _population(_evaluate(tmp_path, _rule(), _suite_of_every_kind()))

        assert (
            "@node: tags, judged by no `scenario_binding` rule of this project, recognised"
        ) in population

    def test_two_kinds_are_separated_by_a_semicolon(self, tmp_path: Path) -> None:
        population = _population(_evaluate(tmp_path, _rule(), _suite_of_every_kind()))

        assert "reindex to record it); 3 self-check file(s) — " in population

    def test_a_node_selected_by_its_ref_id_is_judged(self, tmp_path: Path) -> None:
        """The matcher is asked about each node under that node's own id."""
        rule = _rule(files=None, for_matcher=NodeMatcher(ref_id="invoicing"))

        population = _population(_evaluate(tmp_path, rule))

        assert "nodes: judged 1 node(s) (ref_id=invoicing): 1 with a bound test file" in (
            population
        )


class TestARuleThatCannotJudgeSaysWhy:
    def test_both_dead_legs_are_named_in_one_reason(self, tmp_path: Path) -> None:
        # Arrange
        rule = _rule(files="nowhere/**", for_matcher=NodeMatcher(kind="adr"))
        conn = _index().build(tmp_path)

        # Act
        try:
            inert = inert_rules(conn, [rule])
        finally:
            conn.close()

        # Assert
        assert [reason for _rule, reason in inert] == [
            (
                "its `files` glob `nowhere/**` matches no indexed test file it judges; "
                "its `for` matcher (kind=adr) selects no node"
            )
        ]

    def test_an_index_without_the_test_table_is_one_finding_saying_reindex(
        self, tmp_path: Path
    ) -> None:
        conn = _index().build(tmp_path)
        conn.execute("DROP TABLE test_files")
        try:
            violations = evaluate_test_binding_rules(conn, [_rule()])
        finally:
            conn.close()

        (finding,) = violations
        assert (finding.rule_type, finding.rule_name, finding.message) == (
            LIVENESS_RULE_TYPE,
            "test-binding",
            "Rule 'test-binding' cannot judge a leg: the index holds no test-file table — "
            "it was written before test files were indexed, so no binding was judged",
        )

    def test_the_finding_for_a_missing_table_carries_the_rule_and_the_remedy(
        self, tmp_path: Path
    ) -> None:
        conn = _index().build(tmp_path)
        conn.execute("DROP TABLE test_files")
        try:
            (finding,) = evaluate_test_binding_rules(conn, [_rule()])
        finally:
            conn.close()

        assert (finding.rule_description, finding.remediation) == (
            "a test file binds to a node",
            _NO_TABLE_REMEDIATION,
        )
