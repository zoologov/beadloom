"""Every surface states a census that derived no room as a named skip, not as ``0 of 0``.

BDL-083 S2a (``beadloom-3618``), RFC D6, BDL-UX #332. Measured on 9.0.0 over the monorepo
fixture: ``ci --format github`` printed ``0 of 0 declared room(s) entered by this run``, a
count that reads as a measurement and names nothing. A census that derived no room now
carries the reason, and the gate's three formats and the ``rooms`` command print it.
"""

from __future__ import annotations

import json

from click.testing import CliRunner

from beadloom.application.gate import GateResult, GateStep
from beadloom.application.rooms import Room, RoomCensus
from beadloom.services.cli import main
from beadloom.services.commands.federation import (
    _format_gate_github,
    _format_gate_json,
    _gate_room_lines,
)

_REASON = "no readable pipeline: no `.github/workflows/*.yml` and no `.gitlab-ci.yml`"


def _result() -> GateResult:
    census = RoomCensus(
        current=Room(dimensions={"os": "Linux"}, source="this process"),
        not_derived=_REASON,
    )
    return GateResult(steps=[GateStep("lint", summary="0 violations")], room=census)


def test_the_rich_room_block_names_the_skip() -> None:
    lines = _gate_room_lines(_result())

    assert lines[1] == f"  rooms: not derived — {_REASON}"
    assert "0 of 0" not in "\n".join(lines)


def test_the_github_notice_names_the_skip_instead_of_a_count() -> None:
    out = _format_gate_github(_result())

    notice = next(line for line in out.splitlines() if line.startswith("::notice::room"))
    assert notice.endswith(f"— rooms: not derived — {_REASON}")
    assert "0 of 0" not in notice


def test_the_json_room_carries_the_reason() -> None:
    payload = json.loads(_format_gate_json(_result()))

    assert payload["room"]["not_derived"] == _REASON


def test_a_derived_census_carries_a_null_reason_in_json() -> None:
    result = _result()
    derived = GateResult(
        steps=result.steps,
        room=RoomCensus(current=Room(dimensions={}, source="this process")),
    )

    assert json.loads(_format_gate_json(derived))["room"]["not_derived"] is None


def test_the_rooms_command_names_the_skip_in_both_formats(tmp_path: object) -> None:
    runner = CliRunner()

    human = runner.invoke(main, ["rooms", "--project", str(tmp_path)])
    as_json = runner.invoke(main, ["rooms", "--json", "--project", str(tmp_path)])

    assert human.exit_code == 0, human.output
    assert "rooms: not derived — no readable pipeline" in human.stdout
    assert json.loads(as_json.stdout)["not_derived"].startswith("no readable pipeline")


def test_the_dimension_refusal_names_the_skip(tmp_path: object) -> None:
    result = CliRunner().invoke(
        main, ["rooms", "--dimension", "python", "--project", str(tmp_path)]
    )

    assert result.exit_code == 2
    assert "not derived — no readable pipeline" in result.stderr
