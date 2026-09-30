"""Each contract in the landscape data file names what decided its verdict (beadloom-ujzb.6).

The landscape's impact mode marks a service at risk when it takes part in a
contract nothing verified. Whether a verdict compared the two sides' declared
surface is known only to the reconciliation: a GraphQL contract checked by
name keeps its names out of the data file, so the viewer cannot tell it from
one nobody checked. The generator therefore states it, per contract, as
``verdict_basis``:

- ``surface``: the verdict compared what the consumer reads with what the
  producer declares (an AMQP body on both sides, GraphQL fields on both sides,
  or the GraphQL names a consumer references);
- ``presence``: the verdict says only which sides exist;
- ``lifecycle``: a declared intent (planned, deprecated, dead, external)
  decided the verdict, and nothing was compared.

The key is additive: the schema version stays 1 and every existing key stays.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from beadloom.application.site.landscape_view import (
    LANDSCAPE_SCHEMA_VERSION,
    build_landscape_view_data,
)
from beadloom.infrastructure.db import create_schema

_BODY = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
_FIELDS = [{"name": "name", "type": "String!", "args": []}]


def _open() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    for ref_id in ("producer-svc", "consumer-svc"):
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source) VALUES (?, ?, ?, ?)",
            (ref_id, "service", f"{ref_id}.", None),
        )
    return conn


def _edge(
    conn: sqlite3.Connection,
    *,
    src: str,
    dst: str,
    kind: str,
    contract: dict[str, object] | None,
    contract_key: str = "",
    lifecycle: str = "active",
) -> None:
    extra = json.dumps({"contract": contract}) if contract is not None else ""
    conn.execute(
        "INSERT INTO edges (src_ref_id, dst_ref_id, kind, contract_key, extra, lifecycle) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (src, dst, kind, contract_key, extra, lifecycle),
    )


def _amqp(direction: str, *, body: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "protocol": "amqp",
        "direction": direction,
        "message_type": "Placed",
        "exchange": "orders",
        "routing_key": "placed",
    }
    if body:
        payload["body"] = _BODY
    return payload


def _graphql(direction: str, **surface: object) -> dict[str, object]:
    return {"protocol": "graphql", "direction": direction, "schema": "Catalog", **surface}


def _both_sides(
    conn: sqlite3.Connection,
    producer: dict[str, object],
    consumer: dict[str, object],
    *,
    lifecycle: str = "active",
) -> None:
    _edge(
        conn,
        src="producer-svc",
        dst="consumer-svc",
        kind="produces",
        contract=producer,
        lifecycle=lifecycle,
    )
    _edge(
        conn,
        src="consumer-svc",
        dst="producer-svc",
        kind="consumes",
        contract=consumer,
        lifecycle=lifecycle,
    )


def _only_contract(conn: sqlite3.Connection) -> dict[str, object]:
    contracts = build_landscape_view_data(conn)["contracts"]
    assert isinstance(contracts, list)
    assert len(contracts) == 1
    contract = contracts[0]
    assert isinstance(contract, dict)
    return contract


def test_an_amqp_body_on_both_sides_is_a_verdict_from_the_surface() -> None:
    conn = _open()
    _both_sides(conn, _amqp("produces", body=True), _amqp("consumes", body=True))

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("confirmed", "surface")


def test_an_amqp_contract_with_no_body_is_confirmed_by_presence_only() -> None:
    conn = _open()
    _both_sides(conn, _amqp("produces", body=False), _amqp("consumes", body=False))

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("confirmed", "presence")


def test_an_amqp_body_on_one_side_only_compares_nothing() -> None:
    conn = _open()
    _both_sides(conn, _amqp("produces", body=True), _amqp("consumes", body=False))

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("confirmed", "presence")


def test_graphql_fields_on_both_sides_decide_a_breaking_verdict_from_the_surface() -> None:
    conn = _open()
    _both_sides(
        conn,
        _graphql("produces", fields=_FIELDS),
        _graphql("consumes", fields=[{"name": "price", "type": "Float", "args": []}]),
    )

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("breaking", "surface")


def test_graphql_names_a_consumer_references_are_a_comparison_of_the_surface() -> None:
    # No typed fields: the reconciler compares the referenced names with the
    # exposed ones, and that comparison is not in the data file.
    conn = _open()
    _both_sides(
        conn,
        _graphql("produces", exposed=["name"]),
        _graphql("consumes", references=["name"]),
    )

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("confirmed", "surface")
    assert contract["fields"] == {"exposed": {}, "referenced": {}}


def test_graphql_with_no_reference_is_confirmed_by_presence_only() -> None:
    conn = _open()
    _both_sides(conn, _graphql("produces", exposed=["name"]), _graphql("consumes"))

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("confirmed", "presence")


@pytest.mark.parametrize(
    ("lifecycle", "verdict"),
    [("planned", "expected"), ("deprecated", "expected"), ("dead", "dead")],
)
def test_a_declared_intent_decides_the_verdict_and_compares_nothing(
    lifecycle: str, verdict: str
) -> None:
    conn = _open()
    _both_sides(
        conn,
        _amqp("produces", body=True),
        _amqp("consumes", body=True),
        lifecycle=lifecycle,
    )

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == (verdict, "lifecycle")


def test_a_consumer_with_no_producer_is_orphaned_by_presence() -> None:
    conn = _open()
    _edge(
        conn,
        src="consumer-svc",
        dst="producer-svc",
        kind="consumes",
        contract=_amqp("consumes", body=True),
    )

    contract = _only_contract(conn)

    assert (contract["verdict"], contract["verdict_basis"]) == ("orphaned_consumer", "presence")


def test_a_plain_dependency_is_confirmed_by_presence_only() -> None:
    # A contract in a protocol the reconciler reads no surface for: the edges
    # carry only a contract key, as this repository's own `site-data` does.
    conn = _open()
    for src, dst, kind in (
        ("producer-svc", "consumer-svc", "produces"),
        ("consumer-svc", "producer-svc", "consumes"),
    ):
        _edge(conn, src=src, dst=dst, kind=kind, contract=None, contract_key="data:bundle")

    contract = _only_contract(conn)

    assert (contract["protocol"], contract["verdict"]) == ("", "confirmed")
    assert contract["verdict_basis"] == "presence"


def test_the_key_is_added_without_a_new_schema_version_or_a_lost_key() -> None:
    conn = _open()
    _both_sides(conn, _amqp("produces", body=True), _amqp("consumes", body=True))

    data = build_landscape_view_data(conn)
    contract = _only_contract(conn)

    assert data["schema_version"] == LANDSCAPE_SCHEMA_VERSION == 1
    assert set(contract) == {
        "body",
        "consumers",
        "contract_key",
        "fields",
        "lifecycle",
        "missing",
        "name",
        "producers",
        "protocol",
        "routing",
        "verdict",
        "verdict_basis",
    }
