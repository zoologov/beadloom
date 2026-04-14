"""F2 cross-cutting gate (BDL-038 BEAD-09).

This module closes the *cross-cutting* gaps that the per-bead F2 suites
(``test_graph_contracts.py``, ``test_graph_sdl.py``, ``test_export.py``,
``test_federate.py``, ``test_db.py``) leave open by design — each of those
verifies one focused surface, while the F2 acceptance gate needs the whole
hub path exercised together:

1. **Every ``ContractVerdict`` end-to-end through ``aggregate_exports``** — the
   per-bead suites cover most verdicts at the hub, but ``EXTERNAL`` and ``DEAD``
   are only asserted via the unit ``classify``. A contract-bearing edge with an
   ``external`` / ``dead`` lifecycle must surface the matching contract verdict
   on the federated output (not just on a hand-built ``Contract``).
2. **Unknown protocol is skipped in reconciliation** — a contract edge with a
   non-AMQP/non-GraphQL protocol (e.g. ``rest`` — an F3 non-goal) must NOT
   reconcile, leaving F2 honest about what it does and does not understand
   (covers the ``protocol not in _RECONCILED_PROTOCOLS`` skip in all three
   reconcile helpers).
3. **Determinism across FRESH re-aggregation** — the per-bead determinism test
   re-serializes the *same* ``FederatedGraph`` object. The gate needs a stronger
   invariant: two independent ``aggregate_exports`` calls over identical input
   (and two independent ``build_export`` calls) serialize byte-identically,
   including across input-ordering permutations of the satellites.
4. **v1-export AMQP-only parity with F1 semantics** — a schema-version-1 export
   (message_type only, no exchange/routing, no protocol enrichment, no
   landscape) must reconcile with exactly the F1 three verdicts
   (CONFIRMED / UNDECLARED_PRODUCER / ORPHANED_CONSUMER) and the F1 flat keys.

All fixtures are SYNTHETIC export dicts (per the F2 test constraint) with an
injected ``exported_at`` / ``commit_sha`` / ``now`` — never wall-clock.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from beadloom.graph.contracts import (
    Contract,
    ContractEndpoint,
    ContractVerdict,
    classify,
    cross_landscape_keys,
    edge_group_key,
    reconcile_contracts,
)
from beadloom.graph.federation import (
    aggregate_exports,
    build_export,
    serialize_export,
    serialize_federation,
)
from beadloom.infrastructure.db import create_schema, open_db

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_T0 = "2026-06-01T00:00:00+00:00"  # injected reference "now" / exported_at


def _export(
    repo: str,
    *,
    nodes: list[dict[str, object]] | None = None,
    edges: list[dict[str, object]] | None = None,
    commit_sha: str | None = "abc1234",
    exported_at: str = _T0,
    schema_version: int = 1,
    landscape: str | None = None,
) -> dict[str, object]:
    """Build a synthetic satellite export artifact (``landscape`` omitted if None)."""
    export: dict[str, object] = {
        "schema_version": schema_version,
        "repo": repo,
        "commit_sha": commit_sha,
        "exported_at": exported_at,
        "generator": "beadloom test",
        "nodes": nodes or [],
        "edges": edges or [],
    }
    if landscape is not None:
        export["landscape"] = landscape
    return export


def _node(
    ref_id: str, *, kind: str = "service", lifecycle: str = "active"
) -> dict[str, object]:
    return {
        "ref_id": ref_id,
        "kind": kind,
        "summary": ref_id,
        "lifecycle": lifecycle,
        "source": None,
    }


def _edge(
    src: str,
    dst: str,
    *,
    kind: str = "depends_on",
    lifecycle: str = "active",
    contract: Mapping[str, object] | None = None,
) -> dict[str, object]:
    edge: dict[str, object] = {
        "src": src,
        "dst": dst,
        "kind": kind,
        "lifecycle": lifecycle,
    }
    if contract is not None:
        edge["contract"] = dict(contract)
    return edge


class TestAllContractVerdictsEndToEnd:
    """All eight ``ContractVerdict`` cases must be reachable through ``federate``.

    CONFIRMED / DRIFT-shape / ORPHANED_CONSUMER / UNDECLARED_PRODUCER / BREAKING /
    EXPECTED are exercised by ``test_federate.TestContractVerdicts``; this class
    adds the two the hub path never asserts end-to-end: EXTERNAL and DEAD.
    """

    def test_external_lifecycle_contract_is_external_verdict(self) -> None:
        # Arrange: a contract-bearing edge declared external (a native bridge —
        # produces+consumes shape that would otherwise CONFIRM).
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Bridged"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "Bridged"}
        exports = [
            _export(
                "a",
                nodes=[_node("svc"), _node("q", kind="queue")],
                edges=[
                    _edge("svc", "q", kind="produces", lifecycle="external",
                          contract=produces)
                ],
            ),
            _export(
                "b",
                nodes=[_node("w"), _node("q", kind="queue")],
                edges=[_edge("w", "q", kind="consumes", contract=consumes)],
            ),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert: the louder external lifecycle wins -> EXTERNAL, never CONFIRMED.
        contract = next(c for c in fed.contracts if c["message_type"] == "Bridged")
        assert contract["verdict"] == ContractVerdict.EXTERNAL.value

    def test_dead_lifecycle_contract_is_dead_verdict(self) -> None:
        # Arrange: a both-sides contract declared dead.
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Retired"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "Retired"}
        exports = [
            _export(
                "a",
                nodes=[_node("svc"), _node("q", kind="queue")],
                edges=[
                    _edge("svc", "q", kind="produces", lifecycle="dead",
                          contract=produces)
                ],
            ),
            _export(
                "b",
                nodes=[_node("w"), _node("q", kind="queue")],
                edges=[_edge("w", "q", kind="consumes", contract=consumes)],
            ),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert: dead intent dominates the both-sides shape -> DEAD.
        contract = next(c for c in fed.contracts if c["message_type"] == "Retired")
        assert contract["verdict"] == ContractVerdict.DEAD.value

    def test_every_verdict_value_is_producible(self) -> None:
        # Arrange / Act: drive each verdict through the classify table that the
        # hub uses, asserting the full enum is reachable (no dead enum member).
        cases = {
            ContractVerdict.CONFIRMED: Contract(
                "amqp:*/*:M", "amqp", "M",
                endpoints=[
                    ContractEndpoint("a", "a", "produces"),
                    ContractEndpoint("b", "b", "consumes"),
                ],
            ),
            ContractVerdict.ORPHANED_CONSUMER: Contract(
                "amqp:*/*:M", "amqp", "M",
                endpoints=[ContractEndpoint("a", "a", "consumes")],
            ),
            ContractVerdict.UNDECLARED_PRODUCER: Contract(
                "amqp:*/*:M", "amqp", "M",
                endpoints=[ContractEndpoint("a", "a", "produces")],
            ),
            ContractVerdict.BREAKING: Contract(
                "graphql:S", "graphql", "S",
                endpoints=[
                    ContractEndpoint("a", "a", "produces"),
                    ContractEndpoint("b", "b", "consumes"),
                ],
                exposed=["x"], references=["x", "gone"],
            ),
            ContractVerdict.EXPECTED: Contract(
                "amqp:*/*:M", "amqp", "M", lifecycle="planned",
                endpoints=[ContractEndpoint("a", "a", "produces")],
            ),
            ContractVerdict.EXTERNAL: Contract(
                "amqp:*/*:M", "amqp", "M", lifecycle="external",
            ),
            ContractVerdict.DEAD: Contract(
                "amqp:*/*:M", "amqp", "M", lifecycle="dead",
            ),
        }
        # Assert: every mapping holds, and every enum member is covered.
        for expected, contract in cases.items():
            assert classify(contract) is expected
        assert set(cases) | {ContractVerdict.DRIFT} == set(ContractVerdict)


class TestUnknownProtocolHonest:
    """An unrecognized protocol must be skipped, not faked (F3 non-goal honesty)."""

    def _rest_edges(self) -> list[dict[str, object]]:
        rest: dict[str, object] = {
            "protocol": "rest", "direction": "produces", "name": "GET /plans",
        }
        edge: dict[str, object] = {
            "src": "@a:svc",
            "dst": "@a:api",
            "kind": "produces",
            "lifecycle": "active",
            "repo": "a",
            "contract": rest,
        }
        return [edge]

    def test_unknown_protocol_not_reconciled(self) -> None:
        # Arrange: a REST contract edge (rest is not an F2 protocol).
        edges = self._rest_edges()
        # Act.
        contracts = reconcile_contracts(edges)
        # Assert: F2 produces no contract for an unknown protocol.
        assert contracts == []

    def test_unknown_protocol_has_no_group(self) -> None:
        # Arrange.
        edges = self._rest_edges()
        # Act / Assert: the group helper returns None for a non-F2 protocol.
        assert edge_group_key(edges[0], set()) is None

    def test_unknown_protocol_not_a_cross_landscape_key(self) -> None:
        # Arrange: an explicit cross-repo REST edge.
        rest: dict[str, object] = {
            "protocol": "rest", "direction": "produces", "name": "GET /x",
        }
        edge: dict[str, object] = {
            "src": "@a:svc",
            "dst": "@b:api",
            "kind": "produces",
            "lifecycle": "active",
            "repo": "a",
            "contract": rest,
        }
        # Act / Assert: an unknown protocol never seeds a cross-landscape key.
        assert cross_landscape_keys([edge]) == set()

    def test_unknown_protocol_federates_without_error(self) -> None:
        # Arrange: a full federate run where one edge carries a REST contract.
        rest = {"protocol": "rest", "direction": "produces", "name": "GET /plans"}
        exports = [
            _export(
                "a",
                nodes=[_node("svc"), _node("api", kind="endpoint")],
                edges=[_edge("svc", "api", kind="produces", contract=rest)],
            ),
            _export("b", nodes=[_node("w")]),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert: no contract reconciled, but the edge still exists in the union.
        assert fed.contracts == []
        assert any(e["dst"] == "@a:api" for e in fed.edges)


class TestDeterminismAcrossFreshRuns:
    """Byte-identical output across INDEPENDENT runs over identical input."""

    def _mixed_exports(self) -> list[dict[str, object]]:
        amqp_p = {"protocol": "amqp", "direction": "produces", "message_type": "Evt",
                  "exchange": "domain", "routing_key": "evt.created"}
        amqp_c = {"protocol": "amqp", "direction": "consumes", "message_type": "Evt",
                  "exchange": "domain", "routing_key": "evt.created"}
        gql_p = {"protocol": "graphql", "schema": "API", "direction": "produces",
                 "exposed": ["plan", "user"]}
        gql_c = {"protocol": "graphql", "schema": "API", "direction": "consumes",
                 "references": ["user", "plan"]}
        return [
            _export(
                "backend",
                nodes=[_node("svc"), _node("api", kind="schema"), _node("q", kind="queue")],
                edges=[
                    _edge("svc", "q", kind="produces", contract=amqp_p),
                    _edge("api", "api", kind="produces", contract=gql_p),
                ],
            ),
            _export(
                "client",
                nodes=[_node("w"), _node("page", kind="page"), _node("q", kind="queue")],
                edges=[
                    _edge("w", "q", kind="consumes", contract=amqp_c),
                    _edge("page", "page", kind="consumes", contract=gql_c),
                ],
            ),
        ]

    def test_federation_byte_identical_across_two_runs(self) -> None:
        # Arrange.
        exports = self._mixed_exports()
        # Act: two fully independent aggregations.
        first = serialize_federation(aggregate_exports(exports, now=_T0))
        second = serialize_federation(aggregate_exports(exports, now=_T0))
        # Assert.
        assert first == second

    def test_federation_byte_identical_under_satellite_reordering(self) -> None:
        # Arrange: the same two satellites in swapped input order.
        exports = self._mixed_exports()
        # Act.
        forward = serialize_federation(aggregate_exports(exports, now=_T0))
        reversed_ = serialize_federation(
            aggregate_exports(list(reversed(exports)), now=_T0)
        )
        # Assert: sorted output makes satellite input-order irrelevant.
        assert forward == reversed_

    @staticmethod
    def _gql_exports(
        exposed: list[str], references: list[str]
    ) -> list[dict[str, object]]:
        p = {"protocol": "graphql", "schema": "API", "direction": "produces",
             "exposed": exposed}
        c = {"protocol": "graphql", "schema": "API", "direction": "consumes",
             "references": references}
        return [
            _export("backend", nodes=[_node("api", kind="schema")],
                    edges=[_edge("api", "api", kind="produces", contract=p)]),
            _export("client", nodes=[_node("page", kind="page")],
                    edges=[_edge("page", "page", kind="consumes", contract=c)]),
        ]

    def test_graphql_contracts_section_surface_order_independent(self) -> None:
        # Arrange: the same exposed/references sets in different list orders.
        # Act: compare ONLY the reconciled ``contracts`` section, which sorts +
        # dedupes the surface onto the first-class Contract.
        a = aggregate_exports(self._gql_exports(["b", "a", "c"], ["c", "a"]), now=_T0)
        b = aggregate_exports(self._gql_exports(["c", "b", "a"], ["a", "c"]), now=_T0)
        # Assert: the contract-level surface is deterministic regardless of order.
        assert json.dumps(a.contracts, sort_keys=True) == json.dumps(
            b.contracts, sort_keys=True
        )

    def test_graphql_edge_payload_surface_order_independent(self) -> None:
        # BEAD-12: federation._resolve_edge now sorts+dedupes the per-edge
        # contract mirror's exposed/references, so the FULL federated JSON is
        # byte-identical regardless of the satellite's SDL surface ordering
        # (the reconciled contracts[] section was already deterministic).
        # Arrange / Act: the FULL federated JSON over two surface orderings.
        a = serialize_federation(
            aggregate_exports(self._gql_exports(["b", "a", "c"], ["c", "a"]), now=_T0)
        )
        b = serialize_federation(
            aggregate_exports(self._gql_exports(["c", "b", "a"], ["a", "c"]), now=_T0)
        )
        # Assert: edge-payload surface is order-independent.
        assert a == b

    def test_build_export_byte_identical_across_two_runs(self, tmp_path: Path) -> None:
        # Arrange: a populated DB.
        conn = open_db(tmp_path / "g.db")
        create_schema(conn)
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, lifecycle) "
            "VALUES (?, ?, ?, ?, ?)",
            ("z-svc", "service", "Z", None, "active"),
        )
        conn.execute(
            "INSERT INTO nodes (ref_id, kind, summary, source, lifecycle) "
            "VALUES (?, ?, ?, ?, ?)",
            ("a-svc", "service", "A", None, "active"),
        )
        conn.execute(
            "INSERT INTO edges (src_ref_id, dst_ref_id, kind, lifecycle) "
            "VALUES (?, ?, ?, ?)",
            ("a-svc", "z-svc", "depends_on", "active"),
        )
        conn.commit()
        kwargs = {
            "repo": "proj",
            "commit_sha": "deadbeef",
            "exported_at": _T0,
            "generator": "beadloom test",
        }
        # Act: two independent builds.
        first = serialize_export(build_export(conn, **kwargs))
        second = serialize_export(build_export(conn, **kwargs))
        conn.close()
        # Assert.
        assert first == second


class TestV1ExportAmqpOnlyParity:
    """A v1 export (message_type only) reconciles with exactly F1 semantics."""

    def test_v1_amqp_confirmed_keeps_f1_flat_keys(self) -> None:
        # Arrange: v1 AMQP produces+consumes (no exchange/routing/landscape).
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "PlanCreated"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "PlanCreated"}
        exports = [
            _export(
                "core",
                nodes=[_node("orders"), _node("q", kind="queue")],
                edges=[_edge("orders", "q", kind="produces", contract=produces)],
            ),
            _export(
                "integration",
                nodes=[_node("plans"), _node("q", kind="queue")],
                edges=[_edge("plans", "q", kind="consumes", contract=consumes)],
            ),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert: CONFIRMED + the F1 flat key shape is preserved verbatim.
        contract = next(c for c in fed.contracts if c["message_type"] == "PlanCreated")
        assert contract["verdict"] == ContractVerdict.CONFIRMED.value
        assert contract["confirmed"] is True
        assert contract["directions"] == ["consumes", "produces"]
        assert contract["repos"] == ["core", "integration"]
        # Wildcard exchange/routing key keeps v1 back-compat identity.
        assert contract["contract_key"] == "amqp:*/*:PlanCreated"

    def test_v1_amqp_producer_only_is_undeclared_producer(self) -> None:
        # Arrange.
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Lonely"}
        exports = [
            _export("core", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=produces)]),
            _export("integration", nodes=[_node("plans")]),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert.
        contract = next(c for c in fed.contracts if c["message_type"] == "Lonely")
        assert contract["verdict"] == ContractVerdict.UNDECLARED_PRODUCER.value
        assert contract["confirmed"] is False

    def test_v1_amqp_consumer_only_is_orphaned_consumer(self) -> None:
        # Arrange.
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "Ghost"}
        exports = [
            _export("core", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes", contract=consumes)]),
            _export("integration", nodes=[_node("svc")]),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        # Assert.
        contract = next(c for c in fed.contracts if c["message_type"] == "Ghost")
        assert contract["verdict"] == ContractVerdict.ORPHANED_CONSUMER.value
        assert contract["confirmed"] is False

    def test_v1_amqp_only_contract_has_no_graphql_surface_keys(self) -> None:
        # Arrange: an AMQP contract must not leak GraphQL-only report keys.
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "M"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "M"}
        exports = [
            _export("a", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=produces)]),
            _export("b", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes", contract=consumes)]),
        ]
        # Act.
        fed = aggregate_exports(exports, now=_T0)
        contract = next(c for c in fed.contracts if c["message_type"] == "M")
        # Assert: no exposed/references/missing keys on an AMQP contract.
        assert "exposed" not in contract
        assert "references" not in contract
        assert "missing" not in contract

    def test_v1_export_no_landscape_treated_as_one_run(self) -> None:
        # Arrange: no landscape declared on either side (the F1 wire shape).
        produces = {"protocol": "amqp", "direction": "produces", "message_type": "Shared"}
        consumes = {"protocol": "amqp", "direction": "consumes", "message_type": "Shared"}
        exports = [
            _export("core", nodes=[_node("svc"), _node("q", kind="queue")],
                    edges=[_edge("svc", "q", kind="produces", contract=produces)]),
            _export("integration", nodes=[_node("w"), _node("q", kind="queue")],
                    edges=[_edge("w", "q", kind="consumes", contract=consumes)]),
        ]
        # Act: provenance falls back to repo, reconciliation treats it as one group.
        fed = aggregate_exports(exports, now=_T0)
        # Assert: the no-landscape run still confirms cross-repo (F1 behavior),
        # and provenance reports landscape == repo (honest default).
        contract = next(c for c in fed.contracts if c["message_type"] == "Shared")
        assert contract["verdict"] == ContractVerdict.CONFIRMED.value
        landscapes = {r["repo"]: r["landscape"] for r in fed.repos}
        assert landscapes == {"core": "core", "integration": "integration"}
