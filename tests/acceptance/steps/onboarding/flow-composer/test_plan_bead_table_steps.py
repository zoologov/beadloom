"""Step implementations for BDL-075 T1 — the PLAN bead table without a status.

Every step reads a real composition of the shipped sources, for a ddd python
project, so the table is checked where an adopter meets it rather than in this
repository's own composed copy, which a hand edit could make agree with a test.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then

from beadloom.onboarding.composer import compose
from beadloom.onboarding.doc_templates import DEFAULT_DOC_CONFIG, planning_skeletons

scenarios("../../../onboarding/flow-composer/plan_bead_table.feature")

#: The section of the PLAN skeleton that holds the bead table.
_BEADS_HEADING = "## Beads"

#: Where `/task-init` creates the beads: Step 3, item 6, up to item 7.
_CREATION_STEP = "**Create beads in tracker**"
_NEXT_STEP = "\n7. "


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _one_line(text: str) -> str:
    """The text with its wrapping and its case undone."""
    return " ".join(text.split()).lower()


def _beads_section(skeleton: str) -> str:
    """The PLAN skeleton's ``## Beads`` section, up to the next level-two heading."""
    start = skeleton.index(f"\n{_BEADS_HEADING}\n")
    end = skeleton.find("\n## ", start + len(_BEADS_HEADING) + 1)
    return skeleton[start : end if end != -1 else len(skeleton)]


def _header_cells(section: str) -> list[str]:
    """The cells of the first table header in *section*."""
    header = next(line for line in section.splitlines() if line.startswith("|"))
    return [cell.strip() for cell in header.strip().strip("|").split("|")]


@given("the templates command composed for a ddd python project")
def _composed_templates(world: dict[str, Any]) -> None:
    world["plan"] = planning_skeletons(config=DEFAULT_DOC_CONFIG)["PLAN"]


@given("the task-init command composed for a ddd python project")
def _composed_task_init(world: dict[str, Any]) -> None:
    world["text"] = compose("commands", "task-init", config=DEFAULT_DOC_CONFIG).text


@then(parsers.parse('the PLAN skeleton\'s bead table has a "{column}" column'))
def _table_has_column(world: dict[str, Any], column: str) -> None:
    assert column in _header_cells(_beads_section(world["plan"]))


@then(parsers.parse('the PLAN skeleton\'s bead table has no "{column}" column'))
def _table_lacks_column(world: dict[str, Any], column: str) -> None:
    assert column not in _header_cells(_beads_section(world["plan"]))


@then("the PLAN skeleton says the status lives in ACTIVE.md, reconciled from the tracker")
def _skeleton_names_the_status_home(world: dict[str, Any]) -> None:
    section = _one_line(_beads_section(world["plan"]))
    assert "status lives in active.md" in section
    assert "reconciled from the tracker" in section


@then("the step that creates the beads says to fill the PLAN's Tracker column")
def _creation_step_fills_the_column(world: dict[str, Any]) -> None:
    text = world["text"]
    start = text.index(_CREATION_STEP)
    step = text[start : text.index(_NEXT_STEP, start)]
    assert "`Tracker`" in step
    assert "plan.md" in _one_line(step)
