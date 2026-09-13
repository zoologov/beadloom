"""A rule that reported a finding is not also reported as unable to fire.

BDL-070 B5 (`beadloom-bi78`) FOUND this as BDL-UX #296 and held it in three
`xfail(strict=True)` statements; B5-fix (`beadloom-5tcc.6`) closed it and this
file is now the regression guard. Release B moved `evaluate_layer_rules` onto the
derived layer — a node's own tag, else the nearest `part_of` container that
declares one — and `liveness._layer_reasons` was not moved with it. Until it was,
one `beadloom lint` run said three things that cannot all be true: the rule
reported an error about an edge, the population statement said it judged every
edge it was handed, and the liveness leg said the rule "cannot fire" and "checks
nothing".

Measured 2026-09-13 before the fix: on the nested-parts fixture, `error_count 1`,
`rules_evaluated 1`, `rules_inert 1`, population `evaluated=2 skipped_untagged=0`;
on the peer-container fixture, `error_count 2` and `rules_inert 1` with the
liveness message `fewer than two of its layers are populated`.

The two fixtures reach the two branches of `_layer_reasons` and both are needed.
Nested parts put the ends in DIFFERENT tiers, so the swap onto the derived layer
alone answers it. Peer containers put both ends in ONE tier, where no swap
changes which tags are carried: what the rule reports there is a same-layer
crossing, so liveness has to ask whether the rule decides any edge rather than
whether two of its layers are inhabited.

**This repository cannot see either shape.** Every node here that is in a layer
carries the tag itself, so own tags and derived layers agree and liveness is
satisfied. The shape needs untagged components inside tagged containers, which is
the shape an adopter has and the reason this epic's CONTEXT requires every layer
claim to be measured on a graph that is not ours.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from beadloom.graph.linter import lint
from beadloom.graph.rules.liveness import inert_rules
from beadloom.graph.rules.loader import load_rules
from beadloom.graph.rules.types import LayerRule
from tests.acceptance.steps.tiered_project import (
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult

@pytest.fixture()
def inheriting_project(tmp_path: Path) -> Path:
    """Two untagged components inside containers in different tiers.

    The rule finds against `store-db -> web-api` here, so any claim that it
    could not fire is refutable by the same run's own output.
    """
    nodes, edges = graph_with_nested_parts()
    return write_tiered_project(tmp_path / "shop", nodes=nodes, edges=edges)


@pytest.fixture()
def result(inheriting_project: Path) -> LintResult:
    """One lint run over one index, read by every test below."""
    return lint(inheriting_project)


@pytest.fixture()
def peer_project(tmp_path: Path) -> Path:
    """Two containers in ONE tier, each holding an untagged part.

    Only the middle tier is carried by any node, so the count of populated
    layers is the same before and after the derived-layer swap. What the rule
    reports here is two same-layer crossings.
    """
    nodes, edges = graph_with_peer_containers()
    return write_tiered_project(tmp_path / "bank", nodes=nodes, edges=edges)


@pytest.fixture()
def peer_result(peer_project: Path) -> LintResult:
    """One lint run over one index, read by every peer-container test below."""
    return lint(peer_project)


def _liveness_messages(result: LintResult) -> list[str]:
    return [v.message for v in result.violations if v.rule_type == "rule_liveness"]


def _inert_for(project: Path) -> list[tuple[object, str]]:
    """`inert_rules`' own answer for the project's layer rule.

    Asserted against the function directly, so a fix that only silenced the
    message in `lint` would not satisfy the tests that call this.
    """
    rule = next(
        candidate
        for candidate in load_rules(project / ".beadloom" / "_graph" / "rules.yml")
        if isinstance(candidate, LayerRule)
    )
    with closing(sqlite3.connect(project / ".beadloom" / "beadloom.db")) as conn:
        return list(inert_rules(conn, [rule], project_root=project))


class TestAnEdgeBetweenTiersItInherited:
    """Nested parts: the rule reports a direction violation and is live."""

    def test_the_rule_reports_an_error_about_an_edge(self, result: LintResult) -> None:
        assert result.error_count == 1
        assert [
            (v.from_ref_id, v.to_ref_id) for v in result.violations if v.rule_type == "layer"
        ] == [("store-db", "web-api")]

    def test_the_population_statement_says_it_judged_every_edge(
        self, result: LintResult
    ) -> None:
        assert [reach.population.skipped_untagged for reach in result.layer_populations] == [0]
        assert [reach.population.evaluated for reach in result.layer_populations] == [2]

    def test_a_rule_that_reported_a_finding_is_not_counted_inert(
        self, result: LintResult
    ) -> None:
        """`rules_inert` is what a reader takes as "this check did nothing"."""
        assert result.rules_inert == 0

    def test_no_liveness_message_says_a_firing_rule_cannot_fire(
        self, result: LintResult
    ) -> None:
        assert _liveness_messages(result) == []

    def test_liveness_sees_the_layers_the_rule_decides_on(
        self, inheriting_project: Path
    ) -> None:
        assert _inert_for(inheriting_project) == []


class TestACrossingInsideTheOneTierAnybodyCarries:
    """Peer containers: one populated layer, and the rule still decides edges.

    The other branch of the same function. `tier-web` and `tier-store` are
    carried by no node here, before the swap or after it, so a liveness leg that
    counts inhabited layers reports a rule that has just reported twice.
    """

    def test_the_rule_reports_both_crossings(self, peer_result: LintResult) -> None:
        assert peer_result.error_count == 2
        assert [
            (v.from_ref_id, v.to_ref_id)
            for v in peer_result.violations
            if v.rule_type == "layer"
        ] == [("ledger-api", "postings-api"), ("postings-api", "ledger-api")]

    def test_a_rule_that_reported_two_crossings_is_not_counted_inert(
        self, peer_result: LintResult
    ) -> None:
        assert peer_result.rules_inert == 0
        assert _liveness_messages(peer_result) == []

    def test_liveness_asks_whether_the_rule_decides_an_edge(self, peer_project: Path) -> None:
        assert _inert_for(peer_project) == []

    def test_the_two_layers_nobody_carries_are_still_named(
        self, peer_result: LintResult
    ) -> None:
        """The fact liveness used to carry does not disappear with the message.

        `declaration_statement` deferred to liveness whenever fewer than two
        layers held a node, on the assumption that liveness reported it for
        exactly that graph. Here liveness no longer does, so the declaration
        states it — otherwise closing #296 would silently drop the report that
        two of three declared tiers are inhabited by nobody.
        """
        declared = [
            v.message for v in peer_result.violations if v.rule_type == "layer_declaration"
        ]
        assert len(declared) == 1
        assert "`tier-web`" in declared[0]
        assert "`tier-store`" in declared[0]
        assert [
            v.severity for v in peer_result.violations if v.rule_type == "layer_declaration"
        ] == ["warn"]

    def test_the_one_inhabited_layer_is_counted_in_the_singular(
        self, peer_result: LintResult
    ) -> None:
        """A branch nothing could reach until liveness stopped covering it.

        `declaration_statement` stood down whenever fewer than two layers held a
        node, so its sentence had never been printed with a count of one and read
        "1 of them hold a node".
        """
        declared = [
            v.message for v in peer_result.violations if v.rule_type == "layer_declaration"
        ]
        assert "1 of them holds a node" in declared[0]
