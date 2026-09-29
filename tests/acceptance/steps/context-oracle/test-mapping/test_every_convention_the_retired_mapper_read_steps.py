"""Steps for `every_convention_the_retired_mapper_read_is_read.feature` (test-mapping).

BDL-074 G5, ``beadloom-2mj3.15``. The steps run ``reindex``, ``ctx`` and ``status
--debt-report`` through the CLI against a two-node TypeScript project written into
a temporary directory: the reviewer's reproduction, file for file. The project is
written here, not imported from ``tests.support``, because the acceptance suite
runs standalone.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios(
    "../../../context-oracle/test-mapping/every_convention_the_retired_mapper_read_is_read.feature"
)

_CODE = "export function total(a: number, b: number): number { return a + b; }\n"
_TEST = (
    "import { total } from '../{name}';\n\n"
    "test('adds', () => { expect(total(1, 2)).toBe(3); });\n"
    "it('adds zero', () => { expect(total(0, 0)).toBe(0); });\n"
)


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, tests: dict[str, str], config: dict[str, object]) -> Path:
    _write(root, "package.json", '{"name": "shop", "devDependencies": {"jest": "29"}}\n')
    for name, test_path in tests.items():
        _write(root, f"src/{name}/{name}.ts", _CODE)
        _write(root, test_path, _TEST.replace("{name}", name))
    _write(root, ".beadloom/config.yml", yaml.safe_dump(config))
    nodes: list[dict[str, str]] = [{"ref_id": "shop", "kind": "service", "summary": "Shop"}]
    nodes += [
        {"ref_id": name, "kind": "domain", "summary": name, "source": f"src/{name}/"}
        for name in tests
    ]
    edges = [{"src": name, "dst": "shop", "kind": "part_of"} for name in tests]
    graph = yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False)
    _write(root, ".beadloom/_graph/services.yml", graph)
    return root


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


@given("a TypeScript project with one test beside its code and one in a __tests__ folder")
def _given_jest(world: dict[str, Any], tmp_path: Path) -> None:
    tests = {"billing": "src/billing/billing.test.ts", "orders": "src/orders/__tests__/orders.ts"}
    world["config"] = {"languages": [".ts"], "scan_paths": ["src"]}
    world["project"] = _project(tmp_path / "shop", tests, world["config"])


@given("a TypeScript project whose tests sit in an e2e folder beside its code")
def _given_e2e(world: dict[str, Any], tmp_path: Path) -> None:
    tests = {"billing": "src/billing/e2e/billing.ts", "orders": "src/orders/e2e/orders.ts"}
    world["config"] = {"languages": [".ts"], "scan_paths": ["src"]}
    world["project"] = _project(tmp_path / "shop", tests, world["config"])


@given(parsers.parse("the project declares the jest pattern {pattern}"))
def _given_pattern(world: dict[str, Any], pattern: str) -> None:
    config = {**world["config"], "tests": {"patterns": {"jest": [pattern]}}}
    _write(world["project"], ".beadloom/config.yml", yaml.safe_dump(config))


@when("the index is rebuilt and the context of the orders node is read")
def _when_read(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")
    world["tests"] = json.loads(_cli(world["project"], "ctx", "orders", "--json"))["tests"]


@when("the index is rebuilt and the context of the orders node is printed")
def _when_printed(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")
    world["printed"] = _cli(world["project"], "ctx", "orders")


@when("the index is rebuilt and the debt report is read")
def _when_debt(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")
    world["debt"] = json.loads(_cli(world["project"], "status", "--debt-report", "--json"))


def _expect(world: dict[str, Any], path: str) -> None:
    assert world["tests"] == {
        "framework": "jest",
        "test_files": [path],
        "test_count": 2,
        "coverage_estimate": "medium",
    }


@then("the context names the orders __tests__ file as a jest file holding 2 tests")
def _then_tests_folder(world: dict[str, Any]) -> None:
    _expect(world, "src/orders/__tests__/orders.ts")


@then("the context names the orders e2e file as a jest file holding 2 tests")
def _then_e2e(world: dict[str, Any]) -> None:
    _expect(world, "src/orders/e2e/orders.ts")


@then("the debt report counts 0 untested nodes")
def _then_untested(world: dict[str, Any]) -> None:
    (gaps,) = [c for c in world["debt"]["categories"] if c["name"] == "test_gaps"]
    assert gaps["details"]["untested"] == 0


@then("its test population names the jest folder pattern it read the tests by")
def _then_population(world: dict[str, Any]) -> None:
    population = world["debt"]["test_population"]
    assert "all 2 test file(s) placed" in population
    assert "a test file is read when its path matches a pattern of" in population
    assert "__tests__/**/*.[jt]s" in population


@then("the printed context says a test file is read when its path matches a pattern")
def _then_printed(world: dict[str, Any]) -> None:
    assert "  A test file is read when its path matches a pattern of " in world["printed"]
