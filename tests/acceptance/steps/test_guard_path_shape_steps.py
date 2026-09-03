"""Step implementations for `features/guard_path_shape.feature` (beadloom-mr2l.60).

Against the real shape gate and the real evaluator. The scenarios that name a
platform pass that platform's :class:`PathFlavour` as an argument rather than
patching the interpreter: the flavour is the product's own input, so a scenario
run on Linux exercises the Windows rules through the code the Windows harness
would run, not through a double of it.

What the substitution does NOT reach is stated where it matters (the docstring of
:func:`~beadloom.application.guards.paths.resolve_edit_path` and the SPEC's
"Windows: unverified by decision"): a target the shape gate REFUSES is settled
here in full, because the refusal is lexical and returns before anything touches
the filesystem; a target it accepts is then resolved by whatever kernel is
running the suite.

The module is named ``test_*`` so default pytest collection picks the scenarios
up — the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, then, when

from beadloom.application.guards.contract import ClaimedBead, GuardProbes
from beadloom.application.guards.evaluation import evaluate_guard
from beadloom.application.guards.models import GuardOutcome
from beadloom.application.guards.paths import (
    NATIVE_PATHS,
    POSIX_PATHS,
    WINDOWS_PATHS,
    PathScope,
    resolve_edit_path,
)

if TYPE_CHECKING:
    from beadloom.application.guards.paths import PathFlavour

scenarios("../features/guard_path_shape.feature")

_GUARD = "bead-claimed"


class _Claimed:
    def claimed_beads(self) -> tuple[ClaimedBead, ...]:
        return (ClaimedBead(id="beadloom-0mdo.33", title="the refusal rule"),)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path}


def _judge(world: dict[str, Any], raw: str) -> None:
    """The shape gate's whole answer for *raw* under the scenario's platform."""
    flavour: PathFlavour = world.get("flavour", NATIVE_PATHS)
    world["resolved"] = resolve_edit_path(raw, world["root"], flavour=flavour)


@given("a bead is claimed")
def _a_bead_is_claimed(world: dict[str, Any]) -> None:
    world["probes"] = GuardProbes(tracker=_Claimed())


@given("a platform that separates directories with a forward slash")
def _a_posix_platform(world: dict[str, Any]) -> None:
    world["flavour"] = POSIX_PATHS


@given("a platform that separates directories with a backslash")
def _a_windows_platform(world: dict[str, Any]) -> None:
    world["flavour"] = WINDOWS_PATHS


@when("the guard is asked about a target spelled with this platform's own separator")
def _asked_about_a_native_spelling(world: dict[str, Any]) -> None:
    # ``str(Path(...))`` renders with the separator of whatever platform is
    # running this — a literal would hard-code one platform's answer into a
    # scenario whose whole subject is that they differ.
    world["verdict"] = evaluate_guard(
        _GUARD,
        project_root=world["root"],
        context={"path": str(Path("src", "app.py"))},
        probes=world["probes"],
    )


@when("the guard is asked about a target it refuses")
def _asked_about_a_refused_target(world: dict[str, Any]) -> None:
    # A leading ``~`` is refused on every platform, so this scenario has an
    # example wherever it is collected. A foreign separator would not: on a
    # platform that reads both spellings as separators there is no such target,
    # and the scenario would pass by having nothing to look at.
    world["verdict"] = evaluate_guard(
        _GUARD,
        project_root=world["root"],
        context={"path": "~/secrets.env"},
        probes=world["probes"],
    )


@when("the shape gate is asked about a target spelled with a backslash")
def _asked_about_a_backslash(world: dict[str, Any]) -> None:
    _judge(world, "src\\app.py")


@when("the shape gate is asked about a component ending in a dot")
def _asked_about_a_trailing_dot(world: dict[str, Any]) -> None:
    _judge(world, "src/app.py.")


@when("the shape gate is asked about a component that names a device")
def _asked_about_a_device_name(world: dict[str, Any]) -> None:
    _judge(world, "docs/CON.md")


@then("the guard reaches a verdict about that file rather than refusing to read it")
def _a_verdict_about_the_file(world: dict[str, Any]) -> None:
    verdict = world["verdict"]

    assert verdict.outcome is not GuardOutcome.ERROR, verdict
    assert "malformed" not in verdict.why, verdict.why


@then("the target is refused, and the reason names both readings of the character")
def _refused_naming_both_readings(world: dict[str, Any]) -> None:
    resolved = world["resolved"]

    assert resolved.scope is PathScope.MALFORMED, resolved
    assert resolved.relative is None, resolved
    assert "separates directories on the platform" in resolved.rejection
    assert "an ordinary file-name character on this one" in resolved.rejection


@then("the target is accepted, and it names the file that platform's writer would touch")
def _accepted_and_names_the_file(world: dict[str, Any]) -> None:
    resolved = world["resolved"]
    flavour: PathFlavour = world["flavour"]

    assert resolved.scope is not PathScope.MALFORMED, resolved
    assert flavour.parser("src\\app.py").parts == ("src", "app.py")


@then("the target is refused, and the reason says the platform would rewrite the name")
def _refused_for_rewriting(world: dict[str, Any]) -> None:
    resolved = world["resolved"]

    assert resolved.scope is PathScope.MALFORMED, resolved
    assert "strips" in resolved.rejection, resolved.rejection
    assert "separates directories" not in resolved.rejection, resolved.rejection


@then("the target is refused, and the reason says the write would reach a device")
def _refused_for_a_device(world: dict[str, Any]) -> None:
    resolved = world["resolved"]

    assert resolved.scope is PathScope.MALFORMED, resolved
    assert "device" in resolved.rejection, resolved.rejection
    assert "separates directories" not in resolved.rejection, resolved.rejection


@then("the target is accepted")
def _accepted(world: dict[str, Any]) -> None:
    resolved = world["resolved"]

    assert resolved.scope is not PathScope.MALFORMED, resolved


#: Named in a remediation, these would each be a claim about a platform rather
#: than about the one running — the class of sentence this bead is repairing.
_PLATFORM_NAMES = ("POSIX", "Windows", "Unix", "Linux", "macOS")


@then("the remediation names the separator this platform uses rather than a platform's name")
def _remediation_names_the_separator(world: dict[str, Any]) -> None:
    verdict = world["verdict"]

    assert verdict.outcome is GuardOutcome.ERROR, verdict
    assert repr(os.sep) in verdict.remediation, verdict.remediation
    for name in _PLATFORM_NAMES:
        assert name not in verdict.remediation, verdict.remediation
