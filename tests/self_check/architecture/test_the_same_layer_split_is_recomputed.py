"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/integration/graph/rules/test_the_same_layer_split_is_recomputed.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_exemptions import excused_crossings
from beadloom.graph.rules.layer_reach import (
    part_of_parents,
)
from beadloom.graph.rules.layers import (
    own_layer_of,
    shares_tagged_ancestor,
)
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE
from tests.support.layer_rule import (
    Split,
    read_only_index,
    retired_crossings,
    rule_of,
    split_of,
)
from tests.support.tiered_project import (
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path



@pytest.fixture()
def live_split(self_check_snapshot: Path) -> Split:
    """This repository's split, recomputed from the index built for this session."""
    with read_only_index(self_check_snapshot) as conn:
        return split_of(conn, rule_of(self_check_snapshot))


@pytest.fixture()
def peers(tmp_path: Path) -> Path:
    """Two peer containers in one tier: one internal edge and two crossings.

    Written and indexed once, then read without a further reindex — the same
    lineage discipline the live half holds.
    """
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(tmp_path / "ledger", nodes=nodes, edges=edges)


class TestTheSplitIsRecomputedOnThisRepository:
    """Every figure below is measured in the assertion that reads it."""

    def test_the_two_halves_account_for_every_same_layer_edge(
        self, live_split: Split
    ) -> None:
        """Exhaustive and disjoint: an edge is internal or a crossing, never both."""
        assert set(live_split.internal) | set(live_split.crossings) == set(
            live_split.same_layer
        )
        assert set(live_split.internal) & set(live_split.crossings) == set()
        assert len(live_split.internal) + len(live_split.crossings) == len(
            live_split.same_layer
        )

    def test_the_population_accounts_for_every_edge_the_rule_was_handed(
        self, live_split: Split
    ) -> None:
        """Judged plus skipped is the whole edge set, and the same-layer edges
        are a subset of what was judged — a crossing inside an unjudged edge
        would be a finding the population statement says was never looked at."""
        assert live_split.evaluated + live_split.skipped == live_split.total
        assert len(live_split.same_layer) <= live_split.evaluated

    def test_neither_retired_predicate_could_have_produced_this_split(
        self, live_split: Split
    ) -> None:
        """The measurement RFC Q1 rests on, retaken rather than quoted.

        `evaluators.py:632` passed every same-layer edge and
        `architecture_view.py:268` flagged every one. Both halves being
        non-empty refutes both in one assertion, and it does so without naming
        the size of either.
        """
        assert live_split.internal, "no same-layer edge is internal to a container"
        assert live_split.crossings, "no same-layer edge runs between peers"
        assert 0 < len(live_split.crossings) < len(live_split.same_layer)

    def test_the_internal_half_is_the_larger_one(self, live_split: Split) -> None:
        """The shape of the decision: most same-layer edges are inside a domain.

        Asserted as a relation and not as 114 against 15, because the counts
        move with every module this repository adds and the relation is what
        made flagging all of them wrong.
        """
        assert len(live_split.internal) > len(live_split.crossings)

    def test_every_crossing_is_reported_or_excused_by_a_named_entry(
        self, self_check_snapshot: Path, live_split: Split
    ) -> None:
        """No crossing falls between the rule and its exemptions.

        The counts come from the rule's own splitter, so a crossing silently
        dropped by neither path would leave the two sides short.
        """
        rule = rule_of(self_check_snapshot)
        reported, excused = excused_crossings(rule, list(live_split.crossings))
        assert len(reported) + sum(excused.values()) == len(live_split.crossings)

    def test_the_findings_the_rule_reports_are_the_crossings_it_did_not_excuse(
        self, self_check_snapshot: Path, live_split: Split
    ) -> None:
        """The recomputation and `evaluate_layer_rules` agree on this graph."""
        rule = rule_of(self_check_snapshot)
        reported, _ = excused_crossings(rule, list(live_split.crossings))
        with read_only_index(self_check_snapshot) as conn:
            findings = [
                (v.from_ref_id, v.to_ref_id)
                for v in evaluate_layer_rules(conn, [rule])
                if v.rule_type == LAYER_EDGE_RULE_TYPE
                and "Same-layer crossing" in v.message
            ]
        assert sorted(findings) == sorted(reported)


class TestThePublishedFigureCameFromAnotherPredicate:
    """The RFC's correction, as a measurement rather than as a paragraph."""

    def test_the_retired_predicate_reports_more_crossings_here(
        self, self_check_snapshot: Path, live_split: Split
    ) -> None:
        """Strictly more, and the direction is why the planning figure was high."""
        retired = retired_crossings(self_check_snapshot, live_split)
        assert len(retired) > len(live_split.crossings)

    def test_the_shipped_predicate_calls_no_edge_a_crossing_that_the_retired_one_allows(
        self, self_check_snapshot: Path, live_split: Split
    ) -> None:
        """One-directional: the shipped predicate is the more permissive of the two."""
        retired = retired_crossings(self_check_snapshot, live_split)
        assert set(live_split.crossings) <= retired

    def test_every_pair_they_disagree_on_has_the_shape_the_correction_names(
        self, self_check_snapshot: Path, live_split: Split
    ) -> None:
        """Both ends carrying their own tag while sharing a tagged container.

        That is the only shape on which "the same nearest tagged container" and
        "both ends share a tagged ancestor" can differ, and asserting it turns
        the RFC's explanation of its own error into something that fails if the
        explanation is wrong.
        """
        rule = rule_of(self_check_snapshot)
        with read_only_index(self_check_snapshot) as conn:
            parents = part_of_parents(conn)
            tags = node_tags(conn).as_mapping()
        disputed = retired_crossings(self_check_snapshot, live_split) - set(
            live_split.crossings
        )
        assert disputed, "the two predicates agree here, so the correction is unmeasured"
        for src, dst in sorted(disputed):
            assert own_layer_of(src, rule.layers, tags) is not None, src
            assert own_layer_of(dst, rule.layers, tags) is not None, dst
            assert shares_tagged_ancestor(src, dst, rule.layers, parents, tags), (src, dst)
