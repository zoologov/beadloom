"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/graph/rules/test_the_rule_decides_on_the_derived_layer.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_reach import layer_rule_reach
from tests.support.layer_rule import judged_by_another_layer_rule, rule_of

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture()
def live(self_check_snapshot: Path) -> Iterator[sqlite3.Connection]:
    """A read-only handle on this repository's own indexed graph."""
    db_path = self_check_snapshot / ".beadloom" / "beadloom.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


class TestOnThisRepository:
    """The measurement the epic ordered its beads around, taken from the code."""

    def test_the_rule_now_judges_the_ancestry_population(
        self, live: sqlite3.Connection, self_check_snapshot: Path
    ) -> None:
        """16 of 365 by own tags before this bead; the ancestry figure is the claim now.

        The population is the rule's own: the site's edges are judged by
        `site-fsd-layers` and are subtracted (BDL-076 A3).
        """
        rule = rule_of(self_check_snapshot)
        reach = layer_rule_reach(live, rule)
        elsewhere = judged_by_another_layer_rule(live, self_check_snapshot, rule)
        own = reach.population.total - elsewhere
        assert own > 300
        assert reach.population.evaluated > own * 9 // 10

    def test_it_decides_nothing_new_here_because_b1_and_b2_ran_first(
        self, live: sqlite3.Connection, self_check_snapshot: Path
    ) -> None:
        """Not neutrality by construction: the one reverse edge was removed (B1) and
        every crossing left was excused by name with a reason (B2). This asserts
        that work held, on the graph, rather than on a report of it.
        """
        rule = rule_of(self_check_snapshot)
        assert [v for v in evaluate_layer_rules(live, [rule]) if v.rule_type == "layer"] == []

