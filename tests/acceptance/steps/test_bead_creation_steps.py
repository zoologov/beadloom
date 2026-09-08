"""Step implementations for the bead-creation path (BDL-068 S5, BDL-UX #171, #165).

Thin, like every acceptance module here, and nothing invokes ``bd``: the steps hand
over the two things bd actually emits — the JSON answer it returns for a plan and the
text an artifact instructs — because what is under test is how a creation path of ours
composes a plan and reads an answer, not what the tracker in front of the runner holds.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.bd_seam.assumptions import (
    ASSUMPTION_ALLOCATED_ID,
    ASSUMPTION_ECHOED_TITLES,
    ASSUMPTION_INTENDED_ID,
    VERDICT_SECURED,
    VERDICT_UNSECURED,
    call_sites,
)
from beadloom.services.bd_seam.creation import (
    AuthoredNumberError,
    PlannedBead,
    allocated_ids,
    graph_plan,
    plan_is_required,
)
from beadloom.services.bd_seam.invocations import text_invocations

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/bead_creation.feature")

_ROLE_CHAIN = ("dev", "test", "review", "tech-writer")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {
        "root": tmp_path,
        "beads": (),
        "plan": None,
        "refusal": None,
        "answer": "",
        "ids": None,
        "sites": (),
        "required": None,
    }


def _role_chain(titles: tuple[str, ...] | None = None) -> tuple[PlannedBead, ...]:
    """The mandatory four-role DAG, each bead blocked by the one before it."""
    return tuple(
        PlannedBead(
            key=role,
            title=(titles[index] if titles else f"[BDL-068] {role}: {role} work"),
            bead_type="task",
            depends_on=() if index == 0 else (_ROLE_CHAIN[index - 1],),
        )
        for index, role in enumerate(_ROLE_CHAIN)
    )


@given(
    parsers.parse(
        "a creation plan of {count:d} beads wired dev -> test -> review -> tech-writer"
    )
)
def _given_role_chain(world: dict[str, Any], count: int) -> None:
    world["beads"] = _role_chain()[:count]


@given(parsers.parse('a creation plan whose bead titles include "{title}"'))
def _given_authored_title(world: dict[str, Any], title: str) -> None:
    titles = (title, *(f"[BDL-068] {role}" for role in _ROLE_CHAIN[1:]))
    world["beads"] = _role_chain(titles)


@given(parsers.parse("the tracker answered a plan with ids dev={dev} and test={test}"))
def _given_answer(world: dict[str, Any], dev: str, test: str) -> None:
    world["answer"] = json.dumps({"ids": {"dev": dev, "test": test}, "schema_version": 1})


@given("the tracker's answer to a plan was not readable")
def _given_unreadable(world: dict[str, Any]) -> None:
    world["answer"] = "Created 2 issues\n  dev -> proj-fac\n"


@given(parsers.parse('an artifact that instructs "{command}"'))
def _given_artifact(world: dict[str, Any], command: str) -> None:
    world["sites"] = call_sites(text_invocations((("guide.md", f"Run `{command}` now.\n"),)))


@given(parsers.parse('an artifact that instructs "{first}" and "{second}"'))
def _given_artifact_pair(world: dict[str, Any], first: str, second: str) -> None:
    body = f"Run `{first}` and then `{second}`.\n"
    world["sites"] = call_sites(text_invocations((("guide.md", body),)))


@given(parsers.parse("a creation of {count:d} bead"))
@given(parsers.parse("a creation of {count:d} beads"))
def _given_creation_size(world: dict[str, Any], count: int) -> None:
    world["required"] = plan_is_required(count)


@when("the plan document is written")
def _when_plan_written(world: dict[str, Any]) -> None:
    try:
        world["plan"] = graph_plan(world["beads"])
    except AuthoredNumberError as exc:
        world["refusal"] = str(exc)


@when("the allocated ids are read")
def _when_ids_read(world: dict[str, Any]) -> None:
    world["ids"] = allocated_ids(world["answer"])


@when("the call sites are judged")
def _when_judged(world: dict[str, Any]) -> None:
    return None


@then("every edge names two plan keys")
def _then_edges_by_key(world: dict[str, Any]) -> None:
    keys = {bead.key for bead in world["beads"]}
    edges = world["plan"]["edges"]
    assert edges
    for edge in edges:
        assert edge["from_key"] in keys
        assert edge["to_key"] in keys


@then("no id appears anywhere in the plan")
def _then_no_id(world: dict[str, Any]) -> None:
    assert "from_id" not in repr(world["plan"])
    assert "parent_id" not in repr(world["plan"])


@then(parsers.parse("the bead keyed {key} is {bead_id}"))
def _then_key_maps(world: dict[str, Any], key: str, bead_id: str) -> None:
    assert world["ids"] is not None
    assert world["ids"][key] == bead_id


@then("the ids are reported as unreadable rather than as an empty plan")
def _then_unreadable(world: dict[str, Any]) -> None:
    assert world["ids"] is None


@then("the plan is refused for authoring a number the tracker has not allocated")
def _then_refused(world: dict[str, Any]) -> None:
    assert world["plan"] is None
    assert world["refusal"] is not None


@then(parsers.parse('the refusal names "{reference}"'))
def _then_refusal_names(world: dict[str, Any], reference: str) -> None:
    assert reference in (world["refusal"] or "")


@then("the plan is accepted")
def _then_accepted(world: dict[str, Any]) -> None:
    assert world["refusal"] is None
    assert world["plan"] is not None


def _verdict(world: dict[str, Any], assumption: str) -> str:
    found = [
        entry
        for site in world["sites"]
        for entry in site.assumptions
        if entry.name == assumption
    ]
    assert found, f"no site carried {assumption}"
    return found[0].verdict


@then(parsers.parse("the site's {assumption} assumption is secured"))
def _then_secured(world: dict[str, Any], assumption: str) -> None:
    assert _verdict(world, assumption) == VERDICT_SECURED


@then(parsers.parse("the site's {assumption} assumption is unsecured"))
def _then_unsecured(world: dict[str, Any], assumption: str) -> None:
    assert _verdict(world, assumption) == VERDICT_UNSECURED


@then("the detail names the count bd prints instead of the titles")
def _then_detail_names_count(world: dict[str, Any]) -> None:
    details = [
        entry.detail
        for site in world["sites"]
        for entry in site.assumptions
        if entry.name == ASSUMPTION_ECHOED_TITLES
    ]
    assert details
    assert "Added 2 dependencies" in details[0]


@then("a plan is not required")
def _then_not_required(world: dict[str, Any]) -> None:
    assert world["required"] is False


@then("a plan is required")
def _then_required(world: dict[str, Any]) -> None:
    assert world["required"] is True


_UNUSED = (ASSUMPTION_ALLOCATED_ID, ASSUMPTION_INTENDED_ID)
