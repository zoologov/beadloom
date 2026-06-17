"""Determinism of the federated GraphQL ``contract.fields`` wire (BDL-060 S2).

The typed Tier-A surface only earns trust if a hub re-running ``federate`` (or
ingesting the same satellites in a different order, with fields/args emitted in a
different traversal order) produces a BYTE-IDENTICAL federated artifact. This is
the federation determinism invariant the epic CONTEXT marks NON-NEGOTIABLE:
every emitted payload (here the per-edge ``contract.fields`` block) is
sorted/deduped + golden-tested.

``graph.federation.reconcile._normalize_typed_fields`` is the canonicalizer; this
file proves the canonicalization survives end-to-end through
``aggregate_exports`` + ``serialize_federation``, regardless of satellite order
or in-payload ordering — and that a v1 (no typed ``fields``) export still
federates byte-stably (honest absence, no fabricated block).
"""

from __future__ import annotations

from beadloom.graph.federation import aggregate_exports, serialize_federation

_T0 = "2026-06-01T00:00:00+00:00"
_NOW = "2026-06-02T00:00:00+00:00"


def _node(ref_id: str, *, kind: str = "schema") -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": kind,
        "summary": ref_id,
        "lifecycle": "active",
        "source": None,
    }


def _edge(
    src: str, dst: str, *, kind: str, contract: dict[str, object]
) -> dict[str, object]:
    return {
        "src": src,
        "dst": dst,
        "kind": kind,
        "lifecycle": "active",
        "contract": contract,
    }


def _export(repo: str, *, nodes: list, edges: list, version: int = 2) -> dict[str, object]:
    return {
        "schema_version": version,
        "repo": repo,
        "commit_sha": "abc1234",
        "exported_at": _T0,
        "generator": "beadloom test",
        "nodes": nodes,
        "edges": edges,
    }


# A producer typed ``fields`` block emitted in SCRAMBLED field + arg order — the
# canonicalizer must sort fields by name and args by name on the wire.
def _scrambled_producer_fields() -> list[dict[str, object]]:
    return [
        {
            "name": "plans",
            "type": "[Plan!]!",
            "args": [
                {"name": "limit", "type": "Int"},
                {"name": "after", "type": "String"},
            ],
        },
        {"name": "account", "type": "Account!", "args": []},
        {
            "name": "plan",
            "type": "Plan",
            "args": [
                {"name": "id", "type": "ID!"},
                {"name": "filter", "type": "PlanFilter"},
            ],
        },
        # Duplicate field entry (later wins, deduped) — identical surface, must
        # not appear twice and must not change the canonical output.
        {
            "name": "plan",
            "type": "Plan",
            "args": [
                {"name": "id", "type": "ID!"},
                {"name": "filter", "type": "PlanFilter"},
            ],
        },
    ]


def _producer_export(repo: str, fields: list[dict[str, object]]) -> dict[str, object]:
    contract = {
        "protocol": "graphql",
        "schema": "WebAPI",
        "direction": "produces",
        "exposed": ["account", "plan", "plans"],
        "fields": fields,
    }
    return _export(
        repo,
        nodes=[_node("api")],
        edges=[_edge("api", "api", kind="produces", contract=contract)],
    )


def _consumer_export(repo: str) -> dict[str, object]:
    contract = {
        "protocol": "graphql",
        "schema": "WebAPI",
        "direction": "consumes",
        "references": ["plan", "plans"],
        "fields": [
            {"name": "plan", "type": "Plan", "args": [{"name": "id", "type": "ID!"}]},
            {"name": "plans", "type": "[Plan!]!", "args": []},
        ],
    }
    return _export(
        repo,
        nodes=[_node("client", kind="page")],
        edges=[_edge("client", "client", kind="consumes", contract=contract)],
    )


def _graphql_edge(fed: object) -> dict[str, object]:
    """The single GraphQL producer edge from a federated graph."""
    edges = [
        e
        for e in fed.edges  # type: ignore[attr-defined]
        if isinstance(e.get("contract"), dict)
        and e["contract"].get("direction") == "produces"
    ]
    assert len(edges) == 1
    return edges[0]


class TestFederatedFieldsCanonicalization:
    """The per-edge ``contract.fields`` block is sorted + deduped on the wire."""

    def test_fields_sorted_by_name(self) -> None:
        exports = [
            _producer_export("backend", _scrambled_producer_fields()),
            _consumer_export("ui"),
        ]
        fed = aggregate_exports(exports, now=_NOW)
        fields = _graphql_edge(fed)["contract"]["fields"]
        names = [f["name"] for f in fields]
        assert names == sorted(names)
        assert names == ["account", "plan", "plans"]

    def test_args_sorted_by_name(self) -> None:
        exports = [
            _producer_export("backend", _scrambled_producer_fields()),
            _consumer_export("ui"),
        ]
        fed = aggregate_exports(exports, now=_NOW)
        fields = {f["name"]: f for f in _graphql_edge(fed)["contract"]["fields"]}
        plan_args = [a["name"] for a in fields["plan"]["args"]]
        plans_args = [a["name"] for a in fields["plans"]["args"]]
        assert plan_args == sorted(plan_args)
        assert plans_args == sorted(plans_args) == ["after", "limit"]

    def test_duplicate_field_entry_deduped(self) -> None:
        exports = [
            _producer_export("backend", _scrambled_producer_fields()),
            _consumer_export("ui"),
        ]
        fed = aggregate_exports(exports, now=_NOW)
        names = [f["name"] for f in _graphql_edge(fed)["contract"]["fields"]]
        assert names.count("plan") == 1

    def test_duplicate_field_dedup_is_last_wins(self) -> None:
        # Two entries for the SAME field name: the canonicalizer keeps the LAST
        # (a deterministic merge rule), so the surface is never doubled.
        fields = [
            {"name": "plan", "type": "Plan", "args": []},
            {"name": "plan", "type": "Plan!", "args": [{"name": "id", "type": "ID!"}]},
        ]
        exports = [_producer_export("backend", fields), _consumer_export("ui")]
        fed = aggregate_exports(exports, now=_NOW)
        plan_entries = [
            f for f in _graphql_edge(fed)["contract"]["fields"] if f["name"] == "plan"
        ]
        assert len(plan_entries) == 1
        assert plan_entries[0]["type"] == "Plan!"  # the LAST entry won

    def test_field_type_wrapping_preserved_on_wire(self) -> None:
        exports = [
            _producer_export("backend", _scrambled_producer_fields()),
            _consumer_export("ui"),
        ]
        fed = aggregate_exports(exports, now=_NOW)
        fields = {f["name"]: f for f in _graphql_edge(fed)["contract"]["fields"]}
        assert fields["plans"]["type"] == "[Plan!]!"
        assert fields["account"]["type"] == "Account!"


class TestFederatedArtifactByteStability:
    """``serialize_federation`` is byte-identical across runs + reordering."""

    def test_byte_identical_across_repeated_runs(self) -> None:
        exports = [
            _producer_export("backend", _scrambled_producer_fields()),
            _consumer_export("ui"),
        ]
        a = serialize_federation(aggregate_exports(exports, now=_NOW))
        b = serialize_federation(aggregate_exports(exports, now=_NOW))
        assert a == b

    def test_byte_identical_when_satellites_reordered(self) -> None:
        producer = _producer_export("backend", _scrambled_producer_fields())
        consumer = _consumer_export("ui")
        forward = serialize_federation(
            aggregate_exports([producer, consumer], now=_NOW)
        )
        reversed_ = serialize_federation(
            aggregate_exports([consumer, producer], now=_NOW)
        )
        assert forward == reversed_

    def test_byte_identical_when_producer_field_order_scrambled(self) -> None:
        # Same logical surface, different in-payload field/arg ordering -> the
        # canonicalizer makes both serialize byte-identically.
        ordered = [
            {"name": "account", "type": "Account!", "args": []},
            {
                "name": "plan",
                "type": "Plan",
                "args": [
                    {"name": "filter", "type": "PlanFilter"},
                    {"name": "id", "type": "ID!"},
                ],
            },
            {
                "name": "plans",
                "type": "[Plan!]!",
                "args": [
                    {"name": "after", "type": "String"},
                    {"name": "limit", "type": "Int"},
                ],
            },
        ]
        scrambled = serialize_federation(
            aggregate_exports(
                [
                    _producer_export("backend", _scrambled_producer_fields()),
                    _consumer_export("ui"),
                ],
                now=_NOW,
            )
        )
        canonical = serialize_federation(
            aggregate_exports(
                [_producer_export("backend", ordered), _consumer_export("ui")],
                now=_NOW,
            )
        )
        assert scrambled == canonical


class TestHonestAbsenceOfTypedFields:
    """A v1 / name-level export without a ``fields`` block federates byte-stably."""

    def test_name_level_only_export_has_no_fabricated_fields(self) -> None:
        producer = _export(
            "backend",
            nodes=[_node("api")],
            edges=[
                _edge(
                    "api",
                    "api",
                    kind="produces",
                    contract={
                        "protocol": "graphql",
                        "schema": "WebAPI",
                        "direction": "produces",
                        "exposed": ["plan"],
                    },
                )
            ],
            version=2,
        )
        consumer = _consumer_export("ui")
        consumer_edge_contract = consumer["edges"][0]["contract"]  # type: ignore[index]
        # Strip the typed block from the consumer too -> a pure name-level run.
        del consumer_edge_contract["fields"]  # type: ignore[union-attr]
        fed = aggregate_exports([producer, consumer], now=_NOW)
        produces_edge = _graphql_edge(fed)
        # No fabricated typed ``fields`` key when the satellite emitted none.
        assert "fields" not in produces_edge["contract"]

    def test_name_level_run_byte_stable(self) -> None:
        producer = _export(
            "backend",
            nodes=[_node("api")],
            edges=[
                _edge(
                    "api",
                    "api",
                    kind="produces",
                    contract={
                        "protocol": "graphql",
                        "schema": "WebAPI",
                        "direction": "produces",
                        "exposed": ["zeta", "alpha", "mid"],
                    },
                )
            ],
        )
        consumer = _export(
            "ui",
            nodes=[_node("client", kind="page")],
            edges=[
                _edge(
                    "client",
                    "client",
                    kind="consumes",
                    contract={
                        "protocol": "graphql",
                        "schema": "WebAPI",
                        "direction": "consumes",
                        "references": ["mid", "alpha"],
                    },
                )
            ],
        )
        a = serialize_federation(aggregate_exports([producer, consumer], now=_NOW))
        b = serialize_federation(aggregate_exports([consumer, producer], now=_NOW))
        assert a == b
        # The name-level ``exposed`` list is sorted on the wire (determinism).
        produces_edge = _graphql_edge(aggregate_exports([producer, consumer], now=_NOW))
        assert produces_edge["contract"]["exposed"] == ["alpha", "mid", "zeta"]
