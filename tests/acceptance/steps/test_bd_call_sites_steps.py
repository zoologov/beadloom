"""Step implementations for the bd call-site population (BDL-068 S5, CONTEXT Q4).

Thin, like every other acceptance module here: the derivation runs for real over
text and over Python source the steps build. Nothing invokes ``bd`` — the check
is about what our call FORMS assume, which is a property of our artifacts and of
a recorded measurement, not of the tracker in front of us.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.bd_seam.assumptions import (
    BD_MEASURED_VERSION,
    VERDICT_HOLDS,
    VERDICT_SECURED,
    VERDICT_UNMEASURED,
    VERDICT_UNSECURED,
    call_sites,
    report_of,
)
from beadloom.services.bd_seam.invocations import python_invocations, text_invocations

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/bd_call_sites.feature")

_VERDICTS = {
    "secured": VERDICT_SECURED,
    "unsecured": VERDICT_UNSECURED,
    "holds": VERDICT_HOLDS,
    "unmeasured": VERDICT_UNMEASURED,
}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {
        "root": tmp_path,
        "artifacts": [],
        "python": [],
        "unreachable": [],
        "sites": None,
        "report": None,
    }


@given(parsers.parse('an instruction artifact carrying "{text}"'))
def _artifact(world: dict[str, Any], text: str) -> None:
    label = f"artifact-{len(world['artifacts'])}.md"
    world["artifacts"].append((label, f"Run this before you commit:\n\n    {text}\n"))


@given("a python module invoking run_bd with argv from a module constant")
def _python_constant(world: dict[str, Any]) -> None:
    world["python"].append(
        (
            "probe.py",
            'ARGV = ["list", "--all", "--json"]\n'
            "\n"
            "def probe():\n"
            "    return run_bd(ARGV, cwd=None)\n",
        )
    )


@given("a python module invoking run_bd with a runtime bead id")
def _python_runtime(world: dict[str, Any]) -> None:
    world["python"].append(
        (
            "closer.py",
            "def close(bead):\n"
            '    return run_bd(["close", bead, "--suggest-next"], cwd=None)\n',
        )
    )


@given("a region the sweep cannot reach")
def _unreachable(world: dict[str, Any]) -> None:
    world["unreachable"].append(("the launch prompt", "it is not a file"))


@when("the bd call sites are derived")
def _derive(world: dict[str, Any]) -> None:
    invocations = (
        *text_invocations(world["artifacts"]),
        *python_invocations(world["python"]),
    )
    world["sites"] = call_sites(invocations)
    world["report"] = report_of(world["sites"], unreached=tuple(world["unreachable"]))


def _only_site(world: dict[str, Any]) -> Any:
    sites = world["sites"]
    assert sites, "the derivation found no call site at all"
    return sites[0]


@then(parsers.parse('the site assumes "{name}" and the assumption is "{verdict}"'))
def _assumption(world: dict[str, Any], name: str, verdict: str) -> None:
    site = _only_site(world)
    found = {a.name: a for a in site.assumptions}
    assert name in found, f"{site.subcommand} assumes {sorted(found)}, not {name!r}"
    assert found[name].verdict == _VERDICTS[verdict]


@then("the assumption names the bd version it was measured against")
def _version_on_assumption(world: dict[str, Any]) -> None:
    site = _only_site(world)
    assert any(BD_MEASURED_VERSION in a.detail for a in site.assumptions)


@then(parsers.parse('the subcommand is still reported as "{subcommand}"'))
def _subcommand(world: dict[str, Any], subcommand: str) -> None:
    assert _only_site(world).subcommand == subcommand


@then("the site records that it carries an argument the derivation could not resolve")
def _unresolved_arg(world: dict[str, Any]) -> None:
    assert _only_site(world).unresolved_arguments > 0


@then("the report names the region it could not reach")
def _region(world: dict[str, Any]) -> None:
    assert any("launch prompt" in region for region, _ in world["report"].unreached)


@then("the report names the bd version every verdict was measured against")
def _version_on_report(world: dict[str, Any]) -> None:
    assert world["report"].measured_against == BD_MEASURED_VERSION
