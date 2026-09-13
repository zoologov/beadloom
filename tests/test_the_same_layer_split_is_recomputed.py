"""The same-layer split is measured where it is asserted, never carried in.

BDL-070 B5 (`beadloom-bi78`). RFC Q1 was decided on a split of this repository's
same-layer `depends_on` edges: the ones running between two parts of one
container, and the ones running between peers. The figure the planning documents
published for the second half — 16 — was produced by a DIFFERENT predicate from
the one it was published under. It counted pairs that do not share the same
NEAREST tagged container, and it was printed beneath a sentence that says both
ends share a tagged ancestor. The RFC records the correction rather than
overwriting it, and the corrected figure is 15.

Two numbers computed by one rule and published under another is the defect this
whole epic exists to remove, and the documents that define the rule contain an
instance of it. So this module asserts nothing about 114, 116, 15 or 16. It
RECOMPUTES the split from the graph on every run and asserts the relations those
numbers were published to support:

- the split is exhaustive and disjoint, so no same-layer edge is counted twice
  or dropped;
- neither retired predicate can produce it, because both halves are non-empty —
  `evaluators.py:632` passed all of them and `architecture_view.py:268` flagged
  all of them, and a split with a non-empty half on each side refutes both in
  one measurement;
- the retired "same nearest tagged container" predicate and the shipped one
  disagree HERE, and every pair they disagree about has the shape the RFC's
  correction names: both ends carrying a declared tag of their own while
  sharing a tagged container;
- every crossing is accounted for — reported as a finding, or excused by a
  declared `exempt:` entry — so a crossing cannot be lost between the two.

**The index lineage held is a full reindex of the working tree, taken once per
session and read without a further reindex** (`live_repo_reindexed`). Both sides
of every comparison here read that one index, because a carried-forward index
and a fresh one disagree on a population's denominator (BDL-UX #290) and a
comparison whose halves counted two graphs measures the index.

The foreign-graph half reads a project written and indexed by this test, whose
layering is `tier-web` / `tier-core` / `tier-store` — a vocabulary `src/` does
not contain. The figures asserted there are small enough to read off the fixture
beside them, which is the one place a literal is not a carried number.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_exemptions import excused_crossings
from beadloom.graph.rules.layer_reach import (
    live_edges_of_kind,
    part_of_parents,
    reach_of,
)
from beadloom.graph.rules.layers import (
    layer_of,
    own_layer_of,
    part_of_generations,
    same_layer_crossings,
    shares_tagged_ancestor,
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LAYER_EDGE_RULE_TYPE, LayerRule
from tests.acceptance.steps.tiered_project import (
    graph_with,
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from pathlib import Path

    from beadloom.graph.rules.types import LayerDef


def _rule_of(project: Path) -> LayerRule:
    """The layer rule the project declares, as the linter loads it."""
    return next(
        rule
        for rule in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(rule, LayerRule)
    )


@dataclass(frozen=True)
class Split:
    """One recomputation of a layer rule's edge set, by what the rule does with it.

    Every field is derived in :func:`split_of` from one index and one rule. The
    class exists so a test names the half it is asserting about instead of
    indexing a tuple, and so a failure message can print all of them at once —
    the question a red here raises is always "then what ARE the numbers".
    """

    total: int
    evaluated: int
    same_layer: tuple[tuple[str, str], ...]
    internal: tuple[tuple[str, str], ...]
    crossings: tuple[tuple[str, str], ...]

    @property
    def skipped(self) -> int:
        """Edges with an end in no declared layer, which the rule does not judge."""
        return self.total - self.evaluated


def split_of(conn: sqlite3.Connection, rule: LayerRule) -> Split:
    """Recompute *rule*'s split over the indexed graph, from the shipped predicates.

    It calls :func:`~beadloom.graph.rules.layers.same_layer_crossings` rather
    than restating the predicate, because a test that reimplements the rule
    asserts agreement between two of its own bodies.
    """
    edges = live_edges_of_kind(conn, rule.edge_kind)
    parents = part_of_parents(conn)
    tags = node_tags(conn).as_mapping()
    same_layer = tuple(
        (src, dst)
        for src, dst in edges
        if (layer := layer_of(src, rule.layers, parents, tags)) is not None
        and layer == layer_of(dst, rule.layers, parents, tags)
    )
    crossings = tuple(same_layer_crossings(edges, rule.layers, parents, tags))
    return Split(
        total=len(edges),
        evaluated=reach_of(rule, edges, parents, tags).population.evaluated,
        same_layer=same_layer,
        internal=tuple(edge for edge in same_layer if edge not in set(crossings)),
        crossings=crossings,
    )


def nearest_tagged_container(
    ref_id: str,
    layers: Sequence[LayerDef],
    parents: Mapping[str, Collection[str]],
    tags: Mapping[str, Collection[str]],
) -> str | None:
    """The RETIRED predicate's half: the nearest container that carries a layer.

    Transcribed here, in the test that shows it is not the shipped one, because
    the alternative is a paragraph claiming the two differ. Reflexive in the
    same way the shipped predicate is — a node carrying its own tag is its own
    nearest tagged container — and that reflexivity is exactly where the two
    part company.
    """
    if own_layer_of(ref_id, layers, tags) is not None:
        return ref_id
    for generation in part_of_generations(ref_id, parents):
        declared = sorted(
            ancestor
            for ancestor in generation
            if own_layer_of(ancestor, layers, tags) is not None
        )
        if declared:
            return declared[0]
    return None


def _read_only(project: Path) -> closing[sqlite3.Connection]:
    """A read-only handle on *project*'s index that closes itself.

    Read-only on purpose: every handle this module opens on the live index is
    one that cannot move the lineage the session fixture established.
    """
    db_path = project / ".beadloom" / "beadloom.db"
    return closing(sqlite3.connect(f"file:{db_path}?mode=ro", uri=True))


@pytest.fixture()
def live_split(live_repo_reindexed: Path) -> Split:
    """This repository's split, recomputed from the index built for this session."""
    with _read_only(live_repo_reindexed) as conn:
        return split_of(conn, _rule_of(live_repo_reindexed))


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
        self, live_repo_reindexed: Path, live_split: Split
    ) -> None:
        """No crossing falls between the rule and its exemptions.

        The counts come from the rule's own splitter, so a crossing silently
        dropped by neither path would leave the two sides short.
        """
        rule = _rule_of(live_repo_reindexed)
        reported, excused = excused_crossings(rule, list(live_split.crossings))
        assert len(reported) + sum(excused.values()) == len(live_split.crossings)

    def test_the_findings_the_rule_reports_are_the_crossings_it_did_not_excuse(
        self, live_repo_reindexed: Path, live_split: Split
    ) -> None:
        """The recomputation and `evaluate_layer_rules` agree on this graph."""
        rule = _rule_of(live_repo_reindexed)
        reported, _ = excused_crossings(rule, list(live_split.crossings))
        with _read_only(live_repo_reindexed) as conn:
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
        self, live_repo_reindexed: Path, live_split: Split
    ) -> None:
        """Strictly more, and the direction is why the planning figure was high."""
        retired = _retired_crossings(live_repo_reindexed, live_split)
        assert len(retired) > len(live_split.crossings)

    def test_the_shipped_predicate_calls_no_edge_a_crossing_that_the_retired_one_allows(
        self, live_repo_reindexed: Path, live_split: Split
    ) -> None:
        """One-directional: the shipped predicate is the more permissive of the two."""
        retired = _retired_crossings(live_repo_reindexed, live_split)
        assert set(live_split.crossings) <= retired

    def test_every_pair_they_disagree_on_has_the_shape_the_correction_names(
        self, live_repo_reindexed: Path, live_split: Split
    ) -> None:
        """Both ends carrying their own tag while sharing a tagged container.

        That is the only shape on which "the same nearest tagged container" and
        "both ends share a tagged ancestor" can differ, and asserting it turns
        the RFC's explanation of its own error into something that fails if the
        explanation is wrong.
        """
        rule = _rule_of(live_repo_reindexed)
        with _read_only(live_repo_reindexed) as conn:
            parents = part_of_parents(conn)
            tags = node_tags(conn).as_mapping()
        disputed = _retired_crossings(live_repo_reindexed, live_split) - set(
            live_split.crossings
        )
        assert disputed, "the two predicates agree here, so the correction is unmeasured"
        for src, dst in sorted(disputed):
            assert own_layer_of(src, rule.layers, tags) is not None, src
            assert own_layer_of(dst, rule.layers, tags) is not None, dst
            assert shares_tagged_ancestor(src, dst, rule.layers, parents, tags), (src, dst)


def _retired_crossings(project: Path, split: Split) -> set[tuple[str, str]]:
    """The same-layer edges the RETIRED predicate would have called crossings."""
    rule = _rule_of(project)
    with _read_only(project) as conn:
        parents = part_of_parents(conn)
        tags = node_tags(conn).as_mapping()
    return {
        (src, dst)
        for src, dst in split.same_layer
        if nearest_tagged_container(src, rule.layers, parents, tags)
        != nearest_tagged_container(dst, rule.layers, parents, tags)
    }


@pytest.fixture()
def peers(tmp_path: Path) -> Path:
    """Two peer containers in one tier: one internal edge and two crossings.

    Written and indexed once, then read without a further reindex — the same
    lineage discipline the live half holds.
    """
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(tmp_path / "ledger", nodes=nodes, edges=edges)


@pytest.fixture()
def without_containment(tmp_path: Path) -> Path:
    """Tagged and untagged nodes and not one `part_of` edge."""
    nodes, edges = graph_with(tiered_edges=3, untiered_edges=2)
    return write_tiered_project(tmp_path / "shop", nodes=nodes, edges=edges)


class TestTheSplitOnAGraphThatIsNotThisRepository:
    """The same recomputation where every edge can be counted by hand."""

    def test_the_peer_fixture_splits_one_internal_against_two_crossings(
        self, peers: Path
    ) -> None:
        """`ledger-api -> ledger-store` is inside `ledger`; the two edges between
        `ledger-api` and `postings-api` run between peers under an untagged root."""
        with closing(sqlite3.connect(peers / ".beadloom" / "beadloom.db")) as conn:
            split = split_of(conn, _rule_of(peers))
        assert len(split.same_layer) == 3
        assert split.internal == (("ledger-api", "ledger-store"),)
        assert sorted(split.crossings) == [
            ("ledger-api", "postings-api"),
            ("postings-api", "ledger-api"),
        ]

    def test_a_graph_with_no_part_of_has_no_same_layer_edges_to_split(
        self, without_containment: Path
    ) -> None:
        """The upgrade path: nothing to inherit from, so nothing shares a container.

        Its three tiered edges each run between adjacent tiers, so the rule's
        whole same-layer half is empty here — and an empty half is a fact to
        assert, because a predicate that crashed on it would look identical to
        one that found nothing.
        """
        with closing(sqlite3.connect(without_containment / ".beadloom" / "beadloom.db")) as conn:
            split = split_of(conn, _rule_of(without_containment))
        assert split.same_layer == ()
        assert split.internal == ()
        assert split.crossings == ()
        assert split.evaluated == 3
        assert split.skipped == 2

    def test_the_two_predicates_agree_where_no_node_carries_its_own_tag(
        self, peers: Path
    ) -> None:
        """The control for the disagreement asserted on this repository.

        Every part of the peer fixture is untagged, so each end's nearest tagged
        container IS the container that gives it its layer, and the retired
        predicate and the shipped one cannot differ. A disagreement measured
        here would mean the two differ for some reason other than the one the
        RFC's correction names.
        """
        with closing(sqlite3.connect(peers / ".beadloom" / "beadloom.db")) as conn:
            split = split_of(conn, _rule_of(peers))
        assert _retired_crossings(peers, split) == set(split.crossings)
