"""Steps of `onboarding/agent-prime/init_reads_slice_groups_and_pages_first.feature`.

BDL-082 S2a (`beadloom-6e2o`). The real `beadloom init` and `beadloom lint --strict --format
json` run through the CLI on the specification's examples of `tests/support/fsd_spec_examples.py`;
the graph is read back from the YAML init wrote, which is what an adopter commits. Nothing is
patched.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.fsd_spec_examples import (
    GROUP,
    NESTED_GROUP,
    PRE_MIGRATION_SLICE,
    pages_first,
    write_example,
)

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../onboarding/agent-prime/init_reads_slice_groups_and_pages_first.feature")

#: The rules file `init` wrote for this tree before BDL-082, as far as this case needs it: the
#: limit on the pages layer an adopter may keep, and the feature limit beside it.
_EARLIER_RULES = """\
# The rules `beadloom init` wrote for a Feature-Sliced Design frontend (preset `fsd`).
version: 3
rules:
  - name: fsd-cohesion-pages
    description: "A slice of the pages layer owns at most 60 symbols"
    severity: warn
    check:
      for: { kind: component, tag: fsd-pages }
      max_symbols: 60
  - name: fsd-cohesion-features
    description: "A slice of the features layer owns at most 60 symbols"
    severity: warn
    check:
      for: { kind: component, tag: fsd-features }
      max_symbols: 60
"""


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(
    parsers.parse('the specification\'s slice group "{group}" holding "{first}" and "{second}"')
)
def _group(tmp_path: Path, state: dict[str, Any], group: str, first: str, second: str) -> None:
    assert {f"src/{group}/{first}/index.ts", f"src/{group}/{second}/index.ts"} <= set(GROUP)
    state["root"] = write_example(tmp_path / "probe", GROUP)


@given(
    parsers.parse(
        'a slice group "{group}" holding only the group "{inner}" of "{first}" and "{second}"'
    )
)
def _nested_group(
    tmp_path: Path, state: dict[str, Any], group: str, inner: str, first: str, second: str
) -> None:
    folders = {path.rsplit("/", 2)[0] for path in NESTED_GROUP if path.startswith(f"src/{group}/")}
    assert {f"src/{group}/{inner}/{first}", f"src/{group}/{inner}/{second}"} <= folders
    state["root"] = write_example(tmp_path / "probe", NESTED_GROUP)


@given(
    parsers.parse(
        'a slice "{folder}" with code at its top and a component "{component}" holding an index'
    )
)
def _pre_migration(tmp_path: Path, state: dict[str, Any], folder: str, component: str) -> None:
    top = [p for p in PRE_MIGRATION_SLICE if p.rsplit("/", 1)[0] == f"src/{folder}"]
    assert top, PRE_MIGRATION_SLICE
    assert f"src/{folder}/{component}/index.ts" in PRE_MIGRATION_SLICE
    state["root"] = write_example(tmp_path / "probe", PRE_MIGRATION_SLICE)


@given("a pages-first frontend whose page and feature each own 90 symbols")
def _pages_first(tmp_path: Path, state: dict[str, Any]) -> None:
    state["root"] = write_example(tmp_path / "probe", pages_first(with_large_feature=True))


@given("a rules file written by an earlier init that limits the pages layer")
def _earlier_rules(state: dict[str, Any]) -> None:
    rules = state["root"] / ".beadloom" / "_graph" / "rules.yml"
    rules.parent.mkdir(parents=True)
    rules.write_text(_EARLIER_RULES, encoding="utf-8")
    state["rules_before"] = rules.read_bytes()


@when(parsers.parse("beadloom init is run with {flag}"))
def _init(state: dict[str, Any], flag: str) -> None:
    result = CliRunner().invoke(main, ["init", flag, "--project", str(state["root"])])
    assert result.exception is None or isinstance(result.exception, SystemExit), result.output
    state["init_output"] = result.output
    graph = yaml.safe_load(
        (state["root"] / ".beadloom" / "_graph" / "services.yml").read_text(encoding="utf-8")
    )
    state["nodes"] = {node["ref_id"]: node for node in graph["nodes"]}


@when("beadloom lint --strict is run")
def _lint(state: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--strict", "--format", "json", "--project", str(state["root"])]
    )
    state["lint"] = json.loads(result.stdout)


def _violations(state: dict[str, Any], rule: str) -> list[dict[str, Any]]:
    return [v for v in state["lint"]["violations"] if v["rule_name"] == rule]


@then(parsers.parse('the graph holds the node "{ref_id}" tagged "{tag}"'))
def _node(state: dict[str, Any], ref_id: str, tag: str) -> None:
    assert state["nodes"][ref_id]["tags"] == [tag], state["nodes"]


@then(parsers.parse('the graph holds no node for the folder "{folder}"'))
def _no_node(state: dict[str, Any], folder: str) -> None:
    sources = {node.get("source") for node in state["nodes"].values()}
    assert f"{folder}/" not in sources, sources


@then(parsers.parse('lint reports "{rule}" for the edge "{src}" -> "{dst}"'))
def _reported_edge(state: dict[str, Any], rule: str, src: str, dst: str) -> None:
    found = _violations(state, rule)
    assert any(
        v.get("from_ref_id") == src and v.get("to_ref_id") == dst and v["severity"] == "error"
        for v in found
    ), found


@then(parsers.parse('lint reports "{rule}" for "{ref_id}"'))
def _reported(state: dict[str, Any], rule: str, ref_id: str) -> None:
    found = _violations(state, rule)
    assert any(v.get("from_ref_id") == ref_id for v in found), found


@then(parsers.parse('lint reports no "{rule}" finding'))
def _not_reported(state: dict[str, Any], rule: str) -> None:
    found = [v for v in _violations(state, rule) if v["rule_type"] != "rule_liveness"]
    assert found == [], found


@then("lint reports no finding of code at a group's top")
def _no_group_top(state: dict[str, Any]) -> None:
    found = [v for v in _violations(state, "fsd-slice-shape") if "Group folder" in v["message"]]
    assert found == [], found


@then("the rules file is byte for byte the one the adopter had")
def _rules_kept(state: dict[str, Any]) -> None:
    rules = state["root"] / ".beadloom" / "_graph" / "rules.yml"
    assert rules.read_bytes() == state["rules_before"]
