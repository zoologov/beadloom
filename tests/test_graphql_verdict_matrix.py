"""Golden verdict MATRIX for the native typed GraphQL breaking analysis (BDL-060 S2).

This is the epic spine's DATA-STRICTNESS proof: one golden table that pins, on a
representative schema surface, *exactly* which producer changes break a consumer
and which are benign. It exercises both layers the verdict is built from:

- the pure comparator ``graph.graphql_breaking.breaking_field_descriptors``
  (which consumer references does the producer break, named field/arg), and
- the contract-level ``graph.contracts.classify`` / ``Contract.breaking_fields``
  that lift those descriptors into a ``ContractVerdict``.

The break classes covered (parametrized so the golden table is the test):
field removed, return-type changed (incompatible named type), nullability
narrowed (``T!`` expected, producer ``T``), new REQUIRED arg, supplied-arg
narrowed (``T`` -> ``T!``), supplied-arg retyped. Benign: new optional field,
new nullable arg, widened nullability (``T`` -> ``T!``), exact match.

Subscriptions are first-class — a subscription-field break is in the SAME table,
and a subscription-only producer/consumer pair is verified to verdict correctly.

KNOWN LIMITATION (documented honestly, not papered over): the comparator unwraps
``!`` and ``[]`` to the underlying NAMED type, so a pure list-wrapping change
(``[T]`` <-> ``T``, ``[T]`` <-> ``[T!]``) is NOT currently caught — the inner
named type is identical and the OUTER nullability is unchanged. These cases are
pinned as ``xfail(strict=True)`` so the day the comparator gains list-structure
awareness, the guard flips RED and forces this matrix to be updated (it never
silently rots into a false pass). See ``TestListWrappingLimitation``.
"""

from __future__ import annotations

import pytest

from beadloom.graph.contracts import (
    Contract,
    ContractEndpoint,
    ContractVerdict,
    classify,
)
from beadloom.graph.graphql_breaking import breaking_field_descriptors


def _field(type_: str, **args: str) -> dict[str, object]:
    """A serialized typed field: ``{"type": <gql>, "args": {name: type}}``."""
    return {"type": type_, "args": dict(args)}


def _gql_contract(
    exposed_fields: dict[str, object],
    referenced_fields: dict[str, object],
    *,
    lifecycle: str = "active",
) -> Contract:
    """A both-sided typed GraphQL contract (producer + consumer present)."""
    return Contract(
        contract_key="graphql:WebAPI",
        protocol="graphql",
        name="WebAPI",
        endpoints=[
            ContractEndpoint("backend", "schema", "produces"),
            ContractEndpoint("ui", "client", "consumes"),
        ],
        lifecycle=lifecycle,
        exposed_fields=exposed_fields,
        referenced_fields=referenced_fields,
    )


# --------------------------------------------------------------------------- #
# The golden BREAKING matrix: each row is (id, exposed, referenced, expected   #
# offending descriptor). ``expected`` must appear in the descriptors list.     #
# --------------------------------------------------------------------------- #
_BREAKING_CASES: list[
    tuple[str, dict[str, object], dict[str, object], str]
] = [
    (
        "field_removed",
        {"plan": _field("Plan")},
        {"plan": _field("Plan"), "account": _field("Account")},
        "account",
    ),
    (
        "return_type_changed_incompatible",
        {"plan": _field("Account")},
        {"plan": _field("Plan")},
        "plan",
    ),
    (
        "return_nullability_narrowed",  # consumer relied on T!, producer is T
        {"plan": _field("Plan")},
        {"plan": _field("Plan!")},
        "plan",
    ),
    (
        "new_required_arg",  # producer requires a non-null arg consumer omits
        {"plan": _field("Plan", id="ID!")},
        {"plan": _field("Plan")},
        "plan(id)",
    ),
    (
        "supplied_arg_narrowed",  # arg the consumer supplies narrowed Int -> Int!
        {"plan": _field("Plan", limit="Int!")},
        {"plan": _field("Plan", limit="Int")},
        "plan(limit)",
    ),
    (
        "supplied_arg_retyped",  # arg's named type changed under the consumer
        {"plan": _field("Plan", filter="String")},
        {"plan": _field("Plan", filter="Int")},
        "plan(filter)",
    ),
    (
        "subscription_field_removed",  # subscriptions are first-class
        {"planUpdated": _field("Plan!")},
        {"planUpdated": _field("Plan!"), "accountUpdated": _field("Account!")},
        "accountUpdated",
    ),
    (
        "subscription_field_retyped",
        {"planUpdated": _field("Account!")},
        {"planUpdated": _field("Plan!")},
        "planUpdated",
    ),
]


# --------------------------------------------------------------------------- #
# The golden BENIGN matrix: additive producer changes never break a consumer.  #
# --------------------------------------------------------------------------- #
_BENIGN_CASES: list[
    tuple[str, dict[str, object], dict[str, object]]
] = [
    (
        "new_optional_field",
        {"plan": _field("Plan"), "extra": _field("Extra")},
        {"plan": _field("Plan")},
    ),
    (
        "new_nullable_arg",  # producer adds a NULLABLE arg the consumer omits
        {"plan": _field("Plan", filter="String")},
        {"plan": _field("Plan")},
    ),
    (
        "widened_nullability",  # producer T -> T!, more guarantees, still ok
        {"plan": _field("Plan!")},
        {"plan": _field("Plan")},
    ),
    (
        "exact_match",
        {"plan": _field("Plan", id="ID!")},
        {"plan": _field("Plan", id="ID!")},
    ),
    (
        "exact_match_subscription",
        {"planUpdated": _field("Plan!")},
        {"planUpdated": _field("Plan!")},
    ),
    (
        "widened_arg_nullability",  # supplied arg producer Int -> consumer Int!
        {"plan": _field("Plan", limit="Int")},
        {"plan": _field("Plan", limit="Int!")},
    ),
    (
        "consumer_subset_of_producer",  # consumer references fewer fields
        {"a": _field("A"), "b": _field("B"), "c": _field("C")},
        {"a": _field("A")},
    ),
]


class TestBreakingDescriptorMatrix:
    """Pure comparator: each break class yields the named offending descriptor."""

    @pytest.mark.parametrize(
        ("exposed", "referenced", "expected"),
        [(c[1], c[2], c[3]) for c in _BREAKING_CASES],
        ids=[c[0] for c in _BREAKING_CASES],
    )
    def test_break_class_named(
        self,
        exposed: dict[str, object],
        referenced: dict[str, object],
        expected: str,
    ) -> None:
        descriptors = breaking_field_descriptors(exposed, referenced)
        assert expected in descriptors

    @pytest.mark.parametrize(
        ("exposed", "referenced"),
        [(c[1], c[2]) for c in _BENIGN_CASES],
        ids=[c[0] for c in _BENIGN_CASES],
    )
    def test_benign_class_empty(
        self, exposed: dict[str, object], referenced: dict[str, object]
    ) -> None:
        assert breaking_field_descriptors(exposed, referenced) == []


class TestContractVerdictMatrix:
    """Contract layer: the same matrix lifts to BREAKING / CONFIRMED verdicts."""

    @pytest.mark.parametrize(
        ("exposed", "referenced", "expected"),
        [(c[1], c[2], c[3]) for c in _BREAKING_CASES],
        ids=[c[0] for c in _BREAKING_CASES],
    )
    def test_break_class_is_breaking_verdict(
        self,
        exposed: dict[str, object],
        referenced: dict[str, object],
        expected: str,
    ) -> None:
        contract = _gql_contract(exposed, referenced)
        assert classify(contract) is ContractVerdict.BREAKING
        assert expected in contract.breaking_fields
        # The report surfaces the offending name under ``missing``.
        assert expected in contract.to_report_dict()["missing"]  # type: ignore[operator]

    @pytest.mark.parametrize(
        ("exposed", "referenced"),
        [(c[1], c[2]) for c in _BENIGN_CASES],
        ids=[c[0] for c in _BENIGN_CASES],
    )
    def test_benign_class_is_confirmed_verdict(
        self, exposed: dict[str, object], referenced: dict[str, object]
    ) -> None:
        contract = _gql_contract(exposed, referenced)
        assert classify(contract) is ContractVerdict.CONFIRMED
        assert contract.breaking_fields == []


class TestDescriptorDeterminism:
    """Descriptors are sorted + deduped regardless of input field ordering."""

    def test_multiple_breaks_are_sorted(self) -> None:
        exposed = {"plan": _field("Plan")}
        referenced = {
            "zeta": _field("Z"),
            "alpha": _field("A"),
            "plan": _field("Plan"),
            "mid": _field("M"),
        }
        descriptors = breaking_field_descriptors(exposed, referenced)
        assert descriptors == sorted(descriptors)
        assert descriptors == ["alpha", "mid", "zeta"]

    def test_field_and_arg_break_on_same_field_both_named(self) -> None:
        # A field with BOTH a return-type break AND a required-arg break names
        # both the bare field and the ``field(arg)`` descriptor.
        exposed = {"plan": _field("Account", id="ID!")}
        referenced = {"plan": _field("Plan")}
        descriptors = breaking_field_descriptors(exposed, referenced)
        assert "plan" in descriptors
        assert "plan(id)" in descriptors

    def test_empty_reference_set_is_never_breaking(self) -> None:
        assert breaking_field_descriptors({"plan": _field("Plan")}, {}) == []

    def test_empty_producer_breaks_every_reference(self) -> None:
        referenced = {"a": _field("A"), "b": _field("B")}
        assert breaking_field_descriptors({}, referenced) == ["a", "b"]


class TestSubscriptionOnlySurface:
    """A subscription-only contract verdicts as a first-class surface."""

    def test_subscription_only_confirmed(self) -> None:
        contract = _gql_contract(
            {"ticker": _field("Quote!")},
            {"ticker": _field("Quote!")},
        )
        assert classify(contract) is ContractVerdict.CONFIRMED

    def test_subscription_only_breaking_when_dropped(self) -> None:
        contract = _gql_contract(
            {"ticker": _field("Quote!")},
            {"ticker": _field("Quote!"), "depth": _field("Book!")},
        )
        assert classify(contract) is ContractVerdict.BREAKING
        assert "depth" in contract.breaking_fields


class TestLifecycleDominatesVerdict:
    """Lifecycle intent dominates a typed break (a dead/planned contract is not
    reported BREAKING even when its typed surface is broken)."""

    @pytest.mark.parametrize(
        ("lifecycle", "expected"),
        [
            ("dead", ContractVerdict.DEAD),
            ("planned", ContractVerdict.EXPECTED),
            ("deprecated", ContractVerdict.EXPECTED),
            ("external", ContractVerdict.EXTERNAL),
        ],
    )
    def test_lifecycle_overrides_typed_break(
        self, lifecycle: str, expected: ContractVerdict
    ) -> None:
        contract = _gql_contract(
            {"plan": _field("Plan")},
            {"plan": _field("Plan"), "gone": _field("X")},
            lifecycle=lifecycle,
        )
        assert classify(contract) is expected


class TestListWrappingLimitation:
    """KNOWN LIMITATION: pure list-wrapping changes are not yet detected.

    The comparator ``_unwrap`` strips ``[]`` to the underlying named type, so a
    ``[T]`` <-> ``T`` or ``[T]`` <-> ``[T!]`` shape change has an identical named
    type and unchanged OUTER nullability — it is NOT flagged. These are pinned
    ``xfail(strict=True)``: list-structure awareness landing in the comparator
    flips them RED and forces this matrix to be revisited (no silent rot).
    """

    @pytest.mark.xfail(
        strict=True,
        reason="list-structure not modelled: [T]<->T flattens to the same named "
        "type with unchanged outer nullability (BDL-060 S2 known limitation)",
    )
    def test_list_to_scalar_should_break(self) -> None:
        # Consumer expects a list ``[Plan]``; producer now returns scalar ``Plan``.
        exposed = {"plan": _field("Plan")}
        referenced = {"plan": _field("[Plan]")}
        assert breaking_field_descriptors(exposed, referenced) == ["plan"]

    @pytest.mark.xfail(
        strict=True,
        reason="list inner-nullability not modelled: [T] vs [T!] share the same "
        "named type + outer nullability (BDL-060 S2 known limitation)",
    )
    def test_list_inner_nullability_should_break(self) -> None:
        # Consumer relied on ``[Plan!]`` (no nulls inside); producer now ``[Plan]``.
        exposed = {"plan": _field("[Plan]")}
        referenced = {"plan": _field("[Plan!]")}
        assert breaking_field_descriptors(exposed, referenced) == ["plan"]

    def test_outer_list_nullability_narrowing_is_caught(self) -> None:
        # The OUTER nullability IS modelled: ``[Plan]!`` -> ``[Plan]`` narrows the
        # outermost ``!`` and is correctly flagged (regression guard).
        exposed = {"plan": _field("[Plan]")}
        referenced = {"plan": _field("[Plan]!")}
        assert breaking_field_descriptors(exposed, referenced) == ["plan"]
