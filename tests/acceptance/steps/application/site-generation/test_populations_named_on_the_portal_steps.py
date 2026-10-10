"""Steps for `application/site-generation/populations_named_on_the_portal.feature`.

BDL-080 S4a (`beadloom-5pxv`). Against a real project directory, the real
reindex, the real linter, the real debt report and the real site generator: the
project is written to disk, `generate_site` builds its portal, and the steps read
the two data files it publishes. The expected numbers come from the linter and
the debt report, run on the same index. Nothing is mocked.
"""

from __future__ import annotations

import json
import math
import sqlite3
from typing import TYPE_CHECKING, Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from beadloom.application.debt_report import (
    collect_debt_data,
    compute_top_offenders,
    load_debt_weights,
)
from beadloom.application.site.generate import generate_site
from beadloom.graph.linter import lint
from tests.support.tiered_project import write_tiered_project

if TYPE_CHECKING:
    from pathlib import Path

scenarios("../../../application/site-generation/populations_named_on_the_portal.feature")

_VIEW_DATA = "public/architecture.data.json"
_DASHBOARD_DATA = "public/dashboard.data.json"

#: A fixed instant for the one metrics point `generate_site` records.
_NOW = "2026-10-09T00:00:00+00:00"

#: A `deny` rule over a tag no node carries: lint reports that it cannot fire,
#: and that finding is about the rule, so it is bound to no node.
_INERT_RULE = (
    "  - name: nobody-reaches-core\n"
    '    description: "a deny over a tag nobody carries"\n'
    "    severity: warn\n"
    "    deny:\n"
    "      from: {tag: nobody}\n"
    "      to: {tag: tier-core}\n"
)

#: The box, its three tiers and a feature inside the top tier. `store -> core`
#: and `core -> api` run against `tier-order`'s direction.
_NODES = [
    ("shop", "service", []),
    ("api", "domain", ["tier-web"]),
    ("core", "domain", ["tier-core"]),
    ("store", "domain", ["tier-store"]),
    ("cart", "feature", ["tier-web"]),
]
_EDGES = [
    ("api", "shop", "part_of"),
    ("core", "shop", "part_of"),
    ("store", "shop", "part_of"),
    ("cart", "api", "part_of"),
    ("store", "core", "depends_on"),
    ("core", "api", "depends_on"),
]


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    return {"root": tmp_path / "shop", "site": tmp_path / "site"}


@given("a project whose layering lint finds against and one rule that cannot fire")
def _project(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    write_tiered_project(root, nodes=_NODES, edges=_EDGES, severity="warn", more_rules=_INERT_RULE)
    (root / "README.md").write_text("# Shop\n\nThe shop.\n", encoding="utf-8")
    (root / "README.ru.md").write_text("# Shop, in Russian\n\nThe shop.\n", encoding="utf-8")


@when("the site is generated for the project")
def _generate(world: dict[str, Any]) -> None:
    root: Path = world["root"]
    conn = sqlite3.connect(root / ".beadloom" / "beadloom.db")
    conn.row_factory = sqlite3.Row
    try:
        result = generate_site(conn, world["site"], project_root=root, now_ts=_NOW)
        weights = load_debt_weights(root)
        debt = collect_debt_data(conn, root, weights)
        world["debt"] = {
            offender.ref_id: offender
            for offender in compute_top_offenders(debt, weights, limit=len(debt.node_issues))
        }
    finally:
        conn.close()
    site: Path = world["site"]
    world["written"] = result.written
    world["data"] = json.loads((site / _VIEW_DATA).read_text(encoding="utf-8"))
    world["dashboard"] = json.loads((site / _DASHBOARD_DATA).read_text(encoding="utf-8"))
    world["lint"] = lint(root)


def _node(world: dict[str, Any], ref_id: str) -> dict[str, Any]:
    nodes = {str(node["id"]): node for node in world["data"]["nodes"]}
    return dict(nodes[ref_id])


@then("the data file's lint totals are the ones the linter reports")
def _totals(world: dict[str, Any]) -> None:
    reach = world["data"]["lint"]
    result = world["lint"]
    assert (reach["errors"], reach["warnings"]) == (result.error_count, result.warning_count)
    assert reach["warnings"] == len(result.violations)


@then(parsers.parse("the lint totals name {count:d} nodes with findings"))
def _nodes_with_findings(world: dict[str, Any], count: int) -> None:
    assert world["data"]["lint"]["nodes_with_findings"] == count
    carrying = [node["id"] for node in world["data"]["nodes"] if node["findings"]]
    assert sorted(carrying) == ["core", "store"]


@then(parsers.parse('the node-less findings of the data file are the rule "{rule}"'))
def _nodeless(world: dict[str, Any], rule: str) -> None:
    nodeless = world["data"]["lint"]["nodeless"]
    assert [finding["rule"] for finding in nodeless] == [rule]
    (finding,) = nodeless
    assert set(finding) == {"rule", "severity", "message", "file", "line"}
    (expected,) = [v for v in world["lint"].violations if v.from_ref_id is None]
    assert (finding["severity"], finding["message"]) == (expected.severity, expected.message)


@then("the dashboard's data file lists the same node-less findings")
def _nodeless_on_the_dashboard(world: dict[str, Any]) -> None:
    dashboard = world["dashboard"]["lint"]
    assert dashboard["nodeless"] == world["data"]["lint"]["nodeless"]
    assert dashboard["nodes_with_findings"] == world["data"]["lint"]["nodes_with_findings"]


_PARTS_OF_SHOP = ("api", "core", "store", "cart")


@then(parsers.parse('the debt inside the box "{box}" is the sum of its parts\' own debt'))
def _inside_sum(world: dict[str, Any], box: str) -> None:
    inside = _node(world, box)["debt"]["inside"]
    owed = [world["debt"][ref] for ref in _PARTS_OF_SHOP if ref in world["debt"]]
    assert inside["nodes"] == len(owed) > 0
    assert inside["score"] == math.fsum(offender.score for offender in owed)
    for ref in _PARTS_OF_SHOP:
        own = _node(world, ref)["debt"]["score"]
        assert own == (world["debt"][ref].score if ref in world["debt"] else 0.0)


@then(parsers.parse('the debt inside the box "{box}" counts its parts by each reason they carry'))
def _inside_by_reason(world: dict[str, Any], box: str) -> None:
    inside = _node(world, box)["debt"]["inside"]
    expected: dict[str, int] = {}
    for ref in _PARTS_OF_SHOP:
        if ref in world["debt"]:
            for reason in set(world["debt"][ref].reasons):
                expected[reason] = expected.get(reason, 0) + 1
    assert inside["by_reason"] == expected
    assert list(inside["by_reason"]) == sorted(expected)


@then(parsers.parse('the leaf "{ref_id}" carries no debt inside'))
def _leaf(world: dict[str, Any], ref_id: str) -> None:
    assert set(_node(world, ref_id)["debt"]) == {"score", "reasons"}


@then("the page map counts every page the run wrote under its section")
def _page_map(world: dict[str, Any]) -> None:
    pages = world["dashboard"]["pages"]
    site: Path = world["site"]
    written = sorted(
        path.relative_to(site).as_posix() for path in world["written"] if path.suffix == ".md"
    )
    listed = [page for section in pages["sections"] for page in section["pages"]]
    assert sorted(listed) == written
    assert pages["count"] == len(written)
    assert all(section["count"] == len(section["pages"]) for section in pages["sections"])
    # Every section is named in the sidebar's order, an empty one with 0 pages:
    # this project publishes no docs/ tree.
    assert [(section["name"], section["count"]) for section in pages["sections"]] == [
        ("about", 2),
        ("dashboard", 1),
        ("architecture", 2),
        ("nodes", len(world["data"]["nodes"])),
        ("landscape", 2),
        ("docs", 0),
    ]


@then("the page map's node pages are one per node")
def _node_pages(world: dict[str, Any]) -> None:
    (nodes,) = [s for s in world["dashboard"]["pages"]["sections"] if s["name"] == "nodes"]
    assert nodes["count"] == len(world["data"]["nodes"])


@then("the page map names the language of each About page")
def _languages(world: dict[str, Any]) -> None:
    assert world["dashboard"]["pages"]["languages"] == [
        {"language": "en", "page": "index.md"},
        {"language": "ru", "page": "ru/index.md"},
    ]
