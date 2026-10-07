"""Step implementations for `a_manifest_is_an_input_of_the_files_it_governs.feature`.

BDL-078 (`beadloom-jcng`). Each fixture is indexed the way an adopter indexes it, then only
a manifest is edited: no source file changes, so an incremental run that reads only the
files that changed reads nothing. The answer is compared with a fresh index of a copy of
the same tree; that step and the indexing steps are in this folder's `conftest.py`.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, scenarios, when

from beadloom.application.reindex import incremental_reindex

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

pytest.importorskip("tree_sitter_go")
pytest.importorskip("tree_sitter_swift")

scenarios("../../../graph/import-resolver/a_manifest_is_an_input_of_the_files_it_governs.feature")


def _graph(service: str, nodes: dict[str, str]) -> str:
    """A root service and one node per source folder, each ``part_of`` the root."""
    lines = [
        "nodes:",
        f"  - ref_id: {service}",
        "    kind: service",
        f"    summary: The {service} service.",
        '    source: ""',
    ]
    for ref_id, source in nodes.items():
        lines += [
            f"  - ref_id: {ref_id}",
            "    kind: service",
            f"    summary: The {ref_id} package.",
            f"    source: {source}/",
        ]
    lines.append("edges:")
    for ref_id in nodes:
        lines += [f"  - src: {ref_id}", f"    dst: {service}", "    kind: part_of"]
    return "\n".join(lines) + "\n"


def _imports(*paths: str) -> str:
    return "import (\n" + "".join(f'\t"{path}"\n' for path in paths) + ")\n"


def _rewrite(state: dict[str, Any], rel_path: str, text: str) -> None:
    """Write *text* over one file of the fixture, then update its index incrementally."""
    (state["root"] / rel_path).write_text(text, encoding="utf-8")
    incremental_reindex(state["root"])


#: A Go service whose ledger imports berths under the module path `example.org/harbour`.
_HARBOUR: dict[str, str] = {
    "go.mod": "module example.org/quay\n\ngo 1.22\n",
    "internal/berths/berths.go": "package berths\n",
    "internal/ledger/ledger.go": "package ledger\n\n"
    + _imports("example.org/harbour/internal/berths"),
}
_HARBOUR_NODES = {"berths": "internal/berths", "ledger": "internal/ledger"}
_HARBOUR_CONFIG = "scan_paths:\n- internal\nlanguages:\n- .go\n"
_HARBOUR_GO_MOD = "module example.org/harbour\n\ngo 1.22\n"

#: A workspace whose orders module imports `example.org/money`, a path the module under
#: `libs/money` does not declare: only the workspace's `replace` maps it there.
_WORKSPACE_USE = "go 1.22\n\nuse ./services/orders\n"
_WORKSPACE: dict[str, str] = {
    "go.work": _WORKSPACE_USE,
    "services/orders/go.mod": "module example.org/orders\n",
    "services/orders/orders.go": "package orders\n\n" + _imports("example.org/money/fx"),
    "libs/money/go.mod": "module example.org/cash\n",
    "libs/money/fx/fx.go": "package fx\n",
}
_WORKSPACE_NODES = {"orders": "services/orders", "money": "libs/money"}
_WORKSPACE_CONFIG = "scan_paths:\n- services\n- libs\nlanguages:\n- .go\n"
_WORKSPACE_GO_WORK = _WORKSPACE_USE + "\nreplace example.org/money => ./libs/money\n"


def _package_swift(core_path: str) -> str:
    return (
        "// swift-tools-version:5.9\n"
        "import PackageDescription\n\n"
        "let package = Package(\n"
        '    name: "Tides",\n'
        "    targets: [\n"
        '        .executableTarget(name: "App", dependencies: ["Core"]),\n'
        f'        .target(name: "Core", path: "{core_path}"),\n'
        "    ]\n"
        ")\n"
    )


#: A Swift package whose App imports Core, and Core's code is under `Modules/CoreKit`.
_TIDES: dict[str, str] = {
    "Package.swift": _package_swift("Modules/Missing"),
    "Sources/App/main.swift": "import Core\n\nprint(Tide())\n",
    "Modules/CoreKit/Tide.swift": "public struct Tide {}\n",
}
_TIDES_NODES = {"app": "Sources/App", "core": "Modules/CoreKit"}
_TIDES_CONFIG = "scan_paths:\n- Sources\n- Modules\nlanguages:\n- .swift\n"

#: A module whose path has no slash; its command imports the module's root package.
_TIDEWATER: dict[str, str] = {
    "tidewater/go.mod": "module tidewater\n\ngo 1.22\n",
    "tidewater/tide.go": "package tidewater\n",
    "tidewater/cmd/tide/main.go": "package main\n\n" + _imports("fmt", "tidewater"),
}
_TIDEWATER_NODES = {"tide": "tidewater", "cli": "tidewater/cmd"}
_TIDEWATER_CONFIG = "scan_paths:\n- tidewater\nlanguages:\n- .go\n"


@given("a Go service whose go.mod declares a module path its imports do not use")
def _go_service(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "quayside"
    write_project(root, _graph("quayside", _HARBOUR_NODES), _HARBOUR_CONFIG, _HARBOUR)
    state["root"] = root


@given("a Go workspace whose go.work does not yet replace the money module")
def _go_workspace(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "market"
    write_project(root, _graph("market", _WORKSPACE_NODES), _WORKSPACE_CONFIG, _WORKSPACE)
    state["root"] = root


@given("a Swift package whose manifest places the Core target in a folder that holds no code")
def _swift_package(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "tides"
    write_project(root, _graph("tides", _TIDES_NODES), _TIDES_CONFIG, _TIDES)
    state["root"] = root


@given("a Go module named tidewater whose command imports the module's root package")
def _root_package(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "estuary"
    write_project(root, _graph("estuary", _TIDEWATER_NODES), _TIDEWATER_CONFIG, _TIDEWATER)
    state["root"] = root


@when("go.mod is rewritten to declare the module path the imports use and the index is updated")
def _go_mod_rewritten(state: dict[str, Any]) -> None:
    _rewrite(state, "go.mod", _HARBOUR_GO_MOD)


@when("go.work is rewritten to replace the money module with its folder and the index is updated")
def _go_work_rewritten(state: dict[str, Any]) -> None:
    _rewrite(state, "go.work", _WORKSPACE_GO_WORK)


@when("Package.swift is rewritten to place Core where its code is and the index is updated")
def _package_swift_rewritten(state: dict[str, Any]) -> None:
    _rewrite(state, "Package.swift", _package_swift("Modules/CoreKit"))
