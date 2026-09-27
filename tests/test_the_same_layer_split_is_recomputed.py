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

**The index lineage held is a full reindex of a copy of the working tree, taken
once per session and read without a further reindex** (`self_check_snapshot`). Both sides
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
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import LayerRule
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
