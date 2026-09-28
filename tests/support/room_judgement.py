"""The two judgements `features/verdict_room.feature` makes about a census.

Here rather than in the step module because the half about a leg the run IS
inside cannot be reached from a developer machine: this repository's legs are
ubuntu-latest and the machine the suite is authored on is Darwin. A unit test
drives these over a project that declares this run's own platform, and it cannot
import the step module to do it -- importing that module creates the scenarios,
whose binding tags are only handled by the acceptance suite's conftest.

Kept beside the steps, not under `src/`: this is what the scenario asserts, and
a scenario whose assertion lives in the product would be judging itself.
"""

from __future__ import annotations

from typing import Any

#: The platform each runner label names. Written here rather than read from
#: `beadloom.application.rooms`: a scenario that borrows the derivation it is
#: judging can only prove the derivation agrees with itself. The vocabulary is
#: the labels the feature and its drivers write, and one outside it is an error
#: rather than a silent "no difference".
_PLATFORM_OF_LABEL = {
    "ubuntu-latest": "Linux",
    "macos-latest": "Darwin",
    "windows-latest": "Windows",
}


def differs(dimension: str, declared: str, current: dict[str, Any]) -> bool:
    """Whether this run differs from *declared* along *dimension*."""
    if dimension == "os":
        if declared not in _PLATFORM_OF_LABEL:
            raise AssertionError(f"this feature declares no platform for {declared!r}")
        return bool(_PLATFORM_OF_LABEL[declared] != current["os"])
    if dimension == "python":
        return bool(declared != current["python"])
    raise AssertionError(f"the scenario declares no dimension {dimension!r}")


def legs_not_entered_naming_no_difference(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """The legs this run did not enter whose reason does not name the difference.

    Empty is the scenario's claim. A leg reported as not entered for no stated
    dimension, or for a dimension its reason leaves out, is a report that says
    where the run was not without saying what decided it.
    """
    current = payload["current"]
    faulty = []
    for room in [r for r in payload["declared"] if not r["entered"]]:
        differing = [
            key for key, want in room["dimensions"].items() if differs(key, want, current)
        ]
        if not differing or any(key not in room["why"] for key in differing):
            faulty.append(room)
    return faulty


def legs_entered_that_do_not_match(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """The legs reported as entered that this run does not actually match.

    Empty is the scenario's claim, and it is the half only a run inside a
    declared leg can make non-vacuously.
    """
    current = payload["current"]
    return [
        room
        for room in payload["declared"]
        if room["entered"]
        and (
            any(differs(key, want, current) for key, want in room["dimensions"].items())
            or room["why"] != ""
        )
    ]
