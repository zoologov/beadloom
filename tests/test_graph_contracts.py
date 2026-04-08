"""Unit tests for the first-class contract model (BDL-038 BEAD-01).

Covers ``contract_key`` derivation (AMQP back-compat + GraphQL hook + unknown
protocol), the ``Contract`` projection back to F1's flat shape, the
producers/consumers views, ``reconcile_contracts`` grouping/ordering, and the
``ContractVerdict`` skeleton.
"""

from __future__ import annotations

from beadloom.graph.contracts import (
    Contract,
    ContractEndpoint,
    ContractVerdict,
    contract_key,
    reconcile_contracts,
)


def _amqp_edge(
    repo: str,
    src: str,
    direction: str,
    message_type: str,
    **contract_extra: object,
) -> dict[str, object]:
    return {
        "repo": repo,
        "src": src,
        "dst": "q",
        "kind": direction,
        "contract": {
            "protocol": "amqp",
            "message_type": message_type,
            "direction": direction,
            **contract_extra,
        },
    }


class TestContractKey:
    def test_amqp_message_type_only_is_back_compatible(self) -> None:
        # A v1 export (no exchange/routing) -> wildcard key, still reconciles.
        key = contract_key({"protocol": "amqp", "message_type": "plan_uploaded"})
        assert key == "amqp:*/*:plan_uploaded"

    def test_amqp_exchange_and_routing_participate(self) -> None:
        key = contract_key(
            {
                "protocol": "amqp",
                "message_type": "plan_uploaded",
                "exchange": "plans",
                "routing_key": "upload",
            }
        )
        assert key == "amqp:plans/upload:plan_uploaded"

    def test_amqp_same_name_different_exchange_distinct(self) -> None:
        a = contract_key({"protocol": "amqp", "message_type": "x", "exchange": "e1"})
        b = contract_key({"protocol": "amqp", "message_type": "x", "exchange": "e2"})
        assert a != b

    def test_graphql_resolves_by_schema_name(self) -> None:
        assert contract_key({"protocol": "graphql", "schema": "PublicAPI"}) == (
            "graphql:PublicAPI"
        )

    def test_graphql_falls_back_to_name(self) -> None:
        assert contract_key({"protocol": "graphql", "name": "PublicAPI"}) == (
            "graphql:PublicAPI"
        )

    def test_unknown_protocol_is_namespaced_and_stable(self) -> None:
        assert contract_key({"protocol": "grpc", "name": "Greeter"}) == "grpc:Greeter"


class TestContractProjection:
    def test_to_report_dict_confirmed_both_sides(self) -> None:
        contract = Contract(
            contract_key="amqp:*/*:m",
            protocol="amqp",
            name="m",
            endpoints=[
                ContractEndpoint("repo-a", "svc", "produces"),
                ContractEndpoint("repo-b", "worker", "consumes"),
            ],
        )
        report = contract.to_report_dict()
        assert report == {
            "message_type": "m",
            "directions": ["consumes", "produces"],
            "repos": ["repo-a", "repo-b"],
            "confirmed": True,
        }

    def test_to_report_dict_one_sided_not_confirmed(self) -> None:
        contract = Contract(
            contract_key="amqp:*/*:m",
            protocol="amqp",
            name="m",
            endpoints=[ContractEndpoint("repo-a", "svc", "produces")],
        )
        report = contract.to_report_dict()
        assert report["confirmed"] is False
        assert report["directions"] == ["produces"]
        assert report["repos"] == ["repo-a"]

    def test_producers_and_consumers_views(self) -> None:
        contract = Contract(
            contract_key="amqp:*/*:m",
            protocol="amqp",
            name="m",
            endpoints=[
                ContractEndpoint("repo-a", "svc", "produces"),
                ContractEndpoint("repo-b", "worker", "consumes"),
                ContractEndpoint("repo-c", "other", "consumes"),
            ],
        )
        assert [e.repo for e in contract.producers] == ["repo-a"]
        assert [e.repo for e in contract.consumers] == ["repo-b", "repo-c"]

    def test_endpoint_is_frozen(self) -> None:
        endpoint = ContractEndpoint("repo-a", "svc", "produces")
        try:
            endpoint.repo = "x"  # type: ignore[misc]
        except AttributeError:
            return
        raise AssertionError("ContractEndpoint must be frozen")


class TestReconcileContracts:
    def test_groups_produces_and_consumes_into_one_contract(self) -> None:
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "m"),
            _amqp_edge("repo-b", "worker", "consumes", "m"),
        ]
        contracts = reconcile_contracts(edges)
        assert len(contracts) == 1
        assert contracts[0].to_report_dict()["confirmed"] is True

    def test_ignores_plain_edges_but_groups_graphql(self) -> None:
        edges = [
            {"repo": "r", "src": "a", "dst": "b", "kind": "depends_on"},
            {
                "repo": "r",
                "src": "a",
                "dst": "b",
                "kind": "consumes",
                "contract": {"protocol": "graphql", "schema": "API"},
            },
            _amqp_edge("repo-a", "svc", "produces", "m"),
        ]
        contracts = reconcile_contracts(edges)
        # BEAD-03: AMQP + GraphQL both reconcile; plain edge ignored.
        protocols = {c.protocol for c in contracts}
        assert protocols == {"amqp", "graphql"}

    def test_distinct_message_types_stay_separate(self) -> None:
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "msg_a"),
            _amqp_edge("repo-a", "svc", "produces", "msg_b"),
        ]
        contracts = reconcile_contracts(edges)
        assert {c.name for c in contracts} == {"msg_a", "msg_b"}

    def test_insertion_order_preserved(self) -> None:
        # First-appearance order (byte-identical to F1, which did not sort).
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "zeta"),
            _amqp_edge("repo-a", "svc", "produces", "alpha"),
        ]
        contracts = reconcile_contracts(edges)
        assert [c.name for c in contracts] == ["zeta", "alpha"]

    def test_one_sided_producer_not_confirmed(self) -> None:
        contracts = reconcile_contracts([_amqp_edge("repo-a", "svc", "produces", "m")])
        assert contracts[0].to_report_dict()["confirmed"] is False


def _graphql_edge(
    repo: str,
    src: str,
    direction: str,
    schema: str,
    **contract_extra: object,
) -> dict[str, object]:
    return {
        "repo": repo,
        "src": src,
        "dst": "@backend:Schema",
        "kind": direction,
        "contract": {
            "protocol": "graphql",
            "schema": schema,
            "direction": direction,
            **contract_extra,
        },
    }


class TestReconcileGraphQL:
    """BEAD-03 / G3: GraphQL contracts resolve across the language boundary by name."""

    def test_producer_and_consumer_group_by_schema_name(self) -> None:
        edges = [
            _graphql_edge("backend", "schema", "produces", "PublicAPI",
                          exposed=["Plan", "plan", "plans"]),
            _graphql_edge("ui", "client", "consumes", "PublicAPI",
                          references=["plan", "plans"]),
        ]
        contracts = reconcile_contracts(edges)
        assert len(contracts) == 1
        contract = contracts[0]
        assert contract.protocol == "graphql"
        assert contract.contract_key == "graphql:PublicAPI"
        assert contract.name == "PublicAPI"
        # Cross-language resolve: a producer and a consumer, by NAME not symbol.
        assert len(contract.producers) == 1
        assert len(contract.consumers) == 1

    def test_exposed_and_references_attached_sorted(self) -> None:
        edges = [
            _graphql_edge("backend", "schema", "produces", "PublicAPI",
                          exposed=["plans", "Plan", "plan"]),
            _graphql_edge("ui", "client", "consumes", "PublicAPI",
                          references=["plans", "plan"]),
        ]
        contract = reconcile_contracts(edges)[0]
        assert contract.exposed == ["Plan", "plan", "plans"]
        assert contract.references == ["plan", "plans"]

    def test_different_schemas_stay_separate(self) -> None:
        edges = [
            _graphql_edge("backend", "s", "produces", "ApiA"),
            _graphql_edge("backend", "s", "produces", "ApiB"),
        ]
        contracts = reconcile_contracts(edges)
        assert {c.name for c in contracts} == {"ApiA", "ApiB"}

    def test_amqp_and_graphql_both_reconciled(self) -> None:
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "m"),
            _graphql_edge("backend", "schema", "produces", "PublicAPI"),
        ]
        contracts = reconcile_contracts(edges)
        assert {c.protocol for c in contracts} == {"amqp", "graphql"}

    def test_graphql_to_report_dict_is_generic_flat_shape(self) -> None:
        """GraphQL Contract still renders the F1 flat shape (name=schema)."""
        edges = [
            _graphql_edge("backend", "schema", "produces", "PublicAPI"),
            _graphql_edge("ui", "client", "consumes", "PublicAPI"),
        ]
        report = reconcile_contracts(edges)[0].to_report_dict()
        assert report["message_type"] == "PublicAPI"
        assert report["directions"] == ["consumes", "produces"]
        assert report["confirmed"] is True

    def test_amqp_contract_has_empty_exposed_and_references(self) -> None:
        """No regression: AMQP contracts default exposed/references to empty."""
        contract = reconcile_contracts([_amqp_edge("r", "svc", "produces", "m")])[0]
        assert contract.exposed == []
        assert contract.references == []


class TestContractVerdictSkeleton:
    def test_all_f2_verdicts_defined(self) -> None:
        values = {v.value for v in ContractVerdict}
        assert values == {
            "confirmed",
            "drift",
            "orphaned_consumer",
            "undeclared_producer",
            "breaking",
            "expected",
            "external",
            "dead",
        }
