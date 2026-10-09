"""Steps for `graph/rule-engine/slice_rules.feature` (BDL-080 S3c, `beadloom-5t8d`).

The synthetic FSD frontend of `tests/support/fsd_tree.py` on disk, a graph of its slices
written by hand, and the real `beadloom lint --format json`, which reindexes first:
the imports the rules read are the ones the resolver resolved, through the tsconfig
`@/*` path and the `@features` alias the config declares. Nothing is mocked.
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

scenarios("../../../graph/rule-engine/slice_rules.feature")

_SLICES = {
    "pages-home": ("src/pages/home/", "fsd-pages"),
    "pages-profile": ("src/pages/profile/", "fsd-pages"),
    "widgets-header": ("src/widgets/header/", "fsd-widgets"),
    "features-auth": ("src/features/auth/", "fsd-features"),
    "features-cart": ("src/features/cart/", "fsd-features"),
    "entities-user": ("src/entities/user/", "fsd-entities"),
    "entities-product": ("src/entities/product/", "fsd-entities"),
    "shared": ("src/shared/", "fsd-shared"),
}
_SLICE_TAGS = "[fsd-pages, fsd-widgets, fsd-features, fsd-entities]"


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "orchard-web"}


@given("the synthetic FSD frontend with a hand-written graph of its slices")
def _project(world: dict[str, Any]) -> None:
    root = write_fsd_tree(world["root"])
    graph_dir = root / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (root / ".beadloom" / "config.yml").write_text(
        yaml.safe_dump(
            {
                "scan_paths": ["src"],
                "languages": [".ts", ".vue"],
                "imports": {"aliases": {"@features": "src/features"}},
            }
        ),
        encoding="utf-8",
    )
    nodes = [{"ref_id": "orchard-web", "kind": "service", "summary": "web", "source": ""}]
    nodes += [
        {"ref_id": ref, "kind": "component", "summary": ref, "source": source, "tags": [tag]}
        for ref, (source, tag) in _SLICES.items()
    ]
    edges = [{"src": ref, "dst": "orchard-web", "kind": "part_of"} for ref in _SLICES]
    (graph_dir / "services.yml").write_text(
        yaml.safe_dump({"nodes": nodes, "edges": edges}), encoding="utf-8"
    )


def _rules(world: dict[str, Any], block: str) -> None:
    (world["root"] / ".beadloom" / "_graph" / "rules.yml").write_text(
        "version: 3\nrules:\n  - name: fsd-slices\n" + block, encoding="utf-8"
    )


@given("the rules declare slice_public_api over the four sliced layers")
def _public_api(world: dict[str, Any]) -> None:
    _rules(world, f"    slice_public_api:\n      tags: {_SLICE_TAGS}\n")


@given("the rules declare slice_shape over the four sliced layers")
def _shape(world: dict[str, Any]) -> None:
    _rules(world, f"    slice_shape:\n      tags: {_SLICE_TAGS}\n")


@given(parsers.parse('the rules declare slice_public_api over the tag "{tag}"'))
def _public_api_over(world: dict[str, Any], tag: str) -> None:
    _rules(world, f"    slice_public_api:\n      tags: [{tag}]\n")


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    result = CliRunner().invoke(
        main, ["lint", "--format", "json", "--project", str(world["root"])]
    )
    world["violations"] = json.loads(result.stdout)["violations"]


def _of_type(world: dict[str, Any], rule_type: str) -> list[dict[str, Any]]:
    return [v for v in world["violations"] if v["rule_type"] == rule_type]


@then(parsers.parse('"{rule_type}" reports "{importer}" reaching into "{slice_ref}"'))
def _reaching(world: dict[str, Any], rule_type: str, importer: str, slice_ref: str) -> None:
    found = [(v["file_path"], v["to_ref_id"]) for v in _of_type(world, rule_type)]
    assert (importer, slice_ref) in found, found


@then(parsers.parse('"{rule_type}" reports nothing from "{importer}"'))
def _nothing_from(world: dict[str, Any], rule_type: str, importer: str) -> None:
    assert [v for v in _of_type(world, rule_type) if v["file_path"] == importer] == []


@then(parsers.parse('"{rule_type}" reports the folder "{folder}" of "{slice_ref}"'))
def _folder(world: dict[str, Any], rule_type: str, folder: str, slice_ref: str) -> None:
    found = [v["message"] for v in _of_type(world, rule_type) if v["from_ref_id"] == slice_ref]
    assert any(f"'{folder}'" in message for message in found), found


@then(parsers.parse('"{rule_type}" reports nothing about "{slice_ref}"'))
def _nothing_about(world: dict[str, Any], rule_type: str, slice_ref: str) -> None:
    assert [v for v in _of_type(world, rule_type) if v["from_ref_id"] == slice_ref] == []


@then(parsers.parse('the rule is reported as checking nothing because no node carries "{tag}"'))
def _inert(world: dict[str, Any], tag: str) -> None:
    found = [v["message"] for v in _of_type(world, "rule_liveness")]
    assert any("cannot fire" in m and tag in m for m in found), found
