"""Golden tests for the NATIVE typed GraphQL breaking verdict (BDL-060 S2, G1a).

The name-level presence verdict (BDL-038) flags a consumer-referenced NAME absent
from the producer's exposed surface. S2 deepens this: when BOTH sides carry a
TYPED surface (``graphql-core`` parsed the SDL — see
:mod:`beadloom.graph.graphql_surface`), the verdict additionally catches:

- an absent referenced field (presence — unchanged),
- a field whose producer type is incompatibly changed (type-narrowed),
- a nullability break (producer made a referenced field nullable, or requires a
  new non-null arg the consumer doesn't supply),
- an arg-type narrowing.

Purely additive producer changes (a new optional field, a new nullable arg) are
BENIGN. Subscriptions are FIRST-CLASS (a dropped/retyped subscription field is a
break). A verdict is only as strong as the data: absent typed depth on either
side, the check honestly degrades to name-presence (identical to BDL-038).
"""

from __future__ import annotations

from beadloom.graph.contracts import Contract, ContractEndpoint, ContractVerdict, classify


def _typed_contract(
    *,
    exposed_fields: dict[str, object] | None = None,
    referenced_fields: dict[str, object] | None = None,
    exposed: list[str] | None = None,
    references: list[str] | None = None,
    lifecycle: str = "active",
) -> Contract:
    """Build a both-sided GraphQL contract with optional typed surfaces."""
    return Contract(
        contract_key="graphql:WebAPI",
        protocol="graphql",
        name="WebAPI",
        endpoints=[
            ContractEndpoint("backend", "schema", "produces"),
            ContractEndpoint("ui", "client", "consumes"),
        ],
        lifecycle=lifecycle,
        exposed=sorted(exposed or []),
        references=sorted(references or []),
        exposed_fields=exposed_fields or {},
        referenced_fields=referenced_fields or {},
    )


def _field(type_: str, **args: str) -> dict[str, object]:
    return {"type": type_, "args": dict(args)}


class TestTypedBreakingVerdict:
    """When both sides are typed, the verdict reasons over types + args."""

    def test_absent_referenced_field_is_breaking(self) -> None:
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan")},
            referenced_fields={"plan": _field("Plan"), "subscriptionTier": _field("Tier")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "subscriptionTier" in contract.breaking_fields

    def test_type_narrowing_is_breaking(self) -> None:
        # Producer changed `plan`'s return type incompatibly (Plan -> Account).
        contract = _typed_contract(
            exposed_fields={"plan": _field("Account")},
            referenced_fields={"plan": _field("Plan")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "plan" in contract.breaking_fields

    def test_nullability_break_on_return_type_is_breaking(self) -> None:
        # Consumer relied on a NON-NULL `plan: Plan!`; producer made it nullable.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan")},
            referenced_fields={"plan": _field("Plan!")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "plan" in contract.breaking_fields

    def test_new_required_arg_is_breaking(self) -> None:
        # Producer added a NON-NULL arg the consumer never supplied.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan", id="ID!")},
            referenced_fields={"plan": _field("Plan")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert any("plan" in b for b in contract.breaking_fields)

    def test_arg_type_narrowing_is_breaking(self) -> None:
        # Producer narrowed an arg the consumer supplies (Int -> Int!): the
        # consumer's nullable Int no longer satisfies the required arg.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan", limit="Int!")},
            referenced_fields={"plan": _field("Plan", limit="Int")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert any("plan" in b for b in contract.breaking_fields)


class TestTypedBenignVerdict:
    """Purely additive producer changes are CONFIRMED, never BREAKING."""

    def test_new_optional_field_is_benign(self) -> None:
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan"), "newThing": _field("Thing")},
            referenced_fields={"plan": _field("Plan")},
        )
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.breaking_fields == []

    def test_new_nullable_arg_is_benign(self) -> None:
        # Producer added a NULLABLE arg — old consumers still satisfy the field.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan", filter="String")},
            referenced_fields={"plan": _field("Plan")},
        )
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.breaking_fields == []

    def test_producer_widened_nullability_is_benign(self) -> None:
        # Consumer relied on nullable `plan: Plan`; producer made it NON-NULL
        # `plan: Plan!` — strictly more guarantees, still satisfies the consumer.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan!")},
            referenced_fields={"plan": _field("Plan")},
        )
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.breaking_fields == []

    def test_exact_match_is_confirmed(self) -> None:
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan", id="ID!")},
            referenced_fields={"plan": _field("Plan", id="ID!")},
        )
        assert classify(contract) is ContractVerdict.CONFIRMED


class TestSubscriptionFirstClass:
    """A dropped or retyped subscription field is a first-class break."""

    def test_dropped_subscription_field_is_breaking(self) -> None:
        contract = _typed_contract(
            exposed_fields={"planUpdated": _field("Plan")},
            referenced_fields={"planUpdated": _field("Plan"), "accountUpdated": _field("Account")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "accountUpdated" in contract.breaking_fields

    def test_retyped_subscription_field_is_breaking(self) -> None:
        contract = _typed_contract(
            exposed_fields={"planUpdated": _field("Account!")},
            referenced_fields={"planUpdated": _field("Plan!")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "planUpdated" in contract.breaking_fields


class TestHonestDegradationToNameLevel:
    """Absent typed depth, the verdict stays name-presence (BDL-038 parity)."""

    def test_no_typed_surface_uses_name_presence_breaking(self) -> None:
        contract = _typed_contract(
            exposed=["plan", "account"],
            references=["plan", "subscriptionTier"],
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert contract.missing_references == ["subscriptionTier"]

    def test_no_typed_surface_present_names_confirmed(self) -> None:
        contract = _typed_contract(
            exposed=["plan", "account"],
            references=["plan"],
        )
        assert classify(contract) is ContractVerdict.CONFIRMED

    def test_only_producer_typed_falls_back_to_presence(self) -> None:
        # Consumer has no typed surface -> cannot type-check; presence only.
        contract = _typed_contract(
            exposed_fields={"plan": _field("Account")},
            exposed=["plan"],
            references=["plan"],
        )
        # Type differs, but with no consumer typed surface we honestly can't
        # claim a type break — name is present -> CONFIRMED.
        assert classify(contract) is ContractVerdict.CONFIRMED

    def test_amqp_contract_has_no_breaking_fields(self) -> None:
        contract = Contract(
            contract_key="amqp:*/*:m",
            protocol="amqp",
            name="m",
            endpoints=[ContractEndpoint("p", "svc", "produces")],
        )
        assert contract.breaking_fields == []


class TestReportDictCarriesTypedBreaks:
    """``to_report_dict`` surfaces the typed break names under ``missing``."""

    def test_report_missing_includes_typed_breaks(self) -> None:
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan")},
            referenced_fields={"plan": _field("Plan"), "gone": _field("X")},
        )
        report = contract.to_report_dict()
        assert report["verdict"] == "breaking"
        assert "gone" in report["missing"]  # type: ignore[operator]

    def test_report_missing_empty_when_confirmed(self) -> None:
        contract = _typed_contract(
            exposed_fields={"plan": _field("Plan")},
            referenced_fields={"plan": _field("Plan")},
        )
        report = contract.to_report_dict()
        assert report["verdict"] == "confirmed"
        assert report["missing"] == []
