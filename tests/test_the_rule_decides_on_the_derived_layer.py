"""The layer rule judges an edge by the layer each end is IN, container or not.

BDL-070 B3 (`beadloom-ku26`). Release A made the rule's reach visible and moved
no verdict: it read a node's OWN layer tags and passed over every edge whose
ends carried none — 16 of 365 live `depends_on` edges on this repository,
measured 2026-09-13. This release is the one that changes what the rule decides,
and these are the claims it changes it to:

- an end takes its layer from the nearest `part_of` container that declares one,
  so an edge between two untagged components inside tagged domains is judged;
- an edge INSIDE one layer is legal when both ends share a container the
  declaration gives a layer, and a finding when they do not (RFC Q1, decided by
  the owner on a measurement: 116 internal against 14 peer crossings here);
- a node carrying its own tag keeps it and does not climb;
- and a graph with no `part_of` at all is judged exactly as it was before,
  because there is nothing to inherit from. That last one is the upgrade path
  for a project that tags its nodes directly, and it is asserted against a
  verbatim transcription of the pre-change evaluator rather than against a
  description of it.

Every graph here declares `tier-web` / `tier-core` / `tier-store`, a vocabulary
`src/` does not contain, and is written to disk and indexed by the real reindex
— a fixture assembled out of `INSERT` statements proves what the test author
believed the indexer writes.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.linter import lint
from beadloom.graph.rules.evaluators import evaluate_layer_rules
from beadloom.graph.rules.layer_crossings import SAME_LAYER_REMEDIATION
from beadloom.graph.rules.layer_reach import layer_rule_reach
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerRule, Violation
from tests.acceptance.steps.tiered_project import (
    TIERS,
    graph_with,
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
)
from tests.the_lint_path_before_release_a import (
    comparable,
    decisions,
    layer_findings_before_release_a,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: The only exemption the fixtures below need: one crossing, excused by name.
_EXCUSING_LEDGER_API = (
    "    exempt:\n"
    "      - from: ledger-api\n"
    "        to: postings-api\n"
    '        reason: "the two read one ledger and the read seam is not built yet"\n'
    '        until: "2030-01-01"\n'
)


def _rule_of(project: Path) -> LayerRule:
    """The layer rule the project declares, as the linter loads it."""
    return next(
        rule
        for rule in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(rule, LayerRule)
    )


def _conn(project: Path) -> closing[sqlite3.Connection]:
    """A handle on the project's index that closes itself.

    `sqlite3.Connection` is its own context manager and that manager commits a
    transaction rather than closing the handle, which is the shape that leaves
    a test's connections open until the interpreter exits.
    """
    return closing(sqlite3.connect(project / ".beadloom" / "beadloom.db"))


def _layer_findings(project: Path) -> list[Violation]:
    """What the rule DECIDES about *project* — its advisories left out."""
    with _conn(project) as conn:
        return [
            v for v in evaluate_layer_rules(conn, [_rule_of(project)]) if v.rule_type == "layer"
        ]


def _edges_judged(findings: list[Violation]) -> set[tuple[str | None, str | None]]:
    return {(v.from_ref_id, v.to_ref_id) for v in findings}


@pytest.fixture(scope="module")
def nested_parts(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two untagged components inside containers in different tiers."""
    nodes, edges = graph_with_nested_parts()
    return write_tiered_project(
        tmp_path_factory.mktemp("nested") / "shop", nodes=nodes, edges=edges
    )


@pytest.fixture(scope="module")
def peer_containers(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two containers in ONE tier, each holding a part — the crossing shape."""
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(
        tmp_path_factory.mktemp("peers") / "ledger", nodes=nodes, edges=edges
    )


@pytest.fixture(scope="module")
def peer_containers_with_an_exemption(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The same graph, with one of its two crossings excused by name."""
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(
        tmp_path_factory.mktemp("excused") / "ledger",
        nodes=nodes,
        edges=edges,
        exempt=_EXCUSING_LEDGER_API,
    )


@pytest.fixture(scope="module")
def graph_without_containment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Tagged nodes, untagged nodes, and not one `part_of` edge.

    The upgrade path for a project that tags its nodes directly: there is
    nothing to inherit from, so this release must decide here exactly what the
    release before it decided.
    """
    nodes, edges = graph_with(tiered_edges=3, untiered_edges=2)
    nodes.append(("legacy", "domain", [TIERS[2]]))
    edges.append(("legacy", "a0", "depends_on"))
    return write_tiered_project(tmp_path_factory.mktemp("flat") / "shop", nodes=nodes, edges=edges)


class TestAnEndTakesItsLayerFromItsContainer:
    """The verdict change: an edge no own tag reaches is judged."""

    def test_an_edge_between_two_untagged_parts_is_judged(self, nested_parts: Path) -> None:
        """`store-db -> web-api` runs from the bottom tier into the top one."""
        assert ("store-db", "web-api") in _edges_judged(_layer_findings(nested_parts))

    def test_the_same_dependency_the_right_way_round_is_not(self, nested_parts: Path) -> None:
        """A differential over findings alone would pass on a rule that flags everything."""
        assert ("web-api", "store-db") not in _edges_judged(_layer_findings(nested_parts))

    def test_the_pre_change_rule_saw_neither(self, nested_parts: Path) -> None:
        """The premise: this is a verdict the rule could not reach before B3."""
        with _conn(nested_parts) as conn:
            assert layer_findings_before_release_a(conn, [_rule_of(nested_parts)]) == []

    def test_the_finding_names_the_container_the_layer_came_from(self, nested_parts: Path) -> None:
        """A reader meeting this finding on upgrade asks why the node is in that tier."""
        found = [v for v in _layer_findings(nested_parts) if v.from_ref_id == "store-db"]
        assert "inherited from 'store'" in found[0].message

    def test_a_node_with_its_own_tag_does_not_say_it_inherited_one(
        self, graph_without_containment: Path
    ) -> None:
        """An end that declares its own layer reads exactly as it read before."""
        found = [
            v for v in _layer_findings(graph_without_containment) if v.from_ref_id == "legacy"
        ]
        assert found and "inherited from" not in found[0].message


class TestAnEdgeInsideOneLayer:
    """RFC Q1: legal between parts of one container, a finding between peers."""

    def test_a_dependency_between_two_parts_of_one_container_is_legal(
        self, peer_containers: Path
    ) -> None:
        assert ("ledger-api", "ledger-store") not in _edges_judged(
            _layer_findings(peer_containers)
        )

    def test_a_crossing_between_peers_is_a_finding(self, peer_containers: Path) -> None:
        assert ("ledger-api", "postings-api") in _edges_judged(_layer_findings(peer_containers))

    def test_it_is_reported_at_the_severity_the_rule_declares(self, peer_containers: Path) -> None:
        """`architecture-layers` is `error` here and in every project that copied it."""
        crossings = [v for v in _layer_findings(peer_containers) if v.to_ref_id == "postings-api"]
        assert [v.severity for v in crossings] == ["error"]

    def test_the_finding_says_what_would_make_the_edge_legal(self, peer_containers: Path) -> None:
        crossings = [v for v in _layer_findings(peer_containers) if v.to_ref_id == "postings-api"]
        assert crossings[0].remediation == SAME_LAYER_REMEDIATION

    def test_an_excused_crossing_is_not_reported(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        judged = _edges_judged(_layer_findings(peer_containers_with_an_exemption))
        assert ("ledger-api", "postings-api") not in judged

    def test_excusing_one_direction_does_not_excuse_the_other(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        judged = _edges_judged(_layer_findings(peer_containers_with_an_exemption))
        assert ("postings-api", "ledger-api") in judged


class TestAGraphWithNoContainmentIsJudgedAsBefore:
    """The upgrade path for a project whose nodes carry their own tags."""

    def test_the_decisions_are_identical(self, graph_without_containment: Path) -> None:
        with _conn(graph_without_containment) as conn:
            rules = [_rule_of(graph_without_containment)]
            before = layer_findings_before_release_a(conn, rules)
            assert comparable(before), "a comparison over an empty findings list proves nothing"
            assert decisions(evaluate_layer_rules(conn, rules)) == comparable(before)

    def test_the_whole_lint_run_reports_the_same_population(
        self, graph_without_containment: Path
    ) -> None:
        """Three tiered edges of six, and no container to reach the other three."""
        result = lint(graph_without_containment)
        assert [
            (reach.population.evaluated, reach.population.total)
            for reach in result.layer_populations
        ] == [(4, 6)]


class TestThePopulationIsTheOneTheRuleDecidesOn:
    """What the run states is what the rule judged, not what own tags reach."""

    def test_a_graph_whose_containers_carry_the_layers_states_a_full_population(
        self, nested_parts: Path
    ) -> None:
        with _conn(nested_parts) as conn:
            reach = layer_rule_reach(conn, _rule_of(nested_parts))
        assert (reach.population.evaluated, reach.population.total) == (2, 2)

    def test_an_end_in_no_declared_layer_is_still_skipped(
        self, graph_without_containment: Path
    ) -> None:
        with _conn(graph_without_containment) as conn:
            reach = layer_rule_reach(conn, _rule_of(graph_without_containment))
        assert reach.population.skipped_untagged == 2

    def test_the_statement_names_containment_as_a_way_to_be_judged(
        self, graph_without_containment: Path
    ) -> None:
        """The remaining unjudged edges are actionable two ways, and it says both."""
        statements = [
            v
            for v in lint(graph_without_containment).violations
            if v.rule_type == "layer_population"
        ]
        assert len(statements) == 1
        assert "part_of" in str(statements[0].remediation)


@pytest.fixture()
def live(live_repo_reindexed: Path) -> Iterator[sqlite3.Connection]:
    """A read-only handle on this repository's own indexed graph."""
    db_path = live_repo_reindexed / ".beadloom" / "beadloom.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        yield conn
    finally:
        conn.close()


class TestOnThisRepository:
    """The measurement the epic ordered its beads around, taken from the code."""

    def test_the_rule_now_judges_the_ancestry_population(
        self, live: sqlite3.Connection, live_repo_reindexed: Path
    ) -> None:
        """16 of 365 by own tags before this bead; the ancestry figure is the claim now."""
        reach = layer_rule_reach(live, _rule_of(live_repo_reindexed))
        assert reach.population.total > 300
        assert reach.population.evaluated > reach.population.total * 9 // 10

    def test_it_decides_nothing_new_here_because_b1_and_b2_ran_first(
        self, live: sqlite3.Connection, live_repo_reindexed: Path
    ) -> None:
        """Not neutrality by construction: the one reverse edge was removed (B1) and
        every crossing left was excused by name with a reason (B2). This asserts
        that work held, on the graph, rather than on a report of it.
        """
        rule = _rule_of(live_repo_reindexed)
        assert [v for v in evaluate_layer_rules(live, [rule]) if v.rule_type == "layer"] == []

    def test_lint_has_no_error_on_this_repository(self, live_repo_reindexed: Path) -> None:
        """What `lint --strict` and the Gate decide on is the error count alone."""
        result = lint(live_repo_reindexed)
        assert result.error_count == 0
