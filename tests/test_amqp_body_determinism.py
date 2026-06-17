"""AMQP body determinism + additive-schema tolerance + 4-corpus dogfood (S3 .10).

Strengthens :mod:`tests.test_amqp_body_federation` on the axes the brief calls
out explicitly:

- **Satellite reordering** — federating the same satellites in a different ORDER
  (not just a different property order) yields a byte-identical artifact.
- **Additive schema** — an older reader (and ``parse_body``) tolerates a contract
  edge carrying NO ``body`` (the F1 name-level shape) without crash or fabrication.
- **4-AMQP-corpus dogfood** — the four real ``core-monolith`` <-> ``integration-
  service`` message types reconcile both-sides WITH bodies, and a body break
  seeded on ONE named contract is caught by name while the other three stay
  confirmed (no collateral false-BREAK).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.amqp_body import parse_body, serialize_body
from beadloom.graph.federation import aggregate_exports, serialize_federation

if TYPE_CHECKING:
    from collections.abc import Mapping

_T0 = "2026-06-01T00:00:00+00:00"

# (message_type, core direction, integration direction) — the real corpus.
_CONTRACT = [
    ("start_plan_version_upload", "produces", "consumes"),
    ("ensure_plans_folder_path", "produces", "consumes"),
    ("plan_version_upload_completed", "consumes", "produces"),
    ("ensure_plans_folder_path_completed", "consumes", "produces"),
]


def _channel(message_type: str) -> str:
    return "q-" + message_type.replace("_", "-")


def _body() -> dict[str, object]:
    """A shared both-sides body for every corpus message (sorted-stable)."""
    return {
        "type": "object",
        "properties": {
            "plan_version_id": {"type": "string"},
            "account_id": {"type": "string"},
            "status": {"type": "string", "enum": ["pending", "done"]},
        },
        "required": ["plan_version_id"],
    }


def _node(ref_id: str, kind: str) -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": kind,
        "summary": ref_id,
        "lifecycle": "active",
        "source": None,
    }


def _edge(
    repo: str, message_type: str, direction: str, body: Mapping[str, object] | None
) -> dict[str, object]:
    contract: dict[str, object] = {
        "protocol": "amqp",
        "message_type": message_type,
        "direction": direction,
    }
    if body is not None:
        contract["body"] = body
    return {
        "src": repo,
        "dst": _channel(message_type),
        "kind": "uses",
        "lifecycle": "active",
        "contract": contract,
    }


def _satellite(
    repo: str,
    role_index: int,
    *,
    body_override: Mapping[str, object] | None = None,
    override_message: str | None = None,
) -> dict[str, object]:
    edges: list[dict[str, object]] = []
    for message_type, *dirs in _CONTRACT:
        body = _body()
        if override_message == message_type and body_override is not None:
            body = dict(body_override)
        edges.append(_edge(repo, message_type, dirs[role_index], body))
    nodes = [_node(repo, "service")]
    nodes += [_node(_channel(mt), "feature") for mt, *_ in _CONTRACT]
    return {
        "schema_version": 2,
        "repo": repo,
        "commit_sha": "deadbeef",
        "exported_at": _T0,
        "generator": "beadloom dogfood",
        "nodes": nodes,
        "edges": edges,
    }


def _corpus(
    *,
    body_override: Mapping[str, object] | None = None,
    override_message: str | None = None,
) -> object:
    core = _satellite("core-monolith", 0)
    integ = _satellite(
        "integration-service",
        1,
        body_override=body_override,
        override_message=override_message,
    )
    return aggregate_exports([core, integ], now=_T0)


def _contracts_by_message(fed: object) -> dict[str, dict[str, object]]:
    return {
        c["message_type"]: c
        for c in fed.contracts  # type: ignore[attr-defined]
        if c["protocol"] == "amqp"
    }


class TestSatelliteReorderingDeterminism:
    def test_satellite_order_does_not_change_artifact(self) -> None:
        core = _satellite("core-monolith", 0)
        integ = _satellite("integration-service", 1)
        forward = serialize_federation(aggregate_exports([core, integ], now=_T0))
        reverse = serialize_federation(aggregate_exports([integ, core], now=_T0))
        assert forward == reverse

    def test_artifact_is_byte_stable_across_repeated_runs(self) -> None:
        run_one = serialize_federation(_corpus())
        run_two = serialize_federation(_corpus())
        assert run_one == run_two

    def test_every_wire_body_is_sorted(self) -> None:
        fed = _corpus()
        bodied = 0
        for edge in fed.edges:  # type: ignore[attr-defined]
            contract = edge.get("contract")
            if not isinstance(contract, dict):
                continue
            body = contract.get("body")
            if not isinstance(body, dict) or not body:
                continue
            bodied += 1
            props = body["properties"]
            assert list(props.keys()) == sorted(props.keys())
            assert body["required"] == sorted(body["required"])
        assert bodied == len(_CONTRACT) * 2  # one edge per side per message


class TestAdditiveSchemaTolerance:
    def test_edge_without_body_reconciles_name_level(self) -> None:
        # F1-shaped corpus (no `body`) must still confirm all four both-sides.
        core = _satellite("core-monolith", 0)
        integ = _satellite("integration-service", 1)
        for sat in (core, integ):
            for edge in sat["edges"]:  # type: ignore[index]
                edge["contract"].pop("body", None)  # type: ignore[index]
        fed = aggregate_exports([core, integ], now=_T0)
        confirmed = {c["message_type"] for c in fed.contracts if c["confirmed"]}  # type: ignore[attr-defined]
        assert confirmed == {mt for mt, *_ in _CONTRACT}

    def test_parse_body_tolerates_missing_body(self) -> None:
        # An older reader handed no body gets an honest empty node, never a crash.
        assert parse_body(None).to_payload() == {
            "type": "",
            "properties": {},
            "required": [],
        }

    def test_serialize_body_is_order_independent(self) -> None:
        one = {
            "type": "object",
            "properties": {"b": {"type": "string"}, "a": {"type": "number"}},
            "required": ["b", "a"],
        }
        two = {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "string"}},
            "required": ["a", "b"],
        }
        assert json.dumps(serialize_body(one), sort_keys=True) == json.dumps(
            serialize_body(two), sort_keys=True
        )


class TestFourCorpusDogfood:
    def test_all_four_confirmed_both_sides_with_bodies(self) -> None:
        contracts = _contracts_by_message(_corpus())
        assert set(contracts) == {mt for mt, *_ in _CONTRACT}
        for message_type, contract in contracts.items():
            assert contract["verdict"] == "confirmed", message_type
            assert contract.get("missing") in (None, []), message_type

    def test_seeded_body_break_caught_by_name_others_unaffected(self) -> None:
        # Seed an INCOMPATIBLE consumer body on exactly one message: the consumer
        # newly reads `region` the producer never emits -> that contract breaks by
        # name; the other three stay confirmed.
        broken = {
            "type": "object",
            "properties": {
                "plan_version_id": {"type": "string"},
                "account_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "done"]},
                "region": {"type": "string"},
            },
            "required": ["plan_version_id"],
        }
        fed = _corpus(
            body_override=broken, override_message="start_plan_version_upload"
        )
        contracts = _contracts_by_message(fed)
        target = contracts["start_plan_version_upload"]
        assert target["verdict"] == "breaking"
        assert "region" in target["missing"]  # type: ignore[operator]
        for message_type, contract in contracts.items():
            if message_type == "start_plan_version_upload":
                continue
            assert contract["verdict"] == "confirmed", message_type

    def test_seeded_enum_narrowing_break_caught_by_name(self) -> None:
        # Consumer expects an extra `status` value the producer can never emit.
        narrowed_consumer = {
            "type": "object",
            "properties": {
                "plan_version_id": {"type": "string"},
                "account_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "done", "cancelled"]},
            },
            "required": ["plan_version_id"],
        }
        fed = _corpus(
            body_override=narrowed_consumer,
            override_message="ensure_plans_folder_path",
        )
        contracts = _contracts_by_message(fed)
        target = contracts["ensure_plans_folder_path"]
        assert target["verdict"] == "breaking"
        assert "status" in target["missing"]  # type: ignore[operator]
