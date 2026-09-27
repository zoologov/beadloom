"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_the_graph_is_one_file_per_node.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from beadloom.application.waves import (
    GraphFile,
)
from beadloom.onboarding.graph_layout import (
    GraphLayout,
    layout_of,
)
from tests.test_the_graph_is_one_file_per_node import (
    _graph_verdict,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


_GRAPH_DIR = _REPO_ROOT / ".beadloom" / "_graph"


class TestThisProjectsGraph:
    """The pins. Each goes red on a hand edit that puts the layout back."""

    @pytest.fixture
    def layout(self) -> GraphLayout:
        return layout_of(_GRAPH_DIR)

    def test_no_graph_file_declares_two_nodes(self, layout: GraphLayout) -> None:
        assert layout.shared == ()

    def test_every_node_is_declared_in_the_file_named_after_it(
        self, layout: GraphLayout
    ) -> None:
        assert layout.misnamed == ()

    def test_every_edge_is_declared_under_one_of_its_endpoints(
        self, layout: GraphLayout
    ) -> None:
        assert layout.misplaced_edges == ()

    def test_the_declared_population_did_not_change_with_the_layout(
        self, layout: GraphLayout
    ) -> None:
        # The migration is behaviour-preserving or it is not a migration. The
        # count is the coarse half; `beadloom doctor` and `lint --strict` on the
        # same tree are the fine one.
        assert layout.declared == len(layout.files)
        assert layout.declared > 0


class TestTheSplitMakesTheSerialisationRedundantRatherThanMeaningful:
    """`beadloom-kqsv`'s prediction, measured on the tree that met its condition.

    It recorded that a graph split across files is the condition under which the
    declined serialisation becomes worth building, and pinned that condition as
    `TestTheGraphFileCannotSerialiseWithoutNoise`. The condition is now met and
    the conclusion does not follow: one node per file makes the node-to-file map
    INJECTIVE, so "two beads whose declared nodes are defined in one graph file"
    holds exactly when the two beads declare the same node — which
    `conflict_between` already serialises as `shared_node`. A serialisation that
    can produce no pair `shared_node` does not already produce is a check that
    cannot fail, which is the same ground on which `shared_document` was
    declined.

    THIS GOES RED when some file of this repository's graph declares two nodes
    again, because then the map stops being injective and there is a pair the
    file reason finds that the node reason does not.
    """

    def test_the_file_a_node_is_declared_in_names_exactly_that_node(self) -> None:
        file_of: dict[str, str] = {}
        for file in layout_of(_GRAPH_DIR).files:
            for ref in file.nodes:
                file_of[ref] = file.name
        refs = sorted(file_of)
        shared = [
            pair
            for pair in itertools.combinations(refs, 2)
            if file_of[pair[0]] == file_of[pair[1]]
        ]
        assert shared == []

    def test_the_declined_serialisation_would_now_fire_on_no_pair(self) -> None:
        layout = layout_of(_GRAPH_DIR)
        assert layout.shared_nodes == 0


class TestTheMediumStopsNamingAFileEveryNodeAddingBeadWrites:
    """The pass sentence was true of a one-file graph and is false of this one."""

    def test_the_verdict_over_this_repositorys_own_graph_names_no_shared_file(
        self,
    ) -> None:
        files = tuple(
            GraphFile(path=f".beadloom/_graph/{file.name}", nodes=file.nodes)
            for file in layout_of(_GRAPH_DIR).files
        )
        assert "a file of its own" in _graph_verdict(files)
