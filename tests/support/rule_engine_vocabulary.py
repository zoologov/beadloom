"""The rule engine's shared step vocabulary: one wording, one meaning, in every feature.

BDL-074 E1. Before this module the four layer features each defined "a project whose
layering is declared as three tiers" and "the project is linted" for themselves, and
two of the copies meant different graphs. A phrase now has one definition, here, and
a step module that wants it says so by calling one of the two functions below at
import time:

* :func:`use_findings_vocabulary` — what a reader can see of any rule's run: that it
  checked nothing, or did not, and the severity that report reaches them with. The
  step module keeps an ``outcome`` fixture whose ``run`` its When step sets.
* :func:`use_doc_area_vocabulary` — the ``doc_area_coherence`` rule, evaluated over a
  :class:`~tests.support.rule_engine_driver.DocPlacements` the step module keeps as
  ``placements``, and the one verdict two features read off it.
* :func:`use_layered_project_vocabulary` — the layer rule's projects, the ways they
  are judged, and what the judgement says. The step module keeps a
  ``layered_project`` fixture (a :class:`~tests.support.rule_engine_driver.LayeredProject`)
  and an ``outcome`` fixture returning the same object.

**Why a function and not a module of step definitions.** ``pytest-bdd`` registers a
step as a fixture in the module that defines it, so a step defined here would be
visible only here. Each function registers its steps into the CALLER's module
(``stacklevel=2``), which is ``pytest-bdd``'s own mechanism for exactly this.

The steps say what; :mod:`tests.support.rule_engine_driver` says how.

**Why it lives in ``tests/support/`` and not in ``steps/common/``.** ``steps/common/``
holds the step MODULES that load features of two or more nodes. This is not a step
module — it loads no feature — but a helper several step modules import, and the
suite's lock (``tests/self_check/architecture/test_the_suite_shares_helpers_through_support.py``)
admits an import of a suite module only from ``tests/support/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_bdd import given, parsers, then, when

from tests.support.rule_engine_driver import DEFAULT_EXEMPTION_REASON, DocPlacements
from tests.support.tiered_project import (
    TIERS,
    graph_with,
    graph_with_a_deeper_nest,
    graph_with_a_part_that_declares_its_own_tier,
    graph_with_nested_parts,
    graph_with_peer_containers,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.support.rule_engine_driver import LayeredProject, Outcome, RuleRun
    from tests.support.tiered_project import Edge, Node

#: The tiered shapes a scenario can name, each by the words a reader would use.
SHAPES: dict[str, Callable[[], tuple[list[Node], list[Edge]]]] = {
    "two containers in different tiers": graph_with_nested_parts,
    "two peer containers in one tier": graph_with_peer_containers,
    "parts two part_of generations below their tagged container": graph_with_a_deeper_nest,
    "parts two generations down under a tagged middle container": (
        lambda: graph_with_a_deeper_nest(middle_tag=TIERS[2])
    ),
    "a part carrying a tier its container does not": (
        graph_with_a_part_that_declares_its_own_tier
    ),
}

#: A layering with one edge that runs the wrong way: ``store -> web`` is bottom-up
#: under ``enforce: top-down``, so the rule has something to decide.
ONE_EDGE_UP_THE_TIERS: tuple[list[Node], list[Edge]] = (
    [
        ("ledger", "service", []),
        ("web", "domain", ["tier-web"]),
        ("core", "domain", ["tier-core"]),
        ("store", "domain", ["tier-store"]),
    ],
    [
        ("web", "ledger", "part_of"),
        ("core", "ledger", "part_of"),
        ("store", "ledger", "part_of"),
        ("web", "core", "depends_on"),
        ("core", "store", "depends_on"),
        ("store", "web", "depends_on"),
    ],
)


class _HasRun:
    """What the findings vocabulary reads: anything carrying the last ``run``."""

    run: RuleRun


def use_findings_vocabulary() -> None:
    """Register the steps any rule's run is read by, into the calling step module."""

    @then("the rule reports that it checked nothing", stacklevel=2)
    def _checked_nothing(outcome: _HasRun) -> None:
        liveness = outcome.run.liveness()
        assert len(liveness) == 1, f"expected one stand-down report, got {liveness}"
        assert "checked nothing" in liveness[0].message, liveness[0].message

    @then("the rule does not report that it checked nothing", stacklevel=2)
    def _did_not_stand_down(outcome: _HasRun) -> None:
        assert outcome.run.liveness_messages() == [], outcome.run.liveness_messages()

    @then(parsers.parse('that report carries the severity "{severity}"'), stacklevel=2)
    def _report_severity(outcome: _HasRun, severity: str) -> None:
        liveness = outcome.run.liveness()
        assert liveness, "no stand-down report to carry a severity"
        assert [v.severity for v in liveness] == [severity] * len(liveness)


def use_layered_project_vocabulary() -> None:
    """Register the layer rule's Given/When/Then steps into the calling step module."""

    # -- Given: the layering and the graph ------------------------------------

    @given("a project whose layering is declared as three tiers", stacklevel=2)
    def _three_tiers(layered_project: LayeredProject) -> None:
        layered_project.declare_tiers(TIERS)

    @given(
        parsers.parse(
            "{tiered:d} dependency edges between tiered nodes and {untiered:d} "
            "with an untiered end"
        ),
        stacklevel=2,
    )
    def _counted_graph(layered_project: LayeredProject, tiered: int, untiered: int) -> None:
        layered_project.use_graph(*graph_with(tiered_edges=tiered, untiered_edges=untiered))

    @given("one dependency running up the tiers", stacklevel=2)
    def _one_edge_up(layered_project: LayeredProject) -> None:
        layered_project.use_graph(*ONE_EDGE_UP_THE_TIERS)

    @given(parsers.parse("a project with {shape}"), stacklevel=2)
    def _shaped(layered_project: LayeredProject, shape: str) -> None:
        if shape == "dependencies derived only from Python imports":
            layered_project.derive_edges_from_imports()
            return
        layered_project.use_graph(*SHAPES[shape]())

    @given(parsers.parse('the rule excuses "{src} -> {dst}" until "{until}"'), stacklevel=2)
    def _excused(layered_project: LayeredProject, src: str, dst: str, until: str) -> None:
        layered_project.excuse(src, dst, until=until, reason=DEFAULT_EXEMPTION_REASON)

    @given(parsers.parse('the rule excuses "{src} -> {dst}" with no reason'), stacklevel=2)
    def _excused_without_reason(layered_project: LayeredProject, src: str, dst: str) -> None:
        layered_project.excuse(src, dst, until="2030-01-01", reason=None)

    # -- When: the one thing that happens -------------------------------------

    @when("the project is linted", stacklevel=2)
    def _lint(layered_project: LayeredProject) -> None:
        layered_project.lint()

    @when("the project is linted with the flag that fails on warnings", stacklevel=2)
    def _lint_failing_on_warnings(layered_project: LayeredProject) -> None:
        layered_project.lint_cli("--fail-on-warn")

    @when("the evaluators are called the way a reader past lint calls them", stacklevel=2)
    def _evaluate_without_lint(layered_project: LayeredProject) -> None:
        layered_project.evaluate_without_lint()

    # -- Then: what the judgement says ----------------------------------------

    @then(parsers.parse('"{src} -> {dst}" is reported as a layering violation'), stacklevel=2)
    def _a_violation(layered_project: LayeredProject, src: str, dst: str) -> None:
        pairs = layered_project.run.layer_pairs()
        assert (src, dst) in pairs, pairs

    @then(parsers.parse('"{src} -> {dst}" is reported as a same-layer crossing'), stacklevel=2)
    def _a_crossing(layered_project: LayeredProject, src: str, dst: str) -> None:
        findings = layered_project.run.layer_findings()
        crossing = [
            v
            for v in findings
            if (v.from_ref_id, v.to_ref_id) == (src, dst) and "Same-layer crossing" in v.message
        ]
        assert len(crossing) == 1, [v.message for v in findings]

    @then(parsers.parse('no finding names "{src} -> {dst}"'), stacklevel=2)
    def _not_named(layered_project: LayeredProject, src: str, dst: str) -> None:
        assert (src, dst) not in layered_project.run.layer_pairs()

    @then("no finding is a layering violation", stacklevel=2)
    def _nothing_decided(layered_project: LayeredProject) -> None:
        assert layered_project.run.layer_findings() == []

    @then(
        parsers.parse('the finding says that layer was inherited from "{container}"'),
        stacklevel=2,
    )
    def _inherited_from(layered_project: LayeredProject, container: str) -> None:
        messages = [v.message for v in layered_project.run.layer_findings()]
        assert any(f"inherited from '{container}'" in m for m in messages), messages

    @then(
        parsers.parse(
            "the run states that it evaluated {evaluated:d} of {total:d} dependency edges"
        ),
        stacklevel=2,
    )
    def _states_evaluated(layered_project: LayeredProject, evaluated: int, total: int) -> None:
        [statement] = layered_project.run.population_statements()
        assert f"evaluated {evaluated} of {total} live `depends_on` edge(s)" in statement.message
        reach = layered_project.reach()
        assert (reach.population.evaluated, reach.population.total) == (evaluated, total)

    @then(
        parsers.parse(
            "it states that it skipped {skipped:d} for an end carrying no declared layer"
        ),
        stacklevel=2,
    )
    def _states_skipped(layered_project: LayeredProject, skipped: int) -> None:
        [statement] = layered_project.run.population_statements()
        assert f"skipped {skipped} for an end in no declared layer" in statement.message
        assert layered_project.reach().population.skipped_untagged == skipped

    @then("the run makes no statement about its population", stacklevel=2)
    def _no_statement(layered_project: LayeredProject) -> None:
        assert layered_project.run.population_statements() == []

    @then(
        parsers.parse("the layer rule's reach is {evaluated:d} of {total:d} dependency edges"),
        stacklevel=2,
    )
    def _reach(layered_project: LayeredProject, evaluated: int, total: int) -> None:
        population = layered_project.reach().population
        assert (population.evaluated, population.total) == (evaluated, total)
        assert population.skipped_untagged == total - evaluated

    @then(parsers.parse("the command exits {code:d}"), stacklevel=2)
    def _exit_code(layered_project: LayeredProject, code: int) -> None:
        assert layered_project.run.exit_code == code, layered_project.run.output


def use_doc_area_vocabulary() -> None:
    """Register the ``doc_area_coherence`` steps into the calling step module."""

    @when("the doc-area-coherence rule is evaluated", stacklevel=2)
    def _evaluate(placements: DocPlacements, outcome: Outcome) -> None:
        outcome.run = placements.evaluate()

    @then("no node is reported", stacklevel=2)
    def _none_reported(outcome: Outcome) -> None:
        named = DocPlacements.reported(outcome.run)
        assert named == [], f"the rule reported {named}"

    @then("no node is reported as misplaced", stacklevel=2)
    def _none_misplaced(outcome: Outcome) -> None:
        assert DocPlacements.reported(outcome.run) == []
