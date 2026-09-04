"""Step implementations for `features/role_duties.feature` (BDL-068 S4).

Thin by design: every step writes a real fragment into a real project layer and
runs the real composition, so a scenario that passes has exercised the same
`compose()` the adapters are generated from. Nothing is doubled, because a
scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.waves import room_for
from beadloom.onboarding.composer import compose
from beadloom.onboarding.flow_config import resolve_flow_config
from beadloom.onboarding.role_composer import ROLE_NAMES
from beadloom.onboarding.role_duties import duty_report
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/role_duties.feature")

_FLOW_YML = """\
tools:
- claude
architecture:
- ddd
stack:
- python
"""


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    return {"root": tmp_path}


def _write_project_fragment(world: dict[str, Any], kind: str, name: str, body: str) -> None:
    directory = world["root"] / ".beadloom" / "flow" / kind
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.md").write_text(body, encoding="utf-8")


@given(
    parsers.parse(
        'a flow whose coordinator declares the "{duty}" duty for {first} and {second}'
    )
)
def _coordinator_declares(
    world: dict[str, Any], duty: str, first: str, second: str
) -> None:
    _write_project_fragment(
        world,
        "commands",
        "coordinator",
        f"\n## Duties\n\n<!-- beadloom:duty={duty} roles={first},{second} -->\n"
        "Verify in a clean room and say so in those words.\n",
    )


@given(parsers.parse('the {role} role\'s project layer carries the "{duty}" duty'))
def _role_carries(world: dict[str, Any], role: str, duty: str) -> None:
    _write_project_fragment(
        world,
        "roles",
        role,
        f"\n## The clean room\n\n<!-- beadloom:carries={duty} -->\n"
        "Verify in a clean room and say so in those words.\n",
    )


@given(parsers.parse('no artifact declares the "{duty}" duty'))
def _nothing_declares(world: dict[str, Any], duty: str) -> None:
    report = duty_report(world["root"])
    assert not [d for d in report.declarations if d.duty == duty]


@given(
    parsers.parse(
        'a project fragment for a role this flow does not ship carries the '
        '"{duty}" duty'
    )
)
def _orphan_fragment_carries(world: dict[str, Any], duty: str) -> None:
    _write_project_fragment(
        world, "roles", "scout", f"<!-- beadloom:carries={duty} -->\n"
    )


@when("the duties are checked")
def _check(world: dict[str, Any]) -> None:
    world["report"] = duty_report(world["root"])


@when("the agent-config check runs")
def _config_check(world: dict[str, Any]) -> None:
    outcome = CliRunner().invoke(
        main, ["config-check", "--project", str(world["root"])]
    )
    world["outcome"] = outcome


@then(
    parsers.parse('"{role}" is reported as a role that does not carry "{duty}"')
)
def _undelivered(world: dict[str, Any], role: str, duty: str) -> None:
    assert _undelivered_roles(world, duty) == {role}


@then(
    parsers.parse('"{role}" is not reported as a role that does not carry "{duty}"')
)
def _not_undelivered(world: dict[str, Any], role: str, duty: str) -> None:
    assert role not in _undelivered_roles(world, duty)


def _undelivered_roles(world: dict[str, Any], duty: str) -> set[str | None]:
    return {
        f.role
        for f in world["report"].findings
        if f.kind == "undelivered" and f.duty == duty
    }


@then(parsers.parse('"{duty}" is reported as carried by {role} and declared by nothing'))
def _undeclared(world: dict[str, Any], duty: str, role: str) -> None:
    undeclared = [
        f
        for f in world["report"].findings
        if f.kind == "undeclared" and f.duty == duty and f.role == role
    ]
    assert len(undeclared) == 1, world["report"].findings
    assert "declares" in undeclared[0].why


@then(parsers.parse('"{role}" is reported as a role no core fragment ships'))
def _unknown_role(world: dict[str, Any], role: str) -> None:
    unknown = [
        f
        for f in world["report"].findings
        if f.kind == "unknown-role" and f.role == role
    ]
    assert len(unknown) == 1, world["report"].findings


@then("no duty finding is reported")
def _no_findings(world: dict[str, Any]) -> None:
    assert world["report"].findings == ()


@then("the report still names the channel it cannot inspect")
@then("the report names the launch prompt as a channel no file-based check reaches")
def _names_the_prompt(world: dict[str, Any]) -> None:
    prompts = [
        entry
        for entry in world["report"].not_inspected
        if "prompt" in entry.source
    ]
    assert len(prompts) == 1, world["report"].not_inspected
    assert "not an artifact" in prompts[0].why


@then("the report states how many artifacts it did inspect")
def _names_the_corpus(world: dict[str, Any]) -> None:
    assert len(world["report"].inspected) >= len(
        [name for name in world["report"].inspected if name.startswith("roles/")]
    )
    assert world["report"].inspected


@then("that fragment is reported as not inspected")
def _orphan_not_inspected(world: dict[str, Any]) -> None:
    orphans = [
        entry
        for entry in world["report"].not_inspected
        if entry.source.endswith("roles/scout.md")
    ]
    assert len(orphans) == 1, world["report"].not_inspected
    assert "compose" in orphans[0].why


@then(parsers.parse('it is not reported as a role that carries "{duty}"'))
def _orphan_carries_nothing(world: dict[str, Any], duty: str) -> None:
    assert not [f for f in world["report"].findings if f.role == "scout"]


@then("the check reports the undelivered duty and blocks")
def _config_check_blocks(world: dict[str, Any]) -> None:
    outcome = world["outcome"]
    combined = outcome.stdout + outcome.stderr
    assert "example-duty" in combined, combined
    assert "review" in combined, combined
    assert outcome.exit_code == 1, combined


# --- BDL-UX #228: the flow as this repository ships it -----------------------
#
# The steps above build a synthetic duty in a temporary project. These run the
# shipped templates unchanged, because the defect was in what an ADOPTER
# receives and a synthetic fixture cannot see that.


@given("a project running the flow exactly as this repository ships it")
def _shipped_flow(world: dict[str, Any]) -> None:
    """No project fragment at all -- the composition is CORE plus overlays."""
    assert not (world["root"] / ".beadloom" / "flow").exists()


@when("a role's core is composed")
def _compose_a_role(world: dict[str, Any]) -> None:
    world["composed"] = {
        role: compose(
            "roles",
            role,
            config=resolve_flow_config(world["root"]),
            project_root=world["root"],
        ).text
        for role in ROLE_NAMES
    }


@then(parsers.parse('"{duty}" is declared for every role this flow ships'))
def _declared_for_every_role(world: dict[str, Any], duty: str) -> None:
    declared: set[str] = set()
    for declaration in world["report"].declarations:
        if declaration.duty == duty:
            declared.update(declaration.roles)
    assert declared == set(ROLE_NAMES), declared


@then(parsers.parse('every role\'s composed core carries "{duty}"'))
def _carried_by_every_role(world: dict[str, Any], duty: str) -> None:
    carried = {
        artifact.partition("/")[2]
        for artifact, carried_duty in world["report"].carried
        if carried_duty == duty and artifact.startswith("roles/")
    }
    assert carried == set(ROLE_NAMES), carried


@then("it names the room a bead owes in the form the wave planner emits")
def _names_the_room_form(world: dict[str, Any]) -> None:
    """The prose and the machine agree on one spelling, or this goes red.

    The literal is derived from `room_for`, so renaming the room in the planner
    reddens the role text that promises it -- which is the binding the two halves
    of #228 exist to have.
    """
    form = room_for("<bead-id>")
    for role, text in world["composed"].items():
        assert form in text, (role, form)


@then("it names the gate owner as the one who measures the combined tree")
def _names_the_gate_owner(world: dict[str, Any]) -> None:
    for role, text in world["composed"].items():
        assert "gate owner" in text, role
        assert "combined tree" in text, role


@then("the check names the composition as the corpus it read")
def _names_the_composition(world: dict[str, Any]) -> None:
    output = world["outcome"].output
    assert "COMPOSITION" in output, output
    assert "not the role files on disk" in output, output


@then("it reports that no role adapter is on disk to receive it")
def _names_the_empty_disk(world: dict[str, Any]) -> None:
    output = world["outcome"].output
    assert "NOTHING TO CHECK" in output, output
    assert "no role adapter is written here" in output, output
