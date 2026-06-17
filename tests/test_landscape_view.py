"""Tests for beadloom.application.landscape_view — the interactive G2 landscape.

The interactive Cytoscape+ELK landscape is fed a renderer-agnostic data
artifact (``landscape.data.json``) built from the SAME contract reconciliation
the gate/report uses — never a re-implemented surface. These tests assert the
artifact carries honest nodes/edges/contracts (with the S2 GraphQL typed fields
and the S3 AMQP body), degrades honestly when a field surface is absent
("undeclared", never fabricated), and is byte-stable on regeneration.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from beadloom.application.landscape_view import (
    build_landscape_view_data,
    render_landscape_view_md,
    serialize_landscape_view,
)
from beadloom.application.site import generate_site
from beadloom.infrastructure.db import create_schema

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


def _add_node(conn: sqlite3.Connection, ref_id: str, kind: str, source: str | None) -> None:
    conn.execute(
        "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
        (ref_id, kind, f"{ref_id} summary.", source),
    )


def _add_contract_edge(
    conn: sqlite3.Connection,
    *,
    src: str,
    dst: str,
    kind: str,
    contract_key: str,
    contract: dict[str, object],
    lifecycle: str = "active",
) -> None:
    extra = json.dumps({"contract": contract})
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key, extra, lifecycle) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (src, dst, kind, contract_key, extra, lifecycle),
    )


def _seed_dogfood(conn: sqlite3.Connection) -> None:
    """The anonymized dogfood corpus: catalog-service + storefront-web.

    - An AMQP contract ``OrderPlaced`` (catalog-service produces, storefront-web
      consumes) carrying a JSON-Schema ``body`` on both sides → CONFIRMED.
    - A GraphQL contract ``Catalog`` (catalog-service produces a typed surface,
      storefront-web references a field the producer no longer exposes) →
      BREAKING by the S2 typed analysis (``price`` missing).
    """
    _add_node(conn, "catalog-service", "service", "src/catalog")
    _add_node(conn, "storefront-web", "service", "src/storefront")
    _add_node(conn, "graph", "domain", "src/beadloom/graph")  # structural-only

    amqp_body = {
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "total": {"type": "number"}},
        "required": ["order_id"],
    }
    _add_contract_edge(
        conn,
        src="catalog-service",
        dst="storefront-web",
        kind="produces",
        contract_key="amqp:orders/order.placed:OrderPlaced",
        contract={
            "protocol": "amqp",
            "direction": "produces",
            "message_type": "OrderPlaced",
            "exchange": "orders",
            "routing_key": "order.placed",
            "body": amqp_body,
        },
    )
    _add_contract_edge(
        conn,
        src="storefront-web",
        dst="catalog-service",
        kind="consumes",
        contract_key="amqp:orders/order.placed:OrderPlaced",
        contract={
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
        },
    )

    # GraphQL: producer exposes name+stock (typed); consumer references price
    # (a field the producer does NOT expose) → typed BREAKING.
    producer_fields = [
        {"name": "name", "type": "String!", "args": []},
        {"name": "stock", "type": "Int", "args": []},
    ]
    consumer_fields = [{"name": "price", "type": "Float", "args": []}]
    _add_contract_edge(
        conn,
        src="catalog-service",
        dst="storefront-web",
        kind="produces",
        contract_key="graphql:Catalog",
        contract={
            "protocol": "graphql",
            "direction": "produces",
            "schema": "Catalog",
            "exposed": ["name", "stock"],
            "fields": producer_fields,
        },
    )
    _add_contract_edge(
        conn,
        src="storefront-web",
        dst="catalog-service",
        kind="consumes",
        contract_key="graphql:Catalog",
        contract={
            "protocol": "graphql",
            "direction": "consumes",
            "schema": "Catalog",
            "references": ["price"],
            "fields": consumer_fields,
        },
    )


def _build(conn: sqlite3.Connection) -> dict[str, object]:
    return build_landscape_view_data(conn=conn, pages={})


# ---------------------------------------------------------------------------
# Shape + content
# ---------------------------------------------------------------------------


def test_has_schema_version_and_sections() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    assert isinstance(data["schema_version"], int)
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert isinstance(data["contracts"], list)


def test_nodes_are_contract_participants_only() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {"catalog-service", "storefront-web"}
    assert "graph" not in node_ids  # structural-only node excluded


def test_nodes_carry_health_and_group() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    cat = by_id["catalog-service"]
    assert cat["kind"] == "service"
    # The BREAKING GraphQL contract poisons both endpoints red.
    assert cat["health"] == "broken"
    assert "group" in cat
    assert "label" in cat


def test_contracts_carry_amqp_body() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    amqp = next(
        c for c in data["contracts"] if c["protocol"] == "amqp"
    )
    assert amqp["verdict"] == "confirmed"
    assert amqp["routing"]["exchange"] == "orders"
    assert amqp["routing"]["routing_key"] == "order.placed"
    assert amqp["routing"]["message_type"] == "OrderPlaced"
    # The producer body JSON-Schema is surfaced (S3, G1b).
    body = amqp["body"]["exposed"]
    assert body["properties"]["order_id"]["type"] == "string"
    # Honest producer↔consumer endpoints.
    assert amqp["producers"] == ["catalog-service"]
    assert amqp["consumers"] == ["storefront-web"]


def test_contracts_carry_graphql_typed_fields() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    gql = next(c for c in data["contracts"] if c["protocol"] == "graphql")
    assert gql["verdict"] == "breaking"
    # S2 typed surface: producer exposes name+stock, consumer references price.
    exposed = gql["fields"]["exposed"]
    assert exposed["name"]["type"] == "String!"
    referenced = gql["fields"]["referenced"]
    assert referenced["price"]["type"] == "Float"
    # The breaking field is named honestly.
    assert "price" in gql["missing"]


def test_honest_degradation_no_fields_when_absent() -> None:
    """A name-level AMQP contract (no body) surfaces no fabricated field data."""
    conn = _open()
    try:
        _add_node(conn, "svc-a", "service", "src/a")
        _add_node(conn, "svc-b", "service", "src/b")
        _add_contract_edge(
            conn,
            src="svc-a",
            dst="svc-b",
            kind="produces",
            contract_key="amqp:*/*:Ping",
            contract={"protocol": "amqp", "direction": "produces", "message_type": "Ping"},
        )
        _add_contract_edge(
            conn,
            src="svc-b",
            dst="svc-a",
            kind="consumes",
            contract_key="amqp:*/*:Ping",
            contract={"protocol": "amqp", "direction": "consumes", "message_type": "Ping"},
        )
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    amqp = next(c for c in data["contracts"] if c["protocol"] == "amqp")
    # No body declared → empty body sides (the view renders "undeclared"),
    # never a fabricated field.
    assert amqp["body"]["exposed"] == {}
    assert amqp["body"]["referenced"] == {}
    assert amqp["verdict"] == "confirmed"


def test_edges_carry_verdict_and_contract_ref() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    keys = {e["contract_key"] for e in data["edges"]}
    assert "graphql:Catalog" in keys
    assert "amqp:orders/order.placed:OrderPlaced" in keys
    verdicts = {e["verdict"] for e in data["edges"]}
    assert "breaking" in verdicts


def test_node_click_url_only_when_page_exists() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = build_landscape_view_data(
            conn=conn, pages={"catalog-service": "/services/catalog-service"}
        )
    finally:
        conn.close()
    by_id = {n["id"]: n for n in data["nodes"]}
    assert by_id["catalog-service"]["url"] == "/services/catalog-service"
    # storefront-web has no page → honest empty url (no dead link).
    assert by_id["storefront-web"]["url"] == ""


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_nodes_edges_contracts_sorted() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    node_ids = [n["id"] for n in data["nodes"]]
    assert node_ids == sorted(node_ids)
    edge_keys = [(e["src"], e["dst"], e["contract_key"]) for e in data["edges"]]
    assert edge_keys == sorted(edge_keys)
    contract_keys = [c["contract_key"] for c in data["contracts"]]
    assert contract_keys == sorted(contract_keys)


def test_render_md_mounts_component_and_is_deterministic() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        data = _build(conn)
    finally:
        conn.close()
    first = render_landscape_view_md(data)
    second = render_landscape_view_md(data)
    assert first == second
    assert "<ClientOnly>" in first
    assert "<LandscapeMap" in first
    # A static honest fallback (counts) survives when JS is disabled.
    assert "2" in first  # 2 contracts in the dogfood corpus
    # Links to the secondary Mermaid diagram (fallback / no dead link).
    assert "/landscape-diagram" in first


def test_serialize_is_byte_stable() -> None:
    conn = _open()
    try:
        _seed_dogfood(conn)
        conn.commit()
        first = serialize_landscape_view(_build(conn))
        second = serialize_landscape_view(_build(conn))
    finally:
        conn.close()
    assert first == second
    assert first.endswith("\n")
    # Valid, sorted JSON.
    assert json.loads(first)["schema_version"] == json.loads(second)["schema_version"]


# ---------------------------------------------------------------------------
# Generator wiring (the artifact lands under public/ for the VitePress build)
# ---------------------------------------------------------------------------


def test_generator_emits_data_under_public(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_dogfood(conn)
        conn.commit()
        result = generate_site(conn, out, project_root=tmp_path)
    finally:
        conn.close()
    data_path = out / "public" / "landscape.data.json"
    assert data_path.exists()
    assert data_path in result.written
    # The primary interactive page + the Mermaid fallback both exist (no dead link).
    assert (out / "landscape.md").exists()
    assert (out / "landscape-diagram.md").exists()


def test_generator_data_byte_identical_on_regenerate(tmp_path: Path) -> None:
    conn = _open()
    out = tmp_path / "site"
    try:
        _seed_dogfood(conn)
        conn.commit()
        generate_site(conn, out, project_root=tmp_path, now_ts="2026-06-05T00:00:00+00:00")
        first = (out / "public" / "landscape.data.json").read_bytes()
        first_md = (out / "landscape.md").read_bytes()
        generate_site(conn, out, project_root=tmp_path, now_ts="2026-06-05T00:00:00+00:00")
        second = (out / "public" / "landscape.data.json").read_bytes()
        second_md = (out / "landscape.md").read_bytes()
    finally:
        conn.close()
    assert first == second
    assert first_md == second_md
