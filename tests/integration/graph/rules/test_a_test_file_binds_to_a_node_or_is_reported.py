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

    def test_a_file_bound_by_other_means_is_outside_the_population(self, tmp_path: Path) -> None:
        """An acceptance step file binds through its scenarios' tags, not its path."""
        violations = _evaluate(tmp_path, _rule())

        paths = {v.file_path for v in violations}
        assert "tests/acceptance/steps/test_billing_steps.py" not in paths
        assert "4 of 5 indexed test file(s)" in _population(violations)
        assert "1 bind by other means" in _population(violations)

    def test_the_files_glob_narrows_the_population(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(files="tests/unit/**"))

        reported = [v.file_path for v in _of_type(violations, TEST_BINDING_RULE_TYPE)]
        assert reported == ["tests/unit/vault/test_vault.py"]

    def test_the_finding_carries_the_rule_severity(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(severity="error"))

        assert {v.severity for v in _of_type(violations, TEST_BINDING_RULE_TYPE)} == {"error"}


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
        assert "1 excused by an exemption" in _population(violations)

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
