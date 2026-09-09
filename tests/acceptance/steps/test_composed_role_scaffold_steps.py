"""Step implementations for `features/composed_role_scaffold.feature` (BDL-068 S6).

The scenarios exercise the path that writes role files from inside the scaffold
itself — ``include_agents=True``. That path is not dead: ``config-check --fix``
reaches it through ``refresh_agentic_flow_files`` for a repository that adopted
the flow before ``.beadloom/flow.yml`` existed, so what it writes is what such a
repository receives.

Two of the scenarios read the shipped package rather than a project, because
the defect they name is a property of the distribution: an asset that is a copy
of one repository's local file, and the function that made it one. The module is
named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.onboarding import agentic_flow_setup
from beadloom.onboarding.agentic_flow_setup import scaffold, templates_root
from beadloom.onboarding.composer import PROJECT_FLOW_DIRNAME
from beadloom.onboarding.flow_config import FlowConfig, resolve_flow_config
from beadloom.onboarding.role_composer import ROLE_NAMES, compose_all_roles

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/composed_role_scaffold.feature")

#: The line a team writes into its own project layer. It exists in no shipped
#: fragment, so finding it in a composed body can only mean the project layer
#: was read.
_PROJECT_FRAGMENT = "## OUR TEAM RULE\n\nEvery bead names the runbook it changes.\n"

#: The marker each architecture overlay opens with. Reading the marker rather
#: than a sentence keeps the assertion about which overlay was selected instead
#: of about the prose inside it.
_OVERLAY_MARKER = "<!-- overlay:{name} —"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    root = tmp_path / "acme"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "acme"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    return {"root": root, "architecture": None}


@given("a project the scaffold writes role files into")
def a_project(world: dict[str, Any]) -> None:
    assert world["root"].is_dir()


@given(parsers.parse('that project declares its own "{role}" role fragment'))
def a_project_role_fragment(world: dict[str, Any], role: str) -> None:
    fragment = world["root"] / PROJECT_FLOW_DIRNAME / "roles" / f"{role}.md"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    fragment.write_text(_PROJECT_FRAGMENT, encoding="utf-8")


@given(parsers.parse('that project\'s flow declares architecture "{architecture}"'))
def a_project_architecture(world: dict[str, Any], architecture: str) -> None:
    world["architecture"] = architecture


@given("the agentic-flow assets this package ships")
def the_shipped_assets(world: dict[str, Any]) -> None:
    world["assets"] = sorted(templates_root().rglob("*.md.txt"))
    assert world["assets"], "the package ships no agentic-flow assets at all"


@given("the module that scaffolds the agentic flow")
def the_scaffold_module(world: dict[str, Any]) -> None:
    world["module"] = agentic_flow_setup


@when("the scaffold writes its role files")
def the_scaffold_runs(world: dict[str, Any]) -> None:
    config = resolve_flow_config(world["root"])
    if world["architecture"] is not None:
        config = FlowConfig(
            tools=config.tools,
            architecture=world["architecture"],
            stack=config.stack,
            language=config.language,
        )
    world["config"] = config
    world["result"] = scaffold(world["root"], include_agents=True, config=config)


@then("every role file it wrote is the composition for that project's own flow")
def every_role_file_is_the_composition(world: dict[str, Any]) -> None:
    expected = compose_all_roles(world["config"], world["root"])
    for role in ROLE_NAMES:
        on_disk = (world["root"] / ".claude" / "agents" / f"{role}.md").read_text(
            encoding="utf-8"
        )
        assert on_disk == expected[role], role


@then(parsers.parse('the fragment\'s text is in "{relpath}"'))
def the_fragment_is_in(world: dict[str, Any], relpath: str) -> None:
    body = (world["root"] / relpath).read_text(encoding="utf-8")
    assert _PROJECT_FRAGMENT.strip() in body


@then(parsers.parse('"{relpath}" carries the "{name}" architecture overlay'))
def carries_overlay(world: dict[str, Any], relpath: str, name: str) -> None:
    body = (world["root"] / relpath).read_text(encoding="utf-8")
    assert _OVERLAY_MARKER.format(name=name) in body


@then(parsers.parse('"{relpath}" carries no "{name}" architecture overlay'))
def carries_no_overlay(world: dict[str, Any], relpath: str, name: str) -> None:
    body = (world["root"] / relpath).read_text(encoding="utf-8")
    assert _OVERLAY_MARKER.format(name=name) not in body


@then("none of them is a role body")
def none_is_a_role_body(world: dict[str, Any]) -> None:
    roles = set(ROLE_NAMES)
    offenders = [
        asset.relative_to(templates_root()).as_posix()
        for asset in world["assets"]
        if asset.parent.name == "agents" or asset.name.removesuffix(".md.txt") in roles
    ]
    assert offenders == [], offenders


@then("it exposes nothing that writes package data")
def exposes_no_package_writer(world: dict[str, Any]) -> None:
    assert not hasattr(world["module"], "sync_agentic_flow")
