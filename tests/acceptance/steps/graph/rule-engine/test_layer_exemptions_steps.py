"""Steps for `graph/rule-engine/layer_exemptions.feature` (BDL-070 B2; BDL-074 E1).

Against a real project directory, the real reindex and the real linter, through
:class:`~tests.support.rule_engine_driver.LayeredProject`. The shape, the
exemption and the lint are the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`); what is defined here
is what only this feature reads: what the run says about an entry, and the
crossings read straight off the graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pytest_bdd import parsers, scenarios, then, when

from tests.support.rule_engine_driver import LayeredProject
from tests.support.rule_engine_vocabulary import (
    use_findings_vocabulary,
    use_layered_project_vocabulary,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/layer_exemptions.feature")
use_findings_vocabulary()
use_layered_project_vocabulary()

#: What each state of an entry reads as, in the finding the run makes about it.
STATE_WORDS = {"excuses nothing": "excuses nothing", "expired": "expired on"}


@pytest.fixture()
def layered_project(tmp_path: Path) -> LayeredProject:
    return LayeredProject(tmp_path / "ledger")


@pytest.fixture()
def outcome(layered_project: LayeredProject) -> LayeredProject:
    return layered_project


@pytest.fixture()
def crossings() -> list[tuple[str, str]]:
    """The same-layer crossings the When step read off the graph."""
    return []


@when("the same-layer crossings are read off the graph")
def _read_crossings(layered_project: LayeredProject, crossings: list[tuple[str, str]]) -> None:
    crossings.extend(layered_project.same_layer_crossings())


@then(parsers.parse('the run reports that the exemption for "{end}" {state}'))
def _reported(layered_project: LayeredProject, end: str, state: str) -> None:
    words = STATE_WORDS[state]
    messages = layered_project.run.messages()
    assert any(words in m and f"'{end}'" in m for m in messages), messages


@then("the run makes no finding about an exemption that excuses nothing")
def _not_reported(layered_project: LayeredProject) -> None:
    assert not [m for m in layered_project.run.messages() if "excuses nothing" in m]


@then("the lint fails, naming the entry that carries no reason")
def _refused(layered_project: LayeredProject) -> None:
    error = layered_project.run.error
    assert error is not None
    assert "layers.exempt[0]" in error
    assert "reason" in error


@then(parsers.parse('"{src} -> {dst}" is still a crossing no entry excuses'))
def _still_a_crossing(layered_project: LayeredProject, src: str, dst: str) -> None:
    assert (src, dst) in layered_project.crossings_no_entry_excuses()


@then(parsers.parse('"{src} -> {dst}" is not among them'))
def _not_a_crossing(crossings: list[tuple[str, str]], src: str, dst: str) -> None:
    assert crossings, "no crossing was read, so absence proves nothing"
    assert (src, dst) not in crossings
