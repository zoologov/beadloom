"""Step implementations for BDL-068 S1.5 — the ``Explore`` role and the route check.

Thin by design: every step arranges real fragments, a real composition or a real
adopter project and runs the real derivation. Nothing is doubled, because a
scenario that passes against a double proves the double.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.work_item_routing import (
    FULL,
    SIMPLIFIED,
    task_init_routing,
)
from beadloom.doc_sync.work_item_type import (
    ROUTE_NOT_SUPPORTED_BY_THE_AXES,
    ROUTED_WITHOUT_AXES,
    check_work_item_types,
)
from beadloom.onboarding.agentic_flow_setup import AGENT_FILES, scaffold
from beadloom.onboarding.composer import SHARED_ROLE_FRAGMENTS
from beadloom.onboarding.config_sync import check_config_drift
from beadloom.onboarding.flow_config import load_flow_config
from beadloom.onboarding.role_adapters import generate_adapters
from beadloom.onboarding.role_composer import (
    compose_role,
    roles_in,
    roles_templates_root,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/explore_role.feature")
scenarios("../features/work_item_type.feature")

_EXPLORE = "explore"

_FLOW_YML = "tools: [claude]\narchitecture: ddd\nstack: [python]\n"


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


# ---------------------------------------------------------------------------
# The role population, derived from the shipped fragments
# ---------------------------------------------------------------------------


@given("the shipped role fragments")
def _shipped_fragments(world: dict[str, Any]) -> None:
    world["fragments"] = roles_templates_root() / "core"


@given("a role fragment directory holding one named fragment and one unnamed")
def _mixed_fragments(world: dict[str, Any], tmp_path: Path) -> None:
    directory = tmp_path / "core"
    directory.mkdir()
    (directory / "scout.md.txt").write_text(
        "---\nname: scout\ndescription: derives axes.\n---\n\nYou are the Scout.\n",
        encoding="utf-8",
    )
    (directory / "_house-style.md.txt").write_text(
        "\n<!-- Shared by every role. -->\n\n## House style\n",
        encoding="utf-8",
    )
    world["fragments"] = directory


@when("the role population is derived from them")
@when("the role population is derived from that directory")
def _derive_roles(world: dict[str, Any]) -> None:
    world["roles"] = roles_in(world["fragments"])


@then("explore is one of the roles")
def _explore_is_a_role(world: dict[str, Any]) -> None:
    assert _EXPLORE in world["roles"]


@then("the shared writing fragment is not one of the roles")
def _writing_is_not_a_role(world: dict[str, Any]) -> None:
    for shared in SHARED_ROLE_FRAGMENTS:
        assert shared not in world["roles"]


@then("only the named fragment is a role")
def _only_the_named_fragment(world: dict[str, Any]) -> None:
    assert world["roles"] == ("scout",)


@then("the vendored scaffold names exactly the same roles")
def _scaffold_agrees(world: dict[str, Any]) -> None:
    assert tuple(AGENT_FILES) == tuple(world["roles"])


# ---------------------------------------------------------------------------
# The role's own deliverable
# ---------------------------------------------------------------------------


@given("the Explore role composed for a ddd python project")
def _composed_explore(world: dict[str, Any]) -> None:
    world["role"] = compose_role(_EXPLORE, architecture="ddd", stack=("python",))


@then("it names the Axes section as its deliverable")
def _names_the_section(world: dict[str, Any]) -> None:
    assert "## Axes" in world["role"]


@then("it names the command the axes are derived by")
def _names_the_command(world: dict[str, Any]) -> None:
    assert "beadloom impact" in world["role"]


@then("it forbids returning a narrative instead")
def _forbids_narrative(world: dict[str, Any]) -> None:
    assert "narrative" in world["role"].lower()


# ---------------------------------------------------------------------------
# config-check sees the fifth adapter
# ---------------------------------------------------------------------------


@given("a project that adopted the flow and had its role adapters composed")
def _adopter(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "acme-service"
    (project / ".beadloom").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "acme-service"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    (project / ".beadloom" / "flow.yml").write_text(_FLOW_YML, encoding="utf-8")
    generate_adapters(load_flow_config(project), project)
    scaffold(project, include_agents=False)
    world["project"] = project


@when("the Explore adapter on disk is edited by hand")
def _edit_the_adapter(world: dict[str, Any]) -> None:
    adapter = world["project"] / ".claude" / "agents" / f"{_EXPLORE}.md"
    adapter.write_text(
        adapter.read_text(encoding="utf-8") + "\nReturn a narrative.\n",
        encoding="utf-8",
    )


@then("config-check reports the Explore adapter")
def _config_check_reports(world: dict[str, Any]) -> None:
    drifts = check_config_drift(world["project"], sqlite3.connect(":memory:"))
    assert any(f"agents/{_EXPLORE}.md" in drift.file for drift in drifts), [
        drift.file for drift in drifts
    ]


# ---------------------------------------------------------------------------
# The route a work item was decided into, checked against its axes
# ---------------------------------------------------------------------------


def _axes(rows: list[tuple[str, str]]) -> str:
    body = [
        "## Axes",
        "",
        "> **Derived by:** `beadloom impact src/pkg/thing.py` over `src/pkg`",
        "> **Seed:** `write_it` (effect `serialises-yaml`), under rule `reaches-an-effect-sink`",
        "> **Unresolved:** none",
        "",
        "| Axis | Node | Sites | In scope | Why |",
        "|---|---|---|---|---|",
    ]
    body.extend(
        f"| co-writers | {node} | 1 — `src/pkg/thing.py:1` | {scope} | measured |"
        for node, scope in rows
    )
    return "\n".join(body) + "\n"


def _work_item(world: dict[str, Any], name: str, kind: str, axes: str | None) -> None:
    text = f"# {kind}: {name}\n\n## Problem\n\nA thing is broken.\n"
    if axes is not None:
        text += "\n" + axes
    world.setdefault("documents", []).append(
        (f".claude/development/docs/features/{name}/{kind}.md", text)
    )


@given("a work item routed through the simplified flow with no Axes section")
def _simplified_without_axes(world: dict[str, Any]) -> None:
    _work_item(world, "ACME-1", "BRIEF", None)


@given("a work item routed through the simplified flow whose axes keep two nodes")
def _simplified_two_nodes(world: dict[str, Any]) -> None:
    _work_item(
        world, "ACME-2", "BRIEF", _axes([("graph-loader", "yes"), ("cli-commands", "yes")])
    )


@given("a work item routed through the simplified flow whose axes keep one node")
def _simplified_one_node(world: dict[str, Any]) -> None:
    _work_item(
        world, "ACME-3", "BRIEF", _axes([("graph-loader", "yes"), ("cli-commands", "no")])
    )


@given("a work item routed through the full flow with no Axes section")
def _full_without_axes(world: dict[str, Any]) -> None:
    _work_item(world, "ACME-4", "RFC", None)


@when("the work item's type is checked against its axes")
def _check_types(world: dict[str, Any]) -> None:
    world["report"] = check_work_item_types(
        world["documents"], simplified_kinds=frozenset({"BRIEF"})
    )


@then("the work item is reported as routed without axes")
def _reported_without_axes(world: dict[str, Any]) -> None:
    assert [f.check for f in world["report"].findings] == [ROUTED_WITHOUT_AXES]


@then("the work item is reported as routed past what its axes support")
def _reported_past_support(world: dict[str, Any]) -> None:
    assert [f.check for f in world["report"].findings] == [
        ROUTE_NOT_SUPPORTED_BY_THE_AXES
    ]


@then("the finding names both nodes")
def _names_both_nodes(world: dict[str, Any]) -> None:
    excerpt = world["report"].findings[0].excerpt
    assert "graph-loader" in excerpt
    assert "cli-commands" in excerpt


@then("the work item is not reported")
def _not_reported(world: dict[str, Any]) -> None:
    assert world["report"].findings == ()


# ---------------------------------------------------------------------------
# The routing itself, derived from the composed command
# ---------------------------------------------------------------------------


@given("the composed task-init command")
def _composed_task_init(world: dict[str, Any]) -> None:
    world["routing"] = task_init_routing()


@when("the work-item routing is derived from it")
def _routing_derived(world: dict[str, Any]) -> None:
    assert world["routing"].routes


@then("a bug is routed through the simplified flow")
def _bug_is_simplified(world: dict[str, Any]) -> None:
    assert world["routing"].flow_of("bug") == SIMPLIFIED


@then("an epic is routed through the full flow")
def _epic_is_full(world: dict[str, Any]) -> None:
    assert world["routing"].flow_of("epic") == FULL


@then("the simplified flow's documents include the BRIEF")
def _simplified_documents(world: dict[str, Any]) -> None:
    assert "BRIEF" in world["routing"].simplified_kinds


@then("the explore step is stated before the type decision")
def _explore_precedes(world: dict[str, Any]) -> None:
    routing = world["routing"]
    assert routing.explore_line is not None
    assert routing.decision_line is not None
    assert routing.explore_precedes_the_decision


@then("the explore step names the Explore role")
def _explore_step_names_the_role(world: dict[str, Any]) -> None:
    assert _EXPLORE in world["routing"].explore_step.lower()
