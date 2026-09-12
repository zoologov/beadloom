"""Step implementations for BDL-UX #284 (a) — where a person rules the axis rows.

Every step reads a real composition of the shipped sources, for a ddd python
project, so the guidance is checked where an adopter meets it rather than in
this repository's own composed copy — which a hand edit could make agree with a
test while the shipped fragment said nothing.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then

from beadloom.doc_sync.axes_section import AXES_HEADING, OWNS_UNREAD_COLUMN
from beadloom.onboarding.composer import compose
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG
from beadloom.onboarding.role_composer import compose_role

scenarios("../features/axes_ruling.feature")

#: The two sentences BDL-UX #284 asks for, as the shipped sources spell them.
AXIS_IS_NOT_A_ROLE = "the axis a node surfaced under is not its role"
CALLERS_CAN_BE_A_WORK_SITE = "a `callers` row can be a work site"

#: Where `/task-init` has the person rule the rows: Step 0.5, up to the next rule.
_RULING_STEP = "## Step 0.5"


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _step(text: str, heading: str) -> str:
    """The body of the step opening at *heading*, up to the next horizontal rule."""
    start = text.index(heading)
    end = text.find("\n---\n", start)
    return text[start : end if end != -1 else len(text)]


def _axes_skeletons(text: str) -> list[str]:
    """Every ``## Axes`` skeleton in the templates, up to the next level-two heading."""
    marker = f"\n## {AXES_HEADING}\n"
    skeletons: list[str] = []
    start = text.find(marker)
    while start != -1:
        end = text.find("\n## ", start + len(marker))
        skeletons.append(text[start : end if end != -1 else len(text)])
        start = text.find(marker, start + len(marker))
    return skeletons


def _one_line(text: str) -> str:
    """The text with its wrapping and its case undone.

    A sentence split at 95 columns, or opening a bold lead-in with a capital,
    is still the sentence.
    """
    return " ".join(text.split()).lower()


@given("the task-init command composed for a ddd python project")
def _composed_task_init(world: dict[str, Any]) -> None:
    world["text"] = compose("commands", "task-init", config=DEFAULT_DOC_CONFIG).text


@given("the templates command composed for a ddd python project")
def _composed_templates(world: dict[str, Any]) -> None:
    world["text"] = compose("commands", "templates", config=DEFAULT_DOC_CONFIG).text


@given("the Explore role composed for a ddd python project")
def _composed_explore(world: dict[str, Any]) -> None:
    world["text"] = compose_role("explore", architecture="ddd", stack=("python",))


@then("the step that rules the axis rows says the axis a node surfaced under is not its role")
def _ruling_step_says_not_a_role(world: dict[str, Any]) -> None:
    assert AXIS_IS_NOT_A_ROLE in _one_line(_step(world["text"], _RULING_STEP))


@then("that step says a callers row can be a work site")
def _ruling_step_says_work_site(world: dict[str, Any]) -> None:
    assert CALLERS_CAN_BE_A_WORK_SITE in _one_line(_step(world["text"], _RULING_STEP))


@then("that step points at the column naming what the node owns and was not read")
def _ruling_step_names_the_column(world: dict[str, Any]) -> None:
    assert f"`{OWNS_UNREAD_COLUMN}`" in _step(world["text"], _RULING_STEP)


@then("every Axes skeleton says the axis a node surfaced under is not its role")
def _skeletons_say_not_a_role(world: dict[str, Any]) -> None:
    skeletons = _axes_skeletons(world["text"])
    assert len(skeletons) >= 2, "the RFC and the BRIEF each carry an Axes skeleton"
    assert all(AXIS_IS_NOT_A_ROLE in _one_line(skeleton) for skeleton in skeletons)


@then("every Axes skeleton carries the column naming what the node owns and was not read")
def _skeletons_carry_the_column(world: dict[str, Any]) -> None:
    for skeleton in _axes_skeletons(world["text"]):
        header = next(line for line in skeleton.splitlines() if line.startswith("| Axis |"))
        assert f"| {OWNS_UNREAD_COLUMN} |" in header


@then("its deliverable table carries the column naming what the node owns and was not read")
def _explore_table_carries_the_column(world: dict[str, Any]) -> None:
    header = next(line for line in world["text"].splitlines() if line.startswith("| Axis |"))
    assert f"| {OWNS_UNREAD_COLUMN} |" in header


@then("it says the axis a node surfaced under is not its role")
def _explore_says_not_a_role(world: dict[str, Any]) -> None:
    assert AXIS_IS_NOT_A_ROLE in _one_line(world["text"])
