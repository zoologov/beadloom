"""Step implementations for `graph/import-resolver/go_module_imports.feature`.

BDL-076 B5 (`beadloom-ujzb.14`). Nothing here is stubbed: the real `reindex` and
the real linter run over Go projects written to disk, because the subject is the
edge set and the findings a Go project gets, and a double would agree with
whatever the resolver does now.

**FAKES PROVE FAKES.** This repository holds no Go and no `go.mod`. Each fixture
has an `internal/` package whose name another module's path also ends in, and a
node sourced at `net/`, so a resolver that read segments or dotted paths instead
of the module path would draw an edge these scenarios forbid.

The shared When/Then steps are in this folder's `conftest.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    WriteProject = Callable[[Path, str, str, dict[str, str]], None]

pytest.importorskip("tree_sitter_go")

scenarios("../../../graph/import-resolver/go_module_imports.feature")


def _graph(service: str, nodes: dict[str, str]) -> str:
    """A root service and one node per source directory, each ``part_of`` the root."""
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


#: A Go service on the standard layout: `cmd/harbour/` is named after the module.
_HARBOUR: dict[str, str] = {
    "go.mod": "module example.org/harbour\n\ngo 1.22\n",
    "cmd/harbour/main.go": "package main\n\n"
    + _imports(
        "fmt",
        "net/http",
        "example.org/harbour/internal/berths",
        "example.org/harbour/internal/ledger",
    ),
    "internal/berths/berths.go": "package berths\n",
    "internal/ledger/ledger.go": "package ledger\n\n"
    + _imports("example.org/harbour/internal/berths", "github.com/acme/harbour/internal/berths"),
    "net/net.go": "package net\n",
}
_HARBOUR_NODES = {
    "harbour": "cmd/harbour",
    "berths": "internal/berths",
    "ledger": "internal/ledger",
    "net": "net",
}
_HARBOUR_CONFIG = "scan_paths:\n- cmd\n- internal\n- net\nlanguages:\n- .go\n"

#: A workspace of two modules: the orders module imports the money module.
_WORKSPACE: dict[str, str] = {
    "go.work": "go 1.22\n\nuse (\n\t./services/orders\n\t./libs/money\n)\n",
    "services/orders/go.mod": "module example.org/orders\n",
    "services/orders/orders.go": "package orders\n\n" + _imports("example.org/money/fx"),
    "libs/money/go.mod": "module example.org/money\n",
    "libs/money/fx/fx.go": "package fx\n",
}
_WORKSPACE_NODES = {"orders": "services/orders", "money": "libs/money"}
_WORKSPACE_CONFIG = "scan_paths:\n- services\n- libs\nlanguages:\n- .go\n"

#: The rule the deny scenario adds: the entry point may not import berths itself.
_DENY_BERTHS = (
    "version: 1\n"
    "rules:\n"
    "  - name: entry-reaches-berths-through-the-ledger\n"
    '    description: "The entry point reaches berths through the ledger"\n'
    "    severity: warn\n"
    "    deny:\n"
    "      from: { ref_id: harbour }\n"
    "      to: { ref_id: berths }\n"
)


@given("a Go service whose entry point is named after its module")
def _go_service(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "quayside"
    write_project(root, _graph("quayside", _HARBOUR_NODES), _HARBOUR_CONFIG, _HARBOUR)
    state["root"] = root


@given("a Go workspace whose orders module imports a package of its money module")
def _go_workspace(tmp_path: Path, state: dict[str, Any], write_project: WriteProject) -> None:
    root = tmp_path / "market"
    write_project(root, _graph("market", _WORKSPACE_NODES), _WORKSPACE_CONFIG, _WORKSPACE)
    state["root"] = root


@given("a warn rule that denies the entry point any import of the berths package")
def _deny_rule(state: dict[str, Any]) -> None:
    rules = state["root"] / ".beadloom" / "_graph" / "rules.yml"
    rules.write_text(_DENY_BERTHS, encoding="utf-8")


@when("the project is linted")
def _linted(state: dict[str, Any]) -> None:
    from beadloom.application.reindex import reindex

    state["lint"] = lint(state["root"], reindex=reindex)


@then(parsers.parse('the rule reports "{file_path}" importing "{ref_id}"'))
def _rule_reports(state: dict[str, Any], file_path: str, ref_id: str) -> None:
    found = [
        (violation.file_path, violation.to_ref_id)
        for violation in state["lint"].violations
        if violation.rule_name == "entry-reaches-berths-through-the-ledger"
    ]
    assert found == [(file_path, ref_id)]
