"""Golden tests for the AMQP body-diff at the Contract/verdict layer (S3, G1b).

When BOTH sides of an AMQP contract carry a ``body`` JSON-Schema, the verdict
reasons over the body fields/types (mirroring the GraphQL typed verdict): a
consumer-read field that is absent, type-incompatible, required-but-now-optional,
or nested/array-broken in the producer body → ``BREAKING`` naming the field path.
Absent a body on either side, the AMQP verdict honestly degrades to the
name-level both-sides presence check (BDL-038 parity — ``CONFIRMED``).
"""

from __future__ import annotations

from beadloom.graph.contracts import (
    Contract,
    ContractEndpoint,
    ContractVerdict,
    classify,
)


def _obj(
    properties: dict[str, dict[str, object]],
    required: list[str] | None = None,
) -> dict[str, object]:
    node: dict[str, object] = {"type": "object", "properties": properties}
    if required is not None:
        node["required"] = required
    return node


def _amqp_contract(
    *,
    exposed_body: dict[str, object] | None = None,
    referenced_body: dict[str, object] | None = None,
    lifecycle: str = "active",
) -> Contract:
    """A both-sided AMQP contract with optional producer/consumer body schemas."""
    return Contract(
        contract_key="amqp:ex/rk:start_plan_version_upload",
        protocol="amqp",
        name="start_plan_version_upload",
        endpoints=[
            ContractEndpoint("core", "publisher", "produces"),
            ContractEndpoint("integration", "consumer", "consumes"),
        ],
        lifecycle=lifecycle,
        exposed_body=exposed_body or {},
        referenced_body=referenced_body or {},
    )


class TestAmqpBodyBreaking:
    def test_absent_consumer_field_is_breaking(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"id": {"type": "string"}}),
            referenced_body=_obj({"id": {"type": "string"}, "amount": {"type": "number"}}),
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "amount" in contract.body_breaking_fields

    def test_type_incompatible_field_is_breaking(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"amount": {"type": "string"}}),
            referenced_body=_obj({"amount": {"type": "number"}}),
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "amount" in contract.body_breaking_fields

    def test_required_by_consumer_now_optional_is_breaking(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"id": {"type": "string"}}, required=[]),
            referenced_body=_obj({"id": {"type": "string"}}, required=["id"]),
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "id" in contract.body_breaking_fields

    def test_nested_object_break_names_path(self) -> None:
        nested = _obj({"id": {"type": "string"}, "tier": {"type": "string"}})
        contract = _amqp_contract(
            exposed_body=_obj({"plan": _obj({"id": {"type": "string"}})}),
            referenced_body=_obj({"plan": nested}),
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "plan.tier" in contract.body_breaking_fields

    def test_report_dict_surfaces_body_breaks(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"id": {"type": "string"}}),
            referenced_body=_obj({"id": {"type": "string"}, "gone": {"type": "string"}}),
        )
        report = contract.to_report_dict()
        assert report["verdict"] == "breaking"
        assert "gone" in report["missing"]  # type: ignore[operator]


class TestAmqpBodyBenign:
    def test_additive_producer_field_is_benign(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"id": {"type": "string"}, "extra": {"type": "string"}}),
            referenced_body=_obj({"id": {"type": "string"}}),
        )
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.body_breaking_fields == []

    def test_widened_requiredness_is_benign(self) -> None:
        contract = _amqp_contract(
            exposed_body=_obj({"id": {"type": "string"}}, required=["id"]),
            referenced_body=_obj({"id": {"type": "string"}}, required=[]),
        )
        assert classify(contract) is ContractVerdict.CONFIRMED


class TestAmqpHonestDegradation:
    def test_no_body_falls_back_to_presence_confirmed(self) -> None:
        # Both sides present, no body declared -> name-level CONFIRMED (BDL-038).
        contract = _amqp_contract()
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.body_breaking_fields == []

    def test_only_producer_body_falls_back_to_presence(self) -> None:
        # Consumer declared no body -> cannot prove a break; presence-based.
        contract = _amqp_contract(exposed_body=_obj({"id": {"type": "number"}}))
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.body_breaking_fields == []

    def test_graphql_contract_has_no_body_breaks(self) -> None:
        contract = Contract(
            contract_key="graphql:WebAPI",
            protocol="graphql",
            name="WebAPI",
            endpoints=[ContractEndpoint("p", "schema", "produces")],
        )
        assert contract.body_breaking_fields == []
