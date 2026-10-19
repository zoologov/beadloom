"""Step implementations for `services/mcp-server/the_verdict_names_a_report_that_raised.feature`.

BDL-083 S1 fix 4 (``beadloom-ba9w.17``). Each scenario runs the real
``complete_bead`` handler, and with it the real gate, over a small project on which
every gate step passes and whose pipeline declares a test suite, so the list of
verifications not run has something to name. The fault is injected by replacing the
derivation that produces the report, which is the one place an unexpected exception
can be put without inventing a broken project for each report: the room census is
replaced where the gate calls it and where the tool calls it, so both take a census
that raises. The ``bd`` seam is doubled to close the bead and to report no claimed
bead, so a scenario neither needs a beads database nor reads the author's tracker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application import gate, rooms
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.bd_seam import BdResult

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../services/mcp-server/the_verdict_names_a_report_that_raised.feature")

#: The command the declared pipeline runs for the test suite.
_SUITE = "uv run pytest"

#: The report a scenario names, and the modules whose derivation produces it.
_DERIVATIONS: dict[str, tuple[tuple[object, str], ...]] = {
    "coverage report": ((gate, "derive_gate_coverage"),),
    "room census": ((gate, "take_census"), (rooms, "take_census")),
}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(guard_probes.BdWorkTracker, "claimed_beads", lambda _self: ())
    return {"root": tmp_path, "verdict": None}


@given("a project on which every gate step passes and whose pipeline runs the test suite")
def _a_clean_project(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(
        f"jobs:\n  tests:\n    runs-on: ubuntu-latest\n    steps:\n      - run: {_SUITE}\n",
        encoding="utf-8",
    )


@given(parsers.parse("the {report} raises an unexpected exception"))
def _report_raises(report: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise LookupError("injected fault")

    for module, name in _DERIVATIONS[report]:
        monkeypatch.setattr(module, name, _raise)


@when("an agent completes a bead through the MCP tool without the test suite")
def _complete(world: dict[str, Any]) -> None:
    from beadloom.services.mcp_server import handle_complete_bead

    with patch("beadloom.services.mcp_server.run_bd") as run_bd:
        run_bd.return_value = BdResult(0, "", "")
        world["verdict"] = handle_complete_bead(world["root"], bead="bd-1", run_tests=False)


@then(parsers.parse('the tool closes the bead with the verdict "{status}"'))
def _verdict(world: dict[str, Any], status: str) -> None:
    verdict = world["verdict"]
    assert verdict["status"] == status, verdict
    assert verdict["findings"] == []


@then(parsers.parse('its "{key}" is "{reason}"'))
def _key_is(world: dict[str, Any], key: str, reason: str) -> None:
    assert world["verdict"][key] == reason


@then(parsers.parse('its "{key}" is empty'))
def _key_is_empty(world: dict[str, Any], key: str) -> None:
    assert world["verdict"][key] is None


@then(parsers.parse('its "{key}" names "{duty}"'))
def _key_names(world: dict[str, Any], key: str, duty: str) -> None:
    assert world["verdict"][key] == [duty]


@then(parsers.parse('its room gives the reason "{reason}"'))
def _room_reason(world: dict[str, Any], reason: str) -> None:
    assert world["verdict"]["room"] == {"reason": reason}
