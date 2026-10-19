"""Step implementations for `application/ci-gate/a_step_that_raises.feature`.

BDL-083 S1e (``beadloom-ba9w.13``, BDL-UX #318). Each scenario runs the real
``beadloom ci`` in-process over a small project on which every step passes, with one
step made to raise. The fault is injected by replacing the step function the Gate
calls, which is the one place an unexpected exception can be put without inventing a
broken project for each step. The tracker adapter is doubled to report no claimed bead,
so a scenario neither needs a beads database in a temporary directory nor reads the
author's real tracker.

The steps the Gate runs are read from a run of the same project without the fault, so
"every step after docs-audit" is the population the Gate itself produced, not a list
spelled here that goes stale when a leg is added.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application import gate
from beadloom.application.reindex import reindex
from beadloom.onboarding.scanner import generate_agents_md
from beadloom.services.cli import main
from beadloom.services.commands.hook_templates import GATE_VERDICT_PATTERN

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/ci-gate/a_step_that_raises.feature")

#: The step the scenarios break: the fourth, so steps run both before and after it.
_CRASHED = "docs-audit"

#: The exception the broken step raises, named so the assertions can look for it.
_FAULT = "LookupError"

#: One step line of the rich report, ``[STATUS] name: summary``.
_STEP_LINE = re.compile(r"^\s*\[(?P<status>[A-Z]+)\] (?P<name>[\w-]+):", re.MULTILINE)


@pytest.fixture()
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """One mutable bag the steps share, kept explicit rather than global."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(guard_probes.BdWorkTracker, "claimed_beads", lambda _self: ())
    return {"root": tmp_path, "baseline": [], "result": None}


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
    world["baseline"] = [step["name"] for step in json.loads(clean.stdout)["steps"]]
    assert _CRASHED in world["baseline"]


@given("the docs-audit step raises an unexpected exception")
def _docs_audit_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_args: object, **_kwargs: object) -> gate.GateStep:
        raise LookupError("injected fault")

    monkeypatch.setattr(gate, "_step_docs_audit", _raise)


@when("the gate runs on that project")
def _run_rich(world: dict[str, Any]) -> None:
    world["result"] = _ci(world["root"], "--format", "rich")


@when("the gate reports on that project as JSON")
def _run_json(world: dict[str, Any]) -> None:
    world["result"] = _ci(world["root"], "--format", "json")


def _rich_statuses(world: dict[str, Any]) -> dict[str, str]:
    output = world["result"].stdout
    return {m["name"]: m["status"] for m in _STEP_LINE.finditer(output)}


@then("the docs-audit step reads ERROR and names the exception it raised")
def _rich_error_line(world: dict[str, Any]) -> None:
    assert _rich_statuses(world).get(_CRASHED) == "ERROR", world["result"].output
    line = next(
        line for line in world["result"].stdout.splitlines() if f"] {_CRASHED}:" in line
    )
    assert _FAULT in line


@then("every step after docs-audit reported a status of its own")
def _later_steps_reported(world: dict[str, Any]) -> None:
    statuses = _rich_statuses(world)
    baseline = world["baseline"]
    after = baseline[baseline.index(_CRASHED) + 1 :]
    assert after, "the scenario needs steps after the broken one"
    assert list(statuses) == baseline
    assert all(statuses[name] != "ERROR" for name in after)


@then("the gate exits 1")
def _exits_one(world: dict[str, Any]) -> None:
    assert world["result"].exit_code == 1


@then("the verdict says 1 step(s) crashed and names docs-audit")
def _verdict_counts(world: dict[str, Any]) -> None:
    verdict = next(
        line for line in world["result"].stdout.splitlines() if line.startswith("FAIL")
    )
    assert "1 step(s) crashed" in verdict
    assert _CRASHED in verdict
    # The pre-push hook finds the verdict by this pattern; a line it cannot find is
    # reported as a Gate that did not run.
    assert re.search(GATE_VERDICT_PATTERN, verdict), verdict


@then("the docs-audit step's status is ERROR and its error names the exception")
def _json_step(world: dict[str, Any]) -> None:
    payload = json.loads(world["result"].stdout)
    step = next(s for s in payload["steps"] if s["name"] == _CRASHED)
    assert step["status"] == "ERROR"
    assert step["passed"] is False
    assert _FAULT in step["error"]
    assert payload["ok"] is False


@then("the report lists docs-audit as the one crashed step")
def _json_crashed(world: dict[str, Any]) -> None:
    payload = json.loads(world["result"].stdout)
    assert payload["crashed"] == [_CRASHED]
    others = [s for s in payload["steps"] if s["name"] != _CRASHED]
    assert all(s["error"] is None for s in others)
