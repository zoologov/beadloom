"""Self-checks of this repository's documents and published site (BDL-074 A3).

Moved out of ``tests/test_bead15_s3b_coverage.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from beadloom.onboarding.graph_files import each_graph_file
from beadloom.services.cli import main
from tests.test_bead15_s3b_coverage import (
    _no_baseline_skip_reason,
    _pairs_have_no_freshness_baseline,
)

if TYPE_CHECKING:
    from pathlib import Path


def _load_real_nodes(root: Path) -> dict[str, dict[str, object]]:
    """Load *root*'s graph DIRECTORY's nodes into ``{ref_id: node_dict}`` (no DB).

    *root* is the self-check snapshot, so the nodes are read from the same copy
    whose index the caller reads (BDL-074 A2).

    The directory rather than one file since BDL-UX #265 split this repository's
    graph into one file per node. `each_graph_file` owns the codec and the skip
    policy, so neither is restated here.
    """
    nodes: dict[str, dict[str, object]] = {}
    for _path, data in each_graph_file(root / ".beadloom" / "_graph"):
        for node in data.get("nodes") or []:
            if isinstance(node, dict) and node.get("ref_id"):
                nodes[str(node["ref_id"])] = node
    return nodes


#: The nodes whose SPEC/DOC pair this file holds to freshness. A tuple rather
#: than a set literal inside the test, because the guard tests below assert that
#: the population is non-empty and the sample is the thing they name.
_FRESHNESS_SAMPLE = frozenset(
    {
        "code-indexer",
        "route-extraction",
        "test-mapping",
        "sync-check",
        "snapshot",
        "ci-gate",
        "config-check",
        "branch-protection",
        "site-generation",
        "graph-loader",
        "contracts",
        "sdl",
        "context-builder",
        "doc-indexer",
        "db",
        "git-activity",
        "health",
        "mcp-tools",
        "bd-seam",
    }
)


@pytest.fixture(scope="module")
def live_sync_pairs(self_check_snapshot: Path) -> list[dict[str, object]]:
    """Every pair ``sync-check`` reports for this checkout, read once per module.

    Module-scoped because the command walks 449 pairs over the real tree and
    three tests ask it the same question; a per-test invocation was ~5 s of the
    file's runtime for an answer that cannot change between them.

    TWO EXIT CODES ARE ANSWERS AND ONE IS NOT. ``sync-check`` exits 2 when a
    blocking pair exists and emits the same JSON it emits at 0, so demanding 0
    here pre-empted the freshness assertion with the raw CLI dump instead of
    naming the stale pair -- measured on this tree, where a neighbour's
    untracked module made both cases in this class fail on the exit code rather
    than on what they check. Exit 1 IS refused: it means no database or an
    invalid ref, and there is no payload behind it.
    """
    result = CliRunner().invoke(
        main, ["sync-check", "--json", "--project", str(self_check_snapshot)]
    )
    assert result.exit_code in {0, 2}, (
        f"sync-check exited {result.exit_code}, which is neither clean (0) nor "
        f"blocking (2), so it reported no pairs to read:\n{result.output}"
    )
    pairs: list[dict[str, object]] = json.loads(result.stdout)["pairs"]
    return pairs


class TestSyncCheckNewPairs:
    """The new SPEC/DOC skeletons are tracked by sync-check and currently fresh."""

    def test_new_node_docs_are_tracked_pairs(
        self, live_sync_pairs: list[dict[str, object]], self_check_snapshot: Path
    ) -> None:
        """Each new node's SPEC/DOC appears as a tracked sync-check pair."""
        nodes = _load_real_nodes(self_check_snapshot)
        tracked_refs = {str(p["ref_id"]) for p in live_sync_pairs}
        sample = (
            "code-indexer",
            "sync-check",
            "ci-gate",
            "site-generation",
            "db",
            "graph-loader",
            "bd-seam",
        )
        for ref_id in sample:
            assert ref_id in nodes
            assert ref_id in tracked_refs, f"{ref_id} not tracked by sync-check"

    def test_all_new_node_pairs_are_fresh(self, live_sync_pairs: list[dict[str, object]]) -> None:
        """None of the new node SPEC/DOC pairs are stale, where freshness is knowable.

        BDL-UX #258, and the reason this test states its environment instead of
        failing in one. It CANNOT pass in a clean room — measured at ``6a55d5cc``
        with zero carried files, 444 of 448 pairs came back
        ``unverified/no_baseline`` — and it was the only failure in a 9 445-test
        run there. So "one failure, the expected one" became the shape of a
        CORRECT clean-room verdict across roughly thirty reports, and a SECOND
        failure had to be noticed against a background that already held one.
        ``beadloom-0mdo.41`` and ``.61`` each re-ran their extra failure at HEAD
        in a control room to prove it was not theirs; that is the tax.

        The population was counted before this was chosen rather than inferred
        from the reports: ONE test fails in a room, and ~40 of the 59 that skip
        there already declare a checkout property in their reason. This joins
        them instead of staying the exception nobody reads.

        The check keeps its bite: the skip is decided by the ``baseline`` field
        alone, so any checkout that CAN compare still fails on a stale pair.
        """
        sampled = [p for p in live_sync_pairs if str(p["ref_id"]) in _FRESHNESS_SAMPLE]
        assert sampled, (
            "sync-check reported no pair for any of the sampled ref ids, so this "
            "check is green about nothing. Either the sample names nodes the "
            f"graph no longer has ({sorted(_FRESHNESS_SAMPLE)}) or sync-check "
            "tracked no pair at all."
        )
        if _pairs_have_no_freshness_baseline(sampled):
            pytest.skip(_no_baseline_skip_reason(sampled))
        stale = [p for p in sampled if p["status"] != "ok"]
        assert stale == [], stale


class TestTheFreshnessSkipIsDecidedByTheBaseline:
    """The skip above must fire in a room and in no other checkout.

    A skip is the cheapest way to make a check quiet, so the decision behind
    this one is a function with its own cases rather than a condition nobody
    exercises. Every case here is synthetic: the point is which shapes of
    ``sync-check`` output license a skip, and that question needs no tree.
    """


    def test_every_live_pair_reports_the_baseline_the_decision_reads(
        self, live_sync_pairs: list[dict[str, object]]
    ) -> None:
        """The real output carries the field, so the decision is never guessing.

        Asserted against the tree rather than a fixture because the risk is that
        ``sync-check`` stops emitting ``baseline`` — which no synthetic pair of
        ours would ever notice.
        """
        without = [p for p in live_sync_pairs if not isinstance(p.get("baseline"), str)]

        assert without == [], without
        assert live_sync_pairs, "sync-check reported no pairs for this checkout"
