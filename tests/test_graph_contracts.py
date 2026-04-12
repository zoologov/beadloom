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
    classify,
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
        # F1 flat keys preserved as a subset (BEAD-04 adds verdict/protocol/...).
        assert report["message_type"] == "m"
        assert report["directions"] == ["consumes", "produces"]
        assert report["repos"] == ["repo-a", "repo-b"]
        assert report["confirmed"] is True

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

    def test_external_edge_lifecycle_folds_to_external_verdict(self) -> None:
        """BDL-038 G7: an edge declaring ``lifecycle: external`` folds the external
        lifecycle onto the Contract → ``EXTERNAL`` verdict (never DRIFT). This is
        the end-to-end trigger for the classify branch wired defensively in BEAD-04."""
        edge = _amqp_edge("repo-a", "svc", "produces", "m")
        edge["lifecycle"] = "external"
        contract = reconcile_contracts([edge])[0]
        assert contract.lifecycle == "external"
        assert contract.verdict is ContractVerdict.EXTERNAL


class TestLandscapeScopedReconciliation:
    """BEAD-06 / U5: implicit same-key matching is scoped *within* a landscape.

    A v1/v2 edge with no ``landscape`` shares the run-level default group, so
    F1 behavior (cross-repo implicit confirm) is byte-identical. Distinct
    declared landscapes split the group, so unrelated products do not cross-
    pollute. An explicit ``@repo:`` target always resolves cross-landscape.
    """

    def test_no_landscape_implicit_match_still_confirms(self) -> None:
        # Back-compat: neither edge declares a landscape -> one shared group.
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "m"),
            _amqp_edge("repo-b", "worker", "consumes", "m"),
        ]
        contracts = reconcile_contracts(edges)
        assert len(contracts) == 1
        assert contracts[0].to_report_dict()["confirmed"] is True

    def test_same_landscape_implicit_match_confirms(self) -> None:
        edges = [
            _amqp_edge("repo-a", "svc", "produces", "m", landscape="prod"),
            _amqp_edge("repo-b", "worker", "consumes", "m", landscape="prod"),
        ]
        # Reconciliation reads landscape off the EDGE, not the contract payload.
        for edge in edges:
            edge["landscape"] = edge["contract"].pop("landscape")  # type: ignore[union-attr,index]
        contracts = reconcile_contracts(edges)
        assert len(contracts) == 1
        assert contracts[0].to_report_dict()["confirmed"] is True

    def test_distinct_landscapes_do_not_cross_pollute(self) -> None:
        # Two unrelated products sharing a coincidental message_type -> two
        # SEPARATE one-sided contracts, neither auto-confirmed.
        edges = [
            {**_amqp_edge("prod-a-svc", "svc", "produces", "Event"),
             "landscape": "product-a"},
            {**_amqp_edge("prod-b-svc", "worker", "consumes", "Event"),
             "landscape": "product-b"},
        ]
        contracts = reconcile_contracts(edges)
        assert len(contracts) == 2
        assert all(c.to_report_dict()["confirmed"] is False for c in contracts)

    def test_explicit_foreign_target_resolves_cross_landscape(self) -> None:
        # A real cross-product contract: the consumer declares @product-b:Schema.
        # It MUST reconcile with product-b's producer despite distinct landscapes.
        produce = {
            "repo": "product-b-backend",
            "src": "schema",
            "dst": "Schema",
            "kind": "produces",
            "landscape": "product-b",
            "contract": {
                "protocol": "graphql",
                "schema": "PublicAPI",
                "direction": "produces",
            },
        }
        consume = {
            "repo": "product-a-ui",
            "src": "client",
            "dst": "@product-b-backend:Schema",
            "kind": "consumes",
            "landscape": "product-a",
            "contract": {
                "protocol": "graphql",
                "schema": "PublicAPI",
                "direction": "consumes",
            },
        }
        contracts = reconcile_contracts([produce, consume])
        assert len(contracts) == 1
        assert contracts[0].to_report_dict()["confirmed"] is True


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


def _amqp_contract(
    *,
    producers: int = 0,
    consumers: int = 0,
    lifecycle: str = "active",
) -> Contract:
    endpoints = [
        ContractEndpoint(f"prod-{i}", "svc", "produces") for i in range(producers)
    ] + [ContractEndpoint(f"cons-{i}", "worker", "consumes") for i in range(consumers)]
    return Contract(
        contract_key="amqp:*/*:m",
        protocol="amqp",
        name="m",
        endpoints=endpoints,
        lifecycle=lifecycle,
    )


def _graphql_contract(
    *,
    producers: int = 1,
    consumers: int = 1,
    exposed: list[str] | None = None,
    references: list[str] | None = None,
    lifecycle: str = "active",
) -> Contract:
    endpoints = [
        ContractEndpoint(f"prod-{i}", "schema", "produces") for i in range(producers)
    ] + [ContractEndpoint(f"cons-{i}", "client", "consumes") for i in range(consumers)]
    return Contract(
        contract_key="graphql:PublicAPI",
        protocol="graphql",
        name="PublicAPI",
        endpoints=endpoints,
        lifecycle=lifecycle,
        exposed=sorted(exposed or []),
        references=sorted(references or []),
    )


class TestClassify:
    """RFC §5 truth table — one assertion per verdict (the moat)."""

    def test_dead_lifecycle_is_dead(self) -> None:
        contract = _amqp_contract(producers=1, consumers=1, lifecycle="dead")
        assert classify(contract) is ContractVerdict.DEAD

    def test_planned_lifecycle_is_expected(self) -> None:
        contract = _amqp_contract(producers=1, lifecycle="planned")
        assert classify(contract) is ContractVerdict.EXPECTED

    def test_deprecated_lifecycle_is_expected(self) -> None:
        contract = _amqp_contract(producers=1, consumers=1, lifecycle="deprecated")
        assert classify(contract) is ContractVerdict.EXPECTED

    def test_external_lifecycle_is_external(self) -> None:
        # Defensive branch; the `external` lifecycle trigger is wired in BEAD-05.
        contract = _amqp_contract(producers=1, lifecycle="external")
        assert classify(contract) is ContractVerdict.EXTERNAL

    def test_amqp_both_sides_is_confirmed(self) -> None:
        contract = _amqp_contract(producers=1, consumers=1)
        assert classify(contract) is ContractVerdict.CONFIRMED

    def test_consumers_only_is_orphaned_consumer(self) -> None:
        contract = _amqp_contract(consumers=1)
        assert classify(contract) is ContractVerdict.ORPHANED_CONSUMER

    def test_producers_only_is_undeclared_producer(self) -> None:
        contract = _amqp_contract(producers=1)
        assert classify(contract) is ContractVerdict.UNDECLARED_PRODUCER

    def test_graphql_both_sides_compatible_is_confirmed(self) -> None:
        contract = _graphql_contract(
            exposed=["Plan", "plan", "plans"], references=["plan", "plans"]
        )
        assert classify(contract) is ContractVerdict.CONFIRMED

    def test_graphql_references_not_subset_is_breaking(self) -> None:
        # Consumer references `removedField` the producer no longer exposes.
        contract = _graphql_contract(
            exposed=["Plan", "plan"], references=["plan", "removedField"]
        )
        assert classify(contract) is ContractVerdict.BREAKING

    def test_graphql_no_exposed_with_references_is_breaking(self) -> None:
        # Unparseable SDL -> exposed [] -> any reference breaks (honest, not confirmed).
        contract = _graphql_contract(exposed=[], references=["plan"])
        assert classify(contract) is ContractVerdict.BREAKING

    def test_graphql_producer_only_is_undeclared_producer(self) -> None:
        contract = _graphql_contract(producers=1, consumers=0, exposed=["plan"])
        assert classify(contract) is ContractVerdict.UNDECLARED_PRODUCER

    def test_graphql_consumer_only_is_orphaned_consumer(self) -> None:
        contract = _graphql_contract(producers=0, consumers=1, references=["plan"])
        assert classify(contract) is ContractVerdict.ORPHANED_CONSUMER

    def test_dead_outranks_breaking(self) -> None:
        # Lifecycle intent dominates the shape check.
        contract = _graphql_contract(
            exposed=[], references=["plan"], lifecycle="dead"
        )
        assert classify(contract) is ContractVerdict.DEAD


class TestContractLifecycleSignificance:
    """`reconcile_contracts` folds the most-significant edge lifecycle onto the Contract."""

    def test_dead_outranks_active(self) -> None:
        edges = [
            _amqp_edge("a", "svc", "produces", "m"),
            {**_amqp_edge("b", "worker", "consumes", "m"), "lifecycle": "dead"},
        ]
        edges[0]["lifecycle"] = "active"
        contract = reconcile_contracts(edges)[0]
        assert contract.lifecycle == "dead"

    def test_deprecated_outranks_planned(self) -> None:
        edges = [
            {**_amqp_edge("a", "svc", "produces", "m"), "lifecycle": "planned"},
            {**_amqp_edge("b", "worker", "consumes", "m"), "lifecycle": "deprecated"},
        ]
        contract = reconcile_contracts(edges)[0]
        assert contract.lifecycle == "deprecated"

    def test_default_lifecycle_is_active(self) -> None:
        contract = reconcile_contracts([_amqp_edge("a", "svc", "produces", "m")])[0]
        assert contract.lifecycle == "active"


class TestVerdictWiredIntoReconcile:
    def test_reconcile_assigns_verdict(self) -> None:
        edges = [
            _amqp_edge("a", "svc", "produces", "m"),
            _amqp_edge("b", "worker", "consumes", "m"),
        ]
        contract = reconcile_contracts(edges)[0]
        assert contract.verdict is ContractVerdict.CONFIRMED

    def test_report_dict_keeps_f1_keys_and_adds_verdict(self) -> None:
        edges = [
            _amqp_edge("a", "svc", "produces", "m"),
            _amqp_edge("b", "worker", "consumes", "m"),
        ]
        report = reconcile_contracts(edges)[0].to_report_dict()
        # F1 flat keys preserved (nothing downstream breaks).
        assert report["message_type"] == "m"
        assert report["directions"] == ["consumes", "produces"]
        assert report["repos"] == ["a", "b"]
        assert report["confirmed"] is True
        # F2 enrichment.
        assert report["verdict"] == "confirmed"
        assert report["protocol"] == "amqp"
        assert report["contract_key"] == "amqp:*/*:m"

    def test_report_dict_graphql_includes_missing_references(self) -> None:
        edges = [
            _graphql_edge("backend", "schema", "produces", "PublicAPI",
                          exposed=["plan"]),
            _graphql_edge("ui", "client", "consumes", "PublicAPI",
                          references=["plan", "removedField"]),
        ]
        report = reconcile_contracts(edges)[0].to_report_dict()
        assert report["verdict"] == "breaking"
        assert report["exposed"] == ["plan"]
        assert report["references"] == ["plan", "removedField"]
        assert report["missing"] == ["removedField"]
