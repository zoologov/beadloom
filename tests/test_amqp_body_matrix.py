"""Golden body-diff verdict matrix for the strict AMQP body (S3, G1b — .10).

Strengthens :mod:`tests.test_amqp_body` with the full break-class matrix the
data-strictness brief demands: every break class proven CAUGHT (no
false-CONFIRMED) and every benign change proven SILENT (no false-BREAK), with
precise producer-vs-consumer enum direction, scalar-type cross products,
array-of-objects nested fields, multi-break sorting/dedup, and deep path naming.

A consumer-read body field breaks when, vs the producer body, it is: absent,
structurally type-incompatible, required-by-consumer-but-now-optional/removed,
or enum-narrowed (the producer dropped a value the consumer relies on). Nested
objects and array ``items`` recurse with the same rigor; benign = additive
producer field, widened producer requiredness, widened producer enum.
"""

from __future__ import annotations

import pytest

from beadloom.graph.amqp_body import breaking_body_descriptors


def _obj(
    properties: dict[str, dict[str, object]],
    required: list[str] | None = None,
) -> dict[str, object]:
    node: dict[str, object] = {"type": "object", "properties": properties}
    if required is not None:
        node["required"] = required
    return node


def _arr(items: dict[str, object]) -> dict[str, object]:
    return {"type": "array", "items": items}


class TestScalarTypeMatrix:
    """A consumer-read scalar whose producer type differs structurally breaks."""

    @pytest.mark.parametrize(
        ("producer_type", "consumer_type"),
        [
            ("string", "number"),
            ("number", "string"),
            ("string", "boolean"),
            ("boolean", "string"),
            ("integer", "string"),
            ("string", "integer"),
            ("number", "boolean"),
            ("integer", "boolean"),
        ],
    )
    def test_incompatible_scalar_types_break_the_field(
        self, producer_type: str, consumer_type: str
    ) -> None:
        producer = _obj({"field": {"type": producer_type}})
        consumer = _obj({"field": {"type": consumer_type}})
        assert breaking_body_descriptors(producer, consumer) == ["field"]

    @pytest.mark.parametrize("shared_type", ["string", "number", "integer", "boolean"])
    def test_identical_scalar_types_are_benign(self, shared_type: str) -> None:
        body = _obj({"field": {"type": shared_type}})
        assert breaking_body_descriptors(body, body) == []

    def test_object_vs_scalar_is_breaking(self) -> None:
        producer = _obj({"meta": {"type": "string"}})
        consumer = _obj({"meta": _obj({"x": {"type": "string"}})})
        assert breaking_body_descriptors(producer, consumer) == ["meta"]

    def test_object_vs_array_is_breaking(self) -> None:
        producer = _obj({"meta": _obj({"x": {"type": "string"}})})
        consumer = _obj({"meta": _arr({"type": "string"})})
        assert breaking_body_descriptors(producer, consumer) == ["meta"]

    def test_unknown_producer_type_degrades_to_no_break(self) -> None:
        # Honest degradation: an unknown ("") type on either side is never claimed
        # as a break (a verdict is only as strong as the data behind it).
        producer = _obj({"field": {}})
        consumer = _obj({"field": {"type": "string"}})
        assert breaking_body_descriptors(producer, consumer) == []


class TestRequirednessMatrix:
    """Required-by-consumer fields the producer no longer guarantees break."""

    def test_required_field_removed_entirely_is_breaking(self) -> None:
        producer = _obj({}, required=[])
        consumer = _obj({"id": {"type": "string"}}, required=["id"])
        assert breaking_body_descriptors(producer, consumer) == ["id"]

    def test_required_field_now_optional_is_breaking(self) -> None:
        producer = _obj({"id": {"type": "string"}}, required=[])
        consumer = _obj({"id": {"type": "string"}}, required=["id"])
        assert breaking_body_descriptors(producer, consumer) == ["id"]

    def test_widened_producer_requiredness_is_benign(self) -> None:
        # Producer now requires a field the consumer treated as optional ->
        # strictly more guarantees, never a break.
        producer = _obj({"id": {"type": "string"}}, required=["id"])
        consumer = _obj({"id": {"type": "string"}}, required=[])
        assert breaking_body_descriptors(producer, consumer) == []

    def test_both_required_is_benign(self) -> None:
        body = _obj({"id": {"type": "string"}}, required=["id"])
        assert breaking_body_descriptors(body, body) == []

    def test_neither_required_is_benign(self) -> None:
        body = _obj({"id": {"type": "string"}}, required=[])
        assert breaking_body_descriptors(body, body) == []


class TestEnumDirection:
    """Producer-vs-consumer enum direction, stated precisely.

    The producer body is the message a producer EMITS; the consumer body is what
    a consumer READS. A consumer breaks when the producer can no longer emit a
    value the consumer expects: the producer enum must be a SUPERSET of the
    consumer enum.
    """

    def test_producer_dropped_value_consumer_expects_is_breaking(self) -> None:
        # Consumer expects {active, paused}; producer can only emit {active} ->
        # the consumer may never see `paused` again -> BREAKING.
        producer = _obj({"status": {"type": "string", "enum": ["active"]}})
        consumer = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        assert breaking_body_descriptors(producer, consumer) == ["status"]

    def test_producer_emits_extra_value_consumer_ignores_is_benign(self) -> None:
        # Producer may emit {active, paused, archived}; consumer only enumerates
        # {active, paused}. The producer is a superset -> every value the consumer
        # expects is still producible -> benign (consumer's enum is advisory here).
        producer = _obj(
            {"status": {"type": "string", "enum": ["active", "archived", "paused"]}}
        )
        consumer = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_disjoint_enum_is_breaking(self) -> None:
        producer = _obj({"status": {"type": "string", "enum": ["x"]}})
        consumer = _obj({"status": {"type": "string", "enum": ["y"]}})
        assert breaking_body_descriptors(producer, consumer) == ["status"]

    def test_consumer_no_enum_accepts_any_producer_enum(self) -> None:
        # Consumer enumerates nothing -> it reads any value -> never an enum break.
        producer = _obj({"status": {"type": "string", "enum": ["active"]}})
        consumer = _obj({"status": {"type": "string"}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_producer_no_enum_can_emit_anything(self) -> None:
        # Producer declares no enum -> may emit any value -> superset of any
        # consumer enum -> benign.
        producer = _obj({"status": {"type": "string"}})
        consumer = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_identical_enum_is_benign(self) -> None:
        body = _obj({"status": {"type": "string", "enum": ["active", "paused"]}})
        assert breaking_body_descriptors(body, body) == []


class TestNestedAndArrayPaths:
    """Nested object + array-item breaks recurse and name the precise path."""

    def test_array_of_objects_required_field_break(self) -> None:
        # Producer item no longer requires `sku` the consumer item requires.
        producer = _obj(
            {"lines": _arr(_obj({"sku": {"type": "string"}}, required=[]))}
        )
        consumer = _obj(
            {"lines": _arr(_obj({"sku": {"type": "string"}}, required=["sku"]))}
        )
        assert breaking_body_descriptors(producer, consumer) == ["lines[].sku"]

    def test_array_of_objects_absent_field_break(self) -> None:
        producer = _obj({"lines": _arr(_obj({"sku": {"type": "string"}}))})
        consumer = _obj(
            {"lines": _arr(_obj({"sku": {"type": "string"}, "qty": {"type": "number"}}))}
        )
        assert breaking_body_descriptors(producer, consumer) == ["lines[].qty"]

    def test_array_of_objects_type_break(self) -> None:
        producer = _obj({"lines": _arr(_obj({"qty": {"type": "string"}}))})
        consumer = _obj({"lines": _arr(_obj({"qty": {"type": "number"}}))})
        assert breaking_body_descriptors(producer, consumer) == ["lines[].qty"]

    def test_nested_enum_narrowing_names_nested_path(self) -> None:
        producer = _obj(
            {"plan": _obj({"status": {"type": "string", "enum": ["active"]}})}
        )
        consumer = _obj(
            {"plan": _obj({"status": {"type": "string", "enum": ["active", "paused"]}})}
        )
        assert breaking_body_descriptors(producer, consumer) == ["plan.status"]

    def test_array_item_enum_narrowing_names_item_path(self) -> None:
        producer = _obj({"tags": _arr({"type": "string", "enum": ["a"]})})
        consumer = _obj({"tags": _arr({"type": "string", "enum": ["a", "b"]})})
        assert breaking_body_descriptors(producer, consumer) == ["tags[]"]

    def test_three_level_deep_path_named(self) -> None:
        producer = _obj(
            {"a": _obj({"b": _obj({"c": {"type": "number"}})})}
        )
        consumer = _obj(
            {"a": _obj({"b": _obj({"c": {"type": "string"}})})}
        )
        assert breaking_body_descriptors(producer, consumer) == ["a.b.c"]

    def test_array_of_objects_nested_object_path(self) -> None:
        producer = _obj(
            {"lines": _arr(_obj({"meta": _obj({"sku": {"type": "string"}})}))}
        )
        consumer = _obj(
            {
                "lines": _arr(
                    _obj({"meta": _obj({"sku": {"type": "string"}, "qty": {"type": "number"}})})
                )
            }
        )
        assert breaking_body_descriptors(producer, consumer) == ["lines[].meta.qty"]


class TestMultipleBreaks:
    """Several simultaneous breaks are all named, sorted, and deduped."""

    def test_multiple_breaks_sorted(self) -> None:
        producer = _obj({"id": {"type": "string"}})
        consumer = _obj(
            {
                "zeta": {"type": "string"},
                "alpha": {"type": "number"},
                "id": {"type": "number"},
            }
        )
        # absent: alpha, zeta ; type-break: id -> sorted union, deduped.
        assert breaking_body_descriptors(producer, consumer) == ["alpha", "id", "zeta"]

    def test_break_at_both_top_and_nested_levels(self) -> None:
        producer = _obj({"plan": _obj({"id": {"type": "string"}})})
        consumer = _obj(
            {
                "plan": _obj({"id": {"type": "string"}, "tier": {"type": "string"}}),
                "amount": {"type": "number"},
            }
        )
        assert breaking_body_descriptors(producer, consumer) == ["amount", "plan.tier"]


class TestBenignChanges:
    """No false-BREAK on additive/widened/empty-consumer changes."""

    def test_additive_producer_top_field_benign(self) -> None:
        producer = _obj({"id": {"type": "string"}, "extra": {"type": "string"}})
        consumer = _obj({"id": {"type": "string"}})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_additive_producer_nested_field_benign(self) -> None:
        producer = _obj(
            {"plan": _obj({"id": {"type": "string"}, "added": {"type": "string"}})}
        )
        consumer = _obj({"plan": _obj({"id": {"type": "string"}})})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_additive_producer_array_item_field_benign(self) -> None:
        producer = _obj(
            {"lines": _arr(_obj({"sku": {"type": "string"}, "added": {"type": "number"}}))}
        )
        consumer = _obj({"lines": _arr(_obj({"sku": {"type": "string"}}))})
        assert breaking_body_descriptors(producer, consumer) == []

    def test_empty_consumer_reads_nothing_benign(self) -> None:
        producer = _obj({"id": {"type": "string"}, "amount": {"type": "number"}})
        assert breaking_body_descriptors(producer, _obj({})) == []
