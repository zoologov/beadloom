"""Steps for `context-oracle/test-mapping/tests_beside_the_code_bind.feature`.

BDL-074 G2, ``beadloom-2mj3.11``. Every step runs the real commands — ``reindex``
and ``ctx --json`` through the CLI — against a project written into a temporary
directory. The Go module is the one review ``beadloom-b9ll`` reproduced M3 on.

The projects are written here rather than imported from ``tests.support``: the
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

scenarios("../../../context-oracle/test-mapping/tests_beside_the_code_bind.feature")

_GO_CODE = "package {name}\n\nfunc Total(a, b int) int {{ return a + b }}\n"
_GO_TEST = 'package {name}\n\nimport "testing"\n\nfunc TestTotal(t *testing.T) {{}}\n'
_PY_TEST = "def test_total() -> None:\n    pass\n\n\ndef test_zero() -> None:\n    pass\n"

#: The entry the billing node declares that no test file sits under.
DEAD_ENTRY = "internal/billing/e2e"


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _graph(root: Path, source_of: dict[str, str], billing_tests: list[str] | None = None) -> None:
    nodes: list[dict[str, Any]] = [{"ref_id": "shop", "kind": "service", "summary": "Shop"}]
    for name, source in source_of.items():
        nodes.append({"ref_id": name, "kind": "domain", "summary": name, "source": source})
        if name == "billing" and billing_tests is not None:
            nodes[-1]["tests"] = billing_tests
    edges = [{"src": name, "dst": "shop", "kind": "part_of"} for name in source_of]
    _write(
        root,
        ".beadloom/_graph/services.yml",
        yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False),
    )


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


@given("a Go module with a test beside each of its two packages")
def _given_a_go_module(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "shop"
    _write(project, "go.mod", "module example.com/shop\n\ngo 1.22\n")
    for name in ("billing", "orders"):
        _write(project, f"internal/{name}/{name}.go", _GO_CODE.format(name=name))
        _write(project, f"internal/{name}/{name}_test.go", _GO_TEST.format(name=name))
    _write(project, ".beadloom/config.yml", "languages: [.go]\nscan_paths: [internal]\n")
    world["sources"] = {"billing": "internal/billing/", "orders": "internal/orders/"}
    _graph(project, world["sources"])
    world["project"] = project


@given("a Python project that declares test as its test root and mirrors billing under it")
def _given_a_python_project(world: dict[str, Any], tmp_path: Path) -> None:
    project = tmp_path / "shop"
    _write(project, "src/shop/__init__.py", "")
    _write(project, "src/shop/billing/__init__.py", "")
    _write(project, "src/shop/billing/invoice.py", "def total() -> int:\n    return 0\n")
    _write(project, "test/unit/billing/test_invoice.py", _PY_TEST)
    _write(
        project,
        ".beadloom/config.yml",
        "languages: [.py]\nscan_paths: [src]\ntests:\n  roots: [test]\n",
    )
    _graph(project, {"billing": "src/shop/billing/"})
    world["project"] = project


@given("the billing node declares a tests entry that names no test file")
def _given_a_dead_entry(world: dict[str, Any]) -> None:
    _graph(world["project"], world["sources"], billing_tests=[DEAD_ENTRY])


def _rebuild(world: dict[str, Any]) -> None:
    world["reindex_output"] = _cli(world["project"], "reindex", "--full")


@when("the index is rebuilt and the context of the billing node is read")
def _when_rebuilt_and_read(world: dict[str, Any]) -> None:
    _rebuild(world)
    world["tests"] = json.loads(_cli(world["project"], "ctx", "billing", "--json"))["tests"]


@when("the index is rebuilt")
def _when_rebuilt(world: dict[str, Any]) -> None:
    _rebuild(world)


@then("the context names the billing test as a go_test file holding 1 test")
def _then_the_go_test(world: dict[str, Any]) -> None:
    assert world["tests"] == {
        "framework": "go_test",
        "test_files": ["internal/billing/billing_test.go"],
        "test_count": 1,
        "coverage_estimate": "medium",
    }


@then("the context names the mirrored billing test as a pytest file holding 2 tests")
def _then_the_python_test(world: dict[str, Any]) -> None:
    assert world["tests"] == {
        "framework": "pytest",
        "test_files": ["test/unit/billing/test_invoice.py"],
        "test_count": 2,
        "coverage_estimate": "medium",
    }


@then("the rebuild warns that the billing entry binds nothing")
def _then_the_warning(world: dict[str, Any]) -> None:
    output = " ".join(world["reindex_output"].split())
    assert f"Node 'billing': `tests:` prefix '{DEAD_ENTRY}' covers no indexed test file" in (
        output
    ), world["reindex_output"]
