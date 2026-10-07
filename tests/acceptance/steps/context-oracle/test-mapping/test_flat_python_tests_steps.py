"""Steps for `context-oracle/test-mapping/flat_python_tests_bind_after_init.feature`.

BDL-078, ``beadloom-76mk``. Every step runs the real commands — ``init --yes``,
``reindex`` and ``ctx --json`` through the CLI — against a Python project written
into a temporary directory, its tests directly under ``tests/`` the way most
Python projects keep them.

The project is written here rather than imported from ``tests.support``: the
acceptance suite is copied out of the repository and run standalone, where the
``tests`` package is not importable.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../context-oracle/test-mapping/flat_python_tests_bind_after_init.feature")

#: The project's code, by path under its root: billing imports storage.
CODE: dict[str, str] = {
    "src/shipyard/__init__.py": '"""Shipyard."""\n',
    "src/shipyard/billing/__init__.py": "",
    "src/shipyard/billing/invoice.py": (
        "from shipyard.storage.rates import rate\n\n\n"
        "def total(weight: float) -> float:\n    return rate() * weight\n"
    ),
    "src/shipyard/storage/__init__.py": "",
    "src/shipyard/storage/rates.py": "def rate() -> float:\n    return 2.0\n",
}
BILLING = "src/shipyard/billing/"
STORAGE = "src/shipyard/storage/"

NAMED_TEST = "tests/test_invoice.py"
IMPORTING_TEST = "tests/test_pricing_table.py"
TWO_NODE_TEST = "tests/test_end_to_end.py"

_IMPORTS_BILLING = "from shipyard.billing.invoice import total\n"
_IMPORTS_STORAGE = "from shipyard.storage.rates import rate\n"
_TEST_BODY = "\n\ndef test_it() -> None:\n    assert True\n"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


def _lay_out(world: dict[str, Any], relative: str, imports: str) -> None:
    _write(world["project"], relative, imports + _TEST_BODY)
    world["test"] = relative


def _ref_ids_by_source(project: Path) -> dict[str, str]:
    """Each node's source and ref_id, read from the graph files on disk."""
    found: dict[str, str] = {}
    for graph_file in sorted((project / ".beadloom" / "_graph").glob("*.yml")):
        loaded = yaml.safe_load(graph_file.read_text(encoding="utf-8")) or {}
        for node in loaded.get("nodes") or []:
            found[str(node.get("source") or "")] = str(node["ref_id"])
    return found


def _tests_of(world: dict[str, Any], source: str) -> list[str]:
    project = world["project"]
    ref_id = _ref_ids_by_source(project)[source]
    bundle = json.loads(_cli(project, "ctx", ref_id, "--json"))
    return list(bundle["tests"]["test_files"])


@given("a Python project with a billing and a storage package and its tests directly under tests")
def _given_a_project(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "shipyard"
    for relative, text in CODE.items():
        _write(project, relative, text)
    world["project"] = project


@given("a flat test named after the invoice module of the billing package")
def _given_a_named_test(world: dict[str, Any]) -> None:
    _lay_out(world, NAMED_TEST, _IMPORTS_BILLING)


@given("a flat test named after no module that imports only the storage package")
def _given_an_importing_test(world: dict[str, Any]) -> None:
    _lay_out(world, IMPORTING_TEST, _IMPORTS_STORAGE)


@given("a flat test named after no module that imports both packages")
def _given_a_two_node_test(world: dict[str, Any]) -> None:
    _lay_out(world, TWO_NODE_TEST, _IMPORTS_STORAGE + _IMPORTS_BILLING)


@given("the project's config declares a test layout without flat tests")
def _given_a_layout_without_flat_tests(world: dict[str, Any]) -> None:
    project = world["project"]
    _write(
        project,
        ".beadloom/config.yml",
        "languages: [.py]\nscan_paths: [src]\ntests:\n  roots: [tests]\n",
    )
    nodes = [
        {"ref_id": "shipyard", "kind": "service", "summary": "Shipyard"},
        {"ref_id": "billing", "kind": "domain", "summary": "Billing", "source": BILLING},
        {"ref_id": "storage", "kind": "domain", "summary": "Storage", "source": STORAGE},
    ]
    edges = [{"src": ref, "dst": "shipyard", "kind": "part_of"} for ref in ("billing", "storage")]
    _write(
        project,
        ".beadloom/_graph/services.yml",
        yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False),
    )


@when("the project is initialised")
def _when_initialised(world: dict[str, Any]) -> None:
    world["init_output"] = _cli(world["project"], "init", "--yes")


@when("the index is rebuilt")
def _when_rebuilt(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")


@then("the context of the billing node names that flat test")
def _then_billing_names_it(world: dict[str, Any]) -> None:
    assert _tests_of(world, BILLING) == [world["test"]]


@then("the context of the storage node names that flat test")
def _then_storage_names_it(world: dict[str, Any]) -> None:
    assert _tests_of(world, STORAGE) == [world["test"]]


@then("the init output names that flat test as bound to no node")
def _then_init_names_it(world: dict[str, Any]) -> None:
    lines = world["init_output"].splitlines()
    heading = [i for i, line in enumerate(lines) if "bound to no node" in line]
    assert heading, world["init_output"]
    assert world["test"] in lines[heading[0] + 1].split(), world["init_output"]


@then("no node's context names that flat test")
def _then_no_node_names_it(world: dict[str, Any]) -> None:
    for source in (BILLING, STORAGE):
        assert world["test"] not in _tests_of(world, source)
