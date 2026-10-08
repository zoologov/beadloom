"""Step implementations for `graph/site_is_an_alias_of_service.feature`.

BDL-080 S1a (`beadloom-je0i`), RFC D1. Nothing here is stubbed: the real
`load_graph`, the real `reindex` command and the real linter run over a project
written on disk, because the subject is what those readers see of a node the
graph file declares `kind: site`.

The fixture is `atlas` with its portal `atlas-portal`, a project this repository
cannot be mistaken for: our own portal is declared `kind: service`.

The module is named `test_*` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from click.testing import CliRunner
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.graph.linter import lint
from beadloom.graph.loader import load_graph
from beadloom.infrastructure.db import create_schema, open_db
from beadloom.services.cli import main

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../graph/graph-loader/site_is_an_alias_of_service.feature")

#: The portal node, and the root service it is part of.
PORTAL = "atlas-portal"
ROOT = "atlas"

_PART_OF_ROOT = f"""\
  - src: {PORTAL}
    dst: {ROOT}
    kind: part_of
"""

_RULES = f"""\
version: 3
rules:
  - name: service-needs-parent
    description: "Every service except the root is part of the root"
    require:
      for: {{ kind: service, exclude: [{ROOT}] }}
      has_edge_to: {{ ref_id: {ROOT} }}
      edge_kind: part_of
"""


def _graph(*, kind: str, with_parent: bool) -> str:
    edges = f"edges:\n{_PART_OF_ROOT}" if with_parent else "edges: []\n"
    return (
        "nodes:\n"
        f"  - ref_id: {ROOT}\n"
        "    kind: service\n"
        "    summary: The atlas product.\n"
        f"  - ref_id: {PORTAL}\n"
        f"    kind: {kind}\n"
        "    summary: The atlas portal.\n"
        f"{edges}"
    )


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / ROOT}


def _write_project(world: dict[str, Any], *, kind: str, with_parent: bool) -> None:
    graph_dir = world["root"] / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "atlas.yml").write_text(_graph(kind=kind, with_parent=with_parent))
    (graph_dir / "rules.yml").write_text(_RULES)
    world["graph_dir"] = graph_dir


@given(parsers.parse('a graph whose portal node is declared with the kind "{kind}"'))
@given(parsers.parse('a project whose portal node is declared with the kind "{kind}"'))
def _declared(world: dict[str, Any], kind: str) -> None:
    _write_project(world, kind=kind, with_parent=True)


@given(
    parsers.parse(
        'a project whose portal node is declared with the kind "{kind}" and has no parent'
    )
)
def _declared_orphan(world: dict[str, Any], kind: str) -> None:
    _write_project(world, kind=kind, with_parent=False)


@when("the graph is loaded")
def _load(world: dict[str, Any], tmp_path: Path) -> None:
    conn = open_db(tmp_path / "load.db")
    create_schema(conn)
    world["result"] = load_graph(world["graph_dir"], conn)
    world["conn"] = conn


@when("the project is reindexed from the command line")
def _reindex_cli(world: dict[str, Any]) -> None:
    outcome = CliRunner().invoke(main, ["reindex", "--full", "--project", str(world["root"])])
    assert outcome.exit_code == 0, outcome.output
    world["output"] = outcome.output


@when("the project is linted")
def _lint(world: dict[str, Any]) -> None:
    world["lint"] = lint(world["root"], reindex=reindex)


@then(parsers.parse('the portal node\'s kind in the graph is "{kind}"'))
def _kind_in_graph(world: dict[str, Any], kind: str) -> None:
    row = world["conn"].execute("SELECT kind FROM nodes WHERE ref_id = ?", (PORTAL,)).fetchone()
    assert row[0] == kind


@then(
    parsers.parse(
        'the load reports one info line naming the portal node, "{alias}" and "{canonical}"'
    )
)
def _one_info_line(world: dict[str, Any], alias: str, canonical: str) -> None:
    infos = world["result"].infos
    assert len(infos) == 1, infos
    assert all(word in infos[0] for word in (PORTAL, f"'{alias}'", f"'{canonical}'")), infos


@then("the load reports no error and no warning about the portal node")
def _nothing_else(world: dict[str, Any]) -> None:
    result = world["result"]
    assert not [line for line in (*result.errors, *result.warnings) if PORTAL in line]


@then(
    parsers.parse(
        'the output carries an info line naming the portal node, "{alias}" and "{canonical}"'
    )
)
def _info_in_output(world: dict[str, Any], alias: str, canonical: str) -> None:
    lines = [line for line in world["output"].splitlines() if "[info]" in line]
    assert any(
        all(word in line for word in (PORTAL, f"'{alias}'", f"'{canonical}'")) for line in lines
    ), world["output"]


@then("the rule that requires every service to have a parent names the portal node")
def _rule_judges_portal(world: dict[str, Any]) -> None:
    named = [v for v in world["lint"].violations if v.rule_name == "service-needs-parent"]
    assert [v.from_ref_id for v in named] == [PORTAL], named
