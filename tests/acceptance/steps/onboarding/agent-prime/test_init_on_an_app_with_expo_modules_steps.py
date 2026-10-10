"""Step implementations for `onboarding/agent-prime/init_on_an_app_with_expo_modules.feature`.

BDL-080 S3b (`beadloom-wbqd`). The real `beadloom init --bootstrap` runs through the CLI on
the synthetic app of `tests/support/expo_module_tree.py`; the graph is read back from the
YAML init wrote, which is what an adopter commits, and the edges from the index init's own
reindex built. Nothing is patched.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.expo_module_tree import write_expo_app

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../onboarding/agent-prime/init_on_an_app_with_expo_modules.feature")


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("an Expo app with local Expo modules on iOS and Android")
def _tree(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = write_expo_app(tmp_path / "pathfinder-app")


@when("beadloom init is run with --bootstrap")
def _init(state: dict[str, Any]) -> None:
    root: Path = state["root"]
    result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(root)])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    state["init_output"] = result.output
    beadloom = root / ".beadloom"
    graph = yaml.safe_load((beadloom / "_graph" / "services.yml").read_text(encoding="utf-8"))
    state["nodes"] = {node["ref_id"]: node for node in graph["nodes"]}
    state["edges"] = graph.get("edges", [])
    state["parents"] = {
        edge["src"]: edge["dst"] for edge in state["edges"] if edge["kind"] == "part_of"
    }
    state["root_ref"] = graph["nodes"][0]["ref_id"]
    state["config"] = yaml.safe_load((beadloom / "config.yml").read_text(encoding="utf-8"))


def _placed(state: dict[str, Any], ref_id: str, source: str, parent: str) -> None:
    node = state["nodes"][ref_id]
    assert (node["kind"], node["source"]) == ("component", source)
    assert state["parents"][ref_id] == parent


@then(
    parsers.parse('the node "{ref_id}" is a component with source "{source}" and part of the root')
)
def _part_of_root(state: dict[str, Any], ref_id: str, source: str) -> None:
    _placed(state, ref_id, source, state["root_ref"])


@then(
    parsers.parse(
        'the node "{ref_id}" is a component with source "{source}" and part of "{parent}"'
    )
)
def _part_of(state: dict[str, Any], ref_id: str, source: str, parent: str) -> None:
    _placed(state, ref_id, source, parent)


@then(parsers.parse('no node is written for the folder "{folder}"'))
def _no_node_for(state: dict[str, Any], folder: str) -> None:
    assert [n for n in state["nodes"].values() if n.get("source") == folder] == []


@then("init does not report a file it did not read")
def _nothing_unread(state: dict[str, Any]) -> None:
    assert "Not read" not in state["init_output"], state["init_output"]


@then(parsers.parse('the scan paths hold "{first}" and "{second}"'))
def _scan_paths(state: dict[str, Any], first: str, second: str) -> None:
    assert {first, second} <= set(state["config"]["scan_paths"])


@then("init wrote no uses edge into the graph YAML")
def _no_uses_in_yaml(state: dict[str, Any]) -> None:
    assert [edge for edge in state["edges"] if edge["kind"] == "uses"] == []


@then(parsers.parse("the index holds the uses edges {edges}"))
def _uses_in_index(state: dict[str, Any], edges: str) -> None:
    expected = {tuple(part.strip().split(" -> ")) for part in edges.replace('"', "").split(",")}
    with sqlite3.connect(state["root"] / ".beadloom" / "beadloom.db") as conn:
        rows = conn.execute("SELECT src_ref_id, dst_ref_id FROM edges WHERE kind = 'uses'")
        assert {(str(src), str(dst)) for src, dst in rows.fetchall()} == expected
