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

Two mechanisms were DECLINED here with the measurement that declines them, on the
`TestDocumentOwnershipCannotSerialiseAnything` precedent `beadloom-0mdo.75` set:
a serialisation keyed on the graph FILE a bead's declared nodes are defined in,
and an ancestor-reaching document statement
(`TestAnAncestorReachingRuleIsSharedByEveryPair`). Each pin carries the condition
under which it goes red and the mechanism becomes worth reconsidering.

THE FIRST PIN FIRED, AND THE ANSWER IT UNLOCKED WAS STILL NO.
`TestTheGraphFileCannotSerialiseWithoutNoise` asserted that one file held every
one of this project's 100 nodes and would go red on a graph split across files.
`beadloom-0mdo.80` (BDL-UX #265) split it, so it went red as designed. It is not
restated here, because the answer that replaced it belongs with the layout that
produced it: `tests/integration/onboarding/graph_layout/test_the_graph_is_one_file_per_node.py`
`TestTheSplitMakesTheSerialisationRedundantRatherThanMeaningful` measures that one
node per file makes the node-to-file map INJECTIVE, so the serialisation fires
exactly when two beads declare the same node — which `conflict_between` already
reports as `shared_node`. Keeping a second copy of that measurement here would be
one derivable fact with two homes, which is the defect entry 2 below is about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


