"""Step implementations for the population a tracker answer covers (BDL-068 S5).

Thin, like every acceptance module here. Nothing invokes ``bd``: the steps hand
over the two things bd actually emits — the notice it prints on stderr and the
text it prints on stdout — because what is under test is how a call site of ours
reads them, not what the tracker in front of the runner happens to hold.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.bd_seam.answers import (
    COVERAGE_AS_ASKED,
    COVERAGE_FILTERED,
    COVERAGE_TRUNCATED,
    COVERAGE_UNCHECKED,
    NOT_COMPARED,
    NOTHING_TO_CHECK,
    confirmed_suggestion,
    coverage_of,
)
from beadloom.services.bd_seam.assumptions import (
    VERDICT_SECURED,
    VERDICT_UNSECURED,
    call_sites,
)
from beadloom.services.bd_seam.invocations import text_invocations

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/bd_answer_population.feature")

_COVERAGE = {
    "as-asked": COVERAGE_AS_ASKED,
    "filtered": COVERAGE_FILTERED,
    "truncated": COVERAGE_TRUNCATED,
    "unchecked": COVERAGE_UNCHECKED,
}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    return {
        "root": tmp_path,
        "argv": (),
        "stderr": "",
        "suggested": "",
        "ready": None,
        "coverage": None,
        "confirmed": None,
        "sites": (),
        "artifacts": [],
    }


@given(parsers.parse('a listing asked for with "{argv}"'))
def _listing(world: dict[str, Any], argv: str) -> None:
    world["argv"] = tuple(argv.split())


@given(parsers.parse('bd announced "{notice}" on stderr'))
def _notice(world: dict[str, Any], notice: str) -> None:
    world["stderr"] = notice


@given("bd announced nothing on stderr")
def _silent(world: dict[str, Any]) -> None:
    world["stderr"] = ""


@when("the answer's population is read")
def _read_coverage(world: dict[str, Any]) -> None:
    world["coverage"] = coverage_of(world["argv"], world["stderr"])


@then(parsers.parse('the answer covers "{name}"'))
def _covers(world: dict[str, Any], name: str) -> None:
    assert world["coverage"].coverage == _COVERAGE[name], world["coverage"].stated


@then("the answer states how many rows bd said it withheld")
def _withheld(world: dict[str, Any]) -> None:
    assert "50" in world["coverage"].stated


@then("the answer does not claim to cover the tracker")
def _no_tracker_claim(world: dict[str, Any]) -> None:
    assert "not the same claim as covering the tracker" in world["coverage"].stated


@then("the answer names the flag that would have widened it")
def _names_flag(world: dict[str, Any]) -> None:
    assert "--all" in world["coverage"].stated


@given(parsers.parse('bd suggested "{first}" and "{second}" as newly unblocked'))
def _suggested(world: dict[str, Any], first: str, second: str) -> None:
    world["suggested"] = (
        f"✓ Closed rig-x — a blocker: Closed\n\nNewly unblocked:\n"
        f"  • {first} — a target (P1)\n"
        f"  • {second} — another target (P2)\n"
    )


@given("bd suggested no bead as newly unblocked")
def _suggested_nothing(world: dict[str, Any]) -> None:
    world["suggested"] = "✓ Closed rig-x — a blocker: Closed\n"


@given(parsers.parse('the tracker\'s ready list holds "{bead}"'))
def _ready(world: dict[str, Any], bead: str) -> None:
    world["ready"] = (bead,)


@given("the tracker's ready list could not be read")
def _no_ready(world: dict[str, Any]) -> None:
    world["ready"] = None


@when("the suggestion is confirmed against the ready list")
def _confirm(world: dict[str, Any]) -> None:
    world["confirmed"] = confirmed_suggestion(world["suggested"], world["ready"])


@then(parsers.parse('the confirmed beads are "{bead}"'))
def _confirmed(world: dict[str, Any], bead: str) -> None:
    assert world["confirmed"].confirmed == (bead,)


@then(parsers.parse('the still-blocked beads are "{bead}"'))
def _still_blocked(world: dict[str, Any], bead: str) -> None:
    assert world["confirmed"].still_blocked == (bead,)


@then("the suggestion is not readable as a list of ready beads")
def _not_readable_as_ready(world: dict[str, Any]) -> None:
    answer = world["confirmed"]
    assert answer.candidates != answer.confirmed
    assert "still blocked" in answer.stated


@then(parsers.parse('the suggestion reads "{phrase}"'))
def _reads(world: dict[str, Any], phrase: str) -> None:
    expected = {"not compared": NOT_COMPARED, "nothing to check": NOTHING_TO_CHECK}
    assert expected[phrase] in world["confirmed"].stated


@then("no bead is reported as confirmed")
def _none_confirmed(world: dict[str, Any]) -> None:
    assert world["confirmed"].confirmed == ()


@given(parsers.parse('an artifact instructing "{text}" and nothing else'))
def _artifact_alone(world: dict[str, Any], text: str) -> None:
    world["artifacts"].append(("role.md", f"Close the bead:\n\n    {text}\n"))


@given(parsers.parse('an artifact instructing "{first}" and "{second}"'))
def _artifact_pair(world: dict[str, Any], first: str, second: str) -> None:
    world["artifacts"].append(
        ("role.md", f"Close the bead:\n\n    {first}\n\nThen confirm:\n\n    {second}\n")
    )


@when("the bd call sites are derived over the artifact")
def _derive(world: dict[str, Any]) -> None:
    world["sites"] = call_sites(text_invocations(world["artifacts"]))


@then(parsers.parse('the close site assumes "{name}" and the assumption is "{verdict}"'))
def _close_assumption(world: dict[str, Any], name: str, verdict: str) -> None:
    wanted = {"secured": VERDICT_SECURED, "unsecured": VERDICT_UNSECURED}[verdict]
    closes = [site for site in world["sites"] if site.subcommand == "close"]
    assert closes, "the derivation found no close site at all"
    found = {a.name: a for a in closes[0].assumptions}
    assert name in found, f"close assumes {sorted(found)}, not {name!r}"
    assert found[name].verdict == wanted, found[name].detail


@then("the verdict says what a derivation of call forms cannot see")
def _states_its_limit(world: dict[str, Any]) -> None:
    closes = [site for site in world["sites"] if site.subcommand == "close"]
    detail = next(a.detail for a in closes[0].assumptions if a.name == "unblocked-is-ready")
    assert "COMPARED" in detail, detail
    assert "can see" in detail, detail
