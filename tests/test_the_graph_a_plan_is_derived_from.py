"""BDL-UX #261 — the rest of the population #257 named one member of.

`beadloom-0mdo.59` measured four artifacts shared by three beads of one wave
whose code scopes were disjoint, and `beadloom waves` reported `0
serialisations` over all three pairs. #257 covered the first of the four. This
module is the other three, and they are three shapes rather than one:

1. `.beadloom/_graph/services.yml` — THE GRAPH, which is what this plan derives
   its scopes FROM. A bead that adds a node writes the file the plan is computed
   from, and the node it adds is not in the graph the plan read. That
   self-reference is stated as a seventh shared medium, `graph-files`, with the
   one half of it a plan can OBSERVE as its check: whether the graph on disk is
   still the graph the index resolved these scopes from.
2. `tests/test_bead77_kind_and_root_disagree.py` — hand-maintained POPULATION
   LITERALS. Not a medium and not a serialisation: one derivable fact with two
   homes, whose answer is to remove the copy. Filed, not taken here.
3. `docs/services/components/cli-commands/DOC.md` — measured, and it is NOT the
   ancestor-document case the entry guessed at.
   `TestTheCliCommandsDocumentIsAnUndeclaredNode` is that measurement as an
   executable.

Two mechanisms are DECLINED here with the measurement that declines them, on the
`TestDocumentOwnershipCannotSerialiseAnything` precedent `beadloom-0mdo.75` set:
a serialisation keyed on the graph FILE a bead's declared nodes are defined in
(`TestTheGraphFileCannotSerialiseWithoutNoise`), and an ancestor-reaching
document statement (`TestAnAncestorReachingRuleIsSharedByEveryPair`). Each pin
carries the condition under which it goes red and the mechanism becomes worth
building.
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from beadloom.application.waves import (
    MEDIUM_GRAPH_FILES,
    SHARED_MEDIA,
    STATUS_FAILED,
    STATUS_PASSED,
    STATUS_UNMEASURED,
    BeadRecord,
    GraphFile,
    GraphInput,
    WaveEnvironment,
    check_media,
)

if TYPE_CHECKING:
    from beadloom.application.waves import MediumCheck

#: This repository's own graph, read the way every reader of that directory
#: reads it. The pins below are measurements OF this project, so they take it
#: from the tree rather than from a fixture.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_GRAPH_DIR = _REPO_ROOT / ".beadloom" / "_graph"


def _repo_graph_files() -> dict[str, list[dict[str, Any]]]:
    """Every graph file of this repository, mapped to the nodes it defines."""
    from beadloom.onboarding.graph_files import each_graph_file

    return {
        yml.name: list(data.get("nodes") or []) for yml, data in each_graph_file(_GRAPH_DIR)
    }


def _records(*bead_ids: str) -> list[BeadRecord]:
    """Beads that declare nothing — this check does not read a declaration."""
    return [BeadRecord(bead_id=bead, declaration="Do the work.") for bead in bead_ids]


def _check(environment: WaveEnvironment) -> MediumCheck:
    """The `graph-files` verdict under *environment*."""
    checks = check_media(_records("alpha"), environment=environment)
    return next(check for check in checks if check.medium == MEDIUM_GRAPH_FILES)


class TestTheGraphIsStatedAsASharedMedium:
    """It is shared by construction, so every wave says so."""

    def test_the_graph_is_a_medium_of_every_plan(self) -> None:
        named = {medium.name for medium in SHARED_MEDIA}
        assert MEDIUM_GRAPH_FILES in named

    def test_the_statement_names_the_self_reference_rather_than_leaving_it(self) -> None:
        medium = next(m for m in SHARED_MEDIA if m.name == MEDIUM_GRAPH_FILES)
        assert "#261" in medium.evidence
        assert "derive" in medium.statement or "derived" in medium.statement


class TestTheCheckOverThePlansOwnInput:
    """Whether the graph on disk is the graph these scopes were resolved from."""

    def test_a_graph_nobody_read_is_unmeasured_rather_than_clean(self) -> None:
        check = _check(WaveEnvironment())
        assert check.status == STATUS_UNMEASURED

    def test_a_project_with_no_graph_file_passes_and_says_so(self) -> None:
        check = _check(WaveEnvironment(graph_input=GraphInput()))
        assert check.status == STATUS_PASSED
        assert "no graph file" in check.detail

    def test_a_node_on_disk_the_index_does_not_hold_fails(self) -> None:
        check = _check(
            WaveEnvironment(
                graph_input=GraphInput(
                    files=(GraphFile(path=".beadloom/_graph/services.yml",
                                     nodes=("billing", "shipping")),),
                    indexed=frozenset({"billing"}),
                )
            )
        )
        assert check.status == STATUS_FAILED
        assert "shipping" in check.detail

    def test_a_node_the_index_holds_that_no_graph_file_declares_fails(self) -> None:
        check = _check(
            WaveEnvironment(
                graph_input=GraphInput(
                    files=(GraphFile(path=".beadloom/_graph/services.yml",
                                     nodes=("billing",)),),
                    indexed=frozenset({"billing", "shipping"}),
                )
            )
        )
        assert check.status == STATUS_FAILED
        assert "shipping" in check.detail

    def test_a_graph_that_matches_the_index_passes(self) -> None:
        check = _check(
            WaveEnvironment(
                graph_input=GraphInput(
                    files=(GraphFile(path=".beadloom/_graph/services.yml",
                                     nodes=("billing", "shipping")),),
                    indexed=frozenset({"billing", "shipping"}),
                )
            )
        )
        assert check.status == STATUS_PASSED

    def test_the_pass_states_the_half_no_plan_can_observe(self) -> None:
        """A bead that ADDS a node is invisible here, and the pass says so."""
        check = _check(
            WaveEnvironment(
                graph_input=GraphInput(
                    files=(GraphFile(path=".beadloom/_graph/services.yml",
                                     nodes=("billing", "shipping")),),
                    indexed=frozenset({"billing", "shipping"}),
                )
            )
        )
        assert "2 node(s)" in check.detail
        assert "1 graph file(s)" in check.detail
        assert "adds" in check.detail

    def test_the_pass_names_the_file_every_node_adding_bead_writes(self) -> None:
        check = _check(
            WaveEnvironment(
                graph_input=GraphInput(
                    files=(
                        GraphFile(path=".beadloom/_graph/a.yml", nodes=("billing",)),
                        GraphFile(path=".beadloom/_graph/b.yml", nodes=("shipping", "ops")),
                    ),
                    indexed=frozenset({"billing", "shipping", "ops"}),
                )
            )
        )
        assert check.status == STATUS_PASSED
        assert ".beadloom/_graph/b.yml" in check.detail


class TestTheGraphFileCannotSerialiseWithoutNoise:
    """The entry's own suggestion, measured before it was built rather than after.

    BDL-UX #261 sketched a serialisation over "the graph FILE a bead's declared
    nodes are defined in". Measured on this repository it fires on EVERY pair,
    because one file holds every node — which collapses every wave to a wave of
    one, the failure mode BDL-UX #245 is already open about, against a real write
    rate of 8 of the 55 commits this epic's branch carries.

    **When this goes red the mechanism becomes worth building.** A project whose
    graph is split across files gives two node-adding beads two different files,
    and then the serialisation says something a wave can act on.
    """

    def test_every_node_of_this_project_is_defined_in_one_file(self) -> None:
        files = _repo_graph_files()
        holding_nodes = {name: nodes for name, nodes in files.items() if nodes}
        assert len(holding_nodes) == 1

    def test_the_serialisation_would_fire_on_every_pair_of_this_project(self) -> None:
        file_of: dict[str, str] = {
            str(node["ref_id"]): name
            for name, nodes in _repo_graph_files().items()
            for node in nodes
            if isinstance(node, dict) and node.get("ref_id")
        }
        refs = sorted(file_of)
        pairs = list(itertools.combinations(refs, 2))
        shared = [pair for pair in pairs if file_of[pair[0]] == file_of[pair[1]]]
        assert len(shared) == len(pairs)


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
        data = yaml.safe_load((_GRAPH_DIR / "services.yml").read_text(encoding="utf-8"))
        return {
            str(edge["src"]): str(edge["dst"])
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
