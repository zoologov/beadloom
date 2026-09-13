"""A rule that reported a finding is not also reported as unable to fire.

BDL-070 B5 (`beadloom-bi78`), FINDING BDL-UX #296. Release B moved
`evaluate_layer_rules` onto the derived layer — a node's own tag, else the
nearest `part_of` container that declares one. `liveness._layer_reasons` was not
moved with it and still decides on own tags alone, and its docstring says
`beadloom-ku26` (B3) would make that move "in the release that announces it".
B3 announced it and did not make it.

On a graph whose parts inherit their layers, one `beadloom lint` run therefore
says three things that cannot all be true: the rule reports an error about an
edge, the population statement says it evaluated every edge it was handed, and
the liveness leg says the rule "cannot fire" and "checks nothing". Measured
2026-09-13 on the nested-parts fixture: `error_count 1`, `rules_evaluated 1`,
`rules_inert 1`, population `evaluated=2 skipped_untagged=0`.

**This repository cannot see it.** Every node here that is in a layer carries
the tag itself, so own tags and derived layers agree and liveness is satisfied.
The shape needs untagged components inside tagged containers, which is the
shape an adopter has and the reason this epic's CONTEXT requires every layer
claim to be measured on a graph that is not ours.

The properties below are asserted as they SHOULD behave and marked
`xfail(strict=True)`: a gap stated as an executable claim goes green the day it
is closed, where a paragraph describing it does not. Nothing here is a
regression guard — the last two tests pin the CURRENT behaviour, so a reader can
tell what the run says today from what it ought to say.
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
    write_tiered_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult

#: Why the finding is stated here rather than only in the issue log: the log is
#: read when somebody goes looking, and this runs on every commit.
FINDING = "BDL-UX #296 — liveness decides on own tags while the rule decides on derived ones"


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


def _liveness_messages(result: LintResult) -> list[str]:
    return [v.message for v in result.violations if v.rule_type == "rule_liveness"]


class TestWhatTheRunSaysToday:
    """The contradiction, pinned so the xfails below are readable as a gap."""

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

    def test_and_the_same_run_says_the_rule_checks_nothing(self, result: LintResult) -> None:
        assert result.rules_inert == 1
        assert any("cannot fire" in message for message in _liveness_messages(result))


class TestWhatTheRunShouldSay:
    """FINDING BDL-UX #296. Each of these goes green when liveness is moved."""

    @pytest.mark.xfail(strict=True, reason=FINDING)
    def test_a_rule_that_reported_a_finding_is_not_counted_inert(
        self, result: LintResult
    ) -> None:
        """`rules_inert` is what a reader takes as "this check did nothing"."""
        assert result.rules_inert == 0

    @pytest.mark.xfail(strict=True, reason=FINDING)
    def test_no_liveness_message_says_a_firing_rule_cannot_fire(
        self, result: LintResult
    ) -> None:
        assert _liveness_messages(result) == []

    @pytest.mark.xfail(strict=True, reason=FINDING)
    def test_liveness_sees_the_layers_the_rule_decides_on(
        self, inheriting_project: Path
    ) -> None:
        """Asserted against `inert_rules` directly, so a fix that only silenced the
        message in `lint` would not satisfy it."""
        rule = next(
            candidate
            for candidate in load_rules(
                inheriting_project / ".beadloom" / "_graph" / "rules.yml"
            )
            if isinstance(candidate, LayerRule)
        )
        with closing(
            sqlite3.connect(inheriting_project / ".beadloom" / "beadloom.db")
        ) as conn:
            inert = inert_rules(conn, [rule], project_root=inheriting_project)
        assert inert == []
