"""Steps of `doc-sync/sync-check/a_shrunken_surface_names_the_pairs_it_dropped.feature`.

BDL-083 S2f (``beadloom-27br``), RFC D11. The monorepo fixture is indexed and its surface
recorded with ``sync-check --record-surface``, both through the CLI; then the backend
service's ``source:`` is misspelled in the committed graph and the index rebuilt, which drops
the pair of the one file the service owns directly and no other. The Gate runs through
``run_ci_gate`` with its own reindex.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.application.gate import run_ci_gate
from beadloom.doc_sync.surface_ledger import read_ledger
from beadloom.services.cli import main
from tests.support.shipped_monorepo import shipped_monorepo_checkout

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../doc-sync/sync-check/a_shrunken_surface_names_the_pairs_it_dropped.feature")

#: The backend service's document, docs-relative, and the one pair its own file makes.
_DOC = "backend/README.md"
_DROPPED = [[_DOC, "backend/src/application/__init__.py"]]

#: The declaration as the fixture writes it, and as the scenario's commit misspells it.
_SOURCE = "source: backend/src/\n"
_MISSPELLED = "source: backend/source/\n"


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _invoke(*args: str) -> str:
    """Run the CLI and return its standard output, which is where ``--json`` writes."""
    result = CliRunner().invoke(main, list(args))
    assert result.exit_code in (0, 2), result.output
    return result.stdout


@given("the monorepo fixture indexed with its declared surface recorded")
def _recorded(tmp_path: Path, state: dict[str, Any]) -> None:
    root = shipped_monorepo_checkout(tmp_path)
    _invoke("reindex", "--project", str(root))
    _invoke("sync-check", "--record-surface", "--project", str(root))
    state["root"] = root


@given("the backend service's source misspelled and the index rebuilt")
def _misspelled(state: dict[str, Any]) -> None:
    graph = state["root"] / ".beadloom" / "_graph" / "services.yml"
    text = graph.read_text(encoding="utf-8")
    assert text.count(_SOURCE) == 1, "the fixture declares the source once"
    graph.write_text(text.replace(_SOURCE, _MISSPELLED), encoding="utf-8")
    _invoke("reindex", "--project", str(state["root"]))


@when("sync-check runs")
def _sync_check(state: dict[str, Any]) -> None:
    state["report"] = json.loads(_invoke("sync-check", "--json", "--project", str(state["root"])))


@when("the Gate runs")
def _gate(state: dict[str, Any]) -> None:
    result = run_ci_gate(state["root"], fail_on=None, hub_exports=[], no_reindex=False)
    state["step"] = next(step for step in result.steps if step.name == "sync-check")


@then("the ledger lists the pair of the backend document and the file the service owns")
def _listed(state: dict[str, Any]) -> None:
    ledger = read_ledger(state["root"])

    assert ledger is not None
    assert tuple(_DROPPED[0]) in ledger.pairs
    assert len(ledger.pairs) == ledger.declared_pairs


@then("its declared surface says the surface shrank and names the dropped pair")
def _named(state: dict[str, Any]) -> None:
    surface = state["report"]["declared_surface"]

    assert surface["shrank"] is True
    assert surface["dropped"] == _DROPPED
    assert all(f"{doc} ↔ {file}" in surface["message"] for doc, file in _DROPPED)


@then("its sync-check step's finding names the dropped pair")
def _gate_named(state: dict[str, Any]) -> None:
    whys = [str(finding.get("why", "")) for finding in state["step"].findings]

    named = [why for why in whys if all(f"{d} ↔ {f}" in why for d, f in _DROPPED)]
    assert named, whys
