"""Step implementations for `features/layer_inheritance.feature` (BDL-070 B3, B5).

Against a real project directory, the real reindex and the real linter: each
scenario writes a graph on disk and runs the shipped code over it. Nothing is
mocked, because a scenario that passes against a double proves the double.

BDL-070 B5 (`beadloom-bi78`) added the steps for the deeper nests, the part that
declares its own tier and the project whose dependencies are DERIVED from
Python imports rather than written into `nodes.yml`. The last one closes the
distance between what these scenarios exercise and what an adopter runs: an
adopter writes `part_of` and imports, and the `depends_on` edges the layer rule
judges are the indexer's answer about the code.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint
from beadloom.graph.rules.layer_reach import LAYER_POPULATION_RULE_TYPE

from .tiered_project import (
    TIERS,
    graph_with,
    graph_with_a_deeper_nest,
    graph_with_a_part_that_declares_its_own_tier,
    graph_with_nested_parts,
    graph_with_peer_containers,
    write_tiered_project,
    write_zoned_import_project,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beadloom.graph.rules.types import Violation

scenarios("../features/layer_inheritance.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "tiers": TIERS}


@given("a project whose layering is declared as two containers in different tiers")
def _nested_parts(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_nested_parts()


@given("a project whose layering is declared as two peer containers in one tier")
def _peer_containers(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_peer_containers()


@given("a project whose layering is declared as three tiers")
def _three_tiers(world: dict[str, Any]) -> None:
    world["tiers"] = TIERS


@given(
    parsers.parse(
        "{tiered:d} dependency edges between tiered nodes and {untiered:d} with an untiered end"
    )
)
def _flat_graph(world: dict[str, Any], tiered: int, untiered: int) -> None:
    world["nodes"], world["edges"] = graph_with(tiered_edges=tiered, untiered_edges=untiered)


@given("a project whose parts are two part_of generations below the tagged container")
def _deeper_nest(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_a_deeper_nest()


@given("a project whose parts are two generations down and the nearer container is tagged")
def _deeper_nest_with_a_tagged_middle(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_a_deeper_nest(middle_tag=TIERS[2])


@given("a project where a part carries a tier its container does not")
def _own_tier_on_a_part(world: dict[str, Any]) -> None:
    world["nodes"], world["edges"] = graph_with_a_part_that_declares_its_own_tier()


@given("a project whose dependencies come only from Python imports")
def _imports_only(world: dict[str, Any]) -> None:
    """Written and indexed HERE, so the `depends_on` edges are the indexer's.

    The other `given` steps hand the `when` step a node and edge list; this one
    hands it a finished project, because the point of the scenario is that no
    edge list was written at all.
    """
    world["project"] = write_zoned_import_project(world["root"])


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    project = world.get("project") or write_tiered_project(
        world["root"], nodes=world["nodes"], edges=world["edges"], tiers=world["tiers"]
    )
    world["project"] = project
    world["violations"] = lint(project).violations


def _layer_findings(world: dict[str, Any]) -> list[Violation]:
    return [v for v in world["violations"] if v.rule_type == "layer"]


def _judged(world: dict[str, Any]) -> set[tuple[str | None, str | None]]:
    return {(v.from_ref_id, v.to_ref_id) for v in _layer_findings(world)}


@then(parsers.parse('"{src} -> {dst}" is reported as a layering violation'))
def _reported_as_a_violation(world: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) in _judged(world), _judged(world)


@then(parsers.parse('the finding says that layer was inherited from "{container}"'))
def _names_the_container(world: dict[str, Any], container: str) -> None:
    assert any(f"inherited from '{container}'" in v.message for v in _layer_findings(world)), [
        v.message for v in _layer_findings(world)
    ]


@then(parsers.parse('"{src} -> {dst}" is reported as a same-layer crossing'))
def _reported_as_a_crossing(world: dict[str, Any], src: str, dst: str) -> None:
    reported = [
        v
        for v in _layer_findings(world)
        if (v.from_ref_id, v.to_ref_id) == (src, dst) and "Same-layer crossing" in v.message
    ]
    assert len(reported) == 1, [v.message for v in _layer_findings(world)]


@then(parsers.parse('no finding names "{src} -> {dst}"'))
def _not_reported(world: dict[str, Any], src: str, dst: str) -> None:
    assert (src, dst) not in _judged(world)


@then(
    parsers.parse("the run states that it evaluated {evaluated:d} of {total:d} dependency edges")
)
def _states_evaluated(world: dict[str, Any], evaluated: int, total: int) -> None:
    statements = [v for v in world["violations"] if v.rule_type == LAYER_POPULATION_RULE_TYPE]
    assert len(statements) == 1
    assert f"evaluated {evaluated} of {total} live `depends_on` edge(s)" in statements[0].message


@then("no finding is a layering violation")
def _nothing_decided(world: dict[str, Any]) -> None:
    assert _layer_findings(world) == []


@then("no dependency edge was written in the graph file by hand")
def _no_declared_dependency(world: dict[str, Any]) -> None:
    """The load-bearing half of the import scenario, asserted rather than assumed.

    Without this the scenario would pass against a fixture that declared the
    edge in `nodes.yml` and never imported anything, which proves the layer
    rule and says nothing about the path from a line of code to a verdict.
    """
    graph_file = world["project"] / ".beadloom" / "_graph" / "nodes.yml"
    assert "depends_on" not in graph_file.read_text(encoding="utf-8")


@then(
    parsers.parse(
        'the finding says the source is in layer "{src_layer}" '
        'and the target in layer "{dst_layer}"'
    )
)
def _names_both_layers(world: dict[str, Any], src_layer: str, dst_layer: str) -> None:
    """Both ends, by the NAME the declaration gives the layer rather than the tag."""
    messages = [v.message for v in _layer_findings(world)]
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
def _claims_no_inheritance(world: dict[str, Any], ref_id: str) -> None:
    """A node that declares its own layer is not described as having taken one."""
    offenders = [
        (v.message, claims)
        for v in _layer_findings(world)
        if (claims := _provenance_claims(v.message, ref_id))
    ]
    assert offenders == [], offenders


@then(parsers.parse('no finding says "{ref_id}" is in a layer inherited from "{container}"'))
def _did_not_inherit_from(world: dict[str, Any], ref_id: str, container: str) -> None:
    """The farther container did not decide — a claim the nearest-ancestor rule owes.

    Spelled against the FAR container by name: a scenario asserting only that
    the near one was named would pass against a rule that named both.
    """
    offenders = [
        v.message
        for v in _layer_findings(world)
        if container in _provenance_claims(v.message, ref_id)
    ]
    assert offenders == [], offenders
