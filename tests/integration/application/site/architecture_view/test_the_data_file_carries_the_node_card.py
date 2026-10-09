"""The architecture data file, schema version 2: what the node card and the impact mode read.

BDL-076 A1 (`beadloom-o2ua`). The viewer is static, so everything the card shows
is computed by `beadloom docs site` into `architecture.data.json`. Version 2 adds
the card's fields and keeps every key of version 1, because the viewer core that
lands beside this change (A2) still reads only version-1 keys.

The key sets are pinned here in full. A key added or dropped without this file
changing is a contract change nobody reviewed.
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from beadloom import __version__
from beadloom.application.debt_report import NodeDebt
from beadloom.application.site.architecture_card import (
    PUBLIC_SYMBOL_CAP,
    NodeFinding,
    NodeVerdicts,
)
from beadloom.application.site.architecture_view import (
    ARCHITECTURE_SCHEMA_VERSION,
    build_architecture_view_data,
    render_architecture_view_md,
)
from beadloom.application.site.generate import generate_site
from beadloom.application.site.node_pages import node_page_urls, render_all_pages
from beadloom.application.site.repository_link import RepositoryLink
from tests.support.in_memory_graph import add_edge, add_node, open_graph

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Iterator
    from pathlib import Path

#: Every top-level key of schema version 1.
V1_TOP_KEYS = {"schema_version", "scope", "nodes", "edges"}

#: The top-level keys schema version 2 adds. Nothing derived from the git remote
#: is among them: A1 added `project` and A3 `repository`, no screen read either,
#: and a remote can carry a credential (BDL-076 re-review finding m3). What the
#: card needs from the remote reaches it as each node's finished `source_url`.
V2_TOP_KEYS = {
    "generated_at",
    "beadloom_version",
    "layers",
    "layer_order",
    # BDL-080 S1b (`beadloom-kgh6`): every layer rule, beside the first rule's
    # `layers` / `layer_order`, which keep their meaning.
    "layer_rules",
}

#: Every node key of schema version 1, with `lint_clean` present because lint ran.
V1_NODE_KEYS = {
    "id",
    "label",
    "kind",
    "summary",
    "layer",
    "layer_rank",
    "group",
    "symbols",
    "doc_status",
    "doc_links",
    "url",
    "parent",
    "depends_on",
    "depended_on_by",
    "uses",
    "used_by",
    "lint_clean",
}

#: The node keys schema version 2 adds, with `findings` and `debt` present
#: because both were computed. `source_url` joined in R1's fix (`beadloom-ujzb.7`):
#: the finished link to the node's source, decided per forge by the generator.
V2_NODE_KEYS = {
    "source",
    "source_url",
    "lifecycle",
    "tags",
    "docs",
    "tests",
    "public_symbols",
    "activity",
    "debt",
    "findings",
    # BDL-080 S1b (`beadloom-kgh6`): the rule that places the node among every
    # layer rule, and its rank there; `layer` / `layer_rank` stay the first's.
    "layer_rule",
    "layer_rule_rank",
}

#: What a node's ``tests`` carries: the files bound to the node itself, and the
#: counts over the node and its ``part_of`` descendants. A file is listed once,
#: at the node that holds it; an ancestor counts it without repeating the path.
TESTS_KEYS = {"files", "file_count", "count", "placement"}

#: The activity keys a node may carry: the ones the node card shows. The reindex
#: records more — among them the names of a node's most frequent committers —
#: and the data file is published, so a key reaches it only by being listed here
#: (BDL-076 R1 finding M2).
ACTIVITY_KEYS = {"commits_30d", "lines_30d", "level"}

#: What a declared layer carries at the top level.
LAYER_KEYS = {"name", "rank", "tag", "token"}

#: A layering this repository does not declare.
_FOREIGN_LAYERS = (("web", "tier-web"), ("core", "tier-core"), ("store", "tier-store"))


def _declare(conn: sqlite3.Connection, layers: tuple[tuple[str, str], ...]) -> None:
    conn.execute(
        "INSERT INTO rules (name, description, rule_type, rule_json, enabled) "
        "VALUES ('tier-order', 'web over core over store', 'layers', ?, 1)",
        (
            json.dumps(
                {
                    "layers": [{"name": name, "tag": tag} for name, tag in layers],
                    "enforce": "top-down",
                    "edge_kind": "depends_on",
                }
            ),
        ),
    )


def _set_source(conn: sqlite3.Connection, ref_id: str, source: str) -> None:
    conn.execute("UPDATE nodes SET source = ? WHERE ref_id = ?", (source, ref_id))


def _set_extra(conn: sqlite3.Connection, ref_id: str, extra: dict[str, object]) -> None:
    conn.execute("UPDATE nodes SET extra = ? WHERE ref_id = ?", (json.dumps(extra), ref_id))


def _pair(conn: sqlite3.Connection, ref_id: str, doc: str, code: str, status: str) -> None:
    conn.execute(
        "INSERT INTO sync_state (doc_path, code_path, ref_id, code_hash_at_sync, "
        "doc_hash_at_sync, synced_at, status) VALUES (?, ?, ?, 'c', 'd', 't', ?)",
        (doc, code, ref_id, status),
    )


def _doc(conn: sqlite3.Connection, path: str, ref_id: str) -> None:
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, 'domain', ?, 'h')", (path, ref_id)
    )


def _symbol(conn: sqlite3.Connection, file_path: str, name: str, line: int) -> None:
    conn.execute(
        "INSERT INTO code_symbols (file_path, symbol_name, kind, line_start, line_end, "
        "file_hash) VALUES (?, ?, 'function', ?, ?, 'h')",
        (file_path, name, line, line),
    )


def _test_file(conn: sqlite3.Connection, path: str, ref_id: str | None, placement: str) -> None:
    conn.execute(
        "INSERT INTO test_files (path, kind, ref_id, placement, test_count, file_hash) "
        "VALUES (?, 'unit', ?, ?, 1, 'h')",
        (path, ref_id, placement),
    )


@pytest.fixture()
def graph() -> Iterator[sqlite3.Connection]:
    """An empty index in memory, closed when the test ends."""
    conn = open_graph()
    yield conn
    conn.close()


@pytest.fixture()
def shop(graph: sqlite3.Connection) -> sqlite3.Connection:
    """A small graph with one node of each shape the card has to show."""
    conn = graph
    add_node(conn, "shop", "service")
    add_node(conn, "orders", "domain", "tier-core")
    add_node(conn, "pricing", "component")
    add_node(conn, "storefront", "site")
    add_edge(conn, "orders", "shop", "part_of")
    add_edge(conn, "pricing", "orders", "part_of")
    add_edge(conn, "storefront", "shop", "part_of")
    add_edge(conn, "pricing", "orders", "depends_on")
    add_edge(conn, "pricing", "orders", "touches_code")
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key) VALUES "
        "('shop', 'storefront', 'produces', 'site-data:bundle'), "
        "('storefront', 'shop', 'consumes', 'site-data:bundle')"
    )
    _set_source(conn, "orders", "src/orders/")
    _set_source(conn, "pricing", "src/orders/pricing.py")
    conn.execute("UPDATE nodes SET lifecycle = 'deprecated' WHERE ref_id = 'pricing'")
    _declare(conn, _FOREIGN_LAYERS)
    conn.commit()
    return conn


def _verdicts() -> NodeVerdicts:
    return NodeVerdicts(
        findings={
            "pricing": [
                NodeFinding(rule="tier-order", severity="error", message="pricing reaches up"),
                NodeFinding(rule="docs-present", severity="warn", message="pricing has no doc"),
            ]
        },
        debt={"pricing": NodeDebt(ref_id="pricing", score=6.0, reasons=["undocumented"])},
    )


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - fixed git arguments written by this test
        ["git", *args],  # noqa: S607 - the test drives the git on PATH, as the generator does
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _nodes(data: dict[str, object]) -> dict[str, dict[str, object]]:
    nodes = data["nodes"]
    assert isinstance(nodes, list)
    return {str(node["id"]): node for node in nodes}


# ---------------------------------------------------------------------------
# The schema, pinned
# ---------------------------------------------------------------------------


def test_the_schema_version_is_2() -> None:
    assert ARCHITECTURE_SCHEMA_VERSION == 2


def test_the_top_level_keys_are_version_1_plus_the_version_2_additions(
    shop: sqlite3.Connection,
) -> None:
    data = build_architecture_view_data(shop, verdicts=_verdicts(), generated_at="t")

    assert set(data) == V1_TOP_KEYS | V2_TOP_KEYS
    assert data["schema_version"] == 2
    assert data["scope"] == "architecture"


def test_every_node_carries_the_version_1_keys_and_the_card(shop: sqlite3.Connection) -> None:
    data = build_architecture_view_data(shop, verdicts=_verdicts())

    for node in _nodes(data).values():
        assert set(node) == V1_NODE_KEYS | V2_NODE_KEYS, node["id"]


def test_what_was_not_computed_is_omitted_rather_than_reported_clean(
    shop: sqlite3.Connection,
) -> None:
    node = _nodes(build_architecture_view_data(shop))["pricing"]

    assert set(node) == (V1_NODE_KEYS | V2_NODE_KEYS) - {"lint_clean", "findings", "debt"}


def test_edges_keep_their_version_1_keys(shop: sqlite3.Connection) -> None:
    edges = build_architecture_view_data(shop)["edges"]
    assert isinstance(edges, list)

    by_kind = {str(edge["kind"]): edge for edge in edges}
    assert set(by_kind["part_of"]) == {"src", "dst", "kind"}
    assert set(by_kind["depends_on"]) == {"src", "dst", "kind", "violation"}


# ---------------------------------------------------------------------------
# Top level: provenance and the declared layers
# ---------------------------------------------------------------------------


def test_the_provenance_is_what_the_caller_states(shop: sqlite3.Connection) -> None:
    data = build_architecture_view_data(shop, generated_at="2026-09-30T00:00:00+00:00")

    assert data["generated_at"] == "2026-09-30T00:00:00+00:00"
    assert data["beadloom_version"] == __version__


def test_a_repository_the_card_cannot_link_to_leaves_no_trace_in_the_file(
    shop: sqlite3.Connection,
) -> None:
    """The remote reaches the file only as a finished source link (re-review m3).

    A host no forge is recognised for gets no link, so nothing of it is published:
    for a private self-hosted repository, the host and the path are internal.
    """
    repository = RepositoryLink(url="https://git.corp.example/team/shop", ref="abc123")

    text = json.dumps(build_architecture_view_data(shop, repository=repository))

    assert "git.corp.example" not in text
    assert "abc123" not in text


def test_the_layers_are_the_declaration_in_its_order(shop: sqlite3.Connection) -> None:
    data = build_architecture_view_data(shop)

    assert data["layers"] == [
        {"name": "web", "rank": 0, "tag": "tier-web", "token": "tier-web"},
        {"name": "core", "rank": 1, "tag": "tier-core", "token": "tier-core"},
        {"name": "store", "rank": 2, "tag": "tier-store", "token": "tier-store"},
    ]
    assert data["layer_order"] == "top-down"
    layers = data["layers"]
    assert isinstance(layers, list)
    assert all(set(layer) == LAYER_KEYS for layer in layers)


def test_a_layer_token_is_the_one_a_node_carries(graph: sqlite3.Connection) -> None:
    conn = graph
    add_node(conn, "api", "domain", "layer-api")
    _declare(conn, (("api", "layer-api"),))
    conn.commit()
    data = build_architecture_view_data(conn)

    layers = data["layers"]
    assert isinstance(layers, list)
    token = layers[0]["token"]
    assert token == "api"  # noqa: S105 - a layer token, not a credential
    assert _nodes(data)["api"]["layer"] == token


def test_a_project_that_declares_no_layers_gets_none(graph: sqlite3.Connection) -> None:
    conn = graph
    add_node(conn, "shop", "service", "layer-service")
    conn.commit()
    data = build_architecture_view_data(conn)

    assert data["layers"] == []
    assert data["layer_order"] == ""


# ---------------------------------------------------------------------------
# Edges: the contract kinds join, the file kind stays out
# ---------------------------------------------------------------------------


def test_consumes_and_produces_edges_carry_their_contract(shop: sqlite3.Connection) -> None:
    edges = build_architecture_view_data(shop)["edges"]
    assert isinstance(edges, list)

    contract = [e for e in edges if e["kind"] in {"consumes", "produces"}]
    assert contract == [
        {"src": "shop", "dst": "storefront", "kind": "produces", "contract": "site-data:bundle"},
        {"src": "storefront", "dst": "shop", "kind": "consumes", "contract": "site-data:bundle"},
    ]


def test_touches_code_stays_out_because_it_points_at_files(shop: sqlite3.Connection) -> None:
    edges = build_architecture_view_data(shop)["edges"]
    assert isinstance(edges, list)

    assert all(edge["kind"] != "touches_code" for edge in edges)


# ---------------------------------------------------------------------------
# The node card
# ---------------------------------------------------------------------------


def test_the_card_carries_source_lifecycle_and_tags(shop: sqlite3.Connection) -> None:
    nodes = _nodes(build_architecture_view_data(shop))

    assert nodes["pricing"]["source"] == "src/orders/pricing.py"
    assert nodes["pricing"]["lifecycle"] == "deprecated"
    assert nodes["orders"]["tags"] == ["tier-core"]
    assert nodes["shop"]["source"] == ""
    assert nodes["shop"]["tags"] == []


def test_each_doc_carries_the_worst_status_of_its_pairs(shop: sqlite3.Connection) -> None:
    conn = shop
    _doc(conn, "domains/orders/README.md", "orders")
    _doc(conn, "domains/orders/SPEC.md", "orders")
    _doc(conn, "domains/orders/NOTES.md", "orders")
    _pair(conn, "orders", "domains/orders/README.md", "src/orders/a.py", "ok")
    _pair(conn, "orders", "domains/orders/SPEC.md", "src/orders/a.py", "ok")
    _pair(conn, "orders", "domains/orders/SPEC.md", "src/orders/b.py", "stale")
    conn.commit()
    node = _nodes(build_architecture_view_data(conn))["orders"]

    assert node["docs"] == [
        {"path": "domains/orders/NOTES.md", "status": "unpaired"},
        {"path": "domains/orders/README.md", "status": "ok"},
        {"path": "domains/orders/SPEC.md", "status": "stale"},
    ]
    assert node["doc_status"] == "stale"


def test_public_symbols_are_capped_and_the_rest_counted(shop: sqlite3.Connection) -> None:
    conn = shop
    overflow = 7
    for index in range(PUBLIC_SYMBOL_CAP + overflow):
        _symbol(conn, "src/orders/a.py", f"name_{index:03d}", index + 1)
    _symbol(conn, "src/orders/a.py", "_private", 999)
    conn.commit()
    node = _nodes(build_architecture_view_data(conn))["orders"]

    public = node["public_symbols"]
    assert isinstance(public, dict)
    assert public["names"] == [f"name_{index:03d}" for index in range(PUBLIC_SYMBOL_CAP)]
    assert public["omitted"] == overflow
    # The version-1 count is kept as it was: every owned symbol, private included.
    assert node["symbols"] == PUBLIC_SYMBOL_CAP + overflow + 1


@pytest.mark.parametrize(
    ("public", "listed", "omitted"),
    [(49, 49, 0), (50, 50, 0), (51, 50, 1)],
    ids=["below-the-cap", "at-the-cap", "one-over"],
)
def test_the_card_lists_at_most_fifty_public_names_and_counts_the_rest(
    shop: sqlite3.Connection, public: int, listed: int, omitted: int
) -> None:
    # The RFC's figure, written out: a test that read the constant would pass
    # whatever the constant became.
    conn = shop
    for index in range(public):
        _symbol(conn, "src/orders/a.py", f"name_{index:03d}", index + 1)
    conn.commit()

    node = _nodes(build_architecture_view_data(conn))["orders"]

    public_symbols = node["public_symbols"]
    assert isinstance(public_symbols, dict)
    assert (len(public_symbols["names"]), public_symbols["omitted"]) == (listed, omitted)


def _bind_orders_and_pricing(conn: sqlite3.Connection) -> None:
    """`orders` holds one file itself; its part `pricing` holds the other.

    The reindex writes each node's ``extra["tests"]`` as the union over the node
    and its ``part_of`` descendants, so `orders` names both files.
    """
    _test_file(conn, "tests/unit/orders/test_a.py", "orders", "mirror")
    _test_file(conn, "tests/unit/orders/pricing/test_b.py", "pricing", "mirror")
    _set_extra(
        conn,
        "orders",
        {
            "tags": ["tier-core"],
            "tests": {
                "framework": "pytest",
                "test_files": [
                    "tests/unit/orders/test_a.py",
                    "tests/unit/orders/pricing/test_b.py",
                ],
                "test_count": 5,
            },
        },
    )
    _set_extra(
        conn,
        "pricing",
        {
            "tests": {
                "framework": "pytest",
                "test_files": ["tests/unit/orders/pricing/test_b.py"],
                "test_count": 3,
            },
        },
    )
    conn.commit()


def test_the_tests_object_carries_its_own_files_and_the_union_counts(
    shop: sqlite3.Connection,
) -> None:
    _bind_orders_and_pricing(shop)
    nodes = _nodes(build_architecture_view_data(shop))

    for ref in ("orders", "pricing"):
        tests = nodes[ref]["tests"]
        assert isinstance(tests, dict)
        assert set(tests) == TESTS_KEYS, ref


def test_a_test_file_is_listed_at_its_own_node_and_counted_at_its_ancestors(
    shop: sqlite3.Connection,
) -> None:
    _bind_orders_and_pricing(shop)
    nodes = _nodes(build_architecture_view_data(shop))

    # `orders` lists only the file bound to it, and still counts its part's file:
    # the counts are what the card showed before, the list is not repeated.
    assert nodes["orders"]["tests"] == {
        "files": ["tests/unit/orders/test_a.py"],
        "file_count": 2,
        "count": 5,
        "placement": {"mirror": 2},
    }
    assert nodes["pricing"]["tests"] == {
        "files": ["tests/unit/orders/pricing/test_b.py"],
        "file_count": 1,
        "count": 3,
        "placement": {"mirror": 1},
    }
    # A node the binding does not cover says so, rather than claiming no tests.
    assert nodes["shop"]["tests"] is None


def test_each_test_file_is_listed_at_exactly_one_node(shop: sqlite3.Connection) -> None:
    _bind_orders_and_pricing(shop)
    nodes = _nodes(build_architecture_view_data(shop))

    listed = [
        path
        for node in nodes.values()
        if isinstance(node["tests"], dict)
        for path in node["tests"]["files"]
    ]
    assert sorted(listed) == [
        "tests/unit/orders/pricing/test_b.py",
        "tests/unit/orders/test_a.py",
    ]


def test_a_file_whose_owner_is_not_a_node_stays_listed_where_it_is_counted(
    shop: sqlite3.Connection,
) -> None:
    conn = shop
    # One file has no record at all, one names a node the graph does not hold:
    # neither has another node to be listed at, so dropping it would lose it.
    _test_file(conn, "tests/unit/orders/test_gone.py", "retired-node", "mirror")
    _set_extra(
        conn,
        "orders",
        {
            "tests": {
                "test_files": ["tests/unit/orders/test_gone.py", "tests/unit/orders/test_x.py"],
                "test_count": 2,
            },
        },
    )
    conn.commit()
    tests = _nodes(build_architecture_view_data(conn))["orders"]["tests"]

    assert isinstance(tests, dict)
    assert tests["files"] == ["tests/unit/orders/test_gone.py", "tests/unit/orders/test_x.py"]
    assert tests["file_count"] == 2
    assert tests["placement"] == {"mirror": 1}


def test_the_activity_is_the_one_the_reindex_recorded(shop: sqlite3.Connection) -> None:
    conn = shop
    activity = {"level": "hot", "commits_30d": 12}
    _set_extra(conn, "orders", {"tags": ["tier-core"], "activity": activity})
    conn.commit()
    nodes = _nodes(build_architecture_view_data(conn))

    assert nodes["orders"]["activity"] == activity
    assert nodes["shop"]["activity"] is None


def test_the_activity_carries_only_what_the_card_shows(shop: sqlite3.Connection) -> None:
    conn = shop
    recorded = {
        "level": "warm",
        "lines_30d": 41,
        "lines_90d": 120,
        "commits_30d": 3,
        "commits_90d": 9,
        "last_commit": "2026-09-29",
        "top_contributors": ["Ada Quillfeather", "Grace Tallow"],
        "a_key_nobody_reviewed": "value",
    }
    _set_extra(conn, "orders", {"tags": ["tier-core"], "activity": recorded})
    conn.commit()
    data = build_architecture_view_data(conn)

    # BDL-078 F-activity: the card says "N lines changed in 30 days", so lines_30d
    # is published; lines_90d is not shown and stays in the index.
    assert _nodes(data)["orders"]["activity"] == {
        "level": "warm",
        "lines_30d": 41,
        "commits_30d": 3,
    }
    for node in _nodes(data).values():
        activity = node["activity"]
        assert activity is None or set(activity) <= ACTIVITY_KEYS, node["id"]
    assert "Ada Quillfeather" not in json.dumps(data)


def test_a_source_links_to_the_page_its_forge_serves(shop: sqlite3.Connection) -> None:
    data = build_architecture_view_data(
        shop, repository=RepositoryLink(url="https://bitbucket.org/team/shop", ref="abc123")
    )
    nodes = _nodes(data)

    assert nodes["pricing"]["source_url"] == (
        "https://bitbucket.org/team/shop/src/abc123/src/orders/pricing.py"
    )
    # A node with no source has nothing to link.
    assert nodes["shop"]["source_url"] == ""


def test_a_forge_the_generator_does_not_recognise_gets_no_source_link(
    shop: sqlite3.Connection,
) -> None:
    data = build_architecture_view_data(
        shop, repository=RepositoryLink(url="https://git.example/team/shop", ref="abc123")
    )

    assert all(node["source_url"] == "" for node in _nodes(data).values())


def test_findings_name_the_rule_the_severity_and_the_message(shop: sqlite3.Connection) -> None:
    nodes = _nodes(build_architecture_view_data(shop, verdicts=_verdicts()))

    assert nodes["pricing"]["findings"] == [
        {"rule": "docs-present", "severity": "warn", "message": "pricing has no doc"},
        {"rule": "tier-order", "severity": "error", "message": "pricing reaches up"},
    ]
    assert nodes["pricing"]["lint_clean"] is False
    assert nodes["orders"]["findings"] == []
    assert nodes["orders"]["lint_clean"] is True


def test_debt_is_the_debt_report_for_the_node(shop: sqlite3.Connection) -> None:
    nodes = _nodes(build_architecture_view_data(shop, verdicts=_verdicts()))

    assert nodes["pricing"]["debt"] == {"score": 6.0, "reasons": ["undocumented"]}
    assert nodes["orders"]["debt"] == {"score": 0.0, "reasons": []}


# ---------------------------------------------------------------------------
# A url for every kind, where the page is written
# ---------------------------------------------------------------------------


def test_every_node_gets_the_url_of_the_page_that_is_written_for_it(
    shop: sqlite3.Connection,
) -> None:
    conn = shop
    urls = node_page_urls(conn)
    written = {page.rel_path for page in render_all_pages(conn)}

    assert urls["pricing"] == "/other/pricing"
    assert urls["storefront"] == "/other/storefront"
    assert urls["orders"] == "/domains/orders"
    assert {f"{url.lstrip('/')}.md" for url in urls.values()} == written


# ---------------------------------------------------------------------------
# The page text names the declared layers
# ---------------------------------------------------------------------------


def test_the_page_names_the_declared_layers(shop: sqlite3.Connection) -> None:
    page = render_architecture_view_md(build_architecture_view_data(shop))

    assert "web → core → store" in page
    assert "infra" not in page


def test_the_page_describes_what_the_viewer_draws_and_does(shop: sqlite3.Connection) -> None:
    # BDL-076 R1 finding n4: the intro still described the first viewer — one
    # edge kind as solid arrows, and a click that highlights a blast radius.
    page = render_architecture_view_md(build_architecture_view_data(shop))

    for kind in ("depends_on", "uses", "consumes", "produces"):
        assert f"`{kind}`" in page, kind
    assert "neighbourhood" in page
    assert "**Impact**" in page
    assert "solid arrows" not in page
    assert "blast radius" not in page


def test_the_page_says_so_when_no_layers_are_declared(graph: sqlite3.Connection) -> None:
    conn = graph
    add_node(conn, "shop", "service")
    conn.commit()
    page = render_architecture_view_md(build_architecture_view_data(conn))

    assert "declares no layers" in page
    assert "→" not in page


# ---------------------------------------------------------------------------
# The generator writes version 2
# ---------------------------------------------------------------------------


@pytest.fixture()
def generated(shop: sqlite3.Connection, tmp_path: Path) -> dict[str, object]:
    out = tmp_path / "site"
    project = tmp_path / "shop"
    project.mkdir()
    generate_site(shop, out, project_root=project, now_ts="2026-09-30T00:00:00+00:00")
    loaded = json.loads((out / "public" / "architecture.data.json").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_generator_stamps_the_file_with_its_run(generated: dict[str, object]) -> None:
    assert generated["schema_version"] == 2
    assert generated["generated_at"] == "2026-09-30T00:00:00+00:00"
    assert generated["beadloom_version"] == __version__


def test_the_generator_links_no_source_for_a_project_outside_git(
    generated: dict[str, object],
) -> None:
    assert all(node["source_url"] == "" for node in _nodes(generated).values())


def test_the_generator_links_sources_through_the_projects_own_remote(
    shop: sqlite3.Connection, tmp_path: Path
) -> None:
    project = tmp_path / "shop"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "remote", "add", "origin", "git@github.com:team/shop.git")
    identity = ("-c", "user.name=t", "-c", "user.email=t@example")
    _git(project, *identity, "commit", "-q", "--allow-empty", "-m", "first")
    head = _git(project, "rev-parse", "HEAD")
    out = tmp_path / "site"

    generate_site(shop, out, project_root=project, now_ts="2026-09-30T00:00:00+00:00")

    loaded = json.loads((out / "public" / "architecture.data.json").read_text("utf-8"))
    assert _nodes(loaded)["pricing"]["source_url"] == (
        f"https://github.com/team/shop/tree/{head}/src/orders/pricing.py"
    )


def test_the_generator_links_a_component_to_its_page(generated: dict[str, object]) -> None:
    assert _nodes(generated)["pricing"]["url"] == "/other/pricing"
