"""Golden tests for the strict AMQP message-body JSON-Schema model + diff (S3, G1b).

The name-level AMQP contract (F1/BDL-038) only knew a ``message_type`` was
produced/consumed. S3 deepens this with an optional ``body`` JSON-Schema on the
producer/consumer edge: properties + types + ``required`` + enums + nested
objects/arrays. The native body-diff verdict (mirroring the GraphQL one) compares
the **consumer-referenced body fields/types vs the producer's body schema**:

- a field the consumer reads that is **absent** in the producer body → BREAKING,
- a field whose producer **type is incompatible** with the consumer's → BREAKING,
- a field **required by the consumer but now optional/removed** in the producer →
  BREAKING,
- nested-object and array-``items`` breaks recurse with the same rigor.

Additive producer fields, and a producer **widening** an optional field the
consumer required (i.e. producer requires it too — strictly more guarantees) are
benign. A verdict is only as strong as the data: absent a body on either side the
check degrades honestly to name-presence (BDL-038 parity).
"""

from __future__ import annotations

from beadloom.graph.amqp_body import (
    BodySchema,
    breaking_body_descriptors,
    parse_body,
    serialize_body,
)


def _obj(
    properties: dict[str, dict[str, object]],
    required: list[str] | None = None,
) -> dict[str, object]:
    """A JSON-Schema object node ({type:object, properties, required})."""
    node: dict[str, object] = {"type": "object", "properties": properties}
    if required is not None:
        node["required"] = required
    return node


class TestBodyDiffBreaking:
    """A consumer-read field absent/retyped/required-but-now-optional → breaking."""

    def test_absent_field_is_breaking(self) -> None:
        producer = _obj({"id": {"type": "string"}})
        consumer = _obj({"id": {"type": "string"}, "amount": {"type": "number"}})
        assert breaking_body_descriptors(producer, consumer) == ["amount"]

    def test_type_incompatible_field_is_breaking(self) -> None:
        producer = _obj({"amount": {"type": "string"}})
        consumer = _obj({"amount": {"type": "number"}})
        assert breaking_body_descriptors(producer, consumer) == ["amount"]

    def test_required_by_consumer_now_optional_is_breaking(self) -> None:
        # Consumer requires `id`; producer still has it but no longer requires it.
        producer = _obj({"id": {"type": "string"}}, required=[])
        consumer = _obj({"id": {"type": "string"}}, required=["id"])
        assert breaking_body_descriptors(producer, consumer) == ["id"]

    def test_required_by_consumer_removed_is_breaking(self) -> None:
        producer = _obj({}, required=[])
        consumer = _obj({"id": {"type": "string"}}, required=["id"])
        assert breaking_body_descriptors(producer, consumer) == ["id"]

    def test_nested_object_break_names_the_path(self) -> None:
        producer = _obj({"plan": _obj({"id": {"type": "string"}})})
        consumer = _obj({"plan": _obj({"id": {"type": "string"}, "tier": {"type": "string"}})})
        assert breaking_body_descriptors(producer, consumer) == ["plan.tier"]

    def test_nested_object_type_break_names_the_path(self) -> None:
        producer = _obj({"plan": _obj({"id": {"type": "number"}})})
        consumer = _obj({"plan": _obj({"id": {"type": "string"}})})
        assert breaking_body_descriptors(producer, consumer) == ["plan.id"]

    def test_array_items_break_names_the_path(self) -> None:
        producer = {
            "type": "object",
            "properties": {
                "lines": {"type": "array", "items": _obj({"sku": {"type": "string"}})}
            },
        }
        consumer = {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "array",
                    "items": _obj({"sku": {"type": "string"}, "qty": {"type": "number"}}),
                }
            },
        }
        assert breaking_body_descriptors(producer, consumer) == ["lines[].qty"]

    def test_array_item_type_mismatch_is_breaking(self) -> None:
        producer = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "number"}}},
        }
        consumer = {
            "type": "object",
            "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        }
        assert breaking_body_descriptors(producer, consumer) == ["tags[]"]

    def test_array_vs_scalar_mismatch_is_breaking(self) -> None:
        producer = _obj({"tags": {"type": "string"}})
        consumer = _obj({"tags": {"type": "array", "items": {"type": "string"}}})
        assert breaking_body_descriptors(producer, consumer) == ["tags"]

    def test_enum_narrowing_is_breaking(self) -> None:
        # Producer dropped an enum value the consumer relies on.
        producer = _obj({"status": {"type": "string", "enum": ["active"]}})
        consumer = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        assert breaking_body_descriptors(producer, consumer) == ["status"]


class TestBodyDiffBenign:
    """Additive producer fields / widened requiredness are benign."""

    def test_additive_producer_field_is_benign(self) -> None:
        producer = _obj({"id": {"type": "string"}, "extra": {"type": "string"}})
        consumer = _obj({"id": {"type": "string"}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_producer_now_requires_optional_consumer_field_is_benign(self) -> None:
        # Consumer treated `id` as optional; producer now requires it -> strictly
        # more guarantees, still satisfies the consumer.
        producer = _obj({"id": {"type": "string"}}, required=["id"])
        consumer = _obj({"id": {"type": "string"}}, required=[])
        assert breaking_body_descriptors(producer, consumer) == []

    def test_exact_match_is_benign(self) -> None:
        body = _obj({"id": {"type": "string"}, "plan": _obj({"tier": {"type": "string"}})})
        assert breaking_body_descriptors(body, body) == []

    def test_enum_widening_is_benign(self) -> None:
        producer = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        consumer = _obj({"status": {"type": "string", "enum": ["active"]}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_consumer_with_empty_body_reads_nothing(self) -> None:
        producer = _obj({"id": {"type": "string"}})
        assert breaking_body_descriptors(producer, _obj({})) == []


class TestBodySerializationDeterminism:
    """serialize_body is sorted/byte-stable; parse_body round-trips."""

    def test_serialize_sorts_properties_and_required(self) -> None:
        body = _obj(
            {"b": {"type": "string"}, "a": {"type": "number"}},
            required=["b", "a"],
        )
        serialized = serialize_body(body)
        assert list(serialized["properties"].keys()) == ["a", "b"]
        assert serialized["required"] == ["a", "b"]

    def test_serialize_is_order_independent(self) -> None:
        one = _obj({"x": {"type": "string"}, "y": {"type": "number"}}, required=["y", "x"])
        two = _obj({"y": {"type": "number"}, "x": {"type": "string"}}, required=["x", "y"])
        assert serialize_body(one) == serialize_body(two)

    def test_parse_round_trips(self) -> None:
        body = _obj({"plan": _obj({"id": {"type": "string"}})}, required=["plan"])
        schema = parse_body(body)
        assert isinstance(schema, BodySchema)
        assert serialize_body(body) == serialize_body(schema.to_payload())

    def test_parse_tolerates_non_dict(self) -> None:
        assert parse_body(None).to_payload() == {"type": "", "properties": {}, "required": []}
        assert parse_body([1, 2]).to_payload() == {"type": "", "properties": {}, "required": []}
