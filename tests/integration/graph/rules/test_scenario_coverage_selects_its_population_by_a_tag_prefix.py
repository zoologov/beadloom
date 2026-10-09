"""``scenario_coverage`` selects the nodes it judges by a ``tag_prefix`` matcher.

The rule loads a node's tags only when its matcher reads them, and a matcher
handed no tags skips its tag test. An evaluator that did not know a prefix reads
tags would therefore select EVERY node of the graph and report each one without
a scenario. The cases below put nodes outside the prefix where that defect would
report them, and a prefix that no node carries where it would stay silent.

The project is written to disk and indexed with the real reindex. The tags
(``ui-*``, ``tier-*``) are none of this repository's.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beadloom.graph.linter import lint
from beadloom.graph.rules import LIVENESS_RULE_TYPE, ScenarioCoverageRule, load_rules
from tests.support.tiered_project import write_tiered_project

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult

_RULE_NAME = "ui-slices-have-scenarios"

_NODES = [
    ("shop", "service", []),
    ("board", "component", ["ui-widgets"]),
    ("search", "component", ["ui-features"]),
    ("cart", "component", ["ui-features"]),
    ("ledger", "component", ["tier-core"]),
]

_EDGES = [
    ("board", "shop", "part_of"),
    ("search", "shop", "part_of"),
    ("cart", "shop", "part_of"),
]

#: One scenario, bound to ``board``. ``search`` and ``cart`` carry the prefix
#: and no scenario; ``ledger`` and ``shop`` carry no scenario and no prefix.
_FEATURE = (
    "@bead:shop-1 @node:board\n"
    "Feature: The board\n"
    "  Scenario: The board lists the stock\n"
    "    Given a board\n"
)


def _rule(prefix: str) -> str:
    return (
        f"  - name: {_RULE_NAME}\n"
        '    description: "a UI slice carries an executable scenario"\n'
        "    severity: warn\n"
        "    scenario_coverage:\n"
        f"      for: {{ tag_prefix: {prefix} }}\n"
        '      features: "tests/acceptance/**/*.feature"\n'
    )


def _project(tmp_path: Path, prefix: str) -> Path:
    root = tmp_path / "shop"
    feature = root / "tests" / "acceptance" / "board.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(_FEATURE, encoding="utf-8")
    return write_tiered_project(root, nodes=_NODES, edges=_EDGES, more_rules=_rule(prefix))


def _uncovered(result: LintResult) -> set[str]:
    return {
        str(v.from_ref_id)
        for v in result.violations
        if v.rule_name == _RULE_NAME
        and v.rule_type == "scenario_coverage"
        and v.from_ref_id is not None
    }


def test_a_tag_prefix_in_the_rules_file_is_read_into_the_coverage_matcher(
    tmp_path: Path,
) -> None:
    # Arrange
    root = _project(tmp_path, "ui-")

    # Act
    rules = load_rules(root / ".beadloom" / "_graph" / "rules.yml")

    # Assert
    coverage = [rule for rule in rules if isinstance(rule, ScenarioCoverageRule)]
    assert [rule.for_matcher.tag_prefix for rule in coverage] == ["ui-"]


def test_only_the_prefixed_nodes_without_a_scenario_are_reported(tmp_path: Path) -> None:
    # Arrange
    root = _project(tmp_path, "ui-")

    # Act
    result = lint(root)

    # Assert
    assert _uncovered(result) == {"search", "cart"}


def test_the_population_statement_counts_the_prefixed_nodes_of_the_graph(
    tmp_path: Path,
) -> None:
    # Arrange
    root = _project(tmp_path, "ui-")

    # Act
    result = lint(root)

    # Assert
    statements = [
        v.message for v in result.violations if v.rule_name == _RULE_NAME and v.from_ref_id is None
    ]
    assert any("3 of 5 graph node(s) (tag_prefix=ui-)" in m for m in statements)


def test_a_prefix_no_node_carries_is_reported_as_selecting_no_node(tmp_path: Path) -> None:
    # Arrange
    root = _project(tmp_path, "mobile-")

    # Act
    result = lint(root)

    # Assert
    liveness = [
        v.message
        for v in result.violations
        if v.rule_name == _RULE_NAME and v.rule_type == LIVENESS_RULE_TYPE
    ]
    assert any("tag_prefix=mobile-" in m and "selects no node" in m for m in liveness)
