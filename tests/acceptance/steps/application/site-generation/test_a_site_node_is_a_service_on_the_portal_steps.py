"""Step implementations for `site-generation/a_site_node_is_a_service_on_the_portal.feature`.

BDL-080 S1a (`beadloom-je0i`), RFC D1. Against a real project directory, the
real reindex and the real site generator: the graph file declares the portal
`kind: site`, and every reader the portal is built from is read back from what
`generate_site` wrote — the page tree, the generated VitePress config and the
two data files — because those are the whole of what a reader of the portal sees.

The module is named ``test_*`` so default pytest collection picks the scenarios up.
"""

from __future__ import annotations

import json
import re
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.reindex import reindex
from beadloom.application.site.generate import generate_site

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/a_site_node_is_a_service_on_the_portal.feature")

PORTAL = "atlas-portal"
ROOT = "atlas"

#: A fixed instant for the one wall-clock read `generate_site` makes.
_NOW = "2026-10-08T00:00:00+00:00"

#: The generated VitePress module the nav is written into.
_NAV_MODULE = ".vitepress/config.generated.mjs"

#: The landscape's Mermaid page, whose `click <id> "<url>"` lines are the diagram's links.
_LANDSCAPE_DIAGRAM = "landscape-diagram.md"
_CLICK = re.compile(r'^\s*click \S+ "([^"]+)"', re.MULTILINE)

_CONTRACT = """\
    contract:
      protocol: portal-data
      message_type: portal-bundle
      direction: {kind}
"""


def _edge(src: str, dst: str, kind: str) -> str:
    edge = f"  - src: {src}\n    dst: {dst}\n    kind: {kind}\n"
    return edge + _CONTRACT.format(kind=kind) if kind in {"produces", "consumes"} else edge


def _graph(kind: str) -> str:
    nodes = (
        "nodes:\n"
        f"  - ref_id: {ROOT}\n"
        "    kind: service\n"
        "    summary: The atlas product.\n"
        f"  - ref_id: {PORTAL}\n"
        f"    kind: {kind}\n"
        "    summary: The atlas portal.\n"
    )
    edges = (
        _edge(PORTAL, ROOT, "part_of")
        + _edge(ROOT, PORTAL, "produces")
        + _edge(PORTAL, ROOT, "consumes")
    )
    return f"{nodes}edges:\n{edges}"


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / ROOT, "site": tmp_path / "site"}


@given(
    parsers.parse(
        'a project whose portal node is declared with the kind "{kind}" '
        "and consumes the data the product produces"
    )
)
def _project(world: dict[str, Any], kind: str) -> None:
    graph_dir = world["root"] / ".beadloom" / "_graph"
    graph_dir.mkdir(parents=True)
    (graph_dir / "atlas.yml").write_text(_graph(kind), encoding="utf-8")
    reindex(world["root"])


@when("the site is generated for the project")
def _generate(world: dict[str, Any]) -> None:
    conn = sqlite3.connect(world["root"] / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        generate_site(conn, world["site"], project_root=world["root"], now_ts=_NOW)
    finally:
        conn.close()


@then(parsers.parse('the portal node\'s page is "{page}" and there is none under "{other}"'))
def _page(world: dict[str, Any], page: str, other: str) -> None:
    site: Path = world["site"]
    assert (site / page).is_file()
    assert not (site / other / f"{PORTAL}.md").exists()


@then(parsers.parse('the nav links the portal node at "{link}"'))
def _nav(world: dict[str, Any], link: str) -> None:
    nav = (world["site"] / _NAV_MODULE).read_text(encoding="utf-8")
    assert f'link: "{link}"' in nav


def _group_in(world: dict[str, Any], data_file: str) -> str:
    data = json.loads((world["site"] / "public" / data_file).read_text(encoding="utf-8"))
    nodes = {str(node["id"]): node for node in data["nodes"]}
    return str(nodes[PORTAL]["group"])


@then(parsers.parse('the architecture data file groups the portal node with "{group}"'))
def _architecture_group(world: dict[str, Any], group: str) -> None:
    assert _group_in(world, "architecture.data.json") == group


@then(parsers.parse('the landscape data file groups the portal node with "{group}"'))
def _landscape_group(world: dict[str, Any], group: str) -> None:
    assert _group_in(world, "landscape.data.json") == group


def _diagram_links(world: dict[str, Any]) -> list[str]:
    diagram = (world["site"] / _LANDSCAPE_DIAGRAM).read_text(encoding="utf-8")
    return _CLICK.findall(diagram)


@then(parsers.parse('the landscape diagram links the portal node at "{link}"'))
def _diagram_link(world: dict[str, Any], link: str) -> None:
    diagram = (world["site"] / _LANDSCAPE_DIAGRAM).read_text(encoding="utf-8")
    node_id = "n_" + PORTAL.replace("-", "_")
    assert f'click {node_id} "{link}"' in diagram


@then(parsers.parse('the landscape data file links the portal node at "{link}"'))
def _landscape_link(world: dict[str, Any], link: str) -> None:
    data = json.loads((world["site"] / "public" / "landscape.data.json").read_text("utf-8"))
    nodes = {str(node["id"]): node for node in data["nodes"]}
    assert nodes[PORTAL]["url"] == link


@then("every page the landscape diagram links to is a page of the site")
def _diagram_links_are_pages(world: dict[str, Any]) -> None:
    links = _diagram_links(world)
    assert links
    missing = [url for url in links if not (world["site"] / f"{url.lstrip('/')}.md").is_file()]
    assert missing == []
