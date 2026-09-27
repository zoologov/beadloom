"""Self-checks of this repository's graph, rules and code structure (BDL-074 A3).

Moved out of
``tests/integration/graph/rules/test_the_layer_rule_states_the_population_it_judged.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from beadloom.graph import rules
from beadloom.graph.linter import lint
from beadloom.graph.loader import get_node_tags
from beadloom.graph.rules import evaluators
from beadloom.graph.rules.evaluators import (
    evaluate_cardinality_rules,
    evaluate_deny_rules,
    evaluate_layer_rules,
    evaluate_require_rules,
)
from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    layer_rule_reach,
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import node_tags
from beadloom.graph.rules.types import (
    CardinalityRule,
    DenyRule,
    LayerRule,
    RequireRule,
    Violation,
)
from tests.support.layer_rule import (
    DDD_LAYERS,
    ddd_layer_rule,
)
from tests.support.the_lint_path_before_release_a import (
    ClosureTags,
    comparable,
    decisions,
    layer_findings_before_release_a,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from beadloom.graph.rules import Rule


@pytest.fixture(scope="session")
def live_graph(self_check_snapshot: Path) -> Iterator[sqlite3.Connection]:
    """A read-only handle on this repository's own indexed graph."""
    db_path = self_check_snapshot / ".beadloom" / "beadloom.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def live_rules(self_check_snapshot: Path) -> list[Rule]:
    """This repository's declared rules, as the linter loads them."""
    return load_rules(self_check_snapshot / ".beadloom" / "_graph" / "rules.yml")


class TestTheReachIsReadableWithoutRunningTheRule:
    """`layer_rule_reach` — the numbers, for the readers that render them (A3/A4)."""

    def test_on_this_repository_the_rule_now_reaches_almost_every_edge(
        self, live_graph: sqlite3.Connection
    ) -> None:
        """The measurement this epic exists for, taken from the code rather than quoted.

        16 of 362 at `aa4bfad4` by own tags; the figure below is what the rule
        decides on since `beadloom-ku26`.
        """
        reach = layer_rule_reach(live_graph, ddd_layer_rule())
        assert reach.population.total > 300
        assert reach.population.evaluated > reach.population.total * 9 // 10


class TestWhatTheDecisionsChangedTo:
    """The layer rule decides more than it did, and exactly this much more.

    Release A moved no verdict and this module held that. BDL-070 B3
    (`beadloom-ku26`) is the release that moves one, so the claim becomes a
    differential with a stated content rather than an empty one: against the
    same transcription of the pre-Release-A evaluator, what is added is the
    edges an end's `part_of` container brought into the population.
    """

    def test_on_this_repository_under_its_own_declaration_nothing_moves(
        self, live_graph: sqlite3.Connection, live_rules: list[Rule]
    ) -> None:
        """Not neutrality by construction, and not a property of the predicate.

        This repository's own `rules.yml` is read here rather than `ddd_layer_rule()`.
        Two beads ran before this one so that this would hold: `beadloom-46am`
        removed the single edge running from a domain into the application
        layer, and `beadloom-xmfs` excused every same-layer crossing left, each
        by name with a reason and an exit condition. The test asserts that work
        held on the graph rather than in a report of it.
        """
        rules = [rule for rule in live_rules if isinstance(rule, LayerRule)]
        assert rules, "this repository declares a layer rule"
        assert decisions(evaluate_layer_rules(live_graph, rules)) == comparable(
            layer_findings_before_release_a(live_graph, rules)
        )

    def test_the_same_graph_without_those_exemptions_reports_exactly_them(
        self, live_graph: sqlite3.Connection, live_rules: list[Rule]
    ) -> None:
        """The differential above is over a set that is NOT empty by nature.

        `ddd_layer_rule()` is this repository's layering with its `exempt:` block left
        off. Every crossing it then reports must be one the rules file excuses,
        and every entry must excuse one — an entry that excused nothing would be
        a reason written for an edge that is not there. The comparison is a set
        of pairs and not a count, so it does not have to be rewritten when the
        number moves; the entries name literal ref_ids on this repository.
        """
        declared = next(rule for rule in live_rules if isinstance(rule, LayerRule))
        added = comparable(evaluate_layer_rules(live_graph, [ddd_layer_rule()])) - comparable(
            layer_findings_before_release_a(live_graph, [ddd_layer_rule()])
        )
        crossings = {(entry[5], entry[6]) for entry in added if entry[1] == "layer"}
        assert crossings == {
            (exemption.from_glob, exemption.to_glob) for exemption in declared.exempt
        }

    def test_no_node_carries_two_declared_layer_tags(self, live_graph: sqlite3.Connection) -> None:
        """The condition under which the pre-change hash-order answer was unambiguous.

        The old body took the first declared tag it met while iterating a
        node's tag `set`; the shared lookup takes the topmost DECLARED one. The
        two agree exactly while no node carries two, which is a fact about this
        graph and is asserted here so the differential above is a derivation
        rather than a coincidence.
        """
        declared = {layer.tag for layer in DDD_LAYERS}
        for row in live_graph.execute("SELECT ref_id, extra FROM nodes"):
            raw = row[1]
            if raw is None:
                continue
            carried = declared & set(json.loads(str(raw)).get("tags", []))
            assert len(carried) <= 1, f"{row[0]} carries {sorted(carried)}"

    def test_under_its_own_declaration_the_only_addition_is_the_population_statement(
        self, live_graph: sqlite3.Connection, live_rules: list[Rule]
    ) -> None:
        """Stated as a set difference, so a second addition could not hide in it."""
        rules = [rule for rule in live_rules if isinstance(rule, LayerRule)]
        added = comparable(evaluate_layer_rules(live_graph, rules)) - comparable(
            layer_findings_before_release_a(live_graph, rules)
        )
        assert {entry[1] for entry in added} == {LAYER_POPULATION_RULE_TYPE}


class TestTheWholeLintRunIsUnchanged:
    """`lint --strict` on this repository, taken twice in one process.

    Still true after BDL-070 B3, and no longer true by construction: the rule
    now judges 357 of this repository's 365 live `depends_on` edges where it
    judged 16, and the verdict does not move because `beadloom-46am` and
    `beadloom-xmfs` disposed of everything it newly reaches.

    The comparison is not against a recorded baseline. A baseline of this
    repository's 70 findings would rot on the next bead — `scenario-coverage`
    states `483 scenarios in 71 files` in forty of them, so adding one
    `.feature` file rewrites forty messages — and a test that has to be
    regenerated to stay green is a test nobody reads. Instead the pre-change
    code path is reconstructed here (the layer evaluator as it stood at
    `a8c306d8`, and the tag closure it replaced) and run against the same index
    in the same process, so both sides always see the same repository.
    """

    def _lint(self, project_root: Path) -> list[Violation]:
        return lint(project_root).violations

    def test_the_findings_are_identical_apart_from_the_population_statement(
        self, self_check_snapshot: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        after = self._lint(self_check_snapshot)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        before = self._lint(self_check_snapshot)
        assert comparable(before), "a comparison over an empty findings list proves nothing"
        assert decisions(after) == comparable(before)

    def test_the_one_addition_is_the_population_statement(
        self, self_check_snapshot: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stated as a difference, so a second addition could not hide behind the first."""
        after = self._lint(self_check_snapshot)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        added = comparable(after) - comparable(self._lint(self_check_snapshot))
        assert {entry[1] for entry in added} == {LAYER_POPULATION_RULE_TYPE}
        assert {entry[2] for entry in added} == {"warn"}

    def test_the_addition_moves_no_error_count(
        self, self_check_snapshot: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """What `lint --strict` and the Gate decide on is the error count alone."""
        after = lint(self_check_snapshot)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        before = lint(self_check_snapshot)
        assert after.error_count == before.error_count
        assert after.has_errors is before.has_errors
        assert after.rules_inert == before.rules_inert
        assert after.warning_count == before.warning_count + 1


class TestTheOtherFourRuleKindsAreUnchanged:
    """The shared tag lookup answers what the five closures answered."""

    def test_the_lookup_agrees_with_get_node_tags_for_every_node(
        self, live_graph: sqlite3.Connection
    ) -> None:
        lookup = node_tags(live_graph)
        ref_ids = [str(row[0]) for row in live_graph.execute("SELECT ref_id FROM nodes")]
        assert ref_ids
        for ref_id in ref_ids:
            assert lookup.of(ref_id) == get_node_tags(live_graph, ref_id)

    def test_a_node_the_graph_does_not_hold_has_no_tags(
        self, live_graph: sqlite3.Connection
    ) -> None:
        assert node_tags(live_graph).of("no-such-node") == set()

    @pytest.mark.parametrize(
        ("rule_class", "evaluate"),
        [
            (DenyRule, evaluate_deny_rules),
            (RequireRule, evaluate_require_rules),
            (CardinalityRule, evaluate_cardinality_rules),
        ],
    )
    def test_their_findings_match_the_closure_they_replaced(
        self,
        live_graph: sqlite3.Connection,
        live_rules: list[Rule],
        rule_class: type,
        evaluate: Callable[[sqlite3.Connection, list[Rule]], list[Violation]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Run on this repository's declared rules, against both tag sources."""
        selected = [rule for rule in live_rules if isinstance(rule, rule_class)]
        assert selected, f"this repository declares no {rule_class.__name__}"
        with_shared = comparable(evaluate(live_graph, selected))
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        with_closure = comparable(evaluate(live_graph, selected))
        assert with_shared == with_closure
