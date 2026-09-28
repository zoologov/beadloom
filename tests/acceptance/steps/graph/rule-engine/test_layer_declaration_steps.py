"""Steps for `graph/rule-engine/layer_declaration.feature` (BDL-070 A7; BDL-074 E1).

Against a real project directory, the real reindex, the real linter and the real
architecture view, through :class:`~tests.support.rule_engine_driver.LayeredProject`.
The layering, the graph and the lint are the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`); what is defined here is
what only this feature asks: the second instrument, and the validation of the
declaration against the graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.rule_engine_driver import LayeredProject
from tests.support.rule_engine_vocabulary import (
    use_findings_vocabulary,
    use_layered_project_vocabulary,
)
from tests.support.tiered_project import OUR_LAYER_PREFIX, TIERS

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/layer_declaration.feature")
use_findings_vocabulary()
use_layered_project_vocabulary()

#: The node the first scenario adds: no tier of its own, inside one that has a tier.
#: This is the shape an adopter meets and this repository hides.
INHERITING_NODE = "core-widget"


@pytest.fixture()
def layered_project(tmp_path: Path) -> LayeredProject:
    return LayeredProject(tmp_path / "ledger")


@pytest.fixture()
def outcome(layered_project: LayeredProject) -> LayeredProject:
    return layered_project


@dataclass
class Answers:
    """What the When step asked, kept for the Then steps."""

    engine: dict[str, int | None] = field(default_factory=dict)
    view: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@pytest.fixture()
def answers() -> Answers:
    return Answers()


@given("a node carrying no tier of its own inside a container that carries one")
def _inheriting_node(layered_project: LayeredProject) -> None:
    layered_project.use_graph(
        [*layered_project.nodes, (INHERITING_NODE, "component", [])],
        [*layered_project.edges, (INHERITING_NODE, "core", "part_of")],
    )


@given(parsers.parse('the declaration names a fourth tier "{tier}" that no node carries'))
def _fourth_tier(layered_project: LayeredProject, tier: str) -> None:
    layered_project.declare_tiers((*TIERS, tier))


@when("each instrument is asked what layer every node is in")
def _ask_both(layered_project: LayeredProject, answers: Answers) -> None:
    answers.engine, answers.view = layered_project.layers_by_instrument()


@when("the rules are validated against the graph")
def _validate(layered_project: LayeredProject, answers: Answers) -> None:
    answers.warnings = layered_project.validate()


@then("the two answers agree node for node")
def _they_agree(layered_project: LayeredProject, answers: Answers) -> None:
    assert answers.engine == answers.view
    assert set(answers.engine) == {ref_id for ref_id, *_ in layered_project.nodes}


@then("the inherited node is placed in its container's tier by both")
def _the_inherited_node(answers: Answers) -> None:
    """Non-vacuous: equal answers are worthless if both are `None` everywhere."""
    assert answers.engine[INHERITING_NODE] == answers.engine["core"]
    assert answers.view[INHERITING_NODE] == TIERS.index("tier-core")


@then(parsers.parse('it is the only layering violation, at severity "{severity}"'))
def _the_only_violation(layered_project: LayeredProject, severity: str) -> None:
    found = layered_project.run.layer_findings()
    assert [(v.from_ref_id, v.to_ref_id, v.severity) for v in found] == [
        ("store", "web", severity)
    ]


@then("no layer tag this project ships appears anywhere in that project")
def _no_shipped_tag(layered_project: LayeredProject) -> None:
    """The scenario's whole point: the rule read a declaration it could not know."""
    assert OUR_LAYER_PREFIX not in layered_project.graph_files_text()


@then(parsers.parse('the validation names the tier "{tier}"'))
def _names_the_empty_tier(answers: Answers, tier: str) -> None:
    assert [w for w in answers.warnings if f"'{tier}'" in w], answers.warnings


@then("it says nothing about the three tiers that hold a node")
def _silent_about_the_populated(answers: Answers) -> None:
    joined = " ".join(answers.warnings)
    for tier in TIERS:
        assert tier not in joined, joined
