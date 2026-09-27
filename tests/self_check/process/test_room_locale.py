"""Self-checks of this repository's agent roles, hooks, tracker and commits (BDL-074 A3).

Moved out of ``tests/test_room_locale.py``;
the product tests of the same code stay there.
Everything here asserts on this repository's own tree, so it carries the
``self_check`` marker by its folder (see ``tests/conftest.py``).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_room_locale import (
    _codec_of_a_child,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


#: The codec the `C` leg is, so the bite arm can say what it is contrasted with.
_C_CODEC = "ascii"


#: A module asserting that every declared leg was entered. Written out rather
#: than parametrised in-process, because the room is replaced at
#: `pytest_configure` and a process can only stand in one room.
_A_MODULE_THAT_ENTERS_THE_LOCALE_LEG = '''
import json

from click.testing import CliRunner

from beadloom.services.cli import main


def test_the_locale_leg_is_entered(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\\n"
        "  tests-locale:\\n"
        "    runs-on: ubuntu-latest\\n"
        "    strategy:\\n"
        "      matrix:\\n"
        '        locale: ["C"]\\n',
        encoding="utf-8",
    )
    outcome = CliRunner().invoke(main, ["rooms", "--project", str(tmp_path), "--json"])
    payload = json.loads(outcome.stdout)
    entered = [r for r in payload["declared"] if r["entered"]]
    assert entered == payload["declared"], payload["declared"]
'''


def _pytest_in_a_simulated_room(
    directory: Path, *, locale_name: str
) -> subprocess.CompletedProcess[str]:
    """Run the leg-entering module in a fabricated platform and a real locale."""
    module = directory / "test_enters_the_locale_leg.py"
    module.write_text(_A_MODULE_THAT_ENTERS_THE_LOCALE_LEG, encoding="utf-8")
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "tests.room_simulation",
            str(module),
            "-p",
            "no:cacheprovider",
            "-q",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
            "BEADLOOM_SIMULATED_ROOM": f"Linux/{sys.version_info[0]}.{sys.version_info[1]}",
            "LC_ALL": locale_name,
            "PYTHONUTF8": "0",
            "PYTHONCOERCECLOCALE": "0",
        },
    )


class TestTheLegIsEnterableFromADeveloperMachine:
    """The point of the dimension: the leg this project keeps tripping on.

    `tests/room_simulation.py` fabricates the platform and the interpreter, and
    it carries the locale through UNCHANGED — the locale is the one dimension of
    a CI leg a developer machine can genuinely be in, so fabricating it would
    manufacture the coverage the census exists to refuse. Together they make
    `tests-locale (C)` reachable from a laptop, which is what BDL-061 S2, PR #61
    and PR #62 each needed and did not have.

    Both arms are run, because a green simulation over a suite nobody has broken
    demonstrates nothing: the same module passes under an ASCII locale and fails
    under this machine's own.
    """

    def test_the_locale_leg_is_entered_under_an_ascii_locale(self, tmp_path: Path) -> None:
        outcome = _pytest_in_a_simulated_room(tmp_path, locale_name="C")

        assert outcome.returncode == 0, outcome.stdout + outcome.stderr

    def test_the_same_module_fails_when_the_locale_is_not_the_legs(
        self, tmp_path: Path
    ) -> None:
        """The bite: the simulation carries the locale rather than assuming it."""
        codec = _codec_of_a_child("en_US.UTF-8")
        if codec == _C_CODEC:
            pytest.skip("this machine cannot leave the ASCII room, so there is no other arm")

        outcome = _pytest_in_a_simulated_room(tmp_path, locale_name="en_US.UTF-8")

        assert outcome.returncode != 0, outcome.stdout
