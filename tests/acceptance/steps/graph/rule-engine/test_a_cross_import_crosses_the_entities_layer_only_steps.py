"""Steps for `graph/rule-engine/a_cross_import_crosses_the_entities_layer_only.feature`.

BDL-082 S1a (`beadloom-r15q`). Each scenario writes the specification's `@x` example (or one
step from it) to disk with a graph of its slices by hand, and runs the real
`beadloom lint --format json`, which reindexes first: the edge fact the layer rule reads is
the one the reindex recorded from the imports the resolver resolved. Nothing is mocked.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.services.cli import main
from tests.support.fsd_cross_import_tree import (
    FEATURE_SLICES,
    FEATURES_CROSS_IMPORT,
    FSD_LAYERS_RULE,
    SPEC_CROSS_IMPORTS,
    SPEC_SLICES,
    write_fsd_project,
)

if TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("tree_sitter_typescript")

scenarios("../../../graph/rule-engine/a_cross_import_crosses_the_entities_layer_only.feature")


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "probe", "files": {}, "slices": (), "declared": []}


@given("the specification's artist entity importing the song's API for it three ways")
def _spec(world: dict[str, Any]) -> None:
    world["files"] = dict(SPEC_CROSS_IMPORTS)
    world["slices"] = SPEC_SLICES


@given('the feature "b" importing the API the feature "a" opens to it')
def _features(world: dict[str, Any]) -> None:
    world["files"] = dict(FEATURES_CROSS_IMPORT)
    world["slices"] = FEATURE_SLICES


@given(parsers.parse('"{importer}" importing the song through its index on line 2'))
def _mixed(world: dict[str, Any], importer: str) -> None:
    first_line = world["files"][importer].splitlines()[0]
    world["files"][importer] = (
        f"{first_line}\nimport {{ type Song as Plain }} from '@/entities/song'\n"
        "export const rel = (s: Song, t: Plain) => [s, t]\n"
    )


@given(parsers.parse('the graph declares "{src}" depending on "{dst}"'))
def _declared(world: dict[str, Any], src: str, dst: str) -> None:
    world["declared"].append((src, dst))


@given("the rules declare the Feature-Sliced layers")
def _rules(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    write_fsd_project(root, world["files"], world["slices"], declared=world["declared"])
    (root / ".beadloom" / "_graph" / "rules.yml").write_text(FSD_LAYERS_RULE, encoding="utf-8")


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--format", "json", "--project", str(world["root"])]
    )
    world["violations"] = json.loads(result.stdout)["violations"]


def _between(world: dict[str, Any], src: str, dst: str) -> list[dict[str, Any]]:
    return [
        v
        for v in world["violations"]
        if v["rule_name"] == "fsd-layers" and (v["from_ref_id"], v["to_ref_id"]) == (src, dst)
    ]


@then(parsers.parse('the layer rule reports nothing between "{src}" and "{dst}"'))
def _nothing(world: dict[str, Any], src: str, dst: str) -> None:
    assert _between(world, src, dst) == [], world["violations"]


@then(parsers.parse('the layer rule reports "{src}" depending on "{dst}" once'))
def _once(world: dict[str, Any], src: str, dst: str) -> None:
    found = _between(world, src, dst)
    assert len(found) == 1, world["violations"]
    world["finding"] = found[0]


@then(parsers.parse('that finding says "{text}"'))
def _says(world: dict[str, Any], text: str) -> None:
    assert text in world["finding"]["message"], world["finding"]


@then(parsers.parse('that finding does not say "{text}"'))
def _does_not_say(world: dict[str, Any], text: str) -> None:
    assert text not in world["finding"]["message"], world["finding"]


@then(parsers.parse('that finding sits at line {line:d} of "{path}"'))
def _sits_at(world: dict[str, Any], line: int, path: str) -> None:
    finding = world["finding"]
    assert (finding["file_path"], finding["line_number"]) == (path, line), finding
    assert f"{path}:{line}" in finding["message"]
