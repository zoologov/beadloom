"""Step implementations for the ACTIVE reconcile (BDL-068 S5, BDL-UX #210 and #207).

Thin, like every acceptance module here. Nothing invokes ``bd`` and nothing runs
``git``: the two things under test are how a row cell of OURS is read and how a
staging decision of OURS is taken, so the steps hand over the tracker's answer and
the commit's staged set directly. What a tracker or a git in front of the runner
happens to hold is not what these scenarios are about.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.active_table import (
    SHAPE_NO_ID,
    SHAPE_RANGE,
    SHAPE_UNKNOWN_TO_TRACKER,
    SHAPE_WITH_TEXT,
    decide_staging,
    reconcile_active_tables,
    resolve_row_bead_id,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/active_reconcile.feature")

_EPIC_DIR = "PROJ-1"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {
        "root": tmp_path,
        "statuses": {},
        "row": None,
        "result": None,
        "active": None,
        "decision": None,
        "staged": None,
        "candidates": (),
    }


def _write_table(root: Path, cells: tuple[str, ...]) -> Path:
    """An ACTIVE.md carrying one bead-status table whose first cells are *cells*."""
    directory = root / ".claude" / "development" / "docs" / "features" / _EPIC_DIR
    directory.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| {cell} | dev | ✓ done |" for cell in cells)
    path = directory / "ACTIVE.md"
    path.write_text(
        f"# ACTIVE\n\n| Bead | Role | Status |\n|------|------|--------|\n{rows}\n",
        encoding="utf-8",
    )
    return path


# --------------------------------------------------------------------------- #
# Given
# --------------------------------------------------------------------------- #


@given(parsers.parse("the tracker reports {bead_id} as closed"))
def _tracker_reports(world: dict[str, Any], bead_id: str) -> None:
    world["statuses"][bead_id] = "closed"


@given(parsers.parse('an ACTIVE table whose rows are {cells}'))
def _an_active_table(world: dict[str, Any], cells: str) -> None:
    parts = tuple(part.strip().strip('"') for part in cells.replace(" and ", ", ").split(","))
    world["active"] = _write_table(world["root"], parts)


@given(parsers.parse("the tracker reports {numbers} of that epic as closed"))
def _tracker_reports_epic(world: dict[str, Any], numbers: str) -> None:
    for number in (n.strip() for n in numbers.replace(" and ", ", ").split(",")):
        world["statuses"][f"proj-e{number}"] = "closed"


@given("the commit already stages the corrected ACTIVE.md")
def _commit_stages_it(world: dict[str, Any]) -> None:
    world["candidates"] = ("docs/ACTIVE.md",)
    world["staged"] = frozenset({"docs/ACTIVE.md"})


@given("the commit stages nothing")
def _commit_stages_nothing(world: dict[str, Any]) -> None:
    world["candidates"] = ("docs/ACTIVE.md",)
    world["staged"] = frozenset()


@given("the commit's staged paths cannot be read")
def _commit_scope_unreadable(world: dict[str, Any]) -> None:
    world["candidates"] = ("docs/ACTIVE.md",)
    world["staged"] = None


@given("the pre-commit hook this project installs")
def _the_hook(world: dict[str, Any]) -> None:
    from beadloom.services.commands.docsync import pre_commit_hook_body

    world["hook"] = pre_commit_hook_body(blocking=False)


# --------------------------------------------------------------------------- #
# When
# --------------------------------------------------------------------------- #


@when(parsers.parse('the row cell "{cell}" is resolved against the epic {prefix}'))
def _resolve_with_prefix(world: dict[str, Any], cell: str, prefix: str) -> None:
    world["row"] = resolve_row_bead_id(cell, world["statuses"], prefix=prefix)


@when(parsers.parse('the row cell "{cell}" is resolved'))
def _resolve(world: dict[str, Any], cell: str) -> None:
    world["row"] = resolve_row_bead_id(cell, world["statuses"])


@when("the tables are reconciled")
def _reconcile(world: dict[str, Any]) -> None:
    world["result"] = reconcile_active_tables(
        world["root"], dict(world["statuses"]), epic_prefixes={_EPIC_DIR: "proj-e"}
    )


@when("the reconcile decides what to stage")
def _decide(world: dict[str, Any]) -> None:
    world["decision"] = decide_staging(world["candidates"], world["staged"])


# --------------------------------------------------------------------------- #
# Then
# --------------------------------------------------------------------------- #


@then(parsers.parse("the row resolves to {bead_id}"))
def _resolves_to(world: dict[str, Any], bead_id: str) -> None:
    assert world["row"].bead_id == bead_id
    assert world["row"].reason is None


@then("the row does not resolve")
def _does_not_resolve(world: dict[str, Any]) -> None:
    assert world["row"].bead_id is None
    assert world["row"].reason


@then(parsers.parse('the reason names the shape "{shape}"'))
def _names_shape(world: dict[str, Any], shape: str) -> None:
    expected = {
        "names a bead and then adds text": SHAPE_WITH_TEXT,
        "names more than one bead": SHAPE_RANGE,
        "carries no bead id": SHAPE_NO_ID,
    }[shape]
    assert world["row"].shape == expected


@then(parsers.parse('the reason quotes "{text}"'))
def _reason_quotes(world: dict[str, Any], text: str) -> None:
    assert text in world["row"].reason


@then("the reason names the tracker rather than the cell")
def _reason_names_tracker(world: dict[str, Any]) -> None:
    assert world["row"].shape == SHAPE_UNKNOWN_TO_TRACKER
    assert "tracker" in world["row"].reason


@then(parsers.parse("{count:d} row resolved"))
def _rows_resolved(world: dict[str, Any], count: int) -> None:
    assert world["result"].rows_resolved == count


@then(
    parsers.parse(
        "the unresolved rows are counted as {with_text:d} with-text, "
        "{no_id:d} no-id and {ranges:d} range"
    )
)
def _counted_by_shape(
    world: dict[str, Any], with_text: int, no_id: int, ranges: int
) -> None:
    counts = world["result"].unresolved_by_shape
    assert counts.get(SHAPE_WITH_TEXT, 0) == with_text
    assert counts.get(SHAPE_NO_ID, 0) == no_id
    assert counts.get(SHAPE_RANGE, 0) == ranges


@then(parsers.parse("the bead {number} is reported as carried by no row"))
def _unlisted(world: dict[str, Any], number: str) -> None:
    named = {bead_id for _, bead_id in world["result"].unlisted_beads}
    assert f"proj-e{number}" in named


@then(parsers.parse("the table still has {count:d} row"))
def _table_row_count(world: dict[str, Any], count: int) -> None:
    body = world["active"].read_text(encoding="utf-8")
    data_rows = [
        line
        for line in body.splitlines()
        if line.startswith("|") and "Bead" not in line and not set(line) <= set("|-: ")
    ]
    assert len(data_rows) == count


@then("the ACTIVE.md is staged")
def _is_staged(world: dict[str, Any]) -> None:
    assert world["decision"].staged == ("docs/ACTIVE.md",)


@then("nothing is withheld")
def _nothing_withheld(world: dict[str, Any]) -> None:
    assert world["decision"].withheld == ()


@then("nothing is staged")
def _nothing_staged(world: dict[str, Any]) -> None:
    assert world["decision"].staged == ()


@then("the ACTIVE.md is withheld")
def _is_withheld(world: dict[str, Any]) -> None:
    assert world["decision"].withheld == ("docs/ACTIVE.md",)


@then("the decision states that the commit's scope could not be read")
def _scope_unreadable(world: dict[str, Any]) -> None:
    assert world["decision"].scope_unreadable is True
    assert "could not be read" in world["decision"].stated


@then("it runs no git add of its own")
def _no_git_add(world: dict[str, Any]) -> None:
    assert "git add" not in world["hook"]


@then("it reports the paths the reconcile withheld")
def _reports_withheld(world: dict[str, Any]) -> None:
    assert "withheld" in world["hook"]


@then(parsers.parse("the bead {number} is reported as named by a row this run could not read"))
def _named_by_an_unresolved_row(world: dict[str, Any], number: str) -> None:
    named = {bead_id for _, bead_id, _ in world["result"].beads_named_by_an_unresolved_row}
    assert f"proj-e{number}" in named


@then("the two populations name no bead in common")
def _populations_are_disjoint(world: dict[str, Any]) -> None:
    result = world["result"]
    unlisted = {bead_id for _, bead_id in result.unlisted_beads}
    named = {bead_id for _, bead_id, _ in result.beads_named_by_an_unresolved_row}
    assert unlisted & named == set()


@then(parsers.parse('the row quoted against the bead {number} is "{cell}"'))
def _row_quoted_against(world: dict[str, Any], number: str, cell: str) -> None:
    quoted = {
        bead_id: row_cell
        for _, bead_id, row_cell in world["result"].beads_named_by_an_unresolved_row
    }
    assert quoted[f"proj-e{number}"] == cell


@then(parsers.parse("the bead {number} is reported in neither population"))
def _in_neither_population(world: dict[str, Any], number: str) -> None:
    result = world["result"]
    bead_id = f"proj-e{number}"
    assert bead_id not in {b for _, b in result.unlisted_beads}
    assert bead_id not in {b for _, b, _ in result.beads_named_by_an_unresolved_row}
