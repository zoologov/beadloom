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

from typing import TYPE_CHECKING

import pytest

from tests.support.layer_rule import rule_flags, view_flags, view_verdicts
from tests.support.tiered_project import (
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
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
        assert view_verdicts(peer_containers)[("ledger-api", "ledger-store")] is False

    def test_a_dependency_between_peers_in_one_layer_is_flagged(
        self, peer_containers: Path
    ) -> None:
        """Guard the guard: the agreement above is not the view flagging nothing."""
        assert ("ledger-api", "postings-api") in view_flags(peer_containers)
        assert ("postings-api", "ledger-api") in view_flags(peer_containers)

    def test_the_two_instruments_flag_the_same_edges(self, peer_containers: Path) -> None:
        assert view_flags(peer_containers) == rule_flags(peer_containers)

    def test_an_excused_crossing_is_not_flagged(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        """An `exempt:` entry reaches the view, or the site contradicts the Gate.

        The entry is carried to the view through the indexed rule, so this also
        asserts that reindex writes the exemptions a layer rule declares.
        """
        flags = view_flags(peer_containers_with_an_exemption)
        assert ("ledger-api", "postings-api") not in flags
        assert ("postings-api", "ledger-api") in flags

    def test_the_two_instruments_agree_about_an_excused_crossing(
        self, peer_containers_with_an_exemption: Path
    ) -> None:
        assert view_flags(peer_containers_with_an_exemption) == rule_flags(
            peer_containers_with_an_exemption
        )

    def test_direction_is_still_judged_and_still_inherited(self, nested_parts: Path) -> None:
        """The half the two instruments already agreed on, held across the change."""
        verdicts = view_verdicts(nested_parts)
        assert verdicts[("store-db", "web-api")] is True
        assert verdicts[("web-api", "store-db")] is False
        assert view_flags(nested_parts) == rule_flags(nested_parts)


