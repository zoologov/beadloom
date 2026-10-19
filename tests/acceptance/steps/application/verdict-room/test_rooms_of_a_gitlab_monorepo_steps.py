"""Steps of `application/verdict-room/rooms_of_a_gitlab_monorepo.feature`.

BDL-083 S2a (``beadloom-3618``), RFC D6, BDL-UX #332. The monorepo fixture is checked out
and committed as the adopter's clone, and ``rooms`` and ``ci`` run through the CLI, so what
the scenarios read is what an adopter reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/verdict-room/rooms_of_a_gitlab_monorepo.feature")


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _rooms_json(root: Path) -> dict[str, Any]:
    result = CliRunner().invoke(main, ["rooms", "--json", "--project", str(root)])
    assert result.exit_code == 0, result.output
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


@given("the monorepo fixture checked out")
def _checked_out(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = shipped_monorepo_checkout(tmp_path)


@given("the checkout's pipeline replaced by a Jenkinsfile")
def _jenkins(state: dict[str, Any]) -> None:
    root: Path = state["root"]
    (root / ".gitlab-ci.yml").unlink()
    (root / "Jenkinsfile").write_text("pipeline { agent any }\n", encoding="utf-8")


@when("the rooms are reported as JSON")
def _rooms(state: dict[str, Any]) -> None:
    state["rooms"] = _rooms_json(state["root"])


@when(parsers.parse("the gate runs in the {fmt} format"))
def _gate(state: dict[str, Any], fmt: str) -> None:
    result = CliRunner().invoke(main, ["ci", "--format", fmt, "--project", str(state["root"])])
    state["gate"] = result.stdout


@then(parsers.parse('a declared room comes from "{source}"'))
def _room_source(state: dict[str, Any], source: str) -> None:
    found = [room for room in state["rooms"]["declared"] if room["source"] == source]
    assert len(found) == 1, state["rooms"]["declared"]
    state["room"] = found[0]


@then(parsers.parse('that room declares the python "{version}"'))
def _room_python(state: dict[str, Any], version: str) -> None:
    assert state["room"]["dimensions"].get("python") == version, state["room"]


@then(parsers.parse('the interpreter floor is "{floor}"'))
def _floor(state: dict[str, Any], floor: str) -> None:
    assert state["rooms"]["floor"] == floor, state["rooms"]


@then("no unresolved entry names a packaging file at the root")
def _no_root_packaging(state: dict[str, Any]) -> None:
    sources = [entry["source"] for entry in state["rooms"]["unresolved"]]
    assert "pyproject.toml" not in sources, state["rooms"]["unresolved"]


@then(parsers.parse('the room notice counts "{count}"'))
def _notice(state: dict[str, Any], count: str) -> None:
    notices = [line for line in state["gate"].splitlines() if line.startswith("::notice::room")]
    assert len(notices) == 1, state["gate"]
    assert count in notices[0], notices[0]


@then(parsers.parse('the room block says "{words}"'))
def _room_block(state: dict[str, Any], words: str) -> None:
    lines = state["gate"].splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Room:"))
    block = "\n".join(lines[start : start + 3])
    assert words in block, block


@then(parsers.parse('the rooms JSON carries a not-derived reason that names "{name}"'))
def _not_derived(state: dict[str, Any], name: str) -> None:
    reason = _rooms_json(state["root"]).get("not_derived")
    assert isinstance(reason, str), reason
    assert name in reason, reason


@then(parsers.parse('the verifications not run name "{command}" from "{source}"'))
def _not_run(state: dict[str, Any], command: str, source: str) -> None:
    not_run = json.loads(state["gate"])["not_run"]
    pairs = {(item["command"], item["source"]) for item in not_run["not_performed"]}
    assert (command, source) in pairs, not_run
