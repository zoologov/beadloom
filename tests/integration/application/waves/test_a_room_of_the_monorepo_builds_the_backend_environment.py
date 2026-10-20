"""``clean-room`` on the monorepo fixture builds the backend's environment (BDL-UX #333).

The first outside adopter's room held no environment: ``clean-room`` read the legs of
``.github/workflows`` only, the fixture's Python project lives under ``backend/`` with its own
``uv.lock`` and a GitLab pipeline, and the room exited 1 with "no environment was built",
leaving its verdict to whichever interpreter the machine held. Measured on the fixture with a
claimed bead: 9.0.0 exits 1 with no environment; this release exits 0 with
``backend/.venv`` installed from ``backend/uv.lock``.

The environment is built for real by ``uv``, as in ``clean_room_of_a_monorepo.feature``. The
tracker is a double at its boundary, because the bead a room is built for is not what is
measured here. Every field read below exists in 9.0.0's ``--json`` too, so the file fails
there on its assertions and not on a missing key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_checkout


class _TrackerHoldingTheBead:
    """A tracker that answers ``in_progress`` for every bead it is asked about."""

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        record = {"id": args[1], "status": "in_progress"}
        return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")


@pytest.fixture
def room(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """The JSON ``clean-room --json`` prints for a room carrying one backend file."""
    monkeypatch.setattr("beadloom.services.bd_seam.run_bd", _TrackerHoldingTheBead())
    root = shipped_monorepo_checkout(tmp_path / "checkout")
    sections = root / "backend" / "src" / "digest" / "sections.py"
    sections.write_text(
        sections.read_text(encoding="utf-8") + "\n# the bead's edit\n", encoding="utf-8"
    )
    result = CliRunner().invoke(
        main,
        [
            "clean-room",
            "desk-1",
            "--project",
            str(root),
            "--at",
            str(tmp_path / "rooms"),
            "--carry",
            "backend/src/digest/sections.py",
            "--json",
        ],
    )
    payload: dict[str, Any] = json.loads(result.stdout)
    payload["cli_exit_code"] = result.exit_code
    return payload


def test_the_room_of_a_backend_file_is_built_at_exit_0(room: dict[str, Any]) -> None:
    assert room["cli_exit_code"] == 0, room["findings"]


def test_the_room_holds_an_environment_under_the_backend_project(room: dict[str, Any]) -> None:
    environment = room["environment"]

    assert environment["built"] is True, environment
    assert Path(environment["python"]).is_relative_to(Path(room["room"]) / "backend" / ".venv")
