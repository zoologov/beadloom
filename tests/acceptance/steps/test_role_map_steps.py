"""Step implementations for `features/role_map.feature` (BDL-068 S6, BDL-UX #252).

Thin by design, and the same shape as `test_role_duties_steps.py`: every step
writes a real fragment into a real project layer and runs the real composition,
so a scenario that passes has exercised the same `compose()` an adopter's
`CLAUDE.md` is written from.

The one substitution is the role POPULATION. A scenario about a sixth role
cannot write `templates/roles/core/scout.md.txt` into the shipped templates
directory, because that directory is shared by every concurrent run in this
working tree and a neighbour's `config-check` would read the sixth role too. So
the fragment is written into a COPY of the shipped core directory and the
population is derived from it by the real `roles_in`. The derivation is the
production one; only the directory it is pointed at differs.

The module is named ``test_*`` so default pytest collection picks the scenarios
up -- the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.onboarding.flow_config import FlowConfig
from beadloom.onboarding.role_composer import ROLE_NAMES, roles_in
from beadloom.onboarding.role_map import role_map_report
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/role_map.feature")

_FLOW_YML = """\
tools:
- claude
architecture:
- ddd
stack:
- python
"""

#: A CORE fragment is a role when its front matter names its own file. Minimal
#: on purpose: the shape is what `roles_in` reads, and anything more would be
#: this fixture asserting a second fact.
_ROLE_FRAGMENT = """\
---
name: {role}
description: A synthetic role that exists only inside this scenario.
---

## The role

It exists so the check can be shown red.
"""


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    (tmp_path / ".beadloom").mkdir()
    (tmp_path / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    return {"root": tmp_path, "roles": None}


def _write_project_fragment(world: dict[str, Any], name: str, body: str) -> None:
    directory = world["root"] / ".beadloom" / "flow" / "claude"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.md").write_text(body, encoding="utf-8")


@given("a project running the flow exactly as this repository ships it")
def _shipped_flow(world: dict[str, Any]) -> None:
    """No project fragment at all -- the composition is CORE plus overlays."""
    assert not (world["root"] / ".beadloom" / "flow").exists()


@given(parsers.parse('the flow composes a role named "{role}"'))
def _sixth_role(world: dict[str, Any], role: str) -> None:
    from beadloom.onboarding.composer import templates_dir

    core = world["root"] / "core"
    shutil.copytree(templates_dir() / "roles" / "core", core)
    (core / f"{role}.md.txt").write_text(_ROLE_FRAGMENT.format(role=role), encoding="utf-8")
    world["roles"] = roles_in(core)
    assert role in world["roles"], world["roles"]


@given(parsers.parse('the project layer names "{role}" in a role designation'))
def _project_designates(world: dict[str, Any], role: str) -> None:
    _write_project_fragment(
        world,
        "CLAUDE",
        f'\n## Our roles\n\nLaunch it with `Agent(subagent_type="{role}")`.\n',
    )


@given(parsers.parse('the project layer says "{sentence}" in ordinary prose'))
def _project_prose(world: dict[str, Any], sentence: str) -> None:
    _write_project_fragment(world, "CLAUDE", f"\n## A note\n\n{sentence}.\n")


@given(parsers.parse('the project layer lists "{first}" and "{second}" as a punctuated roster'))
def _project_roster(world: dict[str, Any], first: str, second: str) -> None:
    _write_project_fragment(
        world,
        "CLAUDE",
        f"\n## Our environments\n\nWe deploy to `{first}`, `{second}`.\n"
        f'\nLaunch it with `Agent(subagent_type="scout")`.\n',
    )


@given(parsers.parse('a project whose flow declares "{tool}" alone'))
def _one_tool(world: dict[str, Any], tool: str) -> None:
    """The declaration an adopter writes, through the file production reads."""
    flow = world["root"] / ".beadloom" / "flow.yml"
    flow.write_text(_FLOW_YML.replace("- claude", f"- {tool}"), encoding="utf-8")


@given("the flow declares a tool this release ships no map artifact for")
def _tool_without_a_map(world: dict[str, Any]) -> None:
    """Built through the config seam, because `flow.yml` cannot express it.

    `build_flow_config` validates `tools:` against `SUPPORTED_TOOLS`, so the
    arrangement this scenario is about is one a future release reaches and a
    current `flow.yml` cannot declare. The seam is the one `role_map_report`
    already offers its callers, and it is the same control `beadloom-ec1a` used
    to measure the other tool-population constant in this domain.
    """
    world["config"] = FlowConfig(
        tools=("windsurf",), architecture="ddd", stack=("python",)
    )


@when("the role map is checked")
def _check(world: dict[str, Any]) -> None:
    world["report"] = role_map_report(
        world["root"], world.get("config"), roles=world["roles"]
    )


@when("the agent-config check runs")
def _config_check(world: dict[str, Any]) -> None:
    world["outcome"] = CliRunner().invoke(main, ["config-check", "--project", str(world["root"])])


def _findings(world: dict[str, Any], kind: str, role: str) -> list[Any]:
    return [
        finding
        for finding in world["report"].findings
        if finding.kind == kind and finding.role == role
    ]


@then(parsers.parse('"{role}" is reported as a role the map names nowhere'))
def _unmapped(world: dict[str, Any], role: str) -> None:
    found = _findings(world, "unmapped", role)
    assert len(found) == 1, world["report"].findings
    assert "names it nowhere" in found[0].why, found[0].why


@then(parsers.parse('"{role}" is not reported as a role the map names nowhere'))
def _not_unmapped(world: dict[str, Any], role: str) -> None:
    assert not _findings(world, "unmapped", role), world["report"].findings


@then(parsers.parse('"{role}" is reported as omitted from a roster that names other roles'))
def _partial(world: dict[str, Any], role: str) -> None:
    found = _findings(world, "partial", role)
    assert len(found) == 1, world["report"].findings
    assert found[0].sites, found[0]


@then(parsers.parse('"{role}" is reported as a name no composed role backs'))
def _unbacked(world: dict[str, Any], role: str) -> None:
    found = _findings(world, "unbacked", role)
    assert len(found) == 1, world["report"].findings


@then(parsers.parse('"{role}" is not reported as a name no composed role backs'))
def _not_unbacked(world: dict[str, Any], role: str) -> None:
    assert not _findings(world, "unbacked", role), world["report"].findings


@then("the report names every line that lists two or more roles in a shape it does not read")
def _not_judged(world: dict[str, Any]) -> None:
    report = world["report"]
    assert report.not_judged, report
    for entry in report.not_judged:
        assert entry.source, entry
        assert len(entry.roles) >= 2, entry


@then("it states how many role designations it did read")
def _states_the_corpus(world: dict[str, Any]) -> None:
    assert world["report"].references, world["report"]


@then("the check reports the unbacked name and blocks")
def _config_check_blocks(world: dict[str, Any]) -> None:
    outcome = world["outcome"]
    combined = outcome.stdout + outcome.stderr
    assert "scout" in combined, combined
    assert outcome.exit_code == 1, combined


@then("the finding about that roster carries the `warn` severity")
def _roster_warns(world: dict[str, Any]) -> None:
    inferred = [
        finding
        for finding in world["report"].findings
        if finding.kind == "partial" and finding.severity == "warn"
    ]
    assert inferred, world["report"].findings


@then("a finding about a role designation carries the `error` severity")
def _designation_errors(world: dict[str, Any]) -> None:
    designated = [
        finding
        for finding in world["report"].findings
        if finding.kind == "unbacked" and finding.severity == "error"
    ]
    assert designated, world["report"].findings


# --- BDL-UX #252: the flow as this repository ships it -----------------------
#
# The steps above build a synthetic role in a temporary project. These run the
# shipped templates unchanged, because the defect was in what an ADOPTER
# receives and a synthetic fixture cannot see it.


@then("every composed role is named in the map")
def _every_role_named(world: dict[str, Any]) -> None:
    named = {name for reference in world["report"].references for name in reference.names}
    assert set(ROLE_NAMES) <= named, sorted(set(ROLE_NAMES) - named)


@then("every roster in the map names every composed role")
def _every_roster_complete(world: dict[str, Any]) -> None:
    for roster in world["report"].rosters:
        assert set(ROLE_NAMES) <= set(roster.names), (roster.source, roster.names)


@then("no role map finding is reported")
def _no_findings(world: dict[str, Any]) -> None:
    assert world["report"].findings == (), world["report"].findings


# --- BDL-068 `.84`: the map artifact is derived per declared tool ------------


def _artifact_names(world: dict[str, Any]) -> dict[str, str]:
    return {artifact.tool: artifact.name for artifact in world["report"].artifacts}


@then(parsers.parse('the map artifact read for "{tool}" is "{name}"'))
def _artifact_for(world: dict[str, Any], tool: str, name: str) -> None:
    read = _artifact_names(world)
    assert read.get(tool) == name, read


@then(parsers.parse('no map artifact is read for "{tool}"'))
def _no_artifact_for(world: dict[str, Any], tool: str) -> None:
    assert tool not in _artifact_names(world), _artifact_names(world)


@then(parsers.parse('that finding names the tool "{tool}" and the artifact "{name}"'))
def _finding_names_the_tool(world: dict[str, Any], tool: str, name: str) -> None:
    for finding in world["report"].findings:
        assert finding.tool == tool, finding
        assert finding.artifact == name, finding
        assert name in finding.why, finding.why


@then("that tool is reported as unreached and its reason names it")
def _unreached(world: dict[str, Any]) -> None:
    report = world["report"]
    assert [entry.tool for entry in report.unreached] == ["windsurf"], report.unreached
    assert "windsurf" in report.unreached[0].why, report.unreached[0].why


@then("it states how many declared tools a map artifact was read for and how many were not")
def _states_the_tool_population(world: dict[str, Any]) -> None:
    report = world["report"]
    assert report.tools, report
    assert len(report.artifacts) + len(report.unreached) == len(report.tools), report


@then("its role-map block names each declared tool beside the artifact read for it")
def _config_check_names_the_tools(world: dict[str, Any]) -> None:
    combined = world["outcome"].stdout + world["outcome"].stderr
    assert "claude -> .claude/CLAUDE.md" in combined, combined
    assert "1 of 1 declared tool(s)" in combined, combined
