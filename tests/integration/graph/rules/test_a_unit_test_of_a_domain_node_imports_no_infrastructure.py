"""`test_import_boundary` — `forbid_import`'s evaluator, run over the imports of TEST files.

BDL-074 C3. A unit test of a node in the domain layer that imports the
infrastructure layer is testing through the database, which is what an
integration test does. The rule reads the test imports C1 records (never
`code_imports`, which holds no test file), narrows them to the files bound to a
node the `of` matcher selects — that node or one of its containers — and hands
them to the same evaluator `forbid_import` uses, so a crossing, an exemption and a
dead glob mean here exactly what they mean there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SUITE_POPULATION_RULE_TYPE,
    TEST_IMPORT_BOUNDARY_RULE_TYPE,
    ImportExemption,
    NodeMatcher,
    TestImportBoundaryRule,
    evaluate_all,
    evaluate_test_import_boundary_rules,
    inert_rule_names,
    load_rules,
)
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode, write_rules

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Violation

INFRA_DB = "vaultpkg.infrastructure.db"


def _rule(**kwargs: object) -> TestImportBoundaryRule:
    defaults: dict[str, object] = {
        "name": "domain-unit-tests-no-infra",
        "description": "a unit test of a domain node does not import infrastructure",
        "from_glob": "tests/unit/**",
        "to_glob": "vaultpkg/infrastructure/**",
        "of_matcher": NodeMatcher(tag="layer-domain"),
    }
    defaults.update(kwargs)
    return TestImportBoundaryRule(**defaults)  # type: ignore[arg-type]  # kwargs typed by the test


def _index() -> SuiteIndex:
    return SuiteIndex(
        nodes=[
            SuiteNode("ledger", kind="domain", tags=("layer-domain",)),
            SuiteNode("billing", part_of=("ledger",)),
            SuiteNode("infrastructure", kind="domain", tags=("layer-infra",)),
            SuiteNode("store", kind="component", part_of=("infrastructure",)),
        ],
        files=[
            SuiteFile(
                "tests/unit/ledger/test_billing.py",
                ref_id="billing",
                imports=("pytest", "vaultpkg.ledger.billing", INFRA_DB),
            ),
            SuiteFile(
                "tests/unit/infrastructure/test_store.py",
                ref_id="store",
                imports=(INFRA_DB,),
            ),
            SuiteFile(
                "tests/integration/ledger/test_billing.py",
                ref_id="billing",
                kind="integration",
                imports=(INFRA_DB,),
            ),
            SuiteFile("tests/unit/vault/test_loose.py", placement="unowned", imports=(INFRA_DB,)),
        ],
    )


def _evaluate(
    tmp_path: Path, rule: TestImportBoundaryRule, index: SuiteIndex | None = None
) -> list[Violation]:
    conn = (index or _index()).build(tmp_path)
    try:
        return evaluate_test_import_boundary_rules(conn, [rule])
    finally:
        conn.close()


def _of_type(violations: list[Violation], rule_type: str) -> list[Violation]:
    return [v for v in violations if v.rule_type == rule_type]


class TestTheCrossing:
    def test_a_unit_test_of_a_domain_node_importing_infrastructure_is_reported(
        self, tmp_path: Path
    ) -> None:
        violations = _evaluate(tmp_path, _rule())

        (crossing,) = _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE)
        assert crossing.file_path == "tests/unit/ledger/test_billing.py"
        assert crossing.line_number == 3
        assert INFRA_DB in crossing.message
        assert crossing.severity == "error"

    def test_a_unit_test_of_the_infrastructure_itself_is_not_judged(self, tmp_path: Path) -> None:
        """`of` selects the node or a container of it; `store` is in neither."""
        violations = _evaluate(tmp_path, _rule())

        paths = {v.file_path for v in _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE)}
        assert "tests/unit/infrastructure/test_store.py" not in paths

    def test_without_of_every_file_the_glob_names_is_judged(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule(of_matcher=None))

        paths = sorted(
            v.file_path or "" for v in _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE)
        )
        assert paths == [
            "tests/unit/infrastructure/test_store.py",
            "tests/unit/ledger/test_billing.py",
            "tests/unit/vault/test_loose.py",
        ]

    def test_the_code_import_index_is_not_read(self, tmp_path: Path) -> None:
        """The same crossing in a SOURCE file belongs to `forbid_import`, not here."""
        index = _index()
        conn = index.build(tmp_path)
        try:
            conn.execute(
                "INSERT INTO code_imports (file_path, line_number, import_path, file_hash) "
                "VALUES ('tests/unit/ledger/test_other.py', 1, ?, '')",
                (INFRA_DB,),
            )
            conn.commit()
            violations = evaluate_test_import_boundary_rules(conn, [_rule()])
        finally:
            conn.close()

        paths = {v.file_path for v in _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE)}
        assert paths == {"tests/unit/ledger/test_billing.py"}

    def test_an_exemption_excuses_the_crossing_and_a_dead_one_is_reported(
        self, tmp_path: Path
    ) -> None:
        rule = _rule(
            exempt=(
                ImportExemption(
                    from_glob="tests/unit/ledger/test_billing.py",
                    to_glob="vaultpkg/infrastructure/db",
                    reason="opens an index",
                    until="moved to integration",
                ),
                ImportExemption(
                    from_glob="tests/unit/ledger/test_gone.py",
                    reason="r",
                    until="u",
                ),
            )
        )

        violations = _evaluate(tmp_path, rule)

        assert _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE) == []
        (dead,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert "tests/unit/ledger/test_gone.py" in dead.message
        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert "1 crossing(s) excused by an exemption" in population.message


class TestPopulationAndLiveness:
    def test_the_population_states_what_was_judged_and_what_was_not(self, tmp_path: Path) -> None:
        violations = _evaluate(tmp_path, _rule())

        (population,) = _of_type(violations, SUITE_POPULATION_RULE_TYPE)
        assert "judged 1 of 4 test file(s) with recorded imports" in population.message
        assert "1 bound to a node outside" in population.message
        assert "1 bound to no node" in population.message
        assert "1 outside the `from` glob" in population.message
        assert "aliased" in population.message

    @pytest.mark.parametrize(
        ("changes", "phrase"),
        [
            ({"from_glob": "tests/nowhere/**"}, "`from` glob"),
            ({"to_glob": "elsewhere/**"}, "`to` glob"),
            ({"of_matcher": NodeMatcher(tag="layer-ghost")}, "`of` matcher"),
        ],
    )
    def test_a_rule_that_can_judge_nothing_says_why_and_is_counted_inert(
        self, tmp_path: Path, changes: dict[str, object], phrase: str
    ) -> None:
        rule = _rule(**changes)
        conn = _index().build(tmp_path)
        try:
            violations = evaluate_all(conn, [rule], project_root=tmp_path)
            inert = inert_rule_names(conn, [rule], project_root=tmp_path)
        finally:
            conn.close()

        (liveness,) = _of_type(violations, LIVENESS_RULE_TYPE)
        assert phrase in liveness.message
        assert "test file" in liveness.message
        assert inert == {rule.name}

    def test_a_live_rule_is_not_counted_inert(self, tmp_path: Path) -> None:
        conn = _index().build(tmp_path)
        try:
            inert = inert_rule_names(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        assert inert == set()

    def test_the_remediation_names_the_import(self, tmp_path: Path) -> None:
        conn = _index().build(tmp_path)
        try:
            violations = evaluate_all(conn, [_rule()], project_root=tmp_path)
        finally:
            conn.close()

        (crossing,) = _of_type(violations, TEST_IMPORT_BOUNDARY_RULE_TYPE)
        assert crossing.remediation is not None
        assert "tests/unit/ledger/test_billing.py" in crossing.remediation


class TestTheRuleIsDeclaredInRulesYml:
    def test_the_block_parses_with_of_and_exemptions(self, tmp_path: Path) -> None:
        path = write_rules(
            tmp_path,
            "  - name: tib\n"
            "    test_import_boundary:\n"
            "      from: 'tests/unit/**'\n"
            "      to: 'vaultpkg/infrastructure/**'\n"
            "      of: { tag: layer-domain }\n"
            "      exempt:\n"
            "        - from: tests/unit/ledger/test_billing.py\n"
            "          reason: opens an index\n"
            "          until: moved to integration\n",
        )

        (rule,) = load_rules(path)

        assert isinstance(rule, TestImportBoundaryRule)
        assert rule.of_matcher == NodeMatcher(tag="layer-domain")
        assert rule.exempt[0].from_glob == "tests/unit/ledger/test_billing.py"
        assert rule.severity == "error"

    def test_an_exemption_without_a_reason_is_refused(self, tmp_path: Path) -> None:
        path = write_rules(
            tmp_path,
            "  - name: tib\n"
            "    test_import_boundary:\n"
            "      from: 'tests/unit/**'\n"
            "      to: 'x/**'\n"
            "      exempt: [{ from: a, until: b }]\n",
        )

        with pytest.raises(ValueError, match="reason"):
            load_rules(path)


def test_the_rule_survives_being_written_to_the_index() -> None:
    from beadloom.application.reindex.rules_loader import _serialize_rule

    rule_type, payload = _serialize_rule(_rule())

    assert rule_type == "test_import_boundary"
    assert payload == {
        "from_glob": "tests/unit/**",
        "to_glob": "vaultpkg/infrastructure/**",
        "of": {"tag": "layer-domain"},
    }
