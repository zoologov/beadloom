"""Steps for `context-oracle/test-mapping/tests_in_a_build_tools_test_tree_bind.feature`.

BDL-074 G2b, ``beadloom-2mj3.13``. The steps run ``reindex`` and ``ctx --json``
through the CLI against a project written into a temporary directory, laid out
by its ecosystem's standard directory layout. The projects are written here, not
imported from ``tests.support``, because the acceptance suite runs standalone.
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

scenarios("../../../context-oracle/test-mapping/tests_in_a_build_tools_test_tree_bind.feature")

_JAVA_CODE = "package com.shop.{p};\n\npublic class {c} {{}}\n"
_JAVA_TEST = (
    "package com.shop.{p};\n\nimport org.junit.jupiter.api.Test;\n\n"
    "class {c}Test {{\n    @Test\n    void adds() {{}}\n\n    @Test\n    void voids() {{}}\n}}\n"
)
_SWIFT_CODE = "public struct {c} {{}}\n"
_SWIFT_TEST = (
    "import XCTest\n\nfinal class {c}Tests: XCTestCase {{\n"
    "    func testAdds() {{}}\n    func testVoids() {{}}\n}}\n"
)


@pytest.fixture()
def world() -> dict[str, Any]:
    return {}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _project(root: Path, *, language: str, scan_path: str, sources: dict[str, str]) -> None:
    config = {"languages": [language], "scan_paths": [scan_path]}
    _write(root, ".beadloom/config.yml", yaml.safe_dump(config))
    nodes: list[dict[str, str]] = [{"ref_id": "shop", "kind": "service", "summary": "Shop"}]
    nodes += [
        {"ref_id": name, "kind": "domain", "summary": name, "source": source}
        for name, source in sources.items()
    ]
    edges = [{"src": name, "dst": "shop", "kind": "part_of"} for name in sources]
    graph = yaml.safe_dump({"nodes": nodes, "edges": edges}, sort_keys=False)
    _write(root, ".beadloom/_graph/services.yml", graph)


def _cli(project: Path, *args: str) -> str:
    result = CliRunner().invoke(main, [*args, "--project", str(project)])
    assert result.exit_code == 0, result.output
    return result.output


@given("a Maven project with a test class for each of its two packages")
def _given_maven(world: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / "shop"
    _write(root, "pom.xml", "<project><artifactId>shop</artifactId></project>\n")
    sources = {}
    for name in ("billing", "orders"):
        cls = name.title()
        _write(root, f"src/main/java/com/shop/{name}/{cls}.java", _JAVA_CODE.format(p=name, c=cls))
        _write(
            root, f"src/test/java/com/shop/{name}/{cls}Test.java", _JAVA_TEST.format(p=name, c=cls)
        )
        sources[name] = f"src/main/java/com/shop/{name}/"
    _project(root, language=".java", scan_path="src", sources=sources)
    world["project"] = root


@given("a Swift package whose test target holds a test file for each of its two folders")
def _given_swift(world: dict[str, Any], tmp_path: Path) -> None:
    root = tmp_path / "shop"
    _write(root, "Package.swift", "// swift-tools-version:5.9\n")
    sources = {}
    for name in ("billing", "orders"):
        cls = name.title()
        _write(root, f"Sources/Shop/{cls}/{cls}.swift", _SWIFT_CODE.format(c=cls))
        _write(root, f"Tests/ShopTests/{cls}Tests.swift", _SWIFT_TEST.format(c=cls))
        sources[name] = f"Sources/Shop/{cls}/"
    _project(root, language=".swift", scan_path="Sources", sources=sources)
    world["project"] = root


@when("the index is rebuilt and the context of the billing node is read")
def _when_read(world: dict[str, Any]) -> None:
    _cli(world["project"], "reindex", "--full")
    world["tests"] = json.loads(_cli(world["project"], "ctx", "billing", "--json"))["tests"]


def _expect(world: dict[str, Any], framework: str, path: str) -> None:
    assert world["tests"] == {
        "framework": framework,
        "test_files": [path],
        "test_count": 2,
        "coverage_estimate": "medium",
    }


@then("the context names the billing test class as a junit file holding 2 tests")
def _then_junit(world: dict[str, Any]) -> None:
    _expect(world, "junit", "src/test/java/com/shop/billing/BillingTest.java")


@then("the context names the billing test file as an xctest file holding 2 tests")
def _then_xctest(world: dict[str, Any]) -> None:
    _expect(world, "xctest", "Tests/ShopTests/BillingTests.swift")
