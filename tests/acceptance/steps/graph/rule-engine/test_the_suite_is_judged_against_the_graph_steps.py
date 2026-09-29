"""Step implementations for `graph/rule-engine/the_suite_is_judged_against_the_graph.feature`.

BDL-074 C3. The steps run the real rules against real indexes written into a
temporary directory; the rows a reindex would record (a test file's placement, a
test file's imports) are written directly, so each scenario states exactly the
suite it is about. Every node name is invented, so a rule that recognised this
repository's own graph would fail here.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.graph.rules import (
    LIVENESS_RULE_TYPE,
    SCENARIO_BINDING_RULE_TYPE,
    SUITE_POPULATION_RULE_TYPE,
    TEST_BINDING_RULE_TYPE,
    TEST_IMPORT_BOUNDARY_RULE_TYPE,
    ListedExemption,
    NodeMatcher,
    ScenarioBindingRule,
    TestBindingRule,
    TestImportBoundaryRule,
    evaluate_all,
)
from tests.support.suite_index import SuiteFile, SuiteIndex, SuiteNode, write_feature

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules import Rule, Violation

scenarios("../../../graph/rule-engine/the_suite_is_judged_against_the_graph.feature")

LOOSE_FILE = "tests/test_orders_loose.py"
GONE_FILE = "tests/test_orders_gone.py"
UNIT_TEST = "tests/unit/orders/test_checkout.py"
FEATURE_FILE = "acceptance/orders/checkout/checkout.feature"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {"index": SuiteIndex(), "exempt": ()}


def _run(world: dict[str, Any], tmp_path: Path, rule: Rule) -> None:
    conn = world["index"].build(tmp_path)
    try:
        world["violations"] = evaluate_all(conn, [rule], project_root=tmp_path)
    finally:
        conn.close()


def _of_type(world: dict[str, Any], rule_type: str) -> list[Violation]:
    return [v for v in world["violations"] if v.rule_type == rule_type]


@given("a graph with a feature node and a test file placed where its path mirrors no code")
def _loose_file(world: dict[str, Any]) -> None:
    world["index"].nodes.append(SuiteNode("checkout"))
    world["index"].files.append(SuiteFile(LOOSE_FILE, placement="unplaced", kind=None))


@given("the test-binding rule exempts that file and a file that no longer exists")
def _exempt_loose_and_gone(world: dict[str, Any]) -> None:
    world["exempt"] = (
        ListedExemption(
            entries=(LOOSE_FILE, GONE_FILE),
            reason="mixed file, not yet split by node",
            until="split by node and placed by the mirror",
        ),
    )


@when("the test-binding rule is evaluated")
def _evaluate_test_binding(world: dict[str, Any], tmp_path: Path) -> None:
    rule = TestBindingRule(
        name="test-binding",
        description="a test file binds to a node",
        files="tests/**",
        exempt_files=world["exempt"],
        severity="error",
    )
    _run(world, tmp_path, rule)


@then("that test file is reported as bound to no node")
def _loose_reported(world: dict[str, Any]) -> None:
    (finding,) = _of_type(world, TEST_BINDING_RULE_TYPE)
    assert finding.file_path == LOOSE_FILE
    assert finding.severity == "error"


@then("no test file is reported as bound to no node")
def _nothing_reported(world: dict[str, Any]) -> None:
    assert _of_type(world, TEST_BINDING_RULE_TYPE) == []


@then("the entry for the file that no longer exists is reported")
def _dead_entry_reported(world: dict[str, Any]) -> None:
    (dead,) = _of_type(world, LIVENESS_RULE_TYPE)
    assert GONE_FILE in dead.message


@then("the rule states how many test files it judged")
def _population_stated(world: dict[str, Any]) -> None:
    (population,) = _of_type(world, SUITE_POPULATION_RULE_TYPE)
    assert "judged 1 of 1" in population.message


@given("a graph with a domain node and an infrastructure node")
def _domain_and_infrastructure(world: dict[str, Any]) -> None:
    world["index"].nodes.extend(
        [
            SuiteNode("orders", kind="domain", tags=("layer-domain",)),
            SuiteNode("checkout", part_of=("orders",)),
            SuiteNode("storage", kind="domain", tags=("layer-infra",)),
        ]
    )


@given("a unit test of the domain node that imports the infrastructure")
def _unit_test_importing_storage(world: dict[str, Any]) -> None:
    world["index"].files.append(
        SuiteFile(
            UNIT_TEST, ref_id="checkout", imports=("shop.orders.checkout", "shop.storage.db")
        )
    )


@when("the test-import-boundary rule is evaluated")
def _evaluate_test_import_boundary(world: dict[str, Any], tmp_path: Path) -> None:
    rule = TestImportBoundaryRule(
        name="domain-unit-tests-no-infra",
        description="a unit test of a domain node does not import infrastructure",
        from_glob="tests/unit/**",
        to_glob="shop/storage/**",
        of_matcher=NodeMatcher(tag="layer-domain"),
    )
    _run(world, tmp_path, rule)


@then("the import is reported at its line in the unit test")
def _import_reported(world: dict[str, Any]) -> None:
    (finding,) = _of_type(world, TEST_IMPORT_BOUNDARY_RULE_TYPE)
    assert finding.file_path == UNIT_TEST
    assert finding.line_number == 2


@given("a graph with two feature nodes of one domain")
def _two_features(world: dict[str, Any]) -> None:
    world["index"].nodes.extend(
        [
            SuiteNode("orders", kind="domain"),
            SuiteNode("checkout", part_of=("orders",)),
            SuiteNode("refunds", part_of=("orders",)),
        ]
    )


@given("a scenario in the folder of the first node tagged with the second")
def _misplaced_scenario(world: dict[str, Any], tmp_path: Path) -> None:
    write_feature(
        tmp_path,
        FEATURE_FILE,
        "@node:refunds\nFeature: F\n\n  Scenario: a refund\n    Given a step\n",
    )


@when("the scenario-binding rule is evaluated")
def _evaluate_scenario_binding(world: dict[str, Any], tmp_path: Path) -> None:
    rule = ScenarioBindingRule(
        name="scenario-binding",
        description="a scenario lives in the folder of its node",
        features="acceptance/**/*.feature",
    )
    _run(world, tmp_path, rule)


@then("the scenario is reported where it is written")
def _scenario_reported(world: dict[str, Any]) -> None:
    (finding,) = _of_type(world, SCENARIO_BINDING_RULE_TYPE)
    assert finding.file_path == FEATURE_FILE
    assert finding.line_number == 4


@then("the rule states that it does not judge what the steps execute")
def _execution_not_judged(world: dict[str, Any]) -> None:
    (population,) = _of_type(world, SUITE_POPULATION_RULE_TYPE)
    assert "execute" in population.message
    assert "not judged" in population.message
