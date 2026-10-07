"""Steps for `activity_on_a_shallow_history.feature`.

BDL-078 ``beadloom-btkd.9``. A real repository with dated commits, a real
``git clone --depth N`` of it over ``file://`` (a local path clone ignores
``--depth``), the real reindex through the command line and the real Gate:
nothing between the clone and the verdict is mocked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.gate import run_ci_gate
from beadloom.application.reindex import reindex
from beadloom.infrastructure.db import open_db
from beadloom.services.cli import main
from tests.support.dated_history import (
    FIRST_COMMIT_DAYS,
    WEB_LINES_30D,
    build_dated_project,
    shallow_clone,
)

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../infrastructure/git-activity/activity_on_a_shallow_history.feature")

#: The real present: the reindex measures its windows from it, so the history does too.
_NOW = datetime.now(tz=timezone.utc)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"tmp": tmp_path}


def _stored_activity(root: Path) -> dict[str, Any]:
    conn = open_db(root / ".beadloom" / "beadloom.db")
    try:
        return {
            str(row["ref_id"]): json.loads(row["extra"] or "{}").get("activity")
            for row in conn.execute("SELECT ref_id, extra FROM nodes")
        }
    finally:
        conn.close()


@given(parsers.parse("a project whose history reaches back {days:d} days"))
def _project(world: dict[str, Any], days: int) -> None:
    assert days == FIRST_COMMIT_DAYS, "the dated project's first commit is fixed"
    world["origin"] = build_dated_project(world["tmp"] / "origin", now=_NOW)


@given(parsers.re(r"a clone of it (?P<depth>\d+) commits? deep"))
def _clone(world: dict[str, Any], depth: str) -> None:
    world["clone"] = shallow_clone(world["origin"], world["tmp"] / "clone", int(depth))


@when("the clone is reindexed from the command line")
def _reindex_cli(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["reindex", "--project", str(world["clone"])])
    assert result.exit_code == 0, result.output
    world["output"] = result.output


@when("the Gate runs on the clone")
def _gate(world: dict[str, Any]) -> None:
    result = run_ci_gate(world["clone"], fail_on=None, hub_exports=[], no_reindex=False)
    world["step"] = next(step for step in result.steps if step.name == "reindex")


@then("no node of the clone records activity")
def _none_recorded(world: dict[str, Any]) -> None:
    stored = _stored_activity(world["clone"])
    assert set(stored) == {"web", "api"}
    assert all(activity is None for activity in stored.values()), stored


@then(parsers.parse('the reindex says activity was not measured on "{history}"'))
def _said_not_measured(world: dict[str, Any], history: str) -> None:
    line = next(
        (line for line in world["output"].splitlines() if line.startswith("Activity:")), ""
    )
    assert "not measured" in line, world["output"]
    assert history in line, world["output"]
    assert "fetch-depth: 0" in line, world["output"]


@then(
    parsers.parse('the Gate\'s reindex step warns that activity was not measured on "{history}"')
)
def _gate_warns(world: dict[str, Any], history: str) -> None:
    step = world["step"]
    assert step.status == "WARN", (step.status, step.summary)
    assert "activity not measured" in step.summary, step.summary
    assert history in step.summary, step.summary


@then("every node of the clone records the activity the full history gives it")
def _as_full(world: dict[str, Any]) -> None:
    reindex(world["origin"])
    full = _stored_activity(world["origin"])
    shallow = _stored_activity(world["clone"])
    assert full["web"]["lines_30d"] == WEB_LINES_30D, full
    assert full["api"]["level"] == "quiet", full
    assert shallow == full


@then(parsers.parse('the reindex says activity was measured on "{history}"'))
def _said_measured(world: dict[str, Any], history: str) -> None:
    line = next(
        (line for line in world["output"].splitlines() if line.startswith("Activity:")), ""
    )
    assert line.startswith("Activity: measured on"), world["output"]
    assert history in line, world["output"]
