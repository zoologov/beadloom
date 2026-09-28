"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/graph/scenarios/test_bead14_s4_binding.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from beadloom.graph.rules import (
    ScenarioCoverageRule,
    load_rules,
)
from beadloom.onboarding.graph_files import each_graph_file
from tests.support.repository_root import REPO_ROOT

#: This repository, so the shipped configuration is read rather than restated.


GRAPH_DIR = REPO_ROOT / ".beadloom" / "_graph"


def _shipped_scenario_coverage_rule() -> ScenarioCoverageRule:
    """The rule THIS repository runs, read from the file it is configured in."""
    rules = load_rules(GRAPH_DIR / "rules.yml")
    matching = [r for r in rules if isinstance(r, ScenarioCoverageRule)]
    assert len(matching) == 1, (
        "expected exactly one scenario_coverage rule in the shipped rules.yml; "
        f"found {len(matching)}"
    )
    return matching[0]


def _declared_nodes() -> list[tuple[str, str]]:
    """Every node the graph DIRECTORY declares, as ``(ref_id, kind)``.

    Read from the tracked YAML rather than from `.beadloom/beadloom.db`: the index
    is gitignored, so a check that read it would ERROR in a clean room instead of
    measuring anything, and a shared tree may be reindexed mid-run by another
    agent.

    Read from the DIRECTORY rather than from `services.yml`, since BDL-UX #265
    split this repository's graph into one file per node. The reader is
    `each_graph_file`, which is the one policy every reader of that directory
    holds, so this population cannot disagree with the loader's about which files
    count.
    """
    return [
        (str(node["ref_id"]), str(node.get("kind", "")))
        for _path, data in each_graph_file(GRAPH_DIR)
        for node in (data.get("nodes") or [])
        if isinstance(node, dict) and node.get("ref_id")
    ]


class TestThePopulationIsHonest:
    """35 uncovered nodes is only a finding if the denominator was not chosen to fit."""

    def test_the_population_is_a_graph_kind_and_not_a_hand_picked_list(self) -> None:
        """The shipped matcher selects by KIND, with nothing carved out of it.

        A `ref_id` matcher checks one node and an `exclude` list checks whatever is
        left after the awkward ones are removed. Either reports a small number
        honestly-looking, and neither is a statement about the system.
        """
        matcher = _shipped_scenario_coverage_rule().for_matcher

        assert matcher.kind == "feature", matcher
        assert matcher.ref_id is None, (
            "the population is pinned to a single node — that is one check wearing "
            "the name of a coverage rule"
        )
        assert not matcher.exclude, (
            f"nodes are carved out of the population: {matcher.exclude}. An "
            "exclusion here is invisible in the finding count; declare the node "
            "non_behavioural with a reason instead, where a dead declaration is "
            "itself reported"
        )

    def test_every_feature_node_the_graph_declares_is_in_the_population(self) -> None:
        """The matcher's reach is measured against the file that declares the nodes.

        Not "the matcher looks right": the two files are compared, so moving a node
        out of the population requires changing its KIND in `services.yml`, which is
        a visible architectural claim, rather than editing a list in `rules.yml`.
        """
        matcher = _shipped_scenario_coverage_rule().for_matcher
        declared = _declared_nodes()
        features = {ref_id for ref_id, kind in declared if kind == "feature"}
        selected = {ref_id for ref_id, kind in declared if matcher.matches(ref_id, kind)}

        assert selected == features
        assert len(features) >= 30, (
            f"only {len(features)} feature nodes are declared — the population this "
            "rule reports a fraction OF has collapsed, and a small denominator makes "
            "any coverage claim look better than it is"
        )
