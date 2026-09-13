"""The architecture view's edge verdict IS the layer rule's, edge for edge.

BDL-070 B4 (`beadloom-w34m`). Two instruments judged the same dependency and
disagreed. `application.architecture_view` flagged a `depends_on` edge whenever
`dst_rank <= src_rank`, which is every edge that points up AND every edge that
stays inside one layer — so a dependency between two components of one domain
was drawn as a layering violation. Measured on this repository on 2026-09-13,
over a warm full rebuild of the working tree's index: the view flagged **130**
of the 357 edges it could resolve a rank for, and the rule found against **0**.

The predicate the owner decided (RFC Q1) is the rule engine's: an edge inside
one layer is legal when both ends share a container the declaration gives a
layer, a finding when they do not, and an `exempt:` entry with a reason and an
exit condition can excuse one. The view no longer holds a predicate at all — it
asks the rule, through `flagged_layer_edges`, so the two sets cannot drift into
disagreement between releases.

The fixtures declare `tier-web` / `tier-core` / `tier-store`, a vocabulary
`src/` does not contain, and are written to disk and indexed by the real
reindex.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from beadloom.application.architecture_view import build_architecture_view_data
from beadloom.graph.rules.layer_edges import flagged_layer_edges
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerRule
from tests.acceptance.steps.tiered_project import (
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

#: One crossing of the peer-container fixture, excused by name, in one
#: direction only — so the opposite crossing stays reported and the test can
#: tell an exemption that was read from an exemption that silenced the rule.
_EXCUSING_LEDGER_API = (
    "    exempt:\n"
    "      - from: ledger-api\n"
    "        to: postings-api\n"
    '        reason: "the two read one ledger and the read seam is not built yet"\n'
    '        until: "2030-01-01"\n'
)


def _conn(project: Path) -> closing[sqlite3.Connection]:
    """A row-keyed handle on the project's index that closes itself."""
    conn = sqlite3.connect(project / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    return closing(conn)


def _rule_of(project: Path) -> LayerRule:
    """The layer rule the project declares, as the linter loads it."""
    return next(
        rule
        for rule in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(rule, LayerRule)
    )


def _view_verdicts(project: Path) -> dict[tuple[str, str], object]:
    """Each `depends_on` edge of the rendered view, with its `violation` value.

    A missing flag comes back as ``None`` rather than being dropped, because
    "the view said nothing about this edge" is one of the three answers and a
    test that could not see it would read an omission as a pass.
    """
    with _conn(project) as conn:
        data = build_architecture_view_data(conn, pages={})
    edges = [e for e in data["edges"] if isinstance(e, dict) and e.get("kind") == "depends_on"]
    return {(str(e["src"]), str(e["dst"])): e.get("violation") for e in edges}


def _view_flags(project: Path) -> set[tuple[str, str]]:
    return {edge for edge, verdict in _view_verdicts(project).items() if verdict is True}


def _rule_flags(project: Path) -> set[tuple[str, str]]:
    with _conn(project) as conn:
        return set(flagged_layer_edges(conn, _rule_of(project)))


@pytest.fixture()
def peer_containers(tmp_path: Path) -> Path:
    """Two domains in one tier, three edges: one internal and two crossings."""
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(tmp_path / "shop", nodes=nodes, edges=edges)


@pytest.fixture()
def peer_containers_with_an_exemption(tmp_path: Path) -> Path:
    """The same graph, with one of its two crossings excused by name."""
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(
        tmp_path / "shop", nodes=nodes, edges=edges, exempt=_EXCUSING_LEDGER_API
    )


@pytest.fixture()
def nested_parts(tmp_path: Path) -> Path:
    """Two containers in different tiers, each holding an untagged part."""
    nodes, edges = graph_with_nested_parts()
    return write_tiered_project(tmp_path / "shop", nodes=nodes, edges=edges)


class TestTheViewAsksTheRule:
    """What the view draws red is what `beadloom lint` reports, on a foreign graph."""

    def test_an_edge_between_two_parts_of_one_container_is_not_flagged(
        self, peer_containers: Path
    ) -> None:
        """The 116-edge class the old predicate drew as a violation.

        `ledger-api -> ledger-store` is a dependency between two parts of one
        domain. It points nowhere through the layers, and the view flagged it
        for exactly that reason: it stayed inside one.
        """
        assert _view_verdicts(peer_containers)[("ledger-api", "ledger-store")] is False

    def test_a_dependency_between_peers_in_one_layer_is_flagged(
        self, peer_containers: Path
    ) -> None:
        """Guard the guard: the agreement above is not the view flagging nothing."""
        assert ("ledger-api", "postings-api") in _view_flags(peer_containers)
        assert ("postings-api", "ledger-api") in _view_flags(peer_containers)

    def test_the_two_instruments_flag_the_same_edges(self, peer_containers: Path) -> None:
        assert _view_flags(peer_containers) == _rule_flags(peer_containers)

    def test_an_excused_crossing_is_not_flagged(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        """An `exempt:` entry reaches the view, or the site contradicts the Gate.

        The entry is carried to the view through the indexed rule, so this also
        asserts that reindex writes the exemptions a layer rule declares.
        """
        flags = _view_flags(peer_containers_with_an_exemption)
        assert ("ledger-api", "postings-api") not in flags
        assert ("postings-api", "ledger-api") in flags

    def test_the_two_instruments_agree_about_an_excused_crossing(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        assert _view_flags(peer_containers_with_an_exemption) == _rule_flags(
            peer_containers_with_an_exemption
        )

    def test_direction_is_still_judged_and_still_inherited(self, nested_parts: Path) -> None:
        """The half the two instruments already agreed on, held across the change."""
        verdicts = _view_verdicts(nested_parts)
        assert verdicts[("store-db", "web-api")] is True
        assert verdicts[("web-api", "store-db")] is False
        assert _view_flags(nested_parts) == _rule_flags(nested_parts)


@pytest.fixture()
def live(live_repo_reindexed: Path) -> Iterator[Path]:
    yield live_repo_reindexed


class TestOnThisRepository:
    """The done-when, taken on the graph the bead names."""

    def test_the_two_instruments_flag_the_same_edge_set(self, live: Path) -> None:
        assert _view_flags(live) == _rule_flags(live)

    def test_the_agreement_is_not_vacuous(self, live: Path) -> None:
        """Both sets are empty here, and that has to be a measurement.

        This repository's crossings were removed or excused by name in B2, so
        the agreement above would also hold if the view had stopped flagging
        anything at all. What makes it a measurement is the population: the view
        renders a verdict on the edges the rule judges, and that is most of
        them.
        """
        verdicts = _view_verdicts(live)
        decided = [edge for edge, verdict in verdicts.items() if verdict is not None]
        assert len(verdicts) > 300
        assert len(decided) > len(verdicts) * 9 // 10
        assert _view_flags(live) == set()
