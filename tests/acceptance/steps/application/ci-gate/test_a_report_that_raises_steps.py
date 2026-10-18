"""Step implementations for `application/ci-gate/a_report_that_raises.feature`.

BDL-083 S1 fix 1 (``beadloom-4m0w``, S1R Major 1). Each scenario runs the real
``beadloom ci`` in-process over a small project on which every step passes, with one of
the three reports derived after the steps made to raise. The fault is injected by
replacing the derivation the Gate calls, which is the one place an unexpected exception
can be put without inventing a broken project for each report. The tracker adapter is
doubled to report no claimed bead, so a scenario neither needs a beads database in a
temporary directory nor reads the author's real tracker.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application import gate
from beadloom.application.reindex import reindex
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/ci-gate/a_report_that_raises.feature")

#: The report a scenario names, and the derivation the Gate calls to produce it.
_DERIVATIONS = {
    "room census": "take_census",
    "coverage report": "derive_gate_coverage",
    "ownership report": "derive_gate_ownership",
}


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(guard_probes.BdWorkTracker, "claimed_beads", lambda _self: ())
    return {"root": tmp_path, "result": None}


def _ci(root: Path, *args: str) -> Any:
    return CliRunner().invoke(main, ["ci", "--project", str(root), *args])


@given("a project on which every gate step passes")
def _a_clean_project(world: dict[str, Any]) -> None:
    root = world["root"]
    (root / ".beadloom" / "_graph").mkdir(parents=True, exist_ok=True)
    generate_agents_md(root)
    reindex(root)
    clean = _ci(root, "--format", "json")
    assert clean.exit_code == 0, clean.output


@given(parsers.parse("the {report} raises an unexpected exception"))
def _report_raises(report: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> object:
        raise LookupError("injected fault")

    monkeypatch.setattr(gate, _DERIVATIONS[report], _raise)


@when("the gate runs on that project")
def _run_rich(world: dict[str, Any]) -> None:
    world["result"] = _ci(world["root"], "--format", "rich")


@when("the gate reports on that project as JSON")
def _run_json(world: dict[str, Any]) -> None:
    world["result"] = _ci(world["root"], "--format", "json")


@then(parsers.parse('the gate exits 0 with the verdict "{verdict}"'))
def _verdict_stands(world: dict[str, Any], verdict: str) -> None:
    result = world["result"]
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert verdict in result.stdout.splitlines(), result.stdout


@then(parsers.parse('the report says "{reason}"'))
def _reason_printed(world: dict[str, Any], reason: str) -> None:
    assert reason in world["result"].stdout, world["result"].stdout


@then("the JSON report is ok with no crashed step")
def _json_ok(world: dict[str, Any]) -> None:
    result = world["result"]
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["crashed"] == []


@then(parsers.parse('its "{key}" entry gives the reason "{reason}"'))
def _json_reason(world: dict[str, Any], key: str, reason: str) -> None:
    payload = json.loads(world["result"].stdout)
    assert payload[key]["reason"] == reason
