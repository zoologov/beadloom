"""Step implementations for `features/gate_finding_owner.feature` (BDL-068 S6).

Thin by design: every step builds a real project on disk and runs the real
`beadloom ci` over it, because the finding is about what one command's output
says. A double of the gate would report whatever the double was told to report.

The one thing that IS doubled is the tracker adapter — `BdWorkTracker` is the
seam over the `bd` binary, and a scenario must not require a beads database to
exist in a temporary directory, nor claim a bead in the author's real tracker.
The double answers with the same `ClaimedBead` shape the adapter composes.

The module is named ``test_*`` so default pytest collection picks the scenarios
up: the acceptance suite runs inside ``uv run pytest``, not beside it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.gate import run_ci_gate
from beadloom.application.guards.contract import ClaimedBead
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../features/gate_finding_owner.feature")

_GRAPH = """\
nodes:
  - ref_id: root
    kind: service
    summary: "Root service"
  - ref_id: alpha
    kind: domain
    summary: "Alpha domain"
    source: src/alpha
  - ref_id: beta
    kind: domain
    summary: "Beta domain"
    source: src/beta
edges:
  - src: alpha
    dst: root
    kind: part_of
"""

_RULES = """\
version: 3
rules:
  - name: domain-needs-parent
    description: "Every domain must be part_of the root"
    severity: error
    require:
      for: { kind: domain }
      has_edge_to: { ref_id: root }
      edge_kind: part_of
"""

#: A rules file no loader will read, so the run's findings are step-level ones
#: that name no node and carry no path.
_UNREADABLE_RULES = "rules:\n  - name: broken\n    require: {}\n"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    """The one mutable bag the steps share, kept explicit rather than global."""
    project = tmp_path / "proj"
    graph = project / ".beadloom" / "_graph"
    graph.mkdir(parents=True)
    (graph / "graph.yml").write_text(_GRAPH, encoding="utf-8")
    (graph / "rules.yml").write_text(_RULES, encoding="utf-8")
    for domain in ("alpha", "beta"):
        (project / "src" / domain).mkdir(parents=True)
        (project / "src" / domain / f"{domain}.py").write_text(
            "x = 1\n", encoding="utf-8"
        )
    from beadloom.application.reindex import reindex

    reindex(project)
    return {"root": project}


def _claim(monkeypatch: pytest.MonkeyPatch, answer: object) -> None:
    """Make the service-layer tracker adapter answer with *answer*, without bd."""
    from beadloom.services import guard_probes

    monkeypatch.setattr(
        guard_probes.BdWorkTracker, "claimed_beads", lambda _self: answer
    )


@given("a project whose gate finds a fault in a node")
def _fault_in_a_node(world: dict[str, Any]) -> None:
    """The graph the fixture already wrote: `beta` is part_of nothing."""


@given("a project whose gate finds a fault with no node and no path")
def _fault_with_no_node(world: dict[str, Any]) -> None:
    graph = world["root"] / ".beadloom" / "_graph"
    (graph / "rules.yml").write_text(_UNREADABLE_RULES, encoding="utf-8")


@given("a bead is claimed that declares that node")
def _bead_declares_the_node(monkeypatch: pytest.MonkeyPatch) -> None:
    _claim(monkeypatch, (ClaimedBead(id="bd-1", title="bd-1", declaration="refs: beta"),))


@given("a bead is claimed that declares a different node")
def _bead_declares_another_node(monkeypatch: pytest.MonkeyPatch) -> None:
    _claim(
        monkeypatch, (ClaimedBead(id="bd-1", title="bd-1", declaration="refs: alpha"),)
    )


@given("the work tracker cannot be reached")
def _tracker_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    _claim(monkeypatch, None)


@when("the gate reports on that project")
def _run_the_gate(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["ci", "--project", str(world["root"]), "--format", "rich"]
    )
    world["output"] = result.output
    world["exit_code"] = result.exit_code


@then("the report names the claimed bead as the owner of that finding")
def _names_the_bead(world: dict[str, Any]) -> None:
    assert "bd-1 — 1 finding(s)" in world["output"]


@then("the report calls that finding unowned")
def _calls_it_unowned(world: dict[str, Any]) -> None:
    assert "unowned — 1 finding(s)" in world["output"]


@then("it says no bead claimed now declares the node that owns it")
def _says_no_bead_declares_it(world: dict[str, Any]) -> None:
    assert "no bead claimed now declares the node that owns them" in world["output"]
    assert "no finding of this run is owned by a bead claimed now" in world["output"]


@then("the report calls that finding unattributed")
def _calls_it_unattributed(world: dict[str, Any]) -> None:
    assert "unattributed — " in world["output"]


@then("it does not call that finding unowned")
def _does_not_call_it_unowned(world: dict[str, Any]) -> None:
    assert "unowned — " not in world["output"]


@then("the report states that the claim could not be read")
def _states_the_claim_was_not_read(world: dict[str, Any]) -> None:
    from beadloom.application.gate_ownership import NO_TRACKER

    assert NO_TRACKER in world["output"]


@then("it attributes no finding to any bead")
def _attributes_nothing(world: dict[str, Any]) -> None:
    assert "finding(s)" not in world["output"].split("Findings by owner:")[1]


@then("the verdict and the exit code are the ones the steps produced")
def _verdict_unchanged(world: dict[str, Any]) -> None:
    unattributed = run_ci_gate(
        world["root"], fail_on=None, hub_exports=[], no_reindex=True
    )
    assert unattributed.ownership is None
    assert unattributed.ok is False
    assert world["exit_code"] == 1
    assert "FAIL — gate blocked" in world["output"]
