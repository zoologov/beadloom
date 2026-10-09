"""Steps for `graph/rule-engine/cohesion_signal.feature` (BDL-080 S2b, `beadloom-5wh2`).

Against a real project directory, the real reindex and the real linter: each
scenario writes a graph whose slices own a known number of functions and lints it.
Nothing is mocked, because a size count read from a double proves the double.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.graph.linter import lint
from tests.support.tiered_project import write_tiered_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/rule-engine/cohesion_signal.feature")

#: ``ref_id -> (tags, functions it defines)``: two frontend layers and a backend
#: component that is larger than any slice and carries no frontend tag.
_GRAPH: dict[str, tuple[list[str], int]] = {
    "board": (["ui-widgets"], 5),
    "search": (["ui-features"], 4),
    "badge": (["ui-features"], 2),
    "ledger": (["tier-core"], 6),
}


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop"}


@given(
    parsers.parse(
        'a frontend with slices tagged "{first}" and "{second}" beside a backend'
    )
)
def _frontend(world: dict[str, Any], first: str, second: str) -> None:
    declared = {tag for tags, _ in _GRAPH.values() for tag in tags}
    assert {first, second} <= declared


@given(
    parsers.parse(
        'one size check over the components whose tag begins with "{prefix}", '
        "at most {limit:d} symbols"
    )
)
def _size_check(world: dict[str, Any], prefix: str, limit: int) -> None:
    world["rule"] = (
        "  - name: ui-cohesion\n"
        '    description: "a slice owns few symbols"\n'
        "    severity: warn\n"
        "    check:\n"
        f"      for: {{ kind: component, tag_prefix: {prefix} }}\n"
        f"      max_symbols: {limit}\n"
    )


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    nodes = [(ref_id, "component", tags) for ref_id, (tags, _) in _GRAPH.items()]
    modules = {
        f"src/{ref_id}/__init__.py": "".join(
            f"def {ref_id}_{index}() -> None:\n    return None\n\n\n"
            for index in range(functions)
        )
        for ref_id, (_, functions) in _GRAPH.items()
    }
    project = write_tiered_project(
        world["root"], nodes=nodes, edges=[], more_rules=world["rule"], modules=modules
    )
    world["result"] = lint(project)


def _size_findings(world: dict[str, Any]) -> dict[str, str]:
    return {
        str(v.from_ref_id): v.message
        for v in world["result"].violations
        if v.rule_type == "cardinality"
    }


@then(parsers.parse('"{ref_id}" is reported by "{rule}" as owning {count:d} symbols'))
def _reported(world: dict[str, Any], ref_id: str, rule: str, count: int) -> None:
    findings = _size_findings(world)
    assert ref_id in findings, findings
    assert f"has {count} symbols" in findings[ref_id], findings[ref_id]
    assert f"rule '{rule}'" in findings[ref_id], findings[ref_id]


@then(parsers.parse('no size finding names "{ref_id}"'))
def _not_reported(world: dict[str, Any], ref_id: str) -> None:
    findings = _size_findings(world)
    assert findings, "the rule judged nothing, so its silence about a node proves nothing"
    assert ref_id not in findings, findings


@then(
    parsers.parse(
        '"{rule}" is reported as checking nothing because no node carries a tag '
        'beginning with "{prefix}"'
    )
)
def _inert(world: dict[str, Any], rule: str, prefix: str) -> None:
    messages = [
        v.message
        for v in world["result"].violations
        if v.rule_name == rule and "cannot fire" in v.message
    ]
    assert any(f"tag beginning with '{prefix}'" in m for m in messages), messages
