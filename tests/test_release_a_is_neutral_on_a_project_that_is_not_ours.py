"""Release A moves no verdict on a project whose layering is not this one's.

BDL-070 A7 (`beadloom-cfkk`). The epic's constraint is that Release A ships
visibility and changes no adopter's Gate result. A2 (`beadloom-1ylk`) proved
that for the EVALUATOR, on this repository's graph and on two hand-built graphs.
What no test held is the claim an adopter actually cares about: the whole
`lint()` run, over a project directory that is not this repository, indexed by
the real reindex and read through the real linter.

The layering here is declared as `tier-web` / `tier-core` / `tier-store`, three
tags that appear nowhere in `src/`. That is deliberate and is asserted: a
neutrality proof taken only over `layer-domain` and its siblings would be a
proof about this repository's four tags, and the epic's whole premise is that
the declaration is the adopter's.

**How "before" is reconstructed.** Not from a recorded baseline — the pre-change
code path is transcribed in `tests/the_lint_path_before_release_a.py` and run in
the same process against the same index, so both sides always see the same
project. The index is built ONCE per fixture and neither side reindexes, which
is what holds the lineage constant: a carried-forward and a fresh index disagree
on a population's denominator (BDL-UX #290), and a differential in which each
side counted a different graph measures the index rather than the change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beadloom.graph import rules
from beadloom.graph.linter import lint
from beadloom.graph.rules import evaluators
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE
from tests.acceptance.steps.tiered_project import (
    OUR_LAYER_PREFIX,
    TIERS,
    Edge,
    Node,
    write_tiered_project,
)
from tests.the_lint_path_before_release_a import (
    ClosureTags,
    comparable,
    decisions,
    layer_findings_before_release_a,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.linter import LintResult


#: The graph every neutrality test below is taken over: one edge the layering
#: forbids, two edges it allows, and two edges neither end of which carries a
#: tier tag. The forbidden edge is what makes the differential worth taking —
#: a comparison over an empty decision set proves nothing.
_MIXED_NODES: list[Node] = [
    ("ledger", "service", []),
    ("web", "domain", ["tier-web"]),
    ("core", "domain", ["tier-core"]),
    ("store", "domain", ["tier-store"]),
    ("plumbing", "component", []),
]
_MIXED_EDGES: list[Edge] = [
    ("web", "ledger", "part_of"),
    ("core", "ledger", "part_of"),
    ("store", "ledger", "part_of"),
    ("plumbing", "ledger", "part_of"),
    ("web", "core", "depends_on"),
    ("core", "store", "depends_on"),
    ("store", "web", "depends_on"),
    ("plumbing", "core", "depends_on"),
    ("web", "plumbing", "depends_on"),
]


@pytest.fixture()
def foreign_project(tmp_path: Path) -> Path:
    """A project that is not this repository, indexed once."""
    return write_tiered_project(tmp_path / "ledger", nodes=_MIXED_NODES, edges=_MIXED_EDGES)


@pytest.fixture()
def fully_tiered_project(tmp_path: Path) -> Path:
    """The same project with every node inside a declared tier."""
    return write_tiered_project(
        tmp_path / "tiered",
        nodes=[
            ("web", "domain", ["tier-web"]),
            ("core", "domain", ["tier-core"]),
            ("store", "domain", ["tier-store"]),
        ],
        edges=[
            ("web", "core", "depends_on"),
            ("core", "store", "depends_on"),
            ("store", "web", "depends_on"),
        ],
    )


@pytest.fixture()
def project_without_a_layer_rule(tmp_path: Path) -> Path:
    """A project that declares no layering at all."""
    return write_tiered_project(
        tmp_path / "flat",
        nodes=_MIXED_NODES,
        edges=_MIXED_EDGES,
        with_layer_rule=False,
    )


def _before(root: Path, monkeypatch: pytest.MonkeyPatch) -> LintResult:
    """`lint()` with the pre-Release-A layer evaluator and tag closure in place."""
    monkeypatch.setattr(rules, "evaluate_layer_rules", layer_findings_before_release_a)
    monkeypatch.setattr(evaluators, "node_tags", ClosureTags)
    return lint(root)


class TestTheDeclarationUnderTestIsNotThisRepositorys:
    """The premise the neutrality claim rests on, asserted rather than assumed."""

    def test_the_fixture_declares_a_layering_this_project_does_not_ship(
        self, foreign_project: Path
    ) -> None:
        # Arrange
        rules_text = (foreign_project / ".beadloom" / "_graph" / "rules.yml").read_text(
            encoding="utf-8"
        )
        nodes_text = (foreign_project / ".beadloom" / "_graph" / "nodes.yml").read_text(
            encoding="utf-8"
        )
        # Act / Assert
        assert OUR_LAYER_PREFIX not in rules_text
        assert OUR_LAYER_PREFIX not in nodes_text
        assert all(tier in rules_text for tier in TIERS)

    def test_the_layering_it_declares_is_actually_enforced_there(
        self, foreign_project: Path
    ) -> None:
        """A differential over a project the rule says nothing about proves nothing."""
        # Act
        found = [v for v in lint(foreign_project).violations if v.rule_type == "layer"]
        # Assert
        assert [(v.from_ref_id, v.to_ref_id) for v in found] == [("store", "web")]
        assert found[0].severity == "error"


class TestNothingIsRemovedAndNoDecisionMoves:
    """The neutrality criterion, in the three parts it was corrected into."""

    def test_the_decisions_are_identical(
        self, foreign_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        after = lint(foreign_project).violations
        before = _before(foreign_project, monkeypatch).violations
        # Assert
        assert decisions(before), "a comparison over an empty decision set proves nothing"
        assert decisions(after) == decisions(before)

    def test_no_finding_is_removed(
        self, foreign_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stated as a set difference over EVERYTHING, advisories included."""
        # Arrange
        after = lint(foreign_project).violations
        before = _before(foreign_project, monkeypatch).violations
        # Assert
        assert comparable(before) - comparable(after) == set()

    def test_the_only_addition_is_the_population_advisory(
        self, foreign_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        after = lint(foreign_project).violations
        before = _before(foreign_project, monkeypatch).violations
        # Act
        added = comparable(after) - comparable(before)
        # Assert
        assert {entry[1] for entry in added} == {LAYER_POPULATION_RULE_TYPE}
        assert {entry[2] for entry in added} == {"warn"}

    def test_the_verdict_the_gate_reads_does_not_move(
        self, foreign_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`lint --strict` and the Gate decide on the error count and nothing else."""
        # Arrange
        after = lint(foreign_project)
        before = _before(foreign_project, monkeypatch)
        # Assert
        assert after.error_count == before.error_count == 1
        assert after.has_errors is before.has_errors is True
        assert after.rules_inert == before.rules_inert

    def test_the_advisory_is_the_whole_of_the_warning_growth(
        self, foreign_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        after = lint(foreign_project)
        before = _before(foreign_project, monkeypatch)
        # Assert
        assert after.warning_count == before.warning_count + 1


class TestTheProjectsReleaseAIsSilentOn:
    """Two shapes in which Release A adds nothing at all, not even the advisory."""

    def test_a_project_whose_every_node_is_tiered_gains_no_finding(
        self, fully_tiered_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full reach means nothing went unseen, so there is nothing to report."""
        # Arrange
        after = lint(fully_tiered_project).violations
        before = _before(fully_tiered_project, monkeypatch).violations
        # Assert
        assert comparable(after) == comparable(before)
        assert decisions(after)

    def test_a_project_that_declares_no_layering_gains_no_finding(
        self, project_without_a_layer_rule: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        after = lint(project_without_a_layer_rule)
        before = _before(project_without_a_layer_rule, monkeypatch)
        # Assert
        assert comparable(after.violations) == comparable(before.violations)
        assert after.error_count == before.error_count == 0
