"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of ``tests/test_the_graph_a_plan_is_derived_from.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.repository_root import REPO_ROOT as _REPO_ROOT

#: This repository's own graph, read the way every reader of that directory
#: reads it. The pins below are measurements OF this project, so they take it
#: from the tree rather than from a fixture.


_GRAPH_DIR = _REPO_ROOT / ".beadloom" / "_graph"


def _repo_graph_files() -> dict[str, list[dict[str, Any]]]:
    """Every graph file of this repository, mapped to the nodes it defines."""
    from beadloom.onboarding.graph_files import each_graph_file

    return {
        yml.name: list(data.get("nodes") or []) for yml, data in each_graph_file(_GRAPH_DIR)
    }


class TestAnAncestorReachingRuleIsSharedByEveryPair:
    """The calibration BDL-UX #261 said had to be made before building anything.

    The entry proposed reporting an ANCESTOR-reaching document statement for the
    third artifact. Measured on this repository's own graph: every node reaches
    the root service `beadloom` through `part_of`, so a rule that reaches an
    ancestor's documents is shared by every pair of every wave and reports the
    same three documents each time. That is noise, not a finding.

    It goes red on a graph with more than one root, or on one where some node
    reaches no root — which is when an ancestor rule can distinguish a pair.
    """

    @staticmethod
    def _part_of() -> dict[str, str]:
        # The DIRECTORY, not one file: `beadloom-0mdo.80` split this graph into
        # one file per node, and every edge went with the node its `src` names.
        from beadloom.onboarding.graph_files import each_graph_file

        return {
            str(edge["src"]): str(edge["dst"])
            for _yml, data in each_graph_file(_GRAPH_DIR)
            for edge in data.get("edges") or []
            if edge.get("kind") == "part_of" and edge.get("src") != edge.get("dst")
        }

    def test_every_node_reaches_the_same_root(self) -> None:
        parent = self._part_of()
        nodes = {
            str(node["ref_id"])
            for nodes_ in _repo_graph_files().values()
            for node in nodes_
            if isinstance(node, dict) and node.get("ref_id")
        }
        roots = set()
        for ref in nodes:
            seen: set[str] = set()
            cur = ref
            while cur in parent and cur not in seen:
                seen.add(cur)
                cur = parent[cur]
            roots.add(cur)
        assert roots == {"beadloom"}


class TestTheCliCommandsDocumentIsAnUndeclaredNode:
    """The third artifact is not an ancestor case, and this is the measurement.

    `docs/services/components/cli-commands/DOC.md` is owned by node
    `cli-commands`, whose `source` covers BOTH `services/commands/setup.py`
    (`beadloom-0mdo.59`) and `services/commands/waves.py` (`beadloom-0mdo.75`).
    Neither bead declared `cli-commands` — `.59` declared `config-check,
    role-composer, onboarding` and `.75` declared `wave-plan` — so
    `conflict_between` never had a ref to intersect. Had either declared it,
    `shared_node` would have fired. The plan already reports the gap as
    `unguarded_axis`, naming `cli-commands` among the approved nodes no bead of
    the wave declares.

    So no new mechanism is owed for it, and the pin is what says so: this goes
    red if the node stops owning either file or stops owning that document,
    which is when the reasoning above stops holding.
    """

    @staticmethod
    def _node(ref_id: str) -> dict[str, Any]:
        for nodes in _repo_graph_files().values():
            for node in nodes:
                if isinstance(node, dict) and node.get("ref_id") == ref_id:
                    return node
        pytest.fail(f"this project's graph has no node {ref_id!r}")

    def test_one_node_owns_both_beads_source_files_and_that_document(self) -> None:
        node = self._node("cli-commands")
        assert node["source"] == "src/beadloom/services/commands/"
        assert "docs/services/components/cli-commands/DOC.md" in node["docs"]
