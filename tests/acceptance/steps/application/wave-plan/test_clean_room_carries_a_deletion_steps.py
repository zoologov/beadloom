"""Steps of `application/wave-plan/clean_room_carries_a_deletion.feature`.

BDL-083 S2d (``beadloom-flrc``), RFC D6, BDL-UX #335. The monorepo fixture is checked out and
committed as the adopter's clone, the working tree is changed the way a bead and its neighbour
change it, and ``clean-room`` runs through the CLI with ``--json``, so what the scenarios read
is what an adopter reads. The tracker arrives through a double, because the bead a room is
built for is not what these scenarios are about, and ``--no-environment`` is passed because
the room's interpreter is not either: the environment's own scenarios build one for real.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_checkout

scenarios("../../../application/wave-plan/clean_room_carries_a_deletion.feature")

_TEXT = "utf-8"


class _TrackerHoldingTheBead:
    """A tracker that answers ``in_progress`` for every bead it is asked about."""

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        record = {"id": args[1], "status": "in_progress"}
        return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("beadloom.services.bd_seam.run_bd", _TrackerHoldingTheBead())
    return {"renamed": []}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        encoding=_TEXT,
    ).stdout


def _clean_room(state: dict[str, Any], bead: str, *options: str) -> dict[str, Any]:
    result = CliRunner().invoke(
        main,
        [
            "clean-room",
            bead,
            "--project",
            str(state["root"]),
            "--at",
            str(state["rooms"]),
            "--no-environment",
            "--json",
            *options,
        ],
    )
    payload: dict[str, Any] = json.loads(result.stdout)
    state["payload"] = payload
    state["room"] = Path(payload["room"])
    return payload


def _carrying(paths: list[str]) -> list[str]:
    return [option for path in paths for option in ("--carry", path)]


@given("the monorepo fixture checked out")
def _checked_out(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = shipped_monorepo_checkout(tmp_path / "checkout")
    state["rooms"] = tmp_path / "rooms"


@given(parsers.re(r'the checkout renames "(?P<old>[^"]+)" to "(?P<new>[^"]+)"'))
def _renames(state: dict[str, Any], old: str, new: str) -> None:
    root: Path = state["root"]
    olds = _git(root, "ls-files", "-z", "--", old).split("\0")
    _git(root, "mv", old, new)
    for before in filter(None, olds):
        after = new + before[len(old) :]
        (root / after).write_text(
            (root / after).read_text(encoding=_TEXT) + "# renamed by the bead\n", encoding=_TEXT
        )
        state["renamed"].append((before, after))


@given(parsers.re(r'the checkout deletes "(?P<path>[^"]+)"'))
def _deletes(state: dict[str, Any], path: str) -> None:
    (state["root"] / path).unlink()


@given(parsers.re(r'a neighbour has edited "(?P<path>[^"]+)" in the working tree'))
def _neighbour_edits(state: dict[str, Any], path: str) -> None:
    target: Path = state["root"] / path
    target.write_text(target.read_text(encoding=_TEXT) + "\nA neighbour's line.\n", encoding=_TEXT)


@given(parsers.re(r'a neighbour has created "(?P<path>[^"]+)" in the working tree'))
def _neighbour_creates(state: dict[str, Any], path: str) -> None:
    (state["root"] / path).write_text("export const round = 1;\n", encoding=_TEXT)


@given(parsers.re(r'bead "(?P<bead>[^"]+)" has built its clean room carrying "(?P<path>[^"]+)"'))
def _built_before(state: dict[str, Any], bead: str, path: str) -> None:
    payload = _clean_room(state, bead, "--carry", path)
    assert payload["built"] is True, payload


@when(
    parsers.re(
        r'bead "(?P<bead>[^"]+)" builds its clean room carrying "(?P<first>[^"]+)"'
        r'(?: and "(?P<second>[^"]+)")?$'
    )
)
def _builds(state: dict[str, Any], bead: str, first: str, second: str | None) -> None:
    _clean_room(state, bead, *_carrying([first] + ([second] if second else [])))


@when(
    parsers.re(r'bead "(?P<bead>[^"]+)" builds its clean room carrying every path of the rename')
)
def _builds_the_rename(state: dict[str, Any], bead: str) -> None:
    paths = [path for pair in state["renamed"] for path in pair]
    _clean_room(state, bead, *_carrying(paths))


@when(parsers.re(r'bead "(?P<bead>[^"]+)" rebuilds its clean room naming no files'))
def _rebuilds(state: dict[str, Any], bead: str) -> None:
    _clean_room(state, bead, "--rebuild")


@then("the room is built")
def _built(state: dict[str, Any]) -> None:
    assert state["payload"]["built"] is True, state["payload"]


@then("no room is built")
def _not_built(state: dict[str, Any]) -> None:
    assert state["payload"]["built"] is False, state["payload"]
    assert not state["room"].exists()


@then(parsers.re(r'the refusal is reported as "(?P<reason>[^"]+)"'))
def _refusal(state: dict[str, Any], reason: str) -> None:
    assert state["payload"]["refusal"] == reason, state["payload"]


@then(parsers.re(r'the room does not hold "(?P<path>[^"]+)"'))
def _absent(state: dict[str, Any], path: str) -> None:
    assert not (state["room"] / path).exists(), path


@then(parsers.re(r'the room holds the working tree\'s "(?P<path>[^"]+)"'))
def _the_trees(state: dict[str, Any], path: str) -> None:
    held = (state["room"] / path).read_text(encoding=_TEXT)
    assert held == (state["root"] / path).read_text(encoding=_TEXT)


@then(parsers.re(r'the room holds HEAD\'s "(?P<path>[^"]+)"'))
def _heads(state: dict[str, Any], path: str) -> None:
    held = (state["room"] / path).read_text(encoding=_TEXT)
    assert held == _git(state["root"], "show", f"HEAD:{path}")


@then(parsers.re(r'the room reports "(?P<path>[^"]+)" as deleted'))
def _reported_deleted(state: dict[str, Any], path: str) -> None:
    assert path in state["payload"]["deleted"], state["payload"]
    assert path not in state["payload"]["carried"], state["payload"]


def _not_carried(state: dict[str, Any]) -> dict[str, str]:
    listed: list[dict[str, str]] = state["payload"]["not_carried"]
    return {entry["path"]: entry["change"] for entry in listed}


@then(
    parsers.re(r'the room reports "(?P<path>[^"]+)" as an? (?P<change>\w+) file it does not carry')
)
def _reported_not_carried(state: dict[str, Any], path: str, change: str) -> None:
    assert _not_carried(state).get(path) == change, state["payload"]["not_carried"]


@then("the room reports no carried path among the files it does not carry")
def _carried_left_out(state: dict[str, Any]) -> None:
    named = set(state["payload"]["carried"]) | set(state["payload"]["deleted"])
    assert named, state["payload"]
    assert not named & set(_not_carried(state)), state["payload"]["not_carried"]
