"""Step implementations for `features/firing_record.feature` (BDL-061, `.56`).

Against the real record and the real liveness builder: the subject is what the
report says after rotation, and a hand-built summary would prove the fixture.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.firing import (
    ACTIVE_FIRINGS_CAP,
    ARCHIVE_RELPATH,
    FIRINGS_RELPATH,
    read_firings,
)
from beadloom.application.guards.liveness import build_liveness
from beadloom.application.guards.models import GuardOutcome, GuardVerdict

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/firing_record.feature")

_FILLER = "working-branch"
_LATER = "bead-claimed"
_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path, "filled": 0}


def _record(root: Path, guard: str, *, index: int, outcome: GuardOutcome) -> None:
    from beadloom.application.guards.firing import record_firing

    record_firing(
        root,
        GuardVerdict(
            guard=guard,
            outcome=outcome,
            why="a recorded evaluation",
            not_covered=("nothing beyond this guard's own question",),
        ),
        at=_START + timedelta(seconds=index),
    )


@given("a firing record filled to its cap by one guard")
def _fill(world: dict[str, Any]) -> None:
    for index in range(ACTIVE_FIRINGS_CAP):
        _record(world["root"], _FILLER, index=index, outcome=GuardOutcome.PASS)
    world["filled"] = ACTIVE_FIRINGS_CAP


@when("one more guard evaluation is recorded")
def _one_more(world: dict[str, Any]) -> None:
    _record(
        world["root"], _LATER, index=world["filled"], outcome=GuardOutcome.BLOCK
    )


def _row(world: dict[str, Any], guard: str) -> Any:
    rows = {row.guard: row for row in build_liveness(world["root"])}
    return rows[guard]


@then("the active record holds no more firings than its cap")
def _bounded(world: dict[str, Any]) -> None:
    active = (world["root"] / FIRINGS_RELPATH).read_text(encoding="utf-8")
    assert len(active.splitlines()) <= ACTIVE_FIRINGS_CAP, len(active.splitlines())
    assert len(read_firings(world["root"])) < world["filled"]


@then("the liveness report counts every firing ever recorded")
def _counts_all(world: dict[str, Any]) -> None:
    assert _row(world, _FILLER).fired_count == world["filled"]
    assert _row(world, _LATER).fired_count == 1


@then("the guard whose firings were rotated away is not reported as never-fired")
def _not_never_fired(world: dict[str, Any]) -> None:
    row = _row(world, _FILLER)
    assert not row.never_fired
    assert not row.idle


@then("its last recorded outcome is still reported")
def _last_outcome(world: dict[str, Any]) -> None:
    row = _row(world, _FILLER)
    assert row.last_outcome == GuardOutcome.PASS.value
    assert row.last_fired_at


@then("the rotated firings are still readable on disk")
def _archive_readable(world: dict[str, Any]) -> None:
    archive = world["root"] / ARCHIVE_RELPATH
    assert archive.is_file()
    assert len(archive.read_text(encoding="utf-8").splitlines()) == world["filled"]
