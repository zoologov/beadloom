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
"""

from __future__ import annotations

import os
import platform

from beadloom.application import rooms

#: The environment variable the caller names the simulated room in.
SIMULATED_ROOM_ENV = "BEADLOOM_SIMULATED_ROOM"


def pytest_configure(config: object) -> None:
    """Stand the whole session in the room the environment names."""
    spelled = os.environ.get(SIMULATED_ROOM_ENV, "")
    if not spelled:
        return
    system, _, python = spelled.partition("/")
    here = rooms.current_room()
    fabricated = rooms.Room(
        dimensions={
            **here.dimensions,
            "os": system,
            "python": python,
            "python_full": f"{python}.0",
        },
        # The source is this run's own: a simulated room is still the room this
        # process reports itself in, and a test asserting that would otherwise
        # fail for the simulation rather than for a finding.
        source=here.source,
    )
    rooms.current_room = lambda: fabricated
    # `platform.system` is patched beside it so a test comparing the verdict
    # against the platform reads the same answer the census read. `sys` is NOT
    # patched: replacing `sys.version_info` was measured to break pydantic's
    # annotation evaluation, so the MCP verdict tests failed at the seam of the
    # simulation rather than on a finding. The cost of leaving it alone is that a
    # test deriving its own expectation from the interpreter is outside this
    # simulation, which is the rule the caller selects its population by.
    platform.system = lambda: system

