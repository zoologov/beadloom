"""A pytest plugin that runs a suite as if it were taken in another room.

`beadloom.application.rooms.current_room` derives the room from `platform` and
`sys`, and takes no argument on purpose: a room a caller can spell is a room a
caller can spell wrongly. So a run that wants to stand somewhere else replaces
that function -- and this plugin does it in `pytest_configure`, BEFORE the test
modules are imported, so a module holding `from ... import current_room` binds to
the same fabricated room the product sees. Patching it later leaves the tests and
the product standing in different rooms, which produces failures that are
artefacts of the simulation rather than findings.

Used by `tests/test_room_dependent_assertions.py`, which runs the room suite in a
room no local run can enter. The room is read from BEADLOOM_SIMULATED_ROOM as
`<os>/<python>` so the caller names it, rather than this file carrying a list.

THE LOCALE IS CARRIED THROUGH, NEVER FABRICATED, and the grammar above has no
third field on purpose (BDL-068 S6, BDL-UX #248). A developer machine cannot be
Ubuntu and cannot be another interpreter, so those two are replaced. It CAN be
under the leg's locale -- `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0` puts this
process in the ascii room for real -- so the locale arrives in `here.dimensions`
already true, and a spelling that let a caller name one would manufacture the
coverage the census exists to refuse. Together the two halves make
`tests-locale (C)` enterable from a laptop, which BDL-061 S2, PR #61 and PR #62
each needed and did not have; `tests/test_room_locale.py::
TestTheLegIsEnterableFromADeveloperMachine` asserts both arms of it.
"""

from __future__ import annotations

import os
import platform

import pytest

from beadloom.application import rooms

#: The environment variable the caller names the simulated room in.
SIMULATED_ROOM_ENV = "BEADLOOM_SIMULATED_ROOM"


def pytest_configure(config: object) -> None:
    """Stand the whole session in the room the environment names."""
    spelled = os.environ.get(SIMULATED_ROOM_ENV, "")
    if not spelled:
        return
    named, _, python = spelled.partition("/")
    system = _platform_named(named)
    full = f"{python}.0"
    here = rooms.current_room()
    fabricated = rooms.Room(
        dimensions={
            **here.dimensions,
            "os": system,
            "python": python,
            "python_full": full,
        },
        # The source is this run's own: a simulated room is still the room this
        # process reports itself in, and a test asserting that would otherwise
        # fail for the simulation rather than for a finding.
        source=here.source,
    )
    rooms.current_room = lambda: fabricated
    # `platform.system` and `platform.python_version` are patched beside it so a
    # test comparing the verdict against the platform reads the same answer the
    # census read. The second was added in BDL-068 S6 with the measurement that
    # asked for it: run suite-wide in a well-formed room this plugin manufactured
    # three failures, all one cause -- `python_full` is fabricated as `3.13.0`
    # while `platform.python_version()` kept answering `3.13.7`, so the room and
    # the interpreter disagreed about one fact, which is the class this epic
    # exists to remove. Four sites read it: `application/rooms.py` produces it and
    # three mutation-verdict assertions read it back.
    #
    # `sys` is still NOT patched: replacing `sys.version_info` was measured to
    # break pydantic's annotation evaluation, so the MCP verdict tests failed at
    # the seam of the simulation rather than on a finding. The cost of leaving it
    # alone is that a test deriving its expectation from `sys` is outside this
    # simulation, which is the rule the caller selects its population by.
    platform.system = lambda: system
    platform.python_version = lambda: full


def _platform_named(spelled: str) -> str:
    """What `platform.system()` would return for the room a caller named.

    A RUNNER LABEL is accepted and translated, because the caller's list of
    rooms comes from a CI matrix and `ubuntu-latest` is what a leg is called.
    Measured, and this is why the translation exists (BDL-068 S6, BDL-UX #248):
    a suite-wide run spelled `ubuntu-latest/3.13` reported 13 failures in a clean
    room, against 3 for `Linux/3.13` over the same tree. The census compares the
    label against `platform.system()`, so a label in the current room's `os`
    matches NO leg and every room assertion in the suite fails as an artefact of
    the invocation. Nothing said so, and `beadloom-0mdo.49` attributed those
    failures to the plugin.

    A spelling in neither vocabulary stops the session instead of standing the
    run in a room that cannot exist: 13 silent artefacts is the outcome this
    refusal replaces.
    """
    family = spelled.split("-", 1)[0].strip().lower()
    if family in rooms.RUNNER_PLATFORMS:
        return rooms.RUNNER_PLATFORMS[family]
    if spelled in set(rooms.RUNNER_PLATFORMS.values()):
        return spelled
    raise pytest.UsageError(
        f"{SIMULATED_ROOM_ENV}=`{spelled}` names neither a platform nor a runner "
        f"label: `{'`, `'.join(sorted(set(rooms.RUNNER_PLATFORMS.values())))}` are "
        f"what `platform.system()` reports and `{'`, `'.join(sorted(rooms.RUNNER_PLATFORMS))}` "
        "are the label families a workflow declares"
    )

