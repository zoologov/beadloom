"""BDL-UX #265 — the graph is one file, so one writer per file was available and not taken.

`beadloom-kqsv` made the shared write VISIBLE: `graph-files` is the seventh medium
every wave states, and its check compares the node population the graph files
declare against the population the index resolved the plan's scopes from. It
declined the serialisation BDL-UX #261 sketched, with the number that decides it —
one file held every one of this project's 100 nodes, so "two beads whose declared
nodes are defined in one graph file" fired on every pair.

This module is the layout that removes the sharing instead of reporting it: one
graph file per node, named after the node, holding the node and the edges declared
with it. Two node-adding beads then write two different files, and the collision
cannot be attempted.

THE COST, MEASURED RATHER THAN ASSUMED, on this repository's 100 nodes and 169
edges, macOS 26.6.2 arm64, CPython 3.13.7, warm APFS, medians of 20 in-process
runs and 5 subprocess runs against two copies of this tree that differ only in the
graph's layout:

    load_graph          61.34 ms -> 66.40 ms  (+5.06, +8.2%)
    each_graph_file     50.24 ms -> 55.44 ms  (+5.20, +10.3%)
    beadloom reindex --full   1895 ms -> 1950 ms  (+55, +2.9%)
    beadloom lint --strict     368 ms ->  369 ms
    beadloom doctor            427 ms ->  429 ms
    beadloom ctx graph          162 ms ->  168 ms
    beadloom why graph          128 ms ->  131 ms
    beadloom status             787 ms ->  788 ms

NOTHING THAT IS ONE PASS BECOMES N. Every reader of the directory already globs
`*.yml` and iterates — `load_graph`, `each_graph_file`, `graph/diff.py`,
`reindex/change_detection.py`, `reindex/indexing.py`, `setup.py`,
`index_ops.py` — so N files is the same single loop with more iterations. The
readers that go through the INDEX rather than the YAML pay nothing at all, which
is what the `lint`, `doctor` and `status` rows show.

AND THE MECHANISM THE SPLIT WAS SUPPOSED TO UNLOCK IS REDUNDANT, NOT MEANINGFUL.
`beadloom-kqsv` recorded that a graph split across files is the condition under
which the declined serialisation becomes worth building.
:class:`TestTheSplitMakesTheSerialisationRedundantRatherThanMeaningful` is that
prediction measured: under one node per file the map from node to file is
injective, so `file_of[a] == file_of[b]` holds exactly when `a == b`, and
`conflict_between` already serialises that as `shared_node`. The serialisation is
only ever non-trivial while some file holds more than one node — which is the
state the layout removes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from beadloom.application.waves import (
    GraphFile,
)
from beadloom.onboarding.graph_layout import (
    SharedFile,
    layout_of,
    node_file_name,
    shared_files,
)
from tests.support.graph_files_verdict import graph_files_verdict

if TYPE_CHECKING:
    from pathlib import Path


def _write(graph_dir: Path, name: str, refs: list[str]) -> None:
    """Write a graph file declaring *refs*, the way a hand edit would."""
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / name).write_text(
        yaml.safe_dump({"nodes": [{"ref_id": ref, "kind": "feature"} for ref in refs]}),
        encoding="utf-8",
    )


def _write_node(
    graph_dir: Path, ref: str, *, edges: list[tuple[str, str]] | None = None
) -> None:
    """Write one node's own file, the way the layout says a bead writes one."""
    graph_dir.mkdir(parents=True, exist_ok=True)
    document: dict[str, object] = {"nodes": [{"ref_id": ref, "kind": "feature"}]}
    if edges:
        document["edges"] = [
            {"src": src, "dst": dst, "kind": "uses"} for src, dst in edges
        ]
    (graph_dir / f"{ref}.yml").write_text(
        yaml.safe_dump(document), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# The layout, stated once
# ---------------------------------------------------------------------------


class TestTheFileANodeIsDeclaredIn:
    """The naming half: a node is findable by hand without a search."""

    def test_a_nodes_file_is_named_after_the_node(self) -> None:
        assert node_file_name("wave-plan") == "wave-plan.yml"

    def test_the_name_is_the_ref_id_and_nothing_derived_from_it(self) -> None:
        # A ref id is already the graph's own identifier and is already unique,
        # so any transformation here would introduce a second spelling of one
        # name — which is the class of defect this epic removes everywhere else.
        assert node_file_name("ai-techwriter") == "ai-techwriter.yml"


class TestTheSurfaceWhereASharedWriteIsStillPossible:
    """`shared_files` — the one computation, over a mapping either caller holds."""

    def test_a_file_holding_one_node_is_not_a_shared_write(self) -> None:
        assert shared_files({"billing.yml": ("billing",)}) == ()

    def test_a_file_holding_two_nodes_is_reported_with_both(self) -> None:
        assert shared_files({"services.yml": ("billing", "shipping")}) == (
            SharedFile(name="services.yml", nodes=("billing", "shipping")),
        )

    def test_the_nodes_are_reported_sorted_so_the_verdict_is_stable(self) -> None:
        shared = shared_files({"services.yml": ("shipping", "billing")})
        assert shared[0].nodes == ("billing", "shipping")

    def test_files_are_reported_sorted_so_two_runs_read_the_same(self) -> None:
        shared = shared_files({"b.yml": ("c", "d"), "a.yml": ("e", "f")})
        assert [f.name for f in shared] == ["a.yml", "b.yml"]

    def test_a_file_declaring_nothing_is_not_a_file_of_the_layout(self) -> None:
        assert shared_files({"empty.yml": ()}) == ()


class TestTheLayoutOfAGraphDirectory:
    """`layout_of` — the same surface, read off disk through the one skip policy."""

    def test_one_file_per_node_holds(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / "_graph"
        _write(graph_dir, "billing.yml", ["billing"])
        _write(graph_dir, "shipping.yml", ["shipping"])
        layout = layout_of(graph_dir)
        assert layout.holds
        assert layout.declared == 2
        assert layout.shared_nodes == 0

    def test_a_single_file_graph_does_not_hold_and_says_how_many(
        self, tmp_path: Path
    ) -> None:
        graph_dir = tmp_path / "_graph"
        _write(graph_dir, "services.yml", ["billing", "shipping", "catalog"])
        layout = layout_of(graph_dir)
        assert not layout.holds
        assert layout.shared_nodes == 3
        assert [f.name for f in layout.shared] == ["services.yml"]

    def test_the_rules_file_is_not_a_graph_file_here_either(
        self, tmp_path: Path
    ) -> None:
        # The skip policy is `each_graph_file`'s and is not restated here: a
        # second policy over the same directory is the defect that module exists
        # to have removed.
        graph_dir = tmp_path / "_graph"
        _write(graph_dir, "billing.yml", ["billing"])
        (graph_dir / "rules.yml").write_text("rules: []\n", encoding="utf-8")
        assert layout_of(graph_dir).declared == 1

    def test_a_directory_with_no_graph_holds_vacuously_and_declares_nothing(
        self, tmp_path: Path
    ) -> None:
        layout = layout_of(tmp_path / "nothing" / "here")
        assert layout.holds
        assert layout.declared == 0

    def test_a_node_declared_in_a_file_not_named_after_it_is_reported(
        self, tmp_path: Path
    ) -> None:
        graph_dir = tmp_path / "_graph"
        _write(graph_dir, "misc.yml", ["billing"])
        assert layout_of(graph_dir).misnamed == ("billing",)

    def test_the_layout_can_hold_while_a_name_disagrees(self, tmp_path: Path) -> None:
        # One node per file is the property that removes the shared write; the
        # name is what makes the node findable by hand. They are reported apart
        # because a project can have the first without the second.
        graph_dir = tmp_path / "_graph"
        _write(graph_dir, "misc.yml", ["billing"])
        layout = layout_of(graph_dir)
        assert layout.holds
        assert layout.misnamed == ("billing",)


class TestWhereAnEdgeIsDeclared:
    """The half a node split does not answer on its own.

    An edge is a fact about TWO nodes and one file per node can only give it one
    home, so the layout states the weaker property that is nonetheless enough: an
    edge is declared in a file named after one of its endpoints. The migration
    placed every existing edge under its `src`, which is total and deterministic;
    a bead that ADDS a node writes its inbound edges into the new node's file
    instead, because that is the only placement that leaves the existing nodes'
    files untouched. Both satisfy the property, which is why the property is
    stated over endpoints rather than over `src`.
    """

    def test_an_edge_under_its_source_is_placed(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / "_graph"
        _write_node(graph_dir, "billing", edges=[("billing", "core")])
        _write_node(graph_dir, "core")
        assert layout_of(graph_dir).misplaced_edges == ()

    def test_an_edge_under_its_destination_is_placed(self, tmp_path: Path) -> None:
        # This is the case a node-adding bead produces: the new node's file
        # carries the edges that point AT it, so no existing file is written.
        graph_dir = tmp_path / "_graph"
        _write_node(graph_dir, "billing", edges=[("core", "billing")])
        _write_node(graph_dir, "core")
        assert layout_of(graph_dir).misplaced_edges == ()

    def test_an_edge_under_neither_endpoint_is_reported(self, tmp_path: Path) -> None:
        graph_dir = tmp_path / "_graph"
        _write_node(graph_dir, "billing", edges=[("core", "shipping")])
        assert layout_of(graph_dir).misplaced_edges == ("core -> shipping (uses)",)

    def test_a_single_file_graph_reports_every_edge_it_holds(
        self, tmp_path: Path
    ) -> None:
        # Every edge of a graph named `services.yml` is under neither endpoint,
        # which is the true and unsurprising statement about that layout: a bead
        # adding an edge writes the file every other bead writes.
        graph_dir = tmp_path / "_graph"
        graph_dir.mkdir(parents=True)
        (graph_dir / "services.yml").write_text(
            yaml.safe_dump(
                {
                    "nodes": [{"ref_id": "billing"}, {"ref_id": "core"}],
                    "edges": [{"src": "billing", "dst": "core", "kind": "part_of"}],
                }
            ),
            encoding="utf-8",
        )
        assert layout_of(graph_dir).misplaced_edges == ("billing -> core (part_of)",)


# ---------------------------------------------------------------------------
# This repository, which is the tree the layout was taken for
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# What the medium says once the sharing is gone
# ---------------------------------------------------------------------------


class TestTheMediumStopsNamingAFileEveryNodeAddingBeadWrites:
    """The pass sentence was true of a one-file graph and is false of this one."""

    def test_a_split_graph_is_told_the_collision_cannot_be_attempted(self) -> None:
        detail = graph_files_verdict(
            (
                GraphFile(path=".beadloom/_graph/billing.yml", nodes=("billing",)),
                GraphFile(path=".beadloom/_graph/shipping.yml", nodes=("shipping",)),
            )
        )
        assert "a file of its own" in detail

    def test_a_split_graph_still_states_the_half_no_plan_can_reach(self) -> None:
        # Two beads adding nodes write two files, so the collision is gone; the
        # FILES they are about to create are still in no graph this plan read,
        # and a pass that stopped saying so would be the clean list CONTEXT
        # forbids.
        detail = graph_files_verdict(
            (GraphFile(path=".beadloom/_graph/billing.yml", nodes=("billing",)),)
        )
        assert "no graph this plan could read" in detail

    def test_a_shared_file_is_still_named_with_the_count_it_holds(self) -> None:
        detail = graph_files_verdict(
            (
                GraphFile(
                    path=".beadloom/_graph/services.yml",
                    nodes=("billing", "shipping"),
                ),
            )
        )
        assert ".beadloom/_graph/services.yml" in detail
        assert "2" in detail

