"""Step implementations for `features/verdict_room.feature` (BDL-068 S3.2).

Thin by design: each step writes a real declaration on disk and runs the real
`beadloom rooms` / `beadloom ci` commands through Click's runner. Nothing is
doubled, because a scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

from .room_judgement import (
    legs_entered_that_do_not_match,
    legs_not_entered_naming_no_difference,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/verdict_room.feature")


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {"root": tmp_path}


def _write_workflow(world: dict[str, Any], body: str) -> None:
    workflows = world["root"] / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(body, encoding="utf-8")


def _rooms(world: dict[str, Any], *extra: str) -> str:
    outcome = CliRunner().invoke(
        main, ["rooms", "--project", str(world["root"]), *extra]
    )
    assert outcome.exit_code == 0, outcome.stdout + outcome.stderr
    return outcome.stdout


@given(
    parsers.parse(
        "a project whose packaging declares support for Python {first} and {second}"
    )
)
def _packaging_declares(world: dict[str, Any], first: str, second: str) -> None:
    (world["root"] / "pyproject.toml").write_text(
        'requires-python = ">=' + first + '"\n'
        "classifiers = [\n"
        f'  "Programming Language :: Python :: {first}",\n'
        f'  "Programming Language :: Python :: {second}",\n'
        "]\n",
        encoding="utf-8",
    )
    world["versions"] = (first, second)


@given(parsers.parse('a workflow job running on "{label}" over both versions'))
def _a_job_over_both(world: dict[str, Any], label: str) -> None:
    first, second = world["versions"]
    _write_workflow(
        world,
        "jobs:\n"
        "  tests:\n"
        f"    runs-on: {label}\n"
        "    strategy:\n"
        "      matrix:\n"
        f'        python-version: ["{first}", "{second}"]\n',
    )


@given("a workflow job running on a runner label the report has no platform for")
def _an_unknown_label(world: dict[str, Any]) -> None:
    _write_workflow(world, "jobs:\n  publish:\n    runs-on: [self-hosted, publisher]\n")


@given("a project the gate can run over")
def _a_gate_project(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    _write_workflow(
        world,
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    strategy:\n"
        "      matrix:\n"
        '        python-version: ["3.10", "3.11"]\n',
    )


@when("the rooms are reported")
def _report_rooms(world: dict[str, Any]) -> None:
    world["report"] = _rooms(world)
    world["payload"] = json.loads(_rooms(world, "--json"))


@when("the gate verdict is rendered")
def _render_gate(world: dict[str, Any]) -> None:
    outcome = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", "rich"]
    )
    world["verdict"] = outcome.stdout
    world["exit_code"] = outcome.exit_code
    machine = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", "json"]
    )
    world["verdict_payload"] = json.loads(machine.stdout)


@then("both declared legs are reported")
def _both_legs(world: dict[str, Any]) -> None:
    first, second = world["versions"]
    assert len(world["payload"]["declared"]) == 2
    assert {r["dimensions"]["python"] for r in world["payload"]["declared"]} == {
        first,
        second,
    }


@then("a version added to the workflow is reported without the tool being changed")
def _a_third_version(world: dict[str, Any]) -> None:
    first, second = world["versions"]
    _write_workflow(
        world,
        "jobs:\n"
        "  tests:\n"
        "    runs-on: ubuntu-latest\n"
        "    strategy:\n"
        "      matrix:\n"
        f'        python-version: ["{first}", "{second}", "3.13"]\n',
    )
    payload = json.loads(_rooms(world, "--json"))
    assert len(payload["declared"]) == 3
    assert "3.13" in {r["dimensions"]["python"] for r in payload["declared"]}


@then("at least one declared leg is reported as not entered")
def _at_least_one_not_entered(world: dict[str, Any]) -> None:
    """True in every room, which is the point of writing it this way.

    The two legs differ only in the interpreter, so no run can be in both: on a
    developer machine neither is entered, on the 3.10 leg one is. The claim the
    scenario makes -- a verdict names the rooms it did not enter -- is the same
    assertion at both arithmetics, and the earlier wording (`both legs are not
    entered`) made it a claim about the machine instead. It then had to step
    aside on Linux, so the scenario ran only where the feature is least
    exercised.
    """
    declared = world["payload"]["declared"]
    assert len(declared) == 2
    assert [r for r in declared if not r["entered"]]


@then("every leg not entered names the dimension that differs")
def _not_entered_names_the_difference(world: dict[str, Any]) -> None:
    assert legs_not_entered_naming_no_difference(world["payload"]) == []


@then("every leg reported as entered matches this run in every dimension it declares")
def _entered_matches_this_run(world: dict[str, Any]) -> None:
    """The half no run outside a declared leg can reach.

    On a developer machine this iterates nothing and the scenario rests on the
    two steps above; on a CI leg it is the only step that judges what `entered`
    means. Both halves are written because the room decides which one carries
    the scenario, and neither room is the one this suite is always run in. The
    judgement lives in a named function so `tests/test_verdict_room_population`
    can drive it over a run inside a declared leg, which no run on a developer
    machine is.
    """
    assert legs_entered_that_do_not_match(world["payload"]) == []


@then("that job is reported as unresolved")
def _reported_unresolved(world: dict[str, Any]) -> None:
    assert any(
        "self-hosted+publisher" in u["why"] for u in world["payload"]["unresolved"]
    )


@then("it is not reported as a room this run entered")
def _not_entered_at_all(world: dict[str, Any]) -> None:
    assert [r for r in world["payload"]["declared"] if r["entered"]] == []


@then("the verdict names the room it was taken in")
def _verdict_names_room(world: dict[str, Any]) -> None:
    import platform

    assert "Room:" in world["verdict"]
    assert platform.system() in world["verdict"]
    assert platform.system() in _payload_room(world["verdict_payload"])


def _payload_room(payload: dict[str, Any]) -> str:
    """The room out of a verdict payload, in either shape a verdict uses.

    The Gate carries a census — the current room plus the declared ones it did
    or did not enter — and `beadloom mutation` carries the one line naming the
    room its report was produced in. Both are the same claim at different
    widths, and this feature is about whether the claim is made at all, so the
    step reads either rather than being written twice.
    """
    room = payload["room"]
    if isinstance(room, str):
        return room
    return json.dumps(room["current"])


@then("the verdict names how many declared rooms it did not enter")
def _verdict_names_the_gap(world: dict[str, Any]) -> None:
    """The number the verdict prints is the number the census measured.

    Not a literal two. The fixture declares two legs differing only in the
    interpreter, so a run is inside at most one of them: two are outside on a
    developer machine and one is outside on the 3.10 leg, and `== 2` was a claim
    about the machine the assertion was authored on. It reddened `tests (3.10)`
    on PR #60 while passing everywhere else, which is the shape this scenario
    exists to remove — one level up from the scenario it was written beside.
    """
    census = world["verdict_payload"]["room"]
    missed = census["not_entered"]
    declared = len(missed) + len(census["entered"])
    assert declared == 2, "the gate fixture declares two legs"
    assert missed, "two legs differing only in the interpreter leave at least one outside"
    assert f"{len(missed)} of {declared} declared room(s) not entered by this run" in (
        world["verdict"]
    )


@then("the verdict states the same result it states without its room")
def _same_result(world: dict[str, Any]) -> None:
    from beadloom.application.gate import run_ci_gate

    result = run_ci_gate(
        world["root"], fail_on=None, hub_exports=[], no_reindex=False
    )
    assert result.ok is (world["exit_code"] == 0)
    assert ("PASS — gate clean" in world["verdict"]) is result.ok


@then("naming the room adds no finding")
def _no_finding_added(world: dict[str, Any]) -> None:
    findings = [f for step in world["verdict_payload"]["steps"] for f in step["findings"]]
    assert not any("room" in json.dumps(f).lower() for f in findings)


# --- BDL-068 S3.3: the same rule over a second verdict surface -------------


@given(parsers.parse("a project declaring a mutation target that no run covered"))
def _a_mutation_target_no_run_covered(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / ".beadloom").mkdir(parents=True, exist_ok=True)
    (root / ".beadloom" / "config.yml").write_text(
        "languages:\n- .py\nscan_paths:\n- src\n", encoding="utf-8"
    )
    (root / ".beadloom" / "flow.yml").write_text(
        "mutation:\n  targets:\n  - src/core/\n", encoding="utf-8"
    )
    (root / "src" / "core").mkdir(parents=True, exist_ok=True)
    (root / "src" / "core" / "unit.py").write_text("VALUE = 1\n", encoding="utf-8")


@when("the mutation verdict is rendered")
def _render_mutation_verdict(world: dict[str, Any]) -> None:
    runner = CliRunner()
    human = runner.invoke(main, ["mutation", "--project", str(world["root"])])
    machine = runner.invoke(
        main, ["mutation", "--project", str(world["root"]), "--json"]
    )
    world["verdict"] = human.stdout
    world["verdict_payload"] = json.loads(machine.stdout)
    world["exit_code"] = human.exit_code


@then("the verdict reports the target as measured by no run")
def _verdict_reports_the_unmeasured_target(world: dict[str, Any]) -> None:
    checks = [f["check"] for f in world["verdict_payload"]["findings"]]
    assert "mutation-target-unmeasured" in checks
    assert world["exit_code"] == 1
