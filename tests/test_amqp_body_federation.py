"""Determinism + dogfood of the federated AMQP ``contract.body`` wire (S3, G1b).

The strict AMQP body only earns trust if a hub re-running ``federate`` (or
ingesting the same satellites in a different order, with body properties emitted
in a different order) produces a BYTE-IDENTICAL federated artifact. This file
proves the canonicalization (sorted properties/required, recursively) survives
end-to-end through ``aggregate_exports`` + ``serialize_federation``, AND dogfoods
a seeded body-field break vs a benign additive field on the real 4-AMQP corpus.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.federation import aggregate_exports, serialize_federation

if TYPE_CHECKING:
    from collections.abc import Mapping

_T0 = "2026-06-01T00:00:00+00:00"


def _node(ref_id: str, *, kind: str = "feature") -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": kind,
        "summary": ref_id,
        "lifecycle": "active",
        "source": None,
    }


def _edge(repo: str, *, direction: str, body: Mapping[str, object]) -> dict[str, object]:
    return {
        "src": repo,
        "dst": "q-start-plan-version-upload",
        "kind": "uses",
        "lifecycle": "active",
        "contract": {
            "protocol": "amqp",
            "message_type": "start_plan_version_upload",
            "direction": direction,
            "body": body,
        },
    }


def _export(repo: str, *, edges: list) -> dict[str, object]:
    return {
        "schema_version": 2,
        "repo": repo,
        "commit_sha": "abc1234",
        "exported_at": _T0,
        "generator": "beadloom test",
        "nodes": [_node(repo, kind="service"), _node("q-start-plan-version-upload")],
        "edges": edges,
    }


def _scrambled_body() -> dict[str, object]:
    """A body whose properties + required are declared in a non-sorted order."""
    return {
        "type": "object",
        "properties": {
            "plan_version_id": {"type": "string"},
            "account_id": {"type": "string"},
            "metadata": {
                "type": "object",
                "properties": {"size": {"type": "number"}, "name": {"type": "string"}},
            },
        },
        "required": ["plan_version_id", "account_id"],
    }


def _federate(
    producer_body: Mapping[str, object], consumer_body: Mapping[str, object]
) -> object:
    producer = _export(
        "core-monolith",
        edges=[_edge("core-monolith", direction="produces", body=producer_body)],
    )
    consumer = _export(
        "integration-service",
        edges=[_edge("integration-service", direction="consumes", body=consumer_body)],
    )
    return aggregate_exports([producer, consumer], now=_T0)


def _amqp_contract(fed: object) -> dict[str, object]:
    contracts = [c for c in fed.contracts if c["protocol"] == "amqp"]  # type: ignore[attr-defined]
    assert len(contracts) == 1
    return contracts[0]


class TestAmqpBodyFederationDeterminism:
    def test_body_order_independent_byte_stable(self) -> None:
        # Same body, scrambled property order on both runs -> byte-identical wire.
        run_one = serialize_federation(_federate(_scrambled_body(), _scrambled_body()))
        # Re-emit with a different property declaration order.
        alt = {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "size": {"type": "number"}},
                },
                "plan_version_id": {"type": "string"},
            },
            "required": ["account_id", "plan_version_id"],
        }
        run_two = serialize_federation(_federate(alt, alt))
        assert json.dumps(run_one, sort_keys=True) == json.dumps(run_two, sort_keys=True)

    def test_per_edge_body_is_sorted_on_wire(self) -> None:
        fed = _federate(_scrambled_body(), _scrambled_body())
        edges = [
            e for e in fed.edges  # type: ignore[attr-defined]
            if isinstance(e.get("contract"), dict)
            and e["contract"].get("body")
        ]
        assert edges
        for edge in edges:
            body = edge["contract"]["body"]
            assert list(body["properties"].keys()) == sorted(body["properties"].keys())
            assert body["required"] == sorted(body["required"])


class TestAmqpBodyDogfood:
    """Seeded body break caught by name; additive field benign — on the corpus."""

    def test_seeded_body_field_break_is_caught(self) -> None:
        # Producer dropped `account_id` the consumer reads -> BREAKING naming it.
        producer = {
            "type": "object",
            "properties": {"plan_version_id": {"type": "string"}},
            "required": ["plan_version_id"],
        }
        consumer = _scrambled_body()
        contract = _amqp_contract(_federate(producer, consumer))
        assert contract["verdict"] == "breaking"
        assert "account_id" in contract["missing"]  # type: ignore[operator]

    def test_additive_producer_field_is_benign(self) -> None:
        producer = {
            "type": "object",
            "properties": {
                "plan_version_id": {"type": "string"},
                "account_id": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {"size": {"type": "number"}, "name": {"type": "string"}},
                },
                "new_optional_field": {"type": "string"},
            },
            "required": ["plan_version_id", "account_id"],
        }
        contract = _amqp_contract(_federate(producer, _scrambled_body()))
        assert contract["verdict"] == "confirmed"
        assert contract.get("missing") == []
