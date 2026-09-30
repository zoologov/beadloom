"""Step implementations for `onboarding/agent-prime/init_on_a_go_layout.feature`.

BDL-076 B5 (`beadloom-ujzb.14`). The real `beadloom init --yes` runs through the
CLI on a Go repository written to disk, and the graph it writes is read back from
its YAML, which is what an adopter commits. Nothing is patched.

**FAKES PROVE FAKES.** This repository holds no Go. The repository's own folder
is named apart from its module, so the node of `cmd/harbour/` is written as
`harbour-service`, and the scan's old reading — the first segment of an import path that
names a cluster — would draw every internal import onto it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_go")

scenarios("../../../onboarding/agent-prime/init_on_a_go_layout.feature")


def _imports(*paths: str) -> str:
    return "import (\n" + "".join(f'\t"{path}"\n' for path in paths) + ")\n"


_REPOSITORY: dict[str, str] = {
    "go.mod": "module example.org/harbour\n\ngo 1.22\n",
    "cmd/harbour/main.go": "package main\n\n"
    + _imports(
        "net/http",
        "example.org/harbour/internal/berths",
        "example.org/harbour/internal/ledger",
    )
    + "\nfunc main() {}\n",
    "internal/berths/berths.go": "package berths\n\nfunc Free() int { return 1 }\n",
    "internal/ledger/ledger.go": "package ledger\n\n"
    + _imports("example.org/harbour/internal/berths")
    + "\nfunc Total() int { return berths.Free() }\n",
}


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("a Go repository whose entry point directory is named after its module")
def _repository(tmp_path: Path, state: dict[str, Any]) -> None:
    root = tmp_path / "quayside"
    for rel_path, text in _REPOSITORY.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    state["root"] = root


@when("beadloom init is run without prompts")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--yes", "--project", str(state["root"])])
    assert result.exit_code == 0, result.output


def _written_depends_on(root: Path) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for path in sorted((root / ".beadloom" / "_graph").glob("*.yml")):
        for edge in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("edges") or []:
            if edge.get("kind") == "depends_on":
                edges.add((str(edge["src"]), str(edge["dst"])))
    return edges


@then(parsers.parse("the graph init writes has exactly the depends_on edges {edges}"))
def _edges_exactly(state: dict[str, Any], edges: str) -> None:
    expected = {tuple(part.strip().split(" -> ")) for part in edges.replace('"', "").split(",")}
    assert _written_depends_on(state["root"]) == expected


@then(parsers.parse('no depends_on edge init writes points at "{ref_id}"'))
def _none_into(state: dict[str, Any], ref_id: str) -> None:
    assert [e for e in _written_depends_on(state["root"]) if e[1] == ref_id] == []
