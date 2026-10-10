"""Step implementations for `onboarding/agent-prime/init_on_a_feature_sliced_frontend.feature`.

BDL-080 S3c (`beadloom-5t8d`). The real `beadloom init --bootstrap` and `beadloom lint
--strict --format json` run through the CLI on the synthetic tree of
`tests/support/fsd_tree.py`; the graph is read back from the YAML init wrote, which is
what an adopter commits. Nothing is patched.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.fsd_tree import write_fsd_tree

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../onboarding/agent-prime/init_on_a_feature_sliced_frontend.feature")


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given("a frontend in the Feature-Sliced layout with legacy folders beside its layers")
def _tree(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = write_fsd_tree(tmp_path / "orchard-web")


@when("beadloom init is run with --bootstrap")
def _init(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(main, ["init", "--bootstrap", "--project", str(state["root"])])
    # The tree breaks the rules init writes, on purpose; the exit code is a scenario's.
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    state["init_exit"] = result.exit_code
    state["init_output"] = result.output
    graph = yaml.safe_load(
        (state["root"] / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    state["nodes"] = {node["ref_id"]: node for node in graph["nodes"]}
    state["parents"] = {
        edge["src"]: edge["dst"] for edge in graph["edges"] if edge["kind"] == "part_of"
    }
    state["root_ref"] = graph["nodes"][0]["ref_id"]


@when("beadloom lint --strict is run")
def _lint(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--strict", "--format", "json", "--project", str(state["root"])]
    )
    state["lint_exit"] = result.exit_code
    state["lint"] = json.loads(result.stdout)


@then(parsers.parse('init chose the "{preset}" preset'))
def _preset(state: dict[str, Any], preset: str) -> None:
    assert f"(preset: {preset})" in state["init_output"]


def _placed(state: dict[str, Any], ref_id: str, tag: str, parent: str) -> None:
    node = state["nodes"][ref_id]
    assert node["kind"] == "component"
    assert node["tags"] == [tag]
    assert state["parents"][ref_id] == parent


@then(parsers.parse('the node "{ref_id}" is a component tagged "{tag}" and part of the root'))
def _part_of_root(state: dict[str, Any], ref_id: str, tag: str) -> None:
    _placed(state, ref_id, tag, state["root_ref"])


@then(parsers.parse('the node "{ref_id}" is a component tagged "{tag}" and part of "{parent}"'))
def _part_of(state: dict[str, Any], ref_id: str, tag: str, parent: str) -> None:
    _placed(state, ref_id, tag, parent)


@then(parsers.parse('no node is written for the layer folder "{folder}"'))
def _no_layer_node(state: dict[str, Any], folder: str) -> None:
    assert [r for r, n in state["nodes"].items() if n.get("source") == f"{folder}/"] == []


@then("init wrote no depends_on edge into the graph YAML")
def _no_declared_imports(state: dict[str, Any]) -> None:
    graph = yaml.safe_load(
        (state["root"] / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    assert [e for e in graph["edges"] if e["kind"] == "depends_on"] == []


@when(parsers.parse('the cross-import from "{path}" is removed'))
def _remove_cross_import(state: dict[str, Any], path: str) -> None:
    file = state["root"] / path
    text = file.read_text(encoding="utf-8")
    assert "from '@features/auth'" in text
    file.write_text(
        text.replace(
            "import { currentSession } from '@features/auth'",
            "const currentSession = () => 'guest'",
        ),
        encoding="utf-8",
    )


@then(parsers.parse('lint does not report "{rule}" for the edge "{src}" -> "{dst}"'))
def _not_reported_edge(state: dict[str, Any], rule: str, src: str, dst: str) -> None:
    found = _violations(state, rule)
    assert not any(v.get("from_ref_id") == src and v.get("to_ref_id") == dst for v in found), found


@then(parsers.parse("init exits {code:d}"))
def _init_exit(state: dict[str, Any], code: int) -> None:
    assert state["init_exit"] == code, state["init_output"]


@then(parsers.parse('init says "{text}"'))
def _init_says(state: dict[str, Any], text: str) -> None:
    assert text in state["init_output"], state["init_output"]


@then(parsers.parse('init does not say "{text}"'))
def _init_does_not_say(state: dict[str, Any], text: str) -> None:
    assert text not in state["init_output"], state["init_output"]


@then(parsers.parse("lint exits {code:d}"))
def _exit(state: dict[str, Any], code: int) -> None:
    assert state["lint_exit"] == code


def _violations(state: dict[str, Any], rule: str) -> list[dict[str, Any]]:
    return [v for v in state["lint"]["violations"] if v["rule_name"] == rule]


@then(parsers.parse('lint reports "{rule}" for "{subject}"'))
def _reported(state: dict[str, Any], rule: str, subject: str) -> None:
    found = _violations(state, rule)
    assert any(subject in (v.get("file_path"), v.get("from_ref_id")) for v in found), found


@then(parsers.parse('lint reports "{rule}" for the edge "{src}" -> "{dst}"'))
def _reported_edge(state: dict[str, Any], rule: str, src: str, dst: str) -> None:
    found = _violations(state, rule)
    assert any(v.get("from_ref_id") == src and v.get("to_ref_id") == dst for v in found), found


@then(parsers.parse('package.json runs "{command}" as "{script}"'))
def _script(state: dict[str, Any], command: str, script: str) -> None:
    package = json.loads((state["root"] / "package.json").read_text(encoding="utf-8"))
    assert package["scripts"][script] == command
    assert package["scripts"]["dev"] == "vite"
