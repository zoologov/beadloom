"""The room suite, re-run in a room this machine cannot enter (BDL-068 S3.7).

MEASURED, and this file exists because of it. `tests (3.10)` on PR #60 was red on
`assert len(not_entered) == 2` over a fixture declaring 3.10 and 3.11: two legs
are outside a Darwin run and one is outside a 3.10 run, so the literal was a
claim about the machine the assertion was authored on. Every local run is in 0 of
the 21 rooms this project declares, so no local measurement could say so — the
same shape the slice was opened to remove, at the level of the assertion instead
of the level of the skip.

A run cannot enter another room, so the ROOM is replaced and the suite is asked
again. `tests/room_simulation.py` does it in `pytest_configure`, before the test
modules import, so a module holding `from ... import current_room` stands in the
same room the product does.

**What the simulation cannot cover, stated rather than hidden.** It replaces
`current_room` and `platform.system`, and it leaves `sys` alone: replacing
`sys.version_info` was measured to break pydantic's annotation evaluation, so two
MCP verdict tests failed at the seam of the simulation instead of on a finding.
A test that derives its own expectation from the interpreter is therefore outside
this instrument, and that is the rule the population below selects by — not a
list of names, which would go stale the first time a file is added.
"""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The one room the bite test uses: inside the first leg of a fixture that
#: declares two, which is the arithmetic no run on a developer machine has.
A_ROOM_NO_LOCAL_RUN_ENTERS = "Linux/3.10"


def _rooms_the_declared_legs_describe() -> list[str]:
    """The rooms to re-judge in, derived from the legs this project declares.

    Deduplicated by the two dimensions a comparison can be made on, so the four
    interpreter legs give four rooms and the locale legs -- which declare no
    interpreter -- fold into this run's. A fifth leg is covered by the act that
    adds it to `ci.yml`, which is the whole reason the population is read rather
    than written down.
    """
    from beadloom.application.rooms import (
        RUNNER_PLATFORMS,
        current_room,
        derive_declared_rooms,
    )

    here = current_room().dimensions
    spelled = []
    for leg in derive_declared_rooms(REPO_ROOT).rooms:
        label = leg.dimensions.get("os", "")
        system = RUNNER_PLATFORMS.get(label.split("-", 1)[0].strip().lower()) or here["os"]
        python = leg.dimensions.get("python", here["python"])
        room = f"{system}/{python}"
        if room not in spelled:
            spelled.append(room)
    return spelled


def _modules_that_judge_a_verdicts_room() -> list[Path]:
    """Every test module that reads a room census out of a verdict.

    Derived by what a module says, so a module added later is judged by the act
    that adds it. Two exclusions, each a rule rather than a name: a module that
    derives its expectation from `sys.version_info` pins the current room's own
    derivation, which is the function the simulation replaces and therefore
    cannot be judged by it; and this module is the runner, and running the runner
    inside its own run measures nothing.
    """
    here = Path(__file__).resolve()
    found = []
    for path in sorted((REPO_ROOT / "tests").rglob("test_*.py")):
        if path.resolve() == here:
            continue
        text = path.read_text(encoding="utf-8")
        if "not_entered" not in text and "not entered" not in text:
            continue
        if "sys.version_info" in text:
            continue
        found.append(path)
    return found


def _run_in_a_room(modules: list[Path], room: str | None, report: Path) -> list[tuple[str, str]]:
    """Run *modules* standing in *room*, and read per-test outcomes from JUnit.

    Outcomes rather than the exit code: a module that fails to collect and one
    whose assertion is room-dependent are different findings, and the difference
    is the whole question.
    """
    environment = {"PYTHONPATH": str(REPO_ROOT)}
    plugin = ["-p", "tests.room_simulation"] if room else []
    if room:
        environment["BEADLOOM_SIMULATED_ROOM"] = room
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "pytest",
            *plugin,
            *[str(path) for path in modules],
            "-p",
            "no:cacheprovider",
            "--junitxml",
            str(report),
            "-q",
        ],
        cwd=REPO_ROOT,
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        check=False,
    )
    if not report.exists():  # pragma: no cover - only on a collection crash
        pytest.fail(f"pytest produced no report:\n{completed.stdout}\n{completed.stderr}")
    outcomes = []
    # S314: the input is the JUnit report pytest just wrote in a temporary
    # directory, not untrusted data.
    for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314
        children = {child.tag for child in case}
        if "skipped" in children:
            outcome = "skipped"
        elif children & {"failure", "error"}:
            outcome = "failed"
        else:
            outcome = "passed"
        outcomes.append((f"{case.get('classname')}::{case.get('name')}", outcome))
    return outcomes


class TestTheRoomSuiteHoldsInARoomThisRunIsNotIn:
    """An assertion whose number depends on the room it is measured in is a defect."""

    def test_the_population_is_found_rather_than_listed(self) -> None:
        """The instrument judges something, and says what."""
        modules = _modules_that_judge_a_verdicts_room()

        assert modules, "no module reads a room census out of a verdict"
        assert all(path.is_file() for path in modules)

    @pytest.mark.parametrize("room", _rooms_the_declared_legs_describe())
    def test_every_module_that_judges_a_verdicts_room_passes_inside_a_declared_leg(
        self, room: str, tmp_path: Path
    ) -> None:
        """The measurement no run on this machine can take, taken in every leg.

        Green here is NOT evidence about the `tests (3.10)` leg: the interpreter
        is this run's and only the room is fabricated. It is evidence that no
        assertion in the population changes its answer with the room, which is
        the thing that reddened that leg while three others were green.
        """
        outcomes = _run_in_a_room(
            _modules_that_judge_a_verdicts_room(),
            room,
            tmp_path / "simulated.xml",
        )

        assert outcomes
        assert [name for name, outcome in outcomes if outcome == "failed"] == []

    def test_a_count_written_as_a_literal_is_caught_by_the_simulation(
        self, tmp_path: Path
    ) -> None:
        """TESTS MUST BITE: the instrument's failing branch, on the defect itself.

        The assertion PR #60 was red on is written out again, into a module of
        its own, and run in both rooms. It passes where it was authored and fails
        inside the leg — which is the property the instrument exists to have, and
        a green simulation over a suite nobody has broken cannot demonstrate it.
        """
        # Arrange
        module = tmp_path / "test_a_room_dependent_literal.py"
        module.write_text(_A_ROOM_DEPENDENT_LITERAL, encoding="utf-8")

        # Act
        at_home = _run_in_a_room([module], None, tmp_path / "home.xml")
        inside = _run_in_a_room([module], A_ROOM_NO_LOCAL_RUN_ENTERS, tmp_path / "leg.xml")

        # Assert
        assert [outcome for _, outcome in at_home] == ["passed"]
        assert [outcome for _, outcome in inside] == ["failed"]


#: The defect, written as a module the instrument can be pointed at. It is the
#: assertion `tests/test_gate_verdict_room.py` carried until this bead.
_A_ROOM_DEPENDENT_LITERAL = '''
import json

from click.testing import CliRunner

from beadloom.services.cli import main


def test_the_gap_is_two(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\\n"
        "  tests:\\n"
        "    runs-on: ubuntu-latest\\n"
        "    strategy:\\n"
        "      matrix:\\n"
        '        python-version: ["3.10", "3.11"]\\n',
        encoding="utf-8",
    )
    outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path), "--json"])
    payload = json.loads(outcome.stdout)
    assert len([r for r in payload["declared"] if not r["entered"]]) == 2
'''
