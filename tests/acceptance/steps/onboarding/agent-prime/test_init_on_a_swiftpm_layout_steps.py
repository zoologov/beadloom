"""Step implementations for `onboarding/agent-prime/init_on_a_swiftpm_layout.feature`.

BDL-076 B7 (`beadloom-ujzb.16`). The real `beadloom init --yes` and `beadloom
reindex` run through the CLI on Swift packages written to disk. What init writes
is read back from its YAML, which is what an adopter commits; what reindex derives
is read from the index. Nothing is patched.

**FAKES PROVE FAKES.** This repository holds no Swift. Each package imports an
Apple framework and a product of a remote package, which must stay unresolved, and
the second package keeps a target outside `Sources/` and a test target whose name
does not end in `Tests`, which only the manifest can place.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_swift")

scenarios("../../../onboarding/agent-prime/init_on_a_swiftpm_layout.feature")

_TRAILHEAD: dict[str, str] = {
    "Package.swift": (
        "// swift-tools-version:5.9\n"
        "import PackageDescription\n\n"
        "let package = Package(\n"
        '    name: "Trailhead",\n'
        "    products: [\n"
        '        .executable(name: "trail", targets: ["TrailApp"]),\n'
        '        .library(name: "TrailKit", targets: ["TrailCore", "TrailNet"]),\n'
        "    ],\n"
        "    dependencies: [\n"
        '        .package(url: "https://github.com/apple/swift-log.git", from: "1.5.0"),\n'
        "    ],\n"
        "    targets: [\n"
        '        .target(name: "TrailCore"),\n'
        "        .target(\n"
        '            name: "TrailNet",\n'
        "            dependencies: [\n"
        '                .target(name: "TrailCore"),\n'
        '                .product(name: "Logging", package: "swift-log"),\n'
        "            ]\n"
        "        ),\n"
        '        .executableTarget(name: "TrailApp", dependencies: ["TrailCore", "TrailNet"]),\n'
        '        .testTarget(name: "TrailCoreTests", dependencies: ["TrailCore"]),\n'
        "    ]\n"
        ")\n"
    ),
    "Sources/TrailCore/Route.swift": "import Foundation\n\npublic struct Route {}\n",
    "Sources/TrailNet/Client.swift": (
        "import Logging\nimport TrailCore\n\npublic struct Client { let route: Route }\n"
    ),
    "Sources/TrailApp/main.swift": (
        "import Foundation\nimport TrailCore\nimport TrailNet\n\nprint(Route())\n"
    ),
    "Tests/TrailCoreTests/RouteTests.swift": (
        "import XCTest\n@testable import TrailCore\n\n"
        "final class RouteTests: XCTestCase { func testRoute() {} }\n"
    ),
}

_IGNITION: dict[str, str] = {
    "Package.swift": (
        "// swift-tools-version:5.9\n"
        "import PackageDescription\n\n"
        "let package = Package(\n"
        '    name: "Ignition",\n'
        "    targets: [\n"
        '        .target(name: "Engine", path: "Engine"),\n'
        '        .executableTarget(name: "Launcher", dependencies: ["Engine"]),\n'
        '        .testTarget(name: "SmokeChecks", dependencies: ["Engine"]),\n'
        "    ]\n"
        ")\n"
    ),
    "Engine/Ignition.swift": "import Foundation\n\npublic struct Ignition {}\n",
    "Sources/Launcher/main.swift": "import Engine\n\nprint(Ignition())\n",
    "Tests/SmokeChecks/IgnitionSmoke.swift": (
        "import XCTest\n@testable import Engine\n\n"
        "final class IgnitionSmoke: XCTestCase { func testStarts() {} }\n"
    ),
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


def _write(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@given(
    "a Swift package with the library targets TrailCore and TrailNet "
    "and the executable target TrailApp"
)
def _trailhead(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "trailhead"
    _write(state["root"], _TRAILHEAD)


@given(
    'a Swift package whose target Engine declares the path "Engine" '
    "and whose test target SmokeChecks depends on it"
)
def _ignition(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = tmp_path / "ignition"
    _write(state["root"], _IGNITION)


def _run(state: dict[str, Any], *args: str) -> None:
    result = CliRunner().invoke(main, [*args, "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    _run(state, "init", "--yes")


@when("beadloom reindex is run")
def _reindex(state: dict[str, Any]) -> None:
    _run(state, "reindex")


def _listed(text: str) -> set[str]:
    return {part.strip().strip('"') for part in text.split(",")}


def _pairs(text: str) -> set[tuple[str, str]]:
    return {(src, dst) for src, dst in (item.split(" -> ") for item in _listed(text))}


def _graph(root: Path) -> list[dict[str, Any]]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for path in sorted((root / ".beadloom" / "_graph").glob("*.yml"))
    ]


def _config(root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (root / ".beadloom" / "config.yml").read_text(encoding="utf-8")
    )
    return loaded


@then(parsers.parse("the code nodes init writes have exactly the sources {sources}"))
def _sources(state: dict[str, Any], sources: str) -> None:
    written = {
        str(node.get("source") or "")
        for data in _graph(state["root"])
        for node in data.get("nodes") or []
    }
    assert written - {""} == _listed(sources)


@then(parsers.parse("the scan paths init writes are exactly {paths}"))
def _scan_paths(state: dict[str, Any], paths: str) -> None:
    assert set(_config(state["root"])["scan_paths"]) == _listed(paths)


@then(parsers.parse("the languages init writes are exactly {languages}"))
def _languages(state: dict[str, Any], languages: str) -> None:
    assert set(_config(state["root"])["languages"]) == _listed(languages)


@then(parsers.parse("the graph init writes has exactly the depends_on edges {edges}"))
def _written_edges(state: dict[str, Any], edges: str) -> None:
    written = {
        (str(edge["src"]), str(edge["dst"]))
        for data in _graph(state["root"])
        for edge in data.get("edges") or []
        if edge.get("kind") == "depends_on"
    }
    assert written == _pairs(edges)


def _query(root: Path, sql: str, *params: str) -> list[tuple[Any, ...]]:
    with sqlite3.connect(root / ".beadloom" / "beadloom.db") as conn:
        return [tuple(row) for row in conn.execute(sql, params).fetchall()]


@then(parsers.parse("the index holds exactly the depends_on edges {edges}"))
def _indexed_edges(state: dict[str, Any], edges: str) -> None:
    rows = _query(
        state["root"], "SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'depends_on'"
    )
    assert {(str(src), str(dst)) for src, dst in rows} == _pairs(edges)


@then(parsers.parse('the test file "{path}" is bound to "{ref_id}"'))
def _bound(state: dict[str, Any], path: str, ref_id: str) -> None:
    assert _query(state["root"], "SELECT ref_id FROM test_files WHERE path = ?", path) == [
        (ref_id,)
    ]
