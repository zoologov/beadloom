"""A matcher's ``tag_prefix`` reaches the ``rules`` table (BDL-080 S2b).

A reader of the index must not see a wider rule than the one that runs: a ``check``
over ``{kind: component, tag_prefix: fsd-}`` stored as ``{kind: component}`` would
read as a limit on every component.
"""

from __future__ import annotations

from beadloom.application.reindex.rules_loader import _serialize_rule
from beadloom.graph.rules.types import CardinalityRule, NodeMatcher


def test_a_check_over_a_prefix_is_stored_with_its_prefix() -> None:
    rule = CardinalityRule(
        name="fsd-cohesion",
        description="",
        for_matcher=NodeMatcher(kind="component", tag_prefix="fsd-"),
        max_symbols=60,
    )

    rule_type, stored = _serialize_rule(rule)

    assert rule_type == "cardinality"
    assert stored["for"] == {"kind": "component", "tag_prefix": "fsd-"}
