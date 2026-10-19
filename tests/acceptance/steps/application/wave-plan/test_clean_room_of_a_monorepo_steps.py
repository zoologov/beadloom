"""Steps of `application/wave-plan/clean_room_of_a_monorepo.feature`.

BDL-083 S2b (``beadloom-cptm``), RFC D6, BDL-UX #333 and #311. The monorepo fixture is
checked out and committed as the adopter's clone and ``clean-room`` runs through the CLI with
``--json``, so what the scenarios read is what an adopter reads. The tracker arrives through a
double, because the bead a room is built for is not what these scenarios are about.

The environment is built for real, from the fixture's own ``uv.lock``: a double of ``uv``
would prove the double, and the defect #311 records is a version the real resolver chose.
They do not skip without ``uv``: this suite is run by ``uv run pytest``, and a machine without
``uv`` is one where a room cannot read a ``uv.lock``, which the first scenario then reports red.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.committed_project import commit_project
from tests.support.shipped_monorepo import shipped_monorepo_checkout

scenarios("../../../application/wave-plan/clean_room_of_a_monorepo.feature")

_LOCKED_PACKAGE = re.compile(r'^name = "([^"]+)"\nversion = "([^"]+)"', re.MULTILINE)


class _TrackerHoldingTheBead:
    """A tracker that answers ``in_progress`` for every bead it is asked about."""

    def __call__(self, args: list[str], *, cwd: str | None = None) -> Any:
        from beadloom.services.bd_seam import BdResult

        record = {"id": args[1], "status": "in_progress"}
        return BdResult(returncode=0, stdout=json.dumps([record]), stderr="")


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("beadloom.services.bd_seam.run_bd", _TrackerHoldingTheBead())
    return {}


@given("the monorepo fixture checked out")
def _checked_out(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = shipped_monorepo_checkout(tmp_path / "checkout")
    state["rooms"] = tmp_path / "rooms"


@given(parsers.parse('the checkout\'s "{path}" deleted and committed'))
def _deleted(state: dict[str, Any], path: str) -> None:
    root: Path = state["root"]
    (root / path).unlink()
    commit_project(root)


@when(parsers.parse('bead "{bead}" builds its clean room carrying "{path}"'))
def _built(state: dict[str, Any], bead: str, path: str) -> None:
    result = CliRunner().invoke(
        main,
        [
            "clean-room",
            bead,
            "--project",
            str(state["root"]),
            "--at",
            str(state["rooms"]),
            "--carry",
            path,
            "--json",
        ],
    )
    payload: dict[str, Any] = json.loads(result.stdout)
    assert payload["built"] is True, payload
    state["payload"] = payload
    state["room"] = Path(payload["room"])


@then(parsers.parse('the room is built for the Python project "{directory}"'))
def _for_the_project(state: dict[str, Any], directory: str) -> None:
    distribution = state["payload"]["distribution"]
    assert distribution["directory"] == directory, distribution
    assert distribution["packaging"] == f"{directory}/pyproject.toml", distribution


@then(parsers.parse('the room\'s environment was installed from "{lock}"'))
def _from_the_lock(state: dict[str, Any], lock: str) -> None:
    environment = state["payload"]["environment"]
    assert environment["built"] is True, environment
    assert environment["lock"] == lock, environment
    assert "uv sync --frozen" in environment["resolution"], environment


@then(parsers.parse('the room\'s environment holds the version of "{package}" that "{lock}" pins'))
def _the_pinned_version(state: dict[str, Any], package: str, lock: str) -> None:
    pinned = dict(_LOCKED_PACKAGE.findall((state["root"] / lock).read_text(encoding="utf-8")))
    python = state["payload"]["environment"]["python"]
    installed = subprocess.run(  # noqa: S603
        [python, "-c", f"import importlib.metadata as m; print(m.version({package!r}))"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    assert installed == pinned[package], (installed, pinned[package])


@then(parsers.parse('every line of the hint names the interpreter under "{venv}" in the room'))
def _the_hints_interpreter(state: dict[str, Any], venv: str) -> None:
    interpreter = str(state["room"] / venv)
    hint: list[str] = state["payload"]["invocation"]
    assert hint, state["payload"]
    assert all(interpreter in line for line in hint), hint


@then("the hint names no path the room does not hold")
def _no_foreign_path(state: dict[str, Any]) -> None:
    room = str(state["room"])
    for line in state["payload"]["invocation"]:
        for token in re.split(r"[\s=\"]+", line):
            if token.startswith(room):
                assert Path(token).exists(), f"{token} is named and absent: {line}"


@then("the hint's suite line passes when it is run as printed")
def _the_suite_line_runs(state: dict[str, Any]) -> None:
    line = state["payload"]["invocation"][-1]
    assignment, _, command = line.partition(" ")
    name, _, value = assignment.partition("=")
    assert name == "PYTHONPATH", line
    result = subprocess.run(  # noqa: S603
        shlex.split(command),
        cwd=state["room"].parent,
        env={"PYTHONPATH": value, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@then("the room's environment says it was resolved outside a lock")
def _outside_a_lock(state: dict[str, Any]) -> None:
    environment = state["payload"]["environment"]
    assert environment["lock"] is None, environment
    assert "outside any lock" in environment["resolution"], environment


@then("the room's limits say a test that reads git fails there for that reason")
def _the_git_limit(state: dict[str, Any]) -> None:
    limits: list[str] = state["payload"]["limits"]
    assert any("reads git" in limit and "for that reason" in limit for limit in limits), limits
