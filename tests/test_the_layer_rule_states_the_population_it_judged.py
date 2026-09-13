"""The layer rule says how much of its edge set it looked at, and decides nothing new.

BDL-070 A2 (`beadloom-1ylk`). `architecture-layers` is this project's only
machine check that dependencies run in the declared direction, and it is
`severity: error`, so what it evaluates decides whether `main` — ours and every
adopter's — is mergeable. Measured on this repository at `aa4bfad4`: it judged
16 of 362 live `depends_on` edges, because it reads a node's OWN tags and skips
every edge whose ends carry none. The green line said `0 violations, 16 rules
evaluated` either way, so a reader could not tell 16 of 362 from 362 of 362.

This module holds two claims that pull in opposite directions and must both
hold:

- the rule now STATES that fraction, once per rule, in a finding the two
  readers that call the evaluators without `lint()` also receive;
- and its decisions are compared against a verbatim transcription of the
  pre-change evaluator, on this repository's own graph and on two graphs that
  are not it.

**The second claim was "nothing moved" and is now "this much moved."** Release A
of this epic changed no verdict. Release B does: since BDL-070 B3
(`beadloom-ku26`) an end takes its layer from the nearest `part_of` container
that declares one, so the differential against the transcription is no longer
empty and what it contains is asserted by name. On THIS repository it is still
empty under this repository's own declaration, and that is a fact about two
beads that ran first — `beadloom-46am` removed the one edge running upward and
`beadloom-xmfs` excused every same-layer crossing left — rather than a property
of the predicate. The same graph read without those exemptions reports them,
which is asserted beside it so the empty differential cannot be read as the
rule finding nothing.

The transcription of the pre-change path lives in
`tests/the_lint_path_before_release_a.py`, because A7 compares the whole
`lint()` run against the same oracle and two transcriptions of one function
are two things that can drift.

The five tag-cache closures the evaluators each kept are compared the same way:
the four rule kinds that are not the layer rule are run against the shared
lookup and against the closure it replaced, on this repository's real rules, and
their findings must agree as a set.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from beadloom.graph import rules
from beadloom.graph.linter import lint
from beadloom.graph.loader import get_node_tags
from beadloom.graph.rules import evaluators
from beadloom.graph.rules.evaluators import (
    evaluate_cardinality_rules,
    evaluate_deny_rules,
    evaluate_forbid_edge_rules,
    evaluate_layer_rules,
    evaluate_require_rules,
)
from beadloom.graph.rules.layer_reach import (
    LAYER_POPULATION_RULE_TYPE,
    layer_rule_reach,
)
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.node_tags import NodeTags, node_tags
from beadloom.graph.rules.types import (
    CardinalityRule,
    DenyRule,
    ForbidEdgeRule,
    LayerDef,
    LayerRule,
    NodeMatcher,
    RequireRule,
    Violation,
)
from beadloom.infrastructure.db import create_schema, open_db
from tests.the_lint_path_before_release_a import (
    ClosureTags,
    comparable,
    decisions,
    layer_findings_before_release_a,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from beadloom.graph.rules import Rule

REPO_ROOT = Path(__file__).resolve().parent.parent

#: This repository's own declaration, read from `.beadloom/_graph/rules.yml`.
DDD_LAYERS = (
    LayerDef(name="services", tag="layer-service"),
    LayerDef(name="application", tag="layer-application"),
    LayerDef(name="domains", tag="layer-domain"),
    LayerDef(name="infrastructure", tag="layer-infra"),
)


class _CountingConnection:
    """A connection that reports how many statements were run through it.

    `sqlite3.Connection.execute` cannot be reassigned, so the count is taken on
    a stand-in that forwards rather than by patching the real object.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.queries = 0

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.queries += 1
        return self._conn.execute(sql, *args)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Graphs that are not this repository
# ---------------------------------------------------------------------------


def _build_graph(
    db_path: Path,
    *,
    nodes: list[tuple[str, list[str]]],
    edges: list[tuple[str, str, str]],
) -> sqlite3.Connection:
    conn = open_db(db_path)
    create_schema(conn)
    for ref_id, tags in nodes:
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
            (ref_id, "feature", ref_id, json.dumps({"tags": tags})),
        )
    for src, dst, kind in edges:
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
            (src, dst, kind),
        )
    conn.commit()
    return conn


@pytest.fixture()
def nested_graph(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph whose layer tags sit on containers, not on the nodes that depend.

    Two components inside tagged domains, one `depends_on` edge between them
    that no own-tag reaches, and one edge between the tagged containers that
    does. This is the shape an adopter meets and this repository hides: every
    node here is either a container or inside one.
    """
    conn = _build_graph(
        tmp_path / "nested.db",
        nodes=[
            ("infra", ["layer-infra"]),
            ("core", ["layer-domain"]),
            ("core-bit", []),
            ("infra-bit", []),
        ],
        edges=[
            ("core", "infra", "depends_on"),
            ("core-bit", "core", "part_of"),
            ("infra-bit", "infra", "part_of"),
            ("infra-bit", "core-bit", "depends_on"),
        ],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def mixed_graph(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph the rule reaches part of: two edges judged, one it cannot reach.

    `core-bit` is judged through its container, which is what BDL-070 B3
    changed; `loose` is inside nothing and carries no tag, so it is in no
    declared layer at all and the edge from it is what the statement counts as
    skipped. Both halves are needed, because a statement that names only a
    numerator reads the same whatever the denominator is.
    """
    conn = _build_graph(
        tmp_path / "mixed.db",
        nodes=[
            ("infra", ["layer-infra"]),
            ("core", ["layer-domain"]),
            ("core-bit", []),
            ("loose", []),
        ],
        edges=[
            ("core", "infra", "depends_on"),
            ("core-bit", "core", "part_of"),
            ("core-bit", "infra", "depends_on"),
            ("loose", "core", "depends_on"),
        ],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def untagged_graph(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph that declares layers no node carries — the zero denominator."""
    conn = _build_graph(
        tmp_path / "untagged.db",
        nodes=[("a", []), ("b", []), ("c", [])],
        edges=[("a", "b", "depends_on"), ("b", "c", "depends_on")],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def fully_tagged_graph(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A graph in which the rule reaches every edge it was handed."""
    conn = _build_graph(
        tmp_path / "tagged.db",
        nodes=[("svc", ["layer-service"]), ("dom", ["layer-domain"])],
        edges=[("svc", "dom", "depends_on")],
    )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def live_graph(live_repo_reindexed: Path) -> Iterator[sqlite3.Connection]:
    """A read-only handle on this repository's own indexed graph."""
    db_path = live_repo_reindexed / ".beadloom" / "beadloom.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(scope="session")
def live_rules(live_repo_reindexed: Path) -> list[Rule]:
    """This repository's declared rules, as the linter loads them."""
    return load_rules(live_repo_reindexed / ".beadloom" / "_graph" / "rules.yml")


def _rule(
    *,
    severity: str = "error",
    edge_kind: str = "depends_on",
    allow_skip: bool = True,
) -> LayerRule:
    return LayerRule(
        name="architecture-layers",
        description="Services → application → domains → infrastructure — not reverse",
        layers=DDD_LAYERS,
        enforce="top-down",
        allow_skip=allow_skip,
        edge_kind=edge_kind,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# The population statement
# ---------------------------------------------------------------------------


class TestThePopulationStatement:
    """What the rule says about how much of its edge set it judged."""

    def _statements(self, violations: list[Violation]) -> list[Violation]:
        return [v for v in violations if v.rule_type == LAYER_POPULATION_RULE_TYPE]

    def test_it_names_both_the_evaluated_and_the_skipped_count(
        self, mixed_graph: sqlite3.Connection
    ) -> None:
        statements = self._statements(evaluate_layer_rules(mixed_graph, [_rule()]))
        assert len(statements) == 1
        message = statements[0].message
        assert "evaluated 2 of 3" in message
        assert "skipped 1" in message
        assert "no declared layer" in message

    def test_a_rule_that_reaches_every_edge_says_nothing(
        self, fully_tagged_graph: sqlite3.Connection
    ) -> None:
        """There is nothing the rule could not reach, so there is nothing to state."""
        assert self._statements(evaluate_layer_rules(fully_tagged_graph, [_rule()])) == []

    def test_a_graph_no_layer_tag_reaches_reports_its_zero_denominator_once(
        self, untagged_graph: sqlite3.Connection
    ) -> None:
        """Two unjudged edges, one statement — the count is per rule, not per edge."""
        statements = self._statements(evaluate_layer_rules(untagged_graph, [_rule()]))
        assert len(statements) == 1
        assert "0 of 2" in statements[0].message

    def test_no_edge_of_the_rules_kind_produces_no_statement(
        self, untagged_graph: sqlite3.Connection
    ) -> None:
        """An empty edge set is the liveness rule's subject, not this one's."""
        rule = _rule(edge_kind="uses")
        assert self._statements(evaluate_layer_rules(untagged_graph, [rule])) == []

    def test_it_is_a_warning_even_when_the_rule_is_declared_an_error(
        self, mixed_graph: sqlite3.Connection
    ) -> None:
        """A statement about a rule's reach is not a boundary breach."""
        statements = self._statements(evaluate_layer_rules(mixed_graph, [_rule()]))
        assert [v.severity for v in statements] == ["warn"]

    def test_a_graph_whose_containers_carry_the_layers_is_reached_whole(
        self, nested_graph: sqlite3.Connection
    ) -> None:
        """The shape Release A reported 1 of 2 on, and B3 judges both edges of.

        Every node here is either a container carrying a layer or inside one, so
        there is nothing left for the rule to pass over and nothing to state.
        """
        assert self._statements(evaluate_layer_rules(nested_graph, [_rule()])) == []

    def test_it_names_containment_as_a_way_to_be_judged(
        self, mixed_graph: sqlite3.Connection
    ) -> None:
        """The unjudged edge is actionable two ways, and the remediation says both."""
        statements = self._statements(evaluate_layer_rules(mixed_graph, [_rule()]))
        assert "part_of" in str(statements[0].remediation)

    def test_one_statement_per_rule(self, mixed_graph: sqlite3.Connection) -> None:
        rules = [_rule(), _rule(allow_skip=False)]
        statements = self._statements(evaluate_layer_rules(mixed_graph, rules))
        assert len(statements) == 2


class TestTheReachIsReadableWithoutRunningTheRule:
    """`layer_rule_reach` — the numbers, for the readers that render them (A3/A4)."""

    def test_an_untagged_part_is_counted_through_its_container(
        self, nested_graph: sqlite3.Connection
    ) -> None:
        """Own tags reached one of these two edges; containment reaches both."""
        reach = layer_rule_reach(nested_graph, _rule())
        assert (reach.population.evaluated, reach.population.skipped_untagged) == (2, 0)

    def test_an_end_inside_nothing_is_still_outside_the_population(
        self, mixed_graph: sqlite3.Connection
    ) -> None:
        """Inheriting a layer is not the same as having one by default."""
        reach = layer_rule_reach(mixed_graph, _rule())
        assert (reach.population.evaluated, reach.population.skipped_untagged) == (2, 1)

    def test_it_counts_only_edges_of_the_rules_kind(
        self, nested_graph: sqlite3.Connection
    ) -> None:
        """The two `part_of` edges are containment, not the dependencies judged."""
        assert layer_rule_reach(nested_graph, _rule()).population.total == 2

    def test_on_this_repository_the_rule_now_reaches_almost_every_edge(
        self, live_graph: sqlite3.Connection
    ) -> None:
        """The measurement this epic exists for, taken from the code rather than quoted.

        16 of 362 at `aa4bfad4` by own tags; the figure below is what the rule
        decides on since `beadloom-ku26`.
        """
        reach = layer_rule_reach(live_graph, _rule())
        assert reach.population.total > 300
        assert reach.population.evaluated > reach.population.total * 9 // 10


# ---------------------------------------------------------------------------
# What must not have moved
# ---------------------------------------------------------------------------


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

        This repository's own `rules.yml` is read here rather than `_rule()`.
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

        `_rule()` is this repository's layering with its `exempt:` block left
        off. Every crossing it then reports must be one the rules file excuses,
        and every entry must excuse one — an entry that excused nothing would be
        a reason written for an edge that is not there. The comparison is a set
        of pairs and not a count, so it does not have to be rewritten when the
        number moves; the entries name literal ref_ids on this repository.
        """
        declared = next(rule for rule in live_rules if isinstance(rule, LayerRule))
        added = comparable(evaluate_layer_rules(live_graph, [_rule()])) - comparable(
            layer_findings_before_release_a(live_graph, [_rule()])
        )
        crossings = {(entry[5], entry[6]) for entry in added if entry[1] == "layer"}
        assert crossings == {
            (exemption.from_glob, exemption.to_glob) for exemption in declared.exempt
        }

    def test_on_a_graph_whose_layers_sit_on_containers(
        self, nested_graph: sqlite3.Connection
    ) -> None:
        """The one edge added is the one no own tag reached: `infra-bit -> core-bit`.

        Infrastructure depending on a domain, through two components neither of
        which carries a tag — the shape an adopter has and this repository
        hides.
        """
        rules = [_rule()]
        added = comparable(evaluate_layer_rules(nested_graph, rules)) - comparable(
            layer_findings_before_release_a(nested_graph, rules)
        )
        assert {(entry[5], entry[6]) for entry in added if entry[1] == "layer"} == {
            ("infra-bit", "core-bit")
        }

    def test_on_a_graph_that_violates_the_direction(self, tmp_path: Path) -> None:
        """A differential over an empty finding set proves nothing; this one is not empty."""
        conn = _build_graph(
            tmp_path / "violating.db",
            nodes=[
                ("svc", ["layer-service"]),
                ("app", ["layer-application"]),
                ("infra", ["layer-infra"]),
                ("loose", []),
            ],
            edges=[
                ("infra", "svc", "depends_on"),
                ("app", "infra", "depends_on"),
                ("loose", "svc", "depends_on"),
            ],
        )
        try:
            rules = [_rule(allow_skip=False)]
            before = layer_findings_before_release_a(conn, rules)
            assert len(before) >= 2
            assert decisions(evaluate_layer_rules(conn, rules)) == comparable(before)
        finally:
            conn.close()

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
        self, live_repo_reindexed: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        after = self._lint(live_repo_reindexed)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        before = self._lint(live_repo_reindexed)
        assert comparable(before), "a comparison over an empty findings list proves nothing"
        assert decisions(after) == comparable(before)

    def test_the_one_addition_is_the_population_statement(
        self, live_repo_reindexed: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stated as a difference, so a second addition could not hide behind the first."""
        after = self._lint(live_repo_reindexed)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        added = comparable(after) - comparable(self._lint(live_repo_reindexed))
        assert {entry[1] for entry in added} == {LAYER_POPULATION_RULE_TYPE}
        assert {entry[2] for entry in added} == {"warn"}

    def test_the_addition_moves_no_error_count(
        self, live_repo_reindexed: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """What `lint --strict` and the Gate decide on is the error count alone."""
        after = lint(live_repo_reindexed)
        monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
        monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
        before = lint(live_repo_reindexed)
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

    def test_the_forbid_edge_rule_matches_it_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Measured on a graph, because this repository declares no `forbid` rule.

        The fourth closure would otherwise be the one rule kind whose
        replacement was argued rather than run.
        """
        conn = _build_graph(
            tmp_path / "forbidden.db",
            nodes=[("ui", ["layer-service"]), ("db", ["layer-infra"]), ("plain", [])],
            edges=[("ui", "db", "depends_on"), ("plain", "db", "depends_on")],
        )
        rules = [
            ForbidEdgeRule(
                name="no-service-to-infra",
                description="A service must not depend on infrastructure directly",
                from_matcher=NodeMatcher(tag="layer-service"),
                to_matcher=NodeMatcher(tag="layer-infra"),
                edge_kind="depends_on",
                severity="error",
            )
        ]
        try:
            with_shared = comparable(evaluate_forbid_edge_rules(conn, rules))
            assert with_shared
            monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
            assert comparable(evaluate_forbid_edge_rules(conn, rules)) == with_shared
        finally:
            conn.close()

    def test_the_evaluators_hold_no_tag_cache_of_their_own(self) -> None:
        """Five copies of one closure were the duplication the lookup removes."""
        source = (REPO_ROOT / "src" / "beadloom" / "graph" / "rules" / "evaluators.py").read_text(
            encoding="utf-8"
        )
        assert "_cached_tags" not in source
        assert "tags_cache" not in source


class TestTheLookupItself:
    """`NodeTags` — one query, answered from memory."""

    def test_it_reads_the_graph_once_however_many_nodes_are_asked_about(
        self, fully_tagged_graph: sqlite3.Connection
    ) -> None:
        counting = _CountingConnection(fully_tagged_graph)
        lookup = NodeTags(counting)  # type: ignore[arg-type]
        assert lookup.of("svc") == {"layer-service"}
        assert lookup.of("dom") == {"layer-domain"}
        assert lookup.of("svc") == {"layer-service"}
        assert counting.queries == 1

    def test_it_reads_nothing_until_it_is_asked(
        self, fully_tagged_graph: sqlite3.Connection
    ) -> None:
        """Four of the five call sites skip tags entirely when no rule matches on one."""
        counting = _CountingConnection(fully_tagged_graph)
        NodeTags(counting)  # type: ignore[arg-type]
        assert counting.queries == 0

    def test_a_node_with_no_extra_at_all_has_no_tags(
        self, tmp_path: Path
    ) -> None:
        conn = open_db(tmp_path / "bare.db")
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary) VALUES (?, ?, ?)",
            ("bare", "feature", "no extra"),
        )
        conn.commit()
        try:
            assert node_tags(conn).of("bare") == set()
        finally:
            conn.close()

    def test_a_mapping_of_every_nodes_tags_is_available_for_the_layer_lookup(
        self, fully_tagged_graph: sqlite3.Connection
    ) -> None:
        assert node_tags(fully_tagged_graph).as_mapping()["dom"] == {"layer-domain"}

    def test_one_unreadable_extra_does_not_take_the_rest_of_the_table_with_it(
        self, tmp_path: Path
    ) -> None:
        """Three rows — valid, NULL, unparseable — and the valid one still answers.

        Reading every row at once means a malformed `extra` on a node nobody
        asked about is on the path of every tag question in the run; one node at
        a time, only the node you asked about could raise (A8 review, Major 2).
        """
        # Arrange
        conn = open_db(tmp_path / "malformed.db")
        create_schema(conn)
        for ref_id, extra in [
            ("good", json.dumps({"tags": ["layer-domain"]})),
            ("empty", None),
            ("broken", "not json at all"),
        ]:
            conn.execute(
                "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
                (ref_id, "feature", ref_id, extra),
            )
        conn.commit()
        # Act
        try:
            lookup = node_tags(conn)
            # Assert
            assert lookup.of("good") == {"layer-domain"}
            assert lookup.of("empty") == set()
            assert lookup.of("broken") == set()
            assert lookup.as_mapping() == {"good": {"layer-domain"}}
        finally:
            conn.close()

    def test_a_malformed_extra_does_not_escape_the_whole_evaluation(
        self, tmp_path: Path
    ) -> None:
        """`evaluate_all` answers findings or `LintError`, never a JSON traceback."""
        # Arrange
        conn = _build_graph(
            tmp_path / "one-bad-row.db",
            nodes=[("svc", ["layer-service"]), ("infra", ["layer-infra"])],
            edges=[("infra", "svc", "depends_on")],
        )
        conn.execute("UPDATE nodes SET extra = ? WHERE ref_id = ?", ("{not json", "infra"))
        conn.commit()
        rule = LayerRule(
            name="architecture-layers",
            description="services over infrastructure",
            layers=list(DDD_LAYERS),
            enforce="top-down",
            allow_skip=True,
            edge_kind="depends_on",
            severity="error",
        )
        # Act
        try:
            found = evaluate_layer_rules(conn, [rule])
        finally:
            conn.close()
        # Assert
        assert [v.rule_type for v in found] == [LAYER_POPULATION_RULE_TYPE]


# ---------------------------------------------------------------------------
# The two tag readers, shape by shape — BDL-070 A8 re-review, Major 1
# ---------------------------------------------------------------------------


#: The stored `extra` values for which both readers answer the same set. This is
#: the whole of the parity claim `_read_all_tags` makes, and the table is here so
#: that the claim is measured rather than asserted in prose: the docstring the
#: re-review filed against said the two agreed for every malformed shape too.
_AGREEING_SHAPES = [
    pytest.param(None, set(), id="the-column-is-sql-null"),
    pytest.param("{}", set(), id="an-object-with-no-tags-key"),
    pytest.param('{"tags": []}', set(), id="an-empty-tags-list"),
    pytest.param('{"tags": ["tier-web"]}', {"tier-web"}, id="a-tags-list"),
]

#: The stored `extra` values for which they do NOT, and what the one-at-a-time
#: reader raises for each. `null`, `3` and `"x"` parse and are not objects, so
#: `get_node_tags` reaches `.get` on something that has none; `{not json` does
#: not parse at all.
_DIVERGING_SHAPES = [
    pytest.param("null", AttributeError, id="json-null"),
    pytest.param("3", AttributeError, id="a-number"),
    pytest.param('"x"', AttributeError, id="a-string"),
    pytest.param("{not json", json.JSONDecodeError, id="text-that-does-not-parse"),
]


def _one_node_with_extra(db_path: Path, raw: str | None) -> sqlite3.Connection:
    """A graph holding exactly one node, whose `extra` column is *raw*."""
    conn = open_db(db_path)
    create_schema(conn)
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, extra) VALUES (?, ?, ?, ?)",
        ("only", "feature", "the only node", raw),
    )
    conn.commit()
    return conn


class TestWhereTheTwoTagReadersAgreeAndWhereTheyDoNot:
    """`NodeTags.of` against `loader.get_node_tags`, one stored shape at a time.

    The two readers answer the same question — what tags does this node carry —
    and the table read at once must guard shapes the single-row read does not,
    because one malformed row is on the path of every tag question in the run.
    The A8 re-review measured that the guard makes the two DIVERGE for every
    malformed shape rather than agree, which is the opposite of what the
    docstring beside it said. The boundary is measured here so the prose has
    something to point at.
    """

    @pytest.mark.parametrize(("raw", "expected"), _AGREEING_SHAPES)
    def test_both_readers_answer_the_same_set(
        self, tmp_path: Path, raw: str | None, expected: set[str]
    ) -> None:
        # Arrange
        conn = _one_node_with_extra(tmp_path / "agree.db", raw)
        # Act / Assert
        try:
            assert node_tags(conn).of("only") == expected
            assert get_node_tags(conn, "only") == expected
        finally:
            conn.close()

    @pytest.mark.parametrize(("raw", "raised"), _DIVERGING_SHAPES)
    def test_the_table_read_answers_empty_where_the_row_read_raises(
        self, tmp_path: Path, raw: str, raised: type[Exception]
    ) -> None:
        # Arrange
        conn = _one_node_with_extra(tmp_path / "diverge.db", raw)
        # Act / Assert
        try:
            assert node_tags(conn).of("only") == set()
            assert node_tags(conn).as_mapping() == {}
            with pytest.raises(raised):
                get_node_tags(conn, "only")
        finally:
            conn.close()

    def test_neither_reader_raises_for_a_node_the_graph_does_not_hold(
        self, tmp_path: Path
    ) -> None:
        """The one shape that is not about `extra` at all."""
        # Arrange
        conn = _one_node_with_extra(tmp_path / "absent.db", '{"tags": ["tier-web"]}')
        # Act / Assert
        try:
            assert node_tags(conn).of("no-such-node") == set()
            assert get_node_tags(conn, "no-such-node") == set()
        finally:
            conn.close()
