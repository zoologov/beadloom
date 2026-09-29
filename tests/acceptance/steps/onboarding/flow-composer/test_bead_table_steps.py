"""Step implementations for the planning bead tables without a status column.

BDL-075: the PLAN skeleton (``beadloom-10er``) and the BRIEF skeleton
(``beadloom-3nwz``) each carried a Status column that nothing reconciled, a second
copy of what ACTIVE.md holds. Both now name the tracker id instead.

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
scenarios("../../../onboarding/flow-composer/brief_bead_table.feature")

#: The section of a planning skeleton that holds the bead table.
_BEADS_HEADING = "## Beads"

#: Where the full flow creates the beads: Step 3, item 6, up to item 7.
_FULL_CREATION_STEP = "**Create beads in tracker**"
_FULL_NEXT_STEP = "\n7. "

#: Where the simplified flow creates the beads: Step 1, item 4, up to item 5.
_BRIEF_STEP = "### Step 1: BRIEF"
_BRIEF_CREATION_STEP = "\n4. Create beads in tracker"
_BRIEF_NEXT_STEP = "\n5. "


@pytest.fixture()
def world() -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    return {}


def _one_line(text: str) -> str:
    """The text with its wrapping and its case undone."""
    return " ".join(text.split()).lower()


def _beads_section(skeleton: str) -> str:
    """The skeleton's ``## Beads`` section, up to the next level-two heading."""
    start = skeleton.index(f"\n{_BEADS_HEADING}\n")
    end = skeleton.find("\n## ", start + len(_BEADS_HEADING) + 1)
    return skeleton[start : end if end != -1 else len(skeleton)]


def _header_cells(section: str) -> list[str]:
    """The cells of the first table header in *section*."""
    header = next(line for line in section.splitlines() if line.startswith("|"))
    return [cell.strip() for cell in header.strip().strip("|").split("|")]


def _between(text: str, start_marker: str, end_marker: str, *, after: int = 0) -> str:
    """The text from *start_marker* (searched from *after*) up to *end_marker*."""
    start = text.index(start_marker, after)
    return text[start : text.index(end_marker, start + len(start_marker))]


def _says_to_fill_the_tracker_cell(step: str, document: str) -> bool:
    return "`Tracker`" in step and f"{document.lower()}.md" in _one_line(step)


@given("the templates command composed for a ddd python project")
def _composed_templates(world: dict[str, Any]) -> None:
    world["skeletons"] = planning_skeletons(config=DEFAULT_DOC_CONFIG)


@given("the task-init command composed for a ddd python project")
def _composed_task_init(world: dict[str, Any]) -> None:
    world["text"] = compose("commands", "task-init", config=DEFAULT_DOC_CONFIG).text


@then(parsers.parse('the {kind} skeleton\'s bead table has a "{column}" column'))
def _table_has_column(world: dict[str, Any], kind: str, column: str) -> None:
    assert column in _header_cells(_beads_section(world["skeletons"][kind]))


@then(parsers.parse('the {kind} skeleton\'s bead table has no "{column}" column'))
def _table_lacks_column(world: dict[str, Any], kind: str, column: str) -> None:
    assert column not in _header_cells(_beads_section(world["skeletons"][kind]))


@then(
    parsers.parse(
        "the {kind} skeleton says the status lives in ACTIVE.md, reconciled from the tracker"
    )
)
def _skeleton_names_the_status_home(world: dict[str, Any], kind: str) -> None:
    section = _one_line(_beads_section(world["skeletons"][kind]))
    assert "status lives in active.md" in section
    assert "reconciled from the tracker" in section


@then("the step that creates the beads says to fill the PLAN's Tracker column")
def _full_flow_fills_the_column(world: dict[str, Any]) -> None:
    step = _between(world["text"], _FULL_CREATION_STEP, _FULL_NEXT_STEP)
    assert _says_to_fill_the_tracker_cell(step, "PLAN")


@then("the simplified flow's step that creates the beads says to fill the BRIEF's Tracker column")
def _simplified_flow_fills_the_column(world: dict[str, Any]) -> None:
    text = world["text"]
    step = _between(text, _BRIEF_CREATION_STEP, _BRIEF_NEXT_STEP, after=text.index(_BRIEF_STEP))
    assert _says_to_fill_the_tracker_cell(step, "BRIEF")
