"""Guards for the S4 viz DATA layer (``architecture.data.json`` / ``landscape.data.json``).

The dev slice already covers the payload's shape and its byte-stability across a
repeated run. Three properties it does NOT cover are guarded here, because each
one fails in a way that looks green:

- **Order independence.** ``regenerate == regenerate`` passes even if the payload
  is ordered by whatever SQLite happens to return, since both runs read the same
  rows in the same physical order. The real claim — "the same logical graph
  always serializes to the same bytes" — only breaks when the rows arrive in a
  different order, which is what a re-index on another machine produces.

- **Referential closure.** The pop-up is assembled in the browser by looking an
  id up in the payload. An edge endpoint, parent or ``contract_key`` that has no
  entry does not fail the build or the schema — it silently yields a card with
  nothing in it.

- **Dead links inside the data.** The existing dead-link guards scan generated
  *markdown*. Every ``url`` / ``doc_links`` value here is consumed by the graph
  at runtime instead, so a broken one is invisible to that scan — the same
  #116-class regression, one layer down.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

import pytest

from beadloom.application.architecture_view import (
    build_architecture_view_data,
    serialize_architecture_view,
)
from beadloom.application.landscape_view import (
    build_landscape_view_data,
    serialize_landscape_view,
)
from beadloom.application.site import generate_site
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from collections.abc import Iterator


_FIXED_TS = "2026-06-05T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _add_node(
    conn: sqlite3.Connection,
    ref_id: str,
    kind: str,
    source: str | None,
    *,
    layer_tag: str | None = None,
) -> None:
    extra = json.dumps({"tags": [layer_tag]}) if layer_tag else "{}"
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source, extra) VALUES (?, ?, ?, ?, ?)",
        (ref_id, kind, f"{ref_id} summary.", source, extra),
    )


def _add_edge(conn: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind) VALUES (?, ?, ?)",
        (src, dst, kind),
    )


def _add_doc(conn: sqlite3.Connection, path: str, kind: str, ref_id: str) -> None:
    conn.execute(
        "INSERT INTO docs (path, kind, ref_id, hash) VALUES (?, ?, ?, 'h')",
        (path, kind, ref_id),
    )


def _add_contract_edge(
    conn: sqlite3.Connection,
    *,
    src: str,
    dst: str,
    kind: str,
    contract_key: str,
    contract: dict[str, object],
) -> None:
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key, extra, lifecycle) "
        "VALUES (?, ?, ?, ?, ?, 'active')",
        (src, dst, kind, contract_key, json.dumps({"contract": contract})),
    )


# The architecture corpus as data, so the SAME logical graph can be inserted in
# two different physical orders.
_ARCH_NODES: tuple[tuple[str, str, str | None, str | None], ...] = (
    ("beadloom", "service", None, "layer-service"),
    ("application", "domain", "src/beadloom/application/", "layer-application"),
    ("graph", "domain", "src/beadloom/graph/", "layer-domain"),
    ("infrastructure", "domain", "src/beadloom/infrastructure/", "layer-infra"),
    ("site-generation", "feature", "src/beadloom/application/site.py", None),
)

_ARCH_EDGES: tuple[tuple[str, str, str], ...] = (
    ("application", "beadloom", "part_of"),
    ("graph", "beadloom", "part_of"),
    ("infrastructure", "beadloom", "part_of"),
    ("site-generation", "application", "part_of"),
    ("application", "graph", "depends_on"),
    ("graph", "infrastructure", "depends_on"),
)

_ARCH_DOCS: tuple[tuple[str, str, str], ...] = (
    ("domains/application/README.md", "domain", "application"),
    ("domains/graph/SPEC.md", "domain", "graph"),
)

_ARCH_PAGES: dict[str, str] = {
    "beadloom": "/services/beadloom",
    "application": "/domains/application",
    "graph": "/domains/graph",
    "infrastructure": "/domains/infrastructure",
    "site-generation": "/features/site-generation",
}


def _seed_arch(conn: sqlite3.Connection, *, reverse: bool = False) -> None:
    """Insert the architecture corpus, optionally in reverse physical order."""
    nodes = tuple(reversed(_ARCH_NODES)) if reverse else _ARCH_NODES
    edges = tuple(reversed(_ARCH_EDGES)) if reverse else _ARCH_EDGES
    docs = tuple(reversed(_ARCH_DOCS)) if reverse else _ARCH_DOCS
    for ref_id, kind, source, layer in nodes:
        _add_node(conn, ref_id, kind, source, layer_tag=layer)
    for src, dst, kind in edges:
        _add_edge(conn, src, dst, kind)
    for path, kind, ref_id in docs:
        _add_doc(conn, path, kind, ref_id)
    conn.commit()


_AMQP_PRODUCER = {
    "protocol": "amqp",
    "direction": "produces",
    "message_type": "OrderPlaced",
    "exchange": "orders",
    "routing_key": "order.placed",
    "body": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "total": {"type": "number"}},
        "required": ["order_id"],
    },
}
_AMQP_CONSUMER = {
    "protocol": "amqp",
    "direction": "consumes",
    "message_type": "OrderPlaced",
    "exchange": "orders",
    "routing_key": "order.placed",
    "body": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
        "required": ["order_id"],
    },
}
_GQL_PRODUCER = {
    "protocol": "graphql",
    "direction": "produces",
    "schema": "Catalog",
    "exposed": ["name", "stock"],
    "fields": [
        {"name": "name", "type": "String!", "args": []},
        {"name": "stock", "type": "Int", "args": []},
    ],
}
_GQL_CONSUMER = {
    "protocol": "graphql",
    "direction": "consumes",
    "schema": "Catalog",
    "references": ["price"],
    "fields": [{"name": "price", "type": "Float", "args": []}],
}

_LANDSCAPE_CONTRACTS: tuple[tuple[str, str, str, str, dict[str, object]], ...] = (
    (
        "catalog-service",
        "storefront-web",
        "produces",
        "amqp:orders/order.placed:OrderPlaced",
        _AMQP_PRODUCER,
    ),
    (
        "storefront-web",
        "catalog-service",
        "consumes",
        "amqp:orders/order.placed:OrderPlaced",
        _AMQP_CONSUMER,
    ),
    ("catalog-service", "storefront-web", "produces", "graphql:Catalog", _GQL_PRODUCER),
    ("storefront-web", "catalog-service", "consumes", "graphql:Catalog", _GQL_CONSUMER),
)


def _seed_landscape(conn: sqlite3.Connection, *, reverse: bool = False) -> None:
    """Insert the anonymized dogfood corpus, optionally in reverse order."""
    services = ["catalog-service", "storefront-web"]
    contracts = (
        tuple(reversed(_LANDSCAPE_CONTRACTS)) if reverse else _LANDSCAPE_CONTRACTS
    )
    for ref_id in reversed(services) if reverse else services:
        _add_node(conn, ref_id, "service", f"src/{ref_id}")
    for src, dst, kind, key, contract in contracts:
        _add_contract_edge(
            conn, src=src, dst=dst, kind=kind, contract_key=key, contract=contract
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Order independence
# ---------------------------------------------------------------------------


def _raw_node_order(conn: sqlite3.Connection) -> list[str]:
    """Physical scan order of ``nodes`` — what an un-ordered query would return."""
    return [row["ref_id"] for row in conn.execute("SELECT * FROM nodes")]


def test_architecture_data_is_independent_of_row_insertion_order() -> None:
    """The same logical graph serializes identically whatever order rows arrive in.

    ``regenerate == regenerate`` cannot catch a missing ``ORDER BY``: both runs
    read the same physical rows. A re-index on another machine does not.
    """
    forward = _open()
    reverse = _open()
    try:
        _seed_arch(forward)
        _seed_arch(reverse, reverse=True)
        # Guard the guard: if both fixtures ever scanned in the same order the
        # assertion below would hold for the wrong reason.
        assert _raw_node_order(forward) != _raw_node_order(reverse)

        first = serialize_architecture_view(
            build_architecture_view_data(forward, pages=_ARCH_PAGES)
        )
        second = serialize_architecture_view(
            build_architecture_view_data(reverse, pages=_ARCH_PAGES)
        )
    finally:
        forward.close()
        reverse.close()

    assert first == second


def test_landscape_data_is_independent_of_row_insertion_order() -> None:
    """Contract reconciliation is order-free — including the contracts section."""
    forward = _open()
    reverse = _open()
    try:
        _seed_landscape(forward)
        _seed_landscape(reverse, reverse=True)
        assert _raw_node_order(forward) != _raw_node_order(reverse)

        first = serialize_landscape_view(build_landscape_view_data(conn=forward, pages={}))
        second = serialize_landscape_view(build_landscape_view_data(conn=reverse, pages={}))
    finally:
        forward.close()
        reverse.close()

    assert first == second


# ---------------------------------------------------------------------------
# Referential closure (the pop-up looks ids up in the payload)
# ---------------------------------------------------------------------------


def _arch_data() -> dict[str, Any]:
    conn = _open()
    try:
        _seed_arch(conn)
        return build_architecture_view_data(conn, pages=_ARCH_PAGES)
    finally:
        conn.close()


def _landscape_data() -> dict[str, Any]:
    conn = _open()
    try:
        _seed_landscape(conn)
        return build_landscape_view_data(conn=conn, pages={})
    finally:
        conn.close()


def test_architecture_edge_endpoints_all_exist_as_nodes() -> None:
    """An edge to an absent id renders an arrow into nothing, with no error."""
    data = _arch_data()
    ids = {n["id"] for n in data["nodes"]}

    dangling = [
        (e["src"], e["dst"], e["kind"])
        for e in data["edges"]
        if e["src"] not in ids or e["dst"] not in ids
    ]

    assert dangling == []


def test_architecture_node_parents_all_exist_as_nodes() -> None:
    """A parent id ELK cannot resolve breaks the compound layout silently."""
    data = _arch_data()
    ids = {n["id"] for n in data["nodes"]}

    orphaned = [n["id"] for n in data["nodes"] if n["parent"] and n["parent"] not in ids]

    assert orphaned == []


def test_architecture_dependency_lists_reference_known_nodes() -> None:
    """``depends_on`` / ``depended_on_by`` feed the pop-up's impact section."""
    data = _arch_data()
    ids = {n["id"] for n in data["nodes"]}

    unknown = sorted(
        {
            ref
            for node in data["nodes"]
            for key in ("depends_on", "depended_on_by")
            for ref in node.get(key, [])
            if ref not in ids
        }
    )

    assert unknown == []


def test_landscape_edge_contract_keys_resolve_to_a_contract() -> None:
    """Clicking an edge opens its contract card by ``contract_key`` lookup."""
    data = _landscape_data()
    known = {c["contract_key"] for c in data["contracts"]}

    unresolved = sorted(
        {e["contract_key"] for e in data["edges"] if e.get("contract_key") not in known}
    )

    assert unresolved == []


def test_landscape_contract_participants_are_known_nodes() -> None:
    """A card naming a producer/consumer absent from the graph cannot be clicked."""
    data = _landscape_data()
    ids = {n["id"] for n in data["nodes"]}

    unknown = sorted(
        {
            participant
            for contract in data["contracts"]
            for key in ("producers", "consumers")
            for participant in contract.get(key, [])
            if participant not in ids
        }
    )

    assert unknown == []


def test_landscape_edge_endpoints_all_exist_as_nodes() -> None:
    data = _landscape_data()
    ids = {n["id"] for n in data["nodes"]}

    dangling = [
        (e["src"], e["dst"]) for e in data["edges"] if e["src"] not in ids or e["dst"] not in ids
    ]

    assert dangling == []


# ---------------------------------------------------------------------------
# Dead links inside the data payloads
# ---------------------------------------------------------------------------


def _iter_data_links(data: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield ``(owner_id, url)`` for every runtime link the payload carries."""
    for node in data.get("nodes", []):
        if node.get("url"):
            yield node["id"], node["url"]
        for link in node.get("doc_links", []):
            yield node["id"], link


def _link_target_exists(site: Path, url: str) -> bool:
    """Resolve a site-absolute viz link against the generated tree.

    The payload carries what the BUILT site serves — a node page as an
    extension-less clean URL (``/domains/graph``) and a published doc as
    ``.html`` (``/docs/.../SPEC.html``) — while the generator writes markdown.
    Both forms therefore map back onto ``.md``.
    """
    raw = url.split("#", 1)[0].split("?", 1)[0]
    if not raw.startswith("/"):
        return False
    target = PurePosixPath(raw.lstrip("/"))
    if target.suffix == ".html":
        target = target.with_suffix(".md")
    candidates = [target, target.with_suffix(".md"), target / "index.md"]
    return any((site / PurePosixPath(*c.parts)).exists() for c in candidates)


def test_architecture_data_links_resolve_to_generated_pages(tmp_path: Path) -> None:
    """Every url/doc_link the arch graph hands the browser is a real page.

    Node-free counterpart of the markdown dead-link guard: these links live in
    JSON the graph dereferences at runtime, so the markdown scan never sees them.
    """
    docs = tmp_path / "docs" / "domains" / "application"
    docs.mkdir(parents=True)
    (docs / "README.md").write_text("# Application\n", encoding="utf-8")
    graph_docs = tmp_path / "docs" / "domains" / "graph"
    graph_docs.mkdir(parents=True)
    (graph_docs / "SPEC.md").write_text("# Graph\n", encoding="utf-8")

    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_arch(conn)
        generate_site(conn, out, project_root=tmp_path, now_ts=_FIXED_TS)
    finally:
        conn.close()

    data = json.loads((out / "public" / "architecture.data.json").read_text("utf-8"))
    dead = [
        (owner, url) for owner, url in _iter_data_links(data) if not _link_target_exists(out, url)
    ]

    assert dead == [], f"dead links in architecture.data.json: {dead}"


def test_landscape_data_links_resolve_to_generated_pages(tmp_path: Path) -> None:
    """Same guard for the landscape payload's node click-through urls."""
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_landscape(conn)
        generate_site(conn, out, project_root=tmp_path, now_ts=_FIXED_TS)
    finally:
        conn.close()

    data = json.loads((out / "public" / "landscape.data.json").read_text("utf-8"))
    dead = [
        (owner, url) for owner, url in _iter_data_links(data) if not _link_target_exists(out, url)
    ]

    assert dead == [], f"dead links in landscape.data.json: {dead}"


@pytest.mark.parametrize("payload", ["architecture.data.json", "landscape.data.json"])
def test_committed_site_viz_data_has_no_dead_links(payload: str) -> None:
    """The real dogfood payload, against the real generated tree.

    Skipped on a checkout where the site has not been generated (``site/`` is
    gitignored), mirroring the markdown guard's contract.
    """
    site = Path(__file__).resolve().parents[1] / "site"
    data_path = site / "public" / payload
    if not (site / "index.md").exists() or not data_path.exists():
        pytest.skip(f"dogfood site/{payload} not generated in this checkout")

    data = json.loads(data_path.read_text("utf-8"))
    dead = [
        (owner, url) for owner, url in _iter_data_links(data) if not _link_target_exists(site, url)
    ]

    assert dead == [], f"dead links in site/public/{payload}: {dead}"


def test_committed_architecture_data_is_referentially_closed() -> None:
    """The real payload's ids all resolve — the pop-up is never empty in the wild.

    The synthetic guards above run on a corpus built to be well-formed. This one
    runs on Beadloom's own graph, where node selection and edge selection are
    separate queries that can drift apart (the builder emits an edge to an id it
    did not include, rather than dropping it).
    """
    site = Path(__file__).resolve().parents[1] / "site"
    data_path = site / "public" / "architecture.data.json"
    if not data_path.exists():
        pytest.skip("dogfood site/public/architecture.data.json not generated")

    data = json.loads(data_path.read_text("utf-8"))
    ids = {n["id"] for n in data["nodes"]}

    dangling = [
        (e["src"], e["dst"], e["kind"])
        for e in data["edges"]
        if e["src"] not in ids or e["dst"] not in ids
    ]
    orphaned = [n["id"] for n in data["nodes"] if n["parent"] and n["parent"] not in ids]
    unknown = sorted(
        {
            ref
            for node in data["nodes"]
            for key in ("depends_on", "depended_on_by")
            for ref in node.get(key, [])
            if ref not in ids
        }
    )

    assert dangling == [], f"edges to ids absent from nodes: {dangling}"
    assert orphaned == [], f"parents absent from nodes: {orphaned}"
    assert unknown == [], f"dependency refs absent from nodes: {unknown}"


def test_committed_landscape_data_is_referentially_closed() -> None:
    """Same closure check for the real landscape payload."""
    site = Path(__file__).resolve().parents[1] / "site"
    data_path = site / "public" / "landscape.data.json"
    if not data_path.exists():
        pytest.skip("dogfood site/public/landscape.data.json not generated")

    data = json.loads(data_path.read_text("utf-8"))
    ids = {n["id"] for n in data["nodes"]}
    known = {c["contract_key"] for c in data["contracts"]}

    dangling = [
        (e["src"], e["dst"]) for e in data["edges"] if e["src"] not in ids or e["dst"] not in ids
    ]
    unresolved = sorted(
        {e["contract_key"] for e in data["edges"] if e.get("contract_key") not in known}
    )
    unknown = sorted(
        {
            participant
            for contract in data["contracts"]
            for key in ("producers", "consumers")
            for participant in contract.get(key, [])
            if participant not in ids
        }
    )

    assert dangling == [], f"edges to ids absent from nodes: {dangling}"
    assert unresolved == [], f"edge contract_keys with no contract: {unresolved}"
    assert unknown == [], f"contract participants absent from nodes: {unknown}"
