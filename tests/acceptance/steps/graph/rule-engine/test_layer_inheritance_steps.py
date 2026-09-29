"""Steps for `graph/rule-engine/layer_inheritance.feature` (BDL-070 B3, B5; BDL-074 E1).

Against a real project directory, the real reindex and the real linter: each
scenario writes a graph on disk and runs the shipped code over it, through
:class:`~tests.support.rule_engine_driver.LayeredProject`. Nothing is mocked,
because a scenario that passes against a double proves the double.

BDL-070 B5 (`beadloom-bi78`) added the deeper nests, the part that declares its own
tier and the project whose dependencies are DERIVED from Python imports rather than
written into `nodes.yml`. The last one closes the distance between what these
scenarios exercise and what an adopter runs: an adopter writes `part_of` and
imports, and the `depends_on` edges the layer rule judges are the indexer's answer
about the code.

The shapes, the lint and the verdicts are the shared vocabulary
(:mod:`tests.support.rule_engine_vocabulary`); what is defined here
is what only this feature says: where a finding says a layer came from.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from pytest_bdd import parsers, scenarios, then

from tests.support.rule_engine_driver import LayeredProject
from tests.support.rule_engine_vocabulary import (
    use_findings_vocabulary,
    use_layered_project_vocabulary,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/layer_inheritance.feature")
use_findings_vocabulary()
use_layered_project_vocabulary()


@pytest.fixture()
def layered_project(tmp_path: Path) -> LayeredProject:
    return LayeredProject(tmp_path / "shop")


@pytest.fixture()
def outcome(layered_project: LayeredProject) -> LayeredProject:
    return layered_project


@then("no dependency edge was written in the graph file by hand")
def _no_declared_dependency(layered_project: LayeredProject) -> None:
    """The load-bearing half of the import scenario, asserted rather than assumed.

    Without this the scenario would pass against a fixture that declared the
    edge in `nodes.yml` and never imported anything, which proves the layer
    rule and says nothing about the path from a line of code to a verdict.
    """
    graph_file = layered_project.path / ".beadloom" / "_graph" / "nodes.yml"
    assert "depends_on" not in graph_file.read_text(encoding="utf-8")


@then(
    parsers.parse(
        'the finding says the source is in layer "{src_layer}" '
        'and the target in layer "{dst_layer}"'
    )
)
def _names_both_layers(layered_project: LayeredProject, src_layer: str, dst_layer: str) -> None:
    """Both ends, by the NAME the declaration gives the layer rather than the tag."""
    messages = [v.message for v in layered_project.run.layer_findings()]
    assert any(
        f"layer '{src_layer}'" in message and f"layer '{dst_layer}'" in message
        for message in messages
    ), messages


def _provenance_claims(message: str, ref_id: str) -> list[str]:
    """The containers *message* says gave *ref_id* its layer, anchored on *ref_id*.

    A finding names BOTH ends, so a check spelled as two independent substring
    tests reports a clause belonging to the other end. The two shapes are the
    ones the product writes — `layer_crossings._where` for a crossing and
    `evaluators._layer_phrase` for a direction finding — and each is matched
    from the node's own name onward.
    """
    node = re.escape(f"'{ref_id}' ")
    container = "'([^']*)'"
    return [
        *re.findall(rf"{node}\(inside {container}\)", message),
        *re.findall(rf"{node}\(layer '[^']*', index \d+, inherited from {container}\)", message),
    ]


@then(parsers.parse('no finding says "{ref_id}" inherited a layer'))
def _claims_no_inheritance(layered_project: LayeredProject, ref_id: str) -> None:
    """A node that declares its own layer is not described as having taken one."""
    offenders = [
        (v.message, claims)
        for v in layered_project.run.layer_findings()
        if (claims := _provenance_claims(v.message, ref_id))
    ]
    assert offenders == [], offenders


@then(parsers.parse('no finding says "{ref_id}" is in a layer inherited from "{container}"'))
def _did_not_inherit_from(layered_project: LayeredProject, ref_id: str, container: str) -> None:
    """The farther container did not decide — a claim the nearest-ancestor rule owes.

    Spelled against the FAR container by name: a scenario asserting only that
    the near one was named would pass against a rule that named both.
    """
    offenders = [
        v.message
        for v in layered_project.run.layer_findings()
        if container in _provenance_claims(v.message, ref_id)
    ]
    assert offenders == [], offenders
